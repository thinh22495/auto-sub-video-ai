"""Tests for diarizer logic (speaker assignment, no pyannote needed)."""

from backend.core.diarizer import assign_speakers_to_segments
from backend.core.segment import Segment


class TestAssignSpeakers:
    def test_basic_assignment(self):
        segments = [
            Segment(start=0, end=3, text="Hello"),
            Segment(start=4, end=7, text="World"),
            Segment(start=8, end=11, text="Again"),
        ]
        turns = [
            {"start": 0, "end": 5, "speaker": "SPEAKER_00"},
            {"start": 5, "end": 12, "speaker": "SPEAKER_01"},
        ]

        result = assign_speakers_to_segments(segments, turns)

        assert result[0].speaker == "Speaker 1"  # SPEAKER_00 -> Speaker 1
        assert result[1].speaker == "Speaker 2"  # overlap: 4-5 = SPEAKER_00(1s), 5-7 = SPEAKER_01(2s) -> Speaker 2
        assert result[2].speaker == "Speaker 2"

    def test_empty_turns(self):
        segments = [Segment(start=0, end=3, text="Hello")]
        result = assign_speakers_to_segments(segments, [])
        assert result[0].speaker is None

    def test_single_speaker(self):
        segments = [
            Segment(start=0, end=3, text="A"),
            Segment(start=4, end=7, text="B"),
        ]
        turns = [{"start": 0, "end": 10, "speaker": "SPEAKER_00"}]

        result = assign_speakers_to_segments(segments, turns)
        assert result[0].speaker == "Speaker 1"
        assert result[1].speaker == "Speaker 1"

    def test_no_overlap_segment(self):
        segments = [
            Segment(start=0, end=1, text="A"),
            Segment(start=10, end=11, text="B"),  # no speaker turn covers this
        ]
        turns = [{"start": 0, "end": 2, "speaker": "SPEAKER_00"}]

        result = assign_speakers_to_segments(segments, turns)
        assert result[0].speaker == "Speaker 1"
        assert result[1].speaker is None

    def test_speaker_normalization(self):
        """Speakers should be renamed to sequential 'Speaker N' format."""
        segments = [
            Segment(start=0, end=3, text="A"),
            Segment(start=4, end=7, text="B"),
            Segment(start=8, end=11, text="C"),
        ]
        turns = [
            {"start": 0, "end": 3, "speaker": "SPEAKER_02"},
            {"start": 4, "end": 7, "speaker": "SPEAKER_05"},
            {"start": 8, "end": 11, "speaker": "SPEAKER_02"},
        ]

        result = assign_speakers_to_segments(segments, turns)
        assert result[0].speaker == "Speaker 1"  # First seen -> Speaker 1
        assert result[1].speaker == "Speaker 2"  # Second seen -> Speaker 2
        assert result[2].speaker == "Speaker 1"  # Same as first
