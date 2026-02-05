"""
Confidence-aware risk aggregator for robust scam detection.

This service combines ML predictions, rule-based signals, and intent scoring
using a weighted decision mechanism. ML is the primary authority when confident,
while rules and intent act as fallback safety nets for uncertain predictions.
"""

import logging
from typing import Tuple, Dict, Optional
from enum import Enum

from ..models.schemas import Message
from .scam_detector_hybrid import ScamDetector
from .intent_scorer import IntentScorer

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk assessment categories."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    SCAM = "scam"


class ConfidenceLevel(str, Enum):
    """ML confidence levels."""
    HIGH = "high"        # >= 0.7
    MEDIUM = "medium"    # 0.5 - 0.7
    LOW = "low"          # < 0.5


class RiskAggregator:
    """
    Confidence-aware risk aggregation service.

    Combines signals from:
    - ML model predictions (with confidence awareness)
    - Rule-based pattern matching
    - Intent-based NLP scoring

    Decision logic:
    1. High-confidence ML (>= 0.7): ML decision is trusted
    2. Medium-confidence ML (0.5-0.7): ML + intent/rules weighted
    3. Low-confidence ML (< 0.5): Rules + intent compensate
    """

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    MEDIUM_CONFIDENCE_THRESHOLD = 0.5

    # ML weights by confidence level
    WEIGHTS = {
        "high_confidence": {
            "ml": 0.85,
            "rules": 0.10,
            "intent": 0.05,
        },
        "medium_confidence": {
            "ml": 0.60,
            "rules": 0.20,
            "intent": 0.20,
        },
        "low_confidence": {
            "ml": 0.35,
            "rules": 0.35,
            "intent": 0.30,
        }
    }

    # Risk thresholds for final decision
    SCAM_THRESHOLD = 0.51
    SUSPICIOUS_THRESHOLD = 0.35

    def __init__(self):
        """Initialize risk aggregator with required services."""
        self.scam_detector = ScamDetector()
        self.intent_scorer = IntentScorer()

    def _determine_confidence_level(self, ml_confidence: float) -> ConfidenceLevel:
        """Determine confidence level from ML score."""
        if ml_confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return ConfidenceLevel.HIGH
        elif ml_confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _get_weights(self, confidence_level: ConfidenceLevel) -> Dict[str, float]:
        """Get aggregation weights based on confidence level."""
        if confidence_level == ConfidenceLevel.HIGH:
            return self.WEIGHTS["high_confidence"]
        elif confidence_level == ConfidenceLevel.MEDIUM:
            return self.WEIGHTS["medium_confidence"]
        else:
            return self.WEIGHTS["low_confidence"]

    def _determine_risk_level(self, aggregated_score: float) -> RiskLevel:
        """Convert aggregated score to risk level."""
        if aggregated_score >= self.SCAM_THRESHOLD:
            return RiskLevel.SCAM
        elif aggregated_score >= self.SUSPICIOUS_THRESHOLD:
            return RiskLevel.SUSPICIOUS
        else:
            return RiskLevel.SAFE

    def analyze_message(
        self,
        message: Message,
        ml_prediction: Optional[Dict] = None
    ) -> Tuple[RiskLevel, float, Dict]:
        """
        Analyze a message using confidence-aware risk aggregation.

        Args:
            message: Message object to analyze
            ml_prediction: Optional ML prediction dict with 'label' and 'confidence'
                          If not provided, will use internal ML model

        Returns:
            Tuple of (risk_level, confidence_score, explanation_dict)
        """
        text = message.text

        # 1. Get ML prediction
        if ml_prediction is None:
            # Use internal rule-based ScamDetector as ML fallback
            rule_score, rule_keywords = self.scam_detector.analyze_message(message)
            ml_score = rule_score
            ml_label = "possible_scam" if ml_score >= 0.5 else "not_scam"
        else:
            ml_label = ml_prediction.get("label", "not_scam")
            ml_score = ml_prediction.get("confidence", 0.0)

        # Convert ML label to score if needed
        if ml_label == "possible_scam" or ml_label == "scam":
            ml_risk_score = ml_score
        else:
            # For "not_scam", invert the confidence
            # High confidence "not_scam" = low risk score
            ml_risk_score = 1.0 - ml_score if ml_score > 0.5 else 0.2

        # 2. Get rule-based score
        rule_score, rule_keywords = self.scam_detector.analyze_message(message)

        # 3. Get intent score
        intent_score, intent_details = self.intent_scorer.calculate_intent_score(text)

        # 4. Determine confidence level
        confidence_level = self._determine_confidence_level(ml_score)

        # 5. Get weights based on confidence
        weights = self._get_weights(confidence_level)

        # 6. Calculate weighted aggregated score
        aggregated_score = (
            weights["ml"] * ml_risk_score +
            weights["rules"] * rule_score +
            weights["intent"] * intent_score
        )

        # Cap at 1.0
        aggregated_score = min(aggregated_score, 1.0)

        # 7. Determine final risk level
        risk_level = self._determine_risk_level(aggregated_score)

        # 8. Build explanation
        explanation = {
            "risk_level": risk_level.value,
            "aggregated_score": round(aggregated_score, 4),
            "confidence_level": confidence_level.value,
            "signals": {
                "ml": {
                    "score": round(ml_risk_score, 4),
                    "confidence": round(ml_score, 4),
                    "label": ml_label,
                    "weight": weights["ml"],
                    "weighted_contribution": round(weights["ml"] * ml_risk_score, 4),
                },
                "rules": {
                    "score": round(rule_score, 4),
                    "keywords": rule_keywords[:10],  # limit for readability
                    "weight": weights["rules"],
                    "weighted_contribution": round(weights["rules"] * rule_score, 4),
                },
                "intent": {
                    "score": round(intent_score, 4),
                    "details": intent_details,
                    "weight": weights["intent"],
                    "weighted_contribution": round(weights["intent"] * intent_score, 4),
                }
            },
            "decision_logic": self._explain_decision(
                confidence_level, ml_score, rule_score, intent_score, risk_level
            )
        }

        # Log decision for debugging
        logger.info(
            f"RiskAggregator: text='{text[:100]}...' "
            f"risk={risk_level.value} score={aggregated_score:.4f} "
            f"ml_conf={confidence_level.value} ml={ml_risk_score:.4f} "
            f"rules={rule_score:.4f} intent={intent_score:.4f}"
        )

        return risk_level, aggregated_score, explanation

    def _explain_decision(
        self,
        confidence_level: ConfidenceLevel,
        ml_score: float,
        rule_score: float,
        intent_score: float,
        risk_level: RiskLevel
    ) -> str:
        """Generate human-readable explanation of the decision."""
        explanations = []

        # Confidence explanation
        if confidence_level == ConfidenceLevel.HIGH:
            explanations.append(
                f"ML model is highly confident ({ml_score:.2f}), so its prediction is trusted as primary signal."
            )
        elif confidence_level == ConfidenceLevel.MEDIUM:
            explanations.append(
                f"ML model has medium confidence ({ml_score:.2f}), so decision combines ML with rules and intent analysis."
            )
        else:
            explanations.append(
                f"ML model has low confidence ({ml_score:.2f}), so rules and intent-based detection compensate heavily."
            )

        # Signal contributions
        if rule_score >= 0.5:
            explanations.append(
                f"Rule-based patterns detected strong scam signals (score: {rule_score:.2f})."
            )

        if intent_score >= 0.5:
            explanations.append(
                f"Intent analysis detected high-risk scam patterns (score: {intent_score:.2f})."
            )

        # Risk level explanation
        if risk_level == RiskLevel.SCAM:
            explanations.append("Final assessment: HIGH RISK - Classified as scam.")
        elif risk_level == RiskLevel.SUSPICIOUS:
            explanations.append("Final assessment: MODERATE RISK - Flagged as suspicious for monitoring.")
        else:
            explanations.append("Final assessment: LOW RISK - Appears safe.")

        return " ".join(explanations)

    def analyze_session(
        self,
        messages: list,
        ml_predictions: Optional[list] = None
    ) -> Tuple[RiskLevel, float, Dict]:
        """
        Analyze entire conversation session.

        Args:
            messages: List of Message objects
            ml_predictions: Optional list of ML predictions matching messages

        Returns:
            Tuple of (risk_level, confidence_score, explanation_dict)
        """
        if not messages:
            return RiskLevel.SAFE, 0.0, {"error": "No messages to analyze"}

        # Analyze each message
        results = []
        for i, msg in enumerate(messages):
            if msg.sender.lower() == "scammer":
                ml_pred = ml_predictions[i] if ml_predictions and i < len(ml_predictions) else None
                risk_level, score, explanation = self.analyze_message(msg, ml_pred)
                results.append({
                    "message": msg.text[:100],
                    "risk_level": risk_level,
                    "score": score,
                    "explanation": explanation
                })

        if not results:
            return RiskLevel.SAFE, 0.0, {"error": "No scammer messages found"}

        # Aggregate session risk
        avg_score = sum(r["score"] for r in results) / len(results)
        max_score = max(r["score"] for r in results)

        # Session score: weighted average + escalation bonus
        # If any message is very high risk, escalate session risk
        session_score = avg_score * 0.7 + max_score * 0.3

        # Diversity bonus: multiple different scam patterns increase risk
        unique_risk_levels = len(set(r["risk_level"] for r in results))
        if unique_risk_levels > 1:
            session_score = min(session_score + 0.05, 1.0)

        # Determine session risk level
        session_risk = self._determine_risk_level(session_score)

        # Build session explanation
        session_explanation = {
            "session_risk_level": session_risk.value,
            "session_score": round(session_score, 4),
            "message_count": len(results),
            "average_score": round(avg_score, 4),
            "max_score": round(max_score, 4),
            "messages": results
        }

        logger.info(
            f"Session analysis: risk={session_risk.value} "
            f"score={session_score:.4f} messages={len(results)}"
        )

        return session_risk, session_score, session_explanation

    def should_engage(self, risk_level: RiskLevel, score: float) -> bool:
        """
        Determine if honeypot should engage with this conversation.

        Args:
            risk_level: Assessed risk level
            score: Confidence score

        Returns:
            True if should engage (scam or suspicious)
        """
        # Engage with scam or suspicious conversations
        return risk_level in [RiskLevel.SCAM, RiskLevel.SUSPICIOUS]

    def get_engagement_strategy(self, risk_level: RiskLevel, score: float) -> str:
        """
        Get recommended engagement strategy based on risk assessment.

        Args:
            risk_level: Assessed risk level
            score: Confidence score

        Returns:
            Strategy string for agent behavior
        """
        if risk_level == RiskLevel.SCAM and score >= 0.8:
            return "aggressive_engagement"  # High confidence scam - fully engage
        elif risk_level == RiskLevel.SCAM:
            return "cautious_engagement"  # Scam but not totally certain
        elif risk_level == RiskLevel.SUSPICIOUS:
            return "probing_engagement"  # Ask questions to gather more intel
        else:
            return "minimal_engagement"  # Low risk - minimal response
