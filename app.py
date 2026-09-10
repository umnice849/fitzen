from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import sqlite3

from db import get_db
from matching import find_opponent, WEIGHT_CLASSES, InvalidFighterDataError

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-this-before-real-deployment"


# ---------- helpers ----------

def current_role():
    return session.get("role")  # "fighter", "gym", or None (viewer)


def current_fighter(db):
    if session.get("role") != "fighter":
        return None
    return db.execute(
        "SELECT * FROM fighters WHERE user_id = ?", (session["user_id"],)
    ).fetchone()


def current_gym(db):
    if session.get("role") != "gym":
        return None
    return db.execute(
        "SELECT * FROM gyms WHERE user_id = ?", (session["user_id"],)
    ).fetchone()


def login_required(role=None):
    if "user_id" not in session:
        return False
    if role and session.get("role") != role:
        return False
    return True


# ---------- auth & registration ----------

@app.route("/")
def index():
    return redirect(url_for("home"))


@app.route("/register")
def register_choose():
    return render_template("register_choose.html")


@app.route("/register/fighter", methods=["GET", "POST"])
def register_fighter():
    db = get_db()
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash("That username is already taken.")
            return render_template("register_fighter.html")

        gyms = db.execute("SELECT id, name FROM gyms ORDER BY name").fetchall()

        # Numeric fields come in as strings from the form and can be malformed
        # (empty, non-numeric, etc.) — validate them before touching the database.
        try:
            age = int(request.form["age"])
            weight = float(request.form["weight"])
            height = float(request.form["height"]) if request.form.get("height") else None
            skill_level = int(request.form["skill_level"])
        except (ValueError, KeyError):
            flash("Age, weight, height, and skill level must be valid numbers.")
            return render_template("register_fighter.html", gyms=gyms, weight_classes=WEIGHT_CLASSES)

        if age < 16:
            flash("Fighters must be at least 16 years old to register.")
            return render_template("register_fighter.html", gyms=gyms, weight_classes=WEIGHT_CLASSES)

        gym_id = request.form.get("gym_id") or None
        try:
            cur = db.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, 'fighter')",
                (username, generate_password_hash(password)),
            )
            user_id = cur.lastrowid

            db.execute(
                """INSERT INTO fighters
                   (user_id, name, age, weight, height, weight_class, skill_level, wins, losses, photo, gym_id, contact)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?)""",
                (
                    user_id,
                    request.form["name"],
                    age,
                    weight,
                    height,
                    request.form["weight_class"],
                    skill_level,
                    request.form.get("photo") or None,
                    gym_id,
                    request.form.get("contact"),
                ),
            )
            db.commit()
        except sqlite3.IntegrityError as e:
            # e.g. the age CHECK(age >= 16) constraint at the database level,
            # or a duplicate username slipping past the earlier check under
            # concurrent requests.
            db.rollback()
            flash(f"Could not create account: {e}")
            return render_template("register_fighter.html", gyms=gyms, weight_classes=WEIGHT_CLASSES)

        session["user_id"] = user_id
        session["role"] = "fighter"
        return redirect(url_for("home"))

    gyms = db.execute("SELECT id, name FROM gyms ORDER BY name").fetchall()
    return render_template("register_fighter.html", gyms=gyms, weight_classes=WEIGHT_CLASSES)


