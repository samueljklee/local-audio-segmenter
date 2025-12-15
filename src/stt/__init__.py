"""Speech-to-Text module for local transcription."""

from .module import STTModule
from .transcript import Transcript, TranscriptSegment

__all__ = ['STTModule', 'Transcript', 'TranscriptSegment']