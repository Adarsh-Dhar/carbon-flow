"""Memory tools for agents."""
from typing import Dict, Any, List, Optional
from respiro.memory.vector_store import VectorStore
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

class MemoryTools:
    def __init__(self):
        self.vector_store = VectorStore()
    
    def store_preference(self, patient_id: str, preference: str, category: str = "general") -> bool:
        """Store user preference."""
        return self.vector_store.store_memory(
            patient_id,
            preference,
            {"type": "preference", "category": category}
        )
    
    def retrieve_preferences(self, patient_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve user preferences."""
        query = f"user preferences {category}" if category else "user preferences"
        return self.vector_store.retrieve_memories(patient_id, query)
