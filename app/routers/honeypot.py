"""
Main honeypot API router for handling scam messages.
"""

import logging
from fastapi import APIRouter, Depends, BackgroundTasks
from datetime import datetime

from ..models.schemas import (
    MessageRequest, 
    MessageResponse, 
    Message,
    SessionState,
)
from ..services.session_service import SessionService
from ..services.scam_detector import ScamDetector
from ..services.intelligence_extractor import IntelligenceExtractor
from ..services.agent_service import AgentService
from ..services.callback_service import CallbackService
from ..services.translator import Translator
from ..middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Honeypot"])

# Initialize services
session_service = SessionService()
scam_detector = ScamDetector()
intelligence_extractor = IntelligenceExtractor()
agent_service = AgentService()
callback_service = CallbackService()
Translate_service= Translator()

async def process_callback(session: SessionState, agent_notes: str):
    """Background task to send callback."""
    success, error = await callback_service.send_callback(session, agent_notes)
    if success:
        session_service.mark_callback_sent(session.sessionId, agent_notes)
        logger.info(f"Callback sent successfully for session {session.sessionId}")
    else:
        logger.error(f"Callback failed for session {session.sessionId}: {error}")


@router.post("/honeypot", response_model=MessageResponse)
async def handle_message(
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
) -> MessageResponse:
    """
    Handle incoming scam message and return agent response.
    
    This endpoint:
    1. Authenticates the request via API key
    2. Loads or creates session state
    3. Analyzes message for scam patterns
    4. Extracts intelligence from message
    5. Generates human-like agent response
    6. Updates session state
    7. Triggers callback if scam is confirmed
    
    Args:
        request: Incoming message request
        background_tasks: FastAPI background tasks for callback
        api_key: Validated API key
        
    Returns:
        MessageResponse with agent reply
    """
    logger.info(f"Received message for session {request.sessionId}")
    
    # Step 1: Get or create session
    session = session_service.get_or_create_session(
        request.sessionId,
        request.metadata
    )
    
    # Step 2: Add incoming message to session
    session = session_service.add_message(request.sessionId, request.message)
    
    # Add conversation history if provided (for first message reconstruction)
    if request.conversationHistory and session.totalMessages == 1:
        for hist_msg in request.conversationHistory:
            if hist_msg not in session.messages:
                session.messages.insert(-1, hist_msg)
                session.totalMessages += 1
        session = session_service.update_session(session)

    # Step 3: Translate and analyze for scam patterns
    if request.message.sender.lower() == "scammer":
        try:
            translated_text = Translate_service.translate(request.message.text)
            request.message.text = translated_text
            # Update the message in session history so detector sees English
            session.messages[-1].text = translated_text
            logger.info(f"Translated message to English for detection: {translated_text}")
        except Exception as e:
            logger.error(f"Translation failed: {e}")

    confidence, suspected, confirmed, keywords = scam_detector.analyze_session(session)
    session = session_service.update_scam_status(
        request.sessionId,
        suspected=suspected,
        detected=confirmed,
        confidence=confidence,
    )
    
    logger.info(
        f"Session {request.sessionId}: confidence={confidence:.2f}, "
        f"suspected={suspected}, confirmed={confirmed}"
    )
    
    # Step 4: Extract intelligence
    intelligence = intelligence_extractor.extract_from_message(request.message)
    if not intelligence.is_empty():
        # Merge with existing intelligence
        intelligence = session.extractedIntelligence.merge(intelligence)
        session = session_service.update_intelligence(request.sessionId, intelligence)
        logger.info(f"Extracted intelligence: {intelligence.model_dump()}")
    
    # Step 5: Generate agent response
    reply = agent_service.generate_response(session, request.message)
    
    # Add agent response to session
    agent_message = Message(
        sender="user",
        text=reply,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
    session = session_service.add_message(request.sessionId, agent_message)
    
    # Step 6: Check if callback should be sent
    if callback_service.should_send_callback(session):
        # Generate agent notes
        scam_type = scam_detector.get_scam_type(
            session.extractedIntelligence.suspiciousKeywords
        )
        agent_notes = intelligence_extractor.generate_agent_notes(session, scam_type)
        
        # Send callback in background
        background_tasks.add_task(process_callback, session, agent_notes)
        logger.info(f"Callback scheduled for session {request.sessionId}")
    
    return MessageResponse(
        status="success",
        reply=reply,
    )


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    Get session state (for debugging/monitoring).
    
    Args:
        session_id: Session identifier
        api_key: Validated API key
        
    Returns:
        Session state dict
    """
    session = session_service.get_session(session_id)
    if session is None:
        return {"status": "error", "detail": "Session not found"}
    
    return {
        "status": "success",
        "session": session.model_dump(),
    }


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    Delete a session (for cleanup/testing).
    
    Args:
        session_id: Session identifier
        api_key: Validated API key
        
    Returns:
        Status message
    """
    success = session_service.delete_session(session_id)
    if success:
        return {"status": "success", "detail": "Session deleted"}
    return {"status": "error", "detail": "Session not found"}
