const state = {
  topology: [],
  faultsCatalog: {},
  latestReadouts: {},
  outageClusters: new Set(),
  sceneReady: false,
};

async function loadTopology() {
  const res = await fetch("/api/topology");
  const data = await res.json();
  state.topology = data.segments;
  populateClusterSelect();
  initScene();
}

function initScene() {
  const container = document.getElementById("scene-container");
  if (!container) return;

  // three-scene.js is a separate module that must fetch its own imports
  // (three.js + OrbitControls) from the CDN before `window.PipelineScene`
  // exists. Poll briefly rather than assuming it's already loaded by the
  // time this runs.
  const deadline = Date.now() + 8000;
  const tryInit = () => {
    if (window.PipelineScene) {
      try {
        window.PipelineScene.init(container, state.topology);
        state.sceneReady = true;
      } catch (err) {
        console.error("3D scene failed to initialize:", err);
        container.innerHTML = '<div class="scene-hint" style="position:static;padding:24px;">3D view unavailable in this browser.</div>';
      }
      return;
    }
    if (Date.now() < deadline) {
      setTimeout(tryInit, 100);
    } else {
      container.innerHTML = '<div class="scene-hint" style="position:static;padding:24px;">3D view failed to load (network or WebGL issue). The rest of the dashboard is unaffected.</div>';
    }
  };
  tryInit();
}

async function loadFaultsCatalog() {
  const res = await fetch("/api/faults/catalog");
  state.faultsCatalog = await res.json();
  populateFaultTypeSelect();
}

function populateClusterSelect() {
  const sel = document.getElementById("sel-cluster");
  sel.innerHTML = "";
  for (const seg of state.topology) {
    const opt = document.createElement("option");
    opt.value = seg.sensor_cluster_id;
    opt.textContent = `${seg.sensor_cluster_id} (criticality ${seg.criticality_score})`;
    sel.appendChild(opt);
  }
  sel.addEventListener("change", syncOutageButtonLabel);
}

function populateFaultTypeSelect() {
  const sel = document.getElementById("sel-fault-type");
  sel.innerHTML = "";
  for (const ft of Object.keys(state.faultsCatalog)) {
    const opt = document.createElement("option");
    opt.value = ft;
    opt.textContent = ft.replaceAll("_", " ");
    sel.appendChild(opt);
  }
  sel.addEventListener("change", populateMagnitudeSelect);
  populateMagnitudeSelect();
}

function populateMagnitudeSelect() {
  const ft = document.getElementById("sel-fault-type").value;
  const magSel = document.getElementById("sel-magnitude");
  magSel.innerHTML = "";
  for (const m of state.faultsCatalog[ft] || ["default"]) {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    magSel.appendChild(opt);
  }
}

function renderReadouts() {
  const tbody = document.querySelector("#readout-table tbody");
  tbody.innerHTML = "";
  for (const seg of state.topology) {
    const r = state.latestReadouts[seg.sensor_cluster_id] || {};
    const tr = document.createElement("tr");
    const faultLabel = r.active_fault ? `${r.active_fault.replaceAll("_", " ")}${r.magnitude ? " (" + r.magnitude + ")" : ""}` : "nominal";
    tr.innerHTML = `
      <td>${seg.sensor_cluster_id}</td>
      <td>${fmt(r.pressure_psi)} psi</td>
      <td>${fmt(r.flow_rate_lps)} L/s</td>
      <td>${fmt(r.ambient_temp_c)}°C</td>
      <td class="${r.active_fault ? "state-fault" : "state-normal"}">${faultLabel}</td>
    `;
    tbody.appendChild(tr);
  }
}

function fmt(v) {
  return typeof v === "number" ? v.toFixed(1) : "—";
}

function appendRawLog(entry) {
  const console_ = document.getElementById("raw-log-console");
  const line = document.createElement("div");
  line.className = "log-line";
  const value = entry.value === null || entry.value === undefined ? entry.status : `${entry.value}${entry.unit ? " " + entry.unit : ""}`;
  const statusClass = entry.status === "fault" ? "lg-fault" : entry.status === "stale" ? "lg-stale" : "";
  line.innerHTML = `<span class="lg-ts">${entry.timestamp.slice(11, 19)}</span> <span class="lg-dev">${entry.device_id}</span> ${entry.measurement}=<span class="${statusClass}">${value}</span> [${entry.status}]`;
  console_.appendChild(line);
  while (console_.children.length > 200) console_.removeChild(console_.firstChild);
  console_.scrollTop = console_.scrollHeight;
}

function classificationTierClass(threat) {
  if (threat.classification === "confirmed_anomaly") return `tier-${threat.severity_tier}`;
  if (threat.classification === "confirmed_instrument_fault") return "tag-instrument";
  if (threat.classification === "likely_connectivity_artifact") return "tag-artifact";
  return "tag-insufficient";
}

