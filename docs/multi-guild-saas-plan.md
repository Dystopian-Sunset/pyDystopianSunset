# Multi-Guild SaaS Transformation Plan

## Executive Summary

Transform the Discord bot from a single-guild deployment to a multi-tenant SaaS offering that can be installed on multiple Discord servers simultaneously. This document outlines required changes across database schema, configuration, bot logic, and infrastructure.

---

## Current Architecture Analysis

### Single-Guild Assumptions
1. **Hardcoded Configuration**: `config.toml` contains single-guild settings (channel names, categories)
2. **No Guild Scoping**: Database models lack `guild_id` foreign keys
3. **Global Settings**: Single `GameSettings` table applies to all sessions
4. **Hardcoded Role Names**: Player role name is configured globally
5. **Single Namespace**: Channel names, role names assume single Discord server

### Models Requiring Guild Scoping
```
✗ GameSession - No guild_id (uses channel_id only)
✗ GameSettings - Global settings, not per-guild
✗ Player - Discord users tracked globally, no guild context
✗ Character - No guild scoping
✗ GMHistory - No guild scoping
✗ All Memory Models - No guild scoping
✗ World/Location Models - Shared across all guilds
```

---

## Phase 1: Database Schema Changes

### 1.1 Add Guild Model
```python
class Guild(BaseSQLModel, table=True):
    """Discord guild (server) configuration."""

    __tablename__ = "guilds"

    # Discord guild ID (snowflake)
    guild_id: int = Field(sa_column=Column(BigInteger(), unique=True, index=True))

    # Guild metadata
    guild_name: str = Field(description="Guild name for reference")
    owner_discord_id: int = Field(sa_column=Column(BigInteger()))

    # Subscription/billing
    subscription_tier: str = Field(default="free")  # free, basic, premium, enterprise
    subscription_status: str = Field(default="active")  # active, suspended, cancelled
    subscription_expires_at: datetime | None = None

    # Feature flags per guild
    features_enabled: dict = Field(default_factory=dict, sa_type=JSON)

    # Resource limits (per subscription tier)
    max_game_sessions: int = Field(default=3)
    max_players: int = Field(default=50)
    max_characters_per_player: int = Field(default=2)

    # Guild-specific configuration
    config: dict = Field(default_factory=dict, sa_type=JSON)  # Overrides from config.toml

    # Onboarding status
    setup_completed: bool = Field(default=False)
    setup_step: str | None = None

    # Relationships
    game_settings_id: UUID | None = Field(foreign_key="game_settings.id")
    game_settings: "GameSettings" = Relationship(back_populates="guild")
```

### 1.2 Add guild_id to Existing Models

**Critical Models:**
```python
# GameSession - Add guild scoping
class GameSession(BaseSQLModel, table=True):
    guild_id: int = Field(sa_column=Column(BigInteger(), index=True))
    guild: "Guild" = Relationship(back_populates="game_sessions")
    # ... existing fields

# GameSettings - One per guild
class GameSettings(BaseSQLModel, table=True):
    guild_id: int | None = Field(sa_column=Column(BigInteger(), unique=True, nullable=True))
    # nullable for global default settings
    guild: "Guild" = Relationship(back_populates="game_settings")
    # ... existing fields

# Player - Track per-guild membership
class PlayerGuildMembership(BaseSQLModel, table=True):
    """Junction table for player-guild relationship."""
    player_id: UUID = Field(foreign_key="players.id")
    guild_id: int = Field(sa_column=Column(BigInteger()))

    # Per-guild player settings
    nickname: str | None = None
    joined_at: datetime
    is_banned: bool = Field(default=False)

    __table_args__ = (UniqueConstraint("player_id", "guild_id"),)
```

