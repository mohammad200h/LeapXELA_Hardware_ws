#!/usr/bin/env python3
"""Record per-finger LEAP hand demonstrations from ``/leap_state`` and compose them.

Create tab: one live plot per finger, each with its own Record and Play controls. A finger's
Record saves a take of that finger only, named after the text box next to it (a timestamped
default is filled in). Takes (the full hand
is stored alongside for reference) go to ``<demo_dir>/fingers/<finger>/<name>.npz``. The camera
feed of the take is written to ``<demo_dir>/camera/<name>.mp4``; every take stores its path as
``video`` and the frame times as ``video_t`` (same time axis as ``t``). The sim-frame joints
from ``sim_topic`` (``convert_hardware_to_sim``) are stored as ``sim_t`` / ``sim_hand_q`` /
``sim_hand_joint_names``; the raw Xela readings on ``xela_topic`` as ``xela_t`` / ``xela``
(L, T, 3) with the live view's baseline at recording time as ``xela_baseline``. The plots only
show ``joint_topic``. Play sends the take chosen in
the dropdown next to it to the hand on ``cmd_topic``, starting from the play bar position.
A finger's Hold switch keeps it at the pose it had when the switch was turned on. While any
finger is held or playing, the other fingers can still be moved by hand. Under the camera, the
taxels of the hand are placed live by forward kinematics (``taxel_fk_util``) from ``sim_topic``;
the Xela readings on ``xela_topic`` (change from a baseline, divided by ``counts_per_unit``)
deform and color them and are drawn as force vectors. Zero takes a new baseline. Under each
finger's joint plot, a second plot shows the magnitude of each of its 30 fingertip taxels
(same baseline and scaling; hover to name a taxel). Next to that
live view, a Playback column shows the camera recording and FK taxels (with the recorded Xela
forces) of the take being played, at the position Play has reached (empty while nothing plays).

Edit tab: same layout as the Create tab without Record / Play / Hold. Each finger picks one of
its takes; its plots (joints, and fingertip taxel magnitudes when the take has Xela readings)
show the whole take and the play bar (or the plot cursor) scrubs through
it, with the camera recording and the FK taxels / Xela forces of the take following. As in the bag viewer,
an event from ``events_file`` (default: installed ``events.json``) is added at the play bar
position; events are bookmarked on the play bar and the plot, listed next to the plot (click
to seek, Edit / Delete) and saved in the take as ``events`` (JSON list of t, name, type, added,
end). Events with ``"length": "duration"`` are marked with two clicks (start, then end) and
their span is shaded on the play bar and the plot; ``end`` is null for instant events.

Compose tab: pick one take per finger with a time offset and speed; fingers without a
take hold the base pose. The result is resampled on a common timeline and saved as
``<demo_dir>/composed/<name>.npz`` with ``t`` (N,), ``q`` (N, 16), ``joint_names`` and
``meta`` (JSON of the settings, so the composition can be loaded and edited again).

Settings tab: the folder takes are saved into (``demo_dir``, can be changed while running), the
command rate, playback ramp and free-finger deadband used while fingers are held
or playing (applied immediately), and the compliant gains / deadband of ``hand_node``
(leaphand_node), read and set through its ROS parameters. Fingers that are playing or held
use the hand node's stiffer playback gains (``stiff_kP`` / ``stiff_kD`` / ``stiff_curr_lim``,
set through ``stiff_joints``) so they track the take; the other fingers stay compliant.

Usage:
  ros2 run mechanical_pen_data_collection record_demonstration \
      [--ros-args -p joint_topic:=leap_state -p sim_topic:=leap_state_sim -p cmd_topic:=cmd_xela \
                  -p image_topic:=/camera/color/image_raw -p demo_dir:=PATH \
                  -p hand_node:=leaphand_node -p xela_topic:=/xServTopic \
                  -p counts_per_unit:=1000.0 -p events_file:=PATH]
"""

from __future__ import annotations

import functools
import json
import os
import re
import signal
import sys
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets  # imported before pyqtgraph so it binds to PyQt5
import pyqtgraph as pg

# pip opencv-python ships its own Qt and points QT_QPA_PLATFORM_PLUGIN_PATH at it,
# which makes PyQt5 fail to load the xcb plugin. PyQt5 must be imported first.
import cv2  # noqa: E402

os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
os.environ.pop("QT_QPA_FONTDIR", None)
import rclpy
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import GetParameters, SetParametersAtomically
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, JointState

from mechanical_pen_data_collection.bag_data import (
    EVENT_TIME_RESOLUTION,
    default_bag_dir,
    image_to_array,
)
from mechanical_pen_data_collection.bag_viewer import (
    SLIDER_STEPS_PER_SEC,
    UNKNOWN_EVENT_COLOR,
    BookmarkSlider,
    EditEventDialog,
    default_events_file,
    index_at,
    load_event_definitions,
)

FINGERS = (("th", "Thumb"), ("if", "Index"), ("mf", "Middle"), ("rf", "Ring"))
FINGER_LABEL = dict(FINGERS)
# Same order as leaphand_node (xela_description/joint_config.json hardware map).
DEFAULT_JOINT_NAMES = [
    f"{finger}_{joint}"
    for finger, joints in (
        ("th", ("cmc", "axl", "mcp", "ipl")),
        ("if", ("mcp", "pip", "rot", "dip")),
        ("mf", ("mcp", "pip", "rot", "dip")),
        ("rf", ("mcp", "pip", "rot", "dip")),
    )
    for joint in joints
]
NUM_JOINTS = len(DEFAULT_JOINT_NAMES)
JOINT_COLORS = ("#e6194b", "#3cb44b", "#4363d8", "#f58231")
LIVE_WINDOW_S = 10.0
HISTORY_LEN = 2000
REFRESH_MS = 50
# Container frame rate only; real frame times are saved in ``video_t``.
VIDEO_FPS = 30.0
# Defaults of the Settings tab (``HoldSettings``).
COMMAND_RATE_HZ = 30.0
# Playback first moves the finger from where it is to the start of the take over this time.
PLAY_RAMP_S = 0.5
# Free fingers follow the hand once pushed further than this (rad); matches leaphand_node's
# ``compliant_deadband`` so gravity sag does not drag them down.
COMPLIANT_DEADBAND = 0.05
PLAY_BAR_STEPS = 1000
# Xela header stamps further than this from the ROS clock are replaced by the receive time.
XELA_MAX_CLOCK_OFFSET_S = 1.0
HOLD_BASE = "— hold base pose —"
# Fingertip patch of each finger in ``taxel_fk_util.XELA_FLATTEN_ORDER``.
TIP_LINKS = {
    "th": "3aftc_palm_link",
    "if": "0aftc_palm_link",
    "mf": "1aftc_palm_link",
    "rf": "2aftc_palm_link",
}
# leaphand_node parameters shown in the Settings tab:
# (name, label, max, step, decimals, suffix, tooltip).
HAND_PARAMS = (
    ("compliant_kP", "Position kP", 2000.0, 5.0, 0, "",
     "Position P gain of the motors (motors 0, 4 and 8 use 75%). "
     "Higher = held fingers resist pushing more"),
    ("compliant_kD", "Position kD", 2000.0, 5.0, 0, "", "Position D gain (damping) of the motors"),
    ("compliant_curr_lim", "Current limit", 1000.0, 10.0, 0, "",
     "Goal current of the motors (Dynamixel units). Caps how hard a held finger pushes back"),
    ("compliant_deadband", "Deadband", 0.5, 0.005, 3, " rad",
     "leaphand_node moves a joint's goal to where it is once it is pushed further than this "
     "(rad), so fingers stay where they are posed. Paused while fingers are held or playing "
     "(this GUI's free-finger deadband applies then)"),
    ("stiff_kP", "Playback kP", 2000.0, 5.0, 0, "",
     "Position P gain of the fingers that are playing or held (the others keep the compliant "
     "gains). Higher = they track the take more closely"),
    ("stiff_kD", "Playback kD", 2000.0, 5.0, 0, "",
     "Position D gain (damping) of the fingers that are playing or held"),
    ("stiff_curr_lim", "Playback current limit", 1000.0, 10.0, 0, "",
     "Goal current of the fingers that are playing or held (Dynamixel units). Raise it if a "
     "played finger cannot push hard enough, e.g. to click the pen"),
)

pg.setConfigOptions(antialias=True)


def default_demo_dir() -> str:
    try:
        return os.path.join(os.path.dirname(default_bag_dir()), "demonstrations")
    except Exception:  # package not installed (e.g. run from source)
        return os.path.expanduser("~/demonstrations")


def finger_indices(joint_names: list[str], finger: str) -> list[int]:
    names = joint_names if len(joint_names) == NUM_JOINTS else DEFAULT_JOINT_NAMES
    return [i for i, name in enumerate(names) if name.startswith(f"{finger}_")]


def take_columns(joint_names: list[str], take: FingerTake) -> list[int]:
    """Columns of ``joint_names`` that the joints of ``take`` map to."""
    if all(name in joint_names for name in take.joint_names):
        return [joint_names.index(name) for name in take.joint_names]
    return finger_indices(joint_names, take.finger)


@functools.cache
def fingertip_taxel_ids() -> dict[str, np.ndarray] | None:
    """Hardware Xela ids of each finger's fingertip taxels (None if taxel_fk_util cannot load)."""
    try:
        from mechanical_pen_data_collection import taxel_fk_util as fk
    except Exception:
        return None
    links = list(fk.XELA_FLATTEN_ORDER)
    starts = np.cumsum([0, *fk.XELA_FLATTEN_ORDER.values()])
    return {
        finger: fk.TAXEL_IDS_IN_FK_ORDER[starts[links.index(link)]: starts[links.index(link) + 1]]
        for finger, link in TIP_LINKS.items()
    }


def taxel_magnitudes(
    readings: np.ndarray, baseline: np.ndarray, ids: np.ndarray, counts_per_unit: float
) -> np.ndarray:
    """(N, len(ids)) |reading - baseline| / counts_per_unit of taxels ``ids`` from (N, T, 3)."""
    return np.linalg.norm((readings[:, ids] - baseline[ids]) / counts_per_unit, axis=-1)


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip()).strip("._") or "take"


def unique_path(directory: str, name: str) -> str:
    path = os.path.join(directory, f"{name}.npz")
    n = 1
    while os.path.exists(path):
        path = os.path.join(directory, f"{name}_{n}.npz")
        n += 1
    return path


@dataclass
class HoldSettings:
    """How held / playing fingers are commanded and how the free fingers comply meanwhile."""

    command_rate: float = COMMAND_RATE_HZ  # Hz, rate of commands on cmd_topic
    ramp_s: float = PLAY_RAMP_S
    deadband: float = COMPLIANT_DEADBAND  # rad

    @property
    def interval_ms(self) -> int:
        return max(1, round(1000.0 / self.command_rate))


def parameter_value(value: ParameterValue):
    """Python value of a ``ParameterValue`` (None if the parameter is not set)."""
    return {
        ParameterType.PARAMETER_BOOL: value.bool_value,
        ParameterType.PARAMETER_INTEGER: value.integer_value,
        ParameterType.PARAMETER_DOUBLE: value.double_value,
        ParameterType.PARAMETER_STRING: value.string_value,
    }.get(value.type)


@dataclass
class TakeEvent:
    t: float  # seconds from the start of the take
    name: str  # key of events.json
    type: str = ""
    added: float = 0.0  # wall-clock time it was labelled
    end: float | None = None  # end of an event with ``"length": "duration"`` (None if instant)

    def span_text(self) -> str:
        return f"{self.t:.2f} s" if self.end is None else f"{self.t:.2f}-{self.end:.2f} s"


@dataclass
class FingerTake:
    finger: str
    path: str
    t: np.ndarray  # (N,) seconds from the start of the take
    q: np.ndarray  # (N, 4) joints of ``finger``
    joint_names: list[str]  # names of the 4 columns of ``q``
    hand_q: np.ndarray  # (N, 16) whole hand during the take
    hand_joint_names: list[str]
    video: str = ""  # camera recording of the take ("" if no frames were received)
    video_t: np.ndarray = field(default_factory=lambda: np.empty(0))  # (M,) frame times
    sim_t: np.ndarray = field(default_factory=lambda: np.empty(0))  # (K,) sim_topic times
    sim_hand_q: np.ndarray = field(default_factory=lambda: np.empty((0, NUM_JOINTS)))  # (K, 16)
    sim_hand_joint_names: list[str] = field(default_factory=list)
    xela_t: np.ndarray = field(default_factory=lambda: np.empty(0))  # (L,) xela_topic times
    xela: np.ndarray = field(default_factory=lambda: np.empty((0, 0, 3)))  # (L, T, 3) raw x, y, z
    # (T, 3) no-contact reading the forces are measured from (live view's at recording time)
    xela_baseline: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    events: list[TakeEvent] = field(default_factory=list)  # in the order they were added

    @property
    def name(self) -> str:
        return os.path.splitext(os.path.basename(self.path))[0]

    @property
    def duration(self) -> float:
        return float(self.t[-1]) if len(self.t) else 0.0

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        np.savez_compressed(
            self.path,
            finger=self.finger,
            t=self.t,
            q=self.q,
            joint_names=np.array(self.joint_names),
            hand_q=self.hand_q,
            hand_joint_names=np.array(self.hand_joint_names),
            video=self.video,
            video_t=self.video_t,
            sim_t=self.sim_t,
            sim_hand_q=self.sim_hand_q,
            sim_hand_joint_names=np.array(self.sim_hand_joint_names),
            xela_t=self.xela_t,
            xela=self.xela,
            xela_baseline=self.xela_baseline,
            events=json.dumps([asdict(e) for e in self.events]),
        )

    def event_at(self, t: float) -> TakeEvent | None:
        """The event at ``t`` (within ``EVENT_TIME_RESOLUTION``), if there is one."""
        return next((e for e in self.events if abs(e.t - t) < EVENT_TIME_RESOLUTION), None)

    @classmethod
    def load(cls, path: str) -> FingerTake:
        with np.load(path, allow_pickle=False) as data:
            return cls(
                finger=str(data["finger"]),
                path=path,
                t=data["t"],
                q=data["q"],
                joint_names=[str(n) for n in data["joint_names"]],
                hand_q=data["hand_q"],
                hand_joint_names=[str(n) for n in data["hand_joint_names"]],
                video=str(data["video"]) if "video" in data.files else "",
                video_t=data["video_t"] if "video_t" in data.files else np.empty(0),
                sim_t=data["sim_t"] if "sim_t" in data.files else np.empty(0),
                sim_hand_q=(
                    data["sim_hand_q"] if "sim_hand_q" in data.files else np.empty((0, NUM_JOINTS))
                ),
                sim_hand_joint_names=(
                    [str(n) for n in data["sim_hand_joint_names"]]
                    if "sim_hand_joint_names" in data.files
                    else []
                ),
                xela_t=data["xela_t"] if "xela_t" in data.files else np.empty(0),
                xela=data["xela"] if "xela" in data.files else np.empty((0, 0, 3)),
                xela_baseline=(
                    data["xela_baseline"] if "xela_baseline" in data.files else np.empty((0, 3))
                ),
                events=(
                    [TakeEvent(**e) for e in json.loads(str(data["events"]))]
                    if "events" in data.files
                    else []
                ),
            )


