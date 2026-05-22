"""
Receive Quest UDP tracking in VisionProTeleop / avp_stream layout.

Subscribe mode (Quest IP only in Python):
    python quest_streamer.py --quest-ip 192.168.2.48 --port 5006

    from quest_streamer import QuestVisionProStreamer
    s = QuestVisionProStreamer(quest_ip="192.168.2.48", port=5006)
"""

from __future__ import annotations

import json
import socket
import threading
import time
from copy import deepcopy
from typing import Any, Dict, Optional

import numpy as np

JOINT_NAMES = {
    "wrist": 0,
    "thumbKnuckle": 1,
    "thumbIntermediateBase": 2,
    "thumbIntermediateTip": 3,
    "thumbTip": 4,
    "indexMetacarpal": 5,
    "indexKnuckle": 6,
    "indexIntermediateBase": 7,
    "indexIntermediateTip": 8,
    "indexTip": 9,
    "middleMetacarpal": 10,
    "middleKnuckle": 11,
    "middleIntermediateBase": 12,
    "middleIntermediateTip": 13,
    "middleTip": 14,
    "ringMetacarpal": 15,
    "ringKnuckle": 16,
    "ringIntermediateBase": 17,
    "ringIntermediateTip": 18,
    "ringTip": 19,
    "littleMetacarpal": 20,
    "littleKnuckle": 21,
    "littleIntermediateBase": 22,
    "littleIntermediateTip": 23,
    "littleTip": 24,
    "forearmWrist": 25,
    "forearmArm": 26,
}


def _flat_to_mat4(flat: list[float]) -> np.ndarray:
    return np.asarray(flat, dtype=np.float64).reshape(4, 4)


def _mat4_to_batch(items: list[dict]) -> np.ndarray:
    return np.stack([_flat_to_mat4(entry["m"]) for entry in items], axis=0)


def _packet_to_raw(packet: dict) -> Dict[str, Any]:
    head = _flat_to_mat4(packet["head"]["m"])[np.newaxis, ...]
    left_wrist = _flat_to_mat4(packet["left_wrist"]["m"])[np.newaxis, ...]
    right_wrist = _flat_to_mat4(packet["right_wrist"]["m"])[np.newaxis, ...]
    left_arm = _mat4_to_batch(packet["left_arm"]["items"])
    right_arm = _mat4_to_batch(packet["right_arm"]["items"])
    left_fingers = _mat4_to_batch(packet["left_fingers"]["items"])
    right_fingers = _mat4_to_batch(packet["right_fingers"]["items"])

    return {
        "head": head,
        "left_wrist": left_wrist,
        "right_wrist": right_wrist,
        "left_fingers": left_fingers,
        "right_fingers": right_fingers,
        "left_arm": left_arm,
        "right_arm": right_arm,
        "left_pinch_distance": float(packet["left_pinch_distance"]),
        "right_pinch_distance": float(packet["right_pinch_distance"]),
        "left_wrist_roll": float(packet["left_wrist_roll"]),
        "right_wrist_roll": float(packet["right_wrist_roll"]),
    }


class HandData(np.ndarray):
    """Minimal avp_stream-compatible HandData (world joints = wrist @ local)."""

    def __new__(
        cls,
        wrist: np.ndarray,
        fingers: np.ndarray,
        arm: np.ndarray,
        pinch_distance: float,
        wrist_roll: float,
    ):
        wrist_mat = wrist[0] if wrist.ndim == 3 else wrist
        world_joints = wrist_mat @ arm
        obj = np.asarray(world_joints).view(cls)
        obj.pinch_distance = pinch_distance
        obj.wrist_roll = wrist_roll
        obj.has_forearm = arm.shape[0] >= 27
        obj._wrist_mat = wrist_mat
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.pinch_distance = getattr(obj, "pinch_distance", 0.0)
        self.wrist_roll = getattr(obj, "wrist_roll", 0.0)
        self.has_forearm = getattr(obj, "has_forearm", False)
        self._wrist_mat = getattr(obj, "_wrist_mat", None)

    def __getattr__(self, name: str) -> np.ndarray:
        if name.startswith("_") or name in (
            "T",
            "dtype",
            "shape",
            "ndim",
            "size",
            "flat",
            "real",
            "imag",
            "data",
            "strides",
            "base",
            "flags",
            "itemsize",
            "nbytes",
            "ctypes",
        ):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        if name in JOINT_NAMES:
            idx = JOINT_NAMES[name]
            if idx < self.shape[0]:
                return self[idx]
            raise AttributeError(f"Joint '{name}' not available")
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


