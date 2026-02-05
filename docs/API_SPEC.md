# ScamNest API Specification

> **Version**: 1.0  
> **Last Updated**: February 2026  
> **API Type**: RESTful  
> **Base URL**: `http://localhost:8000` (Development) | `https://your-domain.com` (Production)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Data Models](#data-models)
5. [Request/Response Examples](#requestresponse-examples)
6. [Session Management](#session-management)
7. [Scam Detection Pipeline](#scam-detection-pipeline)
8. [Intelligence Extraction](#intelligence-extraction)
9. [Agent Behavior Specification](#agent-behavior-specification)
10. [Callback Mechanism](#callback-mechanism)
11. [Error Handling](#error-handling)
12. [Rate Limiting](#rate-limiting)
13. [Best Practices](#best-practices)
14. [Testing Guide](#testing-guide)

---

## Overview

### System Purpose

ScamNest provides an intelligent honeypot API that:
- **Receives** incoming messages from potential scammers
- **Analyzes** content using ML models and pattern matching
- **Engages** in realistic, multi-turn conversations
- **Extracts** actionable intelligence (UPI IDs, phone numbers, links, etc.)
- **Reports** confirmed scams to evaluation endpoints

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **Scam Detection** | Hybrid ML + rule-based detection with confidence scoring |
| **LLM Validation** | Optional GPT-4o-mini powered validation for borderline cases (opt-in) |
| **Agentic Engagement** | AI-powered conversational responses via OpenAI GPT |
| **Multi-language** | Automatic detection and translation of non-English messages |
| **Intelligence Gathering** | Automated extraction of financial indicators and contact information |
| **Data Masking** | PII protection in logs for GDPR/CCPA compliance |
| **Session Persistence** | Stateful conversation tracking across multiple requests |
| **Automated Reporting** | Callback to evaluation endpoint with complete session data |

---

## Authentication

### API Key Authentication

All API requests must include authentication via the `x-api-key` header.

#### Header Format
```http
x-api-key: your-secure-api-key
Content-Type: application/json
```

#### Authentication Flow

1. Client includes `x-api-key` in request headers
2. Server validates key against configured `API_KEY` environment variable
3. Valid key: Process request and return response
4. Invalid/missing key: Return `401 Unauthorized`

#### Error Response (401)
```json
{
  "detail": "Invalid or missing API key"
}
```

#### Security Considerations

- Store API keys in environment variables, never in code
- Use different keys for development and production
- Rotate keys periodically
- Log failed authentication attempts
- Consider implementing rate limiting per API key

---

## API Endpoints

### POST /honeypot

**Purpose**: Main endpoint for receiving and processing scam messages

#### Request

**Method**: `POST`  
**Path**: `/honeypot`  
**Content-Type**: `application/json`  
**Authentication**: Required (`x-api-key`)

#### Response

**Status Code**: `200 OK`  
**Content-Type**: `application/json`

---

## Data Models

### HoneypotRequest

Complete request payload for the honeypot endpoint.

```json
{
  "sessionId": "string",
  "message": {
    "sender": "string",
    "text": "string",
    "timestamp": "ISO-8601 datetime"
  },
  "conversationHistory": [
    {
      "sender": "string",
      "text": "string",
      "timestamp": "ISO-8601 datetime"
    }
  ],
  "metadata": {
    "channel": "string",
    "language": "string",
    "locale": "string"
  }
}
```

#### Field Specifications

##### sessionId
- **Type**: `string`
- **Required**: Yes
- **Description**: Unique identifier for the conversation session
- **Format**: UUID recommended, but any unique string accepted
- **Example**: `"wertyu-dfghj-ertyui"`, `"session-12345"`
- **Usage**: Used to track conversation state across multiple requests

##### message
- **Type**: `object`
- **Required**: Yes
- **Description**: The latest incoming message from the scammer

###### message.sender
- **Type**: `string`
- **Required**: Yes
- **Allowed Values**: `"scammer"`, `"user"`
- **Description**: Identifies who sent the message
- **Note**: In honeypot context, "scammer" is the incoming message, "user" is the AI agent

###### message.text
- **Type**: `string`
- **Required**: Yes
- **Description**: The actual message content
- **Max Length**: 10,000 characters (configurable)
- **Format**: Plain text, may include emojis and special characters

###### message.timestamp
- **Type**: `string`
- **Required**: Yes
- **Format**: ISO-8601 datetime (e.g., `"2026-01-21T10:15:30Z"`)
- **Timezone**: UTC recommended
- **Description**: When the message was sent

##### conversationHistory
- **Type**: `array of objects`
- **Required**: Optional (but recommended for multi-turn conversations)
- **Description**: Previous messages in chronological order
- **First Message**: Empty array `[]`
- **Follow-up Messages**: Contains all previous exchanges
- **Note**: Each element has same structure as `message` object

##### metadata
- **Type**: `object`
- **Required**: Optional
- **Description**: Additional contextual information

###### metadata.channel
- **Type**: `string`
- **Allowed Values**: `"SMS"`, `"WhatsApp"`, `"Email"`, `"Chat"`, etc.
- **Description**: Communication channel where message originated

###### metadata.language
- **Type**: `string`
- **Example**: `"English"`, `"Hindi"`, `"Tamil"`
- **Description**: Detected or specified language of the message

###### metadata.locale
- **Type**: `string`
- **Format**: ISO 3166-1 alpha-2 country code
- **Example**: `"IN"`, `"US"`, `"GB"`
- **Description**: Geographic region or locale

### HoneypotResponse

Response returned by the API after processing a message.

```json
{
  "status": "string",
  "reply": "string"
}
```

#### Field Specifications

##### status
- **Type**: `string`
- **Allowed Values**: `"success"`, `"error"`
- **Description**: Indicates whether the request was processed successfully

##### reply
- **Type**: `string`
- **Description**: AI-generated response to continue the conversation
- **Characteristics**:
  - Natural, human-like language
  - Context-aware based on conversation history
  - Designed to elicit more information from scammer
  - Never reveals bot nature or scam detection

---

## Request/Response Examples

### Example 1: First Message (Session Initiation)

#### Request
```http
POST /honeypot HTTP/1.1
Host: localhost:8000
Content-Type: application/json
x-api-key: your-api-key

{
  "sessionId": "session-001",
  "message": {
    "sender": "scammer",
    "text": "URGENT! Your bank account will be blocked in 2 hours. Click here to verify: http://fake-bank.com",
    "timestamp": "2026-02-05T10:00:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

#### Response
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "reply": "Oh no! What happened? I didn't receive any notification from my bank. Is this really from ICICI Bank?"
}
```

#### What Happens Internally
1. ✅ API key validated
2. ✅ New session created with ID `"session-001"`
3. ✅ ML model detects high scam probability
4. ✅ Pattern matcher identifies urgency keywords and phishing link
5. ✅ Intelligence extractor captures URL
6. ✅ AI agent generates concerned, naive response
7. ✅ Session state saved with scam detection flag

---

### Example 2: Multi-Turn Conversation

#### Request (Follow-up Message)
```http
POST /honeypot HTTP/1.1
Host: localhost:8000
Content-Type: application/json
x-api-key: your-api-key

{
  "sessionId": "session-001",
  "message": {
    "sender": "scammer",
    "text": "Yes sir, this is from bank security team. Please share your UPI PIN to verify account.",
    "timestamp": "2026-02-05T10:02:30Z"
  },
  "conversationHistory": [
    {
      "sender": "scammer",
      "text": "URGENT! Your bank account will be blocked in 2 hours. Click here to verify: http://fake-bank.com",
      "timestamp": "2026-02-05T10:00:00Z"
    },
    {
      "sender": "user",
      "text": "Oh no! What happened? I didn't receive any notification from my bank. Is this really from ICICI Bank?",
      "timestamp": "2026-02-05T10:01:00Z"
    }
  ],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

#### Response
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "reply": "UPI PIN? I thought banks never ask for PINs. But if you're from the security team, should I share it here or call the bank helpline first?"
}
```

#### What Happens Internally
1. ✅ Session `"session-001"` retrieved from memory
2. ✅ Scam confidence increases (requesting PIN)
3. ✅ Intelligence extraction: flagged request for sensitive data
4. ✅ Agent continues playing naive while probing
5. ✅ Session updated with new intelligence
6. ✅ **Scam confirmed** - callback preparation initiated

---

### Example 3: Scam Confirmation & Callback

After several exchanges where scam is confirmed, the system automatically sends a callback.

#### Callback Sent to GUVI Endpoint
```http
POST /api/updateHoneyPotFinalResult HTTP/1.1
Host: hackathon.guvi.in
Content-Type: application/json

{
  "sessionId": "session-001",
  "scamDetected": true,
  "totalMessagesExchanged": 6,
  "extractedIntelligence": {
    "bankAccounts": [],
    "upiIds": [],
    "phishingLinks": ["http://fake-bank.com"],
    "phoneNumbers": [],
    "suspiciousKeywords": ["urgent", "blocked", "verify", "UPI PIN"]
  },
  "agentNotes": "Scammer impersonated bank security team, created urgency about account blocking, requested sensitive UPI PIN. Phishing link detected in initial message."
}
```

---

## Session Management

### Session Lifecycle

```
┌──────────────────┐
│  Session Start   │ ← Empty conversationHistory
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Message Exchange │ ← Multiple turns
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Scam Confirmed   │ ← Detection threshold met
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Callback Sent    │ ← Final result reported
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Session End     │
└──────────────────┘
```

### Session State Schema

Each session maintains the following state:

```python
{
    "sessionId": "string",
    "messages": [
        {
            "sender": "string",
            "text": "string",
            "timestamp": "ISO-8601"
        }
    ],
    "scamDetected": boolean,
    "scamSuspected": boolean,
    "scamConfidence": float,  # 0.0 to 1.0
    "extractedIntelligence": {
        "bankAccounts": ["string"],
        "upiIds": ["string"],
        "phishingLinks": ["string"],
        "phoneNumbers": ["string"],
        "suspiciousKeywords": ["string"]
    },
    "totalMessages": integer,
    "callbackSent": boolean,
    "agentNotes": "string",
    "metadata": {
        "channel": "string",
        "language": "string",
        "locale": "string"
    },
    "createdAt": "ISO-8601",
    "updatedAt": "ISO-8601"
}
```

### Session Storage

**Current Implementation**: In-memory dictionary  
**Key**: `sessionId`  
**Persistence**: Process lifetime (resets on restart)

**Note**: For production deployments with multiple instances, consider:
- Distributed cache (Redis, Memcached)
- Database storage (PostgreSQL, MongoDB)
- Session replication across instances

---

## Scam Detection Pipeline

### Detection Stages

#### Stage 1: Preliminary ML Screening

**Service**: `preliminary_model_prediction.py`

- **Input**: Message text
- **Process**: 
  - Text preprocessing and normalization
  - Feature extraction (TF-IDF, n-grams)
  - ML model inference
- **Output**: Scam probability score (0.0 to 1.0)
- **Threshold**: If score > 0.5, proceed to Stage 2

#### Stage 2: Hybrid Detection

**Service**: `scam_detector_hybrid.py`

Combines ML prediction with rule-based patterns:

**Pattern Categories**:

1. **Urgency Indicators**
   - Keywords: "urgent", "immediately", "now", "hurry", "quickly"
   - Time pressure: "2 hours", "today", "expiring soon"

2. **Threat Language**
   - Account threats: "blocked", "suspended", "closed", "frozen"
   - Legal threats: "legal action", "court", "penalty", "fine"

3. **Financial Requests**
   - Credentials: "PIN", "password", "OTP", "CVV", "ATM PIN"
   - Account info: "bank details", "account number", "card number"
   - Payment: "transfer money", "send payment", "UPI ID"

4. **Phishing Indicators**
   - Action requests: "verify", "confirm", "update", "click here"
   - Suspicious links: Short URLs, misspelled domains

5. **Authority Impersonation**
   - Claims: "bank official", "government", "security team", "IT department"

**Scoring**:
- ML score weight: 60%
- Pattern matching score: 40%
- Combined score determines final confidence

#### Stage 3: Intelligence Extraction

**Service**: `intelligence_extractor.py`

Extracts specific scam indicators using regex patterns:

| Category | Pattern | Example |
|----------|---------|---------|
| **UPI IDs** | `[a-zA-Z0-9._-]+@[a-zA-Z]+` | `user@paytm`, `9876543210@okicici` |
| **Phone Numbers** | Various international formats | `+91-9876543210`, `(555) 123-4567` |
| **Bank Accounts** | Numeric patterns with IFSC | `123456789012`, `SBIN0001234` |
| **URLs** | URL patterns | `http://phishing-site.com` |
| **Keywords** | Context-based extraction | "urgent", "verify", "blocked" |

#### Stage 4: LLM-Enhanced Detection (Optional)

**Service**: `llm_scam_validator.py`

**\u26a0\ufe0f All LLM features are OPT-IN and disabled by default for cost/latency optimization**

Three optional LLM detection modes using GPT-4o-mini:

**Mode 1: SUSPICIOUS Validation**
- **When**: ML confidence is borderline (SUSPICIOUS risk level, typically 0.5-0.7)
- **Purpose**: Reduce false positives by getting LLM second opinion
- **Latency**: +1-3 seconds
- **Config**: `USE_LLM_VALIDATION=true`
- **Returns**: (decision, score, reasoning) tuple
- **Example**: Validates if "urgent account verification" is legitimate concern or scam tactic

**Mode 2: Natural Language Explanations**
- **When**: Preparing callback payload agentNotes
- **Purpose**: Generate human-readable scam analysis for better reporting
- **Latency**: +1-2 seconds
- **Config**: `USE_LLM_EXPLANATION=true`
- **Returns**: Natural language summary instead of technical notation
- **Example**: "Scammer impersonated bank official and requested OTP for fake account verification" vs "patterns: urgency+authority+credential_request"

**Mode 3: Multi-turn Pattern Analysis**
- **When**: Conversation reaches 3+ messages
- **Purpose**: Detect sophisticated multi-stage scam tactics
- **Latency**: +2-4 seconds
- **Config**: `USE_LLM_PATTERN_ANALYSIS=true`
- **Analyzes**: Conversation flow, psychological manipulation, escalation patterns
- **Detects**: Social engineering, trust building, false urgency, authority abuse
- **Example**: Identifies scammer gradually building trust before requesting sensitive info

**Configuration**:
```env
# LLM Detection (Optional - All disabled by default)
USE_LLM_VALIDATION=false       # Mode 1: Borderline case validation
USE_LLM_EXPLANATION=false      # Mode 2: Natural language agentNotes
USE_LLM_PATTERN_ANALYSIS=false # Mode 3: Multi-turn sophistication detection
LLM_DETECTION_MODEL=gpt-4o-mini
LLM_DETECTION_TIMEOUT=5.0
LLM_MIN_MESSAGES_FOR_PATTERN_ANALYSIS=3
```

**Benefits**:
- \ud83c\udfaf Improved accuracy for borderline cases
- \ud83d\udcca Better callback payload readability
- \ud83e\udde0 Detection of sophisticated multi-stage scams
- \ud83d\udd04 Graceful degradation (falls back to traditional methods if LLM unavailable)

**Trade-offs**:
- \u23f1\ufe0f Adds 1-4 seconds latency (configurable timeout)
- \ud83d\udcb0 Increases operational cost (~$0.0001 per detection)
- \ud83d\udd0c Requires OpenAI API availability

**Recommendation**:
- **Hackathon/Demo**: Keep disabled for speed (15ms traditional vs 1-3s with LLM)
- **Production**: Enable selectively based on false positive rates
- **High-stakes**: Enable all modes for maximum accuracy

---

## Data Masking and Privacy

### PII Protection

**Service**: `data_masker.py`

All sensitive data is automatically masked in logs for GDPR/CCPA compliance:

| Data Type | Masking Example |
|-----------|-----------------|
| API Keys | `sk-proj-abc123...xyz789` \u2192 `sk-proj-***...xyz789` |
| Phone Numbers | `+91-9876543210` \u2192 `+91-98***43210` |
| UPI IDs | `user@paytm` \u2192 `u***@paytm` |
| Bank Accounts | `123456789012` \u2192 `****6789012` |
| Emails | `john@example.com` \u2192 `j***@example.com` |

**Masking Levels**:
- **FULL**: Maximum security (show prefix + last 4)
- **PARTIAL**: Balanced (show first 2 + last 4, mask middle)
- **MINIMAL**: Debugging (show first 6, mask rest)

**Context-Aware**:
- \u2705 Masked in: Logs, error messages, debug output, monitoring dashboards
- \u274c Not masked in: Callback payloads (GUVI needs full data), internal processing

**Example Usage**:
```python
from app.services.data_masker import mask_for_logging, DataMasker

# Quick logging mask
logger.info(f"Processing: {mask_for_logging(sensitive_text)}")

# Mask intelligence
masked = DataMasker.mask_intelligence(intelligence.model_dump())
```

---

## Agent Behavior Specification

### AI Agent Design Principles

The AI agent (powered by OpenAI GPT) is designed to:

#### ✅ DO:
- **Maintain Persona**: Act as a cautious, slightly naive but curious individual
- **Ask Questions**: Probe for more details to extract intelligence
- **Show Concern**: React naturally to threats and urgency
- **Adapt Context**: Reference previous conversation points
- **Gradual Disclosure**: Appear willing to cooperate slowly
- **Natural Language**: Use conversational, human-like responses

#### ❌ DON'T:
- **Reveal Detection**: Never mention "scam", "fraud detection", or system behavior
- **Break Character**: Maintain consistent persona throughout
- **Be Obvious**: Avoid suspicion-raising questions
- **Comply Immediately**: Don't provide fake credentials too quickly
- **Use Technical Terms**: Avoid AI/bot terminology

### Response Generation Strategy

**Conversation Phases**:

1. **Initial Contact** (Messages 1-2)
   - Show surprise or concern
   - Ask clarifying questions
   - Example: *"Oh no! What happened to my account?"*

2. **Information Gathering** (Messages 3-5)
   - Express worry while probing
   - Request verification
   - Example: *"How do I know you're really from the bank?"*

3. **Hesitant Cooperation** (Messages 6-8)
   - Show willingness with caution
   - Ask about process
   - Example: *"Should I share this here or call the helpline?"*

4. **Extraction Phase** (Messages 9+)
   - Continue extracting intelligence
   - Maintain engagement
   - Example: *"What happens after I share this information?"*

### System Prompt Template

```
You are an AI agent acting as a honeypot to engage with potential scammers. 

Your role:
- Pretend to be a concerned individual who receives a suspicious message
- Never reveal you are detecting scams or are an AI
- Ask natural questions to extract information from the scammer
- Show appropriate concern, confusion, or naivety
- Reference previous conversation context
- Be helpful but cautious

Conversation history:
{conversation_history}

Latest message from scammer:
{scammer_message}

Generate a natural, human-like response that continues the conversation and extracts more information.
```

---

## Callback Mechanism

### GUVI Evaluation Endpoint

**Purpose**: Report confirmed scam sessions with extracted intelligence

#### Endpoint Details

**URL**: `https://hackathon.guvi.in/api/updateHoneyPotFinalResult`  
**Method**: `POST`  
**Content-Type**: `application/json`  
**Authentication**: None required

#### Callback Payload

```json
{
  "sessionId": "string",
  "scamDetected": boolean,
  "totalMessagesExchanged": integer,
  "extractedIntelligence": {
    "bankAccounts": ["string"],
    "upiIds": ["string"],
    "phishingLinks": ["string"],
    "phoneNumbers": ["string"],
    "suspiciousKeywords": ["string"]
  },
  "agentNotes": "string"
}
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `sessionId` | string | Unique session identifier (matches request) |
| `scamDetected` | boolean | `true` if scam confirmed, `false` otherwise |
| `totalMessagesExchanged` | integer | Total number of messages in conversation |
| `extractedIntelligence` | object | All extracted scam indicators |
| `agentNotes` | string | Human-readable summary of scammer behavior |

#### Callback Trigger Conditions

Callback is sent when **ALL** of the following are true:

1. ✅ Scam confidence score ≥ 0.8 (configurable threshold)
2. ✅ At least 3 messages exchanged
3. ✅ Callback not already sent for this session
4. ✅ Intelligence extraction completed

#### Implementation

**Service**: `callback_service.py`

```python
async def send_callback(session_data: dict):
    """
    Send final result callback to GUVI endpoint
    """
    payload = {
        "sessionId": session_data["sessionId"],
        "scamDetected": session_data["scamDetected"],
        "totalMessagesExchanged": session_data["totalMessages"],
        "extractedIntelligence": session_data["extractedIntelligence"],
        "agentNotes": session_data["agentNotes"]
    }
    
    try:
        response = requests.post(
            CALLBACK_URL,
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Callback failed: {e}")
        return False
```

#### Callback Behavior

- **Retry Logic**: 3 attempts with exponential backoff
- **Timeout**: 5 seconds per attempt
- **Failure Handling**: Log error, mark session as callback-pending
- **Success**: Mark session as callback-sent, prevent duplicates

---

## Error Handling

### HTTP Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request processed successfully |
| 400 | Bad Request | Invalid request payload or missing required fields |
| 401 | Unauthorized | Invalid or missing API key |
| 422 | Unprocessable Entity | Valid JSON but semantic errors (e.g., invalid timestamp format) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side processing error |
| 503 | Service Unavailable | OpenAI API or external service unavailable |

### Error Response Format

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "string"
  }
}
```

### Common Error Scenarios

#### Missing API Key
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or missing API key",
    "details": "Provide valid x-api-key header"
  }
}
```

#### Invalid Request Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request payload",
    "details": "Field 'message.text' is required"
  }
}
```

#### OpenAI Service Error
```json
{
  "error": {
    "code": "EXTERNAL_SERVICE_ERROR",
    "message": "Failed to generate AI response",
    "details": "OpenAI API temporarily unavailable"
  }
}
```

---

## Rate Limiting

### Current Implementation

**Status**: Not enforced by default  
**Recommendation**: Implement for production

### Suggested Limits

| Tier | Requests per Minute | Requests per Day |
|------|---------------------|------------------|
| Development | 60 | Unlimited |
| Production | 30 | 10,000 |

### Implementation Strategy

```python
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/honeypot")
@limiter.limit("30/minute")
async def honeypot_endpoint(request: Request, payload: HoneypotRequest):
    # Process request
    pass
```

---

## Best Practices

### For API Consumers

1. **Session Management**
   - Use unique `sessionId` for each conversation
   - Include complete `conversationHistory` in follow-up requests
   - Don't reuse session IDs across different conversations

2. **Error Handling**
   - Implement retry logic with exponential backoff
   - Handle all HTTP error codes gracefully
   - Log API responses for debugging

3. **Performance**
   - Avoid sending duplicate requests
   - Implement client-side timeout (30 seconds recommended)
   - Cache session data client-side if needed

4. **Security**
   - Never expose API keys in client-side code
   - Use HTTPS for all production traffic
   - Rotate API keys periodically

### For System Operators

1. **Monitoring**
   - Track callback success/failure rates
   - Monitor OpenAI API usage and costs
   - Log scam detection accuracy metrics

2. **Configuration**
   - Adjust scam detection thresholds based on false positive rate
   - Configure callback retry attempts
   - Set appropriate session timeout values

3. **Maintenance**
   - Regularly update ML models with new data
   - Review and update regex patterns
   - Clear expired sessions from memory

---

## Testing Guide

### Manual Testing

#### Test Case 1: First Contact with Scam Message

**Objective**: Verify scam detection and agent engagement

```bash
curl -X POST http://localhost:8000/honeypot \
  -H "x-api-key: test-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "message": {
      "sender": "scammer",
      "text": "URGENT! Your account will be blocked. Share OTP now.",
      "timestamp": "2026-02-05T10:00:00Z"
    },
    "conversationHistory": []
  }'
```

**Expected Response**:
- Status: 200 OK
- Reply: Natural, concerned response
- Session created with scam detection flag

---

#### Test Case 2: Multi-Turn Conversation

**Objective**: Verify session continuity and intelligence extraction

```bash
curl -X POST http://localhost:8000/honeypot \
  -H "x-api-key: test-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "message": {
      "sender": "scammer",
      "text": "Send money to 9876543210@paytm to verify",
      "timestamp": "2026-02-05T10:02:00Z"
    },
    "conversationHistory": [
      {
        "sender": "scammer",
        "text": "URGENT! Your account will be blocked. Share OTP now.",
        "timestamp": "2026-02-05T10:00:00Z"
      },
      {
        "sender": "user",
        "text": "What happened? Why would it be blocked?",
        "timestamp": "2026-02-05T10:01:00Z"
      }
    ]
  }'
```

**Expected Response**:
- Status: 200 OK
- Reply: Contextual response referencing previous messages
- UPI ID extracted: `9876543210@paytm`
- Increased scam confidence

---

#### Test Case 3: Invalid API Key

**Objective**: Verify authentication

```bash
curl -X POST http://localhost:8000/honeypot \
  -H "x-api-key: wrong-key" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

**Expected Response**:
- Status: 401 Unauthorized
- Error message about invalid API key

---

### Automated Testing

Use the provided test suite:

```bash
# Run all tests
pytest tests/

# Run API tests only
pytest tests/test_api.py -v

# Run service tests only
pytest tests/test_services.py -v
```

### Conversation Simulator

Use the simulation script for end-to-end testing:

```bash
python simulate_scam_conversation.py
```

This simulates a complete scam conversation and verifies:
- Session creation
- Multi-turn engagement
- Intelligence extraction
- Callback invocation

---

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| **Honeypot** | A decoy system designed to attract and study malicious actors |
| **Session** | A complete conversation thread identified by unique `sessionId` |
| **Scam Confidence** | Probability score (0.0-1.0) indicating likelihood of scam |
| **Intelligence** | Extracted data points like UPI IDs, phone numbers, URLs |
| **Callback** | Final result report sent to evaluation endpoint |
| **Agent** | AI-powered conversational component (OpenAI GPT) |

### Configuration Reference

**Environment Variables**:

```env
# Required
API_KEY=your-secure-api-key
OPENAI_API_KEY=sk-your-openai-key

# Optional
HOST=0.0.0.0
PORT=8000
CALLBACK_URL=https://hackathon.guvi.in/api/updateHoneyPotFinalResult
SCAM_DETECTION_THRESHOLD=0.8
SESSION_TIMEOUT_MINUTES=30
MAX_CONVERSATION_TURNS=20
```

### API Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial release with core functionality |

---

## Support & Contact

For technical questions or issues:

- **GitHub Issues**: [github.com/adarshnaik1/ScamNest/issues](https://github.com/adarshnaik1/ScamNest/issues)
- **Documentation**: See [README.md](README.md)
- **Email**: Contact via GitHub profile

---

**Document Version**: 1.0  
**Last Updated**: February 5, 2026  
**API Version**: 1.0  

---

© 2026 ScamNest. Built for GUVI Hackathon.
