#!/usr/bin/env python3
"""The Sparsh-skin play policy on the real hand: ``play_policy_node``.

Service ``~/sample`` (leapxela_sparshskin_msgs/SamplePlayChunk): one action chunk of a play policy
trained with ``python -m play_policy.train --dataset leap_sparsh`` (the play_policy repo), from
the hand's newest state:

  newest /xServTopic reading (368 x 3 raw, hardware ids) + newest leap_state (hardware joints)
    -> sparsh_processing.live_obs: the Sparsh-skin step exactly as the training episodes have it
       (outliers 0, the baseline subtracted, FK order; FK taxel positions)   (368, 6)
    -> the policy's SkinEncoder + DiT, sampled with (eta, init_noise_scale)
    -> (horizon, 16) sim joint angles (rad), the checkpoint's joint order (LEAP_JOINT_ORDER)

The chunk goes back to the caller (record_demonstration's Self-play tab), which converts it to
hardware angles, applies the safety limits and streams it; this node never commands the hand.
Torch stays in this process, out of the GUI. A request is refused when either stream was older
than ``max_obs_age_s`` when it came. The default checkpoint is loaded at start; another one is
loaded at its first request, whose state is then as old as the load took.

ROS parameters:
  - checkpoint (str): default checkpoint; empty: the newest ``ckpt_best.pt`` under
    ``<play_policy_dir>/runs/play_policy`` trained on leap_sparsh
  - play_policy_dir (str, default <ws>/play_policy): the play_policy repo (imported from there)
  - device (str, default cuda; cpu when no GPU)
  - xela_topic (str, /xServTopic), state_topic (str, leap_state)
  - max_obs_age_s (float, 0.3)
"""

from __future__ import annotations

import glob
import os
import sys
import threading
import time
import traceback

import numpy as np
import rclpy
from leapxela_sparshskin_msgs.srv import SamplePlayChunk
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import JointState

from mechanical_pen_data_collection import sparsh_processing
from mechanical_pen_data_collection.joint_conversion import HardwareToSim
from mechanical_pen_data_collection.label_playbacks import default_demo_dir


def default_play_policy_dir() -> str:
    """``<ws>/play_policy``: next to ``ros_ws`` (``<ws>/ros_ws/demonstrations`` is the demo dir)."""
    return os.path.join(os.path.dirname(os.path.dirname(default_demo_dir())), "play_policy")


def newest_checkpoint(play_policy_dir: str) -> str:
    runs = sorted(glob.glob(os.path.join(play_policy_dir, "runs", "play_policy", "*", "ckpt_best.pt")),
                  key=os.path.getmtime, reverse=True)
    for path in runs:
        try:
            import torch
            if torch.load(path, map_location="cpu", weights_only=False).get("obs_encoder") == "skin":
                return path
        except Exception:  # noqa: BLE001 - an unreadable checkpoint is skipped
            continue
    return ""


class LoadedPolicy:
    """A checkpoint loaded with ``deploy_core.load_policy`` and warmed up."""

    def __init__(self, path: str, device: str) -> None:
        from deploy_core import load_policy  # play_policy/isaac, on sys.path

        self.path = path
        self.mtime = os.path.getmtime(path)
        self.policy, _, self.norm_a, self.meta, cfg = load_policy(path, device)
        if cfg.get("obs_encoder") != "skin":
            raise ValueError(f"{path} is not a Sparsh-skin play policy (obs_encoder="
                             f"{cfg.get('obs_encoder')!r}); train with --dataset leap_sparsh")
        self.device = device
        self.horizon, self.n_exec, self.hz = cfg["horizon"], cfg["n_action_steps"], cfg["hz"]
        self.joint_names = [str(n) for n in self.meta["joint_names"]]
        self.baseline_file = str(self.meta.get("baseline", ""))
        self.sample(np.zeros((368, 6), np.float32), 1.0, 1.0, 0)  # first call compiles kernels

    def sample(self, obs: np.ndarray, eta: float, init_noise_scale: float, seed: int) -> np.ndarray:
        import torch

        state = torch.as_tensor(obs.reshape(1, -1), dtype=torch.float32, device=self.device)
        gen = torch.Generator(device=self.device).manual_seed(int(seed)) if seed >= 0 else None
        chunk = self.policy(state, generator=gen, eta=float(eta),
                            init_noise_scale=float(init_noise_scale)).cpu().numpy()[0]
        return self.norm_a.denormalize(chunk).astype(np.float64)  # (H, 16) sim rad


