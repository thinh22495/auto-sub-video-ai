from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ISO 639-1 language names
LANGUAGE_NAMES: dict[str, str] = {
    "af": "Afrikaans", "am": "Amharic", "ar": "Arabic", "as": "Assamese",
    "az": "Azerbaijani", "ba": "Bashkir", "be": "Belarusian", "bg": "Bulgarian",
    "bn": "Bengali", "bo": "Tibetan", "br": "Breton", "bs": "Bosnian",
    "ca": "Catalan", "cs": "Czech", "cy": "Welsh", "da": "Danish",
    "de": "German", "el": "Greek", "en": "English", "es": "Spanish",
    "et": "Estonian", "eu": "Basque", "fa": "Persian", "fi": "Finnish",
    "fo": "Faroese", "fr": "French", "gl": "Galician", "gu": "Gujarati",
    "ha": "Hausa", "haw": "Hawaiian", "he": "Hebrew", "hi": "Hindi",
    "hr": "Croatian", "ht": "Haitian Creole", "hu": "Hungarian", "hy": "Armenian",
    "id": "Indonesian", "is": "Icelandic", "it": "Italian", "ja": "Japanese",
    "jw": "Javanese", "ka": "Georgian", "kk": "Kazakh", "km": "Khmer",
    "kn": "Kannada", "ko": "Korean", "la": "Latin", "lb": "Luxembourgish",
    "ln": "Lingala", "lo": "Lao", "lt": "Lithuanian", "lv": "Latvian",
    "mg": "Malagasy", "mi": "Maori", "mk": "Macedonian", "ml": "Malayalam",
    "mn": "Mongolian", "mr": "Marathi", "ms": "Malay", "mt": "Maltese",
    "my": "Myanmar", "ne": "Nepali", "nl": "Dutch", "nn": "Nynorsk",
    "no": "Norwegian", "oc": "Occitan", "pa": "Punjabi", "pl": "Polish",
    "ps": "Pashto", "pt": "Portuguese", "ro": "Romanian", "ru": "Russian",
    "sa": "Sanskrit", "sd": "Sindhi", "si": "Sinhala", "sk": "Slovak",
    "sl": "Slovenian", "sn": "Shona", "so": "Somali", "sq": "Albanian",
    "sr": "Serbian", "su": "Sundanese", "sv": "Swedish", "sw": "Swahili",
    "ta": "Tamil", "te": "Telugu", "tg": "Tajik", "th": "Thai",
    "tk": "Turkmen", "tl": "Tagalog", "tr": "Turkish", "tt": "Tatar",
    "uk": "Ukrainian", "ur": "Urdu", "uz": "Uzbek", "vi": "Vietnamese",
    "yi": "Yiddish", "yo": "Yoruba", "zh": "Chinese", "zu": "Zulu",
}


def detect_language(audio_path: str, model_name: str = "large-v3-turbo") -> dict:
    """
    Detect the language of an audio file using faster-whisper.

    Returns:
        dict with 'language' (ISO code), 'language_name', and 'confidence'.
    """
    from backend.core.transcriber import _get_model

    model = _get_model(model_name)

    # Use detect_language which only processes first 30 seconds
    segments, info = model.transcribe(
        audio_path,
        language=None,
        beam_size=1,
        vad_filter=True,
    )
    # We need to consume at least one segment to trigger detection
    # but info already has the detected language
    detected = info.language
    confidence = info.language_probability

    logger.info("Language detected: %s (%s) with confidence %.2f",
                detected, LANGUAGE_NAMES.get(detected, "Unknown"), confidence)

    return {
        "language": detected,
        "language_name": LANGUAGE_NAMES.get(detected, "Unknown"),
        "confidence": confidence,
    }


def get_supported_languages() -> list[dict]:
    """Return list of all supported languages."""
    return [
        {"code": code, "name": name}
        for code, name in sorted(LANGUAGE_NAMES.items(), key=lambda x: x[1])
    ]
