#!/usr/bin/env python3
"""Record per-finger LEAP hand demonstrations from ``/leap_state`` and group them by pen box.

Create tab: one live plot per finger, each with its own Record and Play controls. A finger's
Record saves a take of that finger only, named after the text box next to it (a timestamped
default is filled in). Takes (the full hand
is stored alongside for reference) go to ``<demo_dir>/fingers/<finger>/<name>.npz``. The camera
feed of the take is written to ``<demo_dir>/camera/<name>.mp4``; every take stores its path as
``video`` and the frame times as ``video_t`` (same time axis as ``t``). The SAM 3 mask and pen
box from ``bounding_box_sam`` (``sam_prefix``) are drawn on a frame only when their stamp is
that frame's stamp. Every SAM frame's best detection is collected while recording; one frame is
kept for the take (``pen_box_selection``): of the frames matching a camera frame, boxes much
smaller than usual (a hand in front of the pen) are left out, and the box with the highest mean
overlap (IoU) with the others is chosen. It is stored as ``sam_t`` / ``sam_mask`` /
``sam_boxes``. Index, Middle and
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
its takes; Index, Middle and Ring list only the takes with the pen box of the Thumb take picked
(all of them when it has no pen box; a take played from the Compose tab is listed for its play
whatever its box), the box named next to the finger; its plots (joints, and fingertip taxel magnitudes when the take has Xela readings)
show the whole take and the play bar (or the plot cursor) scrubs through
it, with the camera recording and the FK taxels / Xela forces of the take following. As in the bag viewer,
an event from ``events_file`` (default: installed ``events.json``) whose ``tab`` (a name or a
list) has "edit" is added at the play bar position; events are bookmarked on the play bar and the plot, listed next to the plot (click
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
Play on hand only starts once the touch baseline has been set on purpose: with Set touch
baseline (next to it) or Zero on the Create / Edit tab, with the fingertips touching nothing
(``HandView.zeroed_at``); otherwise a warning says so. The automatic baseline (the first Xela
reading the GUI got) does not count.
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
The recordings are played back on the Demonstration tab.
Combinations panel (right): every combination of one edited take per finger with the bounding
box picked (the fingers with takes), listed again when another box is picked. Check in sim plays each in a headless MuJoCo of the
sim's model (``sim_collision``: same model, actuators and finger contact rule as
``mujoco_sim_node``, faster than real time, in a background thread), as Test in sim plays them
but from each take's ``episode_start`` (no random start), with Ring held as in Test in sim. A
combination is valid when no two fingers touch while it plays; Valid only lists just those. The
results are saved in ``<demo_dir>/combinations.json`` and reused while the takes are unchanged.
A combination whose Middle and Ring fingers collide while Ring has no take (it holds the first
take's pose) is modified: ``rf_rot`` is moved the least it takes (``SimCollisionChecker.clear_pair``,
both ways in 0.02 rad steps within its range) for the collision to go without a new one, and
Ring is held there for the whole demonstration. It is listed as [modified], with the joint's old
and new value (``modified`` in the JSON, with the touches before). With a modified combination
picked (and its takes selected), Test in sim and Play in sim hold Ring there, and Play on hand
moves Ring to that pose with the other fingers' starts and holds it until the end; the recording
gets ``meta["modified"]`` and is tagged [modified] on the Demonstration tab.
Each combination lists its Play on hand recordings (those whose ``meta["takes"]`` are its takes,
by finger and take name) and how many are labelled success / fail (Demonstration tab, or
``label_playbacks``), counted again whenever the tab is shown.
Picking a combination shows where the fingers touched and selects its takes in the finger
columns; Play in sim plays it to the live sim. The box cannot be changed while Check in sim runs.
During Play on hand, the slip lights (Index, Middle, Ring) show each finger's contact: grey not
in contact, green in contact (its ``maintain_touch`` holding), red for ``SLIP_LIGHT_S`` after a
slip (``slip_detection``: the contact spot moving on the pad, or the fingertip force falling
away), with a count of the slips;
the slips are saved in the recording's ``meta["slips"]``. With Avoid slip on, Index, Middle and
Ring press harder so the Thumb cannot push the pen out (``AvoidSlipSettings``, next to the
switch, saved with Save settings): the fingers holding contact get ``before_thumb`` more hold
force when the Thumb starts, and every slip of a finger adds ``per_slip``, up to ``max_extra``
(``TouchPress.extra_force``; needs Zero, as the force is held from the live Xela).
Save preset stores the three values under a name (``avoid_slip_presets.json``, next to the
settings file); picking a preset in the dropdown next to it loads them, and each recording
names the preset its values match in ``meta["avoid_slip_preset"]`` ("" for custom values).
A take's ``random_episode_start`` regions (added on the Edit tab) mark where its episode may
start: every Test in sim and Play on hand starts it at a time drawn uniformly from them (the
part between ``episode_start`` and ``terminal``) instead of at ``episode_start``; the Edit tab's
own Play still starts at ``episode_start``.
The Click press row shows where the Thumb is in a Play on hand: moving to its start, held at
it, playing its take, then its ``click_press`` state machine (approach, press, retract,
release), the take on to ``terminal`` and finished; the current stage is highlighted, with the
press's live status (force / target, slips) and how it ended (clicked, no click, kept sliding,
... as ``click_press_labels``), which stays shown until the next one.
Under the selected take's first frame, a Live view shows the camera with the selected bounding
box drawn on it, in yellow, to line the pen up with it before playing.

Demonstration tab: plays back the Compose tab's Play on hand recordings without sending
anything to the hand. Keys: Space plays / pauses, Left / Right move the play bar ``SEEK_FRACTION``
(1 %) of the recording back / forward, ] jumps to the Thumb's first contact with the pen, and
pressed again to the start of the last ``LAST_PART`` (5 %) of the recording (alternating from
then on; [ goes through them the other way) (``thumb_contact_time``: its largest fingertip taxel
rising ``THUMB_CONTACT_RISE`` above its level when the Thumb starts; marked "TH contact" on its
plots), Up / Down pick the previous / next recording. Above the list, the Success / Failed filters (its mark) and the Processed /
Unprocessed ones (``is_processed``, as on the Processing tab): a recording is listed when it
matches a ticked mark and a ticked state (a group with none ticked does not filter; none are
ticked at first, so every recording is listed). Under the list, Success and Fail (keys S and F) mark the picked
recording (pressing the lit one again clears it), saved next to it as ``<box>_<n>.label.json`` as ``label_playbacks``
does; Delete removes it with its camera, audio and label files. Pick a recording and press Play (or drag the play bar): plots
of each finger's joint positions, velocities and efforts (``leap_state``) with the run's
timeline and slips marked, each finger's fingertip taxel magnitudes (recorded Xela, from the
run's baseline), its camera recording with the bounding box drawn on it (the Bounding box button over it, on
by default, turns it off; on the Processing tab too), and the FK
taxels with the recorded Xela readings follow the play bar. The microphone recording is plotted
under the joints and, while playing, heard on the Audio output picked (named as Ubuntu's sound settings name it, e.g. "Front
Headphones - USB Audio (hw:1,1)", ``audio_output_label``; remembered between runs;
Test plays a beep). With Stream to sim (on by default)
the recorded joint positions are also sent to the MuJoCo sim on ``sim_cmd_topic``, converted to
sim joints as ``convert_hardware_to_sim`` does. Play on hand saves the camera next to its
recording, as ``<box>_<n>.mp4``.

Processing tab: the Play on hand recordings marked success or failure on the Demonstration tab.
Above the list, the Success / Failure filters (its mark) and the Processed / To be confirmed /
Needs manual label ones (its state; processed: an ``episode_start`` and a ``terminal`` event, not to be
confirmed, or ``processed`` set in its ``<box>_<n>.label.json``): a recording is listed when
it matches a ticked mark and a ticked state (a group with none ticked does not filter, e.g.
Failure + Processed lists the processed failures); each
entry shows its mark and [processed] when it is. The picked recording plays back, in the
bottom two thirds of the middle, as on the Demonstration tab (play bar, plots, camera, FK
taxels, audio, Stream to sim and its keys but S / F; it is marked and deleted on the
Demonstration tab); the top third is left empty. Under the play bar, the Reward (Process reward's
values at the play bar's time: Every step from ``episode_start`` to ``terminal``, Success /
Fail at ``terminal``) and the Contact and Slip lights show the Compose tab's lights at the play bar's time: the slips are the recording's
``meta["slips"]``; the contacts
(``recorded_contacts``) come from the ``maintain_touch_trace`` / ``click_press_trace`` of each
finger's own play saved with it, lined up by the take time the trace's first region starts at
(a finger whose play is not found shows no contact).
Events whose ``tab`` has "processing" are added under the lights as on the Edit tab (picker,
Add event / Start and End event, Cancel), marked on the play bar and the plots, listed next to
the plots (click to seek, Edit renames, Delete) and saved in the recording's label file as
``events`` (as a take's). A listed recording with no ``events`` saved gets ``episode_start``
at its first command (``cmd_t``) by default; deleting it is kept (an empty list).
The To be confirmed filter lists the recordings with an event found by an automation (Process
click) and not confirmed yet; while it is ticked, the row under the list (where Refresh was;
Refresh is now over the camera) picks the event (``AUTOMATION_EVENTS``) and Confirm keeps the
picked recording's one, Reject deletes it (keys C / R; the recording stays a success, tagged
[needs manual label] until the event is marked by hand, ``rejected`` in its label file), and
the next recording is picked; a
``Thumb_is_clicking_the_pen`` event (marked by hand, found by Process click or confirmed)
gets ``terminal`` and ``success`` at its end if the recording has none (to be confirmed and
rejected with a found one). Process click is
in the Automation section, the top quarter of the empty space over the player. It
(``click_processing``) cuts the confirmed
``Thumb_is_clicking_the_pen`` events (at most ``click_processing.MAX_SAMPLES``, 10, spread over
them) out of their recordings' audio as click samples and sends
them with each recording's audio to click_detector's ``~/detect`` service
(``click_detect_service``, leapxela_sparshskin_msgs/DetectClicks), which searches the
successful recordings without one (and not searched before, ``process_click`` in the label
file) while the Thumb plays; the click it finds is added as an
event with ``params["to_be_confirmed"]``, which Confirm clears and Reject (or Delete under
the events) removes. It runs in the background; pressing it again (Stop) stops it.
Over Automation, Episodes (``episode_processing``) shows the truncation length (saved with the
recordings in ``processing.json``) and the longest processed successful episode (its
``episode_start`` to ``terminal``); Use longest sets the truncation length to it. Process
failure (in Automation) marks ``terminal`` and ``truncated`` at ``episode_start`` + the
truncation length on every failed recording without a ``terminal`` (moving the ones it marked
before when the length changed); recordings that end earlier get ``terminal`` and ``fail`` at
their last timestep. Sparsh-skin transform (in Automation) asks sparsh_skin_transformation's
``~/transform`` service (``sparsh_transform_service``, leapxela_sparshskin_msgs/
SparshSkinTransform) to preprocess every episode as Sparsh-skin does (``sparsh_processing``)
into ``<recordings>/sparsh_skin/`` for the LEQ_DV3 world model; it runs in the background.
Process reward sets the
rewards of every episode written (and of those the transform writes, ``processing.json``):
Success at the last timestep of a success, Fail at the last timestep of a failure, Every step
at every other timestep. The dropdown next to the transform picks the Baseline tab recording whose no-contact baseline every
episode uses (remembered; the newest until one is picked), tagged ``[Sparsh-skin]`` in the
dropdown and in the Baseline tab's list (whose Use for Sparsh-skin picks it too).
Process for DreamerV3 (the progress bar under it follows every Automation run) converts those episodes into DreamerV3 replay
chunks in ``<recordings>/DV3/`` (``dv3_processing``, as LEQ_DV3's ``convert_episodes.py``
does), to copy to ``LEQ_DV3/data/leap/<task>/``.
Keys: Space plays / pauses, E adds the picked event (a duration event: the first press starts
it, the second ends it), C / R confirm / reject the event to be confirmed, Left / Right move the play bar ``SEEK_FRACTION`` (1 %) of
the recording back / forward, [ / ] jump to the start of the previous / next event, Up / Down
pick the previous / next recording.

Analysis tab: the coverage and results of the pen boxes. Every pen box (of the edited takes, and
of Play on hand recordings whose takes are gone) is drawn on the live camera (the first frame of
the picked box's take when there is no live one), coloured by the success rate of its labelled
recordings (red 0 % to green 100 %, grey none labelled); the box picked is thicker, outlined in
yellow. A box's Hide button (after its success rate) leaves it off the camera view (it stays
in the table and the counts); the hidden boxes are remembered between runs. A table lists the
boxes with the takes that have them (the box their Pose switch shows), their Play on hand
recordings (counted for the box the recording's takes have now, the Thumb's first; the box
saved with it only when its takes are gone), success, fail and not labelled counts (``<box>_<n>.label.json``) and success rate; picking one
shows its totals and a breakdown by the combination of takes each recording played.

Click press outcome: how the Thumb's ``click_press`` ended in each Play on hand recording
(``click_press_labels``: clicked, aborted_no_click, aborted_kept_sliding, aborted_no_contact,
...), read from the Thumb's own play recording and saved in the recording's label file
(``click_press``). The Demonstration tab shows it in the list and the title, the Analysis tab
counts it per box and per combination; recordings without one are labelled as the tabs list
them (``ros2 run mechanical_pen_data_collection label_click_press`` labels them all).

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
Backup to Nextcloud (``nextcloud_backup``): the server, user, app password, remote folder and
the local folder to back up (the recordings folder by default); Sync uploads, in the
background, the local folder and the app's own files (``backup_extras``: the settings folder,
the event definitions, the click detector's templates and this GUI's Qt preferences, under
``<remote folder>/_app``), every file the server does not have yet with the same size and time (nothing is
deleted on either side) with a progress bar (press again to stop); Test connection logs in.
Pull lists the backup and shows where each part of it (the recordings, each ``_app`` item;
events.json both to the source, kept by the next build, and to the installed copy the app
reads) will be downloaded, with how many files are new / changed / newer locally / the same;
the destinations can be changed or a part left out before it downloads (newer local files are
kept unless asked; restart the app to load restored settings).
Save settings keeps them, the app password only with Remember password (in plain text; it
is left out of the settings file Sync uploads, ``without_backup_password``).
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

import array
import functools
import itertools
import json
import os
import queue
import re
import signal
import sys
import threading
import wave
import time
import warnings
from collections import Counter, deque
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Callable
from urllib.parse import urlparse

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
from leapxela_sparshskin_msgs.srv import DetectClicks, PlanHandPose, SparshSkinTransform
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
    APPROACH as CLICK_APPROACH,
    DONE as CLICK_DONE,
    PRESS as CLICK_PRESSING,
    RELEASE as CLICK_RELEASE,
    RETRACT as CLICK_RETRACT,
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
    update_label,
)
from mechanical_pen_data_collection import click_processing, episode_processing, nextcloud_backup
from mechanical_pen_data_collection import dv3_processing, sparsh_processing
from mechanical_pen_data_collection.joint_conversion import HardwareToSim
from push_button_pen_click_detection import audio_utils
from mechanical_pen_data_collection.click_processing import (
    CLICK_END_EVENTS,
    CLICK_EVENT,
    TO_BE_CONFIRMED,
    WITH,
)
from mechanical_pen_data_collection.click_press_labels import (
    ABORTED_KEPT_SLIDING,
    ABORTED_NO_CLICK,
    ABORTED_NO_CONTACT,
    CLICKED,
    PAIR_WINDOW_S,
    SHORT as PRESS_SHORT,
    UNKNOWN as PRESS_UNKNOWN,
    ThumbPlays,
    classify_trace,
    click_press_label,
)
from mechanical_pen_data_collection.pen_box_selection import (
    REF_QUANTILE,
    SHRINK_RATIO,
    choose_consistent_box,
)
from mechanical_pen_data_collection.sim_collision import (
    CollisionResult,
    SimCollisionChecker,
    Touch,
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
# How long Process click waits for click_detector's ~/detect to answer one recording (s).
CLICK_DETECT_TIMEOUT_S = 60.0
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
# Tabs an events.json event can be added on (its ``tab``).
EDIT_TAB, PROCESSING_TAB = "edit", "processing"


def event_tabs(info: dict) -> set[str]:
    """The tabs an events.json event can be added on: its ``tab``, a name or a list of them
    (none without one)."""
    tab = info.get("tab", [])
    return {tab} if isinstance(tab, str) else set(tab)


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


# The Avoid slip values a Compose tab preset holds (not ``enabled``).
AVOID_SLIP_VALUES = ("before_thumb", "per_slip", "max_extra")


def avoid_slip_presets_file() -> str:
    """``<colcon workspace>/settings/<package>/avoid_slip_presets.json``, next to the settings."""
    return os.path.join(os.path.dirname(settings_file()), "avoid_slip_presets.json")


def load_avoid_slip_presets(path: str) -> dict[str, dict[str, float]]:
    """Read the Avoid slip presets, {name: {before_thumb, per_slip, max_extra}} ({} if none)."""
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    return {
        str(name): {k: float(values[k]) for k in AVOID_SLIP_VALUES}
        for name, values in data.items()
        if isinstance(values, dict) and all(k in values for k in AVOID_SLIP_VALUES)
    }


def save_avoid_slip_presets(path: str, presets: dict[str, dict[str, float]]) -> None:
    """Write the Avoid slip presets to ``path`` (replaced atomically)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(presets, f, indent=2)
    os.replace(tmp, path)


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


