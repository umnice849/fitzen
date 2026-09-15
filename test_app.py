
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import db
from datetime import date, timedelta
FUTURE = (date.today() + timedelta(days=30)).isoformat()
FUTURE2 = (date.today() + timedelta(days=45)).isoformat()
db.DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "test_fitzen.db")
if os.path.exists(db.DB_PATH):
    os.remove(db.DB_PATH)
db.init_db()

from app import app

client = app.test_client()


def register_gym(username, name, location):
    r = client.post("/register/gym", data={
        "username": username, "password": "testPass1",
        "name": name, "location": location, "ring_size": "6m x 6m", "contact": "9800000000",
    }, follow_redirects=True)
    assert r.status_code == 200
    client.get("/logout")


def register_fighter(username, name, age, weight, weight_class, skill, contact="9800000001"):
    r = client.post("/register/fighter", data={
        "username": username, "password": "testPass1",
        "name": name, "age": age, "weight": weight, "height": 175,
        "weight_class": weight_class, "skill_level": skill, "contact": contact,
    }, follow_redirects=True)
    assert r.status_code == 200
    client.get("/logout")


def login(username):
    r = client.post("/login", data={"username": username, "password": "testPass1"}, follow_redirects=True)
    assert r.status_code == 200


print("--- Registering gyms and fighters ---")
register_gym("gym1", "Ktm Fight Club", "Kathmandu")
register_fighter("f_aarav", "Aarav", 24, 70, "Lightweight", 7, contact="9811111111")
register_fighter("f_close", "Bikash", 26, 71, "Lightweight", 6, contact="9822222222")
register_fighter("f_far", "Suman", 40, 90, "Lightweight", 2, contact="9833333333")
register_fighter("f_heavy", "Nabin", 30, 95, "Middleweight", 8, contact="9855555555")
print("PASS - registration works\n")

print("--- Viewer (not logged in) can browse fighters/gyms/calendar ---")
r = client.get("/fighters")
assert b"Aarav" in r.data and b"Bikash" in r.data
r = client.get("/gyms")
assert b"Ktm Fight Club" in r.data
r = client.get("/calendar")
assert r.status_code == 200
print("PASS - viewer read-only access works, no login required\n")

print("--- Fighter finds an opponent (should pick the closer match) ---")
login("f_aarav")
r = client.post("/find-opponent", data={"fight_date": FUTURE, "preferred_location": "Kathmandu"})
assert b"Bikash" in r.data, "expected the closer-scoring fighter (Bikash) to be suggested"
assert b"Suman" not in r.data
print("PASS - correct opponent suggested over the worse match\n")

print("--- Fighter proposes the match to the gym ---")
gym_row = db.get_db().execute("SELECT id FROM gyms WHERE name = 'Ktm Fight Club'").fetchone()
fighter_row = db.get_db().execute("SELECT id FROM fighters WHERE name = 'Bikash'").fetchone()
r = client.post("/propose-match", data={
    "opponent_id": fighter_row["id"], "gym_id": gym_row["id"],
    "fight_date": FUTURE, "preferred_location": "Kathmandu", "score": "0.915",
}, follow_redirects=True)
assert r.status_code == 200
conn = db.get_db()
match = conn.execute("SELECT * FROM matches").fetchone()
assert match["status"] == "pending"
print("PASS - match created with status 'pending'\n")

print("--- Calendar should NOT show the pending match yet ---")
r = client.get("/calendar")
assert b"Bikash" not in r.data
print("PASS - pending fights are hidden from the public calendar\n")

print("--- Gym accepts the fight ---")
client.get("/logout")
login("gym1")
r = client.get("/gym/fights")
assert b"Bikash" in r.data
r = client.post(f"/gym/fights/{match['id']}/accepted", follow_redirects=True)
conn = db.get_db()
match = conn.execute("SELECT * FROM matches WHERE id = ?", (match["id"],)).fetchone()
assert match["status"] == "accepted"
print("PASS - gym accept updates status correctly\n")

print("--- Calendar NOW shows the accepted match (in the correct month) ---")
r = client.get(f"/calendar?year={date.today().year}&month={date.today().month}" if False else "/calendar?year=" + FUTURE[:4] + "&month=" + str(int(FUTURE[5:7])))
assert b"Bikash" in r.data and b"Ktm Fight Club" in r.data
print("PASS - accepted fights appear on the public calendar\n")

print("--- Calendar renders even with zero fights in view (e.g. current month) ---")
r = client.get("/calendar")
assert r.status_code == 200 and b"Mon" in r.data
print("PASS - calendar grid always renders regardless of fights\n")

print("--- Age under 16 is rejected ---")
r = client.post("/register/fighter", data={
    "username": "too_young", "password": "testPass1", "name": "Kiddo", "age": 12,
    "weight": 40, "height": 150, "weight_class": "Flyweight", "skill_level": 1, "contact": "9844444444",
}, follow_redirects=True)
assert b"at least 16" in r.data
conn = db.get_db()
assert conn.execute("SELECT id FROM users WHERE username = 'too_young'").fetchone() is None
print("PASS - under-16 registration blocked\n")

