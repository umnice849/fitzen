"""
Extra tests for FITZEN: permissions, password storage, data integrity and the
"closest weight class" suggestion. Each test is labelled with the success
criterion (SC) it checks, so the output doubles as evidence for Criterion E.

Run with:  python3 test_extra.py
"""
import os
import sqlite3
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

# Use a throwaway database so real data is never touched.
import db
db.DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "test_extra.db")
if os.path.exists(db.DB_PATH):
    os.remove(db.DB_PATH)
db.init_db()

from werkzeug.security import check_password_hash
from app import app

client = app.test_client()
FUTURE = (date.today() + timedelta(days=30)).isoformat()
PASSWORD = "testPass1"


def register_gym(username, name):
    client.post("/register/gym", data={
        "username": username, "password": PASSWORD, "name": name,
        "location": "Kathmandu", "ring_size": "6m x 6m", "contact": "9800000000",
    }, follow_redirects=True)
    client.get("/logout")


def register_fighter(username, name, age, weight_class, skill, gym_id=""):
    client.post("/register/fighter", data={
        "username": username, "password": PASSWORD, "name": name, "age": age,
        "weight": 70, "height": 175, "weight_class": weight_class,
        "skill_level": skill, "gym_id": gym_id, "contact": "9811111111",
    }, follow_redirects=True)
    client.get("/logout")


def login(username):
    client.get("/logout")
    client.post("/login", data={"username": username, "password": PASSWORD}, follow_redirects=True)


def one(sql, params=()):
    conn = db.get_db()
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


# ---------- set-up: 2 gyms, 4 fighters ----------
register_gym("gym_a", "Gym Alpha")
register_gym("gym_b", "Gym Beta")
gym_a = one("SELECT id FROM gyms WHERE name = 'Gym Alpha'")["id"]
gym_b = one("SELECT id FROM gyms WHERE name = 'Gym Beta'")["id"]

register_fighter("f_alpha", "Alpha One", 24, "Lightweight", 7, gym_a)
register_fighter("f_beta", "Beta Two", 26, "Lightweight", 6, gym_b)
register_fighter("f_bantam", "Solo Bantam", 22, "Bantamweight", 5)
register_fighter("f_feather", "Neighbour Feather", 23, "Featherweight", 5)

passed = 0


def ok(message):
    global passed
    passed += 1
    print("PASS -", message, "\n")


print("--- [SC4] Passwords are stored as hashes, never as plain text ---")
stored = one("SELECT password FROM users WHERE username = 'f_alpha'")["password"]
assert stored != PASSWORD and len(stored) > 30
assert check_password_hash(stored, PASSWORD)
ok("stored value is a hash and still verifies against the real password")

print("--- [SC12] A viewer (not logged in) cannot create a match ---")
client.get("/logout")
before = one("SELECT COUNT(*) AS n FROM matches")["n"]
client.post("/propose-match", data={"opponent_id": 2, "gym_id": gym_a,
                                    "fight_date": FUTURE, "score": "0.5"}, follow_redirects=True)
after = one("SELECT COUNT(*) AS n FROM matches")["n"]
assert before == after
ok("POST /propose-match without logging in created no match")

print("--- [SC12] A viewer cannot open fighter-only or gym-only pages ---")
for path in ("/find-opponent", "/gym/fights", "/gym/fighters"):
    r = client.get(path, follow_redirects=True)
    assert b"Log In" in r.data, path
ok("/find-opponent, /gym/fights and /gym/fighters all redirect to the login page")

print("--- [SC10] A fighter account cannot open the gym pages ---")
login("f_alpha")
r = client.get("/gym/fights", follow_redirects=True)
assert b"Proposed Fights" not in r.data and b"Log In" in r.data
ok("a fighter visiting /gym/fights is sent to the login page")

print("--- [SC10] Only the gym hosting a fight can accept or decline it ---")
opponent = one("SELECT id FROM fighters WHERE name = 'Beta Two'")["id"]
client.post("/propose-match", data={"opponent_id": opponent, "gym_id": gym_a,
                                    "fight_date": FUTURE, "score": "0.915"}, follow_redirects=True)
match_id = one("SELECT id FROM matches")["id"]
assert one("SELECT status FROM matches WHERE id = ?", (match_id,))["status"] == "pending"

login("gym_b")  # a different gym tries to decide on Gym Alpha's fight
client.post(f"/gym/fights/{match_id}/accepted", follow_redirects=True)
assert one("SELECT status FROM matches WHERE id = ?", (match_id,))["status"] == "pending"
ok("Gym Beta tried to accept Gym Alpha's fight and the status stayed 'pending'")

