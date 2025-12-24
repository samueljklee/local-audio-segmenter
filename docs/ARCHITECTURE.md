# Local Audio Segmenter - Architecture

## Overview

A simple, focused tool for audio segmentation using transcript-driven analysis. The tool uses OpenAI Whisper for speech-to-text, then segments audio based on transcript gaps and energy-based classification.

## Design Philosophy

- **Transcript-first**: Trust Whisper timestamps over audio analysis
- **Simple over complex**: Gap-based merging instead of multi-detector systems
- **Local-only**: No network calls after initial installation
- **Modular tools**: Independent transcribe/segment/export scripts

## Architecture

```
Input Audio
    |
    v
Whisper Transcription (STTModule)
    |
    v
Transcript JSON (timestamps + text)
    |
    v
Gap-based Merging (merge_segments_by_gap)
    |
    v
Invert to Find Gaps (invert_intervals)
    |
    v
Energy Classification (classify_non_speech)
    |
    v
Optional Bridge Merging (merge_bridged_segments)
    |
    v
Segments JSON
    |
    v
FFmpeg Export (export_segments)
    |
    v
Individual Audio Clips
```

## Components

### AudioLoader (`src/audio/loader.py`)

Loads audio files with librosa (primary) and pydub (fallback).

```python
class AudioLoader:
    def load_audio(self, file_path: str, target_sr: int = None) -> tuple[np.ndarray, int]
    def get_supported_formats(self) -> list[str]
```

**Supported formats**: WAV, MP3, FLAC, OGG, M4A, AAC

### STTModule (`src/stt/module.py`)

Whisper wrapper for speech-to-text transcription.

```python
class STTModule:
    def __init__(self, model_size: str = "base", language: str = None)
    def transcribe_file(self, audio_path: str, **kwargs) -> Transcript
```

**Models**: tiny, base, small, medium, large

### Gap Merger (`tools/build_segments_from_transcript.py`)

Core segmentation algorithm. Merges transcript segments based on temporal gaps.

**Algorithm (O(n))**:
1. Load transcript segments with start/end timestamps
2. Merge consecutive segments where gap <= threshold
3. Enforce minimum segment length by merging short segments
4. Invert speech intervals to find gaps
5. Classify gaps as music/silence using energy threshold
6. Optionally merge A-B-A bridge patterns

### Exporter (`tools/export_segments.py`)

Uses ffmpeg to extract clips based on segment timestamps.

## Data Flow

```
Audio File → STTModule → Transcript JSON
                             |
                             v
                    build_segments()
                             |
                    +--------+--------+
                    |                 |
            merge_segments()  invert_intervals()
                    |                 |
                    +--------+--------+
                             |
                    classify_non_speech()
                             |
                    merge_bridged_segments() [optional]
                             |
                        Segments JSON
                             |
                    export_segments()
                             |
                        Audio Clips
```

## Segmentation Algorithm

### Gap-based Merging

Transcript segments are merged when the gap between them is below a threshold:

```python
gap = next_segment.start - current_segment.end
if gap <= gap_threshold:
    merge()  # Combine segments
```

### Energy Classification

Gaps (non-speech regions) are classified by median energy:

```python
median_energy = np.median(energies)
if median_energy > energy_threshold:
    type = "music"
else:
    type = "silence"
```

### Bridge Merging

A-B-A patterns are merged when B is short:

```
music - speech(30s) - music  →  music (merged)
```

## Configuration

All configuration is via CLI flags. No YAML profiles are currently used.

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--whisper-model` | base | Whisper model size |
| `--td-gap` | 3.0 | Gap threshold for merging (seconds) |
| `--td-min-length` | 60.0 | Minimum segment length (seconds) |
| `--td-merge-bridges` | true | Enable A-B-A bridge merging |
| `--td-bridge-type` | speech | Bridge type to merge through |
| `--td-bridge-max-duration` | 60.0 | Max bridge duration (seconds) |

## Output Format

### Transcript JSON
```json
{
  "segments": [
    {"start": 0.0, "end": 5.2, "text": "Hello world"},
    {"start": 5.5, "end": 10.0, "text": "How are you?"}
  ]
}
```

### Segments JSON
```json
{
  "segments": [
    {"start": 0.0, "end": 399.08, "type": "speech"},
    {"start": 399.08, "end": 417.08, "type": "music"}
  ]
}
```

## Tools

### Main CLI
```bash
uv run python -m src.cli.main audio.mp3
```

### Standalone Tools
```bash
# Transcribe only
uv run python -m tools.transcribe_audio --audio audio.mp3 --model base

# Segment from existing transcript
uv run python -m tools.build_segments_from_transcript \
  --transcript transcript.json --audio audio.mp3

# Export clips
uv run python -m tools.export_segments \
  --audio audio.mp3 --segments segments.json --outdir clips/
```

## Design Decisions

### Why Transcript-Driven?

- **Accuracy**: Whisper timestamps are more accurate than VAD
- **Simplicity**: One model instead of multiple detectors
- **Language-aware**: Speech context helps segmentation

### Why Simple Energy Classification?

- **Reliability**: Energy thresholds work well for music vs silence
- **Fast**: O(n) computation
- **Transparent**: Easy to debug and tune

### No Semantic Labeling

The archived documentation describes genre/mood classification, but this is not implemented. Current implementation only classifies as:
- **speech**: Has transcript text
- **music**: High energy gap without transcript
- **silence**: Low energy gap without transcript

## Dependencies

- **librosa**: Audio loading
- **pydub**: Fallback audio loading
- **openai-whisper**: Speech-to-text
- **torch**: ML framework for Whisper
- **ffmpeg**: Clip export (external binary)
