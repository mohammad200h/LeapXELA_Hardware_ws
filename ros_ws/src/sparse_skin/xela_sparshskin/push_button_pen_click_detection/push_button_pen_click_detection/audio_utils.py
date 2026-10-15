"""
Audio helpers shared by the click recorder and the click detector.

Everything here is plain numpy/scipy except ``find_input_device``, which imports
``sounddevice`` lazily so the signal-processing code can be tested without
PortAudio or a microphone.

Signals are mono float32 arrays in [-1, 1].
"""

from __future__ import annotations

import glob
import os
import re

import numpy as np
from scipy import signal
from scipy.io import wavfile

SAMPLE_RATE = 48000
DEFAULT_DEVICE = "08bb:2902"  # TI PCM2902 USB mic (ALSA calls it "USB PnP Sound Device")
USB_ID_RE = re.compile(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{4}")
DEFAULT_TEMPLATE_DIR = os.path.expanduser("~/.ros/pen_click_templates")

HIGHPASS_HZ = 300.0
FADE_S = 0.005

# STFT used for matching: ~10.7 ms window, ~2.7 ms hop at 48 kHz
STFT_WINDOW = 512
STFT_HOP = 128
FEATURE_BAND_HZ = (1000.0, 16000.0)


def alsa_card_for_usb_id(usb_id: str) -> int | None:
    """ALSA card number of the USB audio device ``vid:pid``, from /proc/asound/cardN/usbid."""
    for path in glob.glob("/proc/asound/card[0-9]*/usbid"):
        try:
            with open(path) as f:
                if f.read().strip().lower() == usb_id.lower():
                    return int(os.path.basename(os.path.dirname(path))[len("card"):])
        except OSError:
            continue
    return None


def find_output_device(query: str) -> int | None:
    """Index of the output device given by index or name substring, or None if no match."""
    import sounddevice as sd

    query = query.strip()
    if query.isdigit():
        return int(query)
    for index, d in enumerate(sd.query_devices()):
        if d["max_output_channels"] > 0 and query.lower() in d["name"].lower():
            return index
    return None


def find_input_device(query: str) -> int:
    """
    Index of the input device selected by ``query``.

    ``query`` is a device index ("12"), a USB id ("08bb:2902", resolved to its
    ALSA card so it survives card renumbering) or a name substring.
    """
    import sounddevice as sd

    query = query.strip()
    if query.isdigit():
        return int(query)
    inputs = [
        (i, d["name"]) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0
    ]
    if USB_ID_RE.fullmatch(query):
        card = alsa_card_for_usb_id(query)
        if card is not None:
            for index, name in inputs:
                if f"(hw:{card}," in name:
                    return index
        problem = (
            f"USB device {query} has no ALSA card" if card is None
            else f"USB device {query} is ALSA card {card} but has no input device"
        )
    else:
        for index, name in inputs:
            if query.lower() in name.lower():
                return index
        problem = f"No input device matching '{query}'"
    listing = "\n".join(f"  [{i}] {name}" for i, name in inputs) or "  (none)"
    raise RuntimeError(f"{problem}. Available input devices:\n{listing}")


def save_wav(path: str, x: np.ndarray, sr: int) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pcm = np.clip(x, -1.0, 1.0)
    wavfile.write(path, sr, (pcm * 32767).astype(np.int16))


def load_wav(path: str) -> tuple[np.ndarray, int]:
    """Mono float32 samples and the sample rate."""
    sr, data = wavfile.read(path)
    if np.issubdtype(data.dtype, np.integer):
        data = data.astype(np.float32) / np.iinfo(data.dtype).max
    data = data.astype(np.float32)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data, int(sr)


def resample(x: np.ndarray, sr_from: int, sr_to: int) -> np.ndarray:
    if sr_from == sr_to:
        return x
    g = np.gcd(sr_from, sr_to)
    return signal.resample_poly(x, sr_to // g, sr_from // g).astype(np.float32)


def highpass_sos(sr: int, cutoff_hz: float = HIGHPASS_HZ) -> np.ndarray:
    return signal.butter(4, cutoff_hz, btype="highpass", fs=sr, output="sos")


def clean(x: np.ndarray, sr: int) -> np.ndarray:
    """High-pass away hum/rumble, fade the edges and peak-normalize."""
    y = x.astype(np.float64) - np.mean(x)
    if len(y) > 27:  # sosfiltfilt padding needs a minimum length
        y = signal.sosfiltfilt(highpass_sos(sr), y)
    n_fade = min(int(FADE_S * sr), len(y) // 2)
    if n_fade > 0:
        ramp = np.linspace(0.0, 1.0, n_fade)
        y[:n_fade] *= ramp
        y[-n_fade:] *= ramp[::-1]
    peak = np.max(np.abs(y)) if len(y) else 0.0
    if peak > 0:
        y = y / peak * 0.9
    return y.astype(np.float32)


def short_time_rms(x: np.ndarray, frame: int) -> np.ndarray:
    n = len(x) // frame
    if n == 0:
        return np.zeros(0)
    frames = x[: n * frame].astype(np.float64).reshape(n, frame)
    return np.sqrt(np.mean(frames**2, axis=1))


def features(x: np.ndarray, sr: int) -> np.ndarray:
    """Log-magnitude spectrogram in the matching band, shape (freq, frames)."""
    _, _, z = signal.stft(
        x.astype(np.float64),
        fs=sr,
        nperseg=STFT_WINDOW,
        noverlap=STFT_WINDOW - STFT_HOP,
        boundary=None,
        padded=False,
    )
    freqs = np.fft.rfftfreq(STFT_WINDOW, 1.0 / sr)
    lo, hi = FEATURE_BAND_HZ
    band = (freqs >= lo) & (freqs <= min(hi, sr / 2))
    return np.log(np.abs(z[band]) + 1e-6).astype(np.float32)


def _normalize(m: np.ndarray) -> np.ndarray:
    """
    Per-matrix normalization over the last two axes for Pearson correlation.

    The per-frequency mean is removed first so a stationary background spectrum
    (mic colour, fan noise) does not count as similarity; only the time-frequency
    shape of the event does.
    """
    m = m - m.mean(axis=-1, keepdims=True)
    m = m - m.mean(axis=(-2, -1), keepdims=True)
    norm = np.sqrt((m**2).sum(axis=(-2, -1), keepdims=True))
    return m / np.maximum(norm, 1e-9)


def similarity(template_feat: np.ndarray, live_feat: np.ndarray) -> float:
    """
    Best Pearson correlation of the template slid across ``live_feat``, in [-1, 1].

    ``live_feat`` must have at least as many frames as the template.
    """
    n = template_feat.shape[1]
    if live_feat.shape[1] < n:
        return 0.0
    windows = np.lib.stride_tricks.sliding_window_view(live_feat, n, axis=1)
    windows = np.moveaxis(windows, 1, 0)  # (offsets, freq, n)
    scores = (_normalize(windows) * _normalize(template_feat)).sum(axis=(-2, -1))
    return float(scores.max())