def xela_sensor_temps(sensor) -> np.ndarray:
    """(taxels,) temperature of each taxel of a Xela ``SensorFull``: its own when the sensor
    sends one per taxel, else the sensor's mean, else NaN (xela_server sends none)."""
    n, temps = len(sensor.taxels), np.asarray(sensor.temp, dtype=np.float64)
    if len(temps) == n:
        return temps
    return np.full(n, temps.mean() if len(temps) else np.nan)


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
        # click_detector's service finding clicks in given audio from a few click samples.
        self.click_detect_service = self.declare_parameter(
            "click_detect_service", "/click_detector/detect"
        ).value
        self._click_detect = self.create_client(DetectClicks, self.click_detect_service)
        # sparsh_skin_transformation's service writing the episodes for the world model.
        self.sparsh_transform_service = self.declare_parameter(
            "sparsh_transform_service", "/sparsh_skin_transformation/transform"
        ).value
        self._sparsh_transform = self.create_client(
            SparshSkinTransform, self.sparsh_transform_service
        )
        # Its progress ({"done", "total", "text"} JSON), passed to ``on_sparsh_progress``.
        self.on_sparsh_progress: Callable[[int, int, str], None] | None = None
        self.create_subscription(
            String,
            self.declare_parameter(
                "sparsh_progress_topic", "/sparsh_skin_transformation/progress"
            ).value,
            self._on_sparsh_progress, 10,
        )
        # hand_ik's service: paths between hand poses that keep the fingers apart (mink).
        self.hand_ik_service = self.declare_parameter(
            "hand_ik_service", "/hand_ik/plan_to_pose"
        ).value
        self._hand_ik = self.create_client(PlanHandPose, self.hand_ik_service)
        # Microphone stream of push_button_pen_click_detection's audio_publisher.
        self.audio_topic = self.declare_parameter("audio_topic", "/audio").value
        self.audio_rate = 48000  # updated from <audio_topic>/info
        self._play_audio: list[tuple[float, np.ndarray]] | None = None  # (received, samples)
        self.counts_per_unit = float(self.declare_parameter("counts_per_unit", 1000.0).value)
        # Finger-finger contacts shallower than this (m) are not collisions (Combinations).
        self.min_contact_depth = float(self.declare_parameter("min_contact_depth", 0.0005).value)
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
        self._rec_sam_mask: list[np.ndarray] = []  # PNG-encoded (one per SAM frame)
        self._rec_sam_boxes: list[list] = []
        self._rec_sam_score: list[float] = []
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
        # (T,) temperature of each taxel's sensor, alongside ``_xela_history`` (NaN: none sent).
        self._xela_temp_history: deque[np.ndarray] = deque(maxlen=HISTORY_LEN)
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

    def click_detect_ready(self) -> bool:
        return self._click_detect.service_is_ready()

    def detect_clicks(
        self, samples: list[np.ndarray], audio: np.ndarray, sr: int
    ) -> list[tuple[float, float]]:
        """Pen clicks in ``audio`` by click_detector's ``~/detect`` with ``samples`` as its
        templates, without press / release pairing: [(s from the start of ``audio``, score)].
        Waits for the answer, so it is not called on the executor's thread; raises if the
        service fails or does not answer within ``CLICK_DETECT_TIMEOUT_S``."""
        def floats(x: np.ndarray) -> array.array:
            out = array.array("f")
            out.frombytes(np.asarray(x, dtype=np.float32).tobytes())
            return out

        request = DetectClicks.Request(
            samples=floats(np.concatenate(samples)),
            sample_lengths=[len(s) for s in samples],
            audio=floats(audio), sample_rate=int(sr), threshold=0.0, pair=False,
        )
        answered = threading.Event()
        future = self._click_detect.call_async(request)
        future.add_done_callback(lambda _: answered.set())
        if not answered.wait(CLICK_DETECT_TIMEOUT_S):
            future.cancel()
            raise TimeoutError(
                f"{self.click_detect_service} did not answer in {CLICK_DETECT_TIMEOUT_S:.0f} s"
            )
        response = future.result()
        if not response.success:
            raise RuntimeError(f"{self.click_detect_service}: {response.message}")
        return list(zip(response.times, response.scores))

    def hand_ik_ready(self) -> bool:
        return self._hand_ik.service_is_ready()

    def plan_hand_pose(self, names: list[str], start, goal, done) -> None:
        """Asks hand_ik for a path of sim joints ``names`` from ``start`` to ``goal``; ``done``
        gets ((steps, len(names)) sim angles, dt, response) or an exception, on the
        executor's thread."""
        def convert(response):
            if not response.success:
                raise RuntimeError(f"{self.hand_ik_service}: {response.message}")
            path = np.asarray(response.trajectory, dtype=float).reshape(-1, len(names))
            return path, float(response.dt), response

        request = PlanHandPose.Request(
            joint_names=list(names), start=[float(v) for v in start],
            goal=[float(v) for v in goal],
        )
        self._call(self._hand_ik, request, convert, done)

    def sparsh_transform_ready(self) -> bool:
        return self._sparsh_transform.service_is_ready()

    def sparsh_transform(self, recordings_dir: str, baseline_file: str):
        """sparsh_skin_transformation's ``~/transform`` of every episode in ``recordings_dir``
        (into its ``sparsh_skin`` folder) with the baseline of ``baseline_file``; waits for the
        answer (minutes), so it is not called on the executor's thread. Raises if the service
        fails."""
        request = SparshSkinTransform.Request(
            recordings_dir=recordings_dir, baseline_file=baseline_file
        )
        answered = threading.Event()
        future = self._sparsh_transform.call_async(request)
        future.add_done_callback(lambda _: answered.set())
        answered.wait()
        response = future.result()
        if not response.success:
            raise RuntimeError(f"{self.sparsh_transform_service}: {response.message}")
        return response

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

    def _on_sparsh_progress(self, msg: String) -> None:
        callback = self.on_sparsh_progress
        if callback is None:
            return
        try:
            p = json.loads(msg.data)
            callback(int(p["done"]), int(p["total"]), str(p.get("text", "")))
        except (ValueError, KeyError, TypeError):
            pass

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
        # Every frame's detection is recorded; one is chosen for the take when it stops.
        if self._recording:
            self._rec_sam_t.append(header_stamp)
            ok, png = cv2.imencode(".png", np.ascontiguousarray(mask, dtype=np.uint8))
            self._rec_sam_mask.append(png if ok else None)
            self._rec_sam_boxes.append([best_box])
            self._rec_sam_score.append(score)
        # Only the frame with the highest probability is shown.
        if self._sam_best_score is not None and score <= self._sam_best_score:
            return
        self._sam_best_score = score
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
        temps = np.concatenate([xela_sensor_temps(s) for s in msg.sensors] or [np.empty(0)])
        stamp = self._stamp(msg.header)
        now = self.get_clock().now().nanoseconds * 1e-9
        if abs(stamp - now) > XELA_MAX_CLOCK_OFFSET_S:
            # xela_server stamping with another clock would misalign the takes and the plots.
            stamp = now
        with self._lock:
            self._xela = (self._xela[0] + 1, readings)
            self._xela_history.append((stamp, readings))
            self._xela_temp_history.append(temps)
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

    def xela_temps_since(
        self, seq: int
    ) -> tuple[int, list[tuple[float, np.ndarray, np.ndarray]]]:
        """``xela_since`` with each message's (T,) taxel temperatures:
        (latest sequence number, (stamp, raw readings, temperatures) after ``seq``)."""
        with self._lock:
            latest = self._xela[0]
            n = min(latest - seq, len(self._xela_history))
            if n <= 0:
                return latest, []
            items = list(zip(self._xela_history, self._xela_temp_history))[-n:]
        return latest, [(stamp, readings, temps) for (stamp, readings), temps in items]

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
            self._rec_sam_score = []
            self._sam_best_score = None
            self._video_path = video_path
            self._recording = True

    def _choose_sam_frame(self, sam_boxes: list, scores: list[float]) -> int:
        """Index of the recorded SAM frame whose pen box is most like the others
        (``choose_consistent_box``), leaving out boxes that shrank (a hand in front of the
        pen); the highest score if no box has corners."""
        frames, corners = [], []
        for i, boxes in enumerate(sam_boxes):
            pts = _detection_corners(boxes[0]) if boxes else None
            if pts is not None:
                frames.append(i)
                corners.append(pts)
        choice = choose_consistent_box(corners, [scores[i] for i in frames])
        if choice is None:
            return int(np.argmax(scores))
        k = frames[choice.index]
        self.get_logger().info(
            f"Pen box of the take: frame {k + 1} of {len(sam_boxes)} with a SAM box "
            f"(score {scores[k]:.2f}), mean IoU {choice.mean_iou:.2f} with the {choice.kept - 1} "
            f"other(s); {choice.shrunken} shrunken box(es) left out (area under "
            f"{SHRINK_RATIO:.0%} of the {REF_QUANTILE:.0%} quantile, {choice.ref_area:.0f} px^2)"
        )
        return k

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
            sam_png = list(self._rec_sam_mask)
            sam_boxes = list(self._rec_sam_boxes)
            sam_score = list(self._rec_sam_score)
            self._rec_sam_t, self._rec_sam_mask, self._rec_sam_boxes = [], [], []
            self._rec_sam_score = []
        if len(video_t) and len(sam_t):
            keep = [i for i, s in enumerate(sam_t) if stamp_matches(video_t, float(s))]
            sam_t = sam_t[keep]
            sam_png = [sam_png[i] for i in keep]
            sam_boxes = [sam_boxes[i] for i in keep]
            sam_score = [sam_score[i] for i in keep]
        sam_mask = np.empty((0, 0, 0), np.uint8)
        if len(sam_t):
            # One frame is kept: the box most like the others, shrunken ones left out.
            k = self._choose_sam_frame(sam_boxes, sam_score)
            sam_t, sam_boxes = sam_t[k:k + 1], sam_boxes[k:k + 1]
            if sam_png[k] is not None:
                sam_mask = cv2.imdecode(sam_png[k], cv2.IMREAD_UNCHANGED)[None]
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

    def reread(self) -> None:
        """The next ``read`` returns its frame even if it is the one shown."""
        self._index = -1

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
            center - half_w * along + half_h * across,
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
        # time.time() the baseline was last set with Zero (None: only the automatic one, taken
        # from the first reading, whatever the hand was touching then)
        self.zeroed_at: float | None = None
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

    def _zero(self) -> bool:
        """Uses the current reading as the no-contact baseline; False if there is none."""
        readings = self._valid_readings() if self._fk is not None else None
        if readings is None:
            return False
        self._baseline = readings.copy()
        self.zeroed_at = time.time()
        self._redraw()
        return True

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

    def stiff_joints_set_elsewhere(self) -> None:
        """Another tab (Baseline) set the hand's stiff_joints: the next update sends them."""
        self._stiff_sent = ("(set elsewhere)",)

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
        # Events this finger can be given: those of the Edit tab (``tab``) that apply to it
        # (``applied_to`` lists finger codes such as "IF").
        self._addable = {
            name: info for name, info in event_defs.items()
            if EDIT_TAB in event_tabs(info)
            and (not info.get("applied_to")
                 or finger.upper() in {
                     str(code).upper()
                     for code in (
                         [info["applied_to"]] if isinstance(info["applied_to"], str)
                         else info["applied_to"]
                     )
                 })
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
        # Index / Middle / Ring: only the takes with this pen box (the selected Thumb take's,
        # set by the Edit tab; None: all takes), and what the label says about it.
        self.box_filter: bytes | None = None
        self.box_filter_name = ""
        self.box_label = QtWidgets.QLabel()
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
        header.addWidget(QtWidgets.QLabel(f"<b>{label}</b>"))
        header.addWidget(self.box_label, 1)
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

    def fill_takes(self, include: str | None = None) -> None:
        """Lists the takes of this finger (only those with the ``box_filter`` pen box, and
        ``include`` whatever its box), keeping the selection if it is still listed."""
        keep = self.take_combo.currentData()
        self.take_combo.blockSignals(True)
        self.take_combo.clear()
        paths = self.store.list(self.finger)
        shown = [p for p in paths if self.box_filter is None or p == include
                 or self._box_key(p) == self.box_filter]
        for path in shown:
            self.take_combo.addItem(os.path.splitext(os.path.basename(path))[0], path)
        if self.box_filter is not None:
            self.box_label.setText(
                f"<span style='color:#9e9e9e'>box {self.box_filter_name}: "
                f"{len(shown)} of {len(paths)} takes</span>"
            )
            self.take_combo.setToolTip(
                f"Takes of this finger with the pen box of the selected Thumb take "
                f"({self.box_filter_name}), newest first"
            )
        else:
            self.box_label.setText(
                f"<span style='color:#9e9e9e'>{self.box_filter_name}</span>"
                if self.box_filter_name else ""
            )
            self.take_combo.setToolTip("Recorded takes of this finger, newest first")
        index = self.take_combo.findData(keep) if keep else 0
        self.take_combo.setCurrentIndex(max(index, 0))
        self.take_combo.blockSignals(False)
        self._load_selected()

    def _box_key(self, path: str) -> bytes | None:
        """pen_box_key of the take at ``path`` (None if it has no pen box)."""
        try:
            corners = recorded_take_pen_pose(self.store.load(path))
        except Exception:  # noqa: BLE001 - an unreadable take is left out
            return None
        return pen_box_key(corners) if corners is not None else None

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
        # The Thumb first: its take's pen box picks the takes the others list.
        self.panels["th"].fill_takes()
        self._apply_thumb_box(force=True)

    def _apply_thumb_box(self, force: bool = False) -> None:
        """Index, Middle and Ring list only the takes with the selected Thumb take's pen box
        (all of them if it has none); a finger playing keeps its take listed."""
        take = self.panels["th"].take
        corners = recorded_take_pen_pose(take) if take is not None else None
        key = pen_box_key(corners) if corners is not None else None
        if key is not None:
            owner = pen_box_owner(self.store, take)
            name = owner if owner == take.name else f"{owner} (via {take.name})"
        else:
            name = ("no Thumb take: all takes" if take is None
                    else f"{take.name} has no pen box: all takes")
        for finger in PEN_BOX_FROM_THUMB:
            panel = self.panels[finger]
            if not force and panel.box_filter == key and panel.box_filter_name == name:
                continue
            playing = self.create_tab.playback(finger) is not None and panel.take is not None
            panel.box_filter, panel.box_filter_name = key, name
            panel.fill_takes(include=panel.take.path if playing else None)

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
            # Not listed (e.g. another box than the Thumb take's): listed for this play.
            panel.fill_takes(include=path)
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
        """A finger's take changed: reload its pen box if its Pose switch is on; a new Thumb
        take changes the takes Index, Middle and Ring list."""
        if self._pose_finger == finger and self.panels[finger].pose_switch.isChecked():
            self._on_pose(finger, True)
        if finger == "th":
            self._apply_thumb_box()

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
    modified = "  [modified]" if meta.get("modified") else ""
    return f"{name}  {duration:.1f} s, {meta.get('ended', '?')}{modified}\n{when}{slip_text}"


def pair_text(pairs) -> str:
    """Finger pairs as "IF-MF, TH-IF"."""
    return ", ".join(f"{a.upper()}-{b.upper()}" for a, b in sorted(pairs))


def build_sim_plan(
    takes: list[FingerTake], spans: list[tuple[float, float]],
) -> tuple[list[str], np.ndarray, list[tuple[list[int], FingerTake, tuple[float, float], float]]]:
    """What Test in sim plays for ``takes`` (in ``FINGERS`` order) over their (start, terminal)
    ``spans``: hardware joint names, the whole hand of the first take where it starts (fingers
    without a take hold it), and per take (columns, take, span, delay): Index, Middle and Ring
    start at once, the Thumb once they are all done."""
    names = list(takes[0].hand_joint_names)
    base = np.array([
        np.interp(spans[0][0], takes[0].t, takes[0].hand_q[:, j])
        for j in range(takes[0].hand_q.shape[1])
    ])
    others_end = max(
        (abs(end - start) for take, (start, end) in zip(takes, spans) if take.finger != "th"),
        default=0.0,
    )
    parts = [
        (take_columns(names, take), take, span, others_end if take.finger == "th" else 0.0)
        for take, span in zip(takes, spans)
    ]
    return names, base, parts


# Compose tab Combinations: saved results, next to the fingers' takes.
COMBINATIONS_FILE = "combinations.json"
COMBO_VALID_COLOR = "#2e7d32"
COMBO_COLLIDE_COLOR = "#c62828"
COMBO_UNCHECKED_COLOR = "#9e9e9e"


@dataclass
class Combination:
    """One take of each finger, played together as Test in sim plays them (from each take's
    ``episode_start``), and whether the fingers collided in the sim (None: not checked)."""

    takes: list[FingerTake]  # FINGERS order
    result: CollisionResult | None = None
    error: str = ""
    # Modified: a held joint moved to clear a collision, kept for the whole demonstration:
    # {"joint", "from", "to" (hardware rad), "pair": the finger pair it clears}. ``before`` is
    # the result without it.
    fix: dict | None = None
    before: CollisionResult | None = None

    @property
    def key(self) -> tuple[str, ...]:
        return tuple(take.path for take in self.takes)

    @property
    def name(self) -> str:
        return " + ".join(take.name for take in self.takes)

    @property
    def recording_key(self) -> frozenset:
        """Its takes as Play on hand recordings name them (``recording_takes``)."""
        return frozenset((take.finger, take.name) for take in self.takes)

    def mtimes(self) -> dict[str, float]:
        out = {}
        for take in self.takes:
            try:
                out[take.path] = os.path.getmtime(take.path)
            except OSError:
                out[take.path] = 0.0
        return out

    def plan(self, spans: list[tuple[float, float]] | None = None):
        """Test in sim plan of the takes (from each ``episode_start``, or ``spans``), with the
        modified joint held at its new value."""
        spans = spans or [take_episode_span(take) for take in self.takes]
        names, base, parts = build_sim_plan(self.takes, spans)
        if self.fix is not None:
            base[names.index(self.fix["joint"])] = self.fix["to"]
        return names, base, parts

    def fix_text(self) -> str:
        fix = self.fix
        return (f"{fix['joint']} {fix['from']:.3f} -> {fix['to']:.3f} rad "
                f"({fix['to'] - fix['from']:+.3f}), held for the whole demonstration, against "
                f"the {pair_text([tuple(fix['pair'])])} collision")

    def valid(self, min_depth: float) -> bool | None:
        """No finger pair got ``min_depth`` (m) deep; None if not checked (or it failed)."""
        if self.result is None or self.error:
            return None
        return not self.result.collides(min_depth)

    def status_text(self, min_depth: float) -> str:
        if self.error:
            return f"error: {self.error}"
        if self.result is None:
            return "not checked"
        counted = self.result.counted(min_depth)
        if not counted:
            shallow = len(self.result.touches)
            return "valid" + (f" ({shallow} touch(es) under {min_depth * 1000:.2f} mm)"
                              if shallow else "")
        return "collides: " + ", ".join(
            f"{pair_text([pair])} from {touch.first_t:.2f} s (max {touch.depth * 1000:.2f} mm)"
            for pair, touch in sorted(counted.items(), key=lambda kv: kv[1].first_t)
        )


def load_combination_results(path: str) -> dict[tuple[str, ...], dict]:
    """Saved results by combination key (take paths), each with the takes' mtimes then."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {tuple(entry["takes"]): entry for entry in data.get("combinations", [])}


def combination_entry(combo: Combination, min_depth: float) -> dict:
    result = combo.result
    return {
        "takes": list(combo.key),
        "names": [take.name for take in combo.takes],
        "mtimes": combo.mtimes(),
        "valid": not result.collides(min_depth),
        "min_depth_m": min_depth,
        "modified": combo.fix,
        "touches_before": None if combo.before is None else [
            {"fingers": list(pair), "t": touch.first_t, "depth_m": round(touch.depth, 6),
             "bodies": list(touch.bodies)}
            for pair, touch in combo.before.touches.items()
        ],
        "duration": round(result.duration, 3),
        "touches": [
            {"fingers": list(pair), "t": touch.first_t, "depth_m": round(touch.depth, 6),
             "bodies": list(touch.bodies)}
            for pair, touch in result.touches.items()
        ],
    }


def result_from_entry(entry: dict, key: str = "touches") -> CollisionResult:
    return CollisionResult(
        duration=float(entry.get("duration", 0.0)),
        touches={
            tuple(t["fingers"]): Touch(float(t["t"]), float(t["depth_m"]), tuple(t["bodies"]))
            for t in entry.get(key) or []
        },
    )


# Play on hand recordings: path -> (mtime, ``recording_info``), so the npz files are read once.
_RECORDING_INFO: dict[str, tuple[float, dict]] = {}


def recording_info(path: str) -> dict | None:
    """What a Play on hand recording played, from its meta: ``takes`` as {(finger, take
    name)}, ``modified``, its pen ``box`` name and ``corners`` ((4, 2) or None); None if it
    cannot be read."""
    try:
        mtime = os.path.getmtime(path)
        cached = _RECORDING_INFO.get(path)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        with np.load(path, allow_pickle=False) as data:  # only its meta is read
            meta = json.loads(str(data["meta"])) if "meta" in data.files else {}
    except Exception:  # noqa: BLE001 - an unreadable recording is not counted
        return None
    corners = meta.get("box_corners")
    info = {
        "takes": frozenset(
            (finger, os.path.splitext(os.path.basename(take))[0])
            for finger, take in meta.get("takes", {}).items()
        ),
        "modified": bool(meta.get("modified")),
        "box": str(meta.get("box", "")),
        "corners": np.asarray(corners, dtype=np.float32) if corners is not None else None,
    }
    _RECORDING_INFO[path] = (mtime, info)
    return info


def recording_takes(path: str) -> tuple[frozenset, bool] | None:
    """(takes the recording played as {(finger, take name)}, modified) of a Play on hand
    recording, or None if it cannot be read."""
    info = recording_info(path)
    return None if info is None else (info["takes"], info["modified"])


def takes_name(key: frozenset) -> str:
    """Takes of a recording ({(finger, take name)}) as "th_4 + if_2 + mf_3"."""
    order = {finger: i for i, (finger, _) in enumerate(FINGERS)}
    return " + ".join(name for _, name in sorted(key, key=lambda fn: order.get(fn[0], 9)))


@dataclass
class RecordingCounts:
    """Play on hand recordings of a combination and their labels (Demonstration tab Success /
    Fail, or ``label_playbacks``)."""

    paths: list[str] = field(default_factory=list)  # newest first
    success: int = 0
    failure: int = 0
    modified: int = 0
    press: Counter = field(default_factory=Counter)  # click_press outcome -> recordings

    @property
    def total(self) -> int:
        return len(self.paths)

    @property
    def unlabelled(self) -> int:
        return self.total - self.success - self.failure

    @property
    def success_rate(self) -> float | None:
        """Success / (success + fail) of the labelled ones; None if none is labelled."""
        labelled = self.success + self.failure
        return self.success / labelled if labelled else None

    def add(self, path: str, modified: bool) -> None:
        self.paths.append(path)
        self.modified += modified
        saved = load_label(path) or {}
        label = saved.get("label")
        self.success += label == SUCCESS
        self.failure += label == FAILURE
        self.press[saved.get("click_press") or PRESS_UNKNOWN] += 1

    def merge(self, other: RecordingCounts) -> None:
        self.paths += other.paths
        self.success += other.success
        self.failure += other.failure
        self.modified += other.modified
        self.press.update(other.press)

    def press_other(self) -> int:
        """Recordings whose press ended otherwise than in the main columns."""
        return self.total - sum(self.press[k] for k in PRESS_COLUMNS)


# Analysis tab: the click_press outcomes with their own column (the rest: "Other press").
PRESS_COLUMNS = (CLICKED, ABORTED_NO_CLICK, ABORTED_KEPT_SLIDING, ABORTED_NO_CONTACT)


def press_text(counts: RecordingCounts) -> str:
    """The click_press outcomes of some recordings, e.g. "3 clicked, 10 no click"."""
    return ", ".join(f"{n} {PRESS_SHORT.get(k, k)}" for k, n in counts.press.most_common()) or "-"


def count_recordings(directory: str) -> dict[frozenset, RecordingCounts]:
    """Play on hand recordings in ``directory`` by the takes they played."""
    counts: dict[frozenset, RecordingCounts] = {}
    for path in list_playbacks(directory):
        found = recording_takes(path)
        if found is None:
            continue
        key, modified = found
        counts.setdefault(key, RecordingCounts()).add(path, modified)
    return counts


# Held joint the combination check may move to clear a collision: (joint, finger pair). Only when
# the joint's finger has no take in the combination (it holds the first take's pose).
COMBO_FIXES = (("rf_rot", ("mf", "rf")),)


def pen_box_key(corners: np.ndarray) -> bytes:
    """Identity of a pen box: equal only for exactly the same corners."""
    return np.ascontiguousarray(corners, dtype=np.float32).tobytes()


@dataclass
class BoxGroups:
    """Edited takes (with ``episode_start`` / ``terminal``) grouped by their exact pen box."""

    groups: dict[bytes, dict[str, list[FingerTake]]]  # pen_box_key -> finger -> takes
    corners: dict[bytes, np.ndarray]  # pen_box_key -> (4, 2)
    names: dict[bytes, str]  # pen_box_key -> the take the box belongs to (the Thumb's)
    not_edited: int  # takes left out: no episode_start / terminal
    no_box: int  # edited takes left out: no pen box


def group_takes_by_box(store: TakeStore) -> BoxGroups:
    """Every finger's edited takes grouped by their exact pen box, each box named after the
    take it belongs to (the Thumb take the others inherited it from)."""
    groups: dict[bytes, dict[str, list[FingerTake]]] = {}
    corners_by: dict[bytes, np.ndarray] = {}
    labels: dict[bytes, str] = {}
    no_box = not_edited = 0
    for finger, _ in FINGERS:
        for path in store.list(finger):
            try:
                take = store.load(path)
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
            corners_by[key] = corners
            groups.setdefault(key, {f: [] for f, _ in FINGERS})[finger].append(take)
            if len(take.pen_box) == 4:
                if take.pen_box_source:
                    labels.setdefault(
                        key, os.path.splitext(os.path.basename(take.pen_box_source))[0]
                    )
            else:
                labels[key] = take.name
            labels.setdefault(key, take.name)
    return BoxGroups(groups, corners_by, labels, not_edited, no_box)


def pen_box_owner(store: TakeStore, take: FingerTake, max_steps: int = 50) -> str:
    """Name of the take whose own SAM detection ``take``'s pen box is: its ``pen_box_source``
    followed back through the takes that inherited it (as far as they still exist)."""
    name, current = take.name, take
    for _ in range(max_steps):
        if len(current.pen_box) != 4 or not current.pen_box_source:
            return current.name
        name = os.path.splitext(os.path.basename(current.pen_box_source))[0]
        try:
            current = store.load(current.pen_box_source)
        except Exception:  # noqa: BLE001 - the source is gone: the last name known
            return name
    return name


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

    def select_path(self, path: str) -> bool:
        """Selects the listed take at ``path``; False if it is not listed."""
        paths = [take.path for take in self._takes]
        if path not in paths:
            return False
        self.list.setCurrentRow(paths.index(path))
        return True

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


class ClickPressStateView(QtWidgets.QWidget):
    """Where the Thumb is in a Play on hand, and its ``click_press`` state machine: a row of
    stages (the current one highlighted, those passed pale green), the press's live status and
    how it ended."""

    # (key, label, tooltip)
    STAGES = (
        ("moving", "Moving to start", "The Thumb moves to where its episode starts"),
        ("held", "Held at start", "Held stiff at its start while Index / Middle / Ring play"),
        ("take", "Take", "Plain position replay of the take, up to the click_press region"),
        (CLICK_APPROACH, "Approach",
         "Guarded move of the fingertip along the press axis until contact (take time held)"),
        (CLICK_PRESSING, "Press",
         "Force ramp along the press axis until a click or an abort (take time held)"),
        (CLICK_RETRACT, "Retract", "Backs off along the press axis"),
        (CLICK_RELEASE, "Release", "Take jumps to the region's end; blend back into it"),
        ("after", "Take to terminal", "Plain position replay from the region's end"),
        ("finished", "Finished", "The Thumb got to its terminal"),
    )
    STYLE = "QLabel {{ background-color: {bg}; color: {fg}; border-radius: 4px; padding: 2px 6px; {extra} }}"

    def __init__(self) -> None:
        super().__init__()
        rows = QtWidgets.QVBoxLayout(self)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.setSpacing(2)
        layout = QtWidgets.QHBoxLayout()
        rows.addLayout(layout)
        layout.addWidget(QtWidgets.QLabel("<b>Click press:</b>"))
        self.boxes: dict[str, QtWidgets.QLabel] = {}
        for k, (key, label, tip) in enumerate(self.STAGES):
            if k:
                layout.addWidget(QtWidgets.QLabel("\u2192"))
            box = QtWidgets.QLabel(label)
            box.setToolTip(tip)
            box.setStyleSheet(self.STYLE.format(bg="#eeeeee", fg="#9e9e9e", extra="font-weight: bold;"))
            box.setMinimumWidth(box.sizeHint().width())  # never squashed into "Ap", "Pr"
            self.boxes[key] = box
            layout.addWidget(box)
        layout.addStretch(1)
        # Under the stages: how the press ended, and its live status.
        self.outcome = QtWidgets.QLabel()
        self.status = QtWidgets.QLabel()
        line = QtWidgets.QHBoxLayout()
        line.addSpacing(QtWidgets.QLabel("<b>Click press:</b>").sizeHint().width() + 6)
        line.addWidget(self.outcome)
        line.addWidget(self.status, 1)
        rows.addLayout(line)
        self._shown: tuple | None = None
        self.show_stage(None, "", None)

    def show_stage(self, stage: str | None, status: str, outcome: tuple[str, str] | None,
                   no_press: bool = False) -> None:
        """Highlights ``stage`` (None: idle), with the press ``status`` and its ``outcome``
        ((label, why) from ``classify_trace``, None while undecided)."""
        key = (stage, status, outcome, no_press)
        if key == self._shown:
            return
        self._shown = key
        keys = [k for k, _, _ in self.STAGES]
        current = keys.index(stage) if stage in keys else -1
        for k, name in enumerate(keys):
            if k == current:
                bg, fg, extra = "#1976d2", "white", "font-weight: bold;"
            elif 0 <= k < current:
                bg, fg, extra = "#c8e6c9", "#1b5e20", ""
            else:
                bg, fg, extra = "#eeeeee", "#9e9e9e", ""
            if no_press and name in (CLICK_APPROACH, CLICK_PRESSING, CLICK_RETRACT,
                                     CLICK_RELEASE):
                bg, fg, extra = "#eeeeee", "#bdbdbd", "text-decoration: line-through;"
            self.boxes[name].setStyleSheet(self.STYLE.format(bg=bg, fg=fg, extra=extra))
        if outcome is None:
            self.outcome.setText("<i>no click_press region in this take</i>" if no_press else "")
            self.outcome.setToolTip("")
        else:
            label, why = outcome
            color = COMBO_VALID_COLOR if label == CLICKED else COMBO_COLLIDE_COLOR
            self.outcome.setText(
                f"<span style='color:{color}'><b>{PRESS_SHORT.get(label, label)}</b></span>"
            )
            self.outcome.setToolTip(why)
        self.status.setText(f"<span style='color:#616161'>{status}</span>" if status else "")


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
        self._hand_fix: dict | None = None  # modified combination playing: its fix and finger
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
        # Combinations panel: the combinations listed, and the background sim check
        # (its thread, stop flag and the results it sends back).
        self._combos: list[Combination] = []
        self._combo_counts = ""
        self._rec_counts: dict[frozenset, RecordingCounts] = {}  # Play on hand recordings
        self._check_thread: threading.Thread | None = None
        self._check_stop = threading.Event()
        self._check_queue: queue.Queue = queue.Queue()
        self._check_total = 0
        self._check_done = 0
        self._check_timer = QtCore.QTimer(self)
        self._check_timer.setInterval(100)
        self._check_timer.timeout.connect(self._poll_check)
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
            "click_press, force replay, playback recording). Key: Space play / stop"
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
        self.baseline_btn = QtWidgets.QPushButton("Set touch baseline")
        self.baseline_btn.setToolTip(
            "Use the current Xela reading as the no-contact baseline (as Zero on the Create / "
            "Edit tab): the fingertips should touch nothing. Maintain touch, click press, force "
            "replay, slip detection and Avoid slip measure the fingertip force from it. Play on "
            "hand needs it to be set"
        )
        self.baseline_btn.clicked.connect(self._set_touch_baseline)
        self.baseline_status = QtWidgets.QLabel()
        self._baseline_shown: float | None | bool = False  # zeroed_at the label shows
        top.addWidget(self.baseline_btn)
        top.addWidget(self.baseline_status)
        top.addWidget(self.hand_status)
        top.addWidget(self.hand_btn)
        top.addWidget(refresh_btn)
        combos_panel = self._build_combinations_panel()
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
        self.avoid_spins: dict[str, QtWidgets.QDoubleSpinBox] = {}
        for name, label, tip in (
            ("before_thumb", "Thumb", "Force units added to the fingers holding the pen when "
                                      "the Thumb starts"),
            ("per_slip", "slip", "Force units added to a finger each time it slips"),
            ("max_extra", "max", "Largest extra force of a finger (units)"),
        ):
            spin = double_spin(0.0, 50.0, 0.5, 1, "", tip)
            spin.setValue(getattr(avoid_slip, name))
            spin.valueChanged.connect(lambda v, n=name: setattr(avoid_slip, n, float(v)))
            spin.valueChanged.connect(lambda _v: self._sync_avoid_preset())
            self.avoid_spins[name] = spin
            plays_row.addWidget(QtWidgets.QLabel(f"+{label}" if name != "max_extra" else label))
            plays_row.addWidget(spin)
        # Saved sets of the three Avoid slip values, to compare their Play on hand results.
        self._avoid_presets_path = avoid_slip_presets_file()
        try:
            self._avoid_presets = load_avoid_slip_presets(self._avoid_presets_path)
        except (OSError, ValueError) as e:
            self.node.get_logger().warn(f"Could not read {self._avoid_presets_path}: {e}")
            self._avoid_presets = {}
        self.avoid_preset_combo = QtWidgets.QComboBox()
        self.avoid_preset_combo.setToolTip(
            "Avoid slip presets: picking one loads its Thumb / slip / max values. Each Play on "
            "hand recording stores the preset its values match (meta avoid_slip_preset)"
        )
        self.avoid_preset_combo.activated.connect(self._load_avoid_preset)
        save_preset = QtWidgets.QPushButton("Save preset")
        save_preset.setToolTip("Save the three Avoid slip values under a name")
        save_preset.clicked.connect(self._save_avoid_preset)
        self.delete_preset_button = QtWidgets.QPushButton("Delete preset")
        self.delete_preset_button.setToolTip("Delete the Avoid slip preset picked")
        self.delete_preset_button.clicked.connect(self._delete_avoid_preset)
        plays_row.addWidget(self.avoid_preset_combo)
        plays_row.addWidget(save_preset)
        plays_row.addWidget(self.delete_preset_button)
        self._fill_avoid_presets()
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
        split.addWidget(combos_panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        split.setStretchFactor(2, 1)
        split.setSizes([450, 900, 350])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(plays_row)
        self.press_view = ClickPressStateView()
        layout.addWidget(self.press_view)
        self._press_seen = None  # the Thumb's last ClickPress (shown after its play too)
        self._press_finished = False
        layout.addWidget(split, 1)

        self.box_combo.currentIndexChanged.connect(self._on_box)
        refresh_btn.clicked.connect(self.refresh_takes)
        self.sim_btn.clicked.connect(self._toggle_sim)
        self.hand_btn.clicked.connect(self._toggle_hand)
        # Space while this tab is shown: Play on hand, or stop it if it is playing.
        hand_key = QtWidgets.QShortcut(QtGui.QKeySequence("Space"), self)
        hand_key.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        hand_key.activated.connect(self._toggle_hand)
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
        boxes = group_takes_by_box(self.store)
        self._groups, self._corners, labels = boxes.groups, boxes.corners, boxes.names
        not_edited, no_box = boxes.not_edited, boxes.no_box
        self._box_names = labels
        self.box_combo.blockSignals(True)
        self.box_combo.clear()
        for key, by_finger in self._groups.items():
            cx, cy = self._corners[key].mean(axis=0)
            counts = ", ".join(f"{f.upper()} {len(by_finger[f])}" for f, _ in FINGERS)
            self.box_combo.addItem(f"{labels[key]}  @ ({cx:.0f}, {cy:.0f})  [{counts}]", key)
        index = self._box_index(keep) if keep is not None else -1
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
        self._live_seq = -1  # redraw the live view with the new box
        key = self.box_combo.currentData()
        by_finger = self._groups.get(key, {})
        for finger, column in self.columns.items():
            column.set_takes(by_finger.get(finger, []))
        self.fill_combinations()
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

    def _set_touch_baseline(self) -> None:
        """Set touch baseline: Zero of the Create tab's (and the Edit tab's live) taxel view."""
        if not self.create_tab.hand._zero():
            QtWidgets.QMessageBox.warning(
                self, "Set touch baseline",
                f"No Xela reading to use: nothing has arrived on '{self.node.xela_topic}' yet "
                "(is xela_service running?), or the taxel map is unavailable.",
            )
            return
        self.edit_tab.live_hand._zero()
        self.node.get_logger().info("Touch baseline set from the current Xela reading")
        self._show_baseline_status()

    def _show_baseline_status(self) -> None:
        zeroed = self.create_tab.hand.zeroed_at
        if zeroed == self._baseline_shown:
            return
        self._baseline_shown = zeroed
        if zeroed is None:
            self.baseline_status.setText(
                "<span style='color:#d32f2f'><b>touch baseline: not set</b></span>"
            )
        else:
            when = datetime.fromtimestamp(zeroed).strftime("%H:%M:%S")
            self.baseline_status.setText(
                f"<span style='color:#2e7d32'>touch baseline: set {when}</span>"
            )

    def _toggle_hand(self) -> None:
        if self._hand_active:
            self.stop_hand()
            return
        if self.create_tab.hand.zeroed_at is None:
            QtWidgets.QMessageBox.warning(
                self, "Play on hand",
                "The touch baseline is not set.\n\nWith the fingertips touching nothing, press "
                "Set touch baseline (or Zero on the Create or Edit tab), then Play on hand "
                "again.\n\nMaintain touch, click press, force replay, slip detection and Avoid "
                "slip all measure the fingertip force from this baseline. Without it they use "
                "the first Xela reading the GUI got, whatever the hand was touching then.",
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
        moves = list(takes)
        self._hand_fix = None
        modified = self._active_fix(takes)
        if modified is not None:
            # The modified finger has no take: it moves to its pose with the others and is held
            # there for the whole demonstration.
            held = self._held_pose_take(modified)
            self._hand_fix = dict(modified.fix, finger=held.finger)
            self._hand_spans[held.finger] = (0.0, 0.0)
            moves.append(held)
            self.node.get_logger().info(f"Play on hand: modified, {modified.fix_text()}")
        self._move_queue = sorted(moves, key=lambda t: START_ORDER.index(t.finger))
        self._moving, self._at_start, self._await_release = None, set(), {}
        for finger, _ in FINGERS:
            self._set_start_light(finger, "off")
        self._move_next_to_start()

    def _held_pose_take(self, combo: Combination) -> FingerTake:
        """A still take of the modified finger at its pose in the combination (the first
        take's pose with the modified joint at its new value), held for the demonstration."""
        names, base, _ = combo.plan()
        finger = combo.fix["joint"].split("_")[0]
        cols = finger_indices(names, finger)
        q = np.tile(base[cols], (2, 1))
        return FingerTake(
            finger=finger, path=f"modified {finger} pose", t=np.array([0.0, 1.0]), q=q,
            joint_names=[names[c] for c in cols], hand_q=np.tile(base, (2, 1)),
            hand_joint_names=list(names),
        )

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
        # The modified finger held at its pose (never in a stage) is let go now.
        held, self._at_start = sorted(self._at_start), set()
        for finger in held:
            self._hand_event(finger, "released")
            if self.create_tab.playback(finger) is not None:
                self.create_tab.stop_play(finger)
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
            "modified": self._hand_fix,
        }
        if self._hand_fix is not None:
            self._hand_event(self._hand_fix["finger"], "held (modified pose)")

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
                "modified": info["modified"],
                "slips": [
                    {"t": round(e.t - t0, 3), "finger": f, "cue": e.cue,
                     "value": round(e.value, 5), "force": round(e.force, 3)}
                    for f, events in slips.items() for e in events
                ],
                "slip_settings": asdict(SlipSettings()),
                "avoid_slip": asdict(self.avoid_slip),
                "avoid_slip_preset": self._matching_avoid_preset(),
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
        self.refresh_recording_counts()

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

    def _avoid_values(self) -> dict[str, float]:
        return {name: round(float(getattr(self.avoid_slip, name)), 3)
                for name in AVOID_SLIP_VALUES}

    def _matching_avoid_preset(self) -> str:
        """Name of the preset with the current Avoid slip values ("" if none)."""
        values = self._avoid_values()
        return next((name for name, preset in self._avoid_presets.items()
                     if all(abs(preset[k] - values[k]) < 1e-6 for k in AVOID_SLIP_VALUES)), "")

    def _fill_avoid_presets(self) -> None:
        combo = self.avoid_preset_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(custom)", "")
        for name in sorted(self._avoid_presets):
            v = self._avoid_presets[name]
            combo.addItem(name, name)
            combo.setItemData(
                combo.count() - 1,
                f"+Thumb {v['before_thumb']:g}, +slip {v['per_slip']:g}, max {v['max_extra']:g}",
                QtCore.Qt.ToolTipRole,
            )
        combo.blockSignals(False)
        self._sync_avoid_preset()

    def _sync_avoid_preset(self) -> None:
        """Show the preset the current values match, (custom) when they match none."""
        name = self._matching_avoid_preset()
        combo = self.avoid_preset_combo
        combo.blockSignals(True)
        combo.setCurrentIndex(max(combo.findData(name), 0))
        combo.blockSignals(False)
        self.delete_preset_button.setEnabled(bool(name))

    def _load_avoid_preset(self, index: int) -> None:
        preset = self._avoid_presets.get(self.avoid_preset_combo.itemData(index) or "")
        if preset is None:
            return
        for name, spin in self.avoid_spins.items():
            spin.setValue(preset[name])  # also sets avoid_slip

    def _write_avoid_presets(self) -> bool:
        try:
            save_avoid_slip_presets(self._avoid_presets_path, self._avoid_presets)
        except OSError as e:
            QtWidgets.QMessageBox.warning(
                self, "Avoid slip presets", f"Could not save {self._avoid_presets_path}: {e}")
            return False
        return True

    def _save_avoid_preset(self) -> None:
        v = self._avoid_values()
        default = self._matching_avoid_preset() or (
            f"T{v['before_thumb']:g}_s{v['per_slip']:g}_m{v['max_extra']:g}")
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save Avoid slip preset",
            f"Name for +Thumb {v['before_thumb']:g}, +slip {v['per_slip']:g}, "
            f"max {v['max_extra']:g}:", text=default)
        name = name.strip()
        if not ok or not name:
            return
        if name in self._avoid_presets and self._avoid_presets[name] != v:
            answer = QtWidgets.QMessageBox.question(
                self, "Save Avoid slip preset", f"Replace the values of preset '{name}'?")
            if answer != QtWidgets.QMessageBox.Yes:
                return
        self._avoid_presets[name] = v
        if self._write_avoid_presets():
            self._fill_avoid_presets()

    def _delete_avoid_preset(self) -> None:
        name = self.avoid_preset_combo.currentData() or ""
        if name not in self._avoid_presets:
            return
        answer = QtWidgets.QMessageBox.question(
            self, "Delete Avoid slip preset", f"Delete preset '{name}'?")
        if answer != QtWidgets.QMessageBox.Yes:
            return
        del self._avoid_presets[name]
        if self._write_avoid_presets():
            self._fill_avoid_presets()

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
        spans = [self._play_span(take) for take in takes]
        names, base, parts = build_sim_plan(takes, spans)
        modified = self._active_fix(takes)
        if modified is not None:
            names, base, parts = modified.plan(spans)
        delays = [delay for _, _, _, delay in parts]
        self._run_sim(names, base, parts, self.sim_btn, "Testing in sim: " + ", ".join(
            f"{FINGER_LABEL[t.finger]} '{t.name}' "
            f"{self._span_text(t, {t.finger: s})}"
            + (f" (after {d:.2f} s)" if d else "")
            for t, s, d in zip(takes, spans, delays)
        ) + (f"; modified: {modified.fix_text()}" if modified is not None else ""))

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
        self.combo_play_btn.setText("Play in sim")
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

    # ---- Combinations ---------------------------------------------------------------------

    def _build_combinations_panel(self) -> QtWidgets.QGroupBox:
        """Combinations panel (right): every combination of one take per finger, and whether
        it plays in the sim without two fingers touching."""
        self.combo_min_depth = double_spin(
            0.0, 20.0, 0.1, 2, " mm",
            "Finger-finger contacts shallower than this are not collisions (the collision geoms "
            "reach a little past the visual meshes). Changing it re-grades the checked "
            "combinations without running them again; the live sim uses its own "
            "min_contact_depth parameter"
        )
        self.combo_min_depth.setValue(self.node.min_contact_depth * 1000.0)
        self.combo_valid_only = QtWidgets.QCheckBox("Valid only")
        self.combo_valid_only.setToolTip(
            "List only the combinations that did not collide in the sim"
        )
        self.combo_check_btn = QtWidgets.QPushButton("Check in sim")
        self.combo_check_btn.setToolTip(
            "Play every combination not checked yet (all of them if all are) in a headless MuJoCo "
            "of the sim's model, as Test in sim plays it from each take's episode_start, faster "
            "than real time; a combination is valid if no two fingers touch while it plays"
        )
        self.combo_progress = QtWidgets.QLabel()
        self.combo_summary = QtWidgets.QLabel()
        self.combo_summary.setWordWrap(True)
        self.combo_list = QtWidgets.QListWidget()
        self.combo_list.setToolTip(
            "One take of each finger; picking one selects its takes in the finger columns "
            f"(results saved in <demo_dir>/{COMBINATIONS_FILE})"
        )
        self.combo_details = QtWidgets.QTextBrowser()
        self.combo_play_btn = QtWidgets.QPushButton("Play in sim")
        self.combo_play_btn.setToolTip(
            f"Play the picked combination to the MuJoCo sim on '{self.node.sim_cmd_topic}' (from "
            "each take's episode_start), to watch it in the viewer"
        )
        self.combo_play_btn.setEnabled(False)
        options = QtWidgets.QHBoxLayout()
        options.addWidget(QtWidgets.QLabel("Min depth:"))
        options.addWidget(self.combo_min_depth)
        options.addWidget(self.combo_valid_only)
        options.addStretch(1)
        check_row = QtWidgets.QHBoxLayout()
        check_row.addWidget(self.combo_check_btn)
        check_row.addWidget(self.combo_progress, 1)
        check_row.addWidget(self.combo_play_btn)
        top = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addLayout(options)
        top_layout.addLayout(check_row)
        top_layout.addWidget(self.combo_summary)
        top_layout.addWidget(self.combo_list, 1)
        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        split.addWidget(top)
        split.addWidget(self.combo_details)
        split.setSizes([500, 200])
        panel = QtWidgets.QGroupBox("Combinations")
        QtWidgets.QVBoxLayout(panel).addWidget(split)
        self.combo_valid_only.toggled.connect(lambda *_: self._list_combinations())
        self.combo_min_depth.valueChanged.connect(self._min_depth_changed)
        self.combo_check_btn.clicked.connect(self._toggle_check)
        self.combo_list.currentRowChanged.connect(self._on_combination)
        self.combo_play_btn.clicked.connect(self._toggle_combo_sim)
        return panel

    def _combination_takes(self) -> dict[str, list[FingerTake]]:
        """The edited takes of each finger with the bounding box picked above."""
        group = self._groups.get(self.box_combo.currentData(), {})
        return {
            finger: sorted(group.get(finger, []), key=lambda take: take.name)
            for finger, _ in FINGERS
        }

    def fill_combinations(self) -> None:
        """Every combination of one take per finger (of the fingers with takes), with the saved
        sim results of those whose takes have not changed since."""
        if self._check_thread is not None:
            return  # listed again once the check has finished
        picked = self._picked_combination()
        by_finger = self._combination_takes()
        lists = [takes for takes in by_finger.values() if takes]
        saved = load_combination_results(self._combinations_path())
        self._combos = []
        for takes in (itertools.product(*lists) if lists else []):
            combo = Combination(list(takes))
            entry = saved.get(combo.key)
            if entry is not None and entry.get("mtimes") == combo.mtimes():
                combo.result = result_from_entry(entry)
                combo.fix = entry.get("modified")
                if entry.get("touches_before") is not None:
                    combo.before = result_from_entry(entry, "touches_before")
            self._combos.append(combo)
        self._combo_counts = ", ".join(
            f"{f.upper()} {len(t)}" for f, t in by_finger.items() if t
        )
        self._rec_counts = count_recordings(self.store.compose_playback_dir)
        self._fill_summary()
        self._list_combinations(picked.key if picked is not None else None)

    def refresh_recording_counts(self) -> None:
        """Counts the Play on hand recordings of each combination again (a new recording, or
        labels changed on the Demonstration tab)."""
        self._rec_counts = count_recordings(self.store.compose_playback_dir)
        self._fill_summary()
        self._list_combinations()

    def _recordings_of(self, combo: Combination) -> RecordingCounts:
        return self._rec_counts.get(combo.recording_key, RecordingCounts())

    def _fill_summary(self) -> None:
        checked = [c for c in self._combos if c.valid(self._min_depth) is not None]
        valid = sum(c.valid(self._min_depth) for c in checked)
        self.combo_summary.setText(
            f"{len(self._combos)} combination(s) of {self._combo_counts or 'no takes'}; "
            f"<span style='color:{COMBO_VALID_COLOR}'><b>{valid} valid</b></span>, "
            f"<span style='color:{COMBO_COLLIDE_COLOR}'>{len(checked) - valid} collide</span>, "
            f"{len(self._combos) - len(checked)} not checked"
            + self._summary_recordings()
        )

    def _summary_recordings(self) -> str:
        """Recordings of the listed combinations, for the summary line."""
        counts = [self._recordings_of(c) for c in self._combos]
        total = sum(c.total for c in counts)
        if not total:
            return "; no recordings yet"
        return (f"; {total} recording(s): {sum(c.success for c in counts)} success, "
                f"{sum(c.failure for c in counts)} fail, "
                f"{sum(c.unlabelled for c in counts)} not labelled")

    def _list_combinations(self, keep: tuple[str, ...] | None = None) -> None:
        """Lists the combinations (only the valid ones with Valid only), keeping the picked one
        (or the one with the take paths ``keep``)."""
        if keep is None:
            picked = self._picked_combination()
            keep = picked.key if picked is not None else None
        valid_only = self.combo_valid_only.isChecked()
        self.combo_list.blockSignals(True)
        self.combo_list.clear()
        row = -1
        for i, combo in enumerate(self._combos):
            if valid_only and not combo.valid(self._min_depth):
                continue
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, i)
            self._show_combination(item, combo)
            self.combo_list.addItem(item)
            if combo.key == keep:
                row = self.combo_list.count() - 1
        self.combo_list.setCurrentRow(row)
        self.combo_list.blockSignals(False)
        self._on_combination()

    def _show_combination(self, item: QtWidgets.QListWidgetItem, combo: Combination) -> None:
        valid = combo.valid(self._min_depth)
        if combo.error or valid is False:
            mark, color = "\u2717", COMBO_COLLIDE_COLOR
        elif valid:
            mark, color = "\u2713", COMBO_VALID_COLOR
        else:
            mark, color = "\u00b7", COMBO_UNCHECKED_COLOR
        recs = self._recordings_of(combo)
        recorded = (f"   {recs.total} rec: \u2713{recs.success} \u2717{recs.failure}"
                    + (f" ?{recs.unlabelled}" if recs.unlabelled else "")) if recs.total else ""
        item.setText(f"{mark} {combo.name}" + ("  [modified]" if combo.fix else "") + recorded)
        item.setForeground(QtGui.QColor(color))
        item.setToolTip(combo.status_text(self._min_depth)
                        + (f"\nModified: {combo.fix_text()}" if combo.fix else ""))

    def _picked_combination(self) -> Combination | None:
        item = self.combo_list.currentItem()
        return self._combos[item.data(QtCore.Qt.UserRole)] if item is not None else None

    def _on_combination(self, *_) -> None:
        """Details of the picked combination; its takes are selected in the finger columns."""
        combo = self._picked_combination()
        self.combo_play_btn.setEnabled(combo is not None)
        if combo is None:
            self.combo_details.setHtml(
                "<i>Pick a combination to see it.</i>" if self.combo_list.count()
                else "<i>No combinations: edit takes (episode_start and terminal) with a pen "
                     "bounding box first.</i>"
            )
            return
        rows = []
        for take in combo.takes:
            start, end = take_episode_span(take)
            rows.append((FINGER_LABEL[take.finger], f"{take.name} ({start:.2f} -> {end:.2f} s)"))
        if combo.result is not None:
            rows.append(("Length", f"{combo.result.duration:.1f} s"))
        valid = combo.valid(self._min_depth)
        if combo.error or valid is False:
            color = COMBO_COLLIDE_COLOR
        elif valid:
            color = COMBO_VALID_COLOR
        else:
            color = COMBO_UNCHECKED_COLOR
        status = combo.status_text(self._min_depth)
        rows.append(("Sim", f"<span style='color:{color}'><b>{status}</b></span>"))
        recs = self._recordings_of(combo)
        rows.append(("Recordings", (
            f"<b>{recs.total}</b>: <span style='color:{COMBO_VALID_COLOR}'><b>{recs.success} "
            f"success</b></span>, <span style='color:{COMBO_COLLIDE_COLOR}'><b>{recs.failure} "
            f"fail</b></span>, {recs.unlabelled} not labelled"
            + (f" ({recs.modified} modified)" if recs.modified else "")
        ) if recs.total else "none yet (Play on hand records one)"))
        for path in recs.paths:
            label = (load_label(path) or {}).get("label")
            mark = {SUCCESS: f"<span style='color:{COMBO_VALID_COLOR}'>success</span>",
                    FAILURE: f"<span style='color:{COMBO_COLLIDE_COLOR}'>fail</span>"}.get(
                label, "not labelled")
            rows.append(("", f"{os.path.splitext(os.path.basename(path))[0]}: {mark}"))
        if combo.fix is not None:
            rows.append(("<span style='color:#ef6c00'>Modified</span>", combo.fix_text()))
            if combo.before is not None:
                rows.append(("Before", Combination(combo.takes, combo.before).status_text(
                    self._min_depth)))
        elif combo.result is not None and not combo.error:
            held = {take.finger for take in combo.takes}
            for joint, pair in COMBO_FIXES:
                if joint.split("_")[0] not in held and pair in combo.result.counted(
                        self._min_depth):
                    rows.append(("Modified", f"no {joint} value in its range clears the "
                                             f"{pair_text([pair])} collision"))
        if combo.result is not None:
            # Every pair that touched, counted or not, with its deepest contact.
            for pair, touch in sorted(combo.result.touches.items(), key=lambda kv: kv[1].first_t):
                text = (f"max {touch.depth * 1000:.2f} mm, from {touch.first_t:.2f} s, "
                        f"{touch.bodies[0]} / {touch.bodies[1]}")
                if touch.depth < self._min_depth:
                    text = f"<span style='color:#9e9e9e'>{text} (under the min depth)</span>"
                rows.append((pair_text([pair]), text))
        self.combo_details.setHtml("<table cellspacing='2'>" + "".join(
            f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in rows
        ) + "</table>")
        for take in combo.takes:
            self.columns[take.finger].select_path(take.path)

    def _box_index(self, key: bytes | None) -> int:
        """Row of the box ``key`` in the dropdown (findData does not match bytes), or -1."""
        return next(
            (i for i in range(self.box_combo.count()) if self.box_combo.itemData(i) == key), -1
        )

    @property
    def _min_depth(self) -> float:
        """Min depth (m) of a finger-finger contact counted as a collision."""
        return self.combo_min_depth.value() / 1000.0

    def _min_depth_changed(self, *_) -> None:
        """Re-grades the checked combinations (their max depths are kept) and saves them."""
        self._fill_summary()
        self._list_combinations()
        if self._check_thread is None and any(c.result is not None for c in self._combos):
            self._save_combinations()

    def _combinations_path(self) -> str:
        return os.path.join(self.store.demo_dir, COMBINATIONS_FILE)

    def _toggle_check(self) -> None:
        if self._check_thread is not None:
            self._check_stop.set()
            self.combo_check_btn.setEnabled(False)
            self.combo_progress.setText("stopping...")
            return
        jobs = [c for c in self._combos if c.result is None] or list(self._combos)
        if not jobs:
            QtWidgets.QMessageBox.warning(self, "Check in sim", "No combinations to check.")
            return
        for combo in jobs:
            combo.result, combo.error, combo.fix, combo.before = None, "", None, None
        self._check_stop.clear()
        self._check_queue = queue.Queue()
        self._check_total, self._check_done = len(jobs), 0
        self._check_thread = threading.Thread(
            target=self._check_worker,
            args=(jobs, self._min_depth, self._check_stop, self._check_queue),
            name="combination_check", daemon=True,
        )
        self.combo_check_btn.setText("Stop check")
        self.combo_check_btn.setStyleSheet(STOP_STYLE)
        self.box_combo.setEnabled(False)  # the list belongs to this box until the check ends
        self.combo_progress.setText(f"0 / {len(jobs)}")
        self.node.get_logger().info(f"Checking {len(jobs)} combination(s) in a headless sim")
        self._fill_summary()
        self._list_combinations()
        self._check_thread.start()
        self._check_timer.start()

    @staticmethod
    def _check_worker(
        jobs: list[Combination], min_depth: float, stop: threading.Event, out: queue.Queue,
    ) -> None:
        """Runs in its own thread: plays each combination in a headless sim, sending
        (combination, result, error, fix, result before the fix) back, then None (or
        ("failed", why) if it cannot). A ``COMBO_FIXES`` collision of a held finger is cleared
        by moving its joint the least it takes, if it can be."""
        try:
            checker = SimCollisionChecker()
            to_sim = HardwareToSim()
        except Exception as e:  # noqa: BLE001 - shown in the panel
            out.put(("failed", f"Could not load the sim: {e}"))
            return
        sim_names = list(to_sim.sim_names)

        def convert(n, q):
            return sim_names, to_sim(n, q)

        for combo in jobs:
            if stop.is_set():
                break
            fix = before = None
            try:
                names, base, parts = combo.plan()
                result = checker.check(
                    names, base, parts, convert, COMMAND_RATE_HZ, should_stop=stop.is_set,
                )
                held = {take.finger for take in combo.takes}
                for joint, pair in COMBO_FIXES:
                    if (result is None or joint.split("_")[0] in held
                            or pair not in result.counted(min_depth)):
                        continue
                    found = checker.clear_pair(
                        names, base, parts, convert, COMMAND_RATE_HZ, joint, pair, min_depth,
                        result, should_stop=stop.is_set,
                    )
                    if found is not None:
                        value, fixed = found
                        col = names.index(joint)
                        fix = {"joint": joint, "from": round(float(base[col]), 5),
                               "to": round(float(value), 5), "pair": list(pair),
                               "min_depth_m": min_depth}
                        before, result = result, fixed
                        base[col] = value
            except Exception as e:  # noqa: BLE001 - one bad take should not stop the rest
                out.put((combo, None, str(e), None, None))
                continue
            if result is None:
                break
            out.put((combo, result, "", fix, before))
        out.put(None)

    def _poll_check(self) -> None:
        """Takes in the background check's results."""
        changed = False
        while True:
            try:
                msg = self._check_queue.get_nowait()
            except queue.Empty:
                break
            if msg is None or msg[0] == "failed":
                if msg is not None:
                    self.node.get_logger().error(f"Combination check: {msg[1]}")
                    QtWidgets.QMessageBox.warning(self, "Check in sim", msg[1])
                self._finish_check()
                return
            combo, result, error, fix, before = msg
            combo.result, combo.error, combo.fix, combo.before = result, error, fix, before
            self._check_done += 1
            changed = True
        if changed:
            self.combo_progress.setText(f"{self._check_done} / {self._check_total}")
            self._fill_summary()
            for row in range(self.combo_list.count()):
                item = self.combo_list.item(row)
                self._show_combination(item, self._combos[item.data(QtCore.Qt.UserRole)])
            if self.combo_list.currentItem() is not None:
                self._on_combination()

    def _finish_check(self) -> None:
        self._check_timer.stop()
        self._check_thread = None
        stopped = self._check_stop.is_set()
        self.combo_check_btn.setText("Check in sim")
        self.combo_check_btn.setStyleSheet("")
        self.combo_check_btn.setEnabled(True)
        self.box_combo.setEnabled(True)
        self._save_combinations()
        checked = [c for c in self._combos if c.valid(self._min_depth) is not None]
        valid = sum(c.valid(self._min_depth) for c in checked)
        word = "stopped" if stopped else "done"
        self.combo_progress.setText(f"{word}: {valid} / {len(checked)} valid")
        self.node.get_logger().info(
            f"Combination check {word}: {valid} of {len(checked)} checked are valid (no finger "
            f"contacts); saved in {self._combinations_path()}"
        )
        self._fill_summary()
        self._list_combinations()

    def stop_combination_check(self) -> None:
        """Stops the background check (on close), without waiting for it."""
        self._check_stop.set()

    def _save_combinations(self) -> None:
        """Adds the checked combinations to ``<demo_dir>/combinations.json`` (the results of
        combinations not listed now are kept)."""
        path = self._combinations_path()
        entries = load_combination_results(path)
        for combo in self._combos:
            if combo.result is not None:
                entries[combo.key] = combination_entry(combo, self._min_depth)
        data = {
            "updated": datetime.now().isoformat(timespec="seconds"),
            "rule": "valid: no contact at least min_depth_m deep between bodies of two different "
                    "fingers while the combination plays in the sim (Test in sim order, from "
                    "episode_start); touches lists every pair that touched, with its max depth",
            "combinations": list(entries.values()),
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=1)
        except OSError as e:
            self.node.get_logger().warn(f"Could not save the combinations to {path}: {e}")

    def _active_fix(self, takes: list[FingerTake]) -> Combination | None:
        """The picked combination if it is modified and ``takes`` are exactly its takes."""
        combo = self._picked_combination()
        if combo is None or combo.fix is None:
            return None
        return combo if combo.key == tuple(take.path for take in takes) else None

    def _toggle_combo_sim(self) -> None:
        """Plays the picked combination to the live sim (or stops the sim)."""
        if self._sim_timer.isActive():
            self.stop_sim()
            return
        combo = self._picked_combination()
        if combo is None:
            return
        names, base, parts = combo.plan()
        self._run_sim(names, base, parts, self.combo_play_btn,
                      f"Playing combination {combo.name} in sim "
                      f"({combo.status_text(self._min_depth)})")

    def _show_press_state(self) -> None:
        """The Click press row: the Thumb's stage in a Play on hand (or a Thumb Play on the Edit
        tab) and its click_press state machine."""
        view = self.press_view
        if self._hand_active and (self._moving == "th" or any(
                t.finger == "th" for t in self._move_queue)):
            self._press_seen, self._press_finished = None, False  # a new run: forget the last
            moving = self._moving == "th"
            view.show_stage("moving" if moving else None,
                            "" if moving else "the other fingers move to their start first", None)
            return
        if self._hand_active and ("th" in self._at_start or "th" in self._await_release):
            view.show_stage("held", "", None)
            return
        p = self.create_tab.playback("th")
        press = p.press if p is not None else None
        if p is not None and p.take.path.startswith("move to the start"):
            p = press = None  # its move to the start: shown above
        if press is not None and press is not self._press_seen:
            self._press_seen, self._press_finished = press, False
        if p is not None and press is None and self._hand_active:
            view.show_stage("take" if not p.finished else "finished", "", None, no_press=True)
            return
        press = self._press_seen
        if press is None:
            view.show_stage(None, "", None)
            return
        decided = [e for e in press.trace if e.get("event") in ("click", "abort")]
        outcome = classify_trace(press.trace) if decided else None
        if p is None:  # the Thumb's play ended: the press's last state stays shown
            self._press_finished = True
            view.show_stage("finished" if decided else None, "", outcome)
            return
        if press.state in (CLICK_APPROACH, CLICK_PRESSING, CLICK_RETRACT, CLICK_RELEASE):
            stage = press.state
        elif press.state == CLICK_DONE or decided:
            stage = "finished" if p.finished else "after"
        else:
            stage = "take"
        view.show_stage(stage, press.status.replace("click press: ", ""), outcome)

    def close_video(self) -> None:
        self._video.release()

    def refresh(self) -> None:
        """Slip lights during Play on hand, and the live camera with the selected bounding box
        (while the tab is shown)."""
        if self._slip:
            self._update_slips()
            self._set_slip_lights()
        self._set_contact_lights()
        self._show_baseline_status()
        self._show_press_state()
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


