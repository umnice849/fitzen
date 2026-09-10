-- FITZEN database schema
-- Weight classes are ordered lightest -> heaviest; this order matters for the
-- matchmaking algorithm's "nearest weight class" fallback (see matching.py).

DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS fighters;
DROP TABLE IF EXISTS gyms;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,          -- hashed, never stored in plain text
    role TEXT NOT NULL CHECK (role IN ('fighter', 'gym'))
);

CREATE TABLE gyms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    ring_size TEXT,
    photo TEXT,
    contact TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE fighters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 16),
    weight REAL NOT NULL,
    height REAL,
    weight_class TEXT NOT NULL,
    skill_level INTEGER NOT NULL,     -- 1 (beginner) to 10 (elite)
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    photo TEXT,
    gym_id INTEGER,                   -- fighter's home gym, optional
    contact TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (gym_id) REFERENCES gyms(id)
);

CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fighter1_id INTEGER NOT NULL,      -- the fighter who requested the match
    fighter2_id INTEGER NOT NULL,      -- the suggested/chosen opponent
    gym_id INTEGER NOT NULL,           -- venue the fight is proposed at
    fight_date TEXT NOT NULL,
    preferred_location TEXT,           -- free-text note only, not used in matching
    weight_class TEXT NOT NULL,
    score REAL,                        -- the compatibility score that produced this match
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
    FOREIGN KEY (fighter1_id) REFERENCES fighters(id),
    FOREIGN KEY (fighter2_id) REFERENCES fighters(id),
    FOREIGN KEY (gym_id) REFERENCES gyms(id)
);
