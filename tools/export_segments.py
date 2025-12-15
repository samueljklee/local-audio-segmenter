"""
Export audio clips for each segment using ffmpeg.

Usage:
  python -m tools.export_segments \
    --audio /path/to/source.mp3 \
    --segments segments_from_whisper.json \
    --outdir output_segments \
    --format mp3
"""

import argparse
import json
import subprocess
from pathlib import Path
from typing import List, Dict


def load_segments(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    segments = data.get("segments", []) if isinstance(data, dict) else data
    return segments


def export_segments(
    audio_path: Path,
    segments: List[Dict],
    outdir: Path,
    fmt: str,
    prefix: str,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    for idx, seg in enumerate(segments, 1):
        start = float(seg["start"])
        end = float(seg["end"])
        duration = max(0.0, end - start)
        seg_type = seg.get("type", "segment")

        outfile = outdir / f"{prefix}_{idx:02d}_{seg_type}.{fmt}"

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.2f}",
            "-i",
            str(audio_path),
            "-t",
            f"{duration:.2f}",
            "-c",
            "copy",
            str(outfile),
        ]
        print(f"[{idx}/{len(segments)}] {outfile.name} ({seg_type}) {start:.2f}-{end:.2f}s")
        subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description="Export audio clips for each segment.")
    ap.add_argument("--audio", required=True, help="Source audio file")
    ap.add_argument("--segments", required=True, help="Segments JSON (with start/end/type)")
    ap.add_argument("--outdir", required=True, help="Output directory for clips")
    ap.add_argument("--format", default="mp3", help="Output audio format (default: mp3)")
    ap.add_argument(
        "--prefix",
        default="segment",
        help="Filename prefix (default: segment)",
    )
    args = ap.parse_args()

    audio_path = Path(args.audio)
    segments_path = Path(args.segments)
    outdir = Path(args.outdir)

    segments = load_segments(segments_path)
    export_segments(audio_path, segments, outdir, args.format, args.prefix)


if __name__ == "__main__":
    main()
