# Initial Setup

# Terminator 1
'''
ros2 launch xela_data_collection xela_server_and_client.launch
'''

# Terminator 2
'''
cd ros_ws
colcon build --symlink-install
source install/leap_hand/share/setup.sh
bash shell/run_xela_server_leap.sh
'''