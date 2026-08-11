"""
Real trained models, used only when there's enough of your own tracked-video
history to fit them. With a handful of data points these will overfit and
say so honestly - the heuristics in analytics.py remain the default until
you've accumulated enough snapshot history for a model to be meaningful.
"""

from datetime import datetime

import numpy as np
from sklearn.ensemble import RandomForestRegressor

MIN_SAMPLES_FOR_RF = 8
MIN_SAMPLES_FOR_ARIMA = 10


def _title_features(title: str, published_at: str | None) -> list[float]:
    length = len(title)
    caps_ratio = sum(1 for c in title if c.isupper()) / max(sum(1 for c in title if c.isalpha()), 1)
    word_count = len(title.split())
    exclaim = title.count("!")
    question = title.count("?")

    hour = 12
    weekday = 0
    if published_at:
        try:
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            hour = dt.hour
            weekday = dt.weekday()
        except ValueError:
            pass

    return [length, caps_ratio, word_count, exclaim, question, hour, weekday]


def train_virality_model(samples: list[dict]) -> dict:
    """samples: [{"title": str, "published_at": str, "virality_score": float}, ...]
    Trains a small RandomForest on your own tracked-video history and returns
    both the fitted feature importances and a usable predict() closure info -
    since we can't return a live closure over HTTP, callers get importances
    plus a re-predict endpoint that retrains on demand (datasets here are
    small enough that retraining per-call is cheap)."""

    if len(samples) < MIN_SAMPLES_FOR_RF:
        return {
            "trained": False,
            "sample_size": len(samples),
            "min_required": MIN_SAMPLES_FOR_RF,
            "note": f"Need at least {MIN_SAMPLES_FOR_RF} tracked videos with history to train a model.",
        }

    X = np.array([_title_features(s["title"], s.get("published_at")) for s in samples])
    y = np.array([s["virality_score"] for s in samples])

    model = RandomForestRegressor(n_estimators=100, max_depth=4, random_state=0, min_samples_leaf=2)
    model.fit(X, y)

    feature_names = ["title_length", "caps_ratio", "word_count", "exclaim_count", "question_count", "publish_hour", "publish_weekday"]
    importances = dict(zip(feature_names, [round(float(v), 3) for v in model.feature_importances_]))

    # In-sample fit quality only - with this few samples, held-out validation
    # isn't meaningful. Framed honestly in the response.
    r2 = round(float(model.score(X, y)), 3)

    return {
        "trained": True,
        "sample_size": len(samples),
        "feature_importances": dict(sorted(importances.items(), key=lambda kv: kv[1], reverse=True)),
        "in_sample_r2": r2,
        "note": "Trained on your own tracked-video history. With this few samples, treat this as directional, not predictive.",
        "_model": model,  # internal use only, stripped before returning to the API layer
    }


def predict_with_model(model: RandomForestRegressor, title: str, published_at: str | None) -> float:
    X = np.array([_title_features(title, published_at)])
    return round(float(model.predict(X)[0]), 1)


def forecast_subscribers_arima(history: list[dict]) -> dict:
    """history: [{"captured_at": iso str, "subscribers": int}, ...] ascending order.
    Forecasts the next snapshot point, not a fixed calendar horizon - snapshot
    cadence depends on how often the poller (or you, manually) runs it."""

    if len(history) < MIN_SAMPLES_FOR_ARIMA:
        return {
            "method": "insufficient_data",
            "sample_size": len(history),
            "min_required": MIN_SAMPLES_FOR_ARIMA,
        }

    from statsmodels.tsa.arima.model import ARIMA

    series = np.array([h["subscribers"] for h in history], dtype=float)

    try:
        model = ARIMA(series, order=(1, 1, 1))
        fitted = model.fit()
        forecast = fitted.forecast(steps=1)
        point = float(forecast[0])
        resid_std = float(np.std(fitted.resid)) if len(fitted.resid) else point * 0.02
        return {
            "method": "arima",
            "sample_size": len(history),
            "estimated_subscribers": round(point),
            "estimated_range": [round(point - resid_std * 1.5), round(point + resid_std * 1.5)],
        }
    except Exception:
        return {"method": "arima_failed", "sample_size": len(history)}
