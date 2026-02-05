"""
LLM-based scam validation and analysis service.

Provides three modes:
1. Single message validation (for SUSPICIOUS cases)
2. Explanation generation (for agentNotes)
3. Multi-turn pattern analysis (for conversation flow)
"""

import logging
from typing import Optional, Dict, List, Tuple
from ..models.schemas import Message, SessionState
from ..config import get_settings

logger = logging.getLogger(__name__)


class LLMScamValidator:
    """
    Uses LLM to validate scam detection and provide detailed analysis.
    """

    def __init__(self):
        """Initialize LLM validator service."""
        self.settings = get_settings()
        self._openai_client = None

    def _get_openai_client(self):
        """Lazily initialize OpenAI client."""
        if self._openai_client is None and self.settings.openai_api_key:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.settings.openai_api_key)
                logger.info("OpenAI client initialized for LLM scam validation")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
        return self._openai_client

    def is_available(self) -> bool:
        """Check if LLM validation is available."""
        return self._get_openai_client() is not None

    async def validate_suspicious_message(
        self,
        message_text: str,
        current_risk_score: float,
        ml_confidence: str,
        rule_keywords: List[str]
    ) -> Tuple[str, float, str]:
        """
        Validate a SUSPICIOUS message using LLM.

        Args:
            message_text: The message to analyze
            current_risk_score: Current aggregated risk score
            ml_confidence: ML confidence level (high/medium/low)
            rule_keywords: Keywords matched by rules

        Returns:
            Tuple of (final_decision, adjusted_score, reasoning)
            final_decision: "safe", "suspicious", or "scam"
            adjusted_score: LLM-adjusted risk score (0.0-1.0)
            reasoning: Natural language explanation
        """
        client = self._get_openai_client()
        if not client:
            logger.warning("LLM validation not available, using current decision")
            return "suspicious", current_risk_score, "LLM unavailable"

        try:
            system_prompt = """You are an expert scam detection analyst. Analyze messages for scam indicators.

Scam indicators include:
- Financial requests (UPI, bank accounts, money transfers)
- Urgency and threats (account blocked, suspended, legal action)
- Authority impersonation (bank, police, government)
- Request for sensitive data (OTP, PIN, password, CVV)
- Phishing links or suspicious URLs
- Coercion and manipulation tactics

Provide:
1. Decision: "safe", "suspicious", or "scam"
2. Confidence score: 0.0 (definitely safe) to 1.0 (definitely scam)
3. Reasoning: Brief explanation (2-3 sentences)

Be conservative: mark as "suspicious" if uncertain."""

            user_prompt = f"""Analyze this message:

MESSAGE: "{message_text}"

CONTEXT:
- Current ML confidence: {ml_confidence}
- Current risk score: {current_risk_score:.2f}
- Rule-based keywords: {', '.join(rule_keywords) if rule_keywords else 'none'}

Provide your analysis in this format:
DECISION: [safe/suspicious/scam]
SCORE: [0.0-1.0]
REASONING: [your explanation]"""

            response = client.chat.completions.create(
                model=self.settings.llm_detection_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,
                temperature=0.3,  # Lower temperature for more consistent detection
                timeout=self.settings.llm_detection_timeout,
            )

            if not response.choices[0].message.content:
                raise ValueError("Empty LLM response")

            result = response.choices[0].message.content.strip()

            # Parse LLM response
            decision = "suspicious"  # default
            score = current_risk_score  # default
            reasoning = result

            for line in result.split('\n'):
                line = line.strip()
                if line.startswith("DECISION:"):
                    decision = line.split(":", 1)[1].strip().lower()
                elif line.startswith("SCORE:"):
                    try:
                        score = float(line.split(":", 1)[1].strip())
                        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                    except ValueError:
                        pass
                elif line.startswith("REASONING:"):
                    reasoning = line.split(":", 1)[1].strip()

            # Ensure decision is valid
            if decision not in ["safe", "suspicious", "scam"]:
                decision = "suspicious"

            logger.info(
                f"LLM validation: decision={decision}, score={score:.2f}, "
                f"original_score={current_risk_score:.2f}"
            )

            return decision, score, reasoning

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return "suspicious", current_risk_score, f"LLM error: {str(e)}"

    async def generate_explanation(
        self,
        session: SessionState,
        scam_type: str,
        intelligence_summary: str
    ) -> str:
        """
        Generate detailed explanation for agentNotes using LLM.

        Args:
            session: Current session state
            scam_type: Detected scam type
            intelligence_summary: Summary of extracted intelligence

        Returns:
            Natural language explanation for agentNotes
        """
        client = self._get_openai_client()
        if not client:
            # Fallback to basic template
            return f"Scam type: {scam_type}. {intelligence_summary}"

        try:
            # Build conversation summary
            conversation = "\n".join([
                f"{'Scammer' if msg.sender.lower() == 'scammer' else 'Agent'}: {msg.text}"
                for msg in session.messages[-10:]  # Last 10 messages
            ])

            system_prompt = """You are a fraud analyst writing a brief scam report.
Summarize the scam attempt in 2-3 sentences for law enforcement.

Focus on:
- Scam tactics used
- Intelligence gathered (UPI, phone, links)
- Manipulation techniques
- Risk level

Be concise and professional."""

            user_prompt = f"""Conversation:
{conversation}

Scam Type: {scam_type}
Intelligence: {intelligence_summary}
Risk Level: {session.riskLevel}
Confidence Score: {session.scamConfidenceScore:.2f}

Write a brief scam report (2-3 sentences)."""

            response = client.chat.completions.create(
                model=self.settings.llm_detection_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.5,
                timeout=self.settings.llm_detection_timeout,
            )

            if response.choices[0].message.content:
                explanation = response.choices[0].message.content.strip()
                logger.info("LLM-generated explanation created")
                return explanation

            # Fallback
            return f"Scam type: {scam_type}. {intelligence_summary}"

        except Exception as e:
            logger.error(f"LLM explanation generation failed: {e}")
            return f"Scam type: {scam_type}. {intelligence_summary}"

    async def analyze_conversation_pattern(
        self,
        messages: List[Message],
        session: SessionState
    ) -> Dict[str, any]:
        """
        Analyze multi-turn conversation for sophisticated scam patterns.

        Args:
            messages: List of conversation messages
            session: Current session state

        Returns:
            Dict with pattern analysis results
        """
        client = self._get_openai_client()
        if not client or len(messages) < 3:
            return {
                "pattern_detected": False,
                "sophistication_level": "unknown",
                "manipulation_tactics": [],
                "analysis": "Insufficient data or LLM unavailable"
            }

        try:
            # Build conversation context
            conversation = "\n".join([
                f"Message {i+1} ({'Scammer' if msg.sender.lower() == 'scammer' else 'Agent'}): {msg.text}"
                for i, msg in enumerate(messages[-10:])  # Last 10 messages
            ])

            system_prompt = """You are a behavioral analyst specializing in scam pattern detection.
Analyze conversation flow for manipulation tactics and social engineering.

Look for:
- Gradual trust building
- Escalating urgency
- Authority establishment
- Information extraction progression
- Emotional manipulation
- Consistency of story

Rate sophistication: low, medium, high"""

            user_prompt = f"""Analyze this conversation:

{conversation}

Provide analysis in this format:
PATTERN: [yes/no - is this a sophisticated scam pattern?]
SOPHISTICATION: [low/medium/high]
TACTICS: [comma-separated list of manipulation tactics used]
ANALYSIS: [2-3 sentence summary]"""

            response = client.chat.completions.create(
                model=self.settings.llm_detection_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=250,
                temperature=0.4,
                timeout=self.settings.llm_detection_timeout,
            )

            if not response.choices[0].message.content:
                raise ValueError("Empty LLM response")

            result = response.choices[0].message.content.strip()

            # Parse response
            pattern_detected = False
            sophistication = "unknown"
            tactics = []
            analysis = result

            for line in result.split('\n'):
                line = line.strip()
                if line.startswith("PATTERN:"):
                    pattern_detected = "yes" in line.lower()
                elif line.startswith("SOPHISTICATION:"):
                    soph = line.split(":", 1)[1].strip().lower()
                    if soph in ["low", "medium", "high"]:
                        sophistication = soph
                elif line.startswith("TACTICS:"):
                    tactics_str = line.split(":", 1)[1].strip()
                    tactics = [t.strip() for t in tactics_str.split(",") if t.strip()]
                elif line.startswith("ANALYSIS:"):
                    analysis = line.split(":", 1)[1].strip()

            logger.info(
                f"Conversation pattern analysis: pattern={pattern_detected}, "
                f"sophistication={sophistication}"
            )

            return {
                "pattern_detected": pattern_detected,
                "sophistication_level": sophistication,
                "manipulation_tactics": tactics,
                "analysis": analysis
            }

        except Exception as e:
            logger.error(f"LLM conversation analysis failed: {e}")
            return {
                "pattern_detected": False,
                "sophistication_level": "unknown",
                "manipulation_tactics": [],
                "analysis": f"Analysis failed: {str(e)}"
            }
