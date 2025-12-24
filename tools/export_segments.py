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
import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


# =============================================================================
# Error Classes
# =============================================================================

class ExportError(Exception):
    """Base exception for export errors."""
    pass


class SegmentLoadError(ExportError):
    """Raised when segments file cannot be loaded."""
    pass


class FFMpegError(ExportError):
    """Raised when ffmpeg command fails."""
    pass


class ValidationError(ExportError):
    """Raised when input validation fails."""
    pass


# =============================================================================
# Validation
# =============================================================================

def validate_segments_path(segments_path: Path) -> None:
    """Validate that segments file exists."""
    if not segments_path.exists():
        raise ValidationError(f"Segments file not found: {segments_path}")

    if not segments_path.is_file():
        raise ValidationError(f"Segments path is not a file: {segments_path}")


def validate_audio_path(audio_path: Path) -> None:
    """Validate that audio file exists."""
    if not audio_path.exists():
        raise ValidationError(f"Audio file not found: {audio_path}")

    if not audio_path.is_file():
        raise ValidationError(f"Audio path is not a file: {audio_path}")


def validate_output_format(fmt: str) -> None:
    """Validate output format."""
    valid_formats = {"mp3", "wav", "flac", "ogg", "m4a", "aac"}
    if fmt.lower() not in valid_formats:
        raise ValidationError(
            f"Invalid format '{fmt}'. Must be one of: {', '.join(sorted(valid_formats))}"
        )


def validate_ffmpeg_available() -> None:
    """Check if ffmpeg is available on PATH."""
    if not shutil.which("ffmpeg"):
        raise ValidationError(
            "ffmpeg not found on PATH. Please install ffmpeg:\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  Windows: Download from https://ffmpeg.org/download.html"
        )


# =============================================================================
# Segment Loading
# =============================================================================