@app.route("/register/gym", methods=["GET", "POST"])
def register_gym():
    db = get_db()
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash("That username is already taken.")
            return render_template("register_gym.html")

        cur = db.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, 'gym')",
            (username, generate_password_hash(password)),
        )
        user_id = cur.lastrowid

        db.execute(
            "INSERT INTO gyms (user_id, name, location, ring_size, photo, contact) VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                request.form["name"],
                request.form["location"],
                request.form.get("ring_size"),
                request.form.get("photo") or None,
                request.form.get("contact"),
            ),
        )
        db.commit()
        session["user_id"] = user_id
        session["role"] = "gym"
        return redirect(url_for("home"))

    return render_template("register_gym.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (request.form["username"],)
        ).fetchone()
        if user and check_password_hash(user["password"], request.form["password"]):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        flash("Incorrect username or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- home / navigation ----------

@app.route("/home")
def home():
    db = get_db()
    role = current_role()
    fighter = current_fighter(db)
    gym = current_gym(db)
    return render_template("home.html", role=role, fighter=fighter, gym=gym)


# ---------- directory: fighters & gyms (open to everyone, including viewers) ----------

@app.route("/fighters")
def fighters_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    wc = request.args.get("weight_class", "").strip()

    query = "SELECT * FROM fighters WHERE 1=1"
    params = []
    if q:
        query += " AND name LIKE ?"
        params.append(f"%{q}%")
    if wc:
        query += " AND weight_class = ?"
        params.append(wc)
    query += " ORDER BY name"

    rows = db.execute(query, params).fetchall()
    return render_template(
        "fighters_list.html", fighters=rows, role=current_role(), q=q,
        weight_class=wc, weight_classes=WEIGHT_CLASSES,
    )


@app.route("/fighters/<int:fighter_id>")
def fighter_profile(fighter_id):
    db = get_db()
    fighter = db.execute("SELECT * FROM fighters WHERE id = ?", (fighter_id,)).fetchone()
    if fighter is None:
        return redirect(url_for("fighters_list"))

    history = db.execute(
        """SELECT m.*, f1.name AS fighter1_name, f2.name AS fighter2_name, g.name AS gym_name
           FROM matches m
           JOIN fighters f1 ON f1.id = m.fighter1_id
           JOIN fighters f2 ON f2.id = m.fighter2_id
           JOIN gyms g ON g.id = m.gym_id
           WHERE (m.fighter1_id = ? OR m.fighter2_id = ?) AND m.status = 'accepted'
           ORDER BY m.fight_date DESC""",
        (fighter_id, fighter_id),
    ).fetchall()

    return render_template(
        "fighter_profile.html", fighter=fighter, history=history, role=current_role()
    )


@app.route("/gyms")
def gyms_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute(
            "SELECT * FROM gyms WHERE name LIKE ? ORDER BY name", (f"%{q}%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM gyms ORDER BY name").fetchall()
    return render_template("gyms_list.html", gyms=rows, role=current_role(), q=q)


@app.route("/calendar")
def calendar_view():
    import calendar as cal_module

    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    db = get_db()
    rows = db.execute(
        """SELECT m.*, f1.name AS fighter1_name, f2.name AS fighter2_name, g.name AS gym_name
           FROM matches m
           JOIN fighters f1 ON f1.id = m.fighter1_id
           JOIN fighters f2 ON f2.id = m.fighter2_id
           JOIN gyms g ON g.id = m.gym_id
           WHERE m.status = 'accepted'
           ORDER BY m.fight_date"""
    ).fetchall()

    fights_by_day = {}
    for r in rows:
        try:
            fdate = date.fromisoformat(r["fight_date"])
        except ValueError:
            continue
        if fdate.year == year and fdate.month == month:
            fights_by_day.setdefault(fdate.day, []).append(r)

    cal = cal_module.Calendar(firstweekday=0)  # Monday first, matches the wireframe
    weeks = cal.monthdayscalendar(year, month)  # 0 = day outside this month

    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month % 12 + 1
    next_year = year + 1 if month == 12 else year

    return render_template(
        "calendar.html",
        role=current_role(),
        weeks=weeks,
        fights_by_day=fights_by_day,
        month_name=cal_module.month_name[month],
        year=year,
        month=month,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
    )


# ---------- find opponent (fighter only) ----------

@app.route("/find-opponent", methods=["GET", "POST"])
def find_opponent_route():
    if not login_required("fighter"):
        return redirect(url_for("login"))

    db = get_db()
    fighter = current_fighter(db)
    result = None
    preferred_location = None
    fight_date = None

    if request.method == "POST":
        fight_date = request.form["fight_date"]
        preferred_location = request.form.get("preferred_location")

        # candidates: everyone except me, not already pending/accepted with me on this date
        already_matched_ids = {
            row["fighter2_id"] if row["fighter1_id"] == fighter["id"] else row["fighter1_id"]
            for row in db.execute(
                """SELECT fighter1_id, fighter2_id FROM matches
                   WHERE fight_date = ? AND status IN ('pending', 'accepted')
                   AND (fighter1_id = ? OR fighter2_id = ?)""",
                (fight_date, fighter["id"], fighter["id"]),
            ).fetchall()
        }

        candidate_rows = db.execute(
            "SELECT * FROM fighters WHERE id != ?", (fighter["id"],)
        ).fetchall()
        candidates = [dict(r) for r in candidate_rows if r["id"] not in already_matched_ids]

        try:
            result = find_opponent(dict(fighter), candidates)
        except InvalidFighterDataError as e:
            # Your own profile is somehow missing a required field — tell the
            # fighter plainly rather than letting the page crash.
            flash(f"Couldn't run the match search: {e}")
            result = None

    gyms = db.execute("SELECT id, name FROM gyms ORDER BY name").fetchall()
    return render_template(
        "find_opponent.html",
        fighter=fighter,
        result=result,
        gyms=gyms,
        fight_date=fight_date,
        preferred_location=preferred_location,
        role=current_role(),
    )


@app.route("/propose-match", methods=["POST"])
def propose_match():
    if not login_required("fighter"):
        return redirect(url_for("login"))

    db = get_db()
    fighter = current_fighter(db)

    try:
        opponent_id = int(request.form["opponent_id"])
        gym_id = int(request.form["gym_id"])
        score = float(request.form["score"])
    except (ValueError, KeyError):
        flash("That match request was malformed — please try again.")
        return redirect(url_for("find_opponent_route"))

    try:
        db.execute(
            """INSERT INTO matches (fighter1_id, fighter2_id, gym_id, fight_date, preferred_location, weight_class, score, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (
                fighter["id"],
                opponent_id,
                gym_id,
                request.form["fight_date"],
                request.form.get("preferred_location"),
                fighter["weight_class"],
                score,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        # e.g. opponent_id or gym_id no longer exists (foreign key violation)
        db.rollback()
        flash(f"Couldn't save that match: {e}")
        return redirect(url_for("find_opponent_route"))

    flash("Match proposed! The gym now needs to accept it before it's confirmed.")
    return redirect(url_for("home"))


# ---------- gym: manage fighters & accept/decline fights ----------

@app.route("/gym/fighters")
def gym_fighters():
    if not login_required("gym"):
        return redirect(url_for("login"))
    db = get_db()
    gym = current_gym(db)
    rows = db.execute(
        "SELECT * FROM fighters WHERE gym_id = ? ORDER BY name", (gym["id"],)
    ).fetchall()
    return render_template("gym_fighters.html", fighters=rows, role=current_role())


@app.route("/gym/fights")
def gym_fights():
    if not login_required("gym"):
        return redirect(url_for("login"))
    db = get_db()
    gym = current_gym(db)
    rows = db.execute(
        """SELECT m.*, f1.name AS fighter1_name, f2.name AS fighter2_name
           FROM matches m
           JOIN fighters f1 ON f1.id = m.fighter1_id
           JOIN fighters f2 ON f2.id = m.fighter2_id
           WHERE m.gym_id = ? AND m.status = 'pending'
           ORDER BY m.fight_date""",
        (gym["id"],),
    ).fetchall()
    return render_template("gym_fights.html", fights=rows, role=current_role())


@app.route("/gym/fights/<int:match_id>/<decision>", methods=["POST"])
def gym_fight_decision(match_id, decision):
    if not login_required("gym"):
        return redirect(url_for("login"))
    if decision not in ("accepted", "declined"):
        return redirect(url_for("gym_fights"))

    db = get_db()
    gym = current_gym(db)
    db.execute(
        "UPDATE matches SET status = ? WHERE id = ? AND gym_id = ?",
        (decision, match_id, gym["id"]),
    )
    db.commit()
    return redirect(url_for("gym_fights"))


if __name__ == "__main__":
    app.run(debug=True)
