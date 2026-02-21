"""Built-in subtitle styling and video encoding presets."""

from __future__ import annotations

# Built-in subtitle presets
# Each preset defines a complete subtitle style configuration
BUILTIN_PRESETS: dict[str, dict] = {
    "netflix": {
        "name": "Netflix",
        "description": "Netflix Timed Text Style Guide — clean, readable, professional",
        "subtitle_style": {
            "font_name": "Arial",
            "font_size": 22,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FFFFFF",
            "outline_color": "#000000",
            "shadow_color": "#000000",
            "outline_width": 2.0,
            "shadow_depth": 0.0,
            "alignment": 2,
            "margin_left": 20,
            "margin_right": 20,
            "margin_vertical": 40,
            "bold": False,
            "italic": False,
            "max_line_length": 42,
            "max_lines": 2,
        },
        "video_settings": {
            "crf": 18,
            "preset": "slow",
        },
    },
    "youtube": {
        "name": "YouTube",
        "description": "Optimized for YouTube player — slightly larger text, white on dark",
        "subtitle_style": {
            "font_name": "Roboto",
            "font_size": 24,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FFFFFF",
            "outline_color": "#000000",
            "shadow_color": "#000000",
            "outline_width": 2.5,
            "shadow_depth": 1.0,
            "alignment": 2,
            "margin_left": 15,
            "margin_right": 15,
            "margin_vertical": 35,
            "bold": False,
            "italic": False,
            "max_line_length": 42,
            "max_lines": 2,
        },
        "video_settings": {
            "crf": 20,
            "preset": "medium",
        },
    },
    "bluray": {
        "name": "Blu-ray",
        "description": "Blu-ray disc standard — bold, shadowed, high contrast",
        "subtitle_style": {
            "font_name": "Arial",
            "font_size": 26,
            "primary_color": "#FFFFFF",
            "secondary_color": "#FFFF00",
            "outline_color": "#000000",
            "shadow_color": "#000000",
            "outline_width": 3.0,
            "shadow_depth": 2.0,
            "alignment": 2,
            "margin_left": 20,
            "margin_right": 20,
            "margin_vertical": 50,
            "bold": True,
            "italic": False,
            "max_line_length": 40,
            "max_lines": 2,
        },
        "video_settings": {
            "crf": 16,
            "preset": "slow",
        },
    },
    "anime": {
        "name": "Anime Fansub",
        "description": "Anime fansub style — colored per speaker, larger text, outline",
        "subtitle_style": {
            "font_name": "Trebuchet MS",
            "font_size": 24,
            "primary_color": "#FFFFFF",
            "secondary_color": "#00FFFF",
            "outline_color": "#000000",
            "shadow_color": "#400040",
            "outline_width": 3.0,
            "shadow_depth": 1.5,
            "alignment": 2,
            "margin_left": 15,
            "margin_right": 15,
            "margin_vertical": 30,
            "bold": True,
            "italic": False,
            "max_line_length": 50,
            "max_lines": 3,
        },
        "video_settings": {
            "crf": 20,
            "preset": "medium",
        },
    },
    "accessibility": {
        "name": "Accessibility",
        "description": "Large text, high contrast, extra wide — for visually impaired viewers",
        "subtitle_style": {
            "font_name": "Arial",
            "font_size": 32,
            "primary_color": "#FFFF00",
            "secondary_color": "#FFFFFF",
            "outline_color": "#000000",
            "shadow_color": "#000000",
            "outline_width": 4.0,
            "shadow_depth": 2.0,
            "alignment": 2,
            "margin_left": 30,
            "margin_right": 30,
            "margin_vertical": 50,
            "bold": True,
            "italic": False,
            "max_line_length": 32,
            "max_lines": 2,
        },
        "video_settings": {
            "crf": 18,
            "preset": "medium",
        },
    },
}


def get_builtin_preset(name: str) -> dict | None:
    """Get a built-in preset by key name."""
    return BUILTIN_PRESETS.get(name)


def list_builtin_presets() -> list[dict]:
    """List all built-in presets with metadata."""
    result = []
    for key, preset in BUILTIN_PRESETS.items():
        result.append({
            "id": f"builtin_{key}",
            "name": preset["name"],
            "description": preset["description"],
            "subtitle_style": preset["subtitle_style"],
            "video_settings": preset.get("video_settings"),
            "is_builtin": True,
        })
    return result
