from sqlalchemy import Column, String, Integer, Float, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base

class Label(Base):
    __tablename__ = "labels"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    color = Column(String, nullable=False)

class SavedReply(Base):
    __tablename__ = "saved_replies"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    language = Column(String, nullable=False)

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    email = Column(String, nullable=True)
    customer_id = Column(String, nullable=True)
    labels = Column(JSON, nullable=False, default=list)
    last_contacted_at = Column(String, nullable=True)
    notes = Column(String, nullable=True)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True)
    channel = Column(String, nullable=False)
    contact_id = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    labels = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False)
    last_message_at = Column(String, nullable=True)
    messages = Column(JSON, nullable=False, default=list)
