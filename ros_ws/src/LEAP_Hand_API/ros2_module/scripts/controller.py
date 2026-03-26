import os
import sys
import time
import threading
import termios

import numpy as np
from leap_hand_utils.dynamixel_client import *
import leap_hand_utils.leap_hand_utils as lhu
from pynput import keyboard

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

from node import LeapNode

JOINT_LABELS = [
    "Index MCP Side",
    "Index MCP Forward",
    "Index PIP",
    "Index DIP",
    "Middle MCP Side",
    "Middle MCP Forward",
    "Middle PIP",
    "Middle DIP",
    "Ring MCP Side",
    "Ring MCP Forward",
    "Ring PIP",
    "Ring DIP",
    "Thumb MCP Side",
    "Thumb Rotation",
    "Thumb MCP Forward",
    "Thumb Phalange",
]

def float_seconds_to_nanoseconds(float_seconds: float) -> int:
    """Convert floating-point seconds to canonical integer nanoseconds (matching logger requirements)."""
    NS_PER_SEC = 1_000_000_000
    return int(round(float(float_seconds) * NS_PER_SEC))

def create_joint_state_msg(desired_joint_degrees):
    """Create a JointState message with proper timestamp for logger alignment."""
    msg = JointState()
    
    # Get current time and convert to nanoseconds using logger's conversion
    current_time_sec = time.time()
    timestamp_ns = float_seconds_to_nanoseconds(current_time_sec)
    
    # Convert back to sec/nanosec format for ROS2 header
    msg.header.stamp.sec = int(timestamp_ns // 1_000_000_000)
    msg.header.stamp.nanosec = int(timestamp_ns % 1_000_000_000)
    
    # Set joint positions (all 16 joints in degrees)
    msg.position = [float(deg) for deg in desired_joint_degrees]
    
    return msg
    
FORBIDDEN_JOINT_INDICES = [] #[4, 5, 6, 7]


def sync_forbidden_joints_to_current(leap_hand, desired_joint_degrees):
    """
    Prevent actively commanding joints we want to leave alone.

    We still call `set_joints_degrees()` which writes all 16 motors, so we
    overwrite the forbidden indices with the motors' current measured angles
    right before each write.
    """
    if not FORBIDDEN_JOINT_INDICES:
        return

    current_degrees = leap_hand.read_pos_degrees()
    for idx in FORBIDDEN_JOINT_INDICES:
        desired_joint_degrees[idx] = current_degrees[idx]

def get_current_joint_degree_for_active_joint(leap_hand, active_joint):
    current_degrees = leap_hand.read_pos_degrees()
    return current_degrees[active_joint]

def get_joint_limits(joint_idx, limits):
    # Map joint index to limits dictionary and sub-index
    if 0 <= joint_idx <= 3:
        group = 'th'
        subidx = joint_idx
    elif 4 <= joint_idx <= 7:
        group = 'if'
        subidx = joint_idx - 4
    elif 8 <= joint_idx <= 11:
        group = 'mf'
        subidx = joint_idx - 8
    elif 12 <= joint_idx <= 15:
        group = 'rf'
        subidx = joint_idx - 12
    else:
        return None, None
    ll = limits[group]['ll'][subidx]
    ul = limits[group]['ul'][subidx]
    return (min(ll, ul), max(ll, ul))

def run_pynput(leap_hand, desired_joint_degrees, limits, step_degrees, joint_publisher):
    state = {
        "active_joint": 4,
        "last_msg": "Use arrows to control joints, 'q' to quit.",
        "running": True,
    }
    lock = threading.Lock()

    def on_press(key):
        with lock:
            did_change = False
            is_adjustment = False

            if key == keyboard.Key.left:
                state["active_joint"] = (state["active_joint"] - 1) % 16
                did_change = True
                state["last_msg"] = (
                    f"Selected joint {state['active_joint']}: {JOINT_LABELS[state['active_joint']]}"
                )
            elif key == keyboard.Key.right:
                state["active_joint"] = (state["active_joint"] + 1) % 16
                did_change = True
                state["last_msg"] = (
                    f"Selected joint {state['active_joint']}: {JOINT_LABELS[state['active_joint']]}"
                )
            elif key == keyboard.Key.up:
                joint = state["active_joint"]
                new_val = desired_joint_degrees[joint] + step_degrees
                min_lim, max_lim = get_joint_limits(joint, limits)
                desired_joint_degrees[joint] = max(min(new_val, max_lim), min_lim)
                did_change = True
                is_adjustment = True
                state["last_msg"] = (
                    f"Increased joint {joint} -> {desired_joint_degrees[joint]:.1f} deg (clamped {min_lim}-{max_lim})"
                )
            elif key == keyboard.Key.down:
                joint = state["active_joint"]
                new_val = desired_joint_degrees[joint] - step_degrees
                min_lim, max_lim = get_joint_limits(joint, limits)
                desired_joint_degrees[joint] = max(min(new_val, max_lim), min_lim)
                did_change = True
                is_adjustment = True
                state["last_msg"] = (
                    f"Decreased joint {joint} -> {desired_joint_degrees[joint]:.1f} deg (clamped {min_lim}-{max_lim})"
                )
            else:
                try:
                    if key.char and key.char.lower() == "q":
                        state["running"] = False
                        return False
                except AttributeError:
                    pass

            if did_change and is_adjustment:
                sync_forbidden_joints_to_current(leap_hand, desired_joint_degrees)
                leap_hand.set_joints_degrees(desired_joint_degrees)

    print("LEAP Hand Joint Control (pynput)")
    print("Controls: Left/Right select joint, Up/Down adjust value, q to quit")

    stdin_fd = sys.stdin.fileno()
    old_attrs = None
    if sys.stdin.isatty():
        old_attrs = termios.tcgetattr(stdin_fd)
        new_attrs = termios.tcgetattr(stdin_fd)
        new_attrs[3] = new_attrs[3] & ~termios.ECHO  # lflags: disable local echo
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, new_attrs)

    try:
        with keyboard.Listener(on_press=on_press) as listener:
            current_degree = get_current_joint_degree_for_active_joint(leap_hand, state["active_joint"])
            print(f"Current degree: {current_degree}")
            while state["running"]:
                with lock:
                    joint = state["active_joint"]
                    status = (
                        f"Selected joint: {joint}/15 | "
                        f"Label: {JOINT_LABELS[joint]} | "
                        f"Desired: {desired_joint_degrees[joint]:.1f} deg | "
                        f"Step: +/- {step_degrees:.1f} deg | "
                        # f"Clamp: {min_lim:.1f}..{max_lim:.1f} deg"
                    )
                    msg = state["last_msg"]
                    
                    # Publish joint state at each iteration
                    joint_msg = create_joint_state_msg(desired_joint_degrees)
                    joint_publisher.publish(joint_msg)
                
                print(f"\r{status} | {msg}    ", end="", flush=True)
                time.sleep(0.05)

            listener.join()
    finally:
        if old_attrs is not None:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_attrs)
    print()

