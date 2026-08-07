#!/usr/bin/env python3
"""Gradio UI for replaying Sparsh-Skin demonstration rosbags."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
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
    except Exception:
        candidate = Path.cwd() / "data" / "sparsh_skin_demonstrations"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _is_bag_dir(path: Path) -> bool:
    """Return True if ``path`` looks like a rosbag2 directory."""
    if not path.is_dir():
        return False
    return (path / "metadata.yaml").is_file() or any(path.glob("*.db3")) or any(
        path.glob("*.mcap")
    )


def _format_demo_label(session_name: str, meta: Dict[str, Any]) -> str:
    object_name = meta.get("object_name") or session_name
    mode = meta.get("mode", "?")
    started = meta.get("started_at", "")
    if started:
        return f"{session_name}  |  {object_name}  [{mode}]  {started}"
    return f"{session_name}  |  {object_name}  [{mode}]"


def _format_metadata(meta: Dict[str, Any], bag_uri: Path) -> str:
    topics = meta.get("topics") or []
    topics_str = "\n".join(f"  - {t}" for t in topics) if topics else "  (none)"
    lines = [
        f"Session: {bag_uri.parent.name}",
        f"Bag: {bag_uri}",
        f"Object name: {meta.get('object_name', '')}",
        f"Object count: {meta.get('object_count', '')}",
        f"Object shape: {meta.get('object_shape', '')}",
        f"Scale: {meta.get('scale', '')}",
        f"Mass (kg): {meta.get('mass', '')}",
        f"Size: {meta.get('size', '')}",
        f"Mode: {meta.get('mode', '')}",
        f"Started: {meta.get('started_at', '')}",
        f"Ended: {meta.get('ended_at', '')}",
        "Topics:",
        topics_str,
    ]
    return "\n".join(lines)


class SparshSkinReplay(Node):
    """ROS node that hosts a Gradio UI and plays demonstration rosbags."""

    def __init__(self) -> None:
        super().__init__("sparsh_skin_replay")

        self.declare_parameter("data_dir", str(_default_data_dir()))
        self.declare_parameter("server_name", "0.0.0.0")
        self.declare_parameter("server_port", 7861)

        data_dir_param = self.get_parameter("data_dir").get_parameter_value().string_value.strip()
        self._data_dir = Path(data_dir_param) if data_dir_param else _default_data_dir()
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._server_name = self.get_parameter("server_name").get_parameter_value().string_value
        self._server_port = int(self.get_parameter("server_port").get_parameter_value().integer_value)

        self._lock = threading.Lock()
        self._play_proc: Optional[subprocess.Popen] = None
        self._playing_uri: Optional[Path] = None
        # session_name -> {"bag_uri": Path, "meta": dict}
        self._demos: Dict[str, Dict[str, Any]] = {}

        self.get_logger().info(f"Listing demonstrations under: {self._data_dir}")
        self._build_and_launch_ui()

    def _scan_demonstrations(self) -> List[str]:
        """Refresh ``self._demos`` and return sorted session labels for the dropdown."""
        demos: Dict[str, Dict[str, Any]] = {}
        if not self._data_dir.is_dir():
            self._demos = demos
            return []

        for session_dir in sorted(self._data_dir.iterdir(), reverse=True):
            if not session_dir.is_dir():
                continue

            meta_path = session_dir / "metadata.json"
            bag_uri = session_dir / "rosbag"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    self.get_logger().warning(f"Skipping {session_dir.name}: {exc}")
                    continue
                bag_from_meta = meta.get("bag_uri")
                if bag_from_meta:
                    candidate = Path(bag_from_meta)
                    if _is_bag_dir(candidate):
                        bag_uri = candidate
            else:
                meta = {"object_name": session_dir.name}

            if not _is_bag_dir(bag_uri):
                # Fallback: any rosbag2-looking subdirectory.
                found = next(
                    (p for p in session_dir.iterdir() if p.is_dir() and _is_bag_dir(p)),
                    None,
                )
                if found is None:
                    continue
                bag_uri = found

            demos[session_dir.name] = {"bag_uri": bag_uri, "meta": meta}

        self._demos = demos
        return [_format_demo_label(name, info["meta"]) for name, info in demos.items()]

    def _label_to_session(self, label: str) -> Optional[str]:
        if not label:
            return None
        # Labels are ``{session_name}  |  ...``; session names have no `` | ``.
        session = label.split("  |  ", 1)[0].strip()
        if session in self._demos:
            return session
        # Exact match fallback if choices were raw session names.
        if label in self._demos:
            return label
        return None

    def _build_and_launch_ui(self) -> None:
        choices = self._scan_demonstrations()
        initial = choices[0] if choices else None
        initial_details = ""
        if initial is not None:
            session = self._label_to_session(initial)
            if session is not None:
                info = self._demos[session]
                initial_details = _format_metadata(info["meta"], info["bag_uri"])

        with gr.Blocks(title="Sparsh-Skin Replay") as demo:
            gr.Markdown("## Sparsh-Skin Demonstration Replay")
            gr.Markdown(
                "Select a collected demonstration, then press **Play** to replay its rosbag. "
                "Press **Stop** to interrupt playback."
            )

            with gr.Row():
                demo_dd = gr.Dropdown(
                    label="Demonstrations",
                    choices=choices,
                    value=initial,
                    interactive=True,
                )
                refresh_btn = gr.Button("Refresh", variant="secondary")

            details = gr.Textbox(
                label="Metadata",
                value=initial_details,
                interactive=False,
                lines=14,
            )

            with gr.Row():
                play_btn = gr.Button("Play", variant="primary")
                stop_btn = gr.Button("Stop", variant="stop")

            status = gr.Textbox(
                label="Status",
                value="Idle" if choices else f"No demonstrations found in {self._data_dir}",
                interactive=False,
            )

            refresh_btn.click(
                fn=self._on_refresh,
                inputs=[],
                outputs=[demo_dd, details, status],
            )
            demo_dd.change(
                fn=self._on_select,
                inputs=[demo_dd],
                outputs=[details, status],
            )
            play_btn.click(
                fn=self._on_play,
                inputs=[demo_dd],
                outputs=[status],
            )
            stop_btn.click(
                fn=self._on_stop,
                inputs=[],
                outputs=[status],
            )

        demo.launch(
            server_name=self._server_name,
            server_port=self._server_port,
            prevent_thread_lock=False,
        )

    def _on_refresh(self) -> Tuple[Any, str, str]:
        with self._lock:
            choices = self._scan_demonstrations()
            if not choices:
                return (
                    gr.update(choices=[], value=None),
                    "",
                    f"No demonstrations found in {self._data_dir}",
                )
            selected = choices[0]
            session = self._label_to_session(selected)
            details = ""
            if session is not None:
                info = self._demos[session]
                details = _format_metadata(info["meta"], info["bag_uri"])
            return (
                gr.update(choices=choices, value=selected),
                details,
                f"Found {len(choices)} demonstration(s).",
            )

    def _on_select(self, label: str) -> Tuple[str, str]:
        with self._lock:
            session = self._label_to_session(label)
            if session is None:
                return "", "Select a demonstration."
            info = self._demos[session]
            return (
                _format_metadata(info["meta"], info["bag_uri"]),
                f"Selected: {session}",
            )

    def _on_play(self, label: str) -> str:
        with self._lock:
            if self._play_proc is not None and self._play_proc.poll() is None:
                return f"Already playing: {self._playing_uri}"

            session = self._label_to_session(label)
            if session is None or session not in self._demos:
                return "Select a valid demonstration before playing."

            bag_uri: Path = self._demos[session]["bag_uri"]
            if not _is_bag_dir(bag_uri):
                return f"Bag not found or invalid: {bag_uri}"

            cmd = ["ros2", "bag", "play", str(bag_uri)]
            self.get_logger().info(f"Playing rosbag: {' '.join(cmd)}")
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid,
                    text=True,
                )
            except OSError as exc:
                return f"Failed to start playback: {exc}"

            self._play_proc = proc
            self._playing_uri = bag_uri
            return f"Playing → {bag_uri}"

    def _on_stop(self) -> str:
        with self._lock:
            return self._stop_playback()

    def _stop_playback(self) -> str:
        uri = self._playing_uri
        if self._play_proc is None:
            return "Idle (nothing playing)."

        err: Optional[str] = None
        if self._play_proc.poll() is None:
            try:
                os.killpg(os.getpgid(self._play_proc.pid), signal.SIGINT)
                self._play_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.get_logger().warning("rosbag play did not exit after SIGINT; killing.")
                try:
                    os.killpg(os.getpgid(self._play_proc.pid), signal.SIGKILL)
                    self._play_proc.wait(timeout=5)
                except Exception as exc:  # noqa: BLE001
                    err = f"Forced kill failed: {exc}"
            except Exception as exc:  # noqa: BLE001
                err = f"Error stopping playback: {exc}"

        self._play_proc = None
        self._playing_uri = None

        if err:
            status = f"Stopped with errors ({uri}): {err}"
            self.get_logger().error(status)
            return status

        status = f"Playback stopped ({uri})." if uri else "Playback stopped."
        self.get_logger().info(status)
        return status

    def shutdown(self) -> None:
        with self._lock:
            if self._play_proc is not None:
                self._stop_playback()


def main(args: Optional[List[str]] = None) -> None:
    rclpy.init(args=args)
    node: Optional[SparshSkinReplay] = None
    try:
        node = SparshSkinReplay()
    finally:
        if node is not None:
            node.shutdown()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
