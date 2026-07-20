"""
Review data import service.
Supports JSON and CSV formats per README requirement:
"The application must also support importing review data from a documented JSON or CSV format."

Expected JSON schema:
[
  {
    "app_id": "1234567890",
    "app_name": "App Name",
    "author": "User Name",
    "rating": 4,
    "title": "Review title",
    "content": "Review body text",
    "review_date": "2024-01-15T12:34:56",
    "app_version": "1.2.3"
  },
  ...
]

Expected CSV schema (column headers):
app_id,app_name,author,rating,title,content,review_date,app_version
"""
import csv
import io
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models import Review

logger = logging.getLogger(__name__)


class ImportService:
    def __init__(self):
        pass

    def parse_json(self, content: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                raise ValueError("JSON must be an array of review objects")
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")

    def parse_csv(self, content: str) -> List[Dict[str, Any]]:
        try:
            reader = csv.DictReader(io.StringIO(content))
            return list(reader)
        except Exception as e:
            raise ValueError(f"Invalid CSV: {str(e)}")

    def normalize_review(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize an imported review to the internal schema."""
        app_id = str(raw.get('app_id') or raw.get('appId') or '').strip()
        app_name = (raw.get('app_name') or raw.get('appName') or 'Imported App').strip()
        author = (raw.get('author') or raw.get('user') or raw.get('userName') or 'Anonymous').strip()
        rating_raw = raw.get('rating') or raw.get('score') or 0
        try:
            rating = int(float(rating_raw))
        except (TypeError, ValueError):
            rating = 0
        rating = max(0, min(5, rating))

        title = (raw.get('title') or raw.get('review_title') or '').strip()
        content_text = (raw.get('content') or raw.get('body') or raw.get('text') or raw.get('review') or '').strip()

        date_raw = raw.get('review_date') or raw.get('date') or raw.get('created_at') or ''
        review_date = self._parse_date(date_raw)

        app_version = (raw.get('app_version') or raw.get('version') or '').strip() or None

        if not app_id:
            raise ValueError("Missing required field: app_id")
        if not content_text:
            raise ValueError("Missing required field: content")

        return {
            'app_id': app_id,
            'app_name': app_name,
            'author': author,
            'rating': rating,
            'title': title,
            'content': content_text,
            'review_date': review_date,
            'app_version': app_version,
            'is_edited': False,
            'vote_count': 0,
            'vote_sum': 0,
            'source_url': 'imported',
            'raw_data': raw,
        }

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now()
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y'):
            try:
                return datetime.strptime(str(date_str).split('.')[0].split('+')[0].strip(), fmt)
            except ValueError:
                continue
        return datetime.now()

    def import_reviews(
        self,
        db: Session,
        content: str,
        format: str = "json",
        app_id_override: str = None,
    ) -> Tuple[int, str, str]:
        """Import reviews from JSON or CSV content. Returns (count, app_id, app_name)."""
        if format.lower() == "json":
            data = self.parse_json(content)
        elif format.lower() == "csv":
            data = self.parse_csv(content)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")

        if not data:
            raise ValueError("No reviews found in the imported file")

        saved_count = 0
        app_id_detected = None
        app_name_detected = None

        for raw in data:
            try:
                normalized = self.normalize_review(raw)
                if app_id_override:
                    normalized['app_id'] = app_id_override

                # Record app_id from the first valid review, even if it turns
                # out to be a duplicate. Otherwise, when ALL reviews are
                # duplicates (re-import), app_id_detected stays None and the
                # caller gets "unknown", which breaks the subsequent
                # /api/import/analyze call.
                if app_id_detected is None:
                    app_id_detected = normalized['app_id']
                    app_name_detected = normalized['app_name']

                # Dedup by (app_id, author, content) — if a review with the
                # same content already exists, skip insertion but still count
                # it as "already available" for the detected app_id.
                existing = db.query(Review).filter(
                    Review.app_id == normalized['app_id'],
                    Review.author == normalized['author'],
                    Review.content == normalized['content'],
                ).first()

                if existing:
                    continue

                review = Review(**normalized)
                db.add(review)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Skipping invalid review row: {str(e)}")
                continue

        db.commit()
        logger.info(f"Imported {saved_count} reviews (format={format})")
        return saved_count, app_id_detected or app_id_override or "unknown", app_name_detected or "Imported App"


import_service = ImportService()
