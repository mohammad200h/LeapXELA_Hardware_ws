# Learning about your own body

A `record_demonstration` tab where the LEAP + Xela hand moves itself to random goal poses
and back, while recording what its joints and skin feel. The data is about the hand's own
body: how far it can move, and what it feels when it touches itself.

## Episode

Every episode starts and ends at the **open pose** (0 on every sim joint, the Baseline tab's
pose):

```
open ──IK──▶ goal ── hold BODY_HOLD_S (1 s) ──IK──▶ open
```

Both legs are planned by `hand_ik` (`/hand_ik/plan_to_pose`, mink differential IK). It keeps
the links of different fingers apart, except pairs that touch at the start or goal, so a
self-touch goal can still be reached.

## Modes

### Workspace exploration
- **Combinations:** which fingers move, every combination of {Thumb, Index, Middle, Ring}
  (15). The fingers not in it stay open (0).
- Goals are sampled uniformly within the joint ranges of the moving fingers.
- A goal is rejected if two parts of the hand press into each other (contact deeper than 1 mm).
- **Novelty.** A goal must be further than the threshold (L2 of the sim joint angles, default
  0.5 rad) from both:
  1. every goal already reached on the hand, and
  2. every point of every trajectory already played on the hand.
- Only hand runs count as explored; Play on sim is a preview. Saved episodes of every mode
  count, and the explored set is rebuilt from disk, so exploration carries over between
  sessions. A stopped episode adds the path it played but not its goal. Deleting an episode
  removes it from the explored set.

### Fingers → palm
- **Touches:** every combination of fingers, i.e. all 15 non-empty subsets of
  {Thumb, Index, Middle, Ring}: 4 singles, 6 pairs, 4 triples and all four.
- **What touches what:** each finger's fingertip pad (`<finger>_ds_tip`) touches one of the
  palm's `uspa46` patches. Several fingers may share a patch, at different spots.
- **How a pose is found.** Each finger is its own chain on a fixed palm, so each finger's
  touch is found on its own (see *Choosing and checking goals* below), with the other fingers
  open. The results are then combined.
  - The thumb crosses the palm, so in a combination with other fingers it is found last,
    with the other fingers already in place. Its goal is rejected if it presses into them.
  - A combination is kept only if, with MuJoCo reset to it, every fingertip is still in
    contact and nothing presses in. No two fingers may touch deeper than **Min depth**.

### Thumb → fingers
- **Touches:** the thumb's fingertip on one sensor pad of the Index, Middle or Ring finger:
  its fingertip (`<f>_ds_tip`) and its `uspa44` pads `md`, `px` and `bs`. That makes 12
  targets.
- The `bs` pads count as the finger's, although the model mounts them on the palm at the
  finger's base.
- **How a pose is found:** see *Choosing and checking goals* below. The thumb's joints and the
  target finger's joints are chosen; the other fingers stay open.