class TakeStore:
    """Takes on disk under ``<demo_dir>/fingers/<finger>/``, cached by mtime."""

    def __init__(self, demo_dir: str) -> None:
        self.demo_dir = demo_dir
        self._cache: dict[str, tuple[float, FingerTake]] = {}

    def finger_dir(self, finger: str) -> str:
        return os.path.join(self.demo_dir, "fingers", finger)

    @property
    def composed_dir(self) -> str:
        return os.path.join(self.demo_dir, "composed")

    def video_path(self, name: str) -> str:
        return os.path.join(self.demo_dir, "camera", f"{name}.mp4")

    def take_path(self, finger: str, name: str) -> str:
        return os.path.join(self.finger_dir(finger), f"{name}.npz")

    def new_take_name(self, prefix: str = "take") -> str:
        """A timestamped name not yet used by any finger take or camera recording."""
        return self.unique_take_name(datetime.now().strftime(f"{prefix}_%Y%m%d_%H%M%S"))

    def unique_take_name(self, base: str) -> str:
        """``base``, suffixed if needed so no finger take or camera recording uses it yet."""
        name, n = base, 1
        while os.path.exists(self.video_path(name)) or any(
            os.path.exists(self.take_path(finger, name)) for finger, _ in FINGERS
        ):
            name = f"{base}_{n}"
            n += 1
        return name

    def list(self, finger: str) -> list[str]:
        """Take paths for ``finger``, newest first."""
        directory = self.finger_dir(finger)
        if not os.path.isdir(directory):
            return []
        paths = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".npz")]
        return sorted(paths, key=os.path.getmtime, reverse=True)

    def load(self, path: str) -> FingerTake:
        mtime = os.path.getmtime(path)
        cached = self._cache.get(path)
        if cached is None or cached[0] != mtime:
            cached = (mtime, FingerTake.load(path))
            self._cache[path] = cached
        return cached[1]

    def delete(self, path: str) -> None:
        """Removes the take at ``path``, and its camera recording unless another finger's take
        of the same recording still uses it."""
        try:
            video = self.load(path).video
        except Exception:
            video = ""
        os.remove(path)
        self._cache.pop(path, None)
        name = os.path.splitext(os.path.basename(path))[0]
        shared = any(
            os.path.exists(self.take_path(finger, name)) for finger, _ in FINGERS
        )
        if video and not shared and os.path.exists(video):
            os.remove(video)


@dataclass
class Recording:
    t: np.ndarray  # (N,) joint times, starting at 0
    q: np.ndarray  # (N, 16)
    video: str  # "" if no camera frames were received
    video_t: np.ndarray  # (M,) frame times on the same axis as ``t``
    sim_t: np.ndarray  # (K,) sim_topic times on the same axis as ``t``
    sim_q: np.ndarray  # (K, 16)
    sim_joint_names: list[str]
    xela_t: np.ndarray  # (L,) xela_topic times on the same axis as ``t``
    xela: np.ndarray  # (L, T, 3) raw Xela readings by hardware id


class LeapStateListener(Node):
    """Buffers ``leap_state``, ``leap_state_sim`` and the camera for the live view and records
    them while asked to."""

    def __init__(self) -> None:
        super().__init__("record_demonstration")
        topic = self.declare_parameter("joint_topic", "leap_state").value
        self.sim_topic = self.declare_parameter("sim_topic", "leap_state_sim").value
        cmd_topic = self.declare_parameter("cmd_topic", "cmd_xela").value
        self.image_topic = self.declare_parameter("image_topic", "/camera/color/image_raw").value
        self.xela_topic = self.declare_parameter("xela_topic", "/xServTopic").value
        self.counts_per_unit = float(self.declare_parameter("counts_per_unit", 1000.0).value)
        self.events_file = self.declare_parameter("events_file", "").value or default_events_file()
        self.demo_dir = os.path.expanduser(
            self.declare_parameter("demo_dir", "").value or default_demo_dir()
        )

        self._lock = threading.Lock()
        self._joint_names: list[str] = []
        self._history: deque[tuple[float, np.ndarray]] = deque(maxlen=HISTORY_LEN)
        self._recording = False
        self._rec_t: list[float] = []
        self._rec_q: list[np.ndarray] = []
        self._frame: np.ndarray | None = None  # latest RGB camera frame
        self._frame_seq = 0
        self._video_path = ""
        self._video: cv2.VideoWriter | None = None
        self._rec_frame_t: list[float] = []
        self._sim: tuple[int, list[str], np.ndarray | None] = (0, [], None)  # (seq, names, q)
        self._rec_sim_t: list[float] = []
        self._rec_sim_q: list[np.ndarray] = []
        self._xela: tuple[int, np.ndarray | None] = (0, None)  # (seq, (T, 3) raw x, y, z)
        self._rec_xela_t: list[float] = []
        self._rec_xela: list[np.ndarray] = []
        self._xela_history: deque[tuple[float, np.ndarray]] = deque(maxlen=HISTORY_LEN)

        self.create_subscription(JointState, topic, self._on_state, 10)
        self.create_subscription(JointState, self.sim_topic, self._on_sim_state, 10)
        if self.image_topic:
            self.create_subscription(Image, self.image_topic, self._on_image, qos_profile_sensor_data)
        if self.xela_topic:
            try:
                from xela_server_ros2.msg import SensStream
            except ImportError as e:
                self.get_logger().warn(f"xela_server_ros2 not available, no taxel forces: {e}")
                self.xela_topic = ""
            else:
                self.create_subscription(SensStream, self.xela_topic, self._on_xela, 10)
        self._cmd_pub = self.create_publisher(JointState, cmd_topic, 10)
        self.hand_node = self.declare_parameter("hand_node", "leaphand_node").value
        self._get_params = self.create_client(GetParameters, f"{self.hand_node}/get_parameters")
        self._set_params = self.create_client(
            SetParametersAtomically, f"{self.hand_node}/set_parameters_atomically"
        )
        self.get_logger().info(
            f"Listening on '{topic}', '{self.sim_topic}', '{self.image_topic or '(no camera)'}' "
            f"and '{self.xela_topic or '(no xela)'}', "
            f"playing takes on '{cmd_topic}', saving demonstrations to '{self.demo_dir}'"
        )

    def send_command(self, q: np.ndarray) -> None:
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        msg.position = [float(v) for v in q]
        self._cmd_pub.publish(msg)

    # ---- parameters of the hand node (called back from the executor thread) --------------

    def hand_params_ready(self) -> bool:
        return self._get_params.service_is_ready() and self._set_params.service_is_ready()

    @staticmethod
    def _call(client, request, convert, done) -> None:
        def finished(future) -> None:
            try:
                result = convert(future.result())
            except Exception as e:
                result = e
            done(result)

        client.call_async(request).add_done_callback(finished)

    def get_hand_params(self, names: list[str], done) -> None:
        """Calls ``done`` with {name: value} of the hand node's parameters, or an exception."""
        self._call(
            self._get_params,
            GetParameters.Request(names=list(names)),
            lambda res: {n: parameter_value(v) for n, v in zip(names, res.values)},
            done,
        )

    def set_hand_params(self, values: dict[str, float | str], done) -> None:
        """Sets double / string parameters of the hand node at once; ``done`` gets the
        ``SetParametersResult`` or an exception."""
        params = [
            Parameter(
                name=name,
                value=(
                    ParameterValue(type=ParameterType.PARAMETER_STRING, string_value=v)
                    if isinstance(v, str)
                    else ParameterValue(type=ParameterType.PARAMETER_DOUBLE, double_value=float(v))
                ),
            )
            for name, v in values.items()
        ]
        self._call(
            self._set_params,
            SetParametersAtomically.Request(parameters=params),
            lambda res: res.result,
            done,
        )

    def set_stiff_joints(self, names: list[str]) -> bool:
        """Makes the hand node use its stiff_* gains on ``names`` (compliant gains elsewhere).
        False if the hand node is not up."""
        if not self.hand_params_ready():
            return False
        joints = ",".join(names)

        def done(result) -> None:
            if isinstance(result, Exception) or not result.successful:
                reason = result if isinstance(result, Exception) else result.reason
                self.get_logger().warn(f"Could not set stiff_joints to '{joints}': {reason}")

        self.set_hand_params({"stiff_joints": joints}, done)
        return True

    def _stamp(self, header) -> float:
        stamp = header.stamp.sec + header.stamp.nanosec * 1e-9
        return stamp if stamp != 0.0 else self.get_clock().now().nanoseconds * 1e-9

    def _on_image(self, msg: Image) -> None:
        try:
            frame = image_to_array(msg)
        except ValueError as e:
            self.get_logger().warn(str(e), throttle_duration_sec=5.0)
            return
        if frame.ndim == 2:
            if frame.dtype != np.uint8:
                frame = (frame >> 8).astype(np.uint8)
            frame = np.repeat(frame[..., None], 3, axis=2)
        frame = np.ascontiguousarray(frame)
        stamp = self._stamp(msg.header)
        with self._lock:
            self._frame = frame
            self._frame_seq += 1
            if not (self._recording and self._video_path):
                return
            if self._video is None:
                h, w = frame.shape[:2]
                os.makedirs(os.path.dirname(self._video_path), exist_ok=True)
                self._video = cv2.VideoWriter(
                    self._video_path, cv2.VideoWriter_fourcc(*"mp4v"), VIDEO_FPS, (w, h)
                )
            self._video.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            self._rec_frame_t.append(stamp)

    def _on_state(self, msg: JointState) -> None:
        if len(msg.position) != NUM_JOINTS:
            self.get_logger().warn(
                f"Expected {NUM_JOINTS} joints, got {len(msg.position)}", throttle_duration_sec=5.0
            )
            return
        stamp = self._stamp(msg.header)
        q = np.asarray(msg.position, dtype=float)
        with self._lock:
            if len(msg.name) == NUM_JOINTS:
                self._joint_names = list(msg.name)
            self._history.append((stamp, q))
            if self._recording:
                self._rec_t.append(stamp)
                self._rec_q.append(q)

    def _on_sim_state(self, msg: JointState) -> None:
        if len(msg.position) != NUM_JOINTS or len(msg.name) != NUM_JOINTS:
            self.get_logger().warn(
                f"Expected {NUM_JOINTS} named joints on '{self.sim_topic}', got {len(msg.position)}",
                throttle_duration_sec=5.0,
            )
            return
        stamp = self._stamp(msg.header)
        q = np.asarray(msg.position, dtype=float)
        with self._lock:
            self._sim = (self._sim[0] + 1, list(msg.name), q)
            if self._recording:
                self._rec_sim_t.append(stamp)
                self._rec_sim_q.append(q)

    def _on_xela(self, msg) -> None:
        # Sensors concatenated in order give the hardware taxel ids.
        readings = np.array(
            [[t.x, t.y, t.z] for s in msg.sensors for t in s.taxels], dtype=np.float64
        ).reshape(-1, 3)
        stamp = self._stamp(msg.header)
        now = self.get_clock().now().nanoseconds * 1e-9
        if abs(stamp - now) > XELA_MAX_CLOCK_OFFSET_S:
            # xela_server stamping with another clock would misalign the takes and the plots.
            stamp = now
        with self._lock:
            self._xela = (self._xela[0] + 1, readings)
            self._xela_history.append((stamp, readings))
            # A take holds one taxel count; readings of another size are dropped.
            if self._recording and (
                not self._rec_xela or len(readings) == len(self._rec_xela[0])
            ):
                self._rec_xela_t.append(stamp)
                self._rec_xela.append(readings.astype(np.float32))

    def latest_xela(self) -> tuple[int, np.ndarray | None]:
        """(sequence number, (T, 3) raw Xela readings by hardware id) of the latest message."""
        with self._lock:
            return self._xela

    def xela_since(self, seq: int) -> tuple[int, list[tuple[float, np.ndarray]]]:
        """(latest sequence number, (stamp, raw readings) of the messages after ``seq``)."""
        with self._lock:
            latest = self._xela[0]
            n = min(latest - seq, len(self._xela_history))
            return latest, list(self._xela_history)[len(self._xela_history) - n:] if n > 0 else []

    def latest_sim(self) -> tuple[int, list[str], np.ndarray | None]:
        """(sequence number, joint names, positions) of the latest ``sim_topic`` message."""
        with self._lock:
            return self._sim

    @property
    def joint_names(self) -> list[str]:
        with self._lock:
            return list(self._joint_names) or list(DEFAULT_JOINT_NAMES)

    def history(self) -> tuple[np.ndarray, np.ndarray]:
        """(t, q) of recent messages, shapes (N,) and (N, 16)."""
        with self._lock:
            items = list(self._history)
        if not items:
            return np.empty(0), np.empty((0, NUM_JOINTS))
        return np.array([t for t, _ in items]), np.stack([q for _, q in items])

    def latest(self) -> np.ndarray | None:
        with self._lock:
            return self._history[-1][1].copy() if self._history else None

    def latest_frame(self) -> tuple[int, np.ndarray | None]:
        """(sequence number, latest RGB frame); the number changes with every new frame."""
        with self._lock:
            return self._frame_seq, self._frame

    @property
    def recording(self) -> bool:
        return self._recording

    def recorded_count(self) -> tuple[float, int]:
        """(joint duration in seconds, camera frames) of the recording in progress."""
        with self._lock:
            n = len(self._rec_t)
            return (self._rec_t[-1] - self._rec_t[0]) if n > 1 else 0.0, len(self._rec_frame_t)

    def start_recording(self, video_path: str = "") -> None:
        with self._lock:
            self._rec_t, self._rec_q, self._rec_frame_t = [], [], []
            self._rec_sim_t, self._rec_sim_q = [], []
            self._rec_xela_t, self._rec_xela = [], []
            self._video_path = video_path
            self._recording = True

    def stop_recording(self) -> Recording:
        with self._lock:
            self._recording = False
            if self._video is not None:
                self._video.release()
                self._video = None
            t = np.array(self._rec_t)
            q = np.stack(self._rec_q) if self._rec_q else np.empty((0, NUM_JOINTS))
            video_t = np.array(self._rec_frame_t)
            video = self._video_path if len(video_t) else ""
            self._video_path = ""
            sim_t = np.array(self._rec_sim_t)
            sim_q = np.stack(self._rec_sim_q) if self._rec_sim_q else np.empty((0, NUM_JOINTS))
            sim_names = list(self._sim[1])
            xela_t = np.array(self._rec_xela_t)
            xela = np.stack(self._rec_xela) if self._rec_xela else np.empty((0, 0, 3), np.float32)
            self._rec_xela_t, self._rec_xela = [], []
        t0 = t[0] if len(t) else (video_t[0] if len(video_t) else 0.0)
        return Recording(
            t=t - t0,
            q=q,
            video=video,
            video_t=video_t - t0,
            sim_t=sim_t - t0,
            sim_q=sim_q,
            sim_joint_names=sim_names,
            xela_t=xela_t - t0,
            xela=xela,
        )


