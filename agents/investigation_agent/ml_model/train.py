"""
Training entrypoint — run this script to train and save the model.

Usage:
  python -m agents.investigation_agent.ml_model.train

Steps:
  1. Load CSV dataset           (preprocessing.load_csv)
  2. Clean and prepare data     (preprocessing.clean_data)
  3. Engineer features          (preprocessing.engineer_features)
  4. Extract feature matrix     (preprocessing.get_feature_matrix)
  5. Split train/test           (preprocessing.split_data)
  6. Train Isolation Forest     (model.train)
  7. Evaluate on test set       (model.evaluate)
  8. Save model artifact        (model.save)
  9. Save baselines             (for Z-score layer)
  10. Print metrics summary     (precision, recall, F1)
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config
from .model import AnomalyModel
from .preprocessing import (
    clean_data,
    compute_baselines,
    engineer_features,
    get_feature_matrix,
    load_csv,
    split_data,
)


def train() -> dict:
    """Execute the full training pipeline.

    Returns
    -------
    dict
        Evaluation metrics from the test set.
    """
    print("=" * 60)
    print("  AquaPulse — ML Anomaly Detection Training Pipeline")
    print("=" * 60)

    # ----- Step 1: Load Data -----
    print("\n[1/8] Loading dataset …")
    df = load_csv()
    print(f"  Loaded {len(df)} rows, {len(df.columns)} columns.")

    # ----- Step 2: Clean Data -----
    print("\n[2/8] Cleaning data …")
    df = clean_data(df)
    print(f"  {len(df)} rows after cleaning.")

    # ----- Step 3: Engineer Features -----
    print("\n[3/8] Engineering features …")
    df = engineer_features(df)
    print(f"  Features: {config.ENGINEERED_FEATURE_COLUMNS}")

    # ----- Step 4: Extract Feature Matrix -----
    print("\n[4/8] Extracting feature matrix …")
    X, y = get_feature_matrix(df)
    print(f"  X shape: {X.shape}, y shape: {y.shape}")
    print(f"  Class distribution: Normal={int((y == 0).sum())}, Leak={int((y == 1).sum())}")

    # ----- Step 5: Stratified Split -----
    print("\n[5/8] Splitting data (stratified) …")
    X_train, X_test, y_train, y_test = split_data(X, y)
    print(
        f"  Train: {X_train.shape[0]} samples "
        f"(Normal={int((y_train == 0).sum())}, Leak={int((y_train == 1).sum())})"
    )
    print(
        f"  Test:  {X_test.shape[0]} samples "
        f"(Normal={int((y_test == 0).sum())}, Leak={int((y_test == 1).sum())})"
    )

    # ----- Step 6: Train Model -----
    print("\n[6/8] Training Isolation Forest …")
    model = AnomalyModel()
    model.train(X_train, y_train)

    # ----- Step 7: Evaluate -----
    print("\n[7/8] Evaluating on test set …")
    metrics = model.evaluate(X_test, y_test)

    print("\n  Confusion Matrix:")
    cm = metrics["confusion_matrix"]
    print(f"    TN={cm[0][0]}  FP={cm[0][1]}")
    print(f"    FN={cm[1][0]}  TP={cm[1][1]}")
    print(f"\n  Classification Report:\n{metrics['classification_report']}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1 Score:  {metrics['f1_score']:.4f}")

    # ----- Step 8: Save Artifacts -----
    print("\n[8/8] Saving model artifacts …")
    model.save()

    # Save baselines for Z-score layer
    # Use the full cleaned dataframe (before split) for baseline computation
    baselines = compute_baselines(df)
    baselines_path = config.MODEL_PATH.parent / "baselines.json"
    with open(baselines_path, "w") as f:
        json.dump(baselines, f, indent=2)
    print(f"  [model] Saved baselines → {baselines_path}")

    print("\n" + "=" * 60)
    print("  Training complete!")
    print("=" * 60)

    return metrics


# Allow execution as a script
if __name__ == "__main__":
    train()
