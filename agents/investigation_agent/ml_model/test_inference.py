from agents.investigation_agent.ml_model import AnomalyDetector, SensorReading

def run_test():
    print("Chargement du détecteur (modèle, scaler et baselines)...")
    # Instancie le détecteur. Il va chercher automatiquement dans le dossier artifacts/
    detector = AnomalyDetector()

    print("\n--- TEST 1 : Situation Normale ---")
    # On simule une lecture normale (proche des moyennes : Pression ~3.2, Débit ~125)
    reading_normal = SensorReading(
        sensor_id="S001",
        timestamp="2024-06-15T12:00:00",
        pressure_bar=3.25,
        flow_rate_lps=124.0,
        temperature_c=25.0
    )
    result_normal = detector.evaluate(reading_normal)
    print(f"Verdict : {result_normal.verdict.upper()}")
    print(f"Explication : {result_normal.details}")


    print("\n--- TEST 2 : Situation Suspecte (Chute de pression) ---")
    # On simule une fuite : pression qui chute drastiquement et débit qui augmente
    reading_leak = SensorReading(
        sensor_id="S001",
        timestamp="2024-06-15T12:05:00",
        pressure_bar=1.5,      # Pression très basse
        flow_rate_lps=280.0,   # Débit très élevé (fuite)
        temperature_c=25.0
    )
    result_leak = detector.evaluate(reading_leak)
    print(f"Verdict : {result_leak.verdict.upper()}")
    print(f"Explication : {result_leak.details}")

if __name__ == "__main__":
    run_test()