class CameraView(QtWidgets.QLabel):
    """Shows RGB frames scaled to fit while keeping their aspect ratio."""

    def __init__(self, topic: str) -> None:
        super().__init__(f"Waiting for {topic} ..." if topic else "No camera (image_topic is empty)")
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.setStyleSheet("background-color: black; color: white;")
        self._pixmap: QtGui.QPixmap | None = None

    def set_message(self, text: str) -> None:
        self._pixmap = None
        self.clear()
        self.setText(text)

    def set_frame(self, frame: np.ndarray) -> None:
        h, w = frame.shape[:2]
        image = QtGui.QImage(frame.data, w, h, 3 * w, QtGui.QImage.Format_RGB888)
        self._pixmap = QtGui.QPixmap.fromImage(image)
        self._show()

    def _show(self) -> None:
        if self._pixmap is not None:
            self.setPixmap(
                self._pixmap.scaled(self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            )

    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        self._show()


class TakeVideo:
    """Reads frames of a take's camera recording by index (sequentially when possible)."""

    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._path = ""
        self._index = -1

    def read(self, path: str, index: int) -> np.ndarray | None:
        """RGB frame ``index`` of ``path``; None if it is already shown or cannot be read."""
        if path != self._path:
            self.release()
            self._cap = cv2.VideoCapture(path)
            self._path = path
        if index == self._index:
            return None
        if index != self._index + 1:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, bgr = self._cap.read()
        if not ok:
            self._index = -1
            return None
        self._index = index
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
        self._cap, self._path, self._index = None, "", -1


def show_take_at(
    take: FingerTake, t: float, camera: CameraView, hand: HandView, video: TakeVideo
) -> None:
    """Camera frame and FK taxels of ``take`` at ``t`` seconds into it."""
    if take.video and len(take.video_t) and os.path.exists(take.video):
        frame = video.read(take.video, max(index_at(take.video_t, t), 0))
        if frame is not None:
            camera.set_frame(frame)
    else:
        video.release()
        camera.set_message(f"No camera recording in {take.name}")
    if len(take.sim_t):
        j = max(index_at(take.sim_t, t), 0)
        hand.set_joints(take.sim_hand_joint_names, take.sim_hand_q[j])
    new_take = hand.take_path != take.path
    if new_take:
        hand.take_path = take.path
        hand.take_xela_index = -1
        hand.set_baseline(take.xela_baseline if len(take.xela_baseline) else None)
    if len(take.xela_t):
        k = max(index_at(take.xela_t, t), 0)
        if k != hand.take_xela_index:
            hand.take_xela_index = k
            hand.set_readings(take.xela[k], source=f"Recorded Xela of {take.name}")
    elif new_take:
        hand.clear_readings(f"No Xela readings in {take.name}")


def side_column(title: QtWidgets.QLabel, camera: CameraView, hand: HandView) -> QtWidgets.QWidget:
    """``title`` above the camera and the FK taxels (split vertically)."""
    split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
    split.addWidget(camera)
    split.addWidget(hand)
    column = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(column)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(title)
    layout.addWidget(split, 1)
    return column


def rgba(colors: np.ndarray) -> np.ndarray:
    return np.column_stack([colors, np.ones(len(colors))])


class HandView(QtWidgets.QWidget):
    """Taxels of the hand placed by forward kinematics from sim-frame joint angles, deformed,
    colored and given force vectors by the live Xela readings (change from a baseline taken at
    the first reading or with Zero), as in the bag viewer."""

    TAXEL_SIZE = 0.003  # m

    def __init__(
        self,
        sim_topic: str,
        xela_topic: str,
        counts_per_unit: float,
        waiting: str | None = None,
        no_xela: str = "No taxel forces (xela_topic is empty)",
    ) -> None:
        """``waiting`` / ``no_xela`` replace the default texts shown before joints arrive and
        when there is no Xela topic."""
        super().__init__()
        self.setMinimumSize(320, 240)
        self.xela_topic = xela_topic
        self.counts_per_unit = counts_per_unit
        self._last: np.ndarray | None = None
        self._pos: np.ndarray | None = None  # (368, 3) FK taxel positions
        self._rot: np.ndarray | None = None  # (368, 3, 3) taxel local -> world
        self._readings: np.ndarray | None = None  # (T, 3) latest raw Xela readings by id
        self._baseline: np.ndarray | None = None  # (368, 3)
        self.take_path: str | None = None  # take whose recorded readings are shown
        self.take_xela_index = -1  # index into that take's ``xela`` shown
        self._fk = None

        self.deform_box = QtWidgets.QCheckBox("Deform")
        self.deform_box.setToolTip("Move and color the taxels by their force")
        self.vectors_box = QtWidgets.QCheckBox("Force vectors")
        self.zero_btn = QtWidgets.QPushButton("Zero")
        self.zero_btn.setToolTip("Use the current Xela reading as the no-contact baseline")
        self.status = QtWidgets.QLabel()
        for box in (self.deform_box, self.vectors_box):
            box.setChecked(True)
            box.toggled.connect(lambda _: self._redraw())
        self.zero_btn.clicked.connect(self._zero)
        controls = QtWidgets.QHBoxLayout()
        for w in (self.deform_box, self.vectors_box, self.zero_btn):
            controls.addWidget(w)
        controls.addWidget(self.status, 1)
        self.stack = QtWidgets.QStackedWidget()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(self.stack, 1)
        self._set_status(f"Waiting for {xela_topic} ..." if xela_topic else no_xela)

        try:
            import pyqtgraph.opengl as gl

            from mechanical_pen_data_collection import taxel_fk_util as fk
        except Exception as e:
            self.stack.addWidget(self._message(f"Hand view unavailable: {e}"))
            self._enable_controls(False)
            return
        self._fk = fk
        self._patch_colors = rgba(fk.taxel_patch_colors(fk.PATCH_IDS_IN_FK_ORDER))
        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor((20, 20, 26))
        self._scatter = gl.GLScatterPlotItem(
            pos=np.zeros((fk.NUM_TAXELS, 3)),
            color=self._patch_colors,
            size=self.TAXEL_SIZE,
            pxMode=False,
        )
        self._vectors = gl.GLLinePlotItem(mode="lines", width=2, antialias=True)
        self._vectors.hide()
        self.view.addItem(self._scatter)
        self.view.addItem(self._vectors)
        self.view.addItem(gl.GLAxisItem(size=QtGui.QVector3D(0.04, 0.04, 0.04)))
        self.stack.addWidget(
            self._message(waiting or f"Waiting for {sim_topic} (convert_hardware_to_sim) ...")
        )
        self.stack.addWidget(self.view)
        self._enable_controls(bool(xela_topic))

    @staticmethod
    def _message(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("background-color: black; color: white;")
        return label

    def _enable_controls(self, on: bool) -> None:
        for w in (self.deform_box, self.vectors_box, self.zero_btn):
            w.setEnabled(on)

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status.setText(f"<span style='color:#d32f2f'>{text}</span>" if error else text)

    def _valid_readings(self) -> np.ndarray | None:
        r = self._readings
        return r[: self._fk.NUM_TAXELS] if r is not None and len(r) >= self._fk.NUM_TAXELS else None

    def _zero(self) -> None:
        readings = self._valid_readings() if self._fk is not None else None
        if readings is not None:
            self._baseline = readings.copy()
            self._redraw()

    def clear(self) -> None:
        """Back to the waiting text until the next ``set_joints``."""
        self.take_path = None
        if self._fk is not None:
            self._last = None
            self.stack.setCurrentIndex(0)

    @property
    def baseline(self) -> np.ndarray | None:
        return self._baseline

    def set_baseline(self, baseline: np.ndarray | None) -> None:
        """Use ``baseline`` as the no-contact reading (None: the next reading)."""
        if self._fk is not None and baseline is not None and len(baseline) >= self._fk.NUM_TAXELS:
            self._baseline = np.asarray(baseline[: self._fk.NUM_TAXELS], dtype=np.float64)
        else:
            self._baseline = None

    def clear_readings(self, status: str) -> None:
        """Drop the readings (taxels keep their patch colors) and show ``status``."""
        self._readings = None
        self._enable_controls(False)
        self._set_status(status)
        self._redraw()

    def set_joints(self, names: list[str], q: np.ndarray) -> None:
        if self._fk is None or (self._last is not None and np.array_equal(q, self._last)):
            return
        first = self._pos is None
        self._last = q.copy()
        try:
            pos, rot = self._fk.get_fk_taxel_frames(self._fk.joint_angles_in_fk_order(names, q))
        except Exception as e:
            self._fk = None
            self._enable_controls(False)
            self.stack.addWidget(self._message(f"Hand view failed: {e}"))
            self.stack.setCurrentIndex(self.stack.count() - 1)
            return
        self._pos, self._rot = pos[0], rot[0]
        self._redraw()
        self.stack.setCurrentWidget(self.view)
        if first:
            # Side view as in the MuJoCo scene: fingers along +Y, Z up.
            center = self._pos.mean(axis=0)
            self.view.setCameraPosition(
                pos=QtGui.QVector3D(*center), distance=0.35, elevation=20, azimuth=-125
            )

    def set_readings(self, readings: np.ndarray, source: str | None = None) -> None:
        """Show raw Xela ``readings``; ``source`` names them in the status (default: live topic)."""
        if self._fk is None:
            return
        self._readings = readings
        valid = self._valid_readings()
        if valid is None:
            self._set_status(
                f"{len(readings)} taxels in {source or self.xela_topic}, "
                f"expected {self._fk.NUM_TAXELS}",
                error=True,
            )
        else:
            if self._baseline is None:
                self._baseline = valid.copy()
            self._enable_controls(True)
            self._set_status(source or f"{self.xela_topic} live")
        self._redraw()

    def _redraw(self) -> None:
        if self._fk is None or self._pos is None:
            return
        fk = self._fk
        readings = self._valid_readings()
        forces_local = None
        if readings is not None and self._baseline is not None:
            forces_local = fk.taxel_readings_to_local_forces(
                readings, self._baseline, self.counts_per_unit
            )
        pos, colors = self._pos, self._patch_colors
        if forces_local is not None and self.deform_box.isChecked():
            pos = fk.deform_taxel_positions(self._pos, self._rot, forces_local)
            vmax = max(float(np.percentile(np.linalg.norm(forces_local, axis=-1), 98)), 1e-6)
            colors = rgba(fk.force_magnitude_colors(forces_local, vmax=vmax))
        self._scatter.setData(pos=pos, color=colors)

        starts = np.empty((0, 3))
        if forces_local is not None and self.vectors_box.isChecked():
            forces_world = fk.local_forces_to_world(forces_local, self._rot)
            starts, ends, vector_colors = fk.force_vector_segments(pos, forces_world)
        if len(starts) == 0:
            self._vectors.hide()
            return
        segments = np.empty((2 * len(starts), 3))
        segments[0::2], segments[1::2] = starts, ends
        self._vectors.setData(pos=segments, color=np.repeat(rgba(vector_colors), 2, axis=0))
        self._vectors.show()


STOP_STYLE = "background-color: #d32f2f; color: white;"


class ToggleSwitch(QtWidgets.QAbstractButton):
    """Sliding on/off switch (iOS style)."""

    OFF_COLOR = QtGui.QColor("#9e9e9e")
    ON_COLOR = QtGui.QColor("#34c759")

    def __init__(self) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedSize(self.sizeHint())
        self._knob = 0.0  # 0 = off (left), 1 = on (right)
        self._anim = QtCore.QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        self.toggled.connect(self._slide)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(48, 28)

    def _get_knob(self) -> float:
        return self._knob

    def _set_knob(self, value: float) -> None:
        self._knob = value
        self.update()

    knob = QtCore.pyqtProperty(float, _get_knob, _set_knob)

    def _slide(self, on: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._knob)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, _) -> None:
        a = self._knob
        off, on = self.OFF_COLOR, self.ON_COLOR
        track = QtGui.QColor(
            int(off.red() + a * (on.red() - off.red())),
            int(off.green() + a * (on.green() - off.green())),
            int(off.blue() + a * (on.blue() - off.blue())),
        )
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        d = rect.height() - 4
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.4)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        p.setBrush(QtGui.QColor("white"))
        x = rect.x() + 2 + a * (rect.width() - d - 4)
        p.drawEllipse(QtCore.QRectF(x, rect.y() + 2, d, d))