**Memory/World Models:**
```python
# All memory models need guild scoping
class SessionMemory(BaseSQLModel, table=True):
    guild_id: int = Field(sa_column=Column(BigInteger(), index=True))
    # ... existing fields

# Location/world models - decision: shared or per-guild?
# Option A: Shared world (better for curated content)
# Option B: Per-guild worlds (better for customization)
class LocationNode(BaseSQLModel, table=True):
    guild_id: int | None = Field(sa_column=Column(BigInteger(), nullable=True))
    # NULL = global/shared, non-NULL = guild-specific
```

### 1.3 Database Migration Strategy
```sql
-- Step 1: Add guild_id columns (nullable initially)
ALTER TABLE game_sessions ADD COLUMN guild_id BIGINT;
ALTER TABLE game_settings ADD COLUMN guild_id BIGINT;
-- ... repeat for all tables

-- Step 2: Backfill existing data with a "default" guild_id
-- (Assuming current deployment is guild ID 123456789)
UPDATE game_sessions SET guild_id = 123456789 WHERE guild_id IS NULL;

-- Step 3: Create Guild table and seed default guild
INSERT INTO guilds (guild_id, guild_name, subscription_tier, max_game_sessions)
VALUES (123456789, 'Original Server', 'premium', 50);

-- Step 4: Make guild_id NOT NULL and add foreign keys
ALTER TABLE game_sessions ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE game_sessions ADD CONSTRAINT fk_guild
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id);

-- Step 5: Add indexes for performance
CREATE INDEX idx_game_sessions_guild ON game_sessions(guild_id);
CREATE INDEX idx_players_guild ON player_guild_membership(guild_id);
```

---

## Phase 2: Configuration System Refactor

### 2.1 Per-Guild Configuration

**Current Problem:** `config.toml` has global channel names:
```toml
[game]
session_category_name = "Speakeasy"
session_join_channel_name = "Join-to-Play"
service_announcements_channel_name = "📟-service-announcements"
```

**Solution:** Move to database with per-guild overrides:

```python
class GuildConfig:
    """Guild-specific configuration with fallback to defaults."""

    def __init__(self, guild_id: int, postgres_manager: PostgresManager):
        self.guild_id = guild_id
        self.postgres_manager = postgres_manager
        self._defaults = load_config_toml()  # Global defaults
        self._guild_overrides: dict = {}

    async def get(self, key: str, default: Any = None) -> Any:
        """Get config value with precedence: guild override > default > fallback."""
        if key in self._guild_overrides:
            return self._guild_overrides[key]

        # Fetch from database
        guild_repo = GuildRepository(self.postgres_manager)
        guild = await guild_repo.get_by_guild_id(self.guild_id)

        if guild and key in guild.config:
            return guild.config[key]

        # Fall back to global defaults
        return self._defaults.get(key, default)
```

### 2.2 Bot-Level vs Guild-Level Settings

**Bot-Level (Global):**
- PostgreSQL connection
- Redis connection
- AI model configuration (can be overridden per guild for premium tiers)
- Metrics/logging settings
- Bot token

**Guild-Level (Per-Guild):**
- Channel names and categories
- Role names
- Game session limits
- Character limits
- Custom prompts/lore
- Theme preferences (cyberpunk, fantasy, western)

---

## Phase 3: Bot Logic Changes

### 3.1 Guild Context Injection

**Before:**
```python
@app_commands.command(name="join")
async def join_game(self, interaction: discord.Interaction):
    # Assumes single guild
    game_session = await self.session_manager.get_or_create_session(...)
```

**After:**
```python
@app_commands.command(name="join")
async def join_game(self, interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.response.send_message("This command must be used in a server.")
        return

    # Verify guild is registered and active
    guild = await self.guild_repo.get_by_guild_id(guild_id)
    if not guild or guild.subscription_status != "active":
        await interaction.response.send_message("This server's subscription is not active.")
        return

    # All queries now scoped to guild
    game_session = await self.session_manager.get_or_create_session(
        guild_id=guild_id,
        ...
    )
```

### 3.2 Repository Pattern Updates

