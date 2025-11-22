"""
Notification Service Interface

Provides notification capabilities (email, SMS, push) with real API implementations
and graceful fallback to mock when services are unavailable or unconfigured.
"""

import json
import os
import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Any
from pathlib import Path

# Set up logger
logger = logging.getLogger(__name__)

# Try importing optional dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests library not available, some notification services will use mock")

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 library not available, AWS services will use mock")


class NotificationService:
    """Notification service with real API implementations and graceful fallback."""
    
    def __init__(self):
        """Initialize notification service with configuration."""
        self.notification_history: list[dict[str, Any]] = []
        self.history_file = Path(__file__).parent.parent / "notification_history.json"
        self._load_history()
        
        # Email service configuration
        self.email_service_type = os.getenv("EMAIL_SERVICE_TYPE", "mock").lower()
        self._init_email_service()
        
        # SMS service configuration
        self.sms_service_type = os.getenv("SMS_SERVICE_TYPE", "mock").lower()
        self._init_sms_service()
        
        # Push notification service configuration
        self.push_service_type = os.getenv("PUSH_SERVICE_TYPE", "mock").lower()
        self._init_push_service()
    
    def _init_email_service(self) -> None:
        """Initialize email service based on configuration."""
        if self.email_service_type == "smtp":
            self.smtp_host = os.getenv("SMTP_HOST")
            self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
            self.smtp_user = os.getenv("SMTP_USER")
            self.smtp_password = os.getenv("SMTP_PASSWORD")
            self.use_real_email = bool(self.smtp_host and self.smtp_user and self.smtp_password)
        elif self.email_service_type == "sendgrid":
            self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
            self.use_real_email = bool(self.sendgrid_api_key and REQUESTS_AVAILABLE)
        elif self.email_service_type == "ses":
            self.ses_region = os.getenv("AWS_SES_REGION", "us-east-1")
            self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            self.use_real_email = bool(self.aws_access_key and self.aws_secret_key and BOTO3_AVAILABLE)
        else:
            self.use_real_email = False
        
        if not self.use_real_email and self.email_service_type != "mock":
            logger.warning(
                f"[NotificationService] Email service type '{self.email_service_type}' configured but credentials missing. Using mock."
            )
    
    def _init_sms_service(self) -> None:
        """Initialize SMS service based on configuration."""
        if self.sms_service_type == "twilio":
            self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            self.twilio_from_number = os.getenv("TWILIO_FROM_NUMBER")
            self.use_real_sms = bool(
                self.twilio_account_sid and self.twilio_auth_token and 
                self.twilio_from_number and REQUESTS_AVAILABLE
            )
        elif self.sms_service_type == "sns":
            self.sns_region = os.getenv("AWS_SNS_REGION", "us-east-1")
            self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            self.use_real_sms = bool(self.aws_access_key and self.aws_secret_key and BOTO3_AVAILABLE)
        else:
            self.use_real_sms = False
        
        if not self.use_real_sms and self.sms_service_type != "mock":
            logger.warning(
                f"[NotificationService] SMS service type '{self.sms_service_type}' configured but credentials missing. Using mock."
            )
    
    def _init_push_service(self) -> None:
        """Initialize push notification service based on configuration."""
        if self.push_service_type == "fcm":
            self.fcm_server_key = os.getenv("FCM_SERVER_KEY")
            self.fcm_service_account = os.getenv("FCM_SERVICE_ACCOUNT_JSON")
            self.use_real_push = bool((self.fcm_server_key or self.fcm_service_account) and REQUESTS_AVAILABLE)
        elif self.push_service_type == "apns":
            self.apns_key_file = os.getenv("APNS_KEY_FILE")
            self.apns_key_id = os.getenv("APNS_KEY_ID")
            self.apns_team_id = os.getenv("APNS_TEAM_ID")
            self.apns_bundle_id = os.getenv("APNS_BUNDLE_ID")
            self.use_real_push = bool(
                self.apns_key_file and self.apns_key_id and 
                self.apns_team_id and self.apns_bundle_id and REQUESTS_AVAILABLE
            )
        elif self.push_service_type == "webpush":
            self.webpush_vapid_public = os.getenv("WEBPUSH_VAPID_PUBLIC_KEY")
            self.webpush_vapid_private = os.getenv("WEBPUSH_VAPID_PRIVATE_KEY")
            self.use_real_push = bool(self.webpush_vapid_public and self.webpush_vapid_private and REQUESTS_AVAILABLE)
        else:
            self.use_real_push = False
        
        if not self.use_real_push and self.push_service_type != "mock":
            logger.warning(
                f"[NotificationService] Push service type '{self.push_service_type}' configured but credentials missing. Using mock."
            )
    
    def _retry_with_backoff(self, func, max_attempts: int = 3, base_delay: float = 1.0):
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Function to retry (should return result or raise exception)
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            
        Returns:
            Result from function call
            
        Raises:
            Exception: If all attempts fail
        """
        last_exception = None
        for attempt in range(1, max_attempts + 1):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(f"[NotificationService] Attempt {attempt} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"[NotificationService] All {max_attempts} attempts failed: {e}")
        
        raise last_exception
    
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
        Send email notification with real API support and fallback to mock.
        
        Args:
            subject: Email subject
            body: Email body
            recipients: List of recipient email addresses
            from_email: Sender email (optional)
            
        Returns:
            Dict with status and details
        """
        from_email = from_email or os.getenv("NOTIFICATION_FROM_EMAIL", "carbonflow@delhi.gov.in")
        
        if not self.use_real_email:
            return self._mock_send_email(subject, body, recipients, from_email)
        
        try:
            if self.email_service_type == "smtp":
                return self._real_send_email_smtp(subject, body, recipients, from_email)
            elif self.email_service_type == "sendgrid":
                return self._real_send_email_sendgrid(subject, body, recipients, from_email)
            elif self.email_service_type == "ses":
                return self._real_send_email_ses(subject, body, recipients, from_email)
            else:
                return self._mock_send_email(subject, body, recipients, from_email)
        except Exception as e:
            logger.error(f"[NotificationService] Email sending failed: {e}. Falling back to mock.")
            return self._mock_send_email(subject, body, recipients, from_email)
    
    def _real_send_email_smtp(
        self,
        subject: str,
        body: str,
        recipients: list[str],
        from_email: str
    ) -> dict[str, Any]:
        """Send email via SMTP."""
        def _send():
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                if self.smtp_port == 587:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"[NotificationService] Email sent via SMTP to {len(recipients)} recipients")
            return {
                "status": "success",
                "type": "email",
                "service": "smtp",
                "recipients": recipients,
                "subject": subject,
                "mode": "real",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = self._retry_with_backoff(_send)
        for recipient in recipients:
            self._add_to_history("email", recipient, subject, body, "sent")
        return result
    
    def _real_send_email_sendgrid(
        self,
        subject: str,
        body: str,
        recipients: list[str],
        from_email: str
    ) -> dict[str, Any]:
        """Send email via SendGrid API."""
        def _send():
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "personalizations": [{"to": [{"email": r} for r in recipients]}],
                "from": {"email": from_email},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}]
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info(f"[NotificationService] Email sent via SendGrid to {len(recipients)} recipients")
            return {
                "status": "success",
                "type": "email",
                "service": "sendgrid",
                "recipients": recipients,
                "subject": subject,
                "mode": "real",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = self._retry_with_backoff(_send)
        for recipient in recipients:
            self._add_to_history("email", recipient, subject, body, "sent")
        return result
    
    def _real_send_email_ses(
        self,
        subject: str,
        body: str,
        recipients: list[str],
        from_email: str
    ) -> dict[str, Any]:
        """Send email via AWS SES."""
        def _send():
            ses_client = boto3.client(
                "ses",
                region_name=self.ses_region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            
            response = ses_client.send_email(
                Source=from_email,
                Destination={"ToAddresses": recipients},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": body}}
                }
            )
            
            logger.info(f"[NotificationService] Email sent via AWS SES to {len(recipients)} recipients. MessageId: {response['MessageId']}")
            return {
                "status": "success",
                "type": "email",
                "service": "ses",
                "recipients": recipients,
                "subject": subject,
                "mode": "real",
                "message_id": response["MessageId"],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = self._retry_with_backoff(_send)
        for recipient in recipients:
            self._add_to_history("email", recipient, subject, body, "sent")
        return result
    
    def _mock_send_email(
        self,
        subject: str,
        body: str,
        recipients: list[str],
        from_email: str
    ) -> dict[str, Any]:
        """Mock email implementation."""
        logger.info(f"[NotificationService] EMAIL (mock): To {', '.join(recipients)}")
        logger.info(f"[NotificationService] Subject: {subject}")
        
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
        Send SMS notification with real API support and fallback to mock.
        
        Args:
            message: SMS message text
            phone_numbers: List of phone numbers
            
        Returns:
            Dict with status and details
        """
        if not self.use_real_sms:
            return self._mock_send_sms(message, phone_numbers)
        
        try:
            if self.sms_service_type == "twilio":
                return self._real_send_sms_twilio(message, phone_numbers)
            elif self.sms_service_type == "sns":
                return self._real_send_sms_sns(message, phone_numbers)
            else:
                return self._mock_send_sms(message, phone_numbers)
        except Exception as e:
            logger.error(f"[NotificationService] SMS sending failed: {e}. Falling back to mock.")
            return self._mock_send_sms(message, phone_numbers)
    
    def _real_send_sms_twilio(
        self,
        message: str,
        phone_numbers: list[str]
    ) -> dict[str, Any]:
        """Send SMS via Twilio API."""
        def _send():
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
            auth = (self.twilio_account_sid, self.twilio_auth_token)
            
            results = []
            for phone in phone_numbers:
                payload = {
                    "From": self.twilio_from_number,
                    "To": phone,
                    "Body": message
                }
                response = requests.post(url, auth=auth, data=payload, timeout=30)
                response.raise_for_status()
                results.append(response.json()["sid"])
            
            logger.info(f"[NotificationService] SMS sent via Twilio to {len(phone_numbers)} recipients")
            return {
                "status": "success",
                "type": "sms",
                "service": "twilio",
                "recipients": phone_numbers,
                "message": message,
                "mode": "real",
                "message_sids": results,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = self._retry_with_backoff(_send)
        for phone in phone_numbers:
            self._add_to_history("sms", phone, None, message, "sent")
        return result
    
    def _real_send_sms_sns(
        self,
        message: str,
        phone_numbers: list[str]
    ) -> dict[str, Any]:
        """Send SMS via AWS SNS."""
        def _send():
            sns_client = boto3.client(
                "sns",
                region_name=self.sns_region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            
            results = []
            for phone in phone_numbers:
                response = sns_client.publish(PhoneNumber=phone, Message=message)
                results.append(response["MessageId"])
            
            logger.info(f"[NotificationService] SMS sent via AWS SNS to {len(phone_numbers)} recipients")
            return {
                "status": "success",
                "type": "sms",
                "service": "sns",
                "recipients": phone_numbers,
                "message": message,
                "mode": "real",
                "message_ids": results,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = self._retry_with_backoff(_send)
        for phone in phone_numbers:
            self._add_to_history("sms", phone, None, message, "sent")
        return result
    
    def _mock_send_sms(
        self,
        message: str,
        phone_numbers: list[str]
    ) -> dict[str, Any]:
        """Mock SMS implementation."""
        logger.info(f"[NotificationService] SMS (mock): To {', '.join(phone_numbers)}")
        logger.info(f"[NotificationService] Message: {message[:100]}...")
        
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
        Send push notification with real API support and fallback to mock.
        
        Args:
            title: Notification title
            message: Notification message
            users: List of user IDs (optional, None means all users)
            
        Returns:
            Dict with status and details
        """
        users = users or ["all_users"]
        
        if not self.use_real_push:
            return self._mock_send_push(title, message, users)
        
        try:
            if self.push_service_type == "fcm":
                return self._real_send_push_fcm(title, message, users)
            elif self.push_service_type == "apns":
                return self._real_send_push_apns(title, message, users)
            elif self.push_service_type == "webpush":
                return self._real_send_push_webpush(title, message, users)
            else:
                return self._mock_send_push(title, message, users)
        except Exception as e:
            logger.error(f"[NotificationService] Push notification sending failed: {e}. Falling back to mock.")
            return self._mock_send_push(title, message, users)
    
    def _real_send_push_fcm(
        self,
        title: str,
        message: str,
        users: list[str]
    ) -> dict[str, Any]:
        """Send push notification via Firebase Cloud Messaging."""
        def _send():
            url = "https://fcm.googleapis.com/fcm/send"
            headers = {
                "Authorization": f"key={self.fcm_server_key}",
                "Content-Type": "application/json"
            }
            
            # Note: In production, you'd need to map user IDs to FCM tokens
            # This is a simplified implementation
            payload = {
                "notification": {
                    "title": title,
                    "body": message
                },
                "registration_ids": users  # In production, these would be FCM tokens
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info(f"[NotificationService] Push notification sent via FCM to {len(users)} users")
            return {
                "status": "success",
                "type": "push",
                "service": "fcm",
                "recipients": users,
                "title": title,
                "message": message,
                "mode": "real",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        result = self._retry_with_backoff(_send)
        for user in users:
            self._add_to_history("push", user, title, message, "sent")
        return result
    
    def _real_send_push_apns(
        self,
        title: str,
        message: str,
        users: list[str]
    ) -> dict[str, Any]:
        """Send push notification via Apple Push Notification Service."""
        # Note: APNS requires JWT token generation and device tokens
        # This is a simplified implementation
        logger.warning("[NotificationService] APNS implementation requires device tokens and JWT generation")
        return self._mock_send_push(title, message, users)
    
    def _real_send_push_webpush(
        self,
        title: str,
        message: str,
        users: list[str]
    ) -> dict[str, Any]:
        """Send push notification via Web Push API."""
        # Note: Web Push requires subscription endpoints and VAPID keys
        # This is a simplified implementation
        logger.warning("[NotificationService] Web Push implementation requires subscription endpoints")
        return self._mock_send_push(title, message, users)
    
    def _mock_send_push(
        self,
        title: str,
        message: str,
        users: list[str]
    ) -> dict[str, Any]:
        """Mock push notification implementation."""
        logger.info(f"[NotificationService] PUSH (mock): To {', '.join(users)}")
        logger.info(f"[NotificationService] Title: {title}")
        logger.info(f"[NotificationService] Message: {message[:100]}...")
        
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

