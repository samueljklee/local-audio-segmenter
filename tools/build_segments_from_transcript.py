"""
Build coarse segments from a timestamped transcript (e.g., superwhisper JSON/SRT).

Usage:
  python -m tools.build_segments_from_transcript --transcript superwhisper.json --audio /path/to/audio.wav --gap 8 --min-length 180 --output segments.json

Inputs:
  - Transcript JSON with segment-level timestamps (start, end, text).
  - Optional audio path to run a simple VAD/silence pass to classify non-speech gaps.

Outputs:
  - segments.json with start/end/type and merged boundaries suitable for ffmpeg cropping.
  - Optional ffmpeg command suggestions printed to stdout.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

try:
    from pydub import AudioSegment as PydubAudio
except Exception:
    PydubAudio = None  # type: ignore

logger = logging.getLogger(__name__)


# =============================================================================
# Error Classes
# =============================================================================

class SegmentBuilderError(Exception):
    """Base exception for segment builder errors."""
    pass


class TranscriptLoadError(SegmentBuilderError):
    """Raised when transcript file cannot be loaded."""
    pass


class AudioLoadError(SegmentBuilderError):
    """Raised when audio file cannot be loaded for energy classification."""
    pass


class ValidationError(SegmentBuilderError):
    """Raised when input validation fails."""
    pass


# =============================================================================
# Input Validation
# =============================================================================

def validate_positive_float(value: float, name: str) -> None:
    """Validate that a float value is positive."""
    if value < 0:
        raise ValidationError(f"{name} must be non-negative, got {value}")


def validate_gap_threshold(gap_threshold: float) -> None:
    """Validate gap threshold parameter."""
    validate_positive_float(gap_threshold, "gap_threshold")


def validate_min_length(min_length: float) -> None:
    """Validate minimum segment length parameter."""
    validate_positive_float(min_length, "min_length")


def validate_bridge_max_duration(max_duration: float) -> None:
    """Validate bridge max duration parameter."""
    validate_positive_float(max_duration, "bridge_max_duration")


def validate_bridge_type(bridge_type: str) -> None:
    """Validate bridge type parameter."""
    valid_types = {"speech", "music", "silence"}
    if bridge_type not in valid_types:
        raise ValidationError(
            f"bridge_type must be one of {valid_types}, got '{bridge_type}'"
        )


def validate_transcript_path(transcript_path: Path) -> None:
    """Validate that transcript file exists."""
    if not transcript_path.exists():
        raise ValidationError(f"Transcript file not found: {transcript_path}")

    if not transcript_path.is_file():
        raise ValidationError(f"Transcript path is not a file: {transcript_path}")


def validate_audio_path(audio_path: Optional[Path]) -> None:
    """Validate audio file path if provided."""
    if audio_path is not None:
        if not audio_path.exists():
            raise ValidationError(f"Audio file not found: {audio_path}")

        if not audio_path.is_file():
            raise ValidationError(f"Audio path is not a file: {audio_path}")


# =============================================================================
# Transcript Loading
# =============================================================================

def load_transcript(path: Path) -> List[Dict[str, Any]]:
    """
    Load and validate transcript JSON file.

    Args:
        path: Path to transcript JSON file

    Returns:
        List of transcript segments with start, end, text fields

    Raises:
        TranscriptLoadError: If file cannot be loaded or parsed
        ValidationError: If transcript format is invalid
    """
    logger.debug(f"Loading transcript from {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise TranscriptLoadError(f"Invalid JSON in {path}: {e}")
    except IOError as e:
        raise TranscriptLoadError(f"Failed to read {path}: {e}")

    # Handle different transcript formats
    if isinstance(data, dict) and "segments" in data:
        segments = data["segments"]
    elif isinstance(data, list):
        segments = data
    else:
        raise TranscriptLoadError(
            f"Unrecognized transcript format in {path}. "
            f"Expected dict with 'segments' key or list of segments."
        )

    if not isinstance(segments, list):
        raise TranscriptLoadError(
            f"Transcript segments must be a list, got {type(segments).__name__}"
        )

    # Normalize and validate segments
    normalized_segments = []
    for i, seg in enumerate(segments):
        try:
            start = seg.get("start")
            if start is None:
                start = seg.get("start_time")
            end = seg.get("end")
            if end is None:
                end = seg.get("end_time")
            text = seg.get("text", "").strip()

            if start is None or end is None:
                logger.warning(f"Segment {i} missing start/end, skipping")
                continue

            # Validate numeric values
            start = float(start)
            end = float(end)

            if start < 0 or end < 0:
                logger.warning(f"Segment {i} has negative timestamps, skipping")
                continue

            if end <= start:
                logger.warning(f"Segment {i} has end <= start, skipping")
                continue

            normalized_segments.append({
                "start": start,
                "end": end,
                "text": text
            })
        except (ValueError, TypeError) as e:
            logger.warning(f"Segment {i} has invalid data: {e}, skipping")
            continue

    if not normalized_segments:
        raise TranscriptLoadError(f"No valid segments found in {path}")

    logger.info(f"Loaded {len(normalized_segments)} valid segments from {path}")
    return normalized_segments


# =============================================================================
# Segment Merging
# =============================================================================

def merge_segments_by_gap(
    segments: List[Dict[str, Any]],
    gap_threshold: float,
    min_length: float,
) -> List[Dict[str, Any]]:
    """
    Merge transcript segments until a gap exceeds threshold, enforce min length.

    Args:
        segments: List of transcript segments with start/end/text
        gap_threshold: Maximum gap (seconds) to merge segments
        min_length: Minimum segment length (seconds) before merging into neighbor

    Returns:
        List of merged speech segments
    """
    if not segments:
        logger.debug("No segments to merge")
        return []

    logger.debug(
        f"Merging {len(segments)} segments: "
        f"gap_threshold={gap_threshold}s, min_length={min_length}s"
    )

    merged = []
    current = {"start": segments[0]["start"], "end": segments[0]["end"], "type": "speech"}

    for seg in segments[1:]:
        gap = seg["start"] - current["end"]

        if gap <= gap_threshold:
            # Extend current segment
            current["end"] = max(current["end"], seg["end"])
            logger.debug(f"Merging: gap={gap:.2f}s <= threshold={gap_threshold}s")
        else:
            # Finalize current and start new
            merged.append(current)
            current = {"start": seg["start"], "end": seg["end"], "type": "speech"}
            logger.debug(f"Splitting: gap={gap:.2f}s > threshold={gap_threshold}s")

    merged.append(current)

    # Enforce min length by merging small ones into neighbors
    if len(merged) > 1:
        logger.debug(f"Enforcing min_length={min_length}s")
        enforced = []
        i = 0

        while i < len(merged):
            seg = merged[i]
            duration = seg["end"] - seg["start"]

            if duration < min_length and i + 1 < len(merged):
                # Merge into next segment
                logger.debug(
                    f"Merging short segment ({duration:.2f}s < {min_length}s) into next"
                )
                merged[i + 1]["start"] = seg["start"]
            else:
                enforced.append(seg)

            i += 1

        merged = enforced

    logger.info(f"Merged into {len(merged)} segments")
    return merged


def invert_intervals(intervals: List[Tuple[float, float]], total: float) -> List[Tuple[float, float]]:
    """
    Invert intervals to find gaps.

    Args:
        intervals: List of (start, end) tuples
        total: Total duration

    Returns:
        List of inverted (gap start, gap end) tuples
    """
    if not intervals:
        logger.debug("No intervals to invert, returning full range")
        return [(0.0, total)]

    intervals = sorted(intervals)
    inv = []
    current = 0.0

    for start, end in intervals:
        if start > current:
            inv.append((current, start))
        current = max(current, end)

    if current < total:
        inv.append((current, total))

    logger.debug(f"Inverted {len(intervals)} intervals into {len(inv)} gaps")
    return inv


def classify_non_speech(
    gaps: List[Tuple[float, float]],
    audio_path: Optional[Path],
    sample_every: float = 0.5,
    energy_threshold: float = 1e-4,
) -> List[Dict[str, Any]]:
    """
    Classify gaps as music or silence based on energy.

    Args:
        gaps: List of (start, end) tuples representing gaps
        audio_path: Optional path to audio file for energy analysis
        sample_every: Seconds between energy samples
        energy_threshold: Threshold for music vs silence classification

    Returns:
        List of gap segments with type field ("music" or "silence")
    """
    if not gaps:
        logger.debug("No gaps to classify")
        return []

    if audio_path is None or PydubAudio is None:
        logger.debug("No audio path or pydub unavailable, classifying all as silence")
        return [{"start": s, "end": e, "type": "silence"} for s, e in gaps]

    logger.debug(f"Classifying {len(gaps)} gaps using energy threshold={energy_threshold}")

    try:
        audio = PydubAudio.from_file(str(audio_path))
        sr = audio.frame_rate
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)

        if audio.channels > 1:
            samples = samples.reshape((-1, audio.channels)).mean(axis=1)

        samples /= np.max(np.abs(samples)) + 1e-9
    except Exception as e:
        logger.error(f"Failed to load audio for energy classification: {e}")
        raise AudioLoadError(f"Failed to load {audio_path}: {e}")

    classified = []

    for i, (start, end) in enumerate(gaps):
        if end <= start:
            logger.warning(f"Skipping invalid gap {i}: start={start}, end={end}")
            continue

        start_idx = int(start * sr)
        end_idx = int(end * sr)
        window = samples[start_idx:end_idx]

        if len(window) == 0:
            logger.warning(f"Gap {i} has empty window, classifying as silence")
            classified.append({"start": start, "end": end, "type": "silence"})
            continue

        # Sample energy over time
        hop = max(1, int(sample_every * sr))
        energies = []

        for j in range(0, len(window), hop):
            chunk = window[j:j + hop]
            energies.append(np.mean(chunk ** 2))

        median_energy = np.median(energies) if energies else 0.0
        gap_type = "music" if median_energy > energy_threshold else "silence"

        classified.append({"start": start, "end": end, "type": gap_type})

        logger.debug(
            f"Gap {i+1}/{len(gaps)}: {start:.2f}-{end:.2f}s, "
            f"median_energy={median_energy:.2e}, type={gap_type}"
        )

    music_count = sum(1 for c in classified if c["type"] == "music")
    silence_count = len(classified) - music_count
    logger.info(f"Classified {music_count} music gaps, {silence_count} silence gaps")

    return classified


def merge_bridged_segments(
    segments: List[Dict[str, Any]],
    bridge_type: str = "speech",
    max_bridge_duration: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Merge A-B-A patterns when the bridge B is short and of a given type.

    Example: music - short speech - music -> merge into one music segment.

    Args:
        segments: List of segments with start/end/type
        bridge_type: Type of segment to treat as bridge
        max_bridge_duration: Maximum bridge duration to allow merging

    Returns:
        List of segments with A-B-A patterns merged
    """
    if len(segments) < 3:
        logger.debug("Fewer than 3 segments, no bridge merging possible")
        return segments

    logger.debug(
        f"Checking for A-B-A patterns: bridge_type={bridge_type}, "
        f"max_duration={max_bridge_duration}s"
    )

    merged: List[Dict[str, Any]] = []
    i = 0
    merges_count = 0

    while i < len(segments):
        # Check for A-B-A pattern
        if (
            i + 2 < len(segments)
            and segments[i]["type"] == segments[i + 2]["type"]
            and segments[i + 1]["type"] == bridge_type
        ):
            bridge_duration = segments[i + 1]["end"] - segments[i + 1]["start"]

            if bridge_duration <= max_bridge_duration:
                # Merge A-B-A into A
                new_seg = {
                    "start": segments[i]["start"],
                    "end": segments[i + 2]["end"],
                    "type": segments[i]["type"],
                }
                merged.append(new_seg)
                logger.debug(
                    f"Merged A-B-A at {i}: {segments[i]['type']}-"
                    f"{bridge_type}-{segments[i]['type']} "
                    f"(bridge={bridge_duration:.2f}s)"
                )
                merges_count += 1
                i += 3
                continue

        merged.append(segments[i])
        i += 1

    logger.info(f"Merged {merges_count} A-B-A patterns")
    return merged


