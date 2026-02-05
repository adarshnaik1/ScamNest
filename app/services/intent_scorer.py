"""
Intent scoring service for detecting scam intent patterns.

This is a lightweight NLP layer that detects financial scam intent through:
- Financial entity detection (UPI, bank, account)
- Action request detection (share, send, verify)
- Coercion/threat language
- Urgency signals

Used as a secondary layer when ML confidence is low or medium.
"""

import re
import unicodedata
from typing import Dict, List, Tuple


class IntentScorer:
    """
    Lightweight intent-based risk scorer for India-specific financial scams.

    This service provides a risk score (0.0-1.0) based on scam intent patterns,
    acting as a safety net when ML predictions are uncertain.

    Includes evasion defense:
    - Unicode normalization
    - Character spacing removal ("U P I" → "UPI")
    - Homoglyph detection
    """

    # Common homoglyphs (lookalike characters used in evasion)
    HOMOGLYPHS = {
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',  # Cyrillic
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e',  # Fullwidth
        '0': 'o', '1': 'i', '3': 'e', '5': 's', '7': 't',  # Number lookalikes
    }

    # Financial entities (India-specific)
    FINANCIAL_ENTITIES = [
        r'\bupi\b',
        r'\bbank(?:\s+account)?\b',
        r'\baccount(?:\s+number)?\b',
        r'\bcard\b',
        r'\bwallet\b',
        r'\bpaytm\b',
        r'\bgpay\b',
        r'\bphonepe\b',
        r'\bamazon\s+pay\b',
        r'\bifsc\b',
        r'\baadhaar\b',
        r'\bpan\b',
        r'\bkyc\b',
        r'\bdebit\b',
        r'\bcredit\b',
        r'\batm\b',
        r'\bnetbanking\b',
        r'\bmobile\s+banking\b',
    ]

    # Action requests that require user to do something
    ACTION_REQUESTS = [
        r'\bshare\b',
        r'\bsend\b',
        r'\bverif(?:y|ied)\b',
        r'\bupdat(?:e|ed)\b',
        r'\bprovid(?:e|ed)\b',
        r'\bconfirm(?:ed)?\b',
        r'\benter(?:ed)?\b',
        r'\bsubmit(?:ted)?\b',
        r'\bclick(?:ed)?\b',
        r'\btransfer(?:red)?\b',
        r'\bpa(?:y|id)\b',
        r'\bcomplete\b',
        r'\bfill\b',
        r'\bregister(?:ed)?\b',
    ]

    # Coercion/threat language
    COERCION_PATTERNS = [
        r'\bblock(?:ed)?\b',
        r'\bsuspend(?:ed)?\b',
        r'\bdeactivat(?:e|ed)\b',
        r'\bfreez(?:e|ing)\b',
        r'\bclose[ds]?\b',
        r'\bterminate[ds]?\b',
        r'\bcancel(?:led)?\b',
        r'\bexpir(?:e|ed|ing)\b',
        r'\bavoid\s+(?:suspension|blocking|deactivation)\b',
        r'\bprevent\s+(?:suspension|blocking|closure)\b',
        r'\blegal\s+action\b',
        r'\bpolice\b',
        r'\barrest(?:ed)?\b',
        r'\bcourt\b',
        r'\bpenalt(?:y|ies)\b',
        r'\bfin(?:e|ed)\b',
        r'\bwarrant\b',
        r'\binvestigation\b',
    ]

    # Urgency signals
    URGENCY_SIGNALS = [
        r'\bimmediately\b',
        r'\btoday\b',
        r'\bnow\b',
        r'\bwithin\s+\d+\s+(?:hours?|minutes?)\b',
        r'\bquickly\b',
        r'\basap\b',
        r'\bfast\b',
        r'\bhurry\b',
        r'\blast\s+(?:chance|warning|reminder)\b',
        r'\bfinal\s+(?:notice|warning|reminder)\b',
        r'\blimited\s+time\b',
        r'\bexpir(?:e|es|ing)\s+(?:today|soon|in)\b',
        r'\bdeadline\b',
        r'\b(?:only|just)\s+\d+\s+(?:hours?|minutes?)\b',
    ]

    # Authority/legitimacy claims
    AUTHORITY_CLAIMS = [
        r'\bofficial\b',
        r'\bauthorized\b',
        r'\bverified\b',
        r'\bcustomer\s+(?:care|service|support)\b',
        r'\bsupport\s+team\b',
        r'\bsecurity\s+(?:team|department)\b',
        r'\brbi\b',
        r'\breserve\s+bank\b',
        r'\bgovernment\b',
        r'\bdepartment\b',
        r'\bheadquarters?\b',
    ]

    # Suspicious UPI-specific patterns
    UPI_SCAM_PATTERNS = [
        r'share.*upi',
        r'send.*upi',
        r'upi.*(?:id|pin|password)',
        r'verify.*upi',
        r'update.*upi',
        r'confirm.*upi',
        r'upi.*(?:blocked|suspended|deactivated)',
        r'reactivate.*upi',
        r'link.*upi',
    ]

    def __init__(self):
        """Initialize intent scorer with compiled patterns."""
        self._compile_patterns()

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text to defend against evasion tactics.

        Handles:
        - Character spacing: "U P I" → "UPI"
        - Unicode normalization: fancy chars → standard ASCII
        - Homoglyphs: lookalike chars → standard chars
        - Case normalization
        """
        # Unicode normalization (NFKD = compatibility decomposition)
        text = unicodedata.normalize('NFKD', text)

        # Remove combining marks
        text = ''.join(c for c in text if not unicodedata.combining(c))

        # Replace homoglyphs
        for homoglyph, standard in self.HOMOGLYPHS.items():
            text = text.replace(homoglyph, standard)

        # Collapse excessive spacing between alphanumeric characters
        # "U P I" → "UPI", "a c c o u n t" → "account"
        text = re.sub(r'(?<=\w)\s+(?=\w)', '', text)

        # Normalize multiple spaces to single space
        text = re.sub(r'\s+', ' ', text)

        # Strip and lowercase
        return text.strip().lower()

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching."""
        self.financial_re = [re.compile(p, re.IGNORECASE) for p in self.FINANCIAL_ENTITIES]
        self.action_re = [re.compile(p, re.IGNORECASE) for p in self.ACTION_REQUESTS]
        self.coercion_re = [re.compile(p, re.IGNORECASE) for p in self.COERCION_PATTERNS]
        self.urgency_re = [re.compile(p, re.IGNORECASE) for p in self.URGENCY_SIGNALS]
        self.authority_re = [re.compile(p, re.IGNORECASE) for p in self.AUTHORITY_CLAIMS]
        self.upi_scam_re = [re.compile(p, re.IGNORECASE) for p in self.UPI_SCAM_PATTERNS]

    def _count_matches(self, text: str, patterns: List[re.Pattern]) -> int:
        """Count pattern matches in text."""
        return sum(1 for pattern in patterns if pattern.search(text))

    def _extract_matches(self, text: str, patterns: List[re.Pattern]) -> List[str]:
        """Extract matched patterns from text."""
        matches = []
        for pattern in patterns:
            found = pattern.findall(text)
            if found:
                matches.extend([m if isinstance(m, str) else m[0] for m in found])
        return list(set(matches))

    def calculate_intent_score(self, text: str) -> Tuple[float, Dict[str, any]]:
        """
        Calculate intent-based risk score for the given text.

        Returns:
            Tuple of (risk_score, details_dict)
            - risk_score: float between 0.0 and 1.0
            - details_dict: breakdown of scoring factors
        """
        # Apply evasion defense normalization
        text_normalized = self._normalize_text(text)
        text_lower = text_normalized  # Already lowercased in normalization
        # Extract matches for logging/explainability
        financial_matches = self._extract_matches(text_lower, self.financial_re)
        action_matches = self._extract_matches(text_lower, self.action_re)
        coercion_matches = self._extract_matches(text_lower, self.coercion_re)
        urgency_matches = self._extract_matches(text_lower, self.urgency_re)
        authority_matches = self._extract_matches(text_lower, self.authority_re)
        upi_scam_matches = self._extract_matches(text_lower, self.upi_scam_re)

        # Count the matches
        financial_count = len(financial_matches)
        action_count = len(action_matches)
        coercion_count = len(coercion_matches)
        urgency_count = len(urgency_matches)
        authority_count = len(authority_matches)
        upi_scam_count = len(upi_scam_matches)

        # Calculate component scores
        # Financial entities: 0.0-0.25
        financial_score = min(financial_count * 0.08, 0.25)

        # Action requests: 0.0-0.20
        action_score = min(action_count * 0.07, 0.20)

        # Coercion/threats: 0.0-0.30 (highest weight as strong scam indicator)
        coercion_score = min(coercion_count * 0.10, 0.30)

        # Urgency signals: 0.0-0.15
        urgency_score = min(urgency_count * 0.05, 0.15)

        # Authority claims: 0.0-0.10
        authority_score = min(authority_count * 0.05, 0.10)

        # UPI-specific scam patterns: 0.0-0.20 (direct hit bonus)
        upi_scam_score = min(upi_scam_count * 0.15, 0.20)

        # Combination bonuses (when multiple categories present)
        combination_bonus = 0.0

        # Financial + Action: asking to do something with money
        if financial_count > 0 and action_count > 0:
            combination_bonus += 0.10

        # Financial + Coercion: threatening financial loss
        if financial_count > 0 and coercion_count > 0:
            combination_bonus += 0.15

        # Action + Urgency: pressuring immediate action
        if action_count > 0 and urgency_count > 0:
            combination_bonus += 0.08

        # Triple threat: financial + action + (coercion OR urgency)
        if financial_count > 0 and action_count > 0 and (coercion_count > 0 or urgency_count > 0):
            combination_bonus += 0.12

        # Total intent score (capped at 1.0)
        base_score = (
            financial_score +
            action_score +
            coercion_score +
            urgency_score +
            authority_score +
            upi_scam_score
        )

        total_score = min(base_score + combination_bonus, 1.0)

        # Build details for explainability
        details = {
            "intent_score": round(total_score, 4),
            "components": {
                "financial": round(financial_score, 4),
                "action": round(action_score, 4),
                "coercion": round(coercion_score, 4),
                "urgency": round(urgency_score, 4),
                "authority": round(authority_score, 4),
                "upi_scam": round(upi_scam_score, 4),
                "combination_bonus": round(combination_bonus, 4),
            },
            "matches": {
                "financial": financial_matches[:5],  # limit for readability
                "action": action_matches[:5],
                "coercion": coercion_matches[:5],
                "urgency": urgency_matches[:5],
            },
            "pattern_counts": {
                "financial": financial_count,
                "action": action_count,
                "coercion": coercion_count,
                "urgency": urgency_count,
                "authority": authority_count,
                "upi_scam": upi_scam_count,
            }
        }

        return total_score, details

    def is_high_intent_risk(self, text: str, threshold: float = 0.5) -> bool:
        """
        Quick check if text has high intent risk.

        Args:
            text: Message text to analyze
            threshold: Risk threshold (default 0.5)

        Returns:
            True if intent score >= threshold
        """
        score, _ = self.calculate_intent_score(text)
        return score >= threshold
