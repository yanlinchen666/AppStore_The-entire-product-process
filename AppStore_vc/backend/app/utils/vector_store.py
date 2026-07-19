import logging
import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from app.config import settings
from app.utils.embedding_client import embedding_client

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=os.path.join(os.getcwd(), settings.CHROMADB_PATH),
            settings=Settings(allow_reset=True)
        )
        self.collection_name = "appstore_reviews"
        self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        try:
            self.collection = self.client.get_collection(self.collection_name)
        except Exception:
            self.collection = self.client.create_collection(self.collection_name)
            logger.info(f"Created collection: {self.collection_name}")
    
    def add_documents(self, documents: List[str], metadatas: Optional[List[Dict]] = None, ids: Optional[List[str]] = None):
        try:
            embeddings = embedding_client.create_embeddings(documents)
            valid_indices = [i for i, emb in enumerate(embeddings) if len(emb) > 0]
            
            valid_docs = [documents[i] for i in valid_indices]
            valid_metadatas = [metadatas[i] for i in valid_indices] if metadatas else None
            valid_ids = [ids[i] for i in valid_indices] if ids else None
            valid_embeddings = [embeddings[i] for i in valid_indices]
            
            self.collection.add(
                documents=valid_docs,
                metadatas=valid_metadatas,
                ids=valid_ids,
                embeddings=valid_embeddings
            )
            logger.info(f"Added {len(valid_docs)} documents to vector store")
            return len(valid_docs)
        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            raise
    
    def search(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        try:
            query_embedding = embedding_client.create_embedding(query)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters
            )
            
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        try:
            count = self.collection.count()
            return {'count': count}
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {'count': 0}
    
    def clear_collection(self):
        try:
            self.client.delete_collection(self.collection_name)
            self._get_or_create_collection()
            logger.info("Cleared collection")
        except Exception as e:
            logger.error(f"Failed to clear collection: {str(e)}")
            raise

vector_store = VectorStore()
