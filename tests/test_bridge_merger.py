"""Tests for bridge merging algorithm."""

import sys
from pathlib import Path

import pytest

# Add tools to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.build_segments_from_transcript import merge_bridged_segments


class TestMergeBridgedSegments:
    """Tests for the A-B-A pattern bridge merging function."""

    def test_empty_segments(self):
        """Test with empty segment list."""
        result = merge_bridged_segments([], bridge_type="speech", max_bridge_duration=30.0)
        assert result == []

    def test_single_segment(self):
        """Test with single segment (no bridge possible)."""
        segments = [{"start": 0.0, "end": 60.0, "type": "speech"}]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=30.0)

        assert len(result) == 1
        assert result[0] == segments[0]

    def test_two_segments(self):
        """Test with two segments (no A-B-A pattern possible)."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 30.0, "end": 60.0, "type": "speech"},
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=30.0)

        # No A-B-A pattern, should remain unchanged
        assert len(result) == 2

    def test_simple_aba_merge(self):
        """Test simple A-B-A pattern merging."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 30.0, "end": 40.0, "type": "speech"},  # 10s bridge
            {"start": 40.0, "end": 120.0, "type": "music"},
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=30.0)

        # Should merge into single music segment
        assert len(result) == 1
        assert result[0]["type"] == "music"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 120.0

    def test_bridge_too_long(self):
        """Test that bridges longer than max_duration are not merged."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 30.0, "end": 80.0, "type": "speech"},  # 50s bridge
            {"start": 80.0, "end": 120.0, "type": "music"},
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=30.0)

        # Should NOT merge (bridge 50s > max 30s)
        assert len(result) == 3

    def test_wrong_bridge_type(self):
        """Test that only specified bridge type is merged."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 30.0, "end": 40.0, "type": "silence"},  # Wrong type
            {"start": 40.0, "end": 120.0, "type": "music"},
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=30.0)

        # Should NOT merge (bridge is silence, not speech)
        assert len(result) == 3

    def test_different_outer_types(self):
        """Test that A-B-A requires same outer types."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 30.0, "end": 40.0, "type": "speech"},
            {"start": 40.0, "end": 120.0, "type": "silence"},  # Different type
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=30.0)

        # Should NOT merge (outer types differ)
        assert len(result) == 3

    def test_multiple_consecutive_bridges(self):
        """Test multiple A-B-A patterns in sequence."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 30.0, "end": 40.0, "type": "speech"},
            {"start": 40.0, "end": 70.0, "type": "music"},
            {"start": 70.0, "end": 90.0, "type": "speech"},
            {"start": 90.0, "end": 120.0, "type": "music"},
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=30.0)

        # The algorithm processes sequentially:
        # i=0: A(0-30,music)-B(30-40,speech)-A(40-70,music) -> merge to [0-70], i+=3
        # i=3: B(70-90,speech) -> no A-B-A, add as-is, i+=1
        # i=4: A(90-120,music) -> no A-B-A, add as-is, i+=1
        # Result: [0-70, music], [70-90, speech], [90-120, music]
        assert len(result) == 3

    def test_exact_boundary_duration(self):
        """Test boundary where bridge duration equals max."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 30.0, "end": 60.0, "type": "speech"},  # Exactly 30s
            {"start": 60.0, "end": 120.0, "type": "music"},
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=30.0)

        # Should merge (30s <= 30s max)
        assert len(result) == 1
        assert result[0]["end"] == 120.0

    def test_nested_patterns(self):
        """Test with more complex patterns."""
        segments = [
            {"start": 0.0, "end": 20.0, "type": "speech"},
            {"start": 20.0, "end": 25.0, "type": "music"},
            {"start": 25.0, "end": 45.0, "type": "speech"},
            {"start": 45.0, "end": 60.0, "type": "silence"},
            {"start": 60.0, "end": 80.0, "type": "speech"},
        ]
        result = merge_bridged_segments(segments, bridge_type="music", max_bridge_duration=30.0)

        # speech-music-speech at [0-45] should merge with bridge_type="music"
        # silence-speech won't merge (wrong bridge type)
        assert len(result) == 3

    def test_overlapping_segments(self):
        """Test handling of overlapping segments in bridge."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 25.0, "end": 50.0, "type": "speech"},  # Overlaps
            {"start": 45.0, "end": 90.0, "type": "music"},
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=30.0)

        # Bridge duration: 50-25=25s, should merge
        assert len(result) == 1
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 90.0

    def test_music_bridge_type(self):
        """Test merging with music as bridge type."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "speech"},
            {"start": 30.0, "end": 40.0, "type": "music"},  # Bridge
            {"start": 40.0, "end": 70.0, "type": "speech"},
        ]
        result = merge_bridged_segments(segments, bridge_type="music", max_bridge_duration=30.0)

        # Should merge speech-music-speech into single speech segment
        assert len(result) == 1
        assert result[0]["type"] == "speech"

    def test_zero_max_duration(self):
        """Test with zero max bridge duration."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 30.0, "end": 30.1, "type": "speech"},  # 0.1s
            {"start": 30.1, "end": 60.0, "type": "music"},
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=0.0)

        # Bridge duration: 30.1 - 30 = 0.1s
        # 0.1s is NOT <= 0.0s, so should NOT merge
        assert len(result) == 3

    def test_very_long_max_duration(self):
        """Test with very large max bridge duration."""
        segments = [
            {"start": 0.0, "end": 30.0, "type": "music"},
            {"start": 30.0, "end": 300.0, "type": "speech"},  # 4.5 minutes
            {"start": 300.0, "end": 360.0, "type": "music"},
        ]
        result = merge_bridged_segments(segments, bridge_type="speech", max_bridge_duration=600.0)

        # Should merge with huge max duration
        assert len(result) == 1
        assert result[0]["end"] == 360.0
