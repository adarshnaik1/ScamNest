"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime
from enum import Enum


class SenderType(str, Enum):
    """Enum for message sender types."""
    SCAMMER = "scammer"
    USER = "user"


class ChannelType(str, Enum):
    """Enum for communication channels."""
    SMS = "SMS"
    WHATSAPP = "WhatsApp"
    EMAIL = "Email"
    CHAT = "Chat"


class RiskLevel(str, Enum):
    """Enum for risk assessment levels."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    SCAM = "scam"


class ConfidenceLevel(str, Enum):
    """Enum for ML confidence levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Message(BaseModel):
    """Schema for a single message."""
    sender: str = Field(..., description="Either 'scammer' or 'user'")
    text: str = Field(..., description="Message content")
    timestamp: Union[str, int] = Field(..., description="ISO-8601 string or Unix timestamp in milliseconds")
    
    @field_validator('timestamp')
    @classmethod
    def convert_timestamp(cls, v):
        """Convert Unix timestamp (int) to ISO-8601 string if needed."""
        if isinstance(v, int):
            # Convert Unix timestamp in milliseconds to ISO-8601
            dt = datetime.fromtimestamp(v / 1000.0)
            return dt.isoformat() + "Z"
        return v


class Metadata(BaseModel):
    """Schema for message metadata."""
    channel: Optional[str] = Field(default="SMS", description="Communication channel")
    language: Optional[str] = Field(default="English", description="Language used")
    locale: Optional[str] = Field(default="IN", description="Country or region")


class MessageRequest(BaseModel):
    """Schema for incoming message request."""
    sessionId: str = Field(..., description="Unique identifier for a conversation")
    message: Message = Field(..., description="Latest incoming message")
    conversationHistory: Optional[List[Message]] = Field(
        default=[],
        description="Previous messages in this session"
    )
    metadata: Optional[Metadata] = Field(
        default=None,
        description="Contextual information"
    )


class MessageResponse(BaseModel):
    """Schema for agent response."""
    status: str = Field(default="success", description="Response status")
    reply: str = Field(..., description="Agent-generated response")


class ExtractedIntelligence(BaseModel):
    """Schema for extracted scam intelligence."""
    bankAccounts: List[str] = Field(default_factory=list)
    upiIds: List[str] = Field(default_factory=list)
    phishingLinks: List[str] = Field(default_factory=list)
    phoneNumbers: List[str] = Field(default_factory=list)
    suspiciousKeywords: List[str] = Field(default_factory=list)

    def merge(self, other: "ExtractedIntelligence") -> "ExtractedIntelligence":
        """Merge intelligence from another extraction."""
        return ExtractedIntelligence(
            bankAccounts=list(set(self.bankAccounts + other.bankAccounts)),
            upiIds=list(set(self.upiIds + other.upiIds)),
            phishingLinks=list(set(self.phishingLinks + other.phishingLinks)),
            phoneNumbers=list(set(self.phoneNumbers + other.phoneNumbers)),
            suspiciousKeywords=list(set(self.suspiciousKeywords + other.suspiciousKeywords)),
        )

    def is_empty(self) -> bool:
        """Check if no intelligence has been extracted."""
        return not any([
            self.bankAccounts,
            self.upiIds,
            self.phishingLinks,
            self.phoneNumbers,
            self.suspiciousKeywords,
        ])


class SessionState(BaseModel):
    """Schema for session state."""
    sessionId: str
    messages: List[Message] = Field(default_factory=list)
    scamDetected: bool = False
    scamSuspected: bool = False
    scamConfidenceScore: float = 0.0
    extractedIntelligence: ExtractedIntelligence = Field(
        default_factory=ExtractedIntelligence
    )
    totalMessages: int = 0
    callbackSent: bool = False
    agentNotes: str = ""
    metadata: Optional[Metadata] = None
    createdAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    preliminaryIntent: Optional[str] = None
    preliminaryConfidence: float = 0.0
    llmEngaged: bool = False

    # Enhanced fields for confidence-aware detection
    riskLevel: Optional[str] = Field(default="safe", description="Risk level: safe, suspicious, or scam")
    mlConfidenceLevel: Optional[str] = Field(default=None, description="ML confidence: high, medium, or low")
    decisionExplanation: Optional[dict] = Field(default=None, description="Detailed decision breakdown")
    intentScore: Optional[float] = Field(default=0.0, description="Intent-based risk score")
    ruleScore: Optional[float] = Field(default=0.0, description="Rule-based risk score")


class CallbackPayload(BaseModel):
    """Schema for GUVI callback payload."""
    sessionId: str
    scamDetected: bool
    totalMessagesExchanged: int
    extractedIntelligence: dict
    agentNotes: str
