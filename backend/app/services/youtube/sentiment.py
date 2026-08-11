"""
Lexicon-based sentiment / emotion / toxicity scoring.

This intentionally avoids a transformer model: there is no ML-serving
infrastructure for this module yet and downloading model weights on every
deploy is unreliable. A weighted lexicon gets a genuinely useful directional
read (positive/negative/mixed, rough emotion mix, toxicity flag) without any
extra runtime dependency. It is not as precise as a fine-tuned classifier -
treat the scores as heuristics, not ground truth.
"""

import re
from collections import Counter

from app.services.youtube.language import prepare_for_sentiment

POSITIVE_WORDS = {
    "amazing": 2, "awesome": 2, "excellent": 2, "great": 1.5, "love": 2, "loved": 2,
    "best": 1.5, "good": 1, "nice": 1, "beautiful": 1.5, "brilliant": 2, "fantastic": 2,
    "perfect": 2, "incredible": 2, "wonderful": 1.5, "happy": 1, "win": 1, "won": 1,
    "goat": 1.5, "legend": 1.5, "class": 1, "quality": 1, "solid": 1, "underrated": 1,
    "clean": 0.5, "smooth": 0.5, "impressive": 1.5, "outstanding": 2, "world class": 2,
    "respect": 1, "proud": 1, "enjoyed": 1.5, "fun": 1, "thanks": 1, "thank you": 1.5,
}

NEGATIVE_WORDS = {
    "terrible": -2, "awful": -2, "worst": -2, "bad": -1, "hate": -2, "hated": -2,
    "poor": -1, "disappointing": -1.5, "disappointed": -1.5, "boring": -1, "trash": -2,
    "garbage": -2, "waste": -1.5, "overrated": -1, "sad": -1, "lost": -0.5, "lose": -0.5,
    "flop": -1.5, "embarrassing": -1.5, "embarrassment": -1.5, "disgrace": -2,
    "clickbait": -1.5, "misleading": -1.5, "fake": -1, "scam": -2, "sack": -1.5,
    "sacked": -1.5, "robbed": -1, "disaster": -2, "shambles": -2, "joke": -1,
}

EMOTION_LEXICON = {
    "excitement": ["hype", "excited", "can't wait", "cant wait", "let's go", "lets go",
                   "insane", "unreal", "wow", "omg", "incredible", "electric"],
    "satisfaction": ["satisfied", "happy", "pleased", "glad", "good job", "well done",
                      "deserved", "quality", "solid", "proud"],
    "disappointment": ["disappointed", "disappointing", "expected more", "let down",
                         "not good enough", "meh", "underwhelming"],
    "anger": ["angry", "furious", "disgrace", "shameful", "ridiculous", "unacceptable",
               "sack him", "sack them", "trash", "garbage", "hate", "sick of"],
    "confusion": ["confused", "what happened", "don't understand", "dont understand",
                   "why would", "makes no sense", "unclear"],
}

TOXICITY_MARKERS = [
    "idiot", "stupid", "moron", "trash club", "kill yourself", "kys", "loser",
    "shut up", "shut your mouth", "brain dead", "braindead", "clown", "pathetic",
    "disgrace to", "hate you", "die", "worthless",
]

# Generic aspects that show up across most YouTube content types (reviews,
# tutorials, vlogs, highlights). Not exhaustive - a lexicon, not a trained
# aspect extractor - but covers the common ones people actually comment about.
ASPECT_LEXICON = {
    "content/topic": ["content", "topic", "subject", "story", "storyline", "plot"],
    "audio/sound": ["audio", "sound", "voice", "mic", "microphone", "music", "volume"],
    "video/picture quality": ["quality", "resolution", "picture", "visuals", "footage", "graphics", "camera work"],
    "editing": ["editing", "cuts", "transitions", "pacing", "edit"],
    "length/pacing": ["too long", "too short", "length", "pacing", "dragged", "rushed"],
    "explanation/clarity": ["explanation", "explained", "clear", "confusing", "unclear", "easy to follow", "hard to follow"],
    "thumbnail/title": ["thumbnail", "title", "clickbait"],
    "price/value": ["price", "expensive", "cheap", "value", "worth it", "cost"],
    "performance": ["performance", "speed", "fast", "slow", "lag", "smooth"],
    "presenter/host": ["host", "presenter", "narrator", "commentary", "commentator"],
}

_SENTENCE_RE = re.compile(r"[.!?\n]+")
_WORD_RE = re.compile(r"[a-z']+")


def _normalize(text: str) -> str:
    return (text or "").lower()


def _phrase_score(text: str, lexicon: dict) -> float:
    score = 0.0
    for phrase, weight in lexicon.items():
        if phrase in text:
            score += weight * text.count(phrase)
    return score


def score_text(text: str) -> dict:
    """Score a single piece of text: sentiment polarity, label, emotions, toxicity."""

    normalized = _normalize(text)
    words = _WORD_RE.findall(normalized)

    pos = _phrase_score(normalized, POSITIVE_WORDS)
    neg = _phrase_score(normalized, NEGATIVE_WORDS)
    raw = pos + neg
    magnitude = max(len(words), 1) ** 0.5
    polarity = max(-1.0, min(1.0, raw / magnitude)) if raw else 0.0

    if pos > 0 and neg > 0:
        label = "mixed"
    elif polarity > 0.15:
        label = "positive"
    elif polarity < -0.15:
        label = "negative"
    else:
        label = "neutral"

    emotions = {}
    for emotion, phrases in EMOTION_LEXICON.items():
        hits = sum(normalized.count(phrase) for phrase in phrases)
        if hits:
            emotions[emotion] = hits

    is_toxic = any(marker in normalized for marker in TOXICITY_MARKERS)

    return {
        "polarity": round(polarity, 3),
        "label": label,
        "emotions": emotions,
        "is_toxic": is_toxic,
    }


