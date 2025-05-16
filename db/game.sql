-- Define Namespace and Database and use them
DEFINE NAMESPACE IF NOT EXISTS ds_qu_shadows;
USE NS ds_qu_shadows;

DEFINE USER IF NOT EXISTS bot ON NAMESPACE PASSWORD "discord" ROLES EDITOR;

-- Define Database and use it
DEFINE DATABASE IF NOT EXISTS game;
USE DB game;

-- Player Table
DEFINE TABLE IF NOT EXISTS player SCHEMAFULL TYPE NORMAL;

DEFINE FIELD IF NOT EXISTS discord_id ON player TYPE int;
DEFINE FIELD IF NOT EXISTS global_name ON player TYPE string;
DEFINE FIELD IF NOT EXISTS display_name ON player TYPE string;
DEFINE FIELD IF NOT EXISTS display_avatar ON player TYPE string;
DEFINE FIELD IF NOT EXISTS joined_at ON player TYPE datetime;
DEFINE FIELD IF NOT EXISTS last_active ON player TYPE datetime;
DEFINE FIELD IF NOT EXISTS is_active ON player TYPE bool;

-- Character Table
DEFINE TABLE IF NOT EXISTS character SCHEMAFULL TYPE NORMAL;

DEFINE FIELD IF NOT EXISTS name ON character TYPE string;
DEFINE FIELD IF NOT EXISTS base_stats ON character TYPE object;
DEFINE FIELD IF NOT EXISTS created_at ON character TYPE datetime;
DEFINE FIELD IF NOT EXISTS last_active ON character TYPE datetime;

-- Relationship between Player and Character
DEFINE TABLE IF NOT EXISTS user_character SCHEMAFULL TYPE RELATION FROM player TO character ENFORCED;