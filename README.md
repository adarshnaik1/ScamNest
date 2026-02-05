# ScamNest 🕷️

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**ScamNest** is an AI-powered agentic honeypot system designed to autonomously engage with potential scammers, extract actionable intelligence, and report findings. Built with FastAPI and powered by advanced machine learning models, ScamNest acts as a sophisticated decoy that can maintain natural, multi-turn conversations while gathering critical evidence of fraudulent activities.

---

## 🌟 Features

### Core Capabilities
- **🔍 Intelligent Scam Detection**: Hybrid approach combining ML models with rule-based patterns
- **� Optional LLM Validation**: GPT-4o-mini powered detection for borderline cases (opt-in)
- **🤖 Autonomous Agent Engagement**: Natural, human-like conversation powered by OpenAI GPT
- **📊 Intelligence Extraction**: Automated extraction of UPI IDs, phone numbers, bank accounts, and phishing links
- **🛡️ Data Masking**: PII protection in logs for GDPR/CCPA compliance
- **🌐 Multi-language Support**: Detect and translate messages in multiple languages
- **🔒 Secure API**: API key-based authentication for all endpoints
- **📝 Comprehensive Logging**: Detailed session tracking with masked sensitive data
- **🎯 Automated Reporting**: Real-time callback to evaluation endpoints with extracted intelligence

### Technical Highlights
- **RESTful API** built with FastAPI
- **Hybrid ML Detection** using trained spam classification models
- **Session Management** with in-memory persistence
- **Asynchronous Processing** for optimal performance
- **Extensible Architecture** for easy feature additions

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip package manager
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/adarshnaik1/ScamNest.git
   cd ScamNest
   ```

2. **Create and activate virtual environment**
   ```powershell
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```
   
   ```bash
   # Linux/MacOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # API Security
   API_KEY=your-secure-api-key-here
   
   # OpenAI Configuration
   OPENAI_API_KEY=sk-your-openai-api-key
   OPENAI_MODEL=gpt-4o-mini
   
   # LLM Detection (Optional - All disabled by default)
   USE_LLM_VALIDATION=false  # Enable for SUSPICIOUS cases
   USE_LLM_EXPLANATION=false  # Enable for natural agentNotes
   USE_LLM_PATTERN_ANALYSIS=false  # Enable for multi-turn detection
   LLM_DETECTION_MODEL=gpt-4o-mini
   LLM_DETECTION_TIMEOUT=5.0
   
   # Server Configuration (Optional)
   HOST=0.0.0.0
   PORT=8000
   
   # Callback Configuration
   CALLBACK_URL=https://hackathon.guvi.in/api/updateHoneyPotFinalResult
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

The API will be available at `http://localhost:8000`

---

## 📡 API Usage

### Endpoint: POST /honeypot

**Request Headers**
```http
x-api-key: your-api-key
Content-Type: application/json
```

**Request Body**
```json
{
  "sessionId": "unique-session-id",
  "message": {
    "sender": "scammer",
    "text": "Your bank account will be blocked! Verify immediately.",
    "timestamp": "2026-01-21T10:00:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

**Response**
```json
{
  "status": "success",
  "reply": "Oh no! What happened? Why would my account be blocked?"
}
```

### Testing the API

**Using PowerShell:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/honeypot" -Method POST `
  -Headers @{
    "x-api-key" = "your-api-key"
    "Content-Type" = "application/json"
  } `
  -Body '{"sessionId":"test-001","message":{"sender":"scammer","text":"Your account is blocked! Share OTP to unblock.","timestamp":"2026-01-21T10:00:00Z"},"conversationHistory":[]}'
```

**Using cURL:**
```bash
curl -X POST http://localhost:8000/honeypot \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "message": {
      "sender": "scammer",
      "text": "Your account is blocked! Share OTP.",
      "timestamp": "2026-01-21T10:00:00Z"
    },
    "conversationHistory": []
  }'
```

For detailed API documentation, see [API_SPEC.md](API_SPEC.md).

---

## 🏗️ Architecture

### System Flow

```
┌─────────────────┐
│  Incoming Msg   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Authentication │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Language Detect │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ML Preliminary │
│    Detection    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Hybrid Scam    │
│    Detection    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Intelligence   │
│   Extraction    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI Agent       │
│  Response Gen   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Session Update  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Return Response │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Callback (if    │
│ scam confirmed) │
└─────────────────┘
```

### Project Structure

```
ScamNest/
│
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application entry point
│   ├── config.py                    # Configuration and environment variables
│   │
│   ├── ai_model/                    # Machine Learning components
│   │   ├── __init__.py
│   │   ├── train_scam_model.py     # Model training script
│   │   ├── spam_detection_model_training.ipynb
│   │   └── models/                  # Trained model artifacts
│   │
│   ├── middleware/                  # Request/Response middleware
│   │   ├── __init__.py
│   │   └── auth.py                  # API key authentication
│   │
│   ├── models/                      # Pydantic schemas
│   │   ├── __init__.py
│   │   └── schemas.py               # Request/response models
│   │
│   ├── routers/                     # API route handlers
│   │   ├── __init__.py
│   │   └── honeypot.py             # Main honeypot endpoint
│   │
│   ├── services/                    # Business logic services
│   │   ├── __init__.py
│   │   ├── preliminary_model_prediction.py  # Initial ML screening
│   │   ├── scam_detector_hybrid.py         # Hybrid detection engine
│   │   ├── intelligence_extractor.py       # Extract scam indicators
│   │   ├── agent_service.py                # AI agent conversation
│   │   ├── translator.py                   # Multi-language support
│   │   ├── lang_detector.py                # Language detection
│   │   ├── session_service.py              # Session management
│   │   └── callback_service.py             # Result reporting
│   │
│   └── scripts/                     # Utility scripts
│       ├── __init__.py
│       ├── validate_model.py        # Model validation
│       └── test_model_inference.py  # Inference testing
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── test_api.py                  # API endpoint tests
│   └── test_services.py             # Service layer tests
│
├── simulate_scam_conversation.py    # Conversation simulator
├── requirements.txt                  # Python dependencies
├── Procfile                         # Deployment configuration
├── API_SPEC.md                      # Detailed API documentation
└── README.md                        # This file
```

---

## 🧠 Machine Learning

### Model Training

The system uses a hybrid approach combining trained ML models with rule-based detection:

1. **Dataset Sources**
   - [Spam Email Classification](https://www.kaggle.com/datasets/ashfakyeafi/spam-email-classification)
   - [Phishing Email Dataset](https://www.kaggle.com/datasets/naserabdullahalam/phishing-email-dataset)
   - [SMS Spam Classification](https://www.kaggle.com/datasets/mariumfaheem666/spam-sms-classification-using-nlp)
   - [UCI SMS Spam Collection](https://www.kaggle.com/datasets/adityakaranth/uci-sms-spam-collection-data-set)

2. **Training the Model**
   ```bash
   python app/ai_model/train_scam_model.py
   ```
   
   Or use the Jupyter notebook:
   ```bash
   jupyter notebook app/ai_model/spam_detection_model_training.ipynb
   ```

3. **Model Validation**
   ```bash
   python app/scripts/validate_model.py
   ```

### Detection Strategy

- **Stage 1**: Preliminary ML-based probability scoring
- **Stage 2**: Hybrid detection (ML + Rule-based patterns)
- **Stage 3**: Intelligence extraction and confidence scoring

---

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api.py -v
```

### Simulate Conversations

Use the conversation simulator to test the system:

```bash
python simulate_scam_conversation.py
```

---

## 📊 Features in Detail

### Scam Detection

The hybrid detection system combines:

- **Machine Learning Models**: Trained on thousands of real scam messages
- **Pattern Matching**: Regex-based detection for:
  - Urgency indicators ("immediately", "urgent", "now")
  - Threats ("blocked", "suspended", "legal action")
  - Financial requests ("bank details", "OTP", "CVV")
  - Phishing attempts ("verify account", "confirm identity")

### Intelligence Extraction

Automatically extracts:
- **UPI IDs**: `user@bank`, `9876543210@paytm`
- **Phone Numbers**: All formats including international
- **Bank Accounts**: Account numbers and IFSC codes
- **Phishing Links**: URLs and suspicious domains
- **Keywords**: Context-aware suspicious terms

### AI Agent Behavior

The agent is designed to:
- Maintain natural conversation flow
- Ask clarifying questions
- Show appropriate emotional responses
- Never reveal it's a bot
- Adapt to scammer tactics
- Gradually extract information

---

## 🔐 Security Considerations

- API key authentication for all requests
- Environment variable-based configuration
- No sensitive data logged
- Session data sanitization
- Rate limiting (configurable)
- Input validation and sanitization

---

## 🚀 Deployment

### Local Deployment

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Production Deployment

The application includes a `Procfile` for easy deployment to platforms like Heroku:

```bash
# Using Heroku
heroku create your-app-name
git push heroku main
```

### Environment Variables for Production

Ensure these are set in your production environment:
- `API_KEY`: Secure API key for authentication
- `OPENAI_API_KEY`: Your OpenAI API key
- `CALLBACK_URL`: GUVI evaluation endpoint URL

---

## 📝 API Documentation

Once the application is running, interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🛠️ Development

### Adding New Services

1. Create service file in `app/services/`
2. Implement business logic
3. Add tests in `tests/test_services.py`
4. Integrate with router in `app/routers/`

### Code Style

This project follows:
- PEP 8 style guidelines
- Type hints for all functions
- Docstrings for all public methods
- Async/await patterns for I/O operations

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- GUVI Hackathon for the challenge framework
- OpenAI for GPT API access
- FastAPI community for excellent documentation
- Kaggle contributors for spam/scam datasets

---

## 📞 Support

For issues, questions, or contributions:
- **GitHub Issues**: [Create an issue](https://github.com/adarshnaik1/ScamNest/issues)
- **Documentation**: [API_SPEC.md](API_SPEC.md)

---

## 🗺️ Roadmap

### Current Version (1.0)
- ✅ Basic scam detection
- ✅ AI agent engagement
- ✅ Intelligence extraction
- ✅ Callback integration

### Planned Features
- [ ] Advanced ML models (BERT, Transformers)
- [ ] Real-time dashboard
- [ ] Webhook support for multiple platforms
- [ ] Redis-based session storage option
- [ ] Multi-model ensemble predictions
- [ ] Advanced conversation strategy library
- [ ] Automated threat intelligence database

---

**Built with ❤️ for a safer digital world**
