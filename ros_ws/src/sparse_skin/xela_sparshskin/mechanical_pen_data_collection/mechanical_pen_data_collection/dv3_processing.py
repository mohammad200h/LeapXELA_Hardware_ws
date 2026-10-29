"""DreamerV3 replay chunks of the Sparsh-skin episodes, for LEQ_DV3's world model and LEQ.

Does what LEQ_DV3's ``data/leap/convert_episodes.py`` does to the ``sparsh_processing``
episodes (``<recordings>/sparsh_skin/episode_*.npz``), so its output folder (``DV3`` next to
them) can be copied as is to ``LEQ_DV3/data/leap/<task>/`` and trained with
``--task leap_<task>``. The chunks are converted already: do not run ``convert_episodes.py``
on them (the actions would be shifted and scaled twice).

Per episode, one chunk:

- ``action``: the actions shifted one step forward (DreamerV3's reward-state-action order:
  ``action[t]`` is taken from ``obs[t]``; the last one is 0), scaled from
  [``ACTION_LOW``, ``ACTION_HIGH``] to [-1, 1] and clipped;
- ``forces_local``, ``positions``: ``flex_taxel_fk/forces_local`` / ``positions``;
- ``reward``: ``rewards``, not shifted;
- ``is_first`` / ``is_last`` on the first / last step, ``is_terminal`` on the last one when the
  episode's ``terminated_by_env``;
- ``stepid``: the chunk's uuid bytes and the step index;

named ``<time>-<chunk uuid>-<successor uuid>-<steps>.npz`` (embodied's ``Chunk``, the name
``replay.load`` parses). The constants must match LEQ_DV3's ``embodied/envs/leap.py``.
"""

from __future__ import annotations

import datetime
import json
import os
import string
import uuid
from typing import Callable

import numpy as np

from mechanical_pen_data_collection.sparsh_processing import EPISODE_PREFIX, MANIFEST_NAME

# LEQ_DV3 embodied/envs/leap.py
N_JOINTS = 16
N_TAXELS = 368
ACTION_LOW = -1.5
ACTION_HIGH = 2.5
BATCH_LENGTH = 65  # LEQ_DV3 configs.yaml batch_length: shorter episodes give no training window
DEFAULT_OUTPUT_NAME = "DV3"  # next to sparsh_skin
BASE62 = string.digits + string.ascii_letters


def base62_uuid(value: bytes) -> str:
    """A 16 byte uuid as embodied's ``uuid.__str__`` writes it (22 base62 characters)."""
    integer = int.from_bytes(value, "big")
    chars = []
    while integer:
        chars.append(BASE62[integer % 62])
        integer //= 62
    return "".join(reversed(chars)).rjust(22, "0")


def normalize_action(action: np.ndarray) -> np.ndarray:
    action = np.asarray(action, np.float32)
    return np.clip(2.0 * (action - ACTION_LOW) / (ACTION_HIGH - ACTION_LOW) - 1.0, -1.0, 1.0)


def convert_episode(path: str) -> tuple[dict[str, np.ndarray], dict]:
    """The DreamerV3 chunk arrays (without ``stepid``) and the metadata of an episode file."""
    with np.load(path) as raw:
        metadata = (json.loads(str(raw["metadata_json"])) if "metadata_json" in raw.files
                    else {})
        actions = np.asarray(raw["actions"], np.float32)
        forces = np.asarray(raw["flex_taxel_fk/forces_local"], np.float32)
        positions = np.asarray(raw["flex_taxel_fk/positions"], np.float32)
        reward = np.asarray(raw["rewards"], np.float32).reshape(-1)
    n = len(actions)
    if actions.ndim != 2 or actions.shape[1] != N_JOINTS:
        raise ValueError(f"actions are {actions.shape}, not (T, {N_JOINTS})")
    for name, taxels in (("forces_local", forces), ("positions", positions)):
        if taxels.shape != (n, N_TAXELS, 3):
            raise ValueError(f"{name} is {taxels.shape}, not ({n}, {N_TAXELS}, 3)")
    if reward.shape != (n,):
        raise ValueError(f"rewards are {reward.shape}, not ({n},)")
    # Reward-state-action: action[t] is taken from obs[t]; the reward stays with its obs.
    action = normalize_action(np.concatenate([actions[1:], np.zeros_like(actions[:1])]))
    is_first, is_last, is_terminal = (np.zeros(n, bool) for _ in range(3))
    is_first[0] = is_last[-1] = True
    is_terminal[-1] = bool(metadata.get("terminated_by_env", False))
    return {
        "forces_local": forces,
        "positions": positions,
        "action": action,
        "reward": reward,
        "is_first": is_first,
        "is_last": is_last,
        "is_terminal": is_terminal,
    }, metadata


