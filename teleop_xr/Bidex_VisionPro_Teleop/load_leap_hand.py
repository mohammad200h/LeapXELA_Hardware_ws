import argparse
import os
import time

import pybullet as p


def load_hand(is_left: bool = True, gui: bool = True):
    """Connect to PyBullet and load the LEAP hand URDF.

    Args:
        is_left: Load left-hand mesh/poses if True, right-hand otherwise.
        gui: Use GUI connection if True, DIRECT otherwise.

    Returns:
        tuple[int, int]: (leap_body_id, num_joints)
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

    num_joints = p.getNumJoints(leap_id)
    p.setGravity(0, 0, 0)
    p.setRealTimeSimulation(0)

    return leap_id, num_joints


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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    leap_id, num_joints = load_hand(is_left=args.left, gui=not args.direct)
    print(f"Loaded hand body id={leap_id}, joints={num_joints}")

    while True:
        p.stepSimulation()
        time.sleep(1.0 / 240.0)
