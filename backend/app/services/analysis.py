from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import librosa


@dataclass
class ProsodyScores:
    melody_score: float
    tonality_score: float


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return float(max(minimum, min(maximum, value)))


def analyze_prosody(mp3_path: str) -> ProsodyScores:
    y, sr = librosa.load(mp3_path, sr=22050, mono=True)

    if y.size == 0:
        return ProsodyScores(0.0, 0.0)

    f0, _, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
    )

    if f0 is None:
        return ProsodyScores(0.0, 0.0)

    voiced = f0[~np.isnan(f0)]
    if voiced.size == 0:
        return ProsodyScores(0.0, 0.0)

    mean_f0 = float(np.mean(voiced))
    std_f0 = float(np.std(voiced))

    coeff_var = std_f0 / max(mean_f0, 1e-6)
    melody_score = _clamp((coeff_var / 0.35) * 100.0)

    stft = librosa.stft(y)
    magnitude = np.abs(stft) ** 2
    freqs = librosa.fft_frequencies(sr=sr)

    high_band = (freqs >= 10000.0) & (freqs <= 21100.0)
    low_band = (freqs >= 1.0) & (freqs <= 70.0)

    high_band_energy = np.sum(magnitude[high_band, :], axis=0)
    high_energy = float(np.mean(high_band_energy))

    if high_energy <= 0:
        tonality_score = 0.0
    else:
        high_energy_db = 10.0 * np.log10(high_energy + 1e-9)
        min_db = -10.0
        max_db = 5.0
        tonality_score = _clamp(((high_energy_db - min_db) / (max_db - min_db)) * 100.0)

    return ProsodyScores(
        melody_score=round(melody_score, 2),
        tonality_score=round(tonality_score, 2),
    )
