"""Edit tab Play recordings: naming and save / load."""

import os

import numpy as np

from mechanical_pen_data_collection import playback_recording as pr


def recording(path):
    t = np.linspace(0.0, 2.0, 61)
    q = np.random.default_rng(0).normal(size=(61, 16))
    return pr.PlaybackRecording(
        path=path,
        take="/demo/fingers/th/th_2.npz",
        finger="th",
        joint_names=[f"j{i}" for i in range(16)],
        cols=[0, 1, 2, 3],
        cmd_t=t,
        cmd_q=q,
        cmd_local=t + 4.5,
        state_t=t[::3],
        position=q[::3],
        velocity=np.full((21, 16), np.nan),
        effort=q[::3] * 100,
        xela_t=t[::2],
        xela=np.ones((31, 368, 3), np.float32),
        xela_baseline=np.zeros((368, 3)),
        click_t=np.array([1.2]),
        meta={"take": "th_2", "replay_of": "", "ended": "finished"},
    )


def test_indices_count_up_per_take(tmp_path):
    d = str(tmp_path)
    first = pr.next_playback_path(d, "th_2")
    assert os.path.basename(first) == "th_2_1.npz"
    recording(first).save()
    second = pr.next_playback_path(d, "th_2")
    assert os.path.basename(second) == "th_2_2.npz"
    recording(second).save()
    assert os.path.basename(pr.next_playback_path(d, "th_1")) == "th_1_1.npz"


def test_list_only_the_take_s_playbacks(tmp_path):
    d = str(tmp_path)
    for name in ("th_2_1", "th_2_2", "th_1_1", "th_2_extra_1"):
        recording(os.path.join(d, f"{name}.npz")).save()
    names = sorted(os.path.basename(p) for p in pr.list_playbacks(d, "th_2"))
    assert names == ["th_2_1.npz", "th_2_2.npz"]
    assert len(pr.list_playbacks(d)) == 4
    assert pr.list_playbacks(os.path.join(d, "missing"), "th_2") == []


def test_round_trip(tmp_path):
    path = str(tmp_path / "th_2_1.npz")
    rec = recording(path)
    rec.save()
    back = pr.PlaybackRecording.load(path)
    assert back.name == "th_2_1"
    assert back.take == rec.take and back.finger == "th"
    assert back.joint_names == rec.joint_names and back.cols == [0, 1, 2, 3]
    for name in ("cmd_t", "cmd_q", "cmd_local", "state_t", "position", "effort",
                 "xela_t", "xela", "xela_baseline", "click_t"):
        assert np.array_equal(getattr(back, name), getattr(rec, name)), name
    assert np.isnan(back.velocity).all()
    assert back.meta == rec.meta
    assert abs(back.duration - 2.0) < 1e-9
