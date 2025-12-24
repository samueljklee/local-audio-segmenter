# Parameter Guide

## Overview

This guide explains the key parameters for transcript-driven segmentation and provides recommended values for different use cases.

## Parameters

### Whisper Model (`--whisper-model`)

Controls which Whisper model to use for transcription.

| Model | Size | Speed | Accuracy | VRAM | Use Case |
|-------|------|-------|----------|------|----------|
| tiny | ~40MB | Fastest | Lowest | ~1GB | Quick testing, low-resource |
| base | ~140MB | Fast | Good | ~1GB | **Default, good balance** |
| small | ~460MB | Medium | Better | ~2GB | Better accuracy |
| medium | ~1.5GB | Slow | Very Good | ~5GB | High accuracy needed |
| large | ~3GB | Slowest | Best | ~10GB | Best accuracy, English only |

**Recommendation**: Start with `base`. Upgrade to `small` or `medium` if transcription quality is poor.

### Gap Threshold (`--td-gap`)

Maximum gap (in seconds) between transcript segments to merge them.

**How it works**: If two speech segments are separated by <= this gap, they're merged into one.

| Value | Use Case |
|-------|----------|
| 1-2 seconds | Fast speech, no pauses (news broadcasts) |
| 3 seconds | **Default, works for most content** |
| 5-8 seconds | Conversational content with natural pauses |
| 10+ seconds | Content with intentional pauses (lectures, sermons) |

**Recommendation**:
- Start with `3.0` (default)
- Increase if you see over-segmentation (too many small clips)
- Decrease if you want segments to break at natural pauses

### Minimum Segment Length (`--td-min-length`)

Minimum duration (in seconds) a segment must have. Shorter segments are merged into neighbors.

| Value | Use Case |
|-------|----------|
| 30 seconds | Strict filtering, only meaningful content |
| 60 seconds | **Default, good for most cases** |
| 120+ seconds | Very coarse segmentation, long-form content |

**Recommendation**:
- Start with `60.0` (default)
- Increase if you want fewer, longer segments
- Decrease to preserve shorter segments

### Bridge Merging (`--td-merge-bridges`)

Enable/disable A-B-A pattern merging.

**Example**: `music - speech(10s) - music` → `music` (merged)

**When to enable** (default: `true`):
- Music with brief announcements
- Speech with short musical interludes
- Any content where short interruptions shouldn't break segments

**When to disable**:
- Every segment should be preserved
- Short segments are meaningful

### Bridge Type (`--td-bridge-type`)

Which type of segment to treat as a "bridge" for A-B-A merging.

| Value | Use Case |
|-------|----------|
| speech | **Default**, merge through short speech segments |
| music | Merge through short musical interludes |
| silence | Merge through short silent pauses |

**Recommendation**: Keep as `speech` unless you have specific needs.

### Bridge Max Duration (`--td-bridge-max-duration`)

Maximum duration (in seconds) of a bridge segment to allow A-B-A merging.

| Value | Use Case |
|-------|----------|
| 10-30 seconds | Very short interruptions only |
| 60 seconds | **Default, allows moderate interruptions** |
| 120+ seconds | Allow longer bridges to be merged |

**Recommendation**:
- Start with `60.0` (default)
- Decrease if you want to preserve shorter interruptions
- Increase if you want more aggressive merging

## Typical Configurations

### Church Service
```bash
--td-gap 8 \
--td-min-length 60 \
--td-merge-bridges \
--td-bridge-type speech \
--td-bridge-max-duration 60
```
**Rationale**: Longer gaps tolerate pauses; merge through short prayers/announcements.

### Podcast
```bash
--td-gap 3 \
--td-min-length 60 \
--td-merge-bridges \
--td-bridge-type speech \
--td-bridge-max-duration 30
```
**Rationale**: Standard gap; shorter bridge duration to preserve sponsor breaks.

### Lecture
```bash
--td-gap 5 \
--td-min-length 120 \
--td-merge-bridges \
--td-bridge-type speech \
--td-bridge-max-duration 45
```
**Rationale**: Tolerate note-taking pauses; longer segments for coherent topics.

### Meeting
```bash
--td-gap 2 \
--td-min-length 30 \
--td-merge-bridges false
```
**Rationale**: Shorter gaps and segments to preserve individual contributions.

## Energy Classification (Internal)

The tool uses an internal `energy_threshold=1e-4` for classifying gaps as music vs silence.

This is not currently configurable via CLI, but can be modified in `tools/build_segments_from_transcript.py`:

```python
def classify_non_speech(gaps, audio_path, energy_threshold=1e-4):
    # Higher threshold = more classified as silence
    # Lower threshold = more classified as music
```

## Export Parameters

### Export Format (`--td-export-format`)

Audio format for exported clips.

| Format | Size | Quality | Compatibility |
|--------|------|---------|---------------|
| mp3 | Small | Good | Universal |
| wav | Large | Perfect | Universal |
| flac | Medium | Perfect | Lossless |

**Recommendation**: `mp3` for distribution, `wav` for editing.

### Output Directory (`--td-export-dir`)

Where to save exported clips.

**Default**: `<output>/<filename>_segments/`

## Tuning Workflow

1. **Start with defaults**
   ```bash
   uv run python -m src.cli.main audio.mp3
   ```

2. **Review the segments JSON**
   ```bash
   cat audio_segments.json | jq '.segments[] | {start, end, type, duration: (.end - .start)}'
   ```

3. **Adjust based on issues**:
   - Too many small segments → increase `--td-gap`
   - Segments too long → decrease `--td-min-length`
   - Unwanted breaks → enable `--td-merge-bridges` with appropriate `--td-bridge-max-duration`

4. **Iterate**: Re-run with adjusted parameters until satisfied.

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Over-segmentation | Many 5-10 second clips | Increase `--td-gap` |
| Under-segmentation | One huge clip | Decrease `--td-gap`, decrease `--td-min-length` |
| Music broken by speech | Short speech segments in music | Enable `--td-merge-bridges` with `--td-bridge-type speech` |
| Transcription errors | Garbled text | Try larger `--whisper-model` |
