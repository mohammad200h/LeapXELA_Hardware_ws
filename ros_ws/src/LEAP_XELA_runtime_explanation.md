# LEAP + XELA ROS 2 Runtime Explanation

This document explains the two main packages in this workspace:

- `LEAP_Hand_API/ros2_module`, installed as the ROS 2 package `leap_hand`
- `xela_data_collection`, installed as the ROS 2 package `xela_data_collection`

It focuses on what happens when these launch files are run:

- `LEAP_Hand_API/ros2_module/launch/launch_leap.py`
- `xela_data_collection/launch/xela_server_and_client.launch.py`

The short version is:

- `launch_leap.py` starts the LEAP hand control node and a trajectory replay node.
- `xela_server_and_client.launch.py` starts the LEAP hand nodes, the XELA server/service bridge, an image publisher that turns XELA taxels into ROS images, and a collector that stores synchronized tactile images plus hand state to HDF5.

## Package Roles

### `LEAP_Hand_API/ros2_module`

This folder builds the ROS 2 package named `leap_hand`.

Its main runtime files are:

- `scripts/leaphand_node.py`
- `scripts/position_node.py`
- `scripts/base.py`
- `scripts/leap_globals.py`
- `launch/launch_leap.py`

The package provides the LEAP hand side of the system. It does three important jobs:

1. Creates the hardware-facing node, `leaphand_node`.
2. Publishes hand state on the ROS topic `leap_state`.
3. Replays a CSV trajectory through `position_node` by publishing commands on `cmd_xela`.

It also defines custom services:

- `LeapPosition`
- `LeapVelocity`
- `LeapEffort`
- `LeapState`

These are generated from the `.srv` files in `LEAP_Hand_API/ros2_module/srv`.

### `xela_data_collection`

This folder builds the ROS 2 package named `xela_data_collection`.

Its main runtime files are:

- `xela_data_collection/xela_image_publisher.py`
- `xela_data_collection/xela_data_collector.py`
- `xela_data_collection/leapXelaMap.py`
- `launch/xela_server_and_client.launch.py`

This package handles the tactile data side of the system. It does three important jobs:

1. Starts the XELA ROS bridge through the `xela_server_ros2` package.
2. Converts streamed XELA taxel readings into `sensor_msgs/Image` messages.
3. Saves synchronized raw image, normalized image, and LEAP hand state into `.h5` recordings.

It relies on a third package in the same `src` folder:

- `xela_server_ros2`

That package provides:

- `/xServTopic`
- `/xServStream`
- custom XELA messages such as `SensStream`, `SensorFull`, and `Taxel`

## Shared ROS Interfaces

The two systems talk through ROS topics and services.

### LEAP Hand Topics

| Topic | Message Type | Publisher | Subscriber | Purpose |
| --- | --- | --- | --- | --- |
| `cmd_xela` | `sensor_msgs/msg/JointState` | `position_node` | `leaphand_node` | Desired 16-joint hand commands |
| `leap_state` | `sensor_msgs/msg/JointState` | `leaphand_node` | `xela_data_collector` | Current 16-joint hand state |

Both topic names come from `leap_globals.py`:

```python
COMMAND_TOPIC = "cmd_xela"
STATE_TOPIC = "leap_state"
```

### LEAP Hand Services

`leaphand_node` creates these services:

| Service | Type | Purpose |
| --- | --- | --- |
| `leap_position` | `LeapPosition` | Returns current joint positions |
| `leap_velocity` | `LeapVelocity` | Returns current joint velocities |
| `leap_effort` | `LeapEffort` | Returns current motor current/effort values |
| `leap_state` | `LeapState` | Returns position, velocity, and effort together |

Note that `leap_state` is both a service name and a topic name in this codebase. The collector subscribes to the topic, not the service.

### XELA Topics and Services

