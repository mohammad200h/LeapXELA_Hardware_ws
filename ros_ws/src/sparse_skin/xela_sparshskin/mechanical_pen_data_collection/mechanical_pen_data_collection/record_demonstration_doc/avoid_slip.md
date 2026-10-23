# How Avoid slip works

This guide explains the Compose tab's **Avoid slip** switch. During a Play on hand, Index,
Middle and Ring hold the pen while the Thumb clicks it. The Thumb's push can drive the pen out
of their grip. Avoid slip makes the holding fingers press harder: once when the Thumb starts,
and again each time one of them slips.

Avoid slip does not have a controller of its own. It raises the target force of the
`maintain_touch` hold that is already holding each finger against the pen. Read
[maintain_touch.md](maintain_touch.md) first if that hold is new to you. The spring picture in
[position_and_force_control.md](position_and_force_control.md) (section 2.2) explains why
raising a force target makes the finger press harder.

Files involved:

| File | What it does |
| --- | --- |
| [record_demonstration.py](../record_demonstration.py) | The settings `AvoidSlipSettings` ([L537](../record_demonstration.py#L537)), the Compose tab switch and spin boxes ([L6056](../record_demonstration.py#L6056)), the Thumb-start boost ([L6312](../record_demonstration.py#L6312)), slip detection during Play on hand ([_update_slips](../record_demonstration.py#L6591)) and the force increase ([_add_extra_force](../record_demonstration.py#L6621)). |
| [slip_detection.py](../slip_detection.py) | `SlipDetector`: finds slips on one fingertip from its live Xela taxels. |
| [maintain_touch.py](../maintain_touch.py) | `TouchPress`, whose `extra_force` Avoid slip raises; the hold law that uses it ([_hold](../maintain_touch.py#L300)). |

---

## 1. Why it is needed

On the hand, a Play on hand runs in two stages
([_next_hand_stage](../record_demonstration.py#L6297)):

1. Index, Middle and Ring play their takes together. When each reaches its `terminal`, it
   stays there, held in contact with the pen by its last `maintain_touch` region, which is
   stretched to `terminal` ([touch_spans_to_end](../record_demonstration.py#L5417)).
2. The Thumb plays its take and clicks the pen with `click_press`. When it finishes, the other
   fingers are let go.

The `maintain_touch` hold presses with a fixed fingertip force, `hold_force` (2.0 force units by
default). That force is chosen for holding a still pen. When the Thumb starts pushing the pen,
the same force may not be enough: the pen rolls or slides across the fingertips, and the click
fails or the pen falls out. Avoid slip adds force at the moments when this is most likely.

---

## 2. Turning it on

The controls are in the Compose tab's row of lights, after the Slip lights:

| Control | Setting | Default | Meaning |
| --- | --- | --- | --- |
| Avoid slip switch | `enabled` | off | Avoid slip on or off. |
| `+Thumb` | `before_thumb` | 2.0 | Force units added to every finger holding the pen when the Thumb starts. |
| `+slip` | `per_slip` | 1.0 | Force units added to a finger each time it slips. |
| `max` | `max_extra` | 6.0 | The most extra force any one finger can get. |

Changes apply immediately, including during a Play on hand. **Save settings** on the Settings
tab writes them to `settings/mechanical_pen_data_collection/record_demonstration.json`
([L8741](../record_demonstration.py#L8741)), and they are loaded at the next start.

### The touch baseline

All fingertip forces, and so the hold, slip detection and Avoid slip, are measured from a
no-contact Xela reading: the **touch baseline**. Set it with the fingertips touching nothing:

- **Set touch baseline** on the Compose tab, next to Play on hand, or
- **Zero** under the live taxel view on the Create or Edit tab (the same baseline).

The status next to the button shows red **touch baseline: not set** until then, and green
**touch baseline: set 10:32:05** after. **Play on hand will not start until it is set**: it
shows a warning box instead.

The GUI also takes a baseline on its own from the first Xela reading it gets. That one does not
count for Play on hand, because it records whatever the hand was touching when the GUI started.
A baseline taken while a fingertip is pressed makes that fingertip read too little force: the
hold presses too hard, and slips are judged against the wrong level.

If no Xela reading has arrived at all, there is no baseline. The `maintain_touch` hold then
falls back to its open-loop version (`TouchHold`, which holds a pose, not a force), there is no
force target to raise, and slip detection is off.

---

## 3. What it does during a Play on hand

### 3.1 The extra force

Every Play on hand starts with an extra force of 0 for each finger
([_start_slip_detection](../record_demonstration.py#L6561)). Two things raise it:

- **The Thumb starts.** If Avoid slip is on, every finger holding the pen at its `terminal`
  gets `before_thumb` more ([L6312](../record_demonstration.py#L6312)). This happens once,
  just before the Thumb moves, as a precaution.
- **A finger slips.** If Avoid slip is on, that finger gets `per_slip` more
  ([L6619](../record_demonstration.py#L6619)). This can happen several times, and at any point
  in the run where the finger is held in contact, not only after the Thumb starts.

Each increase is capped at `max_extra` per finger
([_add_extra_force](../record_demonstration.py#L6621)):

```
extra[finger] = min(extra[finger] + amount, max_extra)
```

The extra force only ever goes up. It is not lowered when the slipping stops, and it is reset
only at the start of the next Play on hand.

With the defaults, a finger that never slips ends with +2.0 (the Thumb boost). After one slip
it has +3.0. It reaches the cap of +6.0 after four slips.

### 3.2 How the extra force changes the hold

The new value is written to the finger's `TouchPress.extra_force`
([set_touch_extra_force](../record_demonstration.py#L3321)). The hold
([_hold](../maintain_touch.py#L300)) adds it to its target force:

```
F_des  = F_contact + (hold_force + extra_force - F_contact) * min(tau / ramp_s, 1)
dq    += force_gain * (F_des - F) * u * dt
q_cmd  = q_c + dq
```

Here `F` is the live fingertip force, `q_c` the joints where contact was made and `u` the
joint direction that pushes the fingertip along the press axis (see
[maintain_touch.md](maintain_touch.md)). The hold has normally finished its ramp by the time
the Thumb starts, so `F_des` steps straight up by the amount added. The missing force is then
integrated into the joint goals at `force_gain` (0.1 rad/s per force unit). Pressing 2 units
harder therefore starts at 0.2 rad/s along `u` and slows as the force catches up.

The hold's own limits still apply: the press offset stays within `max_press_q` (0.5 rad) and
`max_joint_offset` (0.4 rad) per joint, and it stops growing while a joint's motor is at its
current limit (`sat_effort`). A large `max_extra` cannot push past these.

One `TouchPress` covers all of a take's `maintain_touch` regions, so an extra force added
during one region still applies in the later ones.

If a finger is not being held by a live-force `TouchPress` when an increase is due, nothing is
applied. A warning is logged and the timeline event is marked `(no touch)`.

---

## 4. How a slip is detected

Slip detection runs in every Play on hand, whether Avoid slip is on or off. Avoid slip only
decides whether a slip adds force. There is one `SlipDetector`
([slip_detection.py](../slip_detection.py)) for each of Index, Middle and Ring that plays.

Every Xela reading is fed to it ([_update_slips](../record_demonstration.py#L6591)), with:

- the magnitudes of that finger's 30 fingertip taxels, measured from the Zero baseline and
  divided by `counts_per_unit` ([taxel_magnitudes](../record_demonstration.py#L525));
- whether the finger is in contact right now: its `maintain_touch` hold is in its hold state
  ([in_touch_contact](../record_demonstration.py#L3316)).

Slips are only looked for while the finger is in contact. A curled fingertip reads a few force
units with no contact at all because the skin stretches (see also
[maintain_touch.md](maintain_touch.md)), so the force alone cannot tell contact.

In contact, either of two cues reports a slip:

**Spot shift.** The contact spot is the force-weighted average position of the taxels on the
pad. For the first `settle_s` (0.15 s) of contact, its average is taken as the reference.
After that, if the spot moves more than `slip_shift` (2.5 mm) from the reference, it is a
slip, and the reference moves to the new spot, so the next slip is measured from there. This
catches the pen rolling or sliding across the fingertip.

**Force drop.** The fingertip force `F` is the sum of the taxel magnitudes. If `F` falls below
70 % of its peak over the last `drop_window_s` (0.3 s), and by at least `min_drop` (0.3 units),
it is a slip. This catches the pen pulling out of the grip.

After a slip, no other slip is reported for that finger for `refractory_s` (0.3 s). That
stops one slide from being counted, and from adding force, many times over.

These values are `SlipSettings` in [slip_detection.py](../slip_detection.py#L31). They are
not in the GUI.

### The Slip lights

While a Play on hand runs, the Slip lights next to the Avoid slip switch show each finger
([_set_slip_lights](../record_demonstration.py#L6636)):

- **grey**: not in contact;
- **green**: in contact, held by its `maintain_touch`;
- **red**: for 1 s after a slip.

Next to each light is the number of slips so far, plus the extra force when there is one, for
example `IF 2 (+4.0)`.

---

## 5. What is recorded

Every Play on hand recording (`compose_playbacks/<box>_<n>.npz`) stores all of this in its
`meta` ([L6536](../record_demonstration.py#L6536)):

| Field | Contents |
| --- | --- |
| `avoid_slip` | The settings: `enabled`, `before_thumb`, `per_slip`, `max_extra`. |
| `avoid_slip_extra` | The extra force each finger ended with, for example `{"if": 3.0, "mf": 2.0}`. |
| `timeline` | One event per increase, with its time and finger, for example `avoid_slip +3.0` (the finger's new total). |
| `slips` | Every slip: `t`, `finger`, `cue` (`spot shift` or `force drop`), `value` (the shift in m or the drop in force units) and `force` at that moment. |
| `slip_settings` | The `SlipSettings` thresholds used. |
| `maintain_touch` | The hold settings, including `hold_force` and `force_gain`. |

The raw Xela readings and the baseline are saved too, so slips can be detected again offline
with different thresholds.

The settings are saved when the recording ends. If you change the spin boxes during a run, the
recording keeps only the final values. The `timeline` events show the steps that were actually
applied.

On the Demonstration tab, the increases are drawn as faint grey lines and the slips as red
lines on the recording's plots.

---

## 6. What happened in your recordings

At the time of writing there are 229 Play on hand recordings, 224 of them with Avoid slip on.
Almost all used the defaults (+2.0 at the Thumb, +1.0 per slip, max 6.0).

- **Most slips happen after the Thumb starts:** 165 slips after it, against 27 before. That
  fits the reason the feature exists.
- **The extra force each finger ended with** (largest per recording):

  | Largest extra | Recordings |
  | --- | --- |
  | 0 (no increase applied, e.g. stopped before the Thumb) | 2 |
  | +2.0 (Thumb boost only) | 90 |
  | +3.0 (one slip) | 102 |
  | +4.0 to +6.0 | 20 |
  | more than +6.0 (non-default `max_extra`) | 10 |

- **Spot shift is the main cue.** In the first 130 recordings there were 158 spot shifts and
  2 force drops.
- **No `(no touch)` events**: every increase reached a live-force hold.

Only 34 recordings are labelled success or fail, so they cannot yet say whether Avoid slip
improves the click rate. Labelling more on the Demonstration tab, and recording some runs with
Avoid slip off, would answer that.

---

## 7. Limits

- **It only reacts.** A spot shift of 2.5 mm, or a 30 % force drop, has to happen first. Avoid
  slip then presses harder, but the pen has already moved. The Thumb boost is the only part
  that acts before anything goes wrong.
- **It never lowers the force.** A finger that slipped early keeps pressing harder for the
  rest of the run.
- **It needs a good touch baseline and live-force holds.** Without Xela readings there is no
  slip detection and nothing to raise, and a baseline taken while touching skews every force.
- **Only Index, Middle and Ring.** The Thumb's press is `click_press`, which handles its own
  slips: it eases off and tilts its press direction back toward the cap, and gives up after
  three (see [click_press.md](click_press.md), section 5.3).
- **Slip thresholds are fixed in code.** To tune them, change `SlipSettings` in
  [slip_detection.py](../slip_detection.py#L31), or re-run detection offline on saved
  recordings.