function addFeedItem(threat) {
  const emptyState = document.getElementById("feed-empty");
  if (emptyState) emptyState.remove();

  const list = document.getElementById("feed-list");
  const div = document.createElement("div");
  div.className = `feed-item ${classificationTierClass(threat)}`;
  div.innerHTML = `
    <div class="feed-head">
      <span class="feed-cluster">${threat.sensor_cluster_id}</span>
      <span class="feed-tier-badge">${threat.classification.replaceAll("_", " ")} · T${threat.severity_tier}</span>
    </div>
    <div class="feed-meta">
      <span>segment ${threat.segment_id}</span>
      <span>confidence ${(threat.confidence_score * 100).toFixed(0)}%</span>
    </div>
    <div class="feed-evidence">
      <span class="evidence-chip">Δp ${threat.physical_deviations.pressure_drop_pct.toFixed(1)}%</span>
      <span class="evidence-chip">Δq ${threat.physical_deviations.flow_surge_pct.toFixed(1)}%</span>
      <span class="evidence-chip">CAMARA: ${threat.network_status.camara_reachability_status}</span>
      <span class="evidence-chip">congestion: ${threat.network_status.camara_congestion_level}</span>
    </div>
    <div class="feed-memo">${threat.operator_justification}</div>
  `;
  list.prepend(div);
  while (list.children.length > 40) list.removeChild(list.lastChild);

  if (window.PipelineScene && state.sceneReady) {
    window.PipelineScene.setVerdict(threat.sensor_cluster_id, threat.classification, threat.severity_tier);
  }
}

function resetFeed() {
  const list = document.getElementById("feed-list");
  list.innerHTML = '<div class="feed-empty" id="feed-empty">No investigations yet. Inject a fault on the left and the agent will evaluate incoming telemetry independently.</div>';
  if (window.PipelineScene) window.PipelineScene.clearAllVerdicts();
}

function connectWebSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    document.getElementById("conn-label").innerHTML = '<i id="conn-dot" class="status-dot status-dot--on"></i>connected';
  };
  ws.onclose = () => {
    document.getElementById("conn-label").innerHTML = '<i id="conn-dot" class="status-dot status-dot--off"></i>reconnecting…';
    setTimeout(connectWebSocket, 2000);
  };
  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);

    if (msg.type === "sim_state") {
      document.getElementById("tick-label").textContent = msg.tick;
      document.getElementById("temp-label").textContent = `${msg.environment_temp_c.toFixed(1)}°C`;
      for (const [cid, c] of Object.entries(msg.clusters)) {
        state.latestReadouts[cid] = c;
        if (window.PipelineScene && state.sceneReady) {
          window.PipelineScene.updateCluster(cid, c);
        }
      }
      renderReadouts();
    } else if (msg.type === "raw_logs") {
      for (const entry of msg.logs) appendRawLog(entry);
    } else if (msg.type === "aia_results") {
      for (const threat of msg.investigated_threats) addFeedItem(threat);
    }
  };
}

function wireControlPanel() {
  document.getElementById("btn-start").onclick = () => fetch("/api/control/start", { method: "POST" });
  document.getElementById("btn-stop").onclick = () => fetch("/api/control/stop", { method: "POST" });
  document.getElementById("btn-reset").onclick = async () => {
    await fetch("/api/control/reset", { method: "POST" });
    resetFeed();
    document.getElementById("raw-log-console").innerHTML = "";
    state.outageClusters.clear();
    syncOutageButtonLabel();
    document.getElementById("inject-feedback").textContent = "Idle — no fault staged.";
  };

  document.querySelectorAll("#temp-segmented [data-temp]").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll("#temp-segmented .segmented-btn").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      fetch("/api/control/set_temperature", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset: btn.dataset.temp }),
      });
    };
  });

  document.getElementById("btn-inject").onclick = async () => {
    const cluster_id = document.getElementById("sel-cluster").value;
    const fault_type = document.getElementById("sel-fault-type").value;
    const magnitude = document.getElementById("sel-magnitude").value;
    const feedback = document.getElementById("inject-feedback");
    const res = await fetch("/api/control/inject_fault", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cluster_id, fault_type, magnitude }),
    });
    const data = await res.json();
    feedback.textContent = res.ok
      ? `Fault staged on ${cluster_id}: ${data.description}`
      : `Could not stage fault: ${data.detail || "unknown error"}`;
  };

  document.getElementById("btn-clear-all").onclick = async () => {
    await fetch("/api/control/clear_all_faults", { method: "POST" });
    document.getElementById("inject-feedback").textContent = "All faults cleared.";
  };

  document.getElementById("btn-outage-toggle").onclick = async () => {
    const cluster_id = document.getElementById("sel-cluster").value;
    const feedback = document.getElementById("inject-feedback");
    if (state.outageClusters.has(cluster_id)) {
      await fetch(`/api/control/clear_api_outage/${cluster_id}`, { method: "POST" });
      state.outageClusters.delete(cluster_id);
      feedback.textContent = `Nokia NaC platform outage cleared for ${cluster_id}.`;
    } else {
      await fetch(`/api/control/simulate_api_outage/${cluster_id}`, { method: "POST" });
      state.outageClusters.add(cluster_id);
      feedback.textContent = `Simulating a Nokia NaC platform outage for ${cluster_id}.`;
    }
    syncOutageButtonLabel();
  };
}

function syncOutageButtonLabel() {
  const cluster_id = document.getElementById("sel-cluster").value;
  const btn = document.getElementById("btn-outage-toggle");
  btn.textContent = state.outageClusters.has(cluster_id) ? "Clear NaC Outage" : "Simulate NaC Outage";
}

(async function initApp() {
  await loadTopology();
  await loadFaultsCatalog();
  wireControlPanel();
  connectWebSocket();
})();
