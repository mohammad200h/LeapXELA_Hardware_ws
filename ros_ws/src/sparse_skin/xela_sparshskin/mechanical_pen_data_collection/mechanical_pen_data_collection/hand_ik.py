#!/usr/bin/env python3
"""Paths of the LEAP hand between joint poses that keep the fingers apart, with mink.

``HandIK.plan`` runs differential IK (mink) on the MuJoCo model mujoco_sim_node simulates
(xela_description/mjcf/scene.xml): a posture task pulls every joint to the goal, the distal
link of every finger tracks its position at the goal (``FrameTask``), and the joint range,
joint speed (``max_speed``) and the distance between links of different fingers
(``CollisionAvoidanceLimit``, ``min_distance``) are limits, so the fingers go around one
another instead of through. Link pairs closer than ``min_distance`` at the start or the goal
(side by side fingers of the flat open hand touch in the model; fingertips pinching a pen do
too) are not kept apart, or the path could not start or end there. The path ends exactly at
the goal.

Service ``~/plan_to_pose`` (leapxela_sparshskin_msgs/PlanHandPose): sim joint angles in and out.
Called by record_demonstration's Baseline tab.

ROS parameters:
  - model_path (str, default xela_description/mjcf/scene.xml)
  - dt (float, default 0.02): s between trajectory points
  - max_speed (float, default 0.5): rad/s of every joint
  - min_distance (float, default 0.003): m kept between links of different fingers
  - max_time (float, default 20.0): s of trajectory before giving up
"""

from __future__ import annotations

import itertools
import os

import mink
import mujoco
import numpy as np

FINGERS = ("th", "if", "mf", "rf")
TIP_BODIES = {finger: f"{finger}_ds" for finger in FINGERS}  # distal links
GOAL_TOLERANCE = 1e-3  # rad: close enough to the goal to end the path
COLLISION_DETECTION_DISTANCE = 0.02  # m: finger pairs nearer than this are constrained


def default_model_path() -> str:
    from ament_index_python.packages import get_package_share_directory

    return os.path.join(get_package_share_directory("xela_description"), "mjcf", "scene.xml")


