"""
Callback service for sending final results to GUVI endpoint.
"""

import httpx
import logging
from typing import Optional
from ..models.schemas import SessionState, CallbackPayload
from ..config import get_settings

logger = logging.getLogger(__name__)


class CallbackService:
    """
    Handles sending final results to the GUVI evaluation endpoint.
    """
    
    def __init__(self):
        """Initialize callback service."""
        self.settings = get_settings()
        self.callback_url = self.settings.guvi_callback_url
        self.timeout = self.settings.callback_timeout
    
    def _build_payload(self, session: SessionState, agent_notes: str) -> CallbackPayload:
        """Build callback payload from session state."""
        intel = session.extractedIntelligence
        
        return CallbackPayload(
            sessionId=session.sessionId,
            scamDetected=session.scamDetected,
            totalMessagesExchanged=session.totalMessages,
            extractedIntelligence={
                "bankAccounts": intel.bankAccounts,
                "upiIds": intel.upiIds,
                "phishingLinks": intel.phishingLinks,
                "phoneNumbers": intel.phoneNumbers,
                "suspiciousKeywords": intel.suspiciousKeywords,
            },
            agentNotes=agent_notes or session.agentNotes,
        )
    
    def _print_payload_summary(self, payload: CallbackPayload):
        """Print extracted intelligence and callback payload to console."""
        import json
        
        print("\n" + "="*80)
        print("EXTRACTED INTELLIGENCE & CALLBACK PAYLOAD".center(80))
        print("="*80 + "\n")
        
        intel = payload.extractedIntelligence
        
        print(f"Session ID: {payload.sessionId}")
        print(f"Scam Detected: {payload.scamDetected}")
        print(f"Total Messages Exchanged: {payload.totalMessagesExchanged}")
        print()
        
        print("EXTRACTED INTELLIGENCE:")
        print(f"  • UPI IDs ({len(intel['upiIds'])}):")
        for upi in intel['upiIds']:
            print(f"      {upi}")
        
        print(f"  • Bank Accounts ({len(intel['bankAccounts'])}):")
        for acc in intel['bankAccounts']:
            print(f"      {acc}")
        
        print(f"  • Phishing Links ({len(intel['phishingLinks'])}):")
        for link in intel['phishingLinks']:
            print(f"      {link}")
        
        print(f"  • Phone Numbers ({len(intel['phoneNumbers'])}):")
        for phone in intel['phoneNumbers']:
            print(f"      {phone}")
        
        print(f"  • Suspicious Keywords ({len(intel['suspiciousKeywords'])}):")
        if intel['suspiciousKeywords']:
            print(f"      {', '.join(intel['suspiciousKeywords'])}")
        
        print(f"\nAgent Notes: {payload.agentNotes}")
        
        print("\nFULL CALLBACK PAYLOAD:")
        print(json.dumps(payload.model_dump(), indent=2))
        
        print("\nCallback Destination: https://hackathon.guvi.in/api/updateHoneyPotFinalResult")
        print("="*80 + "\n")
    
    async def send_callback(
        self, 
        session: SessionState, 
        agent_notes: str = ""
    ) -> tuple[bool, Optional[str]]:
        """
        Send final result callback to GUVI endpoint.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        # Check if callback already sent
        if session.callbackSent:
            logger.warning(f"Callback already sent for session {session.sessionId}")
            return False, "Callback already sent for this session"
        
        # Check if scam is confirmed
        if not session.scamDetected:
            logger.warning(f"Scam not confirmed for session {session.sessionId}")
            return False, "Cannot send callback - scam not confirmed"
        
        # Build payload
        payload = self._build_payload(session, agent_notes)
        
        # Print intelligence extraction summary and payload to console
        self._print_payload_summary(payload)
        
        logger.info(f"Sending callback for session {session.sessionId}")
        logger.debug(f"Callback payload: {payload.model_dump_json()}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.callback_url,
                    json=payload.model_dump(),
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout,
                )
                
                if response.status_code == 200:
                    logger.info(f"Callback successful for session {session.sessionId}")
                    return True, None
                else:
                    error_msg = f"Callback failed with status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return False, error_msg
                    
        except httpx.TimeoutException:
            error_msg = f"Callback timeout for session {session.sessionId}"
            logger.error(error_msg)
            return False, error_msg
        except httpx.RequestError as e:
            error_msg = f"Callback request error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected callback error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def should_send_callback(self, session: SessionState) -> bool:
        """
        Determine if callback should be sent for this session.
        
        Strategy: Balanced dual-threshold gates that prioritize intelligence gathering
        while ensuring NO confirmed scams are lost.
        
        Prerequisites:
        1. Scam must be confirmed (scamDetected = True)
        2. Callback not already sent
        
        Primary Gates (encourage longer engagement):
        A1) 3+ artifacts + 7+ messages (optimal rich intelligence)
        B1) 2+ artifacts + 12+ messages (optimal good intelligence)
        C1) 1+ artifact + 16+ messages (optimal minimal intelligence)
        
        Safety Net Gates (prevent intelligence loss):
        A2) 3+ artifacts + 5+ messages (fallback for rich intelligence)
        B2) 2+ artifacts + 10+ messages (fallback for good intelligence)
        C2) 1+ artifact + 14+ messages (fallback for minimal intelligence)
        D) Confidence (≥0.50) + 0 artifacts + 20+ messages (non-cooperative scammer)
        E) Exit: 28+ messages (hard cap for any confirmed scam)
        """
        if session.callbackSent:
            return False
        
        if not session.scamDetected:
            return False
        
        intel = session.extractedIntelligence
        
        # Count valuable artifacts (not just keywords)
        valuable_artifacts = (
            len(intel.upiIds) + 
            len(intel.bankAccounts) + 
            len(intel.phishingLinks) + 
            len(intel.phoneNumbers)
        )
        
        # PRIMARY GATES (Optimal - encourage longer engagement)
        
        # Gate A1: Rich intelligence, optimal engagement (3+ artifacts, 7+ messages)
        if valuable_artifacts >= 3 and session.totalMessages >= 7:
            logger.info(
                "Callback condition met (Gate A1 - Optimal Rich): %s artifacts, %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True

        # Gate B1: Good intelligence, optimal engagement (2+ artifacts, 12+ messages)
        if valuable_artifacts >= 2 and session.totalMessages >= 12:
            logger.info(
                "Callback condition met (Gate B1 - Optimal Good): %s artifacts, %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True

        # Gate C1: Minimal intelligence, optimal engagement (1+ artifact, 16+ messages)
        if valuable_artifacts >= 1 and session.totalMessages >= 16:
            logger.info(
                "Callback condition met (Gate C1 - Optimal Minimal): %s artifacts, %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True
        
        # SAFETY NET GATES (Fallback - prevent intelligence loss)
        
        # Gate A2: Rich intelligence, fallback (3+ artifacts, 5+ messages)
        # If scammer shares many artifacts quickly, don't lose them
        if valuable_artifacts >= 3 and session.totalMessages >= 5:
            logger.info(
                "Callback condition met (Gate A2 - Safety Rich): %s artifacts, %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True

        # Gate B2: Good intelligence, fallback (2+ artifacts, 10+ messages)
        # Catch cases where scammer stops after sharing 2 artifacts
        if valuable_artifacts >= 2 and session.totalMessages >= 10:
            logger.info(
                "Callback condition met (Gate B2 - Safety Good): %s artifacts, %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True

        # Gate C2: Minimal intelligence, fallback (1+ artifact, 14+ messages)
        # Ensure single-artifact scams aren't lost
        if valuable_artifacts >= 1 and session.totalMessages >= 14:
            logger.info(
                "Callback condition met (Gate C2 - Safety Minimal): %s artifacts, %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True

        # Gate D: High-confidence scam with no artifacts (20+ messages, confidence ≥0.50)
        # Scammer refuses to cooperate but confidence is moderate or higher
        if valuable_artifacts == 0 and session.totalMessages >= 20:
            if session.scamConfidenceScore >= 0.50:
                logger.info(
                    "Callback condition met (Gate D - Moderate Confidence): %s artifacts, %s messages, confidence=%.2f",
                    valuable_artifacts,
                    session.totalMessages,
                    session.scamConfidenceScore,
                )
                return True

        # Gate E: Exit condition (28+ messages)
        # Hard cap - force callback for any confirmed scam to prevent infinite loop
        if session.totalMessages >= 28:
            logger.info(
                "Callback condition met (Gate E - Exit): %s artifacts, %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True
        
        return False
