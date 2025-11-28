"""Vector memory system using ChromaDB."""
from typing import List, Dict, Any, Optional
import chromadb
from pathlib import Path
from respiro.config.settings import get_settings
from respiro.memory.embeddings import EmbeddingService
from respiro.storage.s3_client import get_s3_client
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

class VectorStore:
    def __init__(self):
        settings = get_settings()
        self.db_path = Path(settings.vector_db.db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.embedding_service = EmbeddingService()
        self.s3_client = get_s3_client()
    
    def store_memory(self, patient_id: str, text: str, metadata: Dict[str, Any]) -> bool:
        """Store a memory for a patient."""
        try:
            collection = self.client.get_or_create_collection(f"patient_{patient_id}")
            embedding = self.embedding_service.embed_text(text)
            collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata],
                ids=[f"{patient_id}_{len(collection.get()['ids'])}"]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False
    
    def retrieve_memories(self, patient_id: str, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories."""
        try:
            collection = self.client.get_or_create_collection(f"patient_{patient_id}")
            query_embedding = self.embedding_service.embed_text(query)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            return [
                {"text": doc, "metadata": meta}
                for doc, meta in zip(results["documents"][0], results["metadatas"][0])
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []
    
    def backup_to_s3(self, patient_id: str) -> bool:
        """Backup vector store to S3."""
        try:
            collection = self.client.get_or_create_collection(f"patient_{patient_id}")
            data = collection.get()
            backup_data = {
                "documents": data["documents"],
                "metadatas": data["metadatas"],
                "ids": data["ids"]
            }
            self.s3_client.save_memory_backup(patient_id, backup_data)
            return True
        except Exception as e:
            logger.error(f"Failed to backup to S3: {e}")
            return False
