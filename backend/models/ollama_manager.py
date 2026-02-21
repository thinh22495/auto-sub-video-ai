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
        "description": "Mô hình đa ngôn ngữ tốt nhất cho dịch thuật. 29+ ngôn ngữ bao gồm tiếng Việt, Nhật, Hàn, Trung.",
        "size_gb": 4.7,
        "vram_gb": 6,
        "parameters": "7B",
        "quality": "rất tốt",
        "speed": "nhanh",
        "languages": "đa ngôn ngữ (29+)",
    },
    {
        "name": "qwen2.5:3b",
        "description": "Mô hình đa ngôn ngữ nhẹ. Tốt cho hệ thống có VRAM hạn chế.",
        "size_gb": 2.0,
        "vram_gb": 4,
        "parameters": "3B",
        "quality": "tốt",
        "speed": "rất nhanh",
        "languages": "đa ngôn ngữ (29+)",
    },
    {
        "name": "qwen2.5:14b",
        "description": "Phiên bản lớn hơn của Qwen 2.5. Chất lượng dịch xuất sắc, cần GPU mạnh.",
        "size_gb": 9.0,
        "vram_gb": 12,
        "parameters": "14B",
        "quality": "xuất sắc",
        "speed": "vừa phải",
        "languages": "đa ngôn ngữ (29+)",
    },
    {
        "name": "qwen2.5:32b",
        "description": "Mô hình Qwen lớn nhất. Chất lượng cao nhất nhưng cần VRAM lớn.",
        "size_gb": 20.0,
        "vram_gb": 24,
        "parameters": "32B",
        "quality": "xuất sắc",
        "speed": "chậm",
        "languages": "đa ngôn ngữ (29+)",
    },
    {
        "name": "llama3.1:8b",
        "description": "Mô hình Meta mạnh mẽ, tập trung tiếng Anh. Tốt cho dịch sang tiếng Anh.",
        "size_gb": 4.7,
        "vram_gb": 6,
        "parameters": "8B",
        "quality": "rất tốt",
        "speed": "nhanh",
        "languages": "tập trung tiếng Anh",
    },
    {
        "name": "llama3.1:70b",
        "description": "Phiên bản lớn của Llama 3.1. Chất lượng cực cao, cần GPU cao cấp.",
        "size_gb": 40.0,
        "vram_gb": 48,
        "parameters": "70B",
        "quality": "xuất sắc",
        "speed": "rất chậm",
        "languages": "tập trung tiếng Anh, đa ngôn ngữ",
    },
    {
        "name": "mistral:7b",
        "description": "Mô hình Mistral AI. Rất tốt cho ngôn ngữ châu Âu: Pháp, Đức, Tây Ban Nha, Ý.",
        "size_gb": 4.1,
        "vram_gb": 6,
        "parameters": "7B",
        "quality": "tốt",
        "speed": "nhanh",
        "languages": "ngôn ngữ châu Âu",
    },
    {
        "name": "gemma2:9b",
        "description": "Mô hình Google Gemma 2. Hiệu suất đa ngôn ngữ tổng quát tốt.",
        "size_gb": 5.4,
        "vram_gb": 8,
        "parameters": "9B",
        "quality": "tốt",
        "speed": "nhanh",
        "languages": "đa ngôn ngữ",
    },
    {
        "name": "gemma2:2b",
        "description": "Mô hình Google Gemma 2 nhẹ. Phù hợp hệ thống yếu hoặc chạy CPU.",
        "size_gb": 1.6,
        "vram_gb": 3,
        "parameters": "2B",
        "quality": "trung bình",
        "speed": "rất nhanh",
        "languages": "đa ngôn ngữ",
    },
    {
        "name": "aya-expanse:8b",
        "description": "Cohere Aya Expanse. Thiết kế chuyên cho đa ngôn ngữ, 23 ngôn ngữ.",
        "size_gb": 4.8,
        "vram_gb": 6,
        "parameters": "8B",
        "quality": "rất tốt",
        "speed": "nhanh",
        "languages": "đa ngôn ngữ (23)",
    },
    {
        "name": "phi3:medium",
        "description": "Microsoft Phi-3 Medium. Cân bằng tốt giữa chất lượng và tốc độ.",
        "size_gb": 7.9,
        "vram_gb": 10,
        "parameters": "14B",
        "quality": "tốt",
        "speed": "vừa phải",
        "languages": "đa ngôn ngữ",
    },
    {
        "name": "phi3:mini",
        "description": "Microsoft Phi-3 Mini. Nhỏ gọn, hiệu quả, phù hợp máy cấu hình thấp.",
        "size_gb": 2.3,
        "vram_gb": 4,
        "parameters": "3.8B",
        "quality": "trung bình",
        "speed": "rất nhanh",
        "languages": "đa ngôn ngữ cơ bản",
    },
    {
        "name": "command-r:35b",
        "description": "Cohere Command R. Mạnh về dịch thuật và xử lý văn bản dài.",
        "size_gb": 20.0,
        "vram_gb": 24,
        "parameters": "35B",
        "quality": "xuất sắc",
        "speed": "chậm",
        "languages": "đa ngôn ngữ (10+)",
    },
    {
        "name": "deepseek-v2.5",
        "description": "DeepSeek V2.5. Hỗ trợ tốt tiếng Trung, tiếng Anh và nhiều ngôn ngữ khác.",
        "size_gb": 8.9,
        "vram_gb": 10,
        "parameters": "16B MoE",
        "quality": "rất tốt",
        "speed": "nhanh",
        "languages": "Trung-Anh, đa ngôn ngữ",
    },
    {
        "name": "mixtral:8x7b",
        "description": "Mistral Mixture of Experts. Hiệu suất cao cho ngôn ngữ châu Âu.",
        "size_gb": 26.0,
        "vram_gb": 32,
        "parameters": "47B MoE",
        "quality": "xuất sắc",
        "speed": "vừa phải",
        "languages": "ngôn ngữ châu Âu",
    },
]
