from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour
from spade.message import Message

class MonitorAgent(Agent):
    """Agent moniteur : collecte et affiche les statistiques globales"""
    def __init__(self, jid, password, gui_callback=None):
        super().__init__(jid, password)
        self.stats = {
            "total_vehicles": 0,
            "total_waiting": 0,
            "avg_wait_time": 0.0,
            "emergencies": 0,
            "optimizations": 0,
            "weather_alerts": 0,
            "cycle": 0
        }
        self.wait_times = []
        self.gui_callback = gui_callback

    class CollectStatsBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=2)
            if not msg:
                return
            t = msg.get_metadata("type")

            if t == "stats_vehicle":
                parts = msg.body.split("|")
                wait = int(parts[1])
                self.agent.wait_times.append(wait)
                if len(self.agent.wait_times) > 50:
                    self.agent.wait_times.pop(0)

            elif t == "stats_emergency":
                self.agent.stats["emergencies"] += 1

            elif t == "stats_optimization":
                self.agent.stats["optimizations"] += 1

            elif t == "stats_weather":
                self.agent.stats["weather_alerts"] += 1

    class ReportBehaviour(PeriodicBehaviour):
        async def run(self):
            agent = self.agent
            agent.stats["cycle"] += 1
            if agent.wait_times:
                agent.stats["avg_wait_time"] = round(sum(agent.wait_times) / len(agent.wait_times), 2)

            print("=" * 55)
            print(f"[📊 MONITEUR] Cycle #{agent.stats['cycle']}")
            print(f"  Temps d'attente moyen : {agent.stats['avg_wait_time']}s")
            print(f"  Urgences traitées     : {agent.stats['emergencies']}")
            print(f"  Optimisations         : {agent.stats['optimizations']}")
            print(f"  Alertes météo         : {agent.stats['weather_alerts']}")
            print("=" * 55)

            if agent.gui_callback:
                agent.gui_callback("monitor", "stats", agent.stats.copy())

    async def setup(self):
        print("[SETUP] Agent Moniteur démarré")
        self.add_behaviour(self.CollectStatsBehaviour())
        self.add_behaviour(self.ReportBehaviour(period=10))
