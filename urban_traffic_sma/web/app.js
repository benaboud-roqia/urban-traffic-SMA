// ── État local ────────────────────────────────────────────────────────────────
const state = {
  lights:   { A:{status:"RED",nb:0,dur:10,force:false}, B:{status:"RED",nb:0,dur:10,force:false}, C:{status:"RED",nb:0,dur:10,force:false} },
  vehicles: {},
  weather:  { condition:"NORMAL", factor:1.0 },
  selectedInter: "A",
  extraVehicles: 0,
};

// ── WebSocket ─────────────────────────────────────────────────────────────────
let ws = null;

function connect() {
  ws = new WebSocket("ws://localhost:8765");
  ws.onopen    = () => { setStatus(true);  log("🔗 Connecté au serveur SMA", "ctrl"); };
  ws.onmessage = (e) => { try { handleMessage(JSON.parse(e.data)); } catch(err){} };
  ws.onclose   = () => { setStatus(false); log("⚠️ Reconnexion dans 3s...", "emerg"); setTimeout(connect, 3000); };
  ws.onerror   = () => ws.close();
}

function send(data) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
}

function setStatus(ok) {
  const el  = document.getElementById("wsStatus");
  const dot = el.querySelector(".dot");
  dot.className = "dot " + (ok ? "connected" : "disconnected");
  el.lastChild.textContent = ok ? " Connecté" : " Déconnecté";
}

// ── Router ────────────────────────────────────────────────────────────────────
function handleMessage(d) {
  switch(d.type) {
    case "light":      updateLight(d);      break;
    case "vehicle":    updateVehicle(d);    break;
    case "emergency":  updateEmergency(d);  break;
    case "parking":    updateParking(d);    break;
    case "weather":    updateWeather(d);    break;
    case "monitor":    updateStats(d);      break;
    case "controller": updateController(d); break;
    case "log":        log(d.msg, d.category || "info"); break;
  }
}

// ── Feux ──────────────────────────────────────────────────────────────────────
function updateLight(d) {
  const { id: inter, status, green_duration: dur, vehicles_waiting: nb, force } = d;
  state.lights[inter] = { status, nb, dur, force };

  const isGreen = status === "GREEN";

  // Panneau gauche
  const rBulb = document.getElementById(`bulb-${inter}-red`);
  const gBulb = document.getElementById(`bulb-${inter}-green`);
  const badge = document.getElementById(`badge-${inter}`);
  const detail= document.getElementById(`detail-${inter}`);
  const prog  = document.getElementById(`prog-${inter}`);

  if (rBulb) {
    rBulb.className = "bulb red"   + ((!isGreen && !force) ? " active" : "");
    gBulb.className = "bulb green" + ((isGreen || force)   ? " active" : "");
    badge.textContent = force ? "🚨 URGENCE" : status;
    badge.className   = "badge " + (force ? "orange" : (isGreen ? "green" : "red"));
    detail.textContent = `${nb} véh · ${dur}s`;
    prog.style.width = (isGreen ? Math.min(100,(dur/25)*100) : 0) + "%";
  }

  // Carte centrale
  const mr = document.getElementById(`mBulb-${inter}-r`);
  const mg = document.getElementById(`mBulb-${inter}-g`);
  if (mr) {
    mr.className = "map-bulb r" + ((!isGreen && !force) ? " on" : "");
    mg.className = "map-bulb g" + (force ? " emergency" : (isGreen ? " on" : ""));
  }

  log(`🚦 Feu ${inter}: ${force?"🚨 URGENCE":status} | ${nb} véh | ${dur}s`, "light");
}

// ── Véhicules ─────────────────────────────────────────────────────────────────
const VEH_IDS = ["v1","v2","v3","v4","v5"];
const VEH_COLORS = ["#6366f1","#0ea5e9","#16a34a","#ca8a04","#7c3aed"];

function initVehicles() {
  const c = document.getElementById("vehicles-container");
  VEH_IDS.forEach((vid, i) => {
    c.innerHTML += `
    <div class="veh-row" id="veh-row-${vid}">
      <div class="veh-id">🚗 ${vid}</div>
      <div class="veh-bar-wrap">
        <div class="veh-bar" id="veh-bar-${vid}" style="width:0%;background:${VEH_COLORS[i]}"></div>
      </div>
      <div class="veh-info" id="veh-info-${vid}">
        <span class="inter">A</span> · 0m · <span class="go">🟢 0s</span>
      </div>
    </div>`;
  });
  initMapVehicles();
}

// Positions sur la carte (x%, y%)
const VEH_POSITIONS = {
  v1: { A:[48,60], B:[20,48], C:[48,30] },
  v2: { A:[55,42], B:[30,52], C:[52,22] },
  v3: { A:[42,55], B:[25,44], C:[44,35] },
  v4: { A:[58,50], B:[35,50], C:[50,18] },
  v5: { A:[45,65], B:[18,55], C:[55,28] },
};

