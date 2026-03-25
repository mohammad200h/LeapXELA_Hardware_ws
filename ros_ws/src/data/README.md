# Data Logger

This folder contains the ROS2 data logger implemented in [logger.py](C:/Users/laray/OneDrive%20-%20University%20College%20London/UCL%203/UCL%203.3/ProjectRepos/tactile-intelligence/data/logger.py).

The logger is designed to record:

- tactile sensor packets from `/xServTopic`
- joint packets from `/leap_joint_states`

It writes the two modalities into separate files while keeping their rows aligned by timestamp.

## What The Logger Does

The logger subscribes to:

- `/xServTopic` as `xela_server_ros2/msg/SensStream`
- `/leap_joint_states` as `sensor_msgs/msg/JointState`

For each incoming message, it does not write immediately by arrival order. Instead it:

1. normalizes the message into an internal packet
2. converts its timestamp into one canonical key
3. stores it in a pending buffer
4. writes a matched pair only when both sensor and joint data exist for the same key

This is the main rule that keeps the files aligned:

- `pending_sensors[key]`
- `pending_joints[key]`
- `write_matched_pair(key)` writes both sides together

## Timestamp Handling

The logger uses integer nanoseconds as the canonical timestamp key.

Sensor side:

- each `SensorFull` inside a `SensStream` has `time: float64`
- the logger checks that all `SensorFull.time` values inside one packet are identical or nearly identical
- if they differ, it logs a warning and uses the first one
- conversion used:

```python
int(round(float_seconds * 1e9))
```

Joint side:

- the logger assumes LeapNode publishes `JointState`
- the logger reads the timestamp from `msg.header.stamp`
- conversion used:

```python
sec * 1_000_000_000 + nanosec
```

Because both sides are converted into the same integer-nanosecond format, matching happens by timestamp key rather than callback order.

## Sensor Representation

The incoming tactile message does not contain true geometry coordinates.

Because of that, the logger currently stores each tactile timestep as an ordered synthetic point set. Each point is:

```text
[sensor_index, taxel_index, 0.0, raw_x, raw_y, raw_z, force_x, force_y, force_z, sensor_id, taxel_index]
```

Meaning:

- `sensor_index`: index after sorting sensors by `sensor_pos`
- `taxel_index`: index within that sensor's `taxels`
- `0.0`: synthetic z coordinate placeholder
- `raw_x, raw_y, raw_z`: raw taxel values
- `force_x, force_y, force_z`: force values if present, otherwise `NaN`
- `sensor_id`: the original `sensor_pos`
- final `taxel_index`: repeated intentionally to match the requested format

Point order is stable:

- sensors are sorted by `sensor_pos`
- taxels stay in message order `0..N-1`

## Output Files

The logger writes four files inside the chosen output directory.

Matched outputs:

- `sensor_log.h5`
- `joint_log.csv`

Unmatched outputs:

- `unmatched_sensor.h5`
- `unmatched_joint.csv`

### `sensor_log.h5`

HDF5 group:

- `/sensor`

Datasets:

- `timestamp_ns`
- `timestamp_sec`
- `point_start_idx`
- `point_count`
- `num_sensors`
- `points`

The `points` dataset is append-only and stores all tactile points across all timesteps. `point_start_idx` and `point_count` tell you which slice belongs to each logged timestep.

### `joint_log.csv`

CSV header:

```text
timestamp_key,timestamp_ns,timestamp_sec,joint_0,...,joint_15
```

### Unmatched files

If a packet stays buffered longer than `--max-pending-age-sec`, it is not silently dropped.

Instead:

- stale sensor packets go to `unmatched_sensor.h5`
- stale joint packets go to `unmatched_joint.csv`

On shutdown, any remaining unmatched entries are also flushed there with reason `shutdown_unmatched`.

## CLI Options

The logger currently supports:

- `--output-dir`
- `--sensor-topic`
- `--joint-topic`
- `--max-pending-age-sec`
- `--write-unmatched` / `--no-write-unmatched`
- `--include-forces` / `--no-include-forces`

Defaults:

- sensor topic: `/xServTopic`
- joint topic: `/leap_joint_states`
- max pending age: `2.0`
- write unmatched: `true`
- include forces: `true`

## LeapNode Compatibility Requirements

For the logger to work correctly, LeapNode must publish joint data in the format the logger expects.

### Required topic and type

LeapNode should publish:

- topic: `/leap_joint_states`
- type: `sensor_msgs/msg/JointState`

### Required field usage

The logger assumes:

- `msg.position` contains exactly 16 joint values
- `msg.header.stamp` contains the source timestamp used for matching

### Required timestamp semantics

LeapNode should preserve the tactile packet's source timestamp semantics as closely as possible.

Recommended behavior:

1. receive one tactile timestep
2. compute the 16-joint output for that timestep
3. publish exactly one `JointState`
4. set `header.stamp` to the canonical form of the tactile timestamp

In practice, that means LeapNode should convert the tactile packet time using the same rule the logger expects:

```python
timestamp_ns = int(round(sensor_time_sec * 1e9))
stamp.sec = timestamp_ns // 1_000_000_000
stamp.nanosec = timestamp_ns % 1_000_000_000
```

### Important compatibility rules

- Do not publish joint rows without a valid timestamp in `header.stamp`
- Do not publish a joint vector with anything other than 16 values
- Do not rely on arrival order to align sensor and joint data
- Prefer one joint message per logical tactile timestep
- If LeapNode publishes multiple joint messages for one timestamp, later ones will replace earlier pending ones before match/write

## Current Limitation

The logger is ready, but the current repo still needs LeapNode to actually publish `/leap_joint_states` in this format. Until that publisher exists, the sensor side can run, but matched logging will only happen once the joint topic is available and timestamped correctly.

## Testing Without Hardware

You can test the logger without a real XELA or LeapNode stream by using [synthetic_stream.py](C:/Users/laray/OneDrive%20-%20University%20College%20London/UCL%203/UCL%203.3/ProjectRepos/tactile-intelligence/data/synthetic_stream.py).

That script publishes:

- synthetic `xela_server_ros2/msg/SensStream` on `/xServTopic`
- synthetic `sensor_msgs/msg/JointState` on `/leap_joint_states`

The timestamps are generated so they match the logger's canonical timestamp conversion rules.

### Basic test

Terminal 1:

```bash
python data/synthetic_stream.py --rate-hz 10 --duration-sec 10
```

Terminal 2:

```bash
python data/logger.py --output-dir data/test_output
```

After the run, you should see:

- `data/test_output/sensor_log.h5`
- `data/test_output/joint_log.csv`

If the stream stays fully matched, the unmatched files should either remain empty or not receive rows.

### Testing unmatched handling

To force some joint packets to be missing:

```bash
python data/synthetic_stream.py --drop-joint-every 5
```

To force some sensor packets to be missing:

```bash
python data/synthetic_stream.py --drop-sensor-every 5
```

That lets you confirm:

- stale unmatched sensor data goes to `unmatched_sensor.h5`
- stale unmatched joint data goes to `unmatched_joint.csv`

### Useful synthetic stream options

- `--rate-hz`: publish frequency
- `--duration-sec`: how long to run, `0` means forever
- `--sensor-count`: number of sensors per `SensStream`
- `--taxels-per-sensor`: number of taxels per sensor
- `--include-forces` / `--no-include-forces`
- `--drop-sensor-every`
- `--drop-joint-every`

### Environment note

Both `logger.py` and `synthetic_stream.py` import `xela_server_ros2.msg.SensStream`, so your ROS2 environment still needs to be sourced such that `xela_server_ros2` messages are available in Python.
