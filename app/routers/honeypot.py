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
from ..services.scam_detector_hybrid import ScamDetector as RuleAndModelScamDetector
from ..services.preliminary_model_prediction import ScamDetector as MLScamDetector
from ..services.intelligence_extractor import IntelligenceExtractor
from ..services.agent_service import AgentService
from ..services.callback_service import CallbackService
from ..services.translator import Translator
from ..services.risk_aggregator import RiskAggregator, RiskLevel
from ..services.review_queue import ReviewQueueService
from ..services.feedback_loop import FeedbackLoopService
from ..services.llm_scam_validator import LLMScamValidator
from ..services.data_masker import DataMasker, mask_for_logging
from ..middleware.auth import verify_api_key
from ..config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Honeypot"])

# Get settings
settings = get_settings()

# Initialize services
session_service = SessionService()
rule_and_model_scam_detector = RuleAndModelScamDetector()
ml_scam_detector = MLScamDetector()
intelligence_extractor = IntelligenceExtractor()
agent_service = AgentService()
callback_service = CallbackService()
Translate_service = Translator()
risk_aggregator = RiskAggregator()  # Confidence-aware risk aggregator
review_queue_service = ReviewQueueService()  # Review queue for suspicious cases
feedback_loop_service = FeedbackLoopService()  # Feedback loop for continuous learning
llm_validator = LLMScamValidator()  # LLM-based validation and analysis
data_masker = DataMasker()  # Data masking for PII protection in logs

async def process_callback(session: SessionState, agent_notes: str):
    """Background task to send callback."""
    success, error = await callback_service.send_callback(session, agent_notes)
    if success:
        session_service.mark_callback_sent(session.sessionId, agent_notes)
        logger.info(f"Callback sent successfully for session {session.sessionId}")
    else:
        logger.error(f"Callback failed for session {session.sessionId}: {error}")


