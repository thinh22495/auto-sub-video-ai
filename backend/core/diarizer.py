from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from backend.core.segment import Segment

logger = logging.getLogger(__name__)

DiarizationCallback = Callable[[float, str], None]


def diarize_audio(
    audio_path: str,
    num_speakers: int | None = None,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
    auth_token: str | None = None,
    on_progress: DiarizationCallback | None = None,
) -> list[dict]:
    """
    Chạy phân biệt người nói trên tệp âm thanh sử dụng pyannote.audio.

    Trả về danh sách các lượt nói:
        [{"start": 0.5, "end": 3.2, "speaker": "SPEAKER_00"}, ...]
    """
    from backend.models.pyannote_manager import get_pipeline

    if on_progress:
        on_progress(0, "Đang tải mô hình phân biệt người nói...")

    pipeline = get_pipeline(use_auth_token=auth_token)

    if on_progress:
        on_progress(10, "Đang phân biệt người nói...")

    # Xây dựng tham số pipeline
    params = {}
    if num_speakers is not None:
        params["num_speakers"] = num_speakers
    elif min_speakers is not None or max_speakers is not None:
        if min_speakers is not None:
            params["min_speakers"] = min_speakers
        if max_speakers is not None:
            params["max_speakers"] = max_speakers

    diarization = pipeline(audio_path, **params)

    if on_progress:
        on_progress(80, "Đang xử lý kết quả phân biệt...")

    # Chuyển đổi sang danh sách các lượt nói
    turns = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        turns.append({
            "start": round(turn.start, 3),
            "end": round(turn.end, 3),
            "speaker": speaker,
        })

    if on_progress:
        on_progress(100, f"Phân biệt hoàn tất: tìm thấy {len(set(t['speaker'] for t in turns))} người nói")

    logger.info(
        "Phân biệt hoàn tất: %d lượt nói, %d người nói",
        len(turns),
        len(set(t["speaker"] for t in turns)),
    )

    return turns


def assign_speakers_to_segments(
    segments: list[Segment],
    speaker_turns: list[dict],
) -> list[Segment]:
    """
    Gán nhãn người nói cho các đoạn phiên âm dựa trên
    sự trùng lặp với các lượt phân biệt người nói.

    Sử dụng trùng lặp đa số — mỗi đoạn nhận người nói
    chiếm phần lớn thời lượng của đoạn đó.
    """
    if not speaker_turns:
        return segments

    for segment in segments:
        best_speaker = None
        best_overlap = 0.0

        for turn in speaker_turns:
            # Tính toán sự trùng lặp giữa đoạn và lượt nói
            overlap_start = max(segment.start, turn["start"])
            overlap_end = min(segment.end, turn["end"])
            overlap = max(0.0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn["speaker"]

        if best_speaker:
            segment.speaker = best_speaker

    # Chuẩn hóa tên người nói theo đánh số tuần tự
    unique_speakers = []
    for seg in segments:
        if seg.speaker and seg.speaker not in unique_speakers:
            unique_speakers.append(seg.speaker)

    speaker_map = {
        name: f"Speaker {i + 1}"
        for i, name in enumerate(unique_speakers)
    }

    for seg in segments:
        if seg.speaker:
            seg.speaker = speaker_map.get(seg.speaker, seg.speaker)

    logger.info(
        "Đã gán người nói cho %d đoạn (%d người nói duy nhất)",
        len(segments),
        len(unique_speakers),
    )

    return segments
