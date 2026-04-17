
import numpy as np
from leap_hand_utils.dynamixel_client import *
import leap_hand_utils.leap_hand_utils as lhu
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
import json
from leap_globals import (
    CURRENT_LIMIT_MA,
    DEFAULT_ZERO_STATE_RAD,
    DYNAMIXEL_CONNECTION_CANDIDATES,
    ENABLE_DXL_CLIENT_INIT,
    MOTOR_IDS,
    PID_KD,
    PID_KI,
    PID_KP,
    POSE_CONFIG_FILENAME,
    SIDE_TO_SIDE_KD_SCALE,
    SIDE_TO_SIDE_KP_SCALE,
    SIDE_TO_SIDE_MOTOR_IDS,
)

def load_pose(pose_name):
    pose_path = Path(get_package_share_directory('leap_hand')) / 'config' / POSE_CONFIG_FILENAME
    with pose_path.open('r', encoding='utf-8') as f:
        pose = json.load(f)

    return pose[pose_name]

class LeapXelaBase:
    def __init__(self):
        self.kP = PID_KP
        self.kI = PID_KI
        self.kD = PID_KD
        self.curr_lim = CURRENT_LIMIT_MA
        self.prev_pos = self.pos = self.curr_pos = lhu.allegro_to_LEAPhand(DEFAULT_ZERO_STATE_RAD)
        self.motors = motors = list(MOTOR_IDS)
        self.hardware_enabled = ENABLE_DXL_CLIENT_INIT
        self.dxl_client = None

        if self.hardware_enabled:
            last_error = None
            for candidate in DYNAMIXEL_CONNECTION_CANDIDATES:
                try:
                    self.dxl_client = DynamixelClient(
                        motors,
                        candidate["port"],
                        candidate["baudrate"],
                    )
                    self.dxl_client.connect()
                    print(f"Connected via {candidate['label']}")
                    break
                except Exception as exc:
                    last_error = exc
                    self.dxl_client = None

            if self.dxl_client is None:
                raise RuntimeError(
                    "Failed to connect to LEAP hand on all configured ports."
                ) from last_error

            self.dxl_client.sync_write(motors, np.ones(len(motors)) * 5, 11, 1)
            self.dxl_client.set_torque_enabled(motors, True)
            self.dxl_client.sync_write(motors, np.ones(len(motors)) * self.kP, 84, 2)
            self.dxl_client.sync_write(
                SIDE_TO_SIDE_MOTOR_IDS,
                np.ones(len(SIDE_TO_SIDE_MOTOR_IDS)) * (self.kP * SIDE_TO_SIDE_KP_SCALE),
                84,
                2,
            )
            self.dxl_client.sync_write(motors, np.ones(len(motors)) * self.kI, 82, 2)
            self.dxl_client.sync_write(motors, np.ones(len(motors)) * self.kD, 80, 2)
            self.dxl_client.sync_write(
                SIDE_TO_SIDE_MOTOR_IDS,
                np.ones(len(SIDE_TO_SIDE_MOTOR_IDS)) * (self.kD * SIDE_TO_SIDE_KD_SCALE),
                80,
                2,
            )
            self.dxl_client.sync_write(motors, np.ones(len(motors)) * self.curr_lim, 102, 2)
        else:
            print("LEAP hardware initialization disabled in leap_globals.py")
 
    def set_joints_degrees(self, degrees_array):
        """Set all 16 joints using degree values (list or np.array of length 16)."""
        if len(degrees_array) != 16:
            print("Error: Please provide exactly 16 values (one per joint).")
            return
        if self.dxl_client is None:
            self.curr_pos = np.array(degrees_array, dtype=float)
            return
        try:
            radians_array = np.radians(degrees_array)
            self.dxl_client.write_desired_pos(self.motors, radians_array)
        except Exception as e:
            print(f"Warning: Failed to write joint positions: {e}")
    
    def safe_disconnect(self):
        """Safely disconnect from Dynamixel motors, handling I/O errors gracefully."""
        if hasattr(self, 'dxl_client') and self.dxl_client:
            try:
                # Try to disable torque first
                if self.dxl_client.is_connected:
                    self.dxl_client.port_handler.is_using = False
                    try:
                        self.dxl_client.set_torque_enabled(self.motors, False, retries=0)
                    except:
                        pass  # Ignore errors during torque disable
            except:
                pass  # Ignore errors during cleanup
            finally:
                try:
                    if self.dxl_client.is_connected:
                        self.dxl_client.port_handler.closePort()
                except:
                    pass  # Ignore I/O errors during port close
 
    def read_pos_degrees(self):
        """Read current joint positions and return in degrees."""
        if self.dxl_client is None:
            return np.array(self.curr_pos, dtype=float)
        pos_rad = self.dxl_client.read_pos()
        return np.degrees(pos_rad)

    def read_pos(self):
        if self.dxl_client is None:
            return np.radians(np.array(self.curr_pos, dtype=float))
        return self.dxl_client.read_pos()

    def read_vel(self):
        if self.dxl_client is None:
            return np.zeros(len(self.motors), dtype=float)
        return self.dxl_client.read_vel()

    def read_cur(self):
        if self.dxl_client is None:
            return np.zeros(len(self.motors), dtype=float)
        return self.dxl_client.read_cur()

    def read_pos_vel_cur(self):
        if self.dxl_client is None:
            pos = np.radians(np.array(self.curr_pos, dtype=float))
            vel = np.zeros(len(self.motors), dtype=float)
            cur = np.zeros(len(self.motors), dtype=float)
            return pos, vel, cur
        return self.dxl_client.read_pos_vel_cur()
 
