# 🚦 Urban Traffic SMA — Système Multi-Agents pour l'Optimisation du Trafic Urbain

> Projet académique réalisé dans le cadre du cours d'Intelligence Artificielle Distribuée  
> Université — Année 2025/2026

---

## 👩‍💻 Étudiantes

| Nom | Prénom |
|-----|--------|
| BENABOUD | Roqia |
| KOUACHKHIA | Dounia Zed | https://github.com/douniaZD
| MEHRAB | Roua |

---

## 📌 Description

**Urban Traffic SMA** est une simulation d'un système multi-agents (SMA) appliqué à l'optimisation du trafic urbain.  
Le projet met en œuvre **15 agents autonomes** qui communiquent entre eux pour réduire les embouteillages et minimiser le temps d'attente aux intersections.

Chaque agent a un rôle précis, perçoit son environnement et prend des décisions en temps réel. L'ensemble est visualisé via une **interface web moderne** (HTML/CSS/JS) connectée au moteur de simulation Python via **WebSocket**.

---

## 🤖 Les 15 Agents

| Type | Nombre | Rôle |
|------|--------|------|
| 🚗 Agent Véhicule | 5 | Se déplace, envoie sa position, réagit aux feux et à la météo |
| 🚦 Agent Feu de Signalisation | 3 | Adapte la durée du vert selon le nombre de véhicules en attente |
| 🧠 Agent Contrôleur | 1 | Optimise globalement le trafic, gère les urgences et redirections |
| 🚑🚓 Agent Prioritaire | 2 | Ambulance et Police — force le feu au vert sur leur trajet |
| 🅿️ Agent Parking | 2 | Surveille les places disponibles, alerte en cas de saturation |
| 🌦️ Agent Météo | 1 | Modifie les conditions de circulation (pluie, neige, verglas...) |
| 📊 Agent Moniteur | 1 | Collecte et affiche les statistiques globales en temps réel |

---

## ⚙️ Fonctionnement

```
Véhicules ──► envoient leur position ──► Feux
Feux      ──► adaptent leur durée    ──► Véhicules (statut rouge/vert)
Feux      ──► envoient rapport       ──► Contrôleur
Contrôleur──► optimise / redirige    ──► Feux + Véhicules
Urgences  ──► forcent le vert        ──► Feux + Contrôleur
Météo     ──► réduit les vitesses    ──► Tous les agents
Parkings  ──► alerte saturation      ──► Contrôleur ──► Véhicules (redirection)
Moniteur  ──► collecte tout          ──► Interface web
```

**Objectifs :**
- Minimiser les embouteillages
- Réduire le temps d'attente moyen
- Gérer les priorités (urgences)
- S'adapter aux conditions météo

---

## 🖥️ Interface Web

Interface en **HTML/CSS/JS** avec thème blanc, connectée via WebSocket :

- 🗺️ Carte visuelle des intersections avec feux et véhicules animés
- ⚙️ **Panneau de simulation manuelle** (centre) :
  - Forcer un feu au vert / rouge / mode auto
  - Déclencher une urgence (ambulance ou police)
  - Changer la météo en un clic
  - Remplir / vider les parkings
- 📊 Statistiques en temps réel
- 📋 Journal des interactions entre agents

---

## 🗂️ Structure du Projet

```
urban-traffic-sma/
├── agents/
│   ├── vehicle_agent.py        # Agent véhicule
│   ├── traffic_light_agent.py  # Agent feu de signalisation
│   ├── controller_agent.py     # Agent contrôleur central
│   ├── emergency_agent.py      # Agent véhicule prioritaire
│   ├── parking_agent.py        # Agent parking
│   ├── weather_agent.py        # Agent météo
│   └── monitor_agent.py        # Agent moniteur statistiques
├── web/
│   ├── index.html              # Interface web
│   ├── style.css               # Thème blanc
│   └── app.js                  # Logique WebSocket + rendu
├── server.py                   # Serveur WebSocket + moteur de simulation
├── simulation.py               # Version standalone (sans serveur XMPP)
├── main.py                     # Version SPADE complète (avec serveur XMPP)
├── requirements.txt
└── README.md
```

---

## 🚀 Installation et Lancement

### Prérequis

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/[votre-username]/urban-traffic-sma.git
cd urban-traffic-sma
pip install websockets
```

### Lancement (version web recommandée)

```bash
python server.py
```

Le navigateur s'ouvre automatiquement sur `http://localhost:8080`.

### Lancement (version Tkinter standalone)

```bash
python simulation.py
```

### Lancement (version SPADE complète)

Nécessite un serveur XMPP local (Prosody) et `pip install spade` :

```bash
python main.py
```

---

## 🛠️ Technologies

| Technologie | Usage |
|-------------|-------|
| Python 3 | Moteur de simulation et agents |
| asyncio | Concurrence des agents |
| websockets | Communication serveur ↔ interface |
| HTML / CSS / JS | Interface web |
| Tkinter | Interface desktop (version standalone) |
| SPADE *(optionnel)* | Framework SMA avec protocole XMPP |

---

## 📸 Aperçu
<img width="3442" height="1795" alt="image" src="https://github.com/user-attachments/assets/18a3ef80-6367-46be-8606-423d2b7182e0" />

```
┌─────────────────────────────────────────────────────────────┐
│  🚦 Système Multi-Agents — Optimisation du Trafic Urbain    │
├──────────────┬──────────────────────────┬───────────────────┤
│ Feux A/B/C   │  ⚙️ Simulation Manuelle  │ 🚗 Véhicules      │
│ Météo        │  [Carte intersections]   │ 🅿️ Parkings       │
│ Contrôleur   │  [Boutons de contrôle]   │ 📋 Journal        │
│ Urgences     │  📊 Statistiques         │                   │
└──────────────┴──────────────────────────┴───────────────────┘
```

---

## 📄 Licence

Projet académique — Usage éducatif uniquement.
