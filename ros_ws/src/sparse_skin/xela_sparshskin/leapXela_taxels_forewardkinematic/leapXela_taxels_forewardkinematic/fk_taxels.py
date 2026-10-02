#!/usr/bin/env python3
"""Forward kinematics of Leap/Xela taxels (``fk_taxels`` node).

Maps the 16 Leap joint angles onto 3D positions and orientations of all 368
Xela taxels (``hand_ss.urdf`` + per-patch sensor grids), and relates hardware
taxel ids to the FK flatten order (``XELA_FLATTEN_ORDER``).

Subscribes (defaults match process_hand_sensors_into_pointcloud / hand_controller):
  - sensor_msgs/JointState on ``xela_joint_publisher``
  - xela_sparshskin_sim/HandSensors on ``hand_sensors``
Publishes:
  - leapxela_sparshskin_msgs/TaxelFrames on ``taxel_frames``
"""

from __future__ import annotations

import json
from pathlib import Path
import threading

import einops
import numpy as np
import pytorch_kinematics as pk
import torch

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from leapxela_sparshskin_msgs.msg import TaxelFrames
from xela_sparshskin_sim.msg import HandSensors

# Patch link frames in hand_ss.urdf (same taxel counts as Allegro XELA flatten order).
# Proximal "B" pads use unprefixed names in the Leap URDF.
XELA_FLATTEN_ORDER = {
    "3aftc_palm_link": 30,
    "link_15_4x4_palm_link": 16,
    "link_14_4x4_palm_link": 16,
    "0aftc_palm_link": 30,
    "link_2_4x4_palm_link": 16,
    "link_1A_4x4_palm_link": 16,
    "1B_4x4_palm_link": 16,
    "1aftc_palm_link": 30,
    "link_6_4x4_palm_link": 16,
    "link_5A_4x4_palm_link": 16,
    "5B_4x4_palm_link": 16,
    "2aftc_palm_link": 30,
    "link_10_4x4_palm_link": 16,
    "link_9A_4x4_palm_link": 16,
    "9B_4x4_palm_link": 16,
    "ahr_palm_2_4x6_palm_link": 24,
    "ahr_palm_1_4x6_palm_link": 24,
    "ahr_palm_3_4x6_palm_link": 24,
}

_PATCH_TO_TAXEL_MAP = {
    "3aftc_palm_link": ("TH", "tip", True, 0, False),
    "link_15_4x4_palm_link": ("TH", "ds", False, 4, False),
    "link_14_4x4_palm_link": ("TH", "third", False, 4, False),
    "0aftc_palm_link": ("IF", "tip", True, 0, False),
    "link_2_4x4_palm_link": ("IF", "ds", False, 4, False),
    "link_1A_4x4_palm_link": ("IF", "md", False, 4, False),
    "1B_4x4_palm_link": ("IF", "bs", False, 4, False),
    "1aftc_palm_link": ("MF", "tip", True, 0, False),
    "link_6_4x4_palm_link": ("MF", "ds", False, 4, False),
    "link_5A_4x4_palm_link": ("MF", "md", False, 4, False),
    "5B_4x4_palm_link": ("MF", "px", False, 4, False),
    "2aftc_palm_link": ("RF", "tip", True, 0, False),
    "link_10_4x4_palm_link": ("RF", "ds", False, 4, False),
    "link_9A_4x4_palm_link": ("RF", "md", False, 4, False),
    "9B_4x4_palm_link": ("RF", "bs", False, 4, False),
    "ahr_palm_2_4x6_palm_link": ("Palm", "uspa46_1", False, 4, True),
    "ahr_palm_1_4x6_palm_link": ("Palm", "uspa46_2", False, 4, True),
    "ahr_palm_3_4x6_palm_link": ("Palm", "uspa46_3", False, 4, True),
}