def build_segments(
    transcript_path: Path,
    audio_path: Optional[Path],
    gap_threshold: float,
    min_length: float,
    merge_bridges: bool = False,
    bridge_type: str = "speech",
    bridge_max_duration: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Build segments from transcript with optional audio-based gap classification.

    Args:
        transcript_path: Path to transcript JSON file
        audio_path: Optional path to audio file for energy classification
        gap_threshold: Gap threshold for merging segments (seconds)
        min_length: Minimum segment length (seconds)
        merge_bridges: Whether to merge A-B-A patterns
        bridge_type: Type of segment to treat as bridge
        bridge_max_duration: Maximum bridge duration for merging

    Returns:
        List of segments with start/end/type

    Raises:
        ValidationError: If input parameters are invalid
        TranscriptLoadError: If transcript cannot be loaded
        AudioLoadError: If audio cannot be loaded for classification
    """
    # Validate inputs
    validate_gap_threshold(gap_threshold)
    validate_min_length(min_length)
    validate_bridge_max_duration(bridge_max_duration)
    validate_bridge_type(bridge_type)
    validate_transcript_path(transcript_path)
    validate_audio_path(audio_path)

    # Load and merge transcript segments
    segs = load_transcript(transcript_path)
    speech = merge_segments_by_gap(segs, gap_threshold, min_length)

    # Get total duration from audio if available
    total_duration = 0.0

    if audio_path is not None and PydubAudio is not None:
        try:
            audio = PydubAudio.from_file(str(audio_path))
            total_duration = len(audio) / 1000.0  # ms to seconds
            logger.debug(f"Audio duration from file: {total_duration:.2f}s")
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}, using transcript duration")

    if total_duration == 0.0:
        total_duration = speech[-1]["end"] if speech else 0.0
        logger.debug(f"Using transcript duration: {total_duration:.2f}s")

    # Find and classify gaps
    speech_intervals = [(s["start"], s["end"]) for s in speech]
    gaps = invert_intervals(speech_intervals, total_duration)
    non_speech = classify_non_speech(gaps, audio_path)

    # Combine and sort
    all_segments = speech + non_speech
    all_segments = sorted(all_segments, key=lambda s: s["start"])

    # Optional bridge merging
    if merge_bridges:
        all_segments = merge_bridged_segments(
            all_segments,
            bridge_type=bridge_type,
            max_bridge_duration=bridge_max_duration,
        )

    logger.info(f"Built {len(all_segments)} total segments")
    return all_segments


def write_segments(path: Path, segments: List[Dict[str, Any]]) -> None:
    """
    Write segments to JSON file.

    Args:
        path: Output file path
        segments: List of segments with start/end/type

    Raises:
        IOError: If file cannot be written
    """
    logger.debug(f"Writing {len(segments)} segments to {path}")

    out = {
        "segments": segments,
        "total_segments": len(segments)
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

        logger.info(f"Wrote segments to {path}")
    except IOError as e:
        raise IOError(f"Failed to write segments to {path}: {e}")


def print_ffmpeg_hints(audio_path: Path, segments: List[Dict[str, Any]]) -> None:
    """Print ffmpeg commands for extracting segments."""
    print("\nFFmpeg crop suggestions:")

    for i, seg in enumerate(segments, 1):
        start = seg["start"]
        dur = seg["end"] - seg["start"]
        tag = seg["type"]
        out = audio_path.with_name(f"{audio_path.stem}_{i:02d}_{tag}{audio_path.suffix}")
        print(f"  ffmpeg -ss {start:.2f} -i \"{audio_path}\" -t {dur:.2f} -c copy \"{out}\"")


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
        description="Build coarse segments from transcript timestamps."
    )
    ap.add_argument("--transcript", required=True, help="Transcript JSON (superwhisper output).")
    ap.add_argument("--audio", help="Optional audio path for energy-based non-speech labeling.")
    ap.add_argument("--gap", type=float, default=8.0, help="Gap threshold (seconds) to split segments.")
    ap.add_argument("--min-length", type=float, default=180.0, help="Minimum segment length (seconds).")
    ap.add_argument("--output", required=True, help="Output segments JSON.")
    ap.add_argument(
        "--merge-bridges",
        action="store_true",
        help="Merge A-B-A patterns when B is a short bridge (default off).",
    )
    ap.add_argument(
        "--bridge-type",
        default="speech",
        help="Bridge type to merge (default: speech).",
    )
    ap.add_argument(
        "--bridge-max-duration",
        type=float,
        default=30.0,
        help="Maximum bridge duration (seconds) to allow merging.",
    )
    ap.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output.",
    )

    args = ap.parse_args()

    # Set verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        transcript_path = Path(args.transcript)
        audio_path = Path(args.audio) if args.audio else None

        segments = build_segments(
            transcript_path,
            audio_path,
            args.gap,
            args.min_length,
            merge_bridges=args.merge_bridges,
            bridge_type=args.bridge_type,
            bridge_max_duration=args.bridge_max_duration,
        )

        write_segments(Path(args.output), segments)

        print(f"Wrote {len(segments)} segments to {args.output}")

        if args.audio:
            print_ffmpeg_hints(Path(args.audio), segments)

    except (ValidationError, TranscriptLoadError, AudioLoadError) as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
