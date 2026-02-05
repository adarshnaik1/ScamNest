# ScamNest Architecture

> **Last Updated**: February 5, 2026  
> **Version**: 1.0  
> **Status**: Production Ready

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [High-Level Architecture](#high-level-architecture)
4. [Component Design](#component-design)
5. [Data Flow](#data-flow)
6. [Technology Stack](#technology-stack)
7. [Design Patterns](#design-patterns)
8. [Scalability Considerations](#scalability-considerations)
9. [Security Architecture](#security-architecture)
10. [Future Architecture](#future-architecture)

---

## System Overview

### Problem Statement

Scammers operate at scale, using automated tools and psychological tactics to defraud victims. Traditional reactive approaches (blocking numbers, reporting sites) are insufficient. We need **proactive intelligence gathering** through deception.

### Solution

**ScamNest** is an AI-powered honeypot that:
- Autonomously engages scammers in natural conversations
- Extracts actionable intelligence (UPI IDs, phone numbers, tactics)
- Reports findings to centralized evaluation systems
- Operates at scale without human intervention

### Core Value Proposition

1. **Autonomous Operation**: No human intervention required
2. **Intelligence Gathering**: Extracts structured scam indicators
3. **Scalability**: Handle multiple concurrent conversations
4. **Realism**: Indistinguishable from real victims
5. **Security**: Built with zero-trust principles

---

## Architecture Principles

### 1. Separation of Concerns
Each module has a single, well-defined responsibility:
- Routing (API layer)
- Business logic (Services)
- Data validation (Models)
- Cross-cutting concerns (Middleware)

### 2. Dependency Injection
- Configuration injected via environment variables
- Services loosely coupled through interfaces
- Easy to mock for testing

### 3. Fail-Safe Defaults
- API key required by default
- Scam detection conservative (minimize false positives)
- Graceful degradation (if OpenAI fails, log and return generic response)

### 4. Asynchronous Processing
- FastAPI async/await for I/O operations
- Non-blocking OpenAI and callback requests
- Optimal resource utilization

### 5. Security by Design
- No secrets in code
- Input validation at boundaries
- Minimal data retention
- Audit logging

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Systems                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ Scammer  │    │ OpenAI   │    │   GUVI   │             │
│  │ (Client) │    │   API    │    │ Endpoint │             │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘             │
└───────┼──────────────┼───────────────┼─────────────────────┘
        │              │               │
        │              │               │
┌───────▼──────────────▼───────────────▼─────────────────────┐
│                     API Gateway                             │
│               (FastAPI Application)                         │
│  ┌──────────────────────────────────────────────────┐     │
│  │           Middleware Layer                       │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │     │
│  │  │   Auth   │  │  CORS    │  │  Logging │      │     │
│  │  └──────────┘  └──────────┘  └──────────┘      │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
│  ┌──────────────────────────────────────────────────┐     │
│  │           Router Layer                           │     │
│  │  ┌──────────────────────────────────────┐       │     │
│  │  │  /honeypot (POST)                    │       │     │
│  │  │  /health (GET)                       │       │     │
│  │  │  /docs (GET) - OpenAPI               │       │     │
│  │  └──────────────────────────────────────┘       │     │
│  └──────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Language   │  │ Preliminary  │  │    Hybrid    │     │
│  │   Detector   │  │  ML Model    │  │   Detector   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Intelligence  │  │  AI Agent    │  │   Session    │     │
│  │  Extractor   │  │   Service    │  │   Manager    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Translator  │  │   Callback   │  │ Data Masker  │     │
│  │   Service    │  │   Service    │  │  (PII Prot)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ LLM Scam     │  │ Risk         │  │ Intent       │     │
│  │ Validator    │  │ Aggregator   │  │ Scorer       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                                │
│  ┌──────────────────────────────────────────────────┐     │
│  │       In-Memory Session Store (Dict)             │     │
│  │  ┌────────────────────────────────────┐          │     │
│  │  │  sessionId -> SessionState         │          │     │
│  │  └────────────────────────────────────┘          │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
│  ┌──────────────────────────────────────────────────┐     │
│  │       ML Model Artifacts (Disk)                  │     │
│  │  ┌────────────────────────────────────┐          │     │
│  │  │  spam_classifier.pkl               │          │     │
│  │  │  tfidf_vectorizer.pkl              │          │     │
│  │  └────────────────────────────────────┘          │     │
│  └──────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 0. Data Protection Layer (`app/services/data_masker.py`)

**Responsibility**: Protect PII (Personally Identifiable Information) in logs and responses for GDPR/CCPA compliance

**Capabilities**:
- **Three masking levels**: FULL (maximum security), PARTIAL (balanced), MINIMAL (debugging)
- **Pattern detection**: API keys, phone numbers, UPI IDs, bank accounts, emails
- **Context-aware masking**: Different levels for logs vs callbacks vs internal processing
- **Header protection**: Automatic masking of x-api-key, authorization headers
- **De-masking support**: Controlled access to original data with audit logging
- **Text masking**: Scan arbitrary text for sensitive patterns

**Masking Examples**:
```python
from app.services.data_masker import DataMasker, mask_for_logging

# API Key:      sk-proj-abc123...xyz789 -> sk-proj-***...xyz789
# Phone:        +91-9876543210 -> +91-98***43210
# UPI:          user@paytm -> u***@paytm
# Bank Account: 123456789012 -> ****6789012
# Email:        john@example.com -> j***@example.com

# Quick logging mask
logger.info(f"Processing: {mask_for_logging(sensitive_text)}")

# Mask intelligence for safe display
masked_intel = DataMasker.mask_intelligence(intelligence.model_dump())

# Mask request headers
masked_headers = DataMasker.mask_request_headers(request.headers)
```

**Integration Points**:
- **Honeypot router**: Masks all sensitive data in log statements
- **Intelligence extractor**: Safe display of extracted UPI/phone/bank data
- **Callback service**: Conditional masking (no masking for GUVI callbacks, full masking for logs)
- **Error handlers**: Masked error messages prevent PII leakage
- **Monitoring**: Masked metrics and dashboards

**Privacy Compliance**:
- **GDPR**: Right to erasure, data minimization, privacy by design
- **CCPA**: California Consumer Privacy Act compliance
- **Audit Trail**: De-masking operations logged for compliance verification

**When to Mask**:
✅ **Always mask in**:
- Log files and debug output
- Error messages and stack traces
- Public API responses (non-callback)
- Monitoring dashboards
- Development/staging environments

❌ **Never mask in**:
- Callback payloads to GUVI endpoint (requires full data)
- Internal ML model processing
- Active session state (in-memory)
- Encrypted database storage

---

### 1. API Layer (`app/routers/`)

**Responsibility**: HTTP request/response handling

#### Components:
- **honeypot.py**: Main endpoint for scam message ingestion
- **health.py**: Health check endpoint (future)

**Design**:
```python
@router.post("/honeypot")
async def honeypot_endpoint(
    request: HoneypotRequest,
    api_key: str = Depends(verify_api_key)
) -> HoneypotResponse:
    """
    1. Validate request (Pydantic handles this)
    2. Delegate to service layer
    3. Return response
    4. Handle errors gracefully
    """
```

**Rationale**:
- Thin layer, no business logic
- Easy to test
- Easy to add new endpoints

---

### 2. Middleware Layer (`app/middleware/`)

**Responsibility**: Cross-cutting concerns

#### Components:
- **auth.py**: API key validation
- **logging.py**: Request/response logging (future)
- **rate_limiting.py**: Rate limiting (future)

**Design**:
```python
async def verify_api_key(x_api_key: str = Header(...)):
    """
    Validates API key from header
    Raises HTTPException(401) if invalid
    """
```

---

### 3. Service Layer (`app/services/`)

**Responsibility**: Business logic orchestration

#### Core Services:

##### 3.1 Language Detection (`lang_detector.py`)
- Detects message language
- Returns ISO language code
- Used for translation decision

##### 3.2 Preliminary Model (`preliminary_model_prediction.py`)
- Fast ML-based scam probability
- Filters out obvious non-scams
- Threshold: 0.5

##### 3.3 Hybrid Detector (`scam_detector_hybrid.py`)
- Combines ML (60%) + Rules (40%)
- Pattern matching for urgency, threats, financial requests
- Returns confidence score (0.0-1.0)

##### 3.4 Intelligence Extractor (`intelligence_extractor.py`)
- Regex-based extraction:
  - UPI IDs: `user@bank`
  - Phone numbers: Multiple formats
  - Bank accounts: Numeric patterns
  - URLs: Phishing links
  - Keywords: Context-aware

##### 3.5 AI Agent (`agent_service.py`)
- OpenAI GPT integration
- Generates human-like responses
- Context-aware (uses conversation history)
- Never reveals bot nature

##### 3.6 Session Manager (`session_service.py`)
- CRUD operations on sessions
- In-memory storage (dict)
- Tracks conversation state

##### 3.7 Callback Service (`callback_service.py`)
- Reports to GUVI endpoint
- Retry logic (3 attempts)
- Idempotent (won't duplicate)

##### 3.8 Translator (`translator.py`)
- Translates non-English messages
- Uses external translation API (future)

---

### 4. Data Models (`app/models/`)

**Responsibility**: Data validation and serialization

#### Components:
- **schemas.py**: Pydantic models
  - `HoneypotRequest`
  - `HoneypotResponse`
  - `Message`
  - `SessionState`
  - `ExtractedIntelligence`

**Benefits**:
- Automatic validation
- Type safety
- API documentation generation
- Serialization/deserialization

---

### 5. Configuration (`app/config.py`)

**Responsibility**: Centralized configuration

```python
class Settings(BaseSettings):
    API_KEY: str
    OPENAI_API_KEY: str
    CALLBACK_URL: str
    # ... other settings
    
    class Config:
        env_file = ".env"
```

**Benefits**:
- Single source of truth
- Environment-based configuration
- Type validation
- Easy to mock for testing

---

## Data Flow

### Request Processing Flow

```
1. Incoming Request
   ↓
2. Middleware: Authentication
   ↓ (if auth fails → 401)
3. Router: Request Validation (Pydantic)
   ↓ (if invalid → 422)
4. Service: Load/Create Session
   ↓
5. Service: Language Detection
   ↓
6. Service: Translation (if non-English)
   ↓
7. Service: Preliminary ML Screening
   ↓ (if low probability → generate neutral response)
8. Service: Hybrid Scam Detection
   ↓
9. Service: Intelligence Extraction
   ↓
10. Service: AI Agent Response Generation
    ↓
11. Service: Update Session State
    ↓
12. Service: Callback (if scam confirmed)
    ↓
13. Router: Return Response
    ↓
14. Client Receives Reply
```

### Session Lifecycle

```
┌─────────────────┐
│ First Message   │
│ (Empty history) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Create Session  │
│ sessionId: xxx  │
│ messages: [1]   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Detect & Reply  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Follow-up Msgs  │
│ messages: [n]   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Scam Confirmed  │
│ confidence≥0.8  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Send Callback   │
│ callbackSent=T  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Session End     │
│ (or timeout)    │
└─────────────────┘
```

---

## Technology Stack

### Core Framework
- **FastAPI**: Modern, async web framework
  - Automatic OpenAPI docs
  - Built-in validation
  - High performance

### AI/ML
- **OpenAI GPT**: Conversational AI
- **scikit-learn**: ML model training
- **joblib/pickle**: Model serialization

### Data Validation
- **Pydantic**: Data models and validation
- Type hints for all functions

### Python Version
- **Python 3.9+**: For modern async features

### Development Tools
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking

---

## Design Patterns

### 1. Repository Pattern
- `session_service.py` abstracts session storage
- Easy to swap in-memory with Redis/DB

### 2. Strategy Pattern
- Scam detection uses multiple strategies (ML + Rules)
- Can add new detection strategies

### 3. Dependency Injection
- Configuration injected via `Settings`
- Services receive dependencies as parameters

### 4. Service Layer Pattern
- Business logic separated from API layer
- Services are reusable and testable

### 5. Facade Pattern
- `agent_service.py` simplifies OpenAI interaction
- Hides complexity of prompt engineering

---

## Scalability Considerations

### Current Architecture
- **Single instance**: In-memory sessions
- **Stateful**: Sessions not shared across instances

### Scaling Strategies

#### Horizontal Scaling (Multi-Instance)
1. **Session Storage**: Replace in-memory with Redis
   ```python
   # app/services/session_service.py
   import redis
   
   class SessionService:
       def __init__(self, redis_client: redis.Redis):
           self.redis = redis_client
   ```

2. **Load Balancer**: Distribute traffic
   - Sticky sessions (session affinity)
   - Or shared session store

#### Vertical Scaling
- Increase instance resources
- Use async workers for CPU-bound tasks (ML inference)

#### Caching
- Cache ML model in memory (already done)
- Cache frequent patterns
- Cache OpenAI responses (with caution)

#### Database
- PostgreSQL for persistent sessions
- Time-series DB for analytics

---

## Security Architecture

### Defense in Depth

1. **API Gateway**
   - API key authentication
   - Rate limiting
   - Input validation

2. **Application Layer**
   - No secrets in code
   - Environment-based config
   - Input sanitization

3. **Data Layer**
   - Minimal data retention
   - No PII logging
   - Encryption at rest (future)

4. **Network Layer**
   - HTTPS only (production)
   - Firewall rules
   - VPC isolation (cloud deployment)

### Threat Model

| Threat | Mitigation |
|--------|------------|
| API key theft | Rotation, monitoring, rate limiting |
| Injection attacks | Pydantic validation, sanitization |
| DDoS | Rate limiting, load balancer |
| Secret exposure | GitGuardian, .env files |
| Data breach | Minimal retention, encryption |

---

## Future Architecture

### Phase 2: Enhanced Intelligence

```
┌─────────────────────────────────────────────┐
│         Advanced Analytics                  │
│  ┌──────────────────────────────────┐      │
│  │  - Scammer profiling              │      │
│  │  - Tactic classification          │      │
│  │  - Network analysis               │      │
│  │  - Trend detection                │      │
│  └──────────────────────────────────┘      │
└─────────────────────────────────────────────┘
```

### Phase 3: Multi-Channel Support

```
┌─────────────────────────────────────────────┐
│         Channel Adapters                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │   SMS   │  │WhatsApp │  │  Email  │    │
│  └─────────┘  └─────────┘  └─────────┘    │
│         │            │            │         │
│         └────────────┴────────────┘         │
│                    │                        │
│                    ▼                        │
│         ┌──────────────────────┐           │
│         │   Unified Gateway    │           │
│         └──────────────────────┘           │
└─────────────────────────────────────────────┘
```

### Phase 4: Real-Time Dashboard

```
┌─────────────────────────────────────────────┐
│         Web Dashboard                       │
│  - Live session monitoring                  │
│  - Intelligence visualization               │
│  - Analytics and reports                    │
│  - Admin controls                           │
└─────────────────────────────────────────────┘
```

---

## Architectural Decisions Records (ADRs)

### ADR-001: In-Memory Session Storage

**Decision**: Use in-memory dictionary for session storage

**Context**: MVP needs simple, fast session management

**Consequences**:
- ✅ Fast performance
- ✅ Simple implementation
- ❌ Data lost on restart
- ❌ Can't scale horizontally

**Future**: Migrate to Redis for production

---

### ADR-002: Hybrid Scam Detection

**Decision**: Combine ML (60%) + Rule-based (40%)

**Context**: Pure ML has false negatives, pure rules too brittle

**Consequences**:
- ✅ Better accuracy
- ✅ Explainable results
- ❌ More maintenance

---

### ADR-003: Synchronous Callback

**Decision**: Send callback synchronously (block until complete)

**Context**: Need to ensure callback is sent before session ends

**Consequences**:
- ✅ Guaranteed delivery
- ❌ Slower response time
- **Future**: Use async queue (Celery, RabbitMQ)

---

## Diagrams

### Component Diagram

```
┌─────────────────────────────────────────────┐
│              ScamNest API                   │
├─────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Routers  │─▶│ Services │─▶│  Models  │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│       │              │              │       │
│       └──────────────┴──────────────┘       │
│                      │                      │
│              ┌───────▼────────┐            │
│              │  Middleware    │            │
│              └────────────────┘            │
└─────────────────────────────────────────────┘
```

---

## Conclusion

ScamNest's architecture balances:
- **Simplicity**: Easy to understand and maintain
- **Scalability**: Clear path to horizontal scaling
- **Security**: Built with zero-trust principles
- **Extensibility**: Easy to add new features

**Next Steps**: See [REFACTORING_GUIDE.md](REFACTORING_GUIDE.md) for specific improvements.

---

**Document Maintainer**: ScamNest Team  
**Review Schedule**: Quarterly or on major changes
