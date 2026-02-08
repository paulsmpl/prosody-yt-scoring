from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import librosa


@dataclass
class ProsodyScores:
    melody_score: float
    frequency_score: float
    combined_score: float


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return float(max(minimum, min(maximum, value)))


def analyze_prosody(mp3_path: str, weight_melody: float, weight_frequency: float) -> ProsodyScores:
    y, sr = librosa.load(mp3_path, sr=22050, mono=True)

    if y.size == 0:
        return ProsodyScores(0.0, 0.0, 0.0)

    f0, _, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
    )

    if f0 is None:
        return ProsodyScores(0.0, 0.0, 0.0)

    voiced = f0[~np.isnan(f0)]
    if voiced.size == 0:
        return ProsodyScores(0.0, 0.0, 0.0)

    mean_f0 = float(np.mean(voiced))
    std_f0 = float(np.std(voiced))

    coeff_var = std_f0 / max(mean_f0, 1e-6)
    melody_score = _clamp((coeff_var / 0.35) * 100.0)

    target_f0 = 180.0
    freq_distance = abs(mean_f0 - target_f0) / target_f0
    frequency_score = _clamp(100.0 - (freq_distance * 100.0))

    combined = _clamp((melody_score * weight_melody) + (frequency_score * weight_frequency))

    return ProsodyScores(
        melody_score=round(melody_score, 2),
        frequency_score=round(frequency_score, 2),
        combined_score=round(combined, 2),
    )
