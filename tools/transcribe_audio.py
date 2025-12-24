"""
Transcribe an audio file with local Whisper and emit a JSON transcript
compatible with build_segments_from_transcript.

Usage:
  uv run python -m tools.transcribe_audio --audio /path/to/audio.mp3 \
    --model base --language en --output data/output/my_transcript.json
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any

try:
    from src.stt.module import STTModule
    from src.stt.transcript import Transcript
    from src.audio.loader import AudioLoader, AudioLoadError
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Failed to import STT modules. Ensure the project is installed or run via `uv run`."
    ) from exc

logger = logging.getLogger(__name__)


# =============================================================================
# Error Classes
# =============================================================================

class TranscriptionError(Exception):
    """Base exception for transcription errors."""
    pass


class ValidationError(TranscriptionError):
    """Raised when input validation fails."""
    pass


# =============================================================================
# Validation
# =============================================================================

def validate_audio_path(audio_path: Path) -> None:
    """Validate that audio file exists and is readable."""
    if not audio_path.exists():
        raise ValidationError(f"Audio file not found: {audio_path}")

    if not audio_path.is_file():
        raise ValidationError(f"Audio path is not a file: {audio_path}")

    # Check if file can be loaded
    try:
        loader = AudioLoader()
        if not loader.validate_audio_file(audio_path):
            raise ValidationError(f"File is not a valid audio file: {audio_path}")
    except Exception as e:
        raise ValidationError(f"Failed to validate audio file: {e}")


def validate_model_size(model: str) -> None:
    """Validate Whisper model size."""
    valid_models = {"tiny", "base", "small", "medium", "large"}
    if model not in valid_models:
        raise ValidationError(
            f"Invalid model '{model}'. Must be one of: {', '.join(sorted(valid_models))}"
        )


def validate_beam_size(beam_size: int) -> None:
    """Validate beam size parameter."""
    if beam_size < 1:
        raise ValidationError(f"beam_size must be >= 1, got {beam_size}")


def validate_temperature(temperature: float) -> None:
    """Validate temperature parameter."""
    if not 0.0 <= temperature <= 1.0:
        raise ValidationError(f"temperature must be between 0.0 and 1.0, got {temperature}")


def validate_no_speech_threshold(threshold: float) -> None:
    """Validate no_speech_threshold parameter."""
    if not 0.0 <= threshold <= 1.0:
        raise ValidationError(f"no_speech_threshold must be between 0.0 and 1.0, got {threshold}")


def validate_output_path(output_path: Path) -> None:
    """Validate output path can be written."""
    # Check parent directory exists or can be created
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValidationError(f"Cannot create output directory {output_path.parent}: {e}")


# =============================================================================
# Conversion Functions
# =============================================================================

def transcript_to_json_dict(transcript: Transcript) -> Dict[str, Any]:
    """
    Convert Transcript object to JSON-serializable dict.

    Args:
        transcript: Transcript object with segments and metadata

    Returns:
        Dictionary ready for JSON serialization
    """
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


# =============================================================================
# Main Transcription Function
# =============================================================================

def transcribe_audio_file(
    audio_path: Path,
    model_size: str = "base",
    language: str = None,
    beam_size: int = 5,
    best_of: int = 5,
    temperature: float = 0.0,
    no_speech_threshold: float = 0.6,
    verbose: bool = False,
) -> Transcript:
    """
    Transcribe audio file with Whisper.

    Args:
        audio_path: Path to audio file
        model_size: Whisper model size (tiny, base, small, medium, large)
        language: Optional language hint (e.g., en, es, fr)
        beam_size: Beam size for decoding
        best_of: Number of candidates when sampling
        temperature: Sampling temperature
        no_speech_threshold: Threshold for no-speech detection
        verbose: Whether to show detailed progress

    Returns:
        Transcript object with transcription results

    Raises:
        TranscriptionError: If transcription fails
    """
    logger.info(f"Starting transcription of {audio_path.name}")
    logger.info(f"Model: {model_size}, Language: {language or 'auto-detect'}")

    try:
        # Initialize STT module
        stt = STTModule(model_size=model_size, language=language)

        # Get audio info for logging
        loader = AudioLoader()
        try:
            info = loader.get_audio_info(audio_path)
            logger.info(
                f"Audio: {info['duration']:.1f}s, "
                f"{info['channels']}ch, "
                f"{info['sample_rate']}Hz"
            )
        except Exception:
            logger.warning("Could not get audio info, proceeding anyway")

        # Transcribe
        logger.info("Transcribing... (this may take a while)")
        transcript = stt.transcribe_file(
            str(audio_path),
            beam_size=beam_size,
            best_of=best_of,
            temperature=temperature,
            no_speech_threshold=no_speech_threshold,
        )

        # Log results
        logger.info(
            f"Transcription complete: "
            f"{len(transcript.segments)} segments, "
            f"{transcript.word_count} words, "
            f"language={transcript.language or 'unknown'}"
        )

        return transcript

    except AudioLoadError as e:
        logger.error(f"Failed to load audio: {e}")
        raise TranscriptionError(f"Audio loading failed: {e}")
    except RuntimeError as e:
        logger.error(f"Transcription failed: {e}")
        raise TranscriptionError(f"Speech-to-Text failed: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error during transcription: {e}")
        raise TranscriptionError(f"Transcription error: {e}")


def write_transcript(transcript: Transcript, output_path: Path) -> None:
    """
    Write transcript to JSON file.

    Args:
        transcript: Transcript object
        output_path: Output file path

    Raises:
        IOError: If file cannot be written
    """
    logger.debug(f"Writing transcript to {output_path}")

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(transcript_to_json_dict(transcript), f, indent=2)

        logger.info(f"Wrote transcript to {output_path}")
    except IOError as e:
        raise IOError(f"Failed to write transcript to {output_path}: {e}")


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    """Main CLI entry point."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    ap = argparse.ArgumentParser(
        description="Transcribe audio with local Whisper."
    )
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
        # Validate inputs
        audio_path = Path(args.audio)
        validate_audio_path(audio_path)
        validate_model_size(args.model)
        validate_beam_size(args.beam_size)
        validate_temperature(args.temperature)
        validate_no_speech_threshold(args.no_speech_threshold)

        output_path = Path(args.output)
        validate_output_path(output_path)

        # Transcribe
        transcript = transcribe_audio_file(
            audio_path=audio_path,
            model_size=args.model,
            language=args.language,
            beam_size=args.beam_size,
            best_of=args.best_of,
            temperature=args.temperature,
            no_speech_threshold=args.no_speech_threshold,
            verbose=args.verbose,
        )

        # Write output
        write_transcript(transcript, output_path)

        print(f"Wrote transcript: {output_path}")

    except (ValidationError, TranscriptionError) as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
