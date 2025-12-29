---
description: "Standards for pydantic-ai agent usage - creating agents, tools, system prompts, and handling responses"
globs:
  - "**/ds_discord_bot/extensions/game.py"
  - "**/*agent*.py"
  - "**/*ai*.py"
alwaysApply: false
---

# Pydantic-AI Standards

## Overview

Pydantic-AI is used for AI agent functionality, specifically for the Game Master agent that handles game interactions. The agent uses OpenAI-compatible models (including local Ollama models).

## Agent Setup Pattern

### Model Configuration
```python
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
import os

# Configure model
model = OpenAIModel(
    model_name=os.getenv("DB_GM_MODEL_NAME", "gemma3:latest"),
    base_url=os.getenv("DB_GM_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("OPENAI_API_KEY", ""),  # Empty for local Ollama
)
```

### Agent Creation
```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# Create agent with model
agent = Agent(
    model=model,
    system_prompt="Your system prompt here",
    result_type=YourResultType,  # Optional: Pydantic model for structured output
)
```

### Reference Files
@src/ds_discord_bot/extensions/game.py

## Agent Tools (Functions)

### Tool Definition Pattern
Tools are functions that the agent can call. Define them with proper type hints and docstrings:

```python
from pydantic_ai import RunContext
from pydantic import BaseModel

class ToolInput(BaseModel):
    """Input schema for the tool."""
    param1: str
    param2: int

async def my_tool(ctx: RunContext[GMAgentDependencies], input: ToolInput) -> ToolResult:
    """
    Tool description that the agent will see.
    
    Args:
        ctx: Run context with dependencies
        input: Tool input parameters
        
    Returns:
        Tool result
    """
    # Access dependencies from context
    deps = ctx.deps
    postgres_manager = deps.postgres_manager
    game_session = deps.game_session
    
    # Tool implementation
    result = await do_something(input.param1, input.param2)
    
    return ToolResult(value=result)
```

### Registering Tools
```python
from pydantic_ai import Agent

agent = Agent(
    model=model,
    system_prompt=system_prompt,
    tools=[my_tool, another_tool],  # List of tool functions
)
```

## System Prompts

### Prompt Structure
- Store prompts in markdown files when possible (e.g., `extensions/prompts/gm_base.md`)
- Load prompts from files using `aiofiles` for async file operations
- Include clear instructions for the agent
- Specify available tools and their purposes
- Define expected output format

### Loading Prompts
```python
import aiofiles
from pathlib import Path

async def load_system_prompt(prompt_path: Path) -> str:
    """Load system prompt from markdown file."""
    async with aiofiles.open(prompt_path, "r") as f:
        return await f.read()
```

### Reference Files
@src/ds_discord_bot/extensions/prompts/gm_base.md

## Running Agents

### Basic Agent Run
```python
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult

# Run agent with a message
result: AgentRunResult = await agent.run(
    "User message here",
    deps=GMAgentDependencies(...),  # Dependencies for tools
)

# Access result
response_text = result.data  # String response
```

### Streaming Responses
```python
from collections.abc import AsyncGenerator
from pydantic_ai.agent import AgentRunResult

async def stream_agent_response(
    agent: Agent,
    message: str,
    deps: GMAgentDependencies,
) -> AsyncGenerator[str, None]:
    """Stream agent responses token by token."""
    async for chunk in agent.run_stream(message, deps=deps):
        if chunk.delta:
            yield chunk.delta
```

### Handling Tool Calls
The agent automatically handles tool calls. Tools receive `RunContext` with dependencies:

```python
from pydantic_ai import RunContext

async def my_tool(ctx: RunContext[GMAgentDependencies], input: ToolInput) -> ToolResult:
    # Access dependencies
    deps = ctx.deps
    # Use dependencies in tool implementation
    result = await perform_action(deps)
    return ToolResult(result=result)
```

## Dependencies Pattern

