"""
Navigator Agent

Explains routing choices to users in clear, user-friendly language.
This is Agent 3 from the guide - the User Interface Agent.
"""

from __future__ import annotations

from typing import Any, Dict

from respiro.integrations.bedrock import BedrockClient
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


class NavigatorAgent:
    """
    Navigator agent that explains routing choices in user-friendly language.
    
    Takes Cartographer output and builds detailed explanations like:
    "I found a route that is 5 minutes longer but avoids heavy traffic on 
    19th Avenue (High NO2). It also skips the steep climb on Filbert St to 
    keep your breathing rate low."
    """
    
    def __init__(self) -> None:
        self.bedrock = BedrockClient()
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Navigator agent to explain routing choices.
        
        Args:
            state: Current orchestrator state with cartographer_output
            
        Returns:
            Navigator output with detailed explanation
        """
        cartographer_output = state.get("cartographer_output", {})
        route_request = state.get("context", {}).get("route_request", {})
        meteorology = state.get("meteorology_output", {})
        
        if not cartographer_output:
            logger.warning("No cartographer output found for Navigator")
            return {
                "explanation": "Route computation in progress...",
                "detailed_explanation": "",
                "route_insights": []
            }
        
        logger.info("Navigator building detailed explanation for route")
        
        # Extract route data
        stats = cartographer_output.get("stats", {})
        adjustments = cartographer_output.get("adjustments", {})
        health_delta = cartographer_output.get("health_delta", 0.0)
        
        # Build detailed explanation
        detailed_explanation = self._build_detailed_explanation(
            stats,
            adjustments,
            health_delta,
            route_request,
            meteorology
        )
        
        # Extract route insights
        route_insights = self._extract_route_insights(stats, adjustments, meteorology)
        
        output = {
            "explanation": cartographer_output.get("explanation", ""),
            "detailed_explanation": detailed_explanation,
            "route_insights": route_insights,
            "health_benefit": f"{health_delta * 100:.1f}% reduction in inhaled dose",
            "timestamp": state.get("timestamp")
        }
        
        logger.info("Navigator completed explanation")
        return output
    
    def _build_detailed_explanation(
        self,
        stats: Dict[str, Any],
        adjustments: Dict[str, Any],
        health_delta: float,
        route_request: Dict[str, Any],
        meteorology: Dict[str, Any]
    ) -> str:
        """
        Build a detailed, user-friendly explanation of the routing choice.
        
        Format: "I found a route that is X minutes longer but avoids Y..."
        """
        fastest_minutes = stats.get("fastest_minutes", 0.0)
        cleanest_minutes = stats.get("cleanest_minutes", 0.0)
        fastest_aqi = stats.get("fastest_aqi", 0.0)
        cleanest_aqi = stats.get("cleanest_aqi", 0.0)
        
        time_difference = cleanest_minutes - fastest_minutes
        aqi_difference = fastest_aqi - cleanest_aqi
        
        # Build explanation components
        explanation_parts = []
        
        # Time comparison
        if time_difference > 0:
            explanation_parts.append(
                f"I found a route that is {time_difference:.1f} minutes longer"
            )
        elif time_difference < 0:
            explanation_parts.append(
                f"I found a route that is {abs(time_difference):.1f} minutes shorter"
            )
        else:
            explanation_parts.append("I found a route with similar travel time")
        
        # AQI benefit
        if aqi_difference > 0:
            explanation_parts.append(
                f"but reduces your exposure to air pollution by {aqi_difference:.0f} AQI points"
            )
        
        # Specific route features
        route_features = []
        
        # Wind breaker
        if adjustments.get("wind_bias") == "westerly":
            route_features.append("stays on the ocean side streets where westerly winds keep the air cleaner")
        
        # Pollen avoidance
        if adjustments.get("pollen_penalty"):
            route_features.append("avoids park pollen corridors where pollen levels are high today")
        
        # Fog guard
        if adjustments.get("fog_guard"):
            route_features.append("accounts for fog conditions that can affect sensor readings")
        
        # Steep hills (if we had that data, we'd mention it)
        # For now, we can infer from grade penalties in the routing
        
        if route_features:
            explanation_parts.append("and " + ", ".join(route_features))
        
        # Health benefit
        if health_delta > 0:
            explanation_parts.append(
                f"This route reduces your inhaled pollution dose by {health_delta * 100:.1f}%"
            )
        
        # Calendar Sentry
        calendar_suggestions = adjustments.get("calendar_suggestions", [])
        if calendar_suggestions:
            for suggestion in calendar_suggestions[:1]:  # Show first suggestion
                event_name = suggestion.get("event_name", "upcoming event")
                aqi_forecast = suggestion.get("aqi_forecast", 0)
                explanation_parts.append(
                    f"Calendar Sentry detected '{event_name}' - AQI will be {aqi_forecast:.0f}. "
                    "Consider rescheduling to avoid peak pollution."
                )
        
        # Combine into full explanation
        explanation = ". ".join(explanation_parts) + "."
        
        # Use Bedrock to refine if available (optional enhancement)
        try:
            refined = self._refine_with_llm(explanation, stats, adjustments)
            return refined
        except Exception as e:
            logger.warning(f"Failed to refine explanation with LLM: {e}")
            return explanation
    
    def _refine_with_llm(
        self,
        base_explanation: str,
        stats: Dict[str, Any],
        adjustments: Dict[str, Any]
    ) -> str:
        """
        Optionally refine the explanation using LLM for more natural language.
        """
        system_prompt = """You are Respiro's Navigator, explaining routing choices to asthma patients.
Keep explanations clear, friendly, and specific. Mention specific streets or areas when relevant.
Be concise but informative."""
        
        prompt = f"""Refine this route explanation to be more natural and user-friendly:

Current explanation: {base_explanation}

Route statistics:
- Fastest route: {stats.get('fastest_minutes', 0):.1f} minutes, AQI {stats.get('fastest_aqi', 0):.0f}
- Cleanest route: {stats.get('cleanest_minutes', 0):.1f} minutes, AQI {stats.get('cleanest_aqi', 0):.0f}

Adjustments applied:
- Wind Breaker: {adjustments.get('wind_bias', 'None')}
- Fog Guard: {adjustments.get('fog_guard', False)}
- Pollen Penalty: {adjustments.get('pollen_penalty', False)}

Provide a refined, natural explanation that a patient would understand easily."""
        
        return self.bedrock.generate(prompt, system_prompt=system_prompt, temperature=0.7, max_tokens=300)
    
    def _extract_route_insights(
        self,
        stats: Dict[str, Any],
        adjustments: Dict[str, Any],
        meteorology: Dict[str, Any]
    ) -> list[Dict[str, Any]]:
        """
        Extract key insights about the route for display.
        """
        insights = []
        
        # Time vs health tradeoff
        time_diff = stats.get("cleanest_minutes", 0) - stats.get("fastest_minutes", 0)
        aqi_diff = stats.get("fastest_aqi", 0) - stats.get("cleanest_aqi", 0)
        
        if time_diff > 0 and aqi_diff > 10:
            insights.append({
                "type": "tradeoff",
                "title": "Time vs Health Tradeoff",
                "description": f"Adds {time_diff:.1f} minutes but reduces AQI by {aqi_diff:.0f} points"
            })
        
        # Wind breaker insight
        if adjustments.get("wind_bias"):
            insights.append({
                "type": "wind",
                "title": "Wind Breaker Active",
                "description": "Route optimized for prevailing wind patterns"
            })
        
        # Pollen insight
        if adjustments.get("pollen_penalty"):
            pollen_alerts = adjustments.get("pollen_alerts", [])
            if pollen_alerts:
                pollen_types = [alert.get("type", "pollen") for alert in pollen_alerts[:2]]
                insights.append({
                    "type": "pollen",
                    "title": "Pollen Avoidance",
                    "description": f"Avoiding high {', '.join(pollen_types)} areas"
                })
        
        # Fog guard insight
        if adjustments.get("fog_guard"):
            insights.append({
                "type": "fog",
                "title": "Fog Guard Active",
                "description": "Accounting for fog conditions affecting sensor readings"
            })
        
        return insights

