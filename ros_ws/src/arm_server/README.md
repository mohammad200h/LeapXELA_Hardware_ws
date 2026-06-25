# arm_server

ROS 2 action server for Franka arm motion using MoveIt. Planning and execution are split into separate actions so you can preview a trajectory before moving the robot.

## Overview

| Action | Topic | Purpose |
|--------|-------|---------|
| `Plan` | `/plan` | Plan to a target end-effector pose (xyz + rpy) |
| `Execute` | `/execute` | Execute a previously stored plan by `plan_id` |
| `UpdatePlanningScene` | `/update_planning_scene` | Add collision objects (walls, boxes, etc.) to the MoveIt scene |

## Dependencies

- ROS 2 Humble
- MoveIt 2
- `franka_moveit_config` and `franka_description` (from `multipanda_ros2` in this workspace)

## Build

```bash
cd ros_ws
colcon build --packages-select arm_server
source install/setup.bash
```

## Launch

### Simulation (recommended)

One command starts MoveIt, MuJoCo, RViz, `arm_server`, and loads workspace walls from `script/ws_table.json`:

```bash
source install/setup.bash
ros2 launch arm_server arm_action_server.launch.py
```

Defaults:
- `load_gripper:=false`
- `initial_positions:='"0.0 0 0.0 0 0.0 0 0"'` (all joints at zero)
- `build_walls:=true` (loads `ws_table.json` into the planning scene after 2 s)

Override the initial arm pose:

```bash
ros2 launch arm_server arm_action_server.launch.py \
  initial_positions:='"0.0 -0.785 0.0 -2.356 0.0 1.571 0.785"'
```

Skip auto wall loading:

```bash
ros2 launch arm_server arm_action_server.launch.py build_walls:=false
```

> **Important:** Use the launch file, not `ros2 run arm_server arm_action_server`. The launch file provides `robot_description`, `robot_description_semantic`, and kinematics parameters required by MoveIt.

### Real Franka

Start MoveIt with hardware, then start `arm_server` without the sim stack:

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
ros2 launch arm_server arm_action_server.launch.py launch_sim:=false
```

`load_gripper` must match on both launches.

### With gripper enabled

```bash
ros2 launch arm_server arm_action_server.launch.py \
  load_gripper:=true \
  planning_group:=panda_manipulator \
  end_effector_link:=panda_hand_tcp
```

## Launch parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `launch_sim` | `true` | Launch MoveIt + MuJoCo via `sim_moveit.launch.py` |
| `load_gripper` | `false` | Load Franka Hand in sim / must match MoveIt on real robot |
| `initial_positions` | `"0.0 0 0.0 0 0.0 0 0"` | MuJoCo initial joint positions (quoted string of 7 values) |
| `arm_id` | `panda` | Robot name prefix in URDF/SRDF |
| `planning_group` | `panda_arm` | MoveIt planning group (`panda_manipulator` with gripper) |
| `end_effector_link` | `panda_link8` | End-effector link (`panda_hand_tcp` with gripper) |
| `build_walls` | `true` | Load workspace walls on startup |
| `walls_config_file` | `script/ws_table.json` | JSON file describing walls to add |
| `clear_existing_walls` | `true` | Remove previously added walls before loading |

Node parameters (pass via `--ros-args -p ...`):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `planning_frame` | `panda_link0` | Reference frame for pose goals and scene objects |
| `planning_time` | `5.0` | MoveIt planning timeout (seconds) |
| `max_velocity_scaling` | `0.2` | Velocity scaling factor |
| `max_acceleration_scaling` | `0.2` | Acceleration scaling factor |

## Plan and execute

### 1. Plan to a pose

```bash
ros2 action send_goal /plan arm_server/action/Plan \
  "{x: 0.4, y: 0.0, z: 0.4, roll: 3.14, pitch: 0.0, yaw: 0.0}" --feedback
```

On success, note the `plan_id` in the result.

### 2. Execute the plan

```bash
ros2 action send_goal /execute arm_server/action/Execute \
  "{plan_id: 1}" --feedback
```

Execute the most recent plan:

```bash
ros2 action send_goal /execute arm_server/action/Execute \
  "{plan_id: 0}" --feedback
```

## Action interfaces

```bash
ros2 interface show arm_server/action/Plan
ros2 interface show arm_server/action/Execute
ros2 interface show arm_server/action/UpdatePlanningScene
ros2 interface show arm_server/msg/SceneObject
```

### `arm_server/action/Plan`

**Goal:** `x`, `y`, `z` (m), `roll`, `pitch`, `yaw` (rad)

**Result:** `success`, `message`, `plan_id`, `trajectory_duration`

### `arm_server/action/Execute`

**Goal:** `plan_id` (`0` = most recent plan)

**Result:** `success`, `message`

### `arm_server/action/UpdatePlanningScene`

**Goal:** `objects` (`SceneObject[]`), `clear_existing` (`bool`)

Each `SceneObject`: `id`, `shape_type` (`box` / `sphere` / `cylinder`), `dimensions`, `x`, `y`, `z`, `roll`, `pitch`, `yaw`, optional `color_r/g/b/a`.

## Troubleshooting

| Problem | Likely cause |
|---------|----------------|
| `Missing robot_description or robot_description_semantic` | Started with `ros2 run` instead of the launch file |
| Planning fails immediately | `move_group` not running (use `launch_sim:=true` or start MoveIt separately) |
| Execution fails | Controllers not loaded, or plan is stale/invalid |
| Parameter / SRDF mismatch | `load_gripper` or planning group does not match MoveIt |
