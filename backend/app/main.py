import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as youtube_router
from app.core.config import settings
from app.db.base import Base
from app.db.database import engine
from app.db.session import SessionLocal
from app.services.youtube.snapshot_sync import run_snapshot_sync

# Import models so their tables register on Base.metadata before create_all.
from app import models  # noqa: F401

logger = logging.getLogger(__name__)


async def snapshot_sync_loop():
    """Snapshot tracked channels/videos for trend history, at a quota-safe
    interval (avoids search.list entirely - see services/youtube/snapshot_sync)."""
    interval_seconds = max(settings.SNAPSHOT_SYNC_INTERVAL_HOURS, 1) * 60 * 60
    while True:
        db = SessionLocal()
        try:
            result = await asyncio.to_thread(run_snapshot_sync, db)
            logger.info("Snapshot sync complete: %s", result)
        except Exception:
            logger.exception("Snapshot sync failed")
        finally:
            db.close()
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(snapshot_sync_loop()) if settings.SNAPSHOT_SYNC_ENABLED else None
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="YouTube Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    # Vercel preview deployments get a fresh, unpredictable subdomain per
    # branch/PR (project-git-branch-team.vercel.app) - a fixed origin list
    # can never include those, so allow the whole *.vercel.app pattern too.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(youtube_router)


@app.get("/")
def root():
    return {"service": "YouTube Intelligence Platform API", "docs": "/docs"}