class TipTaxelPlot(pg.PlotWidget):
    """|force| of each fingertip taxel of one finger over time (one curve per taxel), scaled as
    in ``HandView``. Hovering highlights the nearest curve and names its Xela taxel id."""

    TITLE = "Fingertip taxels"

    def __init__(self, finger: str) -> None:
        super().__init__()
        ids = fingertip_taxel_ids()
        self.ids = ids[finger] if ids is not None else np.empty(0, dtype=int)
        n = len(self.ids)
        item = self.getPlotItem()
        item.showGrid(x=True, y=True, alpha=0.3)
        item.setLabel("bottom", "time", "s")
        item.setLabel("left", "|force|")
        item.setClipToView(True)
        item.setDownsampling(auto=True, mode="peak")
        item.enableAutoRange(axis="x", enable=False)  # follows the joint plot it is linked to
        self._pens = [pg.mkPen(pg.intColor(i, hues=max(n, 1)), width=1) for i in range(n)]
        self.curves = [item.plot(pen=pen, antialias=False) for pen in self._pens]
        # Recorded magnitudes of the take being played; the live ``curves`` are dashed meanwhile.
        self.demo_curves = [
            item.plot(pen=pg.mkPen(pen.color(), width=1.5), antialias=False) for pen in self._pens
        ]
        self._live_style = QtCore.Qt.SolidLine
        self._t = np.empty(0)
        self._mags = np.empty((0, n))
        self._status = ""
        self._hovered: int | None = None
        self.set_status("" if ids is not None else "taxel map unavailable")
        self.scene().sigMouseMoved.connect(self._on_hover)

    def set_status(self, text: str) -> None:
        """Shown after the title (e.g. why there is no data)."""
        self._status = text
        self._show_title()

    def set_data(self, t: np.ndarray, mags: np.ndarray) -> None:
        """``mags`` (N, 30): magnitude of each taxel of ``ids`` at times ``t``."""
        self._t, self._mags = t, mags
        for j, curve in enumerate(self.curves):
            curve.setData(t, mags[:, j])

    def clear_data(self, status: str) -> None:
        self.set_data(np.empty(0), np.empty((0, len(self.ids))))
        self.set_status(status)

    def set_playing(self, on: bool) -> None:
        """While playing: demonstration solid, measured taxels dashed."""
        self._live_style = QtCore.Qt.DashLine if on else QtCore.Qt.SolidLine
        for j, curve in enumerate(self.curves):
            curve.setPen(self._live_pen(j, 3 if j == self._hovered else 1))
        if not on:
            self.set_demo_data(np.empty(0), np.empty((0, len(self.ids))))
        self._show_title()

    def set_demo_data(self, t: np.ndarray, mags: np.ndarray) -> None:
        """``mags`` (N, 30): recorded magnitudes of the take being played at times ``t``."""
        for j, curve in enumerate(self.demo_curves):
            curve.setData(t, mags[:, j] if len(mags) else mags)

    def _live_pen(self, j: int, width: float) -> QtGui.QPen:
        return pg.mkPen(self._pens[j].color(), width=width, style=self._live_style)

    def _show_title(self, extra: str = "") -> None:
        if self._live_style != QtCore.Qt.SolidLine:
            status = "solid: demonstration, dashed: measured"
        else:
            status = self._status
        parts = [self.TITLE] + [p for p in (status, extra) if p]
        self.getPlotItem().setTitle(" - ".join(parts), size="9pt")

    def _highlight(self, j: int | None) -> None:
        if j == self._hovered:
            return
        for k in (self._hovered, j):
            if k is not None:
                self.curves[k].setPen(self._live_pen(k, 3 if k == j else 1))
        if j is not None:
            self.curves[j].setZValue(1)
        if self._hovered is not None:
            self.curves[self._hovered].setZValue(0)
        self._hovered = j

    def _on_hover(self, pos) -> None:
        vb = self.getPlotItem().getViewBox()
        if len(self._t) == 0 or not vb.sceneBoundingRect().contains(pos):
            self._highlight(None)
            self._show_title()
            return
        p = vb.mapSceneToView(pos)
        i = int(np.clip(np.searchsorted(self._t, p.x()), 0, len(self._t) - 1))
        j = int(np.argmin(np.abs(self._mags[i] - p.y())))
        self._highlight(j)
        self._show_title(f"taxel {int(self.ids[j])}: {self._mags[i, j]:.3f}")


class FingerPanel(QtWidgets.QWidget):
    """Hold switch, take name + Record, take picker + Play and a play bar above the live plot of
    one finger."""

    def __init__(self, finger: str, label: str) -> None:
        super().__init__()
        self.finger = finger
        self.label = label
        self.default_name = ""  # generated name shown in ``name_edit`` until the user edits it
        self.duration = 0.0  # of the selected take
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setToolTip("Name of the next take of this finger")
        self.record_btn = QtWidgets.QPushButton("Record")
        self.take_combo = QtWidgets.QComboBox()
        self.take_combo.setToolTip("Recorded takes of this finger, newest first")
        self.take_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.take_combo.setMinimumContentsLength(10)
        self.play_btn = QtWidgets.QPushButton("Play")
        for btn in (self.record_btn, self.play_btn):
            btn.setMinimumWidth(90)
        self.play_bar = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.play_bar.setRange(0, PLAY_BAR_STEPS)
        self.play_bar.setToolTip("Playback position: drag to choose where Play starts, or to seek")
        self.time_label = QtWidgets.QLabel()
        self.hold_switch = ToggleSwitch()
        self.hold_switch.setToolTip("Hold this finger at its current pose")

        header = QtWidgets.QHBoxLayout()
        header.addWidget(QtWidgets.QLabel(f"<b>{label}</b>"), 1)
        header.addWidget(QtWidgets.QLabel("Hold"))
        header.addWidget(self.hold_switch)
        bar_row = QtWidgets.QHBoxLayout()
        bar_row.addWidget(self.play_bar, 1)
        bar_row.addWidget(self.time_label)
        controls = QtWidgets.QGridLayout()
        controls.addLayout(header, 0, 0, 1, 2)
        controls.addWidget(self.name_edit, 1, 0)
        controls.addWidget(self.record_btn, 1, 1)
        controls.addWidget(self.take_combo, 2, 0)
        controls.addWidget(self.play_btn, 2, 1)
        controls.addLayout(bar_row, 3, 0, 1, 2)
        controls.setColumnStretch(0, 1)

        self.plot = pg.PlotWidget()
        item = self.plot.getPlotItem()
        item.showGrid(x=True, y=True, alpha=0.3)
        item.setLabel("bottom", "time", "s")
        item.setLabel("left", "position", "rad")
        self.legend = item.addLegend(offset=(5, 5))
        self.curves = [item.plot(pen=pg.mkPen(color, width=2)) for color in JOINT_COLORS]
        # What Play commands from the take; the measured ``curves`` are dashed meanwhile.
        self.demo_curves = [item.plot(pen=pg.mkPen(color, width=2)) for color in JOINT_COLORS]
        self.tip_plot = TipTaxelPlot(finger)
        self.tip_plot.setXLink(self.plot)
        plots = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        plots.addWidget(self.plot)
        plots.addWidget(self.tip_plot)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(plots, 1)

    def set_playing(self, on: bool) -> None:
        """While playing: demonstration solid, measured joints and taxels dashed."""
        style = QtCore.Qt.DashLine if on else QtCore.Qt.SolidLine
        for curve, color in zip(self.curves, JOINT_COLORS):
            curve.setPen(pg.mkPen(color, width=2, style=style))
        if not on:
            for curve in self.demo_curves:
                curve.setData([], [])
        self.plot.getPlotItem().setTitle(
            "solid: demonstration, dashed: measured" if on else None, size="9pt"
        )
        self.tip_plot.set_playing(on)

    def fill_takes(self, store: TakeStore, select: str | None = None) -> None:
        """Lists the takes of this finger, selecting ``select`` (default: keep the selection)."""
        keep = select or self.take_combo.currentData()
        self.take_combo.blockSignals(True)
        self.take_combo.clear()
        for path in store.list(self.finger):
            self.take_combo.addItem(os.path.splitext(os.path.basename(path))[0], path)
        index = self.take_combo.findData(keep) if keep else 0
        self.take_combo.setCurrentIndex(max(index, 0))
        self.take_combo.blockSignals(False)
        self.update_play_enabled()

    def update_play_enabled(self) -> None:
        self.play_btn.setEnabled(self.take_combo.count() > 0 and not self.hold_switch.isChecked())

    def bar_time(self) -> float:
        return self.play_bar.value() / PLAY_BAR_STEPS * self.duration

    def set_position(self, local: float) -> None:
        self.play_bar.blockSignals(True)
        self.play_bar.setValue(int(round(local / self.duration * PLAY_BAR_STEPS)) if self.duration else 0)
        self.play_bar.blockSignals(False)
        self.time_label.setText(f"{local:.2f} / {self.duration:.2f} s")


def sample_take(take: FingerTake, local: float) -> np.ndarray:
    return np.array([np.interp(local, take.t, take.q[:, j]) for j in range(take.q.shape[1])])


def take_tip_magnitudes(
    take: FingerTake, ids: np.ndarray, counts_per_unit: float
) -> np.ndarray | None:
    """(L, len(ids)) magnitudes of taxels ``ids`` at ``take.xela_t``, from the take's baseline
    (its first reading for takes without one); None if the take has no usable Xela readings."""
    if len(take.xela_t) == 0 or len(ids) == 0 or take.xela.shape[1] <= ids.max():
        return None
    baseline = take.xela_baseline if len(take.xela_baseline) > ids.max() else take.xela[0]
    return taxel_magnitudes(take.xela, baseline, ids, counts_per_unit)


@dataclass
class Playback:
    take: FingerTake
    cols: list[int]  # hand columns driven by the take
    start: float  # time.monotonic() when the ramp started
    from_q: np.ndarray  # finger joints at the start of the ramp
    offset: float  # take time reached at the end of the ramp
    to_q: np.ndarray  # finger joints at ``offset``
    local: float = 0.0  # take time last commanded
    # (ROS time, commanded hand pose) of every command step, plotted against ``leap_state``.
    history: deque[tuple[float, np.ndarray]] = field(
        default_factory=lambda: deque(maxlen=HISTORY_LEN)
    )
    # (ROS time, take time commanded) of every command step, to plot the take's taxels.
    local_history: deque[tuple[float, float]] = field(
        default_factory=lambda: deque(maxlen=HISTORY_LEN)
    )
    tip_mags: np.ndarray | None = None  # (L, 30) recorded fingertip magnitudes (None: no Xela)


