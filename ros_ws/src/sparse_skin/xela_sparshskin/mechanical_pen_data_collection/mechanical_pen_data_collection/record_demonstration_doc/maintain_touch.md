# How `maintain_touch` works

This guide explains what happens when the Edit tab's Play reaches a **`maintain_touch`** region.
In that region the finger has to **stay in contact** with the pen, for example to hold it
steady while the thumb clicks. Play pauses the take until the fingertip touches the pen,
then lets the take's time run while it holds a set fingertip force.

It builds on [position_and_force_control.md](position_and_force_control.md) (the spring
picture, section 2.2) and uses the same fingertip controller as
[click_press.md](click_press.md). Read the click press doc for the derivation of the
press direction `u = K⁻¹Jᵀd`. This doc only summarises it.

Files involved:

| File | What it does |
| --- | --- |
| [maintain_touch.py](../maintain_touch.py) | The controllers: `TouchPress` (closed loop, with live force) and `TouchHold` (open-loop fallback), their settings `MaintainTouchSettings`, and the press-axis choice `touch_axis`. |
| [click_press.py](../click_press.py) | Shared pieces: `FingerKinematics` (contact point, Jacobian, pad normal), the IK constants, `region_settings`. |
| [record_demonstration.py](../record_demonstration.py) | Builds the controller at Play ([_maintain_touch](../record_demonstration.py#L2611)) and calls it every command step ([_command_step](../record_demonstration.py#L2891)). Also the region editing in the Edit tab. |
| [events.json](../events.json) | Defines the `maintain_touch` event: duration, Index / Middle / Ring only. |

---

## 1. Why it is needed

During a recording the finger is soft and **you** hold it against the pen. Plain position replay
sends the recorded joints back as goals. As the spring picture explains, a finger that arrives
where it was in the recording presses with almost no force, and a pen that sits a few mm
further away is not touched at all. Force replay helps only where the recording shows a
clear contact phase with a peak.

`maintain_touch` lets you say explicitly "from here to here this finger must be touching the
pen" and gives that span its own controller:

- it **waits** for contact instead of letting the take run on in the air;
- it holds a **chosen** force (not the recorded one), so a light recorded touch can be
  replayed as a firm hold;
- if the contact is lost during the region, it **goes back and finds the pen again**.

---

## 2. Adding and editing a region

In the Edit tab, select an Index, Middle or Ring take. (The event is not offered for the
Thumb, whose press is `click_press`.) Add `maintain_touch` with two clicks, at the start and
the end of the span where the finger should be touching. The region is shaded on the play bar
and the plot.

- **Moving `terminal`.** If the region reaches past the take's `terminal` event (before it in a
  reversed take), `terminal` is moved to the region's edge and a message tells you so
  ([_fit_terminal](../record_demonstration.py#L4235)). This lets you extend a hold beyond
  the end of the recorded episode.
- **Edit** on a `maintain_touch` event ([EditTakeEventDialog](../record_demonstration.py#L3505))
  has three extra boxes:
  - **Duration**: the region keeps its left edge and grows or shrinks to the right (and can
    move `terminal` again);
  - **Hold force** and **Contact force**: this region's own values, stored in the event's
    `params` as `hold_force` / `contact_force`. The boxes are pre-filled with the Settings tab
    values.

Play picks up the regions with [touch_spans](../record_demonstration.py#L4258), which returns
`(start, end, params)` per region, sorted by start.

---

## 3. What happens when you press Play

[_maintain_touch](../record_demonstration.py#L2611) runs once per Play if the take has any
regions. It chooses between two controllers:

| Condition | Controller |
| --- | --- |
| A live Xela baseline exists (**Zero** pressed), the finger has fingertip taxels, and the URDF / FK loaded | **`TouchPress`**: closed-loop approach and force hold (sections 4–6) |
| Any of those missing | **`TouchHold`**: open loop, holds the recorded pose with a small press (section 7). The log says `maintain_touch without force feedback: <why>; holding the recorded pose`. |

Unlike click press and force replay, maintain touch **also runs when the take plays in
reverse**. The region is then **entered** at its end and **exited** at its start.

For each region, `TouchPress` needs two things from the take:

### 3.1 Contact point

This is the point on the fingertip that should touch the pen. Each fingertip taxel is
weighted by its share of the **recorded force summed over the whole region**, and the contact
point is the weighted average of the taxel positions. If the take has no force in the region,
all taxels get equal weight, so the point is the middle of the pad. FK moves the point with
the finger's joints ([FingerKinematics](../click_press.py#L654)).

### 3.2 Press axis d

[touch_axis](../maintain_touch.py#L107) decides which way the fingertip should move to reach
the pen:

```
motion = contact point at entry − contact point 0.3 s before entry     (in playback order)
```

- If the motion is at least 1 mm **and** within 75° of the fingertip pad's outward normal,
  `d = motion / |motion|`. This is the way the finger was moving toward the pen in the
  recording.
- Otherwise `d` is the **pad normal**: the fingertip patch frame's z axis, pointing to the
  side the taxels are on. Pushing along it presses the pad flat onto whatever is in front of
  it.

The 75° test rejects motions that would mainly slide the pad sideways or pull it away.

The log reports the result per region, for example:

```
Index maintain_touch: region 2.40-6.10 s, press axis [0.21, 0.05, -0.97] from the approach motion (3.4 mm, 18 deg off the pad normal)
```

---

## 4. The state machine (`TouchPress`)

Every command step, [_command_step](../record_demonstration.py#L2891) computes the take's goal
joints `q_rec` at take time `local` and calls [TouchPress.step](../maintain_touch.py#L336). If
`step` returns `None` the take (and force replay) drive the finger as usual. Otherwise its
joints replace the finger's goal.

```
             take time enters the region
  take  ────────────────────────────────►  APPROACH ◄─────────────────┐
(normal)                                    │ take time HELD          │ contact lost
   ▲                                        │ fingertip moves along d │ (F < ½ contact
   │                                        │ F ≥ contact, or blocked │  for loss_s)
   │                                        ▼                         │
   │                                      HOLD ───────────────────────┘
   │                                        │ take time RUNS
   │                                        │ force held at hold_force
   │           take time leaves the region  │
   │           (or give up, or turned off)  ▼
   └──────────────────────────────────── RELEASE
                                          blend into the take over release_s
```

The take's clock behaves differently in the two main states:

- **APPROACH holds the take's time** (`p.held_s` grows). The play bar, camera, plots and the
  other events wait while the finger finds the pen.
- **HOLD lets the take's time run.** The play bar moves across the region, but the finger
  does **not** follow the recorded joints. It stays at the contact pose plus the press offset
  (`q_c + Δq`). The region therefore ends when the take's time reaches its exit, i.e. after
  the region's recorded duration, counted from the moment contact was made.

The current state is shown next to the play bar time, e.g.
`[maintain touch: F 3.10 / 3.20, +0.07 rad]`.

### 4.1 Force reference: relative or absolute

Each fingertip's 30 taxels give the force `F`: the sum of `|reading − baseline| /
counts_per_unit`, the same signal as the tip plots. A **curled** finger reads a few units even
with nothing touching, because bending stretches the skin. With **Forces relative to the force
at entry** on (the default), every force setting is measured from `F_entry`, the live F when Play
entered the region:

```
contact level = F_entry + contact_force
hold level    = F_entry + hold_force
```

With it off, `F_entry` is replaced by 0, so the levels are measured from the Zero baseline.
`F_entry` is taken once per region entry. A re-approach after a contact loss keeps the same
reference.

### 4.2 APPROACH: guarded move along d

[_approach](../maintain_touch.py#L262). This works the same way as click press:

```
x_target += d · approach_speed · dt          # default 10 mm/s
q        += one damped least-squares IK step toward x_target   (λ = 1 mm, ≤ 0.05 rad/joint/step)
```

The approach starts from the joints the finger is at: `q_rec` on a fresh entry, or the
current (possibly blended) command when it re-enters during a release or after a loss.

Contact is detected in one of two ways:

- **Force:** `F ≥ contact level`.
- **Blocked:** F has been above **half** the contact rise (`F_base + 0.5 · contact_force`) for
  0.2 s, while the measured fingertip (FK of `leap_state`) advanced less than 30 % of what the
  approach commanded. This catches a firm touch whose force is still low.

The finger **gives up** on the region after `max_travel` (20 mm) along `d` or `max_wait` (4 s)
without contact (`give up: ...; the take plays over the region`). It blends back into the take,
and the take plays over the rest of that region as plain replay. It does not try that region
again during this Play.

### 4.3 HOLD: force control along d

[_hold](../maintain_touch.py#L297). At contact the controller stores the commanded joints
`q_c`, the force `F₀`, and starts the offset `Δq = 0`. Every step:

```
F_des  = F₀ + (hold level − F₀) · min(t / ramp_s, 1)       # ramp to the hold force over 0.5 s
Δq    += force_gain · (F_des − F) · u · dt
q_cmd  = q_c + Δq
```

- This is an **integral controller on force**. When the force is too low, `Δq` grows and the
  goal sinks into the pen. When it is too high, `Δq` shrinks. Once the error reaches zero the
  offset stays where it is, so the force is held without a steady error.
- `force_gain` is in rad/s **per force unit** (absolute, unlike click press, which divides
  by the recorded peak). Default 0.1.
- `u = K⁻¹Jᵀd` (normalised) is the joint direction whose goal offset makes the fingertip
  **force** point along `d`, not just the fingertip motion. `K` holds the joints' relative
  kP (0.75 for [REDUCED_KP_MOTORS](../record_demonstration.py#L234) 0, 4, 8; else 1). `u` is
  recomputed every 0.2 s. See [click_press.md](click_press.md), section 5.2, for why.
- Limits: each joint of `Δq` is within `±max_joint_offset` (0.4 rad), `|Δq| ≤ max_press_q`
  (0.5 rad), and `Δq` never points back past `q_c`.
- **Current limit:** while any finger joint's `leap_state` effort is at or above `sat_effort`
  (600), `Δq` may not grow. A bigger goal on a saturated joint adds no force, it only turns the
  force sideways. Unlike click press, saturation does **not** end the hold. The finger just
  holds as hard as it can.

### 4.4 Contact loss

If `F` stays below the **loss level** (`F_base + 0.5 · contact_force`) for `loss_s` (0.3 s),
the contact counts as lost (`approach: contact lost ...`). This happens, for example, when the
pen moves or the thumb's click pushes it away. The finger goes back to APPROACH from where it
is (`q_c + Δq`), and the **take's time is held again** until it touches.

### 4.5 RELEASE

The region ends when the take's time leaves it, when you untick **Hold contact in
'maintain_touch' regions**, or on a give-up (`no live fingertip force` also gives up). The
controller then blends from the last command into the take over `release_s` (0.3 s):
`q = (1 − a) · q_last + a · q_rec` ([_step_blend](../maintain_touch.py#L385)). After that,
`step` returns `None`.

Dragging the play bar (seek) resets the controller ([_on_seek](../record_demonstration.py#L2189)).
A region that the new position falls inside is entered fresh, with a new approach.

---

## 5. How it fits with the other controllers

Inside [_command_step](../record_demonstration.py#L2891) the order is:

```python
q[p.cols] = sample_take(p.take, local)        # recorded joints
# 1. click_press (Thumb) — if active, it owns the finger
# 2. maintain_touch     — only if click press is not active
step = p.touch.step(local, dt, now, q[p.cols], measured_hand, live_F, effort[p.cols])
if step is not None:
    q[p.cols] = step.q
    touching = True
    if step.hold: p.held_s += dt              # APPROACH: take time stays at `local`
# 3. force replay       — only if neither of the above is active
```

So inside a region (including its release blend) **force replay is skipped** for that finger.
Click press only runs on the Thumb and maintain touch only on the other fingers, so in practice
the two never act on the same finger.

---

## 6. What is saved

Each Edit-tab Play is saved as a playback recording (see section 5c of
[position_and_force_control.md](position_and_force_control.md)). Its `meta` holds:

- `maintain_touch`: the Settings-tab values used;
- `maintain_touch_trace`: every decision `TouchPress` made:

```json
{"t": 8.512, "region": [2.4, 6.1], "state": "hold", "event": "contact",
 "F": 2.91, "F_des": 2.85, "dq": 0.0, "why": "F 2.91 >= 2.85; travel 3.2 mm, press direction [...]"}
```

The events are `approach`, `contact`, `release` and `give up`. The same lines appear in the ROS
log as `<Finger> maintain_touch: <event>: <why>`. The open-loop `TouchHold` leaves the trace
empty and only logs `maintaining touch (open loop) ...` / `released touch ...`.

---

## 7. Open-loop fallback (`TouchHold`)

[TouchHold](../maintain_touch.py#L447) is used when there is no live force or no kinematics.
For each region ([touch_regions](../maintain_touch.py#L422)):

- `pose` = the recorded joints at the region's entry;
- `direction` = the unit **joint-space** motion over the 0.3 s before entry (zero if the joints
  barely moved, which means no press).

Inside the region:

```
offset = clip(press_offset + press_rate · (time in region), 0, max_offset)
q_cmd  = pose + offset · direction
```

The take's time is **not** held. The finger is frozen at the entry pose, pressed slightly and
increasingly past it. Leaving the region, it blends back into the take over `release_s`. A
region's `params` can set its own `press_offset`, `max_offset` and `press_rate`.

There is no feedback here: if the pen is further away than in the recording, the finger may
not touch it at all. Press **Zero** before Play so that `TouchPress` is used.

---

## 8. Settings

These are in the Settings tab under **Maintain touch (Edit tab Play, applied immediately)**,
built from [TOUCH_FIELDS](../record_demonstration.py#L5320) and saved with **Save settings**.
Settings are read on every step, so changes apply during a hold. A region's `params` can
override any `MaintainTouchSettings` field for that region
([region_settings](../click_press.py#L117)). The Edit dialog sets `hold_force` and
`contact_force`; other fields have to be added to `params` by hand.

| GUI label | Field | Default | Meaning |
| --- | --- | --- | --- |
| Hold contact in 'maintain_touch' regions | `enabled` | on | Master switch |
| Forces relative to the force at entry | `relative` | on | Measure forces from `F_entry` instead of the Zero baseline |
| Hold force | `hold_force` | 2.0 units | Force held during HOLD (above `F_entry` if relative) |
| Contact force | `contact_force` | 0.5 units | Force rise that ends APPROACH; half of it is the loss level |
| Force ramp | `ramp_s` | 0.5 s | Time to ramp from the contact force to the hold force |
| Force gain | `force_gain` | 0.1 rad/(unit·s) | How fast `Δq` moves per unit of missing force |
| Approach speed | `approach_speed` | 10 mm/s | Speed of the guarded move |
| Max approach | `max_travel` | 20 mm | Furthest the approach may go before giving up |
| Max wait | `max_wait` | 4 s | Longest wait for contact before giving up |
| Max press offset | `max_press_q` | 0.5 rad | Cap on `|Δq|` |
| Max joint offset | `max_joint_offset` | 0.4 rad | Cap on any one joint of `Δq` |
| Current limit at | `sat_effort` | 600 | `leap_state` effort treated as saturated (0: off) |
| Contact loss time | `loss_s` | 0.3 s | Time below the loss level before re-approaching |
| Release time | `release_s` | 0.3 s | Blend back into the take after a region |
| No feedback: press | `press_offset` | 0.03 rad | `TouchHold`: initial press past the entry pose |
| No feedback: rate | `press_rate` | 0.05 rad/s | `TouchHold`: how fast the press grows |
| No feedback: max | `max_offset` | 0.2 rad | `TouchHold`: largest press |

Force values are in the tip plots' units (sensor counts / `counts_per_unit`), **not
Newtons**. To choose a hold force, look at the finger's tip plot during the recorded touch.

---

## 9. Troubleshooting

| What you see (log / status) | Likely cause | Try |
| --- | --- | --- |
| `maintain_touch without force feedback: no live Xela baseline (press Zero)` | No Zero since start | Press **Zero** with nothing touching, then Play |
| `give up: no contact within 20 mm` | Pen further away, or `d` points the wrong way | Check the pen position and the logged press axis; raise **Max approach**; move the region's start to just before the finger reaches the pen so the approach motion is clean |
| Contact detected while still in the air | A curled finger's skin reading rises during the approach | Keep **relative** on; raise **Contact force** |
| Finger presses too hard / pushes the pen away | Hold force too high | Lower **Hold force** (for this region in its Edit dialog) |
| Force oscillates around the target | Gain too high | Lower **Force gain** or lengthen **Force ramp** |
| Force slow to reach the target | Gain too low, or current limit | Raise **Force gain**; check the status for `limit on joint`, and raise the **Playback current limit** |
| Repeated `contact lost` → `approach` | Force drops after contact (pen moves, finger slides) | Raise **Contact loss time**, or lower **Contact force** so the loss level is lower |
| The finger snaps when the region ends | Take's pose at the exit is far from the held pose | Raise **Release time**, or end the region where the recording is still near the pen |
| The region seems to last longer than marked | APPROACH held the take's time | Expected: HOLD lasts the region's recorded duration after contact |

---

## 10. Glossary

| Term | Meaning |
| --- | --- |
| **F** | Fingertip force: sum of the fingertip taxel magnitudes from the Zero baseline (tip-plot units) |
| **F_entry** | Live F when Play entered the region; the reference when **relative** is on |
| **entry / exit** | Take times Play enters / leaves the region: start / end, swapped when playing in reverse |
| **d** | Press axis: recorded approach motion of the contact point, or the pad normal |
| **contact point** | Recorded force-weighted average of the fingertip taxel positions over the region |
| **u = K⁻¹Jᵀd** | Joint direction whose goal offset makes a fingertip force along `d` |
| **q_c, Δq** | Commanded joints at contact, and the press offset added to them |
| **held_s** | Time the take's clock has been paused (only during APPROACH) |