| Name | Type | Producer | Consumer | Purpose |
| --- | --- | --- | --- | --- |
| `/xServTopic` | `xela_server_ros2/msg/SensStream` | `xela_service` | `xela_image_publisher` | Continuous XELA sensor stream |
| `/xServStream` | `xela_server_ros2/srv/XelaSensorStream` | `xela_service` | `xela_image_publisher` | Service call for current sensor data |
| `/leap_image` | `sensor_msgs/msg/Image` | `xela_image_publisher` | `xela_data_collector` | Raw tactile image |
| `/leap_image_normalized` | `sensor_msgs/msg/Image` | `xela_image_publisher` | `xela_data_collector` | Normalized tactile image |

## What `launch_leap.py` Does

File:

```text
LEAP_Hand_API/ros2_module/launch/launch_leap.py
```

This launch file creates three launch actions:

1. `leaphand_node`
2. `position_node`
3. an event handler that shuts down the launch when `position_node` exits

The returned launch description is:

```python
return LaunchDescription([
    leaphand_node,
    position_node,
    shutdown_when_position_exits,
])
```

### Node 1: `leaphand_node`

The launch file starts:

```python
Node(
    package="leap_hand",
    executable="leaphand_node.py",
    name="leaphand_node",
    parameters=[
        {"kP": 500},
        {"kI": 0},
        {"kD": 300},
        {"curr_lim": 550},
    ],
)
```

This starts `scripts/leaphand_node.py`.

Inside that file, the node class is:

```python
class LeapXELANode(Node):
```

When the node starts, it:

1. Creates a ROS node named `leaphand_node`.
2. Creates a recursive lock, `_hw_mutex`, to prevent overlapping hardware reads and writes.
3. Creates four services:
   - `leap_position`
   - `leap_velocity`
   - `leap_effort`
   - `leap_state`
4. Instantiates `LeapXelaBase`.
5. Subscribes to `cmd_xela`.
6. Publishes hand state on `leap_state`.
7. Starts a timer that publishes state every `0.1` seconds.

The state timer period comes from:

```python
LEAPHAND_STATE_PUBLISH_PERIOD_SEC = 0.1
```

So the node publishes hand state at about 10 Hz.

### LEAP Hardware Initialization

`leaphand_node` creates:

```python
self._leapXela = LeapXelaBase()
```

`LeapXelaBase` lives in:

```text
LEAP_Hand_API/ros2_module/scripts/base.py
```

Its job is to wrap the Dynamixel connection and low-level LEAP hand commands.

On initialization, it sets default gains and motor IDs:

- motor IDs: `0` through `15`
- `kP = 500`
- `kI = 0`
- `kD = 300`
- current limit: `550`

It then tries to connect to the Dynamixel bus. The connection attempts are hardcoded in this order:

1. `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTA2U1HJ-if00-port0`
2. `/dev/ttyUSB0`
3. `/dev/ttyUSB1`
4. `COM13`

The baudrate is `4000000`.

If `ENABLE_DXL_CLIENT_INIT` is true in `leap_globals.py`, the class then writes configuration to the motors:

- enables torque
- writes proportional gain
- writes integral gain
- writes derivative gain
- writes current limit

There is one important implementation detail: even though `leap_globals.py` defines `DYNAMIXEL_CONNECTION_CANDIDATES`, `base.py` currently does not loop over that list. It uses its own nested `try` blocks with hardcoded ports.

### How Commands Reach the Hand

`leaphand_node` subscribes to:

```text
cmd_xela
```

The callback is:

```python
def _receive_pose(self, msg):
```

It reads:

```python
pose = msg.position
```

Then it stores the command as:

```python
self.curr_pos = np.array(pose)
```

and sends it to the hand:

```python
self._leapXela.set_joints_degrees(self.curr_pos)
```

Despite the message type being `JointState`, only `position` is used as the command. Velocity, effort, and names in the command message are ignored.

`set_joints_degrees()` expects exactly 16 values. If the array is not length 16, it prints an error and returns.

The function converts degrees to radians before writing to Dynamixel:

```python
radians_array = np.radians(degrees_array)
self.dxl_client.write_desired_pos(self.motors, radians_array)
```

So the command topic expects degrees, while the low-level Dynamixel write receives radians.

### How State Is Published

Every `0.1` seconds, `leaphand_node` calls:

