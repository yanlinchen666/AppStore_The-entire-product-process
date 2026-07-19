import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

from app.database import SessionLocal, engine, Base
from app.models import Review, CleanedReview
from app.services.collector import collect_and_save_reviews, extract_app_id_from_url, extract_app_name_from_url
from app.services.cleaner import clean_reviews

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_APP_URL = "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684"

def reset_database():
    logger.info("=" * 60)
    logger.info("Resetting database - dropping all tables")
    logger.info("=" * 60)
    
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    logger.info("✓ Database reset completed")

def collect_real_reviews():
    logger.info("\n" + "=" * 60)
    logger.info("Collecting REAL App Store reviews")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        app_id = extract_app_id_from_url(TARGET_APP_URL)
        app_name = extract_app_name_from_url(TARGET_APP_URL)
        
        logger.info(f"Target: {TARGET_APP_URL}")
        logger.info(f"App ID: {app_id}")
        logger.info(f"App Name: {app_name}")
        
        logger.info("Collecting reviews...")
        saved_count, collected_app_id, collected_app_name = collect_and_save_reviews(
            db=db,
            app_url=TARGET_APP_URL,
            country="us",
            max_reviews=200
        )
        
        logger.info(f"✓ Collected {saved_count} REAL reviews")
        
        total = db.query(Review).count()
        logger.info(f"✓ Total reviews in database: {total}")
        
        sample = db.query(Review).first()
        if sample:
            logger.info(f"\n✓ Sample real review:")
            logger.info(f"  Author: {sample.author}")
            logger.info(f"  Rating: {sample.rating}/5")
            logger.info(f"  Title: {sample.title}")
            logger.info(f"  Content: {sample.content[:100]}...")
            logger.info(f"  Date: {sample.review_date}")
            logger.info(f"  Version: {sample.app_version}")
        
        return app_id
        
    finally:
        db.close()

def clean_real_reviews(app_id):
    logger.info("\n" + "=" * 60)
    logger.info("Cleaning REAL reviews")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        cleaned_count = clean_reviews(db, app_id)
        logger.info(f"✓ Cleaned {cleaned_count} reviews")
        
        from sqlalchemy import func
        
        total_cleaned = db.query(CleanedReview).count()
        logger.info(f"✓ Total cleaned reviews: {total_cleaned}")
        
        lang_counts = db.query(
            CleanedReview.language,
            func.count(CleanedReview.id)
        ).group_by(CleanedReview.language).all()
        
        logger.info("\n✓ Language distribution:")
        for lang, count in lang_counts:
            logger.info(f"  - {lang}: {count}")
        
        avg_sentiment = db.query(func.avg(CleanedReview.sentiment)).scalar()
        logger.info(f"\n✓ Average sentiment: {avg_sentiment:.2f}")
        
        duplicates = db.query(CleanedReview).filter(CleanedReview.has_duplicate == True).count()
        logger.info(f"✓ Duplicate reviews: {duplicates}")
        
    finally:
        db.close()

if __name__ == "__main__":
    try:
        reset_database()
        app_id = collect_real_reviews()
        clean_real_reviews(app_id)
        
        logger.info("\n" + "=" * 60)
        logger.info("Database now contains ONLY REAL data! ✓")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise