"""
Pipeline d'entraînement et d'évaluation des modèles de détection de fuites.

Compare 3 approches :
    1. Isolation Forest (unsupervised baseline)
    2. Random Forest (supervised)
    3. Gradient Boosting (supervised)

Produit :
    - Rapport de classification complet (precision, recall, F1)
    - Matrice de confusion
    - Feature importance
    - Modèle sérialisé (.joblib) du meilleur modèle

Usage:
    python -m ml_model.train
"""
from __future__ import annotations

import logging
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline

from ml_model.config import (
    ARTIFACTS_DIR,
    CATEGORICAL_FEATURES,
    GB_PARAMS,
    ISO_FOREST_PARAMS,
    NUMERICAL_FEATURES,
    PRIMARY_METRIC,
    RANDOM_STATE,
    RF_PARAMS,
    TARGET,
)
from ml_model.preprocessing import build_preprocessor, load_dataset, split_data

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ml_model.train")


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def train_isolation_forest(X_train: np.ndarray) -> IsolationForest:
    """Entraîne un Isolation Forest (unsupervised)."""
    model = IsolationForest(**ISO_FOREST_PARAMS)
    model.fit(X_train)
    return model


def predict_isolation_forest(model: IsolationForest, X: np.ndarray) -> np.ndarray:
    """Convertit les scores IF (-1=anomaly, 1=normal) en labels binaires (1=leak, 0=normal)."""
    raw = model.predict(X)
    return np.where(raw == -1, 1, 0)


def train_random_forest(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    """Entraîne un Random Forest classifier."""
    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X_train, y_train)
    return model


def train_gradient_boosting(X_train: np.ndarray, y_train: np.ndarray) -> GradientBoostingClassifier:
    """Entraîne un Gradient Boosting classifier."""
    model = GradientBoostingClassifier(**GB_PARAMS)
    model.fit(X_train, y_train)
    return model


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_model(
    name: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
) -> dict:
    """
    Évalue un modèle et affiche un rapport complet.
    Retourne un dict avec les métriques clés.
    """
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    auc = roc_auc_score(y_true, y_proba) if y_proba is not None else 0.0
    cm = confusion_matrix(y_true, y_pred)

    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(classification_report(y_true, y_pred, target_names=["Normal", "Fuite"]))
    print(f"  AUC-ROC: {auc:.4f}")
    print(f"\n  Matrice de confusion:")
    print(f"                 Prédit Normal   Prédit Fuite")
    print(f"  Vrai Normal       {cm[0][0]:>6}          {cm[0][1]:>6}")
    print(f"  Vrai Fuite        {cm[1][0]:>6}          {cm[1][1]:>6}")

    # Interprétation métier
    fn = cm[1][0]  # Fuites manquées
    fp = cm[0][1]  # Fausses alertes
    print(f"\n  Fuites manquées (Faux Négatifs): {fn}")
    print(f"  Fausses alertes (Faux Positifs): {fp}")

    return {
        "name": name,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc_roc": auc,
        "false_negatives": fn,
        "false_positives": fp,
    }


