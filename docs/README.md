# Documentation Index

Welcome to the Quillian Undercity documentation! This directory contains comprehensive guides for setting up, developing, and contributing to the project.

## 📚 Documentation Structure

### Getting Started
- **[Installation Guide](installation.md)** - Complete setup instructions from scratch
- **[Configuration Guide](configuration.md)** - All environment variables and settings

### Development
- **[Development Guide](development.md)** - Development workflow, coding standards, and best practices
- **[Database Migrations](migrations.md)** - Working with Alembic migrations
- **[Architecture](architecture.md)** - System design and component overview

### Reference
- **[API Reference](api.md)** - Bot commands and features
- **[Contributing Guide](contributing.md)** - How to contribute to the project

### Design Documents
- **[Memory System Architecture](design/memory-system-architecture.md)** - Three-tier memory system design
- **[Game Description](design/game-description.md)** - Game world and setting
- **[Overview and Factions](design/overview-and-factions.md)** - Faction information
- **[Location: Neotopia](design/location-neotopia.md)** - Location details
- **[Leaders](design/leaders.md)** - Character and faction leaders

## 🚀 Quick Links

### For New Developers
1. Start with [Installation Guide](installation.md)
2. Read [Development Guide](development.md)
3. Review [Architecture](architecture.md) for system overview

### For Contributors
1. Read [Contributing Guide](contributing.md)
2. Review [Development Guide](development.md)
3. Check [API Reference](api.md) for command details

### For Database Work
1. See [Migrations Guide](migrations.md)
2. Review [Architecture](architecture.md) for schema overview

## 📖 Documentation Standards

All documentation should:
- Be clear and concise
- Include code examples where helpful
- Be kept up to date with code changes
- Use proper markdown formatting

## 🔄 Keeping Documentation Updated

When making code changes:
- Update relevant documentation
- Add examples for new features
- Update API reference for new commands
- Keep installation steps current

## 💡 Tips

- Use `make help` to see all available commands
- Check the main [README.md](../README.md) for project overview
- Review code comments for implementation details
- Ask questions via GitHub Issues

## 📝 Contributing to Documentation

Documentation improvements are welcome! See [Contributing Guide](contributing.md) for details.

## 🆕 Recent Updates (December 2025)

### Major Features Added
- **TOML Configuration System**: Dual configuration with TOML files and environment variable overrides
- **Embedding Service**: Support for OpenAI and local embedding services with Redis caching
- **Prompt Analysis System**: AI-based intent classification and contextual prompt loading
- **Location Graph System**: Dynamic location nodes and edges with POI generation
- **Memory System**: Three-tier memory architecture with compression and semantic search
- **Combat System**: Encounter rewards, experience distribution, and loot generation
- **Character Cooldowns**: Cooldown tracking for skills, abilities, and items
- **World Management**: Game time persistence, calendar events, and world events
- **Player Management**: Add/remove players, session capacity limits, welcome DMs
- **World Validation**: Geography-based travel validation and location facts

### Documentation Updates
- Configuration guide updated for TOML system
- Architecture documentation expanded with new systems
- API reference updated with new commands
- Memory system architecture documented

---

*Last updated: 2025-12-25*

