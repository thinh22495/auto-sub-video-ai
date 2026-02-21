from __future__ import annotations

import json
import logging
from pathlib import Path

import pysubs2
from pysubs2 import SSAFile, SSAEvent, SSAStyle, Color

from backend.core.segment import Segment

logger = logging.getLogger(__name__)

# Kiểu phụ đề mặc định
DEFAULT_STYLE = {
    "font_name": "Arial",
    "font_size": 24,
    "primary_color": "#FFFFFF",
    "secondary_color": "#FFFF00",
    "outline_color": "#000000",
    "shadow_color": "#000000",
    "outline_width": 2.0,
    "shadow_depth": 1.0,
    "alignment": 2,  # Giữa dưới (bàn phím số SSA)
    "margin_left": 10,
    "margin_right": 10,
    "margin_vertical": 30,
    "bold": False,
    "italic": False,
    "max_line_length": 42,
    "max_lines": 2,
}

# Bảng màu người nói cho kiểu dáng riêng từng người
SPEAKER_COLORS = [
    "#FFFFFF", "#00FFFF", "#FF69B4", "#7FFF00",
    "#FFD700", "#FF6347", "#40E0D0", "#EE82EE",
]


def _hex_to_ssa_color(hex_color: str) -> Color:
    """Chuyển đổi màu hex (#RRGGBB) sang pysubs2 Color (AABBGGRR)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return Color(r, g, b, 0)


def _wrap_text(text: str, max_length: int, max_lines: int) -> str:
    """Ngắt dòng văn bản để vừa với độ dài dòng tối đa và số dòng tối đa."""
    if len(text) <= max_length:
        return text

    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        if len(test_line) <= max_length:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

            if len(lines) >= max_lines - 1:
                # Dòng cuối: đổ hết các từ còn lại
                remaining_words = words[words.index(word):]
                lines.append(" ".join(remaining_words))
                return "\n".join(lines[:max_lines])

    if current_line:
        lines.append(current_line)

    return "\n".join(lines[:max_lines])


def resolve_style(style: dict | None = None, preset_name: str | None = None) -> dict:
    """
    Xác định kiểu phụ đề cuối cùng bằng cách gộp mặc định, preset và ghi đè.

    Ưu tiên: ghi đè kiểu trực tiếp > preset > mặc định.
    """
    from backend.video.presets import get_builtin_preset

    resolved = {**DEFAULT_STYLE}

    # Áp dụng preset nếu được chỉ định
    if preset_name:
        preset = get_builtin_preset(preset_name)
        if preset and "subtitle_style" in preset:
            resolved.update(preset["subtitle_style"])

    # Áp dụng ghi đè kiểu trực tiếp
    if style:
        resolved.update(style)

    return resolved


def generate_subtitles(
    segments: list[Segment],
    output_path: str,
    format: str = "srt",
    style: dict | None = None,
    use_translated: bool = False,
    preset_name: str | None = None,
) -> str:
    """
    Tạo tệp phụ đề từ các đoạn.

    Tham số:
        segments: Danh sách các đối tượng Segment.
        output_path: Đường dẫn tệp đầu ra (phần mở rộng sẽ được điều chỉnh).
        format: Định dạng đầu ra ('srt', 'ass', 'vtt').
        style: Dict cấu hình kiểu dáng (ghi đè mặc định và preset).
        use_translated: Sử dụng translated_text nếu có.
        preset_name: Tên preset tích hợp để dùng làm kiểu cơ sở.

    Trả về:
        Đường dẫn đến tệp phụ đề đã tạo.
    """
    style_config = resolve_style(style, preset_name)
    max_length = style_config["max_line_length"]
    max_lines = style_config["max_lines"]

    # Đảm bảo phần mở rộng đúng
    ext_map = {"srt": ".srt", "ass": ".ass", "vtt": ".vtt"}
    output_file = Path(output_path).with_suffix(ext_map.get(format, ".srt"))
    output_file.parent.mkdir(parents=True, exist_ok=True)

    subs = SSAFile()

    # Đặt thông tin độ phân giải video cho ASS (hỗ trợ hiển thị)
    if format == "ass":
        subs.info["PlayResX"] = "1920"
        subs.info["PlayResY"] = "1080"
        subs.info["ScaledBorderAndShadow"] = "yes"
        subs.styles["Default"] = _create_ass_style(style_config)

    for seg in segments:
        text = (seg.translated_text if use_translated and seg.translated_text else seg.text)
        text = _wrap_text(text, max_length, max_lines)

        # Thêm nhãn người nói cho SRT/VTT
        if seg.speaker and format != "ass":
            text = f"[{seg.speaker}]: {text}"

        event = SSAEvent(
            start=pysubs2.make_time(s=seg.start),
            end=pysubs2.make_time(s=seg.end),
            text=text,
        )

        # Với ASS có người nói, sử dụng các kiểu khác nhau
        if seg.speaker and format == "ass":
            speaker_style_name = f"Speaker_{seg.speaker}"
            if speaker_style_name not in subs.styles:
                subs.styles[speaker_style_name] = _create_ass_style(
                    style_config, speaker=seg.speaker
                )
            event.style = speaker_style_name

        subs.append(event)

    # Lưu theo định dạng yêu cầu
    output_str = str(output_file)
    subs.save(output_str, format_=format)

    logger.info("Generated subtitle file: %s (%d segments, format=%s)", output_str, len(segments), format)
    return output_str


def _create_ass_style(config: dict, speaker: str | None = None) -> SSAStyle:
    """Create an SSA style from config dict."""
    style = SSAStyle()
    style.fontname = config["font_name"]
    style.fontsize = config["font_size"]
    style.primarycolor = _hex_to_ssa_color(config["primary_color"])
    style.secondarycolor = _hex_to_ssa_color(config["secondary_color"])
    style.outlinecolor = _hex_to_ssa_color(config["outline_color"])
    style.backcolor = _hex_to_ssa_color(config["shadow_color"])
    style.outline = config["outline_width"]
    style.shadow = config["shadow_depth"]
    style.alignment = config["alignment"]
    style.marginl = config["margin_left"]
    style.marginr = config["margin_right"]
    style.marginv = config["margin_vertical"]
    style.bold = config["bold"]
    style.italic = config["italic"]

    # Assign different colors per speaker
    if speaker:
        try:
            idx = int(speaker.split("_")[-1]) if "_" in speaker else hash(speaker)
        except (ValueError, IndexError):
            idx = hash(speaker)
        color = SPEAKER_COLORS[idx % len(SPEAKER_COLORS)]
        style.primarycolor = _hex_to_ssa_color(color)

    return style


def parse_subtitle_file(file_path: str) -> list[Segment]:
    """Parse an existing subtitle file back into Segments."""
    subs = pysubs2.load(file_path)
    segments = []
    for event in subs:
        if event.is_comment:
            continue
        segments.append(
            Segment(
                start=event.start / 1000.0,
                end=event.end / 1000.0,
                text=event.plaintext,
            )
        )
    return segments
