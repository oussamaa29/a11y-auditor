from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Text, DateTime

from database import Base


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    critical_count = Column(Integer, default=0)
    serious_count = Column(Integer, default=0)
    moderate_count = Column(Integer, default=0)
    minor_count = Column(Integer, default=0)
    passes_count = Column(Integer, default=0)
    violations_json = Column(Text, nullable=False)
    error = Column(Text, nullable=True)
    # Heure UTC, stockée sans fuseau (SQLite ne les conserve pas)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
