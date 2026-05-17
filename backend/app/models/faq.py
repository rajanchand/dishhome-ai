from sqlalchemy import Column, String, Boolean, JSON, Float, Integer
from .base import Base

class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(String, primary_key=True)
    question_en = Column(String, nullable=False)
    question_ne = Column(String, nullable=False)
    answer_en = Column(String, nullable=False)
    answer_ne = Column(String, nullable=False)
    category = Column(String, nullable=False)
    tags = Column(JSON, nullable=False, default=list)

class Voice(Base):
    __tablename__ = "voices"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    language = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    preview_url = Column(String, nullable=True)
    provider = Column(String, nullable=False)
    model_id = Column(String, nullable=False)
