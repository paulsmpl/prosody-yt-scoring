import argparse
from pathlib import Path
import librosa
import numpy as np


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return float(max(minimum, min(maximum, value)))


def compute_tonality_score(path: Path) -> tuple[float, float, float]:
    y, sr = librosa.load(path, sr=22050, mono=True)
    if y.size == 0:
        return 0.0, 0.0, 0.0

    stft = librosa.stft(y)
    magnitude = np.abs(stft) ** 2
    freqs = librosa.fft_frequencies(sr=sr)

    high_band = (freqs >= 6000.0) & (freqs <= 21100.0)
    low_band = (freqs >= 1.0) & (freqs <= 70.0)

    high_energy = float(np.sum(magnitude[high_band, :]))
    low_energy = float(np.sum(magnitude[low_band, :]))
    total_energy = high_energy + low_energy

    if total_energy <= 0:
        return 0.0, high_energy, low_energy

    return clamp((high_energy / total_energy) * 100.0), high_energy, low_energy


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare tonality scores for two MP3 files.")
    parser.add_argument("file_a", help="First MP3 file path")
    parser.add_argument("file_b", help="Second MP3 file path")
    args = parser.parse_args()

    file_a = Path(args.file_a)
    file_b = Path(args.file_b)

    if not file_a.exists():
        raise SystemExit(f"File not found: {file_a}")
    if not file_b.exists():
        raise SystemExit(f"File not found: {file_b}")

    score_a, high_a, low_a = compute_tonality_score(file_a)
    score_b, high_b, low_b = compute_tonality_score(file_b)

    print(f"{file_a.name}: {score_a:.2f}% | high={high_a:.2e} low={low_a:.2e}")
    print(f"{file_b.name}: {score_b:.2f}% | high={high_b:.2e} low={low_b:.2e}")


if __name__ == "__main__":
    main()