def get_sensor_grid(patch_name):
    if "aftc" in patch_name:
        h, w, d = 0.031, 0.039, 0.029  # numbers taken from mesh boundingbox
        h_res, w_res = 6, 6
        x = np.linspace(0.5 - h_res / 2, h_res / 2 + 0.5, h_res, endpoint=False) * h / h_res
        y = np.linspace(0.5, w_res + 0.5, w_res, endpoint=False) * w / w_res
        xx_, yy_ = np.meshgrid(x, y)
        xx = np.concatenate([xx_[:4, :].flatten(), xx_[-2, 1:-1], xx_[-1, 2:-2]], axis=0)
        yy = np.concatenate([yy_[:4, :].flatten(), yy_[-2, 1:-1], yy_[-1, 2:-2]], axis=0)
    elif "4x4" in patch_name:
        h, w, d = 0.026, 0.024, 0.0044  # numbers taken from mesh boundingbox
        h_res, w_res = 4, 4
        x = np.linspace(0.5, h_res + 0.5, h_res, endpoint=False) * h / h_res
        y = np.linspace(0.5, w_res + 0.5, w_res, endpoint=False) * w / w_res
        xx, yy = np.meshgrid(x, y)
    elif "4x6" in patch_name:
        # Local to ahr_palm_*_4x6_palm_link (pad-edge / link origin).
        # First taxel at (offset_x, offset_y); then 6 cols x 4 rows by spacing.
        # Values match xela 4x6 taxel sites (mjmodel / 4x6.urdf).
        offset_x = 0.00435
        offset_y = 0.00425
        x_dist = 0.00725
        y_dist = 0.00717
        d = 0.0
        n_cols, n_rows = 6, 4
        x = offset_x + np.arange(n_cols) * x_dist
        y = offset_y + np.arange(n_rows) * y_dist
        xx, yy = np.meshgrid(x, y)
    return xx, yy, d