def print_feature_importance(model, feature_names: list[str], top_n: int = 10) -> None:
    """Affiche les features les plus importantes."""
    if not hasattr(model, "feature_importances_"):
        return
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]

    print(f"\n  Top {top_n} Feature Importances:")
    for rank, idx in enumerate(indices, 1):
        name = feature_names[idx] if idx < len(feature_names) else f"feature_{idx}"
        print(f"    {rank}. {name}: {importances[idx]:.4f}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    # 1. Charger et splitter les données
    print("\n" + "="*60)
    print("  AquaPulse — Pipeline d'entraînement ML")
    print("="*60)

    df = load_dataset()
    train_df, val_df, test_df = split_data(df)

    # 2. Construire le preprocessor et transformer les données
    preprocessor = build_preprocessor()

    feature_cols = NUMERICAL_FEATURES + CATEGORICAL_FEATURES

    X_train = preprocessor.fit_transform(train_df[feature_cols])
    y_train = train_df[TARGET].values

    X_val = preprocessor.transform(val_df[feature_cols])
    y_val = val_df[TARGET].values

    X_test = preprocessor.transform(test_df[feature_cols])
    y_test = test_df[TARGET].values

    # Récupérer les noms des features après encoding
    cat_feature_names = []
    if CATEGORICAL_FEATURES:
        encoder = preprocessor.named_transformers_["cat"].named_steps["encoder"]
        cat_feature_names = list(encoder.get_feature_names_out(CATEGORICAL_FEATURES))
    all_feature_names = NUMERICAL_FEATURES + cat_feature_names

    logger.info("Features après preprocessing : %d", X_train.shape[1])
    logger.info("Feature names : %s", all_feature_names)

    # 3. Entraîner les modèles
    print("\n[1/3] Entraînement Isolation Forest...")
    iso_model = train_isolation_forest(X_train)

    print("[2/3] Entraînement Random Forest...")
    rf_model = train_random_forest(X_train, y_train)

    print("[3/3] Entraînement Gradient Boosting...")
    gb_model = train_gradient_boosting(X_train, y_train)

    # 4. Évaluer sur le set de validation
    print("\n" + "="*60)
    print("  ÉVALUATION SUR LE SET DE VALIDATION")
    print("="*60)

    results = []

    # Isolation Forest
    y_pred_iso = predict_isolation_forest(iso_model, X_val)
    results.append(evaluate_model("Isolation Forest", y_val, y_pred_iso))

    # Random Forest
    y_pred_rf = rf_model.predict(X_val)
    y_proba_rf = rf_model.predict_proba(X_val)[:, 1]
    results.append(evaluate_model("Random Forest", y_val, y_pred_rf, y_proba_rf))
    print_feature_importance(rf_model, all_feature_names)

    # Gradient Boosting
    y_pred_gb = gb_model.predict(X_val)
    y_proba_gb = gb_model.predict_proba(X_val)[:, 1]
    results.append(evaluate_model("Gradient Boosting", y_val, y_pred_gb, y_proba_gb))
    print_feature_importance(gb_model, all_feature_names)

    # 5. Sélection du meilleur modèle (basée sur le recall)
    print("\n" + "="*60)
    print("  COMPARAISON DES MODÈLES")
    print("="*60)
    print(f"\n  {'Modèle':<25} {'Recall':>8} {'Precision':>10} {'F1':>8} {'AUC':>8} {'FN':>6}")
    print(f"  {'-'*67}")
    for r in results:
        print(f"  {r['name']:<25} {r['recall']:>8.4f} {r['precision']:>10.4f} {r['f1']:>8.4f} {r['auc_roc']:>8.4f} {r['false_negatives']:>6}")

    best = max(results, key=lambda r: r["recall"])
    print(f"\n  Meilleur modèle (par {PRIMARY_METRIC}) : {best['name']}")

    # 6. Évaluation finale sur le set de test
    print("\n" + "="*60)
    print(f"  ÉVALUATION FINALE SUR LE SET DE TEST — {best['name']}")
    print("="*60)

    models = {
        "Isolation Forest": (iso_model, True),
        "Random Forest": (rf_model, False),
        "Gradient Boosting": (gb_model, False),
    }
    best_model, is_unsupervised = models[best["name"]]

    if is_unsupervised:
        y_pred_test = predict_isolation_forest(best_model, X_test)
        y_proba_test = None
    else:
        y_pred_test = best_model.predict(X_test)
        y_proba_test = best_model.predict_proba(X_test)[:, 1]

    evaluate_model(f"{best['name']} (TEST SET)", y_test, y_pred_test, y_proba_test)

    # 7. Sauvegarder le meilleur modèle + preprocessor
    model_path = os.path.join(ARTIFACTS_DIR, "best_model.joblib")
    preprocessor_path = os.path.join(ARTIFACTS_DIR, "preprocessor.joblib")

    joblib.dump(best_model, model_path)
    joblib.dump(preprocessor, preprocessor_path)

    # Sauvegarder les métadonnées
    metadata = {
        "model_name": best["name"],
        "features": all_feature_names,
        "metrics_validation": best,
        "random_state": RANDOM_STATE,
    }
    metadata_path = os.path.join(ARTIFACTS_DIR, "model_metadata.joblib")
    joblib.dump(metadata, metadata_path)

    print(f"\n  Modèle sauvegardé     : {model_path}")
    print(f"   Preprocessor sauvegardé: {preprocessor_path}")
    print(f"   Métadonnées sauvegardées: {metadata_path}")
    print("\nDone!")


if __name__ == "__main__":
    main()
