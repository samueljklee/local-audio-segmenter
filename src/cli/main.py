"""Transcript-driven CLI: transcribe with Whisper, merge by transcript gaps, export clips."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

from ..audio.loader import AudioLoader, AudioLoadError
from ..stt.module import STTModule

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Transcribe audio with Whisper, merge segments by transcript gaps, and export clips via ffmpeg.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with defaults
  %(prog)s audio.mp3

  # Custom segmentation parameters
  %(prog)s audio.mp3 --td-gap 5 --td-min-length 120

  # Use larger Whisper model for better accuracy
  %(prog)s audio.mp3 --whisper-model small

  # Verbose output for debugging
  %(prog)s audio.mp3 --verbose
        """,
    )
    parser.add_argument(
        "input_file",
        help="Input audio file to process",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=".",
        help="Output directory or file path base (default: current directory)",
    )
    parser.add_argument(
        "--whisper-model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Whisper model size for transcription (default: base)",
    )
    parser.add_argument(
        "--transcription-language",
        help="Language code for transcription (e.g., en, es, fr)",
    )

    # Transcript-driven segmentation options
    td_group = parser.add_argument_group("Transcript-driven segmentation options")
    td_group.add_argument(
        "--td-gap",
        type=float,
        default=3.0,
        metavar="SECONDS",
        help="Gap threshold for merging transcript segments (default: 3.0)",
    )
    td_group.add_argument(
        "--td-min-length",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="Minimum segment length before merging into neighbor (default: 60.0)",
    )
    td_group.add_argument(
        "--td-merge-bridges",
        action="store_true",
        default=True,
        help="Enable A-B-A bridge merging (default on)",
    )
    td_group.add_argument(
        "--td-no-merge-bridges",
        action="store_false",
        dest="td_merge_bridges",
        help="Disable A-B-A bridge merging",
    )
    td_group.add_argument(
        "--td-bridge-type",
        default="speech",
        choices=["speech", "music", "silence"],
        help="Bridge type to merge through (default: speech)",
    )
    td_group.add_argument(
        "--td-bridge-max-duration",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="Max bridge duration for A-B-A merge (default: 60.0)",
    )

    # Export options
    export_group = parser.add_argument_group("Export options")
    export_group.add_argument(
        "--td-export-dir",
        metavar="DIR",
        help="Output directory for per-segment clips (default: <output>/<name>_segments)",
    )
    export_group.add_argument(
        "--td-export-format",
        default="mp3",
        help="Clip format for export (default: mp3)",
    )
    export_group.add_argument(
        "--td-export-prefix",
        metavar="PREFIX",
        help="Filename prefix for exported clips (default: audio stem)",
    )
    export_group.add_argument(
        "--td-transcript-output",
        metavar="PATH",
        help="Path to save transcript JSON (default: <output>/<name>_transcript.json)",
    )
    export_group.add_argument(
        "--td-segments-output",
        metavar="PATH",
        help="Path to save merged segments JSON (default: <output>/<name>_segments.json)",
    )

    # Global options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    return parser.parse_args()


def validate_input_file(file_path: str, loader: AudioLoader) -> Path:
    """
    Validate that input file exists and is a valid audio file.

    Args:
        file_path: Path to input file
        loader: AudioLoader instance for validation

    Returns:
        Validated Path object

    Raises:
        ValueError: If validation fails
    """
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"Input file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Input path is not a file: {file_path}")

    suffix = path.suffix.lower()[1:]
    if suffix and suffix not in loader.get_supported_formats():
        raise ValueError(
            f"Unsupported audio format: .{suffix}. "
            f"Supported formats: {', '.join(loader.get_supported_formats())}"
        )

    # Try to validate the file can be loaded
    if not loader.validate_audio_file(path):
        raise ValueError(f"File is not a valid audio file: {file_path}")

    return path


def validate_output_path(output_path: str) -> Path:
    """
    Validate and prepare output path.

    Args:
        output_path: Output path string

    Returns:
        Validated Path object

    Raises:
        ValueError: If output path is invalid
    """
    output = Path(output_path)

    try:
        # Create directory if it doesn't exist
        if not output.suffix:
            output.mkdir(parents=True, exist_ok=True)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValueError(f"Cannot create output directory: {e}")

    return output


def validate_parameters(args: argparse.Namespace) -> None:
    """
    Validate CLI parameters.

    Args:
        args: Parsed arguments

    Raises:
        ValueError: If any parameter is invalid
    """
    # Validate transcript-driven parameters
    if args.td_gap < 0:
        raise ValueError("--td-gap must be non-negative")

    if args.td_min_length < 0:
        raise ValueError("--td-min-length must be non-negative")

    if args.td_bridge_max_duration < 0:
        raise ValueError("--td-bridge-max-duration must be non-negative")

    # Validate export format
    valid_formats = {"mp3", "wav", "flac", "ogg", "m4a", "aac"}
    if args.td_export_format.lower() not in valid_formats:
        raise ValueError(
            f"Invalid format '{args.td_export_format}'. "
            f"Must be one of: {', '.join(sorted(valid_formats))}"
        )


