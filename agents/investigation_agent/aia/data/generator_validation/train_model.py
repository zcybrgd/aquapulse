
from __future__ import annotations

import argparse
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ---------------------------------------------------------------------------
# Config — copié de ml_model/config.py pour rester autonome
# ---------------------------------------------------------------------------
NUMERICAL_FEATURES = [
    "p_mean", "p_std", "p_min", "p_max", "p_drop_pct", "p_slope",
    "p_rolling_std_5", "p_jitter", "q_mean", "q_std", "q_surge_pct",
    "q_slope", "pq_corr", "t_mean", "t_max", "zero_count",
    "pipe_diameter_mm", "pipe_age_years", "hour_of_day",
]
CATEGORICAL_FEATURES = ["pipe_material"]
TARGET = "leak"

TEST_SIZE = 0.20
VAL_SIZE = 0.15
RANDOM_STATE = 42

ISO_FOREST_PARAMS = {"n_estimators": 200, "contamination": 0.40,
                      "random_state": RANDOM_STATE, "n_jobs": -1}
RF_PARAMS = {"n_estimators": 300, "max_depth": 10, "min_samples_split": 10,
             "min_samples_leaf": 4, "class_weight": "balanced",
             "random_state": RANDOM_STATE, "n_jobs": -1}
GB_PARAMS = {"n_estimators": 300, "max_depth": 5, "learning_rate": 0.05,
             "subsample": 0.8, "random_state": RANDOM_STATE}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_and_split(dataset_path: str):
    df = pd.read_csv(dataset_path)
    X = df.drop(columns=[TARGET])
    y = df[TARGET]

    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=VAL_SIZE, stratify=y_trainval,
        random_state=RANDOM_STATE)

    print(f"Split : train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")
    return X_train, y_train, X_val, y_val, X_test, y_test


