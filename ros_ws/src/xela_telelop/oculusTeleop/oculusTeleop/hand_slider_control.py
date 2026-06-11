from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from sensor_msgs.msg import JointState


def _xela_description_share() -> Path:
    return Path(get_package_share_directory("xela_description"))


def _default_urdf_path() -> str:
    return str(_xela_description_share() / "hand.urdf")


def _default_joint_config_path() -> str:
    return str(_xela_description_share() / "joint_config.json")


def load_joint_config(path: str) -> dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Joint config not found: {resolved}")
    with open(resolved, "r", encoding="utf-8") as f:
        return json.load(f)

def get_slider_idle_position(name,joint_config: dict[str, Any]):
    fingers_idle_positions = joint_config["leapXela"]["sim"]["fingers"]
    thumb_idle_positions = joint_config["leapXela"]["sim"]["thumb"]


    print(f"name: {name}")
    print(f"fingers_idle_positions: {fingers_idle_positions}")
    print(f"thumb_idle_positions: {thumb_idle_positions}")
    if "th" in name:
        name = name.split("_")[1]
        return thumb_idle_positions[name]["zero"]
    else:
        name = name.split("_")[1]
        return fingers_idle_positions[name]["zero"]


def _joint_slider_limits(lower: float, upper: float) -> tuple[float, float, float]:
    """Return (range_min, range_max, start) for PyBullet debug sliders."""
    if lower <= upper:
        return lower, upper
    return upper, lower


def _create_joint_sliders(p, body_id: int, joint_config: dict[str, Any]) -> list[tuple[int, int]]:
    sliders: list[tuple[int, int]] = []
    for joint_idx in range(p.getNumJoints(body_id)):
        info = p.getJointInfo(body_id, joint_idx)
        if info[2] not in (p.JOINT_REVOLUTE, p.JOINT_PRISMATIC):
            continue
        name = info[1].decode("utf-8")
        lo, hi = _joint_slider_limits(float(info[8]), float(info[9]))
        if lo == hi:
            lo, hi  = -3.14, 3.14
        start = get_slider_idle_position(name,joint_config)
        slider_id = p.addUserDebugParameter(name, lo, hi, start)
        sliders.append((joint_idx, slider_id))
    return sliders


def _apply_joint_sliders(
    p, body_id: int, sliders: list[tuple[int, int]]
) -> tuple[list[str], list[float]]:
    names: list[str] = []
    positions: list[float] = []
    for joint_idx, slider_id in sliders:
        pos = float(p.readUserDebugParameter(slider_id))
        p.resetJointState(body_id, joint_idx, pos)
        info = p.getJointInfo(body_id, joint_idx)
        names.append(info[1].decode("utf-8"))
        positions.append(pos)
    return names, positions


def _setup_pybullet(
    urdf_path: str,
    joint_config: dict[str, Any],
    use_gui: bool = True,
) -> tuple[Any, int, int, list[tuple[int, int]]]:
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
    data_path = Path(pybullet_data.getDataPath()).resolve()
    p.setAdditionalSearchPath(str(data_path))
    p.setAdditionalSearchPath(str(urdf.parent))
    p.setGravity(0, 0, -9.81)

    body_id = p.loadURDF(
        str(urdf),
        basePosition=[0.0, 0.0, 0.0],
        baseOrientation=p.getQuaternionFromEuler([0.0, 0.0, 0.0]),
        useFixedBase=True,
    )

    sliders = _create_joint_sliders(p, body_id, joint_config) if use_gui else []
    return p, cid, body_id, sliders


class SliderControlNode(Node):
    def __init__(self) -> None:
        super().__init__("slider_control")

        self.declare_parameter("urdf_path", _default_urdf_path())
        self.declare_parameter("joint_config_path", _default_joint_config_path())
        self.declare_parameter("use_gui", True)
        self.declare_parameter("joint_topic", "oculus_teleop_joint_commands")
        self.declare_parameter("publish_rate_hz", 30.0)

        urdf_path = str(self.get_parameter("urdf_path").value)
        joint_config_path = str(self.get_parameter("joint_config_path").value)
        use_gui = bool(self.get_parameter("use_gui").value)
        joint_topic = str(self.get_parameter("joint_topic").value)
        publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)

        self.get_logger().info(f"Loading joint config: {joint_config_path}")
        self.joint_config = load_joint_config(joint_config_path)

        self.get_logger().info(f"Loading URDF in PyBullet: {urdf_path}")
        self._p, self._cid, self._body_id, self._sliders = _setup_pybullet(
            urdf_path=urdf_path,
            joint_config=self.joint_config,
            use_gui=use_gui,
        )

        self._joint_pub = self.create_publisher(JointState, joint_topic, 10)
        self._joint_msg = JointState()
        sim_period = 1.0 / 240.0
        self._timer = self.create_timer(sim_period, self._on_timer)

        self.get_logger().info(
            f"Publishing slider joint commands on '{joint_topic}' "
            f"at {publish_rate_hz:.1f} Hz after each slider update."
        )
        self._publish_rate_hz = max(publish_rate_hz, 1.0)
        self._publish_every_n = max(1, int(round(240.0 / self._publish_rate_hz)))
        self._tick = 0

    def _on_timer(self) -> None:
        if not self._p.isConnected(self._cid):
            return

        names, positions = _apply_joint_sliders(self._p, self._body_id, self._sliders)

        self._tick += 1
        if self._tick % self._publish_every_n == 0:
            self._joint_msg.header.stamp = self.get_clock().now().to_msg()
            self._joint_msg.name = names
            self._joint_msg.position = positions
            self._joint_pub.publish(self._joint_msg)

        self._p.stepSimulation()

    def destroy_node(self) -> bool:
        try:
            if hasattr(self, "_p") and hasattr(self, "_cid"):
                self._p.disconnect(self._cid)
        except Exception:
            pass
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node: SliderControlNode | None = None
    try:
        node = SliderControlNode()
        rclpy.spin(node)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
