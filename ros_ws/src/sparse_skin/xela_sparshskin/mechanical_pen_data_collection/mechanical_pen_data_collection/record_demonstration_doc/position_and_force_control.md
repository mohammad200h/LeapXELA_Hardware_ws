# How position control and force control work in `record_demonstration.py`

This guide explains how a recorded take is played back on the LEAP hand: first with plain
**position control**, then with **force replay**, which makes the finger press as hard as it did
during the recording. It assumes no control background beyond a rough idea of what a PID
controller is.

Files involved:

| File | What it does |
| --- | --- |
| [record_demonstration.py](../record_demonstration.py) | The GUI. Plays takes by sending goal joint angles to the hand 30 times a second. |
| [force_replay.py](../force_replay.py) | The force controller used during playback (`ForceTracker`). |
| [leaphand_node.py](../../../../../LEAP_Hand_API/ros2_module/scripts/leaphand_node.py) | The hand driver. Passes the goals to the motors and switches their gains. |
| [base.py](../../../../../LEAP_Hand_API/ros2_module/scripts/base.py) | Writes the PID gains and current limit into the Dynamixel motors. |

---

## 1. The big picture: two loops, one inside the other

There are **two** controllers stacked on top of each other:

```
 ┌────────────────────── record_demonstration.py (30 Hz) ───────────────────────┐
 │                                                                              │
 │  recorded take ──► goal angle q_rec(t) ──►(+)──► q_cmd ──► /cmd_xela ─────────┼──┐
 │                                            ▲                                 │  │
 │                    force replay offset ────┘                                 │  │
 │                    (only while touching)  ▲                                  │  │
 │                                           │ live fingertip force (Xela)      │  │
 └───────────────────────────────────────────┼──────────────────────────────────┘  │
                                             │                                     │
 ┌───────────── each Dynamixel motor (fast, runs inside the motor) ─────────────┐  │
 │                                                                              │◄─┘
 │   error = goal − measured angle  ──►  PD controller  ──►  current (torque)   │
 │                                                          capped by curr_lim  │
 └──────────────────────────────────────────────────────────────────────────────┘
```

- The **inner loop** lives in each motor's firmware. You give it a goal angle; it does the rest.
  This is the PID you already know.
- The **outer loop** lives in the GUI. It decides *which* goal angle to send every 1/30 s.
  Plain playback just reads the goal from the recording. Force replay **moves the goal** a little
  further into the object until the measured force matches the recorded force.

So this code never commands a force or a torque directly. **Force control is built on top of
position control by moving the position goal.** That is the main idea of this guide.

---

## 2. The inner loop: the motor's PID

### 2.1 What the motor computes

