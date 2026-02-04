# Agentic Honeypot API

An AI-powered honeypot system built with FastAPI that acts as a decoy to engage with potential scammers.

## What it does

- **Receives scam messages** via REST API
- **Detects scam patterns** using keyword analysis (urgency, threats, sensitive data requests)
- **Engages scammers** with realistic human-like responses (powered by OpenAI)
- **Extracts intelligence** - UPI IDs, phone numbers, bank accounts, phishing links
- **Reports confirmed scams** to GUVI evaluation endpoint with full session data

## Objective

Build an agentic system that can autonomously handle multi-turn conversations with scammers, gather evidence, and report findings - all without revealing it's a bot.

---

## Setup

```powershell
# Install
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Configure - create .env file
API_KEY=your-api-key
OPENAI_API_KEY=sk-your-key   

# Run
uvicorn app.main:app --reload --port 8000
```

## Test (open new terminal)

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/honeypot" -Method POST `
  -Headers @{"x-api-key"="your-api-key"; "Content-Type"="application/json"} `
  -Body '{"sessionId":"test-1","message":{"sender":"scammer","text":"Your account is blocked! Share OTP.","timestamp":"2026-01-21T10:00:00Z"}}'
```

## API

**POST /honeypot**

```json
// Request
{
  "sessionId": "session-123",
  "message": {"sender": "scammer", "text": "...", "timestamp": "2026-01-21T10:00:00Z"},
  "conversationHistory": []
}

// Response
{"status": "success", "reply": "Oh no, what happened?"}
```

## Flow

```
Message -> Detect Scam -> Extract Intel -> Generate Reply -> Callback to GUVI (if confirmed)
```

## TODO

`app/services/scam_detector.py` uses **hardcoded regex patterns**. Replace with ML model.

## Structure

```
app/
 main.py              # FastAPI app
 config.py            # .env settings
 routers/honeypot.py  # POST /honeypot
 services/
    model_predictor.py       #for preliminary check for possiblity of scam
    scam_detector_hybrid.py         #Hybrid ( Model + Rule Based) detector for scam detection
    intelligence_extractor.py
    agent_service.py         # OpenAI responses
    session_service.py
    callback_service.py
 middleware/auth.py   # x-api-key check
 ai_model/
    dataset/                              #contain the dataset
    model/                                #contain the models
    spam_detection_model_training.ipynb   #model training
    train_scam_model.py                   #model training  
```

## Dataset
```
https://www.kaggle.com/datasets/ashfakyeafi/spam-email-classification
https://www.kaggle.com/datasets/naserabdullahalam/phishing-email-dataset
https://www.kaggle.com/datasets/mariumfaheem666/spam-sms-classification-using-nlp
https://www.kaggle.com/datasets/adityakaranth/uci-sms-spam-collection-data-set
```