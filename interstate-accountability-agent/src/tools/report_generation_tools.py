"""
Report generation tools for InterState-AccountabilityAgent.

Generates structured CAQM accountability reports with legal citations,
reasoning statements, and recommendations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.config.thresholds import (
    HIGH_FIRE_COUNT_THRESHOLD,
    LOW_FIRE_COUNT_THRESHOLD,
    MEDIUM_FIRE_COUNT_THRESHOLD,
)
from src.models.data_models import (
    CAQMReport,
    CorrelationResult,
    LegalCitations,
)
from src.tools.correlation_tools import calculate_confidence_score, debug_log


def generate_report_id() -> str:
    """
    Generate unique report ID.
    
    Format: CAQM-YYYY-MM-DD-NNN where NNN is a 3-digit sequence number.
    For simplicity, we use timestamp-based ID.
    
    Returns:
        Unique report ID string
    """
    now = datetime.utcnow()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    return f"CAQM-{now.strftime('%Y-%m-%d')}-{timestamp[-3:]}"


def generate_executive_summary(
    surge_station_name: str,
    surge_aqi: float,
    correlation_results: list[CorrelationResult],
) -> str:
    """
    Generate executive summary for CAQM report.
    
    Args:
        surge_station_name: Name of the station with surge
        surge_aqi: AQI value at surge station
        correlation_results: List of correlation results by state
        
    Returns:
        Executive summary text
    """
    top_states = sorted(
        correlation_results,
        key=lambda x: x.fire_count,
        reverse=True,
    )[:3]
    
    summary_parts = [
        f"A severe pollution surge has been detected at {surge_station_name} border station "
        f"with AQI of {surge_aqi:.0f}.",
    ]
    
    if top_states:
        state_names = [cr.state for cr in top_states]
        fire_counts = [cr.fire_count for cr in top_states]
        summary_parts.append(
            f"Correlation analysis identifies {', '.join(state_names)} as top contributing states "
            f"with {', '.join(str(c) for c in fire_counts)} fire events respectively."
        )
    else:
        summary_parts.append("Fire correlation analysis is pending.")
    
    return " ".join(summary_parts)


def generate_reasoning_statement(
    surge_station_name: str,
    surge_aqi: float,
    correlation_results: list[CorrelationResult],
    stubble_burning_percent: float | None,
) -> str:
    """
    Generate IF-AND-THEN reasoning statement.
    
    Args:
        surge_station_name: Name of the station with surge
        surge_aqi: AQI value at surge station
        correlation_results: List of correlation results
        stubble_burning_percent: Stubble burning contribution percentage
        
    Returns:
        Reasoning statement text
    """
    total_fires = sum(cr.fire_count for cr in correlation_results)
    top_state = max(correlation_results, key=lambda x: x.fire_count) if correlation_results else None
    
    reasoning_parts = [
        f"IF {surge_station_name} border station shows AQI surge of {surge_aqi:.0f}",
    ]
    
    if top_state:
        reasoning_parts.append(
            f"AND {top_state.state} has {top_state.fire_count} fire events "
            f"within 200km and 48 hours of the surge",
        )
    
    if stubble_burning_percent is not None:
        reasoning_parts.append(
            f"AND DSS data shows {stubble_burning_percent:.1f}% contribution from stubble burning",
        )
    
    reasoning_parts.append(
        f"THEN the pollution surge is directly correlated with cross-border fire events "
        f"from neighboring states, confirming non-compliance with CAQM Direction No. 95."
    )
    
    return " ".join(reasoning_parts)


def generate_recommendations(
    correlation_results: list[CorrelationResult],
    stubble_burning_percent: float | None,
) -> list[str]:
    """
    Generate recommendations based on correlation results.
    
    Args:
        correlation_results: List of correlation results
        stubble_burning_percent: Stubble burning contribution percentage
        
    Returns:
        List of recommendation strings
    """
    recommendations: list[str] = []
    
    total_fires = sum(cr.fire_count for cr in correlation_results)
    
    if total_fires >= HIGH_FIRE_COUNT_THRESHOLD:
        recommendations.append(
            f"Immediate enforcement action required in neighboring states to reduce "
            f"stubble burning. {total_fires} fire events detected within correlation window."
        )
    elif total_fires >= MEDIUM_FIRE_COUNT_THRESHOLD:
        recommendations.append(
            f"Enhanced monitoring and enforcement required. {total_fires} fire events "
            f"detected within correlation window."
        )
    else:
        recommendations.append(
            f"Continued monitoring recommended. {total_fires} fire events detected."
        )
    
    if stubble_burning_percent is not None and stubble_burning_percent > 20:
        recommendations.append(
            f"Critical: Stubble burning contributes {stubble_burning_percent:.1f}% to current "
            f"pollution levels. Immediate intervention required."
        )
    
    recommendations.append(
        "Enhanced monitoring at border stations to track cross-border pollution patterns."
    )
    
    recommendations.append(
        "Coordination with state governments for compliance with CAQM directives "
        "under Section 12 of the CAQM Act, 2021."
    )
    
    return recommendations


def generate_report(
    surge_station: dict[str, Any],
    correlation_results: list[CorrelationResult],
    nasa_data_available: bool = True,
    dss_data_available: bool = True,
    dss_data: dict[str, Any] | None = None,
) -> CAQMReport:
    """
    Generate complete CAQM accountability report.
    
    Args:
        surge_station: Dictionary with surge station data
        correlation_results: List of CorrelationResult objects
        nasa_data_available: Whether NASA data is available
        dss_data_available: Whether DSS data is available
        dss_data: DSS data dictionary (optional)
        
    Returns:
        CAQMReport object
    """
    debug_log("generate_report", "Generating CAQM accountability report")
    
    # Extract surge details
    surge_station_name = surge_station.get("name", "Unknown")
    surge_aqi = surge_station.get("aqi", 0)
    
    # Extract stubble burning percentage
    stubble_burning_percent = None
    if dss_data:
        stubble_burning_percent = dss_data.get("stubble_burning_percent")
    
    # Generate report components
    report_id = generate_report_id()
    executive_summary = generate_executive_summary(
        surge_station_name,
        surge_aqi,
        correlation_results,
    )
    reasoning = generate_reasoning_statement(
        surge_station_name,
        surge_aqi,
        correlation_results,
        stubble_burning_percent,
    )
    
    # Calculate confidence score
    confidence_score = calculate_confidence_score(
        correlation_results,
        nasa_data_available,
        dss_data_available,
    )
    
    # Build surge details
    surge_details = {
        "station_name": surge_station_name,
        "aqi": surge_aqi,
        "pm25": surge_station.get("pm25"),
        "pm10": surge_station.get("pm10"),
        "border": surge_station.get("border"),
        "district": surge_station.get("district"),
        "timestamp": surge_station.get("timestamp"),
    }
    
    # Build fire correlation section
    fire_correlation = {
        "total_fires": sum(cr.fire_count for cr in correlation_results),
        "states": [
            {
                "state": cr.state,
                "fire_count": cr.fire_count,
                "districts": cr.districts,
                "avg_distance_km": cr.avg_distance_km,
                "is_high_contribution": cr.is_high_contribution,
            }
            for cr in correlation_results
        ],
    }
    
    # Build data quality section
    data_quality = {
        "cpcb_data_available": True,  # We have surge data, so CPCB is available
        "nasa_data_available": nasa_data_available,
        "dss_data_available": dss_data_available,
        "data_completeness": (
            "Complete" if (nasa_data_available and dss_data_available)
            else "Partial" if (nasa_data_available or dss_data_available)
            else "Limited"
        ),
    }
    
    # Generate recommendations
    recommendations = generate_recommendations(
        correlation_results,
        stubble_burning_percent,
    )
    
    # Create legal citations
    legal_citations = LegalCitations()
    
    # Create report
    report = CAQMReport(
        report_id=report_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        executive_summary=executive_summary,
        surge_details=surge_details,
        fire_correlation=fire_correlation,
        stubble_burning_percent=stubble_burning_percent,
        reasoning=reasoning,
        confidence_score=confidence_score,
        data_quality=data_quality,
        legal_citations=legal_citations,
        recommendations=recommendations,
    )
    
    debug_log("generate_report", f"Report generated with ID: {report_id}")
    
    return report

