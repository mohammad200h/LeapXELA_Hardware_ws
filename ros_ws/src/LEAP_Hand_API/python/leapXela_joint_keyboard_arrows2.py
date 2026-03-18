import os
import sys
import time
import curses

import numpy as np

# Ensure we can import the sibling script when run directly.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from leapXela_keyboard import LeapNode  # Reuse the same Dynamixel/hand setup


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


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


FORBIDDEN_JOINT_INDICES = [4, 5, 6, 7]


def sync_forbidden_joints_to_current(leap_hand, desired_joint_degrees):
    """
    Prevent actively commanding joints we want to leave alone.

    We still call `set_joints_degrees()` which writes all 16 motors, so we
    overwrite the forbidden indices with the motors' current measured angles
    right before each write.
    """
    current_degrees = leap_hand.read_pos_degrees()
    for idx in FORBIDDEN_JOINT_INDICES:
        desired_joint_degrees[idx] = current_degrees[idx]


def run_curses(leap_hand, desired_joint_degrees, min_angle, max_angle, step_degrees):
    # Active joint index in range [0..15].
    # Left/Right changes this index; Up/Down changes only this joint's degree value.
    active_joint = 3  # Match the original thumb-phalanx index used in leapXela_keyboard.py

    stdscr = curses.initscr()
    try:
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        stdscr.nodelay(True)

        last_msg = "Use arrows to control joints, 'q' to quit."

        while True:
            key = stdscr.getch()
            did_change = False

            if key != -1:
                if key in (ord("q"), ord("Q")):
                    break
                elif key == curses.KEY_LEFT:
                    active_joint = (active_joint - 1) % 16
                    did_change = True
                    last_msg = f"Selected joint {active_joint}: {JOINT_LABELS[active_joint]}"
                elif key == curses.KEY_RIGHT:
                    active_joint = (active_joint + 1) % 16
                    did_change = True
                    last_msg = f"Selected joint {active_joint}: {JOINT_LABELS[active_joint]}"
                elif key == curses.KEY_UP:
                    new_val = desired_joint_degrees[active_joint] + step_degrees
                    #desired_joint_degrees[active_joint] = clamp(new_val, min_angle, max_angle)
                    desired_joint_degrees[active_joint] = new_val
                    did_change = True
                    last_msg = (
                        f"Increased joint {active_joint} -> {desired_joint_degrees[active_joint]:.1f} deg"
                    )
                elif key == curses.KEY_DOWN:
                    new_val = desired_joint_degrees[active_joint] - step_degrees
                    #desired_joint_degrees[active_joint] = clamp(new_val, min_angle, max_angle)
                    desired_joint_degrees[active_joint] = new_val
                    did_change = True
                    last_msg = (
                        f"Decreased joint {active_joint} -> {desired_joint_degrees[active_joint]:.1f} deg"
                    )

            # Only write to motors on value changes (Up/Down).
            if did_change and key in (curses.KEY_UP, curses.KEY_DOWN):
                sync_forbidden_joints_to_current(leap_hand, desired_joint_degrees)
                leap_hand.set_joints_degrees(desired_joint_degrees)

            stdscr.erase()
            stdscr.addstr(0, 0, "LEAP Hand Joint Control (Arrow Keys)")
            stdscr.addstr(2, 0, f"Selected joint: {active_joint} / 15")
            stdscr.addstr(3, 0, f"Label: {JOINT_LABELS[active_joint]}")
            stdscr.addstr(4, 0, f"Desired value: {desired_joint_degrees[active_joint]:.1f} deg")
            stdscr.addstr(6, 0, f"Step: +/- {step_degrees:.1f} deg")
            stdscr.addstr(7, 0, f"Clamp range: {min_angle:.1f} .. {max_angle:.1f} deg")
            stdscr.addstr(9, 0, last_msg)
            stdscr.addstr(11, 0, "Controls: Left/Right select joint, Up/Down adjust value, q to quit")
            stdscr.refresh()

            time.sleep(0.02)
    finally:
        # Always attempt to restore terminal settings.
        try:
            curses.nocbreak()
            stdscr.keypad(False)
            curses.echo()
            curses.endwin()
        except Exception:
            pass


def main():
    # Same style of constraints as the original sinusoidal script.
    min_angle = 120.0
    max_angle = 40.0
    step_degrees = 5.0

    leap_hand = LeapNode()

    # Base joint configuration (16 joints total), matching leapXela_keyboard.py.
    desired_joint_degrees = [
        180,
        80,
        180,
        130,  # Index finger
        180,
        180,
        180,
        180,  # Middle finger
        180,
        180,
        180,
        180,  # Ring finger
        180,
        180,
        180,
        180,  # Thumb (indices 12..15)
    ]

    print("Initializing motors to base configuration...")
    sync_forbidden_joints_to_current(leap_hand, desired_joint_degrees)
    leap_hand.set_joints_degrees(desired_joint_degrees)
    time.sleep(0.5)

    try:
        # Curses must own the terminal while we listen for arrow keys.
        run_curses(leap_hand, desired_joint_degrees, min_angle, max_angle, step_degrees)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nDisconnecting...")
        try:
            leap_hand.safe_disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()