class HandIK:
    def __init__(
        self, model_path: str | None = None, max_speed: float = 0.5,
        min_distance: float = 0.003,
    ) -> None:
        self.model = mujoco.MjModel.from_xml_path(model_path or default_model_path())
        self.data = mujoco.MjData(self.model)
        self.configuration = mink.Configuration(self.model)
        self.joint_names = [self.model.joint(j).name for j in range(self.model.njnt)]
        self._qpos = {n: int(self.model.jnt_qposadr[j]) for j, n in enumerate(self.joint_names)}
        # The posture leads: fingertip targets weighing more trap curled fingers (a fingertip
        # pulled straight at its target folds its finger into the joint limits).
        self.tip_tasks = [
            mink.FrameTask(body, "body", position_cost=0.3, orientation_cost=0.0, lm_damping=1.0)
            for body in TIP_BODIES.values()
        ]
        self.posture = mink.PostureTask(self.model, cost=1.0)
        self.min_distance = min_distance
        # Collision geoms of each finger link (the palm is left out: the fingers sit on it).
        self.link_geoms: dict[str, list[int]] = {}
        for g in range(self.model.ngeom):
            body = self.model.body(self.model.geom_bodyid[g]).name
            if self.model.geom_contype[g] and body.split("_")[0] in FINGERS:
                self.link_geoms.setdefault(body, []).append(g)
        self._finger_of = {
            g: body.split("_")[0] for body, geoms in self.link_geoms.items() for g in geoms
        }
        # Links of different fingers, the pairs the collision limit may keep apart.
        self.link_pairs = [
            (a, b) for a, b in itertools.combinations(sorted(self.link_geoms), 2)
            if a.split("_")[0] != b.split("_")[0]
        ]
        self.limits = [
            mink.ConfigurationLimit(self.model),
            mink.VelocityLimit(self.model, {n: max_speed for n in self.joint_names}),
        ]

    def to_qpos(self, names: list[str], values) -> np.ndarray:
        """Model qpos of joints ``names`` at ``values``, clipped to the joint ranges."""
        missing = [n for n in self.joint_names if n not in names]
        if missing:
            raise ValueError(f"no angle for {', '.join(missing)}")
        q = np.zeros(self.model.nq)
        for name, value in zip(names, values):
            if name in self._qpos:
                q[self._qpos[name]] = value
        lo, hi = self.model.jnt_range[:, 0], self.model.jnt_range[:, 1]
        return np.clip(q, lo, hi)

    def from_qpos(self, names: list[str], q: np.ndarray) -> np.ndarray:
        return np.array([q[self._qpos[n]] for n in names])

    def link_distance(self, a: str, b: str) -> float:
        """Smallest distance (m, up to COLLISION_DETECTION_DISTANCE) of links ``a`` and ``b``
        at the pose ``self.data`` holds."""
        return min(
            mujoco.mj_geomDistance(
                self.model, self.data, g1, g2, COLLISION_DETECTION_DISTANCE, None
            )
            for g1 in self.link_geoms[a] for g2 in self.link_geoms[b]
        )

    def collision_limit(
        self, q_start: np.ndarray, q_goal: np.ndarray
    ) -> tuple[mink.CollisionAvoidanceLimit, int]:
        """(the limit keeping apart the link pairs that are apart at both ``q_start`` and
        ``q_goal``, how many pairs touch at either and are left out)."""
        apart = set(self.link_pairs)
        for q in (q_start, q_goal):
            self.data.qpos[:] = q
            mujoco.mj_kinematics(self.model, self.data)
            apart = {(a, b) for a, b in apart if self.link_distance(a, b) > self.min_distance}
        limit = mink.CollisionAvoidanceLimit(
            self.model,
            [(self.link_geoms[a], self.link_geoms[b]) for a, b in sorted(apart)],
            minimum_distance_from_collisions=self.min_distance,
            collision_detection_distance=COLLISION_DETECTION_DISTANCE,
        )
        return limit, len(self.link_pairs) - len(apart)

    def fingers_touching(self, q: np.ndarray) -> bool:
        """Whether links of two different fingers touch at ``q``."""
        self.data.qpos[:] = q
        mujoco.mj_forward(self.model, self.data)
        for c in self.data.contact[: self.data.ncon]:
            a, b = self._finger_of.get(c.geom1), self._finger_of.get(c.geom2)
            if a is not None and b is not None and a != b and c.dist < 0:
                return True
        return False

    def plan(
        self, names: list[str], start, goal, dt: float, max_time: float = 20.0
    ) -> tuple[np.ndarray, int, int]:
        """((steps, len(names)) path of joints ``names`` from ``start`` to ``goal``, points
        on it where two fingers touch, link pairs left free as they touch at the start or the
        goal). Raises
        if the goal is not reached in ``max_time``."""
        q_start, q_goal = self.to_qpos(names, start), self.to_qpos(names, goal)
        collision, free = self.collision_limit(q_start, q_goal)
        limits = [*self.limits, collision]
        self.configuration.update(q_goal)
        for task, body in zip(self.tip_tasks, TIP_BODIES.values()):
            task.set_target(self.configuration.get_transform_frame_to_world(body, "body"))
        self.posture.set_target(q_goal)
        self.configuration.update(q_start)
        path = [q_start]
        for _ in range(int(max_time / dt)):
            if np.max(np.abs(self.configuration.q - q_goal)) < GOAL_TOLERANCE:
                break
            velocity = mink.solve_ik(
                self.configuration, [*self.tip_tasks, self.posture], dt, "daqp",
                damping=1e-3, limits=limits,
            )
            self.configuration.integrate_inplace(velocity, dt)
            path.append(self.configuration.q.copy())
        else:
            error = np.max(np.abs(self.configuration.q - q_goal))
            raise RuntimeError(
                f"not at the goal after {max_time:g} s ({error:.3f} rad away): the fingers may "
                "be stuck on one another"
            )
        path.append(q_goal)
        contacts = sum(self.fingers_touching(q) for q in path)
        return np.stack([self.from_qpos(names, q) for q in path]), contacts, free


def main(args=None):
    import rclpy
    from leapxela_sparshskin_msgs.srv import PlanHandPose
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node

    class HandIKNode(Node):
        def __init__(self) -> None:
            super().__init__("hand_ik")
            model_path = self.declare_parameter("model_path", "").value
            self._dt = float(self.declare_parameter("dt", 0.02).value)
            self._max_time = float(self.declare_parameter("max_time", 20.0).value)
            self._ik = HandIK(
                model_path or None,
                max_speed=float(self.declare_parameter("max_speed", 0.5).value),
                min_distance=float(self.declare_parameter("min_distance", 0.003).value),
            )
            self.create_service(PlanHandPose, "~/plan_to_pose", self._on_plan)
            self.get_logger().info(f"Serving {self.get_fully_qualified_name()}/plan_to_pose")

        def _on_plan(self, request, response):
            names = list(request.joint_names)
            dt = float(request.dt) if request.dt > 0 else self._dt
            response.joint_names, response.dt = names, dt
            if len(request.start) != len(names) or len(request.goal) != len(names):
                response.success = False
                response.message = "start and goal need one angle per joint name"
                return response
            try:
                path, contacts, free = self._ik.plan(
                    names, request.start, request.goal, dt, self._max_time
                )
            except Exception as e:  # noqa: BLE001 - reported to the caller
                response.success = False
                response.message = str(e)
                return response
            response.success = True
            response.trajectory = path.ravel().tolist()
            response.steps = len(path)
            response.contacts = contacts
            response.message = (
                f"{len(path)} points over {(len(path) - 1) * dt:.2f} s"
                + (f", fingers touch at {contacts}" if contacts else "")
                + f" ({free} link pairs touching at the start or goal not kept apart)"
            )
            self.get_logger().info(f"Planned {response.message}")
            return response

    rclpy.init(args=args)
    node = HandIKNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