**Add guild_id filtering to all queries:**
```python
class GameSessionRepository(BaseRepository[GameSession]):

    async def get_by_guild(self, guild_id: int) -> list[GameSession]:
        """Get all game sessions for a guild."""
        async with self._with_session() as session:
            result = await session.execute(
                select(GameSession)
                .where(GameSession.guild_id == guild_id)
                .where(GameSession.is_open == True)
            )
            return list(result.scalars().all())

    async def get_active_count(self, guild_id: int) -> int:
        """Get count of active sessions for guild (for quota enforcement)."""
        async with self._with_session() as session:
            result = await session.execute(
                select(func.count(GameSession.id))
                .where(GameSession.guild_id == guild_id)
                .where(GameSession.is_open == True)
            )
            return result.scalar_one()
```

### 3.3 Rate Limiting & Quotas

```python
class GuildQuotaService:
    """Enforce per-guild quotas based on subscription tier."""

    async def check_can_create_session(self, guild_id: int) -> tuple[bool, str]:
        """Check if guild can create another game session."""
        guild = await self.guild_repo.get_by_guild_id(guild_id)
        active_count = await self.session_repo.get_active_count(guild_id)

        if active_count >= guild.max_game_sessions:
            return False, f"Max game sessions ({guild.max_game_sessions}) reached. Upgrade subscription for more."

        return True, ""

    async def check_can_create_character(self, guild_id: int, player_id: UUID) -> tuple[bool, str]:
        """Check if player can create another character in this guild."""
        guild = await self.guild_repo.get_by_guild_id(guild_id)
        char_count = await self.character_repo.count_by_player_and_guild(
            player_id, guild_id
        )

        if char_count >= guild.max_characters_per_player:
            return False, f"Max characters ({guild.max_characters_per_player}) reached."

        return True, ""
```

---

## Phase 4: Guild Onboarding Flow

### 4.1 Bot Invite & Setup

**OAuth2 Invite URL:**
```
https://discord.com/api/oauth2/authorize?
  client_id=YOUR_BOT_CLIENT_ID
  &permissions=8 (or specific permissions)
  &scope=bot%20applications.commands
  &guild_id={GUILD_ID}
```

**on_guild_join Event:**
```python
@commands.Cog.listener()
async def on_guild_join(self, guild: discord.Guild):
    """Handle bot being added to a new server."""
    self.logger.info(f"Bot added to guild: {guild.name} ({guild.id})")

    # Create guild record in database
    guild_repo = GuildRepository(self.postgres_manager)

    # Check if guild already exists
    existing = await guild_repo.get_by_guild_id(guild.id)
    if existing:
        self.logger.warning(f"Guild {guild.id} already exists, skipping setup")
        return

    # Create new guild with default free tier
    new_guild = await guild_repo.create(Guild(
        guild_id=guild.id,
        guild_name=guild.name,
        owner_discord_id=guild.owner_id,
        subscription_tier="free",
        subscription_status="trial",  # 7-day trial
        subscription_expires_at=datetime.now(UTC) + timedelta(days=7),
        max_game_sessions=2,
        max_players=25,
        max_characters_per_player=1,
        setup_completed=False,
    ))

    # Create default game settings for this guild
    settings_repo = GameSettingsRepository(self.postgres_manager)
    await settings_repo.create(GameSettings(guild_id=guild.id))

    # Send setup instructions to owner
    owner = guild.owner
    if owner:
        await self.send_setup_dm(owner, guild)

    # Post setup message in system channel
    if guild.system_channel:
        await self.send_setup_message(guild.system_channel)

async def send_setup_message(self, channel: discord.TextChannel):
    """Send setup instructions in the guild."""
    embed = discord.Embed(
        title="🎮 Welcome to Dystopian Sunset!",
        description="Thanks for adding me to your server! Let's get started.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Quick Setup",
        value=(
            "1️⃣ Run `/setup` to configure your server\n"
            "2️⃣ Choose your game theme (cyberpunk, fantasy, western)\n"
            "3️⃣ Create channels and roles automatically\n"
            "4️⃣ Start playing with `/join`!"
        ),
        inline=False
    )
    embed.add_field(
        name="Free Tier Includes:",
        value=(
            "✅ 2 simultaneous game sessions\n"
            "✅ Up to 25 players\n"
            "✅ 1 character per player\n"
            "✅ 7-day free trial"
        ),
        inline=False
    )
    embed.set_footer(text="Run /help for more commands | /upgrade for premium features")

    await channel.send(embed=embed)
```

