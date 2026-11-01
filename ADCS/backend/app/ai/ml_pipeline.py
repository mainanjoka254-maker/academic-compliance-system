"""Machine learning training pipeline placeholder.

This module provides a scaffold for training a risk model once sufficient
historical data becomes available. The production risk assessment currently uses
the explainable rule-based RiskEngine. No model is claimed to be trained.
"""

import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report


def train_risk_model(csv_path: str, output_path: str = "models/risk_model.joblib"):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Training data not found: {csv_path}")

    df = pd.read_csv(csv_path)
    # Expected columns: attendance_rate, missed_assessments, gpa, open_cases, risk_level
    required = {"attendance_rate", "missed_assessments", "gpa", "open_cases", "risk_level"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required}")

    X = df[["attendance_rate", "missed_assessments", "gpa", "open_cases"]]
    y = df["risk_level"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    print(classification_report(y_test, preds))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(model, output_path)
    return output_path


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/risk_training.csv"
    print("Training on", path)
    train_risk_model(path)
