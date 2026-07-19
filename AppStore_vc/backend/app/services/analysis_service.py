import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import AnalysisRun, AnalysisTopic, AnalysisFinding, CleanedReview, Review
from app.utils.llm_client import llm_client
from app.services.evidence_service import evidence_service

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self):
        pass

    def start_analysis(self, db: Session, app_id: str, app_name: str, analysis_goal: str = "") -> AnalysisRun:
        run = AnalysisRun(
            app_id=app_id,
            app_name=app_name,
            analysis_goal=analysis_goal,
            status="running"
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
        logger.info(f"Started analysis run {run.id} for app {app_name}")
        return run

    def get_cleaned_reviews(self, db: Session, app_id: str) -> List[Dict]:
        cleaned_reviews = db.query(CleanedReview).join(Review).filter(
            Review.app_id == app_id,
            CleanedReview.is_valid == True
        ).all()
        
        results = []
        for cr in cleaned_reviews:
            review = cr.review
            results.append({
                'id': cr.id,
                'review_id': review.id,
                'content': cr.cleaned_content,
                'rating': review.rating,
                'version': review.app_version,
                'date': review.review_date.strftime('%Y-%m-%d') if review.review_date else None,
                'sentiment': cr.sentiment,
                'language': cr.language
            })
        
        return results

    def extract_topics(self, reviews: List[Dict], analysis_goal: str = "") -> List[Dict]:
        if len(reviews) == 0:
            return []
        
        sample_reviews = reviews[:50]
        reviews_text = "\n".join([
            f"Review {i+1} (Rating: {r['rating']}/5, Version: {r.get('version', 'N/A')}): {r['content']}"
            for i, r in enumerate(sample_reviews)
        ])

        prompt = f"""
You are an expert product analyst. Analyze the following App Store reviews and identify the main topics/issues users are reporting.

Analysis Goal: {analysis_goal or "General analysis"}

Reviews (Total: {len(reviews)}, Sample: {len(sample_reviews)}):
{reviews_text}

Please provide a JSON array of topics with the following structure:
[
    {{
        "name": "Topic Name",
        "description": "Brief description of what this topic is about",
        "keywords": ["keyword1", "keyword2", ...],
        "severity": "high" | "medium" | "low",
        "confidence": 0.0-1.0
    }}
]

Requirements:
1. Identify 5-10 main topics
2. Focus on user-reported problems and feature requests
3. Include both negative issues and positive feedback
4. Use clear, concise topic names
5. Provide reasonable confidence scores based on how many reviews mention this topic
"""

        try:
            response = llm_client.chat_completion([{"role": "user", "content": prompt}])
            return self._parse_topics_response(response)
        except Exception as e:
            logger.error(f"Topic extraction failed: {str(e)}")
            return self._fallback_topic_extraction(reviews)

    def _parse_topics_response(self, response: str) -> List[Dict]:
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        return []

    def _fallback_topic_extraction(self, reviews: List[Dict]) -> List[Dict]:
        common_topics = {
            "billing": ["subscription", "payment", "charge", "pay", "billing", "money", "refund"],
            "login": ["login", "sign in", "account", "password", "authentication"],
            "performance": ["slow", "crash", "freeze", "lag", "bug", "error", "glitch"],
            "ui": ["interface", "design", "layout", "navigation", "screen", "button"],
            "feature": ["feature", "function", "add", "need", "want", "request"],
            "subscription": ["subscribe", "subscription", "trial", "renew", "cancel"],
            "workout": ["workout", "exercise", "training", "routine", "fitness"],
            "general": ["good", "great", "love", "hate", "bad", "terrible"]
        }

        topics = []
        for topic_name, keywords in common_topics.items():
            count = 0
            for review in reviews:
                content = review['content'].lower()
                if any(k in content for k in keywords):
                    count += 1
            
            if count > 0:
                topics.append({
                    "name": topic_name.replace("_", " ").title(),
                    "description": f"Reviews related to {topic_name}",
                    "keywords": keywords,
                    "severity": "high" if count > len(reviews) * 0.1 else "medium",
                    "confidence": min(count / len(reviews), 1.0)
                })
        
        return topics

    def generate_findings(self, db: Session, run_id: int, topics: List[Dict], reviews: List[Dict]) -> List[Dict]:
        all_findings = []
        
        for topic in topics:
            topic_reviews = []
            for review in reviews:
                content = review['content'].lower()
                if any(k.lower() in content for k in topic.get('keywords', [])):
                    topic_reviews.append(review)
            
            if len(topic_reviews) == 0:
                continue

            review_samples = "\n".join([
                f"Rating {r['rating']}/5: {r['content'][:100]}..."
                for r in topic_reviews[:10]
            ])

            prompt = f"""
You are an expert product analyst. Based on the following reviews about "{topic['name']}", generate specific, actionable findings.

Topic: {topic['name']}
Topic Description: {topic['description']}

Sample Reviews ({len(topic_reviews)} total):
{review_samples}

Please provide a JSON array of findings with the following structure:
[
    {{
        "finding": "Specific finding/observation",
        "evidence_count": estimated_number_of_reviews_supporting_this,
        "confidence": 0.0-1.0,
        "has_conflict": false,
        "impact": "high" | "medium" | "low",
        "type": "problem" | "feature_request" | "positive_feedback" | "question"
    }}
]

Requirements:
1. Generate 2-5 findings per topic
2. Each finding must be grounded in the review evidence
3. Distinguish between problems, feature requests, and positive feedback
4. Include confidence based on evidence strength
5. Mention if there's conflicting feedback
"""

            try:
                response = llm_client.chat_completion([{"role": "user", "content": prompt}])
                findings = self._parse_findings_response(response)
                
                for finding in findings:
                    finding['topic_name'] = topic['name']
                    finding['topic_id'] = None
                    all_findings.append(finding)
            except Exception as e:
                logger.error(f"Finding generation failed for topic {topic['name']}: {str(e)}")
                all_findings.append({
                    "finding": f"Users reported issues with {topic['name']}",
                    "evidence_count": len(topic_reviews),
                    "confidence": 0.7,
                    "has_conflict": False,
                    "impact": topic.get('severity', 'medium'),
                    "type": "problem",
                    "topic_name": topic['name'],
                    "topic_id": None
                })

        return all_findings

    def _parse_findings_response(self, response: str) -> List[Dict]:
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        return []

    def validate_findings(self, db: Session, findings: List[Dict]) -> List[Dict]:
        validated_findings = []
        
        for finding in findings:
            finding_text = finding['finding']
            topic_name = finding.get('topic_name', '')
            
            validation = evidence_service.validate_finding_with_evidence(finding_text, topic_name)
            
            validated_findings.append({
                **finding,
                'supporting_evidence': validation['supporting_evidence'],
                'conflicting_evidence': validation['conflicting_evidence'],
                'support_count': validation['support_count'],
                'conflict_count': validation['conflict_count'],
                'final_confidence': validation['confidence'],
                'has_conflict': validation['has_conflict'],
                'finding_id': validation['finding_id']
            })
        
        return validated_findings

    def save_topics_and_findings(self, db: Session, run_id: int, topics: List[Dict], findings: List[Dict]) -> None:
        topic_map = {}
        
        for topic_data in topics:
            topic = AnalysisTopic(
                run_id=run_id,
                name=topic_data['name'],
                description=topic_data['description'],
                confidence=topic_data.get('confidence', 0.0),
                sample_count=0,
                is_model_generated=True
            )
            db.add(topic)
            db.flush()
            topic_map[topic_data['name']] = topic.id
        
        for finding_data in findings:
            finding = AnalysisFinding(
                run_id=run_id,
                topic_id=topic_map.get(finding_data.get('topic_name')),
                finding_text=finding_data['finding'],
                evidence_review_ids=[e['review_id'] for e in finding_data.get('supporting_evidence', [])],
                sample_count=finding_data.get('support_count', 0),
                confidence=finding_data.get('final_confidence', finding_data.get('confidence', 0.0)),
                has_conflict=finding_data.get('has_conflict', False),
                conflicting_review_ids=[e['review_id'] for e in finding_data.get('conflicting_evidence', [])],
                is_model_generated=True
            )
            db.add(finding)
        
        db.commit()
        logger.info(f"Saved {len(topics)} topics and {len(findings)} findings for run {run_id}")

    def complete_analysis(self, db: Session, run_id: int, total_reviews: int, cleaned_reviews: int) -> None:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run:
            run.status = "completed"
            run.total_reviews = total_reviews
            run.cleaned_reviews = cleaned_reviews
            run.completed_at = datetime.now()
            db.commit()
            logger.info(f"Analysis run {run_id} completed")

    def analyze(self, db: Session, app_id: str, app_name: str, analysis_goal: str = "") -> Dict[str, Any]:
        run = self.start_analysis(db, app_id, app_name, analysis_goal)
        
        try:
            reviews = self.get_cleaned_reviews(db, app_id)
            logger.info(f"Found {len(reviews)} cleaned reviews")
            
            if len(reviews) == 0:
                run.status = "failed"
                run.error_message = "No cleaned reviews available"
                db.commit()
                return {"run_id": run.id, "status": "failed", "error": "No cleaned reviews available"}
            
            topics = self.extract_topics(reviews, analysis_goal)
            logger.info(f"Extracted {len(topics)} topics")
            
            findings = self.generate_findings(db, run.id, topics, reviews)
            logger.info(f"Generated {len(findings)} findings")
            
            validated_findings = self.validate_findings(db, findings)
            logger.info(f"Validated {len(validated_findings)} findings")
            
            self.save_topics_and_findings(db, run.id, topics, validated_findings)
            self.complete_analysis(db, run.id, len(reviews), len(reviews))
            
            return {
                "run_id": run.id,
                "status": "completed",
                "topics_count": len(topics),
                "findings_count": len(validated_findings),
                "reviews_count": len(reviews)
            }
            
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            db.commit()
            logger.error(f"Analysis failed: {str(e)}")
            return {"run_id": run.id, "status": "failed", "error": str(e)}

analysis_service = AnalysisService()