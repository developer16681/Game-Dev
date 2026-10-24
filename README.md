# Game Development Showcase Collection 🎮

A curated monorepo containing 10 interactive 2D and 3D arcade, action, shooter, RPG, and survival games built with Python using **Pygame** and the **Ursina Engine**.

Each game is fully contained within its own directory under [`games/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games) with dedicated instructions, controls, and asset structures.

---

## 🕹️ Catalog of Games

| # | Game | Engine | Genre | Directory | Entry Point |
|---|------|--------|-------|-----------|-------------|
| 1 | **Neon Runner** | Ursina | 3D Infinite Lane Runner | [`games/neon-runner/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/neon-runner) | `python main.py` |
| 2 | **Cyber Tank: Ricochet Arena** | Ursina | 3D Top-Down Tactical Tank Arena | [`games/cyber-tank/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/cyber-tank) | `python main.py` |
| 3 | **Neon Siege** | Ursina | 3D Wave Survival FPS | [`games/neon-siege/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/neon-siege) | `python main.py` |
| 4 | **Open Forest FPS** | Ursina | 3D Open Exploration & Weapon Sandbox | [`games/open-forest-fps/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/open-forest-fps) | `python main.py` |
| 5 | **Open World RPG** | Ursina | 3D Survival, Combat & Crafting RPG | [`games/open-world-rpg/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/open-world-rpg) | `python main.py` |
| 6 | **Zombie Survival** | Ursina | 3D Wave Zombie Shooter | [`games/zombie-survival/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/zombie-survival) | `python main.py` |
| 7 | **Crystal Arena** | Ursina + NumPy | 3D Fast-Paced Sci-Fi Arena FPS | [`games/crystal-arena/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/crystal-arena) | `python main.py` |
| 8 | **Neon Snake** | Pygame | 2D Neon Arcade Snake with Audio Synth | [`games/snake/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/snake) | `python main.py` |
| 9 | **Pac-Man Arcade** | Pygame | 2D Polished Classic Arcade Maze | [`games/pacman/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/pacman) | `python main.py` |
| 10 | **Tic-Tac-Toe Deluxe** | Pygame | 2D Minimax AI & 2-Player Strategy | [`games/tic-tac-toe/`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/games/tic-tac-toe) | `python main.py` |

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Environment Setup
Create and activate an isolated virtual environment:

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install all required libraries across all games with:

```bash
pip install -r requirements.txt
```

### 4. Running Any Game
Navigate to any game's folder inside `games/` and launch its `main.py`:

```bash
# Example: Launch Cyber Tank Ricochet Arena
cd games/cyber-tank
python main.py

# Example: Launch Neon Runner
cd ../neon-runner
python main.py

# Example: Launch Pacman
cd ../pacman
python main.py
```

---

## 📁 Repository Structure

```text
Game-Dev/
├── .gitignore               # Standard Python & engine cache ignores
├── README.md                # Main repository overview & catalog
├── requirements.txt         # Consolidated Python dependencies
└── games/
    ├── crystal-arena/       # 3D Sci-Fi Arena FPS with NumPy procedural audio
    ├── cyber-tank/          # 3D Tactical Ricochet Tank Shooter
    ├── neon-runner/         # Modular 3D Lane Runner with custom UI & synth
    ├── neon-siege/          # 3D Wave Survival Arena FPS
    ├── open-forest-fps/     # 3D Open World weapon testing sandbox
    ├── open-world-rpg/      # 3D Survival RPG with crafting & hotbars
    ├── pacman/              # 2D Retro Pac-Man arcade with procedural FX
    ├── snake/               # 2D Modern Neon Snake game
    ├── tic-tac-toe/         # 2D Tic-Tac-Toe with Minimax AI & particle effects
    └── zombie-survival/     # 3D FPS Zombie Survival wave shooter
```

---

## 🛠️ Contributing & Game Guidelines
- Each game should reside in its own self-contained subfolder under `games/<game-name>/`.
- The primary entry point for each game must be named `main.py`.
- Keep dependencies lean and documented in both the root [`requirements.txt`](file:///c:/Users/devel/OneDrive/Documents/GitHub/Game-Dev/requirements.txt) and the respective game folder where applicable.
- Avoid committing compiled bytecode (`__pycache__`, `*.pyc`).

---

## 📄 License
This repository is open for learning, experimentation, and game development prototyping.
