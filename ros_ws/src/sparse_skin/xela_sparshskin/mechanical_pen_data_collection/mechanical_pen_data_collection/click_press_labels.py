#!/usr/bin/env python3
"""Label the Compose tab's Play on hand recordings with how the Thumb's ``click_press`` ended.

A Play on hand recording (``<demo_dir>/compose_playbacks/<box>_<n>.npz``) does not hold the
press itself: the Thumb's own Edit-tab Play recording, saved just before it
(``<demo_dir>/playbacks/th/<take>_<k>.npz``), has the press's ``click_press_trace`` in its
``meta``. The two are paired by the Thumb take they played and their save times (the Thumb play
is saved 0.3-0.7 s before the Play on hand recording; up to ``PAIR_WINDOW_S`` is accepted).

The first ``click`` or ``abort`` event of the trace gives the label:

- ``clicked``: the press ended in a click;
- ``aborted_no_click``: "no click within N s";
- ``aborted_kept_sliding``: "thumb keeps sliding (...)";
- ``aborted_no_contact``: "no contact within N mm / s";
- ``aborted_current_limit``: "current limit reached ...";
- ``aborted_other``: any other abort (e.g. "joint current N above M", "no live fingertip
  force");
- ``no_press``: the Thumb play has no press (no ``click_press`` region, or it never ran);
- ``unknown``: no Thumb play found for the recording.

It goes into the recording's ``<box>_<n>.label.json`` as ``click_press`` (with the abort reason
as ``click_press_why`` and the Thumb play as ``click_press_play``), next to the success /
failure mark, which is left as it is. The Demonstration and Analysis tabs label recordings
without one when they list them; this script labels them all at once:

  ros2 run mechanical_pen_data_collection label_click_press
  ros2 run mechanical_pen_data_collection label_click_press --demo-dir ~/demos --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter

import numpy as np

from mechanical_pen_data_collection.playback_recording import (
    list_playbacks,
    load_label,
    update_label,
)

CLICKED = "clicked"
ABORTED_NO_CLICK = "aborted_no_click"
ABORTED_KEPT_SLIDING = "aborted_kept_sliding"
ABORTED_NO_CONTACT = "aborted_no_contact"
ABORTED_CURRENT_LIMIT = "aborted_current_limit"
ABORTED_OTHER = "aborted_other"
NO_PRESS = "no_press"
UNKNOWN = "unknown"
# In the order the tabs show them.
OUTCOMES = (CLICKED, ABORTED_NO_CLICK, ABORTED_KEPT_SLIDING, ABORTED_NO_CONTACT,
            ABORTED_CURRENT_LIMIT, ABORTED_OTHER, NO_PRESS, UNKNOWN)
# Short names for the tabs.
SHORT = {
    CLICKED: "clicked", ABORTED_NO_CLICK: "no click", ABORTED_KEPT_SLIDING: "kept sliding",
    ABORTED_NO_CONTACT: "no contact", ABORTED_CURRENT_LIMIT: "current limit",
    ABORTED_OTHER: "other abort", NO_PRESS: "no press", UNKNOWN: "unknown",
}
# Abort reasons (``ClickPress`` "why" texts) -> label.
ABORT_REASONS = (
    (re.compile(r"^no click within"), ABORTED_NO_CLICK),
    (re.compile(r"^thumb keeps sliding"), ABORTED_KEPT_SLIDING),
    (re.compile(r"^no contact within"), ABORTED_NO_CONTACT),
    (re.compile(r"^current limit reached"), ABORTED_CURRENT_LIMIT),
)
# s a Thumb play may be saved before (or, a little, after) its Play on hand recording.
PAIR_WINDOW_S = (-2.0, 10.0)


def classify_trace(trace: list[dict] | None) -> tuple[str, str]:
    """(label, why) of a ``click_press_trace``: its first click or abort."""
    for event in trace or []:
        if event.get("event") == "click":
            return CLICKED, str(event.get("why", ""))
        if event.get("event") == "abort":
            why = str(event.get("why", ""))
            label = next((lab for pattern, lab in ABORT_REASONS if pattern.search(why)),
                         ABORTED_OTHER)
            return label, why
    if trace:
        return NO_PRESS, "the press neither clicked nor aborted"
    return NO_PRESS, "no click_press in the Thumb play"


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(str(path)))[0]


def _meta(path: str) -> dict:
    with np.load(path, allow_pickle=False) as data:  # only the small entries are read
        return json.loads(str(data["meta"])) if "meta" in data.files else {}


class ThumbPlays:
    """The Thumb's Edit-tab Play recordings of a demonstrations folder, by take; their meta
    is read once (again only when a file changes)."""

    _cache: dict[str, tuple[float, str, list | None]] = {}  # path -> (mtime, take, trace)

    def __init__(self, demo_dir: str) -> None:
        self.by_take: dict[str, list[tuple[float, str]]] = {}  # take -> [(mtime, path)]
        for path in list_playbacks(os.path.join(demo_dir, "playbacks", "th")):
            try:
                mtime = os.path.getmtime(path)
                cached = self._cache.get(path)
                if cached is None or cached[0] != mtime:
                    meta = _meta(path)
                    cached = (mtime, _stem(meta.get("take", "")),
                              meta.get("click_press_trace"))
                    self._cache[path] = cached
            except Exception:  # noqa: BLE001 - an unreadable play is skipped
                continue
            self.by_take.setdefault(cached[1], []).append((mtime, path))

    def find(self, recording: str, thumb_take: str) -> str | None:
        """The Thumb play of the Play on hand ``recording`` (which played ``thumb_take``)."""
        try:
            saved = os.path.getmtime(recording)
        except OSError:
            return None
        lo, hi = PAIR_WINDOW_S
        near = [(saved - t, p) for t, p in self.by_take.get(_stem(thumb_take), [])
                if lo <= saved - t <= hi]
        if not near:
            return None
        return min(near, key=lambda gp: (gp[0] < 0, abs(gp[0])))[1]  # just before, first

    def trace(self, play: str) -> list | None:
        cached = self._cache.get(play)
        return cached[2] if cached is not None else None


def click_press_outcome(recording: str, plays: ThumbPlays) -> dict:
    """``{"click_press", "click_press_why", "click_press_play"}`` of a Play on hand
    recording."""
    try:
        thumb = _meta(recording).get("takes", {}).get("th", "")
    except Exception as e:  # noqa: BLE001
        return {"click_press": UNKNOWN, "click_press_why": f"could not read it: {e}",
                "click_press_play": ""}
    if not thumb:
        return {"click_press": NO_PRESS, "click_press_why": "no Thumb take played",
                "click_press_play": ""}
    play = plays.find(recording, thumb)
    if play is None:
        return {"click_press": UNKNOWN,
                "click_press_why": f"no Thumb play of {_stem(thumb)} saved with it",
                "click_press_play": ""}
    label, why = classify_trace(plays.trace(play))
    return {"click_press": label, "click_press_why": why,
            "click_press_play": os.path.basename(play)}


def click_press_label(recording: str, plays: ThumbPlays | None = None,
                      demo_dir: str | None = None, force: bool = False) -> str:
    """The ``click_press`` label of a Play on hand recording, worked out and saved in its
    label file the first time (every time with ``force``). ``plays`` or ``demo_dir`` is needed
    only then (``demo_dir`` defaults to the recording's folder's parent)."""
    saved = (load_label(recording) or {}).get("click_press")
    if saved and not force:
        return saved
    if plays is None:
        demo_dir = demo_dir or os.path.dirname(os.path.dirname(os.path.abspath(recording)))
        plays = ThumbPlays(demo_dir)
    outcome = click_press_outcome(recording, plays)
    if outcome["click_press"] != UNKNOWN or force:
        try:
            update_label(recording, **outcome)
        except OSError:
            pass
    return outcome["click_press"]


def default_demo_dir() -> str:
    """``<colcon workspace>/demonstrations``, as ``record_demonstration``'s default."""
    try:
        from mechanical_pen_data_collection.bag_data import default_bag_dir

        return os.path.join(os.path.dirname(default_bag_dir()), "demonstrations")
    except Exception:  # noqa: BLE001 - package not installed (e.g. run from source)
        return os.path.expanduser("~/demonstrations")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--demo-dir", default=None,
                        help="demonstrations folder (default: <workspace>/demonstrations)")
    parser.add_argument("--force", action="store_true", help="label already labelled ones again")
    args = parser.parse_args()
    demo_dir = os.path.expanduser(args.demo_dir or default_demo_dir())
    paths = list_playbacks(os.path.join(demo_dir, "compose_playbacks"))
    if not paths:
        print(f"No Play on hand recordings in {demo_dir}/compose_playbacks")
        return 1
    plays = ThumbPlays(demo_dir)
    counts: Counter = Counter()
    by_mark: dict[str, Counter] = {}
    for path in reversed(paths):  # oldest first
        name = _stem(path)
        before = (load_label(path) or {}).get("click_press")
        label = click_press_label(path, plays, force=args.force)
        info = load_label(path) or {}
        counts[label] += 1
        by_mark.setdefault(label, Counter())[info.get("label") or "not labelled"] += 1
        kept = " (kept)" if before and not args.force else ""
        print(f"{name:14} {label:22} {info.get('click_press_why', '')[:70]}{kept}")
    print()
    total = sum(counts.values())
    for label in OUTCOMES:
        if counts[label]:
            marks = ", ".join(f"{k} {v}" for k, v in sorted(by_mark[label].items()))
            share = 100.0 * counts[label] / total
            print(f"{label:22} {counts[label]:4d} ({share:.0f} %)  [{marks}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
