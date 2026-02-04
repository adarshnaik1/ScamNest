"""
Unit tests for service modules.
"""

import pytest
from app.models.schemas import Message, SessionState, ExtractedIntelligence
from app.services.scam_detector_hybrid import ScamDetector
from app.services.intelligence_extractor import IntelligenceExtractor
from app.services.lang_detector import LanguageDetector


class TestLanguageDetector:
    """Test language detection service."""
    
    @pytest.fixture
    def detector(self):
        """Create language detector instance."""
        return LanguageDetector()
    
    def test_detect_english(self, detector):
        """Test detection of English text."""
        text = "Hello, how are you doing today?"
        assert detector.detect(text) == "en"
    
    def test_detect_hindi(self, detector):
        """Test detection of Hindi text."""
        # "Hello, how are you?" in Hindi
        text = "नमस्ते, आप कैसे हैं?"
        assert detector.detect(text) == "hi"
    
    def test_detect_mixed_with_confidence(self, detector):
        """Test detection with confidence scores."""
        text = "This is a predominently English sentence with some random words."
        results = detector.detect_with_confidence(text)
        assert len(results) > 0
        assert results[0]["lang"] == "en"
        assert results[0]["prob"] > 0.5

    def test_invalid_input(self, detector):
        """Test detection with invalid input."""
        assert detector.detect("") == "unknown"
        assert detector.detect("   ") == "unknown"
        assert detector.detect_with_confidence(None) == []


class TestScamDetector:
    """Test scam detection service."""
    
    @pytest.fixture
    def detector(self):
        """Create scam detector instance."""
        return ScamDetector()
    
    def test_detect_urgency(self, detector):
        """Test detection of urgency patterns."""
        message = Message(
            sender="scammer",
            text="URGENT: Act immediately or your account will be blocked!",
            timestamp="2026-01-21T10:15:30Z",
        )
        
        score, keywords = detector.analyze_message(message)
        
        assert score > 0.2
        assert any("urgent" in k.lower() for k in keywords)
    
    def test_detect_threats(self, detector):
        """Test detection of threat patterns."""
        message = Message(
            sender="scammer",
            text="Your account has been suspended due to suspicious activity.",
            timestamp="2026-01-21T10:15:30Z",
        )
        
        score, keywords = detector.analyze_message(message)
        
        assert score > 0.1
        assert any("suspend" in k.lower() for k in keywords)
    
    def test_detect_sensitive_data_request(self, detector):
        """Test detection of sensitive data requests."""
        message = Message(
            sender="scammer",
            text="Please share your OTP and UPI PIN for verification.",
            timestamp="2026-01-21T10:15:30Z",
        )
        
        score, keywords = detector.analyze_message(message)
        
        assert score > 0.2
        assert any(k.lower() in ["otp", "pin", "upi"] for k in keywords)
    
    def test_analyze_session(self, detector):
        """Test session analysis."""
        session = SessionState(
            sessionId="test-session",
            messages=[
                Message(
                    sender="scammer",
                    text="Your bank account will be blocked today!",
                    timestamp="2026-01-21T10:15:30Z",
                ),
                Message(
                    sender="user",
                    text="What happened?",
                    timestamp="2026-01-21T10:16:30Z",
                ),
                Message(
                    sender="scammer",
                    text="Share your OTP immediately to verify your identity.",
                    timestamp="2026-01-21T10:17:30Z",
                ),
            ],
        )
        
        confidence, suspected, confirmed, keywords = detector.analyze_session(session)
        
        assert confidence > 0.3
        assert suspected is True
        assert len(keywords) > 0
    
    def test_get_scam_type(self, detector):
        """Test scam type classification."""
        banking_keywords = ["bank", "account", "blocked"]
        assert detector.get_scam_type(banking_keywords) == "Banking Fraud"
        
        upi_keywords = ["upi", "paytm"]
        assert detector.get_scam_type(upi_keywords) == "UPI Fraud"
        
        lottery_keywords = ["prize", "winner"]
        assert detector.get_scam_type(lottery_keywords) == "Lottery/Prize Scam"


class TestIntelligenceExtractor:
    """Test intelligence extraction service."""
    
    @pytest.fixture
    def extractor(self):
        """Create intelligence extractor instance."""
        return IntelligenceExtractor()
    
    def test_extract_phone_numbers(self, extractor):
        """Test phone number extraction."""
        message = Message(
            sender="scammer",
            text="Call me at +91 9876543210 or 9123456789 for verification.",
            timestamp="2026-01-21T10:15:30Z",
        )
        
        intel = extractor.extract_from_message(message)
        
        assert len(intel.phoneNumbers) >= 1
        assert any("9876543210" in num for num in intel.phoneNumbers)
    
    def test_extract_upi_ids(self, extractor):
        """Test UPI ID extraction."""
        message = Message(
            sender="scammer",
            text="Send money to verify@paytm or scammer@upi",
            timestamp="2026-01-21T10:15:30Z",
        )
        
        intel = extractor.extract_from_message(message)
        
        assert len(intel.upiIds) >= 1
    
    def test_extract_links(self, extractor):
        """Test link extraction."""
        message = Message(
            sender="scammer",
            text="Click here to verify: https://malicious-site.com/phish and http://bad.link/steal",
            timestamp="2026-01-21T10:15:30Z",
        )
        
        intel = extractor.extract_from_message(message)
        
        assert len(intel.phishingLinks) >= 1
    
    def test_extract_keywords(self, extractor):
        """Test keyword extraction."""
        message = Message(
            sender="scammer",
            text="URGENT: Your account is blocked. Verify your KYC immediately to avoid penalty.",
            timestamp="2026-01-21T10:15:30Z",
        )
        
        intel = extractor.extract_from_message(message)
        
        assert "urgent" in intel.suspiciousKeywords
        assert "blocked" in intel.suspiciousKeywords
        assert "kyc" in intel.suspiciousKeywords
    
    def test_merge_intelligence(self, extractor):
        """Test intelligence merging."""
        intel1 = ExtractedIntelligence(
            phoneNumbers=["+919876543210"],
            upiIds=["test@upi"],
        )
        
        intel2 = ExtractedIntelligence(
            phoneNumbers=["+919123456789"],
            phishingLinks=["http://bad.com"],
        )
        
        merged = intel1.merge(intel2)
        
        assert len(merged.phoneNumbers) == 2
        assert len(merged.upiIds) == 1
        assert len(merged.phishingLinks) == 1
    
    def test_generate_agent_notes(self, extractor):
        """Test agent notes generation."""
        session = SessionState(
            sessionId="test-session",
            totalMessages=5,
            extractedIntelligence=ExtractedIntelligence(
                upiIds=["scammer@upi"],
                suspiciousKeywords=["urgent", "blocked", "upi"],
            ),
        )
        
        notes = extractor.generate_agent_notes(session, "Banking Fraud")
        
        assert "Banking Fraud" in notes
        assert "UPI IDs" in notes
        assert "5" in notes
