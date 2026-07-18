import re
import time
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import requests
from sqlalchemy.orm import Session
from app.models import Review
from app.config import settings

logger = logging.getLogger(__name__)

def extract_app_id_from_url(url: str) -> Optional[str]:
    match = re.search(r'id(\d+)', url)
    if match:
        return match.group(1)
    return None

def extract_app_name_from_url(url: str) -> Optional[str]:
    match = re.search(r'/app/([^/]+)/id', url)
    if match:
        return match.group(1).replace('-', ' ')
    return None

def parse_datetime(date_str: str) -> datetime:
    try:
        match = re.match(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})', date_str)
        if match:
            return datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
                int(match.group(5)),
                int(match.group(6))
            )
    except:
        pass
    
    return datetime.now()

def collect_reviews_via_rss(app_id: str, app_name: str, country: str = "us", max_reviews: int = 200) -> List[Dict]:
    logger.info(f"Starting to collect reviews via RSS for app: {app_name} (id: {app_id})")
    
    reviews = []
    page = 1
    
    while len(reviews) < max_reviews:
        try:
            rss_url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/page={page}/sortBy=mostRecent/json"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(rss_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'feed' not in data or 'entry' not in data['feed']:
                break
            
            entries = data['feed']['entry']
            
            for entry in entries:
                if len(reviews) >= max_reviews:
                    break
                
                review = {
                    'app_id': app_id,
                    'app_name': app_name,
                    'author': entry.get('author', {}).get('name', {}).get('label', ''),
                    'rating': int(entry.get('im:rating', {}).get('label', '0')),
                    'title': entry.get('title', {}).get('label', ''),
                    'content': entry.get('content', {}).get('label', ''),
                    'review_date': parse_datetime(entry.get('updated', {}).get('label', '')),
                    'app_version': entry.get('im:version', {}).get('label', ''),
                    'is_edited': False,
                    'vote_count': 0,
                    'vote_sum': 0,
                    'source_url': f"https://apps.apple.com/{country}/app/id{app_id}",
                    'raw_data': entry,
                }
                
                reviews.append(review)
            
            if len(entries) == 0:
                break
            
            page += 1
            time.sleep(settings.REQUEST_DELAY)
            
        except Exception as e:
            logger.warning(f"Error fetching page {page}: {str(e)}")
            break
    
    logger.info(f"Successfully collected {len(reviews)} reviews via RSS")
    return reviews

def collect_reviews(app_id: str, app_name: str, country: str = "us", max_reviews: int = 200) -> List[Dict]:
    try:
        return collect_reviews_via_rss(app_id, app_name, country, max_reviews)
    except Exception as e:
        logger.error(f"RSS collection failed: {str(e)}")
        raise

def save_reviews(db: Session, reviews: List[Dict]) -> int:
    saved_count = 0
    for review_data in reviews:
        existing_review = db.query(Review).filter(
            Review.app_id == review_data['app_id'],
            Review.author == review_data['author'],
            Review.review_date == review_data['review_date']
        ).first()
        
        if not existing_review:
            review = Review(**review_data)
            db.add(review)
            saved_count += 1
    
    db.commit()
    logger.info(f"Saved {saved_count} new reviews to database")
    return saved_count

def collect_and_save_reviews(
    db: Session,
    app_url: str,
    country: str = None,
    max_reviews: int = None
) -> Tuple[int, str, str]:
    country = country or settings.APP_STORE_COUNTRY
    max_reviews = max_reviews or settings.MAX_REVIEWS_PER_FETCH
    
    app_id = extract_app_id_from_url(app_url)
    app_name = extract_app_name_from_url(app_url) or "Unknown App"
    
    if not app_id:
        raise ValueError(f"Could not extract app ID from URL: {app_url}")
    
    reviews = collect_reviews(app_id, app_name, country, max_reviews)
    saved_count = save_reviews(db, reviews)
    
    return saved_count, app_id, app_name