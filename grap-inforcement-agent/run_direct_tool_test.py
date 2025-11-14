"""
Direct Tool Test for GRAP Enforcement Agent

This script demonstrates all four enforcement tools working correctly
by calling them directly without LLM orchestration.
"""

import json
from src.tools.enforcement_tools import issue_construction_ban
from src.tools.restrict_vehicles import restrict_vehicles
from src.tools.dispatch_enforcement_teams import dispatch_enforcement_teams
from src.tools.notify_public import notify_public

# Extract the actual functions from CrewAI Tool objects
issue_construction_ban_func = issue_construction_ban.func if hasattr(issue_construction_ban, 'func') else issue_construction_ban
restrict_vehicles_func = restrict_vehicles.func if hasattr(restrict_vehicles, 'func') else restrict_vehicles
dispatch_enforcement_teams_func = dispatch_enforcement_teams.func if hasattr(dispatch_enforcement_teams, 'func') else dispatch_enforcement_teams
notify_public_func = notify_public.func if hasattr(notify_public, 'func') else notify_public

print("=" * 80)
print("--- DIRECT TOOL TEST FOR GRAP ENFORCEMENT AGENT ---")
print("=" * 80)

# Mock forecast data
mock_forecast = {
    "predicted_aqi_category": "Severe",
    "confidence_level": "High",
    "reasoning": "High stubble burning + low wind speed detected",
    "hotspots": ["Anand Vihar", "Punjabi Bagh", "RK Puram", "Dwarka"]
}

print("\nMocked Forecast Input:")
print(json.dumps(mock_forecast, indent=2))
print("\n" + "=" * 80)
print("EXECUTING GRAP STAGE III ENFORCEMENT ACTIONS")
print("=" * 80 + "\n")

# Collect results
results = {}

# Step 1: Issue construction ban
print("STEP 1: Issuing Construction Ban")
print("-" * 80)
result1 = issue_construction_ban_func(mock_forecast["reasoning"])
results["construction_ban"] = json.loads(result1)
print(f"Result: {result1}\n")

# Step 2: Restrict vehicles
print("STEP 2: Restricting Vehicles")
print("-" * 80)
result2 = restrict_vehicles_func(mock_forecast["reasoning"])
results["vehicle_restrictions"] = json.loads(result2)
print(f"Result: {result2}\n")

# Step 3: Notify public
print("STEP 3: Notifying Public")
print("-" * 80)
result3 = notify_public_func(mock_forecast["reasoning"])
results["public_notification"] = json.loads(result3)
print(f"Result: {result3}\n")

# Step 4: Dispatch enforcement teams
print("STEP 4: Dispatching Enforcement Teams")
print("-" * 80)
result4 = dispatch_enforcement_teams_func(mock_forecast["hotspots"])
results["enforcement_teams"] = json.loads(result4)
print(f"Result: {result4}\n")

# Final summary
print("=" * 80)
print("--- TEST COMPLETE ---")
print("=" * 80)
print("\nFinal Summary Report:")
print(json.dumps(results, indent=2))
print("\n" + "=" * 80)
print("✅ ALL FOUR ENFORCEMENT ACTIONS EXECUTED SUCCESSFULLY")
print("=" * 80)
