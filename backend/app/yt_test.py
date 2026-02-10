import argparse
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str]) -> None:
    print("\n$", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    result.check_returncode()


def main() -> None:
    parser = argparse.ArgumentParser(description="Test yt-dlp with cookies.")
    parser.add_argument("url", help="YouTube URL to test")
    parser.add_argument("--cookies", default="backend/app/storage/cookies.txt")
    parser.add_argument("--client", default="android", choices=["android", "web", "mweb", "ios"])
    parser.add_argument("--list", action="store_true", help="List formats only")
    args = parser.parse_args()

    cookies_path = Path(args.cookies)
    if not cookies_path.exists():
        raise SystemExit(f"Cookies file not found: {cookies_path}")

    base = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--cookies",
        str(cookies_path),
        "--extractor-args",
        f"youtube:player_client={args.client}",
    ]

    if args.list:
        run_cmd(base + ["--list-formats", args.url])
        return

    run_cmd(base + ["-f", "bestaudio/best", "-o", "%(title)s.%(ext)s", args.url])


if __name__ == "__main__":
    main()