```python
publish_state()
```

That calls:

```python
pos, vel, cur = self._leapXela.read_pos_vel_cur()
```

Then it publishes a `JointState` on:

```text
leap_state
```

The published message contains:

- `name = ["joint_0", "joint_1", ..., "joint_15"]`
- `position = pos.tolist()`
- `velocity = vel.tolist()`
- `effort = cur.tolist()`

Important caveat: in the current `base.py`, `read_pos_vel_cur()` does not actually read from the Dynamixel client. The hardware-read implementation is commented out. The active implementation returns:

```python
pos = np.radians(np.array(self.curr_pos, dtype=float))
vel = np.zeros(len(self.motors), dtype=float)
cur = np.zeros(len(self.motors), dtype=float)
```

That means `leap_state` is currently based on the last commanded position stored in `curr_pos`, converted to radians, with zero velocity and zero effort. It is not reporting measured motor velocity or current in the current version of the code.

### Node 2: `position_node`

The launch file also starts:

```python
Node(
    package="leap_hand",
    executable="position_node.py",
    name="position_node",
)
```

This starts:

```text
LEAP_Hand_API/ros2_module/scripts/position_node.py
```

`position_node` is a trajectory replay node. Its job is to load a CSV trajectory, interpolate it, and publish it as a sequence of `JointState` command messages on `cmd_xela`.

On startup, it declares these parameters:

| Parameter | Default | Meaning |
| --- | --- | --- |
| `csv_path` | `""` | Optional explicit CSV path |
| `source_units` | `"radians"` | Units in the CSV |
| `sample_stride` | `1` | Keep every Nth source row |
| `interpolation_steps` | `5` | Number of interpolated commands between sampled poses |
| `publish_period_sec` | `0.01` | Command publish period |
| `save_trajectory_artifacts` | `True` | Whether to save CSV/plot outputs |
| `trajectory_output_dir` | `"trajectory_outputs"` | Where planned trajectory outputs are written |
| `trajectory_csv_filename` | `"joint_trajectory.csv"` | Saved planned trajectory CSV |
| `trajectory_plot_filename` | `"joint_trajectory.png"` | Saved planned trajectory plot |

The defaults come from `leap_globals.py`.

The default trajectory file is:

```python
POSITION_NODE_DEFAULT_CSV_FILENAME = "beer_bottle.csv"
```

When `csv_path` is empty, the node tries to find `beer_bottle.csv` in the installed package share directory:

```text
share/leap_hand/config/beer_bottle.csv
```

If it cannot find that, it falls back to a CSV next to `position_node.py` in the source tree.

### CSV Loading

The CSV must have:

- a header with exactly 16 columns
- data rows with exactly 16 numeric values

If the source units are `radians`, each row is converted to degrees:

```python
pose = np.degrees(pose)
```

If the source units are `degrees`, values are used as-is.

The node then creates a command sequence. It optionally applies `sample_stride`, then interpolates using a Catmull-Rom style cubic interpolation between poses. With the default `interpolation_steps = 5`, it generates 5 intermediate commands per source segment.

### Command Publishing

The node publishes commands on:

```text
cmd_xela
```

It publishes one `JointState` every:

```text
0.01 seconds
```

That is about 100 Hz.

Before publishing, it waits until at least one subscriber exists on `cmd_xela`:

```python
if self.count_subscribers(COMMAND_TOPIC) <= 0:
    return
```

This is there so the trajectory does not start before `leaphand_node` is ready to receive commands.

When the first subscriber appears, it logs that replay is starting. Then each timer tick publishes the next command:

```python
msg = JointState()
msg.header.stamp = self.get_clock().now().to_msg()
msg.position = [float(x) for x in self.command_sequence[self._next_index]]
self.pub.publish(msg)
```

Only `position` is filled. The message does not set `name`, `velocity`, or `effort`.

### Launch Shutdown Behavior

`launch_leap.py` registers an event handler:

```python
OnProcessExit(
    target_action=position_node,
    on_exit=[
        EmitEvent(
            event=Shutdown(
                reason="position_node completed trajectory replay"
            )
        )
    ],
)
```

