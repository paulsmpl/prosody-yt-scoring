import argparse
import subprocess
import tempfile
from pathlib import Path
import librosa
import numpy as np


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return float(max(minimum, min(maximum, value)))


def compute_melody_score(y: np.ndarray, sr: int, max_cv: float) -> float:
    f0, _, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
    )

    if f0 is None:
        return 0.0

    voiced = f0[~np.isnan(f0)]
    if voiced.size == 0:
        return 0.0

    mean_f0 = float(np.mean(voiced))
    std_f0 = float(np.std(voiced))
    coeff_var = std_f0 / max(mean_f0, 1e-6)
    return clamp((coeff_var / max_cv) * 100.0)


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


def compute_tonality_score(
    path: Path,
    high_min: float,
    high_max: float,
    mid_min: float,
    mid_max: float,
    mid_weight: float,
    low_max: float,
    min_db: float,
    max_db: float,
) -> tuple[float, float, float, float]:
    y, sr = librosa.load(path, sr=22050, mono=True)
    if y.size == 0:
        return 0.0, 0.0, 0.0, 0.0

    stft = librosa.stft(y)
    magnitude = np.abs(stft) ** 2
    freqs = librosa.fft_frequencies(sr=sr)

    high_band = (freqs >= high_min) & (freqs <= high_max)
    mid_band = (freqs >= mid_min) & (freqs < high_min)
    low_band = (freqs >= 1.0) & (freqs <= low_max)

    high_band_energy = np.sum(magnitude[high_band, :], axis=0)
    mid_band_energy = np.sum(magnitude[mid_band, :], axis=0)

    high_energy = float(np.mean(high_band_energy))
    mid_energy = float(np.mean(mid_band_energy))
    low_energy = float(np.sum(magnitude[low_band, :]))

    weighted_energy = high_energy + (mid_weight * mid_energy)
    if weighted_energy <= 0:
        return 0.0, high_energy, mid_energy, low_energy

    high_energy_db = 10.0 * np.log10(weighted_energy + 1e-9)
    score = clamp(((high_energy_db - min_db) / (max_db - min_db)) * 100.0)

    return score, high_energy, mid_energy, low_energy


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare tonality scores for two MP3 files.")
    parser.add_argument("paths", nargs="+", help="MP3 file(s) or a folder path")
    parser.add_argument("--start-minute", type=int, default=0)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--high-threshold", type=float, default=10000.0)
    parser.add_argument("--high-max", type=float, default=21100.0)
    parser.add_argument("--mid-threshold", type=float, default=4000.0)
    parser.add_argument("--mid-weight", type=float, default=0.1)
    parser.add_argument("--low-max", type=float, default=70.0)
    parser.add_argument("--min-db", type=float, default=0.0)
    parser.add_argument("--max-db", type=float, default=20.0)
    parser.add_argument("--melody-max-cv", type=float, default=0.6)
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.paths]
    if len(input_paths) == 1 and input_paths[0].is_dir():
        files = sorted(input_paths[0].glob("*.mp3"))
    else:
        files = input_paths

    if not files:
        raise SystemExit("No MP3 files found.")

    for path in files:
        if not path.exists():
            raise SystemExit(f"File not found: {path}")

    def analyze_file(path: Path) -> tuple[float, float, float, int, int]:
        start_seconds = args.start_minute * 60
        duration = get_audio_duration_seconds(path)
        if duration is not None and duration < (start_seconds + args.duration):
            start_seconds = 0
        end_minute = (start_seconds // 60) + 1

        with tempfile.TemporaryDirectory() as tmp:
            segment = Path(tmp) / "segment.mp3"
            extract_segment_to_mp3(path, segment, start_seconds, args.duration)
            score, high_energy, mid_energy, low_energy = compute_tonality_score(
                segment,
                high_min=args.high_threshold,
                high_max=args.high_max,
                mid_min=args.mid_threshold,
                mid_max=args.high_threshold,
                mid_weight=args.mid_weight,
                low_max=args.low_max,
                min_db=args.min_db,
                max_db=args.max_db,
            )
            y_segment, sr_segment = librosa.load(segment, sr=22050, mono=True)
            melody = compute_melody_score(y_segment, sr_segment, args.melody_max_cv)
            return score, high_energy, mid_energy, low_energy, melody, int(start_seconds // 60), int(end_minute)

    for path in files:
        score, high, mid, low, melody, start_min, end_min = analyze_file(path)
        weighted_energy = high + (args.mid_weight * mid)
        weighted_db = 10.0 * np.log10(weighted_energy + 1e-9)
        print(
            f"{path.name}: tonality={score:.2f}% melody={melody:.2f}% | high={high:.2e} mid={mid:.2e} (w={args.mid_weight}) db={weighted_db:.2f} low={low:.2e} | segment={start_min}->{end_min} min"
        )


if __name__ == "__main__":
    main()
