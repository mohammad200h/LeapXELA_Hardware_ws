#!/usr/bin/env python3
"""Record per-finger LEAP hand demonstrations from ``/leap_state`` and compose them.

Create tab: one live plot per finger, each with its own Record and Play controls. A finger's
Record saves a take of that finger only, named after the text box next to it (a timestamped
default is filled in); "Record all fingers" saves a take for every finger. Takes (the full hand
is stored alongside for reference) go to ``<demo_dir>/fingers/<finger>/<name>.npz``. The camera
feed of the take is written to ``<demo_dir>/camera/<name>.mp4``; every take stores its path as
``video`` and the frame times as ``video_t`` (same time axis as ``t``). The sim-frame joints
from ``sim_topic`` (``convert_hardware_to_sim``) are stored as ``sim_t`` / ``sim_hand_q`` /
``sim_hand_joint_names``; the plots only show ``joint_topic``. Play sends the take chosen in
the dropdown next to it to the hand on ``cmd_topic``, starting from the play bar position.
A finger's Hold switch keeps it at the pose it had when the switch was turned on. While any
finger is held or playing, the other fingers can still be moved by hand. Under the camera, the
taxels of the hand are placed live by forward kinematics (``taxel_fk_util``) from ``sim_topic``.

Compose tab: pick one take per finger with a time offset and speed; fingers without a
take hold the base pose. The result is resampled on a common timeline and saved as
``<demo_dir>/composed/<name>.npz`` with ``t`` (N,), ``q`` (N, 16), ``joint_names`` and
``meta`` (JSON of the settings, so the composition can be loaded and edited again).

Settings tab: command rate, playback ramp and free-finger deadband used while fingers are held
or playing (applied immediately), and the compliant gains / deadband of ``hand_node``
(leaphand_node), read and set through its ROS parameters.

Usage:
  ros2 run mechanical_pen_data_collection record_demonstration \
      [--ros-args -p joint_topic:=leap_state -p sim_topic:=leap_state_sim -p cmd_topic:=cmd_xela \
                  -p image_topic:=/camera/color/image_raw -p demo_dir:=PATH \
                  -p hand_node:=leaphand_node]
"""

from __future__ import annotations

import json
import os
import re
import signal
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
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

from mechanical_pen_data_collection.bag_data import default_bag_dir, image_to_array

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
HOLD_BASE = "— hold base pose —"
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

    @property
    def name(self) -> str:
        return os.path.splitext(os.path.basename(self.path))[0]

    @property
    def duration(self) -> float:
        return float(self.t[-1]) if len(self.t) else 0.0

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        np.savez(
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
        )

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


@dataclass
class Recording:
    t: np.ndarray  # (N,) joint times, starting at 0
    q: np.ndarray  # (N, 16)
    video: str  # "" if no camera frames were received
    video_t: np.ndarray  # (M,) frame times on the same axis as ``t``
    sim_t: np.ndarray  # (K,) sim_topic times on the same axis as ``t``
    sim_q: np.ndarray  # (K, 16)
    sim_joint_names: list[str]


