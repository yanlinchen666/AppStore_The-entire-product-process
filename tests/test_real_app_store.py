import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

from app.database import SessionLocal, engine, Base
from app.services.collector import collect_and_save_reviews, extract_app_id_from_url, extract_app_name_from_url
from app.services.cleaner import clean_reviews
from app.models import Review, CleanedReview

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_APP_URL = "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684"

def test_real_app_store_collection():
    logger.info("=" * 60)
    logger.info("Testing Real App Store Data Collection")
    logger.info("=" * 60)
    
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    logger.info(f"Target app: {TARGET_APP_URL}")
    
    app_id = extract_app_id_from_url(TARGET_APP_URL)
    app_name = extract_app_name_from_url(TARGET_APP_URL)
    
    logger.info(f"Extracted app_id: {app_id}")
    logger.info(f"Extracted app_name: {app_name}")
    
    assert app_id is not None, "Failed to extract app_id"
    
    try:
        logger.info("Starting to collect real reviews from App Store...")
        saved_count, collected_app_id, collected_app_name = collect_and_save_reviews(
            db=db,
            app_url=TARGET_APP_URL,
            country="us",
            max_reviews=100
        )
        
        logger.info(f"✓ Successfully collected {saved_count} new reviews")
        logger.info(f"✓ App ID: {collected_app_id}")
        logger.info(f"✓ App Name: {collected_app_name}")
        
        total_reviews = db.query(Review).filter(Review.app_id == app_id).count()
        logger.info(f"✓ Total reviews in database: {total_reviews}")
        
        sample_review = db.query(Review).filter(Review.app_id == app_id).first()
        if sample_review:
            logger.info(f"\n✓ Sample review:")
            logger.info(f"  Author: {sample_review.author}")
            logger.info(f"  Rating: {sample_review.rating}/5")
            logger.info(f"  Title: {sample_review.title}")
            logger.info(f"  Content: {sample_review.content[:100]}...")
            logger.info(f"  Date: {sample_review.review_date}")
            logger.info(f"  Version: {sample_review.app_version}")
        
    except Exception as e:
        logger.error(f"Error collecting reviews: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
    
    return app_id

def test_real_app_store_cleaning(app_id):
    logger.info("\n" + "=" * 60)
    logger.info("Testing Real App Store Data Cleaning")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        logger.info("Starting to clean reviews...")
        cleaned_count = clean_reviews(db, app_id)
        
        logger.info(f"✓ Successfully cleaned {cleaned_count} reviews")
        
        total_cleaned = db.query(CleanedReview).filter(CleanedReview.app_id == app_id).count()
        logger.info(f"✓ Total cleaned reviews: {total_cleaned}")
        
        from sqlalchemy import func
        
        language_counts = db.query(
            CleanedReview.language,
            func.count(CleanedReview.id)
        ).filter(CleanedReview.app_id == app_id).group_by(CleanedReview.language).all()
        
        logger.info("\n✓ Language distribution:")
        for lang, count in language_counts:
            logger.info(f"  - {lang}: {count} reviews")
        
        avg_sentiment = db.query(func.avg(CleanedReview.sentiment)).filter(
            CleanedReview.app_id == app_id
        ).scalar()
        
        positive_count = db.query(CleanedReview).filter(
            CleanedReview.app_id == app_id,
            CleanedReview.sentiment > 0
        ).count()
        
        negative_count = db.query(CleanedReview).filter(
            CleanedReview.app_id == app_id,
            CleanedReview.sentiment < 0
        ).count()
        
        neutral_count = db.query(CleanedReview).filter(
            CleanedReview.app_id == app_id,
            CleanedReview.sentiment == 0
        ).count()
        
        logger.info("\n✓ Sentiment distribution:")
        logger.info(f"  - Average sentiment: {avg_sentiment:.2f}")
        logger.info(f"  - Positive: {positive_count}")
        logger.info(f"  - Negative: {negative_count}")
        logger.info(f"  - Neutral: {neutral_count}")
        
        duplicates = db.query(CleanedReview).filter(
            CleanedReview.app_id == app_id,
            CleanedReview.has_duplicate == True
        ).count()
        
        logger.info(f"\n✓ Found {duplicates} duplicate reviews")
        
        sample_cleaned = db.query(CleanedReview).filter(CleanedReview.app_id == app_id).first()
        if sample_cleaned:
            logger.info("\n✓ Sample cleaned review:")
            logger.info(f"  Original review ID: {sample_cleaned.review_id}")
            logger.info(f"  Language: {sample_cleaned.language}")
            logger.info(f"  Sentiment: {sample_cleaned.sentiment}")
            logger.info(f"  Word count: {sample_cleaned.word_count}")
            logger.info(f"  Has duplicate: {sample_cleaned.has_duplicate}")
            logger.info(f"  Cleaned content: {sample_cleaned.cleaned_content[:100]}...")
        
    except Exception as e:
        logger.error(f"Error cleaning reviews: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        app_id = test_real_app_store_collection()
        test_real_app_store_cleaning(app_id)
        
        logger.info("\n" + "=" * 60)
        logger.info("All real App Store tests completed! ✓")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise