from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
import random

class EmergencyAgent(Agent):
    """Agent véhicule prioritaire : ambulance ou police"""
    def __init__(self, jid, password, vehicle_id, vehicle_type, gui_callback=None):
        super().__init__(jid, password)
        self.vehicle_id = vehicle_id
        self.vehicle_type = vehicle_type  # "AMBULANCE" ou "POLICE"
        self.position = random.randint(50, 200)
        self.active = False
        self.current_intersection = random.choice(["A", "B", "C"])
        self.gui_callback = gui_callback

    class EmergencyBehaviour(PeriodicBehaviour):
        async def run(self):
            agent = self.agent
            # Déclencher une urgence aléatoirement
            if not agent.active and random.random() < 0.15:
                agent.active = True
                agent.position = random.randint(50, 150)
                agent.current_intersection = random.choice(["A", "B", "C"])
                print(f"[🚨 {agent.vehicle_type} {agent.vehicle_id}] URGENCE DÉCLENCHÉE → Intersection {agent.current_intersection}")

            if agent.active:
                agent.position = max(0, agent.position - 20)

                # Notifier le contrôleur
                msg = Message(to="controller@localhost")
                msg.set_metadata("performative", "request")
                msg.set_metadata("type", "emergency")
                msg.body = f"{agent.vehicle_id}|{agent.current_intersection}|{agent.vehicle_type}"
                await self.send(msg)

                # Notifier le feu directement
                light_msg = Message(to=f"light_{agent.current_intersection.lower()}@localhost")
                light_msg.set_metadata("performative", "request")
                light_msg.set_metadata("type", "force_green")
                light_msg.body = f"EMERGENCY|{agent.current_intersection}|15"
                await self.send(light_msg)

                print(f"[🚨 {agent.vehicle_type} {agent.vehicle_id}] Position: {agent.position}m | Feu {agent.current_intersection} → VERT forcé")

                if agent.position <= 0:
                    agent.active = False
                    agent.position = random.randint(50, 200)
                    print(f"[🚨 {agent.vehicle_type} {agent.vehicle_id}] Mission terminée")

            if agent.gui_callback:
                agent.gui_callback("emergency", agent.vehicle_id, {
                    "type": agent.vehicle_type,
                    "active": agent.active,
                    "position": agent.position,
                    "intersection": agent.current_intersection
                })

    async def setup(self):
        print(f"[SETUP] {self.vehicle_type} {self.vehicle_id} démarré")
        self.add_behaviour(self.EmergencyBehaviour(period=3))
