"""
Scam detection service using pattern matching and AI analysis.
"""

import re
from typing import Tuple, List
from ..models.schemas import Message, SessionState
import joblib

class ScamDetector:
    """
    Detects scam patterns in messages using rule-based and AI analysis.
    """
    
    # Suspicious keyword patterns
    URGENCY_PATTERNS = [
        r'\burgent\b',
        r'\bimmediately\b',
        r'\btoday\b',
        r'\bnow\b',
        r'\basap\b',
        r'\bquick\b',
        r'\bfast\b',
        r'\bhurry\b',
        r'\blast\s+chance\b',
        r'\blimited\s+time\b',
        r'\bexpir(?:e|ing|ed)\b',  # already good
    ]

    THREAT_PATTERNS = [
        r'\bblock(?:ed)?\b',
        r'\bsuspend(?:ed)?\b',
        r'\bdeactivat(?:e|ed)\b',
        r'\bfreez(?:e|ing)\b',
        r'\bclose[ds]?\b',  # already good (d/s variation)
        r'\blegal\s+action\b',
        r'\barrest(?:ed)?\b',
        r'\bpolice\b',
        r'\bcourt\b',
        r'\bpenalt(?:y|ies)\b',  # added plural variation
        r'\bfin(?:e|ed)\b',  # can be "fine" or "fined"
        r'\bwarrant(?:ed)?\b',
    ]

    REQUEST_PATTERNS = [
        r'\bverif(?:y|ied)\b',  # verify / verified
        r'\bconfirm(?:ed)?\b',
        r'\bupdat(?:e|ed)\b',  # update / updated
        r'\bprovid(?:e|ed)\b',  # provide / provided
        r'\bshar(?:e|ed)\b',  # share / shared
        r'\bsend(?:ing|(?:t|ed))\b',  # send / sending / sent
        r'\btransfer(?:red)?\b',  # transfer / transferred
        r'\bpa(?:y|id)\b',  # pay / paid
        r'\bclick(?:ed)?\b',
        r'\blink\b',
        r'\benter(?:ed)?\b',
    ]

    SENSITIVE_DATA_PATTERNS = [
        r'\botp\b',
        r'\bpin\b',
        r'\bpassword\b',
        r'\bcvv\b',
        r'\bcard\s+number\b',
        r'\baccount\s+number\b',
        r'\bbank\s+details\b',
        r'\bupi\b',
        r'\baadhaar\b',
        r'\bpan\b',
        r'\bkyc\b',
        # These are mostly nouns → no natural past tense forms to add
    ]

    IMPERSONATION_PATTERNS = [
        r'\bbank\b',
        r'\brbi\b',
        r'\bsbi\b',
        r'\bhdfc\b',
        r'\bicici\b',
        r'\baxis\b',
        r'\bpaytm\b',
        r'\bgpay\b',
        r'\bphonepe\b',
        r'\bamazon\b',
        r'\bflipkart\b',
        r'\bcustomer\s+(?:care|service)\b',
        r'\bgovernment\b',
        r'\bofficial\b',
        r'\bauthorized\b',
        r'\bofficials?\b',  # minor addition
        # Mostly proper nouns / adjectives → limited past-tense forms
    ]

    MONEY_PATTERNS = [
        r'₹\s*\d+(?:\.\d+)?',  # improved: allow decimals
        r'\brs\.?\s*\d+(?:\.\d+)?',
        r'\brupees?\b',
        r'\binr\b',
        r'\blakh\b',
        r'\bcrore\b',
        r'\bprize\b',
        r'\blotter(?:y|ies)\b',
        r'\bwinner\b',
        r'\bcashback\b',
        r'\breward\b',
        r'\bbonus\b',
        r'\bamount\b',  # sometimes scammers say "amount"
    ]

    def __init__(self):
        """Initialize the scam detector with compiled patterns."""
        self.model=joblib.load('app/ai_model/models/spam_model.pkl')
        self.vectorizer=joblib.load('app/ai_model/models/tfidf_vectorizer.pkl')
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching."""
        self.urgency_re = [re.compile(p, re.IGNORECASE) for p in self.URGENCY_PATTERNS]
        self.threat_re = [re.compile(p, re.IGNORECASE) for p in self.THREAT_PATTERNS]
        self.request_re = [re.compile(p, re.IGNORECASE) for p in self.REQUEST_PATTERNS]
        self.sensitive_re = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_DATA_PATTERNS]
        self.impersonation_re = [re.compile(p, re.IGNORECASE) for p in self.IMPERSONATION_PATTERNS]
        self.money_re = [re.compile(p, re.IGNORECASE) for p in self.MONEY_PATTERNS]

    def _count_pattern_matches(self, text: str, patterns: List[re.Pattern]) -> int:
        """Count number of pattern matches in text."""
        return sum(1 for pattern in patterns if pattern.search(text))

    def _extract_matched_keywords(self, text: str, patterns: List[re.Pattern]) -> List[str]:
        """Extract matched keywords from text."""
        keywords = []
        for pattern in patterns:
            matches = pattern.findall(text)
            keywords.extend(matches)
        return list(set(keywords))

    def analyze_message(self, message: Message) -> Tuple[float, List[str]]:
        """
        Analyze a single message for scam indicators.
        Returns: (confidence_score, list of suspicious keywords)
        """
        text = message.text.lower()
        rule_score = 0.0
        keywords = []

        # 1. Rule-based detection (Keyword patterns)
        # Check urgency patterns (weight: 0.15)
        urgency_count = self._count_pattern_matches(text, self.urgency_re)
        if urgency_count > 0:
            rule_score += min(urgency_count * 0.05, 0.15)
            keywords.extend(self._extract_matched_keywords(text, self.urgency_re))

        # Check threat patterns (weight: 0.25)
        threat_count = self._count_pattern_matches(text, self.threat_re)
        if threat_count > 0:
            rule_score += min(threat_count * 0.08, 0.25)
            keywords.extend(self._extract_matched_keywords(text, self.threat_re))

        # Check request patterns (weight: 0.15)
        request_count = self._count_pattern_matches(text, self.request_re)
        if request_count > 0:
            rule_score += min(request_count * 0.05, 0.15)
            keywords.extend(self._extract_matched_keywords(text, self.request_re))

        # Check sensitive data patterns (weight: 0.25)
        sensitive_count = self._count_pattern_matches(text, self.sensitive_re)
        if sensitive_count > 0:
            rule_score += min(sensitive_count * 0.08, 0.25)
            keywords.extend(self._extract_matched_keywords(text, self.sensitive_re))

        # Check impersonation patterns (weight: 0.10)
        impersonation_count = self._count_pattern_matches(text, self.impersonation_re)
        if impersonation_count > 0:
            rule_score += min(impersonation_count * 0.05, 0.10)
            keywords.extend(self._extract_matched_keywords(text, self.impersonation_re))

        # Check money-related patterns (weight: 0.10)
        money_count = self._count_pattern_matches(text, self.money_re)
        if money_count > 0:
            rule_score += min(money_count * 0.05, 0.10)
            keywords.extend(self._extract_matched_keywords(text, self.money_re))

        # 2. ML-based detection
        ml_score = 0.0
        try:
            # Vectorize text and predict probability
            features = self.vectorizer.transform([text])
            probs = self.model.predict_proba(features)[0]
            # based on notebook: 0 is spam, 1 is ham
            ml_score = probs[0]
        except Exception:
            # Fallback to 0 if ML fails
            pass

        # 3. Combine scores (Hybrid approach)
        # Use ML as primary, rules as verification/boost
        final_score = max(rule_score, ml_score)

        return min(final_score, 1.0), list(set(keywords))

    def analyze_session(self, session: SessionState) -> Tuple[float, bool, bool, List[str]]:
        """
        Analyze entire session for scam patterns.
        Returns: (confidence_score, is_suspected, is_confirmed, all_keywords)
        """
        total_score = 0.0
        all_keywords = []
        message_count = 0

        # Analyze all messages from scammer
        for msg in session.messages:
            if msg.sender.lower() == "scammer":
                msg_score, msg_keywords = self.analyze_message(msg)
                total_score += msg_score
                all_keywords.extend(msg_keywords)
                message_count += 1

        # Calculate average score
        avg_score = total_score / max(message_count, 1)

        # Boost score if multiple indicators found across messages
        diversity_bonus = min(len(set(all_keywords)) * 0.02, 0.2)
        final_score = min(avg_score + diversity_bonus, 1.0)

        # Determine status (use averaged session confidence)
        # Suspected if >= 0.3, confirmed if >= 0.51 with at least 2 scammer messages
        is_suspected = bool(final_score >= 0.3)
        is_confirmed = bool(final_score >= 0.51 and message_count >= 2)

        return final_score, is_suspected, is_confirmed, list(set(all_keywords))

    def get_scam_type(self, keywords: List[str]) -> str:
        """Determine the type of scam based on keywords."""
        keyword_set = set(k.lower() for k in keywords)

        if any(k in keyword_set for k in ['bank', 'account', 'blocked', 'suspended']):
            return "Banking Fraud"
        elif any(k in keyword_set for k in ['otp', 'pin', 'password', 'cvv']):
            return "Credential Phishing"
        elif any(k in keyword_set for k in ['prize', 'lottery', 'winner', 'reward']):
            return "Lottery/Prize Scam"
        elif any(k in keyword_set for k in ['upi', 'paytm', 'gpay', 'phonepe']):
            return "UPI Fraud"
        elif any(k in keyword_set for k in ['kyc', 'aadhaar', 'pan']):
            return "KYC Fraud"
        else:
            return "General Scam"
