"""
Transcribe an audio file with local Whisper and emit a JSON transcript
compatible with build_segments_from_transcript.

Usage:
  uv run python -m tools.transcribe_audio --audio /path/to/audio.mp3 \
    --model base --language en --output data/output/my_transcript.json
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

try:
    from src.stt.module import STTModule
    from src.stt.transcript import Transcript
except Exception as exc:  # pragma: no cover - defensive import guard
    raise SystemExit(
        "Failed to import STT modules. Ensure the project is installed or run via `uv run`."
    ) from exc


def transcript_to_json_dict(transcript: Transcript) -> Dict[str, Any]:
    """Flatten Transcript into a JSON-serializable dict."""
    return {
        "segments": [
            {
                "start": seg.start_time,
                "end": seg.end_time,
                "text": seg.text,
                "confidence": seg.confidence,
                "language": seg.language,
            }
            for seg in transcript.segments
        ],
        "language": transcript.language,
        "total_duration": transcript.total_duration,
        "word_count": transcript.word_count,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe audio with local Whisper.")
    ap.add_argument("--audio", required=True, help="Path to audio file")
    ap.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )
    ap.add_argument("--language", help="Language hint (e.g., en, es, fr)")
    ap.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size for decoding (default: 5)",
    )
    ap.add_argument(
        "--best-of",
        type=int,
        default=5,
        help="Best-of candidates when sampling (default: 5)",
    )
    ap.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature (default: 0.0)",
    )
    ap.add_argument(
        "--no-speech-threshold",
        type=float,
        default=0.6,
        help="No-speech threshold (default: 0.6)",
    )
    ap.add_argument(
        "--output",
        required=True,
        help="Output JSON path for transcript",
    )
    args = ap.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    stt = STTModule(model_size=args.model, language=args.language)
    transcript = stt.transcribe_file(
        str(audio_path),
        beam_size=args.beam_size,
        best_of=args.best_of,
        temperature=args.temperature,
        no_speech_threshold=args.no_speech_threshold,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(transcript_to_json_dict(transcript), f, indent=2)

    print(f"Wrote transcript: {out_path}")


if __name__ == "__main__":
    main()
