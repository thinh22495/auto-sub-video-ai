"""Tests for subtitle parsing and generation in jobs API."""

from backend.api.jobs import (
    _parse_srt,
    _parse_vtt,
    _parse_ass,
    _generate_srt,
    _generate_vtt,
    _srt_ts_to_seconds,
    _vtt_ts_to_seconds,
    _seconds_to_srt_ts,
    _seconds_to_vtt_ts,
    SubtitleSegment,
)


class TestTimestampParsing:
    def test_srt_timestamp_to_seconds(self):
        assert _srt_ts_to_seconds("00:00:01,000") == 1.0
        assert _srt_ts_to_seconds("01:30:00,500") == 5400.5
        assert _srt_ts_to_seconds("00:01:30,250") == 90.25

    def test_vtt_timestamp_to_seconds(self):
        assert _vtt_ts_to_seconds("00:00:01.000") == 1.0
        assert _vtt_ts_to_seconds("01:30:00.500") == 5400.5

    def test_seconds_to_srt_timestamp(self):
        assert _seconds_to_srt_ts(1.0) == "00:00:01,000"
        assert _seconds_to_srt_ts(5400.5) == "01:30:00,500"
        assert _seconds_to_srt_ts(0.0) == "00:00:00,000"

    def test_seconds_to_vtt_timestamp(self):
        assert _seconds_to_vtt_ts(1.0) == "00:00:01.000"
        assert _seconds_to_vtt_ts(5400.5) == "01:30:00.500"


class TestSRTParsing:
    def test_basic_srt(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:03,000\n"
            "Hello world\n"
            "\n"
            "2\n"
            "00:00:04,000 --> 00:00:06,500\n"
            "Second line\n"
        )
        segments = _parse_srt(content)
        assert len(segments) == 2
        assert segments[0]["index"] == 1
        assert segments[0]["start"] == 1.0
        assert segments[0]["end"] == 3.0
        assert segments[0]["text"] == "Hello world"
        assert segments[1]["text"] == "Second line"

    def test_srt_with_speaker(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:03,000\n"
            "[Speaker 1]: Hello world\n"
        )
        segments = _parse_srt(content)
        assert segments[0]["speaker"] == "Speaker 1"
        assert segments[0]["text"] == "Hello world"

    def test_srt_multiline_text(self):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:03,000\n"
            "Line one\n"
            "Line two\n"
        )
        segments = _parse_srt(content)
        assert segments[0]["text"] == "Line one\nLine two"

    def test_empty_srt(self):
        assert _parse_srt("") == []
        assert _parse_srt("  \n  ") == []


class TestVTTParsing:
    def test_basic_vtt(self):
        content = (
            "WEBVTT\n"
            "\n"
            "00:00:01.000 --> 00:00:03.000\n"
            "Hello world\n"
            "\n"
            "00:00:04.000 --> 00:00:06.000\n"
            "Second line\n"
        )
        segments = _parse_vtt(content)
        assert len(segments) == 2
        assert segments[0]["start"] == 1.0
        assert segments[0]["text"] == "Hello world"

    def test_vtt_with_header(self):
        content = (
            "WEBVTT Kind: captions\n"
            "\n"
            "00:00:01.000 --> 00:00:03.000\n"
            "Test\n"
        )
        segments = _parse_vtt(content)
        assert len(segments) == 1


class TestASSParsing:
    def test_basic_ass(self):
        content = (
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Hello world\n"
            "Dialogue: 0,0:00:04.00,0:00:06.00,Default,,0,0,0,,Second line\n"
        )
        segments = _parse_ass(content)
        assert len(segments) == 2
        assert segments[0]["text"] == "Hello world"

    def test_ass_with_override_tags(self):
        content = "Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,{\\b1}Bold text{\\b0}\n"
        segments = _parse_ass(content)
        assert segments[0]["text"] == "Bold text"

    def test_ass_with_newline(self):
        content = "Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Line one\\NLine two\n"
        segments = _parse_ass(content)
        assert segments[0]["text"] == "Line one\nLine two"


class TestSRTGeneration:
    def test_basic_generation(self):
        segments = [
            SubtitleSegment(index=1, start=1.0, end=3.0, text="Hello"),
            SubtitleSegment(index=2, start=4.0, end=6.0, text="World"),
        ]
        content = _generate_srt(segments)
        assert "1\n00:00:01,000 --> 00:00:03,000\nHello" in content
        assert "2\n00:00:04,000 --> 00:00:06,000\nWorld" in content

    def test_generation_with_speaker(self):
        segments = [
            SubtitleSegment(index=1, start=1.0, end=3.0, text="Hello", speaker="Bob"),
        ]
        content = _generate_srt(segments)
        assert "[Bob]: Hello" in content


class TestVTTGeneration:
    def test_basic_generation(self):
        segments = [
            SubtitleSegment(index=1, start=1.0, end=3.0, text="Hello"),
        ]
        content = _generate_vtt(segments)
        assert "WEBVTT" in content
        assert "00:00:01.000 --> 00:00:03.000" in content

    def test_generation_with_speaker(self):
        segments = [
            SubtitleSegment(index=1, start=1.0, end=3.0, text="Hello", speaker="Bob"),
        ]
        content = _generate_vtt(segments)
        assert "<v Bob>Hello" in content
