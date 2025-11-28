"""
Main Respiro Orchestrator

Handles session management, context persistence, and error recovery.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from langgraph.checkpoint.base import BaseCheckpointSaver

from respiro.orchestrator.state import RespiroState, create_initial_state, update_state_timestamp
from respiro.orchestrator.graph import build_graph
from respiro.storage.s3_client import get_s3_client
from respiro.memory.vector_store import VectorStore
from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class RespiroOrchestrator:
    """Main orchestrator for Respiro agentic system."""
    
    def __init__(self):
        self.graph = build_graph()
        self.s3_client = get_s3_client()
        self.settings = get_settings()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(
        self,
        patient_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new session for a patient.
        
        Loads previous session context and memories for continuity.
        
        Args:
            patient_id: Patient identifier
            initial_context: Optional initial context
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        # Load previous session context if available
        previous_context = {}
        previous_sessions = []
        try:
            latest_session = self.s3_client.load_latest_session(patient_id)
            if latest_session:
                previous_state = latest_session.get("state", {})
                previous_sessions = [latest_session.get("session_id")]
                
                # Extract relevant context from previous session
                previous_context = {
                    "last_risk_level": previous_state.get("current_risk_level"),
                    "last_risk_score": previous_state.get("risk_score"),
                    "last_zone": previous_state.get("clinical_recommendations", {}).get("zone"),
                    "device_ids": previous_state.get("context", {}).get("device_ids", {})
                }
                
                # Merge device IDs into initial context
                if initial_context:
                    if "device_ids" not in initial_context:
                        initial_context["device_ids"] = previous_context.get("device_ids", {})
                else:
                    initial_context = {"device_ids": previous_context.get("device_ids", {})}
                
                logger.info(f"Loaded context from previous session for patient {patient_id}")
        except Exception as e:
            logger.warning(f"Failed to load previous session context: {e}")
        
        # Merge previous context with initial context
        if initial_context:
            initial_context.update(previous_context)
        else:
            initial_context = previous_context
        
        state = create_initial_state(patient_id, session_id, initial_context)
        
        # Load relevant memories from vector store
        try:
            vector_store = VectorStore()
            # Retrieve recent memories for context
            recent_memories = vector_store.retrieve_memories(
                patient_id,
                "recent interactions and preferences",
                n_results=10
            )
            if recent_memories:
                state["memory_retrieval"] = recent_memories
                state["user_preferences"] = {
                    "count": len(recent_memories),
                    "loaded_from_previous_sessions": True
                }
                logger.info(f"Loaded {len(recent_memories)} memories for patient {patient_id}")
        except Exception as e:
            logger.warning(f"Failed to load memories: {e}")
        
        # Track previous sessions
        if previous_sessions:
            state["previous_sessions"] = previous_sessions
        
        # Store session
        self.active_sessions[session_id] = {
            "patient_id": patient_id,
            "created_at": datetime.utcnow(),
            "state": state
        }
        
        logger.info(f"Created session {session_id} for patient {patient_id}")
        return session_id
    
    def execute(
        self,
        session_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> RespiroState:
        """
        Execute the orchestrator graph for a session.
        
        Args:
            session_id: Session identifier
            config: Optional LangGraph config
            
        Returns:
            Final state
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        initial_state = session["state"]
        
        logger.info(f"Executing orchestrator for session {session_id}")
        
        try:
            # Prepare config with thread_id for checkpointing
            graph_config = {
                "configurable": {
                    "thread_id": session_id
                }
            }
            if config:
                graph_config["configurable"].update(config.get("configurable", {}))
            
            # Execute graph
            final_state = None
            for state in self.graph.stream(initial_state, config=graph_config):
                final_state = state
                # Update session state
                if isinstance(state, dict) and len(state) == 1:
                    # State is wrapped in a dict with node name as key
                    for node_state in state.values():
                        session["state"] = node_state
                        break
                else:
                    session["state"] = state
            
            # Persist final state to S3
            if final_state:
                self._persist_state(session_id, final_state)
            
            logger.info(f"Orchestrator completed for session {session_id}")
            return session["state"]
            
        except Exception as e:
            logger.error(f"Orchestrator execution failed for session {session_id}: {e}", exc_info=True)
            # Update state with error
            session["state"] = update_state_timestamp(session["state"])
            session["state"]["errors"] = session["state"].get("errors", []) + [{
                "type": "orchestrator_error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
            raise
    
    def get_session_state(self, session_id: str) -> Optional[RespiroState]:
        """
        Get current state for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Current state or None if not found
        """
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]["state"]
        return None
    
    def load_session(self, session_id: str) -> bool:
        """
        Load a session from S3.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if loaded successfully
        """
        try:
            # Load from S3
            log_data = self.s3_client.download_json(f"sessions/{session_id}/log.json")
            if not log_data:
                return False
            
            state = log_data.get("state")
            if not state:
                return False
            
            # Restore session
            self.active_sessions[session_id] = {
                "patient_id": state.get("patient_id"),
                "created_at": datetime.fromisoformat(log_data.get("created_at", datetime.utcnow().isoformat())),
                "state": state
            }
            
            logger.info(f"Loaded session {session_id} from S3")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return False
    
    def _persist_state(self, session_id: str, state: RespiroState):
        """Persist state to S3."""
        try:
            log_data = {
                "session_id": session_id,
                "patient_id": state.get("patient_id"),
                "created_at": self.active_sessions[session_id]["created_at"].isoformat(),
                "state": state,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.s3_client.save_session_log(session_id, log_data)
            
        except Exception as e:
            logger.error(f"Failed to persist state for session {session_id}: {e}")
    
    def cleanup_old_sessions(self):
        """Clean up sessions older than timeout."""
        timeout = timedelta(seconds=self.settings.app.session_timeout_seconds)
        now = datetime.utcnow()
        
        sessions_to_remove = []
        for session_id, session in self.active_sessions.items():
            age = now - session["created_at"]
            if age > timeout:
                # Persist before removing
                self._persist_state(session_id, session["state"])
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
            logger.info(f"Cleaned up expired session {session_id}")


# Global orchestrator instance
_orchestrator: Optional[RespiroOrchestrator] = None


def get_orchestrator() -> RespiroOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RespiroOrchestrator()
    return _orchestrator
