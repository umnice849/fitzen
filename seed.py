"""
Populates the database with 5 demo gyms and 8 demo fighters, then prints out
every account's username/password. Run this AFTER python3 db.py.

Usage: python3 seed.py
"""
from werkzeug.security import generate_password_hash
from db import get_db

conn = get_db()

gyms = [
    # username, password, name, location, ring_size, photo
    ("gym_ktm_fc", "gymPass1!", "Kathmandu Fight Club", "Kathmandu, Bagmati", "6m x 6m",
     "https://picsum.photos/seed/gym1/300/220", "9801444112"),
    ("gym_thunder", "gymPass2!", "Thunder Ring Gym", "Pokhara, Gandaki", "7m x 7m",
     "https://picsum.photos/seed/gym2/300/220", "9806155667"),
    ("gym_ironfist", "gymPass3!", "Iron Fist Academy", "Lalitpur, Bagmati", "6m x 6m",
     "https://picsum.photos/seed/gym3/300/220", "9801551223"),
    ("gym_redcorner", "gymPass4!", "Red Corner Kickboxing", "Biratnagar, Koshi", "5.5m x 5.5m",
     "https://picsum.photos/seed/gym4/300/220", "9802177889"),
    ("gym_apex", "gymPass5!", "Apex Combat Center", "Bharatpur, Bagmati", "7m x 7m",
     "https://picsum.photos/seed/gym5/300/220", "9805633445"),
]

gym_ids = {}
for username, password, name, location, ring_size, photo, contact in gyms:
    cur = conn.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, 'gym')",
        (username, generate_password_hash(password)),
    )
    user_id = cur.lastrowid
    cur2 = conn.execute(
        "INSERT INTO gyms (user_id, name, location, ring_size, photo, contact) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, location, ring_size, photo, contact),
    )
    gym_ids[name] = cur2.lastrowid

fighters = [
    # username, password, name, age, weight, height, weight_class, skill, wins, losses, photo, gym, contact
    ("f_aarav", "fightPass1!", "Aarav Gurung", 24, 70, 175, "Lightweight", 7, 13, 7,
     "https://i.pravatar.cc/150?img=11", "Kathmandu Fight Club", "9800000001"),
    ("f_bikash", "fightPass2!", "Bikash Rai", 26, 71, 174, "Lightweight", 6, 9, 6,
     "https://i.pravatar.cc/150?img=12", "Thunder Ring Gym", "9800000002"),
    ("f_sujan", "fightPass3!", "Sujan Tamang", 22, 60, 168, "Featherweight", 5, 5, 4,
     "https://i.pravatar.cc/150?img=13", "Iron Fist Academy", "9800000003"),
    ("f_pratik", "fightPass4!", "Pratik Shrestha", 28, 80, 180, "Welterweight", 8, 20, 5,
     "https://i.pravatar.cc/150?img=14", "Kathmandu Fight Club", "9800000004"),
    ("f_nabin", "fightPass5!", "Nabin Thapa", 30, 90, 182, "Middleweight", 9, 25, 3,
     "https://i.pravatar.cc/150?img=15", "Red Corner Kickboxing", "9800000005"),
    ("f_kabita", "fightPass6!", "Kabita Magar", 21, 55, 162, "Flyweight", 4, 3, 2,
     "https://i.pravatar.cc/150?img=16", "Apex Combat Center", "9800000006"),
    ("f_dipesh", "fightPass7!", "Dipesh Karki", 19, 65, 172, "Featherweight", 3, 2, 3,
     "https://i.pravatar.cc/150?img=17", "Iron Fist Academy", "9800000007"),
    ("f_sabina", "fightPass8!", "Sabina Lama", 25, 60, 165, "Featherweight", 6, 8, 4,
     "https://i.pravatar.cc/150?img=18", "Thunder Ring Gym", "9800000008"),
]

for username, password, name, age, weight, height, wc, skill, wins, losses, photo, gym_name, contact in fighters:
    cur = conn.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, 'fighter')",
        (username, generate_password_hash(password)),
    )
    user_id = cur.lastrowid
    conn.execute(
        """INSERT INTO fighters
           (user_id, name, age, weight, height, weight_class, skill_level, wins, losses, photo, gym_id, contact)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, name, age, weight, height, wc, skill, wins, losses, photo, gym_ids[gym_name], contact),
    )

conn.commit()

print("\n=== GYM ACCOUNTS ===")
print(f"{'Username':<15} {'Password':<12} Gym Name")
for username, password, name, *_ in gyms:
    print(f"{username:<15} {password:<12} {name}")

print("\n=== FIGHTER ACCOUNTS ===")
print(f"{'Username':<12} {'Password':<12} Name")
for username, password, name, *_ in fighters:
    print(f"{username:<12} {password:<12} {name}")

print("\nSeeding complete.")
