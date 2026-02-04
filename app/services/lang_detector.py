from langdetect import detect, detect_langs, DetectorFactory
from typing import List, Dict, Any

# Ensure consistent results
DetectorFactory.seed = 0

class LanguageDetector:
    def detect(self, text: str) -> str:
        """
        Detects the language of the input text.
        Returns the language code (e.g., 'en', 'fr') or 'unknown' on failure.
        """
        try:
            if not text or not text.strip():
                return "unknown"
            return detect(text)
        except Exception:
            return "unknown"

    def detect_with_confidence(self, text: str) -> List[Dict[str, Any]]:
        """
        Detects the language and returns a list of possibilities with confidence scores.
        """
        try:
            if not text or not text.strip():
                return []
            
            results = detect_langs(text)
            return [{"lang": r.lang, "prob": r.prob} for r in results]
        except Exception:
            return []


