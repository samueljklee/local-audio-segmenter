"""Transcript data structures."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import timedelta


@dataclass
class TranscriptSegment:
    """Single segment of transcribed speech."""

    start_time: float
    end_time: float
    text: str
    confidence: float
    language: Optional[str] = None
    speaker: Optional[str] = None

    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return self.end_time - self.start_time

    def __str__(self) -> str:
        """String representation of the segment."""
        start_str = str(timedelta(seconds=int(self.start_time)))
        return f"[{start_str}] {self.text}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary."""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'text': self.text,
            'confidence': self.confidence,
            'language': self.language,
            'speaker': self.speaker
        }


@dataclass
class Transcript:
    """Complete transcript with metadata."""

    segments: List[TranscriptSegment]
    language: Optional[str] = None
    total_duration: Optional[float] = None
    word_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_segments(cls, segments: List[TranscriptSegment]) -> 'Transcript':
        """Create transcript from list of segments."""
        if not segments:
            return cls(segments=[], total_duration=0.0, word_count=0)

        total_duration = max(seg.end_time for seg in segments)
        word_count = sum(len(seg.text.split()) for seg in segments)

        return cls(
            segments=segments,
            total_duration=total_duration,
            word_count=word_count
        )

    @property
    def text(self) -> str:
        """Get full transcript text."""
        return ' '.join(seg.text for seg in self.segments)

    def get_segment_at_time(self, time: float) -> Optional[TranscriptSegment]:
        """Get transcript segment at specific time."""
        for segment in self.segments:
            if segment.start_time <= time <= segment.end_time:
                return segment
        return None

    def filter_segments_by_confidence(self, min_confidence: float) -> 'Transcript':
        """Create new transcript with only high-confidence segments."""
        filtered_segments = [
            seg for seg in self.segments
            if seg.confidence >= min_confidence
        ]
        return Transcript.from_segments(filtered_segments)

    def to_dict(self) -> Dict[str, Any]:
        """Convert transcript to dictionary."""
        return {
            'segments': [seg.to_dict() for seg in self.segments],
            'language': self.language,
            'total_duration': self.total_duration,
            'word_count': self.word_count,
            'text': self.text,
            'metadata': self.metadata or {}
        }

    def to_srt(self) -> str:
        """Convert transcript to SRT subtitle format."""
        srt_content = []
        for i, segment in enumerate(self.segments, 1):
            start_time = self._format_srt_time(segment.start_time)
            end_time = self._format_srt_time(segment.end_time)

            srt_content.append(f"{i}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(segment.text)
            srt_content.append("")  # Empty line between entries

        return "\n".join(srt_content)

    def _format_srt_time(self, seconds: float) -> str:
        """Format time in SRT format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"