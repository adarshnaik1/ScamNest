"""
Session management service using simple in-memory storage.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from ..models.schemas import SessionState, Message, Metadata, ExtractedIntelligence


# Global session store - simple dict
_sessions: Dict[str, SessionState] = {}

# Velocity tracking: session_id → list of message timestamps
_velocity_tracker: Dict[str, List[datetime]] = {}


class SessionService:
    """
    Simple in-memory session management with velocity tracking.

    Features:
    - Session CRUD operations
    - Message history tracking
    - Velocity/rate limit detection
    - Contextual risk signals
    """

    # Velocity thresholds
    VELOCITY_WINDOW_MINUTES = 5
    VELOCITY_THRESHOLD = 10  # Max messages in window
    BURST_WINDOW_SECONDS = 30
    BURST_THRESHOLD = 5  # Max messages in burst window

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session by ID."""
        return _sessions.get(session_id)

    def create_session(self, session_id: str, metadata: Optional[Metadata] = None) -> SessionState:
        """Create a new session."""
        session = SessionState(sessionId=session_id, metadata=metadata)
        _sessions[session_id] = session
        return session

    def get_or_create_session(self, session_id: str, metadata: Optional[Metadata] = None) -> SessionState:
        """Get existing session or create new one."""
        return self.get_session(session_id) or self.create_session(session_id, metadata)

    def update_session(self, session: SessionState) -> SessionState:
        """Update session state."""
        session.updatedAt = datetime.utcnow().isoformat()
        _sessions[session.sessionId] = session
        return session

    def add_message(self, session_id: str, message: Message) -> SessionState:
        """Add a message to session history."""
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        session.messages.append(message)
        session.totalMessages += 1
        return self.update_session(session)

    def update_scam_status(self, session_id: str, suspected: bool = False, detected: bool = False, confidence: float = 0.0) -> SessionState:
        """Update scam detection status."""
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        session.scamSuspected = suspected or session.scamSuspected
        session.scamDetected = detected or session.scamDetected
        session.scamConfidenceScore = max(confidence, session.scamConfidenceScore)
        return self.update_session(session)

    def update_intelligence(self, session_id: str, intelligence: ExtractedIntelligence) -> SessionState:
        """Update extracted intelligence."""
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        session.extractedIntelligence = session.extractedIntelligence.merge(intelligence)
        return self.update_session(session)

    def mark_callback_sent(self, session_id: str, notes: str = "") -> SessionState:
        """Mark callback as sent for session."""
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        session.callbackSent = True
        if notes:
            session.agentNotes = notes
        return self.update_session(session)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in _sessions:
            del _sessions[session_id]
            # Clean up velocity tracking
            if session_id in _velocity_tracker:
                del _velocity_tracker[session_id]
            return True
        return False

    def track_message_velocity(self, session_id: str) -> None:
        """
        Track message timestamp for velocity detection.

        Args:
            session_id: Session identifier
        """
        now = datetime.utcnow()

        if session_id not in _velocity_tracker:
            _velocity_tracker[session_id] = []

        # Add current timestamp
        _velocity_tracker[session_id].append(now)

        # Clean up old timestamps (outside velocity window)
        cutoff = now - timedelta(minutes=self.VELOCITY_WINDOW_MINUTES)
        _velocity_tracker[session_id] = [
            ts for ts in _velocity_tracker[session_id] if ts > cutoff
        ]

    def check_velocity_violation(self, session_id: str) -> Dict[str, Any]:
        """
        Check if session has suspicious velocity patterns.

        Detects:
        - Too many messages in time window (sustained rate)
        - Burst patterns (many messages very quickly)

        Args:
            session_id: Session identifier

        Returns:
            Dict with violation status and details
        """
        if session_id not in _velocity_tracker:
            return {"violation": False, "reason": None, "count": 0}

        now = datetime.utcnow()
        timestamps = _velocity_tracker[session_id]

        # Check sustained velocity (messages in window)
        window_cutoff = now - timedelta(minutes=self.VELOCITY_WINDOW_MINUTES)
        window_count = sum(1 for ts in timestamps if ts > window_cutoff)

        if window_count > self.VELOCITY_THRESHOLD:
            return {
                "violation": True,
                "reason": "sustained_high_velocity",
                "count": window_count,
                "threshold": self.VELOCITY_THRESHOLD,
                "window_minutes": self.VELOCITY_WINDOW_MINUTES,
            }

        # Check burst pattern (messages in short burst)
        burst_cutoff = now - timedelta(seconds=self.BURST_WINDOW_SECONDS)
        burst_count = sum(1 for ts in timestamps if ts > burst_cutoff)

        if burst_count > self.BURST_THRESHOLD:
            return {
                "violation": True,
                "reason": "burst_pattern",
                "count": burst_count,
                "threshold": self.BURST_THRESHOLD,
                "window_seconds": self.BURST_WINDOW_SECONDS,
            }

        return {
            "violation": False,
            "reason": None,
            "count": window_count,
        }

    def get_contextual_signals(self, session_id: str) -> Dict[str, Any]:
        """
        Get contextual risk signals for a session.

        Contextual signals help detect scam patterns:
        - New session + financial request = higher risk
        - Repeated identical messages = bot/spam
        - Velocity violations = suspicious activity

        Args:
            session_id: Session identifier

        Returns:
            Dict with contextual risk signals
        """
        session = self.get_session(session_id)
        if not session:
            return {"error": "session_not_found"}

        # Check velocity
        velocity = self.check_velocity_violation(session_id)

        # Check if new session (low message count)
        is_new_session = session.totalMessages <= 3

        # Check for repeated messages
        message_texts = [msg.text.lower() for msg in session.messages]
        unique_messages = len(set(message_texts))
        repetition_ratio = unique_messages / max(len(message_texts), 1)
        has_repetition = repetition_ratio < 0.5 and len(message_texts) > 2

        # Check for financial keywords in early messages
        financial_keywords = ['upi', 'bank', 'account', 'card', 'payment', 'transfer']
        early_financial = False
        if session.totalMessages <= 3:
            for msg in session.messages[:3]:
                if any(kw in msg.text.lower() for kw in financial_keywords):
                    early_financial = True
                    break

        return {
            "velocity_violation": velocity["violation"],
            "velocity_details": velocity,
            "is_new_session": is_new_session,
            "early_financial_request": early_financial,
            "has_message_repetition": has_repetition,
            "repetition_ratio": round(repetition_ratio, 2),
            "total_messages": session.totalMessages,
            "unique_messages": unique_messages,
        }
