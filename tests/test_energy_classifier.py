"""Tests for energy-based gap classification."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

# Add tools to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.build_segments_from_transcript import classify_non_speech, invert_intervals


class TestClassifyNonSpeech:
    """Tests for energy-based gap classification."""

    def test_empty_gaps(self):
        """Test with empty gaps list."""
        result = classify_non_speech([], audio_path=None)
        assert result == []

    def test_no_audio_path(self):
        """Test without audio path (defaults to silence)."""
        gaps = [(0.0, 5.0), (10.0, 15.0)]
        result = classify_non_speech(gaps, audio_path=None)

        assert len(result) == 2
        assert all(r["type"] == "silence" for r in result)

    def test_no_pydub_available(self):
        """Test when pydub is not available."""
        gaps = [(0.0, 5.0)]
        with patch('tools.build_segments_from_transcript.PydubAudio', None):
            result = classify_non_speech(gaps, audio_path=None)
            assert len(result) == 1
            assert result[0]["type"] == "silence"

    @pytest.mark.parametrize("energy_threshold,expected_type", [
        (1e-4, "silence"),  # Low energy = silence
        (1e-6, "music"),    # High threshold = music
    ])
    def test_energy_threshold_classification(self, sample_audio_5sec, energy_threshold, expected_type):
        """Test classification with different energy thresholds."""
        gaps = [(0.0, 1.0)]
        result = classify_non_speech(
            gaps,
            audio_path=sample_audio_5sec,
            energy_threshold=energy_threshold
        )

        assert len(result) == 1
        assert result[0]["type"] in ["music", "silence"]

    def test_multiple_gaps(self, sample_audio_5sec):
        """Test classification of multiple gaps."""
        gaps = [(0.0, 0.5), (1.0, 1.5), (2.0, 2.5)]
        result = classify_non_speech(gaps, audio_path=sample_audio_5sec)

        assert len(result) == 3
        for r in result:
            assert r["type"] in ["music", "silence"]
            assert "start" in r
            assert "end" in r

    def test_invalid_gap_bounds(self, sample_audio_5sec):
        """Test handling of gaps with end < start."""
        gaps = [(5.0, 3.0), (1.0, 2.0)]  # First gap has end < start
        result = classify_non_speech(gaps, audio_path=sample_audio_5sec)

        # Should skip invalid gap
        assert len(result) == 1

    def test_preserves_gap_timing(self, sample_audio_5sec):
        """Test that original gap timing is preserved."""
        gaps = [(0.5, 1.5), (2.0, 3.0)]
        result = classify_non_speech(gaps, audio_path=sample_audio_5sec)

        assert len(result) == 2
        assert result[0]["start"] == 0.5
        assert result[0]["end"] == 1.5
        assert result[1]["start"] == 2.0
        assert result[1]["end"] == 3.0


class TestInvertIntervals:
    """Tests for interval inversion function."""

    def test_empty_intervals(self):
        """Test with empty interval list."""
        result = invert_intervals([], total=100.0)
        assert result == [(0.0, 100.0)]

    def test_single_interval(self):
        """Test inverting a single interval."""
        intervals = [(10.0, 20.0)]
        result = invert_intervals(intervals, total=30.0)

        # Before: [0-10], After: [20-30]
        assert len(result) == 2
        assert result[0] == (0.0, 10.0)
        assert result[1] == (20.0, 30.0)

    def test_multiple_intervals(self):
        """Test inverting multiple intervals."""
        intervals = [(5.0, 10.0), (15.0, 20.0)]
        result = invert_intervals(intervals, total=25.0)

        # Gaps at: [0-5], [10-15], [20-25]
        assert len(result) == 3
        assert result[0] == (0.0, 5.0)
        assert result[1] == (10.0, 15.0)
        assert result[2] == (20.0, 25.0)

    def test_interval_at_start(self):
        """Test with interval starting at 0."""
        intervals = [(0.0, 10.0)]
        result = invert_intervals(intervals, total=20.0)

        # Only gap after: [10-20]
        assert len(result) == 1
        assert result[0] == (10.0, 20.0)

    def test_interval_at_end(self):
        """Test with interval ending at total."""
        intervals = [(10.0, 20.0)]
        result = invert_intervals(intervals, total=20.0)

        # Only gap before: [0-10]
        assert len(result) == 1
        assert result[0] == (0.0, 10.0)

    def test_full_coverage(self):
        """Test when intervals cover entire range."""
        intervals = [(0.0, 100.0)]
        result = invert_intervals(intervals, total=100.0)

        # No gaps
        assert result == []

    def test_overlapping_intervals(self):
        """Test with overlapping intervals."""
        intervals = [(5.0, 15.0), (10.0, 20.0)]
        result = invert_intervals(intervals, total=25.0)

        # Should handle overlap: coverage becomes [5-20]
        # Gaps: [0-5], [20-25]
        assert len(result) == 2
        assert result[0] == (0.0, 5.0)
        assert result[1] == (20.0, 25.0)

    def test_adjacent_intervals(self):
        """Test with adjacent intervals (no gap between)."""
        intervals = [(0.0, 10.0), (10.0, 20.0)]
        result = invert_intervals(intervals, total=20.0)

        # Full coverage, no gaps
        assert result == []

    def test_unsorted_intervals(self):
        """Test with unsorted input intervals."""
        intervals = [(15.0, 20.0), (5.0, 10.0)]
        result = invert_intervals(intervals, total=25.0)

        # Should sort internally
        # Gaps: [0-5], [10-15], [20-25]
        assert len(result) == 3

    def test_zero_total_duration(self):
        """Test with zero total duration."""
        intervals = []
        result = invert_intervals(intervals, total=0.0)

        assert result == [(0.0, 0.0)]

    def test_negative_intervals(self):
        """Test handling of negative interval values."""
        intervals = [(-5.0, 5.0)]
        result = invert_intervals(intervals, total=10.0)

        # Should handle gracefully
        # Coverage is [-5, 5], gaps are [5, 10]
        assert len(result) == 1
