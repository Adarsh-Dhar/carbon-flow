"""Rewards Agent - Gamification engine."""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from respiro.orchestrator.state import RespiroState
from respiro.integrations.insurance import InsuranceClient
from respiro.integrations.pharmacy import PharmacyClient
from respiro.storage.s3_client import get_s3_client
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

class RewardsAgent:
    """Rewards agent for gamification and adherence tracking."""
    
    def __init__(self):
        self.insurance = InsuranceClient()
        self.pharmacy = PharmacyClient()
        self.s3_client = get_s3_client()
    
    def execute(self, state: RespiroState) -> Dict[str, Any]:
        """
        Execute Rewards agent for adherence tracking and rewards.
        
        Args:
            state: Current orchestrator state
            
        Returns:
            Rewards agent output
        """
        patient_id = state.get("patient_id")
        logger.info(f"Executing Rewards agent for patient {patient_id}")
        
        try:
            # Calculate adherence score from state and history
            adherence_score = self._calculate_adherence(state, patient_id)
            
            # Award points
            points = self._award_points(adherence_score, state)
            
            # Unlock rewards
            rewards = self._unlock_rewards(adherence_score, points, state)
            
            # Generate pharmacy discount codes for unlocked rewards
            pharmacy_codes = []
            for reward in rewards:
                if reward.get("type") == "pharmacy_discount":
                    try:
                        # Get medications from clinical recommendations
                        medications = state.get("clinical_recommendations", {}).get("recommendations", {}).get("medications", [])
                        if medications:
                            # Generate discount code for first medication
                            medication_name = medications[0].get("medications", [""])[0] if medications else "asthma_medication"
                            discount_code = self.pharmacy.generate_discount_code(patient_id, medication_name)
                            if discount_code:
                                reward["discount_code"] = discount_code
                                pharmacy_codes.append(discount_code)
                                logger.info(f"Generated pharmacy discount code for patient {patient_id}")
                    except Exception as e:
                        logger.warning(f"Failed to generate pharmacy discount code: {e}")
            
            # Request insurance premium adjustment
            insurance_requested = False
            if adherence_score > 0.8:
                try:
                    insurance_requested = self.insurance.request_premium_adjustment(patient_id, adherence_score)
                    if insurance_requested:
                        logger.info(f"Requested insurance premium adjustment for patient {patient_id}")
                except Exception as e:
                    logger.warning(f"Failed to request insurance adjustment: {e}")
            
            # Build output
            output = {
                "adherence_score": adherence_score,
                "points": points,
                "rewards": rewards,
                "pharmacy_codes": pharmacy_codes,
                "insurance_adjustment_requested": insurance_requested,
                "status": {
                    "adherence_level": self._get_adherence_level(adherence_score),
                    "points_balance": points,
                    "rewards_unlocked": len(rewards)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Store adherence history
            self._store_adherence_history(patient_id, adherence_score, points, state)
            
            # Persist to S3
            try:
                self.s3_client.upload_json(
                    f"patients/{patient_id}/rewards/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
                    output
                )
            except Exception as e:
                logger.warning(f"Failed to persist rewards to S3: {e}")
            
            return output
        except Exception as e:
            logger.error(f"Rewards agent failed: {e}", exc_info=True)
            return {
                "adherence_score": 0.0,
                "points": 0,
                "rewards": [],
                "status": {"adherence_level": "unknown"},
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def _calculate_adherence(self, state: RespiroState, patient_id: str) -> float:
        """
        Calculate medication adherence score from state and history.
        
        Args:
            state: Current state
            patient_id: Patient identifier
            
        Returns:
            Adherence score (0.0 to 1.0)
        """
        # Load adherence history
        adherence_history = self._load_adherence_history(patient_id)
        
        # Check if patient followed recommendations from clinical agent
        clinical_output = state.get("clinical_output", {})
        recommendations = clinical_output.get("recommendations", {})
        zone = recommendations.get("zone", "green")
        
        # Base score from zone compliance
        # Green zone = good adherence, Yellow = moderate, Red = poor
        zone_scores = {
            "green": 0.9,
            "yellow": 0.6,
            "red": 0.3
        }
        base_score = zone_scores.get(zone, 0.5)
        
        # Factor in historical adherence (weighted average)
        if adherence_history:
            historical_avg = sum(h.get("score", 0.5) for h in adherence_history[-7:]) / min(len(adherence_history), 7)
            # Weight: 70% current, 30% historical
            adherence_score = (base_score * 0.7) + (historical_avg * 0.3)
        else:
            adherence_score = base_score
        
        # Check for medication events in state
        # In production, would track actual medication intake events
        # For now, assume good adherence if in green zone
        if zone == "green":
            adherence_score = min(adherence_score + 0.1, 1.0)
        
        return round(adherence_score, 2)
    
    def _award_points(self, adherence_score: float, state: RespiroState) -> int:
        """
        Award points based on adherence and actions.
        
        Args:
            adherence_score: Adherence score
            state: Current state
            
        Returns:
            Points awarded
        """
        base_points = int(adherence_score * 100)
        
        # Bonus points for following recommendations
        clinical_output = state.get("clinical_output", {})
        zone = clinical_output.get("recommendations", {}).get("zone", "green")
        if zone == "green":
            base_points += 20  # Bonus for maintaining green zone
        
        # Bonus for IoT actions taken (showing proactive behavior)
        iot_actions = state.get("iot_actions", [])
        if iot_actions:
            base_points += 10  # Bonus for using smart home features
        
        return base_points
    
    def _unlock_rewards(self, adherence_score: float, points: int, state: RespiroState) -> List[Dict[str, Any]]:
        """
        Unlock rewards based on score and points.
        
        Args:
            adherence_score: Adherence score
            points: Current points
            state: Current state
            
        Returns:
            List of unlocked rewards
        """
        rewards = []
        
        # Premium discount for high adherence
        if adherence_score > 0.9:
            rewards.append({
                "type": "premium_discount",
                "value": "5% off next premium",
                "unlocked_at": datetime.utcnow().isoformat()
            })
        
        # Pharmacy discount for points milestone
        if points > 1000:
            rewards.append({
                "type": "pharmacy_discount",
                "value": "10% off medications",
                "unlocked_at": datetime.utcnow().isoformat()
            })
        
        # Special reward for maintaining green zone
        zone = state.get("clinical_recommendations", {}).get("zone", "green")
        if zone == "green" and adherence_score > 0.85:
            rewards.append({
                "type": "wellness_bonus",
                "value": "Wellness program access",
                "unlocked_at": datetime.utcnow().isoformat()
            })
        
        return rewards
    
    def _get_adherence_level(self, score: float) -> str:
        """Get adherence level description."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.75:
            return "good"
        elif score >= 0.6:
            return "moderate"
        else:
            return "needs_improvement"
    
    def _load_adherence_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Load adherence history from S3."""
        try:
            history_data = self.s3_client.download_json(f"patients/{patient_id}/adherence_history.json")
            if history_data:
                return history_data.get("history", [])
        except Exception as e:
            logger.warning(f"Failed to load adherence history: {e}")
        return []
    
    def _store_adherence_history(self, patient_id: str, score: float, points: int, state: RespiroState):
        """Store adherence history in S3."""
        try:
            history = self._load_adherence_history(patient_id)
            history.append({
                "score": score,
                "points": points,
                "zone": state.get("clinical_recommendations", {}).get("zone", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            })
            # Keep only last 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            history = [h for h in history if datetime.fromisoformat(h["timestamp"].replace("Z", "+00:00")) > cutoff_date]
            
            self.s3_client.upload_json(
                f"patients/{patient_id}/adherence_history.json",
                {"history": history, "updated_at": datetime.utcnow().isoformat()}
            )
        except Exception as e:
            logger.warning(f"Failed to store adherence history: {e}")
