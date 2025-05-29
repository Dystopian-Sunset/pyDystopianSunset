-- Define Namespace and Database and use them
DEFINE NAMESPACE IF NOT EXISTS ds_qu_shadows;
USE NS ds_qu_shadows;

DEFINE USER IF NOT EXISTS bot ON NAMESPACE PASSWORD "discord" ROLES EDITOR;

-- Define Database and use it
DEFINE DATABASE IF NOT EXISTS game;
USE DB game;

-- Game Settings Table
DEFINE TABLE IF NOT EXISTS game_settings SCHEMALESS TYPE NORMAL;

-- Player Table
DEFINE TABLE IF NOT EXISTS player SCHEMAFULL TYPE NORMAL;

DEFINE FIELD IF NOT EXISTS global_name ON player TYPE string COMMENT "Discord player global name";
DEFINE FIELD IF NOT EXISTS display_name ON player TYPE string COMMENT "Discord player display name";
DEFINE FIELD IF NOT EXISTS display_avatar ON player TYPE string COMMENT "Discord player display avatar URL";
DEFINE FIELD IF NOT EXISTS joined_at ON player TYPE datetime COMMENT "Player joined at";
DEFINE FIELD IF NOT EXISTS last_active ON player TYPE datetime COMMENT "Player last active";
DEFINE FIELD IF NOT EXISTS is_active ON player TYPE bool DEFAULT true COMMENT "Player is active";
DEFINE FIELD IF NOT EXISTS is_banned ON player TYPE bool DEFAULT false COMMENT "Player is banned";

-- Character Table
DEFINE TABLE IF NOT EXISTS character SCHEMAFULL TYPE NORMAL;

DEFINE FIELD IF NOT EXISTS name ON character TYPE string COMMENT "Character name";
DEFINE FIELD IF NOT EXISTS level ON character TYPE int DEFAULT 1 COMMENT "Character level";
DEFINE FIELD IF NOT EXISTS exp ON character TYPE int DEFAULT 0 COMMENT "Character experience";
DEFINE FIELD OVERWRITE credits ON character TYPE int DEFAULT 0 COMMENT "Character monatary credits";
DEFINE FIELD OVERWRITE stats ON character FLEXIBLE TYPE object COMMENT "Character stats";
DEFINE FIELD OVERWRITE effects ON character FLEXIBLE TYPE object COMMENT "Effects are temporary modifiers to stats";
DEFINE FIELD OVERWRITE renown ON character TYPE int COMMENT "Character renown";
DEFINE FIELD OVERWRITE shadow_level ON character TYPE int COMMENT "Character shadow level";
DEFINE FIELD OVERWRITE created_at ON character TYPE datetime DEFAULT time::now() COMMENT "Character created at";
DEFINE FIELD OVERWRITE last_active ON character TYPE datetime DEFAULT time::now() COMMENT "Character last active";

DEFINE INDEX IF NOT EXISTS idx_character_name ON TABLE character FIELDS name UNIQUE COMMENT "Character name index";

-- Relationship between Player and Character
DEFINE TABLE IF NOT EXISTS player_has_character TYPE RELATION FROM player TO character ENFORCED;
DEFINE TABLE OVERWRITE player_is_playing_as TYPE RELATION FROM player TO character;

-- Character Class Table
DEFINE TABLE OVERWRITE character_class SCHEMAFULL PERMISSIONS FOR create, update, delete WHERE $auth.admin = true TYPE NORMAL;

DEFINE FIELD IF NOT EXISTS name ON character_class TYPE string COMMENT "Character class name";
DEFINE FIELD IF NOT EXISTS description ON character_class TYPE string COMMENT "Character class description";
DEFINE FIELD IF NOT EXISTS emoji ON character_class TYPE string COMMENT "Character class emoji";

