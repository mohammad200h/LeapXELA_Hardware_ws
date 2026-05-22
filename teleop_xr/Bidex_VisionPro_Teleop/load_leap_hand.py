import argparse
import os
import time

import pybullet as p

# Fingertip / realtip link indices (matches avp_leap.py)
LEAP_END_EFFECTOR_INDEX = [3, 4, 8, 9, 13, 14, 18, 19]

# Per-link RGBA for meshes; RGB prefix is used for addUserDebugText (textColorRGB).
# Colors follow avp_leap.py target balls: R, G, B, white (thumb).
EE_LINK_COLORS: dict[int, list[float]] = {
    3: [1, 0, 0, 1],
    4: [1, 0, 0, 1],
    8: [0, 1, 0, 1],
    9: [0, 1, 0, 1],
    13: [0, 0, 1, 1],
    14: [0, 0, 1, 1],
    18: [1, 1, 1, 1],
    19: [1, 1, 1, 1],
}

# Local offset (meters) for labels in each link frame (see addUserDebugText + parentLinkIndex).
EE_TEXT_OFFSET = [0, 0, 0.012]


def _decode_name(name) -> str:
    return name.decode("utf-8") if isinstance(name, bytes) else str(name)


def get_link_name(body_id: int, link_idx: int) -> str:
    if link_idx == -1:
        return _decode_name(p.getBodyInfo(body_id)[0])
    return _decode_name(p.getJointInfo(body_id, link_idx)[12])


def setup_end_effector_visuals(body_id: int) -> list[int]:
    """Show only EE links, tint them, and attach matching-colored debug text.

    PyBullet debug text API (GUI only):
      addUserDebugText(text, textPosition, textColorRGB, textSize=...,
                       lifeTime=0, parentObjectUniqueId=..., parentLinkIndex=...)
    textColorRGB is [r, g, b] in 0..1. With parentLinkIndex set, textPosition is
    in the link's local frame and follows the link during simulation.
    """
    visible = set(LEAP_END_EFFECTOR_INDEX)
    num_joints = p.getNumJoints(body_id)
    for link_idx in range(-1, num_joints):
        if link_idx not in visible:
            p.changeVisualShape(body_id, link_idx, rgbaColor=[0, 0, 0, 0])

    debug_ids: list[int] = []
    for link_idx in LEAP_END_EFFECTOR_INDEX:
        rgba = EE_LINK_COLORS[link_idx]
        p.changeVisualShape(body_id, link_idx, rgbaColor=rgba)
        rgb = rgba[:3]
        label = f"{link_idx}: {get_link_name(body_id, link_idx)}"
        debug_id = p.addUserDebugText(
            label,
            EE_TEXT_OFFSET,
            rgb,
            textSize=1.0,
            lifeTime=0,
            parentObjectUniqueId=body_id,
            parentLinkIndex=link_idx,
        )
        debug_ids.append(debug_id)
    return debug_ids


def load_hand(
    is_left: bool = True,
    gui: bool = True,
    show_end_effector: bool = False,
):
    """Connect to PyBullet and load the LEAP hand URDF.

    Args:
        is_left: Load left-hand mesh/poses if True, right-hand otherwise.
        gui: Use GUI connection if True, DIRECT otherwise.
        show_end_effector: If True, hide non-EE links and show colored EE labels.

    Returns:
        tuple[int, int, list[int]]: (leap_body_id, num_joints, debug_text_ids)
    """
    if gui:
        p.connect(p.GUI)
    else:
        p.connect(p.DIRECT)

    path_src = os.path.dirname(os.path.abspath(__file__))

    if is_left:
        urdf_path = os.path.join(path_src, "leap_hand_mesh_left/robot_pybullet.urdf")
        base_position = [0.31, 0.01, 0.06]
        base_orientation = p.getQuaternionFromEuler([1.57, 0, 0])
    else:
        urdf_path = os.path.join(path_src, "leap_hand_mesh_right/robot_pybullet.urdf")
        base_position = [-0.22, 0.01, 0.03]
        base_orientation = p.getQuaternionFromEuler([1.57, 0, 3.14])

    leap_id = p.loadURDF(
        urdf_path,
        base_position,
        base_orientation,
        useFixedBase=True,
    )

    debug_text_ids: list[int] = []
    if show_end_effector and gui:
        debug_text_ids = setup_end_effector_visuals(leap_id)

    num_joints = p.getNumJoints(leap_id)
    p.setGravity(0, 0, 0)
    p.setRealTimeSimulation(0)

    return leap_id, num_joints, debug_text_ids


def parse_args():
    parser = argparse.ArgumentParser(description="Load LEAP hand model in PyBullet.")
    hand = parser.add_mutually_exclusive_group(required=True)
    hand.add_argument("--left", action="store_true", help="Load left hand")
    hand.add_argument("--right", action="store_true", help="Load right hand")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use DIRECT connection instead of GUI",
    )
    parser.add_argument(
        "--show-end-effector",
        action="store_true",
        help="Show only end-effector links with colored labels (requires GUI)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    leap_id, num_joints, _ = load_hand(
        is_left=args.left,
        gui=not args.direct,
        show_end_effector=args.show_end_effector,
    )
    print(f"Loaded hand body id={leap_id}, joints={num_joints}")

    while True:
        p.stepSimulation()
        time.sleep(1.0 / 240.0)
