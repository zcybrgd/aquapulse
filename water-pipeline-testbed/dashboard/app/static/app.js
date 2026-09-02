const state = {
  topology: [],
  faultsCatalog: {},
  clusterStatus: {},   // cluster_id -> {tier, classification}
  latestReadouts: {},  // cluster_id -> {pressure, flow, temp, active_fault}
};

const TIER_COLOR = { 1: "dot-yellow", 2: "dot-orange", 3: "dot-red" };

function classificationColorClass(classification, tier) {
  if (classification === "confirmed_instrument_fault") return "dot-gray";
  if (classification === "likely_connectivity_artifact") return "dot-blue";
  if (classification === "insufficient_data") return "dot-blue";
  if (classification === "confirmed_anomaly") return TIER_COLOR[tier] || "dot-yellow";
  return "dot-green";
}

async function loadTopology() {
  const res = await fetch("/api/topology");
  const data = await res.json();
  state.topology = data.segments;
  renderPipelineSvg();
  populateClusterSelect();
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
    opt.textContent = `${seg.sensor_cluster_id} (crit ${seg.criticality_score})`;
    sel.appendChild(opt);
  }
}

function populateFaultTypeSelect() {
  const sel = document.getElementById("sel-fault-type");
  sel.innerHTML = "";
  for (const ft of Object.keys(state.faultsCatalog)) {
    const opt = document.createElement("option");
    opt.value = ft;
    opt.textContent = ft;
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

function renderPipelineSvg() {
  const svg = document.getElementById("pipeline-svg");
  svg.innerHTML = "";
  const ns = "http://www.w3.org/2000/svg";
  const reservoirX = 60, reservoirY = 200;

  const reservoir = document.createElementNS(ns, "circle");
  reservoir.setAttribute("cx", reservoirX);
  reservoir.setAttribute("cy", reservoirY);
  reservoir.setAttribute("r", 30);
  reservoir.setAttribute("fill", "#1f2740");
  reservoir.setAttribute("stroke", "#3b5bfd");
  reservoir.setAttribute("stroke-width", "2");
  svg.appendChild(reservoir);

  const reservoirLabel = document.createElementNS(ns, "text");
  reservoirLabel.setAttribute("x", reservoirX);
  reservoirLabel.setAttribute("y", reservoirY + 45);
  reservoirLabel.setAttribute("text-anchor", "middle");
  reservoirLabel.setAttribute("class", "node-label");
  reservoirLabel.textContent = "Reservoir";
  svg.appendChild(reservoirLabel);

  const n = state.topology.length || 1;
  const startY = 60, endY = 380;
  const stepY = n > 1 ? (endY - startY) / (n - 1) : 0;
  const nodeX = 480;
  const endX = 820;

  state.topology.forEach((seg, i) => {
    const y = n > 1 ? startY + stepY * i : 200;

    const pipe = document.createElementNS(ns, "path");
    pipe.setAttribute("d", `M ${reservoirX + 30} ${reservoirY} L ${nodeX} ${y} L ${endX} ${y}`);
    pipe.setAttribute("class", "pipe-line");
    svg.appendChild(pipe);

    const node = document.createElementNS(ns, "circle");
    node.setAttribute("cx", nodeX);
    node.setAttribute("cy", y);
    node.setAttribute("r", 14);
    node.setAttribute("id", `node-${seg.sensor_cluster_id}`);
    node.setAttribute("fill", "#34d399");
    svg.appendChild(node);

    const valve = document.createElementNS(ns, "rect");
    valve.setAttribute("x", endX - 8);
    valve.setAttribute("y", y - 8);
    valve.setAttribute("width", 16);
    valve.setAttribute("height", 16);
    valve.setAttribute("fill", "#333f5e");
    svg.appendChild(valve);

    const label = document.createElementNS(ns, "text");
    label.setAttribute("x", nodeX);
    label.setAttribute("y", y - 20);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "node-label");
    label.textContent = seg.sensor_cluster_id;
    svg.appendChild(label);

    const sub = document.createElementNS(ns, "text");
    sub.setAttribute("x", endX + 12);
    sub.setAttribute("y", y + 4);
    sub.setAttribute("class", "node-sub");
    sub.textContent = seg.associated_valve_id;
    svg.appendChild(sub);
  });
}

function setNodeColorClass(clusterId, colorClass) {
  const node = document.getElementById(`node-${clusterId}`);
  if (!node) return;
  const colorMap = {
    "dot-green": "#34d399", "dot-yellow": "#fbbf24", "dot-orange": "#fb923c",
    "dot-red": "#f87171", "dot-gray": "#9ca3af", "dot-blue": "#60a5fa",
  };
  node.setAttribute("fill", colorMap[colorClass] || "#34d399");
}

function renderReadouts() {
  const tbody = document.querySelector("#readout-table tbody");
  tbody.innerHTML = "";
  for (const seg of state.topology) {
    const r = state.latestReadouts[seg.sensor_cluster_id] || {};
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${seg.sensor_cluster_id}</td>
      <td>${r.pressure_psi?.toFixed ? r.pressure_psi.toFixed(1) : "—"}</td>
      <td>${r.flow_rate_lps?.toFixed ? r.flow_rate_lps.toFixed(1) : "—"}</td>
      <td>${r.ambient_temp_c?.toFixed ? r.ambient_temp_c.toFixed(1) : "—"}</td>
      <td>${r.active_fault ? `${r.active_fault}${r.magnitude ? " ("+r.magnitude+")" : ""}` : "—"}</td>
    `;
    tbody.appendChild(tr);
  }
}

function addFeedItem(threat) {
  const list = document.getElementById("feed-list");
  const div = document.createElement("div");
  const tierClass = threat.classification === "confirmed_anomaly" ? `tier-${threat.severity_tier}`
    : threat.classification === "confirmed_instrument_fault" ? "tag-instrument"
    : threat.classification === "likely_connectivity_artifact" ? "tag-artifact"
    : "tag-insufficient";
  div.className = `feed-item ${tierClass}`;
  div.innerHTML = `
    <div class="feed-head">
      <span>${threat.sensor_cluster_id}</span>
      <span>${threat.classification} · Tier ${threat.severity_tier}</span>
    </div>
    <div class="feed-meta">confidence ${threat.confidence_score.toFixed(2)} · segment ${threat.segment_id}</div>
    <div class="feed-memo">${threat.operator_justification}</div>
  `;
  list.prepend(div);
  while (list.children.length > 30) list.removeChild(list.lastChild);
}

function connectWebSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    document.getElementById("conn-dot").className = "dot dot-green";
    document.getElementById("conn-label").textContent = "connected";
  };
  ws.onclose = () => {
    document.getElementById("conn-dot").className = "dot dot-red";
    document.getElementById("conn-label").textContent = "disconnected — retrying…";
    setTimeout(connectWebSocket, 2000);
  };
  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    if (msg.type === "sim_state") {
      document.getElementById("tick-label").textContent = `tick ${msg.tick}`;
      document.getElementById("temp-label").textContent = `env ${msg.environment_temp_c.toFixed(1)}°C`;
      for (const [cid, c] of Object.entries(msg.clusters)) {
        state.latestReadouts[cid] = c;
        if (!c.active_fault) {
          // No active fault: keep whatever last classification color was set by
          // the AIA feed a little while, but a fresh reset/clear should visibly
          // relax back to green so the operator can tell the fault is gone.
        }
      }
      renderReadouts();
    } else if (msg.type === "aia_results") {
      for (const threat of msg.investigated_threats) {
        setNodeColorClass(threat.sensor_cluster_id, classificationColorClass(threat.classification, threat.severity_tier));
        addFeedItem(threat);
      }
    }
  };
}

function wireControlPanel() {
  document.getElementById("btn-start").onclick = () => fetch("/api/control/start", { method: "POST" });
  document.getElementById("btn-stop").onclick = () => fetch("/api/control/stop", { method: "POST" });
  document.getElementById("btn-reset").onclick = async () => {
    await fetch("/api/control/reset", { method: "POST" });
    for (const seg of state.topology) setNodeColorClass(seg.sensor_cluster_id, "dot-green");
    document.getElementById("feed-list").innerHTML = "";
  };
  document.getElementById("btn-clear-all").onclick = async () => {
    await fetch("/api/control/clear_all_faults", { method: "POST" });
    for (const seg of state.topology) setNodeColorClass(seg.sensor_cluster_id, "dot-green");
  };

  document.querySelectorAll("[data-temp]").forEach((btn) => {
    btn.onclick = () => fetch("/api/control/set_temperature", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: btn.dataset.temp }),
    });
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
      ? `Injected: ${data.description}`
      : `Error: ${data.detail || "could not inject fault"}`;
  };

  document.getElementById("btn-outage-on").onclick = async () => {
    const cluster_id = document.getElementById("sel-cluster").value;
    const res = await fetch(`/api/control/simulate_api_outage/${cluster_id}`, { method: "POST" });
    document.getElementById("inject-feedback").textContent =
      `Simulated Nokia NaC platform outage for ${cluster_id}`;
  };

  document.getElementById("btn-outage-off").onclick = async () => {
    const cluster_id = document.getElementById("sel-cluster").value;
    await fetch(`/api/control/clear_api_outage/${cluster_id}`, { method: "POST" });
    document.getElementById("inject-feedback").textContent =
      `Cleared Nokia NaC platform outage for ${cluster_id}`;
  };
}

(async function init() {
  await loadTopology();
  await loadFaultsCatalog();
  wireControlPanel();
  connectWebSocket();
})();
