import os
import requests
import streamlit as pd_st
import pandas as pd
import plotly.graph_objects as go
import time

pd_st.set_page_config(layout="wide", page_title="AquaPulse SCADA System")

# Get service URLs from environment
SIMULATOR_URL = os.getenv("SIMULATOR_URL", "http://localhost:8001")
AIA_URL = os.getenv("AIA_URL", "http://localhost:8000")

# Session state initialization for alert logs
if "alert_logs" not in pd_st.session_state:
    pd_st.session_state.alert_logs = []

# Fetch active simulator state
try:
    resp = requests.get(f"{SIMULATOR_URL}/state", timeout=2.0)
    sim_state = resp.json() if resp.status_code == 200 else {}
except Exception:
    sim_state = {}

# Sidebar control panel
pd_st.sidebar.title("🛠️ Scenario Control Panel")
pd_st.sidebar.write("Select a scenario to inject faults into the physical testbed:")

scenario = pd_st.sidebar.radio(
    "Active Scenario",
    ["Normal Operations", "Catastrophic Pipe Burst", "Sensor Blowout", "Thermal Cellular Outage"]
)

# Convert selection to API scenario names
scenario_map = {
    "Normal Operations": "normal",
    "Catastrophic Pipe Burst": "burst",
    "Sensor Blowout": "instrument_fault",
    "Thermal Cellular Outage": "thermal_outage"
}

if pd_st.sidebar.button("Inject Scenario"):
    try:
        requests.post(f"{SIMULATOR_URL}/set-scenario", json={"scenario": scenario_map[scenario]}, timeout=2.0)
        pd_st.sidebar.success(f"Scenario '{scenario}' successfully injected!")
        time.sleep(0.5)
        pd_st.rerun()
    except Exception as e:
        pd_st.sidebar.error(f"Failed to inject scenario: {e}")

# Valve control overrides
pd_st.sidebar.write("---")
pd_st.sidebar.title("🎛️ Motorized Valve Actuator Override")
valve_override = pd_st.sidebar.selectbox("Valve Action", ["OPEN", "CLOSED"])
if pd_st.sidebar.button("Command Valve"):
    try:
        requests.post(f"{SIMULATOR_URL}/control-valve", json={
            "valve_id": "valve-neom-north-01",
            "state": valve_override
        }, timeout=2.0)
        pd_st.sidebar.success(f"Valve commanded {valve_override}!")
        time.sleep(0.5)
        pd_st.rerun()
    except Exception as e:
        pd_st.sidebar.error(f"Failed to override valve: {e}")

# Main dashboard layout
pd_st.title("🚰 AquaPulse Real-Time SCADA & HMI console")
pd_st.write("### Autonomous Water-Management Grid Dashboard")

if not sim_state:
    pd_st.error("⚠️ Connection lost with Pipeline Simulator. Ensure simulator container is running on port 8001.")