### 4.2 Setup Wizard Command

```python
@app_commands.command(name="setup", description="Configure the bot for your server")
@app_commands.default_permissions(administrator=True)
async def setup(self, interaction: discord.Interaction):
    """Interactive setup wizard for guild admins."""
    guild_id = interaction.guild_id

    # Verify admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ You need Administrator permissions to run setup.",
            ephemeral=True
        )
        return

    # Create setup modal/view
    view = SetupWizardView(guild_id, self.postgres_manager)
    await interaction.response.send_message(
        "🔧 Let's configure Dystopian Sunset for your server!",
        view=view,
        ephemeral=True
    )

class SetupWizardView(discord.ui.View):
    """Multi-step setup wizard."""

    def __init__(self, guild_id: int, postgres_manager: PostgresManager):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.postgres_manager = postgres_manager
        self.step = 1

    @discord.ui.button(label="1. Choose Theme", style=discord.ButtonStyle.primary)
    async def step_theme(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Step 1: Choose game theme."""
        view = ThemeSelectionView(self.guild_id, self.postgres_manager)
        await interaction.response.send_message("Choose your game theme:", view=view, ephemeral=True)

    @discord.ui.button(label="2. Create Channels", style=discord.ButtonStyle.primary)
    async def step_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Step 2: Auto-create required channels and categories."""
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild

        # Create category
        category = await guild.create_category("🎮 Game Sessions")

        # Create join channel
        join_channel = await guild.create_text_channel(
            "join-to-play",
            category=category,
            topic="Click 'Join Game' to start playing!"
        )

        # Save to guild config
        guild_repo = GuildRepository(self.postgres_manager)
        await guild_repo.update_config(self.guild_id, {
            "session_category_id": category.id,
            "session_join_channel_id": join_channel.id,
        })

        await interaction.followup.send(
            f"✅ Created category **{category.name}** and channel {join_channel.mention}",
            ephemeral=True
        )

    @discord.ui.button(label="3. Create Roles", style=discord.ButtonStyle.primary)
    async def step_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Step 3: Create player role."""
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild

        # Check if role already exists
        player_role = discord.utils.get(guild.roles, name="Player")
        if not player_role:
            player_role = await guild.create_role(
                name="Player",
                color=discord.Color.blue(),
                mentionable=True
            )

        # Save to guild config
        guild_repo = GuildRepository(self.postgres_manager)
        await guild_repo.update_config(self.guild_id, {
            "player_role_id": player_role.id,
        })

        await interaction.followup.send(
            f"✅ Created role {player_role.mention}",
            ephemeral=True
        )

    @discord.ui.button(label="✅ Finish Setup", style=discord.ButtonStyle.success)
    async def finish_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mark setup as complete."""
        guild_repo = GuildRepository(self.postgres_manager)
        await guild_repo.mark_setup_complete(self.guild_id)

        await interaction.response.send_message(
            "🎉 Setup complete! Your server is ready to play. Use `/join` to start!",
            ephemeral=True
        )
```

---

## Phase 5: Subscription & Billing

### 5.1 Subscription Tiers