class CreateTab(QtWidgets.QWidget):
    """One live plot per finger with Record / Play buttons, plus the camera.

    A finger's Record saves a take of that finger under the name in its text box. Play sends the
    take selected in the finger's dropdown to the hand, starting from the play bar position. Hold
    keeps a finger at its pose.

    While any finger is held or playing, the whole hand is commanded on ``cmd_topic``; the other
    ("free") fingers mimic leaphand_node's compliant mode so they can still be posed by hand.
    """

    takes_changed = QtCore.pyqtSignal()

    def __init__(self, node: LeapStateListener, store: TakeStore, settings: HoldSettings) -> None:
        super().__init__()
        self.node = node
        self.store = store
        self.settings = settings
        self._frame_seq = 0
        self._sim_seq = 0
        self._xela_seq = 0
        # Live fingertip plots: (stamp, readings of ``_tip_ids``) over the last LIVE_WINDOW_S.
        tip_ids = fingertip_taxel_ids()
        self._tip_ids = (
            np.concatenate([tip_ids[f] for f, _ in FINGERS]) if tip_ids else np.empty(0, int)
        )
        self._tip_seq = 0
        self._tip_history: deque[tuple[float, np.ndarray]] = deque()
        self._tip_baseline: np.ndarray | None = None  # baseline the plots were drawn with
        self._tip_waiting = False  # plots show the waiting text
        self._take_name = ""
        self._rec_fingers: tuple[str, ...] = ()
        self._rec_btn: QtWidgets.QPushButton | None = None
        self._free: np.ndarray | None = None  # goal of the fingers neither held nor playing
        self._last_cmd: np.ndarray | None = None
        self._playing: dict[str, Playback] = {}
        self._held: dict[str, np.ndarray] = {}  # finger -> joint positions it is held at
        self._stiff_sent: tuple[str, ...] = ()  # joints last given the hand's stiff gains

        grid = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        self.panels: dict[str, FingerPanel] = {}
        for n, (finger, label) in enumerate(FINGERS):
            panel = FingerPanel(finger, label)
            self.panels[finger] = panel
            grid_layout.addWidget(panel, n // 2, n % 2)
            panel.record_btn.clicked.connect(
                lambda _, f=finger, b=panel.record_btn: self.toggle_recording((f,), b)
            )
            panel.play_btn.clicked.connect(lambda _, f=finger: self.toggle_play(f))
            panel.take_combo.currentIndexChanged.connect(lambda _, f=finger: self._on_take_selected(f))
            panel.play_bar.valueChanged.connect(lambda _, f=finger: self._on_seek(f))
            panel.hold_switch.toggled.connect(lambda on, f=finger: self.set_hold(f, on))
            self._new_default_name(panel)
            panel.fill_takes(store)
            self._on_take_selected(finger)
        self._legend_names: list[str] = []

        self.camera = CameraView(node.image_topic)
        self.hand = HandView(node.sim_topic, node.xela_topic, node.counts_per_unit)
        # The recording of the take being played, next to the live view.
        self.play_title = QtWidgets.QLabel()
        self.play_camera = CameraView("")
        self.play_hand = HandView(
            "", "", node.counts_per_unit,
            waiting="Press Play to see the take's taxels",
            no_xela="Press Play to see the take's Xela readings",
        )
        self._play_video = TakeVideo()
        self._shown_play: str | None = None  # finger whose take the playback column shows
        self._clear_playback_view()
        sides = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        sides.addWidget(side_column(QtWidgets.QLabel("<b>Live</b>"), self.camera, self.hand))
        sides.addWidget(side_column(self.play_title, self.play_camera, self.play_hand))
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(grid)
        splitter.addWidget(sides)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addSpacing(40)
        layout.addWidget(splitter, 1)

        self._cmd_timer = QtCore.QTimer(self)
        self._cmd_timer.timeout.connect(self._command_step)

    def _record_buttons(self) -> list[QtWidgets.QPushButton]:
        return [p.record_btn for p in self.panels.values()]

    def _new_default_name(self, panel: FingerPanel) -> str:
        panel.default_name = self.store.new_take_name(panel.label.lower())
        panel.name_edit.setText(panel.default_name)
        return panel.default_name

    def _on_take_selected(self, finger: str) -> None:
        panel = self.panels[finger]
        path = panel.take_combo.currentData()
        panel.duration = 0.0
        if path is not None:
            try:
                panel.duration = self.store.load(path).duration
            except Exception as e:
                self.node.get_logger().warn(f"Could not load {path}: {e}")
        panel.set_position(0.0)

    def _on_seek(self, finger: str) -> None:
        """Play bar moved by the user: show the time and, if playing, ramp to it and continue."""
        panel = self.panels[finger]
        local = panel.bar_time()
        panel.time_label.setText(f"{local:.2f} / {panel.duration:.2f} s")
        p = self._playing.get(finger)
        if p is None:
            return
        if self._last_cmd is not None:
            p.from_q = self._last_cmd[p.cols].copy()
        p.start = time.monotonic()
        p.offset = local
        p.to_q = sample_take(p.take, local)

    # ---- recording ----------------------------------------------------------------------

    def toggle_recording(self, fingers: tuple[str, ...], button: QtWidgets.QPushButton) -> None:
        if self.node.recording:
            self.stop_recording()
            return
        if len(fingers) == 1:
            panel = self.panels[fingers[0]]
            text = panel.name_edit.text().strip()
            if not text or text == panel.default_name:
                text = self._new_default_name(panel)
            self._take_name = self.store.unique_take_name(safe_name(text))
            panel.name_edit.setText(self._take_name)
        else:
            self._take_name = self.store.new_take_name()
        self._rec_fingers = fingers
        self._rec_btn = button
        self.node.start_recording(self.store.video_path(self._take_name) if self.node.image_topic else "")
        for btn in self._record_buttons():
            btn.setEnabled(btn is button)
        for panel in self.panels.values():
            panel.name_edit.setEnabled(False)
        button.setText("Stop")
        button.setStyleSheet(STOP_STYLE)

    def stop_recording(self) -> None:
        rec = self.node.stop_recording()
        for btn in self._record_buttons():
            btn.setEnabled(True)
            btn.setStyleSheet("")
        for panel in self.panels.values():
            panel.record_btn.setText("Record")
            panel.name_edit.setEnabled(True)
        if len(rec.t) < 2:
            if rec.video:
                os.remove(rec.video)
            QtWidgets.QMessageBox.warning(
                self, "Record", "Fewer than 2 leap_state messages were received; nothing saved."
            )
            return
        if len(rec.sim_t) == 0:
            self.node.get_logger().warn(
                f"No '{self.node.sim_topic}' messages during the take; saving it without sim joints"
            )
        if self.node.xela_topic and len(rec.xela_t) == 0:
            self.node.get_logger().warn(
                f"No '{self.node.xela_topic}' messages during the take; saving it without taxels"
            )
        baseline = self.hand.baseline
        if baseline is None or (len(rec.xela) and len(baseline) > rec.xela.shape[1]):
            baseline = rec.xela[0] if len(rec.xela) else np.empty((0, 3))
        hand_names = self.node.joint_names
        for finger in self._rec_fingers:
            idx = finger_indices(hand_names, finger)
            path = self.store.take_path(finger, self._take_name)
            FingerTake(
                finger=finger,
                path=path,
                t=rec.t,
                q=rec.q[:, idx],
                joint_names=[hand_names[i] for i in idx],
                hand_q=rec.q,
                hand_joint_names=hand_names,
                video=rec.video,
                video_t=rec.video_t,
                sim_t=rec.sim_t,
                sim_hand_q=rec.sim_q,
                sim_hand_joint_names=rec.sim_joint_names,
                xela_t=rec.xela_t,
                xela=rec.xela,
                xela_baseline=np.asarray(baseline, dtype=np.float32),
            ).save()
            panel = self.panels[finger]
            self._new_default_name(panel)
            if finger not in self._playing:
                panel.fill_takes(self.store, select=path)
                self._on_take_selected(finger)
        self.takes_changed.emit()

    # ---- playback -----------------------------------------------------------------------

    def toggle_play(self, finger: str) -> None:
        if finger in self._playing:
            self._stop_play(finger)
            return
        panel = self.panels[finger]
        path = panel.take_combo.currentData()
        if path is None:
            return
        q = self.node.latest()
        if q is None:
            QtWidgets.QMessageBox.warning(self, "Play", "No leap_state received yet.")
            return
        try:
            take = self.store.load(path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Play", f"Could not load {path}:\n{e}")
            return
        panel.duration = take.duration
        offset = panel.bar_time()
        if offset >= take.duration:
            offset = 0.0
        self._start_commanding(q)
        cols = take_columns(self.node.joint_names, take)
        self._playing[finger] = Playback(
            take=take,
            cols=cols,
            start=time.monotonic(),
            from_q=self._current_goal(q)[cols],
            offset=offset,
            to_q=sample_take(take, offset),
            tip_mags=take_tip_magnitudes(take, panel.tip_plot.ids, self.node.counts_per_unit),
        )
        panel.take_combo.setEnabled(False)
        panel.play_btn.setText("Stop")
        panel.play_btn.setStyleSheet(STOP_STYLE)
        panel.set_playing(True)
        self._update_stiff_joints()
        self._shown_play = finger
        self.play_title.setText(f"<b>Playback</b>: {panel.label} - {take.name}")

    def _stop_play(self, finger: str, rewind: bool = False) -> None:
        """Stops ``finger`` where it was last commanded; it then follows the hand again."""
        playback = self._playing.pop(finger)
        if self._last_cmd is not None and self._free is not None:
            self._free[playback.cols] = self._last_cmd[playback.cols]
        panel = self.panels[finger]
        panel.take_combo.setEnabled(True)
        panel.play_btn.setText("Play")
        panel.play_btn.setStyleSheet("")
        panel.set_playing(False)
        if rewind:
            panel.set_position(0.0)
        self._stop_commanding_if_idle()
        self._update_stiff_joints()
        if finger == self._shown_play:
            self._shown_play = next(iter(self._playing), None)
            if self._shown_play is None:
                self._clear_playback_view()
            else:
                shown = self._playing[self._shown_play]
                self.play_title.setText(
                    f"<b>Playback</b>: {FINGER_LABEL[self._shown_play]} - {shown.take.name}"
                )

    def _clear_playback_view(self) -> None:
        self._play_video.release()
        self.play_title.setText("<b>Playback</b>")
        self.play_camera.set_message("Press Play to see the take's camera recording")
        self.play_hand.clear()

    def close_video(self) -> None:
        self._play_video.release()

    def stop_all_playback(self) -> None:
        for finger in list(self._playing):
            self._stop_play(finger)

    def forget_take(self, path: str) -> None:
        """Stops playing the take at ``path`` (about to be deleted)."""
        for finger, playback in list(self._playing.items()):
            if playback.take.path == path:
                self._stop_play(finger, rewind=True)

    def reload_takes(self) -> None:
        """Re-lists every finger's takes and default names, e.g. after the folder changed."""
        for finger, panel in self.panels.items():
            if panel.name_edit.text() == panel.default_name:
                self._new_default_name(panel)
            panel.fill_takes(self.store)
            self._on_take_selected(finger)

    # ---- hold ---------------------------------------------------------------------------

    def set_hold(self, finger: str, on: bool) -> None:
        panel = self.panels[finger]
        cols = finger_indices(self.node.joint_names, finger)
        if not on:
            held = self._held.pop(finger, None)
            if held is not None and self._free is not None:
                self._free[cols] = held
            panel.update_play_enabled()
            self._stop_commanding_if_idle()
            self._update_stiff_joints()
            return
        q = self.node.latest()
        if q is None:
            panel.hold_switch.setChecked(False)
            QtWidgets.QMessageBox.warning(self, "Hold", "No leap_state received yet.")
            return
        self._start_commanding(q)
        self._held[finger] = self._current_goal(q)[cols].copy()
        if finger in self._playing:
            self._stop_play(finger)
        panel.update_play_enabled()
        self._update_stiff_joints()

    def _update_stiff_joints(self) -> None:
        """Playing and held fingers use the hand's stiff (playback) gains, the others stay
        compliant."""
        names = self.node.joint_names
        fingers = set(self._playing) | set(self._held)
        joints = tuple(
            names[i] for finger, _ in FINGERS if finger in fingers
            for i in finger_indices(names, finger)
        )
        if joints != self._stiff_sent and self.node.set_stiff_joints(list(joints)):
            self._stiff_sent = joints

    def release_stiff_joints(self) -> None:
        if self._stiff_sent and self.node.set_stiff_joints([]):
            self._stiff_sent = ()

    # ---- commanding the hand ------------------------------------------------------------

    def _current_goal(self, measured: np.ndarray) -> np.ndarray:
        """Last commanded pose while the hand is being commanded, else the measured one."""
        return self._last_cmd if self._last_cmd is not None else measured

    def _start_commanding(self, measured: np.ndarray) -> None:
        if self._cmd_timer.isActive():
            return
        self._free = measured.copy()
        self._last_cmd = None
        self._cmd_timer.start(self.settings.interval_ms)

    def apply_settings(self) -> None:
        """Picks up a changed command rate; the other settings are read every step."""
        if self._cmd_timer.isActive():
            self._cmd_timer.setInterval(self.settings.interval_ms)

    def _stop_commanding_if_idle(self) -> None:
        if not self._playing and not self._held:
            self._cmd_timer.stop()
            self._last_cmd = None
            self._free = None

    def _command_step(self) -> None:
        now = time.monotonic()
        measured = self.node.latest()
        if measured is not None:
            pushed = np.abs(measured - self._free) > self.settings.deadband
            self._free[pushed] = measured[pushed]
        q = self._free.copy()
        names = self.node.joint_names
        for finger, held in self._held.items():
            q[finger_indices(names, finger)] = held
        finished = []
        ramp = self.settings.ramp_s
        for finger, p in self._playing.items():
            elapsed = now - p.start
            if elapsed < ramp:
                a = elapsed / ramp
                q[p.cols] = (1.0 - a) * p.from_q + a * p.to_q
                local = p.offset
            else:
                local = min(p.offset + elapsed - ramp, p.take.duration)
                q[p.cols] = sample_take(p.take, local)
                if local >= p.take.duration:
                    finished.append(finger)
            p.local = local
            self.panels[finger].set_position(local)
        self.node.send_command(q)
        self._last_cmd = q
        stamp = self.node.get_clock().now().nanoseconds * 1e-9
        for p in self._playing.values():
            p.history.append((stamp, q.copy()))
            p.local_history.append((stamp, p.local))
        for finger in finished:
            self._stop_play(finger, rewind=True)

    # ---- live view ----------------------------------------------------------------------

    def _update_legends(self, names: list[str]) -> None:
        if names == self._legend_names:
            return
        self._legend_names = names
        for finger, panel in self.panels.items():
            panel.legend.clear()
            for curve, i in zip(panel.curves, finger_indices(names, finger)):
                panel.legend.addItem(curve, names[i])

    def _refresh_tip_plots(self) -> None:
        """Fingertip taxel magnitudes of the last LIVE_WINDOW_S, from the live view's baseline."""
        if len(self._tip_ids) == 0:
            return
        self._tip_seq, new = self.node.xela_since(self._tip_seq)
        for stamp, readings in new:
            if len(readings) > self._tip_ids.max():
                self._tip_history.append((stamp, readings[self._tip_ids].astype(np.float32)))
        baseline = self.hand.baseline
        if not self._tip_history or baseline is None:
            if not self._tip_waiting:
                self._tip_waiting = True
                self._tip_baseline = None
                status = (
                    f"waiting for {self.node.xela_topic}" if self.node.xela_topic else "no xela_topic"
                )
                for panel in self.panels.values():
                    panel.tip_plot.clear_data(status)
            return
        self._tip_waiting = False
        if not new and baseline is self._tip_baseline:
            return
        latest = self._tip_history[-1][0]
        while self._tip_history[0][0] < latest - LIVE_WINDOW_S:
            self._tip_history.popleft()
        if self._tip_baseline is None:
            for panel in self.panels.values():
                panel.tip_plot.set_status(f"{self.node.xela_topic} live")
        self._tip_baseline = baseline
        t = np.array([s for s, _ in self._tip_history]) - latest
        readings = np.stack([r for _, r in self._tip_history])  # (N, 4 * 30, 3)
        mags = np.linalg.norm(
            (readings - baseline[self._tip_ids]) / self.node.counts_per_unit, axis=-1
        )
        per_finger = len(self._tip_ids) // len(FINGERS)
        for k, (finger, _) in enumerate(FINGERS):
            self.panels[finger].tip_plot.set_data(t, mags[:, k * per_finger: (k + 1) * per_finger])

    def _refresh_tip_demo(self) -> None:
        """Recorded fingertip magnitudes of the playing takes at the take time each command step
        sent, on the time axis of the live fingertip plots."""
        now = (
            self._tip_history[-1][0]
            if self._tip_history
            else self.node.get_clock().now().nanoseconds * 1e-9
        )
        for finger, p in self._playing.items():
            if p.tip_mags is None or not p.local_history:
                continue
            stamps = np.array([s for s, _ in p.local_history])
            local = np.array([v for _, v in p.local_history])
            shown = stamps >= now - LIVE_WINDOW_S
            k = np.clip(np.searchsorted(p.take.xela_t, local[shown], side="right") - 1, 0, None)
            self.panels[finger].tip_plot.set_demo_data(stamps[shown] - now, p.tip_mags[k])

    def refresh(self) -> None:
        if self.node.recording and self._rec_btn is not None:
            duration, frames = self.node.recorded_count()
            self._rec_btn.setText(f"Stop  ({duration:.1f} s, {frames} frames)")

        seq, frame = self.node.latest_frame()
        if frame is not None and seq != self._frame_seq:
            self._frame_seq = seq
            self.camera.set_frame(frame)

        sim_seq, sim_names, sim_q = self.node.latest_sim()
        if sim_q is not None and sim_seq != self._sim_seq:
            self._sim_seq = sim_seq
            self.hand.set_joints(sim_names, sim_q)

        xela_seq, readings = self.node.latest_xela()
        if readings is not None and xela_seq != self._xela_seq:
            self._xela_seq = xela_seq
            self.hand.set_readings(readings)
        self._refresh_tip_plots()
        self._refresh_tip_demo()

        shown = self._playing.get(self._shown_play) if self._shown_play else None
        if shown is not None:
            show_take_at(shown.take, shown.local, self.play_camera, self.play_hand, self._play_video)

        names = self.node.joint_names
        self._update_legends(names)
        t, q = self.node.history()
        if len(t) == 0:
            return
        keep = t >= t[-1] - LIVE_WINDOW_S
        rel = t[keep] - t[-1]
        for finger, panel in self.panels.items():
            for curve, i in zip(panel.curves, finger_indices(names, finger)):
                curve.setData(rel, q[keep, i])
        for finger, p in self._playing.items():
            if not p.history:
                continue
            cmd_t = np.array([s for s, _ in p.history])
            cmd_q = np.stack([c for _, c in p.history])
            shown = cmd_t >= t[-1] - LIVE_WINDOW_S
            for curve, i in zip(self.panels[finger].demo_curves, finger_indices(names, finger)):
                curve.setData(cmd_t[shown] - t[-1], cmd_q[shown, i])


def color_swatch(color: QtGui.QColor) -> QtGui.QIcon:
    swatch = QtGui.QPixmap(12, 12)
    swatch.fill(color)
    return QtGui.QIcon(swatch)


class SpanBookmarkSlider(BookmarkSlider):
    """``BookmarkSlider`` that also shades spans (duration events) over its groove."""

    SPAN_ALPHA = 90

    def __init__(self) -> None:
        super().__init__()
        self._spans: list[tuple[int, int, QtGui.QColor, str]] = []  # (from, to, colour, tooltip)

    def set_spans(self, spans: list[tuple[int, int, QtGui.QColor, str]]) -> None:
        self._spans = spans
        self.update()

    def paintEvent(self, ev) -> None:
        super().paintEvent(ev)
        if not self._spans:
            return
        painter = QtGui.QPainter(self)
        h = self.height()
        for start, end, color, _ in self._spans:
            x0, x1 = self._mark_x(start), self._mark_x(end)
            fill = QtGui.QColor(color)
            fill.setAlpha(self.SPAN_ALPHA)
            painter.fillRect(QtCore.QRect(x0, 4, max(x1 - x0, 1), h - 8), fill)
        painter.end()

    def event(self, ev) -> bool:
        if ev.type() == QtCore.QEvent.ToolTip:
            x = ev.pos().x()
            hits = [tip for value, _, tip in self._marks if abs(self._mark_x(value) - x) <= 4]
            hits += [
                tip for start, end, _, tip in self._spans
                if self._mark_x(start) - 4 <= x <= self._mark_x(end) + 4
            ]
            if hits:
                QtWidgets.QToolTip.showText(ev.globalPos(), "\n".join(dict.fromkeys(hits)), self)
            else:
                QtWidgets.QToolTip.hideText()
                ev.ignore()
            return True
        return super().event(ev)


class EditFingerPanel(QtWidgets.QWidget):
    """Take picker, play bar with event bookmarks, event picker + Add event above the plot of
    one finger's take, with the take's events listed next to it (click to seek).

    Events with ``"length": "duration"`` in ``events.json`` take two clicks: the first marks
    where they start, the second where they end; the span is shaded on the play bar and plot.
    """

    seeked = QtCore.pyqtSignal(str)  # finger
    delete_requested = QtCore.pyqtSignal(str)  # path of the take, confirmed by the user

    CURSOR_PEN = pg.mkPen("#ffd600", width=1.5)
    REGION_ALPHA = 50
    PENDING_ALPHA = 30

    def __init__(
        self,
        finger: str,
        label: str,
        store: TakeStore,
        event_defs: dict[str, dict],
        counts_per_unit: float,
    ) -> None:
        super().__init__()
        self.finger = finger
        self.store = store
        self.counts_per_unit = counts_per_unit
        self.event_defs = event_defs
        self.take: FingerTake | None = None
        self.now = 0.0
        self._event_items: list[pg.GraphicsObject] = []  # event lines / regions on the plot
        self._marks: list[tuple[int, QtGui.QColor, str]] = []  # saved events on the play bar
        self._spans: list[tuple[int, int, QtGui.QColor, str]] = []
        self._pending: TakeEvent | None = None  # duration event whose end is not marked yet
        self._pending_items: list[pg.GraphicsObject] = []

        self.take_combo = QtWidgets.QComboBox()
        self.take_combo.setToolTip("Recorded takes of this finger, newest first")
        self.take_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.take_combo.setMinimumContentsLength(10)
        self.delete_take_btn = QtWidgets.QPushButton("Delete take")
        self.delete_take_btn.setMinimumWidth(90)
        self.delete_take_btn.setToolTip("Delete the selected take from disk")
        self.event_combo = QtWidgets.QComboBox()
        for name, info in event_defs.items():
            text = f"{name}  (duration)" if self._is_duration(name) else name
            self.event_combo.addItem(color_swatch(self._color(name)), text, name)
            self.event_combo.setItemData(
                self.event_combo.count() - 1,
                f"[{info.get('type', '')}] {info.get('description', '')}",
                QtCore.Qt.ToolTipRole,
            )
        self.add_btn = QtWidgets.QPushButton("Add event")
        self.add_btn.setMinimumWidth(90)
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setToolTip("Discard the duration event being marked")
        self.cancel_btn.hide()
        event_buttons = QtWidgets.QHBoxLayout()
        event_buttons.addWidget(self.add_btn)
        event_buttons.addWidget(self.cancel_btn)
        self.slider = SpanBookmarkSlider()
        self.slider.setToolTip("Position in the take: drag to scrub")
        self.time_label = QtWidgets.QLabel()

        bar_row = QtWidgets.QHBoxLayout()
        bar_row.addWidget(self.slider, 1)
        bar_row.addWidget(self.time_label)
        controls = QtWidgets.QGridLayout()
        controls.addWidget(QtWidgets.QLabel(f"<b>{label}</b>"), 0, 0, 1, 2)
        controls.addWidget(self.take_combo, 1, 0)
        controls.addWidget(self.delete_take_btn, 1, 1)
        controls.addWidget(self.event_combo, 2, 0)
        controls.addLayout(event_buttons, 2, 1)
        controls.addLayout(bar_row, 3, 0, 1, 2)
        controls.setColumnStretch(0, 1)

        self.plot = pg.PlotWidget()
        item = self.plot.getPlotItem()
        item.showGrid(x=True, y=True, alpha=0.3)
        item.setLabel("bottom", "time", "s")
        item.setLabel("left", "position", "rad")
        self.legend = item.addLegend(offset=(5, 5))
        self.curves = [item.plot(pen=pg.mkPen(color, width=2)) for color in JOINT_COLORS]
        self.cursor = pg.InfiniteLine(pos=0.0, angle=90, movable=True, pen=self.CURSOR_PEN)
        self.cursor.setToolTip("Drag to scrub")
        item.addItem(self.cursor, ignoreBounds=True)
        self.tip_plot = TipTaxelPlot(finger)
        self.tip_plot.setXLink(self.plot)
        self.tip_cursor = pg.InfiniteLine(pos=0.0, angle=90, movable=True, pen=self.CURSOR_PEN)
        self.tip_cursor.setToolTip("Drag to scrub")
        self.tip_plot.getPlotItem().addItem(self.tip_cursor, ignoreBounds=True)
        plots = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        plots.addWidget(self.plot)
        plots.addWidget(self.tip_plot)

        self.event_list = QtWidgets.QListWidget()
        self.event_list.setFixedWidth(180)
        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.delete_btn = QtWidgets.QPushButton("Delete")
        list_buttons = QtWidgets.QHBoxLayout()
        list_buttons.addWidget(self.edit_btn)
        list_buttons.addWidget(self.delete_btn)
        events_box = QtWidgets.QVBoxLayout()
        events_box.addWidget(QtWidgets.QLabel("Events"))
        events_box.addWidget(self.event_list, 1)
        events_box.addLayout(list_buttons)
        body = QtWidgets.QHBoxLayout()
        body.addWidget(plots, 1)
        body.addLayout(events_box)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addLayout(body, 1)

        self.take_combo.currentIndexChanged.connect(lambda _: self._load_selected())
        self.delete_take_btn.clicked.connect(self._confirm_delete_take)
        self.slider.valueChanged.connect(lambda v: self.seek(v / SLIDER_STEPS_PER_SEC))
        self.cursor.sigPositionChanged.connect(lambda line: self.seek(line.value()))
        self.tip_cursor.sigPositionChanged.connect(lambda line: self.seek(line.value()))
        self.add_btn.clicked.connect(self.add_event)
        self.cancel_btn.clicked.connect(self.cancel_pending)
        self.event_combo.currentIndexChanged.connect(lambda _: self._update_buttons())
        self.edit_btn.clicked.connect(self.edit_selected_event)
        self.delete_btn.clicked.connect(self.delete_selected_event)
        self.event_list.itemClicked.connect(self._on_event_item)
        self.event_list.itemActivated.connect(self._on_event_item)
        self.event_list.itemSelectionChanged.connect(self._update_buttons)
        self._load_selected()

    def _color(self, name: str, alpha: int = 255) -> QtGui.QColor:
        color = QtGui.QColor(self.event_defs.get(name, {}).get("color", UNKNOWN_EVENT_COLOR))
        color.setAlpha(alpha)
        return color

    def _is_duration(self, name: str) -> bool:
        return self.event_defs.get(name, {}).get("length") == "duration"

    # ---- takes --------------------------------------------------------------------------

    def fill_takes(self) -> None:
        """Lists the takes of this finger, keeping the selection if it still exists."""
        keep = self.take_combo.currentData()
        self.take_combo.blockSignals(True)
        self.take_combo.clear()
        for path in self.store.list(self.finger):
            self.take_combo.addItem(os.path.splitext(os.path.basename(path))[0], path)
        index = self.take_combo.findData(keep) if keep else 0
        self.take_combo.setCurrentIndex(max(index, 0))
        self.take_combo.blockSignals(False)
        self._load_selected()

    def _confirm_delete_take(self) -> None:
        path = self.take_combo.currentData()
        if path is None:
            return
        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Warning)
        box.setWindowTitle("Delete take")
        box.setText(f"Delete the take '{self.take_combo.currentText()}'?")
        box.setInformativeText(
            "Its file, events and (if no other finger uses it) its camera recording are removed "
            "from disk. This cannot be undone."
        )
        cancel = box.addButton(QtWidgets.QMessageBox.Cancel)
        confirm = box.addButton("Confirm", QtWidgets.QMessageBox.DestructiveRole)
        box.setDefaultButton(cancel)
        box.exec_()
        if box.clickedButton() is confirm:
            self.delete_requested.emit(path)

    def _load_selected(self) -> None:
        path = self.take_combo.currentData()
        previous = self.take.path if self.take is not None else None
        if path != previous:
            self._pending = None
        self.take = None
        if path is not None:
            try:
                self.take = self.store.load(path)
            except Exception as e:
                self.time_label.setText(f"<span style='color:#d32f2f'>load failed: {e}</span>")
        if self.take is None or self.take.path != previous:
            self.now = 0.0
        take = self.take
        duration = take.duration if take is not None else 0.0
        self.slider.blockSignals(True)
        self.slider.setRange(0, int(round(duration * SLIDER_STEPS_PER_SEC)))
        self.slider.blockSignals(False)
        self.legend.clear()
        for j, curve in enumerate(self.curves):
            if take is not None and j < take.q.shape[1]:
                curve.setData(take.t, take.q[:, j])
                self.legend.addItem(curve, take.joint_names[j])
            else:
                curve.setData([], [])
        self._show_tip_taxels()
        self.cursor.setVisible(take is not None)
        self.tip_cursor.setVisible(take is not None)
        self.delete_take_btn.setEnabled(path is not None)
        for w in (self.slider, self.event_list):
            w.setEnabled(take is not None)
        if take is None:
            self._pending = None
        self._refresh_events()
        if take is not None:
            self.seek(self.now)
        elif path is None:
            self.time_label.setText("no takes")

    def _show_tip_taxels(self) -> None:
        """Fingertip taxel magnitudes over the whole take, from the take's baseline."""
        take = self.take
        if take is None:
            self.tip_plot.clear_data("")
            return
        mags = take_tip_magnitudes(take, self.tip_plot.ids, self.counts_per_unit)
        if mags is None:
            self.tip_plot.clear_data(f"no Xela readings in {take.name}")
            return
        self.tip_plot.set_data(take.xela_t, mags)
        self.tip_plot.set_status(take.name)

    # ---- position -----------------------------------------------------------------------

    def seek(self, t: float) -> None:
        if self.take is None:
            return
        self.now = float(np.clip(t, 0.0, self.take.duration))
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(self.now * SLIDER_STEPS_PER_SEC)))
        self.slider.blockSignals(False)
        for cursor in (self.cursor, self.tip_cursor):
            cursor.blockSignals(True)
            cursor.setValue(self.now)
            cursor.blockSignals(False)
        self.time_label.setText(f"{self.now:.2f} / {self.take.duration:.2f} s")
        if self._pending is not None:
            self._show_pending()
        self._update_buttons()
        self.seeked.emit(self.finger)

    # ---- events -------------------------------------------------------------------------

    @staticmethod
    def _slider_value(t: float) -> int:
        return int(round(t * SLIDER_STEPS_PER_SEC))

    def _event_line(self, t: float, color: QtGui.QColor) -> pg.InfiniteLine:
        return pg.InfiniteLine(
            pos=t, angle=90, movable=False,
            pen=pg.mkPen(color, width=1.5, style=QtCore.Qt.DashLine),
        )

    def _event_region(self, start: float, end: float, name: str, alpha: int) -> pg.LinearRegionItem:
        region = pg.LinearRegionItem(
            values=(start, end), movable=False, brush=pg.mkBrush(self._color(name, alpha)),
        )
        for line in region.lines:
            line.setPen(pg.mkPen(self._color(name), width=1.5, style=QtCore.Qt.DashLine))
        region.setZValue(-10)
        return region

    def _refresh_events(self) -> None:
        plot = self.plot.getPlotItem()
        for item in self._event_items:
            plot.removeItem(item)
        self._event_items = []
        self.event_list.clear()
        self._marks, self._spans = [], []
        events = self.take.events if self.take is not None else []
        for i, event in enumerate(events, start=1):
            color = self._color(event.name)
            tip = f"{event.name} @ {event.span_text()}"
            item = QtWidgets.QListWidgetItem(color_swatch(color), f"{i}. {tip}")
            item.setData(QtCore.Qt.UserRole, i - 1)
            self.event_list.addItem(item)
            self._marks.append((self._slider_value(event.t), color, tip))
            if event.end is None:
                plot_item = self._event_line(event.t, color)
            else:
                self._marks.append((self._slider_value(event.end), color, tip))
                self._spans.append(
                    (self._slider_value(event.t), self._slider_value(event.end), color, tip)
                )
                plot_item = self._event_region(event.t, event.end, event.name, self.REGION_ALPHA)
            plot.addItem(plot_item, ignoreBounds=True)
            self._event_items.append(plot_item)
        self._show_pending()
        self._update_buttons()

    def _show_pending(self) -> None:
        """Play bar / plot with the saved events plus the duration event being marked, shaded
        from its start to the current position."""
        plot = self.plot.getPlotItem()
        for item in self._pending_items:
            plot.removeItem(item)
        self._pending_items = []
        marks, spans = list(self._marks), list(self._spans)
        p = self._pending
        if p is not None:
            color = self._color(p.name)
            start, end = sorted((p.t, self.now))
            tip = f"{p.name} from {p.t:.2f} s (end not marked yet)"
            marks.append((self._slider_value(p.t), color, tip))
            spans.append((self._slider_value(start), self._slider_value(end), color, tip))
            self._pending_items = [
                self._event_region(start, end, p.name, self.PENDING_ALPHA),
                self._event_line(p.t, color),
            ]
            for item in self._pending_items:
                plot.addItem(item, ignoreBounds=True)
        self.slider.set_marks(marks)
        self.slider.set_spans(spans)

    def _selected_event(self) -> TakeEvent | None:
        item = self.event_list.currentItem()
        if self.take is None or item is None or not item.isSelected():
            return None
        return self.take.events[item.data(QtCore.Qt.UserRole)]

    def _update_buttons(self) -> None:
        selected = self._selected_event() is not None
        self.edit_btn.setEnabled(selected and bool(self.event_defs))
        self.delete_btn.setEnabled(selected)
        p = self._pending
        self.cancel_btn.setVisible(p is not None)
        self.event_combo.setEnabled(self.take is not None and p is None)
        if self.take is None or not self.event_defs:
            self.add_btn.setText("Add event")
            self.add_btn.setEnabled(False)
            return
        if p is not None:
            self.add_btn.setText("End event")
            self.add_btn.setEnabled(True)
            self.add_btn.setToolTip(
                f"Mark the end of '{p.name}' (started at {p.t:.2f} s) at the current time"
            )
            return
        duration = self._is_duration(self.event_combo.currentData())
        self.add_btn.setText("Start event" if duration else "Add event")
        existing = self.take.event_at(self.now)
        self.add_btn.setEnabled(existing is None)
        self.add_btn.setToolTip(
            f"'{existing.name}' already starts at this time" if existing is not None
            else "Mark where the selected event starts; click again where it ends" if duration
            else f"Store the selected event at the current time in {self.take.name}.npz"
        )

    def _on_event_item(self, item: QtWidgets.QListWidgetItem) -> None:
        if self.take is not None:
            self.seek(self.take.events[item.data(QtCore.Qt.UserRole)].t)

    def _save_events(self, events: list[TakeEvent], title: str) -> bool:
        old = self.take.events
        self.take.events = events
        try:
            self.take.save()
        except Exception as e:
            self.take.events = old
            QtWidgets.QMessageBox.warning(self, title, f"Could not save {self.take.path}:\n{e}")
            return False
        self._refresh_events()
        return True

    def add_event(self) -> None:
        """Adds an instant event at the play bar, or starts / ends a duration event there."""
        if self.take is None:
            return
        if self._pending is not None:
            self._end_pending()
            return
        name = self.event_combo.currentData()
        if name is None:
            return
        existing = self.take.event_at(self.now)
        if existing is not None:
            QtWidgets.QMessageBox.information(
                self, "Add event", f"There is already a '{existing.name}' event at {existing.t:.3f} s"
            )
            return
        event = TakeEvent(
            t=self.now, name=name, type=self.event_defs[name].get("type", ""), added=time.time()
        )
        if self._is_duration(name):
            self._pending = event
            self._show_pending()
            self._update_buttons()
        elif self._save_events(self.take.events + [event], "Add event"):
            self.event_list.scrollToBottom()

    def _end_pending(self) -> None:
        p = self._pending
        start, end = sorted((p.t, self.now))
        if end - start < EVENT_TIME_RESOLUTION:
            QtWidgets.QMessageBox.information(
                self, "End event", f"Move the play bar to where '{p.name}' ends, then click again."
            )
            return
        existing = self.take.event_at(start) if start != p.t else None
        if existing is not None:
            QtWidgets.QMessageBox.information(
                self, "End event", f"There is already a '{existing.name}' event at {existing.t:.3f} s"
            )
            return
        event = TakeEvent(t=start, name=p.name, type=p.type, added=p.added, end=end)
        self._pending = None
        if self._save_events(self.take.events + [event], "End event"):
            self.event_list.scrollToBottom()
        else:
            self._pending = p
            self._show_pending()
            self._update_buttons()

    def cancel_pending(self) -> None:
        self._pending = None
        self._show_pending()
        self._update_buttons()

    def edit_selected_event(self) -> None:
        event = self._selected_event()
        if event is None:
            return
        # Only events of the same length, so an instant event never gets (or loses) an end.
        same_length = {
            name: info for name, info in self.event_defs.items()
            if self._is_duration(name) == (event.end is not None)
        }
        dialog = EditEventDialog(
            self, event, same_length, self._color, note=f"{self.take.name}.npz will be updated."
        )
        if dialog.exec_() != QtWidgets.QDialog.Accepted or dialog.name() == event.name:
            return
        row = self.event_list.currentRow()
        name = dialog.name()
        renamed = TakeEvent(
            t=event.t, name=name, type=self.event_defs[name].get("type", ""),
            added=event.added, end=event.end,
        )
        events = [renamed if e is event else e for e in self.take.events]
        if self._save_events(events, "Edit event"):
            self.event_list.setCurrentRow(row)

    def delete_selected_event(self) -> None:
        event = self._selected_event()
        if event is None:
            return
        answer = QtWidgets.QMessageBox.warning(
            self,
            "Delete event",
            f"Delete '{event.name}' at {event.span_text()} from {self.take.name}.npz?\n"
            "This cannot be undone.",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )
        if answer == QtWidgets.QMessageBox.Ok:
            self._save_events([e for e in self.take.events if e is not event], "Delete event")


