---
description: "Item system architecture, equipment slots, and development guidelines"
globs:
  - "**/ds_common/models/item_*.py"
  - "**/ds_common/models/character.py"
  - "**/ds_common/equipment/**/*.py"
  - "**/ds_common/repository/item_*.py"
  - "**/ds_common/repository/character.py"
  - "**/ds_common/seed_data.py"
  - "**/ds_discord_bot/extensions/game.py"
  - "**/ds_discord_bot/extensions/character.py"
alwaysApply: false
---

# Item System Development Rules

## Overview

The item system provides a comprehensive equipment and inventory management system. Items are defined as reusable templates in the database, with instances stored in character inventories. Items can be equipped to specific slots and provide various bonuses to character stats, resources, and combat effectiveness.

## Architecture

### Core Components

1. **Models** (`ds_common/models/`):
   - `ItemCategory` - Item categories (weapon, armor, implant, clothing, consumable, tool, accessory, backpack)
   - `ItemTemplate` - Reusable item definitions with effects and properties
   - `Character` - Contains `inventory` (list of item instances) and `equipped_items` (slot mapping)
   - `CharacterClassStartingEquipment` - Junction table linking classes to starting equipment

2. **Equipment Service** (`ds_common/equipment/`):
   - `effect_calculator.py` - Calculates aggregated equipment effects
   - `validation.py` - Validates slot/item compatibility

3. **Repositories** (`ds_common/repository/`):
   - `ItemCategoryRepository` - CRUD for item categories
   - `ItemTemplateRepository` - CRUD for item templates
   - `CharacterRepository` - Equipment management methods (equip, unequip, etc.)

4. **Seed Data** (`ds_common/seed_data.py`):
   - `ITEM_CATEGORIES` - Initial item categories
   - `ITEM_TEMPLATES` - Initial item templates with effects
   - `CLASS_STARTING_EQUIPMENT` - Class-specific starting equipment mappings

### Reference Files
@src/ds_common/models/item_category.py
@src/ds_common/models/item_template.py
@src/ds_common/equipment/effect_calculator.py
@src/ds_common/repository/character.py

## Item Template Structure

Item templates define reusable item properties:

```python
class ItemTemplate(BaseSQLModel, table=True):
    name: str  # Unique item name
    description: str
    category_id: UUID  # Foreign key to ItemCategory
    equippable_slots: list[str]  # Slots this item can be equipped to
    rarity: str  # "common", "uncommon", "rare", "epic", "legendary"
    value: int  # Credits value
    
    # Effect properties (all JSON dicts)
    stat_bonuses: dict[str, float]  # e.g., {"STR": 5.0, "DEX": 2.0}
    stat_multipliers: dict[str, float]  # e.g., {"INT": 1.2}
    resource_bonuses: dict[str, float]  # e.g., {"max_health": 20.0}
    resource_regeneration_modifiers: dict[str, dict[str, float]]  # e.g., {"health": {"bonus": 0.5, "multiplier": 1.2}}
    damage_bonuses: dict[str, float]  # e.g., {"physical": 10.0}
    damage_multipliers: dict[str, float]  # e.g., {"physical": 1.15}
    healing_bonuses: dict[str, float]  # e.g., {"heal_amount": 5.0}
    inventory_slots_bonus: int  # Additional inventory slots
```

## Item Instance Structure

Items in character inventory are JSON dicts:

```python
{
    "instance_id": "uuid",  # Unique instance ID
    "item_template_id": "uuid",  # Reference to ItemTemplate (optional for backward compatibility)
    "name": "Item Name",  # Display name
    "quantity": 1,
    "equipped": false,  # Whether item is currently equipped
    "equipment_slot": null,  # Slot name if equipped (e.g., "chest")
    "durability": 100,  # Optional instance-specific data
    # ... other instance-specific customization
}
```

## Equipment Slots

Equipment slots are defined in `ds_common/models/game_master.py` as `EQUIPMENT_EQUIP_LOCATION`:

- `head`, `left_ear`, `right_ear`, `neck`, `shoulders`
- `left_hand`, `right_hand`, `chest`, `back`, `waist`, `legs`, `feet`

## Equipment Effects

### Stat Bonuses and Multipliers

- **Stat Bonuses**: Additive bonuses to base stats (e.g., +5 STR)
- **Stat Multipliers**: Multiplicative modifiers (e.g., 1.2x INT)
- Applied when calculating character stats for combat/resource calculations

### Resource Bonuses

- **Max Resource Bonuses**: Additive bonuses to max resources
  - Keys: `max_health`, `max_stamina`, `max_tech_power`, `max_armor`
  - Values: Float bonuses added to base resource calculations
- Integrated into `resource_calculator.py` functions

### Resource Regeneration Modifiers

- **Structure**: `{"resource_name": {"bonus": float, "multiplier": float}}`
- **Resources**: `health`, `stamina`, `tech_power`, `armor`
- Converted to restoration service format: `{resource}_restoration_bonus` and `{resource}_restoration_multiplier`
- Follows existing stacking rules (bonuses additive, multipliers multiplicative)

### Damage and Healing Bonuses

- **Damage Bonuses**: Additive bonuses by damage type (e.g., `{"physical": 10.0}`)
- **Damage Multipliers**: Multiplicative modifiers by damage type
- **Healing Bonuses**: Additive bonuses to healing amounts

### Inventory Expansion

- `inventory_slots_bonus`: Integer value for additional inventory slots
- Applied when calculating character inventory capacity

## Equipment Management

### Equipping Items

1. Validate item/slot compatibility using `validate_item_slot_compatibility()`
2. Unequip existing item in slot (if any)
3. Update item instance: set `equipped: true`, `equipment_slot: <slot>`
4. Update `character.equipped_items[slot] = instance_id`
5. Recalculate resources with `recalculate_resources_with_equipment()`

### Unequipping Items

1. Find item by slot in `character.equipped_items`
2. Update item instance: set `equipped: false`, `equipment_slot: null`
3. Remove from `character.equipped_items[slot]`
4. Recalculate resources

### Resource Recalculation

When equipment changes, `recalculate_resources_with_equipment()`:
1. Gets equipped item templates
2. Calculates equipment resource bonuses
3. Recalculates max resources with equipment bonuses
4. Caps current resources at new max values

## Character Creation Flow

1. Generate character with `Character.generate_character()`
2. Set character class
3. Load starting equipment templates for class from `CharacterClassStartingEquipment`
4. Create item instances in inventory with `item_template_id`
5. Auto-equip starting items (set `equipped: true`, `equipment_slot`, update `equipped_items`)
6. Call `initialize_combat_resources()` - includes equipment bonuses in calculations

## GM Tools

The AI GM has access to these item/equipment tools:

- `get_character_inventory` - Get character's inventory
- `add_character_item` - Add item to inventory (supports item templates)
- `remove_character_item` - Remove item from inventory
- `get_equipped_items` - List all equipped items
- `equip_item` - Equip item from inventory to slot
- `unequip_item` - Remove item from slot

## Development Guidelines

### Adding New Item Templates

1. Add template data to `ITEM_TEMPLATES` in `seed_data.py`
2. Define all effect properties (use empty dicts if no effects)
3. Set appropriate `equippable_slots` for the item type
4. Run seed data to populate database

### Adding New Item Categories

1. Add category data to `ITEM_CATEGORIES` in `seed_data.py`
2. Update category list in this documentation
3. Run seed data to populate database

### Modifying Equipment Effects

When adding new effect types:

1. Add field to `ItemTemplate` model
2. Add calculation function to `effect_calculator.py`
3. Integrate into relevant systems (resource calculator, damage handler, etc.)
4. Update this documentation

### Backward Compatibility

- Existing inventory items without `item_template_id` still work
- Existing `equipped: true` or `equipment_slot` pattern maintained
- Restoration service supports both template-based and direct item properties

## Database Schema

- `item_categories` table - Item categories
- `item_templates` table - Item template definitions
- `character_class_starting_equipment` junction table - Class starting equipment
- `characters.equipped_items` JSON field - Slot to instance ID mapping
- `characters.inventory` JSON field - List of item instances

## Migration Notes

The migration `d7e8f9a0b1c2_add_item_system_and_equipment_slots` adds:
- `item_categories` table
- `item_templates` table
- `character_class_starting_equipment` junction table
- `characters.equipped_items` JSON column

## TODO: Shop Item Population System

**Status**: Not yet implemented

### Requirements

The GM needs a system to populate shops with items for players to purchase. This system should:

1. **Shop Model**: Create a `Shop` or `Vendor` model to represent in-game shops/vendors
   - Location/faction association
   - Shop type (weapon shop, general store, black market, etc.)
   - Inventory management

2. **Shop Inventory**: Link shops to item templates
   - Which items are available in which shops
   - Stock quantities (if applicable)
   - Pricing (base price, markup, discounts)
   - Item availability conditions (level requirements, faction reputation, etc.)

3. **GM Tools**: Provide GM tools to:
   - Create/manage shops
   - Add/remove items from shop inventory
   - Set item prices and availability
   - View shop inventory

4. **Player Interaction**: Player commands to:
   - View shop inventory
   - Purchase items (with credit deduction)
   - Sell items to shops (if applicable)

5. **Dynamic Inventory**: Consider:
   - Shop inventory refresh/rotation
   - Limited stock items
   - Special/rare items that appear conditionally
   - Faction-based availability

### Implementation Considerations

- Use junction table `ShopItem` to link shops to item templates
- Consider shop-specific pricing vs. item template base value
- Integration with existing `add_character_item` tool for purchases
- NPC vendor integration (link shops to NPCs)
- Location-based shop discovery

### Related Files to Create/Modify

- `src/ds_common/models/shop.py` - Shop model
- `src/ds_common/models/junction_tables.py` - Add `ShopItem` junction table
- `src/ds_common/repository/shop.py` - Shop repository
- `src/ds_discord_bot/extensions/game.py` - Add shop management GM tools
- `src/ds_discord_bot/extensions/character.py` - Add player shop commands
- Alembic migration for shop tables

## Future Enhancements

Potential areas for expansion:

1. **Item Crafting** - Combine items to create new ones
2. **Item Modifications** - Enhance items with mods/upgrades
3. **Item Durability** - Items degrade with use
4. **Item Sets** - Set bonuses for wearing multiple related items
5. **Item Enchantments** - Special effects that can be added to items
6. **Auction House** - Player-to-player trading system
7. **Item Rarity Scaling** - Dynamic item generation based on rarity tiers

When implementing these, follow the existing patterns and update this documentation.

