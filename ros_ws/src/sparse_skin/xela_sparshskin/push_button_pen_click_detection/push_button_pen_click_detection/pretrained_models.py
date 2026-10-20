"""
Pretrained sound classifiers that need no training, and a trigger for loud sounds.

  - CLAP (laion/larger_clap_general): zero-shot, scores audio against text descriptions
  - AST (MIT/ast-finetuned-audioset-10-10-0.4593): the 527 AudioSet classes

Both take mono float32 audio at their own ``sr``. ``torch`` and ``transformers``
are imported only when a model is created. The weights are downloaded on first
use (~600 MB CLAP, ~350 MB AST) to ~/.cache/huggingface.
"""

from __future__ import annotations

from typing import Callable, Iterator

import numpy as np
from scipy import signal

from push_button_pen_click_detection import audio_utils

CLAP_NAME = "laion/larger_clap_general"
AST_NAME = "MIT/ast-finetuned-audioset-10-10-0.4593"
DEFAULT_LABELS = [
    "a retractable pen clicking",
    "typing on a computer keyboard",
    "a computer mouse click",
    "tapping on a desk",
    "silence",
    "people talking",
]
MODELS = ("clap", "ast")

HOP_S = 0.05
RMS_FRAME_S = 0.005
NOISE_FLOOR_ALPHA = 0.05


def default_torch_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


class Clap:
    sr = 48000

    def __init__(self, labels: list[str], device: str) -> None:
        import torch
        from transformers import ClapModel, ClapProcessor

        self._torch = torch
        self._device = device
        self._model = ClapModel.from_pretrained(CLAP_NAME).to(device).eval()
        self._proc = ClapProcessor.from_pretrained(CLAP_NAME)
        self.labels = list(labels)
        with torch.no_grad():
            text = self._proc(text=self.labels, return_tensors="pt", padding=True).to(device)
            self._text = self._unit(self._model.get_text_features(**text))

    def _unit(self, out):
        emb = getattr(out, "pooler_output", out)
        return self._torch.nn.functional.normalize(emb, dim=-1)

    def __call__(self, x: np.ndarray) -> list[tuple[str, float]]:
        """Return ``(label, probability)`` for every label, most likely first; they sum to 1."""
        with self._torch.no_grad():
            audio = self._proc(audio=[x], sampling_rate=self.sr, return_tensors="pt")
            emb = self._unit(self._model.get_audio_features(**audio.to(self._device)))
            prob = (emb @ self._text.T * 100).softmax(-1)[0].tolist()
        return sorted(zip(self.labels, prob), key=lambda lp: -lp[1])


class Ast:
    sr = 16000

    def __init__(self, device: str, top: int = 5) -> None:
        import torch
        from transformers import ASTFeatureExtractor, ASTForAudioClassification

        self._torch = torch
        self._device = device
        self._top = top
        self._model = ASTForAudioClassification.from_pretrained(AST_NAME).to(device).eval()
        self._proc = ASTFeatureExtractor.from_pretrained(AST_NAME)

    def __call__(self, x: np.ndarray) -> list[tuple[str, float]]:
        """Return the ``top`` most likely AudioSet classes; each probability is independent."""
        with self._torch.no_grad():
            inputs = self._proc(x, sampling_rate=self.sr, return_tensors="pt")
            logits = self._model(**inputs.to(self._device)).logits[0]
            values, idx = self._torch.sigmoid(logits).topk(self._top)  # multi-label
        names = self._model.config.id2label
        return [(names[int(i)], float(v)) for v, i in zip(values, idx)]


def create(model: str, labels: list[str], device: str):
    if model == "clap":
        return Clap(labels, device)
    if model == "ast":
        return Ast(device)
    raise ValueError(f"Unknown model '{model}', expected one of {MODELS}")


def loud_windows(
    next_chunk: Callable[[], np.ndarray], sr: int, window_s: float, gate: float
) -> Iterator[tuple[float, np.ndarray]]:
    """
    Yield ``(level, window)`` for each sound louder than ``gate`` x the noise floor.

    ``next_chunk`` blocks until it returns the next ``HOP_S`` seconds of audio.
    ``window`` is ``window_s`` seconds with the sound in the middle; ``level`` is
    its loudness over the noise floor.
    """
    hops = max(1, int(round(window_s / 2 / HOP_S)))
    window = np.zeros(int(window_s * sr), np.float32)
    frame = int(RMS_FRAME_S * sr)
    sos = audio_utils.highpass_sos(sr)
    zi = signal.sosfilt_zi(sos) * 0.0
    noise_floor = None
    cooldown = 0

    def push(chunk: np.ndarray) -> None:
        nonlocal window
        window = np.concatenate([window[len(chunk):], chunk])

    while True:
        chunk = next_chunk()
        push(chunk)
        hp, zi = signal.sosfilt(sos, chunk, zi=zi)
        rms = audio_utils.short_time_rms(hp, frame)
        level = float(rms.max()) if len(rms) else 0.0
        if noise_floor is None:
            noise_floor = max(level, 1e-6)
        if cooldown > 0:
            cooldown -= 1
            continue
        if level > gate * noise_floor:
            # Wait half a window so the sound is in the middle of what is classified
            for _ in range(hops):
                push(next_chunk())
            yield level / noise_floor, window
            cooldown = hops
        else:
            noise_floor = max(1e-6, noise_floor + NOISE_FLOOR_ALPHA * (
                float(np.median(rms)) - noise_floor
            ))
