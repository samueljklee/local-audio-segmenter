"""Transcript-driven CLI: transcribe with Whisper, merge by transcript gaps, export clips."""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from ..audio.loader import AudioLoader, AudioLoadError
from ..stt.module import STTModule


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe audio with Whisper, merge segments by transcript gaps, and export clips via ffmpeg.",
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
    parser.add_argument(
        "--td-gap",
        type=float,
        default=3.0,
        help="Gap threshold (seconds) for merging transcript segments (default: 3.0)",
    )
    parser.add_argument(
        "--td-min-length",
        type=float,
        default=60.0,
        help="Minimum segment length (seconds) before merging into neighbor",
    )
    parser.add_argument(
        "--td-merge-bridges",
        action="store_true",
        default=True,
        help="Enable A-B-A bridge merging (default on)",
    )
    parser.add_argument(
        "--td-bridge-type",
        default="speech",
        help="Bridge type to merge through (default: speech)",
    )
    parser.add_argument(
        "--td-bridge-max-duration",
        type=float,
        default=60.0,
        help="Max bridge duration (seconds) for A-B-A merge (default: 60.0)",
    )

    # Export options
    parser.add_argument(
        "--td-export-dir",
        help="Output directory for per-segment clips (default: <output>/<name>_segments)",
    )
    parser.add_argument(
        "--td-export-format",
        default="mp3",
        help="Clip format for export (default: mp3)",
    )
    parser.add_argument(
        "--td-export-prefix",
        help="Filename prefix for exported clips (default: audio stem)",
    )
    parser.add_argument(
        "--td-transcript-output",
        help="Path to save transcript JSON (default: <output>/<name>_transcript.json)",
    )
    parser.add_argument(
        "--td-segments-output",
        help="Path to save merged segments JSON (default: <output>/<name>_segments.json)",
    )

    return parser.parse_args()


def validate_input_file(file_path: str, loader: AudioLoader) -> Path:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {file_path}")

    suffix = path.suffix.lower().lstrip(".")
    if suffix and suffix not in loader.get_supported_formats():
        raise ValueError(f"Unsupported audio format: {suffix}")
    return path


def validate_output_path(output_path: str) -> Path:
    output = Path(output_path)
    if output.suffix:
        output.parent.mkdir(parents=True, exist_ok=True)
    else:
        output.mkdir(parents=True, exist_ok=True)
    return output


def run_transcript_driven_flow(
    audio_path: Path,
    output_path: Path,
    is_file_output: bool,
    args: argparse.Namespace,
) -> int:
    base_output = output_path.parent if is_file_output else output_path
    base_output.mkdir(parents=True, exist_ok=True)

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

    print(f"Transcribing with Whisper ({args.whisper_model})...")
    stt = STTModule(model_size=args.whisper_model, language=args.transcription_language)
    transcript = stt.transcribe_file(
        str(audio_path),
        beam_size=5,
        best_of=5,
        temperature=0.0,
        no_speech_threshold=0.6,
    )

    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    with transcript_path.open("w", encoding="utf-8") as f:
        json.dump(transcript.to_dict(), f, indent=2)
    print(f"Transcript saved to {transcript_path}")

    try:
        from tools.build_segments_from_transcript import build_segments
    except Exception as exc:
        print(f"Failed to import transcript segment builder: {exc}", file=sys.stderr)
        return 1

    segments = build_segments(
        transcript_path=transcript_path,
        audio_path=audio_path,
        gap_threshold=args.td_gap,
        min_length=args.td_min_length,
        merge_bridges=args.td_merge_bridges,
        bridge_type=args.td_bridge_type,
        bridge_max_duration=args.td_bridge_max_duration,
    )
    segments_path.parent.mkdir(parents=True, exist_ok=True)
    with segments_path.open("w", encoding="utf-8") as f:
        json.dump({"segments": segments}, f, indent=2)
    print(f"Merged segments saved to {segments_path} ({len(segments)} segments)")

    try:
        from tools.export_segments import export_segments
    except Exception as exc:
        print(f"Failed to import export helper: {exc}", file=sys.stderr)
        return 1

    export_dir.mkdir(parents=True, exist_ok=True)
    export_segments(audio_path, segments, export_dir, args.td_export_format, export_prefix)
    print(f"Exported clips to {export_dir}")
    return 0


def main() -> int:
    try:
        args = parse_arguments()
        loader = AudioLoader()

        try:
            audio_path = validate_input_file(args.input_file, loader)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        try:
            output_path = validate_output_path(args.output)
            is_file_output = output_path.suffix != ""
        except Exception as e:
            print(f"Error preparing output path: {e}", file=sys.stderr)
            return 1

        print(f"Processing: {audio_path}")
        return run_transcript_driven_flow(audio_path, output_path, is_file_output, args)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except AudioLoadError as e:
        print(f"Audio loading error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
