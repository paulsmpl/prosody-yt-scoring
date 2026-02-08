from pathlib import Path
import os
import subprocess


def download_audio(url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = output_dir / "source.%(ext)s"

    cookies_path = os.getenv("COOKIES_PATH")
    client = "android"
    if cookies_path and Path(cookies_path).exists():
        client = "web"

    cmd = [
        "yt-dlp",
        "-f",
        "bestaudio/best",
        "--no-playlist",
        "--extractor-args",
        f"youtube:player_client={client}",
        "--print",
        "after_move:filepath",
        "-o",
        str(output_template),
        url,
    ]

    if cookies_path and Path(cookies_path).exists():
        cmd.extend(["--cookies", cookies_path])

    extra_args = os.getenv("YTDLP_ARGS")
    if extra_args:
        cmd.extend(extra_args.split())

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Téléchargement échoué.")

    stdout_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for line in reversed(stdout_lines):
        path = Path(line)
        if path.exists():
            return path

    candidates = list(output_dir.glob("source.*"))
    if not candidates:
        raise RuntimeError("Fichier audio introuvable après téléchargement.")

    return candidates[0]
