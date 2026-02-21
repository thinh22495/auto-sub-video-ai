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
    Run speaker diarization on an audio file using pyannote.audio.

    Returns a list of speaker turns:
        [{"start": 0.5, "end": 3.2, "speaker": "SPEAKER_00"}, ...]
    """
    from backend.models.pyannote_manager import get_pipeline

    if on_progress:
        on_progress(0, "Loading diarization model...")

    pipeline = get_pipeline(use_auth_token=auth_token)

    if on_progress:
        on_progress(10, "Running speaker diarization...")

    # Build pipeline parameters
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
        on_progress(80, "Processing diarization results...")

    # Convert to list of turns
    turns = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        turns.append({
            "start": round(turn.start, 3),
            "end": round(turn.end, 3),
            "speaker": speaker,
        })

    if on_progress:
        on_progress(100, f"Diarization complete: {len(set(t['speaker'] for t in turns))} speakers found")

    logger.info(
        "Diarization complete: %d turns, %d speakers",
        len(turns),
        len(set(t["speaker"] for t in turns)),
    )

    return turns


def assign_speakers_to_segments(
    segments: list[Segment],
    speaker_turns: list[dict],
) -> list[Segment]:
    """
    Assign speaker labels to transcription segments based on
    overlap with diarization turns.

    Uses majority overlap — each segment gets the speaker
    that covers the most of its duration.
    """
    if not speaker_turns:
        return segments

    for segment in segments:
        best_speaker = None
        best_overlap = 0.0

        for turn in speaker_turns:
            # Calculate overlap between segment and speaker turn
            overlap_start = max(segment.start, turn["start"])
            overlap_end = min(segment.end, turn["end"])
            overlap = max(0.0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn["speaker"]

        if best_speaker:
            segment.speaker = best_speaker

    # Normalize speaker names to sequential numbering
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
        "Assigned speakers to %d segments (%d unique speakers)",
        len(segments),
        len(unique_speakers),
    )

    return segments
