"""
Advanced Visualization Functions

Provides pollution drift animations, heat maps, and time-lapse visualizations.
"""

import math
from typing import Any
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import folium
from folium.plugins import HeatMap


def create_pollution_drift_animation(
    forecast_data: dict[str, Any],
    fire_data: pd.DataFrame,
    hours: int = 48
) -> go.Figure:
    """
    Create animated visualization showing pollution drift based on wind direction.
    
    Args:
        forecast_data: Forecast data containing wind information
        fire_data: DataFrame with fire locations (lat, lon)
        hours: Number of hours to animate (default: 48)
        
    Returns:
        plotly Figure with animation
    """
    if not forecast_data or "data_sources" not in forecast_data:
        # Return empty figure if no data
        fig = go.Figure()
        fig.add_annotation(
            text="No forecast data available for pollution drift animation",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    ds = forecast_data.get("data_sources", {})
    wind_direction = ds.get("avg_wind_direction_24h_deg")
    wind_speed = ds.get("avg_wind_speed_24h_kmh")
    
    if wind_direction is None or wind_speed is None:
        fig = go.Figure()
        fig.add_annotation(
            text="Wind data not available for pollution drift animation",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Delhi center
    delhi_center = [28.6139, 77.2090]
    
    # Convert wind direction to radians (adjust for map orientation)
    wind_rad = math.radians(wind_direction - 90)
    
    # Create frames for animation
    frames = []
    steps = []
    
    for hour in range(0, hours, 2):  # Every 2 hours
        # Calculate drift distance (km per hour)
        drift_distance_km = wind_speed * (hour / 24.0)  # Scale by hours
        
        # Convert km to degrees (approximate: 1 degree ≈ 111 km)
        drift_deg = drift_distance_km / 111.0
        
        # Calculate drift endpoint
        drift_lat = delhi_center[0] + drift_deg * math.cos(wind_rad)
        drift_lon = delhi_center[1] + drift_deg * math.sin(wind_rad)
        
        # Create scatter plot for fires
        fire_lats = fire_data["lat"].tolist() if not fire_data.empty and "lat" in fire_data.columns else []
        fire_lons = fire_data["lon"].tolist() if not fire_data.empty and "lon" in fire_data.columns else []
        
        # Create frame
        frame_data = [
            go.Scattergeo(
                lon=fire_lons + [drift_lon],
                lat=fire_lats + [drift_lat],
                mode="markers",
                marker=dict(
                    size=[12] * len(fire_lons) + [24],
                    color=["#ef4444"] * len(fire_lons) + ["#3b82f6"],
                    symbol=["circle"] * len(fire_lons) + ["triangle-up"],
                    line=dict(width=2, color="white")
                ),
                name=f"Hour {hour}",
                text=[f"Fire {i+1}" for i in range(len(fire_lons))] + ["Pollution Drift"],
                hovertemplate="%{text}<br>Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<extra></extra>"
            )
        ]
        
        frames.append(go.Frame(
            data=frame_data,
            name=str(hour)
        ))
        
        steps.append({
            "label": f"{hour}h",
            "method": "animate",
            "args": [
                [str(hour)],
                {
                    "frame": {"duration": 500, "redraw": True},
                    "mode": "immediate",
                    "transition": {"duration": 300}
                }
            ]
        )
    
    # Initial data
    initial_fire_lats = fire_data["lat"].tolist() if not fire_data.empty and "lat" in fire_data.columns else []
    initial_fire_lons = fire_data["lon"].tolist() if not fire_data.empty and "lon" in fire_data.columns else []
    
    fig = go.Figure(
        data=[
            go.Scattergeo(
                lon=initial_fire_lons,
                lat=initial_fire_lats,
                mode="markers",
                marker=dict(
                    size=12, 
                    color="#ef4444", 
                    symbol="circle",
                    line=dict(width=2, color="white")
                ),
                name="Farm Fires",
                text=[f"Fire {i+1}" for i in range(len(initial_fire_lons))],
                hovertemplate="<b>%{text}</b><br>Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<extra></extra>"
            )
        ],
        frames=frames
    )
    
    # Update layout
    fig.update_geos(
        center=dict(lat=delhi_center[0], lon=delhi_center[1]),
        projection_scale=8,
        showland=True,
        landcolor="lightgray",
        showocean=True,
        oceancolor="lightblue"
    )
    
    fig.update_layout(
        title=dict(
            text=f"🌬️ Pollution Drift Animation<br><sub>Wind: {wind_direction:.0f}° at {wind_speed:.1f} km/h</sub>",
            font=dict(size=18, color="#0f172a"),
            x=0.5,
            xanchor="center"
        ),
        height=600,
        template='plotly_white',
        paper_bgcolor='white',
        plot_bgcolor='white',
        updatemenus=[{
            "type": "buttons",
            "showactive": False,
            "x": 0.1,
            "y": 0,
            "xanchor": "left",
            "yanchor": "bottom",
            "bgcolor": "rgba(255, 255, 255, 0.8)",
            "bordercolor": "#e2e8f0",
            "borderwidth": 1,
            "buttons": [
                {
                    "label": "▶ Play",
                    "method": "animate",
                    "args": [None, {
                        "frame": {"duration": 500, "redraw": True},
                        "fromcurrent": True,
                        "transition": {"duration": 300}
                    }]
                },
                {
                    "label": "⏸ Pause",
                    "method": "animate",
                    "args": [[None], {
                        "frame": {"duration": 0, "redraw": False},
                        "mode": "immediate",
                        "transition": {"duration": 0}
                    }]
                }
            ]
        }],
        sliders=[{
            "active": 0,
            "steps": steps,
            "currentvalue": {
                "prefix": "Time: ",
                "font": {"size": 12, "color": "#475569"}
            },
            "bgcolor": "rgba(255, 255, 255, 0.8)",
            "bordercolor": "#e2e8f0"
        }]
    )
    
    return fig


def create_aqi_heatmap(
    aqi_data: pd.DataFrame,
    center_lat: float = 28.6139,
    center_lon: float = 77.2090
) -> folium.Map:
    """
    Create AQI heat map overlay on Delhi map.
    
    Args:
        aqi_data: DataFrame with columns: lat, lon, value (AQI)
        center_lat: Center latitude for map
        center_lon: Center longitude for map
        
    Returns:
        folium Map with heat map overlay
    """
    # Create base map with modern tile
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles='CartoDB positron',
        attr='CartoDB'
    )
    
    if aqi_data.empty or "lat" not in aqi_data.columns or "lon" not in aqi_data.columns:
        return m
    
    # Prepare heat map data
    heat_data = []
    for idx, row in aqi_data.iterrows():
        lat = row.get("lat")
        lon = row.get("lon")
        value = row.get("value", 0)
        
        if pd.notna(lat) and pd.notna(lon) and value > 0:
            # Weight by AQI value (higher AQI = more intense)
            weight = min(1.0, value / 500.0)  # Normalize to 0-1
            heat_data.append([lat, lon, weight])
    
    if heat_data:
        # Add heat map layer
        HeatMap(
            heat_data,
            min_opacity=0.2,
            max_zoom=18,
            radius=25,
            blur=15,
            gradient={
                0.0: '#22c55e',  # Green
                0.2: '#eab308',  # Yellow
                0.4: '#f97316',  # Orange
                0.6: '#ef4444',  # Red
                0.8: '#dc2626',  # Dark red
                1.0: '#b91c1c'   # Very dark red
            }
        ).add_to(m)
    
    # Add markers for AQI stations
    for idx, row in aqi_data.iterrows():
        lat = row.get("lat")
        lon = row.get("lon")
        value = row.get("value", 0)
        
        if pd.notna(lat) and pd.notna(lon):
            # Determine color based on AQI (consistent with dashboard theme)
            if value > 400:
                color = "#b91c1c"  # Severe - Dark red
            elif value > 300:
                color = "#ef4444"  # Very Poor - Red
            elif value > 200:
                color = "#f97316"  # Poor - Orange
            elif value > 100:
                color = "#eab308"  # Moderate - Yellow
            else:
                color = "#22c55e"  # Satisfactory - Green
            
            # Enhanced popup
            popup_html = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                        width: 180px; padding: 8px;">
                <div style="border-left: 4px solid {color}; padding-left: 8px;">
                    <h4 style="margin: 0 0 4px 0; color: {color}; font-size: 14px; font-weight: 600;">
                        🌡️ AQI Station
                    </h4>
                    <p style="margin: 0; font-size: 18px; font-weight: 700; color: {color};">
                        {value:.0f}
                    </p>
                </div>
            </div>
            """
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=max(6, min(20, 6 + (value / 30))),
                popup=folium.Popup(popup_html, max_width=200),
                color='white',
                fillColor=color,
                fillOpacity=0.8,
                weight=3
            ).add_to(m)
    
    return m


def create_timelapse_visualization(
    historical_forecasts: list[dict[str, Any]]
) -> go.Figure:
    """
    Create time-lapse visualization showing AQI, fire count, and stubble contribution changes.
    
    Args:
        historical_forecasts: List of historical forecast data
        
    Returns:
        plotly Figure with animated time-lapse
    """
    if not historical_forecasts:
        fig = go.Figure()
        fig.add_annotation(
            text="No historical data available for time-lapse visualization",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Extract data
    timestamps = []
    aqi_values = []
    fire_counts = []
    stubble_percents = []
    
    for forecast in historical_forecasts:
        timestamp_str = forecast.get("timestamp", forecast.get("_file_timestamp", ""))
        if timestamp_str:
            try:
                if "T" in timestamp_str:
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    dt = datetime.fromisoformat(timestamp_str)
                timestamps.append(dt)
            except (ValueError, TypeError):
                continue
        
        data_sources = forecast.get("data_sources", {})
        aqi = data_sources.get("cpcb_aqi")
        fire_count = data_sources.get("nasa_fire_count")
        stubble = data_sources.get("stubble_burning_percent")
        
        aqi_values.append(float(aqi) if aqi is not None else None)
        fire_counts.append(int(fire_count) if fire_count is not None else None)
        stubble_percents.append(float(stubble) if stubble is not None else None)
    
    if not timestamps:
        fig = go.Figure()
        fig.add_annotation(
            text="No valid timestamps found in historical data",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Create subplots
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("AQI Over Time", "Fire Count Over Time", "Stubble Contribution Over Time"),
        vertical_spacing=0.1
    )
    
    # AQI plot with enhanced styling
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=aqi_values,
            mode="lines+markers",
            name="AQI",
            line=dict(color="#ef4444", width=3),
            marker=dict(size=7, color="#ef4444", line=dict(width=1, color="white")),
            fill='tozeroy',
            fillcolor='rgba(239, 68, 68, 0.1)',
            hovertemplate='<b>%{x}</b><br>AQI: %{y:.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Fire count plot with enhanced styling
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=fire_counts,
            mode="lines+markers",
            name="Fire Count",
            line=dict(color="#f97316", width=3),
            marker=dict(size=7, color="#f97316", line=dict(width=1, color="white")),
            fill='tozeroy',
            fillcolor='rgba(249, 115, 22, 0.1)',
            hovertemplate='<b>%{x}</b><br>Fires: %{y}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Stubble contribution plot with enhanced styling
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=stubble_percents,
            mode="lines+markers",
            name="Stubble %",
            line=dict(color="#a16207", width=3),
            marker=dict(size=7, color="#a16207", line=dict(width=1, color="white")),
            fill='tozeroy',
            fillcolor='rgba(161, 98, 7, 0.1)',
            hovertemplate='<b>%{x}</b><br>Stubble: %{y:.1f}%<extra></extra>'
        ),
        row=3, col=1
    )
    
    # Update axes with better styling
    fig.update_xaxes(
        title_text="Time",
        row=3, col=1,
        showgrid=True,
        gridcolor='#e2e8f0',
        title_font=dict(size=12, color="#475569")
    )
    fig.update_yaxes(
        title_text="AQI",
        row=1, col=1,
        showgrid=True,
        gridcolor='#e2e8f0',
        title_font=dict(size=12, color="#475569")
    )
    fig.update_yaxes(
        title_text="Fire Count",
        row=2, col=1,
        showgrid=True,
        gridcolor='#e2e8f0',
        title_font=dict(size=12, color="#475569")
    )
    fig.update_yaxes(
        title_text="Stubble %",
        row=3, col=1,
        showgrid=True,
        gridcolor='#e2e8f0',
        title_font=dict(size=12, color="#475569")
    )
    
    fig.update_layout(
        title=dict(
            text="⏱️ Time-Lapse: Pollution Trends (Last 7 Days)",
            font=dict(size=18, color="#0f172a"),
            x=0.5,
            xanchor="center"
        ),
        height=900,
        showlegend=False,
        template='plotly_white',
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=60, b=0)
    )
    
    return fig

