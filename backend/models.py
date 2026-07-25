from datetime import datetime

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
    created_at = Column(DateTime, default=datetime.utcnow)
