from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.database import Base

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(String(50), nullable=False, index=True)
    app_name = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    rating = Column(Integer, nullable=False)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    review_date = Column(DateTime, nullable=False)
    app_version = Column(String(50), nullable=True)
    is_edited = Column(Boolean, default=False)
    vote_count = Column(Integer, default=0)
    vote_sum = Column(Integer, default=0)
    source_url = Column(String(500), nullable=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())

class CleanedReview(Base):
    __tablename__ = "cleaned_reviews"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, nullable=False, index=True)
    app_id = Column(String(50), nullable=False, index=True)
    cleaned_content = Column(Text, nullable=False)
    language = Column(String(10), nullable=True)
    sentiment = Column(Float, nullable=True)
    word_count = Column(Integer, nullable=True)
    has_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, nullable=True)
    is_valid = Column(Boolean, default=True)
    processed_at = Column(DateTime, default=func.now())