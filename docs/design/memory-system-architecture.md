# Memory System Architecture
## Quillian Undercity: Shadows of the Syndicate

**Version:** 1.0  
**Last Updated:** December 24, 2025  
**Status:** Design Phase

---

## Executive Summary

The memory system provides a three-tiered architecture for managing narrative persistence in a Discord-based RPG. It transforms raw gameplay events into permanent world lore through AI-powered processing, ensuring that player actions have lasting consequences while maintaining scalability.

### Key Principles

1. **Character-Centric Design**: Memory follows characters, not players
2. **Automatic Importance Scoring**: AI determines what matters
3. **Semantic Search**: Find relevant context through meaning, not keywords
4. **Graceful Degradation**: Old memories expire to maintain performance
5. **Type Safety**: All AI outputs are validated Pydantic models

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY LIFECYCLE                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SESSION MEMORY (1-4 hours)                         │   │
│  │  • Raw events, dialogue, actions                     │   │
│  │  • Real-time importance scoring                      │   │
│  │  • Player-specific context                           │   │
│  │  • Auto-expires after processing                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│              [Pydantic AI: Episode Agent]                    │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  EPISODE MEMORY (24-72 hours)                       │   │
│  │  • Condensed narrative summaries                     │   │
│  │  • Key moments extraction                            │   │
│  │  • Relationship tracking                             │   │
│  │  • Semantic embeddings                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│        [Pydantic AI: World Memory Agent]                     │
│                           ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  WORLD MEMORY (Permanent)                           │   │
│  │  • Significant events & characters                   │   │
│  │  • Location lore & history                           │   │
│  │  • Faction dynamics                                  │   │
│  │  • Discoverable secrets                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies
- **Database**: PostgreSQL 16+ with pgvector extension
- **ML Framework**: Pydantic AI (type-safe AI agents)
- **Embeddings**: OpenAI text-embedding-3-small
- **LLM**: GPT-4 Turbo / GPT-4o
- **Language**: Python 3.13
- **Async Framework**: asyncio + asyncpg

### Extensions Required
```sql
CREATE EXTENSION IF NOT EXISTS vector;   -- Semantic search
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Fuzzy text search
```

---

## Database Schema

### Memory Tables

#### 1. Session Memories (Ephemeral)
```sql
CREATE TABLE session_memories (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    character_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    memory_type VARCHAR(50),  -- 'dialogue', 'action', 'observation'
    content JSONB NOT NULL,
    participants UUID[],
    location_id UUID,
    
    -- AI-generated metadata
    importance_score FLOAT,      -- 0.0 to 1.0
    emotional_valence FLOAT,     -- -1.0 to 1.0
    tags TEXT[],
    
    expires_at TIMESTAMPTZ,
    processed BOOLEAN DEFAULT FALSE
);
```

**Purpose**: Capture raw events during active gameplay  
**Retention**: 4 hours after session ends  
**Size Estimate**: ~1KB per event, ~500 events/session  

#### 2. Episode Memories (Short-term)
```sql
CREATE TABLE episode_memories (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,  -- 24-72 hours
    
    -- Narrative content
    title VARCHAR(255),
    summary TEXT,
    one_sentence_summary TEXT,
    key_moments JSONB[],
    relationships_changed JSONB,
    themes TEXT[],
    cliffhangers TEXT[],
    
    -- References
    characters UUID[],
    locations UUID[],
    session_ids UUID[],
    
    -- Semantic search
    embedding vector(1536),
    importance_score FLOAT,
    promoted_to_world BOOLEAN DEFAULT FALSE
);
```

**Purpose**: Condensed narrative summaries of sessions  
**Retention**: 48 hours unless promoted  
**Size Estimate**: ~5-10KB per episode  