-- Character Classes
INSERT IGNORE INTO character_class {id: 1, name: "Enforcer", description: "A physically imposing character who handles the physical aspects of maintaining order within the organization. This character could be designed with a robust, tank-like build and might feature visible cybernetic enhancements that augment their strength and durability.", emoji: "🛡️"};
INSERT IGNORE INTO character_class {id: 2, name: "Tech Wizard", description: "A master of technology and hacking, this character supports the organization by manipulating cyber systems, gathering information, and controlling communication. They could have a more wiry build with tools and tech gadgets integrated into their attire.", emoji: "💻"};
INSERT IGNORE INTO character_class {id: 3, name: "Smooth Talker", description: "This character is the face of the organization for negotiations and dealings with other factions. Charismatic and clever, they can manipulate situations to their favor. Their design might include stylish, sleek clothing that reflects their charisma and social prowess. ", emoji: "💬"};
INSERT IGNORE INTO character_class {id: 4, name: "Spy", description: "Stealthy and elusive, this character specializes in gathering intelligence and carrying out covert operations. They could be depicted with a mysterious, cloaked appearance, equipped with gadgets for espionage.", emoji: "🕵️"};
INSERT IGNORE INTO character_class {id: 5, name: "Wild Card", description: "Unpredictable and volatile, this character adds an element of surprise and unpredictability. Their appearance could be eccentric, with mismatched cybernetics and colorful attire, reflecting their unpredictable nature.", emoji: "🃏"};

-- Relationship between Character and Character Class
DEFINE TABLE OVERWRITE has_class TYPE RELATION FROM character TO character_class;

-- Character Stats Table
DEFINE TABLE OVERWRITE character_stats SCHEMAFULL PERMISSIONS FOR create, update, delete WHERE $auth.admin = true TYPE NORMAL;

DEFINE FIELD IF NOT EXISTS name ON character_stats TYPE string COMMENT "Character stat name";
DEFINE FIELD IF NOT EXISTS abbr ON character_stats TYPE string COMMENT "Character stat abbreviation";
DEFINE FIELD IF NOT EXISTS description ON character_stats TYPE string COMMENT "Character stat description";
DEFINE FIELD IF NOT EXISTS emoji ON character_stats TYPE string COMMENT "Character stat emoji";
DEFINE FIELD IF NOT EXISTS max_value ON character_stats TYPE int COMMENT "Character stat maximum value";
DEFINE FIELD IF NOT EXISTS is_primary ON character_stats TYPE bool COMMENT "Character stat is primary";
DEFINE FIELD IF NOT EXISTS is_mutable ON character_stats TYPE bool COMMENT "Character stat is mutable";

-- Character Stats
INSERT IGNORE INTO character_stats { id: 1, name: "Strength", abbr: "STR", description: "This measures the physical power of a character. It is essential for characters like the Enforcer, who rely on melee strength to overpower foes.", emoji: "💪", max_value: 100, is_primary: true, is_mutable: true};
INSERT IGNORE INTO character_stats { id: 2, name: "Dexterity", abbr: "DEX", description: "This stat reflects agility, reflexes, and balance. It is crucial for classes such as the Spy, who must perform stealthy movements, and also impacts the effectiveness of ranged attacks, making it important for the Wild Card as well.", emoji: "🤸‍♀️", max_value: 100, is_primary: true, is_mutable: true};
INSERT IGNORE INTO character_stats { id: 3, name: "Intellect", abbr: "INT", description: " Intellect governs reasoning, memory, and the ability to understand complex systems, making it a key stat for the Tech Wizard. This stat would also influence abilities related to technology manipulation, hacking, and understanding complex machinery or systems.", emoji: "🧠", max_value: 100, is_primary: true, is_mutable: true};
INSERT IGNORE INTO character_stats { id: 4, name: "Charisma", abbr: "CHA", description: "Charisma represents a character's social skills, including the ability to persuade, lead, and influence others. It is particularly vital for the Smooth Talker, who navigates political landscapes and manipulates others to achieve their goals.", emoji: "🤝", max_value: 100, is_primary: true, is_mutable: true};
INSERT IGNORE INTO character_stats { id: 5, name: "Perception", abbr: "PER", description: "This stat encompasses awareness, intuition, and insight, helping characters to notice hidden details, read social cues, and often get a sense of their surroundings faster than others. It's crucial for the Spy for gathering intelligence and for the Wild Card whose adaptability can benefit from good situational awareness.", emoji: "👁️", max_value: 100, is_primary: true, is_mutable: true};
INSERT IGNORE INTO character_stats { id: 6, name: "Luck", abbr: "LUK", description: "Luck represents a character's ability to get lucky or avoid bad luck. It can impact various aspects of their experience, such as avoiding traps, landing on good deals, or getting unexpected assistance.", emoji: "🍀", max_value: 100, is_primary: true, is_mutable: false};

