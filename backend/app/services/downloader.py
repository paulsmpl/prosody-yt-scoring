from pathlib import Path
import subprocess


def download_audio(url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = output_dir / "source.%(ext)s"

    cmd = [
        "yt-dlp",
        "-f",
        "bestaudio/best",
        "--no-playlist",
        "-o",
        str(output_template),
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Téléchargement échoué.")

    candidates = list(output_dir.glob("source.*"))
    if not candidates:
        raise RuntimeError("Fichier audio introuvable après téléchargement.")

    return candidates[0]
