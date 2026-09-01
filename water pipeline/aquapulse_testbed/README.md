# AquaPulse Smart Water Grid - Multi-Container Testbed (MVP Demo)

Welcome to the **AquaPulse Multi-Container Simulation Testbed**. This platform is an interactive, dockerized demonstration environment showing our **Anomaly Investigation Agent (AIA)** running in a closed-loop water network topology with **Nokia Network-as-Code (NaC) CAMARA API integrations**.

---

## 🏗️ System Components

The testbed orchestrates three main logical layers:
1. **Pipeline Simulator (Field & Wireless Connectivity Layer):**
   * Implements real-time physical telemetry equations for a water pipe segment.
   * Exposes mock Nokia CAMARA APIs (`Device Reachability Status` and `Congestion Insights`).
   * Models motorized valves and scenarios: Normal, Physical Burst, Sensor Outage, and Thermal Fading.
2. **AIA Service (AI/Agentic Reasoning Layer):**
   * Employs the **unsupervised Isolation Forest bootstrap model** for Stage 1 filtering.
   * Programmatically calls CAMARA APIs to determine telemetry authenticity.
   * Calculates deterministic risk assessment matrices in Python to guarantee safety.
   * Compiles natural-language Operator Justification Memos via an LLM/narrator node.
3. **HMI SCADA (Supervisory Dashboard Layer):**
   * An interactive web console built on Streamlit.
   * Visualizes real-time pipeline pressure/flow metrics and topology status.
   * Features a **Scenario Control Panel** to inject faults and watch the AIA react in under 5 seconds!

---

## ⚡ Quick Start Deployment

Deploy the entire sandbox ecosystem using Docker Compose:

```bash
# 1. Build and boot all containers
docker-compose up --build -d

# 2. Check container health
docker-compose ps
```

* **Supervisory SCADA Console:** Open `http://localhost:8501` in your browser.
* **AIA API Swagger Docs:** Available at `http://localhost:8000/docs`.
* **Simulator API Swagger Docs:** Available at `http://localhost:8001/docs`.

---

## 🎮 Evaluation Guide (Jury Scenarios)

### **Scenario A: Normal Operations**
* **HMI Action:** Select "Normal Operations" in the sidebar and click **Inject Scenario**. Click **Trigger Telemetry Ingestion Batch Check**.
* **System Behavior:** System telemetry remains stable (45 psi, 80 lps). The AIA Stage 1 ML/Z-score layer recognizes the pattern as normal, writes it silently to TimescaleDB, and bypasses the rest of the agentic pipeline, protecting Nokia API quotas.

### **Scenario B: Catastrophic Physical Burst**
* **HMI Action:** Select "Catastrophic Pipe Burst" -> click **Inject Scenario** -> click **Trigger Telemetry Ingestion Batch Check**.
* **System Behavior:** Telemetry shows a dramatic pressure drop (to ~28 psi) and flow surge (to ~112 lps). 
  * The AIA flags the suspicious readings.
  * Active CAMARA diagnostics verify that the device is **REACHABLE** with **LOW** network congestion.
  * A **Tier 3 (Catastrophic Alert)** is declared.
  * The AIA instantly dispatches an autonomous valve isolation command.
  * On your SCADA screen, the NEOM Valve changes from **OPEN (Green)** to **CLOSED (Red)**, stopping water loss in under 30 seconds!

### **Scenario C: Localized Instrument Outage**
* **HMI Action:** Select "Sensor Blowout" -> click **Inject Scenario** -> click **Trigger Telemetry Ingestion Batch Check**.
* **System Behavior:** Telemetry drops to exactly 0.0 psi. The active CAMARA check reports the sensor as **UNREACHABLE** with **LOW** congestion (meaning the network tower is healthy but the sensor went dark).
  * The AIA diagnoses a **`confirmed_instrument_fault`**.
  * It logs a maintenance ticket and flags the readings as stale.
  * **Critical Safety Block:** The AIA locks the system from triggering an accidental autonomous valve shutoff, proving its industrial-grade stability.

### **Scenario D: Cellular Tower Thermal Outage**
* **HMI Action:** Select "Thermal Cellular Outage" -> click **Inject Scenario** -> click **Trigger Telemetry Ingestion Batch Check**.
* **System Behavior:** Ambient temperature spikes to 51.5°C. The device is reported as **UNREACHABLE**, but Nokia CAMARA Congestion Insights reports **HIGH** sector congestion (tower under intense thermal strain).
  * The AIA identifies the network fade and classifies the event as a **`likely_connectivity_artifact`**.
  * The physical leak alarm is bypassed, preventing false alarms on the SCADA panel.

---

## 🧹 Teardown

To shut down and clean up all containers:
```bash
docker-compose down
```
