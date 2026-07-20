import logging
import uuid
from typing import List, Dict, Any, Optional
import numpy as np
from ..utils.vector_store import vector_store
from ..utils.graph_store import graph_store
from ..utils.llm_client import llm_client
from ..utils.embedding_client import embedding_client
from ..database import SessionLocal
from ..models.review import Review, CleanedReview

logger = logging.getLogger(__name__)

class EvidenceService:
    """
    NOTE: This service must NOT hold a long-lived SQLAlchemy session.
    MySQL's wait_timeout is 120s on this machine, so any session held
    idle across LLM/HTTP calls will have its connection closed by the
    server and the next DB operation will raise
    `mysql.connector.errors.OperationalError: MySQL Connection not available`.
    Each method below opens a short session via `with SessionLocal() as db:`,
    extracts plain dicts (so ORM instances don't leak out of the session),
    then closes the session before doing any long-running work.
    """

    def __init__(self):
        pass

    def build_vector_index(self, app_id: str = None):
        # Step 1: short DB session — extract plain dicts, then close.
        documents = []
        metadatas = []
        ids = []
        try:
            with SessionLocal() as db:
                query = db.query(CleanedReview)
                if app_id:
                    query = query.join(Review, CleanedReview.review_id == Review.id).filter(Review.app_id == app_id)

                for cr in query.all():
                    review = cr.review
                    documents.append(cr.cleaned_content)
                    metadatas.append({
                        'review_id': str(review.id),
                        'app_id': review.app_id,
                        'app_name': review.app_name,
                        'rating': review.rating,
                        'version': review.app_version or '',
                        'sentiment': float(cr.sentiment) if cr.sentiment is not None else 0.0,
                        'language': cr.language or 'unknown'
                    })
                    ids.append(str(cr.id))
            # session is now closed; ORM instances are not accessed below.

            # Step 2: long-running vector store work (no DB held).
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
            # Step 1: vector search (no DB needed).
            results = vector_store.search(query, top_k, filters)

            # Step 2: collect the review_ids we need to enrich.
            review_ids = []
            for result in results:
                rid = result['metadata'].get('review_id')
                if rid:
                    try:
                        review_ids.append(int(rid))
                    except (TypeError, ValueError):
                        continue

            # Step 3: short DB session — fetch all needed reviews in one query.
            reviews_by_id: Dict[int, Dict[str, Any]] = {}
            if review_ids:
                with SessionLocal() as db:
                    for review in db.query(Review).filter(Review.id.in_(review_ids)).all():
                        reviews_by_id[review.id] = {
                            'id': review.id,
                            'author': review.author,
                            'rating': review.rating,
                            'title': review.title,
                            'version': review.app_version,
                            'date': review.review_date.strftime('%Y-%m-%d') if review.review_date else None,
                            'content': review.content,
                        }
                # session closed; we only use the dicts below.

            # Step 4: attach the enriched review dicts to each result.
            for result in results:
                rid_str = result['metadata'].get('review_id')
                if not rid_str:
                    continue
                try:
                    rid = int(rid_str)
                except (TypeError, ValueError):
                    continue
                if rid in reviews_by_id:
                    result['review'] = reviews_by_id[rid]

            return results
        except Exception as e:
            logger.error(f"Evidence search failed: {str(e)}")
            raise

    def _calculate_relevance(self, query: str, document: str) -> float:
        """Use embedding cosine similarity instead of word overlap."""
        try:
            query_embedding = embedding_client.create_embedding(query)
            doc_embedding = embedding_client.create_embedding(document)

            if not query_embedding or not doc_embedding:
                return self._fallback_word_overlap(query, document)

            q = np.array(query_embedding)
            d = np.array(doc_embedding)

            norm_q = np.linalg.norm(q)
            norm_d = np.linalg.norm(d)

            if norm_q == 0 or norm_d == 0:
                return 0.0

            cosine = float(np.dot(q, d) / (norm_q * norm_d))
            return max(0.0, min(1.0, (cosine + 1) / 2))
        except Exception as e:
            logger.warning(f"Embedding similarity failed, falling back to word overlap: {str(e)}")
            return self._fallback_word_overlap(query, document)

    def _fallback_word_overlap(self, query: str, document: str) -> float:
        query_words = set(query.lower().split())
        doc_words = set(document.lower().split())
        if not query_words:
            return 0.0
        intersection = query_words & doc_words
        return len(intersection) / len(query_words)

    def _classify_evidence(self, finding_text: str, content: str, rating: int, sentiment: float) -> str:
        """
        Classify a review as supporting / conflicting / neutral based on:
        - Semantic relevance to the finding
        - Rating (low rating = pain point)
        - Sentiment score (float, -1..1)
        - Whether the review mentions the finding topic
        """
        relevance = self._calculate_relevance(finding_text, content)
        if relevance < 0.5:
            return "neutral"

        # Negative sentiment OR low rating with high relevance => supporting evidence for a problem
        # Positive sentiment AND high rating => conflicting evidence (contradicts a problem finding)
        is_negative = sentiment < -0.1 or rating <= 2
        is_positive = sentiment > 0.1 or rating >= 4

        if is_negative:
            return "supporting"
        if is_positive:
            return "conflicting"
        return "neutral"

    def validate_finding_with_evidence(self, finding_text: str, topic: str = "") -> Dict[str, Any]:
        try:
            search_results = self.search_evidence(finding_text, top_k=10)

            supporting_evidence = []
            conflicting_evidence = []

            for result in search_results:
                content = result['document']
                rating = int(result['metadata'].get('rating', 0))
                sentiment = float(result['metadata'].get('sentiment', 0.0))

                classification = self._classify_evidence(finding_text, content, rating, sentiment)

                if classification == "supporting":
                    relevance = self._calculate_relevance(finding_text, content)
                    supporting_evidence.append({
                        'review_id': result['metadata'].get('review_id'),
                        'content': content,
                        'rating': rating,
                        'sentiment': sentiment,
                        'relevance': round(relevance, 2)
                    })
                elif classification == "conflicting":
                    relevance = self._calculate_relevance(finding_text, content)
                    conflicting_evidence.append({
                        'review_id': result['metadata'].get('review_id'),
                        'content': content,
                        'rating': rating,
                        'sentiment': sentiment,
                        'relevance': round(relevance, 2)
                    })

            finding_id = str(uuid.uuid4())

            support_count = len(supporting_evidence)
            conflict_count = len(conflicting_evidence)
            total = support_count + conflict_count

            # Confidence: ratio of supporting to total evidence, with conflict penalty
            if total == 0:
                confidence = 0.0
                is_assumption = True
                validation_status = "unverified"
            else:
                confidence = support_count / total
                # Mark as assumption if support is weak
                if support_count < 2 or confidence < 0.4:
                    is_assumption = True
                    validation_status = "assumption"
                else:
                    is_assumption = False
                    validation_status = "validated"

            has_conflict = conflict_count > 0

            if graph_store.is_available():
                graph_store.create_finding_node(finding_id, finding_text, confidence)
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
                'support_count': support_count,
                'conflict_count': conflict_count,
                'confidence': round(confidence, 3),
                'has_conflict': has_conflict,
                'is_assumption': is_assumption,
                'validation_status': validation_status
            }
        except Exception as e:
            logger.error(f"Evidence validation failed: {str(e)}")
            raise

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
                'confidence': validation_result['confidence'],
                'has_conflict': validation_result['has_conflict'],
                'is_assumption': validation_result['is_assumption'],
                'validation_status': validation_result['validation_status'],
                'supporting_examples': evidence_summary
            }

            return trace_info
        except Exception as e:
            logger.error(f"Traceable finding generation failed: {str(e)}")
            raise

evidence_service = EvidenceService()