def run_transcript_driven_flow(
    audio_path: Path,
    output_path: Path,
    is_file_output: bool,
    args: argparse.Namespace,
) -> int:
    """
    Run the complete transcript-driven workflow.

    Args:
        audio_path: Path to input audio file
        output_path: Base output path
        is_file_output: Whether output is a file (vs directory)
        args: Parsed CLI arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    base_output = output_path.parent if is_file_output else output_path
    base_output.mkdir(parents=True, exist_ok=True)

    # Determine output paths
    transcript_path = (
        Path(args.td_transcript_output)
        if args.td_transcript_output
        else base_output / f"{audio_path.stem}_transcript.json"
    )
    segments_path = (
        Path(args.td_segments_output)
        if args.td_segments_output
        else base_output / f"{audio_path.stem}_segments.json"
    )
    export_dir = (
        Path(args.td_export_dir)
        if args.td_export_dir
        else base_output / f"{audio_path.stem}_segments"
    )
    export_prefix = args.td_export_prefix or audio_path.stem

    # Step 1: Transcribe
    logger.info("=" * 60)
    logger.info("STEP 1: Transcribing audio with Whisper")
    logger.info("=" * 60)

    stt = STTModule(model_size=args.whisper_model, language=args.transcription_language)

    try:
        transcript = stt.transcribe_file(
            str(audio_path),
            beam_size=5,
            best_of=5,
            temperature=0.0,
            no_speech_threshold=0.6,
        )

        # Save transcript
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        with transcript_path.open("w", encoding="utf-8") as f:
            json.dump(transcript.to_dict(), f, indent=2)

        logger.info(f"Transcript saved to {transcript_path}")
        logger.info(f"  - {len(transcript.segments)} segments")
        logger.info(f"  - {transcript.word_count} words")
        logger.info(f"  - language: {transcript.language or 'unknown'}")

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return 1

    # Step 2: Build segments
    logger.info("")
    logger.info("=" * 60)
    logger.info("STEP 2: Building segments from transcript")
    logger.info("=" * 60)

    try:
        from tools.build_segments_from_transcript import build_segments
    except ImportError as exc:
        logger.error(f"Failed to import segment builder: {exc}")
        return 1

    try:
        segments = build_segments(
            transcript_path=transcript_path,
            audio_path=audio_path,
            gap_threshold=args.td_gap,
            min_length=args.td_min_length,
            merge_bridges=args.td_merge_bridges,
            bridge_type=args.td_bridge_type,
            bridge_max_duration=args.td_bridge_max_duration,
        )

        # Save segments
        segments_path.parent.mkdir(parents=True, exist_ok=True)
        with segments_path.open("w", encoding="utf-8") as f:
            json.dump({"segments": segments}, f, indent=2)

        logger.info(f"Merged segments saved to {segments_path}")
        logger.info(f"  - {len(segments)} segments")

        # Count by type
        type_counts = {}
        for seg in segments:
            seg_type = seg.get("type", "unknown")
            type_counts[seg_type] = type_counts.get(seg_type, 0) + 1

        for seg_type, count in sorted(type_counts.items()):
            logger.info(f"  - {seg_type}: {count}")

    except Exception as e:
        logger.error(f"Segment building failed: {e}")
        return 1

    # Step 3: Export clips
    logger.info("")
    logger.info("=" * 60)
    logger.info("STEP 3: Exporting audio clips")
    logger.info("=" * 60)

    try:
        from tools.export_segments import export_segments
    except ImportError as exc:
        logger.error(f"Failed to import exporter: {exc}")
        return 1

    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        export_segments(audio_path, segments, export_dir, args.td_export_format, export_prefix)

        logger.info(f"Exported clips to {export_dir}")

    except Exception as e:
        logger.error(f"Export failed: {e}")
        return 1

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Input: {audio_path.name}")
    logger.info(f"Transcript: {transcript_path}")
    logger.info(f"Segments: {segments_path}")
    logger.info(f"Clips: {export_dir}/")
    logger.info("=" * 60)

    return 0


def main() -> int:
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        # Create audio loader
        loader = AudioLoader()

        # Validate input file
        try:
            audio_path = validate_input_file(args.input_file, loader)
        except ValueError as e:
            logger.error(f"Input validation error: {e}")
            return 1

        # Validate output path
        try:
            output_path = validate_output_path(args.output)
            is_file_output = output_path.suffix != ""
        except ValueError as e:
            logger.error(f"Output validation error: {e}")
            return 1

        # Validate parameters
        try:
            validate_parameters(args)
        except ValueError as e:
            logger.error(f"Parameter validation error: {e}")
            return 1

        # Log configuration
        logger.info(f"Processing: {audio_path}")
        if args.verbose:
            logger.info(f"Configuration:")
            logger.info(f"  Whisper model: {args.whisper_model}")
            logger.info(f"  Gap threshold: {args.td_gap}s")
            logger.info(f"  Min length: {args.td_min_length}s")
            logger.info(f"  Merge bridges: {args.td_merge_bridges}")
            logger.info(f"  Export format: {args.td_export_format}")

        # Run workflow
        return run_transcript_driven_flow(audio_path, output_path, is_file_output, args)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 130

    except AudioLoadError as e:
        logger.error(f"Audio loading error: {e}")
        return 1

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
