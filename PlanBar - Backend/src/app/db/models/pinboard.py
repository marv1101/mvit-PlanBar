from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class PinboardThread(Base):
    __tablename__ = "pinboard_threads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    author = relationship("User", backref="pinboard_threads", lazy="selectin")
    messages = relationship(
        "PinboardMessage",
        back_populates="thread",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="PinboardMessage.created_at",
    )


class PinboardMessage(Base):
    __tablename__ = "pinboard_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("pinboard_threads.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    thread = relationship("PinboardThread", back_populates="messages")
    author = relationship("User", backref="pinboard_messages", lazy="selectin")
    documents = relationship(
        "PinboardDocument",
        back_populates="message",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class PinboardDocument(Base):
    __tablename__ = "pinboard_documents"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("pinboard_messages.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    message = relationship("PinboardMessage", back_populates="documents")