```python
class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"      # $5/month
    PREMIUM = "premium"  # $15/month
    ENTERPRISE = "enterprise"  # Custom pricing

TIER_LIMITS = {
    SubscriptionTier.FREE: {
        "max_game_sessions": 2,
        "max_players": 25,
        "max_characters_per_player": 1,
        "ai_model": "basic",  # Smaller/faster model
        "custom_prompts": False,
        "custom_themes": False,
        "priority_support": False,
    },
    SubscriptionTier.BASIC: {
        "max_game_sessions": 5,
        "max_players": 100,
        "max_characters_per_player": 3,
        "ai_model": "standard",
        "custom_prompts": True,
        "custom_themes": True,
        "priority_support": False,
    },
    SubscriptionTier.PREMIUM: {
        "max_game_sessions": 20,
        "max_players": 500,
        "max_characters_per_player": 10,
        "ai_model": "premium",  # Best quality model
        "custom_prompts": True,
        "custom_themes": True,
        "priority_support": True,
        "white_label": True,  # Custom bot name/avatar
    },
    SubscriptionTier.ENTERPRISE: {
        "max_game_sessions": -1,  # Unlimited
        "max_players": -1,
        "max_characters_per_player": -1,
        "ai_model": "custom",  # Custom fine-tuned model
        "custom_prompts": True,
        "custom_themes": True,
        "priority_support": True,
        "white_label": True,
        "dedicated_instance": True,
        "sla": True,
    },
}
```

### 5.2 Payment Integration (Stripe)

```python
class BillingService:
    """Handle subscription billing via Stripe."""

    def __init__(self, stripe_api_key: str):
        import stripe
        stripe.api_key = stripe_api_key
        self.stripe = stripe

    async def create_checkout_session(
        self,
        guild_id: int,
        tier: SubscriptionTier,
        discord_user_id: int
    ) -> str:
        """Create Stripe checkout session for subscription."""

        price_id = {
            SubscriptionTier.BASIC: "price_basic_monthly",
            SubscriptionTier.PREMIUM: "price_premium_monthly",
        }[tier]

        session = self.stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            success_url=f"https://yourdomain.com/success?guild_id={guild_id}",
            cancel_url=f"https://yourdomain.com/cancel?guild_id={guild_id}",
            metadata={
                "guild_id": str(guild_id),
                "discord_user_id": str(discord_user_id),
                "tier": tier.value,
            }
        )

        return session.url

    async def handle_webhook(self, webhook_data: dict):
        """Handle Stripe webhook events."""
        event_type = webhook_data["type"]

        if event_type == "checkout.session.completed":
            # Subscription activated
            await self.activate_subscription(webhook_data)

        elif event_type == "invoice.payment_failed":
            # Payment failed, suspend subscription
            await self.suspend_subscription(webhook_data)

        elif event_type == "customer.subscription.deleted":
            # Subscription cancelled
            await self.cancel_subscription(webhook_data)

@app_commands.command(name="upgrade", description="Upgrade your server's subscription")
@app_commands.default_permissions(administrator=True)
async def upgrade(self, interaction: discord.Interaction):
    """Show subscription upgrade options."""
    view = UpgradeView(interaction.guild_id, self.billing_service)

    embed = discord.Embed(
        title="⭐ Upgrade Your Server",
        description="Choose the plan that's right for your community:",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="💎 Basic ($5/month)",
        value=(
            "• 5 game sessions\n"
            "• 100 players\n"
            "• 3 characters per player\n"
            "• Custom prompts & themes"
        ),
        inline=True
    )

    embed.add_field(
        name="🌟 Premium ($15/month)",
        value=(
            "• 20 game sessions\n"
            "• 500 players\n"
            "• 10 characters per player\n"
            "• Best AI model\n"
            "• Priority support\n"
            "• White-label options"
        ),
        inline=True
    )

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
```

---

## Phase 6: Data Isolation & Security

### 6.1 Multi-Tenancy Strategy

