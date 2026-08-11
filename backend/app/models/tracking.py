from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
)

from app.db.base import Base


class TrackedChannel(Base):
    """A channel the background poller periodically snapshots for history."""

    __tablename__ = "tracked_channels"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(64), nullable=False, unique=True, index=True)
    label = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ChannelSnapshot(Base):
    """One point-in-time reading of a tracked channel's public stats."""

    __tablename__ = "channel_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(64), nullable=False, index=True)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    subscribers = Column(BigInteger, nullable=False, default=0)
    total_views = Column(BigInteger, nullable=False, default=0)
    video_count = Column(Integer, nullable=False, default=0)
    avg_views_per_day_recent = Column(Float, nullable=False, default=0.0)


class TrackedVideo(Base):
    """A video the background poller periodically snapshots for history."""

    __tablename__ = "tracked_videos"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(32), nullable=False, unique=True, index=True)
    label = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class VideoSnapshot(Base):
    """One point-in-time reading of a tracked video's stats + sentiment."""

    __tablename__ = "video_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(32), nullable=False, index=True)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    views = Column(BigInteger, nullable=False, default=0)
    likes = Column(BigInteger, nullable=False, default=0)
    comments = Column(BigInteger, nullable=False, default=0)
    virality_score = Column(Float, nullable=True)
    positive_pct = Column(Float, nullable=True)
    toxicity_pct = Column(Float, nullable=True)


class OAuthCredential(Base):
    """Stores a single connected creator's OAuth tokens for the YouTube
    Analytics API. One row per Google account connected via /oauth."""

    __tablename__ = "oauth_credentials"

    id = Column(Integer, primary_key=True, index=True)
    google_account_email = Column(String(255), nullable=True)
    channel_id = Column(String(64), nullable=True)
    access_token = Column(String(2048), nullable=False)
    refresh_token = Column(String(2048), nullable=False)
    token_expires_at = Column(DateTime, nullable=False)
    scope = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
