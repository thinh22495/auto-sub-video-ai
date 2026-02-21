from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# Tên ngôn ngữ theo ISO 639-1
LANGUAGE_NAMES: dict[str, str] = {
    "af": "Tiếng Afrikaans", "am": "Tiếng Amharic", "ar": "Tiếng Ả Rập", "as": "Tiếng Assam",
    "az": "Tiếng Azerbaijan", "ba": "Tiếng Bashkir", "be": "Tiếng Belarus", "bg": "Tiếng Bulgaria",
    "bn": "Tiếng Bengal", "bo": "Tiếng Tây Tạng", "br": "Tiếng Breton", "bs": "Tiếng Bosnia",
    "ca": "Tiếng Catalan", "cs": "Tiếng Séc", "cy": "Tiếng Wales", "da": "Tiếng Đan Mạch",
    "de": "Tiếng Đức", "el": "Tiếng Hy Lạp", "en": "Tiếng Anh", "es": "Tiếng Tây Ban Nha",
    "et": "Tiếng Estonia", "eu": "Tiếng Basque", "fa": "Tiếng Ba Tư", "fi": "Tiếng Phần Lan",
    "fo": "Tiếng Faroe", "fr": "Tiếng Pháp", "gl": "Tiếng Galicia", "gu": "Tiếng Gujarat",
    "ha": "Tiếng Hausa", "haw": "Tiếng Hawaii", "he": "Tiếng Do Thái", "hi": "Tiếng Hindi",
    "hr": "Tiếng Croatia", "ht": "Tiếng Creole Haiti", "hu": "Tiếng Hungary", "hy": "Tiếng Armenia",
    "id": "Tiếng Indonesia", "is": "Tiếng Iceland", "it": "Tiếng Ý", "ja": "Tiếng Nhật",
    "jw": "Tiếng Java", "ka": "Tiếng Gruzia", "kk": "Tiếng Kazakh", "km": "Tiếng Khmer",
    "kn": "Tiếng Kannada", "ko": "Tiếng Hàn", "la": "Tiếng Latin", "lb": "Tiếng Luxembourg",
    "ln": "Tiếng Lingala", "lo": "Tiếng Lào", "lt": "Tiếng Litva", "lv": "Tiếng Latvia",
    "mg": "Tiếng Malagasy", "mi": "Tiếng Maori", "mk": "Tiếng Macedonia", "ml": "Tiếng Malayalam",
    "mn": "Tiếng Mông Cổ", "mr": "Tiếng Marathi", "ms": "Tiếng Mã Lai", "mt": "Tiếng Malta",
    "my": "Tiếng Myanmar", "ne": "Tiếng Nepal", "nl": "Tiếng Hà Lan", "nn": "Tiếng Na Uy Nynorsk",
    "no": "Tiếng Na Uy", "oc": "Tiếng Occitan", "pa": "Tiếng Punjab", "pl": "Tiếng Ba Lan",
    "ps": "Tiếng Pashto", "pt": "Tiếng Bồ Đào Nha", "ro": "Tiếng Romania", "ru": "Tiếng Nga",
    "sa": "Tiếng Phạn", "sd": "Tiếng Sindhi", "si": "Tiếng Sinhala", "sk": "Tiếng Slovak",
    "sl": "Tiếng Slovenia", "sn": "Tiếng Shona", "so": "Tiếng Somali", "sq": "Tiếng Albania",
    "sr": "Tiếng Serbia", "su": "Tiếng Sunda", "sv": "Tiếng Thụy Điển", "sw": "Tiếng Swahili",
    "ta": "Tiếng Tamil", "te": "Tiếng Telugu", "tg": "Tiếng Tajik", "th": "Tiếng Thái",
    "tk": "Tiếng Turkmen", "tl": "Tiếng Tagalog", "tr": "Tiếng Thổ Nhĩ Kỳ", "tt": "Tiếng Tatar",
    "uk": "Tiếng Ukraine", "ur": "Tiếng Urdu", "uz": "Tiếng Uzbek", "vi": "Tiếng Việt",
    "yi": "Tiếng Yiddish", "yo": "Tiếng Yoruba", "zh": "Tiếng Trung", "zu": "Tiếng Zulu",
}


def detect_language(audio_path: str, model_name: str = "large-v3-turbo") -> dict:
    """
    Nhận diện ngôn ngữ của tệp âm thanh sử dụng faster-whisper.

    Trả về:
        dict với 'language' (mã ISO), 'language_name', và 'confidence'.
    """
    from backend.core.transcriber import _get_model

    model = _get_model(model_name)

    # Sử dụng detect_language chỉ xử lý 30 giây đầu tiên
    segments, info = model.transcribe(
        audio_path,
        language=None,
        beam_size=1,
        vad_filter=True,
    )
    # Cần tiêu thụ ít nhất một đoạn để kích hoạt nhận diện
    # nhưng info đã có ngôn ngữ được phát hiện
    detected = info.language
    confidence = info.language_probability

    logger.info("Đã nhận diện ngôn ngữ: %s (%s) với độ tin cậy %.2f",
                detected, LANGUAGE_NAMES.get(detected, "Không xác định"), confidence)

    return {
        "language": detected,
        "language_name": LANGUAGE_NAMES.get(detected, "Không xác định"),
        "confidence": confidence,
    }


def get_supported_languages() -> list[dict]:
    """Trả về danh sách tất cả ngôn ngữ được hỗ trợ."""
    return [
        {"code": code, "name": name}
        for code, name in sorted(LANGUAGE_NAMES.items(), key=lambda x: x[1])
    ]
