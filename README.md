# Local Audio Segmenter

A Python tool for audio segmentation using transcript-driven analysis. Transcribes audio with Whisper, then segments based on transcript gaps and energy-based classification.

## Features

- Local-first: Whisper transcription + segmentation + ffmpeg export; no network needed after install
- Transcript-driven merging: gap-based and bridge-aware heuristics to avoid over-segmentation
- One-shot CLI: transcribe → merge → export clips (mp3 by default)
- Standalone helper scripts for transcribe/merge/export if you need manual control

## Installation (uv-first)

```bash
git clone https://github.com/example/audio-auto-segmentation.git
cd audio-auto-segmentation
uv sync            # installs prod deps into .venv
# or include dev extras
uv sync --dev
```

Prereqs:
- Python 3.9+
- `uv` installed (https://docs.astral.sh/uv/getting-started/installation/)
- `ffmpeg` available on PATH (e.g., `brew install ffmpeg` on macOS)

Bootstrap helper:
```bash
INSTALL_UV=1 ./scripts/setup.sh   # installs uv if missing, checks Python/ffmpeg, runs uv sync
```

## Quick Start

```bash
# Default (transcript-driven) end-to-end with local Whisper + ffmpeg export
uv run python -m src.cli.main /path/to/audio.mp3

# Override transcript-driven heuristics
uv run python -m src.cli.main /path/to/audio.mp3 \
  --td-gap 3 --td-min-length 60 \
  --td-merge-bridges --td-bridge-type speech --td-bridge-max-duration 60
```

Outputs (defaults):
- Transcript JSON: `<cwd>/<audio>_transcript.json`
- Segments JSON: `<cwd>/<audio>_segments.json`
- Clips directory: `<cwd>/<audio>_segments/` (auto-created if `--td-export-dir` not set)
- Clip filenames: `audio_XX_<type>.mp3`

### Helper tools (transcript-driven workflow)

```bash
# Transcribe audio to JSON (Whisper via uv)
uv run python -m tools.transcribe_audio \
  --audio /path/to/audio.mp3 \
  --model base \
  --output data/output/example_transcript.json

# Build segments from an existing transcript
uv run python -m tools.build_segments_from_transcript \
  --transcript data/input/example_transcript.json \
  --audio /path/to/audio.mp3 \
  --gap 3 --min-length 60 \
  --merge-bridges --bridge-type speech --bridge-max-duration 60 \
  --output data/output/segments.json

# Export the segments to per-clip audio files with ffmpeg
uv run python -m tools.export_segments \
  --audio /path/to/audio.mp3 \
  --segments data/output/segments.json \
  --outdir data/output/output_segments \
  --format mp3 \
  --prefix my-audio
```

## Output format

Segments JSON (produced by main CLI and helpers) looks like:
```json
{
  "segments": [
    {
      "start": 30.0,
      "end": 399.08,
      "type": "speech"
    },
    {
      "start": 399.08,
      "end": 417.08,
      "type": "music"
    }
  ]
}
```

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System architecture and component overview
- **[Transcript-Driven Approach](docs/TRANSCRIPT_DRIVEN_APPROACH.md)** - How the segmentation algorithms work
- **[Parameter Guide](docs/PARAMETER_GUIDE.md)** - Parameter tuning and typical configurations

> **Note**: Previous documentation described a more complex multi-detector system with semantic labeling. Those docs have been archived to `docs/archived/` as they described features that were never implemented. The current implementation uses a simpler, more reliable transcript-driven approach.

## Development

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run performance tests
uv run pytest tests/performance/
```

## License

MIT License
