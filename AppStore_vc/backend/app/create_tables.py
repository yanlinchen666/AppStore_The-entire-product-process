import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine
from app.models.review import Review, CleanedReview
from app.models.analysis import AnalysisRun, AnalysisTopic, AnalysisFinding
from app.models.prd import PRDRequirement, PRDVersion
from app.models.testcase import TestCase

def create_all_tables():
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully!")

if __name__ == "__main__":
    create_all_tables()