### Dependency Dataclass
Create a dataclass to hold all dependencies needed by agent tools:

```python
from dataclasses import dataclass
from ds_discord_bot.postgres_manager import PostgresManager
from ds_common.models.game_session import GameSession
from ds_common.models.player import Player
from ds_common.models.character import Character
from ds_common.models.character_class import CharacterClass

@dataclass
class GMAgentDependencies:
    """Dependencies for Game Master agent tools."""
    postgres_manager: PostgresManager
    game_session: GameSession
    player: Player
    characters: dict[Character, CharacterClass]
    action_character: Character | None = None
```

### Reference Files
@src/ds_common/models/game_master.py

## Request/Response Models

### Using Pydantic Models for Structured Output
Define Pydantic models for tool inputs and outputs:

```python
from pydantic import BaseModel
from typing import Literal

# Request models
class RequestAddCredits(BaseModel):
    character: Character
    amount: int
    currency: Literal["quill", "credit"]

# Response models
class ResponseCharacterCredits(BaseModel):
    character: Character
    credits: int
    currency: Literal["quill", "credit"]
```

### Tool Input/Output Types
- Tool inputs should be Pydantic models
- Tool outputs should be Pydantic models
- Use type hints consistently
- Document all fields with descriptions

## Best Practices

### Error Handling
- Wrap agent runs in try/except blocks
- Log errors with full traceback
- Provide fallback responses for agent failures
- Handle tool execution errors gracefully

### Logging
- Log agent interactions for debugging
- Store agent history in database (see `GMHistory` model)
- Include context in log messages (session ID, user ID, etc.)

### Performance
- Use streaming for long responses
- Cache system prompts when possible
- Monitor token usage and costs
- Implement rate limiting if needed

### Security
- Validate all tool inputs
- Sanitize user messages before passing to agent
- Don't expose sensitive data in prompts
- Use environment variables for API keys

### Testing
- Mock agent responses in tests
- Test tools independently
- Test error handling paths
- Verify tool input/output schemas

## Common Patterns

### Agent Initialization
```python
import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

async def init_agent() -> Agent:
    """Initialize the AI agent."""
    model = OpenAIModel(
        model_name=os.getenv("DB_GM_MODEL_NAME", "gemma3:latest"),
        base_url=os.getenv("DB_GM_BASE_URL", "http://localhost:11434/v1"),
    )
    
    system_prompt = await load_system_prompt(Path("extensions/prompts/gm_base.md"))
    
    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[tool1, tool2, tool3],
    )
```

### Running Agent with History
```python
from pydantic_ai.messages import ModelMessagesTypeAdapter

# Load conversation history
history = await load_history(game_session)

# Run agent with history
result = await agent.run(
    user_message,
    deps=dependencies,
    message_history=ModelMessagesTypeAdapter.validate_python(history),
)
```

### Storing Agent History
```python
from ds_common.models.game_master import GMHistory

# Store interaction in database
gm_history = GMHistory(
    game_session_id=game_session.id,
    player_id=player.id,
    request=user_message,
    model_messages=result.all_messages(),
)
await gm_history_repository.create(gm_history)
```

## Environment Variables

### Required Configuration
- `DB_GM_MODEL_NAME`: Model name (e.g., "gemma3:latest", "gpt-4")
- `DB_GM_BASE_URL`: API base URL (e.g., "http://localhost:11434/v1" for Ollama)
- `OPENAI_API_KEY`: API key (optional for local models)

### Reference
@.env.example

## Things to Avoid

- ❌ Don't hardcode API keys or model names
- ❌ Don't forget to handle errors in tool execution
- ❌ Don't pass unvalidated user input directly to agents
- ❌ Don't skip logging agent interactions
- ❌ Don't use sync file operations (use `aiofiles`)
- ❌ Don't forget to store conversation history
- ❌ Don't expose sensitive data in prompts
- ❌ Don't ignore rate limits or token usage




