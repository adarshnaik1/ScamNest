"""
API endpoint tests for the Honeypot API.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def api_key():
    """Get API key from settings."""
    settings = get_settings()
    return settings.api_key


@pytest.fixture
def auth_headers(api_key):
    """Create authenticated headers."""
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Agentic Honeypot API"
        assert data["status"] == "running"
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAuthentication:
    """Test API key authentication."""
    
    def test_missing_api_key(self, client):
        """Test request without API key returns 401."""
        response = client.post(
            "/honeypot",
            json={
                "sessionId": "test-session",
                "message": {
                    "sender": "scammer",
                    "text": "Test message",
                    "timestamp": "2026-01-21T10:15:30Z",
                },
            },
        )
        assert response.status_code == 401
    
    def test_invalid_api_key(self, client):
        """Test request with invalid API key returns 401."""
        response = client.post(
            "/honeypot",
            headers={"x-api-key": "invalid-key"},
            json={
                "sessionId": "test-session",
                "message": {
                    "sender": "scammer",
                    "text": "Test message",
                    "timestamp": "2026-01-21T10:15:30Z",
                },
            },
        )
        assert response.status_code == 401
    
    def test_valid_api_key(self, client, auth_headers):
        """Test request with valid API key succeeds."""
        response = client.post(
            "/honeypot",
            headers=auth_headers,
            json={
                "sessionId": "test-valid-auth",
                "message": {
                    "sender": "scammer",
                    "text": "Test message",
                    "timestamp": "2026-01-21T10:15:30Z",
                },
            },
        )
        assert response.status_code == 200


class TestHoneypotEndpoint:
    """Test honeypot message handling."""
    
    def test_first_message(self, client, auth_headers):
        """Test handling first message in conversation."""
        response = client.post(
            "/honeypot",
            headers=auth_headers,
            json={
                "sessionId": "test-first-msg",
                "message": {
                    "sender": "scammer",
                    "text": "Your bank account will be blocked today. Verify immediately.",
                    "timestamp": "2026-01-21T10:15:30Z",
                },
                "conversationHistory": [],
                "metadata": {
                    "channel": "SMS",
                    "language": "English",
                    "locale": "IN",
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "reply" in data
        assert len(data["reply"]) > 0
    
    def test_follow_up_message(self, client, auth_headers):
        """Test handling follow-up message."""
        # First message
        client.post(
            "/honeypot",
            headers=auth_headers,
            json={
                "sessionId": "test-followup",
                "message": {
                    "sender": "scammer",
                    "text": "Your account is blocked.",
                    "timestamp": "2026-01-21T10:15:30Z",
                },
            },
        )
        
        # Follow-up message
        response = client.post(
            "/honeypot",
            headers=auth_headers,
            json={
                "sessionId": "test-followup",
                "message": {
                    "sender": "scammer",
                    "text": "Share your UPI ID to verify.",
                    "timestamp": "2026-01-21T10:17:30Z",
                },
                "conversationHistory": [
                    {
                        "sender": "scammer",
                        "text":  """ನಿಮ್ಮ ಬ್ಯಾಂಕ್ ಖಾತೆಯಲ್ಲಿ ಅನುಮಾನಾಸ್ಪದ ಚಟುವಟಿಕೆ ಕಂಡುಬಂದಿದೆ.
            ದಯವಿಟ್ಟು ತಕ್ಷಣ ಕೆಳಗಿನ ಲಿಂಕ್ ಕ್ಲಿಕ್ ಮಾಡಿ ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ
            """,
                        "timestamp": "2026-01-21T10:15:30Z",
                    },
                    {
                        "sender": "user",
                        "text": "What happened?",
                        "timestamp": "2026-01-21T10:16:30Z",
                    },
                ],
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_scam_detection(self, client, auth_headers):
        """Test scam is detected in suspicious messages."""
        # Send multiple scam-like messages
        messages = [
            "URGENT: Your account will be blocked!",
            "Share your OTP immediately to prevent suspension.",
            "Click this link to verify: http://malicious.com/verify",
            """ನಿಮ್ಮ ಬ್ಯಾಂಕ್ ಖಾತೆಯಲ್ಲಿ ಅನುಮಾನಾಸ್ಪದ ಚಟುವಟಿಕೆ ಕಂಡುಬಂದಿದೆ.
            ದಯವಿಟ್ಟು ತಕ್ಷಣ ಕೆಳಗಿನ ಲಿಂಕ್ ಕ್ಲಿಕ್ ಮಾಡಿ ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ
            """
        ]
        
        for i, msg in enumerate(messages):
            response = client.post(
                "/honeypot",
                headers=auth_headers,
                json={
                    "sessionId": "test-scam-detection",
                    "message": {
                        "sender": "scammer",
                        "text": msg,
                        "timestamp": f"2026-01-21T10:{15+i}:30Z",
                    },
                },
            )
            assert response.status_code == 200
        
        # Check session state
        session_response = client.get(
            "/session/test-scam-detection",
            headers=auth_headers,
        )
        
        assert session_response.status_code == 200
        session_data = session_response.json()
        
        # Verify scam was detected
        assert session_data["session"]["scamSuspected"] is True


class TestSessionManagement:
    """Test session management endpoints."""
    
    def test_get_session(self, client, auth_headers):
        """Test retrieving session state."""
        # Create session
        client.post(
            "/honeypot",
            headers=auth_headers,
            json={
                "sessionId": "test-get-session",
                "message": {
                    "sender": "scammer",
                    "text": "Test message",
                    "timestamp": "2026-01-21T10:15:30Z",
                },
            },
        )
        
        # Get session
        response = client.get(
            "/session/test-get-session",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["session"]["sessionId"] == "test-get-session"
    
    def test_get_nonexistent_session(self, client, auth_headers):
        """Test getting non-existent session."""
        response = client.get(
            "/session/nonexistent-session",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
    
    def test_delete_session(self, client, auth_headers):
        """Test deleting session."""
        # Create session
        client.post(
            "/honeypot",
            headers=auth_headers,
            json={
                "sessionId": "test-delete-session",
                "message": {
                    "sender": "scammer",
                    "text": "Test message",
                    "timestamp": "2026-01-21T10:15:30Z",
                },
            },
        )
        
        # Delete session
        response = client.delete(
            "/session/test-delete-session",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify deleted
        get_response = client.get(
            "/session/test-delete-session",
            headers=auth_headers,
        )
        assert get_response.json()["status"] == "error"
