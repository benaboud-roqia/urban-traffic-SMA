from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour
from spade.message import Message

WEATHER_EXTRA = {"NORMAL": 0, "PLUIE": 3, "BROUILLARD": 5, "NEIGE": 7, "VERGLAS": 8}

class TrafficLightAgent(Agent):
    def __init__(self, jid, password, intersection, controller_jid, gui_callback=None):
        super().__init__(jid, password)
        self.intersection = intersection
        self.controller_jid = controller_jid
        self.status = "RED"
        self.green_duration = 10
        self.red_duration = 10
        self.timer = 0
        self.force_green = False
        self.force_timer = 0
        self.weather_extra = 0
        self.vehicles_waiting = {}
        self.gui_callback = gui_callback

    class ManageLightBehaviour(PeriodicBehaviour):
        async def run(self):
            agent = self.agent
            agent.timer += 2

            # Urgence : forcer le vert
            if agent.force_green:
                agent.status = "GREEN"
                agent.force_timer -= 2
                if agent.force_timer <= 0:
                    agent.force_green = False
                print(f"[🚦 FEU {agent.intersection}] 🚨 VERT FORCÉ (urgence) | reste {agent.force_timer}s")
            else:
                nb = len(agent.vehicles_waiting)
                agent.green_duration = min(25, 8 + nb * 2 + agent.weather_extra)
                cycle = agent.green_duration + agent.red_duration
                phase = agent.timer % cycle
                new_status = "GREEN" if phase < agent.green_duration else "RED"
                if new_status != agent.status:
                    agent.status = new_status
                    print(f"[🚦 FEU {agent.intersection}] → {agent.status} | "
                          f"Véhicules: {nb} | Durée verte: {agent.green_duration}s")

            # Notifier véhicules
            for vid in list(agent.vehicles_waiting.keys()):
                msg = Message(to=f"vehicle_{vid}@localhost")
                msg.set_metadata("performative", "inform")
                msg.set_metadata("type", "light_status")
                msg.body = f"{agent.status}|{agent.green_duration}"
                await self.send(msg)

            # Rapport contrôleur
            nb = len(agent.vehicles_waiting)
            ctrl = Message(to=agent.controller_jid)
            ctrl.set_metadata("performative", "inform")
            ctrl.set_metadata("type", "light_report")
            ctrl.body = f"{agent.intersection}|{agent.status}|{nb}|{agent.green_duration}"
            await self.send(ctrl)

            if agent.gui_callback:
                agent.gui_callback("light", agent.intersection, {
                    "status": agent.status,
                    "green_duration": agent.green_duration,
                    "vehicles_waiting": nb,
                    "timer": agent.timer,
                    "force_green": agent.force_green
                })

    class ReceiveCommandsBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=2)
            if not msg:
                return
            t = msg.get_metadata("type")

            if t == "position":
                parts = msg.body.split("|")
                vid, pos, speed, inter = parts[0], int(parts[1]), int(parts[2]), parts[3]
                if inter == self.agent.intersection:
                    if pos < 30:
                        self.agent.vehicles_waiting[vid] = pos
                    else:
                        self.agent.vehicles_waiting.pop(vid, None)

            elif t == "force_green":
                parts = msg.body.split("|")
                duration = int(parts[2]) if len(parts) > 2 else 15
                self.agent.force_green = True
                self.agent.force_timer = duration
                self.agent.status = "GREEN"
                print(f"[🚦 FEU {self.agent.intersection}] 🚨 VERT FORCÉ reçu pour {duration}s")

            elif t in ("weather_adjust", "weather_alert"):
                condition = msg.body.split("|")[0]
                self.agent.weather_extra = WEATHER_EXTRA.get(condition, 0)
                print(f"[🚦 FEU {self.agent.intersection}] 🌦️ Météo '{condition}' → +{self.agent.weather_extra}s")

            elif t == "optimize":
                parts = msg.body.split("|")
                if parts[0] == "EXTEND_GREEN":
                    self.agent.green_duration = min(25, self.agent.green_duration + int(parts[2]))
                    print(f"[🚦 FEU {self.agent.intersection}] ⚡ Durée verte étendue → {self.agent.green_duration}s")

    async def setup(self):
        print(f"[SETUP] Feu {self.intersection} démarré")
        self.add_behaviour(self.ManageLightBehaviour(period=2))
        self.add_behaviour(self.ReceiveCommandsBehaviour())