This means the whole launch system shuts down when `position_node` exits.

The intended lifecycle is:

1. `leaphand_node` starts and connects to the hand.
2. `position_node` starts and loads the trajectory.
3. `position_node` waits for `leaphand_node` to subscribe to `cmd_xela`.
4. `position_node` publishes the trajectory.
5. `leaphand_node` receives each command and writes it to the hand.
6. `position_node` finishes the trajectory and exits.
7. The launch event handler shuts down the full launch.
8. `leaphand_node.destroy_node()` runs and calls `safe_disconnect()`.

## What `xela_server_and_client.launch.py` Does

File:

```text
xela_data_collection/launch/xela_server_and_client.launch.py
```

This launch file starts the full LEAP + XELA data collection stack.

It starts:

1. the same LEAP hand control node, `leaphand_node`
2. the same LEAP trajectory replay node, `position_node`
3. the same shutdown handler when `position_node` exits
4. the XELA server launch from `xela_server_ros2`
5. `xela_image_publisher`
6. `xela_data_collector`

The launch description order is:

```python
[
    file_arg,
    port_arg,
    ip_arg,
    d_arg,
    leaphand_node,
    position_node,
    shutdown_when_position_done,
    included_server,
    client_node,
    collector_node,
]
```

Launch actions are not a strict blocking sequence. ROS launch starts all of these as part of the launch description. The nodes then coordinate through ROS services, topics, and waiting loops.

### Launch Arguments

The launch file declares these arguments:

| Argument | Default | Meaning |
| --- | --- | --- |
| `file` | `/etc/xela/xServ.ini` | XELA server config file |
| `port` | `5000` | TCP port used by XELA server/service |
| `ip` | `127.0.0.1` | IP address used by XELA server/service |
| `d` | `0` | Debug flag passed to `xela_service` |

These are passed into the included `xela_server_ros2` launch file.

### Included XELA Server Launch

The file includes:

```text
xela_server_ros2/launch/service.launch
```

That launch file is XML and starts two nodes:

```xml
<node pkg="xela_server_ros2" exec="xela_server" name="xela_server">
```

and:

```xml
<node pkg="xela_server_ros2" exec="xela_service" name="xela_service">
```

The `xela_server` executable is a shell wrapper around the external `xela_server` command. It strips some ROS launch arguments and then executes:

```bash
xela_server ...
```

The `xela_service` executable is a Python ROS node. It bridges data from the XELA server into ROS. From the package README and message definitions, it provides:

- service `/xServStream`
- topic `/xServTopic`

The `xela_server_ros2` messages are structured like this:

- `SensStream` contains `SensorFull[] sensors`
- `SensorFull` contains metadata plus `Taxel[] taxels` and `Forces[] forces`
- `Taxel` contains `uint16 x`, `uint16 y`, `uint16 z`
- `XelaSensorStream` takes a `uint8 sensor` and returns `SensorFull[] data`

### Node 1: `leaphand_node`

This is the same LEAP hand control node described earlier.

In the combined XELA launch, it is still responsible for:

- subscribing to `cmd_xela`
- sending commands to the LEAP hand
- publishing `leap_state`
- serving the LEAP state services

It uses the same PID/current parameters:

- `kP = 500`
- `kI = 0`
- `kD = 300`
- `curr_lim = 550`

### Node 2: `position_node`

This is the same trajectory replay node described earlier.

In the combined launch, it still:

- loads the default CSV trajectory
- interpolates it
- publishes `JointState.position` commands on `cmd_xela`
- exits when replay is complete

When it exits, the combined launch also shuts down because of:

```python
shutdown_when_position_done
```

That means data collection is tied to the trajectory lifetime. Once the hand trajectory is done, launch shutdown is requested for the whole stack.

### Node 3: `xela_image_publisher`

The launch file starts:

```python
Node(
    package="xela_data_collection",
    executable="xela_image_publisher",
    name="xela_simple_client",
)
```

The executable maps to:

```text
xela_data_collection/xela_data_collection/xela_image_publisher.py
```

