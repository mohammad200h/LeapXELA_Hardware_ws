## Topics:

/cmd_xela
/leap_state
/xServTopic
/leap_image
/leap_image_normalized

## Nodes:

1. leaphand_node:
    * subscribed to: 
        * topic `/cmd_xela` -- sensor_msgs/JointState: desired joint positions (16 floats)
    * publishes to: 
        * topic `/leap_state` -- sensor_msgs/JointState: actual position, velocity, effort arrays (16 each) with header stamp
    * services offered:
        * `leap_position` -- leap_hand/srv/LeapPosition: returns current position vector
        * `leap_velocity` -- leap_hand/srv/LeapVelocity: returns current velocity vector
        * `leap_effort` -- leap_hand/srv/LeapEffort: returns current effort/current vector
        * `leap_state` -- leap_hand/srv/LeapState: returns full state (position, velocity, effort)

2. keyboard_node:
    * subscribed to:
        * (none; reads local keyboard input)
    * publishes to:
        * topic `/cmd_xela` -- sensor_msgs/JointState: interactive desired joint positions (16 floats)
    * services offered:
        * (none)

3. xSensorService_node (xela_service):
    * subscribed to:
        * external WebSocket `ws://<ip>:<port>` (non-ROS) -- JSON sensor frames: sensor id, time, model, taxels as hex string, taxel count, calibrated forces
    * publishes to:
        * topic `/xServTopic` -- xela_server_ros2/msg/SensStream: sequence of `SensorFull` messages containing sensor id/pos, time, model, list of `Taxel` (x,y,z ints) and list of `Forces` (x,y,z floats)
    * services offered:
        * `xServStream` -- xela_server_ros2/srv/XelaSensorStream: synchronous snapshot request/response (sensor==0 => all sensors)

4. xela_image_publisher (LeapXelaImagePublisher):
    * subscribed to:
        * topic `/xServTopic` -- xela_server_ros2/msg/SensStream: incoming sensor taxel messages
        * service client `xServStream` -- xela_server_ros2/srv/XelaSensorStream: optional snapshot requests
    * publishes to:
        * topic `/leap_image` -- sensor_msgs/Image: raw taxel grid mapped to (26x31x3) with int32 backing (published encoding "32FC3" but contains int32 bytes)
        * topic `/leap_image_normalized` -- sensor_msgs/Image: normalized float32 image (26x31x3, encoding "32FC3")
    * services offered:
        * (none)

5. xela_data_collector:
    * subscribed to:
        * topic `/leap_image` -- sensor_msgs/Image: raw image bytes (26x31x3)
        * topic `/leap_image_normalized` -- sensor_msgs/Image: normalized float32 image (26x31x3)
        * topic `/leap_state` -- sensor_msgs/JointState: hand state (position, velocity, effort + header stamps)
    * publishes to:
        * (none)
    * behavior:
        * stores synchronized frames (raw_image, normalized_image) and hand state into HDF5 files (datasets: images, state.position/velocity/effort/name, timestamps, frame_id)

## Services:

`leap_position` (service) — type: leap_hand/srv/LeapPosition  
`leap_velocity` (service) — type: leap_hand/srv/LeapVelocity  
`leap_effort` (service) — type: leap_hand/srv/LeapEffort  
`leap_state` (service) — type: leap_hand/srv/LeapState  
`xServStream` (service) — type: xela_server_ros2/srv/XelaSensorStream