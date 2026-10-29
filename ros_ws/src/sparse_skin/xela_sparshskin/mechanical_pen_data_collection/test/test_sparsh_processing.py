"""Sparsh-skin preprocessing of the episodes for the LEQ_DV3 world model."""

import json
import os

import numpy as np

from mechanical_pen_data_collection import playback_recording as pr
from mechanical_pen_data_collection import sparsh_processing as sp
from mechanical_pen_data_collection import taxel_fk_util as fk


class IdentityToSim:
    """Hardware joints are sim joints (named in FK order)."""

    sim_names = fk.LEAP_JOINT_ORDER

    def __call__(self, names, q):
        return [float(q[names.index(n)]) for n in self.sim_names]


def event(t, name, **params):
    return {"t": t, "name": name, "type": "", "added": 0.0, "end": None, "params": params}


def recording(path, label="success", events=None):
    t = np.linspace(0.0, 3.0, 301)
    xela = np.full((301, fk.NUM_TAXELS, 3), 30000.0, np.float32)
    xela[:, 5] = 10000.0  # dead taxel (hardware id 5)
    xela[150:, 7, 2] += 500.0  # pressed taxel (hardware id 7)
    q = np.full((31, 16), 0.3)
    pr.PlaybackRecording(
        path=path, take="th_1", finger="th", joint_names=list(reversed(fk.LEAP_JOINT_ORDER)),
        cols=list(range(16)), cmd_t=t[::10], cmd_q=np.tile(np.arange(31.0)[:, None], 16) / 30,
        state_t=t[::10], position=q, xela_t=t, xela=xela,
        xela_baseline=np.full((fk.NUM_TAXELS, 3), 30000.0),
    ).save()
    if events is None:
        events = [event(0.5, sp.EPISODE_START), event(2.5, sp.TERMINAL)]
    pr.update_label(path, label=label, events=events)


def test_episode_span_needs_label_and_confirmed_events():
    start, end = event(0.5, sp.EPISODE_START), event(2.5, sp.TERMINAL)
    assert sp.episode_span({"label": "success", "events": [start, end]}) == (0.5, 2.5)
    assert isinstance(sp.episode_span({"events": [start, end]}), str)
    assert isinstance(sp.episode_span({"label": "failure", "events": [start]}), str)
    unconfirmed = event(2.5, sp.TERMINAL, to_be_confirmed=True)
    assert isinstance(sp.episode_span({"label": "success", "events": [start, unconfirmed]}), str)


def test_terminated_by_env():
    start = event(0.5, sp.EPISODE_START)
    assert sp.terminated_by_env({"label": "success", "events": [start, event(2.5, "terminal")]})
    assert sp.terminated_by_env({"label": "failure", "events": [start, event(2.5, "terminal")]})
    truncated = event(2.5, "terminal", process_failure=2.0)
    assert not sp.terminated_by_env({"label": "failure", "events": [start, truncated]})


def test_preprocess_xela_masks_outliers_and_subtracts_baseline():
    t = np.linspace(0.0, 1.0, 11)
    xela = np.full((11, fk.NUM_TAXELS, 3), 30100.0)
    xela[:, 3] = 70000.0
    baseline = np.full((fk.NUM_TAXELS, 3), 30000.0)
    out = sp.preprocess_xela(t, xela, baseline, sp.time_grid(0, 1, 100))
    assert out.shape == (100, fk.NUM_TAXELS, 3)
    dead = int(np.flatnonzero(fk.TAXEL_IDS_IN_FK_ORDER == 3)[0])
    assert np.all(out[:, dead] == 0)
    assert np.allclose(np.delete(out, dead, axis=1), 100.0)


def test_transform_recording(tmp_path):
    path = os.path.join(tmp_path, "th_1_1.npz")
    recording(path)
    data = sp.transform_recording(path, pr.load_label(path), IdentityToSim())
    n = int(2.0 * sp.FREQ)
    assert data["actions"].shape == (n, 16)
    assert data["flex_taxel_fk/forces_local"].shape == (n, fk.NUM_TAXELS, 3)
    assert data["flex_taxel_fk/positions"].shape == (n, fk.NUM_TAXELS, 3)
    assert data["rewards"].tolist() == [0.0] * (n - 1) + [1.0]
    forces = data["flex_taxel_fk/forces_local"]
    dead = int(np.flatnonzero(fk.TAXEL_IDS_IN_FK_ORDER == 5)[0])
    pressed = int(np.flatnonzero(fk.TAXEL_IDS_IN_FK_ORDER == 7)[0])
    assert np.all(forces[:, dead] == 0)
    assert np.allclose(forces[0], 0) and forces[-1, pressed, 2] > 400
    # The command held at each step (k / 30 sent at k * 0.1 s), 0.5 s to 2.5 s.
    assert np.allclose(data["actions"][0], 5 / 30) and np.allclose(data["actions"][-1], 25 / 30)
    metadata = json.loads(str(data["metadata_json"]))
    assert metadata["terminated_by_env"] and metadata["freq"] == sp.FREQ


