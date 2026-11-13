# The Reward Design tab

The GUI is in `mechanical_pen_data_collection/record_demonstration.py`:

- `RewardDesignTab` holds the three sub-tabs;
- `RewardTrainPanel` is the Train tab;
- `RewardVisualizePanel` is the Visualize tab.

The GUI node creates the action and service clients at start-up (`LeapStateListener`,
`reward_train` / `reward_evaluate`, one per method in `REWARD_METHODS`). Replies come back on
the ROS thread and reach the Qt widgets through signals.

**Reward Design** has three sub-tabs:

- **Manual**: a description only; not built yet;
- **Reward2Rank**, with **Train** and **Visualize** tabs;
- **Coupled Local Global RL**, with **Train** and **Visualize** tabs.

Each learned method shows a short description and its paper as a link at the top.

## Train

| Control | What it does |
| --- | --- |
| Recordings | The folder to train on. Default: the app's `compose_playbacks`. **Browse** picks another. |
| Output folder | Where the run goes. Empty means `<recordings>/reward_models/<method>`. |
| Epochs, Batch size, Learning rate | Training length and optimiser settings. |
| Validation share | Share of successes and of failures held out (by recording). |
| Step rate | The Sparsh-skin episodes (100 Hz `forces_local` and `positions`) are taken at this rate, default 25 Hz: every 4th step plus the `terminal` step. Higher is finer but uses more GPU memory (about 11 GB at 100 Hz). |
| Seed | The same seed gives the same split and the same start. |
| Log to Weights & Biases, project, run name | W&B settings. Empty name means `<method>_<time>`. |
| **Train** / **Cancel** | Sends the goal. While it runs the button is Cancel, which stops after the current step and keeps the best epoch. |

While a run goes:

- **The progress bar** fills to 15% while the recordings load, then by epoch.
- **The status line** shows the stage and, for example, `epoch 4/30 (best, saved)`.
- **"Loss per epoch"** plots the training loss (blue) and the validation loss (orange).
- **"Validation metric"** plots the main metric: `val/rank_acc` for Rank2Reward,
  `val/return_auc_global` for Coupled Local Global.
- **At the end** it shows the result and a link to the W&B run, and the Visualize tab
  selects the new run.

If the status says the node is not running, the app was launched with
`reward_models:=false`, or the node failed to start; its log is in the launch terminal.

## Visualize

| Part | What it shows |
| --- | --- |
| Runs folder, **Refresh**, run list | The runs in the folder, newest first. Refresh also reloads the recordings list. |
| Run summary | Epochs, batch, learning rate, step rate, how many train / validation recordings and successes, the best epoch with its main metrics, and a link to the W&B run. |
| **Metrics** list and **Training metrics** plot | Every metric the run logged (`metrics.jsonl`). Tick any to plot it over the training steps. The loss and main metric are ticked by default. |
| **Mean reward per validation recording** | One dot per validation recording at the best epoch (green success, red failure), with the mean of each group in the title. |
| **Validation recordings** list | The same recordings with their mean reward. Click one to plot its reward over time. |
| **Evaluate a recording** | Pick any recording in the app's `compose_playbacks` (label shown) and press **Evaluate**. The inference service scores its Sparsh-skin episode with the selected run. A recording without one, or a run from the earlier camera version, gives a message instead. |
| **Reward over a recording** | The reward (white) and its terms over time from `episode_start`: `progress` / `discriminator` for Rank2Reward, `global` / `local` for Coupled Local Global. A term equal to the reward is not drawn twice. |

## Is the run any good?

A quick checklist, in this order:

1. **Did it learn?** Under Training metrics, the training loss falls and the main metric
   rises over the first epochs. A flat loss usually means the learning rate is too low or
   there are too few successes.
2. **Does it generalise?** The validation loss falls with the training loss. If it rises
   while the training loss keeps falling, the model is overfitting. Use the best epoch
   (which is the one kept) or more data.
3. **Does it separate successes from failures?** In **Mean reward per validation
   recording**, green dots should sit above red ones. `val/return_auc` (Rank2Reward) or
   `val/return_auc_global` (Coupled) near 1 says the same in one number; 0.5 is no better
   than chance.
4. **Is it shaped?** Click a few successful validation recordings. A useful reward rises
   through the episode. For Rank2Reward, progress should go from about 0 to about 1. For
   Coupled Local Global, the global reward should be about 1 through a success and jump
   towards 10 at the click. On failures it should stay low or stall.
5. **Coupled Local Global only: are local and global coupled?** `val/local_global_corr` near 1
   and the local curve close to the global one. A low value means the local model's
   gradients would not follow the reward the rollouts are scored with.
6. **Try recordings it never saw.** Evaluate a few recordings outside the validation set,
   including a "no click" and a "kept sliding" failure, and check that their reward stays
   lower than a success's.

To compare runs, use the same seed and validation share, so they are judged on the same
validation recordings. Then compare their best-epoch metrics in the run summary or side by
side in W&B.
