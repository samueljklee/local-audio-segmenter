"""Integration tests for the full workflow."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, Mock

import pytest

# Add tools to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntegrationWorkflow:
    """Integration tests for the complete segmentation workflow."""

    def test_full_workflow_with_real_audio(self, sample_audio_with_music_silence, temp_dir):
        """Test the complete workflow with real audio file."""
        # This would require Whisper model, so we mock it
        # But we test the other components

        from tools.build_segments_from_transcript import build_segments

        # Create a mock transcript
        transcript_path = temp_dir / "transcript.json"
        transcript_data = {
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "Hello"},
                {"start": 1.6, "end": 2.0, "text": "world"},
            ]
        }
        with transcript_path.open("w") as f:
            json.dump(transcript_data, f)

        # Build segments
        segments = build_segments(
            transcript_path=transcript_path,
            audio_path=sample_audio_with_music_silence,
            gap_threshold=3.0,
            min_length=60.0,
            merge_bridges=False,
        )

        # Should have speech segments and classified gaps
        assert len(segments) > 0
        assert all("start" in s for s in segments)
        assert all("end" in s for s in segments)
        assert all("type" in s for s in segments)

    def test_transcript_to_segments_to_export(self, sample_transcript_json, sample_audio_5sec, temp_dir):
        """Test workflow from transcript through segment building."""
        from tools.build_segments_from_transcript import build_segments, write_segments

        output_path = temp_dir / "segments.json"

        segments = build_segments(
            transcript_path=sample_transcript_json,
            audio_path=sample_audio_5sec,
            gap_threshold=3.0,
            min_length=60.0,
            merge_bridges=False,
        )

        write_segments(output_path, segments)

        # Verify output file was created
        assert output_path.exists()

        # Verify content
        with output_path.open("r") as f:
            data = json.load(f)

        assert "segments" in data
        assert len(data["segments"]) > 0

    def test_gap_merging_integration(self, sample_transcript_json, sample_audio_5sec):
        """Test gap merging as part of full workflow."""
        from tools.build_segments_from_transcript import build_segments

        # Test with different gap thresholds
        segments_strict = build_segments(
            transcript_path=sample_transcript_json,
            audio_path=sample_audio_5sec,
            gap_threshold=1.0,  # Strict
            min_length=60.0,
            merge_bridges=False,
        )

        segments_lenient = build_segments(
            transcript_path=sample_transcript_json,
            audio_path=sample_audio_5sec,
            gap_threshold=10.0,  # Lenient
            min_length=60.0,
            merge_bridges=False,
        )

        # Lenient threshold should produce fewer segments
        assert len(segments_lenient) <= len(segments_strict)

    def test_bridge_merging_integration(self, sample_transcript_json, sample_audio_5sec):
        """Test bridge merging in full workflow."""
        from tools.build_segments_from_transcript import build_segments

        segments_no_bridge = build_segments(
            transcript_path=sample_transcript_json,
            audio_path=sample_audio_5sec,
            gap_threshold=3.0,
            min_length=60.0,
            merge_bridges=False,
        )

        segments_with_bridge = build_segments(
            transcript_path=sample_transcript_json,
            audio_path=sample_audio_5sec,
            gap_threshold=3.0,
            min_length=60.0,
            merge_bridges=True,
            bridge_type="speech",
            bridge_max_duration=60.0,
        )

        # With bridge merging, should have same or fewer segments
        assert len(segments_with_bridge) <= len(segments_no_bridge)

    def test_energy_classification_integration(self, sample_audio_with_music_silence, temp_dir):
        """Test energy classification of non-speech regions."""
        from tools.build_segments_from_transcript import build_segments

        # Create transcript with speech in first section only
        transcript_path = temp_dir / "transcript.json"
        transcript_data = {
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello"},
            ]
        }
        with transcript_path.open("w") as f:
            json.dump(transcript_data, f)

        segments = build_segments(
            transcript_path=transcript_path,
            audio_path=sample_audio_with_music_silence,
            gap_threshold=3.0,
            min_length=10.0,
            merge_bridges=False,
        )

        # Should classify gaps as music or silence
        gap_segments = [s for s in segments if s["type"] in ["music", "silence"]]
        assert len(gap_segments) > 0

    def test_invalid_transcript_handling(self, invalid_json_path, sample_audio_5sec):
        """Test handling of invalid transcript file."""
        from tools.build_segments_from_transcript import load_transcript, TranscriptLoadError

        # Invalid JSON raises TranscriptLoadError
        with pytest.raises(TranscriptLoadError):
            load_transcript(invalid_json_path)

    def test_empty_transcript(self, temp_dir, sample_audio_5sec):
        """Test handling of empty transcript."""
        from tools.build_segments_from_transcript import build_segments, TranscriptLoadError

        transcript_path = temp_dir / "empty.json"
        with transcript_path.open("w") as f:
            json.dump({"segments": []}, f)

        # Empty transcript raises TranscriptLoadError
        with pytest.raises(TranscriptLoadError, match="No valid segments"):
            build_segments(
                transcript_path=transcript_path,
                audio_path=sample_audio_5sec,
                gap_threshold=3.0,
                min_length=60.0,
                merge_bridges=False,
            )

    def test_segments_json_format(self, sample_transcript_json, sample_audio_5sec, temp_dir):
        """Test that segments JSON has expected format."""
        from tools.build_segments_from_transcript import build_segments, write_segments

        output_path = temp_dir / "segments.json"

        segments = build_segments(
            transcript_path=sample_transcript_json,
            audio_path=sample_audio_5sec,
            gap_threshold=3.0,
            min_length=60.0,
            merge_bridges=False,
        )

        write_segments(output_path, segments)

        with output_path.open("r") as f:
            data = json.load(f)

        # Verify required fields
        assert "segments" in data
        for segment in data["segments"]:
            assert "start" in segment
            assert "end" in segment
            assert "type" in segment
            assert segment["end"] >= segment["start"]

    def test_segment_types_are_valid(self, sample_transcript_json, sample_audio_5sec):
        """Test that all segment types are valid."""
        from tools.build_segments_from_transcript import build_segments

        valid_types = {"speech", "music", "silence"}

        segments = build_segments(
            transcript_path=sample_transcript_json,
            audio_path=sample_audio_5sec,
            gap_threshold=3.0,
            min_length=60.0,
            merge_bridges=False,
        )

        for segment in segments:
            assert segment["type"] in valid_types, f"Invalid type: {segment['type']}"
