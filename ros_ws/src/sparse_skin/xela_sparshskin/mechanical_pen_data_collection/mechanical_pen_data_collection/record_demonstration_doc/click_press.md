# How `click_press` works for the thumb

This guide explains what happens when the Edit tab's Play reaches a **`click_press`** region on
a Thumb take. In that region, Play stops following the recorded joints. It drives the thumb's
fingertip into the pen cap and ramps up the force until the pen clicks, then hands control back
to the take.

It builds on [position_and_force_control.md](position_and_force_control.md), mainly the
"spring picture" (section 2.2) and force replay (section 5). Read those first if the motor
PID or force replay are new to you.

Files involved:

| File | What it does |
| --- | --- |
| [click_press.py](../click_press.py) | The controller: `ClickPress`, its settings `ClickPressSettings`, the take analysis `press_geometry`, and the fingertip kinematics. |
| [record_demonstration.py](../record_demonstration.py) | Builds a `ClickPress` when Play starts ([_click_press](../record_demonstration.py#L2549)) and calls it every command step ([_command_step](../record_demonstration.py#L2838)). |
| [force_replay.py](../force_replay.py) | Force replay, which is switched off inside `click_press` regions. Also supplies the constants `LOADING_LEVEL`, `CLICK_DROP` and `CLICK_WINDOW_S`. |
| [events.json](../events.json) | Defines the `click_press` event (duration, Thumb only). |

---

## 1. Why the thumb needs its own press

Force replay presses harder by pushing the goal joints further along the **joint-space**
direction the finger moved in while loading during the recording. That works for the
index/middle/ring fingers. The thumb has more trouble:

- The thumb pushes the pen's **cap**, a small rounded button. If the fingertip force is even
  20–30° off the button's axis, the thumb slides off the cap instead of pushing it down.
- Pushing the goal along a joint-space direction does **not** give a fingertip force in a chosen
  Cartesian direction. On the thumb, the force direction it gave was measured at 20–37° off the
  intended axis, which is enough to slide.
- The pen may not be in exactly the same spot as in the recording, so replaying the recorded
  joints can put the fingertip a few mm off.

`click_press` fixes this by working at the **fingertip**: it works out the direction the thumb
pressed in the recording (a 3D axis `d`), moves the fingertip along it until it touches, and
then chooses joint goal offsets so that the resulting fingertip **force** points along `d`.

---

## 2. Adding a region

In the Edit tab, select a Thumb take and add the `click_press` event. It is a duration event, so
it takes two clicks:

1. **Start:** a little before the thumb touches the cap in the take.
2. **End:** after the thumb has released in the take.

The region is shaded orange on the play bar and the plot. It is saved in the take's `events`
with `t` (start), `end`, and an optional `params` dict (see section 8).

What the start and end are used for:

- The **start** is where Play hands the thumb over to the click press. The fingertip begins its
  approach from wherever the take puts it at that moment.
- The **end** is where the take resumes after the press. Anything in between is skipped.
- Everything between start and end is used to find the recorded force **peak** and the press
  axis (section 4). A region that contains no force peak cannot be pressed.

---

## 3. What happens when you press Play

[_click_press](../record_demonstration.py#L2549) runs once per Play, before the first command.
It returns `None` (so the take plays normally over the region) and logs a warning if any of the
following is true:

| Check | Log message |
| --- | --- |
| **Press in 'click_press' regions** is off in the Settings tab | (no region is used) |
| No `click_press` region ends after the play bar position | (nothing to do) |
| The take has no Xela readings | `click_press off: the take has no Xela readings` |
| The take has no recorded sim joints (needed for FK) | `... the take has no sim joints` |
| You have not pressed **Zero** since starting the GUI | `... no live Xela baseline (press Zero)` |
| The URDF / FK could not be loaded | `... no fingertip kinematics (...)` |
| The region has no force peak, or the fingertip did not move while loading | `no force peak, or no fingertip motion while loading, in click_press region ...` (that region only) |
| Play is in **reverse** | (click press and force replay are both off) |

For each usable region it logs the press axis, how far the fingertip moved while loading, and
the recorded peak and no-contact force, for example:

```
Thumb: click_press 3.10-5.40 s, press axis [0.12, -0.31, -0.94] (loading moved 4.2 mm), recorded force peak 7.41, no contact 2.38
```

It then builds one `PressRegion` per region and one `ClickPress` for the Play.

**Force replay is turned off** for every recorded contact phase that overlaps a `click_press`
region ([_force_tracker](../record_demonstration.py#L2499)). The two controllers would otherwise
both move the same joints.

---

## 4. What is read from the take: `press_geometry`

[press_geometry](../click_press.py#L149) looks at the region once, when Play starts.

### 4.1 Fingertip force F

The same signal as the plots and force replay: the sum over the thumb's 30 fingertip taxels of
`|reading − baseline| / counts_per_unit`. It is in sensor units, not Newtons. Every threshold
in the click press is a fraction of the **recorded peak**, so the units cancel out.

- **peak**: the highest F inside the region.
- **noise**: the 20th percentile of F over the whole take. This is the level F reads at when
  nothing is touching.
- **contact level** (used later): `noise + contact_ratio × (peak − noise)`. With the default
  `contact_ratio = 0.15`, this is 15 % of the way from noise to peak.

### 4.2 Contact point

At the peak sample, each fingertip taxel gets a weight equal to its share of the force
(`weights`, summing to 1). The **contact point** is the weighted average of the taxel
positions. FK moves this point with the thumb's joints, so the controller can always ask
"where is the contact point now?" These weights stay fixed for the whole Play.

### 4.3 Press axis d

Working backwards from the peak, the code finds where loading began: the last sample at or above
`noise + 10 % × (peak − noise)` (`LOADING_LEVEL`), and never earlier than the region start. It
then computes, by FK on the recorded sim joints:

```
motion = contact point at the peak − contact point at the start of loading
d      = motion / |motion|
```

`d` is the direction the fingertip actually travelled while pushing the button down in the
demonstration. If that motion is shorter than 1 mm (`MIN_LOADING_MOTION`), there is no reliable
axis and the region is skipped.

> Why not use the taxels' 3-axis force vectors for the direction? On real takes their sum
> mostly cancels out and barely grows while the press does, and it pointed about 80° off the
> way the thumb moved. The motion of the contact point is a much better estimate.

---

## 5. The state machine

Every command step (30 Hz by default), [_command_step](../record_demonstration.py#L2838) first
computes the take's goal joints `q_rec` at take time `local`. It then calls
[ClickPress.step](../click_press.py#L502). If `step` returns `None`, the take, maintain touch
and force replay drive the finger as usual. If not, its joints replace the thumb's goal.

```
                 take time reaches region start
   take  ──────────────────────────────────────────►  APPROACH
 (normal)                                              │  fingertip moves along d
    ▲                                                  │  F ≥ contact level, or blocked
    │                                                  ▼
    │                                                PRESS
    │                                                  │  force ramps up until a click
    │                     click, or abort (any state)  │
    │                                                  ▼
    │                                                RETRACT
    │                                                  │  back off along −d over release_s
    │          take jumps to the region end            ▼
    └────────────────────────────────────────────── RELEASE
                                                     blend from the retract pose into the take
                                                     over release_s, then DONE
```

The **take's time is held** (`p.held_s` grows) during APPROACH, PRESS and RETRACT. The take
therefore stays at the region's start and does not run past the region while the press is
going on. At the end of RETRACT the take jumps to the region's **end** (`skip_to`) and
`held_s` is adjusted, so the play bar continues from there.

The current state and numbers are shown next to the play bar time, e.g.
`[click press: F 5.80 / 6.90, 0.12 rad]`.

### 5.1 APPROACH: guarded move along d

[_approach](../click_press.py#L358). When the region starts, the controller records the
contact point `x0` at the take's joints. Then at every step:

```
x_target += d · approach_speed · dt          # default 10 mm/s
q        += one damped least-squares IK step toward x_target
```

The IK step ([_solve](../click_press.py#L310)) is
`Δq = Jᵀ (J Jᵀ + λ² I)⁻¹ (x_target − x)`, where `J` is the 3×4 Jacobian of the contact point
over the thumb's 4 joints and `λ = 1 mm`. Each joint moves at most 0.05 rad per step. The
Jacobian is computed by finite differences on the FK ([FingerKinematics](../click_press.py#L654)).
The other 12 hand joints stay where they were when Play started.

Contact is detected in one of two ways:

- **Force:** live `F ≥ contact level`.
- **Blocked:** F has been above the 10 % loading level for 0.2 s (`BLOCKED_S`), and the
  **measured** fingertip (FK of `leap_state`) has advanced less than 30 % (`BLOCKED_RATIO`) of
  what the approach commanded. In other words, the thumb is touching something firm but the
  force is still low.

The approach **aborts** (goes to RETRACT) if the fingertip target has moved `max_travel`
(20 mm) along `d` without contact, or after `max_wait` (4 s).

### 5.2 PRESS: force ramp along d

[_press](../click_press.py#L413). At contact the controller stores the commanded joints `q_c`
and starts a joint offset `Δq = 0`. Every step:

```
F_des = min(F_contact + force_ramp · F_peak · t,   max_force_ratio · F_peak)
Δq   += press_gain_q · (F_des − F) / F_peak · u · dt
q_cmd = q_c + Δq
```

- `t` is the time since contact. With the defaults, the desired force rises at 0.5 × peak per
  second and is capped at 1.3 × the recorded peak.
- `(F_des − F) / F_peak` is the force error as a fraction of the peak. As in force replay, the
  offset is the **integral** of this error. Pressing too lightly makes `Δq` grow, so the goal
  sinks deeper into the cap and the motor springs push harder.
- `Δq` is clipped: each joint to `±max_joint_offset` (0.4 rad), the whole vector to
  `|Δq| ≤ max_press_q` (0.5 rad). It is never allowed to point back past `q_c` (no pulling
  away from the contact pose).

#### Why the joint direction is u = K⁻¹ Jᵀ d

This is the key idea. From the spring picture, a motor whose goal is offset by `Δqᵢ` from where
it is blocked pushes with torque `kPᵢ · Δqᵢ`. For the whole finger:

```
joint torques τ = K Δq           (K = diag of the joints' kP)
```

A fingertip force `f` balances those torques when `Jᵀ f = τ`. We want `f` to point along `d`,
`f = s · d`, so:

```
K Δq = s · Jᵀ d     ⇒     Δq ∝ K⁻¹ Jᵀ d   =: u   (normalised)
```

Pushing the goal along `u` therefore produces a fingertip force along `d`, whatever the thumb's
pose.

The obvious alternative, pushing the goal along the IK direction `J⁺ d` ("move the fingertip
along d"), gives a force along `(J Jᵀ)⁻¹ d`. On the thumb that is 20–37° off `d`, which is past
the friction cone of the fingertip on the cap, so the thumb slid. Moving the fingertip along `d`
and pushing along `d` are different directions.

`K` uses the joints' **relative** kP: [REDUCED_KP_MOTORS](../record_demonstration.py#L229)
(hardware motors 0, 4 and 8) run at 75 % of kP in `leaphand_node`, so they get `0.75` and the
rest `1.0`. `u` is recomputed every 0.2 s (`U_UPDATE_S`) at the current commanded joints
`q_c + Δq`, because `J` changes as the thumb moves.

#### Current limit (saturation)

Each motor's torque is capped by its current limit (**Playback current limit** in the
Settings tab). Once a joint is at the limit, a bigger goal error on that joint adds no torque.
The other joints keep adding torque, so the fingertip force turns sideways instead of growing.

So, while any thumb joint's `leap_state` effort is at or above `sat_effort` (600 by default;
recorded presses plateau around 640–760), `Δq` is **not allowed to grow** (it may still
shrink). If the joint stays saturated for `sat_hold_s` (1 s) without a click, the press aborts
with *"current limit reached ...: raise the Playback current limit"*.

### 5.3 Slips

[_slipped](../click_press.py#L387). At contact (and after each slip) the controller stores a
reference: the measured fingertip position, the **contact spot** on the pad, and the force. A
slip is any of:

| Slip test | Setting (default) |
| --- | --- |
| The contact spot on the fingertip pad moved more than this | `slip_shift` (2.5 mm) |
| The measured fingertip moved more than this **across** `d` | `slip_across` (3 mm) |
| The measured fingertip moved more than this **along** `d` while the force did not grow (fell below the highest force since the reference) | `button_travel` (4 mm) |

The **contact spot** is the force-weighted average of the live fingertip taxels' positions in
the fingertip's own frame ([_live_tip_spot](../record_demonstration.py#L2614)). It shows the
contact moving across the pad even when the joints barely move. The last test exists because a
pen button only travels a few mm: moving further along `d` while the force drops means the thumb
is sliding over the cap or pushing the pen away.

On a slip:

1. `Δq` is cut to `slip_backoff` (60 %) of its value, which takes some pressure off.
2. `d` is tilted `slip_tilt` (10°) **against** the direction the fingertip slid:
   `d ← normalise(cos a · d − sin a · slip_direction)`. The next push therefore leans back
   toward the cap.
3. `u` is recomputed and the slip reference is reset.

After `max_slips` (3) slips the press aborts with *"thumb keeps sliding (...)"*.

### 5.4 Detecting the click

A click ends the PRESS (to RETRACT). There are two ways to detect it:

1. **Click detector.** A new rising edge on `click_topic` (`/pen_click`, Int32 1 while a click is
   heard) since the region started. The node counts rising edges
   ([_on_click](../record_demonstration.py#L989)), so short pulses are not missed.
2. **Force and motion** (only if **Only the click detector ends a press** is off). All of these
   must be true within the last `CLICK_WINDOW_S` (0.25 s):
   - the highest F in the window was at least `click_min_ratio` (0.7) × the recorded peak;
   - F has dropped by `CLICK_DROP` (20 %) from that highest value;
   - the measured fingertip moved forward at least `click_advance` (1 mm) along the
     **give-way direction** `e = J K⁻¹ Jᵀ d`, and sideways by no more than half of that;
   - there was no slip in the window.

Why all these conditions: when a pen clicks, the button suddenly gives way, so the force drops
**and** the thumb lurches forward. Sliding off the cap also drops the force and moves the thumb
forward, but sideways too. A force drop alone is therefore not counted as a click. The thumb
lurches along `e`, not along `d`, because when the resistance vanishes the joint springs unload
along `K⁻¹ Jᵀ d` in joint space, which `J` maps to `e` at the fingertip.

### 5.5 Aborts

Any of the following sends the press to RETRACT without a click (logged as `abort: <why>`). The
take then continues from the region end as usual.

| Reason | When |
| --- | --- |
| `no contact within N mm` / `within N s` | APPROACH ran out of `max_travel` / `max_wait` |
| `no click within N s` | PRESS ran longer than `max_wait` |
| `current limit reached ...` | saturated for `sat_hold_s` |
| `thumb keeps sliding (...)` | more than `max_slips` slips |
| `joint current N above M` | any thumb joint's `|effort|` above `max_current` (off when 0) |
| `no live fingertip force` | no live Xela reading |
| `click press turned off` | you unticked the setting during the press |

### 5.6 RETRACT and RELEASE

- **RETRACT:** the fingertip target moves `retract` (4 mm) back along `−d`, linearly over
  `release_s` (0.3 s), by IK from where the press ended. This takes the thumb off the cap before
  the take resumes, so the take does not drag it across.
- **RELEASE** ([_step_blend](../click_press.py#L573)): the take jumps to the region's end, and
  over another `release_s` the goal is blended from the retract pose to the take's joints:
  `q = (1 − a) · q_retract + a · q_rec`. After that, `step` returns `None` and the take runs
  on.

Each region is pressed at most once per Play. Regions that start before the play bar position
when you press Play are skipped ([reset](../click_press.py#L250)).

---

## 6. Where it plugs into the command loop

The relevant part of [_command_step](../record_demonstration.py#L2838):

```python
q[p.cols] = sample_take(p.take, local)          # recorded joints
if p.press is not None:
    step = p.press.step(local, dt, now, q[p.cols], measured_hand,
                        live_F, click_count, effort[p.cols], live_spot)
    if step is not None:
        q[p.cols] = step.q                       # click press owns the thumb
        if step.hold:     p.held_s += dt         # take time stays at `local`
        if step.skip_to:  local = region end     # pressed: resume after the region
# maintain touch and force replay only run when the click press is not active
```

Inputs to `step` each tick:

| Input | Source |
| --- | --- |
| `q_rec` | the take's joints at `local` |
| `q_hand` | latest measured joints (`leap_state`), for the measured fingertip position |
| `force` | live F ([_live_tip_force](../record_demonstration.py#L2632)), from the Zero baseline |
| `click_count` | rising edges seen on `click_topic` |
| `effort` | the thumb joints' `leap_state` effort (current), for saturation and abort |
| `spot` | live contact spot on the pad ([_live_tip_spot](../record_demonstration.py#L2614)) |

Settings are read on every step, so changes in the Settings tab apply during a press.

---

## 7. What is saved

Every Edit-tab Play is saved as a playback recording (see section 5c of
[position_and_force_control.md](position_and_force_control.md)). For click press its `meta`
holds:

- `click_press`: the Settings-tab values used;
- `click_press_trace`: every decision the controller made, one dict each:

```json
{"t": 12.345, "region": [3.1, 5.4], "state": "press", "event": "slip",
 "F": 5.12, "F_des": 6.3, "dq": 0.142, "slips": 1,
 "why": "contact spot moved 2.8 mm on the pad; backed off to 0.085 rad, d [...]"}
```

The events are `approach`, `contact`, `slip`, `saturated`, `click`, `abort` and `done`. The
same lines appear in the ROS log as `Thumb click_press: <event>: <why>`. When a press fails,
this trace is the first thing to look at.

---

## 8. Settings

These are in the Settings tab under **Click press (Play, applied immediately)**, built from
[PRESS_FIELDS](../record_demonstration.py#L5375). They are saved with **Save settings**. A
region's `params` in the take can override any of them for that region only, using the field
name ([region_settings](../click_press.py#L117)), e.g.
`"params": {"force_ramp": 0.3, "max_force_ratio": 1.6}`.

| GUI label | Field | Default | Meaning |
| --- | --- | --- | --- |
| Press in 'click_press' regions | `enabled` | on | Master switch |
| Approach speed | `approach_speed` | 10 mm/s | Speed of the guarded move |
| Contact level | `contact_ratio` | 0.15 × peak | F that counts as contact (from noise to peak) |
| Max approach | `max_travel` | 20 mm | Furthest the approach may go along `d` |
| Force ramp | `force_ramp` | 0.5 × peak/s | How fast `F_des` rises after contact |
| Max force | `max_force_ratio` | 1.3 × peak | Cap on `F_des` |
| Press gain | `press_gain_q` | 0.15 rad/s per peak | How fast `Δq` grows per unit of missing force |
| Max press offset | `max_press_q` | 0.5 rad | Cap on `|Δq|` |
| Max joint offset | `max_joint_offset` | 0.4 rad | Cap on any one joint of `Δq` |
| Max wait | `max_wait` | 4 s | Time limit for contact, and again for the click |
| Current limit at | `sat_effort` | 600 | `leap_state` effort treated as saturated (0: off) |
| Max time at limit | `sat_hold_s` | 1 s | Saturated this long without a click: abort |
| Slip: pad shift | `slip_shift` | 2.5 mm | Contact spot motion on the pad that is a slip |
| Slip: along d | `button_travel` | 4 mm | Fingertip travel along `d` (with no force gain) that is a slip |
| Slip: across d | `slip_across` | 3 mm | Fingertip travel across `d` that is a slip |
| Slip back-off | `slip_backoff` | 0.6 × | Fraction of `Δq` kept after a slip |
| Slip re-aim | `slip_tilt` | 10° | How far `d` is tilted against a slip |
| Max slips | `max_slips` | 3 | Slips before abort |
| Retract | `retract` | 4 mm | Back-off along `−d` after the press |
| Release time | `release_s` | 0.3 s | Duration of the retract, and of the blend into the take |
| Click force drop from | `click_min_ratio` | 0.7 × peak | A force drop counts as a click only from this force |
| Click give-way | `click_advance` | 1 mm | Fingertip lurch along `e` needed for a click without the detector |
| Only the click detector ends a press | `require_click_detector` | off | Ignore force-drop clicks |
| Abort current | `max_current` | 0 (off) | Any thumb joint `|effort|` above this aborts at once |

---

## 9. Troubleshooting

| What you see (log / status) | Likely cause | Try |
| --- | --- | --- |
| `click_press off: no live Xela baseline (press Zero)` | No Zero since start | Press **Zero** with nothing touching, then Play |
| `no force peak, or no fingertip motion while loading` | The region misses the press, or the thumb barely moved | Widen the region so it covers the whole loading and the peak |
| `no contact within 20 mm` | Pen is further than the take, or `d` points wrong | Check the pen position; raise **Max approach**; check the logged press axis |
| Contact is detected too early (still in the air) | Noisy F or a low contact level | Press **Zero** again; raise **Contact level** |
| `current limit reached ...` | The motors cannot push hard enough | Raise **Playback current limit** (Settings, Apply to hand); or lower **Max force** if the peak was unusually high |
| Repeated `slip` then `thumb keeps sliding` | Thumb is off-center on the cap | Re-pose the pen; raise **Slip re-aim** or lower **Force ramp** so the force builds more gently |
| `no click within 4 s` with F near `F_des` | Button needs more than the cap | Raise **Max force** or **Max wait** |
| A click is reported but the pen did not click | Force-drop detection fooled | Turn on **Only the click detector ends a press**, or raise **Click give-way** |
| The pen clicks but the press keeps going | Detector not running / no give-way seen | Check that `click_topic` publishes; lower **Click give-way** |

---

## 10. Glossary

| Term | Meaning |
| --- | --- |
| **F** | Fingertip force: sum of the 30 fingertip taxel magnitudes from the Zero baseline (sensor units) |
| **peak / noise** | Highest recorded F in the region / 20th percentile of recorded F over the take |
| **d** | Press axis: unit 3D direction the contact point moved while loading in the take (hand base frame) |
| **J** | 3×4 Jacobian of the contact point over the thumb's 4 joints |
| **K** | Diagonal of the joints' relative kP (0.75 for motors 0/4/8, else 1) |
| **u = K⁻¹Jᵀd** | Joint direction whose goal offset makes a fingertip force along `d` |
| **e = JK⁻¹Jᵀd** | Direction the fingertip lurches when the button gives way |
| **q_c, Δq** | Commanded joints at contact, and the press offset added to them |
| **contact spot** | Where on the fingertip pad the live contact is (force-weighted taxel position) |
| **held_s** | Time the take's clock has been paused; it is what holds the take at the region start |
