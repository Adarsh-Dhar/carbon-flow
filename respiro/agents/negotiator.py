"""
Negotiator Agent - Empathetic Communication

Uses Amazon Bedrock for natural language communication and manages lifestyle logistics.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime, timedelta

from respiro.orchestrator.state import RespiroState
from respiro.integrations.bedrock import BedrockClient
from respiro.integrations.calendar import GoogleCalendarClient
from respiro.tools.route_tools import RouteOptimizer
from respiro.tools.memory_tools import MemoryTools
from respiro.storage.s3_client import get_s3_client
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class NegotiatorAgent:
    """Negotiator agent for empathetic communication and lifestyle management."""
    
    def __init__(self):
        self.bedrock = BedrockClient()
        self.calendar = GoogleCalendarClient()
        self.route_optimizer = RouteOptimizer()
        self.memory_tools = MemoryTools()
        self.s3_client = get_s3_client()
    
    def execute(self, state: RespiroState) -> Dict[str, Any]:
        """
        Execute Negotiator agent for communication and logistics.
        
        Args:
            state: Current orchestrator state
            
        Returns:
            Negotiator agent output
        """
        patient_id = state.get("patient_id")
        logger.info(f"Executing Negotiator agent for patient {patient_id}")
        
        try:
            # Get context from previous agents
            sentry_output = state.get("sentry_output", {})
            clinical_output = state.get("clinical_output", {})
            
            # Retrieve user preferences from memory for personalization
            user_preferences = []
            try:
                preferences = self.memory_tools.retrieve_preferences(patient_id, category="communication")
                user_preferences = [pref.get("text", "") for pref in preferences[:5]]  # Top 5 preferences
                logger.info(f"Retrieved {len(preferences)} user preferences for patient {patient_id}")
            except Exception as e:
                logger.warning(f"Failed to retrieve user preferences: {e}")
            
            # Generate empathetic response with personalized context
            context = {
                "risk_level": str(sentry_output.get("risk_level", "")),
                "risk_factors": sentry_output.get("risk_factors", []),
                "user_preferences": user_preferences
            }
            recommendations = clinical_output.get("recommendations", {})
            
            response = self.bedrock.generate_empathetic_response(context, recommendations)
            
            # Store interaction in memory for future personalization
            try:
                interaction_text = f"Patient interaction: Risk level {context['risk_level']}, Response provided: {response[:100]}..."
                self.memory_tools.vector_store.store_memory(
                    patient_id,
                    interaction_text,
                    {"type": "interaction", "timestamp": datetime.utcnow().isoformat()}
                )
            except Exception as e:
                logger.warning(f"Failed to store interaction in memory: {e}")
            
            # Handle calendar rescheduling if needed
            calendar_actions = []
            route_recommendations = []
            risk_level_str = str(sentry_output.get("risk_level", ""))
            if risk_level_str in ["high", "severe"]:
                aqi_forecast = sentry_output.get("sensor_data", {}).get("air_quality", {})
                events_to_reschedule = self.calendar.find_events_to_reschedule(aqi_forecast)
                
                for event in events_to_reschedule:
                    # Reschedule to avoid high AQI period
                    new_start = datetime.utcnow() + timedelta(hours=2)  # Simplified
                    if self.calendar.reschedule_event(event["id"], new_start):
                        calendar_actions.append({
                            "action": "rescheduled",
                            "event_id": event["id"],
                            "new_time": new_start.isoformat()
                        })
                
                # Route optimization for commute events
                try:
                    context = state.get("context", {})
                    location = context.get("location", {})
                    if location.get("latitude") and location.get("longitude"):
                        # Check for commute events
                        commute_events = [e for e in events_to_reschedule if any(keyword in e.get("summary", "").lower() 
                                                                                for keyword in ["commute", "work", "office", "travel"])]
                        for event in commute_events:
                            # Get route with AQI optimization
                            origin = (location.get("latitude"), location.get("longitude"))
                            # Use event location if available, otherwise use default destination
                            event_location = event.get("location", {})
                            if event_location:
                                dest_lat = event_location.get("latitude", location.get("latitude"))
                                dest_lon = event_location.get("longitude", location.get("longitude"))
                            else:
                                # Default destination (e.g., city center)
                                dest_lat = location.get("latitude", 28.6139)
                                dest_lon = location.get("longitude", 77.2090)
                            destination = (dest_lat, dest_lon)
                            
                            route_result = self.route_optimizer.get_route_with_aqi(origin, destination, aqi_forecast)
                            if route_result.get("best_route"):
                                route_recommendations.append({
                                    "event_id": event.get("id"),
                                    "event_summary": event.get("summary"),
                                    "route": route_result.get("best_route"),
                                    "aqi_score": route_result.get("best_route", {}).get("aqi_score", 0)
                                })
                                logger.info(f"Generated route recommendation for event {event.get('id')}")
                except Exception as e:
                    logger.warning(f"Failed to generate route recommendations: {e}")
            
            # Build output
            output = {
                "response": response,
                "calendar_actions": calendar_actions,
                "route_recommendations": route_recommendations,
                "user_preferences_used": len(user_preferences),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Persist to S3
            try:
                self.s3_client.upload_json(
                    f"patients/{patient_id}/negotiator_output/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                    output
                )
            except Exception as e:
                logger.warning(f"Failed to persist negotiator output to S3: {e}")
            
            logger.info("Negotiator agent completed")
            return output
            
        except Exception as e:
            logger.error(f"Negotiator agent execution failed: {e}", exc_info=True)
            # Return safe defaults with error information
            error_output = {
                "response": "I'm here to help you manage your asthma. Please follow your action plan.",
                "calendar_actions": [],
                "route_recommendations": [],
                "user_preferences_used": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "error_type": type(e).__name__
            }
            # Add error to state for tracking
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append({
                "type": "negotiator_execution_error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            return error_output