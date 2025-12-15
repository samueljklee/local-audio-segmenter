"""Speech-to-Text module using Whisper."""

import logging
import tempfile
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

import numpy as np
import soundfile as sf
import whisper

from .transcript import Transcript, TranscriptSegment

logger = logging.getLogger(__name__)


class STTModule:
    """Local Speech-to-Text transcription using Whisper."""

    def __init__(
        self,
        model_size: str = "base",
        device: Optional[str] = None,
        language: Optional[str] = None
    ):
        """
        Initialize STT module.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to run model on (cpu, cuda, mps)
            language: Language code (e.g., 'en', 'es', 'fr')
        """
        self.model_size = model_size
        self.device = device
        self.language = language
        self._model = None

    @property
    def model(self) -> whisper.Whisper:
        """Load Whisper model lazily."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = whisper.load_model(
                self.model_size,
                device=self.device
            )
            logger.info("Whisper model loaded successfully")
        return self._model

    def transcribe_file(
        self,
        audio_path: str,
        beam_size: int = 5,
        best_of: int = 5,
        temperature: float = 0.0,
        no_speech_threshold: float = 0.6
    ) -> Transcript:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            beam_size: Beam size for decoding
            best_of: Number of candidates when sampling
            temperature: Temperature for sampling
            no_speech_threshold: Threshold for no-speech detection

        Returns:
            Transcript object with transcription results
        """
        logger.info(f"Transcribing audio file: {audio_path}")

        # Prepare transcription options
        options = {
            'beam_size': beam_size,
            'best_of': best_of,
            'temperature': temperature,
            'no_speech_threshold': no_speech_threshold,
            'fp16': False  # Disable FP16 for compatibility
        }

        # Add language if specified
        if self.language:
            options['language'] = self.language

        try:
            # Transcribe using Whisper
            result = self.model.transcribe(audio_path, **options)

            # Convert to transcript format
            transcript = self._whisper_result_to_transcript(result)

            logger.info(
                f"Transcription complete: {len(transcript.segments)} segments, "
                f"{transcript.word_count or 0} words"
            )

            return transcript

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Speech-to-Text transcription failed: {e}")

    def transcribe_array(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        beam_size: int = 5,
        best_of: int = 5,
        temperature: float = 0.0,
        no_speech_threshold: float = 0.6
    ) -> Transcript:
        """
        Transcribe audio array.

        Args:
            audio_data: Audio signal as numpy array
            sample_rate: Sample rate in Hz
            beam_size: Beam size for decoding
            best_of: Number of candidates when sampling
            temperature: Temperature for sampling
            no_speech_threshold: Threshold for no-speech detection

        Returns:
            Transcript object with transcription results
        """
        logger.info(f"Transcribing audio array: {len(audio_data)} samples at {sample_rate}Hz")

        # Resample audio to 16kHz if needed (Whisper requirement)
        if sample_rate != 16000:
            import librosa
            audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
            sample_rate = 16000
            logger.debug("Resampled audio to 16kHz for Whisper")

        # Save to temporary WAV file using soundfile (doesn't require ffmpeg)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name

        try:
            # Save audio as WAV file
            sf.write(temp_path, audio_data, 16000)  # Always 16kHz for Whisper
            logger.debug(f"Saved audio to temporary file: {temp_path}")

            # Transcribe the temporary file
            transcript = self.transcribe_file(
                temp_path,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                no_speech_threshold=no_speech_threshold
            )

            return transcript

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
                logger.debug(f"Cleaned up temporary file: {temp_path}")
            except OSError:
                pass

    def detect_language(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """
        Detect spoken language in audio.

        Args:
            audio_data: Audio signal as numpy array
            sample_rate: Sample rate in Hz

        Returns:
            Language code (e.g., 'en', 'es', 'fr') or None
        """
        logger.info("Detecting language in audio")

        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name

        try:
            # Save audio as WAV file
            sf.write(temp_path, audio_data, sample_rate)

            # Load audio and detect language
            audio = whisper.load_audio(temp_path)
            result = self.model.transcribe(audio, fp16=False)

            detected_language = result.get('language')
            logger.info(f"Detected language: {detected_language}")

            return detected_language

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return None

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _whisper_result_to_transcript(self, result: Dict[str, Any]) -> Transcript:
        """Convert Whisper result to Transcript object."""
        segments = []

        for segment in result.get('segments', []):
            transcript_segment = TranscriptSegment(
                start_time=segment['start'],
                end_time=segment['end'],
                text=segment['text'].strip(),
                confidence=segment.get('avg_logprob', 0.0),
                language=result.get('language')
            )
            segments.append(transcript_segment)

        transcript = Transcript.from_segments(segments)
        transcript.language = result.get('language')

        # Add Whisper metadata
        transcript.metadata = {
            'model_size': self.model_size,
            'whisper_language': result.get('language'),
            'whisper_all_languages': result.get('all_language_probs', {}),
            'processing_time': result.get('timings', {})
        }

        return transcript

    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages."""
        # Whisper supported languages
        return {
            'en': 'English',
            'zh': 'Chinese',
            'de': 'German',
            'es': 'Spanish',
            'ru': 'Russian',
            'ko': 'Korean',
            'fr': 'French',
            'ja': 'Japanese',
            'pt': 'Portuguese',
            'tr': 'Turkish',
            'pl': 'Polish',
            'ca': 'Catalan',
            'nl': 'Dutch',
            'ar': 'Arabic',
            'sv': 'Swedish',
            'it': 'Italian',
            'id': 'Indonesian',
            'hi': 'Hindi',
            'fi': 'Finnish',
            'vi': 'Vietnamese',
            'he': 'Hebrew',
            'uk': 'Ukrainian',
            'el': 'Greek',
            'ms': 'Malay',
            'cs': 'Czech',
            'ro': 'Romanian',
            'da': 'Danish',
            'hu': 'Hungarian',
            'ta': 'Tamil',
            'no': 'Norwegian',
            'th': 'Thai',
            'ur': 'Urdu',
            'hr': 'Croatian',
            'bg': 'Bulgarian',
            'lt': 'Lithuanian',
            'la': 'Latin',
            'mi': 'Maori',
            'ml': 'Malayalam',
            'cy': 'Welsh',
            'sk': 'Slovak',
            'te': 'Telugu',
            'fa': 'Persian',
            'lv': 'Latvian',
            'bn': 'Bengali',
            'sr': 'Serbian',
            'az': 'Azerbaijani',
            'sl': 'Slovenian',
            'kn': 'Kannada',
            'et': 'Estonian',
            'mk': 'Macedonian',
            'br': 'Breton',
            'eu': 'Basque',
            'is': 'Icelandic',
            'hy': 'Armenian',
            'ne': 'Nepali',
            'mn': 'Mongolian',
            'bs': 'Bosnian',
            'kk': 'Kazakh',
            'sq': 'Albanian',
            'sw': 'Swahili',
            'gl': 'Galician',
            'mr': 'Marathi',
            'pa': 'Punjabi',
            'si': 'Sinhala',
            'km': 'Khmer',
            'sn': 'Shona',
            'yo': 'Yoruba',
            'so': 'Somali',
            'af': 'Afrikaans',
            'oc': 'Occitan',
            'ka': 'Georgian',
            'be': 'Belarusian',
            'tg': 'Tajik',
            'sd': 'Sindhi',
            'gu': 'Gujarati',
            'am': 'Amharic',
            'yi': 'Yiddish',
            'lo': 'Lao',
            'uz': 'Uzbek',
            'fo': 'Faroese',
            'ht': 'Haitian Creole',
            'ps': 'Pashto',
            'tk': 'Turkmen',
            'nn': 'Nynorsk',
            'mt': 'Maltese',
            'sa': 'Sanskrit',
            'lb': 'Luxembourgish',
            'my': 'Myanmar',
            'bo': 'Tibetan',
            'tl': 'Tagalog',
            'mg': 'Malagasy',
            'as': 'Assamese',
            'tt': 'Tatar',
            'haw': 'Hawaiian',
            'ln': 'Lingala',
            'ha': 'Hausa',
            'ba': 'Bashkir',
            'jw': 'Javanese',
            'su': 'Sundanese'
        }

    def cleanup(self):
        """Cleanup resources."""
        if self._model is not None:
            # Clear model from memory
            del self._model
            self._model = None
            logger.info("Whisper model cleared from memory")