The node class is:

```python
class XelaSimpleClient(Node):
```

It creates a ROS node named:

```text
LeapXelaImagePublisher
```

The launch action names the process `xela_simple_client`, while the Python node itself uses `LeapXelaImagePublisher`.

On startup, it:

1. Creates a `LeapImage` object.
2. Creates a service client for `/xServStream`.
3. Waits until `/xServStream` is available.
4. Subscribes to `/xServTopic`.
5. Creates publishers for `/leap_image` and `/leap_image_normalized`.

The startup wait loop is:

```python
while not self.cli.wait_for_service(timeout_sec=1.0):
    self.get_logger().info("service xServStream not available, waiting...")
```

So if the XELA service is not up yet, this node stays alive and waits.

### Initial Service Request

In `main()`, after constructing the node, it immediately calls:

```python
response = node.make_request(sensor_id=1)
```

That sends a `XelaSensorStream` request:

```python
req.sensor = 1
```

If it succeeds, it logs how many sensor readings came back and prints the response. This appears to be a startup sanity check. Continuous image publishing does not come from the service response; it comes from the `/xServTopic` subscription callback.

### XELA Stream to Image Conversion

The image conversion happens inside:

```python
def on_xela_sensor_stream(self, msg: SensStream):
```

Every time a `/xServTopic` message arrives, the node:

1. Fills a 26 by 31 by 3 image from the XELA taxels.
2. Normalizes the image.
3. Publishes the raw image on `/leap_image`.
4. Publishes the normalized image on `/leap_image_normalized`.

The image arrays live in `LeapImage`:

```python
self.image = np.zeros((26, 31, 3), dtype=np.int32)
self.image_normalized = np.zeros((26, 31, 3), dtype=np.float32)
```

Each XELA taxel has:

```text
x, y, z
```

Those become the three image channels.

The mapping from XELA taxel index to image row/column is in:

```text
xela_data_collection/xela_data_collection/leapXelaMap.py
```

Specifically:

```python
LEAP_XELA_ID
```

This is a 26 by 31 grid. Valid cells contain taxel IDs. Empty/non-taxel cells are marked with `6e6`. During filling, for each taxel index, the code finds where that index lives in the grid:

```python
rows, cols = np.where(self.ids == idx)
row, col = rows[0], cols[0]
self.image[row, col, :] = [taxel.x, taxel.y, taxel.z]
```

The result is a spatial tactile image shaped like:

```text
26 rows x 31 columns x 3 channels
```

### Image Normalization

After filling the raw image, `xela_image_publisher` normalizes it:

```python
mn, mx = np.min(img), np.max(img)
n = (img - mn) / (mx - mn + eps)
```

This is global min-max normalization across the full 26 by 31 by 3 image for that single frame.

The normalized image is therefore in approximately:

```text
[0, 1]
```

for each frame independently.

### Published Image Messages

For both raw and normalized images, the publisher creates a `sensor_msgs/Image` with:

- `height = 26`
- `width = 31`
- `encoding = "32FC3"`
- `step = width * 3 * 4`
- `frame_id = "leap_image"`
- timestamp from `self.get_clock().now()`

The normalized image is genuinely `float32`, which matches `32FC3`.

Important caveat: the raw image array is `int32`, but the message encoding is also set to `32FC3`. That means the encoding says "float32 with 3 channels", but the raw bytes actually come from an `int32` NumPy array. The collector knows about this and decodes `/leap_image` as `int32` despite the `32FC3` encoding.

### Node 4: `xela_data_collector`

The launch file starts:

```python
Node(
    package="xela_data_collection",
    executable="xela_data_collector",
    name="xela_data_collector",
)
```

The executable maps to:

```text
xela_data_collection/xela_data_collection/xela_data_collector.py
```

The node class is:

```python
class XelaDataCollector(Node):
```

It creates a ROS node named:

```text
xela_data_collector
```

Its job is to listen to:

- `/leap_image`
- `/leap_image_normalized`
- `/leap_state`

and save synchronized messages to HDF5.

### HDF5 Storage Setup

