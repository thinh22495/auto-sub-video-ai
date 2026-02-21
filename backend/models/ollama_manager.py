from __future__ import annotations

import logging
from typing import Generator

import httpx

from backend.config.settings import settings

logger = logging.getLogger(__name__)


def list_models() -> list[dict]:
    """Liệt kê tất cả mô hình có sẵn trong Ollama."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()

        models = []
        for m in data.get("models", []):
            models.append({
                "name": m.get("name", ""),
                "size_bytes": m.get("size", 0),
                "size_gb": round(m.get("size", 0) / (1024**3), 2),
                "modified_at": m.get("modified_at", ""),
                "digest": m.get("digest", "")[:12],
                "family": m.get("details", {}).get("family", ""),
                "parameter_size": m.get("details", {}).get("parameter_size", ""),
                "quantization": m.get("details", {}).get("quantization_level", ""),
                "is_default": m.get("name", "") == settings.DEFAULT_OLLAMA_MODEL,
            })
        return models

    except httpx.ConnectError:
        logger.warning("Không thể kết nối Ollama tại %s", settings.OLLAMA_BASE_URL)
        return []
    except Exception as e:
        logger.error("Không thể liệt kê mô hình Ollama: %s", e)
        return []


def pull_model(model_name: str) -> Generator[dict, None, None]:
    """
    Tải (pull) mô hình từ registry Ollama.
    Trả về các cập nhật tiến trình dưới dạng dict.
    """
    logger.info("Đang tải mô hình Ollama: %s", model_name)

    with httpx.Client(timeout=None) as client:
        with client.stream(
            "POST",
            f"{settings.OLLAMA_BASE_URL}/api/pull",
            json={"name": model_name, "stream": True},
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    import json
                    data = json.loads(line)
                    status = data.get("status", "")
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)

                    progress = {
                        "status": status,
                        "total": total,
                        "completed": completed,
                        "percent": round((completed / total) * 100, 1) if total > 0 else 0,
                    }
                    yield progress

                    if status == "success":
                        logger.info("Đã tải xong mô hình Ollama: %s", model_name)
                        return

                except Exception:
                    continue


def pull_model_sync(model_name: str) -> dict:
    """Tải mô hình đồng bộ (chặn). Trả về trạng thái cuối cùng."""
    last_progress = {"status": "unknown", "percent": 0}
    try:
        for progress in pull_model(model_name):
            last_progress = progress
        return {"name": model_name, "status": "success", **last_progress}
    except Exception as e:
        logger.error("Không thể tải mô hình Ollama %s: %s", model_name, e)
        return {"name": model_name, "status": "error", "error": str(e)}


def delete_model(model_name: str) -> bool:
    """Xóa mô hình khỏi Ollama."""
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.delete(
                f"{settings.OLLAMA_BASE_URL}/api/delete",
                json={"name": model_name},
            )
            if resp.status_code == 200:
                logger.info("Đã xóa mô hình Ollama: %s", model_name)
                return True
            else:
                logger.warning(
                    "Không thể xóa mô hình Ollama %s: %d %s",
                    model_name, resp.status_code, resp.text,
                )
                return False
    except Exception as e:
        logger.error("Không thể xóa mô hình Ollama %s: %s", model_name, e)
        return False


def get_model_info(model_name: str) -> dict | None:
    """Lấy thông tin chi tiết về một mô hình Ollama cụ thể."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{settings.OLLAMA_BASE_URL}/api/show",
                json={"name": model_name},
            )
            if resp.status_code != 200:
                return None
            return resp.json()
    except Exception:
        return None


def check_health() -> dict:
    """Kiểm tra dịch vụ Ollama có hoạt động không."""
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            model_count = len(resp.json().get("models", []))
            return {
                "status": "up",
                "url": settings.OLLAMA_BASE_URL,
                "model_count": model_count,
            }
    except httpx.ConnectError:
        return {"status": "down", "url": settings.OLLAMA_BASE_URL, "error": "Từ chối kết nối"}
    except Exception as e:
        return {"status": "error", "url": settings.OLLAMA_BASE_URL, "error": str(e)}


# Các mô hình khuyên dùng cho dịch thuật
RECOMMENDED_MODELS = [
    {
        "name": "qwen2.5:7b",
        "description": "Mô hình đa ngôn ngữ tốt nhất. 29+ ngôn ngữ bao gồm tiếng Việt, Nhật, Hàn, Trung.",
        "size_gb": 4.7,
        "languages": "đa ngôn ngữ (29+)",
    },
    {
        "name": "qwen2.5:3b",
        "description": "Mô hình đa ngôn ngữ nhẹ hơn. Tốt cho hệ thống có VRAM hạn chế.",
        "size_gb": 2.0,
        "languages": "đa ngôn ngữ (29+)",
    },
    {
        "name": "llama3.1:8b",
        "description": "Mô hình mạnh tập trung tiếng Anh. Tốt cho các tác vụ dịch sang tiếng Anh.",
        "size_gb": 4.7,
        "languages": "tập trung tiếng Anh, đa ngôn ngữ cơ bản",
    },
    {
        "name": "mistral:7b",
        "description": "Tốt cho ngôn ngữ châu Âu. Pháp, Đức, Tây Ban Nha, Ý, v.v.",
        "size_gb": 4.1,
        "languages": "ngôn ngữ châu Âu",
    },
    {
        "name": "gemma2:9b",
        "description": "Mô hình Google. Hiệu suất đa ngôn ngữ tổng quát tốt.",
        "size_gb": 5.4,
        "languages": "đa ngôn ngữ",
    },
]