#### 3. World Memories (Permanent)
```sql
CREATE TABLE world_memories (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    memory_category VARCHAR(50),  -- 'event', 'character', 'location', 'faction'
    
    title VARCHAR(255),
    description TEXT,           -- Concise (50-500 chars)
    full_narrative TEXT,        -- Rich detail (200-3000 chars)
    
    related_entities JSONB,     -- {characters: [], locations: [], factions: []}
    source_episodes UUID[],
    consequences TEXT[],
    
    embedding vector(1536),
    tags TEXT[],
    impact_level VARCHAR(20),   -- 'minor', 'moderate', 'major', 'world_changing'
    
    -- Discovery system
    is_public BOOLEAN,
    discovery_requirements JSONB
);
```

**Purpose**: Permanent historical record  
**Retention**: Forever (or until GM explicitly removes)  
**Size Estimate**: ~10-20KB per entry  

#### 4. Character Recognition
```sql
CREATE TABLE character_recognition (
    id UUID PRIMARY KEY,
    character_id UUID NOT NULL,       -- Observer
    known_character_id UUID NOT NULL, -- Known character
    
    first_met_at TIMESTAMPTZ,
    last_interaction_at TIMESTAMPTZ,
    
    known_name VARCHAR(255),
    known_details JSONB,
    relationship_type VARCHAR(50),
    trust_level FLOAT,
    
    shared_episodes UUID[],
    
    UNIQUE (character_id, known_character_id)
);
```

**Purpose**: Track what each character knows about others  
**Key Feature**: Enables realistic NPC dialogue  

---

## Pydantic AI Agent System

### Agent Architecture

```python
# Core agents for memory processing
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

gpt4_model = OpenAIModel('gpt-4-turbo-preview')
gpt4o_model = OpenAIModel('gpt-4o')
```

### 1. Importance Scoring Agent

**Model**: GPT-4o (fast)  
**Output**: `ImportanceAnalysis` (validated Pydantic model)

```python
@dataclass
class ImportanceAnalysis:
    score: float              # 0.0 to 1.0
    reasoning: str            # Why this score
    should_promote: bool      # Promote to world memory?
    tags: List[str]
    emotional_valence: EmotionalValence
```

**Triggers**:
- Real-time during event capture
- Analyzes significance within 100-200ms

**Scoring Criteria**:
- 0.7-1.0: Major plot revelations, world state changes
- 0.4-0.6: Character development, quest completion
- 0.0-0.3: Routine actions, trivial dialogue

### 2. Episode Summarization Agent

**Model**: GPT-4 Turbo (creative writing)  
**Output**: `EpisodeSummary` (validated Pydantic model)

```python
@dataclass
class EpisodeSummary:
    title: str                           # 5-100 chars
    one_sentence_summary: str            # Quick reference
    narrative_summary: str               # 2-3 paragraphs
    key_moments: List[KeyMoment]         # 1-10 moments
    relationships_changed: List[RelationshipChange]
    themes: List[str]
    cliffhangers: List[str]
```

**Triggers**:
- When session ends
- Processes all session memories chronologically

**Style**: Third-person omniscient, noir cyberpunk tone

### 3. World Memory Promotion Agent

**Model**: GPT-4 Turbo (high-quality lore)  
**Output**: `WorldNarrative` (validated Pydantic model)

```python
@dataclass
class WorldNarrative:
    title: str                    # 5-150 chars
    description: str              # Concise (50-500)
    full_narrative: str           # Rich detail (200-3000)
    related_entities: Dict[str, List[str]]
    tags: List[str]
    impact_level: ImpactLevel
    is_public: bool
    discovery_requirements: Optional[Dict]
    consequences: List[str]
```

**Triggers**:
- High importance episodes (>0.75)
- Manual GM promotion
- Faction-changing events

**Responsibilities**:
- Establish canonical facts
- Identify ripple effects
- Create future story hooks
- Maintain lore consistency

### 4. Character Recognition Agent

**Model**: GPT-4o (relationship analysis)  
**Output**: `CharacterKnowledge` (validated Pydantic model)

