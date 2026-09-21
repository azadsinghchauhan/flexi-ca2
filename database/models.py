import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.db import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    keywords = Column(Text, nullable=False)  # Comma-separated or JSON list
    frequency = Column(String(50), default="Daily")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    articles = relationship("Article", back_populates="topic", cascade="all, delete-orphan", lazy="selectin")
    logs = relationship("MonitoringLog", back_populates="topic", cascade="all, delete-orphan", lazy="selectin")

    def get_keywords_list(self):
        """Returns keywords as a clean list of trimmed strings."""
        if not self.keywords:
            return []
        try:
            parsed = json.loads(self.keywords)
            if isinstance(parsed, list):
                return [k.strip() for k in parsed if k.strip()]
        except Exception:
            pass
        return [k.strip() for k in self.keywords.split(",") if k.strip()]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "keywords": self.get_keywords_list(),
            "raw_keywords": self.keywords,
            "frequency": self.frequency,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "article_count": len(self.articles) if self.articles else 0,
        }


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=False, index=True)
    source = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)
    category = Column(String(100), default="General")
    summary = Column(Text, nullable=True)
    key_points = Column(Text, nullable=True)  # JSON-encoded array of 3 items
    importance = Column(String(20), default="Medium")  # Low, Medium, High
    relevance = Column(Integer, default=50)  # 0 to 100
    trend = Column(String(255), nullable=True)  # Short trend label
    entities = Column(Text, nullable=True)  # JSON-encoded array
    reason = Column(Text, nullable=True)  # Reason for importance rating
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topic = relationship("Topic", back_populates="articles", lazy="joined")
    alerts = relationship("Alert", back_populates="article", cascade="all, delete-orphan", lazy="selectin")

    def get_key_points_list(self):
        if not self.key_points:
            return []
        try:
            parsed = json.loads(self.key_points)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [p.strip() for p in self.key_points.split("\n") if p.strip()]

    def get_entities_list(self):
        if not self.entities:
            return []
        try:
            parsed = json.loads(self.entities)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [e.strip() for e in self.entities.split(",") if e.strip()]

    def to_dict(self):
        return {
            "id": self.id,
            "topic_id": self.topic_id,
            "topic_name": self.topic.name if self.topic else None,
            "title": self.title,
            "url": self.url,
            "canonical_url": self.canonical_url,
            "source": self.source,
            "published_at": self.published_at.strftime("%Y-%m-%d %H:%M") if self.published_at else None,
            "category": self.category,
            "summary": self.summary,
            "key_points": self.get_key_points_list(),
            "importance": self.importance,
            "relevance": self.relevance,
            "trend": self.trend,
            "entities": self.get_entities_list(),
            "reason": self.reason,
            "is_demo": self.is_demo,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
        }


class MonitoringLog(Base):
    __tablename__ = "monitoring_logs"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    run_time = Column(DateTime, default=datetime.utcnow)
    articles_found = Column(Integer, default=0)
    articles_processed = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    status = Column(String(50), default="Success")  # Success, Warning, Error
    error = Column(Text, nullable=True)
    steps = Column(Text, nullable=True)  # JSON-encoded list of step audit logs

    # Relationships
    topic = relationship("Topic", back_populates="logs", lazy="joined")

    def get_steps_list(self):
        if not self.steps:
            return []
        try:
            return json.loads(self.steps)
        except Exception:
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "topic_id": self.topic_id,
            "topic_name": self.topic.name if self.topic else f"Topic #{self.topic_id}",
            "run_time": self.run_time.strftime("%Y-%m-%d %H:%M:%S") if self.run_time else None,
            "articles_found": self.articles_found,
            "articles_processed": self.articles_processed,
            "duplicates_removed": self.duplicates_removed,
            "status": self.status,
            "error": self.error,
            "steps": self.get_steps_list(),
        }


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    article = relationship("Article", back_populates="alerts", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "article_id": self.article_id,
            "article_title": self.article.title if self.article else "Unknown Article",
            "topic_name": self.article.topic.name if self.article and self.article.topic else "General",
            "importance": self.article.importance if self.article else "High",
            "message": self.message,
            "read": self.read,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
