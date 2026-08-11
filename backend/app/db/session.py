from sqlalchemy.orm import Session, sessionmaker

from app.db.database import engine

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """Create a database session for each request."""

    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
