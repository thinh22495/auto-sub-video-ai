from backend.video.ffmpeg_wrapper import get_video_info as _get_video_info


def get_video_info(file_path: str) -> dict:
    """Get video metadata. Thin wrapper over ffmpeg_wrapper."""
    return _get_video_info(file_path)


# Supported video extensions
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".3gp", ".ts", ".mts", ".m2ts",
}


def is_video_file(filename: str) -> bool:
    """Check if a filename has a video extension."""
    from pathlib import Path
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS
