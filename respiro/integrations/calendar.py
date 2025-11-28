"""
Google Calendar Integration for Respiro

OAuth2 authentication, event management, and rescheduling logic.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential

from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarClient:
    """Client for Google Calendar API."""
    
    def __init__(self):
        settings = get_settings()
        self.client_id = settings.google_calendar.client_id
        self.client_secret = settings.google_calendar.client_secret
        self.refresh_token = settings.google_calendar.refresh_token
        self.redirect_uri = settings.google_calendar.redirect_uri
        self.credentials = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API."""
        try:
            creds = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            self.credentials = creds
            self.service = build('calendar', 'v3', credentials=creds)
            
        except Exception as e:
            logger.error(f"Google Calendar authentication failed: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def list_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """List calendar events."""
        if not self.service:
            return []
        
        try:
            time_min = time_min or datetime.utcnow()
            time_max = time_max or time_min + timedelta(days=7)
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return [self._format_event(e) for e in events]
            
        except HttpError as e:
            logger.error(f"Failed to list calendar events: {e}")
            return []
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def reschedule_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: Optional[datetime] = None
    ) -> bool:
        """Reschedule a calendar event."""
        if not self.service:
            return False
        
        try:
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            
            event['start'] = {'dateTime': new_start.isoformat(), 'timeZone': 'UTC'}
            if new_end:
                event['end'] = {'dateTime': new_end.isoformat(), 'timeZone': 'UTC'}
            
            self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
            logger.info(f"Rescheduled event {event_id} to {new_start}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to reschedule event: {e}")
            return False
    
    def find_events_to_reschedule(
        self,
        aqi_forecast: Dict[str, Any],
        hours_ahead: int = 24
    ) -> List[Dict[str, Any]]:
        """Find outdoor events that should be rescheduled due to poor air quality."""
        events = self.list_events(
            time_min=datetime.utcnow(),
            time_max=datetime.utcnow() + timedelta(hours=hours_ahead)
        )
        
        # Filter events that are outdoor activities
        outdoor_keywords = ['outdoor', 'park', 'run', 'walk', 'exercise', 'sport']
        high_aqi_periods = [
            period for period in aqi_forecast.get('forecast', [])
            if period.get('aqi', 0) > 200
        ]
        
        events_to_reschedule = []
        for event in events:
            summary = event.get('summary', '').lower()
            if any(keyword in summary for keyword in outdoor_keywords):
                event_start = datetime.fromisoformat(event.get('start', {}).get('dateTime', '').replace('Z', '+00:00'))
                # Check if event overlaps with high AQI period
                for period in high_aqi_periods:
                    period_start = datetime.fromisoformat(period.get('start', '').replace('Z', '+00:00'))
                    if abs((event_start - period_start).total_seconds()) < 3600:  # Within 1 hour
                        events_to_reschedule.append(event)
                        break
        
        return events_to_reschedule
    
    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format Google Calendar event."""
        return {
            'id': event.get('id'),
            'summary': event.get('summary'),
            'start': event.get('start', {}),
            'end': event.get('end', {}),
            'location': event.get('location'),
            'description': event.get('description')
        }