```python
@dataclass
class CharacterKnowledge:
    known_name: str
    known_aliases: List[str]
    known_details: Dict[str, Any]
    relationship_summary: str
    trust_level: float            # 0.0 to 1.0
    last_known_location: Optional[str]
    rumors_heard: List[str]
```

**Triggers**:
- After episode condensation
- When characters interact

**Key Feature**: Distinguishes between fact, belief, and rumor

### 5. Location Lore Agent

**Model**: GPT-4 Turbo (world-building)  
**Output**: `LocationLore` (validated Pydantic model)

**Triggers**:
- Significant events at location
- Periodic lore enrichment

---

## Data Flow & Processing

### Event Capture Flow

```
Player Action
     ↓
Discord Command
     ↓
Game Master Service
     ↓
capture_session_event()
     ↓
[Importance Agent] ← Analyzes in real-time
     ↓
PostgreSQL: session_memories
     ↓
Returns memory_id to GM
```

**Performance Target**: <300ms total

### Session End Flow

```
Session Ends
     ↓
condense_session_to_episode()
     ↓
Fetch all session_memories (sorted by timestamp)
     ↓
[Episode Agent] ← Generates narrative summary
     ↓
Generate embedding (semantic search)
     ↓
Extract unique characters/locations
     ↓
Store in episode_memories
     ↓
[Recognition Agent] ← Update character relationships
     ↓
Mark session_memories as processed
     ↓
Return episode_id
```

**Performance Target**: 5-15 seconds

### World Memory Promotion Flow

```
High-importance episode OR manual GM decision
     ↓
promote_to_world_memory()
     ↓
Fetch episode(s) and related context
     ↓
[World Memory Agent] ← Generate canonical narrative
     ↓
Generate embedding
     ↓
Store in world_memories
     ↓
Mark episodes as promoted
     ↓
Update location lore if applicable
     ↓
Return world_memory_id
```

**Performance Target**: 10-30 seconds

---

## Semantic Search System

### Vector Similarity Search

Uses **pgvector** for efficient similarity queries:

```sql
-- Find similar world memories
SELECT *,
    1 - (embedding <=> $1::vector) as similarity
FROM world_memories
WHERE is_public = TRUE
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

### Indexing Strategy

```sql
-- IVFFlat index for faster approximate search
CREATE INDEX idx_world_embedding 
ON world_memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- For episode memories
CREATE INDEX idx_episode_embedding 
ON episode_memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);
```

### Embedding Generation

**Model**: `text-embedding-3-small`
- Cost: $0.02 per 1M tokens
- Dimensions: 1536
- Quality: High for similarity search

**Caching Strategy**:
```python
class EmbeddingGenerator:
    async def generate(self, text: str) -> List[float]:
        # Check Redis cache first (30-day TTL)
        cache_key = f"embedding:{sha256(text)}"
        if cached := await redis.get(cache_key):
            return json.loads(cached)
        
        # Generate and cache
        embedding = await openai.embeddings.create(...)
        await redis.setex(cache_key, 86400*30, embedding)
        return embedding
```

---

## Scalability Considerations

### Data Volume Projections

**Assumptions**:
- 100 active players
- 3 sessions/week per player
- 2-hour sessions with 500 events each

#### Storage Growth (per year)
```
Session Memories:
  100 players × 3 sessions × 52 weeks × 500 events × 1KB
  = ~7.8 GB/year (but expires after 4 hours)
  
Episode Memories:
  100 players × 3 sessions × 52 weeks × 10KB
  = ~156 MB/year (expires after 48 hours unless promoted)
  
World Memories:
  ~10-20% promotion rate
  15,600 episodes × 20% × 15KB
  = ~47 MB/year (permanent)
```

**Conclusion**: Scalability is manageable due to aggressive expiration

### Partitioning Strategy

For high-volume deployments:

```sql
-- Partition session_memories by month
CREATE TABLE session_memories (
    ...
) PARTITION BY RANGE (timestamp);

-- Automatic partition creation
CREATE TABLE session_memories_2025_01 
PARTITION OF session_memories
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

