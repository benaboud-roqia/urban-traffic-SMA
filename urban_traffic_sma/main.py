"""
SMA - Optimisation du Trafic Urbain
====================================
15 agents SPADE :
  - 5 Agents Véhicule        (v1..v5)
  - 3 Agents Feu             (light_a, light_b, light_c)
  - 1 Agent Contrôleur       (controller)
  - 2 Agents Urgence         (amb1, pol1)
  - 2 Agents Parking         (parking_p1, parking_p2)
  - 1 Agent Météo            (weather)
  - 1 Agent Moniteur         (monitor)
"""

import asyncio
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from agents.vehicle_agent import VehicleAgent
from agents.traffic_light_agent import TrafficLightAgent
from agents.controller_agent import ControllerAgent
from agents.emergency_agent import EmergencyAgent
from agents.parking_agent import ParkingAgent
from agents.weather_agent import WeatherAgent
from agents.monitor_agent import MonitorAgent
from gui.traffic_gui import TrafficGUI

# ── Configuration XMPP (Prosody local ou openfire) ──────────────────────────
# Pour tester sans serveur XMPP, utiliser spade.run() avec mock=True
XMPP_SERVER = "localhost"
PASSWORD = "password123"

def jid(name):
    return f"{name}@{XMPP_SERVER}"

async def run_agents(gui):
    cb = gui.update

    # 1. Agent Moniteur
    monitor = MonitorAgent(jid("monitor"), PASSWORD, gui_callback=cb)

    # 2. Agent Contrôleur
    controller = ControllerAgent(jid("controller"), PASSWORD, gui_callback=cb)

    # 3. Agents Feux (3 intersections)
    lights = [
        TrafficLightAgent(jid("light_a"), PASSWORD, "A", jid("controller"), gui_callback=cb),
        TrafficLightAgent(jid("light_b"), PASSWORD, "B", jid("controller"), gui_callback=cb),
        TrafficLightAgent(jid("light_c"), PASSWORD, "C", jid("controller"), gui_callback=cb),
    ]

    # 4. Agents Véhicules (5 véhicules)
    import random
    vehicles = [
        VehicleAgent(jid(f"vehicle_v{i}"), PASSWORD, f"v{i}",
                     random.choice(["A","B","C"]), gui_callback=cb)
        for i in range(1, 6)
    ]

    # 5. Agents Urgence (ambulance + police)
    emergencies = [
        EmergencyAgent(jid("vehicle_amb1"), PASSWORD, "amb1", "AMBULANCE", gui_callback=cb),
        EmergencyAgent(jid("vehicle_pol1"), PASSWORD, "pol1", "POLICE",    gui_callback=cb),
    ]

    # 6. Agents Parking (2 parkings)
    parkings = [
        ParkingAgent(jid("parking_p1"), PASSWORD, "P1", "A", 20, gui_callback=cb),
        ParkingAgent(jid("parking_p2"), PASSWORD, "P2", "B", 15, gui_callback=cb),
    ]

    # 7. Agent Météo
    weather = WeatherAgent(jid("weather"), PASSWORD, gui_callback=cb)

    all_agents = [monitor, controller, *lights, *vehicles, *emergencies, *parkings, weather]

    print("\n" + "="*55)
    print("  DÉMARRAGE DE 15 AGENTS SMA — TRAFIC URBAIN")
    print("="*55)

    # Démarrer tous les agents
    for agent in all_agents:
        await agent.start(auto_register=True)

    print(f"\n✅ {len(all_agents)} agents actifs\n")
    gui.log(f"✅ {len(all_agents)} agents démarrés")

    # Garder actif
    try:
        while True:
            await asyncio.sleep(1)
            if not any(a.is_alive() for a in all_agents):
                break
    except asyncio.CancelledError:
        pass
    finally:
        for agent in all_agents:
            await agent.stop()
        print("\n🛑 Tous les agents arrêtés.")

def start_agents(gui):
    """Lance la boucle asyncio dans un thread séparé"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_agents(gui))
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

if __name__ == "__main__":
    gui = TrafficGUI()

    # Lancer les agents dans un thread background
    agent_thread = threading.Thread(target=start_agents, args=(gui,), daemon=True)
    agent_thread.start()

    # Lancer l'interface (bloquant, thread principal)
    gui.run()