else:
    # 1. Pipeline Telemetry Gauges
    col1, col2, col3, col4 = pd_st.columns(4)
    
    with col1:
        pd_st.metric(
            label="Pressure (psi)",
            value=f"{sim_state['pressure_psi']} psi",
            delta=f"{round(sim_state['pressure_psi'] - 45.0, 2)} psi"
        )
    with col2:
        pd_st.metric(
            label="Flow Rate (lps)",
            value=f"{sim_state['flow_rate_lps']} lps",
            delta=f"{round(sim_state['flow_rate_lps'] - 80.0, 2)} lps"
        )
    with col3:
        pd_st.metric(
            label="Ambient Temperature (°C)",
            value=f"{sim_state['ambient_temp_c']} °C"
        )
    with col4:
        valve_color = "🟢" if sim_state["valve_state"] == "OPEN" else "🔴"
        pd_st.metric(
            label="Motorized Valve Status",
            value=f"{valve_color} {sim_state['valve_state']}"
        )

    pd_st.write("---")

    # 2. Pipeline Network Layout Visualization
    pd_st.subheader("🌐 Interactive Water Grid Topology Map")
    
    # Create simple node diagram representing physical NEOM segment
    fig = go.Figure()
    
    # Main North Reservoir -> Segment -> Valve -> Blending Station
    nodes_x = [0, 1, 2, 3]
    nodes_y = [0, 0, 0, 0]
    nodes_text = ["Reservoir Main North", "Cluster-Desert-042\n(Sensor)", "Valve-NEOM-North-01\n(Actuator)", "Blending Station 01"]
    
    # Pipe Connection Lines
    fig.add_trace(go.Scatter(
        x=[0, 1, 2, 3], y=[0, 0, 0, 0],
        line=dict(color='blue' if sim_state["valve_state"] == "OPEN" else 'grey', width=6),
        hoverinfo='none',
        mode='lines'
    ))
    
    # Node markers
    node_colors = ['blue', 'cyan', 'green' if sim_state["valve_state"] == "OPEN" else 'red', 'darkblue']
    fig.add_trace(go.Scatter(
        x=nodes_x, y=nodes_y,
        mode='markers+text',
        marker=dict(size=[30, 25, 30, 25], color=node_colors, line_width=2),
        text=nodes_text,
        textposition="bottom center",
        hoverinfo='none'
    ))
    
    fig.update_layout(
        showlegend=False,
        height=220,
        margin=dict(b=20, l=20, r=20, t=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    pd_st.plotly_chart(fig, use_container_width=True)

    # 3. Active AIA Stream Ingestion
    pd_st.write("---")
    col_left, col_right = pd_st.columns(2)
    
    with col_left:
        pd_st.subheader("🕵️ Anomaly Investigation Agent (AIA) Console")
        pd_st.write("Runs continuous real-time evaluations & active CAMARA diagnostics.")
        
        if pd_st.button("Trigger Telemetry Ingestion Batch Check"):
            with pd_st.spinner("Executing 4-Stage Agentic pipeline..."):
                # Pack dummy 10-step sequence with the latest state
                readings = []
                # To simulate regression slopes, we inject slightly declining sequence if burst
                p_base = sim_state["pressure_psi"]
                f_base = sim_state["flow_rate_lps"]
                
                for i in range(10):
                    p_offset = (9 - i) * 1.5 if sim_state["scenario"] == "burst" else 0.0
                    f_offset = -(9 - i) * 2.0 if sim_state["scenario"] == "burst" else 0.0
                    readings.append({
                        "timestamp": f"2026-09-01T05:00:{10+i}Z",
                        "pressure_psi": round(max(0.0, p_base + p_offset), 2),
                        "flow_rate_lps": round(max(0.0, f_base + f_offset), 2),
                        "ambient_temp_c": sim_state["ambient_temp_c"]
                    })
                    
                batch_payload = {
                    "batch_id": "scada-manual-check",
                    "timestamp": "2026-09-01T05:00:20Z",
                    "telemetry_windows": [
                        {
                            "sensor_cluster_id": "cluster-desert-042",
                            "readings": readings
                        }
                    ]
                }
                
                try:
                    aia_resp = requests.post(f"{AIA_URL}/ingest", json=batch_payload, timeout=5.0)
                    if aia_resp.status_code == 200:
                        aia_out = aia_resp.json()
                        pd_st.success("Ingestion cycle complete!")
                        
                        if aia_out["anomalies_detected_count"] > 0:
                            threat = aia_out["investigated_threats"][0]
                            pd_st.write(f"**Anomaly Classification:** `{threat['classification']}`")
                            pd_st.write(f"**Assigned Severity Tier:** `Tier {threat['severity_tier']}`")
                            pd_st.write(f"**Logical Confidence Score:** `{threat['confidence_score']}`")
                            
                            # Log to alarm window
                            log_msg = f"[{threat['classification'].upper()}] {threat['operator_justification']}"
                            if log_msg not in pd_st.session_state.alert_logs:
                                pd_st.session_state.alert_logs.insert(0, log_msg)
                            
                            if threat['classification'] == "confirmed_anomaly" and threat['severity_tier'] == 3:
                                pd_st.error(f"🚨 CLOSED-LOOP SYSTEM INTERVENED: Valve isolated immediately.")
                                time.sleep(0.5)
                                pd_st.rerun()
                        else:
                            pd_st.info("🟢 Grid status verified: Normal operational parameters.")
                    else:
                        pd_st.error(f"AIA Gateway returned error code {aia_resp.status_code}")
                except Exception as e:
                    pd_st.error(f"AIA Connection failed: {e}")
                    
    with col_right:
        pd_st.subheader("🔔 SCADA Alarm Log & Operator Audit Trail")
        if pd_st.session_state.alert_logs:
            for log in pd_st.session_state.alert_logs[:10]:
                if "CONFIRMED_ANOMALY" in log:
                    pd_st.error(log)
                elif "INSTRUMENT_FAULT" in log:
                    pd_st.warning(log)
                else:
                    pd_st.info(log)
        else:
            pd_st.write("No active alarms recorded in this session.")
