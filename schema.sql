-- FITZEN database schema
-- Weight classes are ordered lightest -> heaviest; this order matters for the
-- matchmaking algorithm's "nearest weight class" fallback (see matching.py).
--
-- CHECK constraints here are a deliberate SECOND line of defence: validation.py
-- already rejects bad input at the form, but these guarantee the database can
-- never hold impossible data even if a bug bypassed the application layer.
--
-- ON DELETE behaviour is specified so removing an account never leaves orphaned
-- rows pointing at records that no longer exist.

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
    -- Deleting the login account removes the gym profile with it.
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE fighters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 16 AND age <= 80),
    weight REAL NOT NULL CHECK (weight > 0 AND weight <= 300),
    height REAL CHECK (height IS NULL OR (height >= 120 AND height <= 250)),
    weight_class TEXT NOT NULL,
    skill_level INTEGER NOT NULL CHECK (skill_level BETWEEN 1 AND 10),
    wins INTEGER NOT NULL DEFAULT 0 CHECK (wins >= 0),
    losses INTEGER NOT NULL DEFAULT 0 CHECK (losses >= 0),
    photo TEXT,
    gym_id INTEGER,                   -- fighter's home gym, optional
    contact TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    -- If a gym is deleted, its fighters remain but become unaffiliated rather
    -- than pointing at a gym row that no longer exists.
    FOREIGN KEY (gym_id) REFERENCES gyms(id) ON DELETE SET NULL
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
    -- A fighter can never be matched against themselves, enforced at the
    -- database level as well as in the application.
    CHECK (fighter1_id <> fighter2_id),
    -- Removing a fighter or gym removes the fights that reference them, so no
    -- match can point at a participant or venue that no longer exists.
    FOREIGN KEY (fighter1_id) REFERENCES fighters(id) ON DELETE CASCADE,
    FOREIGN KEY (fighter2_id) REFERENCES fighters(id) ON DELETE CASCADE,
    FOREIGN KEY (gym_id) REFERENCES gyms(id) ON DELETE CASCADE
);
