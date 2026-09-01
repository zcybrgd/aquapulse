import os
import sys
import unittest
from datetime import datetime

# Add components to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "aia_service"))

from src.schemas import StreamingBatchInput, TelemetryWindow, TelemetryReading
from src.detection import AnomalyDetector
from src.risk_assessment import RiskAssessor
from src.narration import LLMNarrator

class LocalIntegrationTest(unittest.TestCase):
    def setUp(self):
        # Override paths to relative sandbox paths
        self.detector = AnomalyDetector(model_path="aia_service/data/isolation_forest_bootstrap.joblib")
        self.assessor = RiskAssessor(topology_path="aia_service/config/topology_cache.json")
        self.narrator = LLMNarrator()

    def test_normal_operations(self):
        # 1. Simulate 10 normal readings
        readings = [
            TelemetryReading(timestamp="2026-09-01T05:00:00Z", pressure_psi=45.0, flow_rate_lps=80.0, ambient_temp_c=48.0)
            for _ in range(10)
        ]
        
        # 2. Check Detection
        is_suspicious = self.detector.evaluate_sequence(readings)
        self.assertFalse(is_suspicious, "Normal telemetry should not trigger suspicious alerts!")

    def test_catastrophic_burst(self):
        # 1. Simulate a progressive pipeline leak ending with a massive burst
        readings = []
        for i in range(10):
            # Pressure dropping rapidly over time
            p = 45.0 - i * 2.0
            # Flow rate spiking
            f = 80.0 + i * 4.0
            readings.append(TelemetryReading(
                timestamp=f"2026-09-01T05:00:{i:02d}Z",
                pressure_psi=p,
                flow_rate_lps=f,
                ambient_temp_c=48.0
            ))
            
        # 2. Check Detection
        is_suspicious = self.detector.evaluate_sequence(readings)
        self.assertTrue(is_suspicious, "A catastrophic physical burst must trigger a suspicious alert!")
        
        # 3. Assess Risk assuming reachable network and low congestion
        diag = self.assessor.assess(
            sensor_cluster_id="cluster-desert-042",
            readings=readings,
            reachability="REACHABLE",
            congestion="LOW",
            api_unavailable=False
        )
        
        self.assertEqual(diag["classification"], "confirmed_anomaly")
        self.assertEqual(diag["severity_tier"], 3)
        self.assertEqual(diag["segment_id"], "seg-neom-north-01")
        
        # 4. Generate AI Narrative Memo
        memo = self.narrator.generate_memo(
            cluster_id="cluster-desert-042",
            diagnostics=diag,
            reach_status="REACHABLE",
            cong_level="LOW"
        )
        
        self.assertIn("catastrophic physical pipeline burst (Tier 3)", memo)
        self.assertIn("valve-neom-north-01", memo)

    def test_thermal_telecom_fade(self):
        # Telemetry flatlines, but we have high temp and unreachable status
        readings = [
            TelemetryReading(timestamp="2026-09-01T05:00:00Z", pressure_psi=45.0, flow_rate_lps=80.0, ambient_temp_c=51.5)
            for _ in range(10)
        ]
        
        # In a real run, if readings freeze, detection could trigger due to EWMA drift.
        # Let's force an active check on this sequence
        diag = self.assessor.assess(
            sensor_cluster_id="cluster-desert-042",
            readings=readings,
            reachability="UNREACHABLE",
            congestion="HIGH",
            api_unavailable=False
        )
        
        self.assertEqual(diag["classification"], "likely_connectivity_artifact")
        self.assertEqual(diag["severity_tier"], 1)

if __name__ == "__main__":
    unittest.main()