**Benefits**:
- Faster queries (partition pruning)
- Easier data archival
- Parallel processing

### Cleanup Jobs

```python
# Background task: runs every hour
async def cleanup_expired_memories():
    deleted_sessions = await db.execute("""
        DELETE FROM session_memories
        WHERE expires_at < NOW() AND processed = TRUE
    """)
    
    deleted_episodes = await db.execute("""
        DELETE FROM episode_memories
        WHERE expires_at < NOW() AND promoted_to_world = FALSE
    """)
```

### Caching Strategy

**Redis Layer**:
- World memories: 1-hour cache
- Episode summaries: 15-minute cache
- Character recognition: 30-minute cache
- Embeddings: 30-day cache

**Cache Keys**:
```
world_memory:{uuid}
episode_memory:{uuid}
character_recognition:{char_id}:{known_char_id}
embedding:text-embedding-3-small:{sha256}
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- [ ] PostgreSQL setup with pgvector
- [ ] Core Pydantic models
- [ ] Session memory capture
- [ ] Basic importance scoring
- [ ] Database schema implementation

**Deliverables**:
- Working session memory capture
- Real-time importance analysis
- Basic database queries

### Phase 2: Episode System (Weeks 3-4)
- [ ] Episode summarization agent
- [ ] Character recognition system
- [ ] Embedding generation
- [ ] Episode expiration cleanup
- [ ] Relationship tracking

**Deliverables**:
- Automated episode creation on session end
- Character relationship updates
- Semantic search preparation

### Phase 3: World Memory (Weeks 5-6)
- [ ] World memory promotion agent
- [ ] Location lore generation
- [ ] Discovery system
- [ ] Semantic search queries
- [ ] Promotion criteria logic

**Deliverables**:
- Permanent world memory creation
- Rich location lore
- Working semantic search

### Phase 4: Optimization (Weeks 7-8)
- [ ] Redis caching layer
- [ ] Database indexing tuning
- [ ] Partitioning implementation
- [ ] Performance monitoring
- [ ] Load testing

**Deliverables**:
- Sub-second memory retrieval
- Efficient embedding caching
- Scalability validation

---

## Key Design Decisions

### 1. Character-Centric Memory
**Decision**: Memory follows characters, not players  
**Rationale**: 
- Supports proper roleplaying boundaries
- Enables multiple characters per player
- NPCs remember specific character identities
- Faction standings are character-specific

### 2. Three-Tier Architecture
**Decision**: Session → Episode → World hierarchy  
**Rationale**:
- Balances detail with scalability
- Natural expiration prevents bloat
- Progressive summarization maintains quality
- AI costs controlled through selective promotion

### 3. Pydantic AI for All ML
**Decision**: Use Pydantic AI library exclusively  
**Rationale**:
- Type-safe AI outputs
- Validated structured responses
- Easier testing and debugging
- Consistent error handling
- Future LLM provider flexibility

### 4. Automatic Importance Scoring
**Decision**: AI scores every event in real-time  
**Rationale**:
- Removes GM cognitive load
- Consistent evaluation criteria
- Enables automated promotion
- Provides metadata for future queries

### 5. Semantic Search Over Keywords
**Decision**: Vector embeddings for memory retrieval  
**Rationale**:
- Context-aware memory recall
- Handles synonyms and concepts
- Mimics human memory associations
- Enables "fuzzy" lore discovery

---

## API Examples

### Capturing an Event

```python
from services.memory.memory_processor import MemoryProcessor
from services.memory.models import MemoryType

# During gameplay
memory_id = await memory_processor.capture_session_event(
    session_id=session.id,
    character_id=character.id,
    memory_type=MemoryType.ACTION,
    content={
        "action": "hack_terminal",
        "target": "SynCorp Database",
        "success": True,
        "data_stolen": ["employee_records", "financial_data"]
    },
    participants=[npc_guard.id],
    location_id=syncorp_hq.id
)