def test_write_dataset(tmp_path):
    recordings, out = os.path.join(tmp_path, "rec"), os.path.join(tmp_path, "out")
    os.makedirs(recordings)
    recording(os.path.join(recordings, "th_1_1.npz"))
    recording(os.path.join(recordings, "th_1_2.npz"), label="failure",
              events=[event(0.5, sp.EPISODE_START)])
    manifest = sp.write_dataset(recordings, out, IdentityToSim())
    assert manifest["written"] == ["episode_th_1_1.npz"]
    assert list(manifest["skipped"]) == ["th_1_2.npz"]
    with np.load(os.path.join(out, "episode_th_1_1.npz")) as data:
        assert set(data.files) == {
            "actions", "flex_taxel_fk/forces_local", "flex_taxel_fk/positions", "rewards",
            "metadata_json",
        }
    with open(os.path.join(out, sp.STATS_NAME)) as f:
        assert len(json.load(f)["xela_mean"]) == 3
    again = sp.write_dataset(recordings, out, IdentityToSim())
    assert again["kept"] == ["episode_th_1_1.npz"] and not again["written"]


def test_write_dataset_with_baseline_file(tmp_path):
    recordings, out = os.path.join(tmp_path, "rec"), os.path.join(tmp_path, "out")
    os.makedirs(recordings)
    recording(os.path.join(recordings, "th_1_1.npz"))
    baseline = os.path.join(tmp_path, "baseline_20261029_120000.npz")
    np.savez_compressed(baseline, xela_baseline=np.full((fk.NUM_TAXELS, 3), 29000.0))
    sp.write_dataset(recordings, out, IdentityToSim())  # the recording's own baseline first
    manifest = sp.write_dataset(recordings, out, IdentityToSim(), baseline_file=baseline)
    # Written with another baseline: written again, with the file's.
    assert manifest["written"] == ["episode_th_1_1.npz"]
    assert manifest["baseline"] == os.path.abspath(baseline)
    episode = os.path.join(out, "episode_th_1_1.npz")
    assert sp.episode_baseline(episode) == os.path.abspath(baseline)
    with np.load(episode) as data:
        forces = data["flex_taxel_fk/forces_local"]
    unpressed = [i for i, hw in enumerate(fk.TAXEL_IDS_IN_FK_ORDER) if hw not in (5, 7)]
    assert np.allclose(forces[:, unpressed], 1000.0)
    again = sp.write_dataset(recordings, out, IdentityToSim(), baseline_file=baseline)
    assert again["kept"] == ["episode_th_1_1.npz"] and not again["written"]


def test_rewards_from_processing_json_and_process_reward(tmp_path):
    from mechanical_pen_data_collection import episode_processing as ep

    recordings, out = os.path.join(tmp_path, "rec"), os.path.join(tmp_path, "out")
    os.makedirs(recordings)
    recording(os.path.join(recordings, "th_1_1.npz"))
    recording(os.path.join(recordings, "th_1_2.npz"), label="failure")
    ep.save_rewards(recordings, {"success": 10.0, "fail": -5.0, "step": -0.01})
    sp.write_dataset(recordings, out, IdentityToSim())

    def rewards(name):
        with np.load(os.path.join(out, name)) as data:
            return data["rewards"]

    ok, bad = rewards("episode_th_1_1.npz"), rewards("episode_th_1_2.npz")
    assert ok[-1] == 10.0 and np.allclose(ok[:-1], -0.01)
    assert bad[-1] == -5.0 and np.allclose(bad[:-1], -0.01)
    # Process reward: new values on the episodes written, without transforming again.
    new = {"success": 1.0, "fail": -1.0, "step": 0.0}
    assert sp.apply_rewards(out, new) == {"success": 1, "failure": 1, "failed": 0}
    ok, bad = rewards("episode_th_1_1.npz"), rewards("episode_th_1_2.npz")
    assert ok.tolist() == [0.0] * (len(ok) - 1) + [1.0]
    assert bad.tolist() == [0.0] * (len(bad) - 1) + [-1.0]