class TrackingData:
    """Dict-compatible wrapper matching avp_stream.get_latest() keys."""

    _DICT_KEYS = {
        "head",
        "left_wrist",
        "right_wrist",
        "left_fingers",
        "right_fingers",
        "left_arm",
        "right_arm",
        "left_pinch_distance",
        "right_pinch_distance",
        "left_wrist_roll",
        "right_wrist_roll",
    }

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._raw = data
        if data is None:
            self._head = None
            self._left = None
            self._right = None
            return

        head = data["head"]
        self._head = head[0] if head.ndim == 3 else head

        self._left = HandData(
            data["left_wrist"],
            data["left_fingers"],
            data["left_arm"],
            data["left_pinch_distance"],
            data["left_wrist_roll"],
        )
        self._right = HandData(
            data["right_wrist"],
            data["right_fingers"],
            data["right_arm"],
            data["right_pinch_distance"],
            data["right_wrist_roll"],
        )

    @property
    def head(self) -> Optional[np.ndarray]:
        return self._head

    @property
    def left(self) -> Optional[HandData]:
        return self._left

    @property
    def right(self) -> Optional[HandData]:
        return self._right

    def __getitem__(self, key: str) -> Any:
        if key not in self._DICT_KEYS:
            raise KeyError(key)
        return self._raw[key]

    def __contains__(self, key: object) -> bool:
        return key in self._DICT_KEYS

    def keys(self):
        return self._raw.keys()


SUBSCRIBE_PAYLOAD = b"avp_subscribe_v1"
DEFAULT_QUEST_SUBSCRIBE_PORT = 5007


def _send_subscribe(quest_ip: str, quest_subscribe_port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(SUBSCRIBE_PAYLOAD, (quest_ip, quest_subscribe_port))
    finally:
        sock.close()


class QuestVisionProStreamer:
    """Drop-in style receiver for Quest UDP avp_tracking_v1 packets."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5006,
        quest_ip: Optional[str] = None,
        quest_subscribe_port: int = DEFAULT_QUEST_SUBSCRIBE_PORT,
        resubscribe_interval_sec: float = 2.0,
        buffer_size: int = 65535,
    ):
        self.host = host
        self.port = port
        self.quest_ip = quest_ip
        self.quest_subscribe_port = quest_subscribe_port
        self._lock = threading.Lock()
        self._latest_raw: Optional[Dict[str, Any]] = None
        self._latest: Optional[TrackingData] = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._recv_loop, args=(buffer_size,), daemon=True)
        self._resub_thread: Optional[threading.Thread] = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        if quest_ip:
            _send_subscribe(quest_ip, quest_subscribe_port)
            if resubscribe_interval_sec > 0:
                self._resub_thread = threading.Thread(
                    target=self._resubscribe_loop,
                    args=(quest_ip, quest_subscribe_port, resubscribe_interval_sec),
                    daemon=True,
                )
                self._resub_thread.start()
        self._thread.start()

    def _resubscribe_loop(self, quest_ip: str, quest_subscribe_port: int, interval: float) -> None:
        while not self._stop.is_set():
            self._stop.wait(interval)
            if self._stop.is_set():
                break
            try:
                _send_subscribe(quest_ip, quest_subscribe_port)
            except OSError:
                pass

    def _recv_loop(self, buffer_size: int) -> None:
        while not self._stop.is_set():
            try:
                data, _addr = self._sock.recvfrom(buffer_size)
                packet = json.loads(data.decode("utf-8"))
                if packet.get("format_version") != "avp_tracking_v1":
                    continue
                raw = _packet_to_raw(packet)
                with self._lock:
                    self._latest_raw = raw
                    self._latest = TrackingData(raw)
            except Exception:
                continue

    def get_latest(self) -> Optional[TrackingData]:
        with self._lock:
            if self._latest is None:
                print("No tracking data received")
                while self._latest is None:
                    time.sleep(0.01)
            return self._latest

    def get_latest_raw(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._latest_raw) if self._latest_raw is not None else None

    def close(self) -> None:
        self._stop.set()
        self._sock.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Print Quest VisionPro-format tracking")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5006)
    parser.add_argument("--quest-ip", default=None, help="Quest IP; sends subscribe so Quest streams to this PC")
    parser.add_argument("--quest-subscribe-port", type=int, default=DEFAULT_QUEST_SUBSCRIBE_PORT)
    args = parser.parse_args()

    streamer = QuestVisionProStreamer(
        host=args.host,
        port=args.port,
        quest_ip=args.quest_ip,
        quest_subscribe_port=args.quest_subscribe_port,
    )
    if args.quest_ip:
        print(f"Subscribed to Quest {args.quest_ip}:{args.quest_subscribe_port}, listening on {args.host}:{args.port}")
    else:
        print(f"Listening on {args.host}:{args.port} (set --quest-ip for subscribe mode)")
    try:
        while True:
            data = streamer.get_latest()
            if data is not None:
                rw = data["right_wrist"][0, :3, 3]
                pinch = data["right_pinch_distance"]
                print(f"right_wrist={rw}  pinch={pinch:.4f}  indexTip(world)={data.right.indexTip[:3, 3]}")
            time.sleep(1 / 30)
    except KeyboardInterrupt:
        streamer.close()


if __name__ == "__main__":
    main()
