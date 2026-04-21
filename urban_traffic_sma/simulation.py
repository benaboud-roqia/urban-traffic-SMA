"""
SMA Trafic Urbain - Version Simulation (sans serveur XMPP)
===========================================================
Simule 15 agents avec messagerie interne (queue asyncio)
et interface Tkinter complète.
"""

import asyncio
import threading
import random
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from collections import defaultdict

# ── Bus de messages interne (remplace XMPP) ─────────────────────────────────
class MessageBus:
    def __init__(self):
        self._queues = defaultdict(asyncio.Queue)

    def get_queue(self, agent_id):
        return self._queues[agent_id]

    async def send(self, to, msg_type, body, sender="?"):
        await self._queues[to].put({"type": msg_type, "body": body, "from": sender})

    async def receive(self, agent_id, timeout=1.0):
        try:
            return await asyncio.wait_for(self._queues[agent_id].get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

BUS = MessageBus()

# ── Interface Graphique ──────────────────────────────────────────────────────
class TrafficGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🚦 SMA — Optimisation Trafic Urbain (15 Agents)")
        self.root.geometry("1250x780")
        self.root.configure(bg="#1a1a2e")
        self._build_ui()

    def _build_ui(self):
        tk.Label(self.root, text="🚦 Système Multi-Agents — Optimisation du Trafic Urbain",
                 font=("Arial", 15, "bold"), bg="#1a1a2e", fg="#e94560").pack(pady=6)

        main = tk.Frame(self.root, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # ── Colonne gauche ──
        left = tk.Frame(main, bg="#1a1a2e")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._sec(left, "🚦 Feux de Signalisation")
        self.light_widgets = {}
        for inter in ["A", "B", "C"]:
            f = tk.Frame(left, bg="#16213e", relief=tk.RIDGE, bd=2)
            f.pack(fill=tk.X, padx=4, pady=2)
            tk.Label(f, text=f"Intersection {inter}", font=("Arial", 10, "bold"),
                     bg="#16213e", fg="white", width=14).pack(side=tk.LEFT, padx=6)
            cv = tk.Canvas(f, width=32, height=32, bg="#16213e", highlightthickness=0)
            cv.pack(side=tk.LEFT, padx=4)
            circ = cv.create_oval(4, 4, 28, 28, fill="red")
            info = tk.Label(f, text="RED | 0 véh | 10s", font=("Arial", 9),
                            bg="#16213e", fg="#aaa")
            info.pack(side=tk.LEFT, padx=4)
            self.light_widgets[inter] = {"cv": cv, "circ": circ, "info": info}

        self._sec(left, "🚨 Véhicules Prioritaires")
        self.emerg_widgets = {}
        for eid, label in [("amb1","🚑 AMBULANCE"), ("pol1","🚓 POLICE")]:
            f = tk.Frame(left, bg="#16213e", relief=tk.RIDGE, bd=2)
            f.pack(fill=tk.X, padx=4, pady=2)
            tk.Label(f, text=label, font=("Arial", 9, "bold"),
                     bg="#16213e", fg="#ff6b6b", width=14).pack(side=tk.LEFT, padx=6)
            info = tk.Label(f, text="💤 INACTIF", font=("Arial", 9),
                            bg="#16213e", fg="#aaa")
            info.pack(side=tk.LEFT, padx=4)
            self.emerg_widgets[eid] = info

        self._sec(left, "🌦️ Météo")
        self.weather_lbl = tk.Label(left, text="NORMAL | Facteur: 1.0",
                                    font=("Arial", 11, "bold"), bg="#16213e",
                                    fg="#4ecdc4", relief=tk.RIDGE, bd=2)
        self.weather_lbl.pack(fill=tk.X, padx=4, pady=3)

        self._sec(left, "🧠 Contrôleur Central")
        self.ctrl_lbl = tk.Label(left, text="En attente...",
                                 font=("Arial", 9), bg="#16213e",
                                 fg="#ffd700", relief=tk.RIDGE, bd=2)
        self.ctrl_lbl.pack(fill=tk.X, padx=4, pady=3)

        # ── Colonne centre ──
        center = tk.Frame(main, bg="#1a1a2e")
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)

        self._sec(center, "🚗 Véhicules (5)")
        self.veh_widgets = {}
        for vid in ["v1","v2","v3","v4","v5"]:
            f = tk.Frame(center, bg="#16213e", relief=tk.RIDGE, bd=2)
            f.pack(fill=tk.X, padx=4, pady=2)
            tk.Label(f, text=f"🚗 {vid}", font=("Arial", 9, "bold"),
                     bg="#16213e", fg="#ffd700", width=5).pack(side=tk.LEFT, padx=4)
            bar = ttk.Progressbar(f, length=130, maximum=150, mode="determinate")
            bar.pack(side=tk.LEFT, padx=4)
            info = tk.Label(f, text="A | 0m | 🟢 0s",
                            font=("Arial", 8), bg="#16213e", fg="#aaa")
            info.pack(side=tk.LEFT, padx=4)
            self.veh_widgets[vid] = {"bar": bar, "info": info}

        self._sec(center, "🅿️ Parkings (2)")
        self.park_widgets = {}
        for pid, cap in [("P1",20),("P2",15)]:
            f = tk.Frame(center, bg="#16213e", relief=tk.RIDGE, bd=2)
            f.pack(fill=tk.X, padx=4, pady=2)
            tk.Label(f, text=f"🅿️ {pid}", font=("Arial", 9, "bold"),
                     bg="#16213e", fg="#a8e6cf", width=5).pack(side=tk.LEFT, padx=4)
            bar = ttk.Progressbar(f, length=130, maximum=cap, mode="determinate")
            bar.pack(side=tk.LEFT, padx=4)
            info = tk.Label(f, text=f"0/{cap} | DISPONIBLE",
                            font=("Arial", 8), bg="#16213e", fg="#aaa")
            info.pack(side=tk.LEFT, padx=4)
            self.park_widgets[pid] = {"bar": bar, "info": info, "cap": cap}

        self._sec(center, "📊 Statistiques")
        self.stat_frame = tk.Frame(center, bg="#16213e", relief=tk.RIDGE, bd=2)
        self.stat_frame.pack(fill=tk.X, padx=4, pady=3)
        self.stat_lbls = {}
        for key, label in [("cycle","Cycle"),("total_waiting","En attente"),
                            ("avg_wait","Temps moy (s)"),("emergencies","Urgences"),
                            ("optimizations","Optimisations"),("weather_alerts","Alertes météo")]:
            row = tk.Frame(self.stat_frame, bg="#16213e")
            row.pack(fill=tk.X, padx=6, pady=1)
            tk.Label(row, text=f"{label}:", font=("Arial", 9), bg="#16213e",
                     fg="#aaa", width=16, anchor="w").pack(side=tk.LEFT)
            v = tk.Label(row, text="0", font=("Arial", 9, "bold"),
                         bg="#16213e", fg="#4ecdc4")
            v.pack(side=tk.LEFT)
            self.stat_lbls[key] = v

        # ── Colonne droite : log ──
        right = tk.Frame(main, bg="#1a1a2e")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._sec(right, "📋 Journal des Interactions")
        self.log_box = scrolledtext.ScrolledText(
            right, height=35, width=44, bg="#0f3460", fg="#e0e0e0",
            font=("Courier", 8), state=tk.DISABLED)
        self.log_box.pack(padx=4, pady=3, fill=tk.BOTH, expand=True)
        tk.Button(right, text="🗑️ Effacer", command=self._clear_log,
                  bg="#e94560", fg="white", font=("Arial", 8)).pack(pady=3)

    def _sec(self, parent, title):
        tk.Label(parent, text=title, font=("Arial", 10, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(anchor="w", padx=4, pady=(7,1))

    def _clear_log(self):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete(1.0, tk.END)
        self.log_box.config(state=tk.DISABLED)

    def log(self, msg):
        def _do():
            self.log_box.config(state=tk.NORMAL)
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_box.insert(tk.END, f"[{ts}] {msg}\n")
            self.log_box.see(tk.END)
            self.log_box.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def update_light(self, inter, status, nb, dur, force=False):
        def _do():
            w = self.light_widgets[inter]
            color = "orange" if force else ("green" if status == "GREEN" else "red")
            w["cv"].itemconfig(w["circ"], fill=color)
            tag = "🚨" if force else ""
            w["info"].config(text=f"{tag}{status} | {nb} véh | {dur}s")
        self.root.after(0, _do)

    def update_vehicle(self, vid, inter, pos, waiting, wait_time):
        def _do():
            w = self.veh_widgets[vid]
            w["bar"]["value"] = max(0, 150 - pos)
            icon = "🔴" if waiting else "🟢"
            w["info"].config(text=f"{inter} | {pos}m | {icon}{wait_time}s")
        self.root.after(0, _do)

    def update_emergency(self, eid, active, inter, pos, vtype):
        def _do():
            w = self.emerg_widgets[eid]
            if active:
                w.config(text=f"🚨 ACTIF | {inter} | {pos}m", fg="#ff6b6b")
            else:
                w.config(text="💤 INACTIF", fg="#aaa")
        self.root.after(0, _do)

    def update_parking(self, pid, occupied, cap, status):
        def _do():
            w = self.park_widgets[pid]
            w["bar"]["value"] = occupied
            colors = {"PLEIN":"#ff6b6b","PRESQUE PLEIN":"#ffd700","DISPONIBLE":"#a8e6cf"}
            w["info"].config(text=f"{occupied}/{cap} | {status}",
                             fg=colors.get(status, "#aaa"))
        self.root.after(0, _do)

    def update_weather(self, condition, factor):
        def _do():
            colors = {"NORMAL":"#4ecdc4","PLUIE":"#74b9ff","BROUILLARD":"#b2bec3",
                      "NEIGE":"#dfe6e9","VERGLAS":"#fd79a8"}
            self.weather_lbl.config(
                text=f"{condition} | Facteur vitesse: {factor}",
                fg=colors.get(condition, "#4ecdc4"))
        self.root.after(0, _do)

    def update_stats(self, stats):
        def _do():
            for k, v in stats.items():
                if k in self.stat_lbls:
                    self.stat_lbls[k].config(text=str(v))
        self.root.after(0, _do)

    def update_controller(self, total_waiting, optimizations):
        def _do():
            self.ctrl_lbl.config(
                text=f"En attente: {total_waiting} | Optimisations: {optimizations}")
        self.root.after(0, _do)

    def run(self):
        self.root.mainloop()

# ── Agents ───────────────────────────────────────────────────────────────────

WEATHER_FACTOR = {"NORMAL":1.0,"PLUIE":0.7,"BROUILLARD":0.5,"NEIGE":0.4,"VERGLAS":0.3}
WEATHER_EXTRA  = {"NORMAL":0,"PLUIE":3,"BROUILLARD":5,"NEIGE":7,"VERGLAS":8}

class SharedState:
    """État partagé entre agents (remplace les messages pour l'état global)"""
    def __init__(self):
        self.lights = {"A":{"status":"RED","green_dur":10,"nb":0,"force":False,"force_t":0},
                       "B":{"status":"RED","green_dur":10,"nb":0,"force":False,"force_t":0},
                       "C":{"status":"RED","green_dur":10,"nb":0,"force":False,"force_t":0}}
        self.weather = "NORMAL"
        self.total_waiting = 0
        self.optimizations = 0
        self.emergencies = 0
        self.weather_alerts = 0
        self.cycle = 0
        self.wait_times = []

STATE = SharedState()

async def agent_vehicle(vid, gui):
    """Agent Véhicule"""
    inter = random.choice(["A","B","C"])
    pos = random.randint(50, 150)
    speed = random.randint(20, 60)
    waiting = False
    wait_time = 0
    weather_factor = 1.0

    print(f"[SETUP] 🚗 Véhicule {vid} → Intersection {inter}")

    while True:
        # Recevoir messages
        msg = await BUS.receive(f"vehicle_{vid}", timeout=0.1)
        if msg:
            if msg["type"] == "light_status":
                parts = msg["body"].split("|")
                waiting = (parts[0] == "RED")
                if parts[0] == "GREEN":
                    wait_time = 0
            elif msg["type"] == "weather":
                parts = msg["body"].split("|")
                weather_factor = float(parts[1])
                speed = max(10, int(speed * weather_factor))
            elif msg["type"] == "redirect":
                old = inter
                inter = random.choice([x for x in ["A","B","C"] if x != inter])
                gui.log(f"🔀 Véhicule {vid}: redirigé {old}→{inter}")

        # Déplacer
        if not waiting:
            move = int(random.randint(5, 15) * weather_factor)
            pos = max(0, pos - move)
        else:
            wait_time += 1

        # Notifier le feu
        await BUS.send(f"light_{inter.lower()}", "position",
                       f"{vid}|{pos}|{speed}|{inter}", sender=f"vehicle_{vid}")

        # Envoyer stats au moniteur
        await BUS.send("monitor", "stats_vehicle", f"{vid}|{wait_time}", sender=f"vehicle_{vid}")

        # Mise à jour GUI
        gui.update_vehicle(vid, inter, pos, waiting, wait_time)
        STATE.wait_times.append(wait_time)
        if len(STATE.wait_times) > 100:
            STATE.wait_times.pop(0)

        print(f"[🚗 {vid}] Inter:{inter} Pos:{pos}m Att:{'OUI' if waiting else 'NON'}({wait_time}s)")

        # Réinitialiser si arrivé
        if pos <= 0:
            pos = random.randint(80, 150)
            inter = random.choice(["A","B","C"])
            wait_time = 0

        await asyncio.sleep(2)

async def agent_traffic_light(inter, gui):
    """Agent Feu de Signalisation"""
    timer = 0
    status = "RED"
    green_dur = 10
    red_dur = 10
    force_green = False
    force_timer = 0
    weather_extra = 0
    vehicles_near = {}

    print(f"[SETUP] 🚦 Feu {inter} démarré")

    while True:
        # Recevoir messages
        msg = await BUS.receive(f"light_{inter.lower()}", timeout=0.1)
        if msg:
            if msg["type"] == "position":
                parts = msg["body"].split("|")
                vid, pos, speed, v_inter = parts[0], int(parts[1]), int(parts[2]), parts[3]
                if v_inter == inter:
                    if pos < 30:
                        vehicles_near[vid] = pos
                    else:
                        vehicles_near.pop(vid, None)
                # Notifier le véhicule du statut
                await BUS.send(f"vehicle_{vid}", "light_status",
                               f"{status}|{green_dur}", sender=f"light_{inter.lower()}")

            elif msg["type"] == "force_green":
                parts = msg["body"].split("|")
                dur = int(parts[2]) if len(parts) > 2 else 15
                force_green = True
                force_timer = dur
                status = "GREEN"
                print(f"[🚦 FEU {inter}] 🚨 VERT FORCÉ pour {dur}s")

            elif msg["type"] in ("weather_adjust", "weather_alert"):
                cond = msg["body"].split("|")[0]
                weather_extra = WEATHER_EXTRA.get(cond, 0)

            elif msg["type"] == "optimize":
                parts = msg["body"].split("|")
                if parts[0] == "EXTEND_GREEN":
                    green_dur = min(25, green_dur + int(parts[2]))

        timer += 2
        nb = len(vehicles_near)

        if force_green:
            status = "GREEN"
            force_timer -= 2
            if force_timer <= 0:
                force_green = False
        else:
            green_dur = min(25, 8 + nb * 2 + weather_extra)
            cycle = green_dur + red_dur
            phase = timer % cycle
            new_status = "GREEN" if phase < green_dur else "RED"
            if new_status != status:
                status = new_status
                print(f"[🚦 FEU {inter}] → {status} | {nb} véh | {green_dur}s")

        # Rapport au contrôleur
        await BUS.send("controller", "light_report",
                       f"{inter}|{status}|{nb}|{green_dur}", sender=f"light_{inter.lower()}")

        # Mise à jour état partagé
        STATE.lights[inter] = {"status": status, "green_dur": green_dur,
                               "nb": nb, "force": force_green, "force_t": force_timer}

        gui.update_light(inter, status, nb, green_dur, force_green)
        await asyncio.sleep(2)

async def agent_controller(gui):
    """Agent Contrôleur Central"""
    print("[SETUP] 🧠 Contrôleur central démarré")

    while True:
        msg = await BUS.receive("controller", timeout=0.5)
        if msg:
            if msg["type"] == "light_report":
                pass  # déjà dans STATE.lights

            elif msg["type"] == "emergency":
                parts = msg["body"].split("|")
                inter = parts[1]
                await BUS.send(f"light_{inter.lower()}", "force_green",
                               f"EMERGENCY|{inter}|15", sender="controller")
                STATE.emergencies += 1
                STATE.optimizations += 1
                gui.log(f"🧠 Contrôleur: 🚨 URGENCE {inter} → VERT forcé")

            elif msg["type"] == "weather_alert":
                cond = msg["body"]
                for inter in ["A","B","C"]:
                    await BUS.send(f"light_{inter.lower()}", "weather_adjust",
                                   cond, sender="controller")
                STATE.weather_alerts += 1
                gui.log(f"🧠 Contrôleur: 🌦️ Météo '{cond}' → feux ajustés")

            elif msg["type"] == "parking_full":
                inter = msg["body"]
                for vid in ["v1","v2","v3","v4","v5"]:
                    await BUS.send(f"vehicle_{vid}", "redirect",
                                   f"PARKING_FULL|{inter}", sender="controller")
                gui.log(f"🧠 Contrôleur: 🅿️ Parking {inter} plein → redirection")

        # Optimisation proactive
        busiest = max(STATE.lights, key=lambda k: STATE.lights[k]["nb"])
        d = STATE.lights[busiest]
        if d["nb"] > 3 and d["status"] == "RED":
            await BUS.send(f"light_{busiest.lower()}", "optimize",
                           f"EXTEND_GREEN|{busiest}|5", sender="controller")
            STATE.optimizations += 1
            gui.log(f"🧠 Contrôleur: ⚡ Extension verte {busiest} ({d['nb']} véh)")

        total = sum(d["nb"] for d in STATE.lights.values())
        STATE.total_waiting = total
        gui.update_controller(total, STATE.optimizations)
        await asyncio.sleep(4)

async def agent_emergency(eid, vtype, gui):
    """Agent Véhicule Prioritaire"""
    pos = random.randint(80, 200)
    active = False
    inter = random.choice(["A","B","C"])

    print(f"[SETUP] 🚨 {vtype} {eid} démarré")

    while True:
        if not active and random.random() < 0.15:
            active = True
            pos = random.randint(60, 150)
            inter = random.choice(["A","B","C"])
            print(f"[🚨 {vtype} {eid}] URGENCE → Intersection {inter}")
            gui.log(f"🚨 {vtype} {eid}: URGENCE déclenchée → {inter}")

        if active:
            pos = max(0, pos - 20)
            await BUS.send("controller", "emergency",
                           f"{eid}|{inter}|{vtype}", sender=eid)
            await BUS.send(f"light_{inter.lower()}", "force_green",
                           f"EMERGENCY|{inter}|15", sender=eid)
            print(f"[🚨 {vtype} {eid}] Pos:{pos}m → Feu {inter} VERT forcé")
            if pos <= 0:
                active = False
                gui.log(f"🚨 {vtype} {eid}: Mission terminée")

        gui.update_emergency(eid, active, inter, pos, vtype)
        await asyncio.sleep(3)

async def agent_parking(pid, inter, capacity, gui):
    """Agent Parking"""
    occupied = random.randint(0, capacity - 2)
    print(f"[SETUP] 🅿️ Parking {pid} démarré (cap:{capacity})")

    while True:
        delta = random.randint(-1, 2)
        occupied = max(0, min(capacity, occupied + delta))
        available = capacity - occupied
        pct = int((occupied / capacity) * 100)

        if available == 0:
            status = "PLEIN"
            await BUS.send("controller", "parking_full", inter, sender=f"parking_{pid.lower()}")
        elif available <= 2:
            status = "PRESQUE PLEIN"
        else:
            status = "DISPONIBLE"

        print(f"[🅿️ {pid}] {occupied}/{capacity} ({pct}%) {status}")
        gui.update_parking(pid, occupied, capacity, status)
        await asyncio.sleep(5)

async def agent_weather(gui):
    """Agent Météo"""
    conditions = ["NORMAL","PLUIE","BROUILLARD","NEIGE","VERGLAS"]
    condition = "NORMAL"
    print("[SETUP] 🌦️ Agent Météo démarré")

    while True:
        if random.random() < 0.2:
            condition = random.choice(conditions)
            factor = WEATHER_FACTOR[condition]
            STATE.weather = condition
            print(f"[🌦️ MÉTÉO] → {condition} (facteur {factor})")
            gui.log(f"🌦️ Météo: {condition} (facteur {factor})")

            # Notifier tous
            await BUS.send("controller", "weather_alert", condition, sender="weather")
            for inter in ["A","B","C"]:
                await BUS.send(f"light_{inter.lower()}", "weather_adjust",
                               condition, sender="weather")
            for vid in ["v1","v2","v3","v4","v5","amb1","pol1"]:
                await BUS.send(f"vehicle_{vid}", "weather",
                               f"{condition}|{WEATHER_FACTOR[condition]}", sender="weather")

        gui.update_weather(condition, WEATHER_FACTOR[condition])
        await asyncio.sleep(8)

async def agent_monitor(gui):
    """Agent Moniteur Statistiques"""
    print("[SETUP] 📊 Agent Moniteur démarré")
    cycle = 0

    while True:
        msg = await BUS.receive("monitor", timeout=0.1)
        # (les stats sont dans STATE)

        cycle += 1
        avg = round(sum(STATE.wait_times) / len(STATE.wait_times), 1) if STATE.wait_times else 0

        stats = {
            "cycle": cycle,
            "total_waiting": STATE.total_waiting,
            "avg_wait": avg,
            "emergencies": STATE.emergencies,
            "optimizations": STATE.optimizations,
            "weather_alerts": STATE.weather_alerts,
        }
        gui.update_stats(stats)

        if cycle % 5 == 0:
            print(f"[📊 MONITEUR] Cycle#{cycle} | Attente moy:{avg}s | "
                  f"Urgences:{STATE.emergencies} | Optim:{STATE.optimizations}")

        await asyncio.sleep(2)

# ── Lancement ────────────────────────────────────────────────────────────────

async def run_all(gui):
    print("\n" + "="*55)
    print("  DÉMARRAGE — 15 AGENTS SMA TRAFIC URBAIN")
    print("="*55 + "\n")

    tasks = [
        # 5 véhicules
        *[agent_vehicle(f"v{i}", gui) for i in range(1, 6)],
        # 3 feux
        *[agent_traffic_light(inter, gui) for inter in ["A","B","C"]],
        # 1 contrôleur
        agent_controller(gui),
        # 2 urgences
        agent_emergency("amb1", "AMBULANCE", gui),
        agent_emergency("pol1", "POLICE", gui),
        # 2 parkings
        agent_parking("P1", "A", 20, gui),
        agent_parking("P2", "B", 15, gui),
        # 1 météo
        agent_weather(gui),
        # 1 moniteur
        agent_monitor(gui),
    ]

    print(f"✅ {len(tasks)} agents lancés\n")
    gui.log(f"✅ {len(tasks)} agents démarrés — Simulation en cours...")
    await asyncio.gather(*tasks)

def start_simulation(gui):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_all(gui))

if __name__ == "__main__":
    gui = TrafficGUI()
    t = threading.Thread(target=start_simulation, args=(gui,), daemon=True)
    t.start()
    gui.run()