class LeapStateListener(Node):
    """Buffers ``leap_state``, ``leap_state_sim`` and the camera for the live view and records
    them while asked to."""

    def __init__(self) -> None:
        super().__init__("record_demonstration")
        topic = self.declare_parameter("joint_topic", "leap_state").value
        self.sim_topic = self.declare_parameter("sim_topic", "leap_state_sim").value
        cmd_topic = self.declare_parameter("cmd_topic", "cmd_xela").value
        self.image_topic = self.declare_parameter("image_topic", "/camera/color/image_raw").value
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

        self.create_subscription(JointState, topic, self._on_state, 10)
        self.create_subscription(JointState, self.sim_topic, self._on_sim_state, 10)
        if self.image_topic:
            self.create_subscription(Image, self.image_topic, self._on_image, qos_profile_sensor_data)
        self._cmd_pub = self.create_publisher(JointState, cmd_topic, 10)
        self.hand_node = self.declare_parameter("hand_node", "leaphand_node").value
        self._get_params = self.create_client(GetParameters, f"{self.hand_node}/get_parameters")
        self._set_params = self.create_client(
            SetParametersAtomically, f"{self.hand_node}/set_parameters_atomically"
        )
        self.get_logger().info(
            f"Listening on '{topic}', '{self.sim_topic}' and '{self.image_topic or '(no camera)'}', "
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

    def set_hand_params(self, values: dict[str, float], done) -> None:
        """Sets double parameters of the hand node at once; ``done`` gets the
        ``SetParametersResult`` or an exception."""
        params = [
            Parameter(
                name=name,
                value=ParameterValue(type=ParameterType.PARAMETER_DOUBLE, double_value=float(v)),
            )
            for name, v in values.items()
        ]
        self._call(
            self._set_params,
            SetParametersAtomically.Request(parameters=params),
            lambda res: res.result,
            done,
        )

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
        t0 = t[0] if len(t) else (video_t[0] if len(video_t) else 0.0)
        return Recording(
            t=t - t0,
            q=q,
            video=video,
            video_t=video_t - t0,
            sim_t=sim_t - t0,
            sim_q=sim_q,
            sim_joint_names=sim_names,
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


class HandView(QtWidgets.QStackedWidget):
    """Taxels of the hand placed by forward kinematics from sim-frame joint angles (no taxel
    values)."""

    TAXEL_SIZE = 0.003  # m

    def __init__(self, topic: str) -> None:
        super().__init__()
        self.setMinimumSize(320, 240)
        self._last: np.ndarray | None = None
        self._fk = None
        try:
            import pyqtgraph.opengl as gl

            from mechanical_pen_data_collection import taxel_fk_util as fk
        except Exception as e:
            self.addWidget(self._message(f"Hand view unavailable: {e}"))
            return
        self._fk = fk
        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor((20, 20, 26))
        colors = fk.taxel_patch_colors(fk.PATCH_IDS_IN_FK_ORDER)
        self._scatter = gl.GLScatterPlotItem(
            pos=np.zeros((fk.NUM_TAXELS, 3)),
            color=np.column_stack([colors, np.ones(len(colors))]),
            size=self.TAXEL_SIZE,
            pxMode=False,
        )
        self.view.addItem(self._scatter)
        self.view.addItem(gl.GLAxisItem(size=QtGui.QVector3D(0.04, 0.04, 0.04)))
        self.addWidget(self._message(f"Waiting for {topic} (convert_hardware_to_sim) ..."))
        self.addWidget(self.view)

    @staticmethod
    def _message(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("background-color: black; color: white;")
        return label

    def set_joints(self, names: list[str], q: np.ndarray) -> None:
        if self._fk is None or (self._last is not None and np.array_equal(q, self._last)):
            return
        first = self._last is None
        self._last = q.copy()
        try:
            pos, _ = self._fk.get_fk_taxel_frames(self._fk.joint_angles_in_fk_order(names, q))
        except Exception as e:
            self._fk = None
            self.addWidget(self._message(f"Hand view failed: {e}"))
            self.setCurrentIndex(self.count() - 1)
            return
        self._scatter.setData(pos=pos[0])
        if first:
            self.setCurrentWidget(self.view)
            # Side view as in the MuJoCo scene: fingers along +Y, Z up.
            center = pos[0].mean(axis=0)
            self.view.setCameraPosition(
                pos=QtGui.QVector3D(*center), distance=0.35, elevation=20, azimuth=-125
            )


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

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(self.plot, 1)

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


@dataclass
class Playback:
    take: FingerTake
    cols: list[int]  # hand columns driven by the take
    start: float  # time.monotonic() when the ramp started
    from_q: np.ndarray  # finger joints at the start of the ramp
    offset: float  # take time reached at the end of the ramp
    to_q: np.ndarray  # finger joints at ``offset``


class CreateTab(QtWidgets.QWidget):
    """One live plot per finger with Record / Play buttons, plus the camera.

    A finger's Record saves a take of that finger under the name in its text box; "Record all
    fingers" saves a take of every finger. Play sends the take selected in the finger's dropdown
    to the hand, starting from the play bar position. Hold keeps a finger at its pose.

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
        self._take_name = ""
        self._rec_fingers: tuple[str, ...] = ()
        self._rec_btn: QtWidgets.QPushButton | None = None
        self._free: np.ndarray | None = None  # goal of the fingers neither held nor playing
        self._last_cmd: np.ndarray | None = None
        self._playing: dict[str, Playback] = {}
        self._held: dict[str, np.ndarray] = {}  # finger -> joint positions it is held at

        self.record_all_btn = QtWidgets.QPushButton("Record all fingers")
        self.record_all_btn.setMinimumHeight(40)
        all_fingers = tuple(finger for finger, _ in FINGERS)
        self.record_all_btn.clicked.connect(
            lambda: self.toggle_recording(all_fingers, self.record_all_btn)
        )

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
        self.hand = HandView(node.sim_topic)
        side = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        side.addWidget(self.camera)
        side.addWidget(self.hand)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(grid)
        splitter.addWidget(side)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.record_all_btn)
        layout.addWidget(splitter, 1)

        self._cmd_timer = QtCore.QTimer(self)
        self._cmd_timer.timeout.connect(self._command_step)

    def _record_buttons(self) -> list[QtWidgets.QPushButton]:
        return [self.record_all_btn] + [p.record_btn for p in self.panels.values()]

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
        self.record_all_btn.setText("Record all fingers")
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
        )
        panel.take_combo.setEnabled(False)
        panel.play_btn.setText("Stop")
        panel.play_btn.setStyleSheet(STOP_STYLE)

    def _stop_play(self, finger: str, rewind: bool = False) -> None:
        """Stops ``finger`` where it was last commanded; it then follows the hand again."""
        playback = self._playing.pop(finger)
        if self._last_cmd is not None and self._free is not None:
            self._free[playback.cols] = self._last_cmd[playback.cols]
        panel = self.panels[finger]
        panel.take_combo.setEnabled(True)
        panel.play_btn.setText("Play")
        panel.play_btn.setStyleSheet("")
        if rewind:
            panel.set_position(0.0)
        self._stop_commanding_if_idle()

    def stop_all_playback(self) -> None:
        for finger in list(self._playing):
            self._stop_play(finger)

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
            self.panels[finger].set_position(local)
        self.node.send_command(q)
        self._last_cmd = q
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
    # Emitted from the executor thread; Qt queues them to the GUI thread.
    _hand_loaded = QtCore.pyqtSignal(object)
    _hand_applied = QtCore.pyqtSignal(object)

    RETRY_MS = 2000

    def __init__(self, node: LeapStateListener, settings: HoldSettings) -> None:
        super().__init__()
        self.node = node
        self.settings = settings
        self._hand_compliant: bool | None = None  # None until read from the hand node

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
        layout.addWidget(gui_box)
        layout.addWidget(self.hand_box)
        layout.addStretch(1)

        self._retry = QtCore.QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.timeout.connect(self._reload_hand)
        self._set_hand_enabled(False)
        self._reload_hand()

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
        self.resize(1300, 900)
        store = TakeStore(node.demo_dir)
        settings = HoldSettings()
        self.create_tab = CreateTab(node, store, settings)
        self.compose_tab = ComposeTab(node, store)
        self.settings_tab = SettingsTab(node, settings)
        self.create_tab.takes_changed.connect(self.compose_tab.refresh_takes)
        self.settings_tab.settings_changed.connect(self.create_tab.apply_settings)
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.create_tab, "Create")
        tabs.addTab(self.compose_tab, "Compose")
        tabs.addTab(self.settings_tab, "Settings")
        self.setCentralWidget(tabs)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.create_tab.refresh)
        self._timer.start(REFRESH_MS)

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
