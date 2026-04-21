from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour
from spade.message import Message
import random

class VehicleAgent(Agent):
    def __init__(self, jid, password, vehicle_id, intersection, gui_callback=None):
        super().__init__(jid, password)
        self.vehicle_id = vehicle_id
        self.intersection = intersection
        self.position = random.randint(30, 150)
        self.speed = random.randint(20, 60)
        self.waiting = False
        self.wait_time = 0
        self.weather_factor = 1.0
        self.parking_info = {}
        self.redirected = False
        self.gui_callback = gui_callback

    class SendPositionBehaviour(PeriodicBehaviour):
        async def run(self):
            agent = self.agent
            if not agent.waiting:
                move = int(random.randint(5, 15) * agent.weather_factor)
                agent.position = max(0, agent.position - move)
            else:
                agent.wait_time += 2

            light_jid = f"light_{agent.intersection.lower()}@localhost"
            msg = Message(to=light_jid)
            msg.set_metadata("performative", "inform")
            msg.set_metadata("type", "position")
            msg.body = f"{agent.vehicle_id}|{agent.position}|{agent.speed}|{agent.intersection}"
            await self.send(msg)

            # Envoyer stats au moniteur
            stat = Message(to="monitor@localhost")
            stat.set_metadata("performative", "inform")
            stat.set_metadata("type", "stats_vehicle")
            stat.body = f"{agent.vehicle_id}|{agent.wait_time}"
            await self.send(stat)

            print(f"[🚗 VÉHICULE {agent.vehicle_id}] Inter:{agent.intersection} | "
                  f"Pos:{agent.position}m | Vitesse:{agent.speed}km/h | "
                  f"Attente:{'OUI' if agent.waiting else 'NON'}({agent.wait_time}s) | "
                  f"Météo:{agent.weather_factor}")

            if agent.gui_callback:
                agent.gui_callback("vehicle", agent.vehicle_id, {
                    "intersection": agent.intersection,
                    "position": agent.position,
                    "speed": agent.speed,
                    "waiting": agent.waiting,
                    "wait_time": agent.wait_time,
                    "weather_factor": agent.weather_factor
                })

            # Réinitialiser si arrivé
            if agent.position <= 0:
                agent.position = random.randint(80, 150)
                agent.intersection = random.choice(["A", "B", "C"])
                agent.wait_time = 0

    class ReceiveMessagesBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=2)
            if not msg:
                return
            t = msg.get_metadata("type")

            if t == "light_status":
                parts = msg.body.split("|")
                self.agent.waiting = (parts[0] == "RED")
                if parts[0] == "GREEN":
                    self.agent.wait_time = 0

            elif t == "weather":
                parts = msg.body.split("|")
                self.agent.weather_factor = float(parts[1])
                self.agent.speed = int(self.agent.speed * float(parts[1]))
                print(f"[🚗 VÉHICULE {self.agent.vehicle_id}] 🌦️ Météo: {parts[0]} → vitesse réduite")

            elif t == "parking_info":
                parts = msg.body.split("|")
                self.agent.parking_info[parts[0]] = {"available": int(parts[2]), "status": parts[3]}

            elif t == "redirect":
                parts = msg.body.split("|")
                if parts[0] == "PARKING_FULL":
                    old = self.agent.intersection
                    options = [x for x in ["A","B","C"] if x != parts[1]]
                    self.agent.intersection = random.choice(options)
                    print(f"[🚗 VÉHICULE {self.agent.vehicle_id}] 🔀 Redirigé de {old} → {self.agent.intersection}")

    async def setup(self):
        print(f"[SETUP] Véhicule {self.vehicle_id} démarré sur intersection {self.intersection}")
        self.add_behaviour(self.SendPositionBehaviour(period=2))
        self.add_behaviour(self.ReceiveMessagesBehaviour())
