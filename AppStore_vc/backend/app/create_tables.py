from database import Base, engine
from models import Review, CleanedReview, AnalysisRun, AnalysisTopic, AnalysisFinding, PRDRequirement, PRDVersion, TestCase

def create_all_tables():
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully!")

if __name__ == "__main__":
    create_all_tables()