# Outputs of Realtek USB audio chips (ALC4080 family, "Generic USB Audio") by PCM device, as
# Ubuntu's sound settings name them (alsa-ucm-conf's Realtek ALC4080 profile).
REALTEK_USB_OUTPUTS = {0: "Speakers", 1: "Front Headphones", 2: "S/PDIF Output"}


def audio_output_label(name: str) -> str:
    """How Ubuntu's sound settings name the PortAudio output ``name`` ("<card>: <pcm>
    (hw:C,D)"), with its ALSA device: e.g. "Front Headphones - USB Audio (hw:1,1)"; ``name``
    itself if it is not an ALSA hardware device."""
    m = re.match(r"^(?P<card>.+?): (?P<pcm>.*?) ?\(hw:(?P<c>\d+),(?P<d>\d+)\)$", name)
    if m is None:
        return name
    card, pcm, c, d = m["card"], m["pcm"].strip(" -"), int(m["c"]), int(m["d"])
    try:
        with open(f"/proc/asound/card{c}/stream0") as f:
            usb_name = f.readline()
    except OSError:
        usb_name = ""
    port = REALTEK_USB_OUTPUTS.get(d) if usb_name.startswith("Generic USB Audio") else None
    if port is None:
        port = pcm.lstrip("#").strip() and (f"Output {pcm.lstrip('#').strip()}"
                                            if pcm.startswith("#") else pcm)
    return f"{port or 'Output'} - {card} (hw:{c},{d})"


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
# Demonstration tab, ] key: the Thumb touches the pen when its largest fingertip taxel
# magnitude rises this much (force units) above its level when the Thumb starts. The largest
# taxel, not the sum: curling alone raises the sum by a few units with no contact, and the
# largest taxel jitters by under 0.005 before contact.
THUMB_CONTACT_RISE = 0.05
THUMB_ENTRY_S = 0.5  # s before the Thumb starts its level is taken over (median)
# Demonstration tab, second ] key: the start of the recording's last part (this fraction).
LAST_PART = 0.05
# How far Left / Right move the Demonstration and Processing tabs' play bar, as a fraction of
# the recording.
SEEK_FRACTION = 0.01


