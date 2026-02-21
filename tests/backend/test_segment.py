"""Tests for segment data structures."""

from backend.core.segment import ProgressInfo, Segment, TranscriptionResult, Word


class TestSegment:
    def test_basic_segment(self):
        seg = Segment(start=1.0, end=3.5, text="Hello world")
        assert seg.start == 1.0
        assert seg.end == 3.5
        assert seg.text == "Hello world"
        assert seg.speaker is None
        assert seg.duration == 2.5

    def test_segment_with_speaker(self):
        seg = Segment(start=0, end=2, text="Test", speaker="Speaker 1")
        assert seg.speaker == "Speaker 1"

    def test_segment_with_words(self):
        words = [
            Word(text="Hello", start=1.0, end=1.5, confidence=0.95),
            Word(text="world", start=1.6, end=2.0, confidence=0.88),
        ]
        seg = Segment(start=1.0, end=2.0, text="Hello world", words=words)
        assert len(seg.words) == 2
        assert seg.words[0].confidence == 0.95

    def test_srt_timestamp_format(self):
        seg = Segment(start=3661.5, end=3665.0, text="Test")
        assert seg.format_timestamp_srt(3661.5) == "01:01:01,500"

    def test_vtt_timestamp_format(self):
        seg = Segment(start=3661.5, end=3665.0, text="Test")
        assert seg.format_timestamp_vtt(3661.5) == "01:01:01.500"

    def test_to_srt_block(self):
        seg = Segment(start=1.0, end=3.0, text="Hello")
        block = seg.to_srt_block(1)
        assert "1\n" in block
        assert "00:00:01,000 --> 00:00:03,000" in block
        assert "Hello" in block

    def test_to_srt_block_with_speaker(self):
        seg = Segment(start=0, end=2, text="Hello", speaker="Bob")
        block = seg.to_srt_block(1)
        assert "[Bob]: Hello" in block

    def test_translated_text_in_srt(self):
        seg = Segment(start=0, end=2, text="Hello", translated_text="Xin chào")
        block = seg.to_srt_block(1)
        assert "Xin chào" in block
        assert "Hello" not in block


class TestTranscriptionResult:
    def test_basic_result(self):
        segs = [
            Segment(start=0, end=1, text="Hello"),
            Segment(start=2, end=3, text="world"),
        ]
        result = TranscriptionResult(segments=segs, language="en", language_confidence=0.95, duration=5.0)
        assert result.language == "en"
        assert result.segment_count == 2
        assert result.text == "Hello world"
        assert result.duration == 5.0


class TestProgressInfo:
    def test_to_dict(self):
        info = ProgressInfo(
            step="Transcribing",
            step_number=2,
            total_steps=5,
            progress_percent=42.567,
            message="Processing...",
        )
        d = info.to_dict()
        assert d["step"] == "Transcribing"
        assert d["step_number"] == 2
        assert d["total_steps"] == 5
        assert d["progress_percent"] == 42.6  # rounded
        assert d["message"] == "Processing..."
        assert d["eta_seconds"] is None
