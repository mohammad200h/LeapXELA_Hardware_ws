# The data: from Sparsh-skin episodes to clips

All of this is in [data.py](../reward_models/data.py).

The reward models learn only from the **Sparsh-skin episodes**: the `flex_taxel_fk/forces_local`
and `flex_taxel_fk/positions` of the 368 taxels. They use no camera images. The Process tab's
Sparsh-skin transform writes these episodes (`sparsh_processing`); they are the same files the
LEQ_DV3 world model is trained on.

## Which recordings are used

Training reads the Play on hand recordings in the recordings folder (by default
`<ws>/demonstrations/compose_playbacks`). A recording is used when:

1. it is an **episode** by the same rule as the Sparsh-skin transform
   (`sparsh_processing.eligible_episodes`): labelled `success` or `failure`, with a confirmed
   `episode_start` and a later confirmed `terminal`;
2. its Sparsh-skin episode exists:
   `<recordings>/sparsh_skin/episode_<recording>.npz`;
3. that episode lies within the label's span. The transform trims the span to the time every
   stream covers, so an episode normally starts or ends a little inside it. One that reaches
   more than 0.02 s outside it was written for an older label, and is skipped until you run the
   transform again.

Everything else is skipped, and the reason is written to the run's `config.json` under
`skipped`. On the current data **564 episodes are used (181 successes, 383 failures)**. The
17 skipped recordings have no label or no confirmed `terminal`.

The label is always the recording's **current** `.label.json`, not the label stored inside
the episode.

## What a clip holds

[`load_clip`](../reward_models/data.py#L124) turns one recording's episode into a `Clip`:

| Field | Shape | What it is |
| --- | --- | --- |
| `t` | (N,) | Recording time (s) of each step |
| `obs` | (N, 368, 6) float32 | Per taxel, in FK order: `forces_local` x, y, z, then `positions` x, y, z |
| `actions` | (N, 16) float32 | The episode's `actions` (sim joint targets); used only by the Coupled Local Global local model |
| `label` | str | `success` or `failure` |

Where the observation channels come from:

- **`forces_local`** is the Sparsh-skin preprocessed Xela reading:
  - resampled to 100 Hz with a cubic spline;
  - readings outside the valid raw range set to 0 (a dead taxel);
  - the Baseline tab's no-contact baseline subtracted, the same baseline file for every
    episode.
- **`positions`** is each taxel's FK position in metres, in the hand base frame, computed from
  the sim joint angles. Positions carry the hand's pose; forces carry the contact.

`obs` is stored as read from the episode. The networks normalise it (see below).

## Step rate

An episode is on a 100 Hz grid from `episode_start` to `terminal`, so an 11 s episode has
about 1180 steps. Training at 100 Hz would put 11 GB on the GPU and make neighbouring steps
almost identical. The **Step rate** setting (`step_hz`, default 25 Hz) keeps every
`round(100 / step_hz)`-th step ([`step_indices`](../reward_models/data.py#L117)). The **last
step, at `terminal`, is always kept**, because a success's last step is the click.

| Step rate | Stride | Steps (all 564 episodes) | GPU memory |
| --- | --- | --- | --- |
| 100 Hz | 1 | ~1.27 M | ~11 GB |
| 25 Hz (default) | 4 | ~318 k | ~2.8 GB |
| 10 Hz | 10 | ~127 k | ~1.1 GB |

A run is evaluated at its own step rate, which is stored in the run.

## Normalisation

[`obs_stats`](../reward_models/data.py#L109) gives a per-channel z-score:

| Channels | Mean / std from |
| --- | --- |
| forces x, y, z | `sparsh_skin/sparsh_stats.json` (`xela_mean`, `xela_std`): the same as LEQ_DV3's `forces_norm` |
| positions x, y, z | Every step of the run's training episodes |

These six means and stds are saved in the run (`config.json` `obs_mean` / `obs_std`). They are
also held as buffers inside each network's `StateEncoder`, so a checkpoint always normalises
the way it was trained. z-scores are clipped to ±20.

## Loading

Each episode is a single `.npz` read, 8 at a time (`LOAD_THREADS`). All 564 load in about
6 s, so there is no cache. Re-running the Sparsh-skin transform (for example with a new
baseline) is picked up by the next training run.

## The train / validation split

[`split_clips`](../reward_models/data.py#L193) splits **by recording, separately for each
label**:

- `round(val_fraction × successes)` successes and `round(val_fraction × failures)` failures
  go to validation, with at least one of each when there are two or more;
- the same `seed` gives the same split, so runs with the same seed are compared on the same
  validation recordings;
- the names of both sets are in the run's `config.json` (`train_recordings`,
  `val_recordings`).

A run needs at least 2 successes in its training set; otherwise the action ends with
`ABORTED` and says so.

## On the GPU

[`StepBank`](../reward_models/training.py#L106) puts every training step's `obs` and
`actions` in one tensor on the GPU, so a batch is just an index lookup. It also keeps, per
step:

- `phase`: 0 at `episode_start`, 1 at `terminal`;
- `time_to_end`: seconds left until `terminal`;
- `step_success`: 1 for steps of successful recordings.

Batches are sampled with each recording weighted by its length, so every step is equally
likely to be drawn.
