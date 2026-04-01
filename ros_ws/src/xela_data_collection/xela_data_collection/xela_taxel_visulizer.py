#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from xela_server_ros2.msg import SensStream

import numpy as np
import threading
from collections import deque

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class LiveTexelHistogram:
    def __init__(
        self,
        window_size: int = 300,
        bins: int = 30,
        texel_num: int = 0,
        sensor_index: int = 0,
    ) -> None:
        # window_size/bins kept for backward compatibility with earlier versions,
        # but this visualizer shows the *latest* x/y/z values (not a histogram).
        self.window_size = int(window_size)
        self.bins = int(bins)
        self.texel_num = int(texel_num)
        self.sensor_index = int(sensor_index)

        self._lock = threading.Lock()
        self._x = deque(maxlen=self.window_size)
        self._y = deque(maxlen=self.window_size)
        self._z = deque(maxlen=self.window_size)
        self._latest = (0.0, 0.0, 0.0)

        self._fig, self._ax = plt.subplots(1, 1, figsize=(10, 6))
        try:
            self._fig.canvas.manager.set_window_title("XELA live texel values (x/y/z)")
        except Exception:
            pass

        self._bars = None
        self._value_text = {"x": None, "y": None, "z": None}
        self._setup_axes()

    def _setup_axes(self) -> None:
        self._ax.set_title(f"Current x/y/z values (sensor={self.sensor_index}, texel={self.texel_num})")
        self._ax.set_xlabel("axis")
        self._ax.set_ylabel("value")
        self._ax.grid(True, alpha=0.25)
        self._ax.set_xticks([0, 1, 2], labels=["X", "Y", "Z"])

    def push_sample(self, x: float, y: float, z: float) -> None:
        with self._lock:
            self._x.append(float(x))
            self._y.append(float(y))
            self._z.append(float(z))
            self._latest = (float(x), float(y), float(z))

    def _get_buffers(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        with self._lock:
            x = np.asarray(self._x, dtype=float)
            y = np.asarray(self._y, dtype=float)
            z = np.asarray(self._z, dtype=float)
        return x, y, z

    def _get_latest(self) -> tuple[float, float, float]:
        with self._lock:
            return self._latest

    def _init_bars(self) -> list:
        xs = np.array([0, 1, 2], dtype=float)
        heights = np.zeros_like(xs)
        self._bars = self._ax.bar(xs, heights, color=["tab:blue", "tab:orange", "tab:green"], alpha=0.85)
        self._value_text["x"] = self._ax.text(0, 0, "", ha="center", va="bottom")
        self._value_text["y"] = self._ax.text(1, 0, "", ha="center", va="bottom")
        self._value_text["z"] = self._ax.text(2, 0, "", ha="center", va="bottom")
        return list(self._bars) + list(self._value_text.values())

    def _animate(self, _frame_idx: int):
        xv, yv, zv = self._get_latest()
        vals = [xv, yv, zv]

        if self._bars is None:
            artists = self._init_bars()
        else:
            artists = list(self._bars) + list(self._value_text.values())

        for rect, v in zip(self._bars, vals):
            rect.set_height(float(v))

        ymax = max(1.0, float(max(vals)))
        ymin = float(min(vals))
        if ymin >= 0:
            self._ax.set_ylim(0.0, ymax * 1.15)
        else:
            # Include negative values if they occur.
            self._ax.set_ylim(ymin * 1.15, ymax * 1.15)

        # Value labels above each bar
        for i, key in enumerate(["x", "y", "z"]):
            v = float(vals[i])
            self._value_text[key].set_position((i, v))
            self._value_text[key].set_text(f"{v:.3f}")

        return artists

    def start(self, interval_ms: int = 100) -> FuncAnimation:
        return FuncAnimation(self._fig, self._animate, interval=int(interval_ms), blit=False)

class XelaServTopicSubscriber(Node):
    def __init__(self, visualizer: LiveTexelHistogram) -> None:
        super().__init__("xela_servtopic_subscriber")
        self._viz = visualizer
        self._sub = self.create_subscription(
            SensStream,
            "/xServTopic",
            self._on_stream,
            10,
        )

    def _on_stream(self, msg: SensStream) -> None:
        si = self._viz.sensor_index
        tn = self._viz.texel_num
        try:
            taxel = msg.sensors[si].taxels[tn]
        except Exception as e:
            self.get_logger().warn(f"Could not read sensors[{si}].taxels[{tn}]: {e}")
            return

        self._viz.push_sample(taxel.x, taxel.y, taxel.z)


def main(args=None) -> None:
    rclpy.init(args=args)
    # texel 0 to 3 belong to first row of fingertip for thumb
    # texel 4 to 8 belong to second row of fingertip for thumb
    # texel 9 to 12 belong to first row of second sensor from top for thumb
    # texel 13 to 16 belong to first row of Third sensor from top for thumb
    # texel 17 to 22 belong to third row of fingertip for thumb

    viz = LiveTexelHistogram(window_size=300, bins=30, texel_num=62, sensor_index=0)
    node = XelaServTopicSubscriber(viz)

    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    stop_event = threading.Event()

    def spin() -> None:
        while rclpy.ok() and not stop_event.is_set():
            executor.spin_once(timeout_sec=0.1)

    spin_thread = threading.Thread(target=spin, daemon=True)
    spin_thread.start()

    anim = viz.start(interval_ms=100)
    _ = anim  # keep reference alive
    try:
        plt.show()
    
    finally:
        stop_event.set()
        try:
            executor.remove_node(node)
        except Exception:
            pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

