USE NS ds_qu_shadows;

USE DB game;

DEFINE TABLE IF NOT EXISTS gm_history SCHEMAFULL TYPE NORMAL;

DEFINE FIELD OVERWRITE game_session_id ON gm_history TYPE string COMMENT "Game session ID";
DEFINE FIELD OVERWRITE character_name ON gm_history TYPE string COMMENT "Character name";
DEFINE FIELD OVERWRITE request ON gm_history TYPE string COMMENT "Request";
DEFINE FIELD OVERWRITE model_messages ON gm_history FLEXIBLE TYPE array<object> COMMENT "Model response messages";
DEFINE FIELD OVERWRITE created_at ON gm_history TYPE datetime DEFAULT time::now() COMMENT "Created at";

DEFINE INDEX IF NOT EXISTS idx_gm_history_game_session_id ON TABLE gm_history FIELDS game_session_id COMMENT "Game session ID index";
