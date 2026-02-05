"""
Data masking and de-masking service for sensitive information.

Protects PII (Personally Identifiable Information) in logs, responses, and storage.
"""

import re
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class MaskingLevel(str, Enum):
    """Masking sensitivity levels."""
    FULL = "full"  # Mask all characters except last 4
    PARTIAL = "partial"  # Mask middle portion
    MINIMAL = "minimal"  # Mask first few characters


class DataMasker:
    """
    Masks and de-masks sensitive data for security and compliance.

    Use Cases:
    - Logging: Mask API keys, tokens, phone numbers
    - Responses: Protect extracted intelligence in public APIs
    - Storage: Comply with GDPR/CCPA data protection
    - Monitoring: Safe display of sensitive patterns
    """

    # Patterns for detecting sensitive data
    API_KEY_PATTERN = re.compile(r'(?:^|[^a-zA-Z0-9])([A-Za-z0-9_-]{20,}|sk-[a-zA-Z0-9]{20,})', re.IGNORECASE)
    UPI_ID_PATTERN = re.compile(r'\b([a-zA-Z0-9._-]+)@([a-zA-Z]+)\b')
    PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})')
    BANK_ACCOUNT_PATTERN = re.compile(r'\b(\d{4})(\d+)(\d{4})\b')
    EMAIL_PATTERN = re.compile(r'\b([a-zA-Z0-9._-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b')

    # Headers that should never be logged
    SENSITIVE_HEADERS = {
        'x-api-key', 'authorization', 'x-auth-token',
        'api-key', 'api_key', 'apikey'
    }

    @staticmethod
    def mask_api_key(api_key: str, level: MaskingLevel = MaskingLevel.FULL) -> str:
        """
        Mask API key for safe logging.

        Examples:
            sk-proj-abc123...xyz789 -> sk-proj-***...xyz789 (FULL)
            ABC-1234-DEF-5678 -> ABC-****-***-5678 (PARTIAL)
        """
        if not api_key or len(api_key) < 8:
            return "***"

        if level == MaskingLevel.FULL:
            # Show prefix and last 4
            if api_key.startswith("sk-"):
                return f"{api_key[:8]}...{api_key[-6:]}"
            return f"{api_key[:4]}...{api_key[-4:]}"

        elif level == MaskingLevel.PARTIAL:
            # Mask middle portion
            visible = len(api_key) // 4
            return api_key[:visible] + "*" * (len(api_key) - 2 * visible) + api_key[-visible:]

        else:  # MINIMAL
            return api_key[:8] + "*" * min(4, len(api_key) - 8)

    @staticmethod
    def mask_phone_number(phone: str, level: MaskingLevel = MaskingLevel.PARTIAL) -> str:
        """
        Mask phone number for safe display.

        Examples:
            +91-9876543210 -> +91-98***43210 (PARTIAL)
            +91-9876543210 -> +91-******3210 (FULL)
        """
        if not phone:
            return ""

        # Extract digits
        digits = re.sub(r'[^\d]', '', phone)

        if len(digits) < 6:
            return "*" * len(digits)

        if level == MaskingLevel.FULL:
            # Show country code and last 4
            if phone.startswith('+'):
                return f"+{digits[:2]}******{digits[-4:]}"
            return f"******{digits[-4:]}"

        elif level == MaskingLevel.PARTIAL:
            # Show first 2 and last 4
            if phone.startswith('+'):
                return f"+{digits[:2]}-{digits[2:4]}***{digits[-4:]}"
            return f"{digits[:2]}***{digits[-4:]}"

        else:  # MINIMAL
            return phone[:6] + "*" * (len(phone) - 6)

    @staticmethod
    def mask_upi_id(upi_id: str, level: MaskingLevel = MaskingLevel.PARTIAL) -> str:
        """
        Mask UPI ID for safe display.

        Examples:
            user@paytm -> u***@paytm (PARTIAL)
            9876543210@okicici -> 98***10@okicici (PARTIAL)
        """
        if not upi_id or '@' not in upi_id:
            return "***@***"

        username, domain = upi_id.split('@', 1)

        if level == MaskingLevel.FULL:
            return f"{username[0]}***@{domain}"

        elif level == MaskingLevel.PARTIAL:
            if len(username) <= 4:
                return f"{username[0]}***@{domain}"
            return f"{username[:2]}***{username[-2:]}@{domain}"

        else:  # MINIMAL
            return f"{username[:3]}***@{domain}"

    @staticmethod
    def mask_bank_account(account: str, level: MaskingLevel = MaskingLevel.FULL) -> str:
        """
        Mask bank account number.

        Examples:
            123456789012 -> ****6789012 (FULL)
            123456789012 -> 1234***9012 (PARTIAL)
        """
        if not account or len(account) < 8:
            return "****"

        if level == MaskingLevel.FULL:
            return "*" * (len(account) - 4) + account[-4:]

        elif level == MaskingLevel.PARTIAL:
            return account[:4] + "*" * (len(account) - 8) + account[-4:]

        else:  # MINIMAL
            return account[:6] + "*" * (len(account) - 6)

    @staticmethod
    def mask_email(email: str, level: MaskingLevel = MaskingLevel.PARTIAL) -> str:
        """
        Mask email address.

        Examples:
            user@example.com -> u***@example.com (PARTIAL)
            john.doe@example.com -> j***@example.com (FULL)
        """
        if not email or '@' not in email:
            return "***@***.com"

        username, domain = email.split('@', 1)

        if level == MaskingLevel.FULL:
            return f"{username[0]}***@{domain}"

        elif level == MaskingLevel.PARTIAL:
            if len(username) <= 3:
                return f"{username[0]}***@{domain}"
            return f"{username[:2]}***{username[-1]}@{domain}"

        else:  # MINIMAL
            return f"{username[:4]}***@{domain}"

    @classmethod
    def mask_intelligence(
        cls,
        intelligence: Dict[str, List[str]],
        level: MaskingLevel = MaskingLevel.PARTIAL
    ) -> Dict[str, List[str]]:
        """
        Mask extracted intelligence for safe logging/display.

        Args:
            intelligence: ExtractedIntelligence dict with lists of data
            level: Masking level to apply

        Returns:
            Masked intelligence dict with same structure
        """
        masked = {}

        # Mask UPI IDs
        if "upiIds" in intelligence:
            masked["upiIds"] = [cls.mask_upi_id(upi, level) for upi in intelligence["upiIds"]]

        # Mask phone numbers
        if "phoneNumbers" in intelligence:
            masked["phoneNumbers"] = [cls.mask_phone_number(phone, level) for phone in intelligence["phoneNumbers"]]

        # Mask bank accounts
        if "bankAccounts" in intelligence:
            masked["bankAccounts"] = [cls.mask_bank_account(acc, level) for acc in intelligence["bankAccounts"]]

        # Keep phishing links and keywords unmasked (they're threats, not PII)
        if "phishingLinks" in intelligence:
            masked["phishingLinks"] = intelligence["phishingLinks"]

        if "suspiciousKeywords" in intelligence:
            masked["suspiciousKeywords"] = intelligence["suspiciousKeywords"]

        return masked

    @classmethod
    def mask_text(cls, text: str, level: MaskingLevel = MaskingLevel.PARTIAL) -> str:
        """
        Mask all sensitive patterns in arbitrary text.

        Use for:
        - Logging user messages
        - Error messages
        - Debug output
        """
        if not text:
            return ""

        masked_text = text

        # Mask phone numbers
        masked_text = cls.PHONE_PATTERN.sub(
            lambda m: cls.mask_phone_number(m.group(0), level),
            masked_text
        )

        # Mask UPI IDs
        masked_text = cls.UPI_ID_PATTERN.sub(
            lambda m: cls.mask_upi_id(m.group(0), level),
            masked_text
        )

        # Mask emails
        masked_text = cls.EMAIL_PATTERN.sub(
            lambda m: cls.mask_email(m.group(0), level),
            masked_text
        )

        return masked_text

    @classmethod
    def mask_request_headers(cls, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Mask sensitive headers for safe logging.

        Args:
            headers: Request headers dict

        Returns:
            Masked headers dict
        """
        masked = {}
        for key, value in headers.items():
            if key.lower() in cls.SENSITIVE_HEADERS:
                masked[key] = cls.mask_api_key(value, MaskingLevel.FULL)
            else:
                masked[key] = value
        return masked

    @staticmethod
    def should_mask_for_context(context: str) -> bool:
        """
        Determine if masking is needed based on context.

        Args:
            context: 'logging', 'api_response', 'callback', 'storage', 'internal'

        Returns:
            True if masking should be applied
        """
        mask_contexts = {'logging', 'api_response', 'storage'}
        no_mask_contexts = {'callback', 'internal'}  # Full data needed

        return context in mask_contexts


class DemaskedData:
    """
    Container for temporarily de-masked sensitive data.

    Ensures data is properly handled and not accidentally logged.
    """

    def __init__(self, data: Any):
        """Initialize with sensitive data."""
        self._data = data
        self._accessed = False

    def get(self) -> Any:
        """
        Get de-masked data (use carefully).

        Returns:
            Original unmasked data
        """
        self._accessed = True
        logger.debug("Sensitive data accessed (de-masked)")
        return self._data

    def __repr__(self) -> str:
        """Prevent accidental logging of sensitive data."""
        return "<DemaskedData: [REDACTED]>"

    def __str__(self) -> str:
        """Prevent accidental printing."""
        return "[SENSITIVE DATA - USE .get() TO ACCESS]"


# Convenience functions for common use cases
def mask_for_logging(text: str) -> str:
    """Quick mask for logging contexts."""
    return DataMasker.mask_text(text, MaskingLevel.PARTIAL)


def mask_for_api_response(intelligence: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Mask intelligence for public API responses."""
    return DataMasker.mask_intelligence(intelligence, MaskingLevel.PARTIAL)


def mask_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Mask sensitive headers."""
    return DataMasker.mask_request_headers(headers)
