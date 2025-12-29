---
description: "Standards for Discord bot extensions, commands, views, and modals"
globs:
  - "**/ds_discord_bot/extensions/**/*.py"
  - "**/ds_discord_bot/bot.py"
alwaysApply: false
---

# Discord Bot Extensions Standards

## Extension Structure

### Cog Pattern
All extensions are `commands.Cog` classes that follow this structure:

```python
import logging
import discord
from discord import app_commands
from discord.ext import commands
from ds_discord_bot.postgres_manager import PostgresManager

class MyExtension(commands.Cog):
    """Description of the extension."""
    
    def __init__(self, bot: commands.Bot, postgres_manager: PostgresManager):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.bot: commands.Bot = bot
        self.postgres_manager: PostgresManager = postgres_manager
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("MyExtension cog loaded")
    
    # Commands go here
```

### Reference Files
@src/ds_discord_bot/extensions/character.py
@src/ds_discord_bot/bot.py

## Commands

### Slash Commands (Preferred)
Use `app_commands` for slash commands:

```python
my_group = app_commands.Group(name="mygroup", description="Group description")

@my_group.command(name="action", description="Command description")
async def action_command(self, interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    
    try:
        # Implementation
        await interaction.followup.send("Success message")
    except Exception as e:
        self.logger.error(f"Error in action_command: {e}", exc_info=True)
        await interaction.followup.send("Error message", ephemeral=True)
```

### Command Groups
- Use `app_commands.Group` for related commands
- Define groups as class attributes
- Use descriptive names and descriptions

### Response Patterns
- Use `defer()` for long-running operations
- Use `ephemeral=True` for user-specific responses
- Use `thinking=True` to show "Bot is thinking..." indicator
- Always handle errors gracefully with user-friendly messages

## Views (UI Components)

### View Pattern
Views inherit from `discord.ui.View`:

```python
import discord
from discord.ui import View, Button

class MyView(View):
    """Description of the view."""
    
    def __init__(self, bot: commands.Bot, postgres_manager: PostgresManager):
        super().__init__(timeout=300.0)  # 5 minute timeout
        self.bot = bot
        self.postgres_manager = postgres_manager
    
    @discord.ui.button(label="Action", style=discord.ButtonStyle.primary)
    async def action_button(
        self, 
        interaction: discord.Interaction, 
        button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        # Implementation
        await interaction.followup.send("Response")
    
    async def on_timeout(self):
        # Handle timeout
        pass
```

### Reference Files
@src/ds_discord_bot/extensions/views/character_selection.py
@src/ds_discord_bot/extensions/views/character_widget.py

## Modals

### Modal Pattern
Modals inherit from `discord.ui.Modal`:

```python
import discord
from discord.ui import Modal, TextInput

class MyModal(Modal, title="Modal Title"):
    """Description of the modal."""
    
    field_name = TextInput(
        label="Field Label",
        placeholder="Placeholder text",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # Access field value: self.field_name.value
        await interaction.followup.send("Response")
```

### Reference Files
@src/ds_discord_bot/extensions/dialogs/character_creation_modal.py

## Best Practices

### Logging
- Use `self.logger` (created in `__init__`)
- Log important events (command invocations, errors, etc.)
- Include context in log messages (user IDs, channel names, etc.)

### Error Handling
- Wrap operations in try/except blocks
- Log errors with full traceback: `self.logger.error(..., exc_info=True)`
- Provide user-friendly error messages
- Use ephemeral responses for errors

### Channel/Role Access
- Store channel/role references as instance variables
- Use bot helper methods: `await bot.get_channel("channel-name")`
- Handle None cases when channels/roles aren't found

### Async Patterns
- All commands and listeners must be async
- Use `await` for all async operations
- Don't block the event loop with sync operations

### User Experience
- Use ephemeral responses for user-specific actions
- Show "thinking" indicator for long operations
- Provide clear feedback for all user actions
- Handle timeouts gracefully in views




