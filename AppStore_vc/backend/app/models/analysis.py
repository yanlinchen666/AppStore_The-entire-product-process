from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(String(50), nullable=False, index=True)
    app_name = Column(String(255), nullable=False)
    analysis_goal = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    total_reviews = Column(Integer, default=0)
    cleaned_reviews = Column(Integer, default=0)
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    topics = relationship("AnalysisTopic", back_populates="run")
    findings = relationship("AnalysisFinding", back_populates="run")

class AnalysisTopic(Base):
    __tablename__ = "analysis_topics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    sample_count = Column(Integer, default=0)
    is_model_generated = Column(Boolean, default=True)
    
    run = relationship("AnalysisRun", back_populates="topics")
    findings = relationship("AnalysisFinding", back_populates="topic")

class AnalysisFinding(Base):
    __tablename__ = "analysis_findings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("analysis_topics.id"), nullable=True)
    finding_text = Column(Text, nullable=False)
    evidence_review_ids = Column(JSON, nullable=True)
    sample_count = Column(Integer, default=0)
    confidence = Column(Float, nullable=True)
    has_conflict = Column(Boolean, default=False)
    conflicting_review_ids = Column(JSON, nullable=True)
    is_model_generated = Column(Boolean, default=True)
    
    run = relationship("AnalysisRun", back_populates="findings")
    topic = relationship("AnalysisTopic", back_populates="findings")