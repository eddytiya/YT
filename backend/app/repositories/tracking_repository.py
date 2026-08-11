from datetime import datetime

from sqlalchemy.orm import Session

from app.models.tracking import (
    ChannelSnapshot,
    TrackedChannel,
    TrackedVideo,
    VideoSnapshot,
)


class TrackingRepository:
    """Persistence for tracked channels/videos and their history snapshots."""

    def __init__(self, db: Session):
        self.db = db

    # -- tracked channels ---------------------------------------------

    def add_tracked_channel(self, channel_id: str, label: str | None) -> TrackedChannel:
        existing = self.db.query(TrackedChannel).filter_by(channel_id=channel_id).first()
        if existing:
            existing.is_active = True
            existing.label = label or existing.label
            self.db.commit()
            self.db.refresh(existing)
            return existing

        row = TrackedChannel(channel_id=channel_id, label=label)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_tracked_channels(self, active_only: bool = True) -> list[TrackedChannel]:
        query = self.db.query(TrackedChannel)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(TrackedChannel.created_at.desc()).all()

    def remove_tracked_channel(self, tracked_id: int) -> bool:
        row = self.db.query(TrackedChannel).filter_by(id=tracked_id).first()
        if not row:
            return False
        row.is_active = False
        self.db.commit()
        return True

    # -- tracked videos -------------------------------------------------

    def add_tracked_video(self, video_id: str, label: str | None) -> TrackedVideo:
        existing = self.db.query(TrackedVideo).filter_by(video_id=video_id).first()
        if existing:
            existing.is_active = True
            existing.label = label or existing.label
            self.db.commit()
            self.db.refresh(existing)
            return existing

        row = TrackedVideo(video_id=video_id, label=label)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_tracked_videos(self, active_only: bool = True) -> list[TrackedVideo]:
        query = self.db.query(TrackedVideo)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(TrackedVideo.created_at.desc()).all()

    def remove_tracked_video(self, tracked_id: int) -> bool:
        row = self.db.query(TrackedVideo).filter_by(id=tracked_id).first()
        if not row:
            return False
        row.is_active = False
        self.db.commit()
        return True

    # -- snapshots --------------------------------------------------------

    def save_channel_snapshot(self, channel_id: str, **fields) -> ChannelSnapshot:
        snapshot = ChannelSnapshot(channel_id=channel_id, captured_at=datetime.utcnow(), **fields)
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def save_video_snapshot(self, video_id: str, **fields) -> VideoSnapshot:
        snapshot = VideoSnapshot(video_id=video_id, captured_at=datetime.utcnow(), **fields)
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def get_channel_history(self, channel_id: str, limit: int = 90) -> list[ChannelSnapshot]:
        return (
            self.db.query(ChannelSnapshot)
            .filter_by(channel_id=channel_id)
            .order_by(ChannelSnapshot.captured_at.asc())
            .limit(limit)
            .all()
        )

    def get_video_history(self, video_id: str, limit: int = 90) -> list[VideoSnapshot]:
        return (
            self.db.query(VideoSnapshot)
            .filter_by(video_id=video_id)
            .order_by(VideoSnapshot.captured_at.asc())
            .limit(limit)
            .all()
        )
