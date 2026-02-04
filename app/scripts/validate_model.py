"""Validation script for ModelPredictor.

Run this after placing your model artifacts in `app/model_artifacts/` and
installing requirements (`pip install -r requirements.txt`).
"""
import json
import sys
from app.services.scam_detector_hybrid import ScamDetector
from app.services.preliminary_model_prediction import ModelPredictor


def main():
    scam_detector = ScamDetector()
    predictor = ModelPredictor(
        scam_detector,
        artifact_paths={
            "logistic": "app/model_artifacts/scam_detection_logistic_regression.pkl",
            "rf": "app/model_artifacts/scam_detection_random_forest.pkl",
            "tfidf_scam": "app/model_artifacts/tfidf_scam.pkl",
            "tfidf_response": "app/model_artifacts/tfidf_response.pkl",
            "preprocessor": "app/model_artifacts/preprocessor.pkl",
            "safe_numerical_features": "app/model_artifacts/safe_numerical_features.pkl",
        },
    )

    print("ML available:", predictor.ml_available)

    tests = [
        ("URGENT: Your account will be blocked today. Verify immediately.", ""),
        ("Hi, are you available for a quick chat?", ""),
    ]

    results = []
    for scam_text, user_resp in tests:
        possible, conf = predictor.is_possible_scam(scam_text, user_resp)
        results.append({"text": scam_text, "possible": possible, "confidence": conf})

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Validation script failed:", e)
        sys.exit(2)
