#!/usr/bin/env python3
"""Training action servers of the reward models: ``rank2reward_train`` and
``coupled_local_global_train``.

Action ``~/train`` (leapxela_sparshskin_msgs/TrainReward): trains the node's reward model
(``rank2reward`` / ``coupled_local_global``) on the Sparsh-skin episodes of the labelled Play
on hand recordings of the goal's ``recordings_dir`` (``training.run_training``), publishing feedback (stage, progress,
epoch, losses, validation metric) after loading and after every epoch, logging to
``metrics.jsonl`` and W&B (``logging_utils``, set up as LEQ_DV3). One goal at a time; a cancel
stops it after the current training step, keeping the best epoch so far. Called by
record_demonstration's Reward Design tab (Train).

ROS parameters (used for the goal's zero / empty fields):
  - recordings_dir (str, default <ws>/demonstrations/compose_playbacks)
  - output_dir (str, default <recordings_dir>/reward_models/<method>)
  - epochs, steps_per_epoch, batch_size, learning_rate, val_fraction, step_hz, episode_hz,
    seed
  - device (str, default cuda; cpu when no GPU)
  - wandb_project (str, default reward_models), wandb_env_file (str, LEQ_DV3's .env)
"""

from __future__ import annotations

import os
import threading
import traceback

import rclpy
from leapxela_sparshskin_msgs.action import TrainReward
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node

from reward_models import coupled_local_global, rank2reward
from reward_models.logging_utils import DEFAULT_ENV_FILE, DEFAULT_PROJECT
from reward_models.training import Cancel, Feedback, TrainConfig, run_training


def default_recordings_dir() -> str:
    try:
        from mechanical_pen_data_collection.label_playbacks import default_demo_dir

        return os.path.join(default_demo_dir(), "compose_playbacks")
    except Exception:  # noqa: BLE001
        return os.path.expanduser("~/demonstrations/compose_playbacks")


class RewardTrainServer(Node):
    def __init__(self, method) -> None:
        super().__init__(f"{method.NAME}_train")
        self.method = method
        defaults = TrainConfig(method=method.NAME, recordings_dir="")
        p = lambda name, value: self.declare_parameter(name, value).value  # noqa: E731
        self.defaults = TrainConfig(
            method=method.NAME,
            recordings_dir=p("recordings_dir", default_recordings_dir()),
            output_dir=p("output_dir", ""),
            epochs=int(p("epochs", defaults.epochs)),
            steps_per_epoch=int(p("steps_per_epoch", defaults.steps_per_epoch)),
            batch_size=int(p("batch_size", defaults.batch_size)),
            learning_rate=float(p("learning_rate", defaults.learning_rate)),
            val_fraction=float(p("val_fraction", defaults.val_fraction)),
            step_hz=float(p("step_hz", defaults.step_hz)),
            episode_hz=float(p("episode_hz", defaults.episode_hz)),
            seed=int(p("seed", defaults.seed)),
            device=p("device", defaults.device),
            wandb_project=p("wandb_project", DEFAULT_PROJECT),
            env_file=p("wandb_env_file", DEFAULT_ENV_FILE),
        )
        self._busy = threading.Lock()
        self._server = ActionServer(
            self, TrainReward, "~/train",
            execute_callback=self._execute,
            goal_callback=self._on_goal,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=ReentrantCallbackGroup(),
        )
        self.get_logger().info(f"Serving {self.get_fully_qualified_name()}/train")

    def _on_goal(self, _goal) -> GoalResponse:
        if self._busy.locked():
            self.get_logger().warn("Already training: goal rejected")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def _config(self, goal) -> TrainConfig:
        d = self.defaults
        return TrainConfig(
            method=self.method.NAME,
            recordings_dir=goal.recordings_dir or d.recordings_dir,
            output_dir=goal.output_dir or d.output_dir,
            epochs=goal.epochs if goal.epochs > 0 else d.epochs,
            steps_per_epoch=d.steps_per_epoch,
            batch_size=goal.batch_size if goal.batch_size > 0 else d.batch_size,
            learning_rate=goal.learning_rate if goal.learning_rate > 0 else d.learning_rate,
            val_fraction=goal.val_fraction if goal.val_fraction > 0 else d.val_fraction,
            step_hz=goal.step_hz if goal.step_hz > 0 else d.step_hz,
            episode_hz=goal.episode_hz if goal.episode_hz > 0 else d.episode_hz,
            seed=goal.seed if goal.seed > 0 else d.seed,
            wandb=bool(goal.wandb),
            wandb_project=goal.wandb_project or d.wandb_project,
            wandb_name=goal.wandb_name,
            env_file=d.env_file,
            device=d.device,
        )

    def _execute(self, goal_handle):
        result = TrainReward.Result()
        with self._busy:
            cfg = self._config(goal_handle.request)
            self.get_logger().info(f"Training {self.method.NAME} on {cfg.recordings_dir}")

            def report(fb: Feedback) -> None:
                msg = TrainReward.Feedback(
                    stage=fb.stage, progress=float(fb.progress), epoch=fb.epoch,
                    epochs=fb.epochs, train_loss=float(fb.train_loss),
                    val_loss=float(fb.val_loss), val_metric=float(fb.val_metric),
                    val_metric_name=fb.val_metric_name, status=fb.status,
                )
                goal_handle.publish_feedback(msg)
                if fb.stage != "loading" or fb.progress == 0:
                    self.get_logger().info(f"[{fb.stage} {fb.progress:.0%}] {fb.status}")

            try:
                out = run_training(self.method, cfg, report,
                                   lambda: goal_handle.is_cancel_requested,
                                   log=self.get_logger().info)
            except Cancel:
                out = {"success": False, "cancelled": True, "message": "cancelled while loading"}
            except Exception as e:  # noqa: BLE001 - reported to the caller
                self.get_logger().error(traceback.format_exc())
                out = {"success": False, "message": f"{type(e).__name__}: {e}"}
        result.success = bool(out.get("success"))
        result.message = out.get("message", "")
        result.run_dir = out.get("run_dir", "")
        result.wandb_url = out.get("wandb_url", "")
        result.train_loss = float(out.get("train_loss", float("nan")))
        result.val_loss = float(out.get("val_loss", float("nan")))
        result.val_metric = float(out.get("val_metric", float("nan")))
        result.val_metric_name = self.method.METRIC
        if out.get("cancelled"):
            goal_handle.canceled()
        elif result.success:
            goal_handle.succeed()
        else:
            goal_handle.abort()
        self.get_logger().info(result.message)
        return result


def _main(method, args=None) -> None:
    rclpy.init(args=args)
    node = RewardTrainServer(method)
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
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
