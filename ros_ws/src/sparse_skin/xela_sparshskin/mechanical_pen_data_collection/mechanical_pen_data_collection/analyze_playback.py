#!/usr/bin/env python3
"""Find out what limits the fingertip force while a take is played back (e.g. a pen click).

Record a bag while playing the take from ``record_demonstration``:

  ros2 bag record -o ~/click_diag /leap_state /cmd_xela /xServTopic

(``leaphand_node`` must publish the motor current in ``leap_state.effort``; start it with
``-p state_rate:=50.0`` so a short click is resolved.) Then:

  ros2 run mechanical_pen_data_collection analyze_playback ~/click_diag --finger if \
      --curr-lim 550

For the joints of ``--finger`` this plots the commanded vs measured position, the tracking
error, the present current as a fraction of the goal current ``--curr-lim`` (the hand node's
``stiff_curr_lim`` while playing) and the fingertip taxel force, and prints a verdict at the
fingertip force peak:

- current at the limit: the motor is saturated, raise ``stiff_curr_lim``;
- current below the limit: the finger stalls short of the target with torque to spare, so the
  force is limited by kP x tracking error (raise ``stiff_kP``, or push the target deeper).
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

from mechanical_pen_data_collection.bag_data import newest_bag, open_reader
from mechanical_pen_data_collection.record_demonstration import (
    FINGERS,
    fingertip_taxel_ids,
    taxel_magnitudes,
)

# leap_state.effort is raw Dynamixel units * DEFAULT_CUR_SCALE (dynamixel_client); the goal
# current (curr_lim) is written in raw units.
DEFAULT_CUR_SCALE = 1.34
# Fraction of the goal current counted as saturated.
SATURATED = 0.9
# Fraction of the force peak that counts as being in contact.
CONTACT = 0.2


def read_bag(uri: str, state_topic: str, cmd_topic: str, xela_topic: str) -> dict:
    reader = open_reader(uri, [state_topic, cmd_topic, xela_topic])
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    classes = {name: get_message(types[name]) for name in (state_topic, cmd_topic, xela_topic)
               if name in types}
    raw: dict[str, list] = {name: [] for name in classes}
    while reader.has_next():
        topic, data, stamp = reader.read_next()
        raw[topic].append((stamp * 1e-9, deserialize_message(data, classes[topic])))
    return raw


def joint_arrays(msgs: list, field: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    kept = [(t, m) for t, m in msgs if len(getattr(m, field)) == len(msgs[0][1].position)]
    return (
        np.array([t for t, _ in kept]),
        np.array([getattr(m, field) for _, m in kept], dtype=float),
        list(msgs[0][1].name),
    )


def hold(t_src: np.ndarray, values: np.ndarray, t: np.ndarray) -> np.ndarray:
    """``values`` (N, J) held from each command until the next one, sampled at ``t``."""
    idx = np.clip(np.searchsorted(t_src, t, side="right") - 1, 0, len(t_src) - 1)
    return values[idx]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("bag", nargs="?", help="bag folder (default: newest under rosbag/)")
    parser.add_argument("--finger", default="if", choices=[f for f, _ in FINGERS])
    parser.add_argument("--curr-lim", type=float, default=550.0,
                        help="goal current of the played finger (stiff_curr_lim), raw units")
    parser.add_argument("--cur-scale", type=float, default=DEFAULT_CUR_SCALE)
    parser.add_argument("--counts-per-unit", type=float, default=1000.0)
    parser.add_argument("--state-topic", default="/leap_state")
    parser.add_argument("--cmd-topic", default="/cmd_xela")
    parser.add_argument("--xela-topic", default="/xServTopic")
    parser.add_argument("--save", help="write the figure to this file instead of showing it")
    args = parser.parse_args(argv)

    uri = args.bag or newest_bag()
    if uri is None:
        print("No bag given and none found.", file=sys.stderr)
        return 1
    raw = read_bag(uri, args.state_topic, args.cmd_topic, args.xela_topic)
    for topic in (args.state_topic, args.cmd_topic, args.xela_topic):
        if not raw.get(topic):
            print(f"No '{topic}' messages in {uri}.", file=sys.stderr)
            return 1

    t_s, q_meas, names = joint_arrays(raw[args.state_topic], "position")
    t_e, cur, _ = joint_arrays(raw[args.state_topic], "effort")
    if len(t_e) == 0:
        print("leap_state has no effort: rebuild/restart leaphand_node so it publishes the "
              "motor current.", file=sys.stderr)
        return 1
    t_c, q_cmd, cmd_names = joint_arrays(raw[args.cmd_topic], "position")
    if cmd_names and cmd_names != names:
        order = [cmd_names.index(n) for n in names]
        q_cmd = q_cmd[:, order]
    cols = [i for i, n in enumerate(names) if n.startswith(f"{args.finger}_")]
    if not cols:
        print(f"No '{args.finger}_*' joints in {names}.", file=sys.stderr)
        return 1

    ids = (fingertip_taxel_ids() or {}).get(args.finger)
    xela_msgs = raw[args.xela_topic]
    readings = [
        np.array([[x.x, x.y, x.z] for s in m.sensors for x in s.taxels]) for _, m in xela_msgs
    ]
    n_taxels = len(readings[0])
    keep = [i for i, r in enumerate(readings) if len(r) == n_taxels]
    t_x = np.array([xela_msgs[i][0] for i in keep])
    xela = np.stack([readings[i] for i in keep])
    if ids is None or ids.max() >= n_taxels:
        print("Fingertip taxel ids unavailable; using all taxels.", file=sys.stderr)
        ids = np.arange(n_taxels)
    # Baseline: median of the readings before the first command (finger not in contact yet).
    before = xela[t_x < t_c[0]]
    baseline = np.median(before if len(before) else xela[:5], axis=0)
    force = taxel_magnitudes(xela, baseline, ids, args.counts_per_unit).sum(axis=1)

    t0 = min(t_s[0], t_c[0], t_x[0])
    rate = (len(t_s) - 1) / max(t_s[-1] - t_s[0], 1e-9)
    if rate < 30.0:
        print(f"Warning: leap_state at {rate:.0f} Hz; restart leaphand_node with "
              f"-p state_rate:=50.0 to resolve the click.", file=sys.stderr)

    # Command held at each leap_state sample; current as a fraction of the goal current.
    q_cmd_s = hold(t_c, q_cmd, t_s)
    err = q_cmd_s - q_meas
    # No command outside playback: the hand node's own goal applies there, not ``q_cmd``.
    err[(t_s < t_c[0]) | (t_s > t_c[-1] + 0.5)] = np.nan
    cmd_dt = np.median(np.diff(t_c)) if len(t_c) > 1 else 0.0
    if cmd_dt > 0.1:
        print(f"Warning: {args.cmd_topic} arrives every {cmd_dt:.2f} s ({1 / cmd_dt:.1f} Hz); "
              "the take is played as a staircase.", file=sys.stderr)
    cur_frac = np.abs(cur) / (args.cur_scale * args.curr_lim)

    k = int(np.argmax(force))
    t_peak = t_x[k]
    contact = force > CONTACT * force[k]
    in_contact = np.interp(t_s, t_x, contact.astype(float)) > 0.5
    j_peak = int(np.argmin(np.abs(t_s - t_peak)))

    print(f"Bag: {uri}")
    print(f"Fingertip force peak {force[k]:.3f} (sum of taxel magnitudes) at "
          f"{t_peak - t0:.2f} s; contact {in_contact.sum()} leap_state samples ({rate:.0f} Hz)\n")
    print(f"{'joint':<8}{'cmd':>9}{'meas':>9}{'error':>9}"
          f"{'cur/lim@peak':>14}{'max in contact':>16}")
    saturated = []
    for c in cols:
        frac_max = cur_frac[in_contact, c].max() if in_contact.any() else cur_frac[j_peak, c]
        if frac_max >= SATURATED:
            saturated.append(names[c])
        print(f"{names[c]:<8}{q_cmd_s[j_peak, c]:>9.3f}{q_meas[j_peak, c]:>9.3f}"
              f"{err[j_peak, c]:>9.3f}{cur_frac[j_peak, c]:>13.0%} {frac_max:>15.0%}")
    print()
    if saturated:
        print(f"Verdict: CURRENT-LIMITED. Reaching >= {SATURATED:.0%} of the goal current during "
              f"contact: {', '.join(saturated)}. Raise stiff_curr_lim (motor permitting).")
    else:
        print(f"Verdict: ERROR-LIMITED. No joint reaches {SATURATED:.0%} of the goal current; "
              "the finger stalls short of the target with torque to spare. Raise stiff_kP, or "
              "command the target deeper during contact (force-aware replay).")

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(11, 10))
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for n, c in enumerate(cols):
        color = colors[n % len(colors)]
        axes[0].plot(t_s - t0, q_meas[:, c], color=color, label=f"{names[c]} measured")
        axes[0].step(t_c - t0, q_cmd[:, c], where="post", color=color, ls="--", alpha=0.7,
                     label=f"{names[c]} cmd")
        axes[1].plot(t_s - t0, err[:, c], color=color, label=names[c])
        axes[2].plot(t_s - t0, cur_frac[:, c], color=color, label=names[c])
    axes[0].set_ylabel("position (rad)")
    axes[1].set_ylabel("cmd - meas (rad)")
    axes[1].axhline(0.0, color="grey", lw=0.5)
    axes[2].set_ylabel("|current| / curr_lim")
    axes[2].axhline(1.0, color="red", ls=":", label="goal current")
    axes[3].plot(t_x - t0, force, color="black")
    axes[3].set_ylabel("fingertip force\n(sum |Δtaxel|)")
    axes[3].set_xlabel("time (s)")
    for ax in axes:
        ax.axvline(t_peak - t0, color="red", alpha=0.4)
        ax.grid(alpha=0.3)
    for ax in axes[:3]:
        ax.legend(fontsize=7, ncol=4, loc="upper left")
    fig.suptitle(f"{args.finger} playback: {uri}")
    fig.tight_layout()
    if args.save:
        fig.savefig(args.save, dpi=120)
        print(f"Saved {args.save}")
    else:
        plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