### Shared by both touch modes
- **Choosing and checking goals.** A goal is chosen at random within the joint ranges of
  the touching finger (and of the finger it touches). MuJoCo is then reset to the goal:
  `mj_resetData`, `qpos` and the actuators' targets set to it, `mj_forward`. This is where
  the sim would be if it jumped there. The goal is kept only if, in MuJoCo's contact list:
  - the fingertip (`<finger>_ds_tip`) is in contact with the target pad, at least 0.5 mm
    deep (the sim's `min_contact_depth`) and at most 3 mm;
  - no two fingers not meant to touch go into one another deeper than **Min depth**, and
    nothing else presses in more than 1 mm.

  Otherwise the goal is ignored and another one is chosen. A goal that touches the pad but
  is rejected (too deep, or pressing elsewhere) is first nudged up to 30 times by about
  0.05 rad per joint, and each nudge is checked the same way. Only checked goals are planned.
- **Why not IK to the pad.** Earlier versions pulled the fingertip to the pad with mink and
  stopped on `mj_geomDistance`. That distance is unreliable once the geoms touch, so most of
  those goals had no MuJoCo contact with the target pad.
- **Felt touch.** On the hand, a touch counts as felt when a touching fingertip's taxel
  magnitude rises by at least `BODY_TOUCH_RISE` from its reading at the episode's start. It is
  measured as a rise rather than an absolute value because curled fingertips read about
  3 units with no contact.

In the model, all 15 palm combinations and all 12 thumb targets have checked goals: the
fingertip is in MuJoCo contact with the pad, 0.5–3 mm deep, with spots spread about 20 mm
across each pad. The Ring finger's `px` and `bs` pads are the hardest; a search can
occasionally run out of samples; press Generate again to retry.

## Layout

| Left | Middle | Right |
|---|---|---|
| Episodes played on the hand, of the mode picked | Mode, novelty threshold (workspace), status, and the hand view below | Combinations of the mode, with Play on sim / Play on hand under the list |

## Combinations panel

Like the Compose tab's Combinations panel. It lists every combination of the picked Mode
(15 for Workspace exploration, 15 for Fingers → palm, 12 for Thumb → fingers), each with the
goals found for it as children:

| Column | Shows |
|---|---|
| Combination | the fingers that move / touch the palm, or the pad the thumb touches; a goal row shows its touches (pad and contact depth) or its novelty now |
| Goals | found / wanted, green when full, orange when partly, ✗ when the model found none |
| On the hand | episodes played on the hand that reached the combination / that goal |

- **Min depth** (default the sim's `min_contact_depth`, 0.5 mm): the deepest two fingers
  not meant to touch may go into one another. Only the thumb and the finger whose pad it
  touches are meant to. Deeper, the sim reports a collision. It is checked:
  - at the goal (MuJoCo reset);
  - along a path open → goal → open that hand_ik plans in the model while the goal is
    searched for. hand_ik does not keep apart links that are close at the goal, so fingers
    near each other there could otherwise pass through each other on the way;
  - on the episode hand_ik actually plans. If it collides, another pose of the same
    combination is tried (up to 3), and a stored goal is no longer listed at that depth.

  Each goal saves its deepest such contact (`collision_depth`). Changing Min depth re-grades
  the list without searching again.
- **Generate** finds goals in the model, in the background, until every combination has
  **Goals per combination** (5 by default). Each touch goal is checked by a MuJoCo reset;
  workspace goals are novel to everything explored and to each other, and those no longer
  novel (after hand runs) are replaced. Press again to stop.
- The goals are saved in `<demo_dir>/body_learning/combinations.json`, so they carry over
  between sessions. A goal searched for there and then is added too.
- **Play on sim** and **Play on hand** (under the list) plan an episode, unless the one
  already planned is of the pick, then play it. They plan:
  - the goal picked in the panel;
  - with a combination picked, its goal played least on the hand;
  - with nothing picked (**Clear pick**), a goal of the combination reached least on the hand
    (ties in list order; combinations the model found none for last).

  A combination without goals is searched for there and then. Picking a goal shows it on
  the hand view.

  While planning or playing, the button pressed reads Stop.
- **Plays** (default 5, right of Play on hand): how many times Play on hand plays the
  episode, one after another from the open pose. Each play is recorded and saved as an
  episode of its own, with `play` / `plays_of` in its meta. Stop ends the play running
  (saved) and skips the rest.
- **Reject** (below Clear pick) removes the picked goal, and its planned episode if there is one. The goal goes
  on the black list (`rejected` in `combinations.json`). It is never used again, and Generate
  and the searches skip any new goal within 0.15 rad (`REJECT_RADIUS`, L2 of the sim angles) of
  it. A search gives up when 20 goals in a row are that close.

## Controls

Keys (anywhere in the tab): **Space** presses Play on hand (Stop while it plans or plays);
**Up** / **Down** pick the previous / next goal in Combinations, across combinations.

| Button | Does |
|---|---|
| Generate | Finds goals for every combination of the mode (see above) |
| Play on sim | Plans the picked goal's episode if needed, then streams it to MuJoCo (`sim_command`) and reports finger–finger contacts. Not saved. |
| Play on hand | Plans the picked goal's episode if needed. Moves to the open pose first if the hand is not there (unrecorded IK move). Then plays the episode with every joint on the hand's stiff gains and records it. The hand turns compliant again when you leave the tab. |

The hand view shows the goal, or the picked episode's goal. It shows the live hand while
playing on the hand or when **Live** is ticked.

## Data

Episodes are saved to `<demo_dir>/body_learning/<mode>/<mode>_<YYYYmmdd_HHMMSS>.npz`, where
`<mode>` is `workspace`, `palm_touch` or `thumb_touch`. They are
listed in this tab only (those of the mode picked), not with the Demonstration tab's
recordings. Stopped episodes are
saved too.

| Key | Content |
|---|---|
| `joint_names`, `sim_joint_names` | hardware / sim joint order |
| `goal_sim`, `goal_reached` | the goal, and whether the play got to it |
| `path_sim`, `planned_path_sim` | the part of the path that was played / the whole planned path (sim) |
| `cmd_t`, `cmd_q`, `cmd_q_sim` | commands sent (hardware / sim) |
| `state_t`, `position`, `velocity`, `effort` | `leap_state`, (N, 16) each |
| `xela_t`, `xela` | raw x/y/z of every taxel, (L, T, 3) |
| `xela_temp` | temperature of every taxel, (L, T); NaN where `xela_server` sends none |
| `xela_baseline` | Create tab's live baseline at the start |
| `meta` (JSON) | mode, times, `ended_by`, hold window (`goal_from` / `goal_to` indices), plan messages, novelty / threshold / samples, `item` (the combination: `th+rf` or a pad name), `goal_id` (its goal in `combinations.json`), `touches` (per finger: pad, part, distance, spot), `touch_felt` |

Times are on the same clock as the node, with `stamp` as the zero.

## Code

- `self_exploration.py`: pure (no ROS or Qt). Holds `ExploredSet`, `sample_workspace_goal`,
  `SelfTouchSolver` (`palm_touch`, `thumb_touch`), `palm_combinations`, `mode_items`,
  `THUMB_TARGETS`, `GoalBank` (`combinations.json`), `least_covered`, `episode_path` and
  `touch_counts`. Tested in
  `test/test_self_exploration.py`.
- `record_demonstration.py`: holds `BodyLearningTab` and the `BODY_*` constants. It also adds
  per-taxel temperatures to the node's play recordings (`xela_temp`).

## Limits / next steps

- The sim only reports finger–finger contacts, so touching the palm is not confirmed in sim.
- Stored touch goals were checked in the model only; whether the hand feels them is in each
  episode's `touch_felt`.
- Workspace novelty is measured in joint space. Fingertip-space novelty could be added if
  joint-space goals turn out to cluster in what the hand feels.
