from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class TestCase(Base):
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(Integer, ForeignKey("prd_requirements.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    case_title = Column(String(500), nullable=False)
    case_description = Column(Text, nullable=True)
    test_steps = Column(JSON, nullable=True)
    expected_result = Column(Text, nullable=False)
    test_type = Column(String(50), nullable=True)
    priority = Column(String(20), nullable=True, default="medium")
    source_review_ids = Column(JSON, nullable=True)
    is_model_generated = Column(Boolean, default=True)
    
    requirement = relationship("PRDRequirement", back_populates="test_cases")