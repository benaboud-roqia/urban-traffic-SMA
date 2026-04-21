from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message

class ControllerAgent(Agent):
    def __init__(self, jid, password, gui_callback=None):
        super().__init__(jid, password)
        self.lights_status = {}      # intersection -> {status, nb_waiting, green_duration}
        self.total_waiting = 0
        self.optimizations = 0
        self.gui_callback = gui_callback

    class ReceiveReportsBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=2)
            if not msg:
                return
            t = msg.get_metadata("type")

            if t == "light_report":
                parts = msg.body.split("|")
                inter, status, nb, dur = parts[0], parts[1], int(parts[2]), int(parts[3])
                self.agent.lights_status[inter] = {
                    "status": status, "nb_waiting": nb, "green_duration": dur
                }

            elif t == "emergency":
                # Véhicule prioritaire : forcer le vert sur l'intersection
                parts = msg.body.split("|")
                inter = parts[1]
                light_jid = f"light_{inter.lower()}@localhost"
                cmd = Message(to=light_jid)
                cmd.set_metadata("performative", "request")
                cmd.set_metadata("type", "force_green")
                cmd.body = f"EMERGENCY|{inter}|15"
                await self.send(cmd)
                self.agent.optimizations += 1
                print(f"[CONTRÔLEUR] 🚨 URGENCE sur {inter} → Feu forcé au VERT")

            elif t == "weather_alert":
                # Adapter les durées selon météo
                condition = msg.body
                for inter in ["A", "B", "C"]:
                    light_jid = f"light_{inter.lower()}@localhost"
                    cmd = Message(to=light_jid)
                    cmd.set_metadata("performative", "request")
                    cmd.set_metadata("type", "weather_adjust")
                    cmd.body = condition
                    await self.send(cmd)
                print(f"[CONTRÔLEUR] 🌦️ Alerte météo '{condition}' → Feux ajustés")

            elif t == "parking_full":
                inter = msg.body
                print(f"[CONTRÔLEUR] 🅿️ Parking {inter} PLEIN → Redirection activée")
                # Notifier les véhicules de l'intersection
                for vid in ["v1","v2","v3","v4","v5"]:
                    v_msg = Message(to=f"vehicle_{vid}@localhost")
                    v_msg.set_metadata("performative", "inform")
                    v_msg.set_metadata("type", "redirect")
                    v_msg.body = f"PARKING_FULL|{inter}"
                    await self.send(v_msg)

    class OptimizeBehaviour(PeriodicBehaviour):
        async def run(self):
            agent = self.agent
            total = sum(d["nb_waiting"] for d in agent.lights_status.values())
            agent.total_waiting = total

            # Trouver l'intersection la plus chargée
            if agent.lights_status:
                busiest = max(agent.lights_status, key=lambda k: agent.lights_status[k]["nb_waiting"])
                data = agent.lights_status[busiest]
                if data["nb_waiting"] > 3 and data["status"] == "RED":
                    light_jid = f"light_{busiest.lower()}@localhost"
                    msg = Message(to=light_jid)
                    msg.set_metadata("performative", "request")
                    msg.set_metadata("type", "optimize")
                    msg.body = f"EXTEND_GREEN|{busiest}|5"
                    await self.send(msg)
                    agent.optimizations += 1
                    print(f"[CONTRÔLEUR] ⚡ Optimisation → Extension verte sur {busiest} ({data['nb_waiting']} véhicules)")

            print(f"[CONTRÔLEUR] 📊 Total en attente: {total} | Optimisations: {agent.optimizations}")
            if agent.gui_callback:
                agent.gui_callback("controller", "central", {
                    "total_waiting": total,
                    "optimizations": agent.optimizations,
                    "lights": agent.lights_status
                })

    async def setup(self):
        print("[SETUP] Contrôleur central démarré")
        self.add_behaviour(self.ReceiveReportsBehaviour())
        self.add_behaviour(self.OptimizeBehaviour(period=4))