@router.post("/honeypot")
async def handle_message(
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
):
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

    # Create/get session and add the incoming message first so translation
    # and analysis can update session history consistently.
    session = session_service.get_or_create_session(request.sessionId, request.metadata)
    session = session_service.add_message(request.sessionId, request.message)

    # Track velocity for rate limiting and suspicious pattern detection
    session_service.track_message_velocity(request.sessionId)

    # Add conversation history if provided (for first message reconstruction)
    if request.conversationHistory and session.totalMessages == 1:
        for hist_msg in request.conversationHistory:
            if hist_msg not in session.messages:
                session.messages.insert(-1, hist_msg)
                session.totalMessages += 1
        session = session_service.update_session(session)

    # For scammer messages: translate first, then run ML preliminary intent
    if request.message.sender.lower() == "scammer":
        try:
            translated_text = Translate_service.translate(request.message.text)
            request.message.text = translated_text
            # Update the message in session history so detector sees English
            session.messages[-1].text = translated_text
            session = session_service.update_session(session)
            logger.info(f"Translated message to English for detection: {mask_for_logging(translated_text)}")
        except Exception as e:
            logger.error(f"Translation failed: {e}")

        # Run ML-based preliminary intent on translated text
        ml_result = ml_scam_detector.is_possible_scam(request.message.text)
        label = ml_result.get("label", "not_scam")
        confidence = float(ml_result.get("confidence", 0.0))
        logger.info("preliminary scam detector output for session %s: %s", request.sessionId, ml_result)

        # Persist preliminary intent and mark LLM engagement
        session.preliminaryIntent = label  # Store actual ML prediction
        session.preliminaryConfidence = confidence
        session.llmEngaged = label == "possible_scam"  # Only engage LLM if ML flags as possible scam
        session = session_service.update_session(session)
        logger.info(f"Preliminary intent: {session.preliminaryIntent} (conf={confidence:.2f})")

    # Use new confidence-aware risk aggregation
    ml_prediction = {
        "label": session.preliminaryIntent or "not_scam",
        "confidence": session.preliminaryConfidence or 0.0
    }

    # Analyze with the new risk aggregator (single message)
    risk_level, aggregated_score, explanation = risk_aggregator.analyze_message(
        request.message,
        ml_prediction=ml_prediction
    )

    # Update session with enhanced risk assessment
    session.riskLevel = risk_level.value
    session.scamConfidenceScore = aggregated_score
    session.mlConfidenceLevel = explanation["confidence_level"]
    session.decisionExplanation = explanation
    session.intentScore = explanation["signals"]["intent"]["score"]
    session.ruleScore = explanation["signals"]["rules"]["score"]

    # Map risk level to legacy boolean fields for backward compatibility
    session.scamSuspected = risk_level in [RiskLevel.SUSPICIOUS, RiskLevel.SCAM]
    session.scamDetected = risk_level == RiskLevel.SCAM

    session = session_service.update_session(session)

    # Get contextual signals for enhanced detection
    contextual_signals = session_service.get_contextual_signals(request.sessionId)

    # Check for velocity violations (rate limiting / suspicious patterns)
    if contextual_signals.get("velocity_violation"):
        logger.warning(
            f"Velocity violation detected for session {request.sessionId}: "
            f"{contextual_signals['velocity_details']}"
        )
        # Boost risk score for velocity violations
        if aggregated_score < 0.6:
            aggregated_score = min(aggregated_score + 0.15, 1.0)
            logger.info(f"Risk score boosted to {aggregated_score:.2f} due to velocity violation")

    # OPTION 1: LLM Validation for SUSPICIOUS cases
    llm_reasoning = None
    if settings.use_llm_validation and risk_level == RiskLevel.SUSPICIOUS and llm_validator.is_available():
        logger.info(f"Running LLM validation for SUSPICIOUS case: session {request.sessionId}")
        try:
            llm_decision, llm_score, llm_reasoning = await llm_validator.validate_suspicious_message(
                message_text=request.message.text,
                current_risk_score=aggregated_score,
                ml_confidence=explanation["confidence_level"],
                rule_keywords=explanation["signals"]["rules"].get("keywords", [])
            )

            # Update risk level based on LLM decision
            if llm_decision == "scam":
                risk_level = RiskLevel.SCAM
                session.scamDetected = True
            elif llm_decision == "safe":
                risk_level = RiskLevel.SAFE
                session.scamSuspected = False

            # Use LLM-adjusted score
            aggregated_score = llm_score
            session.scamConfidenceScore = llm_score
            session.riskLevel = risk_level.value

            # Add LLM reasoning to explanation
            if explanation.get("llm_validation") is None:
                explanation["llm_validation"] = {}
            explanation["llm_validation"] = {
                "decision": llm_decision,
                "score": llm_score,
                "reasoning": llm_reasoning
            }
            session.decisionExplanation = explanation
            session = session_service.update_session(session)

            logger.info(
                f"LLM validation result: {llm_decision}, "
                f"adjusted_score={llm_score:.2f} (was {aggregated_score:.2f})"
            )
        except Exception as e:
            logger.error(f"LLM validation error: {e}")

    # OPTION 3: Multi-turn pattern analysis (if enabled and enough messages)
    pattern_analysis = None
    if (settings.use_llm_pattern_analysis and
        session.totalMessages >= settings.llm_min_messages_for_pattern_analysis and
        llm_validator.is_available()):
        logger.info(f"Running LLM pattern analysis for session {request.sessionId}")
        try:
            pattern_analysis = await llm_validator.analyze_conversation_pattern(
                messages=session.messages,
                session=session
            )

            # If sophisticated pattern detected, upgrade risk level
            if pattern_analysis.get("pattern_detected") and pattern_analysis.get("sophistication_level") in ["medium", "high"]:
                if risk_level != RiskLevel.SCAM:
                    logger.info(
                        f"Sophisticated pattern detected ({pattern_analysis['sophistication_level']}), "
                        f"upgrading risk level"
                    )
                    if risk_level == RiskLevel.SAFE:
                        risk_level = RiskLevel.SUSPICIOUS
                        session.scamSuspected = True
                    # Boost score for sophisticated patterns
                    aggregated_score = min(aggregated_score + 0.20, 1.0)
                    session.scamConfidenceScore = aggregated_score
                    session.riskLevel = risk_level.value

            # Add pattern analysis to explanation
            explanation["pattern_analysis"] = pattern_analysis
            session.decisionExplanation = explanation
            session = session_service.update_session(session)

            logger.info(
                f"Pattern analysis: sophisticated={pattern_analysis.get('sophistication_level')}, "
                f"tactics={pattern_analysis.get('manipulation_tactics', [])}"
            )
        except Exception as e:
            logger.error(f"LLM pattern analysis error: {e}")

    # Log decision to feedback loop
    feedback_loop_service.log_decision(
        session_id=request.sessionId,
        message_text=request.message.text,
        risk_level=risk_level.value,
        aggregated_score=aggregated_score,
        ml_confidence_level=explanation["confidence_level"],
        explanation=explanation,
        contextual_signals=contextual_signals,
    )

    logger.info(
        f"Session {request.sessionId}: risk_level={risk_level.value}, "
        f"score={aggregated_score:.2f}, ml_confidence={explanation['confidence_level']}"
    )

    # Add to review queue if needed
    if review_queue_service.should_queue(
        risk_level.value,
        aggregated_score,
        explanation["confidence_level"]
    ):
        review_queue_service.add_to_queue(
            session_id=request.sessionId,
            message_text=request.message.text,
            risk_level=risk_level.value,
            aggregated_score=aggregated_score,
            explanation=explanation,
            reason="automated_detection"
        )
        logger.info(f"Session {request.sessionId} added to review queue")
    # Determine scam type for display and callbacks
    scam_type = rule_and_model_scam_detector.get_scam_type(
        explanation["signals"]["rules"].get("keywords", [])
    )
    logger.info(f"Session {request.sessionId}: scam_type={scam_type}")

    # Step 4: Extract intelligence
    intelligence = intelligence_extractor.extract_from_message(request.message)
    if not intelligence.is_empty():
        # Merge with existing intelligence
        intelligence = session.extractedIntelligence.merge(intelligence)
        session = session_service.update_intelligence(request.sessionId, intelligence)
        # Mask sensitive data before logging
        masked_intel = data_masker.mask_intelligence(intelligence.model_dump())
        logger.info(f"Extracted intelligence: {masked_intel}")

    # Step 5: Generate agent response based on risk level
    # For hackathon: Always engage if scam suspected or detected to maximize intelligence extraction
    should_engage = session.scamSuspected or session.scamDetected

    logger.info(
        f"Engagement decision: should_engage={should_engage}, "
        f"scamSuspected={session.scamSuspected}, scamDetected={session.scamDetected}"
    )

    reply = agent_service.generate_response_conditional(
        session,
        request.message,
        engage_llm=bool(should_engage),
    )

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
        scam_type = rule_and_model_scam_detector.get_scam_type(
            session.extractedIntelligence.suspiciousKeywords
        )

        # OPTION 2: Use LLM for explanation generation (if enabled)
        if settings.use_llm_explanation and llm_validator.is_available():
            logger.info(f"Generating LLM-enhanced agent notes for session {request.sessionId}")
            try:
                intel = session.extractedIntelligence
                intel_summary = (
                    f"Extracted: {len(intel.upiIds)} UPI IDs, "
                    f"{len(intel.phoneNumbers)} phone numbers, "
                    f"{len(intel.phishingLinks)} phishing links, "
                    f"{len(intel.bankAccounts)} bank accounts"
                )

                agent_notes = await llm_validator.generate_explanation(
                    session=session,
                    scam_type=scam_type,
                    intelligence_summary=intel_summary
                )

                # Add pattern analysis if available
                if pattern_analysis and pattern_analysis.get("pattern_detected"):
                    agent_notes += f" Pattern analysis: {pattern_analysis.get('sophistication_level')} sophistication, tactics: {', '.join(pattern_analysis.get('manipulation_tactics', [])[:3])}"

                logger.info("LLM-generated agent notes created")
            except Exception as e:
                logger.error(f"LLM explanation generation error, using fallback: {e}")
                agent_notes = intelligence_extractor.generate_agent_notes(session, scam_type)
        else:
            # Fallback to traditional agent notes
            agent_notes = intelligence_extractor.generate_agent_notes(session, scam_type)

        # Send callback in background
        background_tasks.add_task(process_callback, session, agent_notes)
        logger.info(f"Callback scheduled for session {request.sessionId}")

    return {
        "status": "success",
        "reply": reply,
    }


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


