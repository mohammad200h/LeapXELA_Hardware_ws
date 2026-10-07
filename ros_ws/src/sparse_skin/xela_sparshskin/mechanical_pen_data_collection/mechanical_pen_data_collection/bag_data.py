"""Load a bag written by ``rosbag_recorder`` into numpy arrays for offline viewing.

Joint and Xela topics are small and are preloaded in full. Camera images are
only indexed by timestamp and decoded on demand, one frame at a time.

Events labelled by hand in the viewer are stored in the bag itself on
``EVENT_TOPIC`` as std_msgs/String JSON, e.g.
``{"event": "success", "type": "reward", "t": 12.3, "stamp": 1791384635.4, "added": 1791385320.1}``
where ``added`` is the wall-clock time the event was labelled.
"""

from __future__ import annotations

import gc
import glob
import json
import os
import sqlite3
import time
from dataclasses import dataclass

import numpy as np
import rosbag2_py
import yaml
from ament_index_python.packages import get_package_prefix
from rclpy.serialization import deserialize_message, serialize_message
from rosidl_runtime_py.utilities import get_message
from std_msgs.msg import String

IMAGE_TOPIC = "/camera/color/image_raw"
JOINT_TOPICS = ("/leap_state", "/leap_state_sim", "/cmd_xela")
XELA_TOPIC = "/xServTopic"
EVENT_TOPIC = "/manual_events"
EVENT_TYPE = "std_msgs/msg/String"
MAX_SEQUENTIAL_SKIP = 30
EVENT_TIME_RESOLUTION = 1e-3  # seconds; events closer than this count as the same timestamp


@dataclass
class JointSeries:
    t: np.ndarray  # (N,) seconds since bag start
    positions: np.ndarray  # (N, J)
    names: list[str]


@dataclass
class XelaSeries:
    t: np.ndarray  # (N,) seconds since bag start
    taxels: np.ndarray  # (N, T, 3) raw x, y, z
    forces: np.ndarray | None  # (N, T, 3) when xela_server publishes calibrated forces
    sensor_of_taxel: np.ndarray  # (T,) index into sensor_pos
    sensor_pos: list[int]
    delta: np.ndarray  # (N, T) |reading - first reading|
    sensor_mean_delta: np.ndarray  # (N, S) mean of ``delta`` over each sensor's taxels


@dataclass
class BagEvent:
    t: float  # seconds since bag start
    name: str
    added: float = 0.0  # wall-clock time it was labelled (0 for events without it)
    stamp: int = 0  # bag timestamp in ns
    raw: bytes = b""  # serialized message; with ``stamp`` identifies it in the bag


def storage_id_for(uri: str) -> str:
    return "mcap" if glob.glob(os.path.join(uri, "*.mcap")) else "sqlite3"


def open_reader(uri: str, topics: list[str] | None = None) -> rosbag2_py.SequentialReader:
    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=uri, storage_id=storage_id_for(uri)),
        rosbag2_py.ConverterOptions(
            input_serialization_format="cdr", output_serialization_format="cdr"
        ),
    )
    if topics:
        reader.set_filter(rosbag2_py.StorageFilter(topics=topics))
    return reader


def default_bag_dir() -> str:
    """``<colcon workspace>/rosbag``, found from this package's install prefix."""
    prefix = get_package_prefix("mechanical_pen_data_collection")  # <ws>/install/<pkg>
    return os.path.join(os.path.dirname(os.path.dirname(prefix)), "rosbag")


def list_bags(bag_dir: str | None = None) -> list[str]:
    """Bag folders directly under ``bag_dir``, newest first."""
    bag_dir = os.path.expanduser(bag_dir or default_bag_dir())
    bags = [
        os.path.dirname(p) for p in glob.glob(os.path.join(bag_dir, "*", "metadata.yaml"))
    ]
    return sorted(bags, key=os.path.getmtime, reverse=True)


def newest_bag(bag_dir: str | None = None) -> str | None:
    bags = list_bags(bag_dir)
    return bags[0] if bags else None


