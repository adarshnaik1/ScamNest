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
        
        Strategy: Multiple escalating gates based on artifact count and message count.
        
        Conditions:
        1. Scam must be confirmed (scamDetected = True)
        2. Callback not already sent
        3. EITHER:
            a) Minimum 3 valuable artifacts AND minimum 8 messages
            b) Minimum 2 valuable artifacts AND minimum 16 messages
            c) Minimum 1 valuable artifact AND minimum 22 messages
            d) Minimum 1 valuable artifact AND minimum 28 messages
            e) Exit condition: 32+ messages
            f) Safety net: ANY artifact + 10+ messages (ensures confirmed scams are reported)
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
        
        # Gate A: More aggressive for hackathon evaluation
        if valuable_artifacts >= 2 and session.totalMessages >= 3:
            logger.info(
                "Callback condition met (Gate A): %s artifacts and %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True

        # Gate B: Backup for edge cases
        if valuable_artifacts >= 1 and session.totalMessages >= 6:
            logger.info(
                "Callback condition met (Gate B): %s artifacts and %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True

        # Safety cap: reduced to 20 messages for faster evaluation
        if session.totalMessages >= 20:
            logger.info(
                "Callback condition met (Gate C): %s artifacts and %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True

        # Gate B: 2+ artifacts + 16+ messages
        if valuable_artifacts >= 2 and session.totalMessages >= 16:
            logger.info(
                "Callback condition met (Gate B): %s artifacts and %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True

        # Gate A: 3+ artifacts + 8+ messages
        if valuable_artifacts >= 3 and session.totalMessages >= 8:
            logger.info(
                "Callback condition met (Gate A): %s artifacts and %s messages",
                valuable_artifacts,
                session.totalMessages,
            )
            return True
        
        # Safety net: If scam is confirmed and we have ANY artifact, send callback after 10 messages
        # This ensures we don't lose confirmed scams just because scammer stopped responding
        if valuable_artifacts >= 1 and session.totalMessages >= 10:
            logger.info(
                "Callback condition met (Safety net): %s artifacts and %s messages (scam confirmed)",
                valuable_artifacts,
                session.totalMessages,
            )
            return True
        
        return False
