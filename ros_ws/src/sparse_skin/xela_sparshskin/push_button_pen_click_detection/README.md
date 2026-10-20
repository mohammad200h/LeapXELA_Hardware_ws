# push_button_pen_click_detection

Detects the click of a push-button pen with a USB microphone (default: TI PCM2902, selected by USB id `08bb:2902`;
ALSA lists it as "USB PnP Sound Device"). Override with `device:=<usb id | name | index>`.

## Prerequisites
- `apt install libportaudio2`. The pip package `sounddevice` needs it.
- The mic must be visible to ALSA (`cat /proc/asound/cards`) and to sounddevice:
  `python3 -c "import sounddevice as sd; print(sd.query_devices())"`

## 1. Record a click template
```
ros2 launch push_button_pen_click_detection launch_click_recorder.py
```
Record, click the pen a few times, then Stop. Play all plays the whole recording with a red
playhead, so you can find the clicks. Left-drag on the waveform to select one click; drag the
green region or its edges to adjust it (mouse wheel zooms, middle-drag pans). Play the
selection to check it, then Save. Pick your speakers/headphones in "Play on:".
The cleaned clip (high-passed, normalized) goes to `~/.ros/pen_click_templates/click_<time>.wav`.
Saving several clicks makes detection more robust: the detector uses every WAV in that folder.
Select a single click (~50 ms), the press or the release, not both: the detector pairs them itself.

## 2. Detect
```
ros2 launch push_button_pen_click_detection launch_click_detector.py
ros2 topic echo /pen_click         # std_msgs/Int32: 1 while a click is heard, else 0
ros2 topic echo /pen_click/score   # std_msgs/Float32: best template similarity
```
A pen makes two clicks, on press and on release. Every template match is an event, and a pen click is
reported only for two events `min_gap_s`..`max_gap_s` apart (default 0.05-0.5 s) with no other event
within `quiet_s` (0.15 s) before the press, between them, or after the release. Typing makes bursts of
clicks and is rejected. The click is reported `quiet_s` after the release; the log prints its
press-release gap, so you can narrow the range to how you (or the robot) press the pen.
`pair:=false` reports every match instead.
If you get false positives, raise `threshold:=0.8`. If clicks are missed, lower it, or lower `energy_gate`.
The live audio's spectrogram is correlated against each template's spectrogram as it slides over the window.
Windows that are not louder than the background are skipped.
