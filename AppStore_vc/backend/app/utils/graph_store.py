import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from app.config import settings

logger = logging.getLogger(__name__)

class GraphStore:
    def __init__(self):
        self.driver = None
        self._connect()
    
    def _connect(self):
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Connected to Neo4j successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Neo4j: {str(e)}. Graph features will be disabled.")
            self.driver = None
    
    def is_available(self) -> bool:
        return self.driver is not None
    
    def create_review_node(self, review_id: str, content: str, rating: int, author: str, app_id: str):
        if not self.driver:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    CREATE (r:Review {id: $review_id, content: $content, rating: $rating, author: $author})
                    WITH r
                    MERGE (a:App {id: $app_id})
                    CREATE (r)-[:BELONGS_TO]->(a)
                """, review_id=review_id, content=content, rating=rating, author=author, app_id=app_id)
        except Exception as e:
            logger.error(f"Failed to create review node: {str(e)}")
    
    def create_topic_node(self, topic_name: str, description: str):
        if not self.driver:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (t:Topic {name: $topic_name})
                    SET t.description = $description
                """, topic_name=topic_name, description=description)
        except Exception as e:
            logger.error(f"Failed to create topic node: {str(e)}")
    
    def create_finding_node(self, finding_id: str, finding_text: str, confidence: float):
        if not self.driver:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    CREATE (f:Finding {id: $finding_id, text: $finding_text, confidence: $confidence})
                """, finding_id=finding_id, finding_text=finding_text, confidence=confidence)
        except Exception as e:
            logger.error(f"Failed to create finding node: {str(e)}")
    
    def create_requirement_node(self, req_id: str, req_text: str, priority: str):
        if not self.driver:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    CREATE (req:Requirement {id: $req_id, text: $req_text, priority: $priority})
                """, req_id=req_id, req_text=req_text, priority=priority)
        except Exception as e:
            logger.error(f"Failed to create requirement node: {str(e)}")
    
    def create_testcase_node(self, tc_id: str, tc_title: str):
        if not self.driver:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    CREATE (tc:TestCase {id: $tc_id, title: $tc_title})
                """, tc_id=tc_id, tc_title=tc_title)
        except Exception as e:
            logger.error(f"Failed to create testcase node: {str(e)}")
    
    def create_evidence_link(self, review_id: str, finding_id: str):
        if not self.driver:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (r:Review {id: $review_id})
                    MATCH (f:Finding {id: $finding_id})
                    CREATE (r)-[:SUPPORTS]->(f)
                """, review_id=review_id, finding_id=finding_id)
        except Exception as e:
            logger.error(f"Failed to create evidence link: {str(e)}")
    
    def create_trace_link(self, from_id: str, from_label: str, to_id: str, to_label: str):
        if not self.driver:
            return
        
        try:
            with self.driver.session() as session:
                session.run(f"""
                    MATCH (a:{from_label} {{id: $from_id}})
                    MATCH (b:{to_label} {{id: $to_id}})
                    CREATE (a)-[:TRACES_TO]->(b)
                """, from_id=from_id, to_id=to_id)
        except Exception as e:
            logger.error(f"Failed to create trace link: {str(e)}")
    
    def query_evidence_for_finding(self, finding_id: str) -> List[Dict]:
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (r:Review)-[:SUPPORTS]->(f:Finding {id: $finding_id})
                    RETURN r.id AS review_id, r.content AS content, r.rating AS rating, r.author AS author
                """, finding_id=finding_id)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Failed to query evidence: {str(e)}")
            return []
    
    def query_trace_chain(self, review_id: str) -> List[Dict]:
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH path = (r:Review {id: $review_id})-[:SUPPORTS|TRACES_TO*]->()
                    RETURN nodes(path) AS nodes
                """, review_id=review_id)
                chains = []
                for record in result:
                    chain = []
                    for node in record['nodes']:
                        labels = list(node.labels)
                        chain.append({
                            'labels': labels,
                            'properties': dict(node)
                        })
                    chains.append(chain)
                return chains
        except Exception as e:
            logger.error(f"Failed to query trace chain: {str(e)}")
            return []
    
    def close(self):
        if self.driver:
            self.driver.close()

graph_store = GraphStore()
