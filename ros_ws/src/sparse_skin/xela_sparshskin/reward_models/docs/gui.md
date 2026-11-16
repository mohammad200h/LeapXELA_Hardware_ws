# The Reward tab

The GUI is in `mechanical_pen_data_collection/record_demonstration.py`:

- `RewardTab` is a `DemonstrationTab` (the same player) with the reward graphs in the middle;
- `RewardPredictionPlot` is one graph (one per entry of `REWARD_PLOTS`: Rank2Reward, SARM);
- `stage_segments` turns SARM's predicted stage per step into (start, end, stage) spans.

The GUI node creates one `EvaluateReward` client per method in `REWARD_METHODS`
(`rank2reward`, `sarm`) at start-up (`LeapStateListener.reward_evaluate`). Replies come back
on the ROS thread and reach the Qt widgets through `RewardEvalSignals`.

## Layout

| Part | What it shows |
| --- | --- |
| Left | The Play on hand recordings, with the Demonstration tab's filters, Success / Fail, Delete and Refresh. |
| Top of the middle | The recording's title, **Play**, the play bar, **Stream to sim** and the audio output, as on the Demonstration tab. SARM's predicted stages are shaded over the play bar; hover for the stage and its time. |
| **Manual** graph and fields | Success / Fail / Every step (saved in `processing.json`). The graph shows Every step from `episode_start` to `terminal` and the Success or Fail value at `terminal`; it redraws as you edit. |
| **Rank2Reward** graph | The reward (white), `progress` and `discriminator`. |
| **SARM** graph | The reward (white, Δφ by default), `progress` φ, and the predicted stages **grip** (blue), **press** (orange) and **click** (green) as shaded regions. |
| Right | The camera recording with the pen box, and the FK taxels with the recorded Xela readings. |

The keys are the Demonstration tab's: Space play / pause, Left / Right seek, ] / [ jump to
the Thumb's first contact and the last part, Up / Down change recording, S / F mark it.

Above each graph, the **run** list holds every trained run of that method that has a
`model.pt`:

- the comparison runs `<recordings>/reward_models/comparison/<comparison>/runs/<method>_<sparsh|proprio>_s<seed>`
  (newest comparison first; `sarm` does not list `sarm_failures`),
- the runs trained by the train node, `<recordings>/reward_models/<method>/<run>`.

The default is the newest comparison's `<method>_sparsh_s0`. The pick is remembered.
**Refresh** lists the runs again.

## How a prediction is made

When a recording is picked, or the run changes, the graph sends an `EvaluateReward` request
(the run folder and the recording) to `/<method>_inference/evaluate`. The node scores the
recording's Sparsh-skin episode (`episode_start` to `terminal`) and returns the reward and
its terms per step, at the recording's own times, so the graph lines up with the play bar.
Each answer is kept for that (run, recording) pair, so going back to a recording is
instant.

The status line beside the run list says what went wrong otherwise:

- **not running**: the app was launched with `reward_models:=false`, or the node failed to
  start (its log is in the launch terminal);
- **no Sparsh-skin episode**: the recording is not processed yet (Processing tab: mark
  `episode_start` / `terminal`, then run the Sparsh-skin transform).

## Writing the rewards into the episodes

The Processing tab's **Process reward** writes the rewards ticked under **Store** (Manual,
Rank2Reward, SARM) into every Sparsh-skin episode (`sparsh_skin/<rate>hz/episode_*.npz`):

| Array | What it holds |
| --- | --- |
| `rewards/manual` | The Manual fields. |
| `rewards/rank2reward` | Rank2Reward's reward, interpolated onto the episode's steps. |
| `rewards/sarm` | SARM's progress φ, interpolated onto the episode's steps. |
| `rewards/sarm_delta` | φ_t − φ_{t−1} on the episode's own steps (sums to the progress made). |
| `rewards` | A copy of the **Primary** one (radio buttons), which Process for DreamerV3 puts in the chunks' `reward`. |

The models use the runs picked on this tab, one inference call per recording. The episode's
metadata records `reward_primary` and `reward_models` (the run of each model). A Sparsh-skin
transform that rewrites an episode puts the Manual reward back as primary, so run Process
reward again afterwards.

## Training

The Reward tab only shows predictions. Train with the comparison script
([compare.py](../reward_models/compare.py)), or start a `<method>_train` node by hand and send
it a `TrainReward` goal ([nodes_and_interfaces.md](nodes_and_interfaces.md)).