**Database-Level Isolation:**
```python
# All queries MUST include guild_id filter
class BaseGuildScopedRepository(BaseRepository[T]):
    """Base repository with built-in guild scoping."""

    def __init__(self, postgres_manager: PostgresManager, guild_id: int):
        super().__init__(postgres_manager)
        self.guild_id = guild_id

    async def _add_guild_filter(self, stmt: Select) -> Select:
        """Automatically add guild_id filter to all queries."""
        return stmt.where(self.model_class.guild_id == self.guild_id)

    async def get_all(self) -> list[T]:
        """Get all records for this guild only."""
        async with self._with_session() as session:
            stmt = select(self.model_class)
            stmt = await self._add_guild_filter(stmt)
            result = await session.execute(stmt)
            return list(result.scalars().all())
```

### 6.2 Row-Level Security (PostgreSQL)

```sql
-- Enable RLS on all guild-scoped tables
ALTER TABLE game_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_memory ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their guild's data
CREATE POLICY guild_isolation_policy ON game_sessions
    FOR ALL
    USING (guild_id = current_setting('app.current_guild_id')::bigint);

-- Set guild context per connection
-- In Python: await session.execute(text(f"SET app.current_guild_id = {guild_id}"))
```

### 6.3 API Key Per Guild (for webhook/API access)

```python
class Guild(BaseSQLModel, table=True):
    # ... existing fields

    api_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="API key for webhook/external integrations"
    )
    api_key_enabled: bool = Field(default=False)

@app_commands.command(name="apikey", description="Manage your server's API key")
@app_commands.default_permissions(administrator=True)
async def apikey(self, interaction: discord.Interaction, action: str):
    """Generate/view/revoke API key for external integrations."""
    if action == "generate":
        new_key = secrets.token_urlsafe(32)
        await self.guild_repo.update_api_key(interaction.guild_id, new_key)
        await interaction.response.send_message(
            f"🔑 New API Key: `{new_key}`\n⚠️ **Save this! It won't be shown again.**",
            ephemeral=True
        )
```

---

## Phase 7: Performance & Scaling

### 7.1 Database Indexing Strategy

```sql
-- Critical indexes for multi-guild performance
CREATE INDEX idx_game_sessions_guild_id ON game_sessions(guild_id);
CREATE INDEX idx_game_sessions_guild_open ON game_sessions(guild_id, is_open)
    WHERE is_open = true;

CREATE INDEX idx_characters_guild_player ON characters(guild_id, player_id);
CREATE INDEX idx_session_memory_guild ON session_memory(guild_id);
CREATE INDEX idx_gm_history_guild_session ON gm_history(guild_id, game_session_id);

-- Composite indexes for common queries
CREATE INDEX idx_guilds_status ON guilds(subscription_status)
    WHERE subscription_status = 'active';
```

### 7.2 Caching Strategy

```python
class GuildCache:
    """Redis-based cache for guild settings and metadata."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.ttl = 300  # 5 minutes

    async def get_guild(self, guild_id: int) -> Guild | None:
        """Get guild from cache or database."""
        cache_key = f"guild:{guild_id}"

        cached = await self.redis.get(cache_key)
        if cached:
            return Guild.parse_raw(cached)

        # Fetch from database
        guild = await self.guild_repo.get_by_guild_id(guild_id)
        if guild:
            await self.redis.setex(
                cache_key,
                self.ttl,
                guild.json()
            )

        return guild

    async def invalidate_guild(self, guild_id: int):
        """Invalidate guild cache after updates."""
        await self.redis.delete(f"guild:{guild_id}")
```

### 7.3 Database Connection Pooling

```python
# Per-guild connection pools for high-traffic guilds
class MultiGuildPostgresManager:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.default_pool = self._create_pool()
        self.guild_pools: dict[int, AsyncEngine] = {}

    async def get_engine(self, guild_id: int | None = None) -> AsyncEngine:
        """Get database engine for guild (or default pool)."""
        if guild_id and guild_id in self.high_traffic_guilds:
            # Dedicated pool for high-traffic guilds
            if guild_id not in self.guild_pools:
                self.guild_pools[guild_id] = self._create_pool()
            return self.guild_pools[guild_id]

        return self.default_pool
```