print("--- Searching fighters by weight class works ---")
r = client.get("/fighters?weight_class=Lightweight")
assert b"Aarav" in r.data and b"Bikash" in r.data
print("PASS - weight class filter returns correct fighters\n")

print("--- Fighter profile page shows fight history ---")
r = client.get(f"/fighters/{fighter_row['id']}")
assert b"Aarav" in r.data  # Bikash's opponent should show in the record
print("PASS - fighter profile page renders with fight record\n")

print("--- Malformed age (non-numeric) is rejected gracefully, no crash ---")
r = client.post("/register/fighter", data={
    "username": "bad_age", "password": "testPass1", "name": "Oops", "age": "not-a-number",
    "weight": 70, "height": 175, "weight_class": "Lightweight", "skill_level": 5, "contact": "9844444444",
}, follow_redirects=True)
assert r.status_code == 200 and b"must be a number" in r.data
conn = db.get_db()
assert conn.execute("SELECT id FROM users WHERE username = 'bad_age'").fetchone() is None
print("PASS - non-numeric age handled without a server error\n")

print("--- Malformed match proposal (bad opponent_id) is rejected gracefully ---")
login("f_aarav")
r = client.post("/propose-match", data={
    "opponent_id": "not-an-id", "gym_id": gym_row["id"],
    "fight_date": FUTURE2, "score": "0.5",
}, follow_redirects=True)
assert r.status_code == 200 and b"malformed" in r.data
print("PASS - malformed match proposal handled without a server error\n")

print("--- Landing page shows the three role tiles ---")
client.get("/logout")   # landing page only shows for logged-out visitors
r = client.get("/")
assert b"Fighter" in r.data and b"Viewer" in r.data and b"Gym" in r.data
print("PASS - role selection landing page renders\n")

print("--- Viewer role goes straight in; Fighter/Gym go to a login page ---")
r = client.get("/role/viewer", follow_redirects=True)
assert b"Welcome to FITZEN" in r.data
r = client.get("/role/fighter", follow_redirects=True)
assert b"Fighter Log In" in r.data
r = client.get("/role/gym", follow_redirects=True)
assert b"Gym Log In" in r.data
print("PASS - role routing works for all three roles\n")

print("--- A fighter cannot be matched against themselves ---")
login("f_aarav")
me = db.get_db().execute("SELECT id FROM fighters WHERE name = 'Aarav'").fetchone()
r = client.post("/propose-match", data={
    "opponent_id": me["id"], "gym_id": gym_row["id"],
    "fight_date": FUTURE2, "score": "0.0",
}, follow_redirects=True)
assert b"cannot request a match against yourself" in r.data
print("PASS - self-matching blocked\n")

print("--- A past fight date is rejected ---")
past = (date.today() - timedelta(days=1)).isoformat()
r = client.post("/find-opponent", data={"fight_date": past}, follow_redirects=True)
assert b"cannot be in the past" in r.data
print("PASS - past fight date rejected\n")

print("--- Cross-weight-class match is blocked ---")
heavy = db.get_db().execute("SELECT id FROM fighters WHERE weight_class != 'Lightweight' LIMIT 1").fetchone()
if heavy:
    r = client.post("/propose-match", data={
        "opponent_id": heavy["id"], "gym_id": gym_row["id"],
        "fight_date": FUTURE2, "score": "1.0",
    }, follow_redirects=True)
    assert b"class, not yours" in r.data
    print("PASS - cross-weight-class match blocked\n")

print("--- Duplicate pending match between the same two fighters is blocked ---")
r = client.post("/propose-match", data={
    "opponent_id": fighter_row["id"], "gym_id": gym_row["id"],
    "fight_date": FUTURE, "score": "0.915",
}, follow_redirects=True)
assert b"already have a match request" in r.data
print("PASS - duplicate match request blocked\n")

print("--- Weak password and bad contact number are rejected ---")
r = client.post("/register/fighter", data={
    "username": "weakpw", "password": "abc", "name": "Weak", "age": 25,
    "weight": 70, "height": 175, "weight_class": "Lightweight", "skill_level": 5,
    "contact": "9800000099",
}, follow_redirects=True)
assert b"at least 8 characters" in r.data
r = client.post("/register/fighter", data={
    "username": "badphone", "password": "goodPass1", "name": "Bad", "age": 25,
    "weight": 70, "height": 175, "weight_class": "Lightweight", "skill_level": 5,
    "contact": "123",
}, follow_redirects=True)
assert b"exactly 10 digits" in r.data
print("PASS - password and contact rules enforced at registration\n")

print("--- Logout clears the session ---")
client.get("/logout")
r = client.get("/find-opponent", follow_redirects=True)
assert b"Log In" in r.data
print("PASS - logout works and protected routes redirect\n")

print("All end-to-end tests passed.")