def main():
    # Initialize ROS2
    rclpy.init(args=None)
    
    # Create a minimal ROS2 node for publishing
    node = rclpy.create_node('leap_hand_controller')
    joint_publisher = node.create_publisher(JointState, '/leap_joint_states', 10)
    
    # Same style of constraints as the original sinusoidal script.
    min_angle = 120.0
    max_angle = 40.0
    step_degrees = 5.0

    # Initialize the LeapNode and set all joints to 0 degrees
    leap_node = LeapNode()

    # Finger-joint mapping
    fingers = {
        "joints_name":["mcp","rot","pip","dip"],
        "ll":[270,185,195,180],
        "ul":[150,90,165,85]
    }
    thumb = {
        "joints_name":["cmc","axl","mcp","ipl"],
        "ll":[105,110,215,155],
        "ul":[15,5,35,295]
    }

    limits = {
        "if":{
            "id":[4,5,6,7],
            "ll":fingers["ll"],
            "ul":fingers["ul"],
        },
        "mf":{
            "id":[8,9,10,11],
            "ll":fingers["ll"],
            "ul":fingers["ul"],
        },
        "rf":{
            "id":[12,13,14,15],
            "ll":fingers["ll"],
            "ul":fingers["ul"],
        },
        "th":{
            "id":[0,1,2,3],
            "ll":thumb["ll"],
            "ul":thumb["ul"],
        },
    }

    # Set to flat palm
    default = [
        180,  # Thumb: th_cmc
        180,  # Thumb: th_axl
        180,  # Thumb: th_mcp_active
        180,  # Thumb: th_ipl_act
        265,  # Index finger: if_mcp (extended)
        180,
        180,
        180,
        265,  # Middle finger: mf_mcp (extended)
        180,
        180,
        180,
        265,  # Ring finger: rf_mcp (extended)
        180,
        180,
        180,
    ]

    print("Initializing motors to base configuration...")
    sync_forbidden_joints_to_current(leap_node, default)
    leap_node.set_joints_degrees(default)
    time.sleep(5.0)  # Give time to reach initial position

    # Keyboard control
    try:
        run_pynput(leap_node, default, limits, step_degrees, joint_publisher)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nDisconnecting...")
        try:
            leap_node.safe_disconnect()
        except Exception:
            pass
        finally:
            # Cleanup ROS2 resources
            node.destroy_publisher(joint_publisher)
            rclpy.shutdown()


if __name__ == "__main__":
    main()