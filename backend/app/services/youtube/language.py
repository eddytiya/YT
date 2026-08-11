"""
Language detection + translation for non-English comments.

Detection is local (langdetect, pure Python, no model download). Translation
calls MyMemory's free public API (no key required, ~5000 words/day
unauthenticated) - if it's unreachable or rate-limited, callers fall back to
scoring the original text rather than failing the whole request.
"""

import logging

import requests
from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0  # deterministic detection results

logger = logging.getLogger(__name__)

MYMEMORY_ENDPOINT = "https://api.mymemory.translated.net/get"
_translation_cache: dict[tuple[str, str], str] = {}
_MAX_CACHE_ENTRIES = 2000


def detect_language(text: str) -> str | None:
    """Returns an ISO 639-1 code (e.g. 'es', 'hi') or None if undetectable."""

    text = (text or "").strip()
    if len(text) < 3:
        return None
    try:
        return detect(text)
    except LangDetectException:
        return None


def translate_to_english(text: str, source_lang: str, timeout: int = 8) -> str:
    """Best-effort translation; returns the original text on any failure."""

    if not text or source_lang == "en":
        return text

    cache_key = (source_lang, text)
    if cache_key in _translation_cache:
        return _translation_cache[cache_key]

    try:
        response = requests.get(
            MYMEMORY_ENDPOINT,
            params={"q": text[:500], "langpair": f"{source_lang}|en"},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        translated = data.get("responseData", {}).get("translatedText")
        if not translated or data.get("responseStatus") not in (200, "200"):
            return text
    except Exception:
        logger.warning("Translation failed for lang=%s; scoring original text", source_lang)
        return text

    if len(_translation_cache) >= _MAX_CACHE_ENTRIES:
        _translation_cache.clear()
    _translation_cache[cache_key] = translated
    return translated


def prepare_for_sentiment(text: str) -> dict:
    """Detects language and translates non-English text to English.

    Returns {"text": <english text to score>, "original_text": <as-is>,
    "language": <detected code or None>, "translated": bool}.
    """

    language = detect_language(text)
    if not language or language == "en":
        return {"text": text, "original_text": text, "language": language, "translated": False}

    translated = translate_to_english(text, language)
    return {
        "text": translated,
        "original_text": text,
        "language": language,
        "translated": translated != text,
    }
