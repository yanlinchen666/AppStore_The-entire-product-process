import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

from app.database import SessionLocal, engine, Base
from app.models import Review, CleanedReview
from app.services.cleaner import clean_reviews, clean_text, detect_language, calculate_sentiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_clean_text():
    logger.info("Testing text cleaning...")
    
    test_cases = [
        ("  Hello   World!  ", "Hello World!"),
        ("This has\nnewlines\nand tabs\t", "This has newlines and tabs"),
        ("Special!@#$%^&*()chars", "Special!chars"),
        ("", ""),
        ("   ", ""),
        ("Normal text with, punctuation!", "Normal text with, punctuation!"),
    ]
    
    for input_text, expected in test_cases:
        result = clean_text(input_text)
        assert result == expected, f"Failed for '{input_text}': expected '{expected}', got '{result}'"
        logger.info(f"✓ '{input_text}' -> '{result}'")
    
    logger.info("✓ Text cleaning tests passed!")

def test_detect_language():
    logger.info("Testing language detection...")
    
    test_cases = [
        ("Hello, this is an English sentence.", "en"),
        ("Bonjour, ceci est une phrase française.", "fr"),
        ("Hola, esta es una oración en español.", "es"),
        ("こんにちは、これは日本語の文です。", "ja"),
        ("你好，这是中文句子。", "zh-cn"),
    ]
    
    for text, expected in test_cases:
        result = detect_language(text)
        assert result == expected, f"Failed for '{text}': expected '{expected}', got '{result}'"
        logger.info(f"✓ Detected '{result}' for text")
    
    logger.info("✓ Language detection tests passed!")

def test_calculate_sentiment():
    logger.info("Testing sentiment calculation...")
    
    test_cases = [
        ("This app is amazing! I love it so much!", 1.0),
        ("Terrible app, hate it!", -1.0),
        ("This is a neutral statement with no emotion.", 0.0),
        ("Great app but has some issues", 0.0),
        ("Love love love this great excellent app!", 1.0),
    ]
    
    for text, expected in test_cases:
        result = calculate_sentiment(text)
        assert result == expected, f"Failed for '{text}': expected {expected}, got {result}"
        logger.info(f"✓ '{text}' -> sentiment: {result}")
    
    logger.info("✓ Sentiment calculation tests passed!")

def test_clean_reviews():
    logger.info("Testing review cleaning workflow...")
    
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    app_id = "839285684"
    
    total_reviews = db.query(Review).filter(Review.app_id == app_id).count()
    logger.info(f"✓ Total raw reviews: {total_reviews}")
    
    assert total_reviews > 0, "No reviews found in database. Run test_data_collection.py first!"
    
    cleaned_count = clean_reviews(db, app_id)
    logger.info(f"✓ Cleaned {cleaned_count} reviews")
    
    total_cleaned = db.query(CleanedReview).filter(CleanedReview.app_id == app_id).count()
    logger.info(f"✓ Total cleaned reviews in database: {total_cleaned}")
    
    assert cleaned_count == total_cleaned, "Cleaned count mismatch"
    
    cleaned_review = db.query(CleanedReview).filter(CleanedReview.app_id == app_id).first()
    assert cleaned_review is not None
    assert cleaned_review.cleaned_content is not None
    assert len(cleaned_review.cleaned_content) > 0
    assert cleaned_review.language is not None
    assert cleaned_review.sentiment is not None
    assert cleaned_review.word_count is not None
    
    logger.info(f"✓ Sample cleaned review:")
    logger.info(f"  - Language: {cleaned_review.language}")
    logger.info(f"  - Sentiment: {cleaned_review.sentiment}")
    logger.info(f"  - Word count: {cleaned_review.word_count}")
    logger.info(f"  - Has duplicate: {cleaned_review.has_duplicate}")
    
    db.close()
    logger.info("✓ Review cleaning tests passed!")

def test_duplicate_identification():
    logger.info("Testing duplicate identification...")
    
    db = SessionLocal()
    
    app_id = "839285684"
    
    duplicates = db.query(CleanedReview).filter(
        CleanedReview.app_id == app_id,
        CleanedReview.has_duplicate == True
    ).count()
    
    logger.info(f"✓ Found {duplicates} duplicate reviews")
    
    if duplicates > 0:
        duplicate = db.query(CleanedReview).filter(
            CleanedReview.app_id == app_id,
            CleanedReview.has_duplicate == True
        ).first()
        logger.info(f"✓ Sample duplicate - duplicate_of: {duplicate.duplicate_of}")
    
    db.close()
    logger.info("✓ Duplicate identification test passed!")

def test_language_distribution():
    logger.info("Testing language distribution...")
    
    db = SessionLocal()
    
    app_id = "839285684"
    
    from sqlalchemy import func
    
    language_counts = db.query(
        CleanedReview.language,
        func.count(CleanedReview.id)
    ).filter(CleanedReview.app_id == app_id).group_by(CleanedReview.language).all()
    
    logger.info("✓ Language distribution:")
    for lang, count in language_counts:
        logger.info(f"  - {lang}: {count} reviews")
    
    db.close()
    logger.info("✓ Language distribution test passed!")

def test_sentiment_distribution():
    logger.info("Testing sentiment distribution...")
    
    db = SessionLocal()
    
    app_id = "839285684"
    
    from sqlalchemy import func
    
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
    
    logger.info("✓ Sentiment distribution:")
    logger.info(f"  - Average sentiment: {avg_sentiment:.2f}")
    logger.info(f"  - Positive: {positive_count}")
    logger.info(f"  - Negative: {negative_count}")
    logger.info(f"  - Neutral: {neutral_count}")
    
    db.close()
    logger.info("✓ Sentiment distribution test passed!")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Running Data Cleaning Tests")
    logger.info("=" * 60)
    
    try:
        test_clean_text()
        test_detect_language()
        test_calculate_sentiment()
        test_clean_reviews()
        test_duplicate_identification()
        test_language_distribution()
        test_sentiment_distribution()
        
        logger.info("=" * 60)
        logger.info("All tests passed! ✓")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise