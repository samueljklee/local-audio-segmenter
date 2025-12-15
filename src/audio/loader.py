"""Audio file loading utilities."""

import logging
from pathlib import Path
from typing import Optional, Tuple, Union

import librosa
import numpy as np
from pydub import AudioSegment


logger = logging.getLogger(__name__)


class AudioLoadError(Exception):
    """Raised when audio file loading fails."""
    pass


class AudioLoader:
    """Handles loading audio files in various formats."""

    SUPPORTED_FORMATS = ['wav', 'mp3', 'flac', 'ogg', 'm4a', 'aac']

    def __init__(self, target_sample_rate: Optional[int] = None, mono: bool = True):
        """
        Initialize audio loader.

        Args:
            target_sample_rate: Target sample rate (None to keep original)
            mono: Whether to convert to mono
        """
        self.target_sample_rate = target_sample_rate
        self.mono = mono

    def load_audio(
        self,
        file_path: Union[str, Path],
        offset: float = 0.0,
        duration: Optional[float] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Load audio file.

        Args:
            file_path: Path to audio file
            offset: Start time in seconds
            duration: Duration to load in seconds (None for entire file)

        Returns:
            Tuple of (audio_data, sample_rate)

        Raises:
            AudioLoadError: If loading fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise AudioLoadError(f"Audio file not found: {file_path}")

        if file_path.suffix.lower()[1:] not in self.SUPPORTED_FORMATS:
            raise AudioLoadError(f"Unsupported audio format: {file_path.suffix}")

        try:
            # Use librosa for primary loading (better for analysis)
            audio_data, sample_rate = librosa.load(
                str(file_path),
                sr=self.target_sample_rate,
                mono=self.mono,
                offset=offset,
                duration=duration,
            )

            logger.info(f"Loaded audio: {file_path.name}, shape: {audio_data.shape}, "
                       f"sample_rate: {sample_rate}, duration: {len(audio_data)/sample_rate:.2f}s")

            return audio_data, sample_rate

        except Exception as e:
            logger.warning(f"librosa failed to load {file_path}, trying pydub: {e}")

            try:
                # Fallback to pydub for formats librosa doesn't handle well
                audio_segment = AudioSegment.from_file(str(file_path))

                # Convert to mono if requested
                if self.mono and audio_segment.channels > 1:
                    audio_segment = audio_segment.set_channels(1)

                # Resample if needed
                if self.target_sample_rate and audio_segment.frame_rate != self.target_sample_rate:
                    audio_segment = audio_segment.set_frame_rate(self.target_sample_rate)

                # Convert to numpy array
                samples = np.array(audio_segment.get_array_of_samples())
                if audio_segment.channels == 2:
                    samples = samples.reshape((-1, 2))

                # Normalize to [-1, 1] range
                audio_data = samples / np.iinfo(samples.dtype).max
                sample_rate = audio_segment.frame_rate

                # Apply offset and duration if specified
                if offset > 0:
                    start_sample = int(offset * sample_rate)
                    audio_data = audio_data[start_sample:]

                if duration is not None:
                    end_sample = int(duration * sample_rate)
                    audio_data = audio_data[:end_sample]

                return audio_data, sample_rate

            except Exception as e2:
                raise AudioLoadError(f"Failed to load audio file {file_path}: {e2}")

    def get_audio_info(self, file_path: Union[str, Path]) -> dict:
        """
        Get information about an audio file without loading the full data.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with audio information
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise AudioLoadError(f"Audio file not found: {file_path}")

        try:
            # Try to get info using pydub first (faster)
            try:
                audio_segment = AudioSegment.from_file(str(file_path))
                return {
                    'duration': len(audio_segment) / 1000.0,  # Convert ms to seconds
                    'sample_rate': audio_segment.frame_rate,
                    'channels': audio_segment.channels,
                    'sample_width': audio_segment.sample_width,
                    'frame_count': audio_segment.frame_count(),
                    'file_size': file_path.stat().st_size,
                }
            except Exception:
                pass

            # Fallback to librosa
            audio_data, sample_rate = librosa.load(str(file_path), sr=None, mono=False)
            return {
                'duration': len(audio_data) / sample_rate if audio_data.ndim == 1 else len(audio_data[0]) / sample_rate,
                'sample_rate': sample_rate,
                'channels': 1 if audio_data.ndim == 1 else audio_data.shape[0],
                'sample_width': None,  # Not available from librosa
                'frame_count': len(audio_data) if audio_data.ndim == 1 else len(audio_data[0]),
                'file_size': file_path.stat().st_size,
            }

        except Exception as e:
            raise AudioLoadError(f"Failed to get audio info for {file_path}: {e}")

    def validate_audio_file(self, file_path: Union[str, Path]) -> bool:
        """
        Validate that a file is a valid audio file.

        Args:
            file_path: Path to file to validate

        Returns:
            True if valid audio file, False otherwise
        """
        try:
            self.get_audio_info(file_path)
            return True
        except (AudioLoadError, Exception):
            return False

    @staticmethod
    def get_supported_formats() -> list:
        """Get list of supported audio formats."""
        return AudioLoader.SUPPORTED_FORMATS.copy()

    @staticmethod
    def estimate_loading_time(file_path: Union[str, Path], duration: Optional[float] = None) -> float:
        """
        Estimate audio loading time based on file size and duration.

        Args:
            file_path: Path to audio file
            duration: Duration in seconds (if known)

        Returns:
            Estimated loading time in seconds
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return 0.0

        file_size_mb = file_path.stat().st_size / (1024 * 1024)

        if duration is None:
            # Rough estimate: 1 MB takes about 0.1 seconds to load
            return file_size_mb * 0.1
        else:
            # Consider duration and compression
            # Uncompressed audio: ~10 MB per minute
            # Compressed audio: ~1 MB per minute
            estimated_size_per_min = file_size_mb / max(duration / 60, 0.0167)  # Avoid division by very small numbers

            if estimated_size_per_min > 5:  # Likely uncompressed
                return duration * 0.01  # 1% of duration
            else:  # Likely compressed
                return duration * 0.02 + file_size_mb * 0.05  # Decompression overhead + file size factor