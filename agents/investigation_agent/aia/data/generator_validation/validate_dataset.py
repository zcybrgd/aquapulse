
from __future__ import annotations

import argparse
import random
import unittest.mock as mock

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import generate_dataset as gd

NUMERICAL_FEATURES = [
    "p_mean", "p_std", "p_min", "p_max", "p_drop_pct", "p_slope",
    "p_rolling_std_5", "p_jitter", "q_mean", "q_std", "q_surge_pct",
    "q_slope", "pq_corr", "t_mean", "t_max", "zero_count",
    "pipe_diameter_mm", "pipe_age_years", "hour_of_day",
]
CATEGORICAL_FEATURES = ["pipe_material"]
RANDOM_STATE = 42

RF_PARAMS = {"n_estimators": 300, "max_depth": 10, "min_samples_split": 10,
             "min_samples_leaf": 4, "class_weight": "balanced",
             "random_state": RANDOM_STATE, "n_jobs": -1}


def _print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# 1. Cohérence physique FAVAD
# ---------------------------------------------------------------------------
def test_favad_material_effect(n_trials: int = 300) -> None:
   

    sensor = gd._build_sensor_pool(1, 1)[0]
    sensor["p_bias"] = 0
    sensor["q_bias"] = 0

    results = {}
    for material in ["HDPE", "PVC", "Steel", "Cast Iron"]:
        surges = []
        for trial in range(n_trials):
            np.random.seed(trial)
            random.seed(trial)
            readings = gd._generate_leak_series(
                base_p=40.0, base_q=50.0, temp=30.0, sensor=sensor, age=10,
                severity="moderate", diameter_mm=200, material=material)
            f = gd.compute_features(readings)
            surges.append(f["q_surge_pct"])
        results[material] = np.mean(surges)
        print(f"  {material:12s}  q_surge_pct moyen = {results[material]:6.2f}")

    ordered = sorted(results, key=results.get, reverse=True)
    expected_order = ["HDPE", "PVC", "Steel", "Cast Iron"]
    print(f"\n  Ordre observé  : {ordered}")
    print(f"  Ordre attendu  : {expected_order} (Steel/Cast Iron interchangeables)")
    ok = ordered[0] == "HDPE" and ordered[-1] in ("Steel", "Cast Iron")
    print(f"  Résultat : {'OK' if ok else 'ÉCART — à examiner'}")


# ---------------------------------------------------------------------------
# 2. Règle triviale à une seule feature
# ---------------------------------------------------------------------------
def test_single_feature_rule(df: pd.DataFrame) -> None:
 

    rules = {
        "pq_corr < 0": df["pq_corr"] < 0,
        "p_slope < -0.3": df["p_slope"] < -0.3,
    }
    for label, pred in rules.items():
        pred = pred.astype(int)
        report = classification_report(df["leak"], pred, target_names=["Normal", "Fuite"],
                                        output_dict=True, zero_division=0)
        acc = (df["leak"] == pred).mean()
        print(f"  Règle '{label}':  accuracy={acc:.2%}  "
              f"recall(Fuite)={report['Fuite']['recall']:.2%}  "
              f"precision(Fuite)={report['Fuite']['precision']:.2%}")


# ---------------------------------------------------------------------------
# 3. Recouvrement des scénarios ambigus
# ---------------------------------------------------------------------------
def test_ambiguous_scenario_overlap(n_trials: int = 300) -> None:
    

    sensor = gd._build_sensor_pool(1, 1)[0]
    scenarios = ["demand_shift", "pump_cycle", "valve_opening",
                 "construction_vibration", "scheduled_purge", "meter_drift"]

    print(f"  {'Scénario':<24s} {'pq_corr<0':>12s} {'p_slope<-0.3':>14s}")
    for scenario in scenarios:
        pq_neg, slope_neg = 0, 0
        for trial in range(n_trials):
            np.random.seed(trial)
            random.seed(trial)
            with mock.patch("random.choices", return_value=[scenario]):
                readings = gd._generate_ambiguous_series(40.0, 50.0, 30.0, sensor, 10)
            f = gd.compute_features(readings)
            if f["pq_corr"] < 0:
                pq_neg += 1
            if f["p_slope"] < -0.3:
                slope_neg += 1
        print(f"  {scenario:<24s} {pq_neg/n_trials:>11.1%} {slope_neg/n_trials:>13.1%}")


# ---------------------------------------------------------------------------
# 4. Ablation conjointe
# ---------------------------------------------------------------------------
def test_joint_ablation(df: pd.DataFrame) -> None:
  
    y = df["leak"]

    def eval_with(drop: list[str]) -> tuple[float, float]:
        feats = [f for f in NUMERICAL_FEATURES if f not in drop]
        X = df[feats + CATEGORICAL_FEATURES]
        X_trainval, X_test, y_trainval, y_test = train_test_split(
            X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE)
        X_train, X_val, y_train, y_val = train_test_split(
            X_trainval, y_trainval, test_size=0.15, stratify=y_trainval,
            random_state=RANDOM_STATE)

        pre = ColumnTransformer([
            ("num", StandardScaler(), feats),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
             CATEGORICAL_FEATURES),
        ])
        Xtr = pre.fit_transform(X_train)
        Xva = pre.transform(X_val)

        rf = RandomForestClassifier(**RF_PARAMS)
        rf.fit(Xtr, y_train)
        acc = rf.score(Xva, y_val)
        auc = roc_auc_score(y_val, rf.predict_proba(Xva)[:, 1])
        return acc, auc

    configs = [
        ([], "toutes features"),
        (["pq_corr"], "sans pq_corr"),
        (["p_slope"], "sans p_slope"),
        (["pq_corr", "p_slope"], "sans pq_corr + p_slope"),
        (["pq_corr", "p_slope", "p_drop_pct"], "sans pq_corr + p_slope + p_drop_pct"),
    ]
    print(f"  {'Configuration':<42s} {'Accuracy':>10s} {'AUC-ROC':>10s}")
    for drop, label in configs:
        acc, auc = eval_with(drop)
        print(f"  {label:<42s} {acc:>10.2%} {auc:>10.4f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Suite de validation du dataset AquaPulse")
    parser.add_argument("--dataset", type=str, default="leak_detection_dataset.csv")
    parser.add_argument("--skip-physics", action="store_true",
                        help="Skip test 1 (génération isolée, plus lente)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  AquaPulse — Suite de validation du dataset synthétique")
    print("=" * 60)

    if not args.skip_physics:
        test_favad_material_effect()

    df = pd.read_csv(args.dataset)
    print(f"\nDataset chargé : {df.shape[0]} lignes, {df.shape[1]} colonnes")
    print(f"Distribution labels : {df['leak'].value_counts().to_dict()}")

    test_single_feature_rule(df)
    test_ambiguous_scenario_overlap()
    test_joint_ablation(df)

    print("=" * 60)


if __name__ == "__main__":
    main()