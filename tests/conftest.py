"""Test configuration and fixtures."""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest
import soundfile as sf
from pydub import AudioSegment
from pydub.generators import Sine, Square


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_audio_1sec(temp_dir) -> Path:
    """Create a 1-second silent audio file for testing."""
    audio_path = temp_dir / "test_1sec.wav"
    silence = AudioSegment.silent(duration=1000)  # 1 second
    silence.export(str(audio_path), format="wav")
    return audio_path


@pytest.fixture
def sample_audio_5sec(temp_dir) -> Path:
    """Create a 5-second audio file with tone for testing."""
    audio_path = temp_dir / "test_5sec.wav"
    tone = Sine(440).to_audio_segment(duration=5000)  # 5 seconds
    tone.export(str(audio_path), format="wav")
    return audio_path


@pytest.fixture
def sample_audio_with_music_silence(temp_dir) -> Path:
    """Create audio with music and silence sections."""
    audio_path = temp_dir / "test_music_silence.wav"

    # Create: 2s tone (music), 1s silence, 2s tone (music)
    tone = Sine(440).to_audio_segment(duration=2000)
    silence = AudioSegment.silent(duration=1000)
    combined = tone + silence + tone

    combined.export(str(audio_path), format="wav")
    return audio_path


@pytest.fixture
def sample_transcript_json(temp_dir) -> Path:
    """Create a sample transcript JSON file."""
    transcript_path = temp_dir / "transcript.json"

    transcript_data = {
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "Hello world"},
            {"start": 2.6, "end": 5.0, "text": "How are you?"},
            {"start": 8.0, "end": 12.0, "text": "Goodbye"},
            {"start": 12.5, "end": 15.0, "text": "See you later"},
        ],
        "language": "en",
        "total_duration": 15.0,
        "word_count": 12,
    }

    with transcript_path.open("w") as f:
        json.dump(transcript_data, f)

    return transcript_path


@pytest.fixture
def sample_transcript_segments():
    """Return sample transcript segments as list of dicts."""
    return [
        {"start": 0.0, "end": 2.5, "text": "Hello world"},
        {"start": 2.6, "end": 5.0, "text": "How are you?"},
        {"start": 8.0, "end": 12.0, "text": "Goodbye"},
        {"start": 12.5, "end": 15.0, "text": "See you later"},
    ]


@pytest.fixture
def sample_segments_json(temp_dir) -> Path:
    """Create a sample segments JSON file."""
    segments_path = temp_dir / "segments.json"

    segments_data = {
        "segments": [
            {"start": 0.0, "end": 5.0, "type": "speech"},
            {"start": 5.0, "end": 8.0, "type": "silence"},
            {"start": 8.0, "end": 15.0, "type": "speech"},
        ]
    }

    with segments_path.open("w") as f:
        json.dump(segments_data, f)

    return segments_path


@pytest.fixture
def mock_whisper_result():
    """Mock Whisper transcription result."""
    return {
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "Hello world", "avg_logprob": -0.1},
            {"start": 2.6, "end": 5.0, "text": "How are you?", "avg_logprob": -0.15},
        ],
        "language": "en",
        "all_language_probs": {},
        "timings": {},
    }


@pytest.fixture
def invalid_audio_path(temp_dir) -> Path:
    """Return a path to a non-existent audio file."""
    return temp_dir / "does_not_exist.mp3"


@pytest.fixture
def invalid_json_path(temp_dir) -> Path:
    """Return a path to an invalid JSON file."""
    json_path = temp_dir / "invalid.json"
    with json_path.open("w") as f:
        f.write("{ invalid json }")
    return json_path
