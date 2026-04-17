#!/usr/bin/env python3

import numpy as np


# Topic names
COMMAND_TOPIC = "cmd_xela"
STATE_TOPIC = "leap_state"


# Queue depths and timer periods
# PositionNode publisher -> LeapXELANode subscriber use the same queue depth.
COMMAND_QUEUE_DEPTH = 50
STATE_QUEUE_DEPTH = 50
LEAPHAND_STATE_PUBLISH_PERIOD_SEC = 0.1


# PositionNode declared parameter defaults
POSITION_NODE_DEFAULT_CSV_PATH = ""
POSITION_NODE_DEFAULT_CSV_FILENAME = "beer_bottle.csv"
POSITION_NODE_DEFAULT_SOURCE_UNITS = "radians"
POSITION_NODE_DEFAULT_SAMPLE_STRIDE = 1
POSITION_NODE_DEFAULT_INTERPOLATION_STEPS = 25
POSITION_NODE_DEFAULT_PUBLISH_PERIOD_SEC = 0.02


# LEAP hand hardware configuration
MOTOR_IDS = [i for i in range(16)]
SIDE_TO_SIDE_MOTOR_IDS = [0, 4, 8]
DEFAULT_ZERO_STATE_RAD = np.zeros(16)


# PID / current limit defaults used by LeapXelaBase
PID_KP = 600
PID_KI = 0
PID_KD = 200
CURRENT_LIMIT_MA = 550
SIDE_TO_SIDE_KP_SCALE = 0.75
SIDE_TO_SIDE_KD_SCALE = 0.75


# Dynamixel bring-up toggle and connection candidates.
# Set to False to skip all real hardware connection/configuration in LeapXelaBase.__init__.
ENABLE_DXL_CLIENT_INIT = True
DYNAMIXEL_CONNECTION_CANDIDATES = [
    {
        "port": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTA2U1HJ-if00-port0",
        "baudrate": 4000000,
        "label": "/dev/serial/by-id (ttyUSB4)",
    },
    {
        "port": "/dev/ttyUSB0",
        "baudrate": 57600,
        "label": "/dev/ttyUSB0",
    },
    {
        "port": "/dev/ttyUSB1",
        "baudrate": 4000000,
        "label": "/dev/ttyUSB1",
    },
    {
        "port": "COM13",
        "baudrate": 4000000,
        "label": "COM13",
    },
]


# Installed config asset names
POSE_CONFIG_FILENAME = "pose.json"
