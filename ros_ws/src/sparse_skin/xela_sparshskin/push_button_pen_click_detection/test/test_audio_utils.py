import numpy as np

from push_button_pen_click_detection import audio_utils

SR = 48000


def _click(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(int(0.03 * SR)) / SR
    return (rng.standard_normal(len(t)) * np.exp(-t / 0.003)
            + 0.6 * np.sin(2 * np.pi * 4200 * t) * np.exp(-t / 0.006))


def _noise(n: int, seed: int) -> np.ndarray:
    return 0.003 * np.random.default_rng(seed).standard_normal(n)


def _template() -> np.ndarray:
    rec = _noise(2 * SR, 0)
    rec[30000:30000 + 1440] += 0.5 * _click(1)
    return audio_utils.clean(rec[29000:32500], SR)


def test_clean_is_normalized():
    y = audio_utils.clean(0.1 * _click(1) + 0.2, SR)
    assert abs(np.max(np.abs(y)) - 0.9) < 0.05
    assert y[0] == 0.0 and y[-1] == 0.0


def test_similarity_click_vs_noise():
    template = audio_utils.features(_template(), SR)
    window = 3000 + 2400
    live = _noise(window, 5)
    live[1000:1000 + 1440] += 0.4 * _click(1)
    assert audio_utils.similarity(template, audio_utils.features(live, SR)) > 0.7
    noise = audio_utils.features(_noise(window, 6), SR)
    assert audio_utils.similarity(template, noise) < 0.3


def test_wav_roundtrip(tmp_path):
    x = audio_utils.clean(_click(2), SR)
    path = str(tmp_path / "click.wav")
    audio_utils.save_wav(path, x, SR)
    y, sr = audio_utils.load_wav(path)
    assert sr == SR
    assert np.allclose(x, y, atol=1e-3)
