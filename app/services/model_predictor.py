"""
Lightweight model predictor wrapper.

Tries to load ML models if available; otherwise falls back to rule-based
scoring via the existing `ScamDetector` service for preliminary intent.
"""
from typing import Tuple, Optional, List
import os
import logging

try:
    import joblib
except Exception:
    joblib = None

try:
    from scipy.sparse import hstack
    from scipy.sparse import csr_matrix
except Exception:
    hstack = None
    csr_matrix = None

import numpy as np
from ..models.schemas import Message
from .scam_detector import ScamDetector as RuleScamDetector

logger = logging.getLogger(__name__)


class ModelPredictor:
    """Wrapper for ML-based preliminary intent detection with TF-IDF + models.

    Expected artifact keys (artifact_paths):
      - logistic: path to logistic regression pkl
      - rf: path to random forest pkl
      - tfidf_scam: path to TF-IDF vectorizer for scam message
      - tfidf_response: path to TF-IDF vectorizer for user response
      - preprocessor: path to preprocessor object (with methods used below)
      - safe_numerical_features: path to list of numerical feature names (pkl/json)

    If any required artifacts are missing or imports unavailable, the predictor
    will fall back to the provided `ScamDetector` rule-based scoring.
    """

    def __init__(
        self,
        scam_detector,
        artifact_paths: Optional[dict] = None,
        ensemble_threshold: float = 0.5,
    ):
        self.scam_detector = scam_detector
        self.artifact_paths = artifact_paths or {}
        self.ensemble_threshold = ensemble_threshold

        # ML artifacts
        self.logistic = None
        self.rf = None
        self.tfidf_scam = None
        self.tfidf_response = None
        self.preprocessor = None
        self.safe_numerical_features: List[str] = []

        self.ml_available = False

        # Try to load artifacts if joblib available
        if joblib and hstack and csr_matrix:
            try:
                # models
                lr_path = self.artifact_paths.get("logistic")
                rf_path = self.artifact_paths.get("rf")
                if lr_path and os.path.exists(lr_path):
                    self.logistic = joblib.load(lr_path)
                if rf_path and os.path.exists(rf_path):
                    self.rf = joblib.load(rf_path)

                # tfidf and preprocessor
                ts_path = self.artifact_paths.get("tfidf_scam")
                tr_path = self.artifact_paths.get("tfidf_response")
                pp_path = self.artifact_paths.get("preprocessor")
                snf_path = self.artifact_paths.get("safe_numerical_features")

                if ts_path and os.path.exists(ts_path):
                    self.tfidf_scam = joblib.load(ts_path)
                if tr_path and os.path.exists(tr_path):
                    self.tfidf_response = joblib.load(tr_path)
                if pp_path and os.path.exists(pp_path):
                    self.preprocessor = joblib.load(pp_path)
                if snf_path and os.path.exists(snf_path):
                    try:
                        self.safe_numerical_features = joblib.load(snf_path)
                    except Exception:
                        # try loading as text lines
                        with open(snf_path, "r", encoding="utf-8") as f:
                            self.safe_numerical_features = [l.strip() for l in f if l.strip()]

                # mark ml_available only if all core artifacts are present
                if (
                    self.logistic is not None
                    and self.rf is not None
                    and self.tfidf_scam is not None
                    and self.tfidf_response is not None
                    and self.preprocessor is not None
                ):
                    self.ml_available = True
                    logger.info("ML artifacts loaded for ModelPredictor")
            except Exception as e:
                logger.warning(f"Failed to load ML artifacts: {e}")
        else:
            logger.debug("joblib or scipy unavailable; ML path disabled")

    def _prepare_features(self, scam_message: str, user_response: str):
        """Preprocess texts and build combined feature matrix for the models."""
        # Preprocess texts
        if self.preprocessor and hasattr(self.preprocessor, "advanced_preprocess"):
            scam_processed = self.preprocessor.advanced_preprocess(scam_message)
            response_processed = self.preprocessor.advanced_preprocess(user_response)
        else:
            scam_processed = scam_message.lower().strip()
            response_processed = user_response.lower().strip()

        # Numeric analysis
        if self.preprocessor and hasattr(self.preprocessor, "analyze_text_complexity"):
            scam_analysis = self.preprocessor.analyze_text_complexity(scam_message)
            response_analysis = self.preprocessor.analyze_text_complexity(user_response)
        else:
            scam_analysis = {}
            response_analysis = {}

        # TF-IDF transforms
        if self.tfidf_scam is None or self.tfidf_response is None:
            return None

        scam_tfidf = self.tfidf_scam.transform([scam_processed])
        response_tfidf = self.tfidf_response.transform([response_processed])

        # numerical features vector
        numerical = []
        for feature in self.safe_numerical_features:
            if feature in scam_analysis:
                numerical.append(scam_analysis.get(feature, 0))
            elif feature in response_analysis:
                numerical.append(response_analysis.get(feature, 0))
            else:
                numerical.append(0)

        # convert numerical to sparse row
        if csr_matrix:
            num_arr = csr_matrix(np.array([numerical]))
        else:
            num_arr = None

        if num_arr is None and (scam_tfidf is None or response_tfidf is None):
            return None

        if num_arr is not None:
            try:
                combined = hstack([scam_tfidf, response_tfidf, num_arr])
            except Exception:
                # fallback: ignore numerical
                combined = hstack([scam_tfidf, response_tfidf])
        else:
            combined = hstack([scam_tfidf, response_tfidf])

        return combined

    def is_possible_scam(self, message_text: str, user_response: str = "") -> Tuple[bool, float]:
        """Return (possible_scam, confidence).

        Uses ML ensemble when available; otherwise falls back to rule-based
        detection using `ScamDetector.analyze_message`.
        """
        if self.ml_available:
            try:
                features = self._prepare_features(message_text, user_response)
                if features is not None:
                    lr_proba = 0.0
                    rf_proba = 0.0
                    try:
                        lr_proba = float(self.logistic.predict_proba(features)[0][1])
                    except Exception:
                        logger.debug("Logistic predict_proba failed")
                    try:
                        rf_proba = float(self.rf.predict_proba(features)[0][1])
                    except Exception:
                        logger.debug("RF predict_proba failed")

                    ensemble = (lr_proba + rf_proba) / 2.0
                    possible = ensemble >= self.ensemble_threshold
                    return bool(possible), float(ensemble)
            except Exception as e:
                logger.warning(f"ML prediction error, falling back: {e}")

        # fallback: rule-based single message score
        try:
            msg = Message(sender="scammer", text=message_text, timestamp="")
            score, _ = self.scam_detector.analyze_message(msg)
            possible = score >= 0.3
            return bool(possible), float(score)
        except Exception:
            return False, 0.0


