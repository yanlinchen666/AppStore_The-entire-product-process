import logging
import uuid
from typing import List, Dict, Any, Optional
from ..utils.vector_store import vector_store
from ..utils.graph_store import graph_store
from ..utils.llm_client import llm_client
from ..database import SessionLocal
from ..models.review import Review, CleanedReview

logger = logging.getLogger(__name__)

class EvidenceService:
    def __init__(self):
        self.db = SessionLocal()
    
    def build_vector_index(self, app_id: str = None):
        try:
            query = self.db.query(CleanedReview)
            if app_id:
                query = query.join(Review, CleanedReview.review_id == Review.id).filter(Review.app_id == app_id)
            
            cleaned_reviews = query.all()
            documents = []
            metadatas = []
            ids = []
            
            for cr in cleaned_reviews:
                review = cr.review
                documents.append(cr.cleaned_content)
                metadatas.append({
                    'review_id': str(review.id),
                    'app_id': review.app_id,
                    'app_name': review.app_name,
                    'rating': review.rating,
                    'version': review.app_version,
                    'sentiment': cr.sentiment,
                    'language': cr.language
                })
                ids.append(str(cr.id))
            
            if documents:
                count = vector_store.add_documents(documents, metadatas, ids)
                logger.info(f"Indexed {count} reviews into vector store")
                return count
            return 0
        except Exception as e:
            logger.error(f"Failed to build vector index: {str(e)}")
            raise
    
    def search_evidence(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        try:
            results = vector_store.search(query, top_k, filters)
            
            enriched_results = []
            for result in results:
                review_id = result['metadata'].get('review_id')
                if review_id:
                    review = self.db.query(Review).filter(Review.id == int(review_id)).first()
                    if review:
                        result['review'] = {
                            'id': review.id,
                            'author': review.author,
                            'rating': review.rating,
                            'title': review.title,
                            'version': review.version,
                            'date': review.date.strftime('%Y-%m-%d') if review.date else None
                        }
                enriched_results.append(result)
            
            return enriched_results
        except Exception as e:
            logger.error(f"Evidence search failed: {str(e)}")
            raise
    
    def validate_finding_with_evidence(self, finding_text: str, topic: str = "") -> Dict[str, Any]:
        try:
            search_results = self.search_evidence(finding_text, top_k=10)
            
            supporting_evidence = []
            conflicting_evidence = []
            
            for result in search_results:
                content = result['document']
                rating = result['metadata'].get('rating', 0)
                sentiment = result['metadata'].get('sentiment', 'neutral')
                
                relevance = self._calculate_relevance(finding_text, content)
                
                if relevance > 0.7:
                    if sentiment == 'positive' or rating >= 4:
                        supporting_evidence.append({
                            'review_id': result['metadata'].get('review_id'),
                            'content': content,
                            'rating': rating,
                            'sentiment': sentiment,
                            'relevance': round(relevance, 2)
                        })
                    elif sentiment == 'negative' or rating <= 2:
                        conflicting_evidence.append({
                            'review_id': result['metadata'].get('review_id'),
                            'content': content,
                            'rating': rating,
                            'sentiment': sentiment,
                            'relevance': round(relevance, 2)
                        })
            
            finding_id = str(uuid.uuid4())
            
            if graph_store.is_available():
                graph_store.create_finding_node(finding_id, finding_text, min(len(supporting_evidence) / 5, 1.0))
                graph_store.create_topic_node(topic, f"Topic: {topic}")
                
                for evidence in supporting_evidence:
                    graph_store.create_review_node(
                        evidence['review_id'],
                        evidence['content'],
                        evidence['rating'],
                        "Unknown",
                        "Unknown"
                    )
                    graph_store.create_evidence_link(evidence['review_id'], finding_id)
            
            return {
                'finding_id': finding_id,
                'finding_text': finding_text,
                'topic': topic,
                'supporting_evidence': supporting_evidence[:5],
                'conflicting_evidence': conflicting_evidence[:5],
                'support_count': len(supporting_evidence),
                'conflict_count': len(conflicting_evidence),
                'confidence': min(len(supporting_evidence) / max(len(supporting_evidence) + len(conflicting_evidence), 1), 1.0),
                'has_conflict': len(conflicting_evidence) > 0
            }
        except Exception as e:
            logger.error(f"Evidence validation failed: {str(e)}")
            raise
    
    def _calculate_relevance(self, query: str, document: str) -> float:
        query_lower = query.lower()
        doc_lower = document.lower()
        
        query_words = set(query_lower.split())
        doc_words = set(doc_lower.split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words & doc_words
        return len(intersection) / len(query_words)
    
    def generate_traceable_finding(self, finding_text: str, topic: str = "") -> Dict[str, Any]:
        try:
            validation_result = self.validate_finding_with_evidence(finding_text, topic)
            
            evidence_summary = []
            for evidence in validation_result['supporting_evidence'][:3]:
                evidence_summary.append(f"- Rating {evidence['rating']}/5: {evidence['content'][:50]}...")
            
            trace_info = {
                'finding': finding_text,
                'topic': topic,
                'evidence_count': validation_result['support_count'],
                'evidence_ids': [e['review_id'] for e in validation_result['supporting_evidence']],
                'confidence': round(validation_result['confidence'], 2),
                'has_conflict': validation_result['has_conflict'],
                'supporting_examples': evidence_summary
            }
            
            return trace_info
        except Exception as e:
            logger.error(f"Traceable finding generation failed: {str(e)}")
            raise

evidence_service = EvidenceService()