def thumb_contact_time(
    rec: PlaybackRecording, tip_ids: np.ndarray, counts_per_unit: float,
    rise: float = THUMB_CONTACT_RISE,
) -> float | None:
    """Time (s, on the recording's axis) the Thumb first touched the pen in a Play on hand
    recording: after the Thumb's ``start`` (the start of the recording without one), the first
    Xela reading whose largest Thumb fingertip taxel is ``rise`` above its level then; None if
    there are no readings or it never rises that far."""
    if len(rec.xela_t) == 0 or len(tip_ids) == 0 or rec.xela.shape[1] <= tip_ids.max():
        return None
    baseline = rec.xela_baseline if len(rec.xela_baseline) > tip_ids.max() else rec.xela[0]
    top = taxel_magnitudes(rec.xela, baseline, tip_ids, counts_per_unit).max(axis=1)
    start = next((e["t"] for e in rec.meta.get("timeline", [])
                  if e.get("finger") == "th" and e.get("event") == "start"), rec.xela_t[0])
    before = (rec.xela_t >= start - THUMB_ENTRY_S) & (rec.xela_t <= start)
    k = max(int(np.searchsorted(rec.xela_t, start)) - 1, 0)
    entry = float(np.median(top[before])) if before.any() else float(top[k])
    hit = np.flatnonzero((rec.xela_t > start) & (top - entry >= rise))
    return float(rec.xela_t[hit[0]]) if len(hit) else None