def save_chunk(out_dir: str, chunk: dict[str, np.ndarray], start: datetime.datetime) -> str:
    """Writes ``chunk`` with its ``stepid`` under embodied's chunk name; returns the path."""
    chunk_id = uuid.uuid4().bytes
    n = len(chunk["action"])
    chunk["stepid"] = np.array(
        [np.frombuffer(chunk_id + i.to_bytes(4, "big"), np.uint8) for i in range(n)]
    )
    name = (f"{start.strftime('%Y%m%dT%H%M%S')}-{base62_uuid(chunk_id)}-"
            f"{base62_uuid(bytes(16))}-{n}.npz")
    path = os.path.join(out_dir, name)
    np.savez_compressed(path, **chunk)
    return path


def episode_files(sparsh_dir: str) -> list[str]:
    names = os.listdir(sparsh_dir) if os.path.isdir(sparsh_dir) else []
    return sorted(os.path.join(sparsh_dir, n) for n in names
                  if n.startswith(EPISODE_PREFIX) and n.endswith(".npz"))


def write_chunks(
    sparsh_dir: str, out_dir: str, progress: Callable[[int, int], None] | None = None
) -> dict:
    """Converts every episode of ``sparsh_dir`` into a chunk in ``out_dir``, replacing the
    chunks there (their names are random: writing again would add copies), with
    ``manifest.json``. ``progress(done, total)`` after each episode. Returns the manifest."""
    episodes = episode_files(sparsh_dir)
    os.makedirs(out_dir, exist_ok=True)
    for name in os.listdir(out_dir):
        if name.endswith(".npz"):
            os.remove(os.path.join(out_dir, name))
    try:
        with open(os.path.join(sparsh_dir, MANIFEST_NAME)) as f:
            source = json.load(f)
    except (OSError, ValueError):
        source = {}
    now = datetime.datetime.now()
    written: dict[str, str] = {}
    skipped: dict[str, str] = {}
    steps, short, rewards = [], [], []
    for i, path in enumerate(episodes, start=1):
        episode = os.path.basename(path)
        try:
            chunk, _ = convert_episode(path)
            n = len(chunk["action"])
            out = save_chunk(out_dir, chunk, now + datetime.timedelta(seconds=i))
            written[episode] = os.path.basename(out)
            steps.append(n)
            rewards += [float(chunk["reward"].min()), float(chunk["reward"].max())]
            if n < BATCH_LENGTH:
                short.append(episode)
        except Exception as e:  # noqa: BLE001 - one bad episode does not stop it
            skipped[episode] = f"failed: {e}"
        if progress is not None:
            progress(i, len(episodes))
    manifest = {
        "created": now.isoformat(timespec="seconds"),
        "note": "DreamerV3 chunks, already converted: do not run convert_episodes.py on them",
        "source": os.path.abspath(sparsh_dir),
        "baseline": source.get("baseline"),
        "rewards": source.get("rewards"),
        "freq": source.get("freq"),
        "action_range": [ACTION_LOW, ACTION_HIGH],
        "written": written,
        "skipped": skipped,
        "steps": {"min": min(steps), "max": max(steps), "total": sum(steps)} if steps else {},
        "reward_range": [min(rewards), max(rewards)] if rewards else [],
        f"shorter_than_{BATCH_LENGTH}": short,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    return manifest
