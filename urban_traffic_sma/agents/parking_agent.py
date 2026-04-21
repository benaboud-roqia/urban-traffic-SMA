from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour
from spade.message import Message
import random

class ParkingAgent(Agent):
    """Agent parking : gère les places disponibles et redirige les véhicules"""
    def __init__(self, jid, password, parking_id, intersection, capacity, gui_callback=None):
        super().__init__(jid, password)
        self.parking_id = parking_id
        self.intersection = intersection
        self.capacity = capacity
        self.occupied = random.randint(0, capacity - 2)
        self.gui_callback = gui_callback

    class ParkingMonitorBehaviour(PeriodicBehaviour):
        async def run(self):
            agent = self.agent
            # Simuler entrées/sorties
            delta = random.randint(-1, 2)
            agent.occupied = max(0, min(agent.capacity, agent.occupied + delta))
            available = agent.capacity - agent.occupied
            occupancy_pct = int((agent.occupied / agent.capacity) * 100)

            status = "PLEIN" if available == 0 else ("PRESQUE PLEIN" if available <= 2 else "DISPONIBLE")
            print(f"[🅿️ PARKING {agent.parking_id}] Intersection {agent.intersection} | "
                  f"{agent.occupied}/{agent.capacity} places | {occupancy_pct}% | {status}")

            # Alerter le contrôleur si plein
            if available == 0:
                msg = Message(to="controller@localhost")
                msg.set_metadata("performative", "inform")
                msg.set_metadata("type", "parking_full")
                msg.body = agent.intersection
                await self.send(msg)

            # Diffuser disponibilité aux véhicules
            for vid in ["v1", "v2", "v3", "v4", "v5"]:
                v_msg = Message(to=f"vehicle_{vid}@localhost")
                v_msg.set_metadata("performative", "inform")
                v_msg.set_metadata("type", "parking_info")
                v_msg.body = f"{agent.parking_id}|{agent.intersection}|{available}|{status}"
                await self.send(v_msg)

            if agent.gui_callback:
                agent.gui_callback("parking", agent.parking_id, {
                    "intersection": agent.intersection,
                    "occupied": agent.occupied,
                    "capacity": agent.capacity,
                    "available": available,
                    "status": status
                })

    async def setup(self):
        print(f"[SETUP] Parking {self.parking_id} démarré (capacité: {self.capacity})")
        self.add_behaviour(self.ParkingMonitorBehaviour(period=5))
