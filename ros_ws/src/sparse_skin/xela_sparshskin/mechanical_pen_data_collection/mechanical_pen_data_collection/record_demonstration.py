#!/usr/bin/env python3
"""Record per-finger LEAP hand demonstrations from ``/leap_state`` and group them by pen box.

Create tab: one live plot per finger, each with its own Record and Play controls. A finger's
Record saves a take of that finger only, named after the text box next to it (a timestamped
default is filled in). Takes (the full hand
is stored alongside for reference) go to ``<demo_dir>/fingers/<finger>/<name>.npz``. The camera
feed of the take is written to ``<demo_dir>/camera/<name>.mp4``; every take stores its path as
``video`` and the frame times as ``video_t`` (same time axis as ``t``). The SAM 3 mask and pen
box from ``bounding_box_sam`` (``sam_prefix``) are drawn on a frame only when their stamp is
that frame's stamp. Only the frame with the highest detection probability is shown; the rest
are ignored. They are stored as ``sam_t`` / ``sam_mask`` / ``sam_boxes``. Index, Middle and
Ring takes inherit the pen box of the Thumb take selected when they are recorded: it is stored
as ``pen_box`` (4, 2) with that take's path as ``pen_box_source`` and is used as their pen box
(Pose switches, playback) instead of their own SAM detection. If a Pose switch is on when
Record is pressed, the new take (any finger) inherits the box that switch shows instead.
The sim-frame joints
from ``sim_topic`` (``convert_hardware_to_sim``) are stored as ``sim_t`` / ``sim_hand_q`` /
``sim_hand_joint_names``; the raw Xela readings on ``xela_topic`` as ``xela_t`` / ``xela``
(L, T, 3) with the live view's baseline at recording time as ``xela_baseline``. The plots only
show ``joint_topic``. Play sends the take chosen in
the dropdown next to it to the hand on ``cmd_topic``, starting from the play bar position.
The Index, Middle and Ring fingers have a Reverse button: with it on, Play runs the take from
the play bar position back to its start (from its end when the bar is at the start), as plain
position replay.
While a finger is playing, the other fingers can still be moved by hand. Each finger's Pose
switch draws that finger's selected recording's pen box on the live camera, in yellow. The
"Live pen box" button at the top draws the latest SAM pen box on the live camera. Under the camera, the
taxels of the hand are placed live by forward kinematics (``taxel_fk_util``) from ``sim_topic``;
the Xela readings on ``xela_topic`` (change from a baseline, divided by ``counts_per_unit``)
deform and color them and are drawn as force vectors. Zero takes a new baseline. Under each
finger's joint plot, a second plot shows the magnitude of each of its 30 fingertip taxels
(same baseline and scaling; hover to name a taxel). Next to that
live view, a Playback column shows the camera recording and FK taxels (with the recorded Xela
forces) of the take being played, at the position Play has reached (empty while nothing plays).

Edit tab: same layout as the Create tab without Record / Play. Each finger picks one of
its takes; its plots (joints, and fingertip taxel magnitudes when the take has Xela readings)
show the whole take and the play bar (or the plot cursor) scrubs through
it, with the camera recording and the FK taxels / Xela forces of the take following. As in the bag viewer,
an event from ``events_file`` (default: installed ``events.json``) is added at the play bar
position; events are bookmarked on the play bar and the plot, listed next to the plot (click
to seek, Edit / Delete) and saved in the take as ``events`` (JSON list of t, name, type, added,
end). Events with ``"length": "duration"`` are marked with two clicks (start, then end) and
their span is shaded on the play bar and the plot; ``end`` is null for instant events.
Once a take has an ``episode_start`` and a later ``terminal`` event, its Play button (left of
Add event) sends the take from the first to the second to the hand, as the Create tab's Play
does (it shares the Create tab's command thread). A Live column (camera and FK taxels) sits right
of the take's recording, and each finger's Pose switch draws its take's pen box on the live
camera, in yellow. Adding ``reverse_demonstration`` (one click; it needs ``episode_start``
and a later ``terminal``) marks that span and swaps the times of the two events, so Play then
runs the take backwards from ``episode_start`` to ``terminal``; deleting it swaps them back.
A reversed take is shown mirrored (play bar, plots, events and times read ``duration - t``),
so its Play runs left to right; the events are still stored in the take's own time.
A ``maintain_touch`` region (two clicks) makes Play hold the finger in contact over it: the take
waits while the fingertip moves along a press axis until it touches, then plays on while the
fingertip force is held at the Settings tab's Maintain touch hold force (a region can set its
own; see ``maintain_touch``); if it reaches past ``terminal``
(before it in a reversed take), ``terminal`` is moved to its edge.
A ``click_press`` region (Thumb, two clicks) makes Play replace the take over it with a
Cartesian press of the fingertip (``click_press``): a guarded move along the way the fingertip
moved while loading in the take until contact, a fingertip force ramp until the pen clicks, a
retract, then the take continues from the region's end. Force replay is off over the
region. Its values are the Settings tab's Click press section (a region's ``params`` can
override them).
A ``change_click_setting`` event (Thumb) opens the joints of force replay's press direction
for the contact phase at (or after) it, prefilled with the computed one; the values entered
(``params["joints"]``) replace that phase's direction, normalised, in force replay on both
tabs, e.g. to keep a joint from sliding the thumb over the pen. The same panel holds that
phase's force replay values (``params["force"]``: on/off, force gain, max press offset, click
push rate, max hold); phases without the event use the defaults (``ForceReplaySettings``).
In that panel a light shows the
click detector (``click_topic``, Int32 1 while a click is heard) live, and Search
(``click_search``) presses the finger from just before the contact along direction after
direction, widening around the current values, until a click is heard; those values are left in
the sliders for OK to save.
Events with an ``applied_to`` list or code (finger codes such as ``"IF"``) are offered only to
those fingers.
While a finger plays, its plot shows the hand's measured joints (``leap_state``) dashed over
the take (solid), at the take time each was measured.
Every Play on the Edit tab is recorded (``playback_recording``) and saved, once it stops, as
``<demo_dir>/playbacks/<finger>/<take>_<n>.npz`` (n = 1, 2, ...): the commands sent, the measured
joint positions, velocities and efforts, the raw Xela readings and the clicks heard. The Plays
dropdown under the play bar lists the take's recordings, newest first; Replay sends the picked
one's commands to the hand again (plain position replay, no force replay or click press). That
is recorded too, as the next index, with ``replay_of`` in its ``meta``.

Compose tab: a dropdown lists the pen bounding boxes of the takes edited on the Edit tab (those
with an ``episode_start`` and its ``terminal``); a box is a Thumb take's own one, which the Index,
Middle and Ring takes recorded with it inherit. Picking one lists, for every finger, the edited
takes with exactly that box, with their joints plotted (all faint, the selected one in color, its
events marked and its episode shaded) and the selected take's first camera frame shown with the
box. Test in sim plays the episode of every finger's selected take at once, as the Edit tab's
Play runs it (from ``episode_start`` to ``terminal``, backwards when reversed; fingers without a
take hold the first take's pose at its ``episode_start``): Index, Middle and Ring together, then
the Thumb once they are all done. It goes to the MuJoCo sim (``mujoco_sim_node``)
on ``sim_cmd_topic``, converted to sim joints as ``convert_hardware_to_sim`` does. It is plain
position replay: ``maintain_touch``, ``click_press`` and force replay need the real hand. The
finger pairs the sim reports touching on ``finger_contact_topic`` are shown live and, once it
stops, listed with the time they first touched. Play on hand plays the same takes on the hand in
the same order (Index, Middle and Ring together, then the Thumb once they have all stopped), each
through its Edit tab Play (the take is selected in the Edit tab's panel), so ``maintain_touch``,
``click_press``, force replay and the playback recording work as there. With a Thumb take after
them, Index, Middle and Ring keep contact until the Thumb is done: the last ``maintain_touch``
region of each (in playback order) is stretched to its ``terminal``, where the finger stays held
in contact instead of stopping; they are let go (and their Plays end) once the Thumb finishes.
Every Play on hand is recorded as one whole-hand ``PlaybackRecording``,
``<demo_dir>/compose_playbacks/<box>_<n>.npz`` (``<box>``: the Thumb take the box belongs to):
the commands sent, ``leap_state`` joint positions, velocities and efforts, the raw Xela readings
(with the live baseline) and the clicks, from Play to the end; ``meta`` holds the takes, how it
ended and the timeline of each finger (start, holding at terminal, finished / stopped). The
Play on hand first moves the fingers to where their episodes start (the sampled random start,
or ``episode_start``), one after another (``START_ORDER``), gently (``move_to_pose_take``: an
S-curve no faster than ``START_MOVE_SPEED``), each then held stiff there; the At start lights
show it (yellow moving, green at its start). The Contact lights next to them turn green while
a finger is in contact with the pen (Index / Middle / Ring: its ``maintain_touch`` holding;
Thumb: its ``click_press`` pressing). Once all are there, the recording starts (data,
camera as ``<box>_<n>.mp4`` and the microphone on ``audio_topic`` as ``<box>_<n>.wav``) and the
episodes play as above.
Hand plays panel (right) lists the box's recordings, newest first; clicking one shows its
details and the Delete recording, Play on sim and Play on hand buttons. The two Play buttons
send the recording's commands again at their recorded times: to the sim as Test in sim does, or
to the hand as plain position replay of the fingers it played (as the Edit tab's Replay).
During Play on hand, the slip lights (Index, Middle, Ring) show each finger's contact: grey not
in contact, green in contact (its ``maintain_touch`` holding), red for ``SLIP_LIGHT_S`` after a
slip (``slip_detection``: the contact spot moving on the pad, or the fingertip force falling
away), with a count of the slips;
the slips are saved in the recording's ``meta["slips"]``. With Avoid slip on, Index, Middle and
Ring press harder so the Thumb cannot push the pen out (``AvoidSlipSettings``, next to the
switch, saved with Save settings): the fingers holding contact get ``before_thumb`` more hold
force when the Thumb starts, and every slip of a finger adds ``per_slip``, up to ``max_extra``
(``TouchPress.extra_force``; needs Zero, as the force is held from the live Xela).
A take's ``random_episode_start`` regions (added on the Edit tab) mark where its episode may
start: every Test in sim and Play on hand starts it at a time drawn uniformly from them (the
part between ``episode_start`` and ``terminal``) instead of at ``episode_start``; the Edit tab's
own Play still starts at ``episode_start``.
Under the selected take's first frame, a Live view shows the camera with the selected bounding
box drawn on it, in yellow, to line the pen up with it before playing.

Demonstration tab: plays back the Compose tab's Play on hand recordings without sending
anything to the hand. Under the list, Success and Fail mark the picked recording (pressing the
lit one again clears it), saved next to it as ``<box>_<n>.label.json`` as ``label_playbacks``
does; Delete removes it with its camera, audio and label files. Pick a recording and press Play (or drag the play bar): plots
of each finger's joint positions, velocities and efforts (``leap_state``) with the run's
timeline and slips marked, each finger's fingertip taxel magnitudes (recorded Xela, from the
run's baseline), its camera recording with the bounding box drawn on it, and the FK
taxels with the recorded Xela readings follow the play bar. The microphone recording is plotted
under the joints and, while playing, heard on the Audio output picked (remembered between runs;
Test plays a beep). With Stream to sim (on by default)
the recorded joint positions are also sent to the MuJoCo sim on ``sim_cmd_topic``, converted to
sim joints as ``convert_hardware_to_sim`` does. Play on hand saves the camera next to its
recording, as ``<box>_<n>.mp4``.

Settings tab: the folder takes are saved into (``demo_dir``, can be changed while running), the
command rate, playback ramp and free-finger deadband used while fingers are
playing (applied immediately), and the compliant gains / deadband of ``hand_node``
(leaphand_node), read and set through its ROS parameters. Fingers that are playing
use the hand node's stiffer playback gains (``stiff_kP`` / ``stiff_kD`` / ``stiff_curr_lim``,
set through ``stiff_joints``) so they track the take; the other fingers stay compliant.
Force replay (``force_replay``, set per contact in ``change_click_setting``) presses past the
take's joints during its contact phases until the live fingertip force matches the recorded one,
holding the take until the finger touches and until it clicks. Commands are sent from their own
thread at the command rate.
Save settings writes these (the folder, the playback / maintain touch values and the hand's
gains) to ``<ws>/settings/mechanical_pen_data_collection/record_demonstration.json``; they are
loaded at the next start, and the saved hand gains are applied once the hand node is found. A
``demo_dir`` given as a parameter overrides the saved folder.

Usage:
  ros2 run mechanical_pen_data_collection record_demonstration \
      [--ros-args -p joint_topic:=leap_state -p sim_topic:=leap_state_sim -p cmd_topic:=cmd_xela \
                  -p sim_cmd_topic:=sim_command -p finger_contact_topic:=finger_contacts \
                  -p audio_topic:=/audio \
                  -p image_topic:=/camera/color/image_raw -p demo_dir:=PATH \
                  -p hand_node:=leaphand_node -p xela_topic:=/xServTopic \
                  -p click_topic:=/pen_click \
                  -p sam_prefix:=/bounding_box_sam \
                  -p counts_per_unit:=1000.0 -p events_file:=PATH]
"""

from __future__ import annotations

import functools
import json
import os
import re
import signal
import sys
import threading
import wave
import time
from collections import deque
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Callable

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets  # imported before pyqtgraph so it binds to PyQt5
import pyqtgraph as pg

# pip opencv-python ships its own Qt and points QT_QPA_PLATFORM_PLUGIN_PATH at it,
# which makes PyQt5 fail to load the xcb plugin. PyQt5 must be imported first.
import cv2  # noqa: E402

os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
os.environ.pop("QT_QPA_FONTDIR", None)
import rclpy
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import GetParameters, SetParametersAtomically
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Image, JointState
from std_msgs.msg import Float32MultiArray, Int32, String

from mechanical_pen_data_collection.bag_data import (
    EVENT_TIME_RESOLUTION,
    default_bag_dir,
    image_to_array,
)
from mechanical_pen_data_collection.bag_viewer import (
    SLIDER_STEPS_PER_SEC,
    UNKNOWN_EVENT_COLOR,
    BookmarkSlider,
    EditEventDialog,
    default_events_file,
    index_at,
    load_event_definitions,
)
from mechanical_pen_data_collection.click_press import (
    PRESS as CLICK_PRESSING,
    ClickPress,
    ClickPressSettings,
    FingerKinematics,
    HandKinematics,
    PressRegion,
    press_geometry,
)
from mechanical_pen_data_collection.click_search import (
    ClickProbe,
    candidate_directions,
    slider_values,
)
from mechanical_pen_data_collection.force_replay import (
    ContactPhase,
    ForceReplaySettings,
    ForceTracker,
    contact_phases,
    sample as sample_joints,
)
from mechanical_pen_data_collection.playback_recording import (
    FAILURE,
    SUCCESS,
    PlaybackRecording,
    delete_playback,
    list_playbacks,
    load_label,
    next_playback_path,
    set_manual_label,
)
from mechanical_pen_data_collection.slip_detection import SPOT_SHIFT, SlipDetector, SlipSettings
from mechanical_pen_data_collection.maintain_touch import (
    HOLD as TOUCH_HOLD,
    MaintainTouchSettings,
    TouchHold,
    TouchPress,
    TouchPressRegion,
    touch_axis,
    touch_regions,
)

PACKAGE_NAME = "mechanical_pen_data_collection"
FINGERS = (("th", "Thumb"), ("if", "Index"), ("mf", "Middle"), ("rf", "Ring"))
FINGER_LABEL = dict(FINGERS)
# Same order as leaphand_node (xela_description/joint_config.json hardware map).
DEFAULT_JOINT_NAMES = [
    f"{finger}_{joint}"
    for finger, joints in (
        ("th", ("cmc", "axl", "mcp", "ipl")),
        ("if", ("mcp", "pip", "rot", "dip")),
        ("mf", ("mcp", "pip", "rot", "dip")),
        ("rf", ("mcp", "pip", "rot", "dip")),
    )
    for joint in joints
]
NUM_JOINTS = len(DEFAULT_JOINT_NAMES)
JOINT_COLORS = ("#e6194b", "#3cb44b", "#4363d8", "#f58231")
LIVE_WINDOW_S = 10.0
HISTORY_LEN = 2000
REFRESH_MS = 50
# Container frame rate only; real frame times are saved in ``video_t``.
VIDEO_FPS = 30.0
# Defaults of the Settings tab (``HoldSettings``).
COMMAND_RATE_HZ = 30.0
# Playback first moves the finger from where it is to the start of the take over this time.
PLAY_RAMP_S = 0.5
# Free fingers follow the hand once pushed further than this (rad); matches leaphand_node's
# ``compliant_deadband`` so gravity sag does not drag them down.
COMPLIANT_DEADBAND = 0.05
PLAY_BAR_STEPS = 1000
# Fingers whose Create tab panel has a Reverse button (play the take from its end to its start).
REVERSE_FINGERS = ("if", "mf", "rf")
# Fingers whose new takes inherit the pen box of the selected Thumb take.
PEN_BOX_FROM_THUMB = ("if", "mf", "rf")
# leaphand_node runs these hardware motors (indices in leap_state's joint order) at 75 % of kP
# and kD; click press weighs the press direction by it.
REDUCED_KP_MOTORS = (0, 4, 8)
REDUCED_KP_SCALE = 0.75
# Play on hand moves the fingers to their episode start one after another, in this order, with
# joints no faster than START_MOVE_SPEED (rad/s, the S-curve's peak) and over START_MOVE_MIN_S
# at least.
START_ORDER = ("if", "mf", "rf", "th")
START_MOVE_SPEED = 0.3
START_MOVE_MIN_S = 1.5
START_COLORS = {"off": "#616161", "moving": "#fdd835", "at_start": "#43a047"}
CONTACT_COLORS = {"off": "#616161", "contact": "#43a047"}
# Fingers whose slips the Compose tab's lights show during Play on hand.
SLIP_FINGERS = ("if", "mf", "rf")
# A slip light stays red this long (s) after a slip.
SLIP_LIGHT_S = 1.0
SLIP_LIGHT_STYLE = (
    "background-color: {}; border: 1px solid #333; border-radius: 9px; "
    "min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px;"
)
SLIP_COLORS = {"off": "#616161", "contact": "#43a047", "slip": "#ff1744"}
# Key of the Compose tab's Play on hand among the node's playback recordings.
COMPOSE_PLAY_KEY = "compose"
# Edit tab Plays shorter than this (s) are not saved as playback recordings.
MIN_PLAY_RECORDING_S = 0.5
# Events that bound the part of a take the Edit tab's Play sends to the hand.
EPISODE_START_EVENT = "episode_start"
EPISODE_END_EVENT = "terminal"
# Duration event from ``episode_start`` to ``terminal``: adding it swaps their times, so Play
# runs the take backwards from ``episode_start`` to ``terminal``.
REVERSE_EVENT = "reverse_demonstration"
# Duration event: the Edit tab's Play holds the finger in contact over its region
# (``maintain_touch``); adding one past ``terminal`` moves ``terminal`` to its end.
MAINTAIN_TOUCH_EVENT = "maintain_touch"
# Duration event: the span the Compose tab draws the episode's start from (instead of
# ``episode_start``) for each Test in sim / Play on hand.
RANDOM_START_EVENT = "random_episode_start"
# Duration event (Thumb): Play replaces the take over its region with a Cartesian force-ramp press
# until the pen clicks (``click_press``).
CLICK_PRESS_EVENT = "click_press"
# Instant event: its ``params["joints"]`` replace force replay's press direction (per joint) for
# the contact phase at or after it, and its ``params["force"]`` that phase's force replay values.
CLICK_SETTING_EVENT = "change_click_setting"
# The click setting search presses from the take's joints this long before the contact starts.
CLICK_SEARCH_LEAD_S = 0.2
# Force replay values of a ``change_click_setting`` event (``params["force"]``, defaults:
# ``ForceReplaySettings``): (name, label, min, max, step, decimals, suffix, tooltip).
CLICK_FORCE_FIELDS = (
    ("force_gain", "Force gain", 0.0, 2.0, 0.01, 3, " rad/(unit·s)",
     "How fast the press offset grows per unit of missing fingertip force"),
    ("force_max_offset", "Max press offset", 0.0, 0.6, 0.01, 2, " rad",
     "Largest press offset past the recorded joints (also the deepest Search press)"),
    ("force_push_rate", "Click push rate", 0.0, 1.0, 0.01, 2, " rad/s",
     "How fast the offset grows while the take is held for the click (also Search's)"),
    ("force_max_wait", "Max hold", 0.0, 20.0, 0.5, 1, " s",
     "Longest the take is held for contact or the click before it continues"),
)
# Xela header stamps further than this from the ROS clock are replaced by the receive time.
XELA_MAX_CLOCK_OFFSET_S = 1.0
# Same header stamp. Far below the 30 Hz camera period, so a detection cannot attach to a neighbor.
SAM_STAMP_TOL_S = 1e-4
# Incomplete SAM image/mask/box sets kept while their partners arrive.
SAM_PART_LIMIT = 8
# The Create tab's live pen box is hidden once the latest SAM result is older than this.
LIVE_SAM_MAX_AGE_S = 1.0
# Channel values draw_boxes writes into the RGB frame (bounding_box_sam.boxes).
SAM_BEST_COLOR = (46, 204, 113)
SAM_OTHER_COLOR = (241, 196, 15)
SAM_LABEL_COLOR = (255, 255, 255)
# Title of mujoco_sim_node's viewer window, brought to the front by Test in sim.
SIM_WINDOW_TITLE = "MuJoCo: LEAP Xela"
# How long (s) after start the GUI looks for that window to bring it to the front.
SIM_WINDOW_WAIT_S = 30
# Median recorded pen box drawn on the live camera.
RECORDED_POSE_COLOR = (255, 255, 0)
# Fingertip patch of each finger in ``taxel_fk_util.XELA_FLATTEN_ORDER``.
TIP_LINKS = {
    "th": "3aftc_palm_link",
    "if": "0aftc_palm_link",
    "mf": "1aftc_palm_link",
    "rf": "2aftc_palm_link",
}
# leaphand_node parameters shown in the Settings tab:
# (name, label, max, step, decimals, suffix, tooltip).
HAND_PARAMS = (
    ("compliant_kP", "Position kP", 2000.0, 5.0, 0, "",
     "Position P gain of the motors (motors 0, 4 and 8 use 75%). "
     "Higher = held fingers resist pushing more"),
    ("compliant_kD", "Position kD", 2000.0, 5.0, 0, "", "Position D gain (damping) of the motors"),
    ("compliant_curr_lim", "Current limit", 1000.0, 10.0, 0, "",
     "Goal current of the motors (Dynamixel units). Caps how hard a held finger pushes back"),
    ("compliant_deadband", "Deadband", 0.5, 0.005, 3, " rad",
     "leaphand_node moves a joint's goal to where it is once it is pushed further than this "
     "(rad), so fingers stay where they are posed. Paused while fingers are held or playing "
     "(this GUI's free-finger deadband applies then)"),
    ("stiff_kP", "Playback kP", 2000.0, 5.0, 0, "",
     "Position P gain of the fingers that are playing or held (the others keep the compliant "
     "gains). Higher = they track the take more closely"),
    ("stiff_kD", "Playback kD", 2000.0, 5.0, 0, "",
     "Position D gain (damping) of the fingers that are playing or held"),
    ("stiff_curr_lim", "Playback current limit", 1000.0, 10.0, 0, "",
     "Goal current of the fingers that are playing or held (Dynamixel units). Raise it if a "
     "played finger cannot push hard enough, e.g. to click the pen"),
)

pg.setConfigOptions(antialias=True)


def settings_file() -> str:
    """``<colcon workspace>/settings/<package>/record_demonstration.json``."""
    try:
        ws = os.path.dirname(default_bag_dir())
    except Exception:  # package not installed (e.g. run from source)
        ws = os.path.expanduser("~")
    return os.path.join(ws, "settings", PACKAGE_NAME, "record_demonstration.json")


def load_saved_settings(path: str) -> dict:
    """Settings saved by the Settings tab ({} if there are none)."""
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def apply_saved_hold_settings(settings, saved: dict) -> None:
    """Copies the saved values of a settings dataclass (``HoldSettings``,
    ``MaintainTouchSettings``) into ``settings``."""
    for name, default in asdict(type(settings)()).items():
        if name in saved:
            setattr(settings, name, type(default)(saved[name]))


def default_demo_dir() -> str:
    try:
        return os.path.join(os.path.dirname(default_bag_dir()), "demonstrations")
    except Exception:  # package not installed (e.g. run from source)
        return os.path.expanduser("~/demonstrations")


def finger_indices(joint_names: list[str], finger: str) -> list[int]:
    names = joint_names if len(joint_names) == NUM_JOINTS else DEFAULT_JOINT_NAMES
    return [i for i, name in enumerate(names) if name.startswith(f"{finger}_")]


def take_columns(joint_names: list[str], take: FingerTake) -> list[int]:
    """Columns of ``joint_names`` that the joints of ``take`` map to."""
    if all(name in joint_names for name in take.joint_names):
        return [joint_names.index(name) for name in take.joint_names]
    return finger_indices(joint_names, take.finger)


def fingertip_fk_slice(finger: str) -> slice:
    """Taxels of ``finger``'s fingertip in ``taxel_fk_util`` FK order (same order as
    ``fingertip_taxel_ids``)."""
    from mechanical_pen_data_collection import taxel_fk_util as fk

    links = list(fk.XELA_FLATTEN_ORDER)
    starts = np.cumsum([0, *fk.XELA_FLATTEN_ORDER.values()])
    k = links.index(TIP_LINKS[finger])
    return slice(int(starts[k]), int(starts[k + 1]))


@functools.cache
def fingertip_taxel_ids() -> dict[str, np.ndarray] | None:
    """Hardware Xela ids of each finger's fingertip taxels (None if taxel_fk_util cannot load)."""
    try:
        from mechanical_pen_data_collection import taxel_fk_util as fk
    except Exception:
        return None
    return {finger: fk.TAXEL_IDS_IN_FK_ORDER[fingertip_fk_slice(finger)] for finger in TIP_LINKS}


def taxel_magnitudes(
    readings: np.ndarray, baseline: np.ndarray, ids: np.ndarray, counts_per_unit: float
) -> np.ndarray:
    """(N, len(ids)) |reading - baseline| / counts_per_unit of taxels ``ids`` from (N, T, 3)."""
    return np.linalg.norm((readings[:, ids] - baseline[ids]) / counts_per_unit, axis=-1)


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip()).strip("._") or "take"


@dataclass
class AvoidSlipSettings:
    """Compose tab Avoid slip: more hold force for Index / Middle / Ring during Play on hand."""

    enabled: bool = False
    before_thumb: float = 2.0  # force units added to the fingers holding when the Thumb starts
    per_slip: float = 1.0  # force units added to a finger per slip
    max_extra: float = 6.0  # largest extra force of a finger


@dataclass
class HoldSettings:
    """How held / playing fingers are commanded and how the free fingers comply meanwhile."""

    command_rate: float = COMMAND_RATE_HZ  # Hz, rate of commands on cmd_topic
    ramp_s: float = PLAY_RAMP_S
    deadband: float = COMPLIANT_DEADBAND  # rad


def parameter_value(value: ParameterValue):
    """Python value of a ``ParameterValue`` (None if the parameter is not set)."""
    return {
        ParameterType.PARAMETER_BOOL: value.bool_value,
        ParameterType.PARAMETER_INTEGER: value.integer_value,
        ParameterType.PARAMETER_DOUBLE: value.double_value,
        ParameterType.PARAMETER_STRING: value.string_value,
    }.get(value.type)


@dataclass
class TakeEvent:
    t: float  # seconds from the start of the take
    name: str  # key of events.json
    type: str = ""
    added: float = 0.0  # wall-clock time it was labelled
    end: float | None = None  # end of an event with ``"length": "duration"`` (None if instant)
    # Event-specific values, e.g. a ``maintain_touch`` region's hold_force / contact_force.
    params: dict = field(default_factory=dict)

    def span_text(self) -> str:
        return f"{self.t:.2f} s" if self.end is None else f"{self.t:.2f}-{self.end:.2f} s"


@dataclass
class FingerTake:
    finger: str
    path: str
    t: np.ndarray  # (N,) seconds from the start of the take
    q: np.ndarray  # (N, 4) joints of ``finger``
    joint_names: list[str]  # names of the 4 columns of ``q``
    hand_q: np.ndarray  # (N, 16) whole hand during the take
    hand_joint_names: list[str]
    video: str = ""  # camera recording of the take ("" if no frames were received)
    video_t: np.ndarray = field(default_factory=lambda: np.empty(0))  # (M,) frame times
    sim_t: np.ndarray = field(default_factory=lambda: np.empty(0))  # (K,) sim_topic times
    sim_hand_q: np.ndarray = field(default_factory=lambda: np.empty((0, NUM_JOINTS)))  # (K, 16)
    sim_hand_joint_names: list[str] = field(default_factory=list)
    xela_t: np.ndarray = field(default_factory=lambda: np.empty(0))  # (L,) xela_topic times
    xela: np.ndarray = field(default_factory=lambda: np.empty((0, 0, 3)))  # (L, T, 3) raw x, y, z
    # (T, 3) no-contact reading the forces are measured from (live view's at recording time)
    xela_baseline: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    events: list[TakeEvent] = field(default_factory=list)  # in the order they were added
    sam_t: np.ndarray = field(default_factory=lambda: np.empty(0))  # SAM frame stamps, on ``t``
    sam_mask: np.ndarray = field(default_factory=lambda: np.empty((0, 0, 0), np.uint8))
    sam_boxes: list = field(default_factory=list)  # detections JSON for each ``sam_t``
    # (4, 2) pen box inherited from another take (the Thumb's), used instead of the SAM one.
    pen_box: np.ndarray = field(default_factory=lambda: np.empty((0, 2), np.float32))
    pen_box_source: str = ""  # path of the take ``pen_box`` came from

    @property
    def name(self) -> str:
        return os.path.splitext(os.path.basename(self.path))[0]

    @property
    def duration(self) -> float:
        return float(self.t[-1]) if len(self.t) else 0.0

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        np.savez_compressed(
            self.path,
            finger=self.finger,
            t=self.t,
            q=self.q,
            joint_names=np.array(self.joint_names),
            hand_q=self.hand_q,
            hand_joint_names=np.array(self.hand_joint_names),
            video=self.video,
            video_t=self.video_t,
            sim_t=self.sim_t,
            sim_hand_q=self.sim_hand_q,
            sim_hand_joint_names=np.array(self.sim_hand_joint_names),
            xela_t=self.xela_t,
            xela=self.xela,
            xela_baseline=self.xela_baseline,
            events=json.dumps([asdict(e) for e in self.events]),
            sam_t=self.sam_t,
            sam_mask=self.sam_mask,
            sam_boxes=json.dumps(self.sam_boxes),
            pen_box=self.pen_box,
            pen_box_source=self.pen_box_source,
        )

    def event_at(self, t: float) -> TakeEvent | None:
        """The event at ``t`` (within ``EVENT_TIME_RESOLUTION``), if there is one."""
        return next((e for e in self.events if abs(e.t - t) < EVENT_TIME_RESOLUTION), None)

    @classmethod
    def load(cls, path: str) -> FingerTake:
        with np.load(path, allow_pickle=False) as data:
            return cls(
                finger=str(data["finger"]),
                path=path,
                t=data["t"],
                q=data["q"],
                joint_names=[str(n) for n in data["joint_names"]],
                hand_q=data["hand_q"],
                hand_joint_names=[str(n) for n in data["hand_joint_names"]],
                video=str(data["video"]) if "video" in data.files else "",
                video_t=data["video_t"] if "video_t" in data.files else np.empty(0),
                sim_t=data["sim_t"] if "sim_t" in data.files else np.empty(0),
                sim_hand_q=(
                    data["sim_hand_q"] if "sim_hand_q" in data.files else np.empty((0, NUM_JOINTS))
                ),
                sim_hand_joint_names=(
                    [str(n) for n in data["sim_hand_joint_names"]]
                    if "sim_hand_joint_names" in data.files
                    else []
                ),
                xela_t=data["xela_t"] if "xela_t" in data.files else np.empty(0),
                xela=data["xela"] if "xela" in data.files else np.empty((0, 0, 3)),
                xela_baseline=(
                    data["xela_baseline"] if "xela_baseline" in data.files else np.empty((0, 3))
                ),
                events=(
                    [TakeEvent(**e) for e in json.loads(str(data["events"]))]
                    if "events" in data.files
                    else []
                ),
                sam_t=data["sam_t"] if "sam_t" in data.files else np.empty(0),
                sam_mask=(
                    data["sam_mask"] if "sam_mask" in data.files else np.empty((0, 0, 0), np.uint8)
                ),
                sam_boxes=(
                    json.loads(str(data["sam_boxes"])) if "sam_boxes" in data.files else []
                ),
                pen_box=(
                    data["pen_box"] if "pen_box" in data.files
                    else np.empty((0, 2), np.float32)
                ),
                pen_box_source=(
                    str(data["pen_box_source"]) if "pen_box_source" in data.files else ""
                ),
            )


def take_is_reversed(take: FingerTake) -> bool:
    """The take has a ``reverse_demonstration`` event (its episode events are swapped)."""
    return any(e.name == REVERSE_EVENT for e in take.events)


def take_episode_events(take: FingerTake) -> tuple[TakeEvent | None, TakeEvent | None]:
    """First ``episode_start`` and the ``terminal`` that goes with it: the first one after it,
    or the last one before it once the take is reversed (None if missing)."""
    starts = [e for e in take.events if e.name == EPISODE_START_EVENT]
    if not starts:
        return None, None
    start = min(starts, key=lambda e: e.t)
    if take_is_reversed(take):
        ends = [e for e in take.events if e.name == EPISODE_END_EVENT and e.t < start.t]
        return start, max(ends, key=lambda e: e.t) if ends else None
    ends = [e for e in take.events if e.name == EPISODE_END_EVENT and e.t > start.t]
    return start, min(ends, key=lambda e: e.t) if ends else None


def take_episode_span(take: FingerTake) -> tuple[float, float] | None:
    """(``episode_start``, ``terminal``) take times the Edit tab's Play runs between (backwards
    when the take is reversed); None if the take does not have both."""
    start, end = take_episode_events(take)
    return (start.t, end.t) if start is not None and end is not None else None


def random_start_regions(take: FingerTake) -> list[tuple[float, float]]:
    """The parts of the take's ``random_episode_start`` regions inside its episode (between
    ``episode_start`` and ``terminal``), as (low, high) take times."""
    span = take_episode_span(take)
    if span is None:
        return []
    lo, hi = min(span), max(span)
    parts = [
        (max(min(e.t, e.end), lo), min(max(e.t, e.end), hi))
        for e in take.events if e.name == RANDOM_START_EVENT and e.end is not None
    ]
    return [(a, b) for a, b in parts if b > a]


def sample_episode_start(take: FingerTake, rng: np.random.Generator) -> float | None:
    """A take time drawn uniformly from ``random_start_regions`` (None without any)."""
    parts = random_start_regions(take)
    if not parts:
        return None
    lengths = np.array([b - a for a, b in parts])
    a, b = parts[int(rng.choice(len(parts), p=lengths / lengths.sum()))]
    return float(rng.uniform(a, b))


class TakeStore:
    """Takes on disk under ``<demo_dir>/fingers/<finger>/``, cached by mtime."""

    def __init__(self, demo_dir: str) -> None:
        self.demo_dir = demo_dir
        self._cache: dict[str, tuple[float, FingerTake]] = {}

    def finger_dir(self, finger: str) -> str:
        return os.path.join(self.demo_dir, "fingers", finger)

    def video_path(self, name: str) -> str:
        return os.path.join(self.demo_dir, "camera", f"{name}.mp4")

    def take_path(self, finger: str, name: str) -> str:
        return os.path.join(self.finger_dir(finger), f"{name}.npz")

    def new_take_name(self, prefix: str = "take") -> str:
        """A timestamped name not yet used by any finger take or camera recording."""
        return self.unique_take_name(datetime.now().strftime(f"{prefix}_%Y%m%d_%H%M%S"))

    def numbered_take_name(self, prefix: str) -> str:
        """``prefix_n`` with the lowest ``n`` >= 1 not yet used by any finger take or camera
        recording."""
        n = 1
        while self.unique_take_name(f"{prefix}_{n}") != f"{prefix}_{n}":
            n += 1
        return f"{prefix}_{n}"

    def unique_take_name(self, base: str) -> str:
        """``base``, suffixed if needed so no finger take or camera recording uses it yet."""
        name, n = base, 1
        while os.path.exists(self.video_path(name)) or any(
            os.path.exists(self.take_path(finger, name)) for finger, _ in FINGERS
        ):
            name = f"{base}_{n}"
            n += 1
        return name

    @property
    def compose_playback_dir(self) -> str:
        return os.path.join(self.demo_dir, "compose_playbacks")

    def playback_dir(self, finger: str) -> str:
        return os.path.join(self.demo_dir, "playbacks", finger)

    def list_playbacks(self, finger: str, take_name: str | None = None) -> list[str]:
        """Recorded Plays of ``finger`` (of ``take_name`` only if given), newest first."""
        return list_playbacks(self.playback_dir(finger), take_name)

    def new_playback_path(self, finger: str, take_name: str) -> str:
        """``<demo_dir>/playbacks/<finger>/<take_name>_<n>.npz``, ``n`` the next free index."""
        return next_playback_path(self.playback_dir(finger), take_name)

    def list(self, finger: str) -> list[str]:
        """Take paths for ``finger``, newest first."""
        directory = self.finger_dir(finger)
        if not os.path.isdir(directory):
            return []
        paths = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".npz")]
        return sorted(paths, key=os.path.getmtime, reverse=True)

    def load(self, path: str) -> FingerTake:
        mtime = os.path.getmtime(path)
        cached = self._cache.get(path)
        if cached is None or cached[0] != mtime:
            cached = (mtime, FingerTake.load(path))
            self._cache[path] = cached
        return cached[1]

    def delete(self, path: str) -> None:
        """Removes the take at ``path``, and its camera recording unless another finger's take
        of the same recording still uses it."""
        try:
            video = self.load(path).video
        except Exception:
            video = ""
        os.remove(path)
        self._cache.pop(path, None)
        name = os.path.splitext(os.path.basename(path))[0]
        shared = any(
            os.path.exists(self.take_path(finger, name)) for finger, _ in FINGERS
        )
        if video and not shared and os.path.exists(video):
            os.remove(video)


@dataclass
class Recording:
    t: np.ndarray  # (N,) joint times, starting at 0
    q: np.ndarray  # (N, 16)
    video: str  # "" if no camera frames were received
    video_t: np.ndarray  # (M,) frame times on the same axis as ``t``
    sim_t: np.ndarray  # (K,) sim_topic times on the same axis as ``t``
    sim_q: np.ndarray  # (K, 16)
    sim_joint_names: list[str]
    xela_t: np.ndarray  # (L,) xela_topic times on the same axis as ``t``
    xela: np.ndarray  # (L, T, 3) raw Xela readings by hardware id
    sam_t: np.ndarray  # stamps of frames SAM segmented, on the same axis as ``t`` / ``video_t``
    sam_mask: np.ndarray  # (K, H, W) uint8 mask for each ``sam_t``
    sam_boxes: list  # detections for each ``sam_t``


class HardwareToSim:
    """Hardware joints to sim joints, as ``convert_hardware_to_sim`` converts them."""

    def __init__(self) -> None:
        from conversions.hardware_to_sim_conversion import map_hardware_to_sim
        from conversions.sim_to_hardware_conversion import (
            get_joint_names,
            get_joint_ranges,
            load_joint_config,
            remap_joint_commands,
        )

        self._map = map_hardware_to_sim
        self._remap = remap_joint_commands
        config = load_joint_config()
        self.sim_names, _ = get_joint_names(config)
        leap = config["leapXela"]
        self._hw_ranges = get_joint_ranges(self.sim_names, leap["hardware"])
        self._sim_ranges = get_joint_ranges(self.sim_names, leap["sim"])

    def __call__(self, hw_joint_names: list[str], q_hw: np.ndarray) -> list[float]:
        """Sim angles (``sim_names`` order) of hardware joints ``q_hw`` (``hw_joint_names``)."""
        ordered = self._remap(self.sim_names, hw_joint_names, [float(v) for v in q_hw])
        return self._map(ordered, self._sim_ranges, self._hw_ranges)


class LeapStateListener(Node):
    """Buffers ``leap_state``, ``leap_state_sim`` and the camera for the live view and records
    them while asked to."""

    def __init__(self) -> None:
        super().__init__("record_demonstration")
        topic = self.declare_parameter("joint_topic", "leap_state").value
        self.sim_topic = self.declare_parameter("sim_topic", "leap_state_sim").value
        cmd_topic = self.declare_parameter("cmd_topic", "cmd_xela").value
        self.sim_cmd_topic = self.declare_parameter("sim_cmd_topic", "sim_command").value
        self.finger_contact_topic = self.declare_parameter(
            "finger_contact_topic", "finger_contacts"
        ).value
        self.image_topic = self.declare_parameter("image_topic", "/camera/color/image_raw").value
        self.sam_prefix = (
            self.declare_parameter("sam_prefix", "/bounding_box_sam").value.rstrip("/")
        )
        self.xela_topic = self.declare_parameter("xela_topic", "/xServTopic").value
        self.click_topic = self.declare_parameter("click_topic", "/pen_click").value
        # Microphone stream of push_button_pen_click_detection's audio_publisher.
        self.audio_topic = self.declare_parameter("audio_topic", "/audio").value
        self.audio_rate = 48000  # updated from <audio_topic>/info
        self._play_audio: list[tuple[float, np.ndarray]] | None = None  # (received, samples)
        self.counts_per_unit = float(self.declare_parameter("counts_per_unit", 1000.0).value)
        self.events_file = self.declare_parameter("events_file", "").value or default_events_file()
        demo_dir = self.declare_parameter("demo_dir", "").value
        self.demo_dir_given = bool(demo_dir)  # overrides the folder saved in the Settings tab
        self.demo_dir = os.path.expanduser(demo_dir or default_demo_dir())

        self._lock = threading.Lock()
        self._joint_names: list[str] = []
        self._history: deque[tuple[float, np.ndarray]] = deque(maxlen=HISTORY_LEN)
        self._effort: np.ndarray | None = None  # latest leap_state effort (present current)
        # Recordings of Plays in progress (``start_play_recording``), by key: buffers of
        # (stamp, position, velocity, effort), (stamp, xela readings) and click edge stamps.
        self._play_recs: dict[str, dict] = {}
        self._recording = False
        self._rec_t: list[float] = []
        self._rec_q: list[np.ndarray] = []
        self._frame: np.ndarray | None = None  # latest RGB camera frame
        self._frame_seq = 0
        self._display_frame: np.ndarray | None = None  # frame the camera widget shows
        self._display_seq = 0
        self._sam_locked = False  # once a matched SAM frame exists, do not show a newer raw frame
        self._sam_best_score: float | None = None  # highest detection score shown so far
        # Latest complete SAM result (whatever its score), for the live pen box:
        # (sequence number, time.monotonic() received, detections).
        self._sam_live: tuple[int, float, list] = (0, 0.0, [])
        self._sam_parts: dict[float, dict] = {}  # stamp -> image / mask / boxes still arriving
        self._rec_sam_t: list[float] = []
        self._rec_sam_mask: list[np.ndarray] = []
        self._rec_sam_boxes: list[list] = []
        self._video_path = ""
        self._video: cv2.VideoWriter | None = None
        # Camera recording of a Play (Compose tab's Play on hand), independent of the takes'.
        self._play_video: cv2.VideoWriter | None = None
        self._play_video_path = ""
        self._play_video_t: list[float] = []
        self._rec_frame_t: list[float] = []
        self._sim: tuple[int, list[str], np.ndarray | None] = (0, [], None)  # (seq, names, q)
        self._rec_sim_t: list[float] = []
        self._rec_sim_q: list[np.ndarray] = []
        self._xela: tuple[int, np.ndarray | None] = (0, None)  # (seq, (T, 3) raw x, y, z)
        self._rec_xela_t: list[float] = []
        self._rec_xela: list[np.ndarray] = []
        self._xela_history: deque[tuple[float, np.ndarray]] = deque(maxlen=HISTORY_LEN)
        # Sim messages with finger-finger contacts: (time.monotonic(), touching finger pairs).
        self._finger_contacts: deque[tuple[float, list[tuple[str, str]]]] = deque(
            maxlen=HISTORY_LEN
        )
        self._finger_contact_seq = 0
        self._click = False  # latest click_topic value is 1
        self._click_count = 0  # rising edges of click_topic, so short pulses are not missed

        self.create_subscription(JointState, topic, self._on_state, 10)
        self.create_subscription(JointState, self.sim_topic, self._on_sim_state, 10)
        if self.image_topic:
            self.create_subscription(Image, self.image_topic, self._on_image, qos_profile_sensor_data)
        if self.sam_prefix:
            self.create_subscription(
                Image, f"{self.sam_prefix}/image", self._on_sam_image, qos_profile_sensor_data
            )
            self.create_subscription(
                Image, f"{self.sam_prefix}/mask", self._on_sam_mask, qos_profile_sensor_data
            )
            self.create_subscription(String, f"{self.sam_prefix}/boxes", self._on_sam_boxes, 10)
        if self.xela_topic:
            try:
                from xela_server_ros2.msg import SensStream
            except ImportError as e:
                self.get_logger().warn(f"xela_server_ros2 not available, no taxel forces: {e}")
                self.xela_topic = ""
            else:
                self.create_subscription(SensStream, self.xela_topic, self._on_xela, 10)
        if self.click_topic:
            self.create_subscription(Int32, self.click_topic, self._on_click, 10)
        if self.audio_topic:
            self.create_subscription(Float32MultiArray, self.audio_topic, self._on_audio, 100)
            self.create_subscription(
                String, self.audio_topic.rstrip("/") + "/info", self._on_audio_info,
                QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL),
            )
        if self.finger_contact_topic:
            self.create_subscription(
                String, self.finger_contact_topic, self._on_finger_contacts, 10
            )
        self._cmd_pub = self.create_publisher(JointState, cmd_topic, 10)
        self._sim_cmd_pub = self.create_publisher(JointState, self.sim_cmd_topic, 10)
        self._to_sim: HardwareToSim | None = None  # loaded on the first sim command
        self.hand_node = self.declare_parameter("hand_node", "leaphand_node").value
        self._get_params = self.create_client(GetParameters, f"{self.hand_node}/get_parameters")
        self._set_params = self.create_client(
            SetParametersAtomically, f"{self.hand_node}/set_parameters_atomically"
        )
        self.get_logger().info(
            f"Listening on '{topic}', '{self.sim_topic}', '{self.image_topic or '(no camera)'}', "
            f"'{self.xela_topic or '(no xela)'}', clicks '{self.click_topic or '(off)'}' "
            f"and SAM '{self.sam_prefix or '(off)'}', "
            f"playing takes on '{cmd_topic}' (sim: '{self.sim_cmd_topic}'), "
            f"saving demonstrations to '{self.demo_dir}'"
        )
        if cmd_topic == self.sim_cmd_topic:
            self.get_logger().error(
                f"cmd_topic and sim_cmd_topic are both '{cmd_topic}': Play sends the hand's "
                "commands to the sim, not to the hand"
            )

    def send_command(self, q: np.ndarray) -> None:
        """Publishes ``q`` (hardware frame) to the hand."""
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        msg.position = [float(v) for v in q]
        self._cmd_pub.publish(msg)
        with self._lock:
            if self._play_recs:
                stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
                for rec in self._play_recs.values():
                    rec["cmd"].append((stamp, np.array(q, dtype=float)))

    def sim_listening(self) -> bool:
        """True when something (``mujoco_sim_node``) subscribes to ``sim_cmd_topic``."""
        return self._sim_cmd_pub.get_subscription_count() > 0

    def send_sim_command(self, joint_names: list[str], q: np.ndarray) -> None:
        """Publishes hardware joints ``q`` (named ``joint_names``), converted to sim joints, to
        the MuJoCo sim on ``sim_cmd_topic``."""
        if self._to_sim is None:
            self._to_sim = HardwareToSim()
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(self._to_sim.sim_names)
        msg.position = [float(v) for v in self._to_sim(joint_names, q)]
        self._sim_cmd_pub.publish(msg)

    # ---- parameters of the hand node (called back from the executor thread) --------------

    def hand_params_ready(self) -> bool:
        return self._get_params.service_is_ready() and self._set_params.service_is_ready()

    @staticmethod
    def _call(client, request, convert, done) -> None:
        def finished(future) -> None:
            try:
                result = convert(future.result())
            except Exception as e:
                result = e
            done(result)

        client.call_async(request).add_done_callback(finished)

    def get_hand_params(self, names: list[str], done) -> None:
        """Calls ``done`` with {name: value} of the hand node's parameters, or an exception."""
        self._call(
            self._get_params,
            GetParameters.Request(names=list(names)),
            lambda res: {n: parameter_value(v) for n, v in zip(names, res.values)},
            done,
        )

    def set_hand_params(self, values: dict[str, float | str], done) -> None:
        """Sets double / string parameters of the hand node at once; ``done`` gets the
        ``SetParametersResult`` or an exception."""
        params = [
            Parameter(
                name=name,
                value=(
                    ParameterValue(type=ParameterType.PARAMETER_STRING, string_value=v)
                    if isinstance(v, str)
                    else ParameterValue(type=ParameterType.PARAMETER_DOUBLE, double_value=float(v))
                ),
            )
            for name, v in values.items()
        ]
        self._call(
            self._set_params,
            SetParametersAtomically.Request(parameters=params),
            lambda res: res.result,
            done,
        )

    def set_stiff_joints(self, names: list[str]) -> bool:
        """Makes the hand node use its stiff_* gains on ``names`` (compliant gains elsewhere).
        False if the hand node is not up."""
        if not self.hand_params_ready():
            return False
        joints = ",".join(names)

        def done(result) -> None:
            if isinstance(result, Exception) or not result.successful:
                reason = result if isinstance(result, Exception) else result.reason
                self.get_logger().warn(f"Could not set stiff_joints to '{joints}': {reason}")

        self.set_hand_params({"stiff_joints": joints}, done)
        return True

    def _stamp(self, header) -> float:
        stamp = header.stamp.sec + header.stamp.nanosec * 1e-9
        return stamp if stamp != 0.0 else self.get_clock().now().nanoseconds * 1e-9

    def _on_image(self, msg: Image) -> None:
        try:
            frame = rgb_frame(msg)
        except ValueError as e:
            self.get_logger().warn(str(e), throttle_duration_sec=5.0)
            return
        stamp = self._stamp(msg.header)
        with self._lock:
            self._frame = frame
            self._frame_seq += 1
            # A newer camera frame must not inherit the previous SAM mask and box.
            if not self._sam_locked:
                self._display_frame = frame
                self._display_seq += 1
            if self._play_video_path:
                if self._play_video is None:
                    h, w = frame.shape[:2]
                    os.makedirs(os.path.dirname(self._play_video_path), exist_ok=True)
                    self._play_video = cv2.VideoWriter(
                        self._play_video_path, cv2.VideoWriter_fourcc(*"mp4v"), VIDEO_FPS, (w, h)
                    )
                self._play_video.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                self._play_video_t.append(stamp)
            if not (self._recording and self._video_path):
                return
            if self._video is None:
                h, w = frame.shape[:2]
                os.makedirs(os.path.dirname(self._video_path), exist_ok=True)
                self._video = cv2.VideoWriter(
                    self._video_path, cv2.VideoWriter_fourcc(*"mp4v"), VIDEO_FPS, (w, h)
                )
            self._video.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            self._rec_frame_t.append(stamp)

    def _header_stamp(self, header) -> float | None:
        """Header stamp in seconds, or None when the message was not stamped."""
        stamp = header.stamp.sec + header.stamp.nanosec * 1e-9
        return stamp if stamp != 0.0 else None

    def _on_sam_image(self, msg: Image) -> None:
        stamp = self._header_stamp(msg.header)
        if stamp is None:
            return
        try:
            frame = rgb_frame(msg)
        except ValueError as e:
            self.get_logger().warn(str(e), throttle_duration_sec=5.0)
            return
        with self._lock:
            self._sam_put(stamp, "image", frame)

    def _on_sam_mask(self, msg: Image) -> None:
        stamp = self._header_stamp(msg.header)
        if stamp is None:
            return
        try:
            mask = image_to_array(msg)
        except ValueError as e:
            self.get_logger().warn(str(e), throttle_duration_sec=5.0)
            return
        if mask.ndim == 3:
            mask = mask[:, :, 0]
        with self._lock:
            self._sam_put(stamp, "mask", np.ascontiguousarray(mask).copy())

    def _on_sam_boxes(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
            stamp = float(payload["stamp"])
            boxes = payload.get("detections") or []
            if not isinstance(boxes, list):
                raise TypeError("detections is not a list")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            self.get_logger().warn(f"Could not read SAM boxes: {e}", throttle_duration_sec=5.0)
            return
        with self._lock:
            self._sam_put(stamp, "boxes", boxes)

    def _sam_put(self, stamp: float, key: str, value) -> None:
        """Store one SAM part under the stamp it was computed for. Caller holds ``_lock``."""
        bucket = stamp
        for existing in self._sam_parts:
            if abs(existing - stamp) <= SAM_STAMP_TOL_S:
                bucket = existing
                break
        part = self._sam_parts.get(bucket)
        if part is None:
            if len(self._sam_parts) >= SAM_PART_LIMIT:
                self._sam_parts.pop(min(self._sam_parts), None)
            part = {}
            self._sam_parts[bucket] = part
        part[key] = value
        if key == "image":
            part["header_stamp"] = stamp
        self._finish_sam(bucket)

    def _finish_sam(self, stamp: float) -> None:
        """Show and record a SAM result once its image, mask and boxes share one stamp."""
        part = self._sam_parts.get(stamp)
        if part is None or "image" not in part or "mask" not in part or "boxes" not in part:
            return
        image, mask, boxes = part["image"], part["mask"], part["boxes"]
        header_stamp = float(part.get("header_stamp", stamp))
        del self._sam_parts[stamp]
        picked = highest_detection(boxes)
        if picked is None:
            return
        if mask.shape[:2] != image.shape[:2]:
            self.get_logger().warn(
                "SAM mask size does not match its image; dropping this frame",
                throttle_duration_sec=5.0,
            )
            return
        score, best_box = picked
        self._sam_live = (self._sam_live[0] + 1, time.monotonic(), [best_box])
        # Keep the one frame shown, and record that same frame.
        if self._sam_best_score is not None and score <= self._sam_best_score:
            return
        self._sam_best_score = score
        if self._recording:
            self._rec_sam_t = [header_stamp]
            self._rec_sam_mask = [mask]
            self._rec_sam_boxes = [[best_box]]
        self._display_frame = image
        self._display_seq += 1
        if not self._sam_locked:
            self._sam_locked = True
            self.get_logger().info(
                "Showing only the camera frame with the highest SAM probability"
            )

    def _on_state(self, msg: JointState) -> None:
        if len(msg.position) != NUM_JOINTS:
            self.get_logger().warn(
                f"Expected {NUM_JOINTS} joints, got {len(msg.position)}", throttle_duration_sec=5.0
            )
            return
        stamp = self._stamp(msg.header)
        q = np.asarray(msg.position, dtype=float)
        with self._lock:
            if len(msg.name) == NUM_JOINTS:
                self._joint_names = list(msg.name)
            self._history.append((stamp, q))
            self._effort = (
                np.asarray(msg.effort, dtype=float) if len(msg.effort) == NUM_JOINTS else None
            )
            if self._play_recs:
                velocity = (
                    np.asarray(msg.velocity, dtype=float) if len(msg.velocity) == NUM_JOINTS
                    else np.full(NUM_JOINTS, np.nan)
                )
                effort = self._effort if self._effort is not None else np.full(NUM_JOINTS, np.nan)
                for rec in self._play_recs.values():
                    rec["state"].append((stamp, q, velocity, effort))
            if self._recording:
                self._rec_t.append(stamp)
                self._rec_q.append(q)

    def _on_sim_state(self, msg: JointState) -> None:
        if len(msg.position) != NUM_JOINTS or len(msg.name) != NUM_JOINTS:
            self.get_logger().warn(
                f"Expected {NUM_JOINTS} named joints on '{self.sim_topic}', got {len(msg.position)}",
                throttle_duration_sec=5.0,
            )
            return
        stamp = self._stamp(msg.header)
        q = np.asarray(msg.position, dtype=float)
        with self._lock:
            self._sim = (self._sim[0] + 1, list(msg.name), q)
            if self._recording:
                self._rec_sim_t.append(stamp)
                self._rec_sim_q.append(q)

    def _on_xela(self, msg) -> None:
        # Sensors concatenated in order give the hardware taxel ids.
        readings = np.array(
            [[t.x, t.y, t.z] for s in msg.sensors for t in s.taxels], dtype=np.float64
        ).reshape(-1, 3)
        stamp = self._stamp(msg.header)
        now = self.get_clock().now().nanoseconds * 1e-9
        if abs(stamp - now) > XELA_MAX_CLOCK_OFFSET_S:
            # xela_server stamping with another clock would misalign the takes and the plots.
            stamp = now
        with self._lock:
            self._xela = (self._xela[0] + 1, readings)
            self._xela_history.append((stamp, readings))
            for rec in self._play_recs.values():
                if not rec["xela"] or len(readings) == len(rec["xela"][0][1]):
                    rec["xela"].append((stamp, readings.astype(np.float32)))
            # A take holds one taxel count; readings of another size are dropped.
            if self._recording and (
                not self._rec_xela or len(readings) == len(self._rec_xela[0])
            ):
                self._rec_xela_t.append(stamp)
                self._rec_xela.append(readings.astype(np.float32))

    def _on_click(self, msg: Int32) -> None:
        with self._lock:
            on = msg.data != 0
            if on and not self._click:
                self._click_count += 1
                stamp = self.get_clock().now().nanoseconds * 1e-9
                for rec in self._play_recs.values():
                    rec["clicks"].append(stamp)
            self._click = on

    def _on_finger_contacts(self, msg: String) -> None:
        try:
            pairs = [
                (str(p["fingers"][0]), str(p["fingers"][1]))
                for p in json.loads(msg.data).get("pairs", [])
            ]
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            return
        if pairs:
            with self._lock:
                self._finger_contact_seq += 1
                self._finger_contacts.append((time.monotonic(), pairs))

    def finger_contacts_since(
        self, seq: int
    ) -> tuple[int, list[tuple[float, list[tuple[str, str]]]]]:
        """(latest sequence number, (time.monotonic(), touching finger pairs) of the sim's
        contact messages after ``seq``)."""
        with self._lock:
            latest = self._finger_contact_seq
            n = min(latest - seq, len(self._finger_contacts))
            items = list(self._finger_contacts)
            return latest, items[len(items) - n:] if n > 0 else []

    def _on_audio_info(self, msg: String) -> None:
        try:
            self.audio_rate = int(json.loads(msg.data)["sample_rate"])
        except (ValueError, KeyError, TypeError):
            pass

    def _on_audio(self, msg: Float32MultiArray) -> None:
        with self._lock:
            if self._play_audio is not None:
                stamp = self.get_clock().now().nanoseconds * 1e-9
                self._play_audio.append((stamp, np.asarray(msg.data, dtype=np.float32)))

    def start_play_audio(self) -> None:
        """Starts keeping the microphone samples from ``audio_topic`` (a Play's recording)."""
        with self._lock:
            self._play_audio = []

    def stop_play_audio(self) -> tuple[np.ndarray, float, int]:
        """Ends ``start_play_audio``: the samples, the (ROS) time of the first one and the
        sample rate; no samples if none came."""
        with self._lock:
            chunks, self._play_audio = self._play_audio or [], None
        if not chunks:
            return np.empty(0, np.float32), 0.0, self.audio_rate
        samples = np.concatenate([c for _, c in chunks])
        # The first chunk ended when it was received.
        first = chunks[0][0] - len(chunks[0][1]) / self.audio_rate
        return samples, first, self.audio_rate

    def start_play_video(self, path: str) -> None:
        """Starts writing the camera frames to ``path`` (a Play's recording)."""
        with self._lock:
            if self._play_video is not None:
                self._play_video.release()
            self._play_video, self._play_video_path, self._play_video_t = None, path, []

    def stop_play_video(self) -> tuple[str, np.ndarray]:
        """Ends ``start_play_video``: the file ("" if no frame came) and the frame stamps."""
        with self._lock:
            if self._play_video is not None:
                self._play_video.release()
            stamps = np.array(self._play_video_t)
            path = self._play_video_path if len(stamps) else ""
            self._play_video, self._play_video_path, self._play_video_t = None, "", []
            return path, stamps

    def start_play_recording(self, key: str) -> None:
        """Starts buffering leap_state (position, velocity, effort), Xela and clicks under
        ``key`` (independent of the Create tab's recording)."""
        with self._lock:
            self._play_recs[key] = {"state": [], "xela": [], "clicks": [], "cmd": []}

    def stop_play_recording(self, key: str) -> dict | None:
        """The buffers recorded under ``key`` since ``start_play_recording`` (None if none)."""
        with self._lock:
            return self._play_recs.pop(key, None)

    def click_state(self) -> tuple[bool, int]:
        """(a click is heard now, clicks heard so far) on ``click_topic``."""
        with self._lock:
            return self._click, self._click_count

    def latest_xela(self) -> tuple[int, np.ndarray | None]:
        """(sequence number, (T, 3) raw Xela readings by hardware id) of the latest message."""
        with self._lock:
            return self._xela

    def xela_since(self, seq: int) -> tuple[int, list[tuple[float, np.ndarray]]]:
        """(latest sequence number, (stamp, raw readings) of the messages after ``seq``)."""
        with self._lock:
            latest = self._xela[0]
            n = min(latest - seq, len(self._xela_history))
            return latest, list(self._xela_history)[len(self._xela_history) - n:] if n > 0 else []

    def latest_sim(self) -> tuple[int, list[str], np.ndarray | None]:
        """(sequence number, joint names, positions) of the latest ``sim_topic`` message."""
        with self._lock:
            return self._sim

    @property
    def joint_names(self) -> list[str]:
        with self._lock:
            return list(self._joint_names) or list(DEFAULT_JOINT_NAMES)

    def history(self) -> tuple[np.ndarray, np.ndarray]:
        """(t, q) of recent messages, shapes (N,) and (N, 16)."""
        with self._lock:
            items = list(self._history)
        if not items:
            return np.empty(0), np.empty((0, NUM_JOINTS))
        return np.array([t for t, _ in items]), np.stack([q for _, q in items])

    def latest(self) -> np.ndarray | None:
        with self._lock:
            return self._history[-1][1].copy() if self._history else None

    def latest_effort(self) -> np.ndarray | None:
        """Effort (present current) of the latest ``leap_state``, if it had one."""
        with self._lock:
            return None if self._effort is None else self._effort.copy()

    def latest_frame(self) -> tuple[int, np.ndarray | None]:
        """(sequence number, RGB frame to show).

        Before the first SAM result this is the latest camera frame. After that it is the
        camera frame SAM segmented, and only when that frame's stamp matches the mask and box.
        """
        with self._lock:
            return self._display_seq, self._display_frame

    def latest_sam(self) -> tuple[int, float, list]:
        """(sequence number, time.monotonic() received, best detection) of the latest SAM
        result, however its score compares to the one recorded."""
        with self._lock:
            return self._sam_live

    def latest_raw_frame(self) -> tuple[int, np.ndarray | None]:
        """(sequence number, latest camera frame), without a SAM overlay."""
        with self._lock:
            return self._frame_seq, self._frame

    @property
    def recording(self) -> bool:
        return self._recording

    def recorded_count(self) -> tuple[float, int]:
        """(joint duration in seconds, camera frames) of the recording in progress."""
        with self._lock:
            n = len(self._rec_t)
            return (self._rec_t[-1] - self._rec_t[0]) if n > 1 else 0.0, len(self._rec_frame_t)

    def start_recording(self, video_path: str = "") -> None:
        with self._lock:
            self._rec_t, self._rec_q, self._rec_frame_t = [], [], []
            self._rec_sim_t, self._rec_sim_q = [], []
            self._rec_xela_t, self._rec_xela = [], []
            self._rec_sam_t, self._rec_sam_mask, self._rec_sam_boxes = [], [], []
            self._sam_best_score = None
            self._video_path = video_path
            self._recording = True

    def stop_recording(self) -> Recording:
        with self._lock:
            self._recording = False
            if self._video is not None:
                self._video.release()
                self._video = None
            t = np.array(self._rec_t)
            q = np.stack(self._rec_q) if self._rec_q else np.empty((0, NUM_JOINTS))
            video_t = np.array(self._rec_frame_t)
            video = self._video_path if len(video_t) else ""
            self._video_path = ""
            sim_t = np.array(self._rec_sim_t)
            sim_q = np.stack(self._rec_sim_q) if self._rec_sim_q else np.empty((0, NUM_JOINTS))
            sim_names = list(self._sim[1])
            xela_t = np.array(self._rec_xela_t)
            xela = np.stack(self._rec_xela) if self._rec_xela else np.empty((0, 0, 3), np.float32)
            self._rec_xela_t, self._rec_xela = [], []
            sam_t = np.array(self._rec_sam_t, dtype=np.float64)
            sam_mask = (
                np.stack(self._rec_sam_mask)
                if self._rec_sam_mask
                else np.empty((0, 0, 0), np.uint8)
            )
            sam_boxes = list(self._rec_sam_boxes)
            self._rec_sam_t, self._rec_sam_mask, self._rec_sam_boxes = [], [], []
        if len(video_t) and len(sam_t):
            keep = [i for i, s in enumerate(sam_t) if stamp_matches(video_t, float(s))]
            sam_t = sam_t[keep]
            sam_mask = sam_mask[keep] if len(sam_mask) else sam_mask
            sam_boxes = [sam_boxes[i] for i in keep]
        if len(sam_t):
            order = np.argsort(sam_t)
            sam_t = sam_t[order]
            sam_mask = sam_mask[order]
            sam_boxes = [sam_boxes[int(i)] for i in order]
        t0 = t[0] if len(t) else (video_t[0] if len(video_t) else 0.0)
        return Recording(
            t=t - t0,
            q=q,
            video=video,
            video_t=video_t - t0,
            sim_t=sim_t - t0,
            sim_q=sim_q,
            sim_joint_names=sim_names,
            xela_t=xela_t - t0,
            xela=xela,
            sam_t=sam_t - t0 if len(sam_t) else sam_t,
            sam_mask=sam_mask,
            sam_boxes=sam_boxes,
        )


class CameraView(QtWidgets.QLabel):
    """Shows RGB frames scaled to fit while keeping their aspect ratio."""

    def __init__(self, topic: str) -> None:
        super().__init__(f"Waiting for {topic} ..." if topic else "No camera (image_topic is empty)")
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.setStyleSheet("background-color: black; color: white;")
        self._pixmap: QtGui.QPixmap | None = None

    def set_message(self, text: str) -> None:
        self._pixmap = None
        self.clear()
        self.setText(text)

    def set_frame(self, frame: np.ndarray) -> None:
        h, w = frame.shape[:2]
        image = QtGui.QImage(frame.data, w, h, 3 * w, QtGui.QImage.Format_RGB888)
        self._pixmap = QtGui.QPixmap.fromImage(image)
        self._show()

    def _show(self) -> None:
        if self._pixmap is not None:
            self.setPixmap(
                self._pixmap.scaled(self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            )

    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        self._show()


class TakeVideo:
    """Reads frames of a take's camera recording by index (sequentially when possible)."""

    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._path = ""
        self._index = -1

    def read(self, path: str, index: int) -> np.ndarray | None:
        """RGB frame ``index`` of ``path``; None if it is already shown or cannot be read."""
        if path != self._path:
            self.release()
            self._cap = cv2.VideoCapture(path)
            self._path = path
        if index == self._index:
            return None
        if index != self._index + 1:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, bgr = self._cap.read()
        if not ok:
            self._index = -1
            return None
        self._index = index
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
        self._cap, self._path, self._index = None, "", -1


def rgb_frame(msg: Image) -> np.ndarray:
    """RGB uint8 copy of a camera image."""
    frame = image_to_array(msg)
    if frame.ndim == 2:
        if frame.dtype != np.uint8:
            frame = (frame >> 8).astype(np.uint8)
        frame = np.repeat(frame[..., None], 3, axis=2)
    return np.ascontiguousarray(frame).copy()


def stamp_matches(stamps: np.ndarray, stamp: float, tol: float = SAM_STAMP_TOL_S) -> bool:
    """True when ``stamp`` equals one value in sorted ``stamps`` (within ``tol``)."""
    if len(stamps) == 0:
        return False
    k = int(np.searchsorted(stamps, stamp))
    return any(
        0 <= j < len(stamps) and abs(float(stamps[j]) - stamp) <= tol for j in (k - 1, k)
    )


def sam_at_stamp(
    sam_t: np.ndarray, sam_mask: np.ndarray, sam_boxes: list, stamp: float
) -> tuple[np.ndarray, list] | None:
    """Mask and boxes whose timestamp equals ``stamp``, or None if this frame has none."""
    if len(sam_t) == 0:
        return None
    k = int(np.searchsorted(sam_t, stamp))
    best_j = None
    best_dt = SAM_STAMP_TOL_S
    for j in (k - 1, k):
        if not 0 <= j < len(sam_t):
            continue
        dt = abs(float(sam_t[j]) - float(stamp))
        if dt <= best_dt:
            best_j = j
            best_dt = dt
    if best_j is None:
        return None
    mask = None
    if getattr(sam_mask, "ndim", 0) == 3 and best_j < len(sam_mask):
        mask = sam_mask[best_j]
    boxes = sam_boxes[best_j] if best_j < len(sam_boxes) else []
    return mask, boxes


def highest_detection(boxes: list) -> tuple[float, dict] | None:
    """The detection with the highest score, or None when nothing was scored."""
    best = None
    score = 0.0
    found = False
    for box in boxes if isinstance(boxes, list) else []:
        if not isinstance(box, dict):
            continue
        value = box.get("score")
        if not isinstance(value, (int, float)):
            continue
        if not found or float(value) > score:
            found = True
            score = float(value)
            best = box
    if best is None:
        return None
    chosen = dict(best)
    chosen["best"] = True
    return score, chosen


def _detection_corners(box: dict) -> np.ndarray | None:
    """(4, 2) corners of one recorded detection, or None."""
    rotated = box.get("rotated") if isinstance(box, dict) else None
    if not isinstance(rotated, dict):
        return None
    corners = rotated.get("corners")
    if corners:
        pts = np.asarray(corners, dtype=np.float64)
        if pts.shape == (4, 2) and np.isfinite(pts).all():
            return pts
    try:
        cx, cy = float(rotated["cx"]), float(rotated["cy"])
        width, height = float(rotated["width"]), float(rotated["height"])
        angle = float(rotated["angle_deg"])
    except (KeyError, TypeError, ValueError):
        return None
    theta = np.deg2rad(angle)
    along = np.array([np.cos(theta), np.sin(theta)])
    across = np.array([-np.sin(theta), np.cos(theta)])
    center = np.array([cx, cy])
    half_w, half_h = width / 2.0, height / 2.0
    return np.array(
        [
            center - half_w * along - half_h * across,
            center + half_w * along - half_h * across,
            center + half_w * along + half_h * across,
            center - half_w * along - half_h * across,
        ],
        dtype=np.float64,
    )


def recorded_take_pen_pose(take: FingerTake) -> np.ndarray | None:
    """Corners of the pen box saved with ``take``, or None.

    The box inherited from the Thumb take (``pen_box``) if there is one; otherwise the take's
    own highest-score SAM detection. Nothing is combined across frames or takes.
    """
    if len(take.pen_box) == 4:
        return np.asarray(take.pen_box, dtype=np.float32)
    best_pts = None
    best_score = None
    for index, sample in enumerate(take.sam_boxes):
        items = sample if isinstance(sample, list) else []
        picked = highest_detection(items)
        if picked is None:
            continue
        if len(take.video_t) and index < len(take.sam_t):
            if not stamp_matches(take.video_t, float(take.sam_t[index])):
                continue
        pts = _detection_corners(picked[1])
        if pts is None:
            continue
        if best_score is None or picked[0] > best_score:
            best_score = picked[0]
            best_pts = pts
    if best_pts is None:
        return None
    return np.asarray(best_pts, dtype=np.float32)


def draw_recorded_pen_pose(
    frame: np.ndarray, corners: np.ndarray, label: str = "recorded"
) -> np.ndarray:
    """Draw one recorded pen box on a copy of ``frame``, in yellow."""
    vis = np.ascontiguousarray(frame.copy())
    pts = np.round(np.asarray(corners, dtype=np.float32)).astype(np.int32)
    cv2.polylines(vis, [pts], True, RECORDED_POSE_COLOR, 2)
    top = int(pts[:, 1].min())
    left = int(pts[:, 0].min())
    cv2.putText(
        vis, label, (left, max(top - 8, 16)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, RECORDED_POSE_COLOR, 2, cv2.LINE_AA,
    )
    return vis


def overlay_sam(frame: np.ndarray, mask: np.ndarray | None, boxes: list) -> np.ndarray:
    """Draw the highest-probability mask and box onto a copy of their image."""
    vis = np.ascontiguousarray(frame.copy())
    picked = highest_detection(boxes)
    boxes = [] if picked is None else [picked[1]]
    if mask is not None and mask.shape[:2] == vis.shape[:2] and int(np.count_nonzero(mask)):
        color = SAM_BEST_COLOR
        if boxes and not any(box.get("best") for box in boxes if isinstance(box, dict)):
            color = SAM_OTHER_COLOR
        tint = vis.copy()
        tint[mask > 0] = color
        vis = cv2.addWeighted(tint, 0.35, vis, 0.65, 0)
    for box in boxes:
        if not isinstance(box, dict):
            continue
        corners = (box.get("rotated") or {}).get("corners")
        if not corners:
            continue
        pts = np.round(np.asarray(corners, dtype=np.float32)).astype(np.int32)
        color = SAM_BEST_COLOR if box.get("best") else SAM_OTHER_COLOR
        cv2.polylines(vis, [pts], True, color, 2)
        score = box.get("score")
        label = (
            f"{'pen' if box.get('best') else 'pen?'} {score:.2f}"
            if isinstance(score, (int, float))
            else "pen"
        )
        top = int(pts[:, 1].min())
        left = int(pts[:, 0].min())
        cv2.putText(
            vis, label, (left, max(top - 8, 16)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, SAM_LABEL_COLOR, 2, cv2.LINE_AA,
        )
    return vis


def show_take_at(
    take: FingerTake, t: float, camera: CameraView, hand: HandView, video: TakeVideo
) -> None:
    """Camera frame and FK taxels of ``take`` at ``t`` seconds into it."""
    if take.video and len(take.video_t) and os.path.exists(take.video):
        index = max(index_at(take.video_t, t), 0)
        frame = video.read(take.video, index)
        if frame is not None:
            # The mask and box for this frame only — not the latest detection.
            hit = sam_at_stamp(
                take.sam_t, take.sam_mask, take.sam_boxes, float(take.video_t[index])
            )
            if len(take.pen_box) == 4:
                source = os.path.splitext(os.path.basename(take.pen_box_source))[0]
                frame = draw_recorded_pen_pose(frame, take.pen_box, f"from {source or 'thumb'}")
            elif hit is not None:
                frame = overlay_sam(frame, hit[0], hit[1])
            else:
                # Only one SAM frame is stored (the highest-score detection), so Play would
                # otherwise show the box on that frame alone.
                corners = recorded_take_pen_pose(take)
                if corners is not None:
                    frame = draw_recorded_pen_pose(frame, corners)
            camera.set_frame(frame)
    else:
        video.release()
        camera.set_message(f"No camera recording in {take.name}")
    if len(take.sim_t):
        j = max(index_at(take.sim_t, t), 0)
        hand.set_joints(take.sim_hand_joint_names, take.sim_hand_q[j])
    new_take = hand.take_path != take.path
    if new_take:
        hand.take_path = take.path
        hand.take_xela_index = -1
        hand.set_baseline(take.xela_baseline if len(take.xela_baseline) else None)
    if len(take.xela_t):
        k = max(index_at(take.xela_t, t), 0)
        if k != hand.take_xela_index:
            hand.take_xela_index = k
            hand.set_readings(take.xela[k], source=f"Recorded Xela of {take.name}")
    elif new_take:
        hand.clear_readings(f"No Xela readings in {take.name}")


def side_column(title: QtWidgets.QWidget, camera: CameraView, hand: HandView) -> QtWidgets.QWidget:
    """``title`` above the camera and the FK taxels (split vertically)."""
    split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
    split.addWidget(camera)
    split.addWidget(hand)
    column = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(column)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(title)
    layout.addWidget(split, 1)
    return column


def rgba(colors: np.ndarray) -> np.ndarray:
    return np.column_stack([colors, np.ones(len(colors))])


class HandView(QtWidgets.QWidget):
    """Taxels of the hand placed by forward kinematics from sim-frame joint angles, deformed,
    colored and given force vectors by the live Xela readings (change from a baseline taken at
    the first reading or with Zero), as in the bag viewer."""

    TAXEL_SIZE = 0.003  # m

    def __init__(
        self,
        sim_topic: str,
        xela_topic: str,
        counts_per_unit: float,
        waiting: str | None = None,
        no_xela: str = "No taxel forces (xela_topic is empty)",
    ) -> None:
        """``waiting`` / ``no_xela`` replace the default texts shown before joints arrive and
        when there is no Xela topic."""
        super().__init__()
        self.setMinimumSize(320, 240)
        self.xela_topic = xela_topic
        self.counts_per_unit = counts_per_unit
        self._last: np.ndarray | None = None
        self._pos: np.ndarray | None = None  # (368, 3) FK taxel positions
        self._rot: np.ndarray | None = None  # (368, 3, 3) taxel local -> world
        self._readings: np.ndarray | None = None  # (T, 3) latest raw Xela readings by id
        self._baseline: np.ndarray | None = None  # (368, 3)
        self.take_path: str | None = None  # take whose recorded readings are shown
        self.take_xela_index = -1  # index into that take's ``xela`` shown
        self._fk = None

        self.deform_box = QtWidgets.QCheckBox("Deform")
        self.deform_box.setToolTip("Move and color the taxels by their force")
        self.vectors_box = QtWidgets.QCheckBox("Force vectors")
        self.zero_btn = QtWidgets.QPushButton("Zero")
        self.zero_btn.setToolTip("Use the current Xela reading as the no-contact baseline")
        self.status = QtWidgets.QLabel()
        for box in (self.deform_box, self.vectors_box):
            box.setChecked(True)
            box.toggled.connect(lambda _: self._redraw())
        self.zero_btn.clicked.connect(self._zero)
        controls = QtWidgets.QHBoxLayout()
        for w in (self.deform_box, self.vectors_box, self.zero_btn):
            controls.addWidget(w)
        controls.addWidget(self.status, 1)
        self.stack = QtWidgets.QStackedWidget()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(self.stack, 1)
        self._set_status(f"Waiting for {xela_topic} ..." if xela_topic else no_xela)

        try:
            import pyqtgraph.opengl as gl

            from mechanical_pen_data_collection import taxel_fk_util as fk
        except Exception as e:
            self.stack.addWidget(self._message(f"Hand view unavailable: {e}"))
            self._enable_controls(False)
            return
        self._fk = fk
        self._patch_colors = rgba(fk.taxel_patch_colors(fk.PATCH_IDS_IN_FK_ORDER))
        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor((20, 20, 26))
        self._scatter = gl.GLScatterPlotItem(
            pos=np.zeros((fk.NUM_TAXELS, 3)),
            color=self._patch_colors,
            size=self.TAXEL_SIZE,
            pxMode=False,
        )
        self._vectors = gl.GLLinePlotItem(mode="lines", width=2, antialias=True)
        self._vectors.hide()
        self.view.addItem(self._scatter)
        self.view.addItem(self._vectors)
        self.view.addItem(gl.GLAxisItem(size=QtGui.QVector3D(0.04, 0.04, 0.04)))
        self.stack.addWidget(
            self._message(waiting or f"Waiting for {sim_topic} (convert_hardware_to_sim) ...")
        )
        self.stack.addWidget(self.view)
        self._enable_controls(bool(xela_topic))

    @staticmethod
    def _message(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("background-color: black; color: white;")
        return label

    def _enable_controls(self, on: bool) -> None:
        for w in (self.deform_box, self.vectors_box, self.zero_btn):
            w.setEnabled(on)

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status.setText(f"<span style='color:#d32f2f'>{text}</span>" if error else text)

    def _valid_readings(self) -> np.ndarray | None:
        r = self._readings
        return r[: self._fk.NUM_TAXELS] if r is not None and len(r) >= self._fk.NUM_TAXELS else None

    def _zero(self) -> None:
        readings = self._valid_readings() if self._fk is not None else None
        if readings is not None:
            self._baseline = readings.copy()
            self._redraw()

    def clear(self) -> None:
        """Back to the waiting text until the next ``set_joints``."""
        self.take_path = None
        if self._fk is not None:
            self._last = None
            self.stack.setCurrentIndex(0)

    @property
    def baseline(self) -> np.ndarray | None:
        return self._baseline

    def set_baseline(self, baseline: np.ndarray | None) -> None:
        """Use ``baseline`` as the no-contact reading (None: the next reading)."""
        if self._fk is not None and baseline is not None and len(baseline) >= self._fk.NUM_TAXELS:
            self._baseline = np.asarray(baseline[: self._fk.NUM_TAXELS], dtype=np.float64)
        else:
            self._baseline = None

    def clear_readings(self, status: str) -> None:
        """Drop the readings (taxels keep their patch colors) and show ``status``."""
        self._readings = None
        self._enable_controls(False)
        self._set_status(status)
        self._redraw()

    def set_joints(self, names: list[str], q: np.ndarray) -> None:
        if self._fk is None or (self._last is not None and np.array_equal(q, self._last)):
            return
        first = self._pos is None
        self._last = q.copy()
        try:
            pos, rot = self._fk.get_fk_taxel_frames(self._fk.joint_angles_in_fk_order(names, q))
        except Exception as e:
            self._fk = None
            self._enable_controls(False)
            self.stack.addWidget(self._message(f"Hand view failed: {e}"))
            self.stack.setCurrentIndex(self.stack.count() - 1)
            return
        self._pos, self._rot = pos[0], rot[0]
        self._redraw()
        self.stack.setCurrentWidget(self.view)
        if first:
            # Side view: fingers along +Y, Z up.
            center = self._pos.mean(axis=0)
            self.view.setCameraPosition(
                pos=QtGui.QVector3D(*center), distance=0.35, elevation=20, azimuth=-125
            )

    def set_readings(self, readings: np.ndarray, source: str | None = None) -> None:
        """Show raw Xela ``readings``; ``source`` names them in the status (default: live topic)."""
        if self._fk is None:
            return
        self._readings = readings
        valid = self._valid_readings()
        if valid is None:
            self._set_status(
                f"{len(readings)} taxels in {source or self.xela_topic}, "
                f"expected {self._fk.NUM_TAXELS}",
                error=True,
            )
        else:
            if self._baseline is None:
                self._baseline = valid.copy()
            self._enable_controls(True)
            self._set_status(source or f"{self.xela_topic} live")
        self._redraw()

    def _redraw(self) -> None:
        if self._fk is None or self._pos is None:
            return
        fk = self._fk
        readings = self._valid_readings()
        forces_local = None
        if readings is not None and self._baseline is not None:
            forces_local = fk.taxel_readings_to_local_forces(
                readings, self._baseline, self.counts_per_unit
            )
        pos, colors = self._pos, self._patch_colors
        if forces_local is not None and self.deform_box.isChecked():
            pos = fk.deform_taxel_positions(self._pos, self._rot, forces_local)
            vmax = max(float(np.percentile(np.linalg.norm(forces_local, axis=-1), 98)), 1e-6)
            colors = rgba(fk.force_magnitude_colors(forces_local, vmax=vmax))
        self._scatter.setData(pos=pos, color=colors)

        starts = np.empty((0, 3))
        if forces_local is not None and self.vectors_box.isChecked():
            forces_world = fk.local_forces_to_world(forces_local, self._rot)
            starts, ends, vector_colors = fk.force_vector_segments(pos, forces_world)
        if len(starts) == 0:
            self._vectors.hide()
            return
        segments = np.empty((2 * len(starts), 3))
        segments[0::2], segments[1::2] = starts, ends
        self._vectors.setData(pos=segments, color=np.repeat(rgba(vector_colors), 2, axis=0))
        self._vectors.show()


STOP_STYLE = "background-color: #d32f2f; color: white;"


class ToggleSwitch(QtWidgets.QAbstractButton):
    """Sliding on/off switch (iOS style)."""

    OFF_COLOR = QtGui.QColor("#9e9e9e")
    ON_COLOR = QtGui.QColor("#34c759")

    def __init__(self) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedSize(self.sizeHint())
        self._knob = 0.0  # 0 = off (left), 1 = on (right)
        self._anim = QtCore.QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        self.toggled.connect(self._slide)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(48, 28)

    def _get_knob(self) -> float:
        return self._knob

    def _set_knob(self, value: float) -> None:
        self._knob = value
        self.update()

    knob = QtCore.pyqtProperty(float, _get_knob, _set_knob)

    def _slide(self, on: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._knob)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, _) -> None:
        a = self._knob
        off, on = self.OFF_COLOR, self.ON_COLOR
        track = QtGui.QColor(
            int(off.red() + a * (on.red() - off.red())),
            int(off.green() + a * (on.green() - off.green())),
            int(off.blue() + a * (on.blue() - off.blue())),
        )
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        d = rect.height() - 4
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.4)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        p.setBrush(QtGui.QColor("white"))
        x = rect.x() + 2 + a * (rect.width() - d - 4)
        p.drawEllipse(QtCore.QRectF(x, rect.y() + 2, d, d))


class TipTaxelPlot(pg.PlotWidget):
    """|force| of each fingertip taxel of one finger over time (one curve per taxel), scaled as
    in ``HandView``. Hovering highlights the nearest curve and names its Xela taxel id."""

    TITLE = "Fingertip taxels"

    def __init__(self, finger: str) -> None:
        super().__init__()
        ids = fingertip_taxel_ids()
        self.ids = ids[finger] if ids is not None else np.empty(0, dtype=int)
        n = len(self.ids)
        item = self.getPlotItem()
        item.showGrid(x=True, y=True, alpha=0.3)
        item.setLabel("bottom", "time", "s")
        item.setLabel("left", "|force|")
        item.setClipToView(True)
        item.setDownsampling(auto=True, mode="peak")
        item.enableAutoRange(axis="x", enable=False)  # follows the joint plot it is linked to
        self._pens = [pg.mkPen(pg.intColor(i, hues=max(n, 1)), width=1) for i in range(n)]
        self.curves = [item.plot(pen=pen, antialias=False) for pen in self._pens]
        # Recorded magnitudes of the take being played; the live ``curves`` are dashed meanwhile.
        self.demo_curves = [
            item.plot(pen=pg.mkPen(pen.color(), width=1.5), antialias=False) for pen in self._pens
        ]
        self._live_style = QtCore.Qt.SolidLine
        self._t = np.empty(0)
        self._mags = np.empty((0, n))
        self._status = ""
        self._hovered: int | None = None
        self.set_status("" if ids is not None else "taxel map unavailable")
        self.scene().sigMouseMoved.connect(self._on_hover)

    def set_status(self, text: str) -> None:
        """Shown after the title (e.g. why there is no data)."""
        self._status = text
        self._show_title()

    def set_data(self, t: np.ndarray, mags: np.ndarray) -> None:
        """``mags`` (N, 30): magnitude of each taxel of ``ids`` at times ``t``."""
        self._t, self._mags = t, mags
        for j, curve in enumerate(self.curves):
            curve.setData(t, mags[:, j])

    def clear_data(self, status: str) -> None:
        self.set_data(np.empty(0), np.empty((0, len(self.ids))))
        self.set_status(status)

    def set_playing(self, on: bool) -> None:
        """While playing: demonstration solid, measured taxels dashed."""
        self._live_style = QtCore.Qt.DashLine if on else QtCore.Qt.SolidLine
        for j, curve in enumerate(self.curves):
            curve.setPen(self._live_pen(j, 3 if j == self._hovered else 1))
        if not on:
            self.set_demo_data(np.empty(0), np.empty((0, len(self.ids))))
        self._show_title()

    def set_demo_data(self, t: np.ndarray, mags: np.ndarray) -> None:
        """``mags`` (N, 30): recorded magnitudes of the take being played at times ``t``."""
        for j, curve in enumerate(self.demo_curves):
            curve.setData(t, mags[:, j] if len(mags) else mags)

    def _live_pen(self, j: int, width: float) -> QtGui.QPen:
        return pg.mkPen(self._pens[j].color(), width=width, style=self._live_style)

    def _show_title(self, extra: str = "") -> None:
        if self._live_style != QtCore.Qt.SolidLine:
            status = "solid: demonstration, dashed: measured"
        else:
            status = self._status
        parts = [self.TITLE] + [p for p in (status, extra) if p]
        self.getPlotItem().setTitle(" - ".join(parts), size="9pt")

    def _highlight(self, j: int | None) -> None:
        if j == self._hovered:
            return
        for k in (self._hovered, j):
            if k is not None:
                self.curves[k].setPen(self._live_pen(k, 3 if k == j else 1))
        if j is not None:
            self.curves[j].setZValue(1)
        if self._hovered is not None:
            self.curves[self._hovered].setZValue(0)
        self._hovered = j

    def _on_hover(self, pos) -> None:
        vb = self.getPlotItem().getViewBox()
        if len(self._t) == 0 or not vb.sceneBoundingRect().contains(pos):
            self._highlight(None)
            self._show_title()
            return
        p = vb.mapSceneToView(pos)
        i = int(np.clip(np.searchsorted(self._t, p.x()), 0, len(self._t) - 1))
        j = int(np.argmin(np.abs(self._mags[i] - p.y())))
        self._highlight(j)
        self._show_title(f"taxel {int(self.ids[j])}: {self._mags[i, j]:.3f}")


def confirm_delete_take(parent: QtWidgets.QWidget, name: str) -> bool:
    """Asks whether to delete the take ``name``; True if confirmed."""
    box = QtWidgets.QMessageBox(parent)
    box.setIcon(QtWidgets.QMessageBox.Warning)
    box.setWindowTitle("Delete take")
    box.setText(f"Delete the take '{name}'?")
    box.setInformativeText(
        "Its file, events and (if no other finger uses it) its camera recording are removed "
        "from disk. This cannot be undone."
    )
    cancel = box.addButton(QtWidgets.QMessageBox.Cancel)
    confirm = box.addButton("Confirm", QtWidgets.QMessageBox.DestructiveRole)
    box.setDefaultButton(cancel)
    box.exec_()
    return box.clickedButton() is confirm


class FingerPanel(QtWidgets.QWidget):
    """Take name + Record, take picker + Play, Pose switch and a play bar above the live plot
    of one finger."""

    def __init__(self, finger: str, label: str) -> None:
        super().__init__()
        self.finger = finger
        self.label = label
        self.default_name = ""  # generated name shown in ``name_edit`` until the user edits it
        self.duration = 0.0  # of the selected take
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setToolTip("Name of the next take of this finger")
        self.record_btn = QtWidgets.QPushButton("Record")
        self.take_combo = QtWidgets.QComboBox()
        self.take_combo.setToolTip("Recorded takes of this finger, newest first")
        self.take_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.take_combo.setMinimumContentsLength(10)
        self.play_btn = QtWidgets.QPushButton("Play")
        for btn in (self.record_btn, self.play_btn):
            btn.setMinimumWidth(90)
        self.delete_btn = QtWidgets.QPushButton("Delete")
        self.delete_btn.setToolTip("Delete the selected take from disk")
        # Not auto-exclusive, so clicking it again turns it off.
        self.reverse_btn: QtWidgets.QRadioButton | None = None
        if finger in REVERSE_FINGERS:
            self.reverse_btn = QtWidgets.QRadioButton("Reverse")
            self.reverse_btn.setAutoExclusive(False)
            self.reverse_btn.setToolTip(
                "Play the take backwards, from the play bar position (or its end) to its start"
            )
        self.play_bar = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.play_bar.setRange(0, PLAY_BAR_STEPS)
        self.play_bar.setToolTip("Playback position: drag to choose where Play starts, or to seek")
        self.time_label = QtWidgets.QLabel()
        self.pose_switch = ToggleSwitch()
        self.pose_switch.setToolTip(
            "Draw this finger's selected recording's pen box on the live camera, in yellow. "
            "While on, new recordings inherit this pen box."
        )

        header = QtWidgets.QHBoxLayout()
        header.addWidget(QtWidgets.QLabel(f"<b>{label}</b>"), 1)
        header.addWidget(QtWidgets.QLabel("Pose"))
        header.addWidget(self.pose_switch)
        bar_row = QtWidgets.QHBoxLayout()
        bar_row.addWidget(self.play_bar, 1)
        bar_row.addWidget(self.time_label)
        controls = QtWidgets.QGridLayout()
        controls.addLayout(header, 0, 0, 1, 2)
        controls.addWidget(self.name_edit, 1, 0)
        controls.addWidget(self.record_btn, 1, 1)
        take_row = QtWidgets.QHBoxLayout()
        take_row.addWidget(self.take_combo, 1)
        if self.reverse_btn is not None:
            take_row.addWidget(self.reverse_btn)
        controls.addLayout(take_row, 2, 0)
        play_row = QtWidgets.QHBoxLayout()
        play_row.addWidget(self.delete_btn)
        play_row.addWidget(self.play_btn)
        controls.addLayout(play_row, 2, 1)
        controls.addLayout(bar_row, 3, 0, 1, 2)
        controls.setColumnStretch(0, 1)

        self.plot = pg.PlotWidget()
        item = self.plot.getPlotItem()
        item.showGrid(x=True, y=True, alpha=0.3)
        item.setLabel("bottom", "time", "s")
        item.setLabel("left", "position", "rad")
        self.legend = item.addLegend(offset=(5, 5))
        self.curves = [item.plot(pen=pg.mkPen(color, width=2)) for color in JOINT_COLORS]
        # What Play commands from the take; the measured ``curves`` are dashed meanwhile.
        self.demo_curves = [item.plot(pen=pg.mkPen(color, width=2)) for color in JOINT_COLORS]
        self.tip_plot = TipTaxelPlot(finger)
        self.tip_plot.setXLink(self.plot)
        plots = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        plots.addWidget(self.plot)
        plots.addWidget(self.tip_plot)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(plots, 1)

    def set_playing(self, on: bool) -> None:
        """While playing: demonstration solid, measured joints and taxels dashed."""
        style = QtCore.Qt.DashLine if on else QtCore.Qt.SolidLine
        for curve, color in zip(self.curves, JOINT_COLORS):
            curve.setPen(pg.mkPen(color, width=2, style=style))
        if not on:
            for curve in self.demo_curves:
                curve.setData([], [])
        self.plot.getPlotItem().setTitle(
            "solid: demonstration, dashed: measured" if on else None, size="9pt"
        )
        self.tip_plot.set_playing(on)

    def fill_takes(self, store: TakeStore, select: str | None = None) -> None:
        """Lists the takes of this finger, selecting ``select`` (default: keep the selection)."""
        keep = select or self.take_combo.currentData()
        self.take_combo.blockSignals(True)
        self.take_combo.clear()
        for path in store.list(self.finger):
            self.take_combo.addItem(os.path.splitext(os.path.basename(path))[0], path)
        index = self.take_combo.findData(keep) if keep else 0
        self.take_combo.setCurrentIndex(max(index, 0))
        self.take_combo.blockSignals(False)
        self.update_play_enabled()

    def update_play_enabled(self) -> None:
        has_take = self.take_combo.count() > 0
        self.play_btn.setEnabled(has_take)
        self.delete_btn.setEnabled(has_take)
        self.pose_switch.setEnabled(has_take)
        if not has_take and self.pose_switch.isChecked():
            self.pose_switch.setChecked(False)

    @property
    def reverse(self) -> bool:
        return self.reverse_btn is not None and self.reverse_btn.isChecked()

    def bar_time(self) -> float:
        return self.play_bar.value() / PLAY_BAR_STEPS * self.duration

    def set_position(self, local: float) -> None:
        self.play_bar.blockSignals(True)
        self.play_bar.setValue(int(round(local / self.duration * PLAY_BAR_STEPS)) if self.duration else 0)
        self.play_bar.blockSignals(False)
        self.time_label.setText(f"{local:.2f} / {self.duration:.2f} s")


def sample_take(take: FingerTake, local: float) -> np.ndarray:
    return np.array([np.interp(local, take.t, take.q[:, j]) for j in range(take.q.shape[1])])


def take_tip_magnitudes(
    take: FingerTake, ids: np.ndarray, counts_per_unit: float
) -> np.ndarray | None:
    """(L, len(ids)) magnitudes of taxels ``ids`` at ``take.xela_t``, from the take's baseline
    (its first reading for takes without one); None if the take has no usable Xela readings."""
    if len(take.xela_t) == 0 or len(ids) == 0 or take.xela.shape[1] <= ids.max():
        return None
    baseline = take.xela_baseline if len(take.xela_baseline) > ids.max() else take.xela[0]
    return taxel_magnitudes(take.xela, baseline, ids, counts_per_unit)


@dataclass
class Playback:
    take: FingerTake
    cols: list[int]  # hand columns driven by the take
    start: float  # time.monotonic() when the ramp started
    from_q: np.ndarray  # finger joints at the start of the ramp
    offset: float  # take time reached at the end of the ramp
    to_q: np.ndarray  # finger joints at ``offset``
    local: float = 0.0  # take time last commanded
    reverse: bool = False  # take time runs from ``offset`` back to 0
    stop: float | None = None  # take time where it ends (None: the take's end, or 0 in reverse)
    finished: bool = False  # reached the end; the GUI thread is asked to stop it
    # Stay at the end (maintain touch still holding) instead of finishing, until released
    # (``release_end_hold``); ``holding`` once it got there.
    hold_at_end: bool = False
    holding: bool = False
    held_s: float = 0.0  # time since ``start`` the take was held (force replay, presses, touch)
    last_step: float = 0.0  # time.monotonic() of the last command step
    # Force replay (None: plain position replay) and the live fingertip it reads.
    force: ForceTracker | None = None
    tip_ids: np.ndarray | None = None
    live_baseline: np.ndarray | None = None  # (T, 3) live view's baseline at Play
    # (ROS time, commanded hand pose) of every command step, plotted against ``leap_state``.
    history: deque[tuple[float, np.ndarray]] = field(
        default_factory=lambda: deque(maxlen=HISTORY_LEN)
    )
    # (ROS time, take time commanded) of every command step, to plot the take's taxels.
    local_history: deque[tuple[float, float]] = field(
        default_factory=lambda: deque(maxlen=HISTORY_LEN)
    )
    tip_mags: np.ndarray | None = None  # (L, 30) recorded fingertip magnitudes (None: no Xela)
    pen_corners: np.ndarray | None = None  # (4, 2) recorded pen box drawn on the live camera
    touch: TouchPress | TouchHold | None = None  # maintain_touch regions (Edit tab Play)
    probe: ClickProbe | None = None  # click setting search: commands the finger instead of the take
    press: ClickPress | None = None  # click_press regions: command the finger over them
    pad_grid: np.ndarray | None = None  # (30, 3) fingertip taxel positions on the pad (m)
    # (ROS time, take time, commanded hand) of every command step, kept whole for the playback
    # recording (``history`` / ``local_history`` only keep the last HISTORY_LEN).
    cmd_log: list[tuple[float, float, np.ndarray]] = field(default_factory=list)

    @property
    def end(self) -> float:
        if self.stop is not None:
            return self.stop
        return 0.0 if self.reverse else self.take.duration


class CreateTab(QtWidgets.QWidget):
    """One live plot per finger with Record / Play buttons, plus the camera.

    A finger's Record saves a take of that finger under the name in its text box. Play sends the
    take selected in the finger's dropdown to the hand, starting from the play bar position.

    While any finger is playing, the whole hand is commanded on ``cmd_topic``; the other
    ("free") fingers mimic leaphand_node's compliant mode so they can still be posed by hand.
    A finger's Pose switch draws the pen box from that finger's selected recording on the
    live camera. Play does the same for the take being played.
    """

    takes_changed = QtCore.pyqtSignal()
    delete_requested = QtCore.pyqtSignal(str)  # path of the take, confirmed by the user
    playing_changed = QtCore.pyqtSignal(str)  # finger that started or stopped playing
    # Emitted from the command thread when a finger's take has ended; queued to the GUI thread.
    _play_finished = QtCore.pyqtSignal(str)
    play_reached_end = QtCore.pyqtSignal(str)  # finger playing with hold_at_end got to its end

    def __init__(
        self,
        node: LeapStateListener,
        store: TakeStore,
        settings: HoldSettings,
        touch_settings: MaintainTouchSettings,
        press_settings: ClickPressSettings,
    ) -> None:
        super().__init__()
        self.node = node
        self.store = store
        self.settings = settings
        self.touch_settings = touch_settings
        self.press_settings = press_settings
        self._hand_kin: HandKinematics | None = None  # built at the first click_press Play
        self._hand_kin_error = ""  # why it could not be built
        self._frame_seq = 0
        self._sim_seq = 0
        self._xela_seq = 0
        # Live fingertip plots: (stamp, readings of ``_tip_ids``) over the last LIVE_WINDOW_S.
        tip_ids = fingertip_taxel_ids()
        self._tip_ids = (
            np.concatenate([tip_ids[f] for f, _ in FINGERS]) if tip_ids else np.empty(0, int)
        )
        self._tip_seq = 0
        self._tip_history: deque[tuple[float, np.ndarray]] = deque()
        self._tip_baseline: np.ndarray | None = None  # baseline the plots were drawn with
        self._tip_waiting = False  # plots show the waiting text
        self._take_name = ""
        self._rec_fingers: tuple[str, ...] = ()
        # (corners, source take path) of the Pose switch that was on when Record was pressed
        self._rec_pen_ref: tuple[np.ndarray, str] | None = None
        self._rec_btn: QtWidgets.QPushButton | None = None
        self._free: np.ndarray | None = None  # goal of the fingers that are not playing
        self._last_cmd: np.ndarray | None = None
        self._playing: dict[str, Playback] = {}
        self.stopped: dict[str, Playback] = {}  # last playback each finger stopped
        self._stiff_sent: tuple[str, ...] = ()  # joints last given the hand's stiff gains
        self._recorded_pen_finger: str | None = None  # finger whose Pose switch is on
        self._recorded_pen_corners: np.ndarray | None = None  # (4, 2) while a Pose switch is on
        self._recorded_pen_label = "recorded"

        grid = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        self.panels: dict[str, FingerPanel] = {}
        for n, (finger, label) in enumerate(FINGERS):
            panel = FingerPanel(finger, label)
            self.panels[finger] = panel
            grid_layout.addWidget(panel, n // 2, n % 2)
            panel.record_btn.clicked.connect(
                lambda _, f=finger, b=panel.record_btn: self.toggle_recording((f,), b)
            )
            panel.play_btn.clicked.connect(lambda _, f=finger: self.toggle_play(f))
            panel.delete_btn.clicked.connect(lambda _, f=finger: self._confirm_delete(f))
            panel.take_combo.currentIndexChanged.connect(lambda _, f=finger: self._on_take_selected(f))
            panel.play_bar.valueChanged.connect(lambda _, f=finger: self._on_seek(f))
            panel.pose_switch.toggled.connect(
                lambda on, f=finger: self._on_show_recorded_pen_pose(f, on)
            )
            self._new_default_name(panel)
            panel.fill_takes(store)
            self._on_take_selected(finger)
        self._legend_names: list[str] = []

        self.camera = CameraView(node.image_topic)
        self.hand = HandView(node.sim_topic, node.xela_topic, node.counts_per_unit)
        live_title = QtWidgets.QLabel("<b>Live</b>")
        # The recording of the take being played, next to the live view.
        self.play_title = QtWidgets.QLabel()
        self.play_camera = CameraView("")
        self.play_hand = HandView(
            "", "", node.counts_per_unit,
            waiting="Press Play to see the take's taxels",
            no_xela="Press Play to see the take's Xela readings",
        )
        self._play_video = TakeVideo()
        self._shown_play: str | None = None  # finger whose take the playback column shows
        self._clear_playback_view()
        sides = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        sides.addWidget(side_column(live_title, self.camera, self.hand))
        sides.addWidget(side_column(self.play_title, self.play_camera, self.play_hand))
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(grid)
        splitter.addWidget(sides)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # Not auto-exclusive, so clicking it again turns it off.
        self.live_box_btn = QtWidgets.QRadioButton("Live pen box")
        self.live_box_btn.setAutoExclusive(False)
        self.live_box_btn.setToolTip(
            f"Draw the latest SAM pen box ({node.sam_prefix or 'sam_prefix is empty'}) on the "
            "live camera"
        )
        self.live_box_btn.toggled.connect(lambda _: self._invalidate_camera())
        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.live_box_btn)
        top.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)

        # Commands are sent from their own thread: a GUI redraw (cameras, FK taxels, plots) can
        # take several command periods, which played takes as a staircase. ``_cmd_lock`` guards
        # what both threads touch: ``_commanding``, ``_free``, ``_last_cmd``, the ``_playing``
        # dict (changed only by the GUI thread) and the fields of its Playbacks.
        self._cmd_lock = threading.Lock()
        self._commanding = False
        self._cmd_stop = threading.Event()
        self._play_finished.connect(self._on_play_finished)
        self._cmd_thread = threading.Thread(target=self._command_loop, daemon=True)
        self._cmd_thread.start()

    def _confirm_delete(self, finger: str) -> None:
        panel = self.panels[finger]
        path = panel.take_combo.currentData()
        if path is not None and confirm_delete_take(self, panel.take_combo.currentText()):
            self.delete_requested.emit(path)

    def _invalidate_camera(self) -> None:
        self._frame_seq = -1

    def _live_sam_boxes(self) -> list:
        """Latest SAM pen box for the live camera ([] when off, none yet or stale)."""
        if not self.live_box_btn.isChecked():
            return []
        _, received, boxes = self.node.latest_sam()
        if not boxes or time.monotonic() - received > LIVE_SAM_MAX_AGE_S:
            return []
        return boxes

    def _record_buttons(self) -> list[QtWidgets.QPushButton]:
        return [p.record_btn for p in self.panels.values()]

    def _new_default_name(self, panel: FingerPanel) -> str:
        panel.default_name = self.store.numbered_take_name(panel.finger)
        panel.name_edit.setText(panel.default_name)
        return panel.default_name

    def _on_take_selected(self, finger: str) -> None:
        panel = self.panels[finger]
        path = panel.take_combo.currentData()
        panel.duration = 0.0
        if path is not None:
            try:
                panel.duration = self.store.load(path).duration
            except Exception as e:
                self.node.get_logger().warn(f"Could not load {path}: {e}")
        panel.set_position(0.0)
        if self._recorded_pen_finger == finger:
            self._refresh_recorded_pen_pose()

    def _on_seek(self, finger: str) -> None:
        """Play bar moved by the user: show the time and, if playing, ramp to it and continue."""
        panel = self.panels[finger]
        local = panel.bar_time()
        panel.time_label.setText(f"{local:.2f} / {panel.duration:.2f} s")
        p = self._playing.get(finger)
        if p is None:
            return
        with self._cmd_lock:
            if self._last_cmd is not None:
                p.from_q = self._last_cmd[p.cols].copy()
            p.start = time.monotonic()
            p.offset = local
            p.to_q = sample_take(p.take, local)
            p.finished = False
            p.held_s = 0.0
            if p.force is not None:
                p.force.reset(local)
            if p.touch is not None:
                p.touch.reset()

    # ---- recording ----------------------------------------------------------------------

    def toggle_recording(self, fingers: tuple[str, ...], button: QtWidgets.QPushButton) -> None:
        if self.node.recording:
            self.stop_recording()
            return
        if len(fingers) == 1:
            panel = self.panels[fingers[0]]
            text = panel.name_edit.text().strip()
            if not text or text == panel.default_name:
                text = self._new_default_name(panel)
            self._take_name = self.store.unique_take_name(safe_name(text))
            panel.name_edit.setText(self._take_name)
        else:
            self._take_name = self.store.new_take_name()
        self._rec_fingers = fingers
        self._rec_btn = button
        self._rec_pen_ref = None
        if self._recorded_pen_finger is not None and self._recorded_pen_corners is not None:
            source = self.panels[self._recorded_pen_finger].take_combo.currentData() or ""
            self._rec_pen_ref = (np.asarray(self._recorded_pen_corners, np.float32), source)
        self.node.start_recording(self.store.video_path(self._take_name) if self.node.image_topic else "")
        for btn in self._record_buttons():
            btn.setEnabled(btn is button)
        for panel in self.panels.values():
            panel.name_edit.setEnabled(False)
        button.setText("Stop")
        button.setStyleSheet(STOP_STYLE)

    def stop_recording(self) -> None:
        rec = self.node.stop_recording()
        for btn in self._record_buttons():
            btn.setEnabled(True)
            btn.setStyleSheet("")
        for panel in self.panels.values():
            panel.record_btn.setText("Record")
            panel.name_edit.setEnabled(True)
        if len(rec.t) < 2:
            if rec.video:
                os.remove(rec.video)
            QtWidgets.QMessageBox.warning(
                self, "Record", "Fewer than 2 leap_state messages were received; nothing saved."
            )
            return
        if len(rec.sim_t) == 0:
            self.node.get_logger().warn(
                f"No '{self.node.sim_topic}' messages during the take; saving it without sim joints"
            )
        if self.node.xela_topic and len(rec.xela_t) == 0:
            self.node.get_logger().warn(
                f"No '{self.node.xela_topic}' messages during the take; saving it without taxels"
            )
        if self.node.sam_prefix and len(rec.sam_t) == 0:
            self.node.get_logger().warn(
                f"No SAM mask or box on '{self.node.sam_prefix}' during the take; "
                "saving it without them"
            )
        baseline = self.hand.baseline
        if baseline is None or (len(rec.xela) and len(baseline) > rec.xela.shape[1]):
            baseline = rec.xela[0] if len(rec.xela) else np.empty((0, 3))
        hand_names = self.node.joint_names
        pen_box, pen_box_source = np.empty((0, 2), np.float32), ""
        if self._rec_pen_ref is not None:
            pen_box, pen_box_source = self._rec_pen_ref
            self.node.get_logger().info(
                f"Take '{self._take_name}' inherits the Pose pen box of '{pen_box_source}'"
            )
        elif any(f in PEN_BOX_FROM_THUMB for f in self._rec_fingers):
            pen_box, pen_box_source = self._thumb_pen_box()
        for finger in self._rec_fingers:
            idx = finger_indices(hand_names, finger)
            path = self.store.take_path(finger, self._take_name)
            inherit = self._rec_pen_ref is not None or finger in PEN_BOX_FROM_THUMB
            FingerTake(
                finger=finger,
                path=path,
                t=rec.t,
                q=rec.q[:, idx],
                joint_names=[hand_names[i] for i in idx],
                hand_q=rec.q,
                hand_joint_names=hand_names,
                video=rec.video,
                video_t=rec.video_t,
                sim_t=rec.sim_t,
                sim_hand_q=rec.sim_q,
                sim_hand_joint_names=rec.sim_joint_names,
                xela_t=rec.xela_t,
                xela=rec.xela,
                xela_baseline=np.asarray(baseline, dtype=np.float32),
                sam_t=rec.sam_t,
                sam_mask=rec.sam_mask,
                sam_boxes=rec.sam_boxes,
                pen_box=pen_box if inherit else np.empty((0, 2), np.float32),
                pen_box_source=pen_box_source if inherit else "",
            ).save()
            panel = self.panels[finger]
            self._new_default_name(panel)
            if finger not in self._playing:
                panel.fill_takes(self.store, select=path)
                self._on_take_selected(finger)
        self.takes_changed.emit()
        self._refresh_recorded_pen_pose()

    def _thumb_pen_box(self) -> tuple[np.ndarray, str]:
        """Pen box of the Thumb take selected in its panel and that take's path; warns and
        returns an empty box if there is none."""
        none = np.empty((0, 2), np.float32)
        path = self.panels["th"].take_combo.currentData()
        problem = None
        if path is None:
            problem = "No Thumb take is selected"
        else:
            try:
                corners = recorded_take_pen_pose(self.store.load(path))
            except Exception as e:
                corners, problem = None, f"Could not load the Thumb take {path}: {e}"
            if corners is None and problem is None:
                problem = (
                    f"The selected Thumb take '{os.path.splitext(os.path.basename(path))[0]}' "
                    "has no pen box"
                )
        if problem is not None:
            QtWidgets.QMessageBox.warning(
                self, "Record",
                f"{problem}, so the take keeps its own SAM pen box (if any) instead of "
                "inheriting the Thumb's.",
            )
            return none, ""
        self.node.get_logger().info(
            f"Take '{self._take_name}' inherits the pen box of Thumb take '{path}'"
        )
        return np.asarray(corners, dtype=np.float32), path

    # ---- playback -----------------------------------------------------------------------

    def toggle_play(self, finger: str) -> None:
        if finger in self._playing:
            self.stop_play(finger)
            return
        panel = self.panels[finger]
        path = panel.take_combo.currentData()
        if path is None:
            return
        try:
            take = self.store.load(path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Play", f"Could not load {path}:\n{e}")
            return
        panel.duration = take.duration
        reverse = panel.reverse
        offset = panel.bar_time()
        if reverse and offset <= 0.0:
            offset = take.duration
        elif not reverse and offset >= take.duration:
            offset = 0.0
        self.play_take(finger, take, offset, reverse)

    def play_take(
        self,
        finger: str,
        take: FingerTake,
        offset: float,
        reverse: bool = False,
        stop: float | None = None,
        touch_spans: tuple[tuple[float, float, dict], ...] = (),
        select: bool = True,
        hold_at_end: bool = False,
    ) -> bool:
        """Plays ``take`` on ``finger`` from take time ``offset`` to ``stop`` (default: its end,
        or its start in reverse), selecting it in the finger's panel. The finger is held in
        contact over the (start, end, params) ``touch_spans``. With ``hold_at_end`` it stays at
        ``stop`` (``play_reached_end`` is emitted) until ``release_end_hold``. False if it
        cannot start."""
        if finger in self._playing:
            return False
        q = self.node.latest()
        if q is None:
            QtWidgets.QMessageBox.warning(self.window(), "Play", "No leap_state received yet.")
            return False
        panel = self.panels[finger]
        if select and panel.take_combo.currentData() != take.path:
            panel.fill_takes(self.store, select=take.path)
            if self._recorded_pen_finger == finger:
                self._refresh_recorded_pen_pose()
        panel.duration = take.duration
        cols = take_columns(self.node.joint_names, take)
        tip_ids = panel.tip_plot.ids
        tip_mags = take_tip_magnitudes(take, tip_ids, self.node.counts_per_unit)
        pen_corners = recorded_take_pen_pose(take)
        if reverse:
            # Force replay holds and presses in the take's forward order.
            self.node.get_logger().info(
                f"{panel.label}: playing {take.name} in reverse; plain position replay"
            )
            force = None
            press = None
        else:
            press = self._click_press(finger, take, cols, tip_ids, q, offset)
            force = self._force_tracker(
                finger, take, tip_mags, offset,
                [(r.start, r.end) for r in press.regions] if press is not None else [],
            )
        touch = (
            self._maintain_touch(finger, take, cols, tip_mags, q, offset, reverse, touch_spans)
            if touch_spans else None
        )
        now = time.monotonic()
        with self._cmd_lock:
            self._start_commanding(q)
            self._playing[finger] = Playback(
                take=take,
                cols=cols,
                start=now,
                from_q=self._current_goal(q)[cols],
                offset=offset,
                to_q=sample_take(take, offset),
                local=offset,
                reverse=reverse,
                stop=stop,
                last_step=now,
                force=force,
                tip_ids=tip_ids,
                live_baseline=self.hand.baseline,
                tip_mags=tip_mags,
                pen_corners=pen_corners,
                touch=touch,
                press=press,
                hold_at_end=hold_at_end,
            )
        panel.take_combo.setEnabled(False)
        panel.delete_btn.setEnabled(False)
        if panel.reverse_btn is not None:
            panel.reverse_btn.setEnabled(False)
        title = f"{take.name} (reverse)" if reverse else take.name
        panel.play_btn.setText("Stop")
        panel.play_btn.setStyleSheet(STOP_STYLE)
        panel.set_playing(True)
        self._update_stiff_joints()
        self._shown_play = finger
        self.play_title.setText(f"<b>Playback</b>: {panel.label} - {title}")
        self._frame_seq = -1
        self.playing_changed.emit(finger)
        return True

    def start_probe(
        self, finger: str, take: FingerTake, probe: ClickProbe, local: float
    ) -> bool:
        """Runs ``probe`` (click setting search) on ``finger`` as a playback of ``take`` shown at
        take time ``local``; it stops once the probe is done. False if it cannot start."""
        if finger in self._playing:
            return False
        q = self.node.latest()
        if q is None:
            return False
        panel = self.panels[finger]
        cols = take_columns(self.node.joint_names, take)
        now = time.monotonic()
        with self._cmd_lock:
            self._start_commanding(q)
            from_q = self._current_goal(q)[cols]
            self._playing[finger] = Playback(
                take=take,
                cols=cols,
                start=now,
                from_q=from_q,
                offset=local,
                to_q=from_q,
                local=local,
                last_step=now,
                tip_ids=panel.tip_plot.ids,
                live_baseline=self.hand.baseline,
                probe=probe,
            )
        panel.take_combo.setEnabled(False)
        panel.delete_btn.setEnabled(False)
        panel.play_btn.setText("Stop")
        panel.play_btn.setStyleSheet(STOP_STYLE)
        panel.set_playing(True)
        self._update_stiff_joints()
        self.playing_changed.emit(finger)
        return True

    def playback(self, finger: str) -> Playback | None:
        """What ``finger`` is playing (None if nothing)."""
        return self._playing.get(finger)

    @property
    def cmd_lock(self) -> threading.Lock:
        """Held by the command thread while it changes the Playbacks (e.g. their histories)."""
        return self._cmd_lock

    def stop_play(self, finger: str) -> None:
        """Stops ``finger``'s playback; a click setting search backs off first."""
        p = self._playing.get(finger)
        if p is not None and p.probe is not None and not p.probe.done:
            p.probe.cancel()
        elif p is not None:
            self._stop_play(finger)

    def _force_tracker(
        self, finger: str, take: FingerTake, tip_mags: np.ndarray | None, offset: float,
        press_spans: list[tuple[float, float]] = (),
    ) -> ForceTracker | None:
        """Force replay of ``take`` from take time ``offset``; None (plain position replay) when
        the take has no contact phase or the live fingertip force cannot be measured. Contact
        phases overlapping a ``press_spans`` (click_press) region get force replay off."""
        log = self.node.get_logger()
        label = FINGER_LABEL[finger]
        if tip_mags is None:
            log.info(f"{label}: {take.name} has no Xela readings; plain position replay")
            return None
        force = tip_mags.sum(axis=1)
        phases = contact_phases(take.xela_t, force, take.t, take.q)
        if not phases:
            log.info(f"{label}: no contact phase in {take.name}; plain position replay")
            return None
        if self.hand.baseline is None:
            log.warn(f"{label}: no live Xela baseline (press Zero); plain position replay")
            return None
        for p in phases:
            click = f"click at {p.click:.2f} s" if p.click is not None else "no click"
            log.info(f"{label}: {take.name} contact {p.start:.2f}-{p.end:.2f} s, "
                     f"peak force {p.peak:.2f}, {click}")
        apply_click_settings(phases, take, log=lambda msg: log.info(f"{label}: {msg}"))
        defaults = ForceReplaySettings()
        for p in phases:
            if any(p.start <= end and start <= p.end for start, end in press_spans):
                p.settings = replace(p.settings or defaults, force_replay=False)
                log.info(f"{label}: contact {p.start:.2f}-{p.end:.2f} s is in a "
                         f"'{CLICK_PRESS_EVENT}' region; no force replay there")
        tracker = ForceTracker(
            phases, take.xela_t, force, len(take.joint_names), defaults,
            log=lambda msg: log.info(f"{label} force replay: {msg}"),
        )
        tracker.reset(offset)
        return tracker

    def _hand_kinematics(self) -> HandKinematics | None:
        """Fingertip kinematics from hardware joints (None if they cannot load)."""
        if self._hand_kin is None and not self._hand_kin_error:
            try:
                self._hand_kin = HandKinematics(self.node.joint_names)
            except Exception as e:
                self._hand_kin_error = str(e) or type(e).__name__
                self.node.get_logger().warn(
                    f"No fingertip kinematics, '{CLICK_PRESS_EVENT}' is off: {e}"
                )
        return self._hand_kin

    def _click_press(
        self, finger: str, take: FingerTake, cols: list[int], tip_ids: np.ndarray | None,
        q_hand: np.ndarray, offset: float,
    ) -> ClickPress | None:
        """Click press over the take's ``click_press`` regions from take time ``offset``; None
        when it has none or they cannot run (no Xela readings, recorded sim joints, live
        baseline or kinematics)."""
        spans = sorted(
            (e.t, e.end, e.params) for e in take.events
            if e.name == CLICK_PRESS_EVENT and e.end is not None and e.end > offset
        ) if self.press_settings.enabled else []
        if not spans:
            return None
        log = self.node.get_logger()
        label = FINGER_LABEL[finger]
        problem = None
        magnitudes = (
            take_tip_magnitudes(take, tip_ids, self.node.counts_per_unit)
            if tip_ids is not None else None
        )
        if magnitudes is None:
            problem = "the take has no Xela readings"
        elif len(take.sim_t) == 0:
            problem = "the take has no sim joints"
        elif self.hand.baseline is None:
            problem = "no live Xela baseline (press Zero)"
        elif self._hand_kinematics() is None:
            problem = f"no fingertip kinematics ({self._hand_kin_error})"
        if problem is not None:
            log.warn(f"{label}: {CLICK_PRESS_EVENT} off: {problem}; using the take")
            return None
        kin = self._hand_kin
        link = TIP_LINKS[finger]

        def positions_at(at: float) -> np.ndarray:
            sim_q = sample_joints(take.sim_t, take.sim_hand_q, at)
            return kin.frames_from_sim(take.sim_hand_joint_names, sim_q, link)[0][0]

        regions = []
        for start, end, params in spans:
            geometry = press_geometry(start, end, take.xela_t, magnitudes, positions_at)
            if geometry is None:
                log.warn(f"{label}: no force peak, or no fingertip motion while loading, in "
                         f"{CLICK_PRESS_EVENT} region {start:.2f}-{end:.2f} s; using the take "
                         "there")
                continue
            log.info(f"{label}: {CLICK_PRESS_EVENT} {start:.2f}-{end:.2f} s, press axis "
                     f"{np.round(geometry.axis, 3).tolist()} (loading moved "
                     f"{geometry.loading * 1000:.1f} mm), recorded force peak "
                     f"{geometry.peak:.2f}, no contact {geometry.noise:.2f}")
            regions.append(PressRegion(
                start=start, end=end, geometry=geometry,
                kin=FingerKinematics(kin, q_hand, cols, link, geometry.weights),
                params=dict(params),
                kp=np.array([REDUCED_KP_SCALE if c in REDUCED_KP_MOTORS else 1.0 for c in cols]),
            ))
        if not regions:
            return None
        press = ClickPress(
            regions, self.press_settings,
            log=lambda msg: log.info(f"{label} {CLICK_PRESS_EVENT}: {msg}"),
        )
        press.reset(offset)
        return press

    def _maintain_touch(
        self, finger: str, take: FingerTake, cols: list[int], tip_mags: np.ndarray | None,
        q_hand: np.ndarray, offset: float, reverse: bool,
        spans: tuple[tuple[float, float, dict], ...],
    ) -> TouchPress | TouchHold:
        """Maintain touch over the (start, end, params) ``spans`` of ``take``: a guarded
        approach and force hold (``TouchPress``), or the open loop ``TouchHold`` when the live
        fingertip force or the kinematics are not available."""
        log = self.node.get_logger()
        label = FINGER_LABEL[finger]

        def info(msg: str) -> None:
            log.info(f"{label} {MAINTAIN_TOUCH_EVENT}: {msg}")

        problem = None
        if self.hand.baseline is None:
            problem = "no live Xela baseline (press Zero)"
        elif len(self.panels[finger].tip_plot.ids) == 0:
            problem = "no fingertip taxels"
        elif self._hand_kinematics() is None:
            problem = f"no fingertip kinematics ({self._hand_kin_error})"
        if problem is not None:
            log.warn(f"{label}: {MAINTAIN_TOUCH_EVENT} without force feedback: {problem}; "
                     "holding the recorded pose")
            return TouchHold(
                touch_regions(spans, take.t, take.q, reverse), self.touch_settings, log=info
            )
        kin = self._hand_kin
        link = TIP_LINKS[finger]
        kp = np.array([REDUCED_KP_SCALE if c in REDUCED_KP_MOTORS else 1.0 for c in cols])
        n_taxels = len(kin.grid(link))
        regions = []
        for start, end, params in spans:
            entry, exit_ = (end, start) if reverse else (start, end)
            # Contact point: where the recorded force was on the pad over the region (its
            # middle if the take has no force there).
            weights = np.full(n_taxels, 1.0 / n_taxels)
            if tip_mags is not None and tip_mags.shape[1] == n_taxels:
                inside = (take.xela_t >= start) & (take.xela_t <= end)
                total = tip_mags[inside].sum(axis=0)
                if total.sum() > 1e-9:
                    weights = total / total.sum()
            finger_kin = FingerKinematics(kin, q_hand, cols, link, weights)
            axis, source = touch_axis(
                finger_kin, lambda t: sample_take(take, t), entry, reverse,
                (float(take.t[0]), float(take.t[-1])),
            )
            info(f"region {start:.2f}-{end:.2f} s, press axis {np.round(axis, 3).tolist()} "
                 f"from the {source}")
            regions.append(TouchPressRegion(
                entry=entry, exit=exit_, axis=axis, kin=finger_kin, params=dict(params), kp=kp,
            ))
        touch = TouchPress(regions, self.touch_settings, log=info)
        touch.reset(offset)
        return touch

    def _live_tip_spot(self, p: Playback) -> np.ndarray | None:
        """Where on the fingertip pad the live contact is: the force-weighted taxel position in
        the fingertip patch's frame (m); None without contact or Xela readings."""
        if p.press is None or not p.press.regions:
            return None
        _, readings = self.node.latest_xela()
        if readings is None or p.live_baseline is None or len(readings) <= p.tip_ids.max():
            return None
        mags = taxel_magnitudes(
            readings[None], p.live_baseline, p.tip_ids, self.node.counts_per_unit
        )[0]
        total = float(mags.sum())
        if total <= 1e-9:
            return None
        if p.pad_grid is None:
            p.pad_grid = p.press.regions[0].kin.grid
        return (mags / total) @ p.pad_grid

    def _live_tip_force(self, p: Playback) -> float | None:
        """Live fingertip force of ``p``'s finger, measured like the take's (None if unknown)."""
        _, readings = self.node.latest_xela()
        if readings is None or p.live_baseline is None or len(readings) <= p.tip_ids.max():
            return None
        return float(taxel_magnitudes(
            readings[None], p.live_baseline, p.tip_ids, self.node.counts_per_unit
        ).sum())

    def _stop_play(self, finger: str, rewind: bool = False) -> None:
        """Stops ``finger`` where it was last commanded; it then follows the hand again."""
        with self._cmd_lock:
            playback = self._playing.pop(finger)
            self.stopped[finger] = playback
            if self._last_cmd is not None and self._free is not None:
                self._free[playback.cols] = self._last_cmd[playback.cols]
            self._stop_commanding_if_idle()
        panel = self.panels[finger]
        panel.take_combo.setEnabled(True)
        panel.delete_btn.setEnabled(panel.take_combo.count() > 0)
        if panel.reverse_btn is not None:
            panel.reverse_btn.setEnabled(True)
        panel.play_btn.setText("Play")
        panel.play_btn.setStyleSheet("")
        panel.set_playing(False)
        if rewind:
            panel.set_position(playback.take.duration if playback.reverse else 0.0)
        else:
            panel.set_position(playback.local)
        self._update_stiff_joints()
        if finger == self._shown_play:
            self._shown_play = next(iter(self._playing), None)
            if self._shown_play is None:
                self._clear_playback_view()
            else:
                shown = self._playing[self._shown_play]
                title = f"{shown.take.name} (reverse)" if shown.reverse else shown.take.name
                self.play_title.setText(
                    f"<b>Playback</b>: {FINGER_LABEL[self._shown_play]} - {title}"
                )
        self._frame_seq = -1
        self.playing_changed.emit(finger)

    def _clear_playback_view(self) -> None:
        self._play_video.release()
        self.play_title.setText("<b>Playback</b>")
        self.play_camera.set_message("Press Play to see the take's camera recording")
        self.play_hand.clear()

    def close_video(self) -> None:
        self._play_video.release()

    def stop_all_playback(self) -> None:
        for finger in list(self._playing):
            self._stop_play(finger)

    def forget_take(self, path: str) -> None:
        """Stops playing the take at ``path`` (about to be deleted)."""
        for finger, playback in list(self._playing.items()):
            if playback.take.path == path:
                self._stop_play(finger, rewind=True)

    def reload_takes(self) -> None:
        """Re-lists every finger's takes and default names, e.g. after the folder changed."""
        for finger, panel in self.panels.items():
            if panel.name_edit.text() == panel.default_name:
                self._new_default_name(panel)
            panel.fill_takes(self.store)
            self._on_take_selected(finger)
        self._refresh_recorded_pen_pose()

    # ---- recorded pen pose --------------------------------------------------------------

    def _set_pose_switch(self, finger: str, on: bool) -> None:
        switch = self.panels[finger].pose_switch
        switch.blockSignals(True)
        switch.setChecked(on)
        switch.blockSignals(False)

    def _clear_recorded_pen_pose(self) -> None:
        self._recorded_pen_finger = None
        self._recorded_pen_corners = None
        self._recorded_pen_label = "recorded"
        self._frame_seq = -1

    def _load_recorded_pen_pose(self, finger: str) -> np.ndarray | None:
        path = self.panels[finger].take_combo.currentData()
        if path is None:
            return None
        try:
            take = self.store.load(path)
        except Exception as e:
            self.node.get_logger().warn(f"Could not load {path}: {e}")
            return None
        return recorded_take_pen_pose(take)

    def _on_show_recorded_pen_pose(self, finger: str, on: bool) -> None:
        """Show or hide this finger's selected recording's pen box on the live camera."""
        if not on:
            if self._recorded_pen_finger == finger:
                self._clear_recorded_pen_pose()
            return
        for other in self.panels:
            if other != finger:
                self._set_pose_switch(other, False)
        corners = self._load_recorded_pen_pose(finger)
        if corners is None:
            self._set_pose_switch(finger, False)
            self._clear_recorded_pen_pose()
            QtWidgets.QMessageBox.warning(
                self,
                "Recorded pen pose",
                f"The selected recording for {FINGER_LABEL[finger]} has no pen bounding box.",
            )
            return
        self._recorded_pen_finger = finger
        self._recorded_pen_corners = corners
        self._recorded_pen_label = f"{FINGER_LABEL[finger]} recorded"
        self._frame_seq = -1

    def _refresh_recorded_pen_pose(self) -> None:
        """Load the selected finger's recording's pen box again, if its Pose switch is on."""
        finger = self._recorded_pen_finger
        if finger is None:
            return
        corners = self._load_recorded_pen_pose(finger)
        if corners is None:
            self._set_pose_switch(finger, False)
            self._clear_recorded_pen_pose()
            return
        self._recorded_pen_corners = corners
        self._recorded_pen_label = f"{FINGER_LABEL[finger]} recorded"
        self._frame_seq = -1

    def _live_recorded_pen_pose(self) -> tuple[np.ndarray | None, str]:
        """Pen box to draw on the live camera: Pose switch, else the take being played."""
        if self._recorded_pen_corners is not None:
            return self._recorded_pen_corners, self._recorded_pen_label
        shown = self._playing.get(self._shown_play) if self._shown_play else None
        if shown is None or shown.pen_corners is None:
            return None, "recorded"
        return shown.pen_corners, f"{FINGER_LABEL[self._shown_play]} recorded"

    def _update_stiff_joints(self) -> None:
        """Playing fingers use the hand's stiff (playback) gains; the others stay compliant."""
        names = self.node.joint_names
        fingers = set(self._playing)
        joints = tuple(
            names[i] for finger, _ in FINGERS if finger in fingers
            for i in finger_indices(names, finger)
        )
        if joints != self._stiff_sent and self.node.set_stiff_joints(list(joints)):
            self._stiff_sent = joints

    def release_stiff_joints(self) -> None:
        if self._stiff_sent and self.node.set_stiff_joints([]):
            self._stiff_sent = ()

    # ---- commanding the hand ------------------------------------------------------------

    # The methods below that touch the shared state are called with ``_cmd_lock`` held.

    def _current_goal(self, measured: np.ndarray) -> np.ndarray:
        """Last commanded pose while the hand is being commanded, else the measured one."""
        return self._last_cmd if self._last_cmd is not None else measured

    def _start_commanding(self, measured: np.ndarray) -> None:
        if self._commanding:
            return
        self._free = measured.copy()
        self._last_cmd = None
        self._commanding = True

    def _stop_commanding_if_idle(self) -> None:
        if not self._playing:
            self._commanding = False
            self._last_cmd = None
            self._free = None

    def shutdown_commanding(self) -> None:
        """Ends the command thread (window closing)."""
        self._cmd_stop.set()
        self._cmd_thread.join(timeout=1.0)

    def _command_loop(self) -> None:
        """Command thread: one ``_command_step`` per period of ``settings.command_rate`` (read
        every period, so a changed rate applies at once) while fingers are playing."""
        next_t = time.monotonic()
        while not self._cmd_stop.is_set():
            period = 1.0 / self.settings.command_rate
            next_t += period
            delay = next_t - time.monotonic()
            if delay > 0:
                self._cmd_stop.wait(delay)
            elif delay < -period:  # fell behind: carry on from now instead of bursting
                next_t = time.monotonic()
            with self._cmd_lock:
                finished, reached = self._command_step() if self._commanding else ([], [])
            for finger in reached:
                self.play_reached_end.emit(finger)
            for finger in finished:
                self._play_finished.emit(finger)

    def _on_play_finished(self, finger: str) -> None:
        p = self._playing.get(finger)
        if p is not None and p.finished:  # not restarted by a seek in the meantime
            self._stop_play(finger, rewind=True)

    def in_contact(self, finger: str) -> bool:
        """``finger`` is playing and in contact with the pen: its ``maintain_touch`` holds it
        there, or its ``click_press`` is pressing."""
        p = self._playing.get(finger)
        if p is None:
            return False
        return self.in_touch_contact(finger) or (
            p.press is not None and p.press.state == CLICK_PRESSING
        )

    def in_touch_contact(self, finger: str) -> bool:
        """``finger`` is playing and its ``maintain_touch`` holds it in contact with the pen."""
        p = self._playing.get(finger)
        return p is not None and isinstance(p.touch, TouchPress) and p.touch.state == TOUCH_HOLD

    def set_touch_extra_force(self, finger: str, extra: float) -> bool:
        """Adds ``extra`` force units to ``finger``'s maintain touch hold force while it plays
        (False if it is not playing with live force feedback)."""
        with self._cmd_lock:
            p = self._playing.get(finger)
            if p is None or not isinstance(p.touch, TouchPress):
                return False
            p.touch.extra_force = float(extra)
            return True

    def fingertip_grid(self, finger: str) -> np.ndarray | None:
        """(30, 3) positions of ``finger``'s fingertip taxels on the pad (m), in the order of
        its tip plot's taxels; None without fingertip kinematics."""
        kin = self._hand_kinematics()
        return None if kin is None else kin.grid(TIP_LINKS[finger])

    def release_end_hold(self, finger: str) -> None:
        """Lets ``finger``, playing with ``hold_at_end``, finish at its end."""
        with self._cmd_lock:
            p = self._playing.get(finger)
            if p is not None:
                p.hold_at_end = False

    def _command_step(self) -> tuple[list[str], list[str]]:
        """Sends the hand command for now; returns the fingers whose take just ended and those
        that just got to their end and stay there (``hold_at_end``)."""
        now = time.monotonic()
        measured = self.node.latest()
        if measured is not None:
            pushed = np.abs(measured - self._free) > self.settings.deadband
            self._free[pushed] = measured[pushed]
        q = self._free.copy()
        finished, reached = [], []
        ramp = self.settings.ramp_s
        for finger, p in self._playing.items():
            elapsed = now - p.start
            dt, p.last_step = now - p.last_step, now
            if p.probe is not None:
                on, count = self.node.click_state()
                q[p.cols] = p.probe.step(
                    now, dt, p.from_q, on, count, self._live_tip_force(p)
                )
                if p.probe.done and not p.finished:
                    p.finished = True
                    finished.append(finger)
                continue
            if elapsed < ramp:
                a = elapsed / ramp
                q[p.cols] = (1.0 - a) * p.from_q + a * p.to_q
                local = p.offset
            else:
                if p.reverse:
                    local = max(p.offset - (elapsed - ramp - p.held_s), p.end)
                else:
                    local = min(p.offset + elapsed - ramp - p.held_s, p.end)
                q[p.cols] = sample_take(p.take, local)
                pressing = False
                if p.press is not None:
                    measured_hand = self.node.latest()
                    effort = self.node.latest_effort()
                    step = p.press.step(
                        local, dt, now, q[p.cols], measured_hand,
                        self._live_tip_force(p), self.node.click_state()[1],
                        effort[p.cols] if effort is not None else None,
                        self._live_tip_spot(p),
                    )
                    if step is not None:
                        q[p.cols] = step.q
                        pressing = True
                        if step.hold:
                            p.held_s += dt  # pressing: the take stays at ``local``
                        if step.skip_to is not None:  # pressed: go on from the region's end
                            p.held_s -= step.skip_to - local
                            local = min(step.skip_to, p.end)
                touching = pressing
                if p.touch is not None and not pressing:
                    effort = self.node.latest_effort()
                    step = p.touch.step(
                        local, dt, now, q[p.cols], self.node.latest(), self._live_tip_force(p),
                        effort[p.cols] if effort is not None else None,
                    )
                    if step is not None:
                        q[p.cols] = step.q
                        touching = True
                        if step.hold:
                            p.held_s += dt  # approaching the pen: the take stays at ``local``
                if p.force is not None and not touching:
                    if not p.force.step(local, dt, now, self._live_tip_force(p)):
                        p.held_s += dt  # held for contact or the click: stays at ``local``
                    q[p.cols] += p.force.offset_q
                if local == p.end and not p.finished:
                    if not p.hold_at_end:
                        p.finished = True
                        finished.append(finger)
                    elif not p.holding:
                        p.holding = True
                        reached.append(finger)
            p.local = local
        self.node.send_command(q)
        self._last_cmd = q
        stamp = self.node.get_clock().now().nanoseconds * 1e-9
        for p in self._playing.values():
            p.history.append((stamp, q.copy()))
            p.local_history.append((stamp, p.local))
            p.cmd_log.append((stamp, p.local, q.copy()))
        return finished, reached

    # ---- live view ----------------------------------------------------------------------

    def _update_legends(self, names: list[str]) -> None:
        if names == self._legend_names:
            return
        self._legend_names = names
        for finger, panel in self.panels.items():
            panel.legend.clear()
            for curve, i in zip(panel.curves, finger_indices(names, finger)):
                panel.legend.addItem(curve, names[i])

    def _refresh_tip_plots(self) -> None:
        """Fingertip taxel magnitudes of the last LIVE_WINDOW_S, from the live view's baseline."""
        if len(self._tip_ids) == 0:
            return
        self._tip_seq, new = self.node.xela_since(self._tip_seq)
        for stamp, readings in new:
            if len(readings) > self._tip_ids.max():
                self._tip_history.append((stamp, readings[self._tip_ids].astype(np.float32)))
        baseline = self.hand.baseline
        if not self._tip_history or baseline is None:
            if not self._tip_waiting:
                self._tip_waiting = True
                self._tip_baseline = None
                status = (
                    f"waiting for {self.node.xela_topic}" if self.node.xela_topic else "no xela_topic"
                )
                for panel in self.panels.values():
                    panel.tip_plot.clear_data(status)
            return
        self._tip_waiting = False
        if not new and baseline is self._tip_baseline:
            return
        latest = self._tip_history[-1][0]
        while self._tip_history[0][0] < latest - LIVE_WINDOW_S:
            self._tip_history.popleft()
        if self._tip_baseline is None:
            for panel in self.panels.values():
                panel.tip_plot.set_status(f"{self.node.xela_topic} live")
        self._tip_baseline = baseline
        t = np.array([s for s, _ in self._tip_history]) - latest
        readings = np.stack([r for _, r in self._tip_history])  # (N, 4 * 30, 3)
        mags = np.linalg.norm(
            (readings - baseline[self._tip_ids]) / self.node.counts_per_unit, axis=-1
        )
        per_finger = len(self._tip_ids) // len(FINGERS)
        for k, (finger, _) in enumerate(FINGERS):
            self.panels[finger].tip_plot.set_data(t, mags[:, k * per_finger: (k + 1) * per_finger])

    def _refresh_tip_demo(self) -> None:
        """Recorded fingertip magnitudes of the playing takes at the take time each command step
        sent, on the time axis of the live fingertip plots."""
        now = (
            self._tip_history[-1][0]
            if self._tip_history
            else self.node.get_clock().now().nanoseconds * 1e-9
        )
        for finger, p in self._playing.items():
            with self._cmd_lock:  # the command thread appends to it
                local_history = list(p.local_history)
            if p.tip_mags is None or not local_history:
                continue
            stamps = np.array([s for s, _ in local_history])
            local = np.array([v for _, v in local_history])
            shown = stamps >= now - LIVE_WINDOW_S
            k = np.clip(np.searchsorted(p.take.xela_t, local[shown], side="right") - 1, 0, None)
            self.panels[finger].tip_plot.set_demo_data(stamps[shown] - now, p.tip_mags[k])

    def refresh(self) -> None:
        if self.node.recording and self._rec_btn is not None:
            duration, frames = self.node.recorded_count()
            self._rec_btn.setText(f"Stop  ({duration:.1f} s, {frames} frames)")

        # Always the live camera. The SAM display frame is a still of the best detection and
        # would freeze the feed when Pose is turned off.
        seq, frame = self.node.latest_raw_frame()
        if frame is not None and seq != self._frame_seq:
            self._frame_seq = seq
            boxes = self._live_sam_boxes()
            if boxes:
                frame = overlay_sam(frame, None, boxes)  # box only: the mask lags the feed
            corners, label = self._live_recorded_pen_pose()
            if corners is not None:
                frame = draw_recorded_pen_pose(frame, corners, label)
            self.camera.set_frame(frame)

        sim_seq, sim_names, sim_q = self.node.latest_sim()
        if sim_q is not None and sim_seq != self._sim_seq:
            self._sim_seq = sim_seq
            self.hand.set_joints(sim_names, sim_q)

        xela_seq, readings = self.node.latest_xela()
        if readings is not None and xela_seq != self._xela_seq:
            self._xela_seq = xela_seq
            self.hand.set_readings(readings)
        self._refresh_tip_plots()
        self._refresh_tip_demo()

        for finger, p in self._playing.items():
            panel = self.panels[finger]
            panel.set_position(p.local)
            if p.press is not None and p.press.status:
                panel.time_label.setText(f"{panel.time_label.text()}  [{p.press.status}]")
            elif p.touch is not None and p.touch.status:
                panel.time_label.setText(
                    f"{panel.time_label.text()}  [{p.touch.status}, +{p.touch.offset:.2f} rad]"
                )
            elif p.force is not None and p.force.status:
                panel.time_label.setText(
                    f"{panel.time_label.text()}  [{p.force.status}, +{p.force.offset:.2f} rad]"
                )
        shown = self._playing.get(self._shown_play) if self._shown_play else None
        if shown is not None:
            show_take_at(shown.take, shown.local, self.play_camera, self.play_hand, self._play_video)

        names = self.node.joint_names
        self._update_legends(names)
        t, q = self.node.history()
        if len(t) == 0:
            return
        keep = t >= t[-1] - LIVE_WINDOW_S
        rel = t[keep] - t[-1]
        for finger, panel in self.panels.items():
            for curve, i in zip(panel.curves, finger_indices(names, finger)):
                curve.setData(rel, q[keep, i])
        for finger, p in self._playing.items():
            with self._cmd_lock:  # the command thread appends to it
                history = list(p.history)
            if not history:
                continue
            cmd_t = np.array([s for s, _ in history])
            cmd_q = np.stack([c for _, c in history])
            shown = cmd_t >= t[-1] - LIVE_WINDOW_S
            for curve, i in zip(self.panels[finger].demo_curves, finger_indices(names, finger)):
                curve.setData(cmd_t[shown] - t[-1], cmd_q[shown, i])


def color_swatch(color: QtGui.QColor) -> QtGui.QIcon:
    swatch = QtGui.QPixmap(12, 12)
    swatch.fill(color)
    return QtGui.QIcon(swatch)


class SpanBookmarkSlider(BookmarkSlider):
    """``BookmarkSlider`` that also shades spans (duration events) over its groove."""

    SPAN_ALPHA = 90

    def __init__(self) -> None:
        super().__init__()
        self._spans: list[tuple[int, int, QtGui.QColor, str]] = []  # (from, to, colour, tooltip)

    def set_spans(self, spans: list[tuple[int, int, QtGui.QColor, str]]) -> None:
        self._spans = spans
        self.update()

    def paintEvent(self, ev) -> None:
        super().paintEvent(ev)
        if not self._spans:
            return
        painter = QtGui.QPainter(self)
        h = self.height()
        for start, end, color, _ in self._spans:
            x0, x1 = self._mark_x(start), self._mark_x(end)
            fill = QtGui.QColor(color)
            fill.setAlpha(self.SPAN_ALPHA)
            painter.fillRect(QtCore.QRect(x0, 4, max(x1 - x0, 1), h - 8), fill)
        painter.end()

    def event(self, ev) -> bool:
        if ev.type() == QtCore.QEvent.ToolTip:
            x = ev.pos().x()
            hits = [tip for value, _, tip in self._marks if abs(self._mark_x(value) - x) <= 4]
            hits += [
                tip for start, end, _, tip in self._spans
                if self._mark_x(start) - 4 <= x <= self._mark_x(end) + 4
            ]
            if hits:
                QtWidgets.QToolTip.showText(ev.globalPos(), "\n".join(dict.fromkeys(hits)), self)
            else:
                QtWidgets.QToolTip.hideText()
                ev.ignore()
            return True
        return super().event(ev)


def click_setting_phase(phases: list[ContactPhase], t: float) -> ContactPhase | None:
    """Contact phase a ``change_click_setting`` event at take time ``t`` applies to: the one
    containing ``t``, else the next one, else the last one."""
    containing = [p for p in phases if p.start <= t <= p.end]
    if containing:
        return containing[0]
    after = [p for p in phases if p.start > t]
    if after:
        return min(after, key=lambda p: p.start)
    return max(phases, key=lambda p: p.end) if phases else None


def click_force_settings(params: dict | None) -> ForceReplaySettings:
    """Force replay values of a ``change_click_setting`` event's ``params["force"]``; the
    defaults for the ones it does not set."""
    settings = ForceReplaySettings()
    for name, default in asdict(settings).items():
        if params and name in params:
            setattr(settings, name, type(default)(params[name]))
    return settings


def apply_click_settings(
    phases: list[ContactPhase], take: FingerTake, log=lambda _: None
) -> None:
    """Gives the phases with ``change_click_setting`` events the press direction (the joints the
    user set, normalised to unit length like the computed one) and force replay values set in
    them; the other phases keep the computed direction and the default values."""
    for event in take.events:
        phase = (
            click_setting_phase(phases, event.t) if event.name == CLICK_SETTING_EVENT else None
        )
        if phase is None:
            continue
        span = f"contact {phase.start:.2f}-{phase.end:.2f} s"
        joints = event.params.get("joints") or {}
        w = np.array([float(joints.get(name, 0.0)) for name in take.joint_names])
        norm = float(np.linalg.norm(w))
        if norm > 1e-9:
            phase.direction = w / norm
            log(f"{span} presses with the set joints "
                + ", ".join(f"{n} {v:+.2f}" for n, v in zip(take.joint_names, phase.direction)))
        if "force" in event.params:
            phase.settings = click_force_settings(event.params["force"])
            log(f"{span} force replay "
                + ", ".join(f"{k} {v}" for k, v in asdict(phase.settings).items()))


@dataclass
class ClickSearch:
    """Click setting search (``click_search``) of one contact phase of ``finger``'s take, run on
    the hand through ``create_tab``'s command thread."""

    node: LeapStateListener
    create_tab: CreateTab
    finger: str
    take: FingerTake
    phase: ContactPhase

    @property
    def listening(self) -> bool:
        return bool(self.node.click_topic)

    def click_state(self) -> tuple[bool, int]:
        return self.node.click_state()

    def start(self, start_dir: np.ndarray, force: ForceReplaySettings) -> ClickProbe | str:
        """Starts the search from ``start_dir``, pressing as set in ``force``; the probe, or why
        it cannot start."""
        if self.create_tab.playback(self.finger) is not None:
            return f"{FINGER_LABEL[self.finger]} is playing; stop it first."
        if self.node.latest() is None:
            return "No leap_state received yet."
        local = max(self.phase.start - CLICK_SEARCH_LEAD_S, float(self.take.t[0]))
        label = FINGER_LABEL[self.finger]
        log = self.node.get_logger()
        probe = ClickProbe(
            sample_joints(self.take.t, self.take.q, local),
            candidate_directions(start_dir),
            force,
            ramp_s=self.create_tab.settings.ramp_s,
            peak=self.phase.peak,
            log=lambda msg: log.info(f"{label} click search: {msg}"),
        )
        log.info(f"{label} click search: {probe.total} directions from take time {local:.2f} s")
        if not self.create_tab.start_probe(self.finger, self.take, probe, local):
            return "Could not start commanding the hand."
        return probe

    def stop(self) -> None:
        """Backs the finger off and ends the search."""
        self.create_tab.stop_play(self.finger)


class ClickSettingDialog(QtWidgets.QDialog):
    """One slider (-1 to +1) per joint of the press direction force replay uses for one contact
    phase, set to the current values; the computed value and the normalised result are shown.
    Below them, the force replay values of that contact (``force``, defaults otherwise).

    A light shows the click detector (``click_topic``) live. Search (``search``) presses the
    finger along direction after direction until a click is heard and leaves those values in
    the sliders; the sliders follow the direction being tried."""

    STEPS = 100  # slider steps per unit
    LIGHT_STYLE = "border-radius: 8px; border: 1px solid #616161; background-color: {};"

    def __init__(
        self,
        parent,
        joint_names: list[str],
        computed: np.ndarray,
        current: dict | None,
        phase_text: str,
        search: ClickSearch | None = None,
        force: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self.search = search
        self._probe: ClickProbe | None = None
        self._before: dict[str, float] = {}  # slider values when the search started
        self.setWindowTitle("Change click setting")
        self.setMinimumWidth(460)
        self.joint_names = joint_names
        self.computed = computed
        text = QtWidgets.QLabel(
            f"Press direction of force replay for the contact {phase_text}.\n"
            "Each slider is how much that joint moves when force replay presses; the values are "
            "normalised, so only their ratios matter. Lower or zero a joint that slides the "
            "thumb over the pen; move it past 0 to turn it the other way."
        )
        text.setWordWrap(True)
        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("<b>Joint</b>"), 0, 0)
        grid.addWidget(QtWidgets.QLabel("<b>Contribution</b>"), 0, 1, 1, 2)
        grid.addWidget(QtWidgets.QLabel("<b>Computed</b>"), 0, 3)
        self.sliders: dict[str, QtWidgets.QSlider] = {}
        self._labels: dict[str, QtWidgets.QLabel] = {}
        for row, (name, value) in enumerate(zip(joint_names, computed), start=1):
            start = float(current.get(name, value)) if current else float(value)
            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setObjectName(name)
            slider.setRange(-self.STEPS, self.STEPS)
            slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
            slider.setTickInterval(self.STEPS // 2)
            slider.setValue(int(round(np.clip(start, -1.0, 1.0) * self.STEPS)))
            slider.setToolTip(f"Contribution of {name} to the press (computed: {value:+.2f})")
            label = QtWidgets.QLabel()
            label.setMinimumWidth(45)
            self.sliders[name] = slider
            self._labels[name] = label
            slider.valueChanged.connect(lambda _: self._update())
            grid.addWidget(QtWidgets.QLabel(name), row, 0)
            grid.addWidget(slider, row, 1)
            grid.addWidget(label, row, 2)
            grid.addWidget(QtWidgets.QLabel(f"{value:+.2f}"), row, 3)
        grid.setColumnStretch(1, 1)
        self.result_label = QtWidgets.QLabel()
        self.result_label.setWordWrap(True)
        self.force_box = self._build_force_box(click_force_settings(force))
        self.reset_btn = QtWidgets.QPushButton("Reset to computed")
        self.reset_btn.clicked.connect(self._reset)
        self.search_btn = QtWidgets.QPushButton("Search")
        self.search_btn.setObjectName("search")
        self.search_btn.clicked.connect(self._search)
        listening = search is not None and search.listening
        self.search_btn.setEnabled(listening)
        self.search_btn.setToolTip(
            "Press the finger along direction after direction, starting from these values, "
            "until the click detector hears the pen click"
            if listening else "No click topic: start the click detector (click_topic)"
        )
        self.light = QtWidgets.QLabel()
        self.light.setObjectName("click_light")
        self.light.setFixedSize(16, 16)
        self.light_label = QtWidgets.QLabel("Click" if listening else "Click (no click topic)")
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.reset_btn)
        row.addWidget(self.search_btn)
        row.addStretch(1)
        row.addWidget(self.light)
        row.addWidget(self.light_label)
        self.search_label = QtWidgets.QLabel()
        self.search_label.setWordWrap(True)
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(text)
        layout.addLayout(grid)
        layout.addWidget(self.result_label)
        layout.addWidget(self.force_box)
        layout.addLayout(row)
        layout.addWidget(self.search_label)
        layout.addWidget(self.buttons)
        self._update()
        self._set_light(False)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        if search is not None:
            self._timer.start(50)

    def _build_force_box(self, settings: ForceReplaySettings) -> QtWidgets.QGroupBox:
        self.force_check = QtWidgets.QCheckBox("Match the take's fingertip force")
        self.force_check.setToolTip(
            "During this contact, push past the recorded joints until the live fingertip force "
            "matches the recorded one; hold the take until the finger touches and until the "
            "click (needs a Zero baseline before Play)"
        )
        self.force_spins: dict[str, QtWidgets.QDoubleSpinBox] = {}
        box = QtWidgets.QGroupBox("Force replay of this contact")
        form = QtWidgets.QFormLayout(box)
        form.addRow(self.force_check)
        for name, label, minimum, maximum, step, decimals, suffix, tooltip in CLICK_FORCE_FIELDS:
            spin = double_spin(minimum, maximum, step, decimals, suffix, tooltip)
            spin.setObjectName(name)
            self.force_spins[name] = spin
            form.addRow(f"{label}:", spin)
        defaults = QtWidgets.QPushButton("Reset to defaults")
        defaults.clicked.connect(lambda: self._show_force(ForceReplaySettings()))
        form.addRow("", defaults)
        self._show_force(settings)
        return box

    def _show_force(self, settings: ForceReplaySettings) -> None:
        self.force_check.setChecked(settings.force_replay)
        for name, spin in self.force_spins.items():
            spin.setValue(getattr(settings, name))

    def force_values(self) -> dict:
        """``params["force"]`` of the event: the force replay values of this contact."""
        return {
            "force_replay": self.force_check.isChecked(),
            **{name: spin.value() for name, spin in self.force_spins.items()},
        }

    def _update(self) -> None:
        values = self.values()
        for name, value in values.items():
            self._labels[name].setText(f"{value:+.2f}")
        w = np.array(list(values.values()))
        norm = float(np.linalg.norm(w))
        self.result_label.setText(
            "Used by force replay (normalised): "
            + ", ".join(f"{n.split('_')[-1]} {v:+.2f}" for n, v in zip(values, w / norm))
            if norm > 1e-9
            else "<span style='color:#d32f2f'>All joints are 0: nothing would press.</span>"
        )

    def _reset(self) -> None:
        for name, value in zip(self.joint_names, self.computed):
            self.sliders[name].setValue(int(round(np.clip(value, -1.0, 1.0) * self.STEPS)))

    def _set_light(self, on: bool) -> None:
        self.light.setStyleSheet(self.LIGHT_STYLE.format("#43a047" if on else "#9e9e9e"))

    def _set_sliders(self, values) -> None:
        for slider, value in zip(self.sliders.values(), values):
            slider.setValue(int(round(np.clip(value, -1.0, 1.0) * self.STEPS)))

    def _set_searching(self, on: bool) -> None:
        for slider in self.sliders.values():
            slider.setEnabled(not on)
        self.reset_btn.setEnabled(not on)
        self.force_box.setEnabled(not on)
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(not on)
        self.search_btn.setText("Stop" if on else "Search")
        self.search_btn.setStyleSheet(STOP_STYLE if on else "")

    def _search(self) -> None:
        if self._probe is not None:
            self.search.stop()  # backs off; ``_tick`` finishes once the probe is done
            self.search_btn.setEnabled(False)
            return
        self._before = self.values()
        start = np.array(list(self._before.values()))
        if np.linalg.norm(start) < 1e-9:
            start = self.computed
        result = self.search.start(start, click_force_settings(self.force_values()))
        if isinstance(result, str):
            QtWidgets.QMessageBox.warning(self, "Search", result)
            return
        self._probe = result
        self._set_searching(True)

    def _tick(self) -> None:
        on, _ = self.search.click_state()
        self._set_light(on and self.search.listening)
        probe = self._probe
        if probe is None:
            return
        if not probe.done:
            if probe.found is None:
                self._set_sliders(slider_values(probe.direction))
            self.search_label.setText(
                f"Trial {probe.index + 1}/{probe.total} ({probe.angle:.0f}°): "
                f"{probe.message}, offset {probe.offset:.2f} rad"
            )
            return
        self._probe = None
        self._set_searching(False)
        self.search_btn.setEnabled(True)
        if probe.found is not None:
            self._set_sliders(slider_values(probe.found))
            self.search_label.setText(
                f"Click heard on trial {probe.index + 1}/{probe.total} ({probe.angle:.0f}° from "
                "the start); press OK to save these values."
            )
        else:
            self._set_sliders(self._before.values())
            self.search_label.setText(
                (f"Search stopped at trial {probe.index + 1}/{probe.total}"
                 if probe.cancelled else f"No click in any of the {probe.total} directions")
                + "; the sliders are back to their values before the search."
            )

    def reject(self) -> None:
        if self._probe is not None:
            self.search.stop()
        self._timer.stop()
        super().reject()

    def accept(self) -> None:
        if all(abs(v) < 1e-9 for v in self.values().values()):
            QtWidgets.QMessageBox.warning(
                self, "Change click setting", "At least one joint must contribute to the press."
            )
            return
        self._timer.stop()
        super().accept()

    def values(self) -> dict[str, float]:
        return {name: slider.value() / self.STEPS for name, slider in self.sliders.items()}


def number_edit(
    text: str, minimum: float, name: str, tooltip: str
) -> QtWidgets.QLineEdit:
    """Text box that accepts numbers of at least ``minimum`` (3 decimals)."""
    edit = QtWidgets.QLineEdit(text)
    edit.setObjectName(name)
    validator = QtGui.QDoubleValidator(minimum, 1e6, 3, edit)
    validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
    edit.setValidator(validator)
    edit.setToolTip(tooltip)
    return edit


class EditTakeEventDialog(EditEventDialog):
    """``EditEventDialog`` with duration, hold force and contact force boxes, enabled while
    ``maintain_touch`` is picked: its region can be made longer (also past ``terminal``) or
    shorter, and given its own forces (the Settings tab's values are filled in otherwise)."""

    def __init__(
        self,
        parent,
        event: TakeEvent,
        event_defs: dict[str, dict],
        color_of,
        note: str,
        force_defaults: tuple[float, float],
    ):
        super().__init__(parent, event, event_defs, color_of, note=note)
        current = event.end - event.t if event.end is not None else 0.0
        self.duration_edit = QtWidgets.QLineEdit(f"{current:.3f}")
        self.duration_edit.setObjectName("duration")
        validator = QtGui.QDoubleValidator(EVENT_TIME_RESOLUTION, 1e6, 3, self.duration_edit)
        validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        self.duration_edit.setValidator(validator)
        self.duration_edit.setToolTip(
            f"Length of the '{MAINTAIN_TOUCH_EVENT}' region in seconds, from its start at "
            f"{event.t:.2f} s (its end moves). '{EPISODE_END_EVENT}' moves if the region "
            "reaches past it"
        )
        hold = event.params.get("hold_force", force_defaults[0])
        contact = event.params.get("contact_force", force_defaults[1])
        self.hold_edit = number_edit(
            f"{hold:.3f}", 0.0, "hold_force",
            "Fingertip force held in contact over this region (the tip plots' units)",
        )
        self.contact_edit = number_edit(
            f"{contact:.3f}", 0.0, "contact_force",
            "Fingertip force that ends the approach in this region",
        )
        form = QtWidgets.QFormLayout()
        for label, edit, unit in (
            ("Duration:", self.duration_edit, "s"),
            ("Hold force:", self.hold_edit, "units"),
            ("Contact force:", self.contact_edit, "units"),
        ):
            row = QtWidgets.QHBoxLayout()
            row.addWidget(edit, 1)
            row.addWidget(QtWidgets.QLabel(unit))
            form.addRow(label, row)
        self.layout().insertLayout(1, form)  # between the text / dropdown and the buttons
        self.combo.currentIndexChanged.connect(lambda _: self._update_duration())
        self._update_duration()

    def _update_duration(self) -> None:
        on = self.name() == MAINTAIN_TOUCH_EVENT
        for edit in (self.duration_edit, self.hold_edit, self.contact_edit):
            edit.setEnabled(on)

    def accept(self) -> None:
        if self.duration_edit.isEnabled():
            problem = None
            if not self.duration_edit.hasAcceptableInput():
                problem = (
                    f"Duration must be a number of seconds of at least {EVENT_TIME_RESOLUTION:g}."
                )
            elif not (self.hold_edit.hasAcceptableInput()
                      and self.contact_edit.hasAcceptableInput()):
                problem = "Hold force and contact force must be numbers of at least 0."
            if problem is not None:
                QtWidgets.QMessageBox.warning(self, "Edit event", problem)
                return
        super().accept()

    def params(self) -> dict | None:
        """The region's hold_force / contact_force; None when the boxes are disabled."""
        if not self.hold_edit.isEnabled():
            return None
        return {
            "hold_force": float(self.hold_edit.text()),
            "contact_force": float(self.contact_edit.text()),
        }

    def duration(self) -> float | None:
        """New region length in seconds; None when the duration box is disabled."""
        if not self.duration_edit.isEnabled():
            return None
        return float(self.duration_edit.text())


class EditFingerPanel(QtWidgets.QWidget):
    """Take picker, play bar with event bookmarks, event picker + Play / Add event above the
    plot of one finger's take, with the take's events listed next to it (click to seek).

    Play asks (``play_requested``) to send the take from its ``episode_start`` to its
    ``terminal`` event to the hand; it is enabled once the take has both, in that order.

    Events with ``"length": "duration"`` in ``events.json`` take two clicks: the first marks
    where they start, the second where they end; the span is shaded on the play bar and plot.
    """

    seeked = QtCore.pyqtSignal(str)  # finger
    take_loaded = QtCore.pyqtSignal(str)  # finger, after the selected take was (re)loaded
    play_requested = QtCore.pyqtSignal(str)  # finger: start or stop Play
    replay_requested = QtCore.pyqtSignal(str)  # finger: start or stop Replay of the picked Play
    delete_requested = QtCore.pyqtSignal(str)  # path of the take, confirmed by the user

    CURSOR_PEN = pg.mkPen("#ffd600", width=1.5)
    REGION_ALPHA = 50
    PENDING_ALPHA = 30

    def __init__(
        self,
        finger: str,
        label: str,
        store: TakeStore,
        event_defs: dict[str, dict],
        counts_per_unit: float,
        touch_settings: MaintainTouchSettings,
    ) -> None:
        super().__init__()
        self.finger = finger
        self.store = store
        self.counts_per_unit = counts_per_unit
        self.touch_settings = touch_settings  # default press values of maintain_touch events
        # (take, contact phase) -> ClickSearch on the hand, set by the Edit tab.
        self.click_search: Callable[[FingerTake, ContactPhase], ClickSearch] | None = None
        self.event_defs = event_defs
        # Events this finger can be given (``applied_to`` lists finger codes such as "IF").
        self._addable = {
            name: info for name, info in event_defs.items()
            if not info.get("applied_to")
            or finger.upper() in {
                str(code).upper()
                for code in (
                    [info["applied_to"]] if isinstance(info["applied_to"], str)
                    else info["applied_to"]
                )
            }
        }
        self.take: FingerTake | None = None
        self.now = 0.0
        self._event_items: list[pg.GraphicsObject] = []  # event lines / regions on the plot
        self._marks: list[tuple[int, QtGui.QColor, str]] = []  # saved events on the play bar
        self._spans: list[tuple[int, int, QtGui.QColor, str]] = []
        self._pending: TakeEvent | None = None  # duration event whose end is not marked yet
        self._pending_items: list[pg.GraphicsObject] = []
        self._drawn_reversed = False  # the plots show the take mirrored
        self.playing = False  # the hand is playing this finger

        self.take_combo = QtWidgets.QComboBox()
        self.take_combo.setToolTip("Recorded takes of this finger, newest first")
        self.take_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.take_combo.setMinimumContentsLength(10)
        self.delete_take_btn = QtWidgets.QPushButton("Delete take")
        self.delete_take_btn.setMinimumWidth(90)
        self.delete_take_btn.setToolTip("Delete the selected take from disk")
        self.event_combo = QtWidgets.QComboBox()
        for name, info in self._addable.items():
            text = f"{name}  (duration)" if self._is_duration(name) else name
            self.event_combo.addItem(color_swatch(self._color(name)), text, name)
            self.event_combo.setItemData(
                self.event_combo.count() - 1,
                f"[{info.get('type', '')}] {info.get('description', '')}",
                QtCore.Qt.ToolTipRole,
            )
        self.play_btn = QtWidgets.QPushButton("Play")
        self.play_btn.setMinimumWidth(90)
        self.add_btn = QtWidgets.QPushButton("Add event")
        self.add_btn.setMinimumWidth(90)
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setToolTip("Discard the duration event being marked")
        self.cancel_btn.hide()
        event_buttons = QtWidgets.QHBoxLayout()
        event_buttons.addWidget(self.play_btn)
        event_buttons.addWidget(self.add_btn)
        event_buttons.addWidget(self.cancel_btn)
        self.slider = SpanBookmarkSlider()
        self.slider.setToolTip("Position in the take: drag to scrub")
        self.time_label = QtWidgets.QLabel()
        self.pose_switch = ToggleSwitch()
        self.pose_switch.setToolTip(
            "Draw this finger's selected take's pen box on the live camera, in yellow"
        )

        header = QtWidgets.QHBoxLayout()
        header.addWidget(QtWidgets.QLabel(f"<b>{label}</b>"), 1)
        header.addWidget(QtWidgets.QLabel("Pose"))
        header.addWidget(self.pose_switch)
        bar_row = QtWidgets.QHBoxLayout()
        bar_row.addWidget(self.slider, 1)
        bar_row.addWidget(self.time_label)
        controls = QtWidgets.QGridLayout()
        controls.addLayout(header, 0, 0, 1, 2)
        controls.addWidget(self.take_combo, 1, 0)
        controls.addWidget(self.delete_take_btn, 1, 1)
        controls.addWidget(self.event_combo, 2, 0)
        controls.addLayout(event_buttons, 2, 1)
        controls.addLayout(bar_row, 3, 0, 1, 2)
        self.replay_combo = QtWidgets.QComboBox()
        self.replay_combo.setToolTip(
            "Recorded Plays of this take (joints, velocities, efforts, taxels and the commands "
            "sent), newest first: <take>_<index>"
        )
        self.replay_btn = QtWidgets.QPushButton("Replay")
        self.replay_btn.setMinimumWidth(90)
        self.replay_btn.setToolTip("Send the commands of the picked Play to the hand again")
        replay_row = QtWidgets.QHBoxLayout()
        replay_row.addWidget(QtWidgets.QLabel("Plays:"))
        replay_row.addWidget(self.replay_combo, 1)
        controls.addLayout(replay_row, 4, 0)
        controls.addWidget(self.replay_btn, 4, 1)
        controls.setColumnStretch(0, 1)

        self.plot = pg.PlotWidget()
        item = self.plot.getPlotItem()
        item.showGrid(x=True, y=True, alpha=0.3)
        item.setLabel("bottom", "time", "s")
        item.setLabel("left", "position", "rad")
        self.legend = item.addLegend(offset=(5, 5))
        self.curves = [item.plot(pen=pg.mkPen(color, width=2)) for color in JOINT_COLORS]
        # While playing: the hand's measured joints (dashed) at the take time they were measured.
        self.measured_curves = [
            item.plot(pen=pg.mkPen(color, width=2, style=QtCore.Qt.DashLine))
            for color in JOINT_COLORS
        ]
        self._measured: list[tuple[float, np.ndarray]] = []  # (plot x, take joints)
        self._measured_until = -np.inf  # stamp of the last measured sample added
        self.cursor = pg.InfiniteLine(pos=0.0, angle=90, movable=True, pen=self.CURSOR_PEN)
        self.cursor.setToolTip("Drag to scrub")
        item.addItem(self.cursor, ignoreBounds=True)
        self.tip_plot = TipTaxelPlot(finger)
        self.tip_plot.setXLink(self.plot)
        self.tip_cursor = pg.InfiniteLine(pos=0.0, angle=90, movable=True, pen=self.CURSOR_PEN)
        self.tip_cursor.setToolTip("Drag to scrub")
        self.tip_plot.getPlotItem().addItem(self.tip_cursor, ignoreBounds=True)
        plots = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        plots.addWidget(self.plot)
        plots.addWidget(self.tip_plot)

        self.event_list = QtWidgets.QListWidget()
        self.event_list.setFixedWidth(180)
        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.delete_btn = QtWidgets.QPushButton("Delete")
        list_buttons = QtWidgets.QHBoxLayout()
        list_buttons.addWidget(self.edit_btn)
        list_buttons.addWidget(self.delete_btn)
        events_box = QtWidgets.QVBoxLayout()
        events_box.addWidget(QtWidgets.QLabel("Events"))
        events_box.addWidget(self.event_list, 1)
        events_box.addLayout(list_buttons)
        body = QtWidgets.QHBoxLayout()
        body.addWidget(plots, 1)
        body.addLayout(events_box)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addLayout(body, 1)

        self.take_combo.currentIndexChanged.connect(lambda _: self._load_selected())
        self.delete_take_btn.clicked.connect(self._confirm_delete_take)
        self.slider.valueChanged.connect(lambda v: self.seek(self._view(v / SLIDER_STEPS_PER_SEC)))
        self.cursor.sigPositionChanged.connect(lambda line: self.seek(self._view(line.value())))
        self.tip_cursor.sigPositionChanged.connect(
            lambda line: self.seek(self._view(line.value()))
        )
        self.play_btn.clicked.connect(lambda: self.play_requested.emit(self.finger))
        self.replay_btn.clicked.connect(lambda: self.replay_requested.emit(self.finger))
        self.replaying = False
        self.add_btn.clicked.connect(self.add_event)
        self.cancel_btn.clicked.connect(self.cancel_pending)
        self.event_combo.currentIndexChanged.connect(lambda _: self._update_buttons())
        self.edit_btn.clicked.connect(self.edit_selected_event)
        self.delete_btn.clicked.connect(self.delete_selected_event)
        self.event_list.itemClicked.connect(self._on_event_item)
        self.event_list.itemActivated.connect(self._on_event_item)
        self.event_list.itemSelectionChanged.connect(self._update_buttons)
        self._load_selected()

    def _color(self, name: str, alpha: int = 255) -> QtGui.QColor:
        color = QtGui.QColor(self.event_defs.get(name, {}).get("color", UNKNOWN_EVENT_COLOR))
        color.setAlpha(alpha)
        return color

    def _is_duration(self, name: str) -> bool:
        return self.event_defs.get(name, {}).get("length") == "duration"

    # ---- takes --------------------------------------------------------------------------

    def fill_takes(self) -> None:
        """Lists the takes of this finger, keeping the selection if it still exists."""
        keep = self.take_combo.currentData()
        self.take_combo.blockSignals(True)
        self.take_combo.clear()
        for path in self.store.list(self.finger):
            self.take_combo.addItem(os.path.splitext(os.path.basename(path))[0], path)
        index = self.take_combo.findData(keep) if keep else 0
        self.take_combo.setCurrentIndex(max(index, 0))
        self.take_combo.blockSignals(False)
        self._load_selected()

    def _confirm_delete_take(self) -> None:
        path = self.take_combo.currentData()
        if path is not None and confirm_delete_take(self, self.take_combo.currentText()):
            self.delete_requested.emit(path)

    def _load_selected(self) -> None:
        path = self.take_combo.currentData()
        previous = self.take.path if self.take is not None else None
        if path != previous:
            self._pending = None
        self.take = None
        if path is not None:
            try:
                self.take = self.store.load(path)
            except Exception as e:
                self.time_label.setText(f"<span style='color:#d32f2f'>load failed: {e}</span>")
        if self.take is None or self.take.path != previous:
            self.now = 0.0
        take = self.take
        duration = take.duration if take is not None else 0.0
        self.slider.blockSignals(True)
        self.slider.setRange(0, int(round(duration * SLIDER_STEPS_PER_SEC)))
        self.slider.blockSignals(False)
        self._draw_take()
        self.cursor.setVisible(take is not None)
        self.tip_cursor.setVisible(take is not None)
        self.event_list.setEnabled(take is not None)
        self.pose_switch.setEnabled(take is not None)
        if take is None:
            self._pending = None
            if self.pose_switch.isChecked():
                self.pose_switch.setChecked(False)
        self._update_play_lock()
        self._refresh_events()
        if take is not None:
            self.seek(self.now)
        elif path is None:
            self.time_label.setText("no takes")
        self.fill_replays()
        self.take_loaded.emit(self.finger)

    def fill_replays(self, select: str | None = None) -> None:
        """Lists the recorded Plays of the selected take, selecting ``select`` (or keeping the
        selection)."""
        keep = select or self.replay_combo.currentData()
        self.replay_combo.clear()
        if self.take is not None:
            for path in self.store.list_playbacks(self.finger, self.take.name):
                self.replay_combo.addItem(os.path.splitext(os.path.basename(path))[0], path)
        index = self.replay_combo.findData(keep) if keep else 0
        self.replay_combo.setCurrentIndex(max(index, 0))
        self._update_replay_button()

    def set_replaying(self, on: bool) -> None:
        """Replay button shows Stop while the picked Play is being replayed."""
        self.replaying = on
        self.replay_btn.setText("Stop" if on else "Replay")
        self.replay_btn.setStyleSheet(STOP_STYLE if on else "")
        self._update_replay_button()
        self._update_play_button()

    def _update_replay_button(self) -> None:
        playing = getattr(self, "playing", False)
        replaying = getattr(self, "replaying", False)
        self.replay_btn.setEnabled(replaying or (not playing and self.replay_combo.count() > 0))
        self.replay_combo.setEnabled(not playing and not replaying)

    # ---- play ---------------------------------------------------------------------------

    def is_reversed(self) -> bool:
        """The take has a ``reverse_demonstration`` event (its episode events are swapped)."""
        return self.take is not None and take_is_reversed(self.take)

    def _episode_events(self) -> tuple[TakeEvent | None, TakeEvent | None]:
        """``take_episode_events`` of the take (None, None without one)."""
        return (None, None) if self.take is None else take_episode_events(self.take)

    def episode_span(self) -> tuple[float, float] | None:
        """``take_episode_span`` of the take (None without one)."""
        return None if self.take is None else take_episode_span(self.take)

    def set_playing(self, on: bool) -> None:
        """Play button shows Stop, and the take cannot be changed or scrubbed, while playing."""
        self.playing = on
        self._update_replay_button()
        self.play_btn.setText("Stop" if on else "Play")
        self.play_btn.setStyleSheet(STOP_STYLE if on else "")
        self._measured, self._measured_until = [], -np.inf
        for curve in self.measured_curves:
            curve.setData([], [])
        self.plot.getPlotItem().setTitle(
            "solid: demonstration, dashed: measured" if on else None, size="9pt"
        )
        self._update_play_lock()
        self._update_buttons()

    def add_measured(
        self,
        stamps: np.ndarray,
        q: np.ndarray,
        cols: list[int],
        cmd_stamps: np.ndarray,
        cmd_local: np.ndarray,
    ) -> None:
        """Adds the measured hand joints ``q[:, cols]`` (at ``stamps``) newer than those shown,
        each at the take time Play had commanded then (``cmd_local`` at ``cmd_stamps``)."""
        if self.take is None or len(cmd_stamps) == 0:
            return
        new = (stamps > self._measured_until) & (stamps >= cmd_stamps[0]) & (
            stamps <= cmd_stamps[-1]
        )
        if not np.any(new):
            return
        self._measured_until = float(stamps[new][-1])
        x = self._view(np.interp(stamps[new], cmd_stamps, cmd_local))
        self._measured += zip(x.tolist(), q[new][:, cols])
        xs = np.array([v for v, _ in self._measured])
        qs = np.stack([c for _, c in self._measured])
        for j, curve in enumerate(self.measured_curves):
            if j < qs.shape[1]:
                curve.setData(xs, qs[:, j])

    def _update_play_lock(self) -> None:
        free = not self.playing
        has_take = self.take is not None
        self.take_combo.setEnabled(free)
        self.delete_take_btn.setEnabled(free and self.take_combo.currentData() is not None)
        self.slider.setEnabled(free and has_take)
        for cursor in (self.cursor, self.tip_cursor):
            cursor.setMovable(free)

    def _view(self, t: float) -> float:
        """Play bar / plot position of take time ``t``: mirrored (``duration - t``) once the
        take is reversed, so its Play runs left to right. Its own inverse."""
        return self.take.duration - t if self.is_reversed() else t

    def _view_text(self, event: TakeEvent) -> str:
        if event.end is None:
            return f"{self._view(event.t):.2f} s"
        a, b = sorted((self._view(event.t), self._view(event.end)))
        return f"{a:.2f}-{b:.2f} s"

    def _draw_take(self) -> None:
        """Joint and fingertip plots of the whole take, mirrored if it is reversed."""
        take = self.take
        self._drawn_reversed = self.is_reversed()
        self.plot.getPlotItem().setLabel(
            "bottom", "time (reversed)" if self._drawn_reversed else "time", "s"
        )
        self.legend.clear()
        for j, curve in enumerate(self.curves):
            if take is not None and j < take.q.shape[1]:
                if self._drawn_reversed:
                    curve.setData(take.duration - take.t[::-1], take.q[::-1, j])
                else:
                    curve.setData(take.t, take.q[:, j])
                self.legend.addItem(curve, take.joint_names[j])
            else:
                curve.setData([], [])
        self._show_tip_taxels()

    def _show_tip_taxels(self) -> None:
        """Fingertip taxel magnitudes over the whole take, from the take's baseline."""
        take = self.take
        if take is None:
            self.tip_plot.clear_data("")
            return
        mags = take_tip_magnitudes(take, self.tip_plot.ids, self.counts_per_unit)
        if mags is None:
            self.tip_plot.clear_data(f"no Xela readings in {take.name}")
            return
        if self._drawn_reversed:  # ascending times, for the hover lookup
            self.tip_plot.set_data(take.duration - take.xela_t[::-1], mags[::-1])
        else:
            self.tip_plot.set_data(take.xela_t, mags)
        self.tip_plot.set_status(f"{take.name} (reversed)" if self._drawn_reversed else take.name)

    # ---- position -----------------------------------------------------------------------

    def seek(self, t: float) -> None:
        if self.take is None:
            return
        self.now = float(np.clip(t, 0.0, self.take.duration))
        shown = self._view(self.now)
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(shown * SLIDER_STEPS_PER_SEC)))
        self.slider.blockSignals(False)
        for cursor in (self.cursor, self.tip_cursor):
            cursor.blockSignals(True)
            cursor.setValue(shown)
            cursor.blockSignals(False)
        reversed_ = " (reversed)" if self._drawn_reversed else ""
        self.time_label.setText(f"{shown:.2f} / {self.take.duration:.2f} s{reversed_}")
        if self._pending is not None:
            self._show_pending()
        self._update_buttons()
        self.seeked.emit(self.finger)

    # ---- events -------------------------------------------------------------------------

    @staticmethod
    def _slider_value(t: float) -> int:
        return int(round(t * SLIDER_STEPS_PER_SEC))

    def _event_line(self, t: float, color: QtGui.QColor) -> pg.InfiniteLine:
        return pg.InfiniteLine(
            pos=t, angle=90, movable=False,
            pen=pg.mkPen(color, width=1.5, style=QtCore.Qt.DashLine),
        )

    def _event_region(self, start: float, end: float, name: str, alpha: int) -> pg.LinearRegionItem:
        region = pg.LinearRegionItem(
            values=(start, end), movable=False, brush=pg.mkBrush(self._color(name, alpha)),
        )
        for line in region.lines:
            line.setPen(pg.mkPen(self._color(name), width=1.5, style=QtCore.Qt.DashLine))
        region.setZValue(-10)
        return region

    def _refresh_events(self) -> None:
        plot = self.plot.getPlotItem()
        for item in self._event_items:
            plot.removeItem(item)
        self._event_items = []
        self.event_list.clear()
        self._marks, self._spans = [], []
        if self.take is not None and self.is_reversed() != self._drawn_reversed:
            # Reverse added or deleted: mirror the plots and move the cursors.
            self._draw_take()
            self.seek(self.now)
        events = self.take.events if self.take is not None else []
        for i, event in enumerate(events, start=1):
            color = self._color(event.name)
            tip = f"{event.name} @ {self._view_text(event)}"
            if event.name == CLICK_SETTING_EVENT and event.params.get("joints"):
                tip += " (" + ", ".join(
                    f"{n.split('_')[-1]} {v:+.2f}" for n, v in event.params["joints"].items()
                ) + ")"
            if "hold_force" in event.params:
                tip += (
                    f" (hold {event.params['hold_force']:.2f}"
                    f", contact {event.params.get('contact_force', 0.0):.2f})"
                )
            elif "press_offset" in event.params:
                rate = (
                    f", +{event.params['press_rate']:.3f} rad/s"
                    if "press_rate" in event.params else ""
                )
                tip += (
                    f" (press {event.params['press_offset']:.3f}"
                    f"/{event.params.get('max_offset', 0.0):.3f} rad{rate})"
                )
            item = QtWidgets.QListWidgetItem(color_swatch(color), f"{i}. {tip}")
            item.setData(QtCore.Qt.UserRole, i - 1)
            self.event_list.addItem(item)
            if event.end is None:
                t = self._view(event.t)
                self._marks.append((self._slider_value(t), color, tip))
                plot_item = self._event_line(t, color)
            else:
                a, b = sorted((self._view(event.t), self._view(event.end)))
                self._marks.append((self._slider_value(a), color, tip))
                self._marks.append((self._slider_value(b), color, tip))
                self._spans.append((self._slider_value(a), self._slider_value(b), color, tip))
                plot_item = self._event_region(a, b, event.name, self.REGION_ALPHA)
            plot.addItem(plot_item, ignoreBounds=True)
            self._event_items.append(plot_item)
        self._show_pending()
        self._update_buttons()

    def _show_pending(self) -> None:
        """Play bar / plot with the saved events plus the duration event being marked, shaded
        from its start to the current position."""
        plot = self.plot.getPlotItem()
        for item in self._pending_items:
            plot.removeItem(item)
        self._pending_items = []
        marks, spans = list(self._marks), list(self._spans)
        p = self._pending
        if p is not None:
            color = self._color(p.name)
            first = self._view(p.t)
            start, end = sorted((first, self._view(self.now)))
            tip = f"{p.name} from {first:.2f} s (end not marked yet)"
            marks.append((self._slider_value(first), color, tip))
            spans.append((self._slider_value(start), self._slider_value(end), color, tip))
            self._pending_items = [
                self._event_region(start, end, p.name, self.PENDING_ALPHA),
                self._event_line(first, color),
            ]
            for item in self._pending_items:
                plot.addItem(item, ignoreBounds=True)
        self.slider.set_marks(marks)
        self.slider.set_spans(spans)

    def _selected_event(self) -> TakeEvent | None:
        item = self.event_list.currentItem()
        if self.take is None or item is None or not item.isSelected():
            return None
        return self.take.events[item.data(QtCore.Qt.UserRole)]

    def _update_play_button(self) -> None:
        if getattr(self, "replaying", False):
            self.play_btn.setEnabled(False)
            self.play_btn.setToolTip("Replaying a recorded Play")
            return
        if self.playing:
            self.play_btn.setEnabled(True)
            self.play_btn.setToolTip("Stop the hand")
            return
        span = self.episode_span()
        self.play_btn.setEnabled(span is not None)
        backwards = " backwards" if self.is_reversed() else ""
        later = "an earlier" if self.is_reversed() else "a later"
        self.play_btn.setToolTip(
            f"Send the take{backwards} from '{EPISODE_START_EVENT}' ({self._view(span[0]):.2f} s) "
            f"to '{EPISODE_END_EVENT}' ({self._view(span[1]):.2f} s) to the hand"
            if span is not None
            else f"Add an '{EPISODE_START_EVENT}' event and {later} '{EPISODE_END_EVENT}' "
            "event to play the take"
        )

    def _update_buttons(self) -> None:
        self._update_play_button()
        selected = self._selected_event() is not None
        self.edit_btn.setEnabled(selected and bool(self.event_defs))
        self.delete_btn.setEnabled(selected)
        p = self._pending
        self.cancel_btn.setVisible(p is not None)
        self.event_combo.setEnabled(self.take is not None and p is None)
        if self.take is None or not self.event_defs:
            self.add_btn.setText("Add event")
            self.add_btn.setEnabled(False)
            return
        if p is not None:
            self.add_btn.setText("End event")
            self.add_btn.setEnabled(True)
            self.add_btn.setToolTip(
                f"Mark the end of '{p.name}' (started at {p.t:.2f} s) at the current time"
            )
            return
        if self.event_combo.currentData() == CLICK_SETTING_EVENT and self.take.event_at(self.now) is None:
            self.add_btn.setText("Add event")
            self.add_btn.setEnabled(True)
            self.add_btn.setToolTip(
                "Set how much each joint contributes to force replay's press for the contact "
                "phase at (or after) the play bar"
            )
            return
        if self.event_combo.currentData() == REVERSE_EVENT:
            self.add_btn.setText("Reverse")
            self.add_btn.setEnabled(True)
            self.add_btn.setToolTip(
                f"Mark '{EPISODE_START_EVENT}' to '{EPISODE_END_EVENT}' as reversed and swap "
                "their times, so Play runs the take backwards"
            )
            return
        duration = self._is_duration(self.event_combo.currentData())
        self.add_btn.setText("Start event" if duration else "Add event")
        existing = self.take.event_at(self.now)
        self.add_btn.setEnabled(existing is None)
        self.add_btn.setToolTip(
            f"'{existing.name}' already starts at this time" if existing is not None
            else "Mark where the selected event starts; click again where it ends" if duration
            else f"Store the selected event at the current time in {self.take.name}.npz"
        )

    def _on_event_item(self, item: QtWidgets.QListWidgetItem) -> None:
        if self.take is not None:
            self.seek(self.take.events[item.data(QtCore.Qt.UserRole)].t)

    def _save_events(self, events: list[TakeEvent], title: str) -> bool:
        old = self.take.events
        self.take.events = events
        try:
            self.take.save()
        except Exception as e:
            self.take.events = old
            QtWidgets.QMessageBox.warning(self, title, f"Could not save {self.take.path}:\n{e}")
            return False
        self._refresh_events()
        return True

    def add_event(self) -> None:
        """Adds an instant event at the play bar, or starts / ends a duration event there."""
        if self.take is None:
            return
        if self._pending is not None:
            self._end_pending()
            return
        name = self.event_combo.currentData()
        if name is None:
            return
        if name == REVERSE_EVENT:
            self._add_reverse()
            return
        existing = self.take.event_at(self.now)
        if existing is None and name == CLICK_SETTING_EVENT:
            self._add_click_setting()
            return
        if existing is not None:
            QtWidgets.QMessageBox.information(
                self, "Add event", f"There is already a '{existing.name}' event at {existing.t:.3f} s"
            )
            return
        event = TakeEvent(
            t=self.now, name=name, type=self.event_defs[name].get("type", ""), added=time.time()
        )
        if self._is_duration(name):
            self._pending = event
            self._show_pending()
            self._update_buttons()
        elif self._save_events(self.take.events + [event], "Add event"):
            self.event_list.scrollToBottom()

    @staticmethod
    def _moved(event: TakeEvent, t: float) -> TakeEvent:
        return replace(event, t=t)

    def _fit_terminal(
        self, events: list[TakeEvent], start: float, end: float
    ) -> tuple[list[TakeEvent], str]:
        """Moves ``terminal`` to the edge of the region ``start``-``end`` when the region reaches
        past it (later in a forward take, earlier in a reversed one); returns the events and a
        note of the move ("" if none)."""
        _, terminal = self._episode_events()
        if terminal is None:
            return events, ""
        reversed_ = self.is_reversed()
        if reversed_ and start < terminal.t:
            t = start
        elif not reversed_ and end > terminal.t:
            t = end
        else:
            return events, ""
        note = (
            f"The '{MAINTAIN_TOUCH_EVENT}' region reaches past '{EPISODE_END_EVENT}', so "
            f"'{EPISODE_END_EVENT}' was moved from {self._view(terminal.t):.2f} s to "
            f"{self._view(t):.2f} s."
        )
        return [self._moved(e, t) if e is terminal else e for e in events], note

    def touch_spans(self) -> tuple[tuple[float, float, dict], ...]:
        """(start, end, params) of the take's ``maintain_touch`` regions, if this finger can
        have them; ``params`` holds a region's own hold_force / contact_force."""
        if self.take is None or MAINTAIN_TOUCH_EVENT not in self._addable:
            return ()
        return tuple(sorted(
            ((e.t, e.end, e.params) for e in self.take.events
             if e.name == MAINTAIN_TOUCH_EVENT and e.end is not None),
            key=lambda span: span[0],
        ))

    def _contact_phases(self) -> list[ContactPhase]:
        """Force replay's contact phases of the take, with their computed press directions."""
        mags = take_tip_magnitudes(self.take, self.tip_plot.ids, self.counts_per_unit)
        if mags is None:
            return []
        return contact_phases(self.take.xela_t, mags.sum(axis=1), self.take.t, self.take.q)

    def _click_dialog(self, t: float, current: dict | None) -> dict | None:
        """Asks for the press joints and force replay values of the contact phase a click
        setting at ``t`` applies to, starting from its ``current`` params; the new params
        (``joints``, ``force``), None if cancelled or the take has no contact phase."""
        title = "Change click setting"
        phases = self._contact_phases()
        phase = click_setting_phase(phases, t)
        if phase is None:
            QtWidgets.QMessageBox.warning(
                self, title,
                f"{self.take.name} has no contact phase (or no Xela readings), so force replay "
                "does not press in it.",
            )
            return None
        a, b = sorted((self._view(phase.start), self._view(phase.end)))
        current = current or {}
        dialog = ClickSettingDialog(
            self, self.take.joint_names, phase.direction, current.get("joints"),
            f"{a:.2f}-{b:.2f} s",
            search=self.click_search(self.take, phase) if self.click_search else None,
            force=current.get("force"),
        )
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return None
        return {"joints": dialog.values(), "force": dialog.force_values()}

    def _add_click_setting(self) -> None:
        phases = self._contact_phases()
        phase = click_setting_phase(phases, self.now)
        if phase is not None and any(
            e.name == CLICK_SETTING_EVENT and click_setting_phase(phases, e.t) is phase
            for e in self.take.events
        ):
            QtWidgets.QMessageBox.information(
                self, "Change click setting",
                f"This contact phase already has a '{CLICK_SETTING_EVENT}' event; edit it instead.",
            )
            return
        params = self._click_dialog(self.now, None)
        if params is None:
            return
        event = TakeEvent(
            t=self.now, name=CLICK_SETTING_EVENT,
            type=self.event_defs[CLICK_SETTING_EVENT].get("type", ""), added=time.time(),
            params=params,
        )
        if self._save_events(self.take.events + [event], "Add event"):
            self.event_list.scrollToBottom()

    def _add_reverse(self) -> None:
        """Marks ``episode_start`` to ``terminal`` with ``reverse_demonstration`` and swaps the
        two events' times."""
        title = "Reverse demonstration"
        if self.is_reversed():
            QtWidgets.QMessageBox.warning(
                self, title,
                f"{self.take.name} is already reversed. Delete its '{REVERSE_EVENT}' event to "
                "undo it.",
            )
            return
        start, end = self._episode_events()
        if start is None or end is None:
            has_start = start is not None or any(
                e.name == EPISODE_START_EVENT for e in self.take.events
            )
            missing = (
                f"'{EPISODE_START_EVENT}' and '{EPISODE_END_EVENT}' events"
                if not has_start and not any(e.name == EPISODE_END_EVENT for e in self.take.events)
                else f"an '{EPISODE_START_EVENT}' event" if not has_start
                else f"a '{EPISODE_END_EVENT}' event after '{EPISODE_START_EVENT}'"
            )
            QtWidgets.QMessageBox.warning(
                self, title,
                f"{self.take.name} needs {missing} before it can be reversed.",
            )
            return
        reverse = TakeEvent(
            t=start.t, name=REVERSE_EVENT, type=self.event_defs[REVERSE_EVENT].get("type", ""),
            added=time.time(), end=end.t,
        )
        swapped = {id(start): self._moved(start, end.t), id(end): self._moved(end, start.t)}
        events = [swapped.get(id(e), e) for e in self.take.events] + [reverse]
        if self._save_events(events, title):
            self.event_list.scrollToBottom()

    def _end_pending(self) -> None:
        p = self._pending
        start, end = sorted((p.t, self.now))
        if end - start < EVENT_TIME_RESOLUTION:
            QtWidgets.QMessageBox.information(
                self, "End event", f"Move the play bar to where '{p.name}' ends, then click again."
            )
            return
        existing = self.take.event_at(start) if start != p.t else None
        if existing is not None:
            QtWidgets.QMessageBox.information(
                self, "End event", f"There is already a '{existing.name}' event at {existing.t:.3f} s"
            )
            return
        event = TakeEvent(t=start, name=p.name, type=p.type, added=p.added, end=end)
        events = self.take.events + [event]
        moved = ""
        if p.name == MAINTAIN_TOUCH_EVENT:
            events, moved = self._fit_terminal(events, start, end)
        self._pending = None
        if self._save_events(events, "End event"):
            self.event_list.scrollToBottom()
            if moved:
                QtWidgets.QMessageBox.information(self, "Maintain touch", moved)
        else:
            self._pending = p
            self._show_pending()
            self._update_buttons()

    def cancel_pending(self) -> None:
        self._pending = None
        self._show_pending()
        self._update_buttons()

    def edit_selected_event(self) -> None:
        event = self._selected_event()
        if event is None:
            return
        if event.name == REVERSE_EVENT:
            QtWidgets.QMessageBox.information(
                self, "Edit event", f"Delete '{REVERSE_EVENT}' to undo the reverse instead."
            )
            return
        if event.name == CLICK_SETTING_EVENT:
            row = self.event_list.currentRow()
            params = self._click_dialog(event.t, event.params)
            if params is not None and self._save_events(
                [replace(e, params={**e.params, **params}) if e is event else e
                 for e in self.take.events],
                "Edit event",
            ):
                self.event_list.setCurrentRow(row)
            return
        # Only events of the same length, so an instant event never gets (or loses) an end.
        same_length = {
            name: info for name, info in self._addable.items()
            if self._is_duration(name) == (event.end is not None)
            and name not in (REVERSE_EVENT, CLICK_SETTING_EVENT)
        }
        a, b = (self._view(event.t), None) if event.end is None else sorted(
            (self._view(event.t), self._view(event.end))
        )
        shown = replace(event, t=a, end=b)
        dialog = EditTakeEventDialog(
            self, shown, same_length, self._color, note=f"{self.take.name}.npz will be updated.",
            force_defaults=(self.touch_settings.hold_force, self.touch_settings.contact_force),
        )
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        name = dialog.name()
        duration = dialog.duration()
        params = dialog.params()
        params = event.params if params is None else {**event.params, **params}
        start, end = event.t, event.end
        if duration is not None:
            # The region keeps its left edge on the play bar and grows / shrinks to the right.
            if self.is_reversed():
                start = event.end - duration
            else:
                end = event.t + duration
        if name == event.name and (start, end) == (event.t, event.end) and params == event.params:
            return
        row = self.event_list.currentRow()
        renamed = TakeEvent(
            t=start, name=name, type=self.event_defs[name].get("type", ""),
            added=event.added, end=end, params=params,
        )
        events = [renamed if e is event else e for e in self.take.events]
        moved = ""
        if name == MAINTAIN_TOUCH_EVENT:
            events, moved = self._fit_terminal(events, renamed.t, renamed.end)
        if self._save_events(events, "Edit event"):
            self.event_list.setCurrentRow(row)
            if moved:
                QtWidgets.QMessageBox.information(self, "Maintain touch", moved)

    def delete_selected_event(self) -> None:
        event = self._selected_event()
        if event is None:
            return
        undo = (
            f"\n'{EPISODE_START_EVENT}' and '{EPISODE_END_EVENT}' get their times back."
            if event.name == REVERSE_EVENT else ""
        )
        answer = QtWidgets.QMessageBox.warning(
            self,
            "Delete event",
            f"Delete '{event.name}' at {self._view_text(event)} from {self.take.name}.npz?{undo}\n"
            "This cannot be undone.",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )
        if answer != QtWidgets.QMessageBox.Ok:
            return
        events = [e for e in self.take.events if e is not event]
        if event.name == REVERSE_EVENT and event.end is not None:
            # Swapped by ``_add_reverse``: episode_start sits at the span's end, terminal at its start.
            tol = EVENT_TIME_RESOLUTION
            events = [
                self._moved(e, event.t) if e.name == EPISODE_START_EVENT and abs(e.t - event.end) < tol
                else self._moved(e, event.end) if e.name == EPISODE_END_EVENT and abs(e.t - event.t) < tol
                else e
                for e in events
            ]
        self._save_events(events, "Delete event")


class EditTab(QtWidgets.QWidget):
    """Same layout as the Create tab, for labelling recorded takes with events.

    Each finger picks one of its takes; the plot shows the whole take and the play bar / plot
    cursor scrub through it. The Recording column shows the take's camera and FK taxels at the
    position of the finger last scrubbed; the Live column next to it shows the live camera and
    FK taxels. Events from ``events.json`` are added at the play bar position and saved in the
    finger's take as ``events``. Delete take removes the selected take from disk after a
    confirmation. Play sends the take from its ``episode_start`` to its ``terminal`` event to
    the hand through ``create_tab`` (the play bar follows it), and a finger's Pose switch draws
    its take's pen box on the live camera.
    """

    delete_requested = QtCore.pyqtSignal(str)  # path of the take

    def __init__(
        self,
        node: LeapStateListener,
        store: TakeStore,
        event_defs: dict[str, dict],
        create_tab: CreateTab,
    ) -> None:
        super().__init__()
        self.node = node
        self.store = store
        self.create_tab = create_tab
        counts_per_unit = node.counts_per_unit
        self._video = TakeVideo()
        self._frame_seq = 0
        self._sim_seq = 0
        self._xela_seq = 0
        self._pose_finger: str | None = None  # finger whose Pose switch is on
        self._pose_corners: np.ndarray | None = None  # (4, 2) its take's pen box
        # Plays being recorded, by finger: take, replay_of, start time and live baseline.
        self._play_recs: dict[str, dict] = {}

        grid = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        self.panels: dict[str, EditFingerPanel] = {}
        for n, (finger, label) in enumerate(FINGERS):
            panel = EditFingerPanel(
                finger, label, store, event_defs, counts_per_unit, create_tab.touch_settings
            )
            self.panels[finger] = panel
            grid_layout.addWidget(panel, n // 2, n % 2)
            panel.seeked.connect(self._show)
            panel.delete_requested.connect(self.delete_requested)
            panel.play_requested.connect(self._toggle_play)
            panel.replay_requested.connect(self._toggle_replay)
            panel.take_loaded.connect(self._on_take_loaded)
            panel.pose_switch.toggled.connect(lambda on, f=finger: self._on_pose(f, on))
            panel.click_search = functools.partial(ClickSearch, node, create_tab, finger)
        create_tab.playing_changed.connect(self._on_playing_changed)

        self.camera = CameraView("")
        self.camera.set_message("Scrub a take to see its camera recording")
        self.hand = HandView(
            "", "", counts_per_unit,
            waiting="Scrub a take to see its taxels",
            no_xela="Scrub a take to see its Xela readings",
        )
        self.live_camera = CameraView(node.image_topic)
        self.live_hand = HandView(node.sim_topic, node.xela_topic, counts_per_unit)
        # One no-contact baseline for both live views: force replay reads the Create tab's.
        self.live_hand.zero_btn.clicked.connect(create_tab.hand._zero)
        create_tab.hand.zero_btn.clicked.connect(self.live_hand._zero)
        sides = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        sides.addWidget(side_column(QtWidgets.QLabel("<b>Recording</b>"), self.camera, self.hand))
        sides.addWidget(side_column(QtWidgets.QLabel("<b>Live</b>"), self.live_camera, self.live_hand))
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(grid)
        splitter.addWidget(sides)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        hint = QtWidgets.QLabel(
            "Pick a take per finger, scrub with the play bar or the yellow cursor, then add the "
            "selected event at that time (duration events: click once at the start, once at the "
            "end). Click an event in a list to jump to it. Play sends the take from "
            f"'{EPISODE_START_EVENT}' to '{EPISODE_END_EVENT}' to the hand."
            if event_defs
            else "<span style='color:#d32f2f'>No event definitions loaded (events_file).</span>"
        )
        hint.setWordWrap(True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(splitter, 1)
        self.refresh_takes()

    def refresh_takes(self) -> None:
        for panel in self.panels.values():
            panel.fill_takes()

    def _show(self, finger: str) -> None:
        """Camera frame and FK taxels of ``finger``'s take at its play bar position."""
        panel = self.panels[finger]
        if panel.take is not None:
            show_take_at(panel.take, panel.now, self.camera, self.hand, self._video)

    # ---- play ---------------------------------------------------------------------------

    def _toggle_play(self, finger: str) -> None:
        if self.create_tab.playback(finger) is not None:
            self.create_tab.stop_play(finger)
            return
        self._start_play(finger)

    def _start_play(
        self, finger: str, hold_at_end: bool = False, start: float | None = None
    ) -> bool:
        """Plays the episode of ``finger``'s take on the hand, from ``start`` (default:
        ``episode_start``) to ``terminal``; False if it cannot start. With ``hold_at_end`` the
        finger stays held in contact at ``terminal`` (its last ``maintain_touch`` region
        stretched to it) until ``release_end_hold``."""
        panel = self.panels[finger]
        span = panel.episode_span()
        if panel.take is None or span is None:
            return False
        start, end = (span[0] if start is None else start), span[1]
        spans = panel.touch_spans()
        if hold_at_end:
            spans = touch_spans_to_end(spans, start, end)
        self._start_play_recording(finger, panel.take)
        if not self.create_tab.play_take(
            finger, panel.take, start, reverse=end < start, stop=end,
            touch_spans=spans, hold_at_end=hold_at_end,
        ):
            self._cancel_play_recording(finger)
            return False
        return True

    def play_episode(
        self, finger: str, path: str, hold_at_end: bool = False, start: float | None = None
    ) -> bool:
        """Selects take ``path`` in ``finger``'s panel and plays its episode as the panel's Play
        does (``hold_at_end``, ``start``: see ``_start_play``); False if the finger is busy or
        the take cannot be played."""
        if self.create_tab.playback(finger) is not None:
            return False
        panel = self.panels[finger]
        index = panel.take_combo.findData(path)
        if index < 0:
            panel.fill_takes()
            index = panel.take_combo.findData(path)
        if index < 0:
            return False
        panel.take_combo.setCurrentIndex(index)  # loads it
        return (
            panel.take is not None and panel.take.path == path
            and self._start_play(finger, hold_at_end, start)
        )

    def _toggle_replay(self, finger: str) -> None:
        """Replays the commands of the Play picked in ``finger``'s dropdown (or stops it)."""
        if self.create_tab.playback(finger) is not None:
            self.create_tab.stop_play(finger)
            return
        panel = self.panels[finger]
        path = panel.replay_combo.currentData()
        if panel.take is None or path is None:
            return
        try:
            rec = PlaybackRecording.load(path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Replay", f"Could not load {path}:\n{e}")
            return
        if len(rec.cmd_t) < 2:
            QtWidgets.QMessageBox.warning(self, "Replay", f"{rec.name} has no commands.")
            return
        cols = rec.cols
        take = FingerTake(
            finger=finger,
            path=rec.path,
            t=rec.cmd_t - rec.cmd_t[0],
            q=rec.cmd_q[:, cols],
            joint_names=[rec.joint_names[c] for c in cols],
            hand_q=rec.cmd_q,
            hand_joint_names=list(rec.joint_names),
        )
        self._start_play_recording(finger, panel.take, replay_of=rec.path)
        panel.set_replaying(True)
        # No events and no Xela in the replayed take: plain position replay of the commands.
        if not self.create_tab.play_take(finger, take, 0.0, select=False):
            panel.set_replaying(False)
            self._cancel_play_recording(finger)

    def _start_play_recording(
        self, finger: str, take: FingerTake, replay_of: str = ""
    ) -> None:
        self._play_recs[finger] = {
            "take": take,
            "replay_of": replay_of,
            "t0": self.node.get_clock().now().nanoseconds * 1e-9,
            "baseline": self.create_tab.hand.baseline,
        }
        self.node.start_play_recording(finger)

    def _cancel_play_recording(self, finger: str) -> None:
        self._play_recs.pop(finger, None)
        self.node.stop_play_recording(finger)

    def _save_play_recording(self, finger: str) -> None:
        """Saves the Play of ``finger`` that just stopped as ``<take>_<n>``."""
        info = self._play_recs.pop(finger, None)
        buffers = self.node.stop_play_recording(finger)
        playback = self.create_tab.stopped.get(finger)
        if info is None or buffers is None or playback is None or len(playback.cmd_log) < 2:
            return
        log = self.node.get_logger()
        t0 = info["t0"]
        take: FingerTake = info["take"]
        cmd_t = np.array([c[0] for c in playback.cmd_log]) - t0
        if cmd_t[-1] - cmd_t[0] < MIN_PLAY_RECORDING_S:
            log.info(f"{FINGER_LABEL[finger]}: Play shorter than {MIN_PLAY_RECORDING_S} s, "
                     "not saved")
            return
        state, xela = buffers["state"], buffers["xela"]
        empty16 = np.empty((0, NUM_JOINTS))
        baseline = info["baseline"]
        rec = PlaybackRecording(
            path=self.store.new_playback_path(finger, take.name),
            take=take.path,
            finger=finger,
            joint_names=self.node.joint_names,
            cols=list(playback.cols),
            cmd_t=cmd_t,
            cmd_q=np.stack([c[2] for c in playback.cmd_log]),
            cmd_local=np.array([c[1] for c in playback.cmd_log]),
            state_t=np.array([x[0] for x in state]) - t0 if state else np.empty(0),
            position=np.stack([x[1] for x in state]) if state else empty16,
            velocity=np.stack([x[2] for x in state]) if state else empty16,
            effort=np.stack([x[3] for x in state]) if state else empty16,
            xela_t=np.array([x[0] for x in xela]) - t0 if xela else np.empty(0),
            xela=np.stack([x[1] for x in xela]) if xela else np.empty((0, 0, 3), np.float32),
            xela_baseline=baseline if baseline is not None else np.empty((0, 3)),
            click_t=np.array(buffers["clicks"]) - t0,
            meta={
                "take": take.name,
                "replay_of": info["replay_of"],
                "ended": "finished" if playback.finished else "stopped",
                "take_start": float(playback.offset),
                "take_end": float(playback.end),
                "reverse": bool(playback.reverse),
                "click_press": asdict(self.create_tab.press_settings),
                "maintain_touch": asdict(self.create_tab.touch_settings),
                "hold": asdict(self.create_tab.settings),
                "click_press_trace": playback.press.trace if playback.press is not None else [],
                "maintain_touch_trace": playback.touch.trace if playback.touch is not None else [],
            },
        )
        try:
            rec.save()
        except Exception as e:
            log.warn(f"Could not save the Play recording {rec.path}: {e}")
            return
        log.info(f"{FINGER_LABEL[finger]}: saved the Play as {rec.path} ({len(cmd_t)} commands, "
                 f"{len(state)} joint states, {len(xela)} Xela readings, "
                 f"{len(buffers['clicks'])} clicks)")
        self.panels[finger].fill_replays(select=rec.path)

    def _on_playing_changed(self, finger: str) -> None:
        panel = self.panels[finger]
        playing = self.create_tab.playback(finger) is not None
        if panel.replaying:
            if not playing:
                panel.set_replaying(False)
        else:
            panel.set_playing(playing)
        if not playing and finger in self._play_recs:
            self._save_play_recording(finger)
        self._frame_seq = -1

    # ---- pose ---------------------------------------------------------------------------

    def _on_pose(self, finger: str, on: bool) -> None:
        """Show or hide ``finger``'s take's pen box on the live camera (one finger at a time)."""
        self._frame_seq = -1
        if not on:
            if self._pose_finger == finger:
                self._pose_finger, self._pose_corners = None, None
            return
        for other, panel in self.panels.items():
            if other != finger and panel.pose_switch.isChecked():
                panel.pose_switch.blockSignals(True)
                panel.pose_switch.setChecked(False)
                panel.pose_switch.blockSignals(False)
        take = self.panels[finger].take
        corners = recorded_take_pen_pose(take) if take is not None else None
        if corners is None:
            switch = self.panels[finger].pose_switch
            switch.blockSignals(True)
            switch.setChecked(False)
            switch.blockSignals(False)
            self._pose_finger, self._pose_corners = None, None
            QtWidgets.QMessageBox.warning(
                self,
                "Recorded pen pose",
                f"The selected take for {FINGER_LABEL[finger]} has no pen bounding box.",
            )
            return
        self._pose_finger, self._pose_corners = finger, corners

    def _on_take_loaded(self, finger: str) -> None:
        """A finger's take changed: reload its pen box if its Pose switch is on."""
        if self._pose_finger == finger and self.panels[finger].pose_switch.isChecked():
            self._on_pose(finger, True)

    def _live_pen_pose(self) -> tuple[np.ndarray | None, str]:
        """Pen box to draw on the live camera: Pose switch, else a take being played."""
        if self._pose_corners is not None:
            return self._pose_corners, f"{FINGER_LABEL[self._pose_finger]} recorded"
        for finger, label in FINGERS:
            p = self.create_tab.playback(finger)
            if p is not None and p.pen_corners is not None:
                return p.pen_corners, f"{label} recorded"
        return None, "recorded"

    # ---- live view ----------------------------------------------------------------------

    def refresh(self) -> None:
        """Live camera and FK taxels, and the play bars of the takes being played."""
        if not self.isVisible():
            return
        stamps, q = self.node.history()
        for finger, panel in self.panels.items():
            p = self.create_tab.playback(finger)
            if p is not None and panel.take is not None and p.take.path == panel.take.path:
                if abs(p.local - panel.now) > 1e-6:
                    panel.seek(p.local)
                with self.create_tab.cmd_lock:  # the command thread appends to it
                    local_history = list(p.local_history)
                if local_history and len(stamps):
                    panel.add_measured(
                        stamps, q, take_columns(self.node.joint_names, p.take),
                        np.array([t for t, _ in local_history]),
                        np.array([local for _, local in local_history]),
                    )

        seq, frame = self.node.latest_raw_frame()
        if frame is not None and seq != self._frame_seq:
            self._frame_seq = seq
            corners, label = self._live_pen_pose()
            if corners is not None:
                frame = draw_recorded_pen_pose(frame, corners, label)
            self.live_camera.set_frame(frame)

        sim_seq, sim_names, sim_q = self.node.latest_sim()
        if sim_q is not None and sim_seq != self._sim_seq:
            self._sim_seq = sim_seq
            self.live_hand.set_joints(sim_names, sim_q)

        xela_seq, readings = self.node.latest_xela()
        if readings is not None and xela_seq != self._xela_seq:
            self._xela_seq = xela_seq
            self.live_hand.set_readings(readings)

    def forget_take(self, path: str) -> None:
        """Stops showing the take at ``path`` (about to be deleted)."""
        if self.hand.take_path == path:
            self._video.release()
            self.hand.clear()
            self.camera.set_message("Scrub a take to see its camera recording")

    def close_video(self) -> None:
        self._video.release()


def raise_x11_window(title: str) -> bool:
    """Brings the X11 window titled ``title`` to the front, asking the window manager as a pager
    would so focus stealing prevention does not refuse it. False if the window is not found or
    X11 / python-xlib is not available."""
    try:
        from Xlib import X, display, protocol
    except ImportError:
        return False
    try:
        d = display.Display()
    except Exception:
        return False
    try:
        root = d.screen().root
        clients = root.get_full_property(d.intern_atom("_NET_CLIENT_LIST"), X.AnyPropertyType)
        net_name, utf8 = d.intern_atom("_NET_WM_NAME"), d.intern_atom("UTF8_STRING")
        for wid in clients.value if clients else []:
            window = d.create_resource_object("window", wid)
            prop = window.get_full_property(net_name, utf8)
            name = prop.value.decode(errors="replace") if prop else (window.get_wm_name() or "")
            if name != title:
                continue
            event = protocol.event.ClientMessage(
                window=window,
                client_type=d.intern_atom("_NET_ACTIVE_WINDOW"),
                data=(32, [2, X.CurrentTime, 0, 0, 0]),  # 2: request from a pager
            )
            root.send_event(
                event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask
            )
            d.flush()
            return True
        return False
    except Exception:
        return False
    finally:
        d.close()


def move_to_pose_take(
    take: FingerTake, q_from: np.ndarray, q_to: np.ndarray
) -> FingerTake:
    """A take moving ``take``'s finger from joints ``q_from`` to ``q_to`` (``take.joint_names``
    order) along an S-curve (cosine) no faster than START_MOVE_SPEED, over START_MOVE_MIN_S at
    least."""
    q_from, q_to = np.asarray(q_from, dtype=float), np.asarray(q_to, dtype=float)
    distance = float(np.max(np.abs(q_to - q_from))) if len(q_to) else 0.0
    duration = max(np.pi / 2 * distance / START_MOVE_SPEED, START_MOVE_MIN_S)
    t = np.linspace(0.0, duration, max(int(duration * 50), 2))
    s = 0.5 - 0.5 * np.cos(np.pi * t / duration)
    q = q_from + s[:, None] * (q_to - q_from)
    return FingerTake(
        finger=take.finger, path=f"move to the start of {take.name}", t=t, q=q,
        joint_names=list(take.joint_names), hand_q=np.zeros((len(t), NUM_JOINTS)),
        hand_joint_names=list(take.hand_joint_names),
    )


def touch_spans_to_end(
    spans: tuple[tuple[float, float, dict], ...], start: float, end: float
) -> tuple[tuple[float, float, dict], ...]:
    """``spans`` (``maintain_touch`` (start, end, params)) with the one Play from ``start`` to
    ``end`` (backwards if ``end < start``) passes last stretched to ``end``, so the finger is
    still held in contact there. Only regions overlapping the episode count; unchanged if none."""
    lo, hi = min(start, end), max(start, end)
    inside = [k for k, (a, b, _) in enumerate(spans) if b >= lo and a <= hi]
    if not inside:
        return spans
    out = list(spans)
    if end < start:  # backwards: the region with the lowest start comes last
        k = min(inside, key=lambda i: spans[i][0])
        a, b, params = spans[k]
        out[k] = (min(a, end), b, params)
    else:
        k = max(inside, key=lambda i: spans[i][1])
        a, b, params = spans[k]
        out[k] = (a, max(b, end), params)
    return tuple(out)


def save_wav(path: str, samples: np.ndarray, rate: int) -> None:
    """Writes mono float ``samples`` in [-1, 1] as a 16-bit WAV."""
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(int(rate))
        f.writeframes(pcm.tobytes())


def play_list_text(path: str) -> str:
    """Hand plays list entry: name, length and how it ended; when, and the slips."""
    name = os.path.splitext(os.path.basename(path))[0]
    when = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%m-%d %H:%M")
    try:
        with np.load(path, allow_pickle=False) as data:  # only the small entries are read
            meta = json.loads(str(data["meta"])) if "meta" in data.files else {}
            cmd_t = data["cmd_t"] if "cmd_t" in data.files else np.empty(0)
    except Exception:
        return f"{name}  {when}  (unreadable)"
    duration = float(cmd_t[-1] - cmd_t[0]) if len(cmd_t) > 1 else 0.0
    slips = len(meta.get("slips", []))
    slip_text = f", {slips} slip{'s' if slips != 1 else ''}" if slips else ""
    return f"{name}  {duration:.1f} s, {meta.get('ended', '?')}\n{when}{slip_text}"


def play_details_html(rec: PlaybackRecording) -> str:
    """Details of a Play on hand recording for the Hand plays panel."""
    meta = rec.meta
    when = datetime.fromtimestamp(os.path.getmtime(rec.path)).strftime("%Y-%m-%d %H:%M:%S")
    rows = [
        ("Recorded", when),
        ("Length", f"{rec.duration:.1f} s"),
        ("Ended", meta.get("ended", "?")),
    ]
    spans = meta.get("episodes", {})
    for finger, take in meta.get("takes", {}).items():
        span = spans.get(finger)
        played = f" ({span[0]:.2f} -> {span[1]:.2f} s)" if span else ""
        rows.append((FINGER_LABEL.get(finger, finger),
                     os.path.splitext(os.path.basename(take))[0] + played))
    rows += [
        ("Joint states", f"{len(rec.state_t)} (position, velocity, effort)"),
        ("Xela readings", f"{len(rec.xela_t)}" + (" (no Zero baseline)"
                                                  if len(rec.xela_baseline) == 0 else "")),
        ("Commands", str(len(rec.cmd_t))),
        ("Clicks", str(len(rec.click_t))),
        ("Camera", f"{len(rec.video_t)} frames" if rec.video else "none"),
        ("Audio", os.path.basename(rec.audio) if rec.audio else "none"),
    ]
    slips = meta.get("slips", [])
    by_finger = {}
    for e in slips:
        by_finger[e["finger"]] = by_finger.get(e["finger"], 0) + 1
    rows.append(("Slips", ", ".join(f"{f.upper()} {n}" for f, n in by_finger.items()) or "none"))
    avoid = meta.get("avoid_slip", {})
    extra = meta.get("avoid_slip_extra", {})
    if avoid:
        rows.append(("Avoid slip", "on" if avoid.get("enabled") else "off"))
        if extra:
            rows.append(
                ("Extra force", ", ".join(f"{f.upper()} +{v:.1f}" for f, v in extra.items()))
            )
    html = "<table cellspacing='2'>" + "".join(
        f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in rows
    ) + "</table>"
    events = [(e["t"], f"{FINGER_LABEL.get(e['finger'], e['finger'])} {e['event']}")
              for e in meta.get("timeline", [])]
    events += [(e["t"], f"{FINGER_LABEL.get(e['finger'], e['finger'])} slip ({e['cue']})")
               for e in slips]
    if events:
        html += "<p><b>Timeline</b><br>" + "<br>".join(
            f"{t:7.2f} s &nbsp; {text}" for t, text in sorted(events)
        ) + "</p>"
    html += f"<p style='color:#757575'>{rec.path}</p>"
    return html


def pair_text(pairs) -> str:
    """Finger pairs as "IF-MF, TH-IF"."""
    return ", ".join(f"{a.upper()}-{b.upper()}" for a, b in sorted(pairs))


def pen_box_key(corners: np.ndarray) -> bytes:
    """Identity of a pen box: equal only for exactly the same corners."""
    return np.ascontiguousarray(corners, dtype=np.float32).tobytes()


def take_first_frame(take: FingerTake, video: TakeVideo) -> np.ndarray | None:
    """First camera frame of ``take``, or None if it has no readable recording."""
    if not (take.video and len(take.video_t) and os.path.exists(take.video)):
        return None
    video.release()  # always re-open so frame 0 is read even if it was the last one shown
    return video.read(take.video, 0)


class BoxFingerColumn(QtWidgets.QGroupBox):
    """Edited takes of one finger with the selected pen box: a list and their joints over time
    (all takes faint, the selected one in color with its events and episode marked)."""

    take_selected = QtCore.pyqtSignal(object)  # FingerTake

    def __init__(self, finger: str, event_defs: dict[str, dict]) -> None:
        super().__init__(FINGER_LABEL[finger])
        self.finger = finger
        self.event_defs = event_defs
        self._takes: list[FingerTake] = []
        self.list = QtWidgets.QListWidget()
        self.list.setMaximumHeight(110)
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel("bottom", "time", "s")
        self.legend = self.plot.addLegend(offset=(5, 5))
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addWidget(self.plot, 1)
        self.list.currentRowChanged.connect(self._on_row)

    def set_takes(self, takes: list[FingerTake]) -> None:
        """Lists ``takes``, keeping the selected one if it is still among them."""
        keep = self.selected_take()
        keep_path = keep.path if keep is not None else None
        self._takes = takes
        self.setTitle(f"{FINGER_LABEL[self.finger]} - {len(takes)} take(s)")
        self.list.blockSignals(True)
        self.list.clear()
        for take in takes:
            start, end = take_episode_span(take)
            direction = ", reversed" if end < start else ""
            random = "".join(
                f", random start {a:.2f}-{b:.2f} s" for a, b in random_start_regions(take)
            )
            self.list.addItem(
                f"{take.name}  (episode {min(start, end):.2f}-{max(start, end):.2f} s{direction}"
                f"{random}, {len(take.events)} events)"
            )
        paths = [take.path for take in takes]
        row = paths.index(keep_path) if keep_path in paths else 0 if takes else -1
        self.list.setCurrentRow(row)
        self.list.blockSignals(False)
        self._draw()

    def selected_take(self) -> FingerTake | None:
        row = self.list.currentRow()
        return self._takes[row] if 0 <= row < len(self._takes) else None

    def _on_row(self, row: int) -> None:
        self._draw()
        if 0 <= row < len(self._takes):
            self.take_selected.emit(self._takes[row])

    def _draw(self) -> None:
        self.plot.clear()
        self.legend.clear()
        selected = self.list.currentRow()
        faint = pg.mkPen((150, 150, 150, 90), width=1)
        for i, take in enumerate(self._takes):
            if i != selected:
                for j in range(take.q.shape[1]):
                    self.plot.plot(take.t, take.q[:, j], pen=faint)
        if 0 <= selected < len(self._takes):
            take = self._takes[selected]
            for j, color in zip(range(take.q.shape[1]), JOINT_COLORS):
                curve = self.plot.plot(take.t, take.q[:, j], pen=pg.mkPen(color, width=2))
                self.legend.addItem(curve, take.joint_names[j])
            start, end = take_episode_span(take)
            episode = pg.LinearRegionItem(
                (min(start, end), max(start, end)), movable=False,
                brush=pg.mkBrush(100, 100, 255, 35),
            )
            episode.setZValue(-10)
            self.plot.addItem(episode)
            # Labels at staggered heights so events close together stay readable.
            for k, event in enumerate(sorted(take.events, key=lambda e: e.t)):
                color = QtGui.QColor(
                    self.event_defs.get(event.name, {}).get("color", UNKNOWN_EVENT_COLOR)
                )
                if event.end is not None and event.name != REVERSE_EVENT:
                    shade = QtGui.QColor(color)
                    shade.setAlpha(45)
                    region = pg.LinearRegionItem(
                        (min(event.t, event.end), max(event.t, event.end)), movable=False,
                        brush=pg.mkBrush(shade),
                    )
                    region.setZValue(-9)
                    self.plot.addItem(region)
                self.plot.addItem(pg.InfiniteLine(
                    event.t, angle=90, pen=pg.mkPen(color, width=1.5, style=QtCore.Qt.DashLine),
                    label=event.name,
                    labelOpts={"position": 0.95 - 0.12 * (k % 4), "color": color},
                ))


class ComposeTab(QtWidgets.QWidget):
    """Pick a pen bounding box from the dropdown; every finger's takes recorded with exactly
    that box are listed and plotted, and the picked take's first camera frame is shown with it.
    Only takes edited on the Edit tab (with an episode) are listed. Test in sim plays every
    finger's selected take's episode at once to the MuJoCo sim, as the Edit tab's Play runs it."""

    def __init__(
        self,
        node: LeapStateListener,
        store: TakeStore,
        event_defs: dict[str, dict],
        create_tab: CreateTab,
        edit_tab: EditTab,
        avoid_slip: AvoidSlipSettings,
    ) -> None:
        super().__init__()
        self.node = node
        self.store = store
        self.create_tab = create_tab
        self.edit_tab = edit_tab
        self.avoid_slip = avoid_slip
        self._extra: dict[str, float] = {}  # Avoid slip: extra hold force of each finger
        self._rng = np.random.default_rng()
        # Play on hand: the (start, terminal) take times each finger plays between.
        self._hand_spans: dict[str, tuple[float, float]] = {}
        # Play on hand: takes of each stage (Index / Middle / Ring, then Thumb) still to play,
        # and the fingers of the stage that is playing.
        self._hand_stages: list[list[FingerTake]] = []
        self._hand_playing: list[str] = []
        self._hand_holding: list[str] = []  # fingers held in contact at their terminal
        # Moving to the episode starts: takes still to move (in START_ORDER), the finger moving,
        # the fingers held at their start and those released whose episode starts once their
        # move has finished (finger -> (take, hold at its end)).
        self._hand_takes: list[FingerTake] = []
        self._move_queue: list[FingerTake] = []
        self._moving: str | None = None
        self._at_start: set[str] = set()
        self._await_release: dict[str, tuple[FingerTake, bool]] = {}
        self._hand_releasing = False  # the last stage is done: the held fingers are let go
        self._hand_active = False
        # Recording of the Play on hand in progress: start (ROS time), box name, takes and the
        # fingers' timeline (t, finger, event).
        self._hand_rec: dict | None = None
        self._box_names: dict[bytes, str] = {}
        # Slip detection during Play on hand: a detector per finger, the last Xela message read
        # and when each finger last slipped (time.monotonic()).
        self._slip: dict[str, SlipDetector] = {}
        self._slip_xela_seq = 0
        self._slip_at: dict[str, float] = {}
        # pen_box_key -> finger -> takes (newest first), and the box's corners / label
        self._groups: dict[bytes, dict[str, list[FingerTake]]] = {}
        self._corners: dict[bytes, np.ndarray] = {}
        self._video = TakeVideo()
        # Test in sim: hardware joint names, starting hand pose, and per finger the columns,
        # take, (episode_start, terminal) span it runs over and delay (s) before it starts.
        self._sim_plan: tuple[
            list[str], np.ndarray,
            list[tuple[list[int], FingerTake, tuple[float, float], float]],
        ] | None
        self._sim_plan = None
        self._sim_start = 0.0
        self._sim_end = 0.0
        self._contact_seq = 0  # last finger contact message read
        self._touched: dict[tuple[str, str], float] = {}  # finger pair -> first touch (s)
        self._touching: set[tuple[str, str]] = set()  # pairs in the latest contact message
        self._sim_timer = QtCore.QTimer(self)
        self._sim_timer.setInterval(int(1000.0 / COMMAND_RATE_HZ))
        self._sim_timer.timeout.connect(self._sim_tick)

        self.box_combo = QtWidgets.QComboBox()
        self.box_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.box_combo.setToolTip(
            "Pen bounding boxes of the takes; Index, Middle and Ring takes share the box of the "
            "Thumb take they were recorded with"
        )
        self.summary = QtWidgets.QLabel()
        refresh_btn = QtWidgets.QPushButton("Refresh")
        self.sim_btn = QtWidgets.QPushButton("Test in sim")
        self.sim_btn.setToolTip(
            f"Play the episode (episode_start to terminal, backwards when reversed) of every "
            f"finger's selected take to the MuJoCo sim on '{node.sim_cmd_topic}': Index, Middle "
            f"and Ring together, then the Thumb once they are done. Fingers without a take hold "
            f"the first take's pose at its episode_start. Plain position "
            f"replay: maintain_touch, click_press and force replay need the real hand"
        )
        self.sim_status = QtWidgets.QLabel()
        self.hand_btn = QtWidgets.QPushButton("Play on hand")
        self.hand_btn.setToolTip(
            "Play the episode of every finger's selected take on the hand: Index, Middle and Ring "
            "together, then the Thumb once they have all got to their terminal, where they keep "
            "contact until the Thumb is done. Each runs as its Edit tab Play (maintain_touch, "
            "click_press, force replay, playback recording)"
        )
        self.hand_status = QtWidgets.QLabel()
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Bounding box:"))
        top.addWidget(self.box_combo)
        top.addWidget(self.summary, 1)
        top.addWidget(self.sim_status)
        show_sim_btn = QtWidgets.QPushButton("Show sim")
        show_sim_btn.setToolTip(f"Bring the MuJoCo window ('{SIM_WINDOW_TITLE}') to the front")
        show_sim_btn.clicked.connect(self._show_sim_window)
        top.addWidget(show_sim_btn)
        top.addWidget(self.sim_btn)
        top.addWidget(self.hand_status)
        top.addWidget(self.hand_btn)
        top.addWidget(refresh_btn)
        # Hand plays panel (right): the box's Play on hand recordings and the picked one's details.
        self.plays_list = QtWidgets.QListWidget()
        self.plays_list.setToolTip(
            "Recordings of Play on hand for this box, newest first (joint positions, velocities, "
            "efforts, Xela taxels, commands and clicks), in <demo_dir>/compose_playbacks"
        )
        self.plays_details = QtWidgets.QTextBrowser()
        self.plays_details.setOpenLinks(False)
        plays_panel = QtWidgets.QGroupBox("Hand plays")
        # Shown only while a recording is picked (highlighted) in the list.
        self.plays_delete_btn = QtWidgets.QPushButton("Delete recording")
        self.plays_delete_btn.setStyleSheet(STOP_STYLE)
        self.plays_delete_btn.setToolTip("Delete the picked recording from disk")
        plays_top = QtWidgets.QWidget()
        plays_top_layout = QtWidgets.QVBoxLayout(plays_top)
        plays_top_layout.setContentsMargins(0, 0, 0, 0)
        self.plays_sim_btn = QtWidgets.QPushButton("Play on sim")
        self.plays_sim_btn.setToolTip(
            "Send the picked recording's commands to the MuJoCo sim at their recorded times"
        )
        self.plays_hand_btn = QtWidgets.QPushButton("Play on hand")
        self.plays_hand_btn.setToolTip(
            "Send the picked recording's commands to the hand at their recorded times: plain "
            "position replay of the fingers it played (no force replay, maintain touch or "
            "click press)"
        )
        self._replay_fingers: list[str] = []  # fingers of the recording playing on the hand
        plays_buttons = QtWidgets.QWidget()
        plays_buttons_layout = QtWidgets.QHBoxLayout(plays_buttons)
        plays_buttons_layout.setContentsMargins(0, 0, 0, 0)
        plays_buttons_layout.addWidget(self.plays_sim_btn)
        plays_buttons_layout.addWidget(self.plays_hand_btn)
        plays_buttons_layout.addStretch(1)
        plays_buttons_layout.addWidget(self.plays_delete_btn)
        plays_buttons.setVisible(False)
        self.plays_buttons = plays_buttons
        plays_top_layout.addWidget(self.plays_list, 1)
        plays_top_layout.addWidget(plays_buttons)
        plays_split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        plays_split.addWidget(plays_top)
        plays_split.addWidget(self.plays_details)
        plays_split.setSizes([300, 500])
        plays_layout = QtWidgets.QVBoxLayout(plays_panel)
        plays_layout.addWidget(plays_split)
        plays_row = QtWidgets.QHBoxLayout()
        plays_row.addWidget(QtWidgets.QLabel("At start:"))
        self.start_lights: dict[str, QtWidgets.QLabel] = {}
        for finger, _ in FINGERS:
            light = QtWidgets.QLabel()
            light.setToolTip(
                f"{FINGER_LABEL[finger]} during Play on hand: yellow moving to where its episode "
                "starts, green held there (until its episode plays)"
            )
            self.start_lights[finger] = light
            plays_row.addWidget(light)
            plays_row.addWidget(QtWidgets.QLabel(finger.upper()))
            plays_row.addSpacing(4)
            self._set_start_light(finger, "off")
        plays_row.addSpacing(12)
        plays_row.addWidget(QtWidgets.QLabel("Contact:"))
        self.contact_lights: dict[str, QtWidgets.QLabel] = {}
        for finger, _ in FINGERS:
            light = QtWidgets.QLabel()
            light.setToolTip(
                f"{FINGER_LABEL[finger]} during Play on hand: green in contact with the pen "
                "(maintain touch holding, or the Thumb's click press pressing)"
            )
            self.contact_lights[finger] = light
            plays_row.addWidget(light)
            plays_row.addWidget(QtWidgets.QLabel(finger.upper()))
            plays_row.addSpacing(4)
        self._set_contact_lights()
        plays_row.addSpacing(12)
        plays_row.addWidget(QtWidgets.QLabel("Slip:"))
        self.slip_lights: dict[str, QtWidgets.QLabel] = {}
        self.slip_counts: dict[str, QtWidgets.QLabel] = {}
        for finger in SLIP_FINGERS:
            light = QtWidgets.QLabel()
            light.setToolTip(
                f"{FINGER_LABEL[finger]} during Play on hand: grey not in contact, green in "
                f"contact, red for {SLIP_LIGHT_S:.0f} s after a slip (contact spot moving on the "
                "pad, or the fingertip force falling away)"
            )
            count = QtWidgets.QLabel(f"{finger.upper()} 0")
            self.slip_lights[finger], self.slip_counts[finger] = light, count
            plays_row.addWidget(light)
            plays_row.addWidget(count)
            plays_row.addSpacing(6)
        self._set_slip_lights()
        plays_row.addSpacing(12)
        self.avoid_switch = ToggleSwitch()
        self.avoid_switch.setChecked(avoid_slip.enabled)
        self.avoid_switch.setToolTip(
            "Avoid slip: during Play on hand, Index, Middle and Ring press harder so the Thumb "
            "cannot push the pen out of their grip (needs Zero: the force is held from the Xela)"
        )
        self.avoid_switch.toggled.connect(lambda on: setattr(avoid_slip, "enabled", on))
        plays_row.addWidget(self.avoid_switch)
        plays_row.addWidget(QtWidgets.QLabel("Avoid slip"))
        for name, label, tip in (
            ("before_thumb", "Thumb", "Force units added to the fingers holding the pen when "
                                      "the Thumb starts"),
            ("per_slip", "slip", "Force units added to a finger each time it slips"),
            ("max_extra", "max", "Largest extra force of a finger (units)"),
        ):
            spin = double_spin(0.0, 50.0, 0.5, 1, "", tip)
            spin.setValue(getattr(avoid_slip, name))
            spin.valueChanged.connect(lambda v, n=name: setattr(avoid_slip, n, float(v)))
            plays_row.addWidget(QtWidgets.QLabel(f"+{label}" if name != "max_extra" else label))
            plays_row.addWidget(spin)
        plays_row.addStretch(1)

        self.camera_title = QtWidgets.QLabel()
        self.camera = CameraView("")
        self.camera.set_message("Pick a bounding box")
        recorded = QtWidgets.QWidget()
        recorded_layout = QtWidgets.QVBoxLayout(recorded)
        recorded_layout.setContentsMargins(0, 0, 0, 0)
        recorded_layout.addWidget(self.camera_title)
        recorded_layout.addWidget(self.camera, 1)
        # Live camera with the selected bounding box drawn on it.
        self._live_seq = -1
        self.live_camera = CameraView(node.image_topic)
        live = QtWidgets.QWidget()
        live_layout = QtWidgets.QVBoxLayout(live)
        live_layout.setContentsMargins(0, 0, 0, 0)
        live_layout.addWidget(QtWidgets.QLabel("<b>Live</b> (yellow: selected bounding box)"))
        live_layout.addWidget(self.live_camera, 1)
        camera_column = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        camera_column.addWidget(recorded)
        camera_column.addWidget(live)

        fingers = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(fingers)
        grid.setContentsMargins(0, 0, 0, 0)
        self.columns: dict[str, BoxFingerColumn] = {}
        for i, (finger, _) in enumerate(FINGERS):
            column = BoxFingerColumn(finger, event_defs)
            column.take_selected.connect(self._show_take)
            self.columns[finger] = column
            grid.addWidget(column, i // 2, i % 2)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.addWidget(camera_column)
        split.addWidget(fingers)
        split.addWidget(plays_panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        split.setStretchFactor(2, 1)
        split.setSizes([450, 900, 350])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(plays_row)
        layout.addWidget(split, 1)

        self.box_combo.currentIndexChanged.connect(self._on_box)
        refresh_btn.clicked.connect(self.refresh_takes)
        self.sim_btn.clicked.connect(self._toggle_sim)
        self.hand_btn.clicked.connect(self._toggle_hand)
        self.plays_list.currentRowChanged.connect(self._show_play_info)
        self.plays_delete_btn.clicked.connect(self._delete_play)
        self.plays_sim_btn.clicked.connect(self._toggle_play_sim)
        self.plays_hand_btn.clicked.connect(self._toggle_play_hand)
        create_tab.playing_changed.connect(self._on_replay_playing_changed)
        create_tab.playing_changed.connect(self._on_hand_playing_changed)
        create_tab.play_reached_end.connect(self._on_hand_reached_end)
        self.refresh_takes()

    def showEvent(self, ev) -> None:
        # Takes edited on the Edit tab (events added or removed) are only seen on a re-read.
        super().showEvent(ev)
        self.refresh_takes()

    def refresh_takes(self) -> None:
        """Re-reads every finger's takes and groups them by their exact pen box."""
        keep = self.box_combo.currentData()
        self._groups, self._corners = {}, {}
        labels: dict[bytes, str] = {}
        no_box = not_edited = 0
        for finger, _ in FINGERS:
            for path in self.store.list(finger):
                try:
                    take = self.store.load(path)
                    corners = recorded_take_pen_pose(take)
                except Exception:
                    continue
                if take_episode_span(take) is None:
                    not_edited += 1
                    continue
                if corners is None:
                    no_box += 1
                    continue
                key = pen_box_key(corners)
                self._corners[key] = corners
                self._groups.setdefault(key, {f: [] for f, _ in FINGERS})[finger].append(take)
                # Named after the take the box belongs to (the Thumb take it was inherited from).
                if len(take.pen_box) == 4:
                    if take.pen_box_source:
                        labels.setdefault(
                            key, os.path.splitext(os.path.basename(take.pen_box_source))[0]
                        )
                else:
                    labels[key] = take.name
                labels.setdefault(key, take.name)

        self._box_names = labels
        self.box_combo.blockSignals(True)
        self.box_combo.clear()
        for key, by_finger in self._groups.items():
            cx, cy = self._corners[key].mean(axis=0)
            counts = ", ".join(f"{f.upper()} {len(by_finger[f])}" for f, _ in FINGERS)
            self.box_combo.addItem(f"{labels[key]}  @ ({cx:.0f}, {cy:.0f})  [{counts}]", key)
        index = self.box_combo.findData(keep) if keep is not None else -1
        self.box_combo.setCurrentIndex(max(index, 0) if self._groups else -1)
        self.box_combo.blockSignals(False)
        skipped = []
        if not_edited:
            skipped.append(f"{not_edited} take(s) without episode_start / terminal")
        if no_box:
            skipped.append(f"{no_box} edited take(s) without a pen box")
        self.summary.setText(
            f"{len(self._groups)} bounding box(es)"
            + (f" (not listed: {', '.join(skipped)})" if skipped else "")
        )
        self._on_box()

    def _on_box(self, *_) -> None:
        self.fill_plays()
        self._live_seq = -1  # redraw the live view with the new box
        key = self.box_combo.currentData()
        by_finger = self._groups.get(key, {})
        for finger, column in self.columns.items():
            column.set_takes(by_finger.get(finger, []))
        first = next((takes[0] for takes in by_finger.values() if takes), None)
        if first is None:
            self._video.release()
            self.camera_title.setText("")
            self.camera.set_message(
                "No edited takes (episode_start and terminal) with a pen bounding box"
            )
        else:
            self._show_take(first)

    def _show_take(self, take: FingerTake) -> None:
        """First camera frame of ``take`` with the selected pen box drawn on it."""
        corners = self._corners.get(self.box_combo.currentData())
        self.camera_title.setText(f"<b>{FINGER_LABEL[take.finger]}</b>: {take.name}")
        frame = take_first_frame(take, self._video)
        if frame is None:
            self.camera.set_message(f"No camera recording in {take.name}")
        elif corners is not None:
            self.camera.set_frame(draw_recorded_pen_pose(frame, corners, "pen box"))
        else:
            self.camera.set_frame(frame)

    def _selected_takes(self) -> list[FingerTake]:
        return [
            take for take in (c.selected_take() for c in self.columns.values()) if take is not None
        ]

    def _toggle_hand(self) -> None:
        if self._hand_active:
            self.stop_hand()
            return
        if self._replay_fingers:
            QtWidgets.QMessageBox.warning(
                self, "Play on hand", "A recording is playing on the hand. Stop it first."
            )
            return
        takes = self._selected_takes()
        if not takes:
            QtWidgets.QMessageBox.warning(self, "Play on hand", "No take is selected.")
            return
        busy = [FINGER_LABEL[t.finger] for t in takes if self.create_tab.playback(t.finger)]
        if busy:
            QtWidgets.QMessageBox.warning(
                self, "Play on hand", f"Already playing: {', '.join(busy)}. Stop it first."
            )
            return
        stages = [[t for t in takes if t.finger != "th"], [t for t in takes if t.finger == "th"]]
        self._hand_stages = [stage for stage in stages if stage]
        self._hand_spans = {t.finger: self._play_span(t) for t in takes}
        self._hand_holding, self._hand_releasing = [], False
        self._hand_active = True
        self.node.get_logger().info(
            "Playing on hand: " + " then ".join(
                ", ".join(
                    f"{FINGER_LABEL[t.finger]} '{t.name}' {self._span_text(t, self._hand_spans)}"
                    for t in stage
                )
                for stage in self._hand_stages
            )
        )
        self.hand_btn.setText("Stop hand")
        self.hand_btn.setStyleSheet(STOP_STYLE)
        self._hand_takes = takes
        self._move_queue = sorted(takes, key=lambda t: START_ORDER.index(t.finger))
        self._moving, self._at_start, self._await_release = None, set(), {}
        for finger, _ in FINGERS:
            self._set_start_light(finger, "off")
        self._move_next_to_start()

    def _set_start_light(self, finger: str, state: str) -> None:
        self.start_lights[finger].setStyleSheet(SLIP_LIGHT_STYLE.format(START_COLORS[state]))

    def _set_contact_lights(self) -> None:
        for finger, light in self.contact_lights.items():
            on = self._hand_active and self.create_tab.in_contact(finger)
            state = "contact" if on else "off"
            if light.property("state") != state:
                light.setProperty("state", state)
                light.setStyleSheet(SLIP_LIGHT_STYLE.format(CONTACT_COLORS[state]))

    def _move_next_to_start(self) -> None:
        """Moves the next finger to where its episode starts; once all are there, starts the
        recording and the episodes."""
        if not self._move_queue:
            self._moving = None
            self.node.get_logger().info("Play on hand: all fingers at their start")
            self._start_hand_recording(self._hand_takes)
            self._next_hand_stage()
            return
        take = self._move_queue.pop(0)
        label = FINGER_LABEL[take.finger]
        q = self.node.latest()
        cols = take_columns(self.node.joint_names, take)
        if q is None:
            self.stop_hand("no leap_state received yet")
            return
        move = move_to_pose_take(
            take, q[cols], sample_take(take, self._hand_spans[take.finger][0])
        )
        self._moving = take.finger
        self._set_start_light(take.finger, "moving")
        self.hand_status.setText(f"hand: {label} moving to its start ({move.duration:.1f} s)")
        self.node.get_logger().info(
            f"Play on hand: {label} moving to the start of '{take.name}' "
            f"(take time {self._hand_spans[take.finger][0]:.2f} s) over {move.duration:.1f} s"
        )
        if not self.create_tab.play_take(take.finger, move, 0.0, select=False, hold_at_end=True):
            self.stop_hand(f"could not move {label} to its start")

    def _next_hand_stage(self) -> None:
        """Starts the next stage of Play on hand; once none is left, lets the held fingers go
        (or finishes if none is held). A stage with a later one stays held in contact at its
        ``terminal`` until then."""
        if not self._hand_stages:
            if self._hand_holding:
                self._hand_releasing = True
                self.hand_status.setText("hand: letting go")
                for finger in list(self._hand_holding):
                    self.create_tab.release_end_hold(finger)
            else:
                self._finish_hand("done")
            return
        stage = self._hand_stages.pop(0)
        hold = bool(self._hand_stages)
        if self.avoid_slip.enabled and any(t.finger == "th" for t in stage):
            for finger in self._hand_holding:
                self._add_extra_force(finger, self.avoid_slip.before_thumb, "Thumb starts")
        self._hand_playing = []
        for take in stage:
            if take.finger in self._at_start:
                # Held at its start: its episode plays once that hold has ended.
                self._at_start.discard(take.finger)
                self._await_release[take.finger] = (take, hold)
                self.create_tab.release_end_hold(take.finger)
            elif not self._start_episode(take, hold):
                return
        self._show_hand_status()

    def _start_episode(self, take: FingerTake, hold: bool) -> bool:
        """Plays ``take``'s episode from its (sampled) start; stops Play on hand if it can't."""
        if not self.edit_tab.play_episode(
            take.finger, take.path, hold_at_end=hold, start=self._hand_spans[take.finger][0],
        ):
            self.stop_hand(f"could not play {FINGER_LABEL[take.finger]} '{take.name}'")
            return False
        self._hand_playing.append(take.finger)
        self._set_start_light(take.finger, "off")
        self._hand_event(take.finger, "start")
        return True

    def _show_hand_status(self) -> None:
        playing = self._hand_playing + list(self._await_release)  # released: starting now
        text = "hand: " + ", ".join(FINGER_LABEL[f] for f in playing) + " playing"
        if self._hand_holding:
            text += "; holding " + ", ".join(FINGER_LABEL[f] for f in self._hand_holding)
        self.hand_status.setText(text)

    def _on_hand_reached_end(self, finger: str) -> None:
        """A finger got to its start (moving there), or a finger of the stage got to its
        ``terminal`` and is held there in contact."""
        if finger == self._moving:
            self._moving = None
            self._at_start.add(finger)
            self._set_start_light(finger, "at_start")
            self._move_next_to_start()
            return
        if finger not in self._hand_playing:
            return
        self._hand_playing.remove(finger)
        self._hand_holding.append(finger)
        self._hand_event(finger, "holding")
        self._hand_stage_progress()

    def _on_hand_playing_changed(self, finger: str) -> None:
        if self.create_tab.playback(finger) is not None:
            return
        stopped = self.create_tab.stopped.get(finger)
        finished = stopped is not None and stopped.finished
        if finger in self._await_release:
            take, hold = self._await_release.pop(finger)
            if not finished:
                self.stop_hand(f"{FINGER_LABEL[finger]} stopped at its start")
            elif self._start_episode(take, hold):
                self._show_hand_status()
            return
        if finger == self._moving or finger in self._at_start:
            self.stop_hand(f"{FINGER_LABEL[finger]} stopped while moving to / at its start")
            return
        if finger in self._hand_holding or finger in self._hand_playing:
            self._hand_event(finger, "finished" if finished else "stopped")
        if finger in self._hand_holding:
            if not (self._hand_releasing and finished):
                self.stop_hand(f"{FINGER_LABEL[finger]} stopped while holding contact")
                return
            self._hand_holding.remove(finger)
            if not self._hand_holding:
                self._finish_hand("done")
            return
        if finger not in self._hand_playing:
            return
        if not finished:
            # Stopped before its end (its own Stop, a folder change, ...): do not go on.
            self.stop_hand(f"{FINGER_LABEL[finger]} stopped before its terminal")
            return
        self._hand_playing.remove(finger)
        self._hand_stage_progress()

    def _hand_stage_progress(self) -> None:
        """Next stage once every finger of this one is done (finished or held at its end)."""
        if self._hand_playing:
            self._show_hand_status()
        else:
            self._next_hand_stage()

    def stop_hand(self, reason: str = "stopped") -> None:
        """Stops Play on hand: the fingers playing or held stop and the later stages are
        dropped."""
        if not self._hand_active:
            return
        self._hand_stages = []
        fingers = (
            self._hand_playing + self._hand_holding + sorted(self._at_start)
            + list(self._await_release) + ([self._moving] if self._moving else [])
        )
        self._hand_playing, self._hand_holding = [], []
        self._move_queue, self._moving, self._at_start, self._await_release = [], None, set(), {}
        for finger in fingers:
            if self.create_tab.playback(finger) is not None:
                self.create_tab.stop_play(finger)
            self._hand_event(finger, "stopped")
        self._finish_hand(reason)

    def _finish_hand(self, reason: str) -> None:
        self._save_hand_recording(reason)
        self._hand_active = False
        for finger, _ in FINGERS:
            self._set_start_light(finger, "off")
        self.hand_btn.setText("Play on hand")
        self.hand_btn.setStyleSheet("")
        self.hand_status.setText(f"hand: {reason}")
        self.node.get_logger().info(f"Play on hand: {reason}")

    # ---- Play on hand recording ---------------------------------------------------------

    def _ros_now(self) -> float:
        return self.node.get_clock().now().nanoseconds * 1e-9

    def _start_hand_recording(self, takes: list[FingerTake]) -> None:
        self._start_slip_detection(takes)
        self.node.start_play_recording(COMPOSE_PLAY_KEY)
        key = self.box_combo.currentData()
        box = self._box_names.get(key, "compose")
        path = next_playback_path(self.store.compose_playback_dir, box)
        if self.node.image_topic:
            self.node.start_play_video(os.path.splitext(path)[0] + ".mp4")
        if self.node.audio_topic:
            self.node.start_play_audio()
        self._hand_rec = {
            "t0": self._ros_now(),
            "path": path,
            "box": box,
            "box_corners": self._corners[key].tolist() if key in self._corners else None,
            "takes": {t.finger: t.path for t in takes},
            "spans": {t.finger: list(self._hand_spans[t.finger]) for t in takes},
            "timeline": [],
            "baseline": self.create_tab.hand.baseline,
        }

    def _hand_event(self, finger: str, event: str) -> None:
        if self._hand_rec is not None:
            t = round(self._ros_now() - self._hand_rec["t0"], 3)
            self._hand_rec["timeline"].append({"t": t, "finger": finger, "event": event})

    def _save_hand_recording(self, ended: str) -> None:
        """Saves the Play on hand that just ended as ``compose_playbacks/<box>_<n>.npz``."""
        slips = self._stop_slip_detection()
        info, self._hand_rec = self._hand_rec, None
        buffers = self.node.stop_play_recording(COMPOSE_PLAY_KEY)
        video, video_t = self.node.stop_play_video()
        audio, audio_first, audio_rate = self.node.stop_play_audio()
        if info is None or buffers is None:
            return
        log = self.node.get_logger()
        t0 = info["t0"]
        state, xela, cmd = buffers["state"], buffers["xela"], buffers["cmd"]
        cmd_t = np.array([c[0] for c in cmd]) - t0 if cmd else np.empty(0)
        if len(cmd_t) < 2 or cmd_t[-1] - cmd_t[0] < MIN_PLAY_RECORDING_S:
            log.info(f"Play on hand shorter than {MIN_PLAY_RECORDING_S} s, not recorded")
            if video and os.path.exists(video):
                os.remove(video)
            return
        path = info["path"]
        if os.path.exists(path):  # taken meanwhile: the next free name (and its video)
            path = next_playback_path(self.store.compose_playback_dir, info["box"])
            if video:
                moved = os.path.splitext(path)[0] + ".mp4"
                os.replace(video, moved)
                video = moved
        audio_path = ""
        if len(audio):
            audio_path = os.path.splitext(path)[0] + ".wav"
            try:
                save_wav(audio_path, audio, audio_rate)
            except OSError as e:
                log.warn(f"Could not save the audio {audio_path}: {e}")
                audio_path = ""
        empty16 = np.empty((0, NUM_JOINTS))
        baseline = info["baseline"]
        rec = PlaybackRecording(
            path=path,
            take=info["takes"].get("th", next(iter(info["takes"].values()))),
            finger="hand",
            joint_names=self.node.joint_names,
            cols=list(range(NUM_JOINTS)),
            cmd_t=cmd_t,
            cmd_q=np.stack([c[1] for c in cmd]),
            cmd_local=np.full(len(cmd_t), np.nan),  # one take time per finger: see the timeline
            state_t=np.array([x[0] for x in state]) - t0 if state else np.empty(0),
            position=np.stack([x[1] for x in state]) if state else empty16,
            velocity=np.stack([x[2] for x in state]) if state else empty16,
            effort=np.stack([x[3] for x in state]) if state else empty16,
            xela_t=np.array([x[0] for x in xela]) - t0 if xela else np.empty(0),
            xela=np.stack([x[1] for x in xela]) if xela else np.empty((0, 0, 3), np.float32),
            xela_baseline=baseline if baseline is not None else np.empty((0, 3)),
            click_t=np.array(buffers["clicks"]) - t0,
            video=video,
            video_t=video_t - t0 if len(video_t) else np.empty(0),
            audio=audio_path,
            audio_t0=audio_first - t0 if audio_path else 0.0,
            audio_rate=audio_rate if audio_path else 0,
            meta={
                "source": "compose_play_on_hand",
                "box": info["box"],
                "box_corners": info["box_corners"],
                "takes": info["takes"],
                "episodes": info["spans"],
                "ended": ended,
                "timeline": info["timeline"],
                "slips": [
                    {"t": round(e.t - t0, 3), "finger": f, "cue": e.cue,
                     "value": round(e.value, 5), "force": round(e.force, 3)}
                    for f, events in slips.items() for e in events
                ],
                "slip_settings": asdict(SlipSettings()),
                "avoid_slip": asdict(self.avoid_slip),
                "avoid_slip_extra": dict(self._extra),
                "maintain_touch": asdict(self.create_tab.touch_settings),
                "click_press": asdict(self.create_tab.press_settings),
                "hold": asdict(self.create_tab.settings),
            },
        )
        try:
            rec.save()
        except Exception as e:
            log.warn(f"Could not save the Play on hand recording {rec.path}: {e}")
            return
        log.info(f"Saved the Play on hand as {rec.path} ({len(cmd_t)} commands, {len(state)} "
                 f"joint states, {len(xela)} Xela readings, {len(buffers['clicks'])} clicks, "
                 f"{len(video_t)} camera frames, {len(audio) / audio_rate:.1f} s of audio)")
        self.fill_plays(select=rec.path)

    # ---- slip detection ----------------------------------------------------------------

    def _start_slip_detection(self, takes: list[FingerTake]) -> None:
        """Slip detectors for the Index / Middle / Ring fingers that play."""
        self._slip, self._slip_at = {}, {}
        self._extra = {}
        self._slip_xela_seq, _ = self.node.xela_since(0)
        for finger in SLIP_FINGERS:
            self.slip_counts[finger].setText(f"{finger.upper()} 0")
        for take in takes:
            if take.finger in SLIP_FINGERS:
                self._slip[take.finger] = SlipDetector(self.create_tab.fingertip_grid(take.finger))
        if self._slip and self.create_tab.hand.baseline is None:
            self.node.get_logger().warn(
                "Slip detection off: no live Xela baseline (press Zero)"
            )
        self._set_slip_lights()

    def _stop_slip_detection(self) -> dict[str, list]:
        """Ends slip detection; the slips of each finger."""
        self._update_slips()
        slips = {finger: detector.events for finger, detector in self._slip.items()}
        self._slip = {}
        self._set_slip_lights()
        if slips:
            self.node.get_logger().info(
                "Play on hand slips: " + ", ".join(
                    f"{FINGER_LABEL[f]} {len(events)}" for f, events in slips.items()
                )
            )
        return slips

    def _update_slips(self) -> None:
        """Feeds the Xela readings since the last call to the slip detectors."""
        if not self._slip:
            return
        self._slip_xela_seq, items = self.node.xela_since(self._slip_xela_seq)
        baseline = self.create_tab.hand.baseline
        if baseline is None or not items:
            return
        for finger, detector in self._slip.items():
            ids = self.create_tab.panels[finger].tip_plot.ids
            in_contact = self.create_tab.in_touch_contact(finger)
            for stamp, readings in items:
                if len(ids) == 0 or len(readings) <= ids.max():
                    continue
                mags = taxel_magnitudes(
                    readings[None], baseline, ids, self.node.counts_per_unit
                )[0]
                event = detector.update(stamp, mags, in_contact)
                if event is not None:
                    self._slip_at[finger] = time.monotonic()
                    detail = (
                        f"{event.value * 1000:.1f} mm" if event.cue == SPOT_SHIFT
                        else f"-{event.value:.2f}"
                    )
                    self.node.get_logger().warn(
                        f"{FINGER_LABEL[finger]} slip ({event.cue} {detail}, F {event.force:.2f})"
                    )
                    if self.avoid_slip.enabled:
                        self._add_extra_force(finger, self.avoid_slip.per_slip, "slip")

    def _add_extra_force(self, finger: str, amount: float, why: str) -> None:
        """Avoid slip: ``amount`` more hold force for ``finger`` (up to ``max_extra``)."""
        extra = min(self._extra.get(finger, 0.0) + amount, self.avoid_slip.max_extra)
        if extra <= self._extra.get(finger, 0.0):
            return
        self._extra[finger] = extra
        applied = self.create_tab.set_touch_extra_force(finger, extra)
        self._hand_event(finger, f"avoid_slip +{extra:.1f}" + ("" if applied else " (no touch)"))
        log = self.node.get_logger()
        if applied:
            log.info(f"{FINGER_LABEL[finger]} avoid slip: hold +{extra:.1f} ({why})")
        else:
            log.warn(f"{FINGER_LABEL[finger]} avoid slip: no force-held maintain touch to "
                     f"raise ({why}; press Zero)")

    def _set_slip_lights(self) -> None:
        now = time.monotonic()
        for finger, light in self.slip_lights.items():
            detector = self._slip.get(finger)
            if detector is None:
                state = "off"
            elif now - self._slip_at.get(finger, -np.inf) < SLIP_LIGHT_S:
                state = "slip"
            else:
                state = "contact" if detector.in_contact else "off"
            light.setStyleSheet(SLIP_LIGHT_STYLE.format(SLIP_COLORS[state]))
            if detector is not None:
                extra = self._extra.get(finger, 0.0)
                self.slip_counts[finger].setText(
                    f"{finger.upper()} {len(detector.events)}"
                    + (f" (+{extra:.1f})" if extra else "")
                )

    def fill_plays(self, select: str | None = None) -> None:
        """Lists the Play on hand recordings of the selected box, newest first."""
        current = self.plays_list.currentItem()
        keep = select or (current.data(QtCore.Qt.UserRole) if current is not None else None)
        box = self._box_names.get(self.box_combo.currentData())
        paths = list_playbacks(self.store.compose_playback_dir, box) if box else []
        self.plays_list.blockSignals(True)
        self.plays_list.clear()
        for path in paths:
            item = QtWidgets.QListWidgetItem(play_list_text(path))
            item.setData(QtCore.Qt.UserRole, path)
            item.setToolTip(path)
            self.plays_list.addItem(item)
        # Nothing is picked until a recording is clicked (or one was just saved).
        self.plays_list.setCurrentRow(paths.index(keep) if keep in paths else -1)
        self.plays_list.blockSignals(False)
        self._show_play_info()

    def _show_play_info(self, *_) -> None:
        """Details of the recording picked in the Hand plays panel."""
        item = self.plays_list.currentItem()
        self.plays_buttons.setVisible(item is not None)
        if item is None:
            self.plays_details.setHtml(
                "<i>Click a recording to see its details.</i>" if self.plays_list.count()
                else "<i>No Play on hand recorded for this box yet.</i>"
            )
            return
        path = item.data(QtCore.Qt.UserRole)
        try:
            rec = PlaybackRecording.load(path)
        except Exception as e:
            self.plays_details.setHtml(f"<span style='color:#d32f2f'>Load failed: {e}</span>")
            return
        self.plays_details.setHtml(play_details_html(rec))

    def _delete_play(self) -> None:
        """Deletes the recording picked in the Hand plays panel, once confirmed."""
        item = self.plays_list.currentItem()
        if item is None:
            return
        path = item.data(QtCore.Qt.UserRole)
        name = os.path.splitext(os.path.basename(path))[0]
        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Warning)
        box.setWindowTitle("Delete recording")
        box.setText(f"Delete the Play on hand recording '{name}'?")
        box.setInformativeText(
            f"{path} (and its camera, audio and label files, if any) is removed from disk. "
            "This cannot be undone."
        )
        cancel = box.addButton(QtWidgets.QMessageBox.Cancel)
        confirm = box.addButton("Confirm", QtWidgets.QMessageBox.DestructiveRole)
        box.setDefaultButton(cancel)
        box.exec_()
        if box.clickedButton() is not confirm:
            return
        try:
            delete_playback(path)
        except OSError as e:
            QtWidgets.QMessageBox.warning(
                self, "Delete recording", f"Could not delete {path}:\n{e}"
            )
            return
        self.node.get_logger().info(f"Deleted the Play on hand recording '{path}'")
        self.plays_list.setCurrentRow(-1)
        self.fill_plays()

    def _picked_recording(self, title: str) -> PlaybackRecording | None:
        """The recording picked in the Hand plays panel (warns and None if it cannot load)."""
        item = self.plays_list.currentItem()
        if item is None:
            return None
        path = item.data(QtCore.Qt.UserRole)
        try:
            rec = PlaybackRecording.load(path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, title, f"Could not load {path}:\n{e}")
            return None
        if len(rec.cmd_t) < 2:
            QtWidgets.QMessageBox.warning(self, title, f"{rec.name} has no commands.")
            return None
        return rec

    def _recording_takes(self, rec: PlaybackRecording) -> list[FingerTake]:
        """The commands of each finger the recording played, as takes from its start."""
        t = rec.cmd_t - rec.cmd_t[0]
        takes = []
        for finger, _ in FINGERS:
            if finger not in rec.meta.get("takes", {}):
                continue
            cols = finger_indices(rec.joint_names, finger)
            takes.append(FingerTake(
                finger=finger, path=rec.path, t=t, q=rec.cmd_q[:, cols],
                joint_names=[rec.joint_names[c] for c in cols],
                hand_q=rec.cmd_q, hand_joint_names=list(rec.joint_names),
            ))
        return takes

    def _toggle_play_sim(self) -> None:
        """Plays the picked recording's commands to the sim (or stops the sim)."""
        if self._sim_timer.isActive():
            self.stop_sim()
            return
        rec = self._picked_recording("Play on sim")
        if rec is None:
            return
        takes = self._recording_takes(rec)
        if not takes:
            QtWidgets.QMessageBox.warning(self, "Play on sim", f"{rec.name} played no finger.")
            return
        names = list(rec.joint_names)
        parts = [
            (take_columns(names, take), take, (0.0, take.duration), 0.0) for take in takes
        ]
        self._run_sim(names, np.asarray(rec.cmd_q[0], dtype=float), parts, self.plays_sim_btn,
                      f"Playing recording {rec.name} on sim ({rec.duration:.1f} s)")

    def _toggle_play_hand(self) -> None:
        """Plays the picked recording's commands on the hand (or stops them)."""
        if self._replay_fingers:
            self.stop_replay()
            return
        if self._hand_active:
            QtWidgets.QMessageBox.warning(self, "Play on hand", "Play on hand is running.")
            return
        rec = self._picked_recording("Play on hand")
        if rec is None:
            return
        takes = self._recording_takes(rec)
        busy = [FINGER_LABEL[t.finger] for t in takes if self.create_tab.playback(t.finger)]
        if busy:
            QtWidgets.QMessageBox.warning(
                self, "Play on hand", f"Already playing: {', '.join(busy)}. Stop it first."
            )
            return
        for take in takes:
            # Plain position replay of the commands, as the Edit tab's Replay.
            if not self.create_tab.play_take(take.finger, take, 0.0, select=False):
                self.stop_replay()
                return
            self._replay_fingers.append(take.finger)
        if self._replay_fingers:
            self.plays_hand_btn.setText("Stop hand")
            self.plays_hand_btn.setStyleSheet(STOP_STYLE)
            self.node.get_logger().info(
                f"Playing recording {rec.name} on hand ({rec.duration:.1f} s): "
                + ", ".join(FINGER_LABEL[f] for f in self._replay_fingers)
            )

    def _on_replay_playing_changed(self, finger: str) -> None:
        if finger in self._replay_fingers and self.create_tab.playback(finger) is None:
            self._replay_fingers.remove(finger)
            if not self._replay_fingers:
                self._finish_replay()

    def stop_replay(self) -> None:
        """Stops the recording playing on the hand."""
        fingers, self._replay_fingers = self._replay_fingers, []
        for finger in fingers:
            if self.create_tab.playback(finger) is not None:
                self.create_tab.stop_play(finger)
        self._finish_replay()

    def _finish_replay(self) -> None:
        self.plays_hand_btn.setText("Play on hand")
        self.plays_hand_btn.setStyleSheet("")

    def _play_span(self, take: FingerTake) -> tuple[float, float]:
        """(start, terminal) for a Test in sim / Play on hand of ``take``: the start drawn from
        its ``random_episode_start`` regions, or ``episode_start`` without any."""
        start, end = take_episode_span(take)
        sampled = sample_episode_start(take, self._rng)
        return (start if sampled is None else sampled), end

    def _span_text(self, take: FingerTake, spans: dict[str, tuple[float, float]]) -> str:
        start, end = spans[take.finger]
        random = " (random start)" if random_start_regions(take) else ""
        return f"{start:.2f} -> {end:.2f} s{random}"

    def _show_sim_window(self) -> None:
        if not raise_x11_window(SIM_WINDOW_TITLE):
            QtWidgets.QMessageBox.warning(
                self, "Show sim",
                f"No '{SIM_WINDOW_TITLE}' window found. The sim may still be starting, or "
                "mujoco_sim_node is not running or runs without its viewer (viewer:=false).",
            )

    def _toggle_sim(self) -> None:
        if self._sim_timer.isActive():
            self.stop_sim()
            return
        takes = self._selected_takes()
        if not takes:
            QtWidgets.QMessageBox.warning(self, "Test in sim", "No take is selected.")
            return
        names = list(takes[0].hand_joint_names)
        spans = [self._play_span(take) for take in takes]
        # Whole hand of the first take where it starts.
        base = np.array([
            np.interp(spans[0][0], takes[0].t, takes[0].hand_q[:, j])
            for j in range(takes[0].hand_q.shape[1])
        ])
        # The Thumb starts once the other fingers are done (holding its episode_start until then).
        others_end = max(
            (abs(end - start) for take, (start, end) in zip(takes, spans) if take.finger != "th"),
            default=0.0,
        )
        delays = [others_end if take.finger == "th" else 0.0 for take in takes]
        parts = [
            (take_columns(names, take), take, span, delay)
            for take, span, delay in zip(takes, spans, delays)
        ]
        self._run_sim(names, base, parts, self.sim_btn, "Testing in sim: " + ", ".join(
            f"{FINGER_LABEL[t.finger]} '{t.name}' "
            f"{self._span_text(t, {t.finger: s})}"
            + (f" (after {d:.2f} s)" if d else "")
            for t, s, d in zip(takes, spans, delays)
        ))

    def _run_sim(
        self, names: list[str], base: np.ndarray,
        parts: list[tuple[list[int], FingerTake, tuple[float, float], float]],
        button: QtWidgets.QPushButton, message: str,
    ) -> None:
        """Plays ``parts`` (columns, take, (start, end) take times, delay) over the hand pose
        ``base`` to the sim; ``button`` shows Stop sim meanwhile."""
        try:
            self.node.send_sim_command(names, base)
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self, "Sim", f"Could not convert the command to sim joints:\n{e}"
            )
            return
        self._sim_plan = (names, base, parts)
        self._sim_end = max(delay + abs(end - start) for _, _, (start, end), delay in parts)
        self._sim_start = time.monotonic()
        self._contact_seq, _ = self.node.finger_contacts_since(0)
        self._touched, self._touching = {}, set()
        button.setText("Stop sim")
        self.node.get_logger().info(message)
        self._sim_timer.start()
        if not self.node.sim_listening():
            self.sim_status.setText(
                f"<span style='color:#d32f2f'>nothing subscribes to "
                f"'{self.node.sim_cmd_topic}' - is mujoco_sim_node running?</span>"
            )
        elif not raise_x11_window(SIM_WINDOW_TITLE):
            self.node.get_logger().warn(
                f"Could not bring the '{SIM_WINDOW_TITLE}' window to the front (viewer:=false?)"
            )

    def _sim_tick(self) -> None:
        names, base, parts = self._sim_plan
        elapsed = min(time.monotonic() - self._sim_start, self._sim_end)
        q = base.copy()
        for cols, take, (start, end), delay in parts:
            # Holds episode_start until its delay, runs towards terminal (backwards when
            # reversed), then holds terminal.
            run = min(max(elapsed - delay, 0.0), abs(end - start))
            local = start + np.sign(end - start) * run
            q[cols] = sample_take(take, local)
        self.node.send_sim_command(names, q)
        self._read_contacts()
        if self.node.sim_listening():
            text = f"sim {elapsed:.1f} / {self._sim_end:.1f} s"
            if self._touching:
                text += (
                    f" <span style='color:#d32f2f'><b>touching: "
                    f"{pair_text(self._touching)}</b></span>"
                )
            self.sim_status.setText(text)
        if elapsed >= self._sim_end:
            self.stop_sim()

    def _read_contacts(self) -> None:
        """Takes in the sim's finger contact messages since the last call."""
        self._contact_seq, items = self.node.finger_contacts_since(self._contact_seq)
        recent = time.monotonic() - 2.0 * self._sim_timer.interval() / 1000.0
        self._touching = set()
        for stamp, pairs in items:
            for pair in pairs:
                self._touched.setdefault(pair, max(stamp - self._sim_start, 0.0))
            if stamp >= recent:
                self._touching.update(pairs)

    def stop_sim(self) -> None:
        was_running = self._sim_plan is not None
        self._sim_timer.stop()
        self._sim_plan = None
        self.sim_btn.setText("Test in sim")
        self.plays_sim_btn.setText("Play on sim")
        if not was_running:
            return
        self._read_contacts()
        if self._touched:
            summary = "fingers touched: " + ", ".join(
                f"{pair_text([pair])} at {t:.2f} s"
                for pair, t in sorted(self._touched.items(), key=lambda item: item[1])
            )
            self.sim_status.setText(f"<span style='color:#d32f2f'><b>{summary}</b></span>")
            self.node.get_logger().warn(f"Sim: {summary}")
        elif self.node.sim_listening():
            self.sim_status.setText("<span style='color:#2e7d32'>no finger contacts</span>")
            self.node.get_logger().info("Sim: no finger contacts")

    def close_video(self) -> None:
        self._video.release()

    def refresh(self) -> None:
        """Slip lights during Play on hand, and the live camera with the selected bounding box
        (while the tab is shown)."""
        if self._slip:
            self._update_slips()
            self._set_slip_lights()
        self._set_contact_lights()
        if not self.isVisible():
            return
        seq, frame = self.node.latest_raw_frame()
        if frame is None or seq == self._live_seq:
            return
        self._live_seq = seq
        key = self.box_combo.currentData()
        corners = self._corners.get(key)
        if corners is not None:
            frame = draw_recorded_pen_pose(
                frame, corners, f"recorded {self._box_names.get(key, '')}".strip()
            )
        self.live_camera.set_frame(frame)


def load_wav(path: str) -> tuple[np.ndarray, int]:
    """Mono float samples in [-1, 1] and the sample rate of a 16-bit WAV (``save_wav``)."""
    with wave.open(path, "rb") as f:
        rate, channels, width = f.getframerate(), f.getnchannels(), f.getsampwidth()
        raw = f.readframes(f.getnframes())
    if width != 2:
        raise ValueError(f"{path}: {8 * width}-bit samples, expected 16-bit")
    x = np.frombuffer(raw, "<i2").astype(np.float32) / 32767.0
    return x.reshape(-1, channels).mean(axis=1), rate


def audio_output_devices() -> list[str]:
    """Names of the sound devices that can play (PortAudio), or [] without sounddevice."""
    try:
        import sounddevice as sd
        return [d["name"] for d in sd.query_devices() if d["max_output_channels"] > 0]
    except Exception:  # noqa: BLE001 - no PortAudio
        return []


class AudioOut:
    """Plays mono samples on an output device chosen by name, from a given sample on; stops
    at the end or with ``stop``."""

    def __init__(self) -> None:
        self._stream = None
        self._lock = threading.Lock()
        self._buffer = np.empty(0, np.float32)
        self._pos = 0

    def play(self, device: str, samples: np.ndarray, rate: int, start: int = 0) -> str | None:
        """Starts playing ``samples`` (at ``rate``) from sample ``start``; an error text if the
        device cannot play them."""
        self.stop()
        try:
            import sounddevice as sd
        except Exception as e:  # noqa: BLE001
            return f"no sounddevice: {e}"
        index = next(
            (i for i, d in enumerate(sd.query_devices())
             if d["name"] == device and d["max_output_channels"] > 0), None,
        )
        if index is None:
            return f"output '{device}' not found"
        info = sd.query_devices(index)
        channels = min(2, int(info["max_output_channels"]))
        x = np.asarray(samples[max(int(start), 0):], dtype=np.float32)
        # Raw ALSA devices only take some rates: the recording's, else the device's own
        # (resampled).
        for out_rate in dict.fromkeys((int(rate), int(info["default_samplerate"]))):
            try:
                sd.check_output_settings(index, channels=channels, samplerate=out_rate)
            except Exception:  # noqa: BLE001 - rate not supported
                continue
            if out_rate != rate and len(x):
                n = int(round(len(x) * out_rate / rate))
                x = np.interp(np.arange(n) * rate / out_rate, np.arange(len(x)), x)
                x = x.astype(np.float32)
            with self._lock:
                self._buffer, self._pos = x, 0
            try:
                self._stream = sd.OutputStream(
                    device=index, channels=channels, samplerate=out_rate, dtype="float32",
                    callback=self._fill,
                )
                self._stream.start()
            except Exception as e:  # noqa: BLE001
                self._stream = None
                return f"could not open '{device}': {e}"
            return None
        return f"'{device}' plays neither {rate} Hz nor its default rate"

    def _fill(self, outdata, frames, time_info, status) -> None:
        with self._lock:
            chunk = self._buffer[self._pos:self._pos + frames]
            self._pos += frames
        outdata[:len(chunk)] = chunk[:, None]
        outdata[len(chunk):] = 0.0

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None


# Rows of the Demonstration tab's plots: (PlaybackRecording field, title, unit).
DEMO_ROWS = (
    ("position", "position", "rad"),
    ("velocity", "velocity", "rad/s"),
    ("effort", "effort", ""),
)
# Key of the Demonstration tab's fingertip taxel row (under DEMO_ROWS) in its plot dicts.
DEMO_TIP_ROW = "fingertip_taxels"
# How the Demonstration tab's list shows a recording's success / failure label.
LABEL_TEXT = {SUCCESS: "SUCCESS", FAILURE: "FAIL"}
LABEL_COLORS = {SUCCESS: "#2e7d32", FAILURE: "#c62828"}


class DemonstrationTab(QtWidgets.QWidget):
    """Plays back the Compose tab's Play on hand recordings without commanding the hand: the
    joint positions, velocities and efforts of each finger (``leap_state``), its fingertip
    taxel magnitudes, the camera
    recording with the run's bounding box, and the FK taxels with the recorded Xela readings,
    at the play bar's time; with Stream to sim, the recorded joint positions go to the sim."""

    def __init__(self, node: LeapStateListener, store: TakeStore) -> None:
        super().__init__()
        self.node = node
        self.store = store
        self.rec: PlaybackRecording | None = None
        self.duration = 0.0
        self.now = 0.0
        self._last_tick = 0.0
        self._video = TakeVideo()
        self._sim_names: list[str] = []
        self._sim_q: np.ndarray | None = None  # (N, 16) recorded joints in the sim frame
        self._xela_index = -1
        self._sim_index = -1  # last joint state streamed to the sim
        self._audio = np.empty(0, np.float32)  # the recording's microphone samples
        self._audio_rate = 0
        self._audio_out = AudioOut()
        self._settings = QtCore.QSettings(PACKAGE_NAME, "record_demonstration")

        # Left: the recordings.
        self.list = QtWidgets.QListWidget()
        self.list.setToolTip("Play on hand recordings of the Compose tab, newest first")
        refresh_btn = QtWidgets.QPushButton("Refresh")
        self.success_btn = QtWidgets.QPushButton("Success")
        self.success_btn.setToolTip(
            "Mark the picked recording as a success (press again to clear the mark)"
        )
        self.fail_btn = QtWidgets.QPushButton("Fail")
        self.fail_btn.setToolTip(
            "Mark the picked recording as a failure (press again to clear the mark)"
        )
        for btn, color in ((self.success_btn, LABEL_COLORS[SUCCESS]),
                           (self.fail_btn, LABEL_COLORS[FAILURE])):
            btn.setCheckable(True)
            btn.setStyleSheet(f"QPushButton:checked {{ background-color: {color}; color: white; }}")
        self.delete_btn = QtWidgets.QPushButton("Delete")
        self.delete_btn.setToolTip(
            "Delete the picked recording with its camera, audio and label files"
        )
        mark_row = QtWidgets.QHBoxLayout()
        mark_row.addWidget(self.success_btn)
        mark_row.addWidget(self.fail_btn)
        mark_row.addWidget(self.delete_btn)
        left = QtWidgets.QGroupBox("Recordings")
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.addWidget(self.list, 1)
        left_layout.addLayout(mark_row)
        left_layout.addWidget(refresh_btn)

        # Middle: controls and plots (rows: position / velocity / effort, columns: fingers).
        self.title = QtWidgets.QLabel("Pick a recording")
        self.play_btn = QtWidgets.QPushButton("Play")
        self.play_btn.setToolTip("Play the recording back (nothing is sent to the hand)")
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.time_label = QtWidgets.QLabel("0.00 / 0.00 s")
        self.stream_check = QtWidgets.QCheckBox("Stream to sim")
        self.stream_check.setChecked(True)
        self.stream_check.setToolTip(
            f"Send the recorded joint positions to the MuJoCo sim on '{node.sim_cmd_topic}' "
            "(converted to sim joints) as the play bar moves"
        )
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(self.play_btn)
        controls.addWidget(self.slider, 1)
        controls.addWidget(self.time_label)
        controls.addWidget(self.stream_check)
        self.output_combo = QtWidgets.QComboBox()
        self.output_combo.setToolTip("Where the recorded audio is played (e.g. your headphones)")
        self.output_combo.addItem("Muted", None)
        for name in audio_output_devices():
            self.output_combo.addItem(name, name)
        saved = self._settings.value("audio_output", "")
        index = self.output_combo.findData(saved) if saved else -1
        self.output_combo.setCurrentIndex(max(index, 0))
        test_btn = QtWidgets.QPushButton("Test")
        test_btn.setToolTip("Play a short beep on the picked output")
        test_btn.clicked.connect(self._test_output)
        self.output_status = QtWidgets.QLabel()
        outputs = QtWidgets.QHBoxLayout()
        outputs.addWidget(QtWidgets.QLabel("Audio output:"))
        outputs.addWidget(self.output_combo, 1)
        outputs.addWidget(test_btn)
        outputs.addWidget(self.output_status, 1)
        self.plots = pg.GraphicsLayoutWidget()
        self._plots: dict[tuple[str, str], pg.PlotItem] = {}
        self._curves: dict[tuple[str, str], list[pg.PlotDataItem]] = {}
        self._cursors: list[pg.InfiniteLine] = []
        self._marks: list[tuple[pg.PlotItem, pg.InfiniteLine]] = []  # timeline / slip lines
        first = None
        for r, (field_name, title, unit) in enumerate(DEMO_ROWS):
            for c, (finger, label) in enumerate(FINGERS):
                plot = self.plots.addPlot(row=r, col=c, title=f"{label} {title}")
                plot.showGrid(x=True, y=True, alpha=0.3)
                plot.setLabel("left", title, unit)
                if r == 0:
                    plot.addLegend(offset=(5, 5))
                curves = [
                    plot.plot(pen=pg.mkPen(color, width=1.5), connect="finite")
                    for color in JOINT_COLORS
                ]
                cursor = pg.InfiniteLine(0.0, angle=90, pen=pg.mkPen("w", width=1))
                plot.addItem(cursor)
                self._cursors.append(cursor)
                if first is None:
                    first = plot
                else:
                    plot.setXLink(first)
                self._plots[(field_name, finger)] = plot
                self._curves[(field_name, finger)] = curves
        # Fingertip taxel magnitudes of each finger (recorded Xela, from the run's baseline).
        tip_ids = fingertip_taxel_ids()
        self._tip_ids = {
            finger: tip_ids[finger] if tip_ids is not None else np.empty(0, dtype=int)
            for finger, _ in FINGERS
        }
        for c, (finger, label) in enumerate(FINGERS):
            plot = self.plots.addPlot(
                row=len(DEMO_ROWS), col=c, title=f"{label} {TipTaxelPlot.TITLE.lower()}"
            )
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setLabel("left", "|force|")
            plot.setLabel("bottom", "time", "s")
            plot.setClipToView(True)
            plot.setDownsampling(auto=True, mode="peak")
            n = len(self._tip_ids[finger])
            curves = [
                plot.plot(pen=pg.mkPen(pg.intColor(i, hues=max(n, 1)), width=1), antialias=False)
                for i in range(n)
            ]
            cursor = pg.InfiniteLine(0.0, angle=90, pen=pg.mkPen("w", width=1))
            plot.addItem(cursor)
            self._cursors.append(cursor)
            plot.setXLink(first)
            self._plots[(DEMO_TIP_ROW, finger)] = plot
            self._curves[(DEMO_TIP_ROW, finger)] = curves
        # The microphone recording, under the joints, on the same time axis.
        self.audio_plot = self.plots.addPlot(
            row=len(DEMO_ROWS) + 1, col=0, colspan=len(FINGERS), title="Audio"
        )
        self.audio_plot.showGrid(x=True, y=True, alpha=0.3)
        self.audio_plot.setLabel("left", "amplitude")
        self.audio_plot.setLabel("bottom", "time", "s")
        self.audio_plot.setDownsampling(auto=True, mode="peak")
        self.audio_plot.setClipToView(True)
        self.audio_plot.setYRange(-1.0, 1.0)
        # Not linked: it is wider than the joint plots, and pyqtgraph links keep the scale per
        # pixel; it follows their time range instead.
        first.sigXRangeChanged.connect(
            lambda _, r: self.audio_plot.setXRange(r[0], r[1], padding=0.0)
        )
        self.audio_curve = self.audio_plot.plot(pen=pg.mkPen("#4fc3f7", width=1))
        audio_cursor = pg.InfiniteLine(0.0, angle=90, pen=pg.mkPen("w", width=1))
        self.audio_plot.addItem(audio_cursor)
        self._cursors.append(audio_cursor)
        self.plots.ci.layout.setRowStretchFactor(len(DEMO_ROWS) + 1, 1)
        middle = QtWidgets.QWidget()
        middle_layout = QtWidgets.QVBoxLayout(middle)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.addWidget(self.title)
        middle_layout.addLayout(controls)
        middle_layout.addLayout(outputs)
        middle_layout.addWidget(self.plots, 1)

        # Right: the camera recording with the bounding box, and the FK taxels.
        self.camera = CameraView("")
        self.camera.setWordWrap(True)
        self.camera.set_message("Pick a recording")
        self.hand = HandView(
            node.sim_topic, node.xela_topic, node.counts_per_unit, waiting="Pick a recording"
        )
        right = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        right.addWidget(self.camera)
        right.addWidget(self.hand)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(middle)
        split.addWidget(right)
        split.setSizes([250, 900, 500])
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(split)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._tick)
        refresh_btn.clicked.connect(self.refresh_recordings)
        self.success_btn.clicked.connect(lambda: self._mark(SUCCESS))
        self.fail_btn.clicked.connect(lambda: self._mark(FAILURE))
        self.delete_btn.clicked.connect(self._delete_picked)
        self.list.currentRowChanged.connect(self._load_picked)
        self._update_mark_buttons()
        self.play_btn.clicked.connect(self._toggle_play)
        self.output_combo.currentIndexChanged.connect(self._output_changed)
        self.slider.valueChanged.connect(
            lambda v: self.seek(v / SLIDER_STEPS_PER_SEC, from_slider=True)
        )

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        self.refresh_recordings()

    # ---- recordings ---------------------------------------------------------------------

    def refresh_recordings(self) -> None:
        """Lists every Play on hand recording, newest first, keeping the picked one."""
        current = self.list.currentItem()
        keep = current.data(QtCore.Qt.UserRole) if current is not None else None
        paths = list_playbacks(self.store.compose_playback_dir)
        self.list.blockSignals(True)
        self.list.clear()
        for path in paths:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, path)
            item.setToolTip(path)
            self._show_label(item)
            self.list.addItem(item)
        self.list.setCurrentRow(paths.index(keep) if keep in paths else -1)
        self.list.blockSignals(False)
        if keep is not None and keep not in paths:
            self._load(None)
        self._update_mark_buttons()

    def _show_label(self, item: QtWidgets.QListWidgetItem) -> None:
        """The list entry of a recording, with its success / failure label and colour."""
        path = item.data(QtCore.Qt.UserRole)
        label = (load_label(path) or {}).get("label")
        text = play_list_text(path)
        if label in LABEL_COLORS:
            text = f"[{LABEL_TEXT[label]}] {text}"
            item.setForeground(QtGui.QColor(LABEL_COLORS[label]))
        else:
            item.setData(QtCore.Qt.ForegroundRole, None)
        item.setText(text)

    def _update_mark_buttons(self) -> None:
        """Enables the Success / Fail / Delete buttons for a picked recording and checks the
        one of its label."""
        item = self.list.currentItem()
        label = (load_label(item.data(QtCore.Qt.UserRole)) or {}).get("label") if item else None
        for btn in (self.success_btn, self.fail_btn, self.delete_btn):
            btn.setEnabled(item is not None)
        self.success_btn.setChecked(label == SUCCESS)
        self.fail_btn.setChecked(label == FAILURE)

    def _mark(self, label: str) -> None:
        """Marks the picked recording as ``label``; marking it with its own label clears it."""
        item = self.list.currentItem()
        if item is None:
            return
        path = item.data(QtCore.Qt.UserRole)
        current = (load_label(path) or {}).get("label")
        try:
            set_manual_label(path, None if current == label else label)
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "Mark recording", f"Could not label {path}:\n{e}")
        self._show_label(item)
        self._update_mark_buttons()

    def _delete_picked(self) -> None:
        """Deletes the picked recording, once confirmed."""
        item = self.list.currentItem()
        if item is None:
            return
        path = item.data(QtCore.Qt.UserRole)
        name = os.path.splitext(os.path.basename(path))[0]
        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Warning)
        box.setWindowTitle("Delete recording")
        box.setText(f"Delete the recording '{name}'?")
        box.setInformativeText(
            f"{path} (and its camera, audio and label files, if any) is removed from disk. "
            "This cannot be undone."
        )
        cancel = box.addButton(QtWidgets.QMessageBox.Cancel)
        confirm = box.addButton("Confirm", QtWidgets.QMessageBox.DestructiveRole)
        box.setDefaultButton(cancel)
        box.exec_()
        if box.clickedButton() is not confirm:
            return
        self._load(None)  # closes its camera recording before it goes
        try:
            delete_playback(path)
        except OSError as e:
            QtWidgets.QMessageBox.warning(
                self, "Delete recording", f"Could not delete {path}:\n{e}"
            )
        else:
            self.node.get_logger().info(f"Deleted the Play on hand recording '{path}'")
        self.list.setCurrentRow(-1)
        self.refresh_recordings()

    def _load_picked(self, *_) -> None:
        item = self.list.currentItem()
        self._update_mark_buttons()
        self._load(item.data(QtCore.Qt.UserRole) if item is not None else None)

    def _load(self, path: str | None) -> None:
        """Shows the recording at ``path`` (None: nothing) from its start."""
        self._stop()
        self._video.release()
        self.rec, self._sim_q, self._xela_index, self._sim_index = None, None, -1, -1
        self._audio, self._audio_rate = np.empty(0, np.float32), 0
        self.audio_curve.setData([], [])
        self.audio_plot.setTitle("Audio")
        for plot, line in self._marks:
            plot.removeItem(line)
        self._marks = []
        for curves in self._curves.values():
            for curve in curves:
                curve.setData([], [])
        if path is None:
            self.title.setText("Pick a recording")
            self.camera.set_message("Pick a recording")
            self.hand.clear_readings("Pick a recording")
            self.duration = 0.0
            self.slider.setRange(0, 0)
            self._show_time()
            return
        try:
            rec = PlaybackRecording.load(path)
        except Exception as e:
            self.title.setText(f"<span style='color:#d32f2f'>Could not load {path}: {e}</span>")
            return
        self.rec = rec
        self._load_audio(rec)
        ends = [arr[-1] for arr in (rec.state_t, rec.cmd_t, rec.xela_t, rec.video_t) if len(arr)]
        if len(self._audio):
            ends.append(rec.audio_t0 + len(self._audio) / self._audio_rate)
        self.duration = float(max(ends)) if ends else 0.0
        takes = ", ".join(
            f"{f.upper()} {os.path.splitext(os.path.basename(p))[0]}"
            for f, p in rec.meta.get("takes", {}).items()
        )
        self.title.setText(
            f"<b>{rec.name}</b>: {self.duration:.1f} s, {rec.meta.get('ended', '?')} ({takes})"
        )
        self._plot(rec)
        # The whole run on the (linked) time axes; each plot fits its own values.
        for plot in self._plots.values():
            plot.enableAutoRange(axis="y")
        next(iter(self._plots.values())).setXRange(0.0, max(self.duration, 0.1), padding=0.02)
        self._convert_joints(rec)
        self.hand.set_baseline(rec.xela_baseline if len(rec.xela_baseline) else None)
        if not len(rec.xela_t):
            self.hand.clear_readings(f"No Xela readings in {rec.name}")
        if not (rec.video and len(rec.video_t) and os.path.exists(rec.video)):
            self.camera.set_message(
                f"No camera recording in {rec.name}" + (
                    "\n(an older run, or no camera frames came)" if not rec.video else ""
                )
            )
        self.slider.blockSignals(True)
        self.slider.setRange(0, int(round(self.duration * SLIDER_STEPS_PER_SEC)))
        self.slider.blockSignals(False)
        self.seek(0.0)

    def _plot(self, rec: PlaybackRecording) -> None:
        """Joint position / velocity / effort of each finger, with the run's timeline."""
        names = rec.joint_names
        for field_name, _, _ in DEMO_ROWS:
            data = getattr(rec, field_name)
            for finger, _ in FINGERS:
                cols = finger_indices(names, finger)
                curves = self._curves[(field_name, finger)]
                plot = self._plots[(field_name, finger)]
                if plot.legend is not None:
                    plot.legend.clear()
                for curve, col in zip(curves, cols):
                    if len(rec.state_t) and data.shape[0] == len(rec.state_t):
                        curve.setData(rec.state_t, data[:, col])
                    if plot.legend is not None:
                        plot.legend.addItem(curve, names[col])
        self._plot_tips(rec)
        # Milestones (start, holding, finished / stopped) are labelled on the position row;
        # Avoid slip raises (faint) and slips (red) are only lines, as they can be many.
        marks = []
        for e in rec.meta.get("timeline", []):
            avoid = e["event"].startswith("avoid_slip")
            marks.append((e["t"], e["finger"], None if avoid else e["event"],
                          "#616161" if avoid else "#bdbdbd"))
        marks += [(e["t"], e["finger"], None, "#ff1744") for e in rec.meta.get("slips", [])]
        labelled: dict[str, int] = {}
        for t, finger, text, color in marks:
            k = labelled.get(finger, 0)
            if text is not None:
                labelled[finger] = k + 1
            for r, field_name in enumerate([f for f, _, _ in DEMO_ROWS] + [DEMO_TIP_ROW]):
                plot = self._plots.get((field_name, finger))
                if plot is None:
                    continue
                line = pg.InfiniteLine(
                    t, angle=90, pen=pg.mkPen(color, width=1, style=QtCore.Qt.DashLine),
                    label=text if r == 0 else None,
                    labelOpts={"position": 0.92 - 0.12 * (k % 4), "color": color},
                )
                plot.addItem(line)
                self._marks.append((plot, line))

    def _plot_tips(self, rec: PlaybackRecording) -> None:
        """Fingertip taxel magnitudes of each finger over the run, from its Xela baseline (its
        first reading for runs without one)."""
        for finger, label in FINGERS:
            ids = self._tip_ids[finger]
            plot = self._plots[(DEMO_TIP_ROW, finger)]
            title = f"{label} {TipTaxelPlot.TITLE.lower()}"
            if len(ids) == 0:
                plot.setTitle(f"{title} - taxel map unavailable")
                continue
            if len(rec.xela_t) == 0 or rec.xela.shape[1] <= ids.max():
                plot.setTitle(f"{title} - no Xela readings")
                continue
            baseline = rec.xela_baseline if len(rec.xela_baseline) > ids.max() else rec.xela[0]
            mags = taxel_magnitudes(rec.xela, baseline, ids, self.node.counts_per_unit)
            for j, curve in enumerate(self._curves[(DEMO_TIP_ROW, finger)]):
                curve.setData(rec.xela_t, mags[:, j])
            plot.setTitle(title)

    def _convert_joints(self, rec: PlaybackRecording) -> None:
        """The recorded joints in the sim frame, for the FK taxels."""
        if not len(rec.state_t):
            return
        try:
            to_sim = HardwareToSim()
            self._sim_q = np.array([to_sim(rec.joint_names, q) for q in rec.position])
            self._sim_names = list(to_sim.sim_names)
        except Exception as e:
            self.node.get_logger().warn(f"Demonstration: no FK taxels for {rec.name}: {e}")
            self._sim_q = None

    # ---- playback -----------------------------------------------------------------------

    def seek(self, t: float, from_slider: bool = False) -> None:
        """Shows the recording at ``t`` s from its start."""
        self.now = float(np.clip(t, 0.0, self.duration))
        if from_slider and self._timer.isActive():
            self._play_audio()  # heard from the new time
        if not from_slider:
            self.slider.blockSignals(True)
            self.slider.setValue(int(round(self.now * SLIDER_STEPS_PER_SEC)))
            self.slider.blockSignals(False)
        for cursor in self._cursors:
            cursor.setValue(self.now)
        self._show_time()
        rec = self.rec
        if rec is None:
            return
        if rec.video and len(rec.video_t) and os.path.exists(rec.video):
            frame = self._video.read(rec.video, max(index_at(rec.video_t, self.now), 0))
            if frame is not None:
                corners = rec.meta.get("box_corners")
                if corners is not None:
                    frame = draw_recorded_pen_pose(
                        frame, np.asarray(corners), f"box {rec.meta.get('box', '')}".strip()
                    )
                self.camera.set_frame(frame)
        if len(rec.state_t):
            j = max(index_at(rec.state_t, self.now), 0)
            if self._sim_q is not None:
                self.hand.set_joints(self._sim_names, self._sim_q[j])
            if self.stream_check.isChecked() and j != self._sim_index:
                self._sim_index = j
                self._stream(rec, j)
        if len(rec.xela_t):
            k = max(index_at(rec.xela_t, self.now), 0)
            if k != self._xela_index:
                self._xela_index = k
                self.hand.set_readings(rec.xela[k], source=f"Recorded Xela of {rec.name}")

    def _stream(self, rec: PlaybackRecording, j: int) -> None:
        """Sends joint state ``j`` of the recording to the sim (hardware -> sim joints)."""
        try:
            self.node.send_sim_command(rec.joint_names, rec.position[j])
        except Exception as e:
            self.stream_check.setChecked(False)
            self.node.get_logger().warn(f"Demonstration: Stream to sim off: {e}")

    def _load_audio(self, rec: PlaybackRecording) -> None:
        """The recording's microphone samples, plotted on its time axis."""
        if not (rec.audio and os.path.exists(rec.audio)):
            self.audio_plot.setTitle(
                f"Audio: none in {rec.name}" + ("" if rec.audio else " (recorded before audio)")
            )
            return
        try:
            self._audio, self._audio_rate = load_wav(rec.audio)
        except (OSError, ValueError, wave.Error) as e:
            self.audio_plot.setTitle(f"Audio: could not read {rec.audio}: {e}")
            return
        t = rec.audio_t0 + np.arange(len(self._audio)) / self._audio_rate
        self.audio_curve.setData(t, self._audio)
        self.audio_plot.setTitle(
            f"Audio: {os.path.basename(rec.audio)} ({len(self._audio) / self._audio_rate:.1f} s, "
            f"{self._audio_rate} Hz)"
        )

    def _output(self) -> str | None:
        return self.output_combo.currentData()

    def _output_changed(self, *_) -> None:
        self._settings.setValue("audio_output", self._output() or "")
        self.output_status.setText("")
        if self._timer.isActive():
            self._play_audio()

    def _play_audio(self) -> None:
        """Plays the recording's audio on the picked output from the play bar's time."""
        self._audio_out.stop()
        device = self._output()
        if device is None or self.rec is None or not len(self._audio):
            return
        start = int(round((self.now - self.rec.audio_t0) * self._audio_rate))
        if start >= len(self._audio):
            return
        # Before the audio starts: wait that long in silence.
        samples = self._audio[max(start, 0):]
        if start < 0:
            samples = np.concatenate([np.zeros(-start, np.float32), samples])
        error = self._audio_out.play(device, samples, self._audio_rate)
        self.output_status.setText(
            f"<span style='color:#d32f2f'>{error}</span>" if error else ""
        )

    def _test_output(self) -> None:
        device = self._output()
        if device is None:
            self.output_status.setText("Muted: pick an output first")
            return
        rate = 48000
        t = np.arange(int(0.4 * rate)) / rate
        beep = (0.3 * np.sin(2 * np.pi * 880 * t) * np.minimum(1, (0.4 - t) / 0.05)).astype(
            np.float32
        )
        error = self._audio_out.play(device, beep, rate)
        self.output_status.setText(
            f"<span style='color:#d32f2f'>{error}</span>" if error else f"beep on {device}"
        )

    def _show_time(self) -> None:
        self.time_label.setText(f"{self.now:.2f} / {self.duration:.2f} s")

    def _toggle_play(self) -> None:
        if self._timer.isActive():
            self._stop()
            return
        if self.rec is None:
            return
        if self.now >= self.duration:
            self.seek(0.0)
        self._last_tick = time.monotonic()
        self._timer.start()
        self.play_btn.setText("Pause")
        self._play_audio()
        if self.stream_check.isChecked():
            self._sim_index = -1  # resend the current state
            self.seek(self.now)
            if not self.node.sim_listening():
                self.node.get_logger().warn(
                    f"Demonstration: nothing subscribes to '{self.node.sim_cmd_topic}' "
                    "(is mujoco_sim_node running?)"
                )
            else:
                raise_x11_window(SIM_WINDOW_TITLE)

    def _stop(self) -> None:
        self._timer.stop()
        self._audio_out.stop()
        self.play_btn.setText("Play")

    def _tick(self) -> None:
        now = time.monotonic()
        dt, self._last_tick = now - self._last_tick, now
        self.seek(self.now + dt)
        if self.now >= self.duration:
            self._stop()

    def close_video(self) -> None:
        self._stop()
        self._video.release()


def double_spin(
    minimum: float, maximum: float, step: float, decimals: int, suffix: str, tooltip: str
) -> QtWidgets.QDoubleSpinBox:
    spin = QtWidgets.QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setDecimals(decimals)
    spin.setSuffix(suffix)
    spin.setToolTip(tooltip)
    spin.setKeyboardTracking(False)  # typed values apply on Enter, not per keystroke
    return spin


class SettingsTab(QtWidgets.QWidget):
    """Playback / compliance values of this GUI (applied immediately) and the compliant
    gains of the hand node (applied with "Apply to hand")."""

    settings_changed = QtCore.pyqtSignal()
    demo_dir_changed = QtCore.pyqtSignal(str)
    # Emitted from the executor thread; Qt queues them to the GUI thread.
    _hand_loaded = QtCore.pyqtSignal(object)
    _hand_applied = QtCore.pyqtSignal(object)

    RETRY_MS = 2000

    def __init__(
        self,
        node: LeapStateListener,
        store: TakeStore,
        settings: HoldSettings,
        touch_settings: MaintainTouchSettings,
        press_settings: ClickPressSettings,
        saved: dict,
        saved_path: str,
        avoid_slip: AvoidSlipSettings,
    ) -> None:
        """``saved`` are the settings loaded from ``saved_path`` (where Save settings writes)."""
        super().__init__()
        self.node = node
        self.store = store
        self.settings = settings
        self.touch_settings = touch_settings
        self.press_settings = press_settings
        self.avoid_slip = avoid_slip  # set on the Compose tab, saved here
        self._hand_compliant: bool | None = None  # None until read from the hand node
        self._saved_path = saved_path
        # Saved hand gains, applied once when the hand node is first read; kept on save until
        # the hand has been read (the spin boxes do not hold its values before).
        self._saved_hand: dict[str, float] = {
            name: float(value) for name, value in saved.get("hand", {}).items()
            if name in {n for n, *_ in HAND_PARAMS}
        }
        self._hand_read = False
        self._apply_saved_hand = bool(self._saved_hand)

        self.dir_edit = QtWidgets.QLineEdit(store.demo_dir)
        self.dir_edit.setToolTip(
            "Folder takes are saved into (fingers/, camera/ and playbacks/ inside it). "
            "Press Enter to apply"
        )
        browse_btn = QtWidgets.QPushButton("Browse...")
        dir_row = QtWidgets.QHBoxLayout()
        dir_row.addWidget(self.dir_edit, 1)
        dir_row.addWidget(browse_btn)
        dir_box = QtWidgets.QGroupBox("Recordings")
        dir_form = QtWidgets.QFormLayout(dir_box)
        dir_form.addRow("Save to:", dir_row)
        self.dir_edit.editingFinished.connect(lambda: self._set_demo_dir(self.dir_edit.text()))
        browse_btn.clicked.connect(self._browse_demo_dir)

        self.rate_spin = double_spin(
            5.0, 100.0, 5.0, 0, " Hz",
            "How often playing fingers are commanded on cmd_topic",
        )
        self.ramp_spin = double_spin(
            0.0, 5.0, 0.1, 2, " s",
            "Play first moves the finger from where it is to the take over this time",
        )
        self.deadband_spin = double_spin(
            0.0, 0.5, 0.005, 3, " rad",
            "While a finger is playing, the other fingers follow the hand once pushed "
            "further than this. Lower = easier to pose, higher = less drift from gravity sag",
        )
        gui_box = QtWidgets.QGroupBox("Playback (this GUI, applied immediately)")
        gui_form = QtWidgets.QFormLayout(gui_box)
        gui_form.addRow("Command rate:", self.rate_spin)
        gui_form.addRow("Playback ramp:", self.ramp_spin)
        gui_form.addRow("Free-finger deadband:", self.deadband_spin)
        reset_btn = QtWidgets.QPushButton("Reset to defaults")
        gui_form.addRow("", reset_btn)
        self._show_settings()
        for spin in (self.rate_spin, self.ramp_spin, self.deadband_spin):
            spin.valueChanged.connect(self._on_gui_changed)
        reset_btn.clicked.connect(self._reset_gui)

        self.hand_spins: dict[str, QtWidgets.QDoubleSpinBox] = {}
        self.hand_box = QtWidgets.QGroupBox(f"Hand compliance ({node.hand_node}, compliant mode)")
        hand_form = QtWidgets.QFormLayout(self.hand_box)
        for name, label, maximum, step, decimals, suffix, tooltip in HAND_PARAMS:
            spin = double_spin(0.0, maximum, step, decimals, suffix, tooltip)
            self.hand_spins[name] = spin
            hand_form.addRow(f"{label}:", spin)
        self.apply_btn = QtWidgets.QPushButton("Apply to hand")
        self.reload_btn = QtWidgets.QPushButton("Reload from hand")
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.apply_btn)
        buttons.addWidget(self.reload_btn)
        buttons.addStretch(1)
        hand_form.addRow("", buttons)
        self.hand_status = QtWidgets.QLabel()
        self.hand_status.setWordWrap(True)
        hand_form.addRow(self.hand_status)
        self.apply_btn.clicked.connect(self._apply_hand)
        self.reload_btn.clicked.connect(self._reload_hand)
        self._hand_loaded.connect(self._on_hand_loaded)
        self._hand_applied.connect(self._on_hand_applied)

        touch_box = self._build_touch_box()
        press_box = self._build_press_box()

        save_btn = QtWidgets.QPushButton("Save settings")
        save_btn.setToolTip(
            "Save the folder, playback, maintain touch, click press and hand values; they are "
            "used at the "
            f"next start.\n{saved_path}"
        )
        self.save_status = QtWidgets.QLabel(
            f"Loaded saved settings from {saved_path}" if saved else "No saved settings yet."
        )
        self.save_status.setWordWrap(True)
        save_row = QtWidgets.QHBoxLayout()
        save_row.addWidget(save_btn)
        save_row.addWidget(self.save_status, 1)
        save_btn.clicked.connect(self._save)

        # The sections scroll; Save settings stays below them, always in view.
        sections = QtWidgets.QWidget()
        sections_layout = QtWidgets.QVBoxLayout(sections)
        sections_layout.addWidget(dir_box)
        sections_layout.addWidget(gui_box)
        sections_layout.addWidget(touch_box)
        sections_layout.addWidget(press_box)
        sections_layout.addWidget(self.hand_box)
        sections_layout.addStretch(1)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidget(sections)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addLayout(save_row)

        self._retry = QtCore.QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.timeout.connect(self._reload_hand)
        self._set_hand_enabled(False)
        self._reload_hand()

    # ---- recordings folder --------------------------------------------------------------

    def _browse_demo_dir(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Recordings folder", self.store.demo_dir
        )
        if path:
            self._set_demo_dir(path)

    def _set_demo_dir(self, text: str) -> None:
        path = os.path.abspath(os.path.expanduser(text.strip())) if text.strip() else ""
        if not path or path == self.store.demo_dir:
            self.dir_edit.setText(self.store.demo_dir)
            return
        if self.node.recording:
            self.dir_edit.setText(self.store.demo_dir)
            QtWidgets.QMessageBox.warning(
                self, "Recordings", "Stop the recording before changing the folder."
            )
            return
        self.dir_edit.setText(path)
        self.demo_dir_changed.emit(path)

    # ---- this GUI -----------------------------------------------------------------------

    def _show_settings(self) -> None:
        s = self.settings
        for spin, value in (
            (self.rate_spin, s.command_rate),
            (self.ramp_spin, s.ramp_s),
            (self.deadband_spin, s.deadband),
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    def _on_gui_changed(self, *_) -> None:
        s = self.settings
        s.command_rate = self.rate_spin.value()
        s.ramp_s = self.ramp_spin.value()
        s.deadband = self.deadband_spin.value()
        self.settings_changed.emit()

    def _reset_gui(self) -> None:
        for name, value in asdict(HoldSettings()).items():
            setattr(self.settings, name, value)
        self._show_settings()
        self.settings_changed.emit()

    # ---- maintain touch -----------------------------------------------------------------

    # (field, label, min, max, step, decimals, suffix, scale shown / stored, tooltip)
    TOUCH_FIELDS = (
        ("hold_force", "Hold force", 0.0, 50.0, 0.1, 2, " units", 1.0,
         "Fingertip force held in contact over a region (the tip plots' units: sum of the "
         "fingertip taxel magnitudes), above the force at the region's entry if relative"),
        ("contact_force", "Contact force", 0.0, 20.0, 0.05, 2, " units", 1.0,
         "Fingertip force (rise above the force at the entry if relative) that ends the "
         "approach; below half of it for the loss time the contact is lost and the finger "
         "approaches again"),
        ("ramp_s", "Force ramp", 0.0, 5.0, 0.05, 2, " s", 1.0,
         "Time the force ramps from contact up to the hold force"),
        ("force_gain", "Force gain", 0.0, 2.0, 0.005, 3, " rad/(unit·s)", 1.0,
         "How fast the joint goals move past contact (along J^T d, so the force points along "
         "the press axis) per unit of missing force"),
        ("approach_speed", "Approach speed", 0.0, 50.0, 0.5, 1, " mm/s", 1000.0,
         "Speed of the guarded move along the press axis until the fingertip touches (the "
         "take waits meanwhile)"),
        ("max_travel", "Max approach", 0.0, 50.0, 0.5, 1, " mm", 1000.0,
         "Largest approach before giving up on the region (the take then plays over it)"),
        ("max_wait", "Max wait", 0.0, 30.0, 0.5, 1, " s", 1.0,
         "Longest wait for contact before giving up on the region"),
        ("max_press_q", "Max press offset", 0.0, 2.0, 0.05, 2, " rad", 1.0,
         "Largest press offset of the joint goals past where contact was made"),
        ("max_joint_offset", "Max joint offset", 0.0, 2.0, 0.05, 2, " rad", 1.0,
         "Largest press offset of any one joint"),
        ("sat_effort", "Current limit at", 0.0, 2000.0, 10.0, 0, "", 1.0,
         "leap_state effort of a joint at its current limit (0: off). There the press stops "
         "pushing deeper"),
        ("loss_s", "Contact loss time", 0.0, 5.0, 0.05, 2, " s", 1.0,
         "Time below half the contact force before the finger approaches again"),
        ("release_s", "Release time", 0.0, 5.0, 0.05, 2, " s", 1.0,
         "After a region, the finger blends back into the take over this time"),
        ("press_offset", "No feedback: press", 0.0, 0.6, 0.005, 3, " rad", 1.0,
         "Without a Zero baseline or kinematics the recorded pose at the region's entry is "
         "held, pressed this far past it along the joint motion that led there"),
        ("press_rate", "No feedback: rate", 0.0, 2.0, 0.01, 3, " rad/s", 1.0,
         "Without force feedback, how fast the press grows during a region"),
        ("max_offset", "No feedback: max", 0.0, 0.6, 0.01, 2, " rad", 1.0,
         "Without force feedback, the largest press past the held pose"),
    )

    def _build_touch_box(self) -> QtWidgets.QGroupBox:
        self.touch_check = QtWidgets.QCheckBox(f"Hold contact in '{MAINTAIN_TOUCH_EVENT}' regions")
        self.touch_check.setToolTip(
            f"During Play in the Edit tab, at a '{MAINTAIN_TOUCH_EVENT}' region the take waits "
            "while the fingertip moves along the press axis until it touches, then the take "
            "plays on while the fingertip force is held (needs a Zero baseline before Play)"
        )
        self.touch_relative_check = QtWidgets.QCheckBox("Forces relative to the force at entry")
        self.touch_relative_check.setToolTip(
            "Measure the contact and hold forces from the fingertip force where Play enters the "
            "region, not from the Zero baseline: a curled finger's taxels read a few units "
            "without any contact"
        )
        self.touch_spins: dict[str, QtWidgets.QDoubleSpinBox] = {}
        touch_reset = QtWidgets.QPushButton("Reset to defaults")
        box = QtWidgets.QGroupBox("Maintain touch (Edit tab Play, applied immediately)")
        form = QtWidgets.QFormLayout(box)
        form.addRow(self.touch_check)
        form.addRow(self.touch_relative_check)
        for name, label, lo, hi, step, decimals, suffix, _, tooltip in self.TOUCH_FIELDS:
            spin = double_spin(lo, hi, step, decimals, suffix, tooltip)
            self.touch_spins[name] = spin
            form.addRow(f"{label}:", spin)
        form.addRow("", touch_reset)
        self._show_touch_settings()
        for spin in self.touch_spins.values():
            spin.valueChanged.connect(self._on_touch_changed)
        self.touch_check.toggled.connect(self._on_touch_changed)
        self.touch_relative_check.toggled.connect(self._on_touch_changed)
        touch_reset.clicked.connect(self._reset_touch)
        return box

    def _show_touch_settings(self) -> None:
        t = self.touch_settings
        for check, value in ((self.touch_check, t.enabled), (self.touch_relative_check, t.relative)):
            check.blockSignals(True)
            check.setChecked(value)
            check.blockSignals(False)
        self.touch_relative_check.setEnabled(t.enabled)
        for name, *_, scale, _ in self.TOUCH_FIELDS:
            spin = self.touch_spins[name]
            spin.blockSignals(True)
            spin.setValue(getattr(t, name) * scale)
            spin.blockSignals(False)
            spin.setEnabled(t.enabled)

    def _on_touch_changed(self, *_) -> None:
        t = self.touch_settings
        t.enabled = self.touch_check.isChecked()
        t.relative = self.touch_relative_check.isChecked()
        self.touch_relative_check.setEnabled(t.enabled)
        for name, *_, scale, _ in self.TOUCH_FIELDS:
            setattr(t, name, round(self.touch_spins[name].value() / scale, 9))
            self.touch_spins[name].setEnabled(t.enabled)

    def _reset_touch(self) -> None:
        for name, value in asdict(MaintainTouchSettings()).items():
            setattr(self.touch_settings, name, value)
        self._show_touch_settings()

    # ---- click press -------------------------------------------------------------------

    # (field, label, min, max, step, decimals, suffix, scale shown / stored, tooltip)
    PRESS_FIELDS = (
        ("approach_speed", "Approach speed", 0.0, 50.0, 0.5, 1, " mm/s", 1000.0,
         "Speed of the guarded move along the press axis until the fingertip touches"),
        ("contact_ratio", "Contact level", 0.0, 1.0, 0.05, 2, " × peak", 1.0,
         "Fingertip force that counts as contact: no-contact force + this x (recorded peak - "
         "no-contact force)"),
        ("max_travel", "Max approach", 0.0, 50.0, 0.5, 1, " mm", 1000.0,
         "Largest approach from where the region starts before giving up on contact"),
        ("force_ramp", "Force ramp", 0.0, 5.0, 0.05, 2, " × peak/s", 1.0,
         "How fast the desired fingertip force grows while pressing, in recorded peaks per s"),
        ("max_force_ratio", "Max force", 0.0, 5.0, 0.1, 2, " × peak", 1.0,
         "Cap of the desired fingertip force, as a multiple of the recorded peak"),
        ("press_gain_q", "Press gain", 0.0, 5.0, 0.01, 2, " rad/s per peak", 1.0,
         "How fast the joint goals move past contact (along J^T d, so the force points along "
         "the press axis) per recorded peak of missing force"),
        ("max_press_q", "Max press offset", 0.0, 2.0, 0.05, 2, " rad", 1.0,
         "Largest press offset of the joint goals past where contact was made"),
        ("max_joint_offset", "Max joint offset", 0.0, 2.0, 0.05, 2, " rad", 1.0,
         "Largest press offset of any one joint"),
        ("max_wait", "Max wait", 0.0, 30.0, 0.5, 1, " s",
         1.0, "Longest wait for contact, and again for the click, before retracting"),
        ("sat_effort", "Current limit at", 0.0, 2000.0, 10.0, 0, "", 1.0,
         "leap_state effort of a joint at its current limit (0: off). There the press stops "
         "pushing deeper: more goal adds no force, it only turns it sideways"),
        ("sat_hold_s", "Max time at limit", 0.0, 10.0, 0.1, 1, " s", 1.0,
         "Longest time at the current limit without a click before giving up"),
        ("slip_shift", "Slip: pad shift", 0.0, 20.0, 0.1, 1, " mm", 1000.0,
         "The contact spot moving this far on the fingertip pad is a slip"),
        ("button_travel", "Slip: along d", 0.0, 30.0, 0.5, 1, " mm", 1000.0,
         "The fingertip moving further than this along the axis while the force falls back is "
         "a slip (a button gives way a few mm)"),
        ("slip_across", "Slip: across d", 0.0, 30.0, 0.5, 1, " mm", 1000.0,
         "The fingertip moving this far across the axis is a slip"),
        ("slip_backoff", "Slip back-off", 0.0, 1.0, 0.05, 2, " ×", 1.0,
         "Fraction of the press offset kept after a slip"),
        ("slip_tilt", "Slip re-aim", 0.0, 45.0, 1.0, 0, " °", 1.0,
         "How far the press axis turns against the slip"),
        ("max_slips", "Max slips", 0.0, 10.0, 1.0, 0, "", 1.0,
         "Slips before giving up"),
        ("retract", "Retract", 0.0, 30.0, 0.5, 1, " mm", 1000.0,
         "How far the fingertip backs off along the axis after the press"),
        ("release_s", "Release time", 0.0, 5.0, 0.05, 2, " s", 1.0,
         "Time of the retract, and of the blend back into the take"),
        ("click_min_ratio", "Click force drop from", 0.0, 2.0, 0.05, 2, " × peak", 1.0,
         "A sharp force drop counts toward a click only from at least this force"),
        ("click_advance", "Click give-way", 0.0, 10.0, 0.1, 1, " mm", 1000.0,
         "With the force drop, the fingertip must give way this far (along the way the joint "
         "springs unload) for a click without the click detector"),
        ("max_current", "Abort current", 0.0, 2000.0, 10.0, 0, "", 1.0,
         "Finger joint current (leap_state effort) that aborts the press at once (0: off)"),
    )

    def _build_press_box(self) -> QtWidgets.QGroupBox:
        self.press_check = QtWidgets.QCheckBox(f"Press in '{CLICK_PRESS_EVENT}' regions")
        self.press_check.setToolTip(
            f"During Play, replace the take over a '{CLICK_PRESS_EVENT}' region with a press of "
            "the fingertip along the recorded force until the pen clicks (needs Xela readings in "
            "the take and a Zero baseline before Play)"
        )
        self.press_spins: dict[str, QtWidgets.QDoubleSpinBox] = {}
        press_reset = QtWidgets.QPushButton("Reset to defaults")
        box = QtWidgets.QGroupBox("Click press (Play, applied immediately)")
        form = QtWidgets.QFormLayout(box)
        form.addRow(self.press_check)
        for name, label, lo, hi, step, decimals, suffix, _, tooltip in self.PRESS_FIELDS:
            spin = double_spin(lo, hi, step, decimals, suffix, tooltip)
            self.press_spins[name] = spin
            form.addRow(f"{label}:", spin)
        self.press_detector_check = QtWidgets.QCheckBox("Only the click detector ends a press")
        self.press_detector_check.setToolTip(
            "Count only click_topic as the click (a force drop with the fingertip giving way "
            "does not)"
        )
        form.addRow(self.press_detector_check)
        form.addRow("", press_reset)
        self._show_press_settings()
        for spin in self.press_spins.values():
            spin.valueChanged.connect(self._on_press_changed)
        self.press_check.toggled.connect(self._on_press_changed)
        self.press_detector_check.toggled.connect(self._on_press_changed)
        press_reset.clicked.connect(self._reset_press)
        return box

    def _show_press_settings(self) -> None:
        s = self.press_settings
        for check, value in (
            (self.press_check, s.enabled), (self.press_detector_check, s.require_click_detector)
        ):
            check.blockSignals(True)
            check.setChecked(value)
            check.blockSignals(False)
        self.press_detector_check.setEnabled(s.enabled)
        for name, *_, scale, _ in self.PRESS_FIELDS:
            spin = self.press_spins[name]
            spin.blockSignals(True)
            spin.setValue(getattr(s, name) * scale)
            spin.blockSignals(False)
            spin.setEnabled(s.enabled)

    def _on_press_changed(self, *_) -> None:
        s = self.press_settings
        s.enabled = self.press_check.isChecked()
        s.require_click_detector = self.press_detector_check.isChecked()
        self.press_detector_check.setEnabled(s.enabled)
        for name, *_, scale, _ in self.PRESS_FIELDS:
            kind = type(getattr(s, name))  # max_slips is a count
            setattr(s, name, kind(round(self.press_spins[name].value() / scale, 9)))
            self.press_spins[name].setEnabled(s.enabled)

    def _reset_press(self) -> None:
        for name, value in asdict(ClickPressSettings()).items():
            setattr(self.press_settings, name, value)
        self._show_press_settings()

    # ---- saving -------------------------------------------------------------------------

    def _save(self) -> None:
        if self._hand_read:
            self._saved_hand = {name: spin.value() for name, spin in self.hand_spins.items()}
        data = {
            "demo_dir": self.store.demo_dir,
            "gui": asdict(self.settings),
            "maintain_touch": asdict(self.touch_settings),
            "click_press": asdict(self.press_settings),
            "avoid_slip": asdict(self.avoid_slip),
            "hand": self._saved_hand,
        }
        try:
            os.makedirs(os.path.dirname(self._saved_path), exist_ok=True)
            tmp = self._saved_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self._saved_path)
        except OSError as e:
            self.save_status.setText(
                f"<span style='color:#d32f2f'>Could not save {self._saved_path}: {e}</span>"
            )
            return
        note = ""
        if not self._hand_read:
            note = (
                " (hand not read: kept the saved hand gains)" if self._saved_hand
                else " (hand not read: no hand gains saved)"
            )
        self.save_status.setText(f"Saved to {self._saved_path}{note}")
        self.node.get_logger().info(f"Saved settings to '{self._saved_path}'")

    # ---- hand node ----------------------------------------------------------------------

    def _set_hand_enabled(self, on: bool) -> None:
        for spin in self.hand_spins.values():
            spin.setEnabled(on)
        self.apply_btn.setEnabled(on)

    def _status(self, text: str, error: bool = False) -> None:
        self.hand_status.setText(f"<span style='color:#d32f2f'>{text}</span>" if error else text)

    def _reload_hand(self) -> None:
        if not self.node.hand_params_ready():
            self._set_hand_enabled(False)
            self._status(f"Waiting for {self.node.hand_node} ...")
            self._retry.start(self.RETRY_MS)
            return
        self._status("Reading parameters ...")
        names = ["compliant"] + [name for name, *_ in HAND_PARAMS]
        self.node.get_hand_params(names, self._hand_loaded.emit)

    def _on_hand_loaded(self, result) -> None:
        if isinstance(result, Exception):
            self._set_hand_enabled(False)
            self._status(f"Could not read parameters: {result}", error=True)
            return
        missing = [name for name, *_ in HAND_PARAMS if result.get(name) is None]
        if missing:
            self._set_hand_enabled(False)
            self._status(
                f"{self.node.hand_node} does not have {', '.join(missing)} "
                "(rebuild leap_hand and restart it)",
                error=True,
            )
            return
        for name, spin in self.hand_spins.items():
            spin.setValue(float(result[name]))
        self._hand_read = True
        self._hand_compliant = bool(result.get("compliant"))
        self._set_hand_enabled(self._hand_compliant)
        if self._hand_compliant and self._apply_saved_hand:
            # First time the hand is found: send it the saved gains.
            self._apply_saved_hand = False
            for name, value in self._saved_hand.items():
                self.hand_spins[name].setValue(value)
            self._status("Applying the saved gains ...")
            self._apply_hand()
        elif self._hand_compliant:
            self._status("Loaded from the hand.")
        else:
            self._status(
                f"{self.node.hand_node} is not in compliant mode, so these have no effect "
                "(launch with compliant:=true)."
            )

    def _apply_hand(self) -> None:
        if not self.node.hand_params_ready():
            self._status(f"{self.node.hand_node} is not running.", error=True)
            return
        self.apply_btn.setEnabled(False)
        self._status("Applying ...")
        values = {name: spin.value() for name, spin in self.hand_spins.items()}
        self.node.set_hand_params(values, self._hand_applied.emit)

    def _on_hand_applied(self, result) -> None:
        self.apply_btn.setEnabled(bool(self._hand_compliant))
        if isinstance(result, Exception):
            self._status(f"Apply failed: {result}", error=True)
        elif not result.successful:
            self._status(f"Rejected by {self.node.hand_node}: {result.reason}", error=True)
        else:
            self._status("Applied to the hand.")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, node: LeapStateListener) -> None:
        super().__init__()
        self.node = node
        saved_path = settings_file()
        try:
            saved = load_saved_settings(saved_path)
        except Exception as e:
            node.get_logger().warn(f"Could not load settings from {saved_path}: {e}")
            saved = {}
        settings = HoldSettings()
        touch_settings = MaintainTouchSettings()
        press_settings = ClickPressSettings()
        avoid_slip = AvoidSlipSettings()
        if saved:
            node.get_logger().info(f"Loaded settings from '{saved_path}'")
            apply_saved_hold_settings(settings, saved.get("gui", {}))
            apply_saved_hold_settings(touch_settings, saved.get("maintain_touch", {}))
            apply_saved_hold_settings(press_settings, saved.get("click_press", {}))
            apply_saved_hold_settings(avoid_slip, saved.get("avoid_slip", {}))
            if saved.get("demo_dir") and not node.demo_dir_given:
                node.demo_dir = os.path.expanduser(saved["demo_dir"])
        self.setWindowTitle(f"Record demonstration - {node.demo_dir}")
        self.resize(1600, 900)
        self.store = TakeStore(node.demo_dir)
        try:
            event_defs = load_event_definitions(node.events_file)
        except Exception as e:
            node.get_logger().warn(f"Could not load events from {node.events_file}: {e}")
            event_defs = {}
        self.create_tab = CreateTab(node, self.store, settings, touch_settings, press_settings)
        self.edit_tab = EditTab(node, self.store, event_defs, self.create_tab)
        self.compose_tab = ComposeTab(
            node, self.store, event_defs, self.create_tab, self.edit_tab, avoid_slip
        )
        self.demo_tab = DemonstrationTab(node, self.store)
        self.settings_tab = SettingsTab(
            node, self.store, settings, touch_settings, press_settings, saved, saved_path,
            avoid_slip,
        )
        self.create_tab.takes_changed.connect(self.compose_tab.refresh_takes)
        self.create_tab.takes_changed.connect(self.edit_tab.refresh_takes)
        self.edit_tab.delete_requested.connect(self._delete_take)
        self.create_tab.delete_requested.connect(self._delete_take)
        self.settings_tab.demo_dir_changed.connect(self._set_demo_dir)
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.create_tab, "Create")
        tabs.addTab(self.edit_tab, "Edit")
        tabs.addTab(self.compose_tab, "Compose")
        tabs.addTab(self.demo_tab, "Demonstration")
        tabs.addTab(self.settings_tab, "Settings")
        self.setCentralWidget(tabs)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.create_tab.refresh)
        self._timer.timeout.connect(self.edit_tab.refresh)
        self._timer.timeout.connect(self.compose_tab.refresh)
        self._timer.start(REFRESH_MS)
        # The MuJoCo window opens before this one and ends up behind it: bring it to the front
        # once it appears (checked every second for SIM_WINDOW_WAIT_S).
        self._sim_window_tries = 0
        self._sim_window_timer = QtCore.QTimer(self)
        self._sim_window_timer.setInterval(1000)
        self._sim_window_timer.timeout.connect(self._raise_sim_window)
        self._sim_window_timer.start()

    def _raise_sim_window(self) -> None:
        self._sim_window_tries += 1
        if raise_x11_window(SIM_WINDOW_TITLE):
            self._sim_window_timer.stop()
            self.node.get_logger().info(f"Brought the '{SIM_WINDOW_TITLE}' window to the front")
        elif self._sim_window_tries >= SIM_WINDOW_WAIT_S:
            self._sim_window_timer.stop()
            self.node.get_logger().warn(
                f"No '{SIM_WINDOW_TITLE}' window after {SIM_WINDOW_WAIT_S} s: is mujoco_sim_node "
                "running with its viewer?"
            )

    def _delete_take(self, path: str) -> None:
        self.create_tab.forget_take(path)
        self.edit_tab.forget_take(path)
        try:
            self.store.delete(path)
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "Delete take", f"Could not delete {path}:\n{e}")
        else:
            self.node.get_logger().info(f"Deleted take '{path}'")
        self.create_tab.reload_takes()
        self.edit_tab.refresh_takes()
        self.compose_tab.refresh_takes()

    def _set_demo_dir(self, path: str) -> None:
        self.create_tab.stop_all_playback()
        self.node.demo_dir = path
        self.store.demo_dir = path
        self.setWindowTitle(f"Record demonstration - {path}")
        self.node.get_logger().info(f"Saving demonstrations to '{path}'")
        self.create_tab.reload_takes()
        self.edit_tab.refresh_takes()
        self.compose_tab.refresh_takes()

    def closeEvent(self, ev) -> None:
        self.compose_tab.stop_hand()
        self.compose_tab.stop_replay()
        self.create_tab.stop_all_playback()
        if self.node.recording:
            answer = QtWidgets.QMessageBox.question(
                self, "Quit", "A recording is in progress. Save it before quitting?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
            )
            if answer == QtWidgets.QMessageBox.Cancel:
                ev.ignore()
                return
            if answer == QtWidgets.QMessageBox.Save:
                self.create_tab.stop_recording()
            else:
                video = self.node.stop_recording().video
                if video:
                    os.remove(video)
        self.create_tab.shutdown_commanding()
        self.create_tab.release_stiff_joints()
        self.create_tab.close_video()
        self.edit_tab.close_video()
        self.compose_tab.stop_sim()
        self.compose_tab.close_video()
        self.demo_tab.close_video()
        super().closeEvent(ev)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LeapStateListener()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    # Without an explicit version Qt reports OpenGL 2.0 and pyqtgraph.opengl refuses to draw.
    fmt = QtGui.QSurfaceFormat()
    fmt.setVersion(2, 1)
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)
    app = QtWidgets.QApplication(sys.argv[:1])
    window = MainWindow(node)
    window.show()
    signal.signal(signal.SIGINT, lambda *_: window.close())
    wake = QtCore.QTimer()  # lets the Python interpreter handle SIGINT while Qt runs
    wake.timeout.connect(lambda: None)
    wake.start(200)
    try:
        code = app.exec_()
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
