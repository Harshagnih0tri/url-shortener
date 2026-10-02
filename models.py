from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Url(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True)
    code = Column(String(8), unique=True, nullable=False, index=True)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    clicks = relationship("Click", back_populates="url", cascade="all, delete-orphan")


class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True)
    url_id = Column(Integer, ForeignKey("urls.id"), nullable=False, index=True)
    clicked_at = Column(DateTime, default=utcnow, nullable=False)
    user_agent = Column(Text, nullable=True)
    referrer = Column(Text, nullable=True)

    url = relationship("Url", back_populates="clicks")