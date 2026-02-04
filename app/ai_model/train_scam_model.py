import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import joblib

# Load dataset
import pandas as pd

# Load dataset (CSV, not Excel)
df = pd.read_csv("../spam.csv", encoding="latin-1")

# Keep only what we need
df = df[["v1", "v2"]]
df.columns = ["is_scam", "message"]
df = df.dropna()


X = df["message"]
y = df["is_scam"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# TF-IDF Vectorizer
tfidf = TfidfVectorizer(
    ngram_range=(1,2),
    max_features=5000,
    stop_words="english"
)

X_train_vec = tfidf.fit_transform(X_train)
X_test_vec = tfidf.transform(X_test)

# Logistic Regression model
model = LogisticRegression(max_iter=1000)
model.fit(X_train_vec, y_train)

# Evaluate
preds = model.predict(X_test_vec)
print("\n=== Classification Report ===\n")
print(classification_report(y_test, preds))

# Save artifacts
joblib.dump(model, "scam_detection_logistic_regression.pkl")
joblib.dump(tfidf, "tfidf_scam.pkl")

print("\n✅ Model and TF-IDF saved successfully!")
