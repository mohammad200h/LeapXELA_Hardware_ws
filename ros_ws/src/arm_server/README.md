# arm_server

ROS 2 action server for Franka arm motion using MoveIt. Planning and execution are split into two separate actions so you can preview a trajectory before moving the real robot.

## Overview

| Action | Topic | Purpose |
|--------|-------|---------|
| `Plan` | `/plan` | Plan to a target end-effector pose (xyz + rpy) |
| `Execute` | `/execute` | Execute a previously stored plan by `plan_id` |

The server uses `moveit::planning_interface::MoveGroupInterface` and stores planned trajectories in memory until they are executed or replaced by a newer plan.

## Dependencies

- ROS 2 Humble
- MoveIt 2
- `franka_moveit_config` and `franka_description` (from `multipanda_ros2` in this workspace)

MoveIt must be running before sending goals. The `move_group` node provides planning scene updates and trajectory execution controllers.

## Build

```bash
cd ros_ws
colcon build --packages-select arm_server
source install/setup.bash
```

## Launch

Start MoveIt first, then start `arm_server`. The `load_gripper` setting must match on both launches.

### Simulation (no real robot)

**Terminal 1 — MoveIt + MuJoCo sim:**

```bash
source install/setup.bash
ros2 launch franka_moveit_config sim_moveit.launch.py load_gripper:=false
```

**Terminal 2 — arm_server:**

```bash
source install/setup.bash
ros2 launch arm_server arm_action_server.launch.py load_gripper:=false
```

### Real Franka

**Terminal 1 — MoveIt + hardware:**

```bash
source install/setup.bash
ros2 launch franka_moveit_config moveit.launch.py \
  robot_ip:=192.168.2.13 \
  load_gripper:=false
```

**Terminal 2 — arm_server:**

```bash
source install/setup.bash
ros2 launch arm_server arm_action_server.launch.py load_gripper:=false
```

> **Important:** Use the launch file above, not `ros2 run arm_server arm_action_server`. The launch file provides `robot_description`, `robot_description_semantic`, and kinematics parameters required by MoveIt.

### With gripper enabled

If MoveIt is launched with `load_gripper:=true`, start the arm server with matching settings:

```bash
ros2 launch arm_server arm_action_server.launch.py \
  load_gripper:=true \
  planning_group:=panda_manipulator \
  end_effector_link:=panda_hand_tcp
```

## Action interfaces

### `arm_server/action/Plan`

**Goal**

| Field | Type | Description |
|-------|------|-------------|
| `x`, `y`, `z` | `float64` | Target position (meters) in the planning frame |
| `roll`, `pitch`, `yaw` | `float64` | Target orientation (radians) |

**Result**

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether planning succeeded |
| `message` | `string` | Status or error message |
| `plan_id` | `uint64` | ID used to execute this plan |
| `trajectory_duration` | `float64` | Planned trajectory duration (seconds) |

**Feedback**

| Field | Type | Description |
|-------|------|-------------|
| `progress` | `float64` | Planning progress in `[0.0, 1.0]` |

### `arm_server/action/Execute`

**Goal**

| Field | Type | Description |
|-------|------|-------------|
| `plan_id` | `uint64` | Plan to execute. Use `0` to execute the most recent plan. |

**Result**

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether execution succeeded |
| `message` | `string` | Status or error message |

**Feedback**

| Field | Type | Description |
|-------|------|-------------|
| `progress` | `float64` | Execution progress in `[0.0, 1.0]` |

## Plan and execute

### 1. Plan to a pose

```bash
ros2 action send_goal /plan arm_server/action/Plan \
  "{x: 0.4, y: 0.0, z: 0.4, roll: 3.14, pitch: 0.0, yaw: 0.0}" --feedback
```

On success, note the `plan_id` in the result (for example `1`).

### 2. Execute the plan

```bash
ros2 action send_goal /execute arm_server/action/Execute \
  "{plan_id: 1}" --feedback
```

To execute the latest plan without tracking the ID:

```bash
ros2 action send_goal /execute arm_server/action/Execute \
  "{plan_id: 0}" --feedback
```

### Typical workflow

```text
/plan     -> stores trajectory, returns plan_id
/execute  -> runs stored trajectory on the robot
```

Plans are removed from memory after a successful execute. Sending a new `/plan` goal stores an additional plan under a new `plan_id`.

## Launch parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `arm_id` | `panda` | Robot name prefix in URDF/SRDF |
| `load_gripper` | `false` | Must match the MoveIt launch |
| `planning_group` | `panda_arm` | MoveIt planning group (`panda_manipulator` with gripper) |
| `end_effector_link` | `panda_link8` | End-effector link (`panda_hand_tcp` with gripper) |
| `planning_frame` | `world` | Reference frame for pose goals |
| `planning_time` | `5.0` | MoveIt planning timeout (seconds) |
| `max_velocity_scaling` | `0.2` | Velocity scaling factor |
| `max_acceleration_scaling` | `0.2` | Acceleration scaling factor |

Example with custom motion limits:

```bash
ros2 launch arm_server arm_action_server.launch.py load_gripper:=false \
  --ros-args -p planning_time:=10.0 -p max_velocity_scaling:=0.1
```

## Inspecting actions

List available actions:

```bash
ros2 action list | grep -E 'plan|execute'
```

Show action interface:

```bash
ros2 interface show arm_server/action/Plan
ros2 interface show arm_server/action/Execute
```

## RViz preview

If RViz is running from the MoveIt launch, you can preview planned trajectories using the **Planned Path** display, which listens on `/display_planned_path`. The MotionPlanning panel in RViz does this automatically when planning from the GUI.

## Troubleshooting

| Problem | Likely cause |
|---------|----------------|
| `Missing robot_description or robot_description_semantic` | Node started with `ros2 run` instead of the launch file |
| Planning fails immediately | MoveIt (`move_group`) is not running |
| Execution fails | Controllers not loaded, or plan is stale/invalid |
| Parameter / SRDF mismatch | `load_gripper` or planning group does not match MoveIt launch |