def image_to_array(msg) -> np.ndarray:
    """Convert a sensor_msgs/Image into an (H, W) or (H, W, 3) array without cv_bridge."""
    h, w, enc = msg.height, msg.width, msg.encoding
    buf = np.frombuffer(msg.data, dtype=np.uint8)
    if enc in ("rgb8", "bgr8", "rgba8", "bgra8"):
        channels = 4 if enc.endswith("a8") else 3
        img = buf.reshape(h, msg.step)[:, : w * channels].reshape(h, w, channels)[..., :3]
        return img[..., ::-1] if enc.startswith("bgr") else img
    if enc in ("mono8", "8UC1"):
        return buf.reshape(h, msg.step)[:, :w]
    if enc in ("mono16", "16UC1"):
        dtype = np.dtype(">u2" if msg.is_bigendian else "<u2")
        return buf.reshape(h, msg.step)[:, : w * 2].copy().view(dtype).reshape(h, w)
    raise ValueError(f"Unsupported image encoding '{enc}'")


class BagData:
    """Preloaded joint/Xela series plus a lazy reader for camera frames."""

    def __init__(self, uri: str) -> None:
        self.uri = os.path.expanduser(uri)
        reader = open_reader(self.uri)
        types = {t.name: t.type for t in reader.get_all_topics_and_types()}
        msg_classes = {
            name: get_message(types[name])
            for name in (*JOINT_TOPICS, XELA_TOPIC)
            if name in types
        }

        joint_raw: dict[str, list] = {name: [] for name in JOINT_TOPICS}
        xela_raw: list = []
        event_raw: list = []
        image_stamps: list[int] = []
        self._t0: int | None = None
        t_last = 0

        while reader.has_next():
            topic, data, stamp = reader.read_next()
            if self._t0 is None:
                self._t0 = stamp
            t_last = stamp
            if topic == IMAGE_TOPIC:
                image_stamps.append(stamp)
            elif topic in joint_raw:
                joint_raw[topic].append((stamp, deserialize_message(data, msg_classes[topic])))
            elif topic == XELA_TOPIC:
                xela_raw.append((stamp, deserialize_message(data, msg_classes[topic])))
            elif topic == EVENT_TOPIC:
                event_raw.append((stamp, bytes(data)))

        self._t0 = self._t0 or 0
        self.duration = (t_last - self._t0) * 1e-9
        self.events = []  # in the order they were added
        for s, raw in event_raw:
            payload = json.loads(deserialize_message(raw, String).data)
            self.events.append(BagEvent(
                t=(s - self._t0) * 1e-9,
                name=payload.get("event", "?"),
                added=float(payload.get("added", 0.0)),
                stamp=s,
                raw=raw,
            ))
        self.events.sort(key=lambda e: e.added)
        self.joints = {name: self._joint_series(msgs) for name, msgs in joint_raw.items()}
        self.xela = self._xela_series(xela_raw)

        self.image_stamps = np.asarray(image_stamps, dtype=np.int64)
        self.image_t = (self.image_stamps - self._t0) * 1e-9
        self._image_reader = open_reader(self.uri, [IMAGE_TOPIC]) if image_stamps else None
        self._image_class = get_message(types[IMAGE_TOPIC]) if image_stamps else None
        self._cached_index: int | None = None
        self._cached_frame: np.ndarray | None = None

    def _seconds(self, stamps: list[int]) -> np.ndarray:
        return (np.asarray(stamps, dtype=np.int64) - self._t0) * 1e-9

    def _joint_series(self, msgs: list) -> JointSeries | None:
        if not msgs:
            return None
        names = list(msgs[0][1].name)
        n_joints = len(msgs[0][1].position)
        kept = [(s, m) for s, m in msgs if len(m.position) == n_joints]
        return JointSeries(
            t=self._seconds([s for s, _ in kept]),
            positions=np.asarray([m.position for _, m in kept], dtype=np.float64),
            names=names or [f"joint_{i}" for i in range(n_joints)],
        )

    def _xela_series(self, msgs: list) -> XelaSeries | None:
        if not msgs:
            return None

        def flatten(msg):
            sensors = sorted(msg.sensors, key=lambda s: int(s.sensor_pos))
            taxels = [[t.x, t.y, t.z] for s in sensors for t in s.taxels]
            forces = [[f.x, f.y, f.z] for s in sensors for f in s.forces]
            return sensors, taxels, forces

        sensors, taxels, forces = flatten(msgs[0][1])
        sensor_pos = [int(s.sensor_pos) for s in sensors]
        sensor_of_taxel = np.repeat(np.arange(len(sensors)), [len(s.taxels) for s in sensors])
        n_taxels = len(taxels)
        has_forces = len(forces) == n_taxels and n_taxels > 0

        stamps, all_taxels, all_forces = [], [], []
        for stamp, msg in msgs:
            _, taxels, forces = flatten(msg)
            if len(taxels) != n_taxels:
                continue
            stamps.append(stamp)
            all_taxels.append(taxels)
            if has_forces:
                all_forces.append(forces if len(forces) == n_taxels else [[np.nan] * 3] * n_taxels)

        taxels_arr = np.asarray(all_taxels, dtype=np.float32).reshape(-1, n_taxels, 3)
        delta = np.linalg.norm(taxels_arr - taxels_arr[:1], axis=-1)
        sensor_mean = np.stack(
            [delta[:, sensor_of_taxel == i].mean(axis=1) for i in range(len(sensors))], axis=1
        )
        return XelaSeries(
            t=self._seconds(stamps),
            taxels=taxels_arr,
            forces=np.asarray(all_forces, dtype=np.float32) if has_forces else None,
            sensor_of_taxel=sensor_of_taxel,
            sensor_pos=sensor_pos,
            delta=delta,
            sensor_mean_delta=sensor_mean,
        )

    def image_at(self, index: int) -> np.ndarray:
        """Decode camera frame ``index`` (an index into ``image_t``)."""
        if index == self._cached_index:
            return self._cached_frame
        # seek() reopens the sqlite storage, so only use it for backward or long jumps.
        cached = self._cached_index
        if cached is None or not 0 < index - cached <= MAX_SEQUENTIAL_SKIP:
            self._image_reader.seek(int(self.image_stamps[index]))
            cached = index - 1
        for _ in range(index - cached):
            _, data, _ = self._image_reader.read_next()
        self._cached_frame = image_to_array(deserialize_message(data, self._image_class))
        self._cached_index = index
        return self._cached_frame

    def event_at(self, t: float) -> BagEvent | None:
        """The event at ``t`` (within ``EVENT_TIME_RESOLUTION``), if there is one."""
        return next((e for e in self.events if abs(e.t - t) < EVENT_TIME_RESOLUTION), None)

    def add_event(self, name: str, event_type: str, t: float) -> BagEvent:
        """Write event ``name`` at ``t`` seconds since bag start into the bag on ``EVENT_TOPIC``.

        Only one event is allowed per timestamp.
        """
        existing = self.event_at(t)
        if existing is not None:
            raise ValueError(f"There is already a '{existing.name}' event at {existing.t:.3f} s")
        event = BagEvent(t=t, name=name, added=time.time(), stamp=self._t0 + int(round(t * 1e9)))
        event.raw = self._event_message(event, event_type)

        def insert(con: sqlite3.Connection, topic_id: int) -> None:
            con.execute(
                "INSERT INTO messages (topic_id, timestamp, data) VALUES (?, ?, ?)",
                (topic_id, event.stamp, event.raw),
            )

        self._edit_events_in_bag(event.stamp, insert, count_delta=1)
        self.events.append(event)
        return event

    def rename_event(self, event: BagEvent, name: str, event_type: str) -> None:
        """Change ``event`` to ``name`` in the bag, keeping its time and add order."""
        data = self._event_message(BagEvent(event.t, name, event.added, event.stamp), event_type)

        def update(con: sqlite3.Connection, topic_id: int) -> None:
            self._expect_one_row(con.execute(
                f"UPDATE messages SET data = ? WHERE id = ({self._EVENT_ROW_SQL})",
                (data, topic_id, event.stamp, event.raw),
            ))

        self._edit_events_in_bag(event.stamp, update, count_delta=0)
        event.name, event.raw = name, data

    def delete_event(self, event: BagEvent) -> None:
        """Remove ``event`` from the bag."""

        def delete(con: sqlite3.Connection, topic_id: int) -> None:
            self._expect_one_row(con.execute(
                f"DELETE FROM messages WHERE id = ({self._EVENT_ROW_SQL})",
                (topic_id, event.stamp, event.raw),
            ))

        self._edit_events_in_bag(event.stamp, delete, count_delta=-1)
        self.events = [e for e in self.events if e is not event]

    # One row only: bags labelled before the one-event-per-timestamp rule can hold
    # several events with the same stamp.
    _EVENT_ROW_SQL = (
        "SELECT id FROM messages WHERE topic_id = ? AND timestamp = ? AND data = ? LIMIT 1"
    )

    @staticmethod
    def _expect_one_row(cursor: sqlite3.Cursor) -> None:
        if cursor.rowcount != 1:
            raise RuntimeError("The event was not found in the bag (was it changed by another program?)")

    @staticmethod
    def _event_message(event: BagEvent, event_type: str) -> bytes:
        payload = {
            "event": event.name,
            "type": event_type,
            "t": round(event.t, 6),
            "stamp": event.stamp * 1e-9,
            "added": event.added,
        }
        return bytes(serialize_message(String(data=json.dumps(payload))))

    def _edit_events_in_bag(self, stamp: int, edit, count_delta: int) -> None:
        """Run ``edit(connection, topic_id)`` on the sqlite3 file holding ``stamp``.

        rosbag2 (Humble) cannot modify a closed bag, so ``EVENT_TOPIC`` messages are
        edited straight in the sqlite3 file and ``metadata.yaml`` is updated to match.
        """
        if storage_id_for(self.uri) != "sqlite3":
            raise RuntimeError("Editing events is only supported for sqlite3 bags")
        meta_path = os.path.join(self.uri, "metadata.yaml")
        with open(meta_path) as f:
            meta = yaml.safe_load(f)
        info = meta["rosbag2_bagfile_information"]
        files = info.get("files") or [{"path": p} for p in info["relative_file_paths"]]
        # Split bags: the message lives in the last file that starts at or before it.
        file_entry = files[0]
        for entry in files:
            if entry.get("starting_time", {}).get("nanoseconds_since_epoch", 0) <= stamp:
                file_entry = entry

        # The rosbag2 sqlite reader holds an exclusive lock, so release it while writing.
        reopen_images = self._image_reader is not None
        self._image_reader = None
        self._cached_index = None
        gc.collect()
        con = sqlite3.connect(os.path.join(self.uri, file_entry["path"]), timeout=5.0)
        try:
            with con:
                row = con.execute("SELECT id FROM topics WHERE name = ?", (EVENT_TOPIC,)).fetchone()
                if row is None:
                    columns = [c[1] for c in con.execute("PRAGMA table_info(topics)")]
                    values = {
                        "name": EVENT_TOPIC,
                        "type": EVENT_TYPE,
                        "serialization_format": "cdr",
                        "offered_qos_profiles": "",
                        "type_description_hash": "",
                    }
                    cols = [c for c in columns if c in values]
                    topic_id = con.execute(
                        f"INSERT INTO topics ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                        [values[c] for c in cols],
                    ).lastrowid
                else:
                    topic_id = row[0]
                edit(con, topic_id)
        finally:
            con.close()
            if reopen_images:
                self._image_reader = open_reader(self.uri, [IMAGE_TOPIC])
        if count_delta == 0:
            return

        topics = info.setdefault("topics_with_message_count", [])
        topic_entry = next((e for e in topics if e["topic_metadata"]["name"] == EVENT_TOPIC), None)
        if topic_entry is None:
            topic_entry = {
                "topic_metadata": {
                    "name": EVENT_TOPIC,
                    "type": EVENT_TYPE,
                    "serialization_format": "cdr",
                    "offered_qos_profiles": "",
                },
                "message_count": 0,
            }
            topics.append(topic_entry)
        topic_entry["message_count"] += count_delta
        info["message_count"] = info.get("message_count", 0) + count_delta
        if "message_count" in file_entry:
            file_entry["message_count"] += count_delta
        tmp_path = meta_path + ".tmp"
        with open(tmp_path, "w") as f:
            yaml.safe_dump(meta, f, sort_keys=False)
        os.replace(tmp_path, meta_path)
