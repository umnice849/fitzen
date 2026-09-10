# FITZEN — Fighter Matchmaking Platform

CS HL IA project. Flask (Python) backend + SQLite database.

## What every file does

```
fitzen/
├── app.py              Main Flask application — every URL/page ("route") lives here:
│                        registration, login, find-opponent, gym accept/decline,
│                        calendar, directory, fighter profiles.
├── matching.py          The matchmaking algorithm, on its own, with no Flask or
│                        database code in it. Contains the Matchmaker class,
│                        the weighted scoring formula, and the custom
│                        InvalidFighterDataError exception. Kept separate so it
│                        can be tested completely independently (see below).
├── db.py                Two jobs: get_db() opens a connection to the SQLite
│                        file; init_db() builds a fresh database from schema.sql.
├── schema.sql            The database structure: CREATE TABLE statements for
│                        users, fighters, gyms, and matches, including all
│                        constraints (e.g. age >= 16).
├── seed.py               Optional — populates the database with 5 demo gyms
│                        and 8 demo fighters so you have data to test with
│                        immediately, and prints their usernames/passwords.
├── test_matching.py       Unit tests for the algorithm ONLY — no Flask, no
│                        database, just Python function calls checking the
│                        scoring math and every edge case (tie, fallback, etc).
├── test_app.py            End-to-end tests — uses Flask's test client to
│                        simulate real browser requests against the actual
│                        app and a throwaway test database.
├── requirements.txt       One line: "Flask" — what to `pip install`.
├── templates/             Every HTML page (Jinja2 templates). base.html is the
│                        shared layout (nav bar); every other file extends it.
├── static/style.css       All the CSS styling.
└── instance/fitzen.db     The actual database file — created by db.py, NOT
                           included in this zip (you generate your own).
```

## How to run this locally

1. Install Python (python.org) if you haven't already.
2. Open a terminal in this folder and run:
   ```
   pip install flask --break-system-packages
   ```
   (drop the flag if that errors — just `pip install flask`. On Mac, use `python3`/`pip3` — see the note below if `pip` isn't found.)
3. Build the database:
   ```
   python3 db.py
   ```
4. (Optional) Add demo accounts:
   ```
   python3 seed.py
   ```
5. Start the app:
   ```
   python3 app.py
   ```
6. Open **http://127.0.0.1:5000** in your browser.

**Mac note:** if `pip`/`python` aren't found, use `python3` and `python3 -m pip install flask --break-system-packages` instead.

## Running the tests

```
python3 test_matching.py
python3 test_app.py
```
Both should end with "All ... tests passed."

## How the database works (short version)

FITZEN uses **SQLite** — the entire database is a single file (`instance/fitzen.db`), no separate server needed. It has 4 tables:

- **users** — every login (username, hashed password, role: fighter or gym)
- **fighters** — one row per fighter profile, linked to a `users` row
- **gyms** — one row per gym profile, linked to a `users` row
- **matches** — one row per proposed/confirmed fight, linking two fighters and a gym, with a `status` field (`pending` → `accepted`/`declined`)

Every query in app.py uses `?` placeholders (parameterised queries) instead of pasting values directly into the SQL string — this is what prevents SQL injection.

Full field-by-field details (types, constraints) are in the Data Dictionary section of Criteria_C.docx.
