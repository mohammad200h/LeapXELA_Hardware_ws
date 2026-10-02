from __future__ import annotations

from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from sensor_msgs.msg import JointState


def _default_urdf_path() -> str:
    return str(Path(get_package_share_directory("xela_description")) / "hand.urdf")


def _setup_pybullet(urdf_path: str, use_gui: bool):
    try:
        import pybullet as p  # type: ignore
        import pybullet_data  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "PyBullet is required. Install it (e.g. `sudo apt install python3-pybullet` "
            "or `pip install pybullet`)."
        ) from e

    urdf = Path(urdf_path).expanduser().resolve()
    if not urdf.exists():
        raise FileNotFoundError(f"URDF not found: {urdf}")

    cid = p.connect(p.GUI if use_gui else p.DIRECT)
    p.setAdditionalSearchPath(str(Path(pybullet_data.getDataPath()).resolve()))
    p.setAdditionalSearchPath(str(urdf.parent))

    body_id = p.loadURDF(
        str(urdf),
        basePosition=[0.0, 0.0, 0.0],
        baseOrientation=p.getQuaternionFromEuler([0.0, 0.0, 0.0]),
        useFixedBase=True,
    )
    return p, cid, body_id


def _joint_indices_by_name(p, body_id: int) -> dict[str, int]:
    indices: dict[str, int] = {}
    for joint_idx in range(p.getNumJoints(body_id)):
        info = p.getJointInfo(body_id, joint_idx)
        if info[2] in (p.JOINT_REVOLUTE, p.JOINT_PRISMATIC):
            indices[info[1].decode("utf-8")] = joint_idx
    return indices


class SimJointViewer(Node):
    def __init__(self) -> None:
        super().__init__("sim_joint_viewer")

        self.declare_parameter("urdf_path", _default_urdf_path())
        self.declare_parameter("use_gui", True)
        self.declare_parameter("sim_topic", "leap_state_sim")

        urdf_path = str(self.get_parameter("urdf_path").value)
        use_gui = bool(self.get_parameter("use_gui").value)
        sim_topic = str(self.get_parameter("sim_topic").value)

        self.get_logger().info(f"Loading URDF in PyBullet: {urdf_path}")
        self._p, self._cid, self._body_id = _setup_pybullet(urdf_path, use_gui)
        self._joint_indices = _joint_indices_by_name(self._p, self._body_id)
        self._warned_unknown: set[str] = set()

        self._sub = self.create_subscription(JointState, sim_topic, self._callback, 10)
        self.get_logger().info(f"Mirroring sim joint values from '{sim_topic}'")

    def _callback(self, msg: JointState) -> None:
        if not self._p.isConnected(self._cid):
            return

        for name, position in zip(msg.name, msg.position):
            joint_idx = self._joint_indices.get(name)
            if joint_idx is None:
                if name not in self._warned_unknown:
                    self._warned_unknown.add(name)
                    self.get_logger().warn(f"Joint '{name}' not found in URDF; ignoring")
                continue
            self._p.resetJointState(self._body_id, joint_idx, float(position))

    def destroy_node(self) -> bool:
        try:
            self._p.disconnect(self._cid)
        except Exception:
            pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node: SimJointViewer | None = None
    try:
        node = SimJointViewer()
        rclpy.spin(node)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
