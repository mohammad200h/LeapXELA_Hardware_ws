import json
import os
import time

import numpy as np

from mechanical_pen_data_collection.click_press_labels import (
    ABORTED_CURRENT_LIMIT,
    ABORTED_KEPT_SLIDING,
    ABORTED_NO_CLICK,
    ABORTED_NO_CONTACT,
    ABORTED_OTHER,
    CLICKED,
    NO_PRESS,
    UNKNOWN,
    ThumbPlays,
    classify_trace,
    click_press_label,
)
from mechanical_pen_data_collection.playback_recording import load_label, set_manual_label


def ev(event, why=""):
    return {"event": event, "why": why}


def test_classify():
    contact = [ev("approach"), ev("contact", "F 3 >= 1")]
    assert classify_trace(contact + [ev("slip"), ev("click", "click detector"), ev("done")])[0] \
        == CLICKED
    cases = {
        "no click within 8.0 s (F 3.67)": ABORTED_NO_CLICK,
        "thumb keeps sliding (fingertip moved 3.1 mm across d)": ABORTED_KEPT_SLIDING,
        "no contact within 20 mm (F 0.97, contact 1.12)": ABORTED_NO_CONTACT,
        "no contact within 4.0 s": ABORTED_NO_CONTACT,
        "current limit reached (joint 2): raise the Playback current limit": ABORTED_CURRENT_LIMIT,
        "joint current 900 above 800": ABORTED_OTHER,
    }
    for why, label in cases.items():
        assert classify_trace(contact + [ev("abort", why), ev("done")]) == (label, why)
    assert classify_trace([])[0] == NO_PRESS
    assert classify_trace(None)[0] == NO_PRESS
    assert classify_trace(contact + [ev("slip")])[0] == NO_PRESS


def _save(path, meta, mtime):
    np.savez(path, meta=json.dumps(meta))
    os.utime(path, (mtime, mtime))


def test_pairs_and_saves(tmp_path):
    th = tmp_path / "playbacks" / "th"
    compose = tmp_path / "compose_playbacks"
    th.mkdir(parents=True)
    compose.mkdir()
    now = time.time()
    take = str(tmp_path / "fingers" / "th" / "th_4.npz")
    # Two plays of th_4 a minute apart, and one of another take at the same time.
    _save(th / "th_4_1.npz", {"take": "th_4", "click_press_trace": [
        ev("contact"), ev("abort", "no click within 8.0 s (F 3.2)")]}, now - 60.5)
    _save(th / "th_4_2.npz", {"take": "th_4", "click_press_trace": [
        ev("contact"), ev("click", "click detector")]}, now - 0.5)
    _save(th / "th_5_1.npz", {"take": "th_5", "click_press_trace": [
        ev("abort", "thumb keeps sliding (x)")]}, now - 0.4)
    first = str(compose / "th_3_1.npz")
    second = str(compose / "th_3_2.npz")
    lost = str(compose / "th_3_3.npz")
    _save(first, {"takes": {"th": take}}, now - 60.0)
    _save(second, {"takes": {"th": take}}, now)
    _save(lost, {"takes": {"th": take}}, now - 3600.0)
    plays = ThumbPlays(str(tmp_path))
    assert click_press_label(first, plays) == ABORTED_NO_CLICK
    assert click_press_label(second, plays) == CLICKED
    assert click_press_label(lost, plays) == UNKNOWN
    saved = load_label(second)
    assert saved["click_press_play"] == "th_4_2.npz" and "label" not in saved
    assert load_label(lost) is None  # unknown is not saved: tried again later
    # The success / fail mark and the outcome live side by side.
    set_manual_label(second, "success")
    assert load_label(second)["click_press"] == CLICKED
    set_manual_label(second, None)
    assert load_label(second) == {k: v for k, v in saved.items()}
    # Saved: not worked out again (the plays are not needed).
    assert click_press_label(second) == CLICKED
