#!/usr/bin/env python3
"""Gradio UI for Sparsh-Skin demonstration data collection.

Collects object metadata and toggles rosbag recording via a Start/End button.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple, Type

import gradio as gr
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

try:
    from rosidl_runtime_py.utilities import get_message
except ImportError:  # pragma: no cover
    get_message = None  # type: ignore[misc, assignment]

try:
    from xela_server_ros2.msg import SensStream
except ImportError:  # pragma: no cover - optional until workspace is sourced
    SensStream = None  # type: ignore[misc, assignment]

try:
    from xela_sparshskin_sim.msg import HandSensors
except ImportError:  # pragma: no cover - optional until workspace is sourced
    HandSensors = None  # type: ignore[misc, assignment]


def _default_data_dir() -> Path:
    """Prefer ``ros_ws/data/sparsh_skin_demonstrations``, else ``cwd/data/...``."""
    here = Path(__file__).resolve()
    try:
        # .../ros_ws/src/sparse_skin/xela_sparshskin/<pkg>/<pkg>/this.py
        ros_ws = here.parents[5]
        candidate = ros_ws / "data" / "sparsh_skin_demonstrations"
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except Exception:
        pass
    fallback = Path.cwd() / "data" / "sparsh_skin_demonstrations"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _sanitize_name(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name.strip())
    return cleaned or "object"


# Relative path under data_dir. Placeholders: {object_name}, {object_count}, {rollout}.
DEFAULT_NAMING_TEMPLATE = "{object_name}/{object_count}/{rollout}"


def _normalize_template(template: str) -> str:
    text = (template or "").strip().replace("\\", "/")
    return text.strip("/") or DEFAULT_NAMING_TEMPLATE


def _format_session_relpath(
    template: str,
    object_name: str,
    object_count: int,
    rollout: int,
) -> str:
    """Expand the naming template into a relative session path."""
    safe_name = _sanitize_name(object_name)
    count = int(object_count)
    roll = int(rollout)
    try:
        rel = _normalize_template(template).format(
            object_name=safe_name,
            object_count=count,
            rollout=roll,
        )
    except (KeyError, ValueError, IndexError):
        rel = DEFAULT_NAMING_TEMPLATE.format(
            object_name=safe_name,
            object_count=count,
            rollout=roll,
        )
    # Keep the path strictly under data_dir (no ``..`` segments).
    parts = [p for p in Path(rel).parts if p not in ("", ".", "..")]
    return str(Path(*parts)) if parts else safe_name


def _next_rollout(data_dir: Path, object_name: str, object_count: int) -> int:
    """Return the next free rollout index under ``object_name/object_count/``."""
    parent = data_dir / _sanitize_name(object_name) / str(int(object_count))
    if not parent.is_dir():
        return 0
    max_roll = -1
    for child in parent.iterdir():
        if child.is_dir() and child.name.isdigit():
            max_roll = max(max_roll, int(child.name))
    return max_roll + 1


# Topic presets for each collection mode.
TOPIC_PRESETS: Dict[str, List[str]] = {
    "sim": [
        "/hand_sensors",
        "/xela_joint_publisher",
    ],
    "hardware": [
        "/cmd_xela",
        "/leap_state",
        "/oculus_teleop_joint_commands",
        "/xServTopic",
    ],
}

# Primary XELA sample stream (used for summary / metadata).
XELA_SAMPLE_TOPICS: Dict[str, str] = {
    "sim": "/hand_sensors",
    "hardware": "/xServTopic",
}

# Known message types for preset topics (used when the graph has no publisher yet).
_KNOWN_TOPIC_TYPES: Dict[str, Optional[Type[Any]]] = {
    "/hand_sensors": HandSensors,
    "/xela_joint_publisher": JointState,
    "/cmd_xela": JointState,
    "/leap_state": JointState,
    "/oculus_teleop_joint_commands": JointState,
    "/xServTopic": SensStream,
}

_HZ_WINDOW_S = 1.0


def _format_topics(topics: List[str]) -> str:
    return "\n".join(topics) if topics else "(none)"


def _format_elapsed(seconds: float) -> str:
    """Format elapsed seconds as ``HH:MM:SS``."""
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _topics_for_mode(mode: str) -> List[str]:
    key = (mode or "sim").strip().lower()
    if key not in TOPIC_PRESETS:
        key = "sim"
    return list(TOPIC_PRESETS[key])


def _xela_topic_for_mode(mode: str) -> str:
    key = (mode or "sim").strip().lower()
    return XELA_SAMPLE_TOPICS.get(key, XELA_SAMPLE_TOPICS["sim"])


def _format_hz(hz: float) -> str:
    if hz <= 0.0:
        return "-- Hz"
    return f"{hz:6.1f} Hz"


def _hz_from_times(times: List[float]) -> float:
    if len(times) < 2:
        return 0.0
    dt = times[-1] - times[0]
    if dt <= 1e-6:
        return 0.0
    return (len(times) - 1) / dt


def _normalize_topic(topic: str) -> str:
    text = (topic or "").strip()
    if not text:
        return text
    return text if text.startswith("/") else f"/{text}"


class SparshSkinDemonstration(Node):
    """ROS node that hosts a Gradio UI and manages rosbag recording."""

    def __init__(self) -> None:
        super().__init__("sparsh_skin_demonstration")

        self.declare_parameter("data_dir", str(_default_data_dir()))
        self.declare_parameter("server_name", "0.0.0.0")
        self.declare_parameter("server_port", 7860)
        self.declare_parameter("mode", "sim")  # "sim" | "hardware"
        self.declare_parameter("naming_template", DEFAULT_NAMING_TEMPLATE)

        self._data_dir = Path(self.get_parameter("data_dir").get_parameter_value().string_value)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._server_name = self.get_parameter("server_name").get_parameter_value().string_value
        self._server_port = int(self.get_parameter("server_port").get_parameter_value().integer_value)
        self._naming_template = _normalize_template(
            self.get_parameter("naming_template").get_parameter_value().string_value
        )

        mode = self.get_parameter("mode").get_parameter_value().string_value.strip().lower()
        if mode not in TOPIC_PRESETS:
            self.get_logger().warning(f"Unknown mode '{mode}', defaulting to 'sim'")
            mode = "sim"
        self._mode = mode
        self._topics = _topics_for_mode(self._mode)

        self._lock = threading.Lock()
        self._recording = False
        self._bag_proc: Optional[subprocess.Popen] = None
        self._bag_uri: Optional[Path] = None
        self._session_meta: Optional[Dict[str, Any]] = None
        self._record_t0: Optional[float] = None

        self._stats_lock = threading.Lock()
        self._topic_subs: Dict[str, Any] = {}
        self._topic_times: Dict[str, Deque[float]] = {}
        self._topic_samples: Dict[str, int] = {}
        self._xela_topic: str = _xela_topic_for_mode(self._mode)
        self._last_elapsed_str: str = "00:00:00"

        self._setup_topic_monitors(self._topics)
        self._spin_thread = threading.Thread(target=self._spin_ros, daemon=True)
        self._spin_thread.start()

        self.get_logger().info(
            f"Mode={self._mode}, topics={self._topics}, "
            f"xela_monitor={self._xela_topic}, bags under: {self._data_dir}"
        )
        self._build_and_launch_ui()

    def _spin_ros(self) -> None:
        try:
            rclpy.spin(self)
        except Exception:  # noqa: BLE001
            pass

    def _resolve_msg_type(self, topic: str) -> Optional[Type[Any]]:
        """Resolve a topic's message type from the graph, then known presets."""
        topic = _normalize_topic(topic)
        try:
            names_and_types = dict(self.get_topic_names_and_types())
        except Exception:  # noqa: BLE001
            names_and_types = {}
        for candidate in (topic, topic.lstrip("/"), f"/{topic.lstrip('/')}"):
            type_list = names_and_types.get(candidate) or []
            if type_list and get_message is not None:
                try:
                    return get_message(type_list[0])
                except Exception:  # noqa: BLE001
                    pass
        return _KNOWN_TOPIC_TYPES.get(topic)

    def _clear_topic_monitors(self) -> None:
        for sub in list(self._topic_subs.values()):
            try:
                self.destroy_subscription(sub)
            except Exception:  # noqa: BLE001
                pass
        self._topic_subs.clear()
        with self._stats_lock:
            self._topic_times.clear()
            self._topic_samples.clear()

    def _setup_topic_monitors(self, topics: List[str]) -> None:
        """Subscribe to every bag topic to measure live Hz / sample counts."""
        self._clear_topic_monitors()
        self._xela_topic = _xela_topic_for_mode(self._mode)
        for raw in topics:
            topic = _normalize_topic(raw)
            msg_type = self._resolve_msg_type(topic)
            with self._stats_lock:
                self._topic_times[topic] = deque()
                self._topic_samples[topic] = 0
            if msg_type is None:
                self.get_logger().warning(
                    f"No message type for {topic}; rate monitor skipped."
                )
                continue
            self._topic_subs[topic] = self.create_subscription(
                msg_type,
                topic,
                self._make_topic_callback(topic),
                50,
            )
            self.get_logger().info(f"Monitoring rate on {topic}")

    def _make_topic_callback(self, topic: str):
        def _cb(_msg: Any) -> None:
            now = time.monotonic()
            with self._stats_lock:
                times = self._topic_times.setdefault(topic, deque())
                times.append(now)
                cutoff = now - _HZ_WINDOW_S
                while times and times[0] < cutoff:
                    times.popleft()
                if self._recording:
                    self._topic_samples[topic] = self._topic_samples.get(topic, 0) + 1

        return _cb

    def _topic_stats_snapshot(self) -> Dict[str, Dict[str, float]]:
        """Return ``{topic: {hz, samples}}`` for currently monitored topics."""
        with self._stats_lock:
            topics = list(self._topic_times.keys()) or list(self._topics)
            samples = {t: int(self._topic_samples.get(t, 0)) for t in topics}
            times = {t: list(self._topic_times.get(t, ())) for t in topics}
        out: Dict[str, Dict[str, float]] = {}
        for topic in topics:
            out[topic] = {
                "hz": _hz_from_times(times.get(topic, [])),
                "samples": float(samples.get(topic, 0)),
            }
        return out

    def _format_topic_rates(self, *, include_samples: Optional[bool] = None) -> str:
        snap = self._topic_stats_snapshot()
        if include_samples is None:
            include_samples = self._recording or any(
                int(v.get("samples", 0)) > 0 for v in snap.values()
            )
        # Prefer the configured bag topic order.
        ordered = [_normalize_topic(t) for t in self._topics]
        for topic in snap:
            if topic not in ordered:
                ordered.append(topic)
        if not ordered:
            return "(no topics)"
        width = max(len(t) for t in ordered)
        lines: List[str] = []
        for topic in ordered:
            info = snap.get(topic, {"hz": 0.0, "samples": 0.0})
            hz = _format_hz(float(info["hz"]))
            if include_samples:
                n = int(info["samples"])
                lines.append(f"{topic:<{width}}  {hz}  n={n}")
            else:
                lines.append(f"{topic:<{width}}  {hz}")
        return "\n".join(lines)

    def _build_and_launch_ui(self) -> None:
        with gr.Blocks(title="Sparsh-Skin Demonstration") as demo:
            gr.Markdown("## Sparsh-Skin Demonstration Collector")
            gr.Markdown(
                "Fill in object metadata, then press **Start** to begin rosbag recording. "
                "Press **End** to stop and finalize the bag. "
                "Bags are stored as `{object_name}/{object_count}/{rollout}/` under the data directory."
            )

            with gr.Row():
                mode_dd = gr.Dropdown(
                    label="Mode",
                    choices=list(TOPIC_PRESETS.keys()),
                    value=self._mode,
                    interactive=True,
                )
                topics_box = gr.Textbox(
                    label="Topics listening to",
                    value=_format_topics(self._topics),
                    interactive=False,
                    lines=max(2, len(self._topics)),
                )

            naming_template = gr.Textbox(
                label="Naming template",
                value=self._naming_template,
                placeholder=DEFAULT_NAMING_TEMPLATE,
                info="Folder layout under the data dir. Placeholders: {object_name}, {object_count}, {rollout}.",
            )
            path_preview = gr.Textbox(
                label="Next save path",
                value="",
                interactive=False,
            )

            with gr.Row():
                object_name = gr.Textbox(label="Object name", value="", placeholder="e.g. ball")
                object_count = gr.Number(label="Object count", value=1, precision=0, minimum=1)
                rollout = gr.Number(
                    label="Rollout number",
                    value=0,
                    precision=0,
                    minimum=0,
                    info="Auto-filled from existing folders; override if needed.",
                )
            with gr.Row():
                object_shape = gr.Textbox(
                    label="Object shape",
                    value="",
                    placeholder="e.g. sphere, cylinder, box",
                )
                scale = gr.Number(label="Scale", value=1.0, precision=4)
            with gr.Row():
                mass = gr.Number(label="Mass (kg)", value=0.1, precision=4)
                size = gr.Textbox(
                    label="Size",
                    value="",
                    placeholder="e.g. 0.05 or 0.05,0.05,0.05",
                )

            with gr.Row():
                record_btn = gr.Button("Start", variant="primary")
                elapsed_box = gr.Textbox(
                    label="Elapsed",
                    value="00:00:00",
                    interactive=False,
                    scale=1,
                )
            topic_rates_box = gr.Textbox(
                label="Topic rates (live)",
                value=self._format_topic_rates(include_samples=False),
                interactive=False,
                lines=max(2, len(self._topics)),
                info="Live Hz per recorded topic. Sample counts (n=) accumulate while recording.",
            )
            status = gr.Textbox(label="Status", value="Idle", interactive=False)
            # Always-on: keep elapsed / per-topic Hz fresh in the UI.
            ui_timer = gr.Timer(value=0.25, active=True)

            form_inputs = [
                naming_template,
                object_name,
                object_count,
                rollout,
                object_shape,
                scale,
                mass,
                size,
            ]

            mode_dd.change(
                fn=self._on_mode_change,
                inputs=[mode_dd],
                outputs=[mode_dd, topics_box, topic_rates_box, status],
            )

            for trigger in (naming_template, object_name, object_count):
                trigger.change(
                    fn=self._on_path_fields_change,
                    inputs=[naming_template, object_name, object_count, rollout],
                    outputs=[rollout, path_preview],
                )
            rollout.change(
                fn=self._preview_path,
                inputs=[naming_template, object_name, object_count, rollout],
                outputs=[path_preview],
            )

            record_btn.click(
                fn=self._on_toggle_recording,
                inputs=[mode_dd, *form_inputs],
                outputs=[
                    record_btn,
                    status,
                    mode_dd,
                    topics_box,
                    path_preview,
                    *form_inputs,
                    elapsed_box,
                    topic_rates_box,
                ],
            )
            ui_timer.tick(
                fn=self._on_ui_tick,
                outputs=[elapsed_box, topic_rates_box],
                show_progress="hidden",
            )

        demo.launch(
            server_name=self._server_name,
            server_port=self._server_port,
            prevent_thread_lock=False,
        )

    def _on_mode_change(self, mode: str) -> Tuple[Any, ...]:
        with self._lock:
            if self._recording:
                return (
                    gr.update(value=self._mode),
                    _format_topics(self._topics),
                    gr.update(),
                    "Cannot change mode while recording.",
                )
            self._mode = (mode or "sim").strip().lower()
            if self._mode not in TOPIC_PRESETS:
                self._mode = "sim"
            self._topics = _topics_for_mode(self._mode)
            self._setup_topic_monitors(self._topics)
            self.get_logger().info(f"Mode set to {self._mode}, topics={self._topics}")
            return (
                gr.update(value=self._mode),
                _format_topics(self._topics),
                gr.update(
                    value=self._format_topic_rates(include_samples=False),
                    lines=max(2, len(self._topics)),
                ),
                f"Mode: {self._mode} (XELA: {self._xela_topic})",
            )

    def _preview_path(
        self,
        naming_template: str,
        object_name: str,
        object_count: float,
        rollout: float,
    ) -> str:
        name = (object_name or "").strip()
        if not name:
            return "(set object name)"
        count = int(object_count) if object_count is not None else 1
        roll = int(rollout) if rollout is not None else 0
        rel = _format_session_relpath(naming_template, name, count, roll)
        return str(self._data_dir / rel)

    def _on_path_fields_change(
        self,
        naming_template: str,
        object_name: str,
        object_count: float,
        rollout: float,
    ) -> Tuple[Any, str]:
        """Refresh rollout suggestion and path preview when name/count/template change."""
        with self._lock:
            if self._recording:
                name = (object_name or "").strip() or "object"
                count = int(object_count) if object_count is not None else 1
                roll = int(rollout) if rollout is not None else 0
                preview = str(
                    self._data_dir
                    / _format_session_relpath(naming_template, name, count, roll)
                )
                return gr.update(), preview

        name = (object_name or "").strip()
        count = int(object_count) if object_count is not None else 1
        if name:
            next_roll = _next_rollout(self._data_dir, name, count)
        else:
            next_roll = 0
        preview = self._preview_path(naming_template, name, count, next_roll)
        return gr.update(value=next_roll), preview

    def _elapsed_str(self) -> str:
        if self._record_t0 is None:
            return self._last_elapsed_str
        return _format_elapsed(time.monotonic() - self._record_t0)

    def _on_ui_tick(self) -> Tuple[str, str]:
        with self._lock:
            elapsed = self._elapsed_str()
            # Retry monitors for topics that had no type at startup.
            if not self._recording:
                missing = [
                    t
                    for t in (_normalize_topic(x) for x in self._topics)
                    if t not in self._topic_subs
                ]
                if missing:
                    self._setup_topic_monitors(self._topics)
        return elapsed, self._format_topic_rates()

    def _on_toggle_recording(
        self,
        mode: str,
        naming_template: str,
        object_name: str,
        object_count: float,
        rollout: float,
        object_shape: str,
        scale: float,
        mass: float,
        size: str,
    ) -> Tuple[Any, ...]:
        with self._lock:
            if not self._recording:
                # Sync topics from the UI mode before starting.
                self._mode = (mode or self._mode).strip().lower()
                if self._mode not in TOPIC_PRESETS:
                    self._mode = "sim"
                self._topics = _topics_for_mode(self._mode)
                return self._start_recording(
                    naming_template=naming_template,
                    object_name=object_name,
                    object_count=object_count,
                    rollout=rollout,
                    object_shape=object_shape,
                    scale=scale,
                    mass=mass,
                    size=size,
                )
            return self._stop_recording()

    def _start_recording(
        self,
        naming_template: str,
        object_name: str,
        object_count: float,
        rollout: float,
        object_shape: str,
        scale: float,
        mass: float,
        size: str,
    ) -> Tuple[Any, ...]:
        name = (object_name or "").strip()
        template = _normalize_template(naming_template)
        count = int(object_count) if object_count is not None else 1
        roll = int(rollout) if rollout is not None else 0
        values = (template, object_name, count, roll, object_shape, scale, mass, size)
        if not name:
            return self._ui_state(
                button_label="Start",
                status="Object name is required before starting.",
                recording=False,
                values=values,
            )

        # Prefer the next free index if the chosen rollout folder already exists.
        if roll < 0:
            roll = 0
        rel = _format_session_relpath(template, name, count, roll)
        session_dir = self._data_dir / rel
        if session_dir.exists():
            roll = _next_rollout(self._data_dir, name, count)
            rel = _format_session_relpath(template, name, count, roll)
            session_dir = self._data_dir / rel
            values = (template, object_name, count, roll, object_shape, scale, mass, size)

        session_dir.mkdir(parents=True, exist_ok=True)
        bag_uri = session_dir / "rosbag"

        topics = list(self._topics)
        meta: Dict[str, Any] = {
            "object_name": name,
            "object_count": count,
            "rollout": roll,
            "naming_template": template,
            "session_relpath": rel,
            "object_shape": (object_shape or "").strip(),
            "scale": float(scale) if scale is not None else 1.0,
            "mass": float(mass) if mass is not None else 0.0,
            "size": (size or "").strip(),
            "mode": self._mode,
            "topics": topics,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "bag_uri": str(bag_uri),
        }

        meta_path = session_dir / "metadata.json"
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

        cmd: List[str] = ["ros2", "bag", "record", "-o", str(bag_uri), *topics]

        self.get_logger().info(f"Starting rosbag: {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
                text=True,
            )
        except OSError as exc:
            return self._ui_state(
                button_label="Start",
                status=f"Failed to start rosbag: {exc}",
                recording=False,
                values=values,
            )

        self._bag_proc = proc
        self._bag_uri = bag_uri
        self._session_meta = meta
        self._naming_template = template
        # Ensure monitors cover the topics we are about to record.
        self._setup_topic_monitors(topics)
        self._last_elapsed_str = "00:00:00"
        self._record_t0 = time.monotonic()
        self._recording = True

        return self._ui_state(
            button_label="End",
            status=f"Recording [{self._mode}] → {bag_uri}",
            recording=True,
            values=values,
            elapsed="00:00:00",
        )

    def _stop_recording(self) -> Tuple[Any, ...]:
        bag_uri = self._bag_uri
        meta = self._session_meta or {}
        name = meta.get("object_name", "")
        count = int(meta.get("object_count", 1) or 1)
        template = _normalize_template(meta.get("naming_template", self._naming_template))
        elapsed = self._elapsed_str()
        topic_stats = self._topic_stats_snapshot()
        xela_samples = int(topic_stats.get(self._xela_topic, {}).get("samples", 0))
        xela_hz = float(topic_stats.get(self._xela_topic, {}).get("hz", 0.0))
        # Advance to the next free rollout for the following take.
        next_roll = _next_rollout(self._data_dir, name, count) if name else 0
        values = (
            template,
            name,
            count,
            next_roll,
            meta.get("object_shape", ""),
            meta.get("scale", 1.0),
            meta.get("mass", 0.0),
            meta.get("size", ""),
        )

        err: Optional[str] = None
        if self._bag_proc is not None:
            try:
                os.killpg(os.getpgid(self._bag_proc.pid), signal.SIGINT)
                self._bag_proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.get_logger().warning("rosbag did not exit after SIGINT; killing.")
                try:
                    os.killpg(os.getpgid(self._bag_proc.pid), signal.SIGKILL)
                    self._bag_proc.wait(timeout=5)
                except Exception as exc:  # noqa: BLE001
                    err = f"Forced kill failed: {exc}"
            except Exception as exc:  # noqa: BLE001
                err = f"Error stopping rosbag: {exc}"
            finally:
                self._bag_proc = None

        if self._session_meta is not None and bag_uri is not None:
            self._session_meta["ended_at"] = datetime.now().isoformat(timespec="seconds")
            self._session_meta["elapsed_s"] = (
                round(time.monotonic() - self._record_t0, 3)
                if self._record_t0 is not None
                else None
            )
            self._session_meta["xela_topic"] = self._xela_topic
            self._session_meta["xela_samples"] = int(xela_samples)
            self._session_meta["xela_hz_end"] = round(float(xela_hz), 2)
            self._session_meta["topic_stats"] = {
                topic: {
                    "hz": round(float(info["hz"]), 2),
                    "samples": int(info["samples"]),
                }
                for topic, info in topic_stats.items()
            }
            meta_path = Path(bag_uri).parent / "metadata.json"
            try:
                meta_path.write_text(
                    json.dumps(self._session_meta, indent=2) + "\n",
                    encoding="utf-8",
                )
            except OSError as exc:
                err = (err + "; " if err else "") + f"metadata update failed: {exc}"

        self._recording = False
        self._last_elapsed_str = elapsed
        self._record_t0 = None
        self._bag_uri = None
        self._session_meta = None

        if err:
            status = f"Stopped with errors ({bag_uri}): {err}"
            self.get_logger().error(status)
        else:
            status = (
                f"Recording stopped ({elapsed}, {xela_samples} XELA samples "
                f"@ {_format_hz(xela_hz).strip()}). Bag saved at: {bag_uri}"
            )
            self.get_logger().info(status)

        return self._ui_state(
            button_label="Start",
            status=status,
            recording=False,
            values=values,
            elapsed=elapsed,
        )

    def _ui_state(
        self,
        button_label: str,
        status: str,
        recording: bool,
        values: Tuple[Any, ...],
        elapsed: Optional[str] = None,
    ) -> Tuple[Any, ...]:
        """Return Gradio updates: [button, status, mode, topics, preview, ...form, elapsed, rates]."""
        interactive = not recording
        naming_template, object_name, object_count, rollout, object_shape, scale, mass, size = values
        preview = self._preview_path(naming_template, object_name, object_count, rollout)
        if elapsed is None:
            elapsed = self._elapsed_str()
        rates = self._format_topic_rates(include_samples=True)
        return (
            gr.update(value=button_label, variant="stop" if recording else "primary"),
            status,
            gr.update(value=self._mode, interactive=interactive),
            _format_topics(self._topics),
            preview,
            gr.update(value=naming_template, interactive=interactive),
            gr.update(value=object_name, interactive=interactive),
            gr.update(value=object_count, interactive=interactive),
            gr.update(value=rollout, interactive=interactive),
            gr.update(value=object_shape, interactive=interactive),
            gr.update(value=scale, interactive=interactive),
            gr.update(value=mass, interactive=interactive),
            gr.update(value=size, interactive=interactive),
            elapsed,
            rates,
        )

    def shutdown(self) -> None:
        with self._lock:
            if self._recording:
                self._stop_recording()


def main(args: Optional[List[str]] = None) -> None:
    rclpy.init(args=args)
    node: Optional[SparshSkinDemonstration] = None
    try:
        node = SparshSkinDemonstration()
    finally:
        if node is not None:
            node.shutdown()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