# AI automatically scores importance and tags the event
```

### Ending a Session

```python
# When session concludes
episode_id = await memory_processor.condense_session_to_episode(
    session_id=session.id
)

# Returns structured EpisodeSummary with:
# - Narrative title and summary
# - Key moments extracted
# - Relationship changes identified
# - Themes and cliffhangers noted
```

### Retrieving Context for GM

```python
# Before generating NPC dialogue
context = await memory_retriever.get_relevant_context(
    character_id=npc.id,
    location_id=current_location.id,
    query="previous encounters with the player"
)

# Returns:
# - Recent episodes involving this NPC
# - What they know about player characters
# - Location-specific lore
# - Semantically similar world events
```

---

## Testing Strategy

### Unit Tests
- Pydantic model validation
- Individual agent outputs
- Database query logic
- Embedding generation

### Integration Tests
- Full event capture → episode flow
- Episode → world promotion
- Character recognition updates
- Semantic search accuracy

### Performance Tests
- Event capture latency (<300ms)
- Episode generation time (<15s)
- Memory retrieval speed (<100ms)
- Embedding cache hit rate (>80%)

### AI Quality Tests
```python
# Validate importance scoring consistency
test_events = load_test_fixtures()
for event in test_events:
    analysis = await analyze_event_importance(event)
    assert 0.0 <= analysis.score <= 1.0
    assert len(analysis.reasoning) > 20
    assert len(analysis.tags) > 0

# Validate narrative quality
episode = await generate_episode_summary(session_memories)
assert len(episode.title) >= 5
assert len(episode.narrative_summary) >= 100
assert len(episode.key_moments) >= 1
```

---

## Monitoring & Observability

### Key Metrics

**Performance**:
- Event capture latency (p50, p95, p99)
- Episode generation time
- Memory retrieval speed
- Embedding cache hit rate

**AI Quality**:
- Importance score distribution
- Episode promotion rate
- Character recognition accuracy
- User satisfaction ratings

**Storage**:
- Session memory growth rate
- Episode memory count
- World memory growth
- Database size

**Cost**:
- API calls per day
- Token consumption
- Embedding generation cost
- Monthly AI spend

### Logging Strategy

```python
import structlog

logger = structlog.get_logger()

# Log every important event
logger.info(
    "episode_created",
    episode_id=episode_id,
    session_id=session_id,
    importance_score=avg_importance,
    key_moments_count=len(summary.key_moments),
    generation_time_ms=elapsed_ms
)
```

---

## Future Enhancements

### Short-term (3-6 months)
- [ ] Multi-modal memories (images, audio)
- [ ] Cross-episode story arc tracking
- [ ] Automated lore consistency checking
- [ ] Player memory search interface

### Medium-term (6-12 months)
- [ ] Faction memory systems
- [ ] Rumor propagation networks
- [ ] Dynamic world event generation
- [ ] Memory-based quest generation

### Long-term (12+ months)
- [ ] Player-authored world memories
- [ ] Collaborative storytelling features
- [ ] Memory export/import (campaign sharing)
- [ ] Advanced analytics dashboard

---

## Conclusion

This memory system architecture provides a robust, scalable foundation for persistent narrative in Quillian Undercity. By leveraging Pydantic AI for type-safe structured outputs and PostgreSQL with pgvector for semantic search, we achieve:

1. **Automatic importance evaluation** reducing GM workload
2. **Rich narrative preservation** through AI summarization
3. **Character-aware context** for realistic NPC interactions
4. **Scalable storage** through intelligent expiration
5. **Semantic discovery** of relevant lore and connections

The three-tier architecture (Session → Episode → World) balances detail retention with performance, while Pydantic AI ensures type safety and consistency across all ML operations.

**Next Steps**:
1. Implement Phase 1 (database schema + session capture)
2. Develop core Pydantic models and agents
3. Build automated testing suite
4. Deploy to staging environment
5. Iterate based on real gameplay data

---

## References

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [PostgreSQL Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-24 | System Design | Initial architecture proposal |