The collector creates:

```python
self.storage = Storage("xela_data")
```

The `Storage` object builds a stream name from the current date and time:

```text
xela_data_YYYYMMDD_HHMMSS
```

It opens a file at:

```text
<current working directory>/data/xela_data_YYYYMMDD_HHMMSS.h5
```

This is important: the save path is relative to `Path.cwd()`, not relative to the package source folder. In a typical ROS launch, the current working directory is wherever the launch command was run from.

Inside that file, it creates a root group with the same stream name:

```text
xela_data_YYYYMMDD_HHMMSS/
```

Each synchronized frame is stored under a numbered group:

```text
000000/
000001/
000002/
...
```

### Synchronization

The collector first tries to use `message_filters`:

```python
from message_filters import Subscriber, ApproximateTimeSynchronizer
```

If that import and setup succeeds, it creates synchronized subscriptions for:

- `/leap_image`
- `/leap_image_normalized`
- `/leap_state`

The synchronizer uses:

```python
queue_size = 30
slop = 0.05
allow_headerless = False
```

So it tries to match raw image, normalized image, and hand state messages whose timestamps are within about 0.05 seconds of each other.

When a synchronized triple is found, it calls:

```python
_on_synced_images(raw_msg, norm_msg, state_msg)
```

If `message_filters` is not available or initialization fails, the collector falls back to independent subscriptions. In the fallback path it stores the most recent raw, normalized, and state messages in memory, but it does not call `storage.store()`. In other words, actual HDF5 writing only happens in the synchronized callback path.

### What Gets Stored Per Frame

When synchronized data arrives, the collector calls:

```python
self.storage.store(raw_msg, norm_msg, state_msg)
```

For each index group, it stores:

```text
raw_image
normalized_image
state/
```

The structure is:

```text
xela_data_YYYYMMDD_HHMMSS/
  000000/
    raw_image
    normalized_image
    state/
      name
      position
      velocity
      effort
```

The image datasets are compressed with gzip:

```python
compression="gzip", compression_opts=4, shuffle=True
```

The raw image is decoded as `int32`, because of the raw image publisher caveat above.

The normalized image is decoded as `float32`.

The state arrays are stored as:

- `position`: `float64`
- `velocity`: `float64`
- `effort`: `float64`
- `name`: UTF-8 strings

The image datasets also receive attributes copied from the ROS image message:

- `height`
- `width`
- `encoding`
- `is_bigendian`
- `step`
- `stamp_sec`
- `stamp_nanosec`
- `frame_id`

The state group receives timestamp attributes from the `JointState` header:

- `stamp_sec`
- `stamp_nanosec`
- `frame_id`

The frame group receives:

```python
grp.attrs["index"] = int(self.current_index)
```

After every frame, the file is flushed:

```python
self._file.flush()
```

That makes the data safer during long recordings, because each stored frame is pushed to disk immediately.

### Combined Launch Runtime Flow

When `xela_server_and_client.launch.py` is run, the intended flow is:

1. ROS launch declares XELA launch arguments.
2. `leaphand_node` starts.
3. `leaphand_node` initializes `LeapXelaBase`.
4. `LeapXelaBase` attempts to connect to the Dynamixel hand.
5. `leaphand_node` subscribes to `cmd_xela`.
6. `leaphand_node` starts publishing `leap_state` every 0.1 seconds.
7. `position_node` starts.
8. `position_node` loads the CSV trajectory.
9. `position_node` builds an interpolated command sequence.
10. `position_node` waits until `cmd_xela` has a subscriber.
11. The included XELA launch starts `xela_server`.
12. The included XELA launch starts `xela_service`.
13. `xela_service` provides `/xServStream` and publishes `/xServTopic`.
14. `xela_image_publisher` starts and waits for `/xServStream`.
15. Once `/xServStream` exists, `xela_image_publisher` sends a startup request for sensor `1`.
16. `xela_image_publisher` subscribes to `/xServTopic`.
17. `xela_image_publisher` publishes `/leap_image` and `/leap_image_normalized` for each XELA stream message.
18. `xela_data_collector` starts.
19. `xela_data_collector` synchronizes `/leap_image`, `/leap_image_normalized`, and `/leap_state`.
20. For each synchronized triple, `xela_data_collector` writes one HDF5 frame group.
21. Meanwhile, `position_node` publishes hand commands at about 100 Hz.
22. `leaphand_node` receives those commands and writes desired positions to the hand.
23. When `position_node` finishes the trajectory, it exits.
24. The launch event handler emits a shutdown event.
25. The full launch shuts down.
26. `leaphand_node` calls `safe_disconnect()` and attempts to disable torque/close the port.
27. `xela_data_collector` destroys its node; the `Storage` object closes its HDF5 file when destroyed.