function initMapVehicles() {
  const container = document.getElementById("mapVehicles");
  VEH_IDS.forEach((vid, i) => {
    const el = document.createElement("div");
    el.className = "map-vehicle";
    el.id = `mapVeh-${vid}`;
    el.textContent = vid;
    el.style.background = VEH_COLORS[i];
    el.style.left = "50%"; el.style.top = "50%";
    container.appendChild(el);
  });
}

function updateVehicle(d) {
  const { id: vid, intersection: inter, position: pos, waiting, wait_time } = d;
  state.vehicles[vid] = d;

  // Barre
  const bar  = document.getElementById(`veh-bar-${vid}`);
  const info = document.getElementById(`veh-info-${vid}`);
  if (bar) {
    bar.style.width = Math.max(0, ((150-pos)/150)*100) + "%";
    bar.className = "veh-bar" + (waiting ? " waiting" : "");
    const wHtml = waiting
      ? `<span class="wait">🔴 ${wait_time}s</span>`
      : `<span class="go">🟢 ${wait_time}s</span>`;
    info.innerHTML = `<span class="inter">${inter}</span> · ${pos}m · ${wHtml}`;
  }

  // Carte
  const mapEl = document.getElementById(`mapVeh-${vid}`);
  if (mapEl) {
    const positions = VEH_POSITIONS[vid];
    const [px, py] = positions ? (positions[inter] || positions["A"]) : [50,50];
    // Légère variation aléatoire pour éviter superposition
    const jx = (Math.sin(Date.now()/1200 + vid.charCodeAt(1)) * 3);
    const jy = (Math.cos(Date.now()/1200 + vid.charCodeAt(1)) * 3);
    mapEl.style.left = (px + jx) + "%";
    mapEl.style.top  = (py + jy) + "%";
    mapEl.className  = "map-vehicle" + (waiting ? " waiting" : "");
    mapEl.title = `${vid} | ${inter} | ${pos}m | ${waiting?"ATTENTE":"EN ROUTE"}`;
  }
}

// ── Urgences ──────────────────────────────────────────────────────────────────
function updateEmergency(d) {
  const row    = document.getElementById(`emerg-${d.id}`);
  const status = document.getElementById(`emerg-status-${d.id}`);
  const pos    = document.getElementById(`emerg-pos-${d.id}`);
  if (!row) return;
  if (d.active) {
    row.classList.add("active");
    status.className = "emerg-status active";
    status.textContent = `🚨 ACTIF — Inter. ${d.intersection}`;
    pos.textContent = `${d.position}m`;
    log(`🚨 ${d.vehicle_type} ${d.id}: URGENCE → ${d.intersection}`, "emerg");
  } else {
    row.classList.remove("active");
    status.className = "emerg-status inactive";
    status.textContent = "💤 INACTIF";
    pos.textContent = "—";
  }
}

// ── Parking ───────────────────────────────────────────────────────────────────
function updateParking(d) {
  const bar  = document.getElementById(`park-bar-${d.id}`);
  const info = document.getElementById(`park-info-${d.id}`);
  if (!bar) return;
  const pct = (d.occupied / d.capacity) * 100;
  bar.style.width = pct + "%";
  bar.className = "park-bar" + (pct>=100?" danger":pct>=80?" warn":"");
  info.textContent = `${d.occupied}/${d.capacity} · ${d.status}`;
  log(`🅿️ ${d.id}: ${d.occupied}/${d.capacity} (${d.status})`, "park");
}

// ── Météo ─────────────────────────────────────────────────────────────────────
const WEATHER_ICONS   = {NORMAL:"☀️",PLUIE:"🌧️",BROUILLARD:"🌫️",NEIGE:"❄️",VERGLAS:"🧊"};
const WEATHER_COLORS  = {NORMAL:"#0ea5e9",PLUIE:"#60a5fa",BROUILLARD:"#94a3b8",NEIGE:"#cbd5e1",VERGLAS:"#f472b6"};

