"""Tests for AudioLoader class."""

import pytest
from pathlib import Path

from src.audio.loader import AudioLoader, AudioLoadError


class TestAudioLoader:
    """Tests for AudioLoader functionality."""

    def test_supported_formats(self):
        """Test that expected formats are supported."""
        loader = AudioLoader()
        formats = loader.get_supported_formats()

        assert "wav" in formats
        assert "mp3" in formats
        assert "flac" in formats
        assert "ogg" in formats
        assert "m4a" in formats
        assert "aac" in formats

    def test_init_default_parameters(self):
        """Test AudioLoader initialization with defaults."""
        loader = AudioLoader()

        assert loader.target_sample_rate is None
        assert loader.mono is True

    def test_init_custom_parameters(self):
        """Test AudioLoader initialization with custom parameters."""
        loader = AudioLoader(target_sample_rate=16000, mono=False)

        assert loader.target_sample_rate == 16000
        assert loader.mono is False

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading a file that doesn't exist."""
        loader = AudioLoader()
        nonexistent = temp_dir / "does_not_exist.wav"

        with pytest.raises(AudioLoadError, match="not found"):
            loader.load_audio(nonexistent)

    def test_load_unsupported_format(self, temp_dir):
        """Test loading an unsupported format."""
        loader = AudioLoader()
        unsupported = temp_dir / "test.xyz"

        # Create the file
        unsupported.write_text("fake content")

        with pytest.raises(AudioLoadError, match="Unsupported audio format"):
            loader.load_audio(unsupported)

    def test_load_valid_wav(self, sample_audio_5sec):
        """Test loading a valid WAV file."""
        loader = AudioLoader()
        audio_data, sample_rate = loader.load_audio(sample_audio_5sec)

        assert audio_data is not None
        assert sample_rate > 0
        assert len(audio_data) > 0

    def test_load_with_offset(self, sample_audio_5sec):
        """Test loading with offset parameter."""
        loader = AudioLoader()
        audio_data, sample_rate = loader.load_audio(sample_audio_5sec, offset=1.0)

        # Should load from 1 second onwards
        expected_samples = int(4.0 * sample_rate)  # 4 seconds remaining
        assert len(audio_data) == expected_samples

    def test_load_with_duration(self, sample_audio_5sec):
        """Test loading with duration parameter."""
        loader = AudioLoader()
        audio_data, sample_rate = loader.load_audio(sample_audio_5sec, duration=2.0)

        # Should load only 2 seconds
        expected_samples = int(2.0 * sample_rate)
        assert len(audio_data) == expected_samples

    def test_load_with_offset_and_duration(self, sample_audio_5sec):
        """Test loading with both offset and duration."""
        loader = AudioLoader()
        audio_data, sample_rate = loader.load_audio(
            sample_audio_5sec, offset=1.0, duration=2.0
        )

        # Should load 2 seconds starting from 1 second
        expected_samples = int(2.0 * sample_rate)
        assert len(audio_data) == expected_samples

    def test_get_audio_info(self, sample_audio_5sec):
        """Test getting audio file information."""
        loader = AudioLoader()
        info = loader.get_audio_info(sample_audio_5sec)

        assert "duration" in info
        assert "sample_rate" in info
        assert "channels" in info
        assert info["duration"] == 5.0  # 5 seconds
        assert info["sample_rate"] > 0

    def test_get_audio_info_nonexistent(self, temp_dir):
        """Test getting info for nonexistent file."""
        loader = AudioLoader()
        nonexistent = temp_dir / "does_not_exist.wav"

        with pytest.raises(AudioLoadError, match="not found"):
            loader.get_audio_info(nonexistent)

    def test_validate_audio_file_valid(self, sample_audio_5sec):
        """Test validation of valid audio file."""
        loader = AudioLoader()
        assert loader.validate_audio_file(sample_audio_5sec) is True

    def test_validate_audio_file_invalid(self, temp_dir):
        """Test validation of invalid file."""
        loader = AudioLoader()
        invalid = temp_dir / "invalid.txt"
        invalid.write_text("not audio")

        assert loader.validate_audio_file(invalid) is False

    def test_validate_audio_file_nonexistent(self, temp_dir):
        """Test validation of nonexistent file."""
        loader = AudioLoader()
        nonexistent = temp_dir / "does_not_exist.wav"

        assert loader.validate_audio_file(nonexistent) is False

    def test_estimate_loading_time_no_file(self, temp_dir):
        """Test loading time estimation with nonexistent file."""
        loader = AudioLoader()
        nonexistent = temp_dir / "does_not_exist.mp3"

        # Should return 0.0 for nonexistent file
        estimate = loader.estimate_loading_time(nonexistent)
        assert estimate == 0.0

    def test_estimate_loading_time_with_duration(self, sample_audio_5sec):
        """Test loading time estimation with known duration."""
        loader = AudioLoader()
        estimate = loader.estimate_loading_time(sample_audio_5sec, duration=5.0)

        # Should return a reasonable estimate (> 0)
        assert estimate >= 0.0

    def test_load_mono_conversion(self, sample_audio_5sec):
        """Test mono conversion on load."""
        loader = AudioLoader(mono=True)
        audio_data, sample_rate = loader.load_audio(sample_audio_5sec)

        # Mono audio should be 1D array
        assert audio_data.ndim == 1

    def test_load_stereo_conversion(self, sample_audio_5sec):
        """Test loading with stereo output."""
        loader = AudioLoader(mono=False)
        audio_data, sample_rate = loader.load_audio(sample_audio_5sec)

        # May be 1D or 2D depending on source
        assert audio_data.ndim in [1, 2]