[base.py:44](../../../../../LEAP_Hand_API/ros2_module/scripts/base.py#L44) puts every motor in
Dynamixel operating mode 5, **current-based position control**. Each motor then repeats, at a
much higher rate than anything in Python:

```
error   = goal_angle − measured_angle
current = kP · error  +  kI · ∫error dt  +  kD · d(error)/dt
current = clip(current, −curr_lim, +curr_lim)     # the "current limit"
```

Current in an electric motor is proportional to torque, so `current` is "how hard the motor
pushes".

- **kP (P gain)**: pushes in proportion to how far the joint is from its goal.
- **kD (D gain)**: resists fast motion. It acts like damping (a shock absorber), so the joint
  does not overshoot and oscillate.
- **kI**: set to **0** everywhere ([base.py:53](../../../../../LEAP_Hand_API/ros2_module/scripts/base.py#L53)).
  So in practice the motors run a **PD** controller.
- **curr_lim**: the maximum current. Whatever the PID asks for, the motor never pushes harder than
  this. It is a safety cap and also the maximum force the finger can apply.

Motors 0, 4 and 8 (the side-to-side joints) get 75 % of kP and kD.

### 2.2 The spring picture (the most useful idea in this guide)

Since kI = 0, when the finger is standing still (so the D term is zero) the motor pushes with:

```
push ≈ kP · (goal − actual)        (until it hits curr_lim)
```

That is exactly the law of a **spring**: the motor behaves like a spring stretched between the
goal angle and the actual angle, with stiffness kP.

```
     goal                actual
      │◄────── error ─────►│
      ●/\/\/\/\/\/\/\/\/\/\●  finger
         spring of stiffness kP
```

Two consequences you will see again later:

1. **In free air** nothing resists the finger, so it ends up at the goal (error ≈ 0).
2. **When something blocks the finger** (the pen), the finger stops at the object. The error
   stays non-zero and the finger presses with `kP × error`. To press **harder**, you either
   raise kP or put the goal **further inside the object**. Force replay does the second.

### 2.3 Two sets of gains: compliant and stiff

The hand node runs with `compliant:=true`, and keeps two sets of gains
([leaphand_node.py:77-103](../../../../../LEAP_Hand_API/ros2_module/scripts/leaphand_node.py#L77-L103)).
The GUI shows both in the **Settings** tab ([HAND_PARAMS](../record_demonstration.py#L162)):

| Gains | Settings-tab label | Default kP / kD / curr_lim | Used for |
| --- | --- | --- | --- |
| `compliant_*` | Position kP / kD / Current limit | 60 / 40 / 120 | Fingers that are **not** playing. A soft spring, so you can move them by hand. |
| `stiff_*` | Playback kP / kD / current limit | 600 / 200 / 550 | Fingers that **are** playing. A stiff spring, so they follow the take closely and can press hard. |

When you press Play, the GUI tells the hand node which joints should be stiff through the ROS
parameter `stiff_joints` ([_update_stiff_joints](../record_demonstration.py#L2161)); the node
then writes the stiff gains into those motors only
([_apply_gains](../../../../../LEAP_Hand_API/ros2_module/scripts/leaphand_node.py#L158)). When
playback stops, the joints go back to the compliant gains.

---

## 3. Compliance: why you can move the fingers by hand

With a soft spring (kP = 60) you can push a finger away from its goal, but as soon as you let
go it springs back. To make it **stay** where you put it, the goal itself must follow the
finger. Both the hand node and the GUI do this with a **deadband**:

```
if |measured − goal| > deadband:      # someone pushed the joint far enough
    goal = measured                   # accept the new position as the goal
```

- Pushing a joint further than the deadband (default 0.05 rad ≈ 3°) moves its goal, so the
  finger stays where you pose it.
- Small errors (below the deadband) are ignored. Without this, gravity would sag the finger a
  tiny bit, the goal would follow the sag, the finger would sag a bit more, and so on: the
  finger would slowly droop to the table.

This logic lives in two places:

| Where | When it is active |
| --- | --- |
| hand node, [publish_state](../../../../../LEAP_Hand_API/ros2_module/scripts/leaphand_node.py#L123) | When nobody has sent a command for `compliant_cmd_timeout` (0.5 s). Setting: **Deadband** (`compliant_deadband`). |
| GUI, [_command_step](../record_demonstration.py#L2224) | While any finger is playing. The GUI then commands the **whole** hand, so it applies the same rule to the fingers that are not playing ("free fingers"). Setting: **Free-finger deadband**. |

That is why you can still pose the other fingers while one finger plays a take.

---

## 4. Position playback, step by step

### 4.1 The command loop

Commands are sent from their own thread ([_command_loop](../record_demonstration.py#L2202)) at
**Command rate** (default 30 Hz). Each tick calls
[_command_step](../record_demonstration.py#L2224), which builds a full 16-joint goal `q` and
publishes it on `cmd_topic` (`cmd_xela`):

```
q = free-finger goals (deadband rule from section 3)
for each playing finger:
    if still ramping:  q[finger] = blend from where it was to the start of the take
    else:              q[finger] = recorded joints at take time `local`
                       (+ force replay offset, section 5)
send q
```

It runs in its own thread because redrawing the GUI can take longer than 1/30 s; if commands
were sent from the GUI thread the finger would move in a jerky staircase.

### 4.2 The ramp

When you press Play, the finger may be far from where the take starts. Jumping there at once
with stiff gains would be a violent move. So for the first **Playback ramp** seconds (default
0.5 s) the goal slides in a straight line from the current pose to the first pose of the take:

```
a = elapsed / ramp            # goes 0 → 1
q = (1 − a) · from_q  +  a · to_q
```

The same ramp is used when you drag the play bar while playing
([_on_seek](../record_demonstration.py#L1837)).

### 4.3 Following the take

After the ramp, the take time is

```
local = offset + (elapsed − ramp) − held_s
```

- `offset`: where the play bar was when you pressed Play.
- `held_s`: how long force replay has paused the take (section 5.4). Zero for plain playback.

The goal is the recorded joint angles at `local`, linearly interpolated between the two nearest
samples ([sample_take](../record_demonstration.py#L1669)). When `local` reaches the end of the
take, the finger stops and the play bar rewinds.

### 4.4 Why position playback is not enough when touching the pen

Think about what happened during the recording. The finger was soft (compliant gains) and
**you** pushed it into the pen. The recording stored where the finger *was*, and the Xela
sensors stored how hard it pressed.

On playback the motor gets those same angles as its goal. But the pen is in the way:

```
recording:  you push ───► finger at q_rec, pressing with force F_rec   (your hand supplied the force)
playback :  goal = q_rec, the pen stops the finger a bit short of q_rec
            press = kP × (small error)    →  usually much less than F_rec
```

From the spring picture: when the finger reaches about the same place it was during recording,
the error is about zero, so the motor pushes about zero. Nothing in plain position replay knows
that the finger is supposed to press. A mechanical pen will therefore often not click.

---

## 5. Force replay

Force replay ([force_replay.py](../force_replay.py)) fixes this by **pushing the goal past the
recording** until the live fingertip force equals the recorded one. Turn it on or off with
**Match the take's fingertip force** in the Settings tab.

### 5.1 Measuring the fingertip force

Each fingertip has 30 Xela taxels (small 3-axis sensors). The "fingertip force" `F` is a single
number ([taxel_magnitudes](../record_demonstration.py#L220)):

```
for each fingertip taxel:  change = |reading − baseline| / counts_per_unit
F = sum of the changes over the 30 taxels
```

- The **baseline** is a reading with nothing touching the finger. The live baseline is taken when
  you press **Zero** under the hand view; each take stores the baseline it was recorded with.
- `F` is in "force units" (sensor counts / `counts_per_unit`), **not Newtons**. That is fine,
  because live and recorded forces are measured the same way and only compared to each other.

Force replay is used only if the take has Xela data, has at least one contact phase, and a live
baseline exists (you pressed Zero). Otherwise the finger falls back to plain position replay;
the log says why ([_force_tracker](../record_demonstration.py#L1998)).

### 5.2 Finding the contact phases in the recording

When you press Play, [contact_phases](../force_replay.py#L96) looks at the recorded force
`F_rec(t)` and finds where the finger was touching:

```
 force
   ▲             peak
   │            ╭──╮  ← click: sharp drop while the finger is still pressed in
   │           ╱    ╲╮
   │──────────╱──────┼╲───────────────── contact level = noise + 25 % of (peak − noise)
   │         ╱       │ ╲
   │────────╱────────┼──╲──────────────── loading level = noise + 10 % of (peak − noise)
   │ noise ╱         │   ╲_____
   └──────┴─────┴────┴───┴──────────────► take time
         loading start      end
              │ contact start
```

- **noise**: the 20th percentile of the force (what "not touching" looks like).
- A **contact phase** is a stretch above the contact level lasting at least 0.1 s.
- **direction**: how the finger's joints moved from the start of loading to the peak, as a unit
  vector over the finger's 4 joints. This is "the way to press harder". Force replay only ever
  moves the goal along this direction.
- **click** ([find_click](../force_replay.py#L80)): a drop of at least 20 % within 0.25 s while
  the finger moved back less than 10 % of its loading travel. Letting go also lowers the force,
  but only together with the finger moving back, so that is not counted as a click.

### 5.3 The force controller: an I controller on force

During a contact phase, every tick ([ForceTracker.step](../force_replay.py#L208)) does:

```
force_error = F_rec(local) − F_live
offset      = clip(offset + force_gain · force_error · dt,  0,  force_max_offset)
q_cmd       = q_rec(local) + offset · direction
```

If you know PID, you can read this directly: `offset` is the **integral of the force error**,
so this is an **I controller** (integral only) whose output is a position offset.

- Finger pressing **too lightly** (F_live < F_rec): the error is positive, the offset grows, the
  goal moves deeper into the pen, and from the spring picture the motor presses harder.
- Pressing **too hard**: the error is negative and the offset shrinks.
- The offset is clipped between 0 and **Max press offset** (default 0.25 rad ≈ 14°). It never
  goes below 0, so force replay can only press *further* than the recording, never pull back
  from it. The upper limit stops it from driving the finger without bound if, for example, the
  sensor is not reading.

Why an integral and not a P controller? The force only appears when the goal is *past* the
object, and the motor P-gain already turns position error into force. An integrator keeps
moving the goal until the force error is zero and then **stays** there, which is what we want
(a P-only controller would settle with a leftover error).

**Force gain** (default 0.1 rad per force-unit per second) sets how fast it reacts. Example: the
take recorded F_rec = 4 and the live finger reads F_live = 2. Then the offset grows by
`0.1 × 2 = 0.2 rad/s`, which is about 0.0067 rad per 30 Hz tick. After half a second the goal is
0.1 rad (≈ 6°) deeper than the recording and the force has risen. As F_live approaches 4, the
growth slows down and stops.

Where it plugs in: [_command_step](../record_demonstration.py#L2224) adds
`p.force.offset_q` (= `offset · direction`) to the recorded joints before sending.

### 5.4 The state machine around it

A real replay does not line up perfectly in time with the recording: the pen may be a few
millimetres further away, or click a bit earlier or later. So the tracker has a few states. The
current state is shown next to the play bar time, e.g. `[tracking force, +0.08 rad]`.

```
                    take reaches a contact phase
 ┌──────────┐ ─────────────────────────────────────► ┌────────────────────────┐
 │ outside  │                                        │  waiting for contact   │ take time paused,
 │ contact  │                                        │  (live finger not yet  │ offset grows while
 │ offset   │ ◄─── no contact within Max hold ────── │   touching)            │ F_live < F_rec
 │ decays   │                                        └───────────┬────────────┘
 │ to 0     │                                    F_live ≥ 50 % of contact level
 └──────────┘                                                    ▼
      ▲                                              ┌────────────────────────┐
      │◄──────────── phase ends ──────────────────── │     tracking force     │ take time runs,
      │                                              │ (I controller of 5.3)  │ offset follows the
      │                                              └───────────┬────────────┘ force error
      │                                       take reaches the recorded click
      │                                                          ▼
      │                                              ┌────────────────────────┐
      │◄──── live click seen, or Max hold passed ─── │ pressing for the click │ take time paused,
      │                                              │                        │ offset grows at
                                                     └────────────────────────┘ Click push rate
```

- **Waiting for contact.** The recording says "touching now" but the live finger is not. The
  take's time is **paused** (`step` returns False and `held_s` grows), so the recording does not
  run on and pull the finger away. Meanwhile the offset keeps growing so the finger reaches the
  pen. Gives up after **Max hold** (default 3 s) and continues as plain position replay.
- **Tracking force.** The I controller of section 5.3.
- **Pressing for the click.** The take has reached the moment the pen clicked in the recording,
  but the live pen has not clicked. The take time is paused again and the offset grows steadily
  at **Click push rate** (0.15 rad/s) plus the force-error term, until a live click is seen. It
  stops pushing if the live force reaches 1.5 × the recorded peak (a safety limit) and gives up
  after **Max hold**.
- **Live click detection** ([_watch_click](../force_replay.py#L193)) runs all the time, so if
  the pen clicks earlier than in the recording (up to 1 s before the phase), the finger does not
  press it a second time.
- **Release.** After the phase, the offset decays exponentially back to zero with a time
  constant of 0.3 s (it loses about 63 % every 0.3 s), so the finger goes back to following the
  recording smoothly instead of jumping.

---

## 6. Tuning cheat sheet

| Symptom | Try |
| --- | --- |
| Playing finger lags behind the take or looks sloppy | Raise **Playback kP** |
| Playing finger shakes or overshoots | Raise **Playback kD**, or lower **Playback kP** |
| Finger cannot press hard enough even with a large offset | Raise **Playback current limit** (it caps the push) |
| Free fingers are hard to move by hand | Lower **Position kP** / **Current limit** |
| Free fingers slowly droop | Raise **Deadband** / **Free-finger deadband** |
| Free fingers jump back a bit after you pose them | Lower the deadband |
| Force replay reacts too slowly | Raise **Force gain** |
| Force replay oscillates (presses, backs off, presses…) | Lower **Force gain** |
| Pen does not click and the log says "no click within …" | Raise **Max press offset**, **Click push rate** or **Max hold** |
| Log says "no live Xela baseline (press Zero)" | Press **Zero** with nothing touching the finger before Play |
| Jerky start of playback | Raise **Playback ramp** |

GUI values (command rate, ramp, free-finger deadband, force replay) apply immediately. The hand
node's gains are applied with **Apply to hand**.

---

## 7. Glossary

| Term | Meaning |
| --- | --- |
| **Goal / setpoint** | The angle the motor is told to go to. |
| **Error** | Goal minus measured angle (or recorded minus live force, for force replay). |
| **P / I / D** | React to the error now / its accumulated sum / how fast it changes. |
| **Gain** | The multiplier in front of a P, I or D term. |
| **Stiff vs compliant** | High vs low kP: hard vs easy to push away from the goal. |
| **Deadband** | An error size below which nothing happens. |
| **Current limit** | Maximum motor current, i.e. maximum torque the joint can apply. |
| **Take** | One recording of one finger: joint angles, Xela readings, camera. |
| **Contact phase** | A stretch of a take where the recorded fingertip force is clearly above noise. |
| **Offset** | How far (rad, along the loading direction) force replay has moved the goal past the recording. |
| **Ramp** | The smooth move from where the finger is to the start of the take. |