# How the Demonstration tab's list shows a recording's success / failure label.
LABEL_TEXT = {SUCCESS: "SUCCESS", FAILURE: "FAIL"}
# A recording's state on the Demonstration / Processing tab filters (``is_processed``).
PROCESSED = "processed"
UNPROCESSED = "unprocessed"
# Demonstration tab filters: (name, check box text), its marks and its states.
DEMONSTRATION_FILTERS = (
    (SUCCESS, "Success"), (FAILURE, "Failed"), (PROCESSED, "Processed"),
    (UNPROCESSED, "Unprocessed"),
)
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
        self._thumb_contact: float | None = None  # first Thumb contact of the recording (s)
        self._jump_index = -1  # the ] / [ jump target last gone to (-1: none since picked)

        # Left: the recordings.
        left = self._recordings_panel()

        # Middle: controls and plots (rows: position / velocity / effort, columns: fingers).
        self.title = QtWidgets.QLabel("Pick a recording")
        self.play_btn = QtWidgets.QPushButton("Play")
        self.play_btn.setToolTip("Play the recording back (nothing is sent to the hand)")
        self.slider = self._make_slider()
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
            self.output_combo.addItem(audio_output_label(name), name)
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

        # Right: the camera recording with the bounding box (Bounding box over it turns it
        # off), and the FK taxels.
        self.camera = CameraView("")
        self.camera.setWordWrap(True)
        self.camera.set_message("Pick a recording")
        self.bbox_radio = QtWidgets.QRadioButton("Bounding box")
        self.bbox_radio.setAutoExclusive(False)  # alone: a click turns it off again
        self.bbox_radio.setChecked(True)
        self.bbox_radio.setToolTip("Draw the run's pen box on the camera recording")
        self.bbox_radio.toggled.connect(lambda _: self._redraw_frame())
        camera_box = QtWidgets.QWidget()
        camera_layout = QtWidgets.QVBoxLayout(camera_box)
        camera_layout.setContentsMargins(0, 0, 0, 0)
        camera_layout.addWidget(self.bbox_radio)
        camera_layout.addWidget(self.camera, 1)
        self.hand = HandView(
            node.sim_topic, node.xela_topic, node.counts_per_unit, waiting="Pick a recording"
        )
        right = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        right.addWidget(camera_box)
        right.addWidget(self.hand)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(self._middle_column(middle))
        split.addWidget(self._right_column(right))
        split.setSizes([250, 900, 500])
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(split)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._tick)
        keys, keys_text = self._player_keys()
        self._add_keys(keys)
        self.play_btn.setToolTip(
            f"Play the recording back (nothing is sent to the hand). Keys: {keys_text}"
        )
        self.list.currentRowChanged.connect(self._load_picked)
        self._update_mark_buttons()
        self.play_btn.clicked.connect(self._toggle_play)
        self.output_combo.currentIndexChanged.connect(self._output_changed)
        self.slider.valueChanged.connect(
            lambda v: self.seek(v / SLIDER_STEPS_PER_SEC, from_slider=True)
        )

    def _player_keys(self) -> tuple[list[tuple[str, Callable[[], None]]], str]:
        """The player's keys (key, action) and how the Play button's tooltip lists them: Space
        plays / pauses, Left / Right move the play bar ``SEEK_FRACTION`` of the recording back /
        forward, ] / [ jump to the Thumb's first contact and the last ``LAST_PART`` (alternating),
        Up / Down pick the previous / next recording."""
        return [
            ("Space", self._toggle_play),
            ("Left", lambda: self._seek_by(-SEEK_FRACTION * self.duration)),
            ("Right", lambda: self._seek_by(SEEK_FRACTION * self.duration)),
            ("[", lambda: self._jump_to_thumb_contact(-1)),
            ("]", lambda: self._jump_to_thumb_contact(1)),
            ("Up", lambda: self._step_recording(-1)),
            ("Down", lambda: self._step_recording(1)),
        ], (f"Space play / pause, Left / Right {100 * SEEK_FRACTION:g} % of the recording back / "
            f"forward, ] / [ the Thumb's first contact, then the last {LAST_PART:.0%} "
            "(alternating), Up / Down previous / next recording")

    def _add_keys(self, keys: list[tuple[str, Callable[[], None]]]) -> None:
        """Shortcuts (key, action) that work while this tab is shown."""
        for key, action in keys:
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(action)

    def _recordings_panel(self) -> QtWidgets.QWidget:
        """The left panel: the recordings list (``self.list``), Success / Fail (keys S / F) and
        Delete for the picked one, and Refresh."""
        self.list = QtWidgets.QListWidget()
        self.list.setToolTip("Play on hand recordings of the Compose tab, newest first")
        self.filter_checks: dict[str, QtWidgets.QCheckBox] = {}
        filters = QtWidgets.QGridLayout()
        for i, (key, text) in enumerate(DEMONSTRATION_FILTERS):
            check = QtWidgets.QCheckBox(text)
            check.toggled.connect(lambda _: self.refresh_recordings())
            filters.addWidget(check, i // 2, i % 2)
            self.filter_checks[key] = check
        self.filter_checks[PROCESSED].setToolTip(
            f"Recordings with an '{EPISODE_START_EVENT}' and a '{EPISODE_END_EVENT}' event "
            "(set on the Processing tab)"
        )
        self.filter_checks[UNPROCESSED].setToolTip("Recordings that are not processed")
        self.count_label = QtWidgets.QLabel()
        refresh_btn = QtWidgets.QPushButton("Refresh")
        self.success_btn = QtWidgets.QPushButton("Success (S)")
        self.success_btn.setToolTip(
            "Mark the picked recording as a success (press again to clear the mark). Key: S"
        )
        self.fail_btn = QtWidgets.QPushButton("Fail (F)")
        self.fail_btn.setToolTip(
            "Mark the picked recording as a failure (press again to clear the mark). Key: F"
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
        left_layout.addLayout(filters)
        left_layout.addWidget(self.list, 1)
        left_layout.addWidget(self.count_label)
        left_layout.addLayout(mark_row)
        left_layout.addWidget(refresh_btn)
        refresh_btn.clicked.connect(self.refresh_recordings)
        self.success_btn.clicked.connect(lambda: self._mark(SUCCESS))
        self.fail_btn.clicked.connect(lambda: self._mark(FAILURE))
        self.delete_btn.clicked.connect(self._delete_picked)
        self._add_keys([("S", lambda: self._mark(SUCCESS)), ("F", lambda: self._mark(FAILURE))])
        return left

    def _middle_column(self, player: QtWidgets.QWidget) -> QtWidgets.QWidget:
        """The middle of the tab around ``player`` (the title, controls and plots)."""
        return player

    def _right_column(self, views: QtWidgets.QWidget) -> QtWidgets.QWidget:
        """The right of the tab around ``views`` (the camera and the FK taxels)."""
        return views

    def _make_slider(self) -> QtWidgets.QSlider:
        """The play bar."""
        return QtWidgets.QSlider(QtCore.Qt.Horizontal)

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        self.refresh_recordings()

    # ---- recordings ---------------------------------------------------------------------

    def _demo_matches(self, saved: dict) -> bool:
        """Whether a recording's label file matches a ticked mark (Success / Failed) and a
        ticked state (Processed / Unprocessed); a group with none ticked does not filter."""
        marks = [k for k in (SUCCESS, FAILURE) if self.filter_checks[k].isChecked()]
        states = [k for k in (PROCESSED, UNPROCESSED) if self.filter_checks[k].isChecked()]
        processed = PROCESSED if is_processed(saved) else UNPROCESSED
        return ((not marks or saved.get("label") in marks)
                and (not states or processed in states))

    def refresh_recordings(self) -> None:
        """Lists the Play on hand recordings that match the ticked filters, newest first,
        keeping the picked one."""
        current = self.list.currentItem()
        keep = current.data(QtCore.Qt.UserRole) if current is not None else None
        every = list_playbacks(self.store.compose_playback_dir)
        paths = [path for path in every if self._demo_matches(load_label(path) or {})]
        self.count_label.setText(f"{len(paths)} shown of {len(every)} recordings")
        self._plays = None  # the Thumb plays, read when a recording has no press label yet
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

    def _press_label(self, path: str) -> str:
        """How the recording's Thumb press ended (``click_press_labels``), worked out and saved
        the first time."""
        if not (load_label(path) or {}).get("click_press"):
            if getattr(self, "_plays", None) is None:
                self._plays = ThumbPlays(self.store.demo_dir)
            return click_press_label(path, self._plays)
        return click_press_label(path)

    def _show_label(self, item: QtWidgets.QListWidgetItem) -> None:
        """The list entry of a recording, with its success / failure label and colour, and how
        its Thumb press ended."""
        path = item.data(QtCore.Qt.UserRole)
        press = self._press_label(path)
        saved = load_label(path) or {}
        label = saved.get("label")
        text = f"{play_list_text(path)} \u00b7 press: {PRESS_SHORT.get(press, press)}"
        if is_processed(saved):
            text += "  [processed]"
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
        """Marks the picked recording as ``label``; marking it with its own label clears it.
        Changing a mark it already has (to the other one, or clearing it) asks first."""
        item = self.list.currentItem()
        if item is None:
            return
        path = item.data(QtCore.Qt.UserRole)
        saved = load_label(path) or {}
        current = saved.get("label")
        if current in LABEL_TEXT:
            name = os.path.splitext(os.path.basename(path))[0]
            by = "" if saved.get("manual") else " by label_playbacks"
            change = ("clear the mark" if current == label
                      else f"change it to {LABEL_TEXT[label]}")
            box = QtWidgets.QMessageBox(self)
            box.setIcon(QtWidgets.QMessageBox.Warning)
            box.setWindowTitle("Change mark")
            box.setText(f"'{name}' is already marked {LABEL_TEXT[current]}{by}.")
            box.setInformativeText(f"Are you sure you want to {change}?")
            box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            box.setDefaultButton(QtWidgets.QMessageBox.No)
            if box.exec_() != QtWidgets.QMessageBox.Yes:
                self._update_mark_buttons()  # a clicked button shows the old mark again
                return
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
        saved = load_label(path) or {}
        press = saved.get("click_press")
        why = saved.get("click_press_why", "")
        press_html = "" if not press else (
            f"<br>click press: <b>{PRESS_SHORT.get(press, press)}</b>"
            + (f" ({why})" if why else "")
        )
        self.title.setText(
            f"<b>{rec.name}</b>: {self.duration:.1f} s, {rec.meta.get('ended', '?')} ({takes})"
            + press_html
        )
        self._plot(rec)
        self._jump_index = -1
        self._thumb_contact = thumb_contact_time(
            rec, self._tip_ids["th"], self.node.counts_per_unit
        )
        if self._thumb_contact is not None:
            self._mark_thumb_contact(self._thumb_contact)
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

    def _mark_thumb_contact(self, t: float) -> None:
        """A "TH contact" line at ``t`` on the Thumb's plots (where ] jumps to)."""
        color = "#00bcd4"
        for r, field_name in enumerate([f for f, _, _ in DEMO_ROWS] + [DEMO_TIP_ROW]):
            plot = self._plots.get((field_name, "th"))
            if plot is None:
                continue
            line = pg.InfiniteLine(
                t, angle=90, pen=pg.mkPen(color, width=1.5, style=QtCore.Qt.DashLine),
                label="TH contact" if r in (0, len(DEMO_ROWS)) else None,
                labelOpts={"position": 0.5, "color": color},
            )
            plot.addItem(line)
            self._marks.append((plot, line))

    def _jump_to_thumb_contact(self, step: int) -> None:
        """] (``step`` 1) / [ (-1): the play bar to the Thumb's first contact with the pen, then
        (next press) to the start of the last ``LAST_PART`` of the recording, then back, and so
        on ([ goes through them the other way); playing on from there if it plays. Without a
        Thumb contact, always the last part."""
        if self.rec is None:
            return
        last = (1.0 - LAST_PART) * self.duration
        targets = [(self._thumb_contact, "Thumb contact")] if self._thumb_contact is not None else []
        targets.append((last, f"last {LAST_PART:.0%}"))
        self._jump_index = (self._jump_index + step) % len(targets)
        t, what = targets[self._jump_index]
        self.seek(t)
        if self._timer.isActive():
            self._play_audio()  # heard from the new time
        note = "" if self._thumb_contact is not None else ", no Thumb contact found"
        self.time_label.setText(f"{self.time_label.text()}  ({what}{note})")

    def _seek_by(self, dt: float) -> None:
        """Moves the play bar ``dt`` s (back if negative)."""
        if self.rec is None:
            return
        self.seek(self.now + dt)
        if self._timer.isActive():
            self._play_audio()  # heard from the new time

    def _redraw_frame(self) -> None:
        """Shows the camera frame at the play bar again (with or without the bounding box)."""
        self._video.reread()
        self.seek(self.now)

    def _step_recording(self, step: int) -> None:
        """Up / Down arrow: the previous / next recording in the list."""
        count = self.list.count()
        if count == 0:
            return
        row = self.list.currentRow()
        row = 0 if row < 0 else min(max(row + step, 0), count - 1)
        if row != self.list.currentRow():
            self.list.setCurrentRow(row)
            self.list.scrollToItem(self.list.currentItem())

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
                if corners is not None and self.bbox_radio.isChecked():
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


# Processing tab filters: (name, check box text) of the label filters, and the processed one.
PROCESSING_LABEL_FILTERS = ((SUCCESS, "Success"), (FAILURE, "Failure"))
NEEDS_MANUAL_LABEL = "needs_manual_label"
# Label file key: the names of the events found by an automation that were rejected.
REJECTED = "rejected"
# Events the Processing tab's automations add to be confirmed (Process click: the click).
AUTOMATION_EVENTS = (CLICK_EVENT,)


def to_be_confirmed(label: dict) -> bool:
    """Whether a label file has an event to be confirmed (found by Process click)."""
    return any((e.get("params") or {}).get(TO_BE_CONFIRMED) for e in label.get("events", []))


def needs_manual_label(label: dict) -> bool:
    """Whether a recording's event found by an automation was rejected (``rejected`` in its
    label file) and the event was not marked by hand since."""
    names = {e.get("name") for e in label.get("events", [])}
    return any(name not in names for name in label.get(REJECTED, []))


def is_processed(label: dict) -> bool:
    """Whether a recording is processed: it has an ``episode_start`` and a ``terminal`` event
    (not to be confirmed), or ``processed`` set in its label file."""
    names = {
        e.get("name") for e in label.get("events", [])
        if not (e.get("params") or {}).get(TO_BE_CONFIRMED)
    }
    return {EPISODE_START_EVENT, EPISODE_END_EVENT} <= names or bool(label.get(PROCESSED))


class ClickProcessSignals(QtCore.QObject):
    """Process click's (or the Sparsh-skin transform's) thread to the Processing tab: progress
    text, recordings done of how many (the progress bar), then the summary."""

    progress = QtCore.pyqtSignal(str)
    step = QtCore.pyqtSignal(int, int)
    done = QtCore.pyqtSignal(str)

# maintain_touch / click_press trace events that do not end a contact.
CONTACT_KEEP_EVENTS = ("slip", "saturated")


def finger_play(store: TakeStore, recording: str, finger: str, take_path: str) -> str | None:
    """The play of ``finger``'s take saved with the Play on hand ``recording`` (as
    ``ThumbPlays.find``: the one saved just before it)."""
    try:
        saved = os.path.getmtime(recording)
        take_name = os.path.splitext(os.path.basename(take_path))[0]
        plays = [(saved - os.path.getmtime(p), p) for p in store.list_playbacks(finger, take_name)]
    except OSError:
        return None
    lo, hi = PAIR_WINDOW_S
    near = [(gap, p) for gap, p in plays if lo <= gap <= hi]
    return min(near, key=lambda gp: (gp[0] < 0, abs(gp[0])))[1] if near else None


def trace_contact_spans(trace: list[dict], end: float) -> list[tuple[float, float]]:
    """(start, end) trace times a maintain_touch / click_press trace was in contact: from each
    "contact" to the next event that is not a slip or saturation (``end`` if none)."""
    spans, since = [], None
    for event in trace:
        if since is None:
            if event.get("event") == "contact":
                since = event["t"]
        elif event.get("event") not in CONTACT_KEEP_EVENTS:
            spans.append((since, event["t"]))
            since = None
    if since is not None:
        spans.append((since, end))
    return spans


def recorded_contacts(
    store: TakeStore, recording: str, rec: PlaybackRecording, duration: float
) -> dict[str, list[tuple[float, float]]]:
    """When each finger was in contact with the pen in a Play on hand recording (its time, s),
    as the Compose tab's Contact lights showed it: its ``maintain_touch`` holding or its
    ``click_press`` pressing. Read from the traces of the finger's own play (saved with the
    recording), lined up by the first trace event, which is at the take time its region
    starts; fingers whose play is not found have none."""
    timeline = rec.meta.get("timeline", [])
    contacts: dict[str, list[tuple[float, float]]] = {}
    for finger, take_path in rec.meta.get("takes", {}).items():
        start = next((e["t"] for e in timeline
                      if e["finger"] == finger and e["event"] == "start"), None)
        end = next((e["t"] for e in timeline
                    if e["finger"] == finger and e["event"] in ("finished", "stopped")), duration)
        play = finger_play(store, recording, finger, take_path) if start is not None else None
        if play is None:
            continue
        try:
            with np.load(play, allow_pickle=False) as data:  # only the small entries are read
                meta = json.loads(str(data["meta"]))
                cmd_t, local = data["cmd_t"], data["cmd_local"]
        except Exception:  # noqa: BLE001 - an unreadable play shows no contact
            continue
        spans = []
        for key in ("maintain_touch_trace", "click_press_trace"):
            trace = meta.get(key) or []
            if not trace or not trace[0].get("region") or not len(local):
                continue
            side = np.sign(local - trace[0]["region"][0])
            entered = np.flatnonzero((side == 0) | (side != side[0]))
            shift = start + float(cmd_t[entered[0] if len(entered) else 0]) - trace[0]["t"]
            spans += [(a + shift, b + shift) for a, b in trace_contact_spans(trace, end - shift)]
        contacts[finger] = sorted(spans)
    return contacts


# The Processing tab's Reward shows the terminal reward this long from ``terminal`` (s).
REWARD_TERMINAL_S = 0.25


def set_light(light: QtWidgets.QLabel, color: str) -> None:
    if light.property("color") != color:
        light.setProperty("color", color)
        light.setStyleSheet(SLIP_LIGHT_STYLE.format(color))


class ProcessingTab(DemonstrationTab):
    """The Play on hand recordings marked success or failure on the Demonstration tab, listed
    when they match a ticked mark (Success, Failure) and a ticked state (Processed:
    ``is_processed``, To be confirmed, Needs manual label), a group with none ticked not filtering; the picked one plays back as on the Demonstration tab.

    Events of events.json whose ``tab`` has "processing" are added at the play bar as on the
    Edit tab (a duration event takes two clicks: its start, then its end) and saved in the
    recording's label file as ``events``; they are marked on the play bar and the plots and
    listed next to the plots (click to seek, Edit renames, Delete removes)."""

    REGION_ALPHA = 50
    PENDING_ALPHA = 30

    def __init__(
        self, node: LeapStateListener, store: TakeStore, event_defs: dict[str, dict]
    ) -> None:
        self.event_defs = event_defs  # all of them, for the colours of saved events
        self._addable = {
            name: info for name, info in event_defs.items()
            if PROCESSING_TAB in event_tabs(info)
        }
        self.events: list[TakeEvent] = []  # the picked recording's
        self._pending: TakeEvent | None = None  # duration event whose end is not marked yet
        self._event_items: list[tuple[pg.PlotItem, pg.GraphicsObject]] = []
        self._pending_items: list[tuple[pg.PlotItem, pg.GraphicsObject]] = []
        self._event_marks: list[tuple[int, QtGui.QColor, str]] = []  # saved events on the bar
        self._event_spans: list[tuple[int, int, QtGui.QColor, str]] = []
        self._click_thread: threading.Thread | None = None  # Process click, while it runs
        self._click_stop = threading.Event()
        self._click_signals = ClickProcessSignals()
        self._sparsh_thread: threading.Thread | None = None  # Sparsh-skin transform, running
        self._sparsh_signals = ClickProcessSignals()
        super().__init__(node, store)
        self._click_signals.progress.connect(self.process_status.setText)
        self._click_signals.step.connect(self._bar_step)
        self._click_signals.done.connect(self._process_click_done)
        self._sparsh_signals.step.connect(self._bar_step)
        self._sparsh_signals.progress.connect(self.process_status.setText)
        self._sparsh_signals.done.connect(self._sparsh_transform_done)

    def _recordings_panel(self) -> QtWidgets.QWidget:
        """The left panel: the filters, the recordings that match them, their count, Refresh
        and Process click."""
        self.list = QtWidgets.QListWidget()
        self.list.setToolTip(
            "Play on hand recordings marked success / failure on the Demonstration tab, "
            "newest first"
        )
        self.filter_checks: dict[str, QtWidgets.QCheckBox] = {}
        filters = QtWidgets.QGridLayout()
        for i, (key, text) in enumerate((*PROCESSING_LABEL_FILTERS, (PROCESSED, "Processed"),
                                         (TO_BE_CONFIRMED, "To be confirmed"),
                                         (NEEDS_MANUAL_LABEL, "Needs manual label"))):
            check = QtWidgets.QCheckBox(text)
            check.setChecked(key in LABEL_TEXT)  # the states narrow the list when ticked
            check.toggled.connect(lambda _: self.refresh_recordings())
            filters.addWidget(check, i // 2, i % 2)
            self.filter_checks[key] = check
        self.filter_checks[PROCESSED].setToolTip(
            f"Recordings with an '{EPISODE_START_EVENT}' and a '{EPISODE_END_EVENT}' event "
            "(not to be confirmed), or 'processed' set in their label file"
        )
        self.filter_checks[TO_BE_CONFIRMED].setToolTip(
            f"Recordings with a '{CLICK_EVENT}' event found by Process click and not confirmed "
            "yet"
        )
        self.filter_checks[NEEDS_MANUAL_LABEL].setToolTip(
            "Successful recordings whose event found by Process click was rejected and that "
            "have no such event marked by hand yet"
        )
        self.count_label = QtWidgets.QLabel()
        # Shown while To be confirmed is ticked: the picked recording's events of the picked
        # name that an automation found are confirmed or rejected.
        self.confirm_combo = QtWidgets.QComboBox()
        self.confirm_combo.setToolTip("The event (found by an automation) to confirm or reject")
        for name in AUTOMATION_EVENTS:
            self.confirm_combo.addItem(color_swatch(self._color(name)), name, name)
        self.confirm_event_btn = QtWidgets.QPushButton("Confirm (C)")
        self.confirm_event_btn.setToolTip(
            "Keep the picked recording's event to be confirmed (a confirmed click is also a "
            "Process click sample)"
        )
        self.reject_event_btn = QtWidgets.QPushButton("Reject (R)")
        self.reject_event_btn.setToolTip(
            "Delete the picked recording's event to be confirmed: it stays a success, tagged "
            "[needs manual label] until you mark the event by hand (Process click does not "
            "search it again)"
        )
        self.confirm_box = QtWidgets.QWidget()
        confirm_row = QtWidgets.QHBoxLayout(self.confirm_box)
        confirm_row.setContentsMargins(0, 0, 0, 0)
        confirm_row.addWidget(self.confirm_combo, 1)
        confirm_row.addWidget(self.confirm_event_btn)
        confirm_row.addWidget(self.reject_event_btn)
        to_confirm = self.filter_checks[TO_BE_CONFIRMED]
        self.confirm_box.setVisible(to_confirm.isChecked())
        to_confirm.toggled.connect(self.confirm_box.setVisible)
        self.confirm_combo.currentIndexChanged.connect(lambda _: self._update_confirm_buttons())
        self.confirm_event_btn.clicked.connect(lambda: self._resolve_picked(confirm=True))
        self.reject_event_btn.clicked.connect(lambda: self._resolve_picked(confirm=False))
        left = QtWidgets.QGroupBox("Recordings")
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.addLayout(filters)
        left_layout.addWidget(self.list, 1)
        left_layout.addWidget(self.count_label)
        left_layout.addWidget(self.confirm_box)
        return left

    def _update_mark_buttons(self) -> None:
        """No Success / Fail / Delete buttons here: recordings are marked on the Demonstration
        tab."""

    # The recording's contact spans by finger, slips and fingers with a take (see ``_load``).
    _contacts: dict[str, list[tuple[float, float]]] = {}
    _slips: list[dict] = []
    _played: set[str] = set()

    def _middle_column(self, player: QtWidgets.QWidget) -> QtWidgets.QWidget:
        """The top third: Episodes, Automation and ``self.top_panel`` (empty for now); the
        player under it, with the Reward and the Contact and Slip lights under its play bar."""
        row = QtWidgets.QHBoxLayout()
        # (episode_start, terminal, label) of the recording's confirmed episode, or None.
        self._reward_span: tuple[float, float, str] | None = None
        self.reward_label = QtWidgets.QLabel()
        self.reward_label.setToolTip(
            "The episode's reward at the play bar's time (Process reward's values): Every step "
            f"from '{EPISODE_START_EVENT}' to '{EPISODE_END_EVENT}', Success / Fail at "
            f"'{EPISODE_END_EVENT}' (its last timestep); — outside the episode or without a "
            f"confirmed '{EPISODE_START_EVENT}' and '{EPISODE_END_EVENT}'"
        )
        self.reward_label.setMinimumWidth(
            self.reward_label.fontMetrics().horizontalAdvance("Reward: -000.000 (terminal)")
        )
        self.reward_label.setText("Reward: <span style='color:#9e9e9e'>— (no episode)</span>")
        row.addWidget(self.reward_label)
        row.addSpacing(12)
        row.addWidget(QtWidgets.QLabel("Contact:"))
        self.contact_lights: dict[str, QtWidgets.QLabel] = {}
        for finger, _ in FINGERS:
            light = QtWidgets.QLabel()
            light.setToolTip(
                f"{FINGER_LABEL[finger]} at the play bar's time: green in contact with the pen "
                "(maintain touch holding, or the Thumb's click press pressing; from the "
                "finger's own play saved with the recording)"
            )
            self.contact_lights[finger] = light
            row.addWidget(light)
            row.addWidget(QtWidgets.QLabel(finger.upper()))
            row.addSpacing(4)
        row.addSpacing(12)
        row.addWidget(QtWidgets.QLabel("Slip:"))
        self.slip_lights: dict[str, QtWidgets.QLabel] = {}
        for finger in SLIP_FINGERS:
            light = QtWidgets.QLabel()
            light.setToolTip(
                f"{FINGER_LABEL[finger]} at the play bar's time: grey not in contact, green in "
                f"contact, red for {SLIP_LIGHT_S:.0f} s after a slip (the recording's slips)"
            )
            self.slip_lights[finger] = light
            row.addWidget(light)
            row.addWidget(QtWidgets.QLabel(finger.upper()))
            row.addSpacing(4)
        row.addStretch(1)
        self._show_lights()
        # The player's rows: title, play bar, audio output, plots.
        player_layout = player.layout()
        player_layout.insertLayout(2, row)

        # Under the lights: the event picker with Add event (Start / End event) and Cancel.
        self.event_combo = QtWidgets.QComboBox()
        for name, info in self._addable.items():
            text = f"{name}  (duration)" if self._is_duration(name) else name
            self.event_combo.addItem(color_swatch(self._color(name)), text, name)
            self.event_combo.setItemData(
                self.event_combo.count() - 1,
                f"[{info.get('type', '')}] {info.get('description', '')}",
                QtCore.Qt.ToolTipRole,
            )
        self.add_btn = QtWidgets.QPushButton("Add event")
        self.add_btn.setMinimumWidth(90)
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setToolTip("Discard the duration event being marked")
        self.cancel_btn.hide()
        event_row = QtWidgets.QHBoxLayout()
        event_row.addWidget(self.event_combo, 1)
        event_row.addWidget(self.add_btn)
        event_row.addWidget(self.cancel_btn)
        player_layout.insertLayout(3, event_row)

        # Next to the plots: the recording's events, with Edit and Delete.
        self.event_list = QtWidgets.QListWidget()
        self.event_list.setFixedWidth(180)
        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.delete_event_btn = QtWidgets.QPushButton("Delete")
        list_buttons = QtWidgets.QHBoxLayout()
        list_buttons.addWidget(self.edit_btn)
        list_buttons.addWidget(self.delete_event_btn)
        events_box = QtWidgets.QVBoxLayout()
        events_box.addWidget(QtWidgets.QLabel("Events"))
        events_box.addWidget(self.event_list, 1)
        events_box.addLayout(list_buttons)
        body = QtWidgets.QHBoxLayout()
        index = player_layout.indexOf(self.plots)
        player_layout.removeWidget(self.plots)
        body.addWidget(self.plots, 1)
        body.addLayout(events_box)
        player_layout.insertLayout(index, body, 1)

        self.add_btn.clicked.connect(self.add_event)
        self.cancel_btn.clicked.connect(self.cancel_pending)
        self.event_combo.currentIndexChanged.connect(lambda _: self._update_event_buttons())
        self.edit_btn.clicked.connect(self.edit_selected_event)
        self.delete_event_btn.clicked.connect(self.delete_selected_event)
        self.event_list.itemClicked.connect(self._on_event_item)
        self.event_list.itemActivated.connect(self._on_event_item)
        self.event_list.itemSelectionChanged.connect(self._update_event_buttons)
        self._update_event_buttons()

        # The top third: Episodes and Automation over ``self.top_panel`` (empty for now).
        self.process_click_btn = QtWidgets.QPushButton("Process click")
        self.process_click_btn.setToolTip(
            f"Send the confirmed '{CLICK_EVENT}' events as click samples to the click "
            "detector's service, which searches the successful recordings without one (not "
            "searched before); the click it finds is added as an event to be confirmed"
        )
        self.process_click_btn.clicked.connect(self._process_click)
        self.process_failure_btn = QtWidgets.QPushButton("Process failure")
        self.process_failure_btn.setToolTip(
            f"Mark '{EPISODE_END_EVENT}' and '{episode_processing.TRUNCATED}' at "
            f"'{EPISODE_START_EVENT}' + the truncation length on every failed recording "
            f"without a '{EPISODE_END_EVENT}' (and move those it marked before, if the length "
            f"changed); recordings that end earlier get '{EPISODE_END_EVENT}' and "
            f"'{episode_processing.FAIL}' at their last timestep"
        )
        self.process_failure_btn.clicked.connect(self._process_failure)
        self.process_reward_btn = QtWidgets.QPushButton("Process reward")
        self.process_reward_btn.setToolTip(
            "Set the rewards of every episode in "
            f"{sparsh_processing.DEFAULT_OUTPUT_NAME}/ (Sparsh-skin transform): Success at the "
            "last timestep of a success, Fail at the last timestep of a failure, Every step at "
            "every other timestep. The Sparsh-skin transform uses them too."
        )
        self.process_reward_btn.clicked.connect(self._process_reward)
        saved_rewards = episode_processing.load_rewards(self.store.compose_playback_dir)
        self.reward_spins: dict[str, QtWidgets.QDoubleSpinBox] = {}
        reward_row = QtWidgets.QHBoxLayout()
        reward_row.addWidget(self.process_reward_btn)
        for key, text, tip in (
            ("success", "Success:", "Reward at the last timestep of a successful episode"),
            ("fail", "Fail:", "Reward at the last timestep of a failed episode"),
            ("step", "Every step:", "Reward at every other timestep"),
        ):
            spin = double_spin(
                -1e6, 1e6, 0.1, 3, "",
                f"{tip} (saved with the recordings in {episode_processing.SETTINGS_NAME})",
            )
            spin.setValue(saved_rewards[key])
            spin.valueChanged.connect(lambda _: (self._save_rewards(), self._show_reward()))
            self.reward_spins[key] = spin
            reward_row.addWidget(QtWidgets.QLabel(text))
            reward_row.addWidget(spin)
        self.sparsh_transform_btn = QtWidgets.QPushButton("Sparsh-skin transform")
        self.sparsh_transform_btn.setToolTip(
            "Preprocess every episode ('episode_start' to 'terminal' of a success / failure) as "
            "Sparsh-skin does, by the sparsh_skin_transformation service, into "
            f"{sparsh_processing.DEFAULT_OUTPUT_NAME}/ next to the recordings: the LEQ_DV3 "
            "world model's convert_episodes.py input (episodes already there are kept)"
        )
        self.sparsh_transform_btn.clicked.connect(self._sparsh_transform)
        self.sparsh_baseline_combo = QtWidgets.QComboBox()
        self.sparsh_baseline_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.sparsh_baseline_combo.setToolTip(
            "The Baseline tab recording whose no-contact baseline the Sparsh-skin transform "
            f"subtracts from every episode (tagged {SPARSH_BASELINE_TAG} there); episodes "
            "written with another baseline are written again"
        )
        self.sparsh_baseline_combo.activated.connect(self._sparsh_baseline_picked)
        self.dv3_btn = QtWidgets.QPushButton("Process for DreamerV3")
        self.dv3_btn.setToolTip(
            f"Convert the episodes in {sparsh_processing.DEFAULT_OUTPUT_NAME}/ into DreamerV3 "
            f"replay chunks in {dv3_processing.DEFAULT_OUTPUT_NAME}/ next to it (as LEQ_DV3's "
            "convert_episodes.py does: actions shifted one step and scaled to [-1, 1], "
            "is_first / is_last / is_terminal), replacing the chunks there; copy them to "
            "LEQ_DV3/data/leap/<task>/ (do not run convert_episodes.py on them)"
        )
        self.dv3_btn.clicked.connect(self._process_dv3)
        self.process_status = QtWidgets.QLabel()
        # One bar for Process click, Process failure and the Sparsh-skin transform.
        self.process_bar = QtWidgets.QProgressBar()
        self.process_bar.setToolTip(
            "Recordings done by the running Process click, Process failure or Sparsh-skin "
            "transform"
        )
        self._bar_idle()
        self.process_status.setWordWrap(True)
        automation = QtWidgets.QGroupBox("Automation")
        automation_layout = QtWidgets.QHBoxLayout(automation)
        automation_buttons = QtWidgets.QVBoxLayout()
        automation_buttons.addWidget(self.process_click_btn)
        automation_buttons.addWidget(self.process_failure_btn)
        automation_buttons.addLayout(reward_row)
        sparsh_row = QtWidgets.QHBoxLayout()
        sparsh_row.addWidget(self.sparsh_transform_btn)
        sparsh_row.addWidget(QtWidgets.QLabel("Baseline:"))
        sparsh_row.addWidget(self.sparsh_baseline_combo, 1)
        automation_buttons.addLayout(sparsh_row)
        automation_buttons.addWidget(self.dv3_btn)
        automation_buttons.addWidget(self.process_bar)  # under Process for DreamerV3
        automation_buttons.addStretch(1)
        automation_layout.addLayout(automation_buttons)
        automation_layout.addWidget(self.process_status, 1)
        self.top_panel = QtWidgets.QWidget()
        column = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._episodes_box(), 1)
        layout.addWidget(automation, 1)
        layout.addWidget(self.top_panel, 2)
        layout.addWidget(player, 8)  # the player keeps the bottom two thirds
        return column

    def _right_column(self, views: QtWidgets.QWidget) -> QtWidgets.QWidget:
        """Refresh (the recordings list) over the camera and the FK taxels."""
        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.setToolTip("List the recordings again (their labels and events from disk)")
        refresh_btn.clicked.connect(self.refresh_recordings)
        column = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(refresh_btn)
        layout.addWidget(views, 1)
        return column

    def _make_slider(self) -> QtWidgets.QSlider:
        """The play bar, with the events marked over it."""
        return SpanBookmarkSlider()

    def _player_keys(self) -> tuple[list[tuple[str, Callable[[], None]]], str]:
        """Space plays / pauses, E adds the picked event (a duration event: starts it, then
        ends it), C / R confirm / reject the event to be confirmed, Left / Right move the play bar ``SEEK_FRACTION`` of the recording
        back / forward, [ / ]
        jump to the start of the previous / next event, Up / Down pick the previous / next
        recording."""
        return [
            ("Space", self._toggle_play),
            ("E", self.add_event),
            ("C", lambda: self._resolve_picked(confirm=True)),
            ("R", lambda: self._resolve_picked(confirm=False)),
            ("Left", lambda: self._seek_by(-SEEK_FRACTION * self.duration)),
            ("Right", lambda: self._seek_by(SEEK_FRACTION * self.duration)),
            ("[", lambda: self._jump_to_event(-1)),
            ("]", lambda: self._jump_to_event(1)),
            ("Up", lambda: self._step_recording(-1)),
            ("Down", lambda: self._step_recording(1)),
        ], ("Space play / pause, E add event (a duration event: start, then end), C / R "
            "confirm / reject the event to be confirmed, Left / Right "
            f"{100 * SEEK_FRACTION:g} % of the recording back / forward, [ / ] start "
            "of the previous / next event, Up / Down previous / next recording")

    def _jump_to_event(self, step: int) -> None:
        """Moves the play bar to the start of the previous (``step`` -1) or next (1) event."""
        if self.rec is None:
            return
        starts = sorted({e.t for e in self.events})
        tol = EVENT_TIME_RESOLUTION / 2
        if step > 0:
            t = next((s for s in starts if s > self.now + tol), None)
        else:
            t = next((s for s in reversed(starts) if s < self.now - tol), None)
        if t is not None:
            self.seek(t)
            if self._timer.isActive():
                self._play_audio()  # heard from the new time

    def _load(self, path: str | None) -> None:
        self._contacts, self._slips, self._played = {}, [], set()
        self.events, self._pending = [], None
        super()._load(path)
        if self.rec is not None:
            self._played = set(self.rec.meta.get("takes", {}))
            self._slips = sorted(self.rec.meta.get("slips", []), key=lambda s: s["t"])
            self._contacts = recorded_contacts(self.store, path, self.rec, self.duration)
            self.events = [
                TakeEvent(**e) for e in (load_label(path) or {}).get("events", [])
            ]
        self._show_lights()
        self._refresh_events()

    def seek(self, t: float, from_slider: bool = False) -> None:
        super().seek(t, from_slider)
        self._show_lights()
        if self._pending is not None:
            self._show_pending()
        self._update_event_buttons()

    # ---- events -------------------------------------------------------------------------

    def _color(self, name: str, alpha: int = 255) -> QtGui.QColor:
        color = QtGui.QColor(self.event_defs.get(name, {}).get("color", UNKNOWN_EVENT_COLOR))
        color.setAlpha(alpha)
        return color

    def _is_duration(self, name: str) -> bool:
        return self.event_defs.get(name, {}).get("length") == "duration"

    def _event_plots(self) -> list[pg.PlotItem]:
        return [*self._plots.values(), self.audio_plot]

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

    def _draw(self, make) -> list[tuple[pg.PlotItem, pg.GraphicsObject]]:
        """``make()`` drawn on every plot."""
        items = []
        for plot in self._event_plots():
            item = make()
            plot.addItem(item, ignoreBounds=True)
            items.append((plot, item))
        return items

    def _add_default_events(self, path: str) -> None:
        """Saves the default events of a recording that has none saved (no ``events`` in its
        label file; one whose events were all deleted keeps none): ``episode_start`` at its
        first command (``cmd_t``, as the action on /cmd_xela starts there)."""
        if EPISODE_START_EVENT not in self._addable:
            return
        try:
            with np.load(path, allow_pickle=False) as data:
                cmd_t = data["cmd_t"]
            t = round(float(cmd_t[0]), 3) if len(cmd_t) else 0.0
            event = TakeEvent(
                t=t, name=EPISODE_START_EVENT,
                type=self.event_defs[EPISODE_START_EVENT].get("type", ""), added=time.time(),
            )
            update_label(path, events=[asdict(event)])
        except Exception as e:  # noqa: BLE001 - unreadable recording: no default events
            self.node.get_logger().warn(f"Processing: no default events for {path}: {e}")

    def _event_at(self, t: float) -> TakeEvent | None:
        return next((e for e in self.events if abs(e.t - t) < EVENT_TIME_RESOLUTION), None)

    def _refresh_events(self) -> None:
        """The list, play bar marks and plot lines / regions of the recording's events."""
        self._update_reward_span()
        for plot, item in self._event_items:
            plot.removeItem(item)
        self._event_items = []
        self.event_list.clear()
        self._event_marks, self._event_spans = [], []
        for i, event in enumerate(self.events, start=1):
            color = self._color(event.name)
            tip = f"{event.name} @ {event.span_text()}"
            if event.params.get(TO_BE_CONFIRMED):
                tip += f" (to be confirmed, score {event.params.get('score', 0.0):.2f})"
            item = QtWidgets.QListWidgetItem(color_swatch(color), f"{i}. {tip}")
            item.setData(QtCore.Qt.UserRole, i - 1)
            self.event_list.addItem(item)
            value = int(round(event.t * SLIDER_STEPS_PER_SEC))
            self._event_marks.append((value, color, tip))
            if event.end is None:
                self._event_items += self._draw(lambda: self._event_line(event.t, color))
            else:
                end = int(round(event.end * SLIDER_STEPS_PER_SEC))
                self._event_marks.append((end, color, tip))
                self._event_spans.append((value, end, color, tip))
                self._event_items += self._draw(
                    lambda: self._event_region(event.t, event.end, event.name, self.REGION_ALPHA)
                )
        self._show_pending()
        self._update_event_buttons()

    def _show_pending(self) -> None:
        """Play bar / plots with the saved events plus the duration event being marked, shaded
        from its start to the play bar."""
        for plot, item in self._pending_items:
            plot.removeItem(item)
        self._pending_items = []
        marks, spans = list(self._event_marks), list(self._event_spans)
        p = self._pending
        if p is not None:
            color = self._color(p.name)
            start, end = sorted((p.t, self.now))
            tip = f"{p.name} from {p.t:.2f} s (end not marked yet)"
            marks.append((int(round(p.t * SLIDER_STEPS_PER_SEC)), color, tip))
            spans.append((int(round(start * SLIDER_STEPS_PER_SEC)),
                          int(round(end * SLIDER_STEPS_PER_SEC)), color, tip))
            self._pending_items = (
                self._draw(lambda: self._event_region(start, end, p.name, self.PENDING_ALPHA))
                + self._draw(lambda: self._event_line(p.t, color))
            )
        self.slider.set_marks(marks)
        self.slider.set_spans(spans)

    def _selected_event(self) -> TakeEvent | None:
        item = self.event_list.currentItem()
        if self.rec is None or item is None or not item.isSelected():
            return None
        return self.events[item.data(QtCore.Qt.UserRole)]

    def _update_event_buttons(self) -> None:
        self._update_confirm_buttons()
        event = self._selected_event()
        selected = event is not None
        self.edit_btn.setEnabled(selected)
        self.delete_event_btn.setEnabled(selected)
        p = self._pending
        self.cancel_btn.setVisible(p is not None)
        self.event_combo.setEnabled(self.rec is not None and p is None)
        if self.rec is None or not self._addable:
            self.add_btn.setText("Add event")
            self.add_btn.setEnabled(False)
            self.add_btn.setToolTip(
                "" if self._addable
                else f"No events with \"tab\": \"{PROCESSING_TAB}\" in events.json"
            )
            return
        if p is not None:
            self.add_btn.setText("End event")
            self.add_btn.setEnabled(True)
            self.add_btn.setToolTip(
                f"Mark the end of '{p.name}' (started at {p.t:.2f} s) at the current time"
            )
            return
        duration = self._is_duration(self.event_combo.currentData())
        self.add_btn.setText("Start event" if duration else "Add event")
        existing = self._event_at(self.now)
        self.add_btn.setEnabled(existing is None)
        self.add_btn.setToolTip(
            f"'{existing.name}' already starts at this time" if existing is not None
            else "Mark where the selected event starts; click again where it ends" if duration
            else f"Store the selected event at the current time in {self.rec.name}.label.json"
        )

    def _on_event_item(self, item: QtWidgets.QListWidgetItem) -> None:
        if self.rec is not None:
            self.seek(self.events[item.data(QtCore.Qt.UserRole)].t)

    def _save_events(self, events: list[TakeEvent], title: str) -> bool:
        """Saves ``events`` as the recording's (in its label file)."""
        try:
            update_label(self.rec.path, events=[asdict(e) for e in events])
        except OSError as e:
            QtWidgets.QMessageBox.warning(
                self, title, f"Could not save the events of {self.rec.path}:\n{e}"
            )
            return False
        self.events = events
        self._refresh_events()
        return True

    def add_event(self) -> None:
        """Adds an instant event at the play bar, or starts / ends a duration event there."""
        if self.rec is None:
            return
        if self._pending is not None:
            self._end_pending()
            return
        name = self.event_combo.currentData()
        if name is None:
            return
        existing = self._event_at(self.now)
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
            self._update_event_buttons()
        elif self._save_events(self.events + [event], "Add event"):
            self.event_list.scrollToBottom()

    def _end_pending(self) -> None:
        p = self._pending
        start, end = sorted((p.t, self.now))
        if end - start < EVENT_TIME_RESOLUTION:
            QtWidgets.QMessageBox.information(
                self, "End event", f"Move the play bar to where '{p.name}' ends, then click again."
            )
            return
        existing = self._event_at(start) if start != p.t else None
        if existing is not None:
            QtWidgets.QMessageBox.information(
                self, "End event", f"There is already a '{existing.name}' event at {existing.t:.3f} s"
            )
            return
        self._pending = None
        event = TakeEvent(t=start, name=p.name, type=p.type, added=p.added, end=end)
        events = self.events + [event]
        if event.name == CLICK_EVENT:
            events = self._with_click_end(events, event)
        if self._save_events(events, "End event"):
            self.event_list.scrollToBottom()
        else:
            self._pending = p
            self._show_pending()
            self._update_event_buttons()

    def cancel_pending(self) -> None:
        self._pending = None
        self._show_pending()
        self._update_event_buttons()

    def edit_selected_event(self) -> None:
        """Renames the selected event to another of the same length."""
        event = self._selected_event()
        if event is None:
            return
        same_length = {
            name: info for name, info in self._addable.items()
            if self._is_duration(name) == (event.end is not None)
        }
        dialog = EditEventDialog(
            self, event, same_length, self._color,
            note=f"{self.rec.name}.label.json will be updated.",
        )
        if dialog.exec_() != QtWidgets.QDialog.Accepted or dialog.name() == event.name:
            return
        row = self.event_list.currentRow()
        name = dialog.name()
        renamed = replace(event, name=name, type=self.event_defs[name].get("type", ""))
        if self._save_events([renamed if e is event else e for e in self.events], "Edit event"):
            self.event_list.setCurrentRow(row)

    def delete_selected_event(self) -> None:
        event = self._selected_event()
        if event is None:
            return
        answer = QtWidgets.QMessageBox.warning(
            self,
            "Delete event",
            f"Delete '{event.name}' at {event.span_text()} from {self.rec.name}.label.json?\n"
            "This cannot be undone.",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )
        if answer == QtWidgets.QMessageBox.Ok:
            self._save_events([e for e in self.events if e is not event], "Delete event")

    def _with_click_end(self, events: list[TakeEvent], click: TakeEvent) -> list[TakeEvent]:
        """``events`` plus ``terminal`` and ``success`` at the end of the click event ``click``
        (those the recording has none of yet)."""
        types = {name: self.event_defs.get(name, {}).get("type", "") for name in CLICK_END_EVENTS}
        return [
            TakeEvent(**e) for e in click_processing.with_end_events(
                [asdict(e) for e in events], asdict(click), types
            )
        ]

    def _confirm_pending(self) -> list[TakeEvent]:
        """The picked recording's events to be confirmed of the confirm row's name."""
        name = self.confirm_combo.currentData()
        return [
            e for e in self.events if e.params.get(TO_BE_CONFIRMED)
            and (e.name == name or e.params.get(WITH) == name)
        ]

    def _update_confirm_buttons(self) -> None:
        pending = bool(self._confirm_pending())
        self.confirm_event_btn.setEnabled(pending and self._pending is None)
        self.reject_event_btn.setEnabled(pending and self._pending is None)

    def _resolve_picked(self, confirm: bool) -> None:
        """Confirms (keeps, as if marked by hand) or rejects (deletes) the picked recording's
        events to be confirmed of the confirm row's name, then picks the next recording when
        this one leaves the list."""
        pending = self._confirm_pending()
        if not pending:
            return
        if confirm:
            events = [
                replace(e, params={k: v for k, v in e.params.items() if k != TO_BE_CONFIRMED})
                if any(e is p for p in pending) else e
                for e in self.events
            ]
            for click in [e for e in events if e.name == CLICK_EVENT and e.end is not None]:
                events = self._with_click_end(events, click)
        else:
            events = [e for e in self.events if not any(e is p for p in pending)]
        row = self.list.currentRow()
        if self._save_events(events, "Confirm" if confirm else "Reject"):
            if not confirm:  # the event is to be marked by hand: [needs manual label]
                name = self.confirm_combo.currentData()
                rejected = (load_label(self.rec.path) or {}).get(REJECTED, [])
                try:
                    update_label(self.rec.path, **{REJECTED: sorted({*rejected, name})})
                except OSError as e:
                    QtWidgets.QMessageBox.warning(
                        self, "Reject", f"Could not save the rejection of {self.rec.path}:\n{e}"
                    )
            self.refresh_recordings()  # its [to be confirmed] tag goes
            if self.list.currentRow() < 0 and self.list.count():
                self.list.setCurrentRow(min(row, self.list.count() - 1))

    def _in_contact(self, finger: str) -> bool:
        return any(a <= self.now < b for a, b in self._contacts.get(finger, []))

    def _update_reward_span(self) -> None:
        """The episode the Reward follows: the recording's confirmed ``episode_start`` and
        ``terminal`` (its events as they are now) and its label."""
        self._reward_span = None
        if self.rec is not None:
            label = (load_label(self.rec.path) or {}).get("label")
            span = sparsh_processing.episode_span(
                {"label": label, "events": [asdict(e) for e in self.events]}
            )
            if not isinstance(span, str):
                self._reward_span = (*span, label)
        self._show_reward()

    def _show_reward(self) -> None:
        """The reward at the play bar's time."""
        if not hasattr(self, "reward_spins"):  # built after the player
            return
        span = self._reward_span
        if span is None:
            self.reward_label.setText("Reward: <span style='color:#9e9e9e'>— (no episode)</span>")
            return
        start, end, label = span
        rewards = self._rewards()
        if start <= self.now < end:
            text = f"<b>{rewards['step']:g}</b> (step)"
        elif end <= self.now < end + REWARD_TERMINAL_S:
            success = label == SUCCESS
            color = COMBO_VALID_COLOR if success else COMBO_COLLIDE_COLOR
            value = rewards["success"] if success else rewards["fail"]
            text = (f"<span style='color:{color}'><b>{value:g}</b> "
                    f"({'success' if success else 'fail'})</span>")
        else:
            text = "<span style='color:#9e9e9e'>— (outside the episode)</span>"
        self.reward_label.setText(f"Reward: {text}")

    def _show_lights(self) -> None:
        """The Contact and Slip lights (and the Reward) at the play bar's time, as the Compose
        tab showed them during the Play on hand."""
        self._show_reward()
        for finger, light in self.contact_lights.items():
            set_light(light, CONTACT_COLORS["contact" if self._in_contact(finger) else "off"])
        for finger, light in self.slip_lights.items():
            slipped = any(0.0 <= self.now - s["t"] < SLIP_LIGHT_S
                          for s in self._slips if s["finger"] == finger)
            if finger not in self._played:
                state = "off"
            elif slipped:
                state = "slip"
            else:
                state = "contact" if self._in_contact(finger) else "off"
            set_light(light, SLIP_COLORS[state])

    def _matches(self, saved: dict) -> bool:
        """Whether a recording's label file matches a ticked mark (Success / Failure) and a
        ticked state (Processed / To be confirmed / Needs manual label); a group with none ticked does not
        filter."""
        marks = [key for key, _ in PROCESSING_LABEL_FILTERS if self.filter_checks[key].isChecked()]
        states = [
            test for key, test in ((PROCESSED, is_processed), (TO_BE_CONFIRMED, to_be_confirmed),
                                   (NEEDS_MANUAL_LABEL, needs_manual_label))
            if self.filter_checks[key].isChecked()
        ]
        return ((not marks or saved.get("label") in marks)
                and (not states or any(test(saved) for test in states)))

    def refresh_recordings(self) -> None:
        """Lists the labelled recordings that match the ticked filters, keeping the picked one.
        A recording without saved events gets the default ones (``_add_default_events``)."""
        current = self.list.currentItem()
        keep = current.data(QtCore.Qt.UserRole) if current is not None else None
        labelled = []
        for path in list_playbacks(self.store.compose_playback_dir):
            saved = load_label(path) or {}
            if saved.get("label") in LABEL_TEXT:
                if "events" not in saved:
                    self._add_default_events(path)
                labelled.append((path, saved))
        shown = [(path, saved) for path, saved in labelled if self._matches(saved)]
        self.list.blockSignals(True)
        self.list.clear()
        for path, saved in shown:
            label = saved["label"]
            done = "  [processed]" if is_processed(saved) else ""
            done += "  [to be confirmed]" if to_be_confirmed(saved) else ""
            done += "  [needs manual label]" if needs_manual_label(saved) else ""
            item = QtWidgets.QListWidgetItem(f"[{LABEL_TEXT[label]}] {play_list_text(path)}{done}")
            item.setData(QtCore.Qt.UserRole, path)
            item.setToolTip(path)
            item.setForeground(QtGui.QColor(LABEL_COLORS[label]))
            self.list.addItem(item)
        paths = [path for path, _ in shown]
        self.list.setCurrentRow(paths.index(keep) if keep in paths else -1)
        self.list.blockSignals(False)
        if keep is not None and keep not in paths:
            self._load(None)
        processed = sum(is_processed(saved) for _, saved in labelled)
        confirm = sum(to_be_confirmed(saved) for _, saved in labelled)
        manual = sum(needs_manual_label(saved) for _, saved in labelled)
        self.count_label.setText(
            f"{len(shown)} shown of {len(labelled)} labelled ({processed} processed, "
            f"{confirm} to be confirmed, {manual} need a manual label)"
        )
        self._show_episode_stats(labelled)

    # ---- Episodes and Process failure ---------------------------------------------------

    def _episodes_box(self) -> QtWidgets.QGroupBox:
        """The truncation length, Use longest and the episode statistics."""
        saved = episode_processing.load_truncation(self.store.compose_playback_dir)
        self.truncation_spin = double_spin(
            0.0, 3600.0, 0.5, 2, " s",
            f"How long an episode ('{EPISODE_START_EVENT}' to '{EPISODE_END_EVENT}') may run "
            "before it is truncated; Process failure marks failed recordings at it (saved with "
            f"the recordings in {episode_processing.SETTINGS_NAME})",
        )
        self.truncation_spin.setSpecialValueText("not set")
        self.truncation_spin.setValue(saved or 0.0)
        self.truncation_spin.valueChanged.connect(self._save_truncation)
        self.use_longest_btn = QtWidgets.QPushButton("Use longest")
        self.use_longest_btn.setToolTip(
            "Set the truncation length to the longest processed successful episode"
        )
        self.use_longest_btn.clicked.connect(self._use_longest)
        self.episode_stats_label = QtWidgets.QLabel()
        self.episode_stats_label.setWordWrap(True)
        self._longest: tuple[str, float] | None = None
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Truncation length:"))
        row.addWidget(self.truncation_spin)
        row.addWidget(self.use_longest_btn)
        row.addStretch(1)
        box = QtWidgets.QGroupBox("Episodes")
        layout = QtWidgets.QVBoxLayout(box)
        layout.addLayout(row)
        layout.addWidget(self.episode_stats_label, 1)
        return box

    def _show_episode_stats(self, labelled: list[tuple[str, dict]]) -> None:
        stats = episode_processing.episode_stats(labelled, SUCCESS, FAILURE)
        self._longest = stats.longest
        self.use_longest_btn.setEnabled(stats.longest is not None)
        if stats.longest is None:
            text = "Longest successful episode: none processed yet"
        else:
            path, length = stats.longest
            lengths = [s for _, s in stats.lengths]
            text = (
                f"Longest successful episode: <b>{length:.2f} s</b> "
                f"({os.path.splitext(os.path.basename(path))[0]}) · "
                f"median {np.median(lengths):.2f} s over {len(lengths)} processed successes"
            )
        text += (
            f"<br>Failures with '{EPISODE_END_EVENT}': {stats.failures_done} of "
            f"{stats.failures}"
        )
        self.episode_stats_label.setText(text)

    def _save_truncation(self, value: float) -> None:
        try:
            episode_processing.save_truncation(self.store.compose_playback_dir, value)
        except OSError as e:
            self.node.get_logger().warn(f"Processing: could not save the truncation length: {e}")

    def _use_longest(self) -> None:
        if self._longest is not None:
            self.truncation_spin.setValue(round(self._longest[1], 2))

    # ---- the progress bar of Process click / Process failure / Sparsh-skin transform -------

    def _bar_idle(self) -> None:
        self.process_bar.setRange(0, 1)
        self.process_bar.setValue(0)
        self.process_bar.setFormat("No processing running")

    def _bar_start(self, name: str, total: int, unit: str = "recordings") -> None:
        """A run of ``name`` over ``total`` ``unit`` starts."""
        self._bar_name, self._bar_unit = name, unit
        self.process_bar.setRange(0, max(total, 1))
        self.process_bar.setValue(0)
        self.process_bar.setFormat(f"{name}: %v / %m {unit} (%p %)")

    def _bar_step(self, done: int, total: int) -> None:
        if total > 0 and total != self.process_bar.maximum():
            self.process_bar.setMaximum(total)
        self.process_bar.setValue(min(done, self.process_bar.maximum()))

    def _bar_end(self) -> None:
        """Keeps the bar where it got to, marked finished."""
        self.process_bar.setFormat(f"{self._bar_name} finished: %v / %m {self._bar_unit}")

    def _rewards(self) -> dict[str, float]:
        return {key: spin.value() for key, spin in self.reward_spins.items()}

    def _save_rewards(self) -> None:
        try:
            episode_processing.save_rewards(self.store.compose_playback_dir, self._rewards())
        except OSError as e:
            self.process_status.setText(f"Could not save the rewards: {e}")

    def _process_reward(self) -> None:
        """Sets the rewards of every Sparsh-skin episode (``sparsh_processing.apply_rewards``)."""
        out_dir = os.path.join(
            self.store.compose_playback_dir, sparsh_processing.DEFAULT_OUTPUT_NAME
        )
        names = [n for n in (os.listdir(out_dir) if os.path.isdir(out_dir) else [])
                 if n.startswith(sparsh_processing.EPISODE_PREFIX) and n.endswith(".npz")]
        if not names:
            QtWidgets.QMessageBox.information(
                self, "Process reward",
                f"No episodes in {out_dir}: run the Sparsh-skin transform first (it uses these "
                "rewards too).",
            )
            return
        if self._sparsh_thread is not None and self._sparsh_thread.is_alive():
            QtWidgets.QMessageBox.information(
                self, "Process reward", "Wait for the Sparsh-skin transform to finish."
            )
            return
        rewards = self._rewards()
        answer = QtWidgets.QMessageBox.question(
            self, "Process reward",
            f"Set the rewards of {len(names)} episodes in {out_dir}: {rewards['success']:g} at "
            f"the last timestep of a success, {rewards['fail']:g} at the last timestep of a "
            f"failure, {rewards['step']:g} at every other timestep?",
        )
        if answer != QtWidgets.QMessageBox.Yes:
            return
        self._save_rewards()
        self.process_reward_btn.setEnabled(False)
        self._bar_start("Process reward", len(names), "episodes")

        def step(done: int, total: int) -> None:
            self._bar_step(done, total)
            QtWidgets.QApplication.processEvents()  # runs in the GUI thread: draw the bar

        try:
            counts = sparsh_processing.apply_rewards(out_dir, rewards, step)
        except OSError as e:
            self.process_status.setText(f"Process reward failed: {e}")
        else:
            self.process_status.setText(
                f"Process reward: {counts[SUCCESS]} successes ({rewards['success']:g} at the "
                f"end), {counts[FAILURE]} failures ({rewards['fail']:g} at the end), "
                f"{rewards['step']:g} at every other step"
                + (f" · {counts['failed']} episodes could not be rewritten"
                   if counts["failed"] else "")
            )
        self._bar_end()
        self.process_reward_btn.setEnabled(True)

    def _process_dv3(self) -> None:
        """Converts the Sparsh-skin episodes into DreamerV3 chunks
        (``dv3_processing.write_chunks``)."""
        sparsh_dir = os.path.join(
            self.store.compose_playback_dir, sparsh_processing.DEFAULT_OUTPUT_NAME
        )
        out_dir = os.path.join(self.store.compose_playback_dir, dv3_processing.DEFAULT_OUTPUT_NAME)
        episodes = dv3_processing.episode_files(sparsh_dir)
        if not episodes:
            QtWidgets.QMessageBox.information(
                self, "Process for DreamerV3",
                f"No episodes in {sparsh_dir}: run the Sparsh-skin transform first.",
            )
            return
        if self._sparsh_thread is not None and self._sparsh_thread.is_alive():
            QtWidgets.QMessageBox.information(
                self, "Process for DreamerV3", "Wait for the Sparsh-skin transform to finish."
            )
            return
        answer = QtWidgets.QMessageBox.question(
            self, "Process for DreamerV3",
            f"Convert {len(episodes)} episodes into DreamerV3 chunks in {out_dir}? The chunks "
            "there are replaced.",
        )
        if answer != QtWidgets.QMessageBox.Yes:
            return
        self.dv3_btn.setEnabled(False)
        self._bar_start("Process for DreamerV3", len(episodes), "episodes")

        def step(done: int, total: int) -> None:
            self._bar_step(done, total)
            QtWidgets.QApplication.processEvents()  # runs in the GUI thread: draw the bar

        try:
            manifest = dv3_processing.write_chunks(sparsh_dir, out_dir, step)
        except OSError as e:
            self.process_status.setText(f"Process for DreamerV3 failed: {e}")
        else:
            short = manifest[f"shorter_than_{dv3_processing.BATCH_LENGTH}"]
            low, high = manifest["reward_range"] or (0.0, 0.0)
            self.process_status.setText(
                f"Process for DreamerV3: {len(manifest['written'])} chunks in {out_dir} · "
                f"reward {low:g} to {high:g}"
                + (" (all 0: set the rewards with Process reward)" if low == high == 0 else "")
                + (f" · {len(manifest['skipped'])} failed (see its manifest.json)"
                   if manifest["skipped"] else "")
                + (f" · {len(short)} shorter than {dv3_processing.BATCH_LENGTH} steps (no "
                   "training window)" if short else "")
                + f" · copy them with: cp {out_dir}/*.npz LEQ_DV3/data/leap/<task>/"
            )
        self._bar_end()
        self.dv3_btn.setEnabled(True)

    def _process_failure(self) -> None:
        """Marks ``terminal`` and ``truncated`` at the truncation length on the failed
        recordings (``episode_processing.truncate_failure``)."""
        length = self.truncation_spin.value()
        if length <= 0.0:
            QtWidgets.QMessageBox.information(
                self, "Process failure", "Set the truncation length first (e.g. Use longest)."
            )
            return
        targets = []
        for path in list_playbacks(self.store.compose_playback_dir):
            label = load_label(path) or {}
            if (label.get("label") == FAILURE
                    and episode_processing.failure_target(label, length)):
                targets.append(path)
        if not targets:
            QtWidgets.QMessageBox.information(
                self, "Process failure",
                f"Every failed recording has a '{EPISODE_END_EVENT}' event already.",
            )
            return
        answer = QtWidgets.QMessageBox.question(
            self, "Process failure",
            f"Mark '{EPISODE_END_EVENT}' and '{episode_processing.TRUNCATED}' at "
            f"'{EPISODE_START_EVENT}' + {length:.2f} s on {len(targets)} failed recordings? "
            f"Those that end earlier get '{EPISODE_END_EVENT}' and "
            f"'{episode_processing.FAIL}' at their last timestep.",
        )
        if answer != QtWidgets.QMessageBox.Yes:
            return
        types = {
            name: self.event_defs.get(name, {}).get("type", "")
            for name in episode_processing.FAILURE_END_EVENTS
        }
        outcomes = {"truncated": 0, "ended": 0, "no start": 0, "failed": 0}
        self._bar_start("Process failure", len(targets))
        for i, path in enumerate(targets, start=1):
            try:
                outcomes[episode_processing.truncate_failure(path, length, types)] += 1
            except Exception as e:  # noqa: BLE001 - one bad recording does not stop it
                outcomes["failed"] += 1
                self.node.get_logger().warn(f"Process failure: {path}: {e}")
            self._bar_step(i, len(targets))
            QtWidgets.QApplication.processEvents()  # runs in the GUI thread: draw the bar
        self._bar_end()
        self.process_status.setText(
            f"Process failure: {len(targets)} failed recordings · {outcomes['truncated']} "
            f"truncated at {length:.2f} s · {outcomes['ended']} end before it: "
            f"'{EPISODE_END_EVENT}' and '{episode_processing.FAIL}' at their last timestep"
            + (f", {outcomes['no start']} have no '{EPISODE_START_EVENT}'"
               if outcomes["no start"] else "")
            + (f", {outcomes['failed']} failed (see the log)" if outcomes["failed"] else "")
        )
        self.refresh_recordings()
        if self.rec is not None and self._pending is None:  # shows the events it added
            self.events = [
                TakeEvent(**e) for e in (load_label(self.rec.path) or {}).get("events", [])
            ]
            self._refresh_events()

    # ---- Process click ------------------------------------------------------------------

    def _process_click(self) -> None:
        """Starts Process click in the background, or asks the running one to stop."""
        if self._click_thread is not None and self._click_thread.is_alive():
            self._click_stop.set()
            self.process_click_btn.setEnabled(False)
            self.process_status.setText("Process click: stopping after this recording...")
            return
        paths = list_playbacks(self.store.compose_playback_dir)
        marks = click_processing.marked_clicks(paths)
        if not marks:
            QtWidgets.QMessageBox.information(
                self, "Process click",
                f"Mark the click with a '{CLICK_EVENT}' event on some successful recordings "
                "first: they are the click detector's templates.",
            )
            return
        if not self.node.click_detect_ready():
            QtWidgets.QMessageBox.warning(
                self, "Process click",
                f"The click detector's service '{self.node.click_detect_service}' is not "
                "available: start click_detector (push_button_pen_click_detection "
                "launch_click_detector.py).",
            )
            return
        targets = click_processing.to_process(paths, SUCCESS)
        if not targets:
            QtWidgets.QMessageBox.information(
                self, "Process click",
                f"Every successful recording has a '{CLICK_EVENT}' event or was searched "
                "already.",
            )
            return
        types = {
            name: self.event_defs.get(name, {}).get("type", "")
            for name in (CLICK_EVENT, *CLICK_END_EVENTS)
        }
        self._click_stop.clear()
        self.process_click_btn.setText("Stop")
        self.process_status.setText(
            f"Process click: {min(len(marks), click_processing.MAX_SAMPLES)} of {len(marks)} "
            f"marked clicks as samples, searching {len(targets)} recordings..."
        )
        self._bar_start("Process click", len(targets))
        self._click_thread = threading.Thread(
            target=self._run_process_click, args=(marks, targets, types), daemon=True
        )
        self._click_thread.start()

    def _run_process_click(
        self, marks: list[tuple[str, float, float]], targets: list[str], types: dict
    ) -> None:
        """Process click's thread: reports through ``click_progress`` / ``click_done``."""
        sr = click_processing.SAMPLE_RATE
        found = failed = searched = 0
        spent = 0.0  # s spent searching
        used = click_processing.pick_marks(marks)
        detector = {
            "service": self.node.click_detect_service, "pair": False,
            "marked_clicks": len(marks),
        }
        try:
            samples = click_processing.click_samples(used, sr)
            if not samples:
                raise RuntimeError("the marked clicks have no audio")
            duration = click_processing.marked_duration(marks)
            used_text = f"{len(samples)} of {len(marks)} marked clicks as samples"
            for i, path in enumerate(targets, start=1):
                if self._click_stop.is_set():
                    break
                tic = time.monotonic()
                try:
                    result = click_processing.process_recording(
                        path, samples, sr, self.node.detect_clicks, duration, types,
                        detector,
                    )
                    found += result["found"]
                except Exception as e:  # noqa: BLE001 - one bad recording does not stop it
                    failed += 1
                    self.node.get_logger().warn(f"Process click: {path}: {e}")
                last = time.monotonic() - tic
                spent, searched = spent + last, i
                self._click_signals.step.emit(i, len(targets))
                left = spent / i * (len(targets) - i)
                self._click_signals.progress.emit(
                    f"Process click: {i} / {len(targets)} searched, {found} clicks found"
                    + (f", {failed} failed" if failed else "")
                    + f" · {used_text} · {spent / i:.1f} s per recording (last {last:.1f} s), "
                    f"~{left / 60:.0f} min left"
                )
        except Exception as e:  # noqa: BLE001
            self._click_signals.done.emit(f"Process click failed: {e}")
            return
        stopped = " (stopped)" if self._click_stop.is_set() else ""
        average = f"{spent / searched:.1f} s per recording" if searched else "nothing searched"
        self._click_signals.done.emit(
            f"Process click{stopped}: {found} clicks found to be confirmed"
            + (f", {failed} recordings failed (see the log)" if failed else "")
            + f" · {used_text} · {average}"
        )

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        self._refresh_sparsh_baselines()

    def _refresh_sparsh_baselines(self) -> None:
        """Lists the Baseline tab's recordings in the dropdown, the one used picked and tagged."""
        paths = list_baselines(self.store.demo_dir)
        used = sparsh_baseline(self.store.demo_dir)
        combo = self.sparsh_baseline_combo
        combo.clear()
        if not paths:
            combo.addItem("No baseline: record one on the Baseline tab", None)
            return
        for path in paths:
            text = baseline_list_text(path)
            combo.addItem(f"{SPARSH_BASELINE_TAG} {text}" if path == used else text, path)
            combo.setItemData(combo.count() - 1, path, QtCore.Qt.ToolTipRole)
        combo.setCurrentIndex(paths.index(used))

    def _sparsh_baseline_picked(self, index: int) -> None:
        path = self.sparsh_baseline_combo.itemData(index)
        if path:
            set_sparsh_baseline(path)
            self._refresh_sparsh_baselines()

    def _sparsh_transform(self) -> None:
        """Starts the Sparsh-skin transform of the episodes in the background, with the
        dropdown's baseline."""
        if self._sparsh_thread is not None and self._sparsh_thread.is_alive():
            return
        self._refresh_sparsh_baselines()
        baseline = self.sparsh_baseline_combo.currentData()
        if not baseline:
            QtWidgets.QMessageBox.warning(
                self, "Sparsh-skin transform",
                "No baseline recording: record one on the Baseline tab (the hand in the open "
                "pose, nothing touching the skin).",
            )
            return
        if not self.node.sparsh_transform_ready():
            QtWidgets.QMessageBox.warning(
                self, "Sparsh-skin transform",
                f"The service '{self.node.sparsh_transform_service}' is not available: start "
                "sparsh_skin_transformation (mechanical_pen_data_collection).",
            )
            return
        directory = self.store.compose_playback_dir
        paths, skipped = sparsh_processing.eligible_episodes(directory)
        if not paths:
            QtWidgets.QMessageBox.information(
                self, "Sparsh-skin transform",
                "No recording has an episode ('episode_start' and 'terminal', labelled success "
                "or failure).",
            )
            return
        out_dir = os.path.join(directory, sparsh_processing.DEFAULT_OUTPUT_NAME)
        answer = QtWidgets.QMessageBox.question(
            self, "Sparsh-skin transform",
            f"Preprocess {len(paths)} episodes into {out_dir} with the baseline "
            f"{os.path.basename(baseline)} ({baseline_list_text(baseline)})? ({len(skipped)} "
            "recordings have no episode; episodes already there with this baseline are kept.)",
        )
        if answer != QtWidgets.QMessageBox.Yes:
            return
        self.sparsh_transform_btn.setEnabled(False)
        self._bar_start("Sparsh-skin transform", len(paths), "episodes")
        self.node.on_sparsh_progress = self._on_sparsh_progress
        self.process_status.setText(
            f"Sparsh-skin transform: {len(paths)} episodes (progress in the "
            "sparsh_skin_transformation log)..."
        )

        def run() -> None:
            try:
                response = self.node.sparsh_transform(directory, baseline)
                text = f"Sparsh-skin transform: {response.message}"
            except Exception as e:  # noqa: BLE001
                text = f"Sparsh-skin transform failed: {e}"
            self._sparsh_signals.done.emit(text)

        self._sparsh_thread = threading.Thread(target=run, daemon=True)
        self._sparsh_thread.start()

    def _on_sparsh_progress(self, done: int, total: int, text: str) -> None:
        """sparsh_skin_transformation's progress (executor thread)."""
        self._sparsh_signals.step.emit(done, total)
        if done:
            self._sparsh_signals.progress.emit(f"Sparsh-skin transform: {text}")

    def _sparsh_transform_done(self, text: str) -> None:
        self.node.on_sparsh_progress = None
        self._bar_end()
        self.process_status.setText(text)
        self.sparsh_transform_btn.setEnabled(True)

    def _process_click_done(self, text: str) -> None:
        self.process_status.setText(text)
        self._bar_end()
        self.process_click_btn.setText("Process click")
        self.process_click_btn.setEnabled(True)
        self.refresh_recordings()
        if self.rec is not None and self._pending is None:  # shows the events it added
            self.events = [
                TakeEvent(**e) for e in (load_label(self.rec.path) or {}).get("events", [])
            ]
            self._refresh_events()

    def close_video(self) -> None:
        self._click_stop.set()
        super().close_video()


# Analysis tab: box colours by success rate (RGB), from fail to success; grey with no labels.
ANALYSIS_FAIL_RGB = np.array([229, 57, 53], dtype=float)
ANALYSIS_SUCCESS_RGB = np.array([67, 160, 71], dtype=float)
ANALYSIS_NONE_RGB = (176, 176, 176)
ANALYSIS_SELECTED_RGB = (255, 235, 59)


def rate_color(rate: float | None) -> tuple[int, int, int]:
    if rate is None:
        return ANALYSIS_NONE_RGB
    rgb = ANALYSIS_FAIL_RGB + rate * (ANALYSIS_SUCCESS_RGB - ANALYSIS_FAIL_RGB)
    return tuple(int(v) for v in rgb)


def rate_text(counts: RecordingCounts) -> str:
    rate = counts.success_rate
    return "-" if rate is None else f"{100.0 * rate:.0f} %"


@dataclass
class BoxStats:
    """A pen box on the Analysis tab: its corners, takes and Play on hand recordings."""

    name: str
    corners: np.ndarray | None
    takes: dict[str, list[str]] = field(default_factory=dict)  # finger -> its takes' names
    first_take: FingerTake | None = None  # for a camera frame when there is no live one
    recordings: RecordingCounts = field(default_factory=RecordingCounts)
    by_combination: dict[frozenset, RecordingCounts] = field(default_factory=dict)


class AnalysisTab(QtWidgets.QWidget):
    """Coverage and results of the pen boxes: every box drawn on the live camera (coloured by
    success rate), a table of the boxes with their Play on hand recordings and labels, and for
    the box picked, its totals and a breakdown by the combination of takes recorded."""

    def __init__(self, node: LeapStateListener, store: TakeStore) -> None:
        super().__init__()
        self.node = node
        self.store = store
        self._boxes: list[BoxStats] = []
        self._selected: str | None = None
        self._frame_seq = -1
        self._frame_key = None  # what the camera view shows (frame, selection), to redraw
        self._video = TakeVideo()
        self._fallback: dict[str, np.ndarray | None] = {}  # box -> first frame of its take
        # Boxes not drawn on the camera (their Hide button), remembered between runs.
        self._settings = QtCore.QSettings(PACKAGE_NAME, "record_demonstration")
        try:
            self._hidden = set(json.loads(self._settings.value("analysis_hidden_boxes", "[]")))
        except (TypeError, ValueError):
            self._hidden = set()

        self.camera = CameraView(node.image_topic)
        self.camera_note = QtWidgets.QLabel()
        self.camera_note.setWordWrap(True)
        legend = QtWidgets.QLabel(
            "Box colour: success rate of its labelled recordings, "
            f"<span style='color:rgb{tuple(int(v) for v in ANALYSIS_FAIL_RGB)}'><b>0 %</b></span>"
            f" to <span style='color:rgb{tuple(int(v) for v in ANALYSIS_SUCCESS_RGB)}'>"
            f"<b>100 %</b></span>, <span style='color:rgb{ANALYSIS_NONE_RGB}'><b>grey</b></span>"
            " none labelled; the box picked is thicker, outlined in yellow"
        )
        legend.setWordWrap(True)
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.camera, 1)
        left_layout.addWidget(self.camera_note)
        left_layout.addWidget(legend)

        self.overall = QtWidgets.QLabel()
        self.overall.setWordWrap(True)
        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.setToolTip("Read the takes, recordings and labels again")
        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.overall, 1)
        top.addWidget(refresh_btn)
        self.box_table = self._table(
            ["Box", "Centre (px)", "Takes", "Demonstrations", "Success", "Fail",
             "Not labelled", "Success rate", "Clicked", "No click", "Kept sliding",
             "No contact", "Other press", "Hide"]
        )
        self.box_table.setToolTip(
            "Pen boxes of the edited takes (each named after the take it belongs to, with the "
            "takes that have it: the box their Pose switch shows); a Play on hand recording "
            "counts for the box its takes have now. Pick one to see its combinations"
        )
        self.box_title = QtWidgets.QLabel("<i>Pick a box</i>")
        self.box_title.setWordWrap(True)
        self.combo_table = self._table(
            ["Combination", "Demonstrations", "Success", "Fail", "Not labelled",
             "Success rate", "Modified", "Clicked", "No click", "Kept sliding", "No contact",
             "Other press"]
        )
        self.combo_table.setToolTip(
            "Play on hand recordings of the box by the takes they played (labels from the "
            "Demonstration tab's Success / Fail, or label_playbacks)"
        )
        right = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        boxes_panel = QtWidgets.QWidget()
        boxes_layout = QtWidgets.QVBoxLayout(boxes_panel)
        boxes_layout.setContentsMargins(0, 0, 0, 0)
        boxes_layout.addLayout(top)
        boxes_layout.addWidget(self.box_table, 1)
        detail_panel = QtWidgets.QWidget()
        detail_layout = QtWidgets.QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.addWidget(self.box_title)
        detail_layout.addWidget(self.combo_table, 1)
        right.addWidget(boxes_panel)
        right.addWidget(detail_panel)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([800, 700])
        QtWidgets.QVBoxLayout(self).addWidget(split)

        refresh_btn.clicked.connect(self.refresh_data)
        self.box_table.itemSelectionChanged.connect(self._on_box)

    @staticmethod
    def _table(headers: list[str]) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        self.refresh_data()

    # ---- data ---------------------------------------------------------------------------

    def refresh_data(self) -> None:
        """Reads the boxes of the edited takes and the Play on hand recordings (by the box
        they were recorded with) and their labels again."""
        grouped = group_takes_by_box(self.store)
        boxes: dict[str, BoxStats] = {}
        box_of_take: dict[tuple[str, str], str] = {}  # (finger, take name) -> its box now
        for key, by_finger in grouped.groups.items():
            name = grouped.names[key]
            first = next((takes[0] for takes in by_finger.values() if takes), None)
            boxes[name] = BoxStats(
                name, grouped.corners[key],
                {finger: sorted(t.name for t in takes)
                 for finger, takes in by_finger.items() if takes}, first,
            )
            for finger, takes in by_finger.items():
                for take in takes:
                    box_of_take[(finger, take.name)] = name
        order = {finger: i for i, (finger, _) in enumerate(FINGERS)}
        plays = None  # the Thumb plays, read when a recording has no press label yet
        for path in list_playbacks(self.store.compose_playback_dir):
            info = recording_info(path)
            if info is None:
                continue
            if not (load_label(path) or {}).get("click_press"):
                plays = plays or ThumbPlays(self.store.demo_dir)
                click_press_label(path, plays)
            # The box its takes have now (the Thumb's first), as the Pose switches show it;
            # the box saved with the recording only when none of its takes is left.
            played = sorted(info["takes"], key=lambda fn: order.get(fn[0], 9))
            name = next((box_of_take[ft] for ft in played if ft in box_of_take), None)
            if name is None:
                name = (info["box"] or os.path.splitext(os.path.basename(path))[0]
                        .rsplit("_", 1)[0]) + " (takes gone)"
            box = boxes.get(name)
            if box is None:  # its takes are gone: the box from the recording
                box = boxes[name] = BoxStats(name, info["corners"])
            box.recordings.add(path, info["modified"])
            box.by_combination.setdefault(info["takes"], RecordingCounts()).add(
                path, info["modified"]
            )
        self._boxes = sorted(boxes.values(), key=lambda b: b.name)
        self._fill_boxes()
        self._frame_key = None

    def _fill_boxes(self) -> None:
        keep = self._selected
        total = RecordingCounts()
        for box in self._boxes:
            total.merge(box.recordings)
        self.overall.setText(
            f"<b>{len(self._boxes)}</b> bounding box(es); <b>{total.total}</b> demonstrations: "
            f"<span style='color:{COMBO_VALID_COLOR}'><b>{total.success} success</b></span>, "
            f"<span style='color:{COMBO_COLLIDE_COLOR}'><b>{total.failure} fail</b></span>, "
            f"{total.unlabelled} not labelled (success rate {rate_text(total)})"
            f"<br>click press: {press_text(total)}"
        )
        table = self.box_table
        table.blockSignals(True)
        table.setRowCount(len(self._boxes))
        row_keep = -1
        for row, box in enumerate(self._boxes):
            rec = box.recordings
            centre = ("-" if box.corners is None
                      else "({:.0f}, {:.0f})".format(*np.asarray(box.corners).mean(axis=0)))
            takes = "; ".join(
                f"{f.upper()} {', '.join(names)}" for f, names in box.takes.items()
            ) or "none (deleted or changed box)"
            values = [box.name, centre, takes, rec.total, rec.success, rec.failure,
                      rec.unlabelled, rate_text(rec)]
            values += [rec.press[k] for k in PRESS_COLUMNS] + [rec.press_other()]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.DisplayRole, value)
                if col == 0:
                    item.setForeground(QtGui.QColor(*rate_color(rec.success_rate)))
                    item.setData(QtCore.Qt.UserRole, box.name)
                table.setItem(row, col, item)
            table.setCellWidget(row, len(values), self._hide_button(box.name))
            if box.name == keep:
                row_keep = row
        table.blockSignals(False)
        if row_keep < 0 and self._boxes:
            row_keep = 0
        if row_keep >= 0:
            table.selectRow(row_keep)
        self._on_box()

    def _hide_button(self, name: str) -> QtWidgets.QWidget:
        """Hide radio button of box ``name`` (centred in its cell); on, the box is not drawn."""
        button = QtWidgets.QRadioButton()
        button.setAutoExclusive(False)  # each box on its own; clicking again shows it
        button.setChecked(name in self._hidden)
        button.setToolTip(f"Hide box {name} on the camera view (it stays in the counts)")
        button.toggled.connect(lambda on, n=name: self._set_hidden(n, on))
        cell = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(button)
        return cell

    def _set_hidden(self, name: str, hidden: bool) -> None:
        if hidden:
            self._hidden.add(name)
        else:
            self._hidden.discard(name)
        self._settings.setValue("analysis_hidden_boxes", json.dumps(sorted(self._hidden)))
        self._frame_key = None  # redraw

    def _picked(self) -> BoxStats | None:
        return next((b for b in self._boxes if b.name == self._selected), None)

    def _on_box(self) -> None:
        rows = self.box_table.selectionModel().selectedRows()
        self._selected = (
            self.box_table.item(rows[0].row(), 0).data(QtCore.Qt.UserRole) if rows else None
        )
        self._frame_key = None
        box = self._picked()
        table = self.combo_table
        if box is None:
            self.box_title.setText("<i>Pick a box</i>")
            table.setRowCount(0)
            return
        rec = box.recordings
        self.box_title.setText(
            f"<b>{box.name}</b>: <b>{rec.total}</b> demonstrations, "
            f"<span style='color:{COMBO_VALID_COLOR}'><b>{rec.success} success</b></span>, "
            f"<span style='color:{COMBO_COLLIDE_COLOR}'><b>{rec.failure} fail</b></span>, "
            f"{rec.unlabelled} not labelled (success rate {rate_text(rec)})"
            + (f"; {rec.modified} modified" if rec.modified else "")
            + (f"<br>click press: {press_text(rec)}" if rec.total else
               " - nothing recorded with this box yet")
        )
        combos = sorted(box.by_combination.items(), key=lambda kv: (-kv[1].total, takes_name(kv[0])))
        table.setRowCount(len(combos))
        for row, (key, counts) in enumerate(combos):
            missing = [n for f, n in key if not os.path.exists(self.store.take_path(f, n))]
            name = takes_name(key) + (f"  (deleted: {', '.join(missing)})" if missing else "")
            values = [name, counts.total, counts.success, counts.failure, counts.unlabelled,
                      rate_text(counts), counts.modified or ""]
            values += [counts.press[k] for k in PRESS_COLUMNS] + [counts.press_other()]
            for col, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.DisplayRole, value)
                if col == 5:
                    item.setForeground(QtGui.QColor(*rate_color(counts.success_rate)))
                table.setItem(row, col, item)

    # ---- camera ---------------------------------------------------------------------------

    def refresh(self) -> None:
        """The camera with every box drawn on it (while the tab is shown): the live feed, or
        the first frame of the picked box's take when there is no live one."""
        if not self.isVisible():
            return
        seq, frame = self.node.latest_raw_frame()
        if frame is not None:
            key = ("live", seq, self._selected)
            note = "Live camera with every pen bounding box"
        else:
            frame = self._fallback_frame()
            key = ("take", self._selected)
            note = ("No live camera: the first camera frame of the picked box's take, with every "
                    "pen bounding box")
        if key == self._frame_key:
            return
        self._frame_key = key
        if frame is None:
            self.camera.set_message("No live camera and no recorded frame for this box")
            return
        self.camera.set_frame(self._draw_boxes(frame))
        hidden = sum(b.name in self._hidden for b in self._boxes)
        self.camera_note.setText(
            f"{note} ({len(self._boxes) - hidden} shown" + (f", {hidden} hidden)" if hidden else ")")
        )

    def _fallback_frame(self) -> np.ndarray | None:
        box = self._picked()
        if box is None or box.first_take is None:  # e.g. its takes are deleted: any box's
            box = next((b for b in self._boxes if b.first_take), None)
        if box is None:
            return None
        if box.name not in self._fallback:
            self._fallback[box.name] = take_first_frame(box.first_take, self._video)
        return self._fallback[box.name]

    def _draw_boxes(self, frame: np.ndarray) -> np.ndarray:
        """Every box on a copy of ``frame`` (RGB), coloured by success rate, the picked one
        last, thicker and outlined, with a light fill."""
        vis = np.ascontiguousarray(frame.copy())
        boxes = [b for b in self._boxes if b.corners is not None and b.name not in self._hidden]
        boxes.sort(key=lambda b: b.name == self._selected)  # the picked one on top
        for box in boxes:
            pts = np.round(np.asarray(box.corners, dtype=np.float32)).astype(np.int32)
            color = rate_color(box.recordings.success_rate)
            picked = box.name == self._selected
            if picked:
                fill = vis.copy()
                cv2.fillPoly(fill, [pts], color)
                vis = cv2.addWeighted(fill, 0.25, vis, 0.75, 0)
                cv2.polylines(vis, [pts], True, ANALYSIS_SELECTED_RGB, 5)
            cv2.polylines(vis, [pts], True, color, 3 if picked else 2)
            rec = box.recordings
            label = f"{box.name} {rec.success}/{rec.success + rec.failure}" if rec.total else box.name
            x, y = int(pts[:, 0].min()), max(int(pts[:, 1].min()) - 8, 16)
            cv2.putText(vis, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4,
                        cv2.LINE_AA)
            cv2.putText(vis, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        ANALYSIS_SELECTED_RGB if picked else color, 2, cv2.LINE_AA)
        return vis

    def close_video(self) -> None:
        self._video.release()


