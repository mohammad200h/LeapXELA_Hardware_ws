import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/workspace/LeapXELA_Hardware_ws/ros_ws/src/install/dex_retargeting'