@router.get("/review-queue")
async def get_review_queue(
    limit: int = 50,
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    Get pending items in review queue.

    Args:
        limit: Maximum number of items to return
        api_key: Validated API key

    Returns:
        Pending review items
    """
    pending = review_queue_service.get_pending_items(limit=limit)
    stats = review_queue_service.get_stats()

    return {
        "status": "success",
        "pending_items": pending,
        "stats": stats,
    }


@router.post("/review-queue/{session_id}/feedback")
async def submit_review_feedback(
    session_id: str,
    final_decision: str,
    reviewer_notes: str = "",
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    Submit human review feedback for a queued item.

    Args:
        session_id: Session identifier
        final_decision: Final decision (safe/suspicious/scam)
        reviewer_notes: Optional reviewer notes
        api_key: Validated API key

    Returns:
        Status message
    """
    # Mark as reviewed in queue
    success = review_queue_service.mark_reviewed(
        session_id=session_id,
        final_decision=final_decision,
        reviewer_notes=reviewer_notes
    )

    if not success:
        return {"status": "error", "detail": "Session not found in review queue"}

    # Add to feedback loop for learning
    feedback_loop_service.add_feedback(
        session_id=session_id,
        ground_truth_label=final_decision,
        feedback_source="human_review",
        notes=reviewer_notes
    )

    return {
        "status": "success",
        "detail": f"Feedback recorded for session {session_id}"
    }


@router.get("/feedback/stats")
async def get_feedback_stats(
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    Get feedback loop statistics.

    Args:
        api_key: Validated API key

    Returns:
        Feedback statistics
    """
    stats = feedback_loop_service.get_stats()
    patterns = feedback_loop_service.analyze_patterns()

    return {
        "status": "success",
        "stats": stats,
        "patterns": patterns,
    }


@router.get("/feedback/retraining-data")
async def get_retraining_data(
    include_correct: bool = False,
    min_score: float = 0.0,
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    Get data for model retraining.

    Args:
        include_correct: Include correctly predicted samples
        min_score: Minimum score threshold
        api_key: Validated API key

    Returns:
        Training data with ground truth labels
    """
    training_data = feedback_loop_service.get_retraining_data(
        include_correct=include_correct,
        min_score_threshold=min_score
    )

    return {
        "status": "success",
        "training_samples": len(training_data),
        "data": training_data,
    }