def load_segments(path: Path) -> List[Dict]:
    """
    Load and validate segments JSON file.

    Args:
        path: Path to segments JSON file

    Returns:
        List of segment dictionaries with start/end/type fields

    Raises:
        SegmentLoadError: If file cannot be loaded or is invalid
    """
    logger.debug(f"Loading segments from {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise SegmentLoadError(f"Invalid JSON in {path}: {e}")
    except IOError as e:
        raise SegmentLoadError(f"Failed to read {path}: {e}")

    # Handle different formats
    if isinstance(data, dict) and "segments" in data:
        segments = data["segments"]
    elif isinstance(data, list):
        segments = data
    else:
        raise SegmentLoadError(
            f"Unrecognized format in {path}. "
            f"Expected dict with 'segments' key or list of segments."
        )

    if not isinstance(segments, list):
        raise SegmentLoadError(
            f"Segments must be a list, got {type(segments).__name__}"
        )

    # Validate segments
    validated = []
    for i, seg in enumerate(segments):
        try:
            start = float(seg.get("start", 0))
            end = float(seg.get("end", 0))
            seg_type = seg.get("type", "segment")

            if end <= start:
                logger.warning(f"Segment {i}: end ({end}) <= start ({start}), skipping")
                continue

            if start < 0:
                logger.warning(f"Segment {i}: negative start time, skipping")
                continue

            validated.append({
                "start": start,
                "end": end,
                "type": seg_type
            })
        except (ValueError, TypeError) as e:
            logger.warning(f"Segment {i}: invalid data: {e}, skipping")
            continue

    if not validated:
        raise SegmentLoadError(f"No valid segments found in {path}")

    logger.info(f"Loaded {len(validated)} valid segments from {path}")
    return validated


# =============================================================================
# Export Functions
# =============================================================================

def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available."""
    return shutil.which("ffmpeg") is not None


def export_segment(
    audio_path: Path,
    segment: Dict,
    output_path: Path,
    idx: int,
    total: int,
    fmt: str,
    verbose: bool = False,
) -> bool:
    """
    Export a single segment using ffmpeg.

    Args:
        audio_path: Source audio file
        segment: Segment dict with start/end/type
        output_path: Output file path
        idx: Segment index (for logging)
        total: Total number of segments (for logging)
        fmt: Output format
        verbose: Whether to show ffmpeg output

    Returns:
        True if export succeeded, False otherwise

    Raises:
        FFMpegError: If ffmpeg command fails
    """
    start = float(segment["start"])
    end = float(segment["end"])
    duration = max(0.0, end - start)
    seg_type = segment.get("type", "segment")

    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output files
        "-ss", f"{start:.3f}",  # Start time
        "-i", str(audio_path),  # Input file
        "-t", f"{duration:.3f}",  # Duration
        "-c", "copy",  # Copy codec (no re-encoding)
        str(output_path),
    ]

    # Log progress
    logger.info(f"[{idx}/{total}] Exporting: {output_path.name} ({seg_type}) {start:.2f}-{end:.2f}s")

    try:
        # Run ffmpeg
        if verbose:
            # Show ffmpeg output in verbose mode
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=False,
                text=True
            )
        else:
            # Suppress ffmpeg output in normal mode
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg failed for {output_path.name}: {e}")
        if verbose and e.stderr:
            logger.error(f"ffmpeg stderr: {e.stderr}")
        raise FFMpegError(f"Failed to export {output_path.name}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error exporting {output_path.name}: {e}")
        raise FFMpegError(f"Failed to export {output_path.name}: {e}")


def export_segments(
    audio_path: Path,
    segments: List[Dict],
    outdir: Path,
    fmt: str,
    prefix: str,
    verbose: bool = False,
) -> List[Path]:
    """
    Export all segments to individual audio files.

    Args:
        audio_path: Source audio file path
        segments: List of segment dicts with start/end/type
        outdir: Output directory path
        fmt: Output audio format
        prefix: Filename prefix for output files
        verbose: Whether to show verbose output

    Returns:
        List of paths to exported files

    Raises:
        ExportError: If export fails
    """
    logger.info(f"Exporting {len(segments)} segments to {outdir}")

    # Create output directory
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ExportError(f"Failed to create output directory {outdir}: {e}")

    exported_paths = []
    failed = []

    for idx, seg in enumerate(segments, 1):
        start = float(seg["start"])
        end = float(seg["end"])
        seg_type = seg.get("type", "segment")

        # Generate output filename
        outfile = outdir / f"{prefix}_{idx:02d}_{seg_type}.{fmt}"

        try:
            export_segment(audio_path, seg, outfile, idx, len(segments), fmt, verbose)
            exported_paths.append(outfile)
        except FFMpegError:
            failed.append((idx, outfile))
            continue

    # Summary
    logger.info(f"Exported {len(exported_paths)} segments successfully")

    if failed:
        logger.warning(f"Failed to export {len(failed)} segments:")
        for idx, path in failed:
            logger.warning(f"  Segment {idx}: {path.name}")

    return exported_paths


# =============================================================================
# CLI
# =============================================================================

def main():
    """Main CLI entry point."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    ap = argparse.ArgumentParser(
        description="Export audio clips for each segment using ffmpeg."
    )
    ap.add_argument("--audio", required=True, help="Source audio file")
    ap.add_argument("--segments", required=True, help="Segments JSON (with start/end/type)")
    ap.add_argument("--outdir", required=True, help="Output directory for clips")
    ap.add_argument("--format", default="mp3", help="Output audio format (default: mp3)")
    ap.add_argument(
        "--prefix",
        default="segment",
        help="Filename prefix (default: segment)",
    )
    ap.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output (show ffmpeg output).",
    )

    args = ap.parse_args()

    # Set verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Validate inputs
        validate_ffmpeg_available()

        audio_path = Path(args.audio)
        validate_audio_path(audio_path)

        segments_path = Path(args.segments)
        validate_segments_path(segments_path)

        validate_output_format(args.format)

        outdir = Path(args.outdir)

        # Load segments
        segments = load_segments(segments_path)

        # Export
        export_segments(
            audio_path=audio_path,
            segments=segments,
            outdir=outdir,
            fmt=args.format,
            prefix=args.prefix,
            verbose=args.verbose,
        )

        print(f"Exported {len(segments)} segments to {outdir}")

    except (ValidationError, SegmentLoadError, FFMpegError, ExportError) as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
