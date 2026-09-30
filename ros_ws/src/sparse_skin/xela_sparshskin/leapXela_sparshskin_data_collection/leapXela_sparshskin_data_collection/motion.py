import json
from dataclasses import dataclass
from typing import Any, Iterator

import numpy as np

CLOSE_START = 0.0
CLOSE_END = 1.0
SQUEEZE_STEP_SECONDS = 0.25
REGRASP_HZ = 0.5
TAP_HZ = 2.0
TAP_DEPTH = 0.4
SHEAR_HZ = 1.0


def load_hand_pose(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def close_hand(hand_config: dict[str, Any], number_of_steps: int = 100) -> Iterator[list[float]]:
    """Yield interpolated hardware-order poses from open to closed."""
    hand_pose = hand_config["leapXela"]["sim"]["hand_pose"]
    open_pose = hand_pose["open"]
    close_pose = hand_pose["closed"]

    for step in range(number_of_steps + 1):
        alpha = step / number_of_steps
        yield [
            open_val + alpha * (close_val - open_val)
            for open_val, close_val in zip(open_pose, close_pose)
        ]

def pregrip_targets(ctrlrange: np.ndarray, pregrip_fraction: float=0) -> np.ndarray:
    low = ctrlrange[:, 0]
    high = ctrlrange[:, 1]
    return low + pregrip_fraction * (high - low)


def squeeze(
    hand_config: dict[str, Any],
    number_of_steps: int = 1000,
    percentage_of_trajectory: float = 0.5,
) -> Iterator[list[float]]:
    """The thumb remain open while other fingers are squeezed.
    percentage_of_trajectory is how far along open→close to go (0.5 = halfway).
    """
    hand_pose = hand_config["leapXela"]["sim"]["hand_pose"]
    open_pose = hand_pose["open"]
    close_pose = hand_pose["closed"]

    close_pose_thumb_excluded = close_pose[:-4] + open_pose[-4:]

    for step in range(number_of_steps + 1):
        alpha = (step / number_of_steps) * percentage_of_trajectory
        yield [
            open_val + alpha * (close_val - open_val)
            for open_val, close_val in zip(open_pose, close_pose_thumb_excluded)
        ]


@dataclass(frozen=True)
class GraspProfile:
    pattern: str
    grip_fraction: float
    thumb_grip_fraction: float
    pregrip_fraction: float
    thumb_delay: float
    pulse_hz: float
    pulse_amplitude: float
    shear_amplitude: float
    squeeze_steps: int


def pregrip_targets(ctrlrange: np.ndarray, fraction: float) -> np.ndarray:
    low = ctrlrange[:, 0]
    high = ctrlrange[:, 1]
    return low + fraction * (high - low)


def motion_generator(
    ctrlrange: np.ndarray,
    joint_names: list[str],
    profile: GraspProfile,
    duration: float,
    dt: float = 1.0 / 30.0,
) -> Iterator[np.ndarray]:
    """Yield clipped joint targets from t=0 through duration at intervals of dt."""
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    if duration < 0.0:
        raise ValueError("duration must be non-negative")

    low = ctrlrange[:, 0]
    high = ctrlrange[:, 1]
    span = high - low
    is_thumb = np.asarray([name.startswith("th_") for name in joint_names], dtype=bool)
    is_lateral = np.asarray(
        [name.endswith("_rot") or name.endswith("_axl") for name in joint_names],
        dtype=bool,
    )

    grip = low + np.where(
        is_thumb, profile.thumb_grip_fraction, profile.grip_fraction
    ) * span
    pregrip = pregrip_targets(ctrlrange, profile.pregrip_fraction)
    close_span = CLOSE_END - CLOSE_START

    n_steps = int(np.floor(duration / dt)) + 1
    for step in range(n_steps):
        t = step * dt

        finger_phase = np.clip((t - CLOSE_START) / close_span, 0.0, 1.0)
        thumb_phase = np.clip(
            (t - CLOSE_START - profile.thumb_delay) / close_span, 0.0, 1.0
        )
        phase = np.where(is_thumb, thumb_phase, finger_phase)
        smooth = phase * phase * (3.0 - 2.0 * phase)
        targets = pregrip + smooth * (grip - pregrip)

        if t < CLOSE_END + profile.thumb_delay:
            yield np.clip(targets, low, high)
            continue

        elapsed = t - CLOSE_END - profile.thumb_delay
        if profile.pattern == "hold":
            modulation = 0.0
        elif profile.pattern == "pulse":
            modulation = 0.5 * profile.pulse_amplitude * (
                1.0 - np.cos(2.0 * np.pi * profile.pulse_hz * elapsed)
            )
        elif profile.pattern == "squeeze":
            cycle = profile.squeeze_steps * 2
            index = int(elapsed / SQUEEZE_STEP_SECONDS) % cycle
            level = index if index < profile.squeeze_steps else cycle - index - 1
            modulation = profile.pulse_amplitude * level / max(
                profile.squeeze_steps - 1, 1
            )
        elif profile.pattern == "regrasp":
            release = 0.5 * (1.0 - np.cos(2.0 * np.pi * REGRASP_HZ * elapsed))
            yield np.clip(targets + release * (pregrip - targets), low, high)
            continue
        elif profile.pattern == "tap":
            release = 0.5 * (1.0 - np.cos(2.0 * np.pi * TAP_HZ * elapsed))
            yield np.clip(
                targets + TAP_DEPTH * release * (pregrip - targets), low, high
            )
            continue
        elif profile.pattern == "shear":
            lateral = profile.shear_amplitude * np.sin(
                2.0 * np.pi * SHEAR_HZ * elapsed
            )
            yield np.clip(
                targets + np.where(is_lateral, lateral * span, 0.0), low, high
            )
            continue
        else:
            raise ValueError(f"Unknown grasp pattern '{profile.pattern}'")

        yield np.clip(targets + np.where(is_thumb, 0.0, modulation * span), low, high)