function updateWeather(d) {
  state.weather = d;
  document.getElementById("weatherIcon").textContent   = WEATHER_ICONS[d.condition]  || "☀️";
  document.getElementById("weatherName").textContent   = d.condition;
  document.getElementById("weatherFactor").textContent = d.speed_factor;
  const bar = document.getElementById("weatherBar");
  bar.style.width = (d.speed_factor * 100) + "%";
  bar.style.background = `linear-gradient(90deg,${WEATHER_COLORS[d.condition]||"#0ea5e9"},#6366f1)`;
  log(`🌦️ Météo: ${d.condition} (facteur ${d.speed_factor})`, "weather");
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function updateStats(d) {
  setText("statCycle",   d.cycle);
  setText("statWaiting", d.total_waiting);
  setText("statAvg",     d.avg_wait + "s");
  setText("statEmerg",   d.emergencies);
  setText("statOptim",   d.optimizations);
  setText("statWeather", d.weather_alerts);
}

function updateController(d) {
  setText("ctrlWaiting", d.total_waiting);
  setText("ctrlOptim",   d.optimizations);
  if (d.last_action) document.getElementById("ctrlLog").textContent = d.last_action;
  log("🧠 " + (d.last_action || "Optimisation en cours..."), "ctrl");
}

// ── Simulation Manuelle ───────────────────────────────────────────────────────
function selectInter(inter) {
  state.selectedInter = inter;
  ["A","B","C"].forEach(i => {
    document.getElementById(`iBtn-${i}`).className =
      "inter-btn" + (i === inter ? " selected" : "");
  });
  log(`🎯 Intersection ${inter} sélectionnée`, "info");
}

function manualCmd(cmd) {
  const inter = state.selectedInter;
  send({ type: "manual", cmd, intersection: inter });

  // Feedback visuel immédiat
  switch(cmd) {
    case "force_green":
      log(`🟢 Feu ${inter} → VERT forcé manuellement`, "light");
      simulateLight(inter, "GREEN", true);
      break;
    case "force_red":
      log(`🔴 Feu ${inter} → ROUGE forcé manuellement`, "light");
      simulateLight(inter, "RED", false);
      break;
    case "auto":
      log(`🔄 Feu ${inter} → Mode automatique`, "light");
      break;
    case "emergency_amb":
      log(`🚑 Ambulance déclenchée → Intersection ${inter}`, "emerg");
      simulateEmergency("amb1", "AMBULANCE", inter);
      break;
    case "emergency_pol":
      log(`🚓 Police déclenchée → Intersection ${inter}`, "emerg");
      simulateEmergency("pol1", "POLICE", inter);
      break;
    case "add_vehicle":
      log(`🚗 Véhicule ajouté sur intersection ${inter}`, "veh");
      break;
    case "clear_vehicles":
      log(`🗑️ Véhicules vidés sur intersection ${inter}`, "veh");
      break;
    case "park_full_P1":
      log(`🅿️ P1 → PLEIN (manuel)`, "park");
      simulateParking("P1", 20, 20);
      break;
    case "park_full_P2":
      log(`🅿️ P2 → PLEIN (manuel)`, "park");
      simulateParking("P2", 15, 15);
      break;
    case "park_reset":
      log(`🅿️ Parkings réinitialisés`, "park");
      simulateParking("P1", 5, 20);
      simulateParking("P2", 3, 15);
      break;
  }
}

function setWeather(condition) {
  send({ type: "manual", cmd: "set_weather", condition });
  const factors = {NORMAL:1.0,PLUIE:0.7,BROUILLARD:0.5,NEIGE:0.4,VERGLAS:0.3};
  updateWeather({ condition, speed_factor: factors[condition] });
}

// Simulations locales (feedback immédiat sans attendre le serveur)
function simulateLight(inter, status, force) {
  updateLight({ id:inter, status, green_duration:15, vehicles_waiting:state.lights[inter].nb, force });
}

function simulateEmergency(eid, vtype, inter) {
  updateEmergency({ id:eid, vehicle_type:vtype, active:true, intersection:inter, position:80 });
  setTimeout(() => updateEmergency({ id:eid, vehicle_type:vtype, active:false, intersection:inter, position:0 }), 8000);
}

function simulateParking(pid, occupied, capacity) {
  const statuses = {0:"DISPONIBLE"};
  const pct = (occupied/capacity)*100;
  const status = pct>=100?"PLEIN":pct>=80?"PRESQUE PLEIN":"DISPONIBLE";
  updateParking({ id:pid, occupied, capacity, status });
}

// ── Log ───────────────────────────────────────────────────────────────────────
let logCount = 0;
function log(msg, cat="info") {
  const box = document.getElementById("logBox");
  const ts  = new Date().toLocaleTimeString("fr-FR");
  const div = document.createElement("div");
  div.className = `log-entry log-${cat}`;
  div.innerHTML = `<span class="log-ts">[${ts}]</span>${msg}`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  if (++logCount > 150) { box.removeChild(box.firstChild); logCount--; }
}
function clearLog() {
  document.getElementById("logBox").innerHTML = "";
  logCount = 0;
}

// ── Horloge ───────────────────────────────────────────────────────────────────
function updateClock() {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString("fr-FR");
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Init ──────────────────────────────────────────────────────────────────────
initVehicles();
setInterval(updateClock, 1000);
connect();