def backup_extras(events_file: str) -> list[tuple[str, str]]:
    """(local file or folder, name under the backup's ``_app``) of what the app needs besides
    the recordings folder: Settings tab values and avoid slip presets, the event definitions
    it loaded, the click detector's templates and this GUI's Qt preferences (audio output,
    Analysis tab boxes)."""
    return [
        (os.path.dirname(settings_file()), "settings"),
        (os.path.realpath(events_file), "events"),
        (audio_utils.DEFAULT_TEMPLATE_DIR, "pen_click_templates"),
        (QtCore.QSettings(PACKAGE_NAME, "record_demonstration").fileName(), "qt_settings"),
    ]


def source_events_file() -> str | None:
    """events.json in this package's source (found from its colcon build folder), or None."""
    try:
        ws = os.path.dirname(default_bag_dir())
        with open(os.path.join(ws, "build", PACKAGE_NAME, "CMakeCache.txt")) as f:
            for line in f:
                if line.startswith(f"{PACKAGE_NAME}_SOURCE_DIR:"):
                    path = os.path.join(line.split("=", 1)[1].strip(), PACKAGE_NAME, "events.json")
                    return path if os.path.isdir(os.path.dirname(path)) else None
    except Exception:  # noqa: BLE001 - not built with colcon here
        pass
    return None


