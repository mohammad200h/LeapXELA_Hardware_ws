"""Goals of the Learning about your own body tab (``self_exploration``): novelty, workspace
goals and self-touch on the installed MuJoCo model (skipped when it is not installed)."""

import json

import numpy as np
import pytest

from mechanical_pen_data_collection import self_exploration as se


def test_novelty_is_the_distance_to_goals_and_points():
    explored = se.ExploredSet(2)
    assert explored.novelty(np.zeros(2)) == float("inf")
    explored.add_episode(np.array([1.0, 0.0]), np.array([[0.0, 3.0], [0.0, 4.0]]))
    assert explored.novelty(np.array([1.0, 1.0])) == pytest.approx(1.0)
    assert explored.novelty(np.array([0.0, 5.0])) == pytest.approx(1.0)
    explored.add_episode(None, np.array([[1.0, 1.0]]))  # goal not reached: only its path
    assert len(explored.goals) == 1
    assert explored.novelty(np.array([1.0, 1.0])) == 0.0


def test_explored_set_from_saved_episodes(tmp_path):
    names = ["a", "b"]
    for i, reached in enumerate((True, False)):
        np.savez_compressed(
            tmp_path / f"workspace_{i}.npz",
            sim_joint_names=np.array(["b", "a"]),  # saved in another order
            goal_sim=np.array([2.0, 1.0]) * (i + 1),
            goal_reached=reached,
            path_sim=np.array([[0.0, 0.0], [2.0, 1.0]]),
            meta=json.dumps({"goal_reached": reached}),
        )
    (tmp_path / "broken.npz").write_bytes(b"not a file")
    explored = se.ExploredSet.from_episodes(sorted(tmp_path.iterdir()), names)
    np.testing.assert_allclose(explored.goals, [[1.0, 2.0]])
    assert len(explored.points) == 4


def test_episode_path_holds_the_goal():
    out = np.array([[0.0], [0.5], [1.0]])
    back = np.array([[1.0], [0.0]])
    path = se.episode_path(out, back, dt=0.1, hold_s=0.3)
    np.testing.assert_allclose(path[:, 0], [0.0, 0.5, 1.0, 1.0, 1.0, 1.0, 0.0])


def test_waypoints_bring_the_thumb_in_last():
    names = ["th_cmc", "if_mcp", "mf_mcp"]
    goal = np.array([1.0, 2.0, 3.0])
    assert se.waypoints(names, goal, ("th",)) == []
    assert se.waypoints(names, goal, ("if", "mf")) == []
    assert se.waypoints(names, goal, None) == []
    (mid,) = se.waypoints(names, goal, ("th", "if"))
    np.testing.assert_allclose(mid, [0.0, 2.0, 3.0])
    path = se.join_paths([np.array([[0.0], [1.0]]), np.array([[1.0], [2.0]])])
    np.testing.assert_allclose(path[:, 0], [0.0, 1.0, 2.0])


def test_touch_items():
    combos = se.palm_combinations()
    assert len(combos) == 15 and len(set(combos)) == 15
    assert combos[0] == ("th",) and combos[-1] == se.FINGERS
    assert se.palm_combination(se.item_key(("th", "rf"))) == ("th", "rf")
    assert se.palm_combination("if_md_uspa44") is None
    assert len(se.THUMB_TARGETS) == 12
    assert all(se.part_of(pad) in ("if", "mf", "rf") for pad in se.THUMB_TARGETS)


def test_every_mode_has_its_combinations():
    assert se.mode_items(se.WORKSPACE) == se.mode_items(se.PALM_TOUCH)
    assert len(se.mode_items(se.PALM_TOUCH)) == 15
    assert se.mode_items(se.THUMB_TOUCH) == list(se.THUMB_TARGETS)


def test_goal_bank_round_trip(tmp_path):
    path = str(tmp_path / "body" / "combinations.json")
    bank = se.GoalBank(["a", "b"])
    bank.fail(se.PALM_TOUCH, "th", "none")
    bank.add(se.PALM_TOUCH, "th", {"id": "x", "goal": np.array([1.0, 2.0]), "touches": {}})
    bank.add(se.WORKSPACE, "if", {"id": "y", "goal": np.array([3.0, 4.0])})
    bank.fail(se.THUMB_TOUCH, "if_ds_tip", "no contact")
    bank.save(path)
    loaded = se.GoalBank.load(path, ["b", "a"])  # loaded in another order
    np.testing.assert_allclose(loaded.of(se.PALM_TOUCH, "th")[0]["goal"], [2.0, 1.0])
    assert loaded.failed == {se.PALM_TOUCH: {}, se.THUMB_TOUCH: {"if_ds_tip": "no contact"}}
    # Rejected: off the goals, on the black list (kept on disk), with goals near it.
    assert loaded.reject(se.PALM_TOUCH, "th", "x")["id"] == "x"
    assert loaded.of(se.PALM_TOUCH, "th") == []
    assert loaded.near_rejected(se.PALM_TOUCH, "th", np.array([2.05, 1.0]))
    assert not loaded.near_rejected(se.PALM_TOUCH, "th", np.array([3.0, 1.0]))
    assert not loaded.near_rejected(se.PALM_TOUCH, "if", np.array([2.0, 1.0]))
    loaded.save(path)
    again = se.GoalBank.load(path, ["a", "b"])
    np.testing.assert_allclose(again.rejected[se.PALM_TOUCH]["th"][0]["goal"], [1.0, 2.0])
    assert loaded.reject(se.PALM_TOUCH, "th", "x") is None
    loaded.remove(se.WORKSPACE, {"y"})
    assert loaded.of(se.WORKSPACE, "if") == []
    assert se.GoalBank.load(str(tmp_path / "none.json"), ["a"]).goals == {}


