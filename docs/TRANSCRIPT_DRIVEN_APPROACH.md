# Transcript-Driven Segmentation

## Overview

This tool uses a transcript-driven approach to audio segmentation. Instead of analyzing audio features directly, we rely on Whisper's accurate speech timestamps and segment based on gaps in the transcript.

## Why Transcript-Driven?

| Approach | Pros | Cons |
|----------|------|------|
| **Transcript-driven** | Accurate timestamps, language-aware, simple | Requires transcription step |
| **VAD-based** | No transcription needed | Less accurate, language-agnostic |
| **Multi-detector** | Comprehensive | Complex, hard to tune, over-lapping results |

## The Pipeline

```
1. Transcribe with Whisper
   Input: Audio file
   Output: JSON with segments [{"start": 0, "end": 5.2, "text": "..."}]

2. Merge by gap threshold
   Input: Transcript segments
   Output: Merged speech segments

3. Invert to find gaps
   Input: Speech segments
   Output: Non-speech regions (gaps)

4. Classify gaps by energy
   Input: Gaps + audio
   Output: Gaps labeled as "music" or "silence"

5. Optional: Merge A-B-A bridges
   Input: Segments
   Output: Segments with short bridges merged
```

## Algorithm Details

### 1. Gap-Based Merging

Whisper produces many small segments (typically 2-5 seconds each). We merge these to avoid over-segmentation.

**Algorithm**:
```python
def merge_segments_by_gap(segments, gap_threshold, min_length):
    merged = []
    current = segments[0]

    for seg in segments[1:]:
        gap = seg["start"] - current["end"]

        if gap <= gap_threshold:
            # Extend current segment
            current["end"] = max(current["end"], seg["end"])
        else:
            # Finalize current and start new
            merged.append(current)
            current = seg

    merged.append(current)
    return merged
```

**Example**:
```
Input segments:
  [0.0-2.5] "Hello"
  [2.7-5.0] "world"    (gap: 0.2s)
  [8.5-12.0] "How are" (gap: 3.5s)

With gap_threshold=3.0:
  [0.0-5.0] "Hello world" (merged)
  [8.5-12.0] "How are"   (separate, gap > 3.0)
```

### 2. Minimum Length Enforcement

Very short segments are merged into neighbors to avoid fragmentation.

**Algorithm**:
```python
def enforce_min_length(segments, min_length):
    enforced = []
    i = 0

    while i < len(segments):
        seg = segments[i]

        if seg["end"] - seg["start"] < min_length and i + 1 < len(segments):
            # Merge into next segment
            segments[i + 1]["start"] = seg["start"]
        else:
            enforced.append(seg)

        i += 1

    return enforced
```

### 3. Invert Intervals

To find gaps (non-speech regions), we invert the speech intervals.

**Algorithm**:
```python
def invert_intervals(intervals, total_duration):
    inverted = []
    current = 0.0

    for start, end in sorted(intervals):
        if start > current:
            inverted.append((current, start))
        current = max(current, end)

    if current < total_duration:
        inverted.append((current, total_duration))

    return inverted
```

**Example**:
```
Speech: [0-10], [15-20], [25-30]
Total duration: 35

Gaps (inverted):
  [10-15], [20-25], [30-35]
```

### 4. Energy-Based Classification

Gaps are classified as music or silence based on median energy.

**Algorithm**:
```python
def classify_non_speech(gaps, audio_path, energy_threshold=1e-4):
    audio = load_audio(audio_path)
    samples = normalize(audio.get_array_of_samples())

    classified = []
    for start, end in gaps:
        window = samples[start_idx:end_idx]

        # Sample energy over time
        energies = [mean(chunk**2) for chunk in window]
        median_energy = median(energies)

        gap_type = "music" if median_energy > energy_threshold else "silence"
        classified.append({"start": start, "end": end, "type": gap_type})

    return classified
```

**Why median energy?**
- Robust to transient spikes
- Simple to compute
- Works well for distinguishing background music from silence

### 5. Bridge Merging (A-B-A Pattern)

Sometimes a short segment breaks two similar segments. We merge A-B-A when B is short.

**Algorithm**:
```python
def merge_bridged_segments(segments, bridge_type, max_bridge_duration):
    merged = []
    i = 0

    while i < len(segments):
        # Check for A-B-A pattern
        if (i + 2 < len(segments) and
            segments[i]["type"] == segments[i + 2]["type"] and
            segments[i + 1]["type"] == bridge_type and
            segments[i + 1]["end"] - segments[i + 1]["start"] <= max_bridge_duration):

            # Merge A-B-A into A
            new_seg = {
                "start": segments[i]["start"],
                "end": segments[i + 2]["end"],
                "type": segments[i]["type"]
            }
            merged.append(new_seg)
            i += 3
        else:
            merged.append(segments[i])
            i += 1

    return merged
```

**Example**:
```
Input:
  music [0-30]
  speech [30-35]  (5 seconds)
  music [35-120]

With bridge_type="speech", max_bridge_duration=60:
  music [0-120]  (merged)
```

## Complexity

| Step | Complexity |
|------|-----------|
| Gap merging | O(n) |
| Min length | O(n) |
| Invert intervals | O(n log n) |
| Energy classification | O(n × m) where m = samples per gap |
| Bridge merging | O(n) |

**Overall**: O(n × m) where n = number of transcript segments

## Parameter Tuning

See [PARAMETER_GUIDE.md](PARAMETER_GUIDE.md) for recommended values.
