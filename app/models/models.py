from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    strategy = Column(String(50), nullable=False)
    source_url = Column(String(1000), nullable=True)
    source_details = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    # Stores the last observed content hash for direct-page monitoring.
    last_content_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_checked_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    articles = relationship(
        "Article",
        back_populates="website",
        cascade="all, delete-orphan"
    )

    monitoring_checks = relationship(
        "MonitoringCheck",
        back_populates="website",
        cascade="all, delete-orphan"
    )


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)

    website_id = Column(
        Integer,
        ForeignKey("websites.id"),
        nullable=False,
        index=True
    )

    url = Column(String(1000), nullable=False, unique=True)
    canonical_url = Column(String(1000), nullable=True)

    title = Column(String(500), nullable=False)
    author = Column(String(200), nullable=True)
    published_at = Column(DateTime, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    detection_delay_seconds = Column(Float, nullable=True)

    body = Column(Text, nullable=True)
    image_urls = Column(Text, nullable=True)
    categories = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    website = relationship(
        "Website",
        back_populates="articles"
    )


class MonitoringCheck(Base):
    __tablename__ = "monitoring_checks"

    id = Column(Integer, primary_key=True, index=True)

    website_id = Column(
        Integer,
        ForeignKey("websites.id"),
        nullable=False,
        index=True
    )

    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    success = Column(Boolean, nullable=False)
    strategy_used = Column(String(50), nullable=True)

    articles_found = Column(Integer, default=0, nullable=False)
    new_articles = Column(Integer, default=0, nullable=False)

    response_time_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    website = relationship(
        "Website",
        back_populates="monitoring_checks"
    )