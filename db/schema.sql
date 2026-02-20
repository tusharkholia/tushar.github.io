CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    type TEXT NOT NULL,
    tags TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    user_answer TEXT,
    correct BOOLEAN,
    time_taken_seconds INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(question_id) REFERENCES questions(id)
);

CREATE TABLE IF NOT EXISTS embeddings_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    chunk_id TEXT,
    text TEXT,
    source_page INTEGER
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    preferences_json TEXT,
    created_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS study_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    plan_json TEXT,
    created_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