-- Relationship of Character Class to Stats
DEFINE TABLE OVERWRITE has_class_stat TYPE RELATION FROM character_class TO character_stats;

-- Insert class -> stats relationships
INSERT RELATION INTO has_class_stat { in: character_class:1, out: character_stats:1 }; -- Strength (Enforcer)
INSERT RELATION INTO has_class_stat { in: character_class:1, out: character_stats:2 }; -- Dexterity (Enforcer)
INSERT RELATION INTO has_class_stat { in: character_class:2, out: character_stats:3 }; -- Intellect (Tech Wizard)
INSERT RELATION INTO has_class_stat { in: character_class:2, out: character_stats:2 }; -- Dexterity (Tech Wizard)
INSERT RELATION INTO has_class_stat { in: character_class:3, out: character_stats:4 }; -- Charisma (Smooth Talker)
INSERT RELATION INTO has_class_stat { in: character_class:3, out: character_stats:3 }; -- Intelect (Smooth Talker)
INSERT RELATION INTO has_class_stat { in: character_class:4, out: character_stats:2 }; -- Dexterity (Spy)
INSERT RELATION INTO has_class_stat { in: character_class:4, out: character_stats:5 }; -- Perception (Spy)
INSERT RELATION INTO has_class_stat { in: character_class:5, out: character_stats:1 }; -- Strength (Wild Card)
INSERT RELATION INTO has_class_stat { in: character_class:5, out: character_stats:2 }; -- Dexterity (Wild Card)
INSERT RELATION INTO has_class_stat { in: character_class:5, out: character_stats:3 }; -- Intellect (Wild Card)
INSERT RELATION INTO has_class_stat { in: character_class:5, out: character_stats:4 }; -- Charisma (Wild Card)
INSERT RELATION INTO has_class_stat { in: character_class:5, out: character_stats:5 }; -- Perception (Wild Card);

-- Game Session Table
DEFINE TABLE IF NOT EXISTS game_session SCHEMALESS TYPE NORMAL;

DEFINE FIELD IF NOT EXISTS name ON game_session TYPE string COMMENT "Game session name";
DEFINE FIELD IF NOT EXISTS channel_id ON game_session TYPE int COMMENT "Game session channel ID";
DEFINE FIELD IF NOT EXISTS max_players ON game_session TYPE int COMMENT "Game session max players";
DEFINE FIELD IF NOT EXISTS is_open ON game_session TYPE bool COMMENT "Game session is open";
DEFINE FIELD OVERWRITE created_at ON game_session TYPE datetime DEFAULT time::now() COMMENT "Game session created at";
DEFINE FIELD OVERWRITE last_active ON game_session TYPE datetime DEFAULT time::now() COMMENT "Game session last active";

-- Relationship between Game Session and Player
DEFINE TABLE IF NOT EXISTS player_is_playing_in TYPE RELATION FROM player TO game_session;
DEFINE TABLE IF NOT EXISTS character_is_playing_in TYPE RELATION FROM character TO game_session;
