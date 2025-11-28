"""Approval workflow for human-in-the-loop."""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

class ApprovalWorkflow:
    def __init__(self):
        self.settings = get_settings()
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
    
    def request_approval(self, request_id: str, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request human approval.
        
        Args:
            request_id: Unique request identifier
            action: Action requiring approval
            context: Context about the action
            
        Returns:
            Approval request dictionary
        """
        approval_request = {
            "request_id": request_id,
            "action": action,
            "context": context,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "timeout_at": (datetime.utcnow() + timedelta(seconds=self.settings.app.human_approval_timeout_seconds)).isoformat()
        }
        self.pending_approvals[request_id] = approval_request
        logger.info(f"Created approval request {request_id} for action {action}")
        return approval_request
    
    def check_approval(self, request_id: str, state: Optional[Dict[str, Any]] = None) -> Optional[bool]:
        """
        Check if approval has been received.
        
        Args:
            request_id: Request identifier
            state: Optional orchestrator state to check for approval responses
            
        Returns:
            True if approved, False if rejected, None if pending
        """
        # First check state for approval responses
        if state:
            approval_responses = state.get("approval_responses", {})
            if request_id in approval_responses:
                response = approval_responses[request_id]
                approved = response.get("approved", False)
                logger.info(f"Approval request {request_id} {'approved' if approved else 'rejected'} from state")
                return approved
        
        # Fallback to in-memory pending approvals
        request = self.pending_approvals.get(request_id)
        if not request:
            return None
        
        if request["status"] == "approved":
            return True
        elif request["status"] == "rejected":
            return False
        
        # Check timeout
        timeout_at = datetime.fromisoformat(request["timeout_at"])
        if datetime.utcnow() > timeout_at:
            logger.warning(f"Approval request {request_id} timed out")
            request["status"] = "timeout"
            return False  # Default to rejection on timeout
        
        return None  # Still pending
    
    def submit_approval(self, request_id: str, approved: bool, reason: Optional[str] = None) -> bool:
        """
        Submit approval response.
        
        Args:
            request_id: Request identifier
            approved: True if approved, False if rejected
            reason: Optional reason for decision
            
        Returns:
            True if successful
        """
        if request_id not in self.pending_approvals:
            logger.warning(f"Approval request {request_id} not found")
            return False
        
        self.pending_approvals[request_id]["status"] = "approved" if approved else "rejected"
        self.pending_approvals[request_id]["responded_at"] = datetime.utcnow().isoformat()
        if reason:
            self.pending_approvals[request_id]["reason"] = reason
        
        logger.info(f"Approval request {request_id} {'approved' if approved else 'rejected'}")
        return True
    
    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests."""
        return [
            req for req in self.pending_approvals.values()
            if req.get("status") == "pending"
        ]
