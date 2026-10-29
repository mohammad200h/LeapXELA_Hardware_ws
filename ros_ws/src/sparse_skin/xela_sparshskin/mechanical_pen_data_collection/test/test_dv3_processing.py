"""Tests of the DreamerV3 chunks (``dv3_processing``) of the Sparsh-skin episodes."""

import os

import numpy as np

from mechanical_pen_data_collection import dv3_processing as dv3
from mechanical_pen_data_collection import sparsh_processing as sp
from test_sparsh_processing import IdentityToSim, recording


def chunks(tmp_path):
    recordings = os.path.join(tmp_path, "rec")
    sparsh, out = os.path.join(recordings, "sparsh_skin"), os.path.join(recordings, "DV3")
    os.makedirs(recordings)
    recording(os.path.join(recordings, "th_1_1.npz"))
    recording(os.path.join(recordings, "th_1_2.npz"), label="failure")
    sp.write_dataset(recordings, sparsh, IdentityToSim())
    return sparsh, out


def test_base62_uuid_matches_embodied():
    assert dv3.base62_uuid(bytes(16)) == "0" * 22
    assert dv3.base62_uuid((61).to_bytes(16, "big")) == "0" * 21 + "Z"
    value = os.urandom(16)
    text = dv3.base62_uuid(value)
    back = sum(62 ** i * dv3.BASE62.index(c) for i, c in enumerate(reversed(text)))
    assert len(text) == 22 and back.to_bytes(16, "big") == value


def test_write_chunks(tmp_path):
    sparsh, out = chunks(tmp_path)
    manifest = dv3.write_chunks(sparsh, out)
    assert sorted(manifest["written"]) == ["episode_th_1_1.npz", "episode_th_1_2.npz"]
    assert not manifest["skipped"]
    for episode, name in manifest["written"].items():
        time, chunk_id, succ, length = name[:-len(".npz")].split("-")
        assert len(chunk_id) == 22 and succ == "0" * 22
        with np.load(os.path.join(sparsh, episode)) as src, np.load(os.path.join(out, name)) as c:
            n = len(src["actions"])
            assert int(length) == n
            expected = dv3.normalize_action(np.concatenate([src["actions"][1:], np.zeros((1, 16))]))
            assert np.allclose(c["action"], expected) and np.all(c["action"][-1] == expected[-1])
            assert np.array_equal(c["forces_local"], src["flex_taxel_fk/forces_local"])
            assert np.array_equal(c["reward"], src["rewards"])
            assert c["is_first"].tolist() == [True] + [False] * (n - 1)
            assert c["is_last"].tolist() == [False] * (n - 1) + [True]
            assert c["is_terminal"][-1] and not c["is_terminal"][:-1].any()
            assert c["stepid"].shape == (n, 20)
            assert dv3.base62_uuid(c["stepid"][0, :16].tobytes()) == chunk_id
            assert int.from_bytes(c["stepid"][3, 16:].tobytes(), "big") == 3
    # Written again: replaced, not added to.
    dv3.write_chunks(sparsh, out)
    assert len([n for n in os.listdir(out) if n.endswith(".npz")]) == 2