### 7.4 Horizontal Scaling (Sharding)

For **very** large deployments:

```python
# Shard guilds across multiple database instances
def get_database_shard(guild_id: int) -> str:
    """Determine which database shard handles this guild."""
    shard_count = 4  # Number of database shards
    shard_index = guild_id % shard_count

    return f"postgresql://shard-{shard_index}.db.internal:5432/game"

class ShardedPostgresManager:
    def __init__(self, shard_urls: list[str]):
        self.engines = {
            i: create_async_engine(url)
            for i, url in enumerate(shard_urls)
        }

    def get_engine(self, guild_id: int) -> AsyncEngine:
        shard_index = guild_id % len(self.engines)
        return self.engines[shard_index]
```

---

## Phase 8: Monitoring & Analytics

### 8.1 Per-Guild Metrics

```python
# Extend metrics service with guild_id labels
class MetricsService:
    def record_game_session_created(self, guild_id: int):
        self.game_sessions_total.labels(
            guild_id=str(guild_id),
            action="created"
        ).inc()

    def record_ai_request(self, guild_id: int, model: str, duration: float):
        self.ai_requests_total.labels(
            guild_id=str(guild_id),
            model=model
        ).inc()

        self.ai_request_duration.labels(
            guild_id=str(guild_id),
            model=model
        ).observe(duration)
```

### 8.2 Usage-Based Billing Metrics

```python
class UsageTracker:
    """Track usage for billing purposes."""

    async def record_ai_tokens(self, guild_id: int, tokens: int):
        """Track AI token usage for potential usage-based billing."""
        await self.redis.hincrby(
            f"usage:{guild_id}:{datetime.now().strftime('%Y-%m')}",
            "ai_tokens",
            tokens
        )

    async def get_monthly_usage(self, guild_id: int) -> dict:
        """Get usage statistics for current month."""
        key = f"usage:{guild_id}:{datetime.now().strftime('%Y-%m')}"
        return await self.redis.hgetall(key)
```

---

## Phase 9: Admin Dashboard (Web Interface)

### 9.1 Guild Admin Panel

**Features:**
- View subscription status & billing
- Configure game settings without Discord commands
- View analytics (player count, session activity)
- Manage custom prompts/themes
- View usage quotas
- Support ticket system

**Tech Stack:**
- **Backend:** FastAPI (Python) - shares code with Discord bot
- **Frontend:** React + TypeScript
- **Auth:** Discord OAuth2
- **Database:** Same PostgreSQL instance

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer

app = FastAPI()

# Discord OAuth2 for authentication
@app.get("/api/guilds/me")
async def get_my_guilds(user: DiscordUser = Depends(get_current_user)):
    """Get guilds where user is admin and bot is installed."""
    # Fetch from Discord API
    user_guilds = await discord_api.get_user_guilds(user.access_token)

    # Filter to guilds with admin perms and bot installed
    admin_guilds = [
        g for g in user_guilds
        if (int(g["permissions"]) & 0x8) == 0x8  # ADMINISTRATOR
    ]

    # Check which have bot installed
    guild_repo = GuildRepository(postgres_manager)
    installed_guild_ids = await guild_repo.get_guild_ids()

    return [
        g for g in admin_guilds
        if int(g["id"]) in installed_guild_ids
    ]

@app.get("/api/guilds/{guild_id}/settings")
async def get_guild_settings(
    guild_id: int,
    user: DiscordUser = Depends(require_guild_admin)
):
    """Get guild configuration."""
    guild = await guild_repo.get_by_guild_id(guild_id)
    settings = await settings_repo.get_by_guild_id(guild_id)

    return {
        "guild": guild,
        "settings": settings,
        "subscription": {
            "tier": guild.subscription_tier,
            "status": guild.subscription_status,
            "expires_at": guild.subscription_expires_at,
        }
    }