class ScamDetector:
    """Lightweight ML-backed scam detector that loads artifacts and
    exposes a simple `is_possible_scam(message: str) -> dict` API.

    Loads the TF-IDF vectorizer and the trained model from the
    `app/model_artifacts/` directory using joblib. This class purposely
    isolates loading and inference and provides safe error handling so
    the application can continue if artifacts are missing.
    """

    def __init__(self, model_path: Optional[str] = None, tfidf_path: Optional[str] = None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        default_model = os.path.join(base_dir, "model_artifacts", "scam_detection_model.pkl")
        default_tfidf = os.path.join(base_dir, "model_artifacts", "tfidf_scam.pkl")

        self.model_path = model_path or default_model
        self.tfidf_path = tfidf_path or default_tfidf

        self.model = None
        self.tfidf = None
        self.ready = False

        self._load_artifacts()

    def _load_artifacts(self):
        if joblib is None:
            logger.warning("joblib not available; ML scam detector disabled")
            return

        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                logger.info(f"Model artifact not found at {self.model_path}")

            if os.path.exists(self.tfidf_path):
                self.tfidf = joblib.load(self.tfidf_path)
            else:
                logger.info(f"TF-IDF artifact not found at {self.tfidf_path}")

            if self.model is not None and self.tfidf is not None:
                self.ready = True
                logger.info("ML ScamDetector: artifacts loaded and ready")
        except Exception as e:
            logger.exception("Failed to load ML artifacts for ScamDetector: %s", e)
            self.ready = False

    def is_possible_scam(self, message: str) -> dict:
        """Return a dict: {"label": "possible_scam"|"not_scam", "confidence": float}.

        This method never raises; on error or missing artifacts it returns
        `not_scam` with confidence 0.0 so callers can safely continue.
        """
        if not isinstance(message, str) or not message.strip():
            return {"label": "not_scam", "confidence": 0.0}

        if not self.ready:
            # Fallback to rule-based detector when local artifacts are missing
            try:
                rule = RuleScamDetector()
                msg = Message(sender="scammer", text=message, timestamp="")
                score, _ = rule.analyze_message(msg)
                label = "possible_scam" if score >= 0.3 else "not_scam"
                out = {"label": label, "confidence": float(score)}
                logger.info("ScamDetector[fallback=rule] message=%s label=%s confidence=%.4f", message[:200], out["label"], out["confidence"])
                return out
            except Exception:
                return {"label": "not_scam", "confidence": 0.0}

        # When local artifacts are ready, use them for inference
        try:
            # Preprocess minimally: keep original casing to match training behavior
            X = self.tfidf.transform([message])

            # Prefer predict_proba for confidence when available
            proba = None
            try:
                proba = float(self.model.predict_proba(X)[0][1])
            except Exception:
                # Fall back to predict()
                try:
                    pred = self.model.predict(X)[0]
                    # map truthy labels to possible_scam
                    label = "possible_scam" if bool(pred) else "not_scam"
                    conf = 1.0
                    return {"label": label, "confidence": float(conf)}
                except Exception:
                    # If local prediction fails, fallback to rule-based detector
                    try:
                        rule = RuleScamDetector()
                        msg = Message(sender="scammer", text=message, timestamp="")
                        score, _ = rule.analyze_message(msg)
                        label = "possible_scam" if score >= 0.3 else "not_scam"
                        out = {"label": label, "confidence": float(score)}
                        logger.info("ScamDetector[fallback=rule] message=%s label=%s confidence=%.4f", message[:200], out["label"], out["confidence"])
                        return out
                    except Exception:
                        return {"label": "not_scam", "confidence": 0.0}

            label = "possible_scam" if proba >= 0.4 else "not_scam"
            out = {"label": label, "confidence": float(proba)}
            logger.info("ScamDetector[local] message=%s label=%s confidence=%.4f", message[:200], out["label"], out["confidence"])
            return out
        except Exception:
            logger.exception("Error during ML scam prediction, falling back to HF")
            try:
                rule = RuleScamDetector()
                msg = Message(sender="scammer", text=message, timestamp="")
                score, _ = rule.analyze_message(msg)
                label = "possible_scam" if score >= 0.3 else "not_scam"
                out = {"label": label, "confidence": float(score)}
                logger.info("ScamDetector[fallback=rule] message=%s label=%s confidence=%.4f", message[:200], out["label"], out["confidence"])
                return out
            except Exception:
                return {"label": "not_scam", "confidence": 0.0}

