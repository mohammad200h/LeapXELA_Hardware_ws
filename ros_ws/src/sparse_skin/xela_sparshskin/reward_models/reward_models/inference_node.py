#!/usr/bin/env python3
"""Inference services of the reward models: ``rank2reward_inference``, ``sarm_inference`` and
``coupled_local_global_inference``.

Service ``~/evaluate`` (leapxela_sparshskin_msgs/EvaluateReward): the reward of a trained run
(the request's ``run_dir``, or the newest run in ``runs_dir``) over one Play on hand recording's
Sparsh-skin episode (``episode_start`` to ``terminal``, at the run's ``step_hz``), with the reward's terms. The loaded run is kept
until a newer ``model.pt`` replaces it. Each evaluation is logged to W&B (one ``inference`` run
per node, started at the first request): the episode's mean reward, its curves and a table
row (recording, label, run, return). Called by record_demonstration's Reward tab (one graph
per model while a recording plays).

ROS parameters:
  - runs_dir (str, default <ws>/demonstrations/compose_playbacks/reward_models/<method>)
  - device (str, default cuda; cpu when no GPU)
  - wandb (bool, default true), wandb_project (str, default reward_models),
    wandb_env_file (str, LEQ_DV3's .env)
"""

from __future__ import annotations

import os
import threading
import traceback
from datetime import datetime

import rclpy
from leapxela_sparshskin_msgs.srv import EvaluateReward
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from reward_models import coupled_local_global, data, rank2reward, sarm
from reward_models.logging_utils import DEFAULT_ENV_FILE, DEFAULT_PROJECT, RunLogger
from reward_models.train_node import default_recordings_dir
from reward_models.training import MODEL_NAME, newest_run, resolve_device


class RewardInferenceServer(Node):
    def __init__(self, method) -> None:
        super().__init__(f"{method.NAME}_inference")
        self.method = method
        p = lambda name, value: self.declare_parameter(name, value).value  # noqa: E731
        self.runs_dir = p("runs_dir", "") or os.path.join(
            data.runs_root(default_recordings_dir()), method.NAME
        )
        self.device = resolve_device(p("device", "cuda"))
        self._wandb = bool(p("wandb", True))
        self._project = p("wandb_project", DEFAULT_PROJECT)
        self._env_file = p("wandb_env_file", DEFAULT_ENV_FILE)
        self._models: dict[str, tuple[float, object]] = {}  # run_dir -> (mtime, Model)
        self._wandb_log: RunLogger | None = None
        self._calls = 0
        self._table: list[list] = []
        self._lock = threading.Lock()
        self.create_service(EvaluateReward, "~/evaluate", self._on_evaluate)
        self.get_logger().info(
            f"Serving {self.get_fully_qualified_name()}/evaluate (runs in {self.runs_dir}, "
            f"{self.device})"
        )

    def _model(self, run_dir: str):
        mtime = os.path.getmtime(os.path.join(run_dir, MODEL_NAME))
        cached = self._models.get(run_dir)
        if cached is None or cached[0] != mtime:
            self.get_logger().info(f"Loading {run_dir}")
            self._models[run_dir] = (mtime, self.method.Model(run_dir, self.device))
        return self._models[run_dir][1]

    def _log(self, run_dir: str, clip: data.Clip, reward, terms) -> None:
        if not self._wandb:
            return
        if self._wandb_log is None:
            name = f"{self.method.NAME}_inference_{datetime.now():%Y%m%d_%H%M%S}"
            self._wandb_log = RunLogger(
                os.path.join(self.runs_dir, "_inference", name), True, self._project, name,
                {"method": self.method.NAME, "runs_dir": self.runs_dir},
                self._env_file, job_type="inference", log=self.get_logger().info,
            )
        self._calls += 1
        t = clip.t - clip.t[0]
        ret = float(reward.mean())
        self._wandb_log.scalars(self._calls, {
            "inference/return": ret, "inference/final_reward": float(reward[-1]),
            "inference/success": float(clip.success),
        })
        self._wandb_log.curves(
            self._calls, f"inference/{clip.name}",
            {"reward": (t, reward), **{k: (t, v) for k, v in terms.items()}},
            f"{clip.name} ({clip.label}) - {os.path.basename(run_dir)}",
        )
        self._table.append([clip.name, clip.label, os.path.basename(run_dir), ret])
        self._wandb_log.table(self._calls, "inference/evaluations",
                           ["recording", "label", "run", "return"], self._table)

    def _on_evaluate(self, request, response):
        with self._lock:
            try:
                run_dir = request.run_dir or newest_run(self.runs_dir)
                if not run_dir or not os.path.isfile(os.path.join(run_dir, MODEL_NAME)):
                    raise FileNotFoundError(f"no trained run in {request.run_dir or self.runs_dir}")
                if not os.path.isfile(request.recording):
                    raise FileNotFoundError(f"no recording {request.recording!r}")
                model = self._model(run_dir)
                clip = data.load_clip(request.recording, model.step_hz,
                                      episode_hz=model.cfg.episode_hz,
                                      modality=model.cfg.modality)
                reward, terms = model(clip)
                self._log(run_dir, clip, reward, terms)
            except Exception as e:  # noqa: BLE001 - reported to the caller
                if not isinstance(e, (FileNotFoundError, ValueError)):
                    self.get_logger().error(traceback.format_exc())
                response.success = False
                response.message = f"{type(e).__name__}: {e}"
                return response
        response.success = True
        response.run_dir = run_dir
        response.label = clip.label
        response.t = [float(v) for v in clip.t]
        response.reward = [float(v) for v in reward]
        response.term_names = list(terms)
        response.terms = [float(v) for name in terms for v in terms[name]]
        response.message = (
            f"{clip.name} ({clip.label}): mean reward {float(reward.mean()):.3f} over "
            f"{len(clip)} steps, run {os.path.basename(run_dir)}"
        )
        self.get_logger().info(response.message)
        return response

    def destroy_node(self):
        if self._wandb_log is not None:
            self._wandb_log.finish()
        return super().destroy_node()


def _main(method, args=None) -> None:
    rclpy.init(args=args)
    node = RewardInferenceServer(method)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def rank2reward_main(args=None) -> None:
    _main(rank2reward, args)


def coupled_local_global_main(args=None) -> None:
    _main(coupled_local_global, args)


def sarm_main(args=None) -> None:
    _main(sarm, args)