class EditTab(QtWidgets.QWidget):
    """Same layout as the Create tab, for labelling recorded takes with events.

    Each finger picks one of its takes; the plot shows the whole take and the play bar / plot
    cursor scrub through it (nothing is sent to the hand). The camera and the FK taxels show the
    take's recording at the position of the finger last scrubbed. Events from ``events.json``
    are added at the play bar position and saved in the finger's take as ``events``. Delete take
    removes the selected take from disk after a confirmation.
    """

    delete_requested = QtCore.pyqtSignal(str)  # path of the take

    def __init__(
        self, store: TakeStore, event_defs: dict[str, dict], counts_per_unit: float
    ) -> None:
        super().__init__()
        self.store = store
        self._video = TakeVideo()

        grid = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        self.panels: dict[str, EditFingerPanel] = {}
        for n, (finger, label) in enumerate(FINGERS):
            panel = EditFingerPanel(finger, label, store, event_defs, counts_per_unit)
            self.panels[finger] = panel
            grid_layout.addWidget(panel, n // 2, n % 2)
            panel.seeked.connect(self._show)
            panel.delete_requested.connect(self.delete_requested)

        self.camera = CameraView("")
        self.camera.set_message("Scrub a take to see its camera recording")
        self.hand = HandView(
            "", "", counts_per_unit,
            waiting="Scrub a take to see its taxels",
            no_xela="Scrub a take to see its Xela readings",
        )
        side = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        side.addWidget(self.camera)
        side.addWidget(self.hand)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(grid)
        splitter.addWidget(side)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        hint = QtWidgets.QLabel(
            "Pick a take per finger, scrub with the play bar or the yellow cursor, then add the "
            "selected event at that time (duration events: click once at the start, once at the "
            "end). Click an event in a list to jump to it."
            if event_defs
            else "<span style='color:#d32f2f'>No event definitions loaded (events_file).</span>"
        )
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(splitter, 1)
        self.refresh_takes()

    def refresh_takes(self) -> None:
        for panel in self.panels.values():
            panel.fill_takes()

    def _show(self, finger: str) -> None:
        """Camera frame and FK taxels of ``finger``'s take at its play bar position."""
        panel = self.panels[finger]
        if panel.take is not None:
            show_take_at(panel.take, panel.now, self.camera, self.hand, self._video)

    def forget_take(self, path: str) -> None:
        """Stops showing the take at ``path`` (about to be deleted)."""
        if self.hand.take_path == path:
            self._video.release()
            self.hand.clear()
            self.camera.set_message("Scrub a take to see its camera recording")

    def close_video(self) -> None:
        self._video.release()


class FingerRow:
    """Take / offset / speed controls for one finger in the compose tab."""

    def __init__(self, finger: str) -> None:
        self.finger = finger
        self.take_combo = QtWidgets.QComboBox()
        self.take_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.offset_spin = QtWidgets.QDoubleSpinBox()
        self.offset_spin.setRange(0.0, 600.0)
        self.offset_spin.setSingleStep(0.1)
        self.offset_spin.setSuffix(" s")
        self.offset_spin.setToolTip("Start time of this take in the composition")
        self.speed_spin = QtWidgets.QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 10.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setSuffix(" x")
        self.info = QtWidgets.QLabel()

    def fill(self, store: TakeStore, keep: str | None = None) -> None:
        keep = keep if keep is not None else self.take_combo.currentData()
        self.take_combo.blockSignals(True)
        self.take_combo.clear()
        self.take_combo.addItem(HOLD_BASE, None)
        for path in store.list(self.finger):
            self.take_combo.addItem(os.path.splitext(os.path.basename(path))[0], path)
        index = self.take_combo.findData(keep) if keep else 0
        self.take_combo.setCurrentIndex(max(index, 0))
        self.take_combo.blockSignals(False)


class ComposeTab(QtWidgets.QWidget):
    def __init__(self, node: LeapStateListener, store: TakeStore) -> None:
        super().__init__()
        self.node = node
        self.store = store
        self.base_pose: np.ndarray | None = None
        self._t = np.empty(0)
        self._q = np.empty((0, NUM_JOINTS))
        self._joint_names = list(DEFAULT_JOINT_NAMES)

        grid = QtWidgets.QGridLayout()
        for col, header in enumerate(("Finger", "Take", "Offset", "Speed", "")):
            grid.addWidget(QtWidgets.QLabel(f"<b>{header}</b>"), 0, col)
        self.rows: dict[str, FingerRow] = {}
        for r, (finger, label) in enumerate(FINGERS, start=1):
            row = FingerRow(finger)
            self.rows[finger] = row
            grid.addWidget(QtWidgets.QLabel(label), r, 0)
            grid.addWidget(row.take_combo, r, 1)
            grid.addWidget(row.offset_spin, r, 2)
            grid.addWidget(row.speed_spin, r, 3)
            grid.addWidget(row.info, r, 4)
            row.take_combo.currentIndexChanged.connect(self.recompose)
            row.offset_spin.valueChanged.connect(self.recompose)
            row.speed_spin.valueChanged.connect(self.recompose)
        grid.setColumnStretch(4, 1)

        self.base_label = QtWidgets.QLabel()
        self.capture_btn = QtWidgets.QPushButton("Capture base pose from live leap_state")
        self.clear_base_btn = QtWidgets.QPushButton("Clear")
        self.rate_spin = QtWidgets.QDoubleSpinBox()
        self.rate_spin.setRange(1.0, 500.0)
        self.rate_spin.setValue(30.0)
        self.rate_spin.setSuffix(" Hz")
        self.rate_spin.setToolTip("Sample rate of the composed demonstration")
        base_row = QtWidgets.QHBoxLayout()
        base_row.addWidget(QtWidgets.QLabel("Base pose:"))
        base_row.addWidget(self.base_label, 1)
        base_row.addWidget(self.capture_btn)
        base_row.addWidget(self.clear_base_btn)
        base_row.addSpacing(20)
        base_row.addWidget(QtWidgets.QLabel("Rate:"))
        base_row.addWidget(self.rate_spin)

        settings = QtWidgets.QGroupBox("Composition")
        settings_layout = QtWidgets.QVBoxLayout(settings)
        settings_layout.addLayout(grid)
        settings_layout.addLayout(base_row)

        self.plots = pg.GraphicsLayoutWidget()
        self.finger_plots: dict[str, tuple[pg.PlotItem, list[pg.PlotDataItem], pg.LinearRegionItem]] = {}
        first = None
        for finger, label in FINGERS:
            plot = self.plots.addPlot(title=label)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.addLegend(offset=(5, 5))
            region = pg.LinearRegionItem(movable=False, brush=pg.mkBrush(100, 100, 255, 40))
            region.setZValue(-10)
            plot.addItem(region)
            curves = [plot.plot(pen=pg.mkPen(color, width=2)) for color in JOINT_COLORS]
            if first is None:
                first = plot
            else:
                plot.setXLink(first)
            self.finger_plots[finger] = (plot, curves, region)
            self.plots.nextRow()
        plot.setLabel("bottom", "time", "s")

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("composition name (default: timestamp)")
        self.load_btn = QtWidgets.QPushButton("Load composition...")
        self.save_btn = QtWidgets.QPushButton("Save composition")
        self.summary = QtWidgets.QLabel()
        save_row = QtWidgets.QHBoxLayout()
        save_row.addWidget(self.summary, 1)
        save_row.addWidget(QtWidgets.QLabel("Name:"))
        save_row.addWidget(self.name_edit, 1)
        save_row.addWidget(self.load_btn)
        save_row.addWidget(self.save_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(settings)
        layout.addWidget(self.plots, 1)
        layout.addLayout(save_row)

        self.capture_btn.clicked.connect(self._capture_base)
        self.clear_base_btn.clicked.connect(self._clear_base)
        self.rate_spin.valueChanged.connect(self.recompose)
        self.save_btn.clicked.connect(self._save)
        self.load_btn.clicked.connect(self._load)

        self.refresh_takes()

    def refresh_takes(self) -> None:
        for row in self.rows.values():
            row.fill(self.store)
        self.recompose()

    def _capture_base(self) -> None:
        q = self.node.latest()
        if q is None:
            QtWidgets.QMessageBox.warning(self, "Base pose", "No leap_state received yet.")
            return
        self.base_pose = q
        self.recompose()

    def _clear_base(self) -> None:
        self.base_pose = None
        self.recompose()

    def _selected_takes(self) -> dict[str, FingerTake]:
        takes = {}
        for finger, row in self.rows.items():
            path = row.take_combo.currentData()
            row.info.setText("")
            if path is None:
                continue
            try:
                takes[finger] = self.store.load(path)
            except Exception as e:
                row.info.setText(f"<span style='color:#d32f2f'>load failed: {e}</span>")
        return takes

    def recompose(self, *_) -> None:
        takes = self._selected_takes()
        if takes:
            first = next(iter(takes.values()))
            self._joint_names = first.hand_joint_names
        else:
            self._joint_names = self.node.joint_names

        if self.base_pose is not None:
            base = self.base_pose
            self.base_label.setText("captured from live leap_state")
        elif takes:
            base = first.hand_q[0]
            self.base_label.setText(
                f"first frame of '{first.name}' ({FINGER_LABEL[first.finger]}) - capture one to override"
            )
        else:
            base = None
            self.base_label.setText("not set")

        end = 0.0
        for finger, take in takes.items():
            row = self.rows[finger]
            stop = row.offset_spin.value() + take.duration / row.speed_spin.value()
            end = max(end, stop)
            row.info.setText(f"{take.duration:.2f} s take, active {row.offset_spin.value():.2f}-{stop:.2f} s")

        if base is None or end <= 0.0:
            self._t, self._q = np.empty(0), np.empty((0, NUM_JOINTS))
        else:
            t = np.arange(0.0, end, 1.0 / self.rate_spin.value())
            self._t = np.append(t, end) if t[-1] < end else t
            self._q = np.tile(base, (len(self._t), 1))
            for finger, take in takes.items():
                row = self.rows[finger]
                local = (self._t - row.offset_spin.value()) * row.speed_spin.value()
                cols = self._columns_for(take)
                for j, col in enumerate(cols):
                    # np.interp holds the first/last sample outside the take.
                    self._q[:, col] = np.interp(local, take.t, take.q[:, j])
        self._update_plots(takes)

    def _columns_for(self, take: FingerTake) -> list[int]:
        if all(name in self._joint_names for name in take.joint_names):
            return [self._joint_names.index(name) for name in take.joint_names]
        return finger_indices(self._joint_names, take.finger)

    def _update_plots(self, takes: dict[str, FingerTake]) -> None:
        for finger, (plot, curves, region) in self.finger_plots.items():
            idx = finger_indices(self._joint_names, finger)
            for curve, i in zip(curves, idx):
                curve.setData(self._t, self._q[:, i]) if len(self._t) else curve.setData([], [])
            plot.legend.clear()
            for curve, i in zip(curves, idx):
                plot.legend.addItem(curve, self._joint_names[i])
            take = takes.get(finger)
            if take is None:
                region.hide()
            else:
                row = self.rows[finger]
                start = row.offset_spin.value()
                region.setRegion((start, start + take.duration / row.speed_spin.value()))
                region.show()
        if len(self._t):
            self.summary.setText(f"{self._t[-1]:.2f} s, {len(self._t)} samples")
        else:
            self.summary.setText("Select at least one take to compose.")
        self.save_btn.setEnabled(len(self._t) > 0)

    def _meta(self) -> dict:
        return {
            "rate": self.rate_spin.value(),
            "base_pose": None if self.base_pose is None else self.base_pose.tolist(),
            "fingers": {
                finger: {
                    "take": row.take_combo.currentData(),
                    "offset": row.offset_spin.value(),
                    "speed": row.speed_spin.value(),
                }
                for finger, row in self.rows.items()
            },
        }

    def _save(self) -> None:
        name = safe_name(self.name_edit.text() or datetime.now().strftime("demo_%Y%m%d_%H%M%S"))
        os.makedirs(self.store.composed_dir, exist_ok=True)
        path = unique_path(self.store.composed_dir, name)
        np.savez(
            path,
            t=self._t,
            q=self._q,
            joint_names=np.array(self._joint_names),
            meta=json.dumps(self._meta()),
        )
        self.name_edit.clear()
        QtWidgets.QMessageBox.information(self, "Save composition", f"Saved {path}")

    def _load(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load composition", self.store.composed_dir, "Compositions (*.npz)"
        )
        if not path:
            return
        try:
            with np.load(path, allow_pickle=False) as data:
                meta = json.loads(str(data["meta"]))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Load composition", f"Could not load {path}:\n{e}")
            return
        missing = []
        widgets = [self.rate_spin] + [
            w for row in self.rows.values() for w in (row.take_combo, row.offset_spin, row.speed_spin)
        ]
        for w in widgets:
            w.blockSignals(True)
        self.rate_spin.setValue(meta.get("rate", self.rate_spin.value()))
        base = meta.get("base_pose")
        self.base_pose = None if base is None else np.asarray(base, dtype=float)
        for finger, row in self.rows.items():
            settings = meta.get("fingers", {}).get(finger, {})
            take = settings.get("take")
            if take and not os.path.exists(take):
                missing.append(take)
                take = None
            row.fill(self.store, keep=take or "")
            row.offset_spin.setValue(settings.get("offset", 0.0))
            row.speed_spin.setValue(settings.get("speed", 1.0))
        for w in widgets:
            w.blockSignals(False)
        self.name_edit.setText(os.path.splitext(os.path.basename(path))[0])
        self.recompose()
        if missing:
            QtWidgets.QMessageBox.warning(
                self, "Load composition", "These takes no longer exist:\n" + "\n".join(missing)
            )


def double_spin(
    minimum: float, maximum: float, step: float, decimals: int, suffix: str, tooltip: str
) -> QtWidgets.QDoubleSpinBox:
    spin = QtWidgets.QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setDecimals(decimals)
    spin.setSuffix(suffix)
    spin.setToolTip(tooltip)
    spin.setKeyboardTracking(False)  # typed values apply on Enter, not per keystroke
    return spin


class SettingsTab(QtWidgets.QWidget):
    """Hold / playback / compliance values of this GUI (applied immediately) and the compliant
    gains of the hand node (applied with "Apply to hand")."""

    settings_changed = QtCore.pyqtSignal()
    demo_dir_changed = QtCore.pyqtSignal(str)
    # Emitted from the executor thread; Qt queues them to the GUI thread.
    _hand_loaded = QtCore.pyqtSignal(object)
    _hand_applied = QtCore.pyqtSignal(object)

    RETRY_MS = 2000

    def __init__(self, node: LeapStateListener, store: TakeStore, settings: HoldSettings) -> None:
        super().__init__()
        self.node = node
        self.store = store
        self.settings = settings
        self._hand_compliant: bool | None = None  # None until read from the hand node

        self.dir_edit = QtWidgets.QLineEdit(store.demo_dir)
        self.dir_edit.setToolTip(
            "Folder takes are saved into (fingers/, camera/ and composed/ inside it). "
            "Press Enter to apply"
        )
        browse_btn = QtWidgets.QPushButton("Browse...")
        dir_row = QtWidgets.QHBoxLayout()
        dir_row.addWidget(self.dir_edit, 1)
        dir_row.addWidget(browse_btn)
        dir_box = QtWidgets.QGroupBox("Recordings")
        dir_form = QtWidgets.QFormLayout(dir_box)
        dir_form.addRow("Save to:", dir_row)
        self.dir_edit.editingFinished.connect(lambda: self._set_demo_dir(self.dir_edit.text()))
        browse_btn.clicked.connect(self._browse_demo_dir)

        self.rate_spin = double_spin(
            5.0, 100.0, 5.0, 0, " Hz",
            "How often held and playing fingers are commanded on cmd_topic",
        )
        self.ramp_spin = double_spin(
            0.0, 5.0, 0.1, 2, " s",
            "Play first moves the finger from where it is to the take over this time",
        )
        self.deadband_spin = double_spin(
            0.0, 0.5, 0.005, 3, " rad",
            "While a finger is held or playing, the other fingers follow the hand once pushed "
            "further than this. Lower = easier to pose, higher = less drift from gravity sag",
        )
        gui_box = QtWidgets.QGroupBox("Hold && playback (this GUI, applied immediately)")
        gui_form = QtWidgets.QFormLayout(gui_box)
        gui_form.addRow("Command rate:", self.rate_spin)
        gui_form.addRow("Playback ramp:", self.ramp_spin)
        gui_form.addRow("Free-finger deadband:", self.deadband_spin)
        reset_btn = QtWidgets.QPushButton("Reset to defaults")
        gui_form.addRow("", reset_btn)
        self._show_settings()
        for spin in (self.rate_spin, self.ramp_spin, self.deadband_spin):
            spin.valueChanged.connect(self._on_gui_changed)
        reset_btn.clicked.connect(self._reset_gui)

        self.hand_spins: dict[str, QtWidgets.QDoubleSpinBox] = {}
        self.hand_box = QtWidgets.QGroupBox(f"Hand compliance ({node.hand_node}, compliant mode)")
        hand_form = QtWidgets.QFormLayout(self.hand_box)
        for name, label, maximum, step, decimals, suffix, tooltip in HAND_PARAMS:
            spin = double_spin(0.0, maximum, step, decimals, suffix, tooltip)
            self.hand_spins[name] = spin
            hand_form.addRow(f"{label}:", spin)
        self.apply_btn = QtWidgets.QPushButton("Apply to hand")
        self.reload_btn = QtWidgets.QPushButton("Reload from hand")
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.apply_btn)
        buttons.addWidget(self.reload_btn)
        buttons.addStretch(1)
        hand_form.addRow("", buttons)
        self.hand_status = QtWidgets.QLabel()
        self.hand_status.setWordWrap(True)
        hand_form.addRow(self.hand_status)
        self.apply_btn.clicked.connect(self._apply_hand)
        self.reload_btn.clicked.connect(self._reload_hand)
        self._hand_loaded.connect(self._on_hand_loaded)
        self._hand_applied.connect(self._on_hand_applied)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(dir_box)
        layout.addWidget(gui_box)
        layout.addWidget(self.hand_box)
        layout.addStretch(1)

        self._retry = QtCore.QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.timeout.connect(self._reload_hand)
        self._set_hand_enabled(False)
        self._reload_hand()

    # ---- recordings folder --------------------------------------------------------------

    def _browse_demo_dir(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Recordings folder", self.store.demo_dir
        )
        if path:
            self._set_demo_dir(path)

    def _set_demo_dir(self, text: str) -> None:
        path = os.path.abspath(os.path.expanduser(text.strip())) if text.strip() else ""
        if not path or path == self.store.demo_dir:
            self.dir_edit.setText(self.store.demo_dir)
            return
        if self.node.recording:
            self.dir_edit.setText(self.store.demo_dir)
            QtWidgets.QMessageBox.warning(
                self, "Recordings", "Stop the recording before changing the folder."
            )
            return
        self.dir_edit.setText(path)
        self.demo_dir_changed.emit(path)

    # ---- this GUI -----------------------------------------------------------------------

    def _show_settings(self) -> None:
        for spin, value in (
            (self.rate_spin, self.settings.command_rate),
            (self.ramp_spin, self.settings.ramp_s),
            (self.deadband_spin, self.settings.deadband),
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    def _on_gui_changed(self, *_) -> None:
        self.settings.command_rate = self.rate_spin.value()
        self.settings.ramp_s = self.ramp_spin.value()
        self.settings.deadband = self.deadband_spin.value()
        self.settings_changed.emit()

    def _reset_gui(self) -> None:
        defaults = HoldSettings()
        self.settings.command_rate = defaults.command_rate
        self.settings.ramp_s = defaults.ramp_s
        self.settings.deadband = defaults.deadband
        self._show_settings()
        self.settings_changed.emit()

    # ---- hand node ----------------------------------------------------------------------

    def _set_hand_enabled(self, on: bool) -> None:
        for spin in self.hand_spins.values():
            spin.setEnabled(on)
        self.apply_btn.setEnabled(on)

    def _status(self, text: str, error: bool = False) -> None:
        self.hand_status.setText(f"<span style='color:#d32f2f'>{text}</span>" if error else text)

    def _reload_hand(self) -> None:
        if not self.node.hand_params_ready():
            self._set_hand_enabled(False)
            self._status(f"Waiting for {self.node.hand_node} ...")
            self._retry.start(self.RETRY_MS)
            return
        self._status("Reading parameters ...")
        names = ["compliant"] + [name for name, *_ in HAND_PARAMS]
        self.node.get_hand_params(names, self._hand_loaded.emit)

    def _on_hand_loaded(self, result) -> None:
        if isinstance(result, Exception):
            self._set_hand_enabled(False)
            self._status(f"Could not read parameters: {result}", error=True)
            return
        missing = [name for name, *_ in HAND_PARAMS if result.get(name) is None]
        if missing:
            self._set_hand_enabled(False)
            self._status(
                f"{self.node.hand_node} does not have {', '.join(missing)} "
                "(rebuild leap_hand and restart it)",
                error=True,
            )
            return
        for name, spin in self.hand_spins.items():
            spin.setValue(float(result[name]))
        self._hand_compliant = bool(result.get("compliant"))
        self._set_hand_enabled(self._hand_compliant)
        if self._hand_compliant:
            self._status("Loaded from the hand.")
        else:
            self._status(
                f"{self.node.hand_node} is not in compliant mode, so these have no effect "
                "(launch with compliant:=true)."
            )

    def _apply_hand(self) -> None:
        if not self.node.hand_params_ready():
            self._status(f"{self.node.hand_node} is not running.", error=True)
            return
        self.apply_btn.setEnabled(False)
        self._status("Applying ...")
        values = {name: spin.value() for name, spin in self.hand_spins.items()}
        self.node.set_hand_params(values, self._hand_applied.emit)

    def _on_hand_applied(self, result) -> None:
        self.apply_btn.setEnabled(bool(self._hand_compliant))
        if isinstance(result, Exception):
            self._status(f"Apply failed: {result}", error=True)
        elif not result.successful:
            self._status(f"Rejected by {self.node.hand_node}: {result.reason}", error=True)
        else:
            self._status("Applied to the hand.")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, node: LeapStateListener) -> None:
        super().__init__()
        self.node = node
        self.setWindowTitle(f"Record demonstration - {node.demo_dir}")
        self.resize(1600, 900)
        self.store = TakeStore(node.demo_dir)
        settings = HoldSettings()
        try:
            event_defs = load_event_definitions(node.events_file)
        except Exception as e:
            node.get_logger().warn(f"Could not load events from {node.events_file}: {e}")
            event_defs = {}
        self.create_tab = CreateTab(node, self.store, settings)
        self.edit_tab = EditTab(self.store, event_defs, node.counts_per_unit)
        self.compose_tab = ComposeTab(node, self.store)
        self.settings_tab = SettingsTab(node, self.store, settings)
        self.create_tab.takes_changed.connect(self.compose_tab.refresh_takes)
        self.create_tab.takes_changed.connect(self.edit_tab.refresh_takes)
        self.edit_tab.delete_requested.connect(self._delete_take)
        self.settings_tab.settings_changed.connect(self.create_tab.apply_settings)
        self.settings_tab.demo_dir_changed.connect(self._set_demo_dir)
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.create_tab, "Create")
        tabs.addTab(self.edit_tab, "Edit")
        tabs.addTab(self.compose_tab, "Compose")
        tabs.addTab(self.settings_tab, "Settings")
        self.setCentralWidget(tabs)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.create_tab.refresh)
        self._timer.start(REFRESH_MS)

    def _delete_take(self, path: str) -> None:
        self.create_tab.forget_take(path)
        self.edit_tab.forget_take(path)
        try:
            self.store.delete(path)
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "Delete take", f"Could not delete {path}:\n{e}")
        else:
            self.node.get_logger().info(f"Deleted take '{path}'")
        self.create_tab.reload_takes()
        self.edit_tab.refresh_takes()
        self.compose_tab.refresh_takes()

    def _set_demo_dir(self, path: str) -> None:
        self.create_tab.stop_all_playback()
        self.node.demo_dir = path
        self.store.demo_dir = path
        self.setWindowTitle(f"Record demonstration - {path}")
        self.node.get_logger().info(f"Saving demonstrations to '{path}'")
        self.create_tab.reload_takes()
        self.edit_tab.refresh_takes()
        self.compose_tab.refresh_takes()

    def closeEvent(self, ev) -> None:
        self.create_tab.stop_all_playback()
        if self.node.recording:
            answer = QtWidgets.QMessageBox.question(
                self, "Quit", "A recording is in progress. Save it before quitting?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
            )
            if answer == QtWidgets.QMessageBox.Cancel:
                ev.ignore()
                return
            if answer == QtWidgets.QMessageBox.Save:
                self.create_tab.stop_recording()
            else:
                video = self.node.stop_recording().video
                if video:
                    os.remove(video)
        for finger in list(self.create_tab._held):
            self.create_tab.panels[finger].hold_switch.setChecked(False)
        self.create_tab.release_stiff_joints()
        self.create_tab.close_video()
        self.edit_tab.close_video()
        super().closeEvent(ev)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LeapStateListener()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    # Without an explicit version Qt reports OpenGL 2.0 and pyqtgraph.opengl refuses to draw.
    fmt = QtGui.QSurfaceFormat()
    fmt.setVersion(2, 1)
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)
    app = QtWidgets.QApplication(sys.argv[:1])
    window = MainWindow(node)
    window.show()
    signal.signal(signal.SIGINT, lambda *_: window.close())
    wake = QtCore.QTimer()  # lets the Python interpreter handle SIGINT while Qt runs
    wake.timeout.connect(lambda: None)
    wake.start(200)
    try:
        code = app.exec_()
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
