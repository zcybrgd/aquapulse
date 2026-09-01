import os
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    def __init__(self, model_path="data/isolation_forest_bootstrap.joblib"):
        self.model_path = model_path
        self.model = None
        self._load_or_build_model()

    def _load_or_build_model(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"[AIA - Detection] Successfully loaded Isolation Forest model from {self.model_path}")
            except Exception as e:
                print(f"[AIA - Detection] Failed to load model: {e}. Rebuilding...")
                self._build_bootstrap_model()
        else:
            print(f"[AIA - Detection] Model file {self.model_path} not found. Rebuilding model.")
            self._build_bootstrap_model()

    def _build_bootstrap_model(self):
        # Generate lightweight bootstrap dataset of normal operations
        print("[AIA - Detection] Bootstrapping fresh unsupervised Isolation Forest model...")
        np.random.seed(42)
        n_samples = 1440 # 1 day of 1-min data
        
        # Simulating stable temperatures and hydraulics
        temp = 38.5 + 10 * np.sin(np.linspace(0, 2 * np.pi, n_samples)) + np.random.normal(0, 0.5, n_samples)
        flow = 80.0 + np.random.normal(0, 1.0, n_samples)
        pressure = 45.0 - 0.1 * (flow - 80.0) + 0.05 * (temp - 38.0) + np.random.normal(0, 0.4, n_samples)
        
        df = pd.DataFrame({
            'pressure_psi': pressure,
            'flow_rate_lps': flow,
            'ambient_temp_c': temp
        })
        
        # Train lightweight model
        self.model = IsolationForest(n_estimators=50, contamination=0.01, random_state=42)
        self.model.fit(df[['pressure_psi', 'flow_rate_lps', 'ambient_temp_c']])
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        print(f"[AIA - Detection] Serialized bootstrapped model to {self.model_path}")

    def evaluate_sequence(self, readings) -> bool:
        """
        Evaluate sequence of trailing telemetry readings.
        Returns True if a suspicious anomaly is detected, False otherwise.
        """
        if not readings:
            return False
            
        # 1. Deterministic Safety Boundaries (Instant checks)
        latest = readings[-1]
        
        # Immediate sharp drop in pressure or surge in flow rate
        # Let's compare the last reading against the start of the window
        p_start = readings[0].pressure_psi
        p_end = latest.pressure_psi
        f_start = readings[0].flow_rate_lps
        f_end = latest.flow_rate_lps
        
        p_drop_pct = ((p_start - p_end) / p_start) * 100 if p_start > 0 else 0
        f_surge_pct = ((f_end - f_start) / f_start) * 100 if f_start > 0 else 0
        
        if p_drop_pct >= 15.0 or f_surge_pct >= 20.0:
            return True
            
        # 2. Unsupervised ML Check
        # Convert window to DataFrame
        data = []
        for r in readings:
            data.append([r.pressure_psi, r.flow_rate_lps, r.ambient_temp_c])
            
        df = pd.DataFrame(data, columns=['pressure_psi', 'flow_rate_lps', 'ambient_temp_c'])
        
        # Predict: -1 is anomalous, 1 is normal
        # We check the average prediction of the last 3 samples to ignore transient spikes
        preds = self.model.predict(df.tail(3))
        if -1 in preds:
            return True
            
        return False