def _flatten_comment_text(item: dict) -> str:
    snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
    return snippet.get("textDisplay") or snippet.get("textOriginal") or ""


def flatten_comment_text(item: dict) -> str:
    """Public accessor - pulls the plain-text body out of a commentThreads item."""
    return _flatten_comment_text(item)


def _flatten_live_chat_text(item: dict) -> str:
    return item.get("snippet", {}).get("displayMessage", "")


def _aggregate_texts(texts: list[str]) -> dict:
    texts = [t for t in texts if t]

    if not texts:
        return {
            "sample_size": 0,
            "sentiment_breakdown": {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0},
            "overall_positive_pct": 0,
            "dominant_emotions": {},
            "toxicity_pct": 0,
            "representative_comments": [],
        }

    scored = [score_text(t) for t in texts]

    label_counts = Counter(s["label"] for s in scored)
    total = len(scored)
    positive_pct = round(100 * label_counts.get("positive", 0) / total, 1)

    emotion_counter = Counter()
    for s in scored:
        for emotion, hits in s["emotions"].items():
            emotion_counter[emotion] += hits
    total_emotion_hits = sum(emotion_counter.values()) or 1
    dominant_emotions = {
        emotion: round(100 * count / total_emotion_hits, 1)
        for emotion, count in emotion_counter.most_common(5)
    }

    toxic_count = sum(1 for s in scored if s["is_toxic"])
    toxicity_pct = round(100 * toxic_count / total, 1)

    most_positive = max(zip(texts, scored), key=lambda pair: pair[1]["polarity"], default=None)
    most_negative = min(zip(texts, scored), key=lambda pair: pair[1]["polarity"], default=None)

    representative = []
    if most_positive and most_positive[1]["polarity"] > 0:
        representative.append({"text": most_positive[0][:280], "type": "most_positive"})
    if most_negative and most_negative[1]["polarity"] < 0:
        representative.append({"text": most_negative[0][:280], "type": "most_critical"})

    return {
        "sample_size": total,
        "sentiment_breakdown": {
            "positive": label_counts.get("positive", 0),
            "neutral": label_counts.get("neutral", 0),
            "negative": label_counts.get("negative", 0),
            "mixed": label_counts.get("mixed", 0),
        },
        "overall_positive_pct": positive_pct,
        "dominant_emotions": dominant_emotions,
        "toxicity_pct": toxicity_pct,
        "representative_comments": representative,
    }


def aggregate_texts(texts: list[str]) -> dict:
    """Public accessor for _aggregate_texts - scores an arbitrary list of raw
    strings (not tied to any specific YouTube resource shape)."""
    return _aggregate_texts(texts)


def analyze_comments(comment_threads: list[dict]) -> dict:
    """Aggregate sentiment/emotion/toxicity across a list of commentThreads items."""

    return _aggregate_texts([_flatten_comment_text(item) for item in comment_threads])


def analyze_live_chat(messages: list[dict]) -> dict:
    """Aggregate sentiment/emotion/toxicity across a list of liveChatMessages items."""

    return _aggregate_texts([_flatten_live_chat_text(item) for item in messages])


def analyze_comments_multilingual(comment_threads: list[dict]) -> dict:
    """Like analyze_comments, but detects each comment's language and
    translates non-English text to English before scoring. Slower (one
    translation API call per non-English comment) - use as an opt-in, not
    the default path."""

    texts = [_flatten_comment_text(item) for item in comment_threads]
    texts = [t for t in texts if t]

    language_counter = Counter()
    prepared = []
    for text in texts:
        info = prepare_for_sentiment(text)
        language_counter[info["language"] or "unknown"] += 1
        prepared.append(info["text"])

    result = _aggregate_texts(prepared)
    total = sum(language_counter.values()) or 1
    result["language_breakdown"] = {
        lang: {"count": count, "pct": round(100 * count / total, 1)}
        for lang, count in language_counter.most_common(10)
    }
    return result


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]


def analyze_aspects(texts: list[str]) -> dict:
    """Aspect-based sentiment: for each sentence mentioning a known aspect
    (camera, audio, pacing, price...), score that sentence's sentiment and
    attribute it to the aspect. A single comment can touch multiple aspects
    with different sentiment each ("camera is great but battery is bad")."""

    aspect_scores: dict[str, list[float]] = {}

    for text in texts:
        if not text:
            continue
        for sentence in _split_sentences(text):
            normalized = _normalize(sentence)
            matched_aspects = [
                aspect for aspect, keywords in ASPECT_LEXICON.items()
                if any(kw in normalized for kw in keywords)
            ]
            if not matched_aspects:
                continue
            polarity = score_text(sentence)["polarity"]
            for aspect in matched_aspects:
                aspect_scores.setdefault(aspect, []).append(polarity)

    results = {}
    for aspect, scores in aspect_scores.items():
        avg = sum(scores) / len(scores)
        positive = sum(1 for s in scores if s > 0.15)
        negative = sum(1 for s in scores if s < -0.15)
        label = "positive" if avg > 0.15 else "negative" if avg < -0.15 else "mixed" if (positive and negative) else "neutral"
        results[aspect] = {
            "mentions": len(scores),
            "avg_polarity": round(avg, 3),
            "label": label,
            "positive_mentions": positive,
            "negative_mentions": negative,
        }

    return dict(sorted(results.items(), key=lambda kv: kv[1]["mentions"], reverse=True))