# Leap + Xela skin URDF (hand_ss.urdf from xela_description)
def _default_urdf_path() -> Path:
    candidates = []
    try:
        from ament_index_python.packages import get_package_share_directory

        candidates.append(
            Path(get_package_share_directory("xela_description")) / "urdf" / "hand_ss.urdf"
        )
    except Exception:
        pass
    candidates.extend(
        [
            Path("/workspace/LeapXELA_Hardware_ws/ros_ws/src/xela_description/urdf/hand_ss.urdf"),
            Path("/workspace/LeapXELA_Hardware_ws/ros_ws/install/xela_description/share/xela_description/urdf/hand_ss.urdf"),
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


DEFAULT_URDF_PATH = _default_urdf_path()


def _default_taxel_map_path() -> Path:
    candidates = []
    try:
        from ament_index_python.packages import get_package_share_directory

        candidates.append(
            Path(get_package_share_directory("xela_sparshskin_sim")) / "leap_sensor_taxel_map.json"
        )
    except Exception:
        pass
    candidates.extend(
        [
            Path(
                "/workspace/LeapXELA_Hardware_ws/ros_ws/src/sparse_skin/xela_sparshskin"
                "/xela_sparshskin_sim/src/leap_sensor_taxel_map.json"
            ),
            Path(
                "/workspace/LeapXELA_Hardware_ws/ros_ws/install/xela_sparshskin_sim/share"
                "/xela_sparshskin_sim/leap_sensor_taxel_map.json"
            ),
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def _tip_ids_in_fk_grid_order(ids: list[int]) -> list[int]:
    """Reorder hardware tip ids (4-5-6-6-5-4) into ``get_sensor_grid`` aftc order.

    FK tip positions are a 6x6 with distal taper ``(6,6,6,6,4,2)``. Hardware
    ids in ``leap_sensor_taxel_map.json`` / ``LEAP_XELA_ID`` are a centered
    capsule ``(4,5,6,6,5,4)``. Map between them with a 90° CW + vertical flip
    so e.g. FK indices ``23,17,11,5`` ↔ taxels ``0,1,2,3`` and
    ``18,12,6,0`` ↔ ``58,59,60,61`` on the thumb tip.
    """
    if len(ids) != 30:
        raise ValueError(f"tip expected 30 ids, got {len(ids)}")
    grid = np.full((6, 6), -1, dtype=np.int32)
    grid[0, 2:6] = ids[0:4]
    grid[1, 1:6] = ids[4:9]
    grid[2, 0:6] = ids[9:15]
    grid[3, 0:6] = ids[15:21]
    grid[4, 1:6] = ids[21:26]
    grid[5, 2:6] = ids[26:30]
    # out[r, c] = grid[5 - c, 5 - r]
    out = np.full((6, 6), -1, dtype=np.int32)
    for r in range(6):
        for c in range(6):
            out[r, c] = grid[5 - c, 5 - r]
    return (
        out[:4, :].reshape(-1).tolist()
        + out[4, 1:5].tolist()
        + out[5, 2:4].tolist()
    )


def _palm_ids_in_fk_grid_order(ids: list[int], patch: str) -> list[int]:
    """Reorder hardware palm ids (6x4) into ``get_sensor_grid`` 4x6 order.

    JSON / ``LEAP_XELA_ID`` store each ``uspa46_*`` pad as 6 rows of 4. FK
    flattens ``meshgrid`` as 4 rows of 6. Left pads (``uspa46_2``, ``uspa46_3``)
    use 90° CW + vertical flip; the right pad (``uspa46_1``) is a plain
    transpose so FK ``296,302,308,314`` ↔ taxels ``119,120,121,122``.
    """
    if len(ids) != 24:
        raise ValueError(f"palm expected 24 ids, got {len(ids)}")
    hw = np.asarray(ids, dtype=np.int32).reshape(6, 4)
    if patch == "uspa46_1":
        out = hw.T
    else:
        # out[r, c] = hw[5 - c, 3 - r]  (uspa46_2 / uspa46_3)
        out = np.flipud(np.rot90(hw, -1))
    return out.reshape(-1).tolist()


def _flatten_patch_taxel_ids(
    map_dict: dict,
    finger: str,
    patch: str,
    is_tip: bool,
    is_palm: bool = False,
) -> list[int]:
    """Taxel ids for one patch in FK flatten order (matches ``get_sensor_grid``)."""
    patch_dict = map_dict[finger][patch]
    row_keys = sorted(patch_dict.keys(), key=lambda k: int(k))
    ids: list[int] = []
    for key in row_keys:
        ids.extend(int(v) for v in patch_dict[key])
    if is_tip:
        if len(ids) != 30:
            raise ValueError(f"{finger}/{patch} tip expected 30 ids, got {len(ids)}")
        return _tip_ids_in_fk_grid_order(ids)
    if is_palm:
        if len(ids) != 24:
            raise ValueError(f"{finger}/{patch} palm expected 24 ids, got {len(ids)}")
        return _palm_ids_in_fk_grid_order(ids, patch)
    return ids


def _build_taxel_ids_in_fk_order() -> np.ndarray:
    """Hardware taxel ids in ``XELA_FLATTEN_ORDER`` (same order as FK positions).

    Uses ``leap_sensor_taxel_map.json`` via ``_PATCH_TO_TAXEL_MAP`` so 3D labels
    match the white-background reference grid (taxel_pertubation / LEAP_XELA_ID).
    """
    map_path = _default_taxel_map_path()
    if not map_path.is_file():
        raise FileNotFoundError(f"Could not locate leap_sensor_taxel_map.json at {map_path}")

    with map_path.open(encoding="utf-8") as f:
        map_dict = json.load(f)

    taxel_ids: list[int] = []
    for link_name, num_sensors in XELA_FLATTEN_ORDER.items():
        finger, patch, is_tip, _width, is_palm = _PATCH_TO_TAXEL_MAP[link_name]
        ids = _flatten_patch_taxel_ids(map_dict, finger, patch, is_tip, is_palm=is_palm)
        if len(ids) != num_sensors:
            raise ValueError(
                f"{link_name} ({finger}/{patch}): expected {num_sensors} ids, got {len(ids)}"
            )
        taxel_ids.extend(ids)

    out = np.asarray(taxel_ids, dtype=np.int32)
    if out.shape[0] != 368:
        raise ValueError(f"Expected 368 taxel ids, got {out.shape[0]}")
    if not np.array_equal(np.sort(out), np.arange(368)):
        raise ValueError("Taxel ids from map do not cover 0..367 exactly once")
    return out


TAXEL_IDS_IN_FK_ORDER = _build_taxel_ids_in_fk_order()
PATCH_IDS_IN_FK_ORDER = np.repeat(
    np.arange(len(XELA_FLATTEN_ORDER), dtype=np.uint8),
    list(XELA_FLATTEN_ORDER.values()),
)


# Leap hand hinge joints in MuJoCo / hand_controller / hand_ss.urdf order (16 DoF).
LEAP_JOINT_ORDER = [
    "if_mcp",
    "if_rot",
    "if_pip",
    "if_dip",
    "mf_mcp",
    "mf_rot",
    "mf_pip",
    "mf_dip",
    "rf_mcp",
    "rf_rot",
    "rf_pip",
    "rf_dip",
    "th_cmc",
    "th_axl",
    "th_mcp",
    "th_ipl",
]

# MuJoCo scene places the palm with pos="0 0 0.1" quat="0.707107 -0.707107 0 0"
# (Rx -90°). URDF FK is in the unrotated hand base; apply this to match MuJoCo world
# (Z-up, fingers along +Y) so Open3D aligns with process_hand_sensors_into_pointcloud.
_MUJOCO_PALM_R = np.array(
    [
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0],
    ],
    dtype=np.float64,
)
_MUJOCO_PALM_T = np.array([0.0, 0.0, 0.1], dtype=np.float64)


def urdf_base_to_mujoco_world(positions, rotations=None):
    """Map URDF-base FK poses into the MuJoCo world frame used by the sim.

    ``p_w = R_palm @ p_urdf + t_palm``, ``R_w = R_palm @ R_urdf``.
    """
    positions = np.asarray(positions, dtype=np.float64)
    squeeze = positions.ndim == 2
    if squeeze:
        positions = positions[None, ...]
    # (T, S, 3): p' = p @ R^T  <=>  R @ p
    pos_w = np.einsum("ij,tsj->tsi", _MUJOCO_PALM_R, positions) + _MUJOCO_PALM_T
    if rotations is None:
        return pos_w[0] if squeeze else pos_w
    rotations = np.asarray(rotations, dtype=np.float64)
    if rotations.ndim == 3:
        rotations = rotations[None, ...]
    rot_w = np.einsum("ij,tsjk->tsik", _MUJOCO_PALM_R, rotations)
    if squeeze:
        return pos_w[0], rot_w[0]
    return pos_w, rot_w


_kinematic_chain = None
_cached_urdf_path = None


def get_kinematic_chain(urdf_path=None):
    global _kinematic_chain, _cached_urdf_path
    urdf_path = Path(urdf_path) if urdf_path is not None else DEFAULT_URDF_PATH
    urdf_path = urdf_path.resolve()
    if _kinematic_chain is None or _cached_urdf_path != urdf_path:
        assert urdf_path.exists(), f"URDF not found at {urdf_path}"
        # hand_ss.urdf may have leading whitespace before the XML declaration.
        urdf_text = urdf_path.read_text().lstrip()
        _kinematic_chain = pk.build_chain_from_urdf(urdf_text)
        _cached_urdf_path = urdf_path
    return _kinematic_chain


def get_fk_taxel_frames(joint_angles, urdf_path=None, mujoco_world: bool = True):
    """FK taxel positions and orientations from Leap joint angles.

    Runs FK on ``hand_ss.urdf``, then maps each patch link frame onto its
    sensor grid. By default, results are transformed into the MuJoCo world
    frame (same palm ``pos``/``quat`` as ``leapXela_generated_flex_sensor.xml``)
    so they match ``process_hand_sensors_into_pointcloud`` / ``HandSensors``.

    Parameters
    ----------
    joint_angles : array-like, shape (16,) or (T, 16)
        Leap joint positions (radians) in ``LEAP_JOINT_ORDER``.
    urdf_path : path-like, optional
        Path to ``hand_ss.urdf``. Defaults to xela_description share.
    mujoco_world : bool
        If True (default), map URDF-base poses into MuJoCo world (Z-up).

    Returns
    -------
    sensor_positions : np.ndarray, shape (T, 368, 3)
        XYZ positions of all taxels (MuJoCo world if ``mujoco_world``).
    sensor_rotations : np.ndarray, shape (T, 368, 3, 3)
        Rotation matrices (sensor local → world/base) for each taxel.
    """
    joint_angles = np.asarray(joint_angles, dtype=np.float32)
    if joint_angles.ndim == 1:
        joint_angles = joint_angles[None, :]
    assert joint_angles.ndim == 2 and joint_angles.shape[-1] == 16, (
        f"Expected joint_angles of shape (T, 16) or (16,), got {joint_angles.shape}"
    )

    kinematic_chain = get_kinematic_chain(urdf_path)
    # Dict keyed by Leap joint name so order matches hand_ss.urdf regardless of
    # serial-chain enumeration quirks.
    joint_angles_t = torch.tensor(joint_angles).float()
    joint_dict = {
        name: joint_angles_t[:, i] for i, name in enumerate(LEAP_JOINT_ORDER)
    }
    joint_poses = kinematic_chain.forward_kinematics(joint_dict)

    positions = []
    rotations = []
    for k, num_sensors in XELA_FLATTEN_ORDER.items():
        joint_pose = joint_poses[k].get_matrix().numpy()  # (T, 4, 4)
        xx, yy, d = get_sensor_grid(k)
        sensor_local = np.stack([xx.flatten(), yy.flatten()], axis=-1)
        sensor_local = np.concatenate(
            [sensor_local, np.zeros_like(sensor_local)], axis=-1
        )
        sensor_local[..., -2] = d
        sensor_local[..., -1] = 1  # (S, 4) homogeneous

        t = joint_pose.shape[0]
        pose_rep = einops.repeat(joint_pose, "t i j -> t s i j", s=num_sensors)
        pose_flat = einops.rearrange(pose_rep, "t s i j -> (t s) i j")
        local_flat = einops.repeat(sensor_local, "s c -> (t s) c", t=t)
        world_h = np.einsum("m i j, m j -> m i", pose_flat, local_flat)

        pose_flat[..., :, 3] = world_h
        pose_ts = einops.rearrange(pose_flat, "(t s) i j -> t s i j", s=num_sensors)
        positions.append(pose_ts[..., :3, 3])
        rotations.append(pose_ts[..., :3, :3])

    positions = np.concatenate(positions, axis=1)
    rotations = np.concatenate(rotations, axis=1)
    if mujoco_world:
        positions, rotations = urdf_base_to_mujoco_world(positions, rotations)
    return positions, rotations


def get_fk_taxels(joint_angles, urdf_path=None, mujoco_world: bool = True):
    """Forward-kinematics of all Xela taxel positions from Leap joint angles.

    Run FK on ``hand_ss.urdf``, then map each patch link frame onto its sensor
    grid. Defaults to MuJoCo world coordinates (see ``get_fk_taxel_frames``).

    Parameters
    ----------
    joint_angles : array-like, shape (16,) or (T, 16)
        Leap joint positions (radians) in ``LEAP_JOINT_ORDER``.
    urdf_path : path-like, optional
        Path to ``hand_ss.urdf``. Defaults to xela_description share.
    mujoco_world : bool
        If True (default), map into MuJoCo world (Z-up).

    Returns
    -------
    sensor_positions : np.ndarray, shape (T, 368, 3)
        XYZ positions of all taxels (same flatten order as ``XELA_FLATTEN_ORDER``).
    """
    positions, _ = get_fk_taxel_frames(
        joint_angles, urdf_path=urdf_path, mujoco_world=mujoco_world
    )
    return positions


def world_forces_to_local(forces_world: np.ndarray, rotations: np.ndarray) -> np.ndarray:
    """Convert world-frame taxel forces to sensor-local using FK rotations.

    ``rotations`` maps sensor-local → hand/world (from ``get_fk_taxel_frames``),
    so ``f_local = R^T @ f_world``.
    """
    forces_world = np.asarray(forces_world, dtype=np.float64)
    rotations = np.asarray(rotations, dtype=np.float64)
    return np.einsum("nji,nj->ni", rotations, forces_world)


def joint_state_to_angles(msg: JointState, joint_names: list[str]) -> np.ndarray:
    """Extract a (16,) joint vector in ``joint_names`` order from JointState."""
    name_to_pos = {
        n: float(p) for n, p in zip(msg.name, msg.position) if np.isfinite(p)
    }
    q = np.zeros(16, dtype=np.float32)
    for i, name in enumerate(joint_names[:16]):
        if name in name_to_pos:
            q[i] = name_to_pos[name]
        elif i < len(msg.position):
            # Fall back to positional order when names do not match.
            q[i] = float(msg.position[i])
    return q


def hand_sensors_to_forces_world(msg: HandSensors) -> np.ndarray:
    """Pack HandSensors texels into (368, 3) forces in FK flatten order.

    ``process_hand_sensors_into_pointcloud`` publishes contact / xfrc forces in
    the world frame, keyed by hardware ``taxel_id``. Values are reordered to
    match ``XELA_FLATTEN_ORDER`` / ``TAXEL_IDS_IN_FK_ORDER`` so they align with
    FK positions and rotations.
    """
    by_id = np.zeros((368, 3), dtype=np.float64)
    for texel in msg.texels:
        tid = int(texel.taxel_id)
        if 0 <= tid < 368:
            by_id[tid, 0] = float(texel.fx)
            by_id[tid, 1] = float(texel.fy)
            by_id[tid, 2] = float(texel.fz)
    return by_id[TAXEL_IDS_IN_FK_ORDER]


class FkTaxelsNode(Node):
    """Run taxel FK on incoming joint states and publish ``TaxelFrames``."""

    def __init__(self) -> None:
        super().__init__("fk_taxels")

        joint_topic = self.declare_parameter("joint_topic", "xela_joint_publisher").value
        sensors_topic = self.declare_parameter("hand_sensors_topic", "hand_sensors").value
        output_topic = self.declare_parameter("taxel_frames_topic", "taxel_frames").value
        urdf_path = self.declare_parameter("urdf_path", str(DEFAULT_URDF_PATH)).value
        joint_names = self.declare_parameter("joint_names", LEAP_JOINT_ORDER).value
        self._frame_id = self.declare_parameter("frame_id", "world").value
        publish_rate_hz = float(self.declare_parameter("publish_rate_hz", 30.0).value)

        self._joint_names = list(joint_names)
        self._urdf_path = Path(urdf_path)
        self._lock = threading.Lock()
        self._joint_angles: np.ndarray | None = None
        self._forces_world: np.ndarray | None = None
        self._updated = False

        # Warm the FK chain once so the first frame is fast.
        get_kinematic_chain(self._urdf_path)

        self._pub = self.create_publisher(TaxelFrames, output_topic, 10)
        self.create_subscription(JointState, joint_topic, self._on_joint_state, 10)
        self.create_subscription(HandSensors, sensors_topic, self._on_hand_sensors, 10)
        self.create_timer(1.0 / publish_rate_hz, self._on_timer)

        self.get_logger().info(
            f"Listening for joints on '{joint_topic}' and sensors on '{sensors_topic}', "
            f"publishing TaxelFrames on '{output_topic}' at up to {publish_rate_hz:.0f} Hz"
        )

    def _on_joint_state(self, msg: JointState) -> None:
        q = joint_state_to_angles(msg, self._joint_names)
        with self._lock:
            self._joint_angles = q
            self._updated = True

    def _on_hand_sensors(self, msg: HandSensors) -> None:
        forces = hand_sensors_to_forces_world(msg)
        with self._lock:
            self._forces_world = forces
            self._updated = True

    def _on_timer(self) -> None:
        with self._lock:
            if not self._updated or self._joint_angles is None:
                return
            self._updated = False
            q = self._joint_angles.copy()
            f_world = None if self._forces_world is None else self._forces_world.copy()

        pos, rot = get_fk_taxel_frames(q, urdf_path=self._urdf_path)
        pos, rot = pos[0], rot[0]

        out = TaxelFrames()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = self._frame_id
        out.taxel_ids = TAXEL_IDS_IN_FK_ORDER.tolist()
        out.patch_ids = PATCH_IDS_IN_FK_ORDER.tolist()
        out.positions = pos.astype(np.float32).ravel().tolist()
        out.rotations = rot.astype(np.float32).ravel().tolist()
        if f_world is not None:
            f_local = world_forces_to_local(f_world, rot)
            out.forces_world = f_world.astype(np.float32).ravel().tolist()
            out.forces_local = f_local.astype(np.float32).ravel().tolist()
        self._pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = FkTaxelsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
