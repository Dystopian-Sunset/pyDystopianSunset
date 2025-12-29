---
description: "Combat system architecture, formulas, and development guidelines"
globs:
  - "**/ds_common/combat/**/*.py"
  - "**/ds_common/models/character.py"
  - "**/ds_common/models/npc.py"
  - "**/ds_common/models/encounter.py"
  - "**/ds_common/repository/character.py"
  - "**/ds_common/repository/encounter.py"
  - "**/ds_discord_bot/extensions/game.py"
alwaysApply: false
---

# Combat System Development Rules

## Overview

The combat system manages character resources (health, stamina, tech power, armor) with automatic restoration over time. Resources are stored as floats to support fractional restoration rates, but displayed as integers to players.

## Architecture

### Core Components

1. **Models** (`ds_common/models/`):
   - `Character` and `NPC` models contain combat resource fields
   - `Encounter` model tracks active encounters in game sessions

2. **Combat Service** (`ds_common/combat/`):
   - `resource_calculator.py` - Calculates max resources from stats
   - `damage_handler.py` - Applies damage, healing, resource consumption
   - `restoration_service.py` - Handles resource restoration over time
   - `display.py` - Formats resources for player display
   - `models.py` - Data structures (CombatResult, RestorationRates, etc.)

3. **Repositories** (`ds_common/repository/`):
   - `CharacterRepository` - Combat resource initialization and updates
   - `EncounterRepository` - Encounter CRUD operations

4. **GM Agent Tools** (`ds_discord_bot/extensions/game.py`):
   - Tools for the AI GM to manage combat during narrative gameplay

### Reference Files
@src/ds_common/combat/__init__.py
@src/ds_common/models/character.py
@src/ds_common/models/encounter.py

## Resource Fields

All combat resources are stored as **floats** to support fractional restoration:

```python
current_health: float
max_health: float
current_stamina: float
max_stamina: float
current_tech_power: float
max_tech_power: float
current_armor: float
max_armor: float
is_incapacitated: bool
last_resource_update: datetime  # UTC timestamp for catch-up calculations
```

### Important Rules

1. **Always use floats** - Never use int for combat resources
2. **Display as integers** - Use `format_resource_display()` when showing to players
3. **Update timestamps** - Always update `last_resource_update` when modifying resources
4. **Cap at max** - Resources should never exceed their max values

## Resource Calculation Formulas

### Max Health
```
(STR * 8) + (DEX * 2) + (level * 10) + class_modifier
```

Class modifiers:
- Enforcer: +50 base, +5 per level
- Tech Wizard: +20 base
- Smooth Talker: +30 base
- Spy: +25 base
- Wild Card: +35 base

### Max Stamina
```
(DEX * 5) + (STR * 2) + (level * 5) + class_modifier
```

Class modifiers:
- Enforcer: +30 base
- Tech Wizard: +15 base
- Smooth Talker: +20 base
- Spy: +40 base
- Wild Card: +25 base

### Max Tech Power
```
(INT * 10) + (level * 8) + class_modifier
```

Class modifiers:
- Enforcer: +10 base
- Tech Wizard: +50 base, +10 per level
- Smooth Talker: +30 base
- Spy: +25 base
- Wild Card: +35 base

### Max Armor
```
(DEX * 3) + equipment_bonus + (level * 2)
```

All classes use the same base formula. Equipment bonuses are added separately.

## Restoration System

### Restoration Rates (Per Second)

Base rates are calculated from stats, then modified by equipment and buffs:

**Health Restoration:**
```
((STR * 0.1) + (level * 0.5) + class_modifier + equipment_bonus) * equipment_multiplier + buff_bonus) * buff_multiplier
```

**Stamina Restoration:**
```
((DEX * 0.15) + (STR * 0.05) + (level * 0.3) + class_modifier + equipment_bonus) * equipment_multiplier + buff_bonus) * buff_multiplier
```

**Tech Power Restoration:**
```
((INT * 0.2) + (level * 0.4) + class_modifier + equipment_bonus) * equipment_multiplier + buff_bonus) * buff_multiplier
```

**Armor Restoration:**
```
((DEX * 0.05) + (level * 0.2) + equipment_bonus) * equipment_multiplier + buff_bonus) * buff_multiplier
```

### Class Restoration Modifiers

- Enforcer: Health +0.3/sec, Stamina +0.2/sec, Tech Power +0.05/sec
- Tech Wizard: Health +0.1/sec, Stamina +0.1/sec, Tech Power +0.5/sec + 0.1/sec per level
- Smooth Talker: Health +0.15/sec, Stamina +0.15/sec, Tech Power +0.2/sec
- Spy: Health +0.12/sec, Stamina +0.25/sec, Tech Power +0.15/sec
- Wild Card: Health +0.18/sec, Stamina +0.18/sec, Tech Power +0.25/sec

### Equipment Modifiers

Equipment items in inventory can modify restoration rates. Items must have `equipped: true` or be in an equipment slot.

Supported properties:
- `health_restoration_bonus: float` - Flat bonus per second
- `health_restoration_multiplier: float` - Multiplier (e.g., 1.5 for 50% increase)
- `stamina_restoration_bonus: float`
- `stamina_restoration_multiplier: float`
- `tech_power_restoration_bonus: float`
- `tech_power_restoration_multiplier: float`
- `armor_restoration_bonus: float`
- `armor_restoration_multiplier: float`

**Stacking Rules:**
- Bonuses stack **additively** (all bonuses added together)
- Multipliers stack **multiplicatively** (all multipliers multiplied together)

### Buff/Debuff Modifiers

Buffs and debuffs are stored in the character's `effects` dict. Same property names as equipment.

**Stacking Rules:**
- Same as equipment: bonuses additive, multipliers multiplicative
- Negative values are allowed for debuffs (e.g., poison reducing restoration)

### Background Restoration

A 1-second tick background task (`restore_character_resources`) runs continuously:
- Iterates through all active game sessions
- For each character, calculates elapsed time since `last_resource_update`
- Applies restoration based on elapsed seconds
- Updates `last_resource_update` timestamp
- Only restores if character is not incapacitated
- Caps resources at max values

### Catch-up Restoration

When a player joins/returns to a game session:
- Calculate time elapsed since `last_resource_update`
- Apply restoration for the entire elapsed period
- Update `last_resource_update` to current time

This ensures players don't lose restoration time when offline.

## Damage System

### Damage Application

1. **Armor absorbs damage first** - Damage reduces armor before health
2. **Remaining damage goes to health** - After armor is depleted
3. **Incapacitation check** - If health <= 0, character becomes incapacitated

### Damage Types

- `PHYSICAL` - Standard physical damage
- `TECH` - Technology-based damage
- `ENVIRONMENTAL` - Environmental hazards

All damage types currently work the same way (armor then health). Future enhancements may add type-specific mechanics.

## Development Guidelines

### Adding New Resource Types

If you need to add a new resource type (e.g., "mana", "energy"):

1. Add fields to Character/NPC models:
   ```python
   current_mana: float = Field(default=0.0)
   max_mana: float = Field(default=0.0)
   ```

2. Add calculation function to `resource_calculator.py`:
   ```python
   def calculate_max_mana(character, character_class) -> float:
       # Implementation
   ```

3. Add restoration rate calculation to `restoration_service.py`
4. Update `RestorationRates` and `RestorationModifiers` dataclasses
5. Add display formatting to `display.py`
6. Update database migration

### Modifying Restoration Formulas

When modifying restoration formulas:

1. **Update base calculation** in `restoration_service.py` → `calculate_restoration_rates()`
2. **Update class modifiers** in `_get_class_restoration_modifiers()`
3. **Update documentation** in this file
4. **Test with various stat combinations** to ensure balanced rates

### Equipment/Buff Integration

To add new equipment or buff effects:

1. Items in `character.inventory` with `equipped: true` are scanned
2. Effects in `character.effects` dict are scanned
3. Properties must match the naming pattern: `{resource}_restoration_{bonus|multiplier}`
4. Bonuses are summed, multipliers are multiplied

Example equipment item:
```python
{
    "name": "Regenerative Implant",
    "equipped": True,
    "health_restoration_bonus": 0.5,
    "health_restoration_multiplier": 1.2
}
```