def test_least_covered_order():
    keys = ["a", "b", "c", "d", "e"]
    assert se.least_covered(keys, {"a": 3, "b": 1}, {"d"}) == ["c", "e", "b", "a"]


@pytest.fixture(scope="module")
def ik():
    pytest.importorskip("mink")
    try:
        from mechanical_pen_data_collection.hand_ik import HandIK

        return HandIK()
    except Exception as e:  # noqa: BLE001 - no installed model here
        pytest.skip(f"no hand model: {e}")


def test_workspace_goals_are_novel_and_free(ik):
    import mujoco

    names = list(ik.joint_names)
    rng = np.random.default_rng(1)
    explored = se.ExploredSet(len(names))
    for _ in range(5):
        goal, novelty, _ = se.sample_workspace_goal(ik, names, rng, explored, 0.8)
        assert novelty > 0.8 and explored.novelty(goal) == novelty
        ik.data.qpos[:] = ik.to_qpos(names, goal)
        mujoco.mj_forward(ik.model, ik.data)
        assert not se.pressing_pairs(ik.model, ik.data)
        explored.add_episode(goal, np.linspace(np.zeros(len(names)), goal, 10))
    with pytest.raises(RuntimeError):
        se.sample_workspace_goal(ik, names, rng, explored, 100.0, tries=20)
    # Only the picked fingers move.
    goal, _, _ = se.sample_workspace_goal(ik, names, rng, explored, 0.3, fingers=("th", "rf"))
    still = [i for i, n in enumerate(names) if n.split("_")[0] in ("if", "mf")]
    np.testing.assert_allclose(goal[still], 0.0)


@pytest.fixture(scope="module")
def solver(ik):
    return se.SelfTouchSolver(ik)


def test_every_finger_combination_touches_the_palm(ik, solver):
    names = list(ik.joint_names)
    rng = np.random.default_rng(2)
    assert solver.palm_pads == ["uspa46_1", "uspa46_2", "uspa46_3"]
    for combo in se.palm_combinations():
        goal, details = solver.palm_touch(names, combo, rng)
        assert set(details) == set(combo)
        assert all(touch["part"] == se.PALM for touch in details.values())
        # MuJoCo reset to the goal: every fingertip is in contact with its palm pad.
        depths = solver.touch_depths(names, goal, {f: t["pad"] for f, t in details.items()})
        assert min(depths.values()) >= se.CONTACT_DEPTH
        # The fingers not in the combination stay open.
        rest = [i for i, n in enumerate(names) if n.split("_")[0] not in combo]
        np.testing.assert_allclose(goal[rest], 0.0, atol=1e-6)


def test_thumb_touches_finger_pads(ik, solver):
    names = list(ik.joint_names)
    rng = np.random.default_rng(3)
    assert solver.thumb_targets == list(se.THUMB_TARGETS)
    for pad in se.THUMB_TARGETS:
        goal, details = solver.thumb_touch(names, pad, rng)
        assert details["th"]["pad"] == pad
        # MuJoCo reset to the goal: the thumb's fingertip is in contact with the pad.
        assert solver.touch_depths(names, goal, {"th": pad})["th"] >= se.CONTACT_DEPTH


def test_goals_and_paths_keep_the_fingers_apart(ik, solver):
    import mujoco

    names = list(ik.joint_names)
    rng = np.random.default_rng(4)
    data = mujoco.MjData(ik.model)
    solver.min_depth = se.MIN_DEPTH
    for mode, key, (goal, _) in (
        (se.PALM_TOUCH, "th+if+rf", solver.palm_touch(names, ("th", "if", "rf"), rng)),
        (se.THUMB_TOUCH, "mf_ds_tip", solver.thumb_touch(names, "mf_ds_tip", rng)),
    ):
        # At the goal, no two fingers not meant to touch deeper than the min depth.
        depth, pair, _ = se.finger_collision(
            ik.model, data, names, goal[None], se.touch_pairs(mode, key)
        )
        assert depth <= se.MIN_DEPTH, (key, pair, depth)
    assert se.touch_pairs(se.THUMB_TOUCH, "rf_md_uspa44") == {("rf", "th")}
    assert se.touch_pairs(se.PALM_TOUCH, "th+rf") == set()
