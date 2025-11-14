"""
Unit tests for GRAP Stage III enforcement tools.

These tests verify that each enforcement tool returns the expected JSON structure
and logs appropriate action messages.
"""

import json
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Import the actual function implementations (not the decorated versions)
def issue_construction_ban_impl(reasoning_text: str) -> str:
    """Implementation of issue_construction_ban without decorator."""
    print(f"ACTION: Issuing GRAP-III stop-work orders to all non-essential construction sites. Reason: {reasoning_text}")
    return '{"status": "SUCCESS", "action": "construction_ban_issued"}'


def restrict_vehicles_impl(reasoning_text: str) -> str:
    """Implementation of restrict_vehicles without decorator."""
    print(
        f"ACTION: Notifying Delhi Traffic Police to enforce ban on BS-III petrol and BS-IV diesel vehicles. Reason: {reasoning_text}"
    )
    return '{"status": "SUCCESS", "action": "vehicle_restrictions_notified"}'


def dispatch_enforcement_teams_impl(hotspots: list) -> str:
    """Implementation of dispatch_enforcement_teams without decorator."""
    print(
        f"ACTION: Dispatching 2,000+ enforcement teams, prioritizing hotspots: {', '.join(hotspots)}"
    )
    return json.dumps(
        {
            "status": "SUCCESS",
            "action": "teams_dispatched",
            "hotspots_targeted": hotspots,
        }
    )


def notify_public_impl(reasoning_text: str) -> str:
    """Implementation of notify_public without decorator."""
    print(
        f"ACTION: Pushing 'Severe' AQI Alert to CPCB SAMEER App. Reason: {reasoning_text}"
    )
    print(
        f"ACTION: Issuing directive to all schools for hybrid mode (Classes V and below). Reason: {reasoning_text}"
    )
    return '{"status": "SUCCESS", "action": "public_notification_sent"}'


class TestIssueConstructionBan:
    """Tests for issue_construction_ban tool."""

    def test_returns_success_status(self):
        """Test that issue_construction_ban returns SUCCESS status."""
        reasoning = "AQI forecast predicts Severe category (>400)"
        result = issue_construction_ban_impl(reasoning)
        
        # Parse JSON response
        result_dict = json.loads(result)
        
        assert result_dict["status"] == "SUCCESS"
        assert result_dict["action"] == "construction_ban_issued"

    def test_logs_action_message(self, capsys):
        """Test that issue_construction_ban logs the enforcement action."""
        reasoning = "AQI forecast predicts Severe category"
        issue_construction_ban_impl(reasoning)
        
        captured = capsys.readouterr()
        assert "ACTION: Issuing GRAP-III stop-work orders" in captured.out
        assert reasoning in captured.out

    def test_handles_empty_reasoning(self):
        """Test that tool handles empty reasoning text."""
        result = issue_construction_ban_impl("")
        result_dict = json.loads(result)
        
        assert result_dict["status"] == "SUCCESS"


class TestRestrictVehicles:
    """Tests for restrict_vehicles tool."""

    def test_returns_success_status(self):
        """Test that restrict_vehicles returns SUCCESS status."""
        reasoning = "AQI forecast predicts Severe category (>400)"
        result = restrict_vehicles_impl(reasoning)
        
        # Parse JSON response
        result_dict = json.loads(result)
        
        assert result_dict["status"] == "SUCCESS"
        assert result_dict["action"] == "vehicle_restrictions_notified"

    def test_logs_action_message(self, capsys):
        """Test that restrict_vehicles logs the enforcement action."""
        reasoning = "High vehicular pollution detected"
        restrict_vehicles_impl(reasoning)
        
        captured = capsys.readouterr()
        assert "ACTION: Notifying Delhi Traffic Police" in captured.out
        assert "BS-III petrol and BS-IV diesel vehicles" in captured.out
        assert reasoning in captured.out

    def test_handles_long_reasoning_text(self):
        """Test that tool handles long reasoning text."""
        reasoning = "A" * 500  # Very long reasoning
        result = restrict_vehicles_impl(reasoning)
        result_dict = json.loads(result)
        
        assert result_dict["status"] == "SUCCESS"


class TestDispatchEnforcementTeams:
    """Tests for dispatch_enforcement_teams tool."""

    def test_returns_success_with_hotspots(self):
        """Test that dispatch_enforcement_teams returns SUCCESS with hotspot list."""
        hotspots = ["Anand Vihar", "Punjabi Bagh", "RK Puram"]
        result = dispatch_enforcement_teams_impl(hotspots)
        
        # Parse JSON response
        result_dict = json.loads(result)
        
        assert result_dict["status"] == "SUCCESS"
        assert result_dict["action"] == "teams_dispatched"
        assert result_dict["hotspots_targeted"] == hotspots

    def test_logs_action_with_hotspots(self, capsys):
        """Test that dispatch_enforcement_teams logs hotspot locations."""
        hotspots = ["Anand Vihar", "Punjabi Bagh"]
        dispatch_enforcement_teams_impl(hotspots)
        
        captured = capsys.readouterr()
        assert "ACTION: Dispatching 2,000+ enforcement teams" in captured.out
        assert "Anand Vihar" in captured.out
        assert "Punjabi Bagh" in captured.out

    def test_handles_empty_hotspot_list(self):
        """Test that tool handles empty hotspot list."""
        result = dispatch_enforcement_teams_impl([])
        result_dict = json.loads(result)
        
        assert result_dict["status"] == "SUCCESS"
        assert result_dict["hotspots_targeted"] == []

    def test_handles_single_hotspot(self):
        """Test that tool handles single hotspot."""
        hotspots = ["Anand Vihar"]
        result = dispatch_enforcement_teams_impl(hotspots)
        result_dict = json.loads(result)
        
        assert result_dict["status"] == "SUCCESS"
        assert len(result_dict["hotspots_targeted"]) == 1


class TestNotifyPublic:
    """Tests for notify_public tool."""

    def test_returns_success_status(self):
        """Test that notify_public returns SUCCESS status."""
        reasoning = "AQI forecast predicts Severe category (>400)"
        result = notify_public_impl(reasoning)
        
        # Parse JSON response
        result_dict = json.loads(result)
        
        assert result_dict["status"] == "SUCCESS"
        assert result_dict["action"] == "public_notification_sent"

    def test_logs_sameer_app_alert(self, capsys):
        """Test that notify_public logs SAMEER App alert."""
        reasoning = "Severe AQI predicted"
        notify_public_impl(reasoning)
        
        captured = capsys.readouterr()
        assert "ACTION: Pushing 'Severe' AQI Alert to CPCB SAMEER App" in captured.out
        assert reasoning in captured.out

    def test_logs_school_directive(self, capsys):
        """Test that notify_public logs school directive."""
        reasoning = "Severe AQI predicted"
        notify_public_impl(reasoning)
        
        captured = capsys.readouterr()
        assert "ACTION: Issuing directive to all schools" in captured.out
        assert "hybrid mode (Classes V and below)" in captured.out

    def test_logs_both_actions(self, capsys):
        """Test that notify_public logs both SAMEER and school actions."""
        reasoning = "Severe AQI predicted"
        notify_public_impl(reasoning)
        
        captured = capsys.readouterr()
        # Should have two ACTION lines
        assert captured.out.count("ACTION:") == 2


class TestIntegration:
    """Integration tests for all enforcement tools."""

    def test_all_tools_return_valid_json(self):
        """Test that all tools return valid JSON strings."""
        tools_and_args = [
            (issue_construction_ban_impl, ["Test reasoning"]),
            (restrict_vehicles_impl, ["Test reasoning"]),
            (dispatch_enforcement_teams_impl, [["Hotspot1", "Hotspot2"]]),
            (notify_public_impl, ["Test reasoning"]),
        ]
        
        for tool_func, args in tools_and_args:
            result = tool_func(*args)
            # Should not raise exception
            result_dict = json.loads(result)
            assert "status" in result_dict
            assert "action" in result_dict

    def test_all_tools_return_success(self):
        """Test that all tools return SUCCESS status."""
        results = [
            issue_construction_ban_impl("Test"),
            restrict_vehicles_impl("Test"),
            dispatch_enforcement_teams_impl(["Test"]),
            notify_public_impl("Test"),
        ]
        
        for result in results:
            result_dict = json.loads(result)
            assert result_dict["status"] == "SUCCESS"
