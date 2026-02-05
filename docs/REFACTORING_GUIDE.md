# ScamNest Refactoring Guide

> **Purpose**: Specific, actionable recommendations for improving code quality without breaking functionality  
> **Target Audience**: Current and future maintainers  
> **Status**: Recommendations for future iterations

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Critical Improvements](#critical-improvements)
3. [Module-by-Module Recommendations](#module-by-module-recommendations)
4. [Architecture Improvements](#architecture-improvements)
5. [Testing Strategy](#testing-strategy)
6. [Performance Optimizations](#performance-optimizations)
7. [Security Enhancements](#security-enhancements)
8. [Implementation Priority](#implementation-priority)

---

## Overview

### Current State

The codebase is functional and demonstrates good architectural patterns. However, there are opportunities for improvement in:

- **Modularity**: Some files mix concerns
- **Error Handling**: Inconsistent across services
- **Configuration**: Hardcoded values in some places
- **Type Safety**: Missing type hints in several places
- **Testing**: Limited test coverage

### Refactoring Philosophy

- ✅ **Incremental**: Small, testable changes
- ✅ **Non-breaking**: Maintain backward compatibility
- ✅ **Measured**: Profile before optimizing
- ✅ **Documented**: Update docs with changes

---

## Critical Improvements

### 1. Configuration Management

**Current Issue**: Configuration scattered across files

**Recommendation**: Centralize all configuration

```python
# config/settings.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Centralized configuration with validation."""
    
    # API Settings
    API_KEY: str
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # OpenAI Settings
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 500
    OPENAI_TEMPERATURE: float = 0.7
    
    # Scam Detection
    SCAM_THRESHOLD: float = 0.8
    MIN_MESSAGES_FOR_CALLBACK: int = 3
    
    # Session Management
    SESSION_TIMEOUT_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()

# Usage in services
from config.settings import get_settings

settings = get_settings()
```

**Benefits**:
- Single source of truth
- Validated at startup
- Easy to test with overrides
- Type-safe access

---

### 2. Error Handling

**Current Issue**: Inconsistent error handling and logging

**Recommendation**: Centralized error handling with custom exceptions

```python
# app/exceptions.py
class ScamNestException(Exception):
    """Base exception for ScamNest."""
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class AuthenticationError(ScamNestException):
    """Invalid API key."""
    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message, "AUTH_ERROR")

class OpenAIError(ScamNestException):
    """OpenAI API failure."""
    def __init__(self, message: str):
        super().__init__(message, "OPENAI_ERROR")

class SessionNotFoundError(ScamNestException):
    """Session not found."""
    def __init__(self, session_id: str):
        super().__init__(f"Session {session_id} not found", "SESSION_NOT_FOUND")

# app/middleware/error_handler.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.exceptions import ScamNestException
import logging

logger = logging.getLogger(__name__)

async def scamnest_exception_handler(request: Request, exc: ScamNestException):
    """Handle custom exceptions."""
    logger.error(f"ScamNest Error: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message
            }
        }
    )

# In app/main.py
from app.exceptions import ScamNestException
from app.middleware.error_handler import scamnest_exception_handler

app.add_exception_handler(ScamNestException, scamnest_exception_handler)
```

---

### 3. Logging Strategy

**Current Issue**: Print statements and inconsistent logging

**Recommendation**: Structured logging with proper levels

```python
# config/logging_config.py
import logging
import sys
from datetime import datetime

def setup_logging(log_level: str = "INFO"):
    """Configure application logging."""
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File handler (optional)
    file_handler = logging.FileHandler(
        f'logs/scamnest_{datetime.now().strftime("%Y%m%d")}.log'
    )
    file_handler.setFormatter(formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Disable uvicorn access logs in production
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# In app/main.py
from config.logging_config import setup_logging
from config.settings import get_settings

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Usage
logger.info("Application started")
logger.debug(f"Session {session_id} created")
logger.warning("Scam confidence below threshold")
logger.error("OpenAI API failed", exc_info=True)
```

---

## Module-by-Module Recommendations

### app/services/session_service.py

**Issues**:
- In-memory dict not thread-safe
- No session expiration
- Direct dict manipulation

**Improvements**:

```python
# app/services/session_service.py
from typing import Optional, Dict
from datetime import datetime, timedelta
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class SessionService:
    """Thread-safe session management with expiration."""
    
    def __init__(self, timeout_minutes: int = 30):
        self._sessions: Dict[str, dict] = {}
        self._lock = Lock()
        self._timeout = timedelta(minutes=timeout_minutes)
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID, return None if expired."""
        with self._lock:
            session = self._sessions.get(session_id)
            
            if not session:
                return None
            
            # Check expiration
            if self._is_expired(session):
                logger.info(f"Session {session_id} expired, removing")
                del self._sessions[session_id]
                return None
            
            # Update last accessed
            session['last_accessed'] = datetime.utcnow()
            return session
    
    def create_session(self, session_id: str, data: dict) -> dict:
        """Create new session."""
        with self._lock:
            now = datetime.utcnow()
            session = {
                **data,
                'created_at': now,
                'last_accessed': now
            }
            self._sessions[session_id] = session
            logger.debug(f"Session {session_id} created")
            return session
    
    def update_session(self, session_id: str, data: dict) -> bool:
        """Update existing session."""
        with self._lock:
            if session_id not in self._sessions:
                return False
            
            self._sessions[session_id].update(data)
            self._sessions[session_id]['last_accessed'] = datetime.utcnow()
            return True
    
    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count removed."""
        with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if self._is_expired(session)
            ]
            
            for sid in expired:
                del self._sessions[sid]
            
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")
            
            return len(expired)
    
    def _is_expired(self, session: dict) -> bool:
        """Check if session is expired."""
        last_accessed = session.get('last_accessed')
        if not last_accessed:
            return True
        
        return datetime.utcnow() - last_accessed > self._timeout

# Global instance
_session_service: Optional[SessionService] = None

def get_session_service() -> SessionService:
    """Get singleton session service."""
    global _session_service
    if _session_service is None:
        from config.settings import get_settings
        settings = get_settings()
        _session_service = SessionService(
            timeout_minutes=settings.SESSION_TIMEOUT_MINUTES
        )
    return _session_service
```

---

### app/services/scam_detector_hybrid.py

**Issues**:
- Magic numbers for weights
- Hardcoded patterns
- No pattern versioning

**Improvements**:

```python
# app/services/patterns.py
from typing import List, Pattern
import re
from dataclasses import dataclass

@dataclass
class DetectionPattern:
    """Scam detection pattern with metadata."""
    name: str
    pattern: Pattern
    category: str
    severity: int  # 1-10
    description: str

class ScamPatterns:
    """Centralized scam detection patterns."""
    
    # Urgency patterns
    URGENCY = [
        DetectionPattern(
            name="urgent_keywords",
            pattern=re.compile(
                r'\b(urgent|immediately|hurry|quick|now|asap)\b',
                re.IGNORECASE
            ),
            category="urgency",
            severity=7,
            description="Urgency creating keywords"
        ),
        # Add more patterns...
    ]
    
    # Threat patterns
    THREATS = [
        DetectionPattern(
            name="account_threat",
            pattern=re.compile(
                r'\b(block|suspend|close|frozen|disable).*account\b',
                re.IGNORECASE
            ),
            category="threat",
            severity=8,
            description="Account threat language"
        ),
        # Add more patterns...
    ]
    
    @classmethod
    def get_all_patterns(cls) -> List[DetectionPattern]:
        """Get all patterns."""
        return cls.URGENCY + cls.THREATS + cls.FINANCIAL + cls.PHISHING

# app/services/scam_detector_hybrid.py
from typing import Dict
from app.services.patterns import ScamPatterns
import logging

logger = logging.getLogger(__name__)

class HybridScamDetector:
    """Hybrid ML + Rule-based scam detector."""
    
    def __init__(
        self,
        ml_weight: float = 0.6,
        rule_weight: float = 0.4
    ):
        """
        Initialize detector with configurable weights.
        
        Args:
            ml_weight: Weight for ML model score (0-1)
            rule_weight: Weight for rule-based score (0-1)
        """
        if ml_weight + rule_weight != 1.0:
            raise ValueError("Weights must sum to 1.0")
        
        self.ml_weight = ml_weight
        self.rule_weight = rule_weight
        self.patterns = ScamPatterns.get_all_patterns()
    
    def detect(self, text: str, ml_score: float) -> Dict:
        """
        Detect scam with hybrid approach.
        
        Args:
            text: Message text
            ml_score: ML model probability (0-1)
            
        Returns:
            Dict with confidence, breakdown, and matched patterns
        """
        rule_score, matched_patterns = self._calculate_rule_score(text)
        
        combined_score = (
            self.ml_weight * ml_score +
            self.rule_weight * rule_score
        )
        
        result = {
            'confidence': combined_score,
            'ml_score': ml_score,
            'rule_score': rule_score,
            'matched_patterns': matched_patterns,
            'is_scam': combined_score >= 0.8
        }
        
        logger.debug(f"Detection result: {result}")
        return result
    
    def _calculate_rule_score(self, text: str) -> tuple[float, List[str]]:
        """Calculate rule-based score."""
        total_severity = 0
        max_possible = sum(p.severity for p in self.patterns)
        matched = []
        
        for pattern in self.patterns:
            if pattern.pattern.search(text):
                total_severity += pattern.severity
                matched.append(pattern.name)
        
        score = total_severity / max_possible if max_possible > 0 else 0
        return score, matched
```

---

### app/services/intelligence_extractor.py

**Issues**:
- Multiple regex patterns scattered
- No validation of extracted data
- Missing some common patterns

**Improvements**:

```python
# app/services/intelligence_extractor.py
from typing import List, Set
from dataclasses import dataclass, field
import re
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExtractedIntelligence:
    """Structured intelligence extraction results."""
    upi_ids: List[str] = field(default_factory=list)
    phone_numbers: List[str] = field(default_factory=list)
    bank_accounts: List[str] = field(default_factory=list)
    phishing_links: List[str] = field(default_factory=list)
    suspicious_keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            'bankAccounts': self.bank_accounts,
            'upiIds': self.upi_ids,
            'phishingLinks': self.phishing_links,
            'phoneNumbers': self.phone_numbers,
            'suspiciousKeywords': self.suspicious_keywords
        }

class IntelligenceExtractor:
    """Extract intelligence from text using regex patterns."""
    
    # Compiled patterns for performance
    UPI_PATTERN = re.compile(
        r'\b([a-zA-Z0-9._-]+@[a-zA-Z]+)\b'
    )
    
    PHONE_PATTERN = re.compile(
        r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    )
    
    BANK_ACCOUNT_PATTERN = re.compile(
        r'\b\d{9,18}\b'  # Bank accounts typically 9-18 digits
    )
    
    URL_PATTERN = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+'
    )
    
    IFSC_PATTERN = re.compile(
        r'\b[A-Z]{4}0[A-Z0-9]{6}\b'
    )
    
    def extract(self, text: str) -> ExtractedIntelligence:
        """
        Extract all intelligence from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            ExtractedIntelligence object with all findings
        """
        if not text:
            return ExtractedIntelligence()
        
        intel = ExtractedIntelligence()
        
        try:
            intel.upi_ids = self._extract_upi_ids(text)
            intel.phone_numbers = self._extract_phone_numbers(text)
            intel.bank_accounts = self._extract_bank_accounts(text)
            intel.phishing_links = self._extract_urls(text)
            intel.suspicious_keywords = self._extract_keywords(text)
            
            logger.debug(f"Extracted: {intel}")
        except Exception as e:
            logger.error(f"Intelligence extraction failed: {e}", exc_info=True)
        
        return intel
    
    def _extract_upi_ids(self, text: str) -> List[str]:
        """Extract and validate UPI IDs."""
        matches = self.UPI_PATTERN.findall(text)
        
        # Validate (basic check for common UPI providers)
        valid_providers = {
            'paytm', 'phonepe', 'googlepay', 'okaxis',
            'okicici', 'oksbi', 'okhdfc', 'ybl'
        }
        
        valid_upis = [
            match for match in matches
            if any(provider in match.lower() for provider in valid_providers)
        ]
        
        return list(set(valid_upis))  # Remove duplicates
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract and normalize phone numbers."""
        matches = self.PHONE_PATTERN.findall(text)
        
        # Normalize format
        normalized = [
            re.sub(r'[^\d+]', '', match)
            for match in matches
        ]
        
        return list(set(normalized))
    
    def _extract_bank_accounts(self, text: str) -> List[str]:
        """Extract potential bank account numbers."""
        accounts = self.BANK_ACCOUNT_PATTERN.findall(text)
        
        # Filter out likely phone numbers (10-11 digits)
        accounts = [
            acc for acc in accounts
            if len(acc) not in (10, 11)
        ]
        
        return list(set(accounts))
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs."""
        urls = self.URL_PATTERN.findall(text)
        return list(set(urls))
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract suspicious keywords."""
        keywords = [
            'urgent', 'immediately', 'blocked', 'suspended',
            'verify', 'confirm', 'otp', 'pin', 'cvv',
            'bank', 'account', 'payment', 'transfer'
        ]
        
        found = [
            kw for kw in keywords
            if kw in text.lower()
        ]
        
        return found

# Global instance
_extractor: Optional[IntelligenceExtractor] = None

def get_intelligence_extractor() -> IntelligenceExtractor:
    """Get singleton intelligence extractor."""
    global _extractor
    if _extractor is None:
        _extractor = IntelligenceExtractor()
    return _extractor
```

---

### app/services/agent_service.py

**Issues**:
- Hardcoded prompts
- No retry logic for OpenAI
- Missing timeout configuration

**Improvements**:

```python
# app/services/agent_service.py
from typing import List, Dict, Optional
from openai import OpenAI, OpenAIError
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)

class AgentService:
    """AI agent for generating human-like responses."""
    
    SYSTEM_PROMPT = """You are an AI agent acting as a honeypot to engage with potential scammers.

Your role:
- Pretend to be a concerned individual who receives a suspicious message
- Never reveal you are detecting scams or are an AI
- Ask natural questions to extract information from the scammer
- Show appropriate concern, confusion, or naivety
- Reference previous conversation context
- Be helpful but cautious

Generate a natural, human-like response that continues the conversation and extracts more information."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        max_tokens: int = 500,
        temperature: float = 0.7
    ):
        """
        Initialize agent service.
        
        Args:
            api_key: OpenAI API key
            model: Model to use
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(OpenAIError),
        reraise=True
    )
    def generate_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Generate AI response with retry logic.
        
        Args:
            message: Latest scammer message
            conversation_history: Previous conversation
            
        Returns:
            Generated response text
            
        Raises:
            OpenAIError: If API call fails after retries
        """
        try:
            messages = self._build_messages(message, conversation_history)
            
            logger.debug(f"Calling OpenAI API with {len(messages)} messages")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=30.0  # 30 second timeout
            )
            
            reply = response.choices[0].message.content.strip()
            
            logger.debug(f"Generated response: {reply[:100]}...")
            
            return reply
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in agent service: {e}", exc_info=True)
            raise
    
    def _build_messages(
        self,
        message: str,
        history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Build OpenAI messages array."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        
        # Add conversation history
        for msg in history[-10:]:  # Last 10 messages for context
            role = "assistant" if msg["sender"] == "user" else "user"
            messages.append({
                "role": role,
                "content": msg["text"]
            })
        
        # Add latest message
        messages.append({
            "role": "user",
            "content": message
        })
        
        return messages

# Dependency injection
def get_agent_service() -> AgentService:
    """Get agent service with configuration."""
    from config.settings import get_settings
    settings = get_settings()
    
    return AgentService(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE
    )
```

---

## Architecture Improvements

### 1. Repository Pattern for Sessions

**Create abstraction layer** for session storage to easily swap implementations:

```python
# app/repositories/session_repository.py
from abc import ABC, abstractmethod
from typing import Optional, Dict

class SessionRepository(ABC):
    """Abstract session repository."""
    
    @abstractmethod
    def get(self, session_id: str) -> Optional[Dict]:
        """Get session by ID."""
        pass
    
    @abstractmethod
    def create(self, session_id: str, data: Dict) -> Dict:
        """Create new session."""
        pass
    
    @abstractmethod
    def update(self, session_id: str, data: Dict) -> bool:
        """Update existing session."""
        pass
    
    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """Delete session."""
        pass

class InMemorySessionRepository(SessionRepository):
    """In-memory implementation."""
    # Implementation from SessionService above

class RedisSessionRepository(SessionRepository):
    """Redis implementation (future)."""
    def __init__(self, redis_url: str):
        import redis
        self.redis = redis.from_url(redis_url)
    
    def get(self, session_id: str) -> Optional[Dict]:
        import json
        data = self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else None
    
    # ... other methods
```

---

### 2. Service Layer Refactoring

**Create a unified service orchestrator**:

```python
# app/services/honeypot_service.py
from typing import Dict
from app.services.session_service import get_session_service
from app.services.scam_detector_hybrid import HybridScamDetector
from app.services.intelligence_extractor import get_intelligence_extractor
from app.services.agent_service import get_agent_service
from app.services.callback_service import CallbackService
import logging

logger = logging.getLogger(__name__)

class HoneypotService:
    """Main business logic orchestrator."""
    
    def __init__(
        self,
        session_service,
        detector: HybridScamDetector,
        extractor,
        agent_service,
        callback_service: CallbackService
    ):
        self.session_service = session_service
        self.detector = detector
        self.extractor = extractor
        self.agent_service = agent_service
        self.callback_service = callback_service
    
    async def process_message(
        self,
        session_id: str,
        message: str,
        conversation_history: List[Dict]
    ) -> Dict:
        """
        Main message processing pipeline.
        
        Returns response dict with 'status' and 'reply'
        """
        try:
            # 1. Load or create session
            session = await self._get_or_create_session(
                session_id,
                conversation_history
            )
            
            # 2. Detect scam
            detection = await self._detect_scam(message, session)
            
            # 3. Extract intelligence
            intel = self.extractor.extract(message)
            
            # 4. Generate response
            reply = await self.agent_service.generate_response(
                message,
                conversation_history
            )
            
            # 5. Update session
            await self._update_session(
                session_id,
                message,
                reply,
                detection,
                intel
            )
            
            # 6. Send callback if needed
            if detection['is_scam'] and not session.get('callback_sent'):
                await self._send_callback(session_id)
            
            return {
                'status': 'success',
                'reply': reply
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise
    
    # ... helper methods
```

---

## Testing Strategy

### Unit Test Example

```python
# tests/unit/test_intelligence_extractor.py
import pytest
from app.services.intelligence_extractor import IntelligenceExtractor

@pytest.fixture
def extractor():
    """Intelligence extractor fixture."""
    return IntelligenceExtractor()

class TestUPIExtraction:
    """Test UPI ID extraction."""
    
    def test_extract_single_upi(self, extractor):
        """Test extracting single UPI ID."""
        text = "Send money to user@paytm"
        intel = extractor.extract(text)
        
        assert len(intel.upi_ids) == 1
        assert "user@paytm" in intel.upi_ids
    
    def test_extract_multiple_upis(self, extractor):
        """Test extracting multiple UPI IDs."""
        text = "Transfer to user@paytm or backup@phonepe"
        intel = extractor.extract(text)
        
        assert len(intel.upi_ids) == 2
        assert "user@paytm" in intel.upi_ids
        assert "backup@phonepe" in intel.upi_ids
    
    def test_no_upis(self, extractor):
        """Test with no UPI IDs."""
        text = "This is a normal message"
        intel = extractor.extract(text)
        
        assert len(intel.upi_ids) == 0
    
    def test_invalid_upi_format(self, extractor):
        """Test invalid UPI format is not extracted."""
        text = "user@gmail.com is not a UPI"  # email, not UPI
        intel = extractor.extract(text)
        
        # Should not extract email as UPI
        assert "user@gmail.com" not in intel.upi_ids
```

### Integration Test Example

```python
# tests/integration/test_honeypot_endpoint.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)

@pytest.fixture
def valid_headers():
    """Valid authentication headers."""
    return {"x-api-key": "test-api-key"}

class TestHoneypotEndpoint:
    """Test honeypot endpoint integration."""
    
    def test_successful_request(self, client, valid_headers):
        """Test successful message processing."""
        payload = {
            "sessionId": "test-001",
            "message": {
                "sender": "scammer",
                "text": "Your account will be blocked! Verify now.",
                "timestamp": "2026-02-05T10:00:00Z"
            },
            "conversationHistory": []
        }
        
        response = client.post("/honeypot", headers=valid_headers, json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "reply" in data
        assert len(data["reply"]) > 0
    
    def test_missing_api_key(self, client):
        """Test request without API key."""
        payload = {"sessionId": "test", "message": {"text": "test"}}
        
        response = client.post("/honeypot", json=payload)
        
        assert response.status_code == 401
    
    def test_invalid_payload(self, client, valid_headers):
        """Test with invalid payload."""
        payload = {"invalid": "data"}
        
        response = client.post("/honeypot", headers=valid_headers, json=payload)
        
        assert response.status_code == 422
```

---

## Performance Optimizations

### 1. Caching

```python
# app/utils/cache.py
from functools import lru_cache, wraps
from typing import Callable
import hashlib
import json

def cache_with_ttl(ttl_seconds: int = 300):
    """Simple TTL cache decorator."""
    def decorator(func: Callable):
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = hashlib.md5(
                json.dumps([args, kwargs], sort_keys=True).encode()
            ).hexdigest()
            
            # Check cache
            if key in cache:
                value, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    return value
            
            # Execute function
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            
            return result
        
        return wrapper
    return decorator

# Usage
@cache_with_ttl(ttl_seconds=600)  # 10 minute cache
def expensive_operation(data: str) -> dict:
    # Some expensive computation
    return result
```

### 2. Async Callback

```python
# app/services/callback_service.py
import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

class CallbackService:
    """Async callback service."""
    
    def __init__(self, callback_url: str, timeout: int = 5):
        self.callback_url = callback_url
        self.timeout = timeout
    
    async def send_async(self, payload: dict) -> bool:
        """Send callback asynchronously."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.callback_url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                logger.info(f"Callback sent successfully for session {payload['sessionId']}")
                return True
            except Exception as e:
                logger.error(f"Callback failed: {e}", exc_info=True)
                return False
```

---

## Security Enhancements

### 1. Input Sanitization

```python
# app/utils/sanitization.py
import re
from html import escape

def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input."""
    # Truncate
    text = text[:max_length]
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    # Escape HTML
    text = escape(text)
    
    return text.strip()
```

### 2. Rate Limiting

```python
# app/middleware/rate_limiter.py
from fastapi import Request, HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    """Simple rate limiter."""
    
    def __init__(self, requests_per_minute: int = 30):
        self.rpm = requests_per_minute
        self.requests = defaultdict(list)
    
    async def check_rate_limit(self, api_key: str):
        """Check if request is within rate limit."""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=1)
        
        # Clean old requests
        self.requests[api_key] = [
            ts for ts in self.requests[api_key]
            if ts > cutoff
        ]
        
        # Check limit
        if len(self.requests[api_key]) >= self.rpm:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
        
        # Record request
        self.requests[api_key].append(now)
```

---

## Implementation Priority

### Phase 1: Critical (Week 1-2)
1. ✅ Configuration management
2. ✅ Error handling
3. ✅ Logging strategy
4. ✅ Session service improvements

### Phase 2: High Priority (Week 3-4)
1. ✅ Intelligence extractor refactoring
2. ✅ Agent service improvements
3. ✅ Testing infrastructure
4. ✅ Documentation updates

### Phase 3: Medium Priority (Month 2)
1. Repository pattern
2. Service orchestrator
3. Caching layer
4. Performance optimization

### Phase 4: Enhancement (Month 3+)
1. Redis integration
2. Advanced ML models
3. Dashboard UI
4. Multi-channel support

---

## Conclusion

These refactoring recommendations are **suggestions, not requirements**. They are meant to:

- Improve code maintainability
- Enhance scalability
- Increase testability
- Strengthen security

**Implement incrementally** based on your project needs and timeline.

---

**Last Updated**: February 5, 2026  
**Maintainer**: ScamNest Team  
**Status**: Living Document