class PlayPolicyNode(Node):
    def __init__(self) -> None:
        super().__init__("play_policy_node")
        p = lambda name, value: self.declare_parameter(name, value).value  # noqa: E731
        self.play_policy_dir = p("play_policy_dir", default_play_policy_dir())
        self.default_checkpoint = p("checkpoint", "")
        import torch

        self.device = p("device", "cuda")
        if self.device.startswith("cuda") and not torch.cuda.is_available():
            self.device = "cpu"
        self.max_age = float(p("max_obs_age_s", 0.3))
        for sub in ("", "isaac"):  # play_policy package + deploy_core
            path = os.path.join(self.play_policy_dir, sub)
            if path not in sys.path:
                sys.path.insert(0, path)

        self._lock = threading.Lock()
        # (monotonic receipt, serialized SensStream): kept raw, converted only when sampled
        self._xela: tuple[float, bytes] | None = None
        self._state: tuple[float, list[str], np.ndarray] | None = None
        self._policy: LoadedPolicy | None = None
        self._baselines: dict[str, np.ndarray] = {}
        self._to_sim = HardwareToSim()

        from xela_server_ros2.msg import SensStream

        self._xela_type = SensStream
        # One thread for everything: a sample (~30 ms) holds the stream callbacks back, which
        # only matters for the newest message; a second Python thread (MultiThreadedExecutor)
        # competing for the GIL slowed sampling ~10x.
        # raw: converting every 100 Hz SensStream (368 nested Taxel messages) to Python holds
        # the GIL long enough to slow sampling from ~30 ms to seconds; only the newest is used
        self.create_subscription(SensStream, p("xela_topic", "/xServTopic"), self._on_xela,
                                 qos_profile_sensor_data, raw=True)
        self.create_subscription(JointState, p("state_topic", "leap_state"), self._on_state, 10)
        self.create_service(SamplePlayChunk, "~/sample", self._sample)
        try:  # load (and warm up) the default checkpoint now, not at the first request
            self._load("")
        except Exception as e:  # noqa: BLE001 - a request can still name one
            self.get_logger().warning(f"no default checkpoint loaded: {e}")
        self.get_logger().info(f"play policy node ready (device {self.device}, play_policy "
                               f"{self.play_policy_dir})")

    # ---- streams --------------------------------------------------------------------------

    def _on_xela(self, raw: bytes) -> None:
        with self._lock:
            self._xela = (time.monotonic(), raw)

    def _xela_readings(self, raw: bytes) -> np.ndarray:
        """(T, 3) raw Xela by hardware id: sensors concatenated in order (as
        record_demonstration's ``_on_xela``)."""
        msg = deserialize_message(raw, self._xela_type)
        return np.array([[t.x, t.y, t.z] for s in msg.sensors for t in s.taxels],
                        dtype=np.float64).reshape(-1, 3)

    def _on_state(self, msg: JointState) -> None:
        if len(msg.position) != len(msg.name) or not msg.name:
            return
        with self._lock:
            self._state = (time.monotonic(), list(msg.name), np.asarray(msg.position, np.float64))

    # ---- service ----------------------------------------------------------------------------

    def _load(self, path: str) -> LoadedPolicy:
        if not path:
            path = self.default_checkpoint or newest_checkpoint(self.play_policy_dir)
        if not path or not os.path.isfile(path):
            raise FileNotFoundError(f"no play policy checkpoint ({path or 'none found'})")
        cur = self._policy
        if cur is None or cur.path != path or cur.mtime != os.path.getmtime(path):
            self.get_logger().info(f"loading {path}")
            self._policy = cur = LoadedPolicy(path, self.device)
        return cur

    def _baseline(self, path: str) -> np.ndarray:
        if path not in self._baselines:
            self._baselines[path] = sparsh_processing.load_baseline(path)
        return self._baselines[path]

    def _sample(self, request, response):
        response.success = False
        with self._lock:  # the state at the request (a checkpoint load below may take seconds)
            xela, state = self._xela, self._state
        received = time.monotonic()
        try:
            policy = self._load(request.checkpoint)
            baseline_file = request.baseline or policy.baseline_file
            if not baseline_file or not os.path.isfile(baseline_file):
                raise FileNotFoundError(f"no baseline file ({baseline_file or 'none given'})")
            baseline = self._baseline(baseline_file)
            if xela is None or state is None:
                raise RuntimeError("no " + ("Xela" if xela is None else "leap_state") + " received yet")
            now = received
            age = max(now - xela[0], now - state[0])
            if age > self.max_age:
                raise RuntimeError(f"stale state: Xela {now - xela[0]:.2f} s, leap_state "
                                   f"{now - state[0]:.2f} s old (max {self.max_age:g} s)")
            readings = self._xela_readings(xela[1])
            if readings.shape != baseline.shape:
                raise RuntimeError(f"{len(readings)} taxels, the baseline has {len(baseline)}")
            obs = sparsh_processing.live_obs(readings, baseline, self._to_sim, state[1], state[2])
            t0 = time.monotonic()
            chunk = policy.sample(obs, request.eta, request.init_noise_scale, request.seed)
            response.infer_s = float(time.monotonic() - t0)
            response.checkpoint = policy.path
            response.baseline = baseline_file
            response.joint_names = policy.joint_names
            response.dt = float(1.0 / policy.hz)
            response.horizon = int(chunk.shape[0])
            response.n_exec = int(policy.n_exec)
            response.chunk = chunk.reshape(-1).tolist()
            response.obs_age_s = float(age)
            response.success = True
            response.message = "ok"
        except Exception as e:  # noqa: BLE001 - reported to the caller
            response.message = f"{type(e).__name__}: {e}"
            self.get_logger().warning(response.message)
            if not isinstance(e, (RuntimeError, FileNotFoundError, ValueError)):
                self.get_logger().error(traceback.format_exc())
        return response


def main(args=None) -> int:
    rclpy.init(args=args)
    node = PlayPolicyNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
