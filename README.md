# Quillian Undercity: Shadows of the Syndicate

Welcome to **Quillian Undercity: Shadows of the Syndicate** — a community-driven, narrative-rich roguelike adventure game designed for Discord! This project thrives on community contributions and collaboration, aiming to build an immersive world of espionage, intrigue, and emergent storytelling.

---

## 🌆 Project Vision

Quillian Undercity is a text-based adventure where players explore a sprawling, dystopian metropolis teeming with secrets, factions, and syndicates. The game leverages Discord as its primary interface, providing a social, persistent, and ever-evolving world shaped by both developers and players.

---

## 🎮 Features & Gameplay
- **Narrative-driven Roguelike:** Each playthrough offers unique stories, choices, and consequences.
- **Espionage & Factions:** Join syndicates, form alliances, and unravel conspiracies.
- **Persistent World:** Player and character data are stored in SurrealDB, ensuring continuity and depth.
- **Discord Integration:** Play directly in Discord with rich commands and real-time interaction.
- **Community World-Building:** Expand the world, lore, and gameplay through open contributions.

---

## 🛠️ Technologies Used
- **Python** (core game logic)
- **discord.py** (Discord bot framework)
- **SurrealDB** (flexible, modern database for game state)
- **SQLModel** (data modeling)
- **Podman/Docker** (containerization)
- **NATS** (messaging)
- **DragonflyDB** (key-value store)
- **Web3** (future blockchain integration)

---

## 📁 Project Structure
```
├── src
│   ├── ds_discord_bot      # Discord bot service and extensions
│   └── ds_common           # Shared models and utilities
├── db
│   └── game.surrealql      # Database schema and setup
├── Docker/                 # Containerization files
├── web3/                   # Blockchain and smart contract code
├── README.md               # This file
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Docker/Podman (for containers)
- SurrealDB, NATS, DragonflyDB (see docker-compose.yaml)
- Discord account & bot token

### Setup
1. **Clone the repository**
2. **Install dependencies** (recommended: use [uv](https://github.com/astral-sh/uv))
   ```bash
   uv sync
   ```
3. **Configure environment**
   - Copy `.env.example` to `.env` and fill in your secrets.
4. **Run services**
   ```bash
   podman compose up || docker compose up # Depending on taste
   ```
5. **Start the bot**
   ```bash
   uv run bot
   ```

---

## 🤝 Contributing
We welcome contributions from everyone! Here’s how to get involved:
- **Report bugs or request features** via GitHub Issues
- **Submit pull requests** for code, documentation, or world-building content
- **Join discussions** on Discord to help shape the game’s direction

Please read the [CONTRIBUTING.md](CONTRIBUTING.md) (to be created) for guidelines.

---

## 👥 Community & Code of Conduct
This project is dedicated to fostering a welcoming and inclusive community. All participants are expected to adhere to our Code of Conduct (to be added).

---

## 📜 License
Distributed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements
- [discord.py](https://github.com/Rapptz/discord.py)
- [surrealdb](https://github.com/surrealdb/surrealdb)
- [surrealdb.py](https://github.com/surrealdb/surrealdb.py)
- [pydantic](https://github.com/tiangolo/pydantic)
- [uv](https://github.com/astral-sh/uv)

> This project is built by the community, for the community. Your creativity shapes Quillian Undercity!