def pull_targets(local_dir: str, events_file: str) -> list[nextcloud_backup.PullTarget]:
    """Where Pull puts each part of the backup by default (as ``backup_extras`` sent them):
    the recordings into ``local_dir``, events.json into the source (kept by the next build)
    and the installed copy the app reads."""
    app = nextcloud_backup.APP_DIR
    T = nextcloud_backup.PullTarget
    targets = [
        T("Recordings", "", local_dir),
        T("Settings (Settings tab, avoid slip presets)", f"{app}/settings",
          os.path.dirname(settings_file())),
    ]
    source = source_events_file()
    if source is not None:
        targets.append(T("Event definitions (source)", f"{app}/events", source, is_file=True))
    targets += [
        T("Event definitions (installed, read by the app)", f"{app}/events",
          os.path.realpath(events_file), is_file=True),
        T("Click detector templates", f"{app}/pen_click_templates",
          audio_utils.DEFAULT_TEMPLATE_DIR),
        T("Qt preferences (audio output, Analysis boxes)", f"{app}/qt_settings",
          QtCore.QSettings(PACKAGE_NAME, "record_demonstration").fileName(), is_file=True),
    ]
    return targets


class PullDialog(QtWidgets.QDialog):
    """Where Pull downloads each part of the backup: a row per ``PullTarget`` with its
    destination (editable, Browse), what it would do there and a box to leave it out."""

    def __init__(
        self, parent: QtWidgets.QWidget, remote: dict[str, tuple[int, float]],
        targets: list[nextcloud_backup.PullTarget], where: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pull from Nextcloud")
        self.resize(1100, 420)
        self._remote = remote
        self._targets = targets
        self._rows: list[tuple[QtWidgets.QCheckBox, QtWidgets.QLineEdit, QtWidgets.QLabel]] = []
        grid = QtWidgets.QGridLayout()
        for col, text in enumerate(("Part of the backup", "Downloaded to", "", "What it does")):
            grid.addWidget(QtWidgets.QLabel(f"<b>{text}</b>"), 0, col)
        for i, target in enumerate(targets, start=1):
            check = QtWidgets.QCheckBox(target.label)
            check.setChecked(True)
            edit = QtWidgets.QLineEdit(target.dest)
            edit.setMinimumWidth(480)
            edit.setToolTip("A file" if target.is_file else "A folder (created if missing)")
            browse = QtWidgets.QPushButton("Browse...")
            info = QtWidgets.QLabel()
            browse.clicked.connect(lambda _, t=target, e=edit: self._browse(t, e))
            edit.editingFinished.connect(self._update)
            check.toggled.connect(self._update)
            grid.addWidget(check, i, 0)
            grid.addWidget(edit, i, 1)
            grid.addWidget(browse, i, 2)
            grid.addWidget(info, i, 3)
            self._rows.append((check, edit, info))
        grid.setColumnStretch(1, 1)
        self.overwrite_check = QtWidgets.QCheckBox(
            "Also overwrite local files that are newer than the backup's"
        )
        self.overwrite_check.toggled.connect(self._update)
        self.summary = QtWidgets.QLabel()
        self.summary.setWordWrap(True)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.pull_btn = buttons.button(QtWidgets.QDialogButtonBox.Ok)
        self.pull_btn.setText("Pull")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(
            f"Check where each part of the backup in {where} goes, then Pull. Files the same "
            "locally are skipped. Restart the app afterwards to load restored settings."
        ))
        layout.addLayout(grid)
        layout.addStretch(1)
        layout.addWidget(self.overwrite_check)
        layout.addWidget(self.summary)
        layout.addWidget(buttons)
        self._update()

    def _browse(self, target: nextcloud_backup.PullTarget, edit: QtWidgets.QLineEdit) -> None:
        if target.is_file:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, target.label, edit.text(), options=QtWidgets.QFileDialog.DontConfirmOverwrite
            )
        else:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, target.label, edit.text())
        if path:
            edit.setText(path)
            self._update()

    def targets(self) -> list[nextcloud_backup.PullTarget]:
        """The ticked parts with their (edited) destinations."""
        return [
            replace(t, dest=edit.text().strip())
            for t, (check, edit, _) in zip(self._targets, self._rows)
            if check.isChecked() and edit.text().strip()
        ]

    def plan(self) -> list[nextcloud_backup.PullFile]:
        return nextcloud_backup.plan_pull(self._remote, self.targets(), BACKUP_REDACT)

    def _update(self) -> None:
        overwrite = self.overwrite_check.isChecked()
        get = {"new", "changed", "local newer"} if overwrite else {"new", "changed"}
        n = size = 0
        for target, (check, edit, info) in zip(self._targets, self._rows):
            edit.setToolTip(edit.text())
            files = nextcloud_backup.plan_pull(
                self._remote, [replace(target, dest=edit.text())], BACKUP_REDACT
            )
            if not files:
                info.setText("<span style='color:#757575'>not in the backup</span>")
                continue
            count = {state: sum(f.state == state for f in files)
                     for state in ("new", "changed", "local newer", "same")}
            mb = sum(f.size for f in files if f.state in get) / 1e6
            info.setText(
                f"{len(files)} files: {count['new']} new, {count['changed']} changed, "
                f"{count['local newer']} newer locally"
                + (" (overwritten)" if overwrite else " (kept)")
                + f", {count['same']} the same · {mb:.1f} MB to download"
            )
            if check.isChecked():
                n += sum(f.state in get for f in files)
                size += sum(f.size for f in files if f.state in get)
        self.summary.setText(f"<b>{n} files ({size / 1e6:.1f} MB) will be downloaded.</b>")
        self.pull_btn.setEnabled(n > 0)


def without_backup_password(content: bytes) -> bytes:
    """The settings file as backed up: without the Nextcloud app password."""
    data = json.loads(content)
    if isinstance(data, dict) and isinstance(data.get("nextcloud"), dict):
        data["nextcloud"].pop("password", None)
    return json.dumps(data, indent=2).encode()


# Files Sync uploads changed (and Pull compares as uploaded): the settings, without the password.
BACKUP_REDACT = {settings_file(): without_backup_password}


class BackupSignals(QtCore.QObject):
    """Backup to Nextcloud's thread to the Settings tab: (bytes done, bytes to send, files
    done, files to send, current file), then the summary (and whether it went wrong)."""

    progress = QtCore.pyqtSignal(object)
    done = QtCore.pyqtSignal(str, bool)


BASELINE_POSE = "open"  # the pose the baseline is recorded in: 0 on every sim joint (flat hand)
BASELINE_RECORD_S = 10.0  # s of Xela readings Record takes
BASELINE_COLLECT_MS = 200  # how often a recording takes the new Xela readings
BASELINE_SETTLE_S = 1.0  # s Record waits at the pose before recording (fingers settle)
BASELINE_POSE_TOLERANCE = 0.05  # rad: further from the pose and the recording is flagged
BASELINE_TABLE_MS = 200  # how often the taxel table is redrawn
BASELINE_COLUMNS = ["Taxel", "x", "y", "z", "Temp", "Rec x", "Rec y", "Rec z", "Rec temp"]


SPARSH_BASELINE_KEY = "sparsh_baseline"  # QSettings: the baseline the Sparsh-skin transform uses
SPARSH_BASELINE_TAG = "[Sparsh-skin]"  # next to it in the baseline lists


def baseline_dir(demo_dir: str) -> str:
    return os.path.join(demo_dir, "baselines")


def list_baselines(demo_dir: str) -> list[str]:
    """The Baseline tab's recordings, newest first."""
    directory = baseline_dir(demo_dir)
    names = os.listdir(directory) if os.path.isdir(directory) else []
    return sorted(
        (os.path.join(directory, n) for n in names
         if n.startswith("baseline_") and n.endswith(".npz")),
        reverse=True,
    )


def sparsh_baseline(demo_dir: str) -> str | None:
    """The baseline the Sparsh-skin transform uses: the one picked (Processing tab dropdown or
    the Baseline tab's Use for Sparsh-skin), or the newest while none is (None: there is none)."""
    paths = list_baselines(demo_dir)
    picked = QtCore.QSettings(PACKAGE_NAME, "record_demonstration").value(SPARSH_BASELINE_KEY, "")
    return picked if picked in paths else (paths[0] if paths else None)


def set_sparsh_baseline(path: str) -> None:
    QtCore.QSettings(PACKAGE_NAME, "record_demonstration").setValue(SPARSH_BASELINE_KEY, path)


