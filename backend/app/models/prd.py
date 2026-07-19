from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class PRDRequirement(Base):
    __tablename__ = "prd_requirements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    finding_id = Column(Integer, ForeignKey("analysis_findings.id"), nullable=True)
    requirement_text = Column(Text, nullable=False)
    requirement_type = Column(String(50), nullable=True)
    priority = Column(String(20), nullable=True, default="medium")
    version = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True, default="draft")
    source_review_ids = Column(JSON, nullable=True)
    is_model_generated = Column(Boolean, default=True)
    
    test_cases = relationship("TestCase", back_populates="requirement")

class PRDVersion(Base):
    __tablename__ = "prd_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    version_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=1)
    estimated_effort = Column(String(50), nullable=True)
    requirements_count = Column(Integer, default=0)