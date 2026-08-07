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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import rclpy
from rclpy.node import Node


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


# Topic presets for each collection mode.
TOPIC_PRESETS: Dict[str, List[str]] = {
    "sim": [
        "/hand_sensors",
        "/xela_joint_publisher",
    ],
    "real": [
        "/xServTopic",
        "/leap_state",
    ],
}


def _format_topics(topics: List[str]) -> str:
    return "\n".join(topics) if topics else "(none)"


def _topics_for_mode(mode: str) -> List[str]:
    key = (mode or "sim").strip().lower()
    if key not in TOPIC_PRESETS:
        key = "sim"
    return list(TOPIC_PRESETS[key])


class SparshSkinDemonstration(Node):
    """ROS node that hosts a Gradio UI and manages rosbag recording."""

    def __init__(self) -> None:
        super().__init__("sparsh_skin_demonstration")

        self.declare_parameter("data_dir", str(_default_data_dir()))
        self.declare_parameter("server_name", "0.0.0.0")
        self.declare_parameter("server_port", 7860)
        self.declare_parameter("mode", "sim")  # "sim" | "real"

        self._data_dir = Path(self.get_parameter("data_dir").get_parameter_value().string_value)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._server_name = self.get_parameter("server_name").get_parameter_value().string_value
        self._server_port = int(self.get_parameter("server_port").get_parameter_value().integer_value)

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

        self.get_logger().info(
            f"Mode={self._mode}, topics={self._topics}, bags under: {self._data_dir}"
        )
        self._build_and_launch_ui()

    def _build_and_launch_ui(self) -> None:
        with gr.Blocks(title="Sparsh-Skin Demonstration") as demo:
            gr.Markdown("## Sparsh-Skin Demonstration Collector")
            gr.Markdown(
                "Fill in object metadata, then press **Start** to begin rosbag recording. "
                "Press **End** to stop and finalize the bag."
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

            with gr.Row():
                object_name = gr.Textbox(label="Object name", value="", placeholder="e.g. ball")
                object_count = gr.Number(label="Object count", value=1, precision=0, minimum=1)
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

            record_btn = gr.Button("Start", variant="primary")
            status = gr.Textbox(label="Status", value="Idle", interactive=False)

            form_inputs = [object_name, object_count, object_shape, scale, mass, size]

            mode_dd.change(
                fn=self._on_mode_change,
                inputs=[mode_dd],
                outputs=[mode_dd, topics_box, status],
            )

            record_btn.click(
                fn=self._on_toggle_recording,
                inputs=[mode_dd, *form_inputs],
                outputs=[record_btn, status, mode_dd, topics_box, *form_inputs],
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
                    "Cannot change mode while recording.",
                )
            self._mode = (mode or "sim").strip().lower()
            if self._mode not in TOPIC_PRESETS:
                self._mode = "sim"
            self._topics = _topics_for_mode(self._mode)
            self.get_logger().info(f"Mode set to {self._mode}, topics={self._topics}")
            return (
                gr.update(value=self._mode),
                _format_topics(self._topics),
                f"Mode: {self._mode}",
            )

    def _on_toggle_recording(
        self,
        mode: str,
        object_name: str,
        object_count: float,
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
                    object_name=object_name,
                    object_count=object_count,
                    object_shape=object_shape,
                    scale=scale,
                    mass=mass,
                    size=size,
                )
            return self._stop_recording()

    def _start_recording(
        self,
        object_name: str,
        object_count: float,
        object_shape: str,
        scale: float,
        mass: float,
        size: str,
    ) -> Tuple[Any, ...]:
        name = (object_name or "").strip()
        values = (object_name, object_count, object_shape, scale, mass, size)
        if not name:
            return self._ui_state(
                button_label="Start",
                status="Object name is required before starting.",
                recording=False,
                values=values,
            )

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = _sanitize_name(name)
        session_dir = self._data_dir / f"{safe_name}_{stamp}"
        session_dir.mkdir(parents=True, exist_ok=True)
        bag_uri = session_dir / "rosbag"

        topics = list(self._topics)
        meta: Dict[str, Any] = {
            "object_name": name,
            "object_count": int(object_count) if object_count is not None else 1,
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
        self._recording = True

        return self._ui_state(
            button_label="End",
            status=f"Recording [{self._mode}] → {bag_uri}",
            recording=True,
            values=values,
        )

    def _stop_recording(self) -> Tuple[Any, ...]:
        bag_uri = self._bag_uri
        meta = self._session_meta or {}
        values = (
            meta.get("object_name", ""),
            meta.get("object_count", 1),
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
            meta_path = Path(bag_uri).parent / "metadata.json"
            try:
                meta_path.write_text(
                    json.dumps(self._session_meta, indent=2) + "\n",
                    encoding="utf-8",
                )
            except OSError as exc:
                err = (err + "; " if err else "") + f"metadata update failed: {exc}"

        self._recording = False
        self._bag_uri = None
        self._session_meta = None

        if err:
            status = f"Stopped with errors ({bag_uri}): {err}"
            self.get_logger().error(status)
        else:
            status = f"Recording stopped. Bag saved at: {bag_uri}"
            self.get_logger().info(status)

        return self._ui_state(
            button_label="Start",
            status=status,
            recording=False,
            values=values,
        )

    def _ui_state(
        self,
        button_label: str,
        status: str,
        recording: bool,
        values: Tuple[Any, ...],
    ) -> Tuple[Any, ...]:
        """Return Gradio updates: [button, status, mode, topics, ...form fields]."""
        interactive = not recording
        object_name, object_count, object_shape, scale, mass, size = values
        return (
            gr.update(value=button_label, variant="stop" if recording else "primary"),
            status,
            gr.update(value=self._mode, interactive=interactive),
            _format_topics(self._topics),
            gr.update(value=object_name, interactive=interactive),
            gr.update(value=object_count, interactive=interactive),
            gr.update(value=object_shape, interactive=interactive),
            gr.update(value=scale, interactive=interactive),
            gr.update(value=mass, interactive=interactive),
            gr.update(value=size, interactive=interactive),
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
