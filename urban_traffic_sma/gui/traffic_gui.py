import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from datetime import datetime

class TrafficGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🚦 SMA - Optimisation Trafic Urbain")
        self.root.geometry("1200x750")
        self.root.configure(bg="#1a1a2e")
        self.data = {}
        self._build_ui()

    def _build_ui(self):
        # Titre
        title = tk.Label(self.root, text="🚦 Système Multi-Agents — Trafic Urbain",
                         font=("Arial", 16, "bold"), bg="#1a1a2e", fg="#e94560")
        title.pack(pady=8)

        main = tk.Frame(self.root, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Colonne gauche : feux + urgences + météo
        left = tk.Frame(main, bg="#1a1a2e")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Feux de signalisation
        self._section(left, "🚦 Feux de Signalisation")
        self.light_frames = {}
        for inter in ["A", "B", "C"]:
            f = tk.Frame(left, bg="#16213e", relief=tk.RIDGE, bd=2)
            f.pack(fill=tk.X, padx=5, pady=3)
            lbl = tk.Label(f, text=f"Intersection {inter}", font=("Arial", 10, "bold"),
                           bg="#16213e", fg="white")
            lbl.pack(side=tk.LEFT, padx=8)
            canvas = tk.Canvas(f, width=30, height=30, bg="#16213e", highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=5)
            circle = canvas.create_oval(5, 5, 25, 25, fill="red")
            info = tk.Label(f, text="RED | 0 véh | 10s", font=("Arial", 9),
                            bg="#16213e", fg="#aaaaaa")
            info.pack(side=tk.LEFT, padx=5)
            self.light_frames[inter] = {"canvas": canvas, "circle": circle, "info": info}

        # Urgences
        self._section(left, "🚨 Véhicules Prioritaires")
        self.emerg_labels = {}
        for eid in ["amb1", "pol1"]:
            f = tk.Frame(left, bg="#16213e", relief=tk.RIDGE, bd=2)
            f.pack(fill=tk.X, padx=5, pady=2)
            lbl = tk.Label(f, text=f"{'🚑 AMBULANCE' if 'amb' in eid else '🚓 POLICE'} {eid}",
                           font=("Arial", 9, "bold"), bg="#16213e", fg="#ff6b6b")
            lbl.pack(side=tk.LEFT, padx=8)
            info = tk.Label(f, text="En attente...", font=("Arial", 9),
                            bg="#16213e", fg="#aaaaaa")
            info.pack(side=tk.LEFT, padx=5)
            self.emerg_labels[eid] = info

        # Météo
        self._section(left, "🌦️ Conditions Météo")
        self.weather_label = tk.Label(left, text="NORMAL | Facteur: 1.0",
                                      font=("Arial", 11, "bold"), bg="#16213e",
                                      fg="#4ecdc4", relief=tk.RIDGE, bd=2)
        self.weather_label.pack(fill=tk.X, padx=5, pady=3)

        # Colonne centre : véhicules
        center = tk.Frame(main, bg="#1a1a2e")
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self._section(center, "🚗 Véhicules")
        self.vehicle_bars = {}
        for vid in ["v1", "v2", "v3", "v4", "v5"]:
            f = tk.Frame(center, bg="#16213e", relief=tk.RIDGE, bd=2)
            f.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(f, text=f"🚗 {vid}", font=("Arial", 9, "bold"),
                     bg="#16213e", fg="#ffd700", width=5).pack(side=tk.LEFT, padx=4)
            bar = ttk.Progressbar(f, length=120, maximum=150, mode="determinate")
            bar.pack(side=tk.LEFT, padx=4)
            info = tk.Label(f, text="Inter:A | 0m | 0s att",
                            font=("Arial", 8), bg="#16213e", fg="#aaaaaa")
            info.pack(side=tk.LEFT, padx=4)
            self.vehicle_bars[vid] = {"bar": bar, "info": info}

        # Parkings
        self._section(center, "🅿️ Parkings")
        self.parking_labels = {}
        for pid in ["P1", "P2"]:
            f = tk.Frame(center, bg="#16213e", relief=tk.RIDGE, bd=2)
            f.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(f, text=f"🅿️ {pid}", font=("Arial", 9, "bold"),
                     bg="#16213e", fg="#a8e6cf", width=5).pack(side=tk.LEFT, padx=4)
            bar = ttk.Progressbar(f, length=120, maximum=100, mode="determinate")
            bar.pack(side=tk.LEFT, padx=4)
            info = tk.Label(f, text="0/0 | DISPONIBLE",
                            font=("Arial", 8), bg="#16213e", fg="#aaaaaa")
            info.pack(side=tk.LEFT, padx=4)
            self.parking_labels[pid] = {"bar": bar, "info": info}

        # Colonne droite : stats + logs
        right = tk.Frame(main, bg="#1a1a2e")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._section(right, "📊 Statistiques Globales")
        self.stats_frame = tk.Frame(right, bg="#16213e", relief=tk.RIDGE, bd=2)
        self.stats_frame.pack(fill=tk.X, padx=5, pady=3)
        self.stat_labels = {}
        for key, label in [("total_waiting","En attente"),("avg_wait_time","Temps moy (s)"),
                            ("emergencies","Urgences"),("optimizations","Optimisations"),
                            ("weather_alerts","Alertes météo"),("cycle","Cycle")]:
            row = tk.Frame(self.stats_frame, bg="#16213e")
            row.pack(fill=tk.X, padx=5, pady=1)
            tk.Label(row, text=f"{label}:", font=("Arial", 9), bg="#16213e",
                     fg="#aaaaaa", width=16, anchor="w").pack(side=tk.LEFT)
            val = tk.Label(row, text="0", font=("Arial", 9, "bold"),
                           bg="#16213e", fg="#4ecdc4")
            val.pack(side=tk.LEFT)
            self.stat_labels[key] = val

        # Log console
        self._section(right, "📋 Journal des Interactions")
        self.log_box = scrolledtext.ScrolledText(right, height=18, width=42,
                                                  bg="#0f3460", fg="#e0e0e0",
                                                  font=("Courier", 8), state=tk.DISABLED)
        self.log_box.pack(padx=5, pady=3, fill=tk.BOTH, expand=True)

        # Bouton reset log
        tk.Button(right, text="🗑️ Effacer log", command=self._clear_log,
                  bg="#e94560", fg="white", font=("Arial", 8)).pack(pady=3)

    def _section(self, parent, title):
        tk.Label(parent, text=title, font=("Arial", 10, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(anchor="w", padx=5, pady=(8,2))

    def _clear_log(self):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete(1.0, tk.END)
        self.log_box.config(state=tk.DISABLED)

    def log(self, message):
        def _do():
            self.log_box.config(state=tk.NORMAL)
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_box.insert(tk.END, f"[{ts}] {message}\n")
            self.log_box.see(tk.END)
            self.log_box.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def update(self, agent_type, agent_id, data):
        def _do():
            if agent_type == "light":
                f = self.light_frames.get(agent_id)
                if f:
                    color = "green" if data["status"] == "GREEN" else ("orange" if data.get("force_green") else "red")
                    f["canvas"].itemconfig(f["circle"], fill=color)
                    f["info"].config(text=f"{data['status']} | {data['vehicles_waiting']} véh | {data['green_duration']}s")
                self.log(f"🚦 Feu {agent_id}: {data['status']} | {data['vehicles_waiting']} véh")

            elif agent_type == "vehicle":
                v = self.vehicle_bars.get(agent_id)
                if v:
                    v["bar"]["value"] = max(0, 150 - data["position"])
                    status = "🔴" if data["waiting"] else "🟢"
                    v["info"].config(text=f"Inter:{data['intersection']} | {data['position']}m | {status}{data['wait_time']}s")
                self.log(f"🚗 {agent_id}: pos={data['position']}m att={data['wait_time']}s")

            elif agent_type == "emergency":
                lbl = self.emerg_labels.get(agent_id)
                if lbl:
                    icon = "🚨 ACTIF" if data["active"] else "💤 INACTIF"
                    lbl.config(text=f"{icon} | Inter:{data['intersection']} | {data['position']}m",
                               fg="#ff6b6b" if data["active"] else "#aaaaaa")
                if data["active"]:
                    self.log(f"🚨 {data['type']} {agent_id}: URGENCE Inter {data['intersection']}")

            elif agent_type == "parking":
                p = self.parking_labels.get(agent_id)
                if p:
                    pct = int((data["occupied"] / data["capacity"]) * 100) if data["capacity"] else 0
                    p["bar"]["value"] = pct
                    color = "#ff6b6b" if data["status"] == "PLEIN" else ("#ffd700" if "PRESQUE" in data["status"] else "#a8e6cf")
                    p["info"].config(text=f"{data['occupied']}/{data['capacity']} | {data['status']}", fg=color)
                self.log(f"🅿️ {agent_id}: {data['occupied']}/{data['capacity']} ({data['status']})")

            elif agent_type == "weather":
                cond = data["condition"]
                colors = {"NORMAL":"#4ecdc4","PLUIE":"#74b9ff","BROUILLARD":"#b2bec3",
                          "NEIGE":"#dfe6e9","VERGLAS":"#fd79a8"}
                self.weather_label.config(
                    text=f"{cond} | Facteur vitesse: {data['speed_factor']}",
                    fg=colors.get(cond, "#4ecdc4"))
                self.log(f"🌦️ Météo: {cond} (facteur {data['speed_factor']})")

            elif agent_type == "monitor":
                for key, val in data.items():
                    if key in self.stat_labels:
                        self.stat_labels[key].config(text=str(val))

            elif agent_type == "controller":
                if "optimizations" in data:
                    self.stat_labels["optimizations"].config(text=str(data["optimizations"]))
                self.log(f"🧠 Contrôleur: {data.get('total_waiting',0)} en attente | {data.get('optimizations',0)} optim.")

        self.root.after(0, _do)

    def run(self):
        self.root.mainloop()
