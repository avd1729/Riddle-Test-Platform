DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS riddles;
DROP TABLE IF EXISTS test_sessions;
DROP TABLE IF EXISTS user_riddles;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0
);

CREATE TABLE riddles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    hint1 TEXT NOT NULL,
    hint2 TEXT NOT NULL,
    hint3 TEXT NOT NULL
);

CREATE TABLE test_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    completed INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE user_riddles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    riddle_id INTEGER NOT NULL,
    test_session_id INTEGER NOT NULL,
    hint1_used INTEGER DEFAULT 0,
    hint2_used INTEGER DEFAULT 0,
    hint3_used INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    answer_attempt TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (riddle_id) REFERENCES riddles (id),
    FOREIGN KEY (test_session_id) REFERENCES test_sessions (id)
);