def build_preprocessor() -> ColumnTransformer:
    numerical_pipeline = Pipeline([("scaler", StandardScaler())])
    categorical_pipeline = Pipeline([
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])
    return ColumnTransformer(
        transformers=[
            ("num", numerical_pipeline, NUMERICAL_FEATURES),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def predict_isolation_forest(model: IsolationForest, X: np.ndarray) -> np.ndarray:
    raw = model.predict(X)
    return np.where(raw == -1, 1, 0)


def score_isolation_forest(model: IsolationForest, X: np.ndarray) -> np.ndarray:
    """Score continu pour l'AUC-ROC : -score_samples car IsolationForest donne
    un score plus négatif = plus anormal, et on veut score élevé = fuite probable."""
    return -model.score_samples(X)


def evaluate_model(name, y_true, y_pred, y_proba=None, verbose=True) -> dict:
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    auc = roc_auc_score(y_true, y_proba) if y_proba is not None else 0.0
    cm = confusion_matrix(y_true, y_pred)

    if verbose:
        print(f"\n{'='*60}\n  {name}\n{'='*60}")
        print(classification_report(y_true, y_pred, target_names=["Normal", "Fuite"]))
        print(f"  AUC-ROC: {auc:.4f}")

    return {"name": name, "precision": precision, "recall": recall,
            "f1": f1, "auc_roc": auc, "accuracy": (y_true == y_pred).mean(),
            "false_negatives": int(cm[1][0]), "false_positives": int(cm[0][1])}


def print_feature_importance(model, feature_names, top_n=10):
    if not hasattr(model, "feature_importances_"):
        return
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]
    print(f"\n  Top {top_n} Feature Importances:")
    for rank, idx in enumerate(indices, 1):
        name = feature_names[idx] if idx < len(feature_names) else f"feature_{idx}"
        print(f"    {rank}. {name}: {importances[idx]:.4f}")


def get_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    cat_names = []
    if CATEGORICAL_FEATURES:
        encoder = preprocessor.named_transformers_["cat"].named_steps["encoder"]
        cat_names = list(encoder.get_feature_names_out(CATEGORICAL_FEATURES))
    return NUMERICAL_FEATURES + cat_names


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def train_all(dataset_path: str, artifacts_dir: str | None = None, verbose: bool = True):
  
    X_train, y_train, X_val, y_val, X_test, y_test = load_and_split(dataset_path)

    preprocessor = build_preprocessor()
    feature_cols = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
    Xtr = preprocessor.fit_transform(X_train[feature_cols])
    Xva = preprocessor.transform(X_val[feature_cols])
    Xte = preprocessor.transform(X_test[feature_cols])
    feature_names = get_feature_names(preprocessor)

    if verbose:
        print(f"Features après preprocessing : {Xtr.shape[1]}")

    if verbose:
        print("\n[1/3] Entraînement Isolation Forest...")
    iso_model = IsolationForest(**ISO_FOREST_PARAMS).fit(Xtr)

    if verbose:
        print("[2/3] Entraînement Random Forest...")
    rf_model = RandomForestClassifier(**RF_PARAMS).fit(Xtr, y_train)

    if verbose:
        print("[3/3] Entraînement Gradient Boosting...")
    gb_model = GradientBoostingClassifier(**GB_PARAMS).fit(Xtr, y_train)

    if verbose:
        print("\n" + "="*60 + "\n  ÉVALUATION SUR LE SET DE VALIDATION\n" + "="*60)

    results = []
    y_pred_iso = predict_isolation_forest(iso_model, Xva)
    y_score_iso = score_isolation_forest(iso_model, Xva)
    results.append(evaluate_model("Isolation Forest", y_val, y_pred_iso, y_score_iso, verbose))

    y_pred_rf = rf_model.predict(Xva)
    y_proba_rf = rf_model.predict_proba(Xva)[:, 1]
    results.append(evaluate_model("Random Forest", y_val, y_pred_rf, y_proba_rf, verbose))
    if verbose:
        print_feature_importance(rf_model, feature_names)

    y_pred_gb = gb_model.predict(Xva)
    y_proba_gb = gb_model.predict_proba(Xva)[:, 1]
    results.append(evaluate_model("Gradient Boosting", y_val, y_pred_gb, y_proba_gb, verbose))
    if verbose:
        print_feature_importance(gb_model, feature_names)

    best = max(results, key=lambda r: r["recall"])
    if verbose:
        print(f"\nMeilleur modèle (par recall) : {best['name']}")

    models = {"Isolation Forest": (iso_model, True),
              "Random Forest": (rf_model, False),
              "Gradient Boosting": (gb_model, False)}
    best_model, is_unsupervised = models[best["name"]]

    if is_unsupervised:
        y_pred_test = predict_isolation_forest(best_model, Xte)
        y_proba_test = score_isolation_forest(best_model, Xte)
    else:
        y_pred_test = best_model.predict(Xte)
        y_proba_test = best_model.predict_proba(Xte)[:, 1]

    test_result = evaluate_model(f"{best['name']} (TEST SET)", y_test, y_pred_test,
                                  y_proba_test, verbose)

    if artifacts_dir:
        os.makedirs(artifacts_dir, exist_ok=True)
        joblib.dump(best_model, os.path.join(artifacts_dir, "best_model.joblib"))
        joblib.dump(preprocessor, os.path.join(artifacts_dir, "preprocessor.joblib"))
        if verbose:
            print(f"\nModèle sauvegardé dans {artifacts_dir}")

    return {
        "val_results": results,
        "test_result": test_result,
        "best_model_name": best["name"],
        "models": {"Isolation Forest": iso_model, "Random Forest": rf_model,
                   "Gradient Boosting": gb_model},
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "splits": {"X_train": X_train, "y_train": y_train, "X_val": X_val,
                   "y_val": y_val, "X_test": X_test, "y_test": y_test},
    }


def main():
    parser = argparse.ArgumentParser(description="Entraînement autonome AquaPulse (dataset_validation)")
    parser.add_argument("--dataset", type=str, default="leak_detection_dataset.csv")
    parser.add_argument("--artifacts-dir", type=str, default="artifacts")
    args = parser.parse_args()

    print("\n" + "="*60 + "\n  AquaPulse — Entraînement (dataset_validation)\n" + "="*60)
    train_all(args.dataset, artifacts_dir=args.artifacts_dir, verbose=True)
    print("\nDone!")


if __name__ == "__main__":
    main()