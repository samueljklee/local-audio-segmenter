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
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

try:
    from pydub import AudioSegment as PydubAudio
except Exception:
    PydubAudio = None  # type: ignore


def load_transcript(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Expecting a list of segments with start/end/text or a dict with 'segments'
    if isinstance(data, dict) and "segments" in data:
        segments = data["segments"]
    elif isinstance(data, list):
        segments = data
    else:
        raise ValueError("Unrecognized transcript JSON format")
    norm_segments = []
    for seg in segments:
        start = seg.get("start")
        if start is None:
            start = seg.get("start_time")
        end = seg.get("end")
        if end is None:
            end = seg.get("end_time")
        text = seg.get("text", "").strip()
        if start is None or end is None:
            continue
        norm_segments.append({"start": float(start), "end": float(end), "text": text})
    return norm_segments


def merge_segments_by_gap(
    segments: List[Dict[str, Any]],
    gap_threshold: float,
    min_length: float,
) -> List[Dict[str, Any]]:
    """Merge transcript segments until a gap exceeds threshold, enforce min length."""
    if not segments:
        return []
    merged = []
    current = {"start": segments[0]["start"], "end": segments[0]["end"], "type": "speech"}
    for seg in segments[1:]:
        gap = seg["start"] - current["end"]
        if gap <= gap_threshold:
            current["end"] = max(current["end"], seg["end"])
        else:
            merged.append(current)
            current = {"start": seg["start"], "end": seg["end"], "type": "speech"}
    merged.append(current)

    # Enforce min length by merging small ones into neighbors
    if len(merged) > 1:
        enforced = []
        i = 0
        while i < len(merged):
            seg = merged[i]
            if seg["end"] - seg["start"] < min_length and i + 1 < len(merged):
                # merge into next
                merged[i + 1]["start"] = seg["start"]
            else:
                enforced.append(seg)
            i += 1
        merged = enforced

    return merged


def invert_intervals(intervals: List[Tuple[float, float]], total: float) -> List[Tuple[float, float]]:
    if not intervals:
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
    return inv


def classify_non_speech(
    gaps: List[Tuple[float, float]],
    audio_path: Optional[Path],
    sample_every: float = 0.5,
    energy_threshold: float = 1e-4,
) -> List[Dict[str, Any]]:
    """
    Simple energy-based classifier for gaps: label as music/other if energy is high.
    Requires pydub; otherwise defaults to silence.
    """
    if not gaps:
        return []
    if audio_path is None or PydubAudio is None:
        return [{"start": s, "end": e, "type": "silence"} for s, e in gaps]

    audio = PydubAudio.from_file(str(audio_path))
    sr = audio.frame_rate
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    if audio.channels > 1:
        samples = samples.reshape((-1, audio.channels)).mean(axis=1)
    samples /= np.max(np.abs(samples) + 1e-9)

    classified = []
    for start, end in gaps:
        if end <= start:
            continue
        start_idx = int(start * sr)
        end_idx = int(end * sr)
        window = samples[start_idx:end_idx]
        if len(window) == 0:
            continue
        # Sample energy over time
        hop = max(1, int(sample_every * sr))
        energies = []
        for i in range(0, len(window), hop):
            chunk = window[i : i + hop]
            energies.append(np.mean(chunk**2))
        median_energy = np.median(energies) if energies else 0.0
        gap_type = "music" if median_energy > energy_threshold else "silence"
        classified.append({"start": start, "end": end, "type": gap_type})
    return classified


def merge_bridged_segments(
    segments: List[Dict[str, Any]],
    bridge_type: str = "speech",
    max_bridge_duration: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Merge A-B-A patterns when the bridge B is short and of a given type.

    Example: music - short speech - music -> merge into one music segment.
    """
    if len(segments) < 3:
        return segments

    merged: List[Dict[str, Any]] = []
    i = 0
    while i < len(segments):
        if (
            i + 2 < len(segments)
            and segments[i]["type"] == segments[i + 2]["type"]
            and segments[i + 1]["type"] == bridge_type
            and (segments[i + 1]["end"] - segments[i + 1]["start"]) <= max_bridge_duration
        ):
            new_seg = {
                "start": segments[i]["start"],
                "end": segments[i + 2]["end"],
                "type": segments[i]["type"],
            }
            merged.append(new_seg)
            i += 3
        else:
            merged.append(segments[i])
            i += 1

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
    segs = load_transcript(transcript_path)
    speech = merge_segments_by_gap(segs, gap_threshold, min_length)
    # Total duration from audio if available, otherwise from transcript
    total_duration = 0.0
    if audio_path and PydubAudio is not None:
        try:
            audio = PydubAudio.from_file(str(audio_path))
            total_duration = len(audio) / 1000.0  # ms to seconds
        except Exception:
            pass
    if total_duration == 0.0:
        total_duration = speech[-1]["end"] if speech else 0.0

    speech_intervals = [(s["start"], s["end"]) for s in speech]
    gaps = invert_intervals(speech_intervals, total_duration)
    non_speech = classify_non_speech(gaps, audio_path)
    all_segments = speech + non_speech
    all_segments = sorted(all_segments, key=lambda s: s["start"])
    if merge_bridges:
        all_segments = merge_bridged_segments(
            all_segments,
            bridge_type=bridge_type,
            max_bridge_duration=bridge_max_duration,
        )
    return all_segments


def write_segments(path: Path, segments: List[Dict[str, Any]]) -> None:
    out = {"segments": segments, "total_segments": len(segments)}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


def print_ffmpeg_hints(audio_path: Path, segments: List[Dict[str, Any]]) -> None:
    print("\nFFmpeg crop suggestions:")
    for i, seg in enumerate(segments, 1):
        start = seg["start"]
        dur = seg["end"] - seg["start"]
        tag = seg["type"]
        out = audio_path.with_name(f"{audio_path.stem}_{i:02d}_{tag}{audio_path.suffix}")
        print(f"ffmpeg -ss {start:.2f} -i \"{audio_path}\" -t {dur:.2f} -c copy \"{out}\"")


def main():
    ap = argparse.ArgumentParser(description="Build coarse segments from transcript timestamps.")
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
    args = ap.parse_args()

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
    if audio_path:
        print_ffmpeg_hints(audio_path, segments)


if __name__ == "__main__":
    main()