@app.post("/api/guilds/{guild_id}/settings")
async def update_guild_settings(
    guild_id: int,
    settings: GameSettingsUpdate,
    user: DiscordUser = Depends(require_guild_admin)
):
    """Update guild game settings."""
    updated = await settings_repo.update(guild_id, settings)

    # Invalidate cache
    await guild_cache.invalidate_guild(guild_id)

    return updated
```

---

## Summary: Migration Checklist

### Database
- [ ] Create `guilds` table
- [ ] Add `guild_id` to all models
- [ ] Create migration scripts for existing data
- [ ] Add indexes for `guild_id`
- [ ] Implement Row-Level Security (optional)

### Bot Code
- [ ] Refactor repositories to require `guild_id`
- [ ] Add guild context injection to all commands
- [ ] Implement `on_guild_join` / `on_guild_remove` events
- [ ] Create setup wizard (`/setup` command)
- [ ] Add quota enforcement service
- [ ] Implement per-guild configuration system

### Billing
- [ ] Integrate Stripe (or payment provider)
- [ ] Define subscription tiers
- [ ] Create `/upgrade` command
- [ ] Implement webhook handlers for payment events
- [ ] Add trial period logic

### Infrastructure
- [ ] Setup database connection pooling
- [ ] Add Redis caching layer
- [ ] Configure per-guild metrics
- [ ] Setup monitoring dashboards
- [ ] Implement rate limiting

### Web Dashboard
- [ ] Create FastAPI backend
- [ ] Implement Discord OAuth2 authentication
- [ ] Build React admin panel
- [ ] Add billing management UI

### Testing
- [ ] Unit tests for guild-scoped queries
- [ ] Integration tests for multi-guild scenarios
- [ ] Load testing with multiple guilds
- [ ] Security audit for data isolation

### Documentation
- [ ] Update bot invite instructions
- [ ] Create setup guide for server owners
- [ ] Document subscription tiers
- [ ] API documentation for webhooks

### Legal/Compliance
- [ ] Privacy policy (GDPR compliance)
- [ ] Terms of Service
- [ ] Data retention policy
- [ ] DMCA/content moderation policy

---

## Estimated Timeline

- **Phase 1 (Database):** 2-3 weeks
- **Phase 2 (Configuration):** 1 week
- **Phase 3 (Bot Logic):** 3-4 weeks
- **Phase 4 (Onboarding):** 2 weeks
- **Phase 5 (Billing):** 2-3 weeks
- **Phase 6 (Security):** 1-2 weeks
- **Phase 7 (Performance):** 2 weeks
- **Phase 8 (Monitoring):** 1 week
- **Phase 9 (Dashboard):** 4-6 weeks
- **Testing & QA:** 2-3 weeks

**Total:** ~4-6 months for full SaaS transformation

---

## Risks & Considerations

1. **Data Migration:** Existing single-guild deployment needs careful migration
2. **Breaking Changes:** Major refactor will break existing deployment
3. **Cost:** AI API costs scale with number of guilds
4. **Support:** Multi-tenant = more support requests
5. **Performance:** Need to ensure queries scale with guild count
6. **Competition:** Discord bot SaaS market is competitive
7. **Compliance:** Privacy laws (GDPR, CCPA) for user data

---

## Recommended First Steps

1. **Proof of Concept:** Add `guild_id` to 2-3 core models and test multi-guild queries
2. **Setup Wizard:** Implement basic `/setup` command before full migration
3. **Billing Integration:** Get Stripe working with test subscriptions
4. **Gradual Rollout:** Deploy to a test Discord server before opening to public
5. **Monitor Metrics:** Track performance impact of guild scoping early

---

*This plan provides a comprehensive roadmap for transforming the bot into a scalable SaaS offering. Adjust timeline and priorities based on resources and business goals.*