def baseline_list_text(path: str) -> str:
    """A baseline recording's list entry: its date and time (``meta``, or the file name of a
    recording without one), length, readings and distance from the pose."""
    stamp = os.path.basename(path)[len("baseline_"):-len(".npz")]
    try:
        when = datetime.strptime(stamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        when = stamp
    try:
        with np.load(path) as data:
            t = data["t"]
            error = float(data["pose_error"]) if "pose_error" in data.files else np.nan
            meta = baseline_meta(data)
    except Exception:
        return f"{when} \u00b7 unreadable"
    if "date" in meta:
        when = f"{meta['date']} {meta['time']}"
    text = f"{when} \u00b7 {t[-1] if len(t) else 0.0:.1f} s \u00b7 {len(t)} readings"
    if np.isfinite(error) and error > BASELINE_POSE_TOLERANCE:
        text += f" \u00b7 \u26a0 {error:.2f} rad"
    return text


def baseline_meta(data) -> dict:
    """The ``meta`` of a loaded baseline recording ({} for one saved before it had one)."""
    return json.loads(str(data["meta"])) if "meta" in data.files else {}


class BaselineStateView(QtWidgets.QWidget):
    """Where the Baseline tab's Record is, as the Compose tab's ``ClickPressStateView``
    shows the click press: a row of stages (the current one highlighted, those passed pale
    green), how it ended and its live status."""

    # (key, label, tooltip)
    STAGES = (
        ("planning", "Plan path", "hand_ik (mink) plans a path to the pose that keeps the "
         "fingers apart"),
        ("moving", f"Move to {BASELINE_POSE} pose",
         "The path is played on the hand, every joint on the stiff gains"),
        ("settling", "Settle", f"Held at the pose {BASELINE_SETTLE_S:g} s so the fingers and "
         "the skin settle"),
        ("recording", "Record", f"{BASELINE_RECORD_S:g} s of Xela readings and temperatures "
         "(nothing may touch the skin)"),
        ("saved", "Saved", "Saved to <demo_dir>/baselines and picked in the Recordings list"),
    )
    STYLE = ClickPressStateView.STYLE
    TITLE = "<b>Baseline:</b>"

    def __init__(self) -> None:
        super().__init__()
        rows = QtWidgets.QVBoxLayout(self)
        rows.setContentsMargins(0, 0, 0, 0)
        rows.setSpacing(2)
        layout = QtWidgets.QHBoxLayout()
        rows.addLayout(layout)
        layout.addWidget(QtWidgets.QLabel(self.TITLE))
        self.boxes: dict[str, QtWidgets.QLabel] = {}
        for k, (key, label, tip) in enumerate(self.STAGES):
            if k:
                layout.addWidget(QtWidgets.QLabel("\u2192"))
            box = QtWidgets.QLabel(label)
            box.setToolTip(tip)
            box.setMinimumWidth(box.sizeHint().width())
            self.boxes[key] = box
            layout.addWidget(box)
        layout.addStretch(1)
        # Under the stages: how it ended, and its live status.
        self.outcome = QtWidgets.QLabel()
        self.status = QtWidgets.QLabel()
        line = QtWidgets.QHBoxLayout()
        line.addSpacing(QtWidgets.QLabel(self.TITLE).sizeHint().width() + 6)
        line.addWidget(self.outcome)
        line.addWidget(self.status, 1)
        rows.addLayout(line)
        self.stage: str | None = None
        self.show_stage(None)

    def show_stage(self, stage: str | None, status: str = "",
                   outcome: tuple[str, bool] | None = None) -> None:
        """Highlights ``stage`` (None: idle) with its live ``status``, and ``outcome`` ((text,
        whether it went well), None while it runs). A stage that ended with an outcome is
        shown passed (went well) or red (did not)."""
        self.stage = stage
        keys = [k for k, _, _ in self.STAGES]
        current = keys.index(stage) if stage in keys else -1
        for k, name in enumerate(keys):
            if k == current and outcome is not None and not outcome[1]:
                bg, fg, extra = COMBO_COLLIDE_COLOR, "white", "font-weight: bold;"
            elif k == current and outcome is None:
                bg, fg, extra = "#1976d2", "white", "font-weight: bold;"
            elif 0 <= k <= current:
                bg, fg, extra = "#c8e6c9", "#1b5e20", ""
            else:
                bg, fg, extra = "#eeeeee", "#9e9e9e", ""
            self.boxes[name].setStyleSheet(self.STYLE.format(bg=bg, fg=fg, extra=extra))
        if outcome is None:
            self.outcome.setText("")
        else:
            text, ok = outcome
            color = COMBO_VALID_COLOR if ok else COMBO_COLLIDE_COLOR
            self.outcome.setText(f"<span style='color:{color}'><b>{text}</b></span>")
        self.status.setText(f"<span style='color:#616161'>{status}</span>" if status else "")


class BaselinePlanSignals(QtCore.QObject):
    """hand_ik's answer (executor thread) to the Baseline tab."""

    planned = QtCore.pyqtSignal(object)


class BaselineTab(QtWidgets.QWidget):
    """Records a Sparsh-skin style no-contact baseline: Record asks hand_ik (mink) for a path
    from the hand's joints (as sim angles) to the open pose (0 on every sim joint) that keeps
    the fingers apart, and plays it on the hand with every joint on the hand node's stiff
    (playback) gains, which hold it there while the tab is shown (compliant again when it is
    left; Record is Stop until the recording starts); it waits ``BASELINE_SETTLE_S`` at the
    pose, then takes ``BASELINE_RECORD_S`` of Xela readings and temperatures (nothing may touch the skin), saved
    with their mean as ``<demo_dir>/baselines/baseline_<time>.npz``, with a ``meta`` JSON
    (``baseline_meta``: the date and time it started and ended, its length, readings, rate,
    taxels, temperature and pose). The Recordings panel on the
    left lists them, newest first (Up / Down pick the previous / next, Delete removes the picked
    one, Use for Sparsh-skin makes it the Sparsh-skin transform's baseline, tagged
    ``SPARSH_BASELINE_TAG``); ``BaselineStateView`` shows the stage of a Record (plan, move, settle, record,
    saved); the table shows every taxel's live reading and temperature next to the picked
    recording's means."""

    _RECORD_TEXT = f"Record {BASELINE_RECORD_S:g} s"

    def __init__(self, node: LeapStateListener, create_tab: CreateTab) -> None:
        super().__init__()
        self.node = node
        self.create_tab = create_tab  # keeps the playing fingers' stiff_joints
        self._stiff = False  # every joint given the hand's stiff gains by this tab
        self._to_sim: HardwareToSim | None = None  # loaded on first use
        self._planning = False
        self._signals = BaselinePlanSignals()
        self._signals.planned.connect(self._on_planned)
        # (time.monotonic() at its start, (steps, 16) hardware path, dt) of the move.
        self._move: tuple[float, np.ndarray, float] | None = None
        self._move_timer = QtCore.QTimer(self)
        self._move_timer.setInterval(10)
        self._move_timer.timeout.connect(self._move_step)
        self._settle_timer = QtCore.QTimer(self)
        self._settle_timer.setSingleShot(True)
        self._settle_timer.setInterval(int(BASELINE_SETTLE_S * 1000))
        self._settle_timer.timeout.connect(self._record_now)
        # [last Xela sequence taken, stamp at Record, (stamp, readings, temps) taken so far,
        # local datetime at Record]: taken every BASELINE_COLLECT_MS, as the node only keeps
        # HISTORY_LEN messages.
        self._record: list | None = None
        self._collect_timer = QtCore.QTimer(self)
        self._collect_timer.setInterval(BASELINE_COLLECT_MS)
        self._collect_timer.timeout.connect(self._collect)
        self._recorded: tuple[np.ndarray, np.ndarray] | None = None  # (T, 3) mean, (T,) temp
        self._table_drawn = 0.0

        self.record_btn = QtWidgets.QPushButton(self._RECORD_TEXT)
        self.record_btn.setToolTip(
            f"Move the hand to the {BASELINE_POSE} pose (0 on every sim joint) along a path "
            f"hand_ik (mink) plans to keep the fingers apart, wait {BASELINE_SETTLE_S:g} s, then "
            f"record {BASELINE_RECORD_S:g} s of Xela readings and temperatures as the "
            "no-contact baseline (nothing may touch the skin). Pressing it again before the "
            "recording starts stops."
        )
        self.record_btn.clicked.connect(self._toggle_record)
        self.pose_label = QtWidgets.QLabel()
        self.temp_label = QtWidgets.QLabel()
        self.status = QtWidgets.QLabel(
            f"Record moves the hand to the {BASELINE_POSE} pose first: make sure nothing will "
            "touch the skin."
        )
        self.status.setWordWrap(True)
        self.state_view = BaselineStateView()
        self.table = QtWidgets.QTableWidget(0, len(BASELINE_COLUMNS))
        self.table.setHorizontalHeaderLabels(BASELINE_COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.record_btn)
        buttons.addWidget(self.pose_label, 1)
        middle = QtWidgets.QWidget()
        middle_layout = QtWidgets.QVBoxLayout(middle)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.addLayout(buttons)
        middle_layout.addWidget(self.state_view)
        middle_layout.addWidget(self.status)
        middle_layout.addWidget(self.temp_label)
        middle_layout.addWidget(self.table, 1)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.addWidget(self._recordings_panel())
        split.addWidget(middle)
        split.setSizes([250, 1150])
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(split)

    def _recordings_panel(self) -> QtWidgets.QWidget:
        """The left panel, as on the Demonstration tab: the baseline recordings list
        (``self.list``, newest first, the Sparsh-skin transform's tagged
        ``SPARSH_BASELINE_TAG``), Use for Sparsh-skin and Delete for the picked one, and
        Refresh."""
        self.list = QtWidgets.QListWidget()
        self.list.setToolTip(
            f"Baseline recordings in <demo_dir>/baselines, newest first: the picked one's means "
            "are shown in the table's Rec columns"
        )
        self.list.currentRowChanged.connect(self._load_picked)
        self.count_label = QtWidgets.QLabel()
        self.delete_btn = QtWidgets.QPushButton("Delete")
        self.delete_btn.setToolTip("Delete the picked baseline recording")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_picked)
        self.use_btn = QtWidgets.QPushButton("Use for Sparsh-skin")
        self.use_btn.setToolTip(
            "The Sparsh-skin transform (Processing tab) subtracts the picked baseline from "
            f"every episode (tagged {SPARSH_BASELINE_TAG}; also picked in its dropdown)"
        )
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self._use_picked)
        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_recordings)
        left = QtWidgets.QGroupBox("Recordings")
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.addWidget(self.list, 1)
        left_layout.addWidget(self.count_label)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.use_btn)
        buttons.addWidget(self.delete_btn)
        left_layout.addLayout(buttons)
        left_layout.addWidget(refresh_btn)
        for key, step in (("Up", -1), ("Down", 1)):
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(functools.partial(self._step_recording, step))
        return left

    def showEvent(self, event) -> None:  # noqa: N802 - Qt
        super().showEvent(event)
        self.refresh_recordings()

    # ---- recordings --------------------------------------------------------------------

    def refresh_recordings(self, pick: str | None = None) -> None:
        """Lists the baseline recordings, newest first, keeping the picked one (or picking
        ``pick``)."""
        if pick is None:
            current = self.list.currentItem()
            pick = current.data(QtCore.Qt.UserRole) if current is not None else None
        paths = list_baselines(self.node.demo_dir)
        used = sparsh_baseline(self.node.demo_dir)
        self.count_label.setText(f"{len(paths)} recordings")
        self.list.blockSignals(True)
        self.list.clear()
        for path in paths:
            text = baseline_list_text(path)
            item = QtWidgets.QListWidgetItem(
                f"{SPARSH_BASELINE_TAG} {text}" if path == used else text
            )
            item.setData(QtCore.Qt.UserRole, path)
            item.setToolTip(path + ("\nUsed by the Sparsh-skin transform (Processing tab)"
                                    if path == used else ""))
            if path == used:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.list.addItem(item)
        self.list.setCurrentRow(paths.index(pick) if pick in paths else -1)
        self.list.blockSignals(False)
        self._load_picked()

    def _step_recording(self, step: int) -> None:
        """Picks the previous (-1) / next (1) recording of the list."""
        if self.list.count():
            row = self.list.currentRow()
            row = 0 if row < 0 else min(max(row + step, 0), self.list.count() - 1)
            self.list.setCurrentRow(row)

    def _load_picked(self, *_) -> None:
        """Shows the picked recording's means in the table (none picked: empty Rec columns)."""
        item = self.list.currentItem()
        self.delete_btn.setEnabled(item is not None)
        self.use_btn.setEnabled(item is not None)
        self._recorded = None
        self._table_drawn = 0.0
        if item is None:
            return
        path = item.data(QtCore.Qt.UserRole)
        try:
            with np.load(path) as data:
                self._recorded = (data["xela_baseline"], data["temp_mean"])
                std = data["xela_std"]
                meta = baseline_meta(data)
        except Exception as e:
            self.status.setText(f"Could not load {path}: {e}")
            return
        span = (f" \u00b7 {meta['started']} \u2013 {meta['ended']}" if "started" in meta
                else " \u00b7 no metadata (an older recording)")
        temp = (f" \u00b7 mean temperature {meta['temp_mean']:.2f}"
                if meta.get("temp_mean") is not None else "")
        self.status.setText(
            f"{baseline_list_text(path)}{span} \u00b7 taxel std median {np.median(std):.1f} counts "
            f"(max {std.max():.1f}){temp} \u00b7 {path}"
        )

    def _use_picked(self) -> None:
        """The picked recording becomes the Sparsh-skin transform's baseline."""
        item = self.list.currentItem()
        if item is not None:
            set_sparsh_baseline(item.data(QtCore.Qt.UserRole))
            self.refresh_recordings()

    def _delete_picked(self) -> None:
        """Deletes the picked recording, once confirmed."""
        item = self.list.currentItem()
        if item is None:
            return
        path = item.data(QtCore.Qt.UserRole)
        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Warning)
        box.setWindowTitle("Delete recording")
        box.setText(f"Delete the baseline recording '{os.path.basename(path)}'?")
        box.setInformativeText(f"{path} is removed from disk. This cannot be undone.")
        cancel = box.addButton(QtWidgets.QMessageBox.Cancel)
        confirm = box.addButton("Confirm", QtWidgets.QMessageBox.DestructiveRole)
        box.setDefaultButton(cancel)
        box.exec_()
        if box.clickedButton() is not confirm:
            return
        try:
            os.remove(path)
        except OSError as e:
            QtWidgets.QMessageBox.warning(
                self, "Delete recording", f"Could not delete {path}:\n{e}"
            )
        else:
            self.node.get_logger().info(f"Deleted the baseline recording '{path}'")
        self.list.setCurrentRow(-1)
        self.refresh_recordings()

    def _sim_now(self) -> tuple[list[str], np.ndarray] | None:
        """(sim joint names, sim angles) of the hand's latest joints, or None."""
        q = self.node.latest()
        if q is None:
            return None
        if self._to_sim is None:
            self._to_sim = HardwareToSim()
        return list(self._to_sim.sim_names), np.array(self._to_sim(self.node.joint_names, q))

    @staticmethod
    def _pose_sim(names: list[str]) -> np.ndarray:
        """The open pose's sim angles of joints ``names``: 0 on every joint."""
        return np.zeros(len(names))

    def _pose_error(self) -> float | None:
        """Largest joint distance (rad, sim angles) of the hand from the pose, or None."""
        now = self._sim_now()
        if now is None:
            return None
        return float(np.max(np.abs(now[1] - self._pose_sim(now[0]))))

    # ---- moving to the pose ------------------------------------------------------------

    def _start_move(self) -> bool:
        """Starts planning the move to the pose; False (with a warning) if it cannot."""
        now = self._sim_now()
        if now is None:
            QtWidgets.QMessageBox.warning(
                self, "Baseline", "No hand state yet: is the hand (leaphand_node) running?"
            )
            return False
        names, start = now
        goal = self._pose_sim(names)
        if not self.node.hand_ik_ready():
            QtWidgets.QMessageBox.warning(
                self, "Baseline",
                f"The IK service '{self.node.hand_ik_service}' is not available: start hand_ik "
                "(mechanical_pen_data_collection launch_mujoco_sim.py starts it).",
            )
            return False
        # A compliant hand only tracks commands on its stiff joints: all of them, to move.
        if not self.node.set_stiff_joints(list(self.node.joint_names)):
            QtWidgets.QMessageBox.warning(
                self, "Baseline",
                f"The hand node '{self.node.hand_node}' does not answer: its joints cannot be "
                "made stiff to follow the path.",
            )
            return False
        self._stiff = True
        self.create_tab.stiff_joints_set_elsewhere()
        self._planning = True
        self.status.setText(f"Planning the path to the {BASELINE_POSE} pose (hand_ik)...")
        self.state_view.show_stage("planning", f"hand_ik '{self.node.hand_ik_service}'")
        self.node.plan_hand_pose(names, start, goal, self._signals.planned.emit)
        return True

    def _on_planned(self, result) -> None:
        """hand_ik's path (sim angles): converted to hardware angles and played on the hand."""
        if not self._planning:  # stopped meanwhile
            return
        self._planning = False
        if isinstance(result, Exception):
            self._stop_move(f"Planning failed: {result}", ("Planning failed", False))
            return
        path_sim, dt, response = result
        names = list(response.joint_names)
        by_name = [dict(zip(self._to_sim.sim_names, self._to_sim.to_hardware(names, q)))
                   for q in path_sim]
        path = np.array([[q[n] for n in self.node.joint_names] for q in by_name])
        self._move = (time.monotonic(), path, dt)
        self.state_view.show_stage("moving", f"{len(path) * dt:.1f} s path")
        self.status.setText(
            f"Moving to the {BASELINE_POSE} pose along the IK path: {response.message}"
        )
        self._move_timer.start()

    def _move_step(self) -> None:
        """Sends the point of the path due now."""
        if self._move is None:
            return
        start, path, dt = self._move
        i = min(int((time.monotonic() - start) / dt), len(path) - 1)
        self.node.send_command(path[i])
        if i == len(path) - 1:  # there: held while it settles
            self._move_timer.stop()
            self._move = None
            self.status.setText(
                f"At the {BASELINE_POSE} pose: recording in {BASELINE_SETTLE_S:g} s..."
            )
            self.state_view.show_stage("settling", f"{BASELINE_SETTLE_S:g} s at the pose")
            self._settle_timer.start()

    def _moving(self) -> bool:
        """Whether Record is planning, moving to the pose or settling there."""
        return self._move is not None or self._planning or self._settle_timer.isActive()

    def _stop_move(self, text: str, outcome: tuple[str, bool] | None = None) -> None:
        """Ends Record's move (or its settling), shown ending with ``outcome``."""
        self._move_timer.stop()
        self._settle_timer.stop()
        self._move = None
        self._planning = False
        self.record_btn.setText(self._RECORD_TEXT)
        self.record_btn.setEnabled(self._record is None)
        self.status.setText(text)
        if outcome is not None:
            self.state_view.show_stage(self.state_view.stage, "", outcome)

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt
        """Leaving the tab stops a move and makes the hand compliant again."""
        if self._moving():
            self._stop_move("Stopped (left the tab).", ("Stopped (left the tab)", False))
        if self._stiff and self.node.set_stiff_joints([]):
            self._stiff = False
            self.create_tab.stiff_joints_set_elsewhere()
        super().hideEvent(event)

    # ---- recording ---------------------------------------------------------------------

    def _toggle_record(self) -> None:
        """Record: moves the hand to the pose, ``_record_now`` once it has been there
        ``BASELINE_SETTLE_S``; pressed again before that (Stop), stops."""
        if self._moving():
            self._stop_move("Stopped.", ("Stopped", False))
            return
        if self.node.latest_xela()[1] is None:
            QtWidgets.QMessageBox.warning(
                self, "Baseline", f"No Xela readings on '{self.node.xela_topic}' yet."
            )
            return
        if self._start_move():
            self.record_btn.setText("Stop")

    def _record_now(self) -> None:
        """Starts taking the ``BASELINE_RECORD_S`` of Xela readings."""
        self.record_btn.setText(self._RECORD_TEXT)
        seq, readings = self.node.latest_xela()
        if readings is None:
            self.record_btn.setEnabled(True)
            self.status.setText(f"Record: no Xela readings on '{self.node.xela_topic}'.")
            self.state_view.show_stage("recording", "", ("No Xela readings", False))
            return
        self._record = [seq, self.node.get_clock().now().nanoseconds * 1e-9, [],
                        datetime.now().astimezone()]
        self.record_btn.setEnabled(False)
        self.status.setText(f"Recording {BASELINE_RECORD_S:g} s...")
        self.state_view.show_stage("recording", f"0.0 / {BASELINE_RECORD_S:g} s")
        self._collect_timer.start()
        # A little longer, so the last messages of the recording have arrived.
        QtCore.QTimer.singleShot(int((BASELINE_RECORD_S + 0.2) * 1000), self._finish_record)

    def _collect(self) -> None:
        """Takes the Xela messages that came since the last time."""
        if self._record is None:
            return
        self._record[0], items = self.node.xela_temps_since(self._record[0])
        self._record[2].extend(items)
        elapsed = self.node.get_clock().now().nanoseconds * 1e-9 - self._record[1]
        progress = (f"{min(elapsed, BASELINE_RECORD_S):.1f} / {BASELINE_RECORD_S:g} s "
                    f"({len(self._record[2])} readings)")
        self.status.setText(f"Recording {progress}...")
        self.state_view.show_stage("recording", progress)

    def _finish_record(self) -> None:
        self._collect_timer.stop()
        self.record_btn.setEnabled(True)
        if self._record is None:
            return
        self._collect()
        _, start, items, started = self._record
        self._record = None
        items = [it for it in items if start <= it[0] <= start + BASELINE_RECORD_S]
        if items:  # a recording holds one taxel count
            items = [it for it in items if len(it[1]) == len(items[0][1])]
        if not items:
            self.status.setText(f"Record: no Xela readings in {BASELINE_RECORD_S:g} s.")
            self.state_view.show_stage("recording", "", ("No Xela readings", False))
            return
        t = np.array([stamp for stamp, _, _ in items]) - start
        xela = np.stack([readings for _, readings, _ in items]).astype(np.float32)
        temp = np.stack([temps for _, _, temps in items]).astype(np.float32)
        mean, std = xela.mean(axis=0), xela.std(axis=0)
        with warnings.catch_warnings():  # taxels without a temperature are all NaN
            warnings.simplefilter("ignore", RuntimeWarning)
            temp_mean = np.nanmean(temp, axis=0)
        error, q, now = self._pose_error(), self.node.latest(), self._sim_now()
        sim_names = now[0] if now is not None else []
        pose = self._pose_sim(sim_names) if now is not None else None  # sim angles
        directory = baseline_dir(self.node.demo_dir)
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"baseline_{started.strftime('%Y%m%d_%H%M%S')}.npz")
        has_temp = np.isfinite(temp_mean)
        meta = {
            "date": started.strftime("%Y-%m-%d"),
            "time": started.strftime("%H:%M:%S"),
            "started": started.isoformat(timespec="seconds"),
            "ended": datetime.now().astimezone().isoformat(timespec="seconds"),
            "duration_s": BASELINE_RECORD_S,
            "readings": len(t),
            "rate_hz": len(t) / BASELINE_RECORD_S,
            "taxels": int(xela.shape[1]),
            "xela_topic": self.node.xela_topic,
            "temp_mean": float(np.mean(temp_mean[has_temp])) if has_temp.any() else None,
            "std_median": float(np.median(std)),
            "pose": BASELINE_POSE,
            "pose_error": error,
            "at_pose": error is not None and error <= BASELINE_POSE_TOLERANCE,
        }
        np.savez_compressed(
            path,
            t=t, xela=xela, temp=temp, xela_baseline=mean, xela_std=std, temp_mean=temp_mean,
            joint_names=np.array(self.node.joint_names),
            q=q if q is not None else np.empty(0),
            sim_joint_names=np.array(sim_names),
            q_sim=now[1] if now is not None else np.empty(0),
            pose=BASELINE_POSE, pose_sim=pose if pose is not None else np.empty(0),
            pose_error=np.nan if error is None else error,
            stamp=start,
            meta=json.dumps(meta),
        )
        self.refresh_recordings(pick=path)  # lists it and shows its means in the table
        self.state_view.show_stage(
            "saved", os.path.basename(path),
            ("Saved", True) if meta["at_pose"]
            else (f"Saved, but {error:.2f} rad from the pose" if error is not None
                  else "Saved, pose unknown", False),
        )
        self.status.setText(
            f"Recorded {len(t)} readings in {BASELINE_RECORD_S:g} s "
            f"({len(t) / BASELINE_RECORD_S:.0f} Hz) · taxel std median "
            f"{np.median(std):.1f} counts (max {std.max():.1f}) · "
            + (f"mean temperature {np.mean(temp_mean[has_temp]):.2f}" if has_temp.any()
               else "no temperature from xela_server")
            + f" · saved to {path}"
            + ("" if error is None or error <= BASELINE_POSE_TOLERANCE else
               f"  ⚠ the hand was {error:.2f} rad from the {BASELINE_POSE} pose")
        )

    # ---- live view ---------------------------------------------------------------------

    def refresh(self) -> None:
        if not self.isVisible():
            return
        error = self._pose_error()
        self.pose_label.setText(
            "No hand state" if error is None
            else f"{error:.3f} rad (sim) from the {BASELINE_POSE} pose"
            + (" ✓" if error <= BASELINE_POSE_TOLERANCE else "")
        )
        now = time.monotonic()
        if now - self._table_drawn < BASELINE_TABLE_MS / 1000:
            return
        seq, readings = self.node.latest_xela()
        if readings is None:
            self.temp_label.setText(f"No Xela readings on '{self.node.xela_topic}'")
            return
        self._table_drawn = now
        _, items = self.node.xela_temps_since(seq - 1)
        temps = items[-1][2] if items else np.full(len(readings), np.nan)
        finite = temps[np.isfinite(temps)]
        self.temp_label.setText(
            f"Temperature: min {finite.min():.2f} · mean {finite.mean():.2f} · "
            f"max {finite.max():.2f}" if len(finite)
            else "Temperature: none from xela_server"
        )
        self._fill_table(readings, temps)

    def _fill_table(self, readings: np.ndarray, temps: np.ndarray) -> None:
        def text(v: float, digits: int) -> str:
            return "" if not np.isfinite(v) else f"{v:.{digits}f}"

        n = len(readings)
        mean, temp_mean = self._recorded if self._recorded is not None else (None, None)
        if mean is not None and len(mean) != n:
            mean = temp_mean = None
        self.table.setUpdatesEnabled(False)
        if self.table.rowCount() != n:
            self.table.setRowCount(n)
        for i in range(n):
            row = [str(i), *(text(v, 0) for v in readings[i]),
                   text(temps[i] if i < len(temps) else np.nan, 2)]
            if mean is not None:
                row += [*(text(v, 1) for v in mean[i]), text(temp_mean[i], 2)]
            else:
                row += [""] * 4
            for c, value in enumerate(row):
                item = self.table.item(i, c)
                if item is None:
                    self.table.setItem(i, c, QtWidgets.QTableWidgetItem(value))
                elif item.text() != value:
                    item.setText(value)
        self.table.setUpdatesEnabled(True)


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
        backup_box = self._build_backup_box(saved.get("nextcloud", {}))

        save_btn = QtWidgets.QPushButton("Save settings")
        save_btn.setToolTip(
            "Save the folder, playback, maintain touch, click press, hand and Nextcloud values; "
            "they are used at the "
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
        sections_layout.addWidget(backup_box)
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

    # ---- Backup to Nextcloud ------------------------------------------------------------

    def _build_backup_box(self, saved: dict) -> QtWidgets.QGroupBox:
        """Server, user, app password, remote and local folders, Test connection, Sync and
        its progress bar."""
        self._backup_thread: threading.Thread | None = None
        self._backup_stop = threading.Event()
        self._backup_signals = BackupSignals()
        self._backup_signals.progress.connect(self._backup_progress)
        self._backup_signals.done.connect(self._backup_done)
        self.nc_url = QtWidgets.QLineEdit(saved.get("url", ""))
        self.nc_url.setPlaceholderText("https://cloud.example.com")
        self.nc_url.setToolTip("The address of the Nextcloud server (as in the browser)")
        self.nc_user = QtWidgets.QLineEdit(saved.get("user", ""))
        self.nc_user.setToolTip("Your Nextcloud login name")
        self.nc_password = QtWidgets.QLineEdit(saved.get("password", ""))
        self.nc_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.nc_password.setToolTip(
            "An app password: Nextcloud > Settings > Security > Devices & sessions > Create new "
            "app password (your login password works too, unless two-factor login is on)"
        )
        self.nc_remember = QtWidgets.QCheckBox("Remember password")
        self.nc_remember.setChecked(bool(saved.get("password")))
        self.nc_remember.setToolTip(
            f"Save settings also writes the app password, in plain text, to {self._saved_path} "
            "(Sync leaves it out of the copy it uploads)"
        )
        self.nc_remote = QtWidgets.QLineEdit(
            saved.get("remote_dir", nextcloud_backup.NextcloudConfig.remote_dir)
        )
        self.nc_remote.setToolTip("Folder on the server the files are uploaded into (created if missing)")
        self.nc_local = QtWidgets.QLineEdit(saved.get("local_dir") or self.store.demo_dir)
        self.nc_local.setToolTip("Folder backed up, with everything in it (the recordings folder)")
        local_browse = QtWidgets.QPushButton("Browse...")
        local_browse.clicked.connect(self._browse_backup_dir)
        password_row = QtWidgets.QHBoxLayout()
        password_row.addWidget(self.nc_password, 1)
        password_row.addWidget(self.nc_remember)
        local_row = QtWidgets.QHBoxLayout()
        local_row.addWidget(self.nc_local, 1)
        local_row.addWidget(local_browse)
        self.nc_test_btn = QtWidgets.QPushButton("Test connection")
        self.nc_test_btn.clicked.connect(self._test_backup)
        self.nc_sync_btn = QtWidgets.QPushButton("Sync")
        self.nc_sync_btn.setToolTip(
            "Upload every file of the local folder, and the app's own files (settings, event "
            "definitions, click templates, Qt preferences; under <remote folder>/_app), the "
            "server does not have yet with the same size and time (nothing is deleted on "
            "either side); press again to stop\n"
            + "\n".join(f"_app/{name}: {path}" for path, name in backup_extras(self.node.events_file))
        )
        self.nc_sync_btn.clicked.connect(self._sync_backup)
        self.nc_pull_btn = QtWidgets.QPushButton("Pull")
        self.nc_pull_btn.setToolTip(
            "Download the backup: shows where each part of it goes first (change or leave "
            "out any), then downloads what is missing or different locally; press again to stop"
        )
        self.nc_pull_btn.clicked.connect(self._pull_backup)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.nc_test_btn)
        buttons.addWidget(self.nc_sync_btn)
        buttons.addWidget(self.nc_pull_btn)
        buttons.addStretch(1)
        self.nc_progress = QtWidgets.QProgressBar()
        self.nc_progress.setRange(0, 1000)
        self.nc_progress.setValue(0)
        self.nc_progress.setFormat("%p %")
        self.nc_status = QtWidgets.QLabel("Not synced in this session.")
        self.nc_status.setWordWrap(True)
        box = QtWidgets.QGroupBox("Backup to Nextcloud")
        form = QtWidgets.QFormLayout(box)
        form.addRow("Server:", self.nc_url)
        form.addRow("User:", self.nc_user)
        form.addRow("App password:", password_row)
        form.addRow("Remote folder:", self.nc_remote)
        form.addRow("Local folder:", local_row)
        form.addRow("", buttons)
        form.addRow(self.nc_progress)
        form.addRow(self.nc_status)
        return box

    def _backup_config(self) -> nextcloud_backup.NextcloudConfig:
        url = self.nc_url.text().strip()
        if url and "://" not in url:
            url = "https://" + url
        return nextcloud_backup.NextcloudConfig(
            url=url, user=self.nc_user.text().strip(), password=self.nc_password.text(),
            remote_dir=self.nc_remote.text().strip(),
            local_dir=os.path.abspath(os.path.expanduser(self.nc_local.text().strip())),
        )

    def _backup_saved(self) -> dict:
        cfg = self._backup_config()
        data = {"url": cfg.url, "user": cfg.user, "remote_dir": cfg.remote_dir,
                "local_dir": cfg.local_dir}
        if self.nc_remember.isChecked() and cfg.password:
            data["password"] = cfg.password
        return data

    def _browse_backup_dir(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Folder to back up", self.nc_local.text()
        )
        if path:
            self.nc_local.setText(path)

    def _backup_status(self, text: str, error: bool = False) -> None:
        self.nc_status.setText(f"<span style='color:#d32f2f'>{text}</span>" if error else text)

    def _test_backup(self) -> None:
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self._backup_status(nextcloud_backup.test_connection(self._backup_config()))
        except Exception as e:  # noqa: BLE001 - shown to the user
            self._backup_status(f"Could not connect: {e}", error=True)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    def _sync_backup(self) -> None:
        """Starts the backup in the background, or asks the running one to stop."""
        if self._backup_running():
            self._backup_stop.set()
            self.nc_sync_btn.setEnabled(False)
            self._backup_status("Stopping...")
            return
        cfg = self._backup_config()
        if not cfg.url or not cfg.user or not cfg.password:
            self._backup_status("Fill in the server, user and app password.", error=True)
            return
        self._start_backup_thread(self.nc_sync_btn, self._run_backup, cfg)

    def _start_backup_thread(self, button: QtWidgets.QPushButton, target, *args) -> None:
        """Runs Sync or Pull (``target``) in the background; ``button`` becomes its Stop."""
        self._backup_stop.clear()
        self._backup_button = button
        for btn in (self.nc_sync_btn, self.nc_pull_btn, self.nc_test_btn):
            btn.setEnabled(btn is button)
        button.setText("Stop")
        self.nc_progress.setValue(0)
        self._backup_started = time.monotonic()
        self._backup_thread = threading.Thread(target=target, args=args, daemon=True)
        self._backup_thread.start()

    def _backup_running(self) -> bool:
        return self._backup_thread is not None and self._backup_thread.is_alive()

    def _pull_backup(self) -> None:
        """Lists the backup, shows where each part goes (``PullDialog``) and, once confirmed,
        downloads it in the background; or asks the running one to stop."""
        if self._backup_running():
            self._backup_stop.set()
            self.nc_pull_btn.setEnabled(False)
            self._backup_status("Stopping...")
            return
        cfg = self._backup_config()
        if not cfg.url or not cfg.user or not cfg.password:
            self._backup_status("Fill in the server, user and app password.", error=True)
            return
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self._backup_status("Listing the backup...")
        QtWidgets.QApplication.processEvents()
        try:
            remote = nextcloud_backup.list_backup(cfg)
        except Exception as e:  # noqa: BLE001 - shown to the user
            self._backup_status(f"Could not list the backup: {e}", error=True)
            return
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        if not remote:
            self._backup_status(f"There is no backup in {cfg.remote_dir}.", error=True)
            return
        self._backup_status(f"{len(remote)} files in the backup.")
        dialog = PullDialog(
            self, remote, pull_targets(cfg.local_dir, self.node.events_file),
            f"{urlparse(cfg.url).netloc}/{cfg.remote_dir}",
        )
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        self._start_backup_thread(
            self.nc_pull_btn, self._run_pull, cfg, dialog.plan(),
            dialog.overwrite_check.isChecked(),
        )

    def _run_pull(self, cfg, files, overwrite: bool) -> None:
        """Pull's thread: reports through ``_backup_signals``."""
        try:
            result = nextcloud_backup.pull(
                cfg, files, self._throttled_progress(), self._backup_stop, overwrite
            )
        except Exception as e:  # noqa: BLE001 - shown to the user
            self._backup_signals.done.emit(f"Pull failed: {e}", True)
            return
        spent = time.monotonic() - self._backup_started
        text = (
            f"{'Stopped' if result.cancelled else 'Pulled'} from {cfg.remote_dir}: "
            f"{result.downloaded} files downloaded ({result.bytes_received / 1e6:.1f} MB in "
            f"{spent:.0f} s), {result.skipped} already the same"
            + (f", {result.kept_newer} newer locally kept" if result.kept_newer else "")
        )
        if result.failed:
            text += f", {len(result.failed)} failed (first: {result.failed[0][0]}: " \
                    f"{result.failed[0][1]}; see the log)"
            for rel, why in result.failed:
                self.node.get_logger().warn(f"Pull from Nextcloud: {rel}: {why}")
        if result.downloaded:
            text += ". Restart the app to load restored settings."
        self._backup_signals.done.emit(text, bool(result.failed))

    def _throttled_progress(self):
        """A progress callback for the thread: at most 10 updates a second (and the last)."""
        last = [0.0]

        def progress(*info) -> None:
            now = time.monotonic()
            if now - last[0] >= 0.1 or not info[4]:
                last[0] = now
                self._backup_signals.progress.emit(info)

        return progress

    def _run_backup(self, cfg: nextcloud_backup.NextcloudConfig) -> None:
        """The backup's thread: reports through ``_backup_signals``."""
        try:
            result = nextcloud_backup.sync(
                cfg, self._throttled_progress(), self._backup_stop, backup_extras(self.node.events_file),
                redact=BACKUP_REDACT,
            )
        except Exception as e:  # noqa: BLE001 - shown to the user
            self._backup_signals.done.emit(f"Sync failed: {e}", True)
            return
        spent = time.monotonic() - self._backup_started
        text = (
            f"{'Stopped' if result.cancelled else 'Synced'} to {cfg.remote_dir}: "
            f"{result.uploaded} files uploaded ({result.bytes_sent / 1e6:.1f} MB in "
            f"{spent:.0f} s), {result.skipped} already there"
        )
        if result.failed:
            text += f", {len(result.failed)} failed (first: {result.failed[0][0]}: " \
                    f"{result.failed[0][1]}; see the log)"
            for rel, why in result.failed:
                self.node.get_logger().warn(f"Backup to Nextcloud: {rel}: {why}")
        self._backup_signals.done.emit(text, bool(result.failed))

    def _backup_progress(self, info: tuple) -> None:
        sent, total, files_done, files, current = info
        if total:
            self.nc_progress.setValue(int(1000 * sent / total))
        spent = max(time.monotonic() - self._backup_started, 1e-3)
        rate = sent / spent
        left = (total - sent) / rate if rate > 0 else 0.0
        if not files and current:
            self._backup_status(current)  # listing the server
            return
        self._backup_status(
            f"{files_done} / {files} files, {sent / 1e6:.1f} / {total / 1e6:.1f} MB, "
            f"{rate / 1e6:.1f} MB/s, ~{left / 60:.0f} min left"
            + (f"\n{current}" if current else "")
        )

    def _backup_done(self, text: str, error: bool) -> None:
        self._backup_status(text, error)
        if not error and "Stopped" not in text:
            self.nc_progress.setValue(self.nc_progress.maximum())
        self.nc_sync_btn.setText("Sync")
        self.nc_pull_btn.setText("Pull")
        for btn in (self.nc_sync_btn, self.nc_pull_btn, self.nc_test_btn):
            btn.setEnabled(True)

    def stop_backup(self) -> None:
        self._backup_stop.set()

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
            "nextcloud": self._backup_saved(),
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
        self.processing_tab = ProcessingTab(node, self.store, event_defs)
        self.analysis_tab = AnalysisTab(node, self.store)
        self.baseline_tab = BaselineTab(node, self.create_tab)
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
        tabs.addTab(self.processing_tab, "Processing")
        tabs.addTab(self.analysis_tab, "Analysis")
        tabs.addTab(self.baseline_tab, "Baseline")
        tabs.addTab(self.settings_tab, "Settings")
        self.setCentralWidget(tabs)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.create_tab.refresh)
        self._timer.timeout.connect(self.edit_tab.refresh)
        self._timer.timeout.connect(self.compose_tab.refresh)
        self._timer.timeout.connect(self.analysis_tab.refresh)
        self._timer.timeout.connect(self.baseline_tab.refresh)
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
        self.compose_tab.stop_combination_check()
        self.analysis_tab.close_video()
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
        self.processing_tab.close_video()
        self.settings_tab.stop_backup()
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
