"""
Notification Service Interface

Provides notification capabilities (email, SMS, push) with mock implementations.
Real implementations can be swapped in when actual services are configured.
"""

import json
import os
from datetime import datetime
from typing import Any
from pathlib import Path


class NotificationService:
    """Notification service with mock implementations."""
    
    def __init__(self):
        """Initialize notification service."""
        self.notification_history: list[dict[str, Any]] = []
        self.history_file = Path(__file__).parent.parent / "notification_history.json"
        self._load_history()
    
    def _load_history(self) -> None:
        """Load notification history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.notification_history = json.load(f)
            except Exception:
                self.notification_history = []
    
    def _save_history(self) -> None:
        """Save notification history to file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.notification_history, f, indent=2, default=str)
        except Exception:
            pass  # Silently fail if can't save
    
    def _add_to_history(
        self,
        notification_type: str,
        recipient: str,
        subject: str | None,
        message: str,
        status: str = "sent"
    ) -> None:
        """Add notification to history."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": notification_type,
            "recipient": recipient,
            "subject": subject,
            "message": message,
            "status": status
        }
        self.notification_history.append(entry)
        # Keep only last 1000 entries
        if len(self.notification_history) > 1000:
            self.notification_history = self.notification_history[-1000:]
        self._save_history()
    
    def send_email(
        self,
        subject: str,
        body: str,
        recipients: list[str],
        from_email: str | None = None
    ) -> dict[str, Any]:
        """
        Send email notification (mock implementation).
        
        Args:
            subject: Email subject
            body: Email body
            recipients: List of recipient email addresses
            from_email: Sender email (optional)
            
        Returns:
            Dict with status and details
        """
        from_email = from_email or os.getenv("NOTIFICATION_FROM_EMAIL", "carbonflow@delhi.gov.in")
        
        # Mock implementation - just log
        print(f"[NotificationService] EMAIL: To {', '.join(recipients)}")
        print(f"[NotificationService] Subject: {subject}")
        print(f"[NotificationService] Body: {body[:100]}...")
        
        for recipient in recipients:
            self._add_to_history("email", recipient, subject, body, "sent")
        
        return {
            "status": "success",
            "type": "email",
            "recipients": recipients,
            "subject": subject,
            "mode": "mock",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def send_sms(
        self,
        message: str,
        phone_numbers: list[str]
    ) -> dict[str, Any]:
        """
        Send SMS notification (mock implementation).
        
        Args:
            message: SMS message text
            phone_numbers: List of phone numbers
            
        Returns:
            Dict with status and details
        """
        # Mock implementation - just log
        print(f"[NotificationService] SMS: To {', '.join(phone_numbers)}")
        print(f"[NotificationService] Message: {message[:100]}...")
        
        for phone in phone_numbers:
            self._add_to_history("sms", phone, None, message, "sent")
        
        return {
            "status": "success",
            "type": "sms",
            "recipients": phone_numbers,
            "message": message,
            "mode": "mock",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def send_push_notification(
        self,
        title: str,
        message: str,
        users: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Send push notification (mock implementation).
        
        Args:
            title: Notification title
            message: Notification message
            users: List of user IDs (optional, None means all users)
            
        Returns:
            Dict with status and details
        """
        users = users or ["all_users"]
        
        # Mock implementation - just log
        print(f"[NotificationService] PUSH: To {', '.join(users)}")
        print(f"[NotificationService] Title: {title}")
        print(f"[NotificationService] Message: {message[:100]}...")
        
        for user in users:
            self._add_to_history("push", user, title, message, "sent")
        
        return {
            "status": "success",
            "type": "push",
            "recipients": users,
            "title": title,
            "message": message,
            "mode": "mock",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_history(
        self,
        limit: int = 50,
        notification_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get notification history.
        
        Args:
            limit: Maximum number of entries to return
            notification_type: Filter by type (email, sms, push) or None for all
            
        Returns:
            List of notification entries
        """
        history = self.notification_history.copy()
        
        if notification_type:
            history = [h for h in history if h.get("type") == notification_type]
        
        # Return most recent first
        return list(reversed(history[-limit:]))
    
    def clear_history(self) -> None:
        """Clear notification history."""
        self.notification_history = []
        self._save_history()


# Global notification service instance
_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Get global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service

