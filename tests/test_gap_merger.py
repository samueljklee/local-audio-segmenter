"""Tests for gap-based segment merging algorithm."""

import sys
from pathlib import Path

import pytest

# Add tools to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.build_segments_from_transcript import merge_segments_by_gap


class TestMergeSegmentsByGap:
    """Tests for the gap-based segment merging function."""

    def test_empty_segments(self):
        """Test with empty segment list."""
        result = merge_segments_by_gap([], gap_threshold=3.0, min_length=60.0)
        assert result == []

    def test_single_segment(self):
        """Test with single segment (no merging possible)."""
        segments = [{"start": 0.0, "end": 5.0, "text": "Hello"}]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=60.0)

        assert len(result) == 1
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 5.0
        assert result[0]["type"] == "speech"

    def test_merge_small_gaps(self):
        """Test merging segments with small gaps."""
        segments = [
            {"start": 0.0, "end": 2.5, "text": "Hello"},
            {"start": 2.6, "end": 5.0, "text": "world"},  # 0.1s gap
        ]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=60.0)

        # Should merge since gap (0.1) < threshold (3.0)
        assert len(result) == 1
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 5.0

    def test_no_merge_large_gaps(self):
        """Test that segments with large gaps are not merged by gap threshold."""
        # Use smaller segments to avoid min_length enforcement
        segments = [
            {"start": 0.0, "end": 120.0, "text": "Hello"},  # 2 minutes
            {"start": 125.0, "end": 240.0, "text": "world"},  # 5s gap, both > min_length
        ]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=60.0)

        # Should NOT merge since gap (5.0) > threshold (3.0)
        assert len(result) == 2
        assert result[0]["end"] == 120.0
        assert result[1]["start"] == 125.0

    def test_exact_threshold_boundary(self):
        """Test boundary condition where gap equals threshold."""
        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 5.0, "end": 7.0, "text": "world"},  # Exactly 3.0s gap
        ]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=60.0)

        # Should merge since gap (3.0) <= threshold (3.0)
        assert len(result) == 1
        assert result[0]["end"] == 7.0

    def test_min_length_enforcement(self):
        """Test that short segments are merged into neighbors."""
        segments = [
            {"start": 0.0, "end": 30.0, "text": "Long segment"},
            {"start": 30.0, "end": 35.0, "text": "Short"},  # 5 seconds
            {"start": 35.0, "end": 70.0, "text": "Another long"},
        ]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=60.0)

        # First segment (30s) gets merged into second
        # [0-30] + [30-35] = [0-35] (35s, still < 60s)
        # [0-35] gets merged into [35-70] = [0-70] (70s, >= 60s)
        # Result should have 1 segment: [0-70]
        assert len(result) == 1
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 70.0

    def test_complex_merging_scenario(self):
        """Test a complex scenario with multiple gaps and min-length enforcement."""
        segments = [
            {"start": 0.0, "end": 2.0, "text": "A"},
            {"start": 2.1, "end": 4.0, "text": "B"},  # 0.1s gap
            {"start": 10.0, "end": 12.0, "text": "C"},  # 6s gap
            {"start": 12.1, "end": 14.0, "text": "D"},  # 0.1s gap
        ]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=5.0)

        # Gap-based merge: A-B -> [0-4], C-D -> [10-14]
        # Min-length enforcement: [0-4] is 4s < 5s, so it modifies next segment's start
        # [0-4] modifies [10-14] to become [0-14]
        # Then [0-14] has duration 14s >= 5s, so it's kept
        # Result: [0-14]
        assert len(result) == 1
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 14.0

    def test_overlapping_segments(self):
        """Test handling of overlapping segments."""
        segments = [
            {"start": 0.0, "end": 5.0, "text": "First"},
            {"start": 4.0, "end": 8.0, "text": "Second"},  # Overlaps by 1s
        ]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=60.0)

        # Should merge and extend end to max
        assert len(result) == 1
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 8.0  # Extended to max end

    def test_all_segments_below_min_length(self):
        """Test when all segments are below minimum length."""
        segments = [
            {"start": 0.0, "end": 10.0, "text": "A"},
            {"start": 10.0, "end": 20.0, "text": "B"},
            {"start": 20.0, "end": 25.0, "text": "C"},
        ]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=60.0)

        # All segments get merged together into [0-25]
        assert len(result) == 1
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 25.0

    def test_preserves_type_field(self):
        """Test that type field is set correctly."""
        segments = [{"start": 0.0, "end": 5.0, "text": "Hello"}]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=60.0)

        assert result[0]["type"] == "speech"

    def test_negative_gap_threshold(self):
        """Test with negative gap threshold (segments don't merge)."""
        segments = [
            {"start": 0.0, "end": 2.0, "text": "A"},
            {"start": 2.1, "end": 4.0, "text": "B"},
        ]
        result = merge_segments_by_gap(segments, gap_threshold=-1.0, min_length=60.0)

        # With negative threshold, 0.1s gap doesn't merge (-1.0 is very small)
        # But then min_length enforcement kicks in...
        # Actually, gap_threshold check: gap (0.1) <= threshold (-1.0) is False
        # So they don't merge in first pass, we get [0-2], [2.1-4]
        # Then min_length: [0-2] is 2s < 60s, merges into [2.1-4] -> [0-4]
        # Result is 1 segment
        assert len(result) == 1

    def test_zero_min_length(self):
        """Test with zero minimum length."""
        segments = [
            {"start": 0.0, "end": 1.0, "text": "A"},
            {"start": 2.0, "end": 2.5, "text": "B"},
            {"start": 3.0, "end": 3.2, "text": "C"},
        ]
        result = merge_segments_by_gap(segments, gap_threshold=3.0, min_length=0.0)

        # With min_length=0, gap merging still applies
        # Gaps: 1.0s and 0.5s, both < 3.0, so all merge
        assert len(result) == 1
