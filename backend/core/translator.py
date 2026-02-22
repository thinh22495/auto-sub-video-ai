from __future__ import annotations

import logging
import time
from typing import Callable

import httpx

from backend.config.settings import settings
from backend.core.segment import Segment

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]

SYSTEM_PROMPT_TEMPLATE = """You are a professional subtitle translator. Translate the following subtitle segments from {source_lang} to {target_lang}.

Rules:
- Keep translations concise and natural for spoken dialogue
- Preserve the original meaning and tone
- Each line must not exceed {max_chars} characters
- Do not add explanations, notes, or extra text
- Preserve speaker labels if present (e.g., [Speaker 1]:)
- Maintain informal/formal register matching the original
- For idiomatic expressions, use equivalent expressions in the target language
- Return ONLY the translated text, one segment per line, numbered to match input"""


def translate_segments(
    segments: list[Segment],
    source_lang: str,
    target_lang: str,
    model: str | None = None,
    max_chars: int = 42,
    batch_size: int = 8,
    context_size: int = 2,
    temperature: float = 0.3,
    on_progress: ProgressCallback | None = None,
) -> list[Segment]:
    """
    Dịch các đoạn phụ đề sử dụng Ollama LLM.

    Sử dụng dịch theo lô với ngữ cảnh xung quanh để đảm bảo tính mạch lạc.
    Mỗi lô gửi context_size đoạn trước đó làm tham chiếu.

    Tham số:
        segments: Các đoạn cần dịch.
        source_lang: Tên ngôn ngữ nguồn (vd: "English").
        target_lang: Tên ngôn ngữ đích (vd: "Vietnamese").
        model: Tên model Ollama. Mặc định theo cài đặt.
        batch_size: Số đoạn mỗi lần gọi API.
        context_size: Số đoạn trước đó gửi làm ngữ cảnh.
        on_progress: Callback(phần trăm, thông báo).

    Trả về:
        Các đoạn giống nhau với translated_text đã được điền.
    """
    if not segments:
        return segments

    model = model or settings.DEFAULT_OLLAMA_MODEL
    total = len(segments)
    translated_count = 0
    start_time = time.time()

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        source_lang=source_lang,
        target_lang=target_lang,
        max_chars=max_chars,
    )

    if on_progress:
        on_progress(0, f"Translating {total} segments ({source_lang} -> {target_lang})...")

    # Xử lý theo lô
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = segments[batch_start:batch_end]

        # Xây dựng ngữ cảnh từ các đoạn trước đó
        context_segments = segments[max(0, batch_start - context_size):batch_start]

        user_message = _build_translation_prompt(context_segments, batch, batch_start)

        try:
            response_text = _call_ollama(
                model=model,
                system=system_prompt,
                prompt=user_message,
                temperature=temperature,
            )

            logger.debug(
                "Ollama response for batch %d-%d: %s",
                batch_start, batch_end, response_text[:500],
            )

            # Phân tích phản hồi và gán bản dịch
            translations = _parse_translation_response(response_text, len(batch))

            for i, translation in enumerate(translations):
                if batch_start + i < total:
                    if translation:
                        segments[batch_start + i].translated_text = translation
                    else:
                        logger.warning(
                            "Empty translation for segment %d, using original text",
                            batch_start + i,
                        )
                        segments[batch_start + i].translated_text = segments[batch_start + i].text

            translated_count += len(batch)

        except Exception as e:
            logger.error(
                "Translation failed for batch %d-%d: %s",
                batch_start, batch_end, e,
            )
            # Khi thất bại, sao chép văn bản gốc làm dự phòng
            for seg in batch:
                if not seg.translated_text:
                    seg.translated_text = seg.text

            translated_count += len(batch)

        if on_progress:
            percent = (translated_count / total) * 100
            elapsed = time.time() - start_time
            rate = translated_count / elapsed if elapsed > 0 else 0
            remaining = (total - translated_count) / rate if rate > 0 else 0
            on_progress(
                percent,
                f"Translated {translated_count}/{total} segments "
                f"({rate:.1f} seg/s, ~{remaining:.0f}s remaining)",
            )

    elapsed = time.time() - start_time
    logger.info(
        "Translation complete: %d segments in %.1fs (%s -> %s, model=%s)",
        total, elapsed, source_lang, target_lang, model,
    )

    if on_progress:
        on_progress(100, f"Translation complete: {total} segments")

    return segments


def _build_translation_prompt(
    context: list[Segment],
    batch: list[Segment],
    batch_start: int,
) -> str:
    """Xây dựng prompt cho người dùng với ngữ cảnh và các đoạn được đánh số."""
    parts = []

    if context:
        parts.append("Context (previous segments, for reference only - do NOT translate these):")
        for i, seg in enumerate(context):
            idx = batch_start - len(context) + i + 1
            parts.append(f"  [{idx}] {seg.text}")
        parts.append("")

    parts.append("Translate these segments:")
    for i, seg in enumerate(batch):
        idx = batch_start + i + 1
        text = seg.text
        if seg.speaker:
            text = f"[{seg.speaker}]: {text}"
        parts.append(f"  [{idx}] {text}")

    return "\n".join(parts)


def _parse_translation_response(response: str, expected_count: int) -> list[str]:
    """Phân tích các bản dịch được đánh số từ phản hồi LLM."""
    lines = response.strip().split("\n")
    translations: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Thử khớp các mẫu như "[1] text", "1. text", "1) text", hoặc chỉ "text"
        cleaned = line
        for prefix_pattern in ["[", ""]:
            if prefix_pattern == "[" and line.startswith("["):
                bracket_end = line.find("]")
                if bracket_end != -1:
                    cleaned = line[bracket_end + 1:].strip()
                    break
            elif line[0].isdigit():
                # Bỏ qua số đầu dòng + ký tự phân cách
                i = 0
                while i < len(line) and line[i].isdigit():
                    i += 1
                if i < len(line) and line[i] in ".)]:-":
                    cleaned = line[i + 1:].strip()
                    break

        if cleaned:
            translations.append(cleaned)

    # Nếu nhận được quá ít, thêm chuỗi rỗng
    while len(translations) < expected_count:
        translations.append("")

    # Nếu nhận được quá nhiều, cắt bớt
    return translations[:expected_count]


def _call_ollama(model: str, system: str, prompt: str, temperature: float = 0.3) -> str:
    """Gọi API chat Ollama và trả về văn bản phản hồi."""
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_predict": 2048,
        },
    }

    with httpx.Client(timeout=120) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    return data.get("message", {}).get("content", "")


def test_ollama_connection(model: str | None = None) -> dict:
    """Kiểm tra xem Ollama có truy cập được và model có sẵn không."""
    model = model or settings.DEFAULT_OLLAMA_MODEL
    try:
        with httpx.Client(timeout=5) as client:
            # Kiểm tra xem Ollama có đang chạy không
            resp = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            tags = resp.json()

            available_models = [m["name"] for m in tags.get("models", [])]
            model_ready = any(model in m for m in available_models)

            return {
                "connected": True,
                "model_available": model_ready,
                "available_models": available_models,
            }
    except Exception as e:
        return {
            "connected": False,
            "model_available": False,
            "error": str(e),
        }
