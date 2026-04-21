"""
Serveur WebSocket — SMA Trafic Urbain
Fait tourner les 15 agents et diffuse leur état en JSON vers le navigateur.
"""

import asyncio
import json
import random
import threading
import webbrowser
import os
from collections import defaultdict
from http.server import HTTPServer, SimpleHTTPRequestHandler

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

# ── Bus de messages interne ───────────────────────────────────────────────────
class MessageBus:
    def __init__(self):
        self._q = defaultdict(asyncio.Queue)

    async def send(self, to, msg_type, body, sender="?"):
        await self._q[to].put({"type": msg_type, "body": body, "from": sender})

    async def receive(self, agent_id, timeout=0.1):
        try:
            return await asyncio.wait_for(self._q[agent_id].get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

BUS = MessageBus()

# ── État partagé ──────────────────────────────────────────────────────────────
class State:
    def __init__(self):
        self.lights = {
            k: {"status":"RED","green_dur":10,"nb":0,"force":False}
            for k in ["A","B","C"]
        }
        self.weather = "NORMAL"
        self.total_waiting = 0
        self.optimizations = 0
        self.emergencies = 0
        self.weather_alerts = 0
        self.cycle = 0
        self.wait_times = []
        self.last_ctrl_action = ""

STATE = State()

WEATHER_FACTOR = {"NORMAL":1.0,"PLUIE":0.7,"BROUILLARD":0.5,"NEIGE":0.4,"VERGLAS":0.3}
WEATHER_EXTRA  = {"NORMAL":0,"PLUIE":3,"BROUILLARD":5,"NEIGE":7,"VERGLAS":8}

# ── Clients WebSocket connectés ───────────────────────────────────────────────
clients = set()

async def broadcast(data: dict):
    if not clients:
        return
    msg = json.dumps(data)
    await asyncio.gather(*[c.send(msg) for c in list(clients)], return_exceptions=True)

async def ws_log(msg, category="info"):
    await broadcast({"type":"log","msg":msg,"category":category})

# ── Agents ────────────────────────────────────────────────────────────────────

async def agent_vehicle(vid):
    inter = random.choice(["A","B","C"])
    pos   = random.randint(50, 150)
    speed = random.randint(20, 60)
    waiting   = False
    wait_time = 0
    weather_f = 1.0

    print(f"[SETUP] 🚗 Véhicule {vid}")

    while True:
        msg = await BUS.receive(f"vehicle_{vid}")
        if msg:
            t = msg["type"]
            if t == "light_status":
                parts = msg["body"].split("|")
                waiting = (parts[0] == "RED")
                if parts[0] == "GREEN":
                    wait_time = 0
            elif t == "weather":
                parts = msg["body"].split("|")
                weather_f = float(parts[1])
                speed = max(10, int(speed * weather_f))
            elif t == "redirect":
                old = inter
                inter = random.choice([x for x in ["A","B","C"] if x != inter])
                await ws_log(f"🔀 Véhicule {vid}: redirigé {old}→{inter}", "veh")

        if not waiting:
            pos = max(0, pos - int(random.randint(5,15) * weather_f))
        else:
            wait_time += 1

        await BUS.send(f"light_{inter.lower()}", "position",
                       f"{vid}|{pos}|{speed}|{inter}", sender=f"vehicle_{vid}")
        await BUS.send("monitor", "stats_vehicle", f"{vid}|{wait_time}")

        STATE.wait_times.append(wait_time)
        if len(STATE.wait_times) > 100:
            STATE.wait_times.pop(0)

        await broadcast({"type":"vehicle","id":vid,"intersection":inter,
                         "position":pos,"speed":speed,
                         "waiting":waiting,"wait_time":wait_time})

        if pos <= 0:
            pos = random.randint(80, 150)
            inter = random.choice(["A","B","C"])
            wait_time = 0

        await asyncio.sleep(2)

async def agent_traffic_light(inter):
    timer = 0; status = "RED"; green_dur = 10; red_dur = 10
    force_green = False; force_timer = 0; weather_extra = 0
    vehicles_near = {}

    print(f"[SETUP] 🚦 Feu {inter}")

    while True:
        msg = await BUS.receive(f"light_{inter.lower()}")
        if msg:
            t = msg["type"]
            if t == "position":
                parts = msg["body"].split("|")
                vid, pos, v_inter = parts[0], int(parts[1]), parts[3]
                if v_inter == inter:
                    vehicles_near[vid] = pos if pos < 30 else vehicles_near.pop(vid, None) or None
                    if pos >= 30:
                        vehicles_near.pop(vid, None)
                    else:
                        vehicles_near[vid] = pos
                await BUS.send(f"vehicle_{vid}", "light_status",
                               f"{status}|{green_dur}", sender=f"light_{inter.lower()}")
            elif t == "force_green":
                parts = msg["body"].split("|")
                dur = int(parts[2]) if len(parts) > 2 else 15
                force_green = True; force_timer = dur; status = "GREEN"
                await ws_log(f"🚦 Feu {inter}: 🚨 VERT FORCÉ {dur}s", "light")
            elif t == "force_red":
                force_green = False; force_timer = 0; status = "RED"
                await ws_log(f"🚦 Feu {inter}: 🔴 ROUGE forcé", "light")
            elif t == "set_auto":
                force_green = False; force_timer = 0
                await ws_log(f"🚦 Feu {inter}: 🔄 Mode auto", "light")
            elif t in ("weather_adjust","weather_alert"):
                weather_extra = WEATHER_EXTRA.get(msg["body"].split("|")[0], 0)
            elif t == "optimize":
                parts = msg["body"].split("|")
                if parts[0] == "EXTEND_GREEN":
                    green_dur = min(25, green_dur + int(parts[2]))

        timer += 2
        nb = len(vehicles_near)

        if force_green:
            status = "GREEN"; force_timer -= 2
            if force_timer <= 0:
                force_green = False
        else:
            green_dur = min(25, 8 + nb * 2 + weather_extra)
            phase = timer % (green_dur + red_dur)
            new_s = "GREEN" if phase < green_dur else "RED"
            if new_s != status:
                status = new_s
                await ws_log(f"🚦 Feu {inter}: {status} | {nb} véh | {green_dur}s", "light")

        STATE.lights[inter] = {"status":status,"green_dur":green_dur,
                               "nb":nb,"force":force_green}

        await BUS.send("controller","light_report",
                       f"{inter}|{status}|{nb}|{green_dur}")
        await broadcast({"type":"light","id":inter,"status":status,
                         "green_duration":green_dur,"vehicles_waiting":nb,
                         "force":force_green})
        await asyncio.sleep(2)

async def agent_controller():
    print("[SETUP] 🧠 Contrôleur")

    while True:
        msg = await BUS.receive("controller", timeout=0.5)
        if msg:
            t = msg["type"]
            if t == "emergency":
                parts = msg["body"].split("|")
                inter = parts[1]
                await BUS.send(f"light_{inter.lower()}","force_green",
                               f"EMERGENCY|{inter}|15")
                STATE.emergencies += 1; STATE.optimizations += 1
                action = f"🚨 URGENCE {inter} → VERT forcé"
                STATE.last_ctrl_action = action
                await ws_log(f"🧠 Contrôleur: {action}", "ctrl")
            elif t == "weather_alert":
                cond = msg["body"]
                for i in ["A","B","C"]:
                    await BUS.send(f"light_{i.lower()}","weather_adjust",cond)
                STATE.weather_alerts += 1
                action = f"🌦️ Météo '{cond}' → feux ajustés"
                STATE.last_ctrl_action = action
                await ws_log(f"🧠 Contrôleur: {action}", "ctrl")
            elif t == "parking_full":
                inter = msg["body"]
                for vid in ["v1","v2","v3","v4","v5"]:
                    await BUS.send(f"vehicle_{vid}","redirect",f"PARKING_FULL|{inter}")
                action = f"🅿️ Parking {inter} plein → redirection"
                STATE.last_ctrl_action = action
                await ws_log(f"🧠 Contrôleur: {action}", "ctrl")

        # Optimisation proactive
        busiest = max(STATE.lights, key=lambda k: STATE.lights[k]["nb"])
        d = STATE.lights[busiest]
        if d["nb"] > 3 and d["status"] == "RED":
            await BUS.send(f"light_{busiest.lower()}","optimize",
                           f"EXTEND_GREEN|{busiest}|5")
            STATE.optimizations += 1
            action = f"⚡ Extension verte {busiest} ({d['nb']} véh)"
            STATE.last_ctrl_action = action

        total = sum(x["nb"] for x in STATE.lights.values())
        STATE.total_waiting = total
        await broadcast({"type":"controller","total_waiting":total,
                         "optimizations":STATE.optimizations,
                         "last_action":STATE.last_ctrl_action})
        await asyncio.sleep(4)

async def agent_emergency(eid, vtype):
    pos = random.randint(80, 200); active = False
    inter = random.choice(["A","B","C"])
    print(f"[SETUP] 🚨 {vtype} {eid}")

    while True:
        if not active and random.random() < 0.15:
            active = True; pos = random.randint(60,150)
            inter = random.choice(["A","B","C"])
            await ws_log(f"🚨 {vtype} {eid}: URGENCE → {inter}", "emerg")

        if active:
            pos = max(0, pos - 20)
            await BUS.send("controller","emergency",f"{eid}|{inter}|{vtype}")
            await BUS.send(f"light_{inter.lower()}","force_green",
                           f"EMERGENCY|{inter}|15")
            if pos <= 0:
                active = False
                await ws_log(f"🚨 {vtype} {eid}: Mission terminée", "emerg")

        await broadcast({"type":"emergency","id":eid,"vehicle_type":vtype,
                         "active":active,"intersection":inter,"position":pos})
        await asyncio.sleep(3)

async def agent_parking(pid, inter, capacity):
    occupied = random.randint(0, capacity - 2)
    print(f"[SETUP] 🅿️ Parking {pid}")

    while True:
        occupied = max(0, min(capacity, occupied + random.randint(-1,2)))
        available = capacity - occupied
        pct = int((occupied/capacity)*100)
        status = "PLEIN" if available==0 else ("PRESQUE PLEIN" if available<=2 else "DISPONIBLE")

        if available == 0:
            await BUS.send("controller","parking_full",inter)

        await broadcast({"type":"parking","id":pid,"intersection":inter,
                         "occupied":occupied,"capacity":capacity,
                         "available":available,"status":status})
        await ws_log(f"🅿️ {pid}: {occupied}/{capacity} ({status})", "park")
        await asyncio.sleep(5)

async def agent_weather():
    conditions = ["NORMAL","PLUIE","BROUILLARD","NEIGE","VERGLAS"]
    condition = "NORMAL"
    print("[SETUP] 🌦️ Météo")

    while True:
        if random.random() < 0.2:
            condition = random.choice(conditions)
            factor = WEATHER_FACTOR[condition]
            STATE.weather = condition
            await BUS.send("controller","weather_alert",condition)
            for i in ["A","B","C"]:
                await BUS.send(f"light_{i.lower()}","weather_adjust",condition)
            for vid in ["v1","v2","v3","v4","v5","amb1","pol1"]:
                await BUS.send(f"vehicle_{vid}","weather",
                               f"{condition}|{factor}")
            await ws_log(f"🌦️ Météo: {condition} (facteur {factor})", "weather")

        await broadcast({"type":"weather","condition":condition,
                         "speed_factor":WEATHER_FACTOR[condition]})
        await asyncio.sleep(8)

async def agent_monitor():
    cycle = 0
    print("[SETUP] 📊 Moniteur")

    while True:
        await BUS.receive("monitor", timeout=0.1)
        cycle += 1; STATE.cycle = cycle
        avg = round(sum(STATE.wait_times)/len(STATE.wait_times),1) if STATE.wait_times else 0
        await broadcast({"type":"monitor","cycle":cycle,
                         "total_waiting":STATE.total_waiting,
                         "avg_wait":avg,
                         "emergencies":STATE.emergencies,
                         "optimizations":STATE.optimizations,
                         "weather_alerts":STATE.weather_alerts})
        await asyncio.sleep(2)

# ── WebSocket Handler ─────────────────────────────────────────────────────────
async def ws_handler(websocket):
    clients.add(websocket)
    print(f"[WS] Client connecté ({len(clients)} total)")
    try:
        async for raw in websocket:
            try:
                data = json.loads(raw)
                if data.get("type") == "manual":
                    await handle_manual(data)
            except Exception:
                pass
    finally:
        clients.discard(websocket)
        print(f"[WS] Client déconnecté ({len(clients)} restants)")

async def handle_manual(data):
    cmd   = data.get("cmd", "")
    inter = data.get("intersection", "A")
    print(f"[MANUEL] cmd={cmd} inter={inter}")

    if cmd == "force_green":
        await BUS.send(f"light_{inter.lower()}", "force_green", f"MANUAL|{inter}|20")
        await ws_log(f"🟢 [MANUEL] Feu {inter} → VERT forcé", "light")

    elif cmd == "force_red":
        await BUS.send(f"light_{inter.lower()}", "force_red", f"MANUAL|{inter}")
        await ws_log(f"🔴 [MANUEL] Feu {inter} → ROUGE forcé", "light")

    elif cmd == "auto":
        await BUS.send(f"light_{inter.lower()}", "set_auto", inter)
        await ws_log(f"🔄 [MANUEL] Feu {inter} → Mode auto", "light")

    elif cmd == "emergency_amb":
        await BUS.send("controller", "emergency", f"amb1|{inter}|AMBULANCE")
        await BUS.send(f"light_{inter.lower()}", "force_green", f"EMERGENCY|{inter}|15")
        STATE.emergencies += 1
        await ws_log(f"🚑 [MANUEL] Ambulance → Intersection {inter}", "emerg")

    elif cmd == "emergency_pol":
        await BUS.send("controller", "emergency", f"pol1|{inter}|POLICE")
        await BUS.send(f"light_{inter.lower()}", "force_green", f"EMERGENCY|{inter}|15")
        STATE.emergencies += 1
        await ws_log(f"🚓 [MANUEL] Police → Intersection {inter}", "emerg")

    elif cmd == "set_weather":
        cond = data.get("condition", "NORMAL")
        STATE.weather = cond
        await BUS.send("controller", "weather_alert", cond)
        for i in ["A","B","C"]:
            await BUS.send(f"light_{i.lower()}", "weather_adjust", cond)
        for vid in ["v1","v2","v3","v4","v5"]:
            await BUS.send(f"vehicle_{vid}", "weather",
                           f"{cond}|{WEATHER_FACTOR.get(cond,1.0)}")
        STATE.weather_alerts += 1
        await ws_log(f"🌦️ [MANUEL] Météo → {cond}", "weather")

    elif cmd == "park_full_P1":
        await BUS.send("controller", "parking_full", "A")
        await ws_log("🅿️ [MANUEL] P1 → PLEIN", "park")

    elif cmd == "park_full_P2":
        await BUS.send("controller", "parking_full", "B")
        await ws_log("🅿️ [MANUEL] P2 → PLEIN", "park")

# ── HTTP Server (sert les fichiers web/) ─────────────────────────────────────
def start_http():
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    os.chdir(web_dir)
    server = HTTPServer(("localhost", 8080), SimpleHTTPRequestHandler)
    print("[HTTP] Serveur web sur http://localhost:8080")
    server.serve_forever()

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    print("\n" + "="*55)
    print("  SMA TRAFIC URBAIN — 15 AGENTS + INTERFACE WEB")
    print("="*55)

    if not HAS_WS:
        print("\n❌ websockets non installé. Lancement: pip install websockets")
        return

    # Lancer HTTP dans un thread
    http_thread = threading.Thread(target=start_http, daemon=True)
    http_thread.start()

    # Ouvrir le navigateur
    await asyncio.sleep(1)
    webbrowser.open("http://localhost:8080")

    # Lancer le serveur WebSocket + tous les agents
    async with websockets.serve(ws_handler, "localhost", 8765):
        print("[WS] Serveur WebSocket sur ws://localhost:8765")
        print(f"[✅] 15 agents démarrés\n")

        await asyncio.gather(
            *[agent_vehicle(f"v{i}") for i in range(1,6)],
            *[agent_traffic_light(i) for i in ["A","B","C"]],
            agent_controller(),
            agent_emergency("amb1","AMBULANCE"),
            agent_emergency("pol1","POLICE"),
            agent_parking("P1","A",20),
            agent_parking("P2","B",15),
            agent_weather(),
            agent_monitor(),
        )

if __name__ == "__main__":
    asyncio.run(main())
