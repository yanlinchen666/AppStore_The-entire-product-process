import re
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from langdetect import detect, LangDetectException
from sqlalchemy.orm import Session
from app.models import Review, CleanedReview

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    if not text:
        return ""
    
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s.,!?]', '', text)
    
    return text

def detect_language(text: str) -> str:
    try:
        if len(text) < 10:
            return "unknown"
        return detect(text)
    except LangDetectException:
        return "unknown"

def calculate_sentiment(text: str) -> float:
    positive_words = ["love", "great", "excellent", "amazing", "best", "good", "perfect", "awesome", "wonderful", "fantastic"]
    negative_words = ["hate", "bad", "terrible", "awful", "worst", "broken", "bug", "crash", "problem", "issue"]
    
    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    total = positive_count + negative_count
    if total == 0:
        return 0.0
    
    return (positive_count - negative_count) / total

def find_duplicates(reviews: List[Dict]) -> Dict[int, int]:
    duplicates = {}
    content_hash = {}
    
    for i, review in enumerate(reviews):
        cleaned = review.get('cleaned_content', review.get('content', '')).lower()
        if len(cleaned) < 10:
            continue
        
        hash_key = hash(cleaned)
        if hash_key in content_hash:
            duplicates[i] = content_hash[hash_key]
        else:
            content_hash[hash_key] = i
    
    return duplicates

def clean_reviews(db: Session, app_id: str) -> int:
    logger.info(f"Starting to clean reviews for app: {app_id}")
    
    reviews = db.query(Review).filter(Review.app_id == app_id).all()
    
    cleaned_count = 0
    review_data_list = []
    
    for review in reviews:
        cleaned_content = clean_text(review.content)
        
        if not cleaned_content or len(cleaned_content) < 5:
            continue
        
        language = detect_language(cleaned_content)
        sentiment = calculate_sentiment(cleaned_content)
        word_count = len(cleaned_content.split())
        
        review_data_list.append({
            'index': cleaned_count,
            'review_id': review.id,
            'app_id': app_id,
            'cleaned_content': cleaned_content,
            'language': language,
            'sentiment': sentiment,
            'word_count': word_count,
        })
        cleaned_count += 1
    
    duplicates = find_duplicates(review_data_list)
    
    for data in review_data_list:
        idx = data['index']
        has_duplicate = idx in duplicates
        duplicate_of = duplicates.get(idx)
        
        existing_cleaned = db.query(CleanedReview).filter(
            CleanedReview.review_id == data['review_id']
        ).first()
        
        if not existing_cleaned:
            cleaned_review = CleanedReview(
                review_id=data['review_id'],
                app_id=data['app_id'],
                cleaned_content=data['cleaned_content'],
                language=data['language'],
                sentiment=data['sentiment'],
                word_count=data['word_count'],
                has_duplicate=has_duplicate,
                duplicate_of=duplicate_of,
                is_valid=True,
            )
            db.add(cleaned_review)
    
    db.commit()
    logger.info(f"Successfully cleaned {cleaned_count} reviews, found {len(duplicates)} duplicates")
    
    return cleaned_count