Example buff effect:
```python
character.effects = {
    "well_rested": 1.5,  # This won't work - needs proper key
    "stamina_restoration_multiplier": 1.5  # This works
}
```

### Character Initialization

When creating a new character:

1. Generate character with `Character.generate_character()`
2. Save character to database
3. Set character class
4. **Call `character_repository.initialize_combat_resources(character)`**
5. This calculates max resources and sets current = max

**Never skip step 4** - characters without initialized resources will have 0 max values.

### NPC Initialization

NPCs initialize combat resources automatically in `NPC.generate_npc()`:
- Resources are calculated without class modifiers (NPCs don't have classes)
- Current resources are set to max
- `last_resource_update` is set to current time

### Encounter Management

Encounters track active combat/social/environmental situations:

1. **Start encounter** - Use `start_encounter` GM tool
2. **Link characters/NPCs** - Add to encounter via relationships
3. **End encounter** - Use `end_encounter` GM tool (sets status to COMPLETED)

Encounters are linked to game sessions and can contain multiple characters and NPCs.

## GM Agent Tools

The AI GM has access to these combat tools:

- `apply_character_damage` - Apply damage during combat
- `apply_character_healing` - Heal characters
- `consume_character_resource` - Consume stamina/tech power for abilities
- `restore_character_resource` - Restore resources (rare, usually automatic)
- `get_character_combat_status` - Get current resource status
- `start_encounter` - Begin a new encounter
- `end_encounter` - End an active encounter
- `get_encounter_status` - Check active encounter status

All tools return integer-formatted values for display to players.

## Common Patterns

### Applying Damage

```python
from ds_common.combat import apply_damage
from ds_common.combat.models import DamageType

result = apply_damage(character, damage_amount=25.0, damage_type=DamageType.PHYSICAL)
await character_repository.update(character)
```

### Checking Resource Status

```python
from ds_common.combat import format_resource_display

resources = format_resource_display(character)
print(f"Health: {resources['current_health']}/{resources['max_health']}")
```

### Calculating Restoration

```python
from ds_common.combat import calculate_restoration_rates

rates = calculate_restoration_rates(character, character_class)
# rates.health_per_second, rates.stamina_per_second, etc.
```

### Updating Resources Safely

```python
# Use repository method for safe updates
await character_repository.update_combat_resources(
    character,
    {"current_health": 50.0, "current_stamina": 30.0}
)
```

## Testing Considerations

When testing combat system:

1. **Fractional restoration** - Test with rates < 1.0 per second
2. **Equipment modifiers** - Test stacking of bonuses and multipliers
3. **Buff modifiers** - Test positive and negative values
4. **Catch-up restoration** - Test various time gaps (seconds, minutes, hours)
5. **Resource capping** - Ensure resources never exceed max
6. **Incapacitation** - Verify incapacitated characters don't restore
7. **Class differences** - Test all character classes have appropriate modifiers

## Database Schema

Combat fields are stored as:
- `FLOAT` for all resource values (current/max)
- `BOOLEAN` for `is_incapacitated`
- `TIMESTAMP WITH TIME ZONE` for `last_resource_update`

The `encounters` table links to `game_sessions` and uses junction tables for many-to-many relationships with characters and NPCs.

## Migration Notes

The migration `a1b2c3d4e5f6_add_combat_system_fields` adds:
- Combat resource columns to `characters` table
- Combat resource columns to `npcs` table
- `encounters` table
- `encounter_characters` junction table
- `encounter_npcs` junction table

All new columns have default values to support existing records.

## Future Enhancements

Potential areas for expansion:

1. **Status Effects** - Poison, burn, stun, etc. (can use existing `effects` dict)
2. **Combat Abilities** - Skills that consume resources
3. **Equipment Stats** - Equipment affecting max resources, not just restoration
4. **Damage Type Interactions** - Different armor effectiveness vs different damage types
5. **Turn-based Combat** - Structured combat commands (currently narrative-based)
6. **Combat History** - Log of combat events for analysis

When implementing these, follow the existing patterns and update this documentation.