login("gym_a")  # the real host accepts
client.post(f"/gym/fights/{match_id}/accepted", follow_redirects=True)
assert one("SELECT status FROM matches WHERE id = ?", (match_id,))["status"] == "accepted"
ok("Gym Alpha accepted its own fight and the status became 'accepted'")

print("--- [SC14] A gym only sees the fighters that belong to it ---")
r = client.get("/gym/fighters")
assert b"Alpha One" in r.data and b"Beta Two" not in r.data
ok("Gym Alpha's list shows Alpha One and does not show Beta Two")

print("--- [SC13] Fighter search by name returns only matching fighters ---")
client.get("/logout")
r = client.get("/fighters?q=Alpha")
assert b"Alpha One" in r.data and b"Beta Two" not in r.data
ok("searching 'Alpha' shows Alpha One only")

print("--- [SC7/SC8] A closest-class suggestion has no Propose button ---")
login("f_bantam")
r = client.post("/find-opponent", data={"fight_date": FUTURE}, follow_redirects=True)
assert b"Neighbour Feather" in r.data           # the neighbouring-class fighter is shown
assert b"Propose This Match" not in r.data      # but it cannot be proposed
assert b"arranged with the gym" in r.data
ok("Solo Bantam sees Neighbour Feather as the closest fighter, with no Propose button")

print("--- [SC16] Impossible values in the calendar address do not crash the page ---")
client.get("/logout")
for query in ("month=13", "month=-4", "month=abc", "year=99999", "year=0&month=1"):
    r = client.get("/calendar?" + query)
    assert r.status_code == 200, query
ok("month=13, month=-4, month=abc, year=99999 and year=0 all show a normal calendar")

print("--- [SC15] The database rejects impossible data even if the app is bypassed ---")
conn = db.get_db()
conn.execute("INSERT INTO users (username, password, role) VALUES ('raw_user', 'x', 'fighter')")
uid = conn.execute("SELECT id FROM users WHERE username = 'raw_user'").fetchone()["id"]
try:
    conn.execute(
        """INSERT INTO fighters (user_id, name, age, weight, weight_class, skill_level, contact)
           VALUES (?, 'Raw', 25, 70, 'Lightweight', 999, '9800000000')""", (uid,))
    raise AssertionError("skill level 999 should have been rejected")
except sqlite3.IntegrityError:
    pass
ids = [r["id"] for r in conn.execute("SELECT id FROM fighters LIMIT 1")]
try:
    conn.execute(
        """INSERT INTO matches (fighter1_id, fighter2_id, gym_id, fight_date, weight_class)
           VALUES (?, ?, ?, ?, 'Lightweight')""", (ids[0], ids[0], gym_a, FUTURE))
    raise AssertionError("a fighter matched with themselves should have been rejected")
except sqlite3.IntegrityError:
    pass
conn.close()
ok("skill level 999 and a self-match were both refused by the database itself")

print("--- [SC15] Deleting a fighter removes their matches (no orphan rows) ---")
conn = db.get_db()
fighter_user = conn.execute(
    "SELECT user_id FROM fighters WHERE name = 'Beta Two'").fetchone()["user_id"]
conn.execute("DELETE FROM users WHERE id = ?", (fighter_user,))
conn.commit()
remaining = conn.execute("SELECT COUNT(*) AS n FROM matches").fetchone()["n"]
conn.close()
assert remaining == 0
ok("the match involving Beta Two was removed when Beta Two's account was deleted")

print("--- [SC15] Deleting a gym keeps its fighters but removes the link ---")
conn = db.get_db()
gym_user = conn.execute("SELECT user_id FROM gyms WHERE id = ?", (gym_a,)).fetchone()["user_id"]
conn.execute("DELETE FROM users WHERE id = ?", (gym_user,))
conn.commit()
alpha = conn.execute("SELECT name, gym_id FROM fighters WHERE name = 'Alpha One'").fetchone()
conn.close()
assert alpha is not None and alpha["gym_id"] is None
ok("Alpha One still exists, and their gym_id is now empty instead of pointing at a deleted gym")

print("--- [SC15] Data is still there when the database is opened again ---")
fresh = sqlite3.connect(db.DB_PATH)
users = fresh.execute("SELECT COUNT(*) FROM users").fetchone()[0]
fresh.close()
assert users > 0
ok(f"a brand-new connection to the database file found {users} saved accounts")

print(f"All extra tests passed ({passed} checks).")
