import argparse
import subprocess
import tempfile
from pathlib import Path
import librosa
import numpy as np


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return float(max(minimum, min(maximum, value)))


def get_audio_duration_seconds(input_path: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def extract_segment_to_mp3(input_path: Path, output_path: Path, start_seconds: int, duration_seconds: int) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_seconds),
        "-t",
        str(duration_seconds),
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ar",
        "44100",
        "-ac",
        "1",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Audio extraction failed.")


def compute_tonality_score(path: Path, high_min: float, high_max: float, low_max: float) -> tuple[float, float, float]:
    y, sr = librosa.load(path, sr=22050, mono=True)
    if y.size == 0:
        return 0.0, 0.0, 0.0

    stft = librosa.stft(y)
    magnitude = np.abs(stft) ** 2
    freqs = librosa.fft_frequencies(sr=sr)

    high_band = (freqs >= high_min) & (freqs <= high_max)
    low_band = (freqs >= 1.0) & (freqs <= low_max)

    high_band_energy = np.sum(magnitude[high_band, :], axis=0)
    high_energy = float(np.mean(high_band_energy))
    low_energy = float(np.sum(magnitude[low_band, :]))

    if high_energy <= 0:
        return 0.0, high_energy, low_energy

    high_energy_db = 10.0 * np.log10(high_energy + 1e-9)
    min_db = -10.0
    max_db = 5.0
    score = clamp(((high_energy_db - min_db) / (max_db - min_db)) * 100.0)

    return score, high_energy, low_energy


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare tonality scores for two MP3 files.")
    parser.add_argument("file_a", help="First MP3 file path")
    parser.add_argument("file_b", help="Second MP3 file path")
    parser.add_argument("--start-minute", type=int, default=0)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--high-threshold", type=float, default=10000.0)
    parser.add_argument("--high-max", type=float, default=21100.0)
    parser.add_argument("--low-max", type=float, default=70.0)
    args = parser.parse_args()

    file_a = Path(args.file_a)
    file_b = Path(args.file_b)

    if not file_a.exists():
        raise SystemExit(f"File not found: {file_a}")
    if not file_b.exists():
        raise SystemExit(f"File not found: {file_b}")

    def analyze_file(path: Path) -> tuple[float, float, float, int, int]:
        start_seconds = args.start_minute * 60
        duration = get_audio_duration_seconds(path)
        if duration is not None and duration < (start_seconds + args.duration):
            start_seconds = 0
        end_minute = (start_seconds // 60) + 1

        with tempfile.TemporaryDirectory() as tmp:
            segment = Path(tmp) / "segment.mp3"
            extract_segment_to_mp3(path, segment, start_seconds, args.duration)
            score, high_energy, low_energy = compute_tonality_score(
                segment,
                high_min=args.high_threshold,
                high_max=args.high_max,
                low_max=args.low_max,
            )
            return score, high_energy, low_energy, int(start_seconds // 60), int(end_minute)

    score_a, high_a, low_a, start_a, end_a = analyze_file(file_a)
    score_b, high_b, low_b, start_b, end_b = analyze_file(file_b)

    high_a_db = 10.0 * np.log10(high_a + 1e-9)
    high_b_db = 10.0 * np.log10(high_b + 1e-9)

    print(
        f"{file_a.name}: {score_a:.2f}% | high={high_a:.2e} (db={high_a_db:.2f}) low={low_a:.2e} | segment={start_a}->{end_a} min"
    )
    print(
        f"{file_b.name}: {score_b:.2f}% | high={high_b:.2e} (db={high_b_db:.2f}) low={low_b:.2e} | segment={start_b}->{end_b} min"
    )


if __name__ == "__main__":
    main()
