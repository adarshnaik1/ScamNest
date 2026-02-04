from app.services.preliminary_model_prediction import ScamDetector

det = ScamDetector()

samples = [
    ("URGENT: Your account will be blocked, send OTP to verify.", True),
    ("Hey, want to grab coffee tomorrow?", False),
]

for text, expect_scam in samples:
    out = det.is_possible_scam(text)
    print("MSG:", text)
    print("OUT:", out)
    assert isinstance(out, dict)
    assert "label" in out and "confidence" in out
    assert 0.0 <= float(out["confidence"]) <= 1.0
    if expect_scam:
        assert out["label"] == "possible_scam"
    else:
        assert out["label"] == "not_scam"
print("Smoke checks passed")