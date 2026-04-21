from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
import random

WEATHER_CONDITIONS = ["NORMAL", "PLUIE", "BROUILLARD", "NEIGE", "VERGLAS"]
WEATHER_SPEED_FACTOR = {
    "NORMAL": 1.0, "PLUIE": 0.7, "BROUILLARD": 0.5, "NEIGE": 0.4, "VERGLAS": 0.3
}

class WeatherAgent(Agent):
    """Agent météo : influence les conditions de circulation"""
    def __init__(self, jid, password, gui_callback=None):
        super().__init__(jid, password)
        self.condition = "NORMAL"
        self.gui_callback = gui_callback

    class WeatherBehaviour(PeriodicBehaviour):
        async def run(self):
            agent = self.agent
            # Changer météo aléatoirement
            if random.random() < 0.2:
                agent.condition = random.choice(WEATHER_CONDITIONS)
                print(f"[🌦️ MÉTÉO] Nouvelle condition: {agent.condition} | "
                      f"Facteur vitesse: {WEATHER_SPEED_FACTOR[agent.condition]}")

                # Alerter le contrôleur
                msg = Message(to="controller@localhost")
                msg.set_metadata("performative", "inform")
                msg.set_metadata("type", "weather_alert")
                msg.body = agent.condition
                await self.send(msg)

                # Alerter tous les feux
                for inter in ["A", "B", "C"]:
                    light_msg = Message(to=f"light_{inter.lower()}@localhost")
                    light_msg.set_metadata("performative", "inform")
                    light_msg.set_metadata("type", "weather_adjust")
                    light_msg.body = agent.condition
                    await self.send(light_msg)

                # Alerter tous les véhicules
                for vid in ["v1","v2","v3","v4","v5","amb1","pol1"]:
                    v_msg = Message(to=f"vehicle_{vid}@localhost")
                    v_msg.set_metadata("performative", "inform")
                    v_msg.set_metadata("type", "weather")
                    v_msg.body = f"{agent.condition}|{WEATHER_SPEED_FACTOR[agent.condition]}"
                    await self.send(v_msg)
            else:
                print(f"[🌦️ MÉTÉO] Condition actuelle: {agent.condition}")

            if agent.gui_callback:
                agent.gui_callback("weather", "meteo", {
                    "condition": agent.condition,
                    "speed_factor": WEATHER_SPEED_FACTOR[agent.condition]
                })

    async def setup(self):
        print("[SETUP] Agent Météo démarré")
        self.add_behaviour(self.WeatherBehaviour(period=8))