## Important Timing Detail

The hand command stream and the saved state stream run at different rates:

- `position_node` publishes commands every `0.01` seconds, about 100 Hz.
- `leaphand_node` publishes `leap_state` every `0.1` seconds, about 10 Hz.
- XELA stream rate depends on the XELA server and hardware.
- The collector stores only synchronized triples within `0.05` seconds.

This means the HDF5 file records tactile frames at the rate at which synchronized image/state triples are available, not necessarily at the 100 Hz hand command rate.

## Important Caveats In The Current Code

### 1. `leap_state` is not currently measured hardware state

`LeapXelaBase.read_pos_vel_cur()` currently returns cached command position and zero velocity/current. The hardware read is commented out.

So the saved `state/position` is best interpreted as the most recent commanded pose, converted to radians, not measured joint position.

### 2. Raw image encoding and raw image bytes disagree

`xela_image_publisher` publishes `/leap_image` with:

```python
encoding = "32FC3"
```

but the backing NumPy array is:

```python
dtype=np.int32
```

The collector compensates by decoding raw images as `int32`. External tools that trust only the ROS image encoding may decode raw image bytes incorrectly.

### 3. HDF5 output path depends on launch working directory

The collector writes to:

```text
Path.cwd() / "data" / "<stream_name>.h5"
```

So if the launch command is run from different directories, output files will appear in different `data/` folders.

### 4. `message_filters` is required for actual storage

The fallback independent subscription mode logs messages but does not write synchronized HDF5 frames. For collection runs, `message_filters` needs to be installed and working.

### 5. Launch shutdown is tied to `position_node`

In both launch files, the full launch shuts down when `position_node` exits. This is good for one-shot trajectory recording, but it means the XELA collection stack is not intended to keep running indefinitely after the trajectory finishes.

## Practical Commands

From a built and sourced ROS 2 workspace, the LEAP-only launch would be run like:

```bash
ros2 launch leap_hand launch_leap.py
```

The combined LEAP + XELA collection launch would be run like:

```bash
ros2 launch xela_data_collection xela_server_and_client.launch.py
```

With custom XELA server arguments:

```bash
ros2 launch xela_data_collection xela_server_and_client.launch.py \
  file:=/etc/xela/xServ.ini \
  port:=5000 \
  ip:=127.0.0.1 \
  d:=0
```

Useful topic checks during runtime:

```bash
ros2 topic list
ros2 topic echo /xServTopic
ros2 topic echo /leap_image
ros2 topic echo /leap_image_normalized
ros2 topic echo /leap_state
```

Useful service checks:

```bash
ros2 service list
ros2 service call /xServStream xela_server_ros2/srv/XelaSensorStream "{sensor: 1}"
ros2 service call /leap_state leap_hand/srv/LeapState "{}"
```

## Mental Model

Think of the full system as three pipelines running together:

1. LEAP command pipeline:
   `position_node -> cmd_xela -> leaphand_node -> Dynamixel hand`

2. LEAP state pipeline:
   `leaphand_node -> leap_state -> xela_data_collector`

3. XELA tactile pipeline:
   `xela_server/xela_service -> /xServTopic -> xela_image_publisher -> /leap_image + /leap_image_normalized -> xela_data_collector`

The collector is the point where the state and tactile pipelines meet. It aligns the latest tactile images with the hand state and writes them into a structured HDF5 file.
