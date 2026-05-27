import argparse
import os
import time

import pybullet as p


def disable_body_collision(body_id: int) -> None:
    """Turn off all collisions for a PyBullet multibody."""
    for link_idx in range(-1, p.getNumJoints(body_id)):
        p.setCollisionFilterGroupMask(body_id, link_idx, 0, 0)

def load_hand(is_left: bool = False, gui: bool = True):
    """Connect to PyBullet and load the LeapXela hand URDF.

    Args:
        is_left: Load left-hand model if True (not implemented).
        gui: Use GUI connection if True, DIRECT otherwise.

    Returns:
        tuple[int, int]: (leap_body_id, num_joints)
    """
    if is_left:
        raise ValueError("Left hand is not implemented")

    if gui:
        p.connect(p.GUI)
    else:
        p.connect(p.DIRECT)

    path_src = os.path.dirname(os.path.abspath(__file__))
    urdf_dir = os.path.join(path_src, "leapXela_right")
    urdf_path = os.path.join(urdf_dir, "hand.urdf")

    p.setAdditionalSearchPath(urdf_dir)

    base_position = [-0.12, 0.035, -0.01]

    base_orientation = p.getQuaternionFromEuler([1.57, -1.57, -1.57])
    leap_id = p.loadURDF(
        urdf_path,
        base_position,
        base_orientation,
        useFixedBase=True,
    )

    disable_body_collision(leap_id)

    urdf_path = os.path.join(path_src, "leap_hand_mesh_right/robot_pybullet.urdf")
    base_position = [-0.22, 0.01, 0.03]
    base_orientation = p.getQuaternionFromEuler([1.57, 0, 3.14])

    leap_id = p.loadURDF(
        urdf_path,
        base_position,
        base_orientation,
        useFixedBase=True,
    )
    
    disable_body_collision(leap_id)

    num_joints = p.getNumJoints(leap_id)
    p.setGravity(0, 0, 0)
    p.setRealTimeSimulation(0)

    return leap_id, num_joints


def parse_args():
    parser = argparse.ArgumentParser(description="Load LeapXela hand model in PyBullet.")
    hand = parser.add_mutually_exclusive_group(required=True)
    hand.add_argument("--left", action="store_true", help="Load left hand")
    hand.add_argument("--right", action="store_true", help="Load right hand")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use DIRECT connection instead of GUI",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    leap_id, num_joints = load_hand(is_left=args.left, gui=not args.direct)
    print(f"Loaded hand body id={leap_id}, joints={num_joints}")

    while True:
        p.stepSimulation()
        time.sleep(1.0 / 240.0)
