"""
Input validation rules for FITZEN.

Kept in its own module (no Flask, no database) so every rule can be unit-tested
directly and reused by both the registration routes and the test suite.

Every validator either returns a cleaned value or raises ValidationError with a
message that is safe to show the user directly.
"""
import re
from datetime import date

# --- Limits, with the reasoning behind each ---------------------------------
# Age: 16 is the minimum because most combat-sports bodies require a competitor
# to be at least 16 (and under-18s need guardian consent). 80 is an upper bound
# that is generous for masters divisions while still rejecting typos like 150.
MIN_AGE, MAX_AGE = 16, 80

# Weight: covers everything from the lightest amateur divisions up past the
# heaviest recorded competitors, while rejecting 0, negatives, and typos.
MIN_WEIGHT_KG, MAX_WEIGHT_KG = 30.0, 300.0

# Height in centimetres. The lower bound also catches the common mistake of
# entering height in metres (e.g. "1.75"), which would otherwise store nonsense.
MIN_HEIGHT_CM, MAX_HEIGHT_CM = 120.0, 250.0

MIN_SKILL, MAX_SKILL = 1, 10

MIN_USERNAME_LEN, MAX_USERNAME_LEN = 3, 20
MIN_PASSWORD_LEN = 8

CONTACT_DIGITS = 10

# How far ahead a fight may be scheduled. A year is long enough for real
# planning, short enough to catch someone typing the wrong year.
MAX_FIGHT_DAYS_AHEAD = 365


class ValidationError(Exception):
    """Raised when user-supplied input fails a validation rule. The message is
    written to be shown directly to the user."""
    pass


def _to_number(raw, field, converter):
    if raw is None or str(raw).strip() == "":
        raise ValidationError(f"{field} is required.")
    try:
        return converter(str(raw).strip())
    except (ValueError, TypeError):
        raise ValidationError(f"{field} must be a number.")


def validate_age(raw):
    age = _to_number(raw, "Age", int)
    if age < MIN_AGE:
        raise ValidationError(f"Fighters must be at least {MIN_AGE} years old to register.")
    if age > MAX_AGE:
        raise ValidationError(f"Age must be {MAX_AGE} or below.")
    return age


def validate_weight(raw):
    weight = _to_number(raw, "Weight", float)
    if weight < MIN_WEIGHT_KG or weight > MAX_WEIGHT_KG:
        raise ValidationError(f"Weight must be between {MIN_WEIGHT_KG:g}kg and {MAX_WEIGHT_KG:g}kg.")
    return weight


def validate_height(raw, required=False):
    """Height is optional; an empty value returns None unless required=True."""
    if raw is None or str(raw).strip() == "":
        if required:
            raise ValidationError("Height is required.")
        return None
    height = _to_number(raw, "Height", float)
    if height < MIN_HEIGHT_CM or height > MAX_HEIGHT_CM:
        raise ValidationError(
            f"Height must be between {MIN_HEIGHT_CM:g}cm and {MAX_HEIGHT_CM:g}cm "
            f"(enter centimetres, not metres)."
        )
    return height


def validate_skill_level(raw):
    skill = _to_number(raw, "Skill level", int)
    if skill < MIN_SKILL or skill > MAX_SKILL:
        raise ValidationError(f"Skill level must be between {MIN_SKILL} and {MAX_SKILL}.")
    return skill


def validate_username(raw):
    username = (raw or "").strip()
    if len(username) < MIN_USERNAME_LEN or len(username) > MAX_USERNAME_LEN:
        raise ValidationError(
            f"Username must be between {MIN_USERNAME_LEN} and {MAX_USERNAME_LEN} characters."
        )
    if not re.fullmatch(r"[A-Za-z0-9_]+", username):
        raise ValidationError("Username may only contain letters, numbers, and underscores.")
    return username


def validate_password(raw):
    password = raw or ""
    if len(password) < MIN_PASSWORD_LEN:
        raise ValidationError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        raise ValidationError("Password must contain at least one letter and one number.")
    return password


def validate_contact(raw):
    """Strips spaces, dashes, brackets and a leading +, then requires exactly 10 digits."""
    cleaned = re.sub(r"[\s\-()]", "", (raw or "").strip())
    cleaned = cleaned.lstrip("+")
    if not cleaned.isdigit():
        raise ValidationError("Contact number must contain digits only.")
    if len(cleaned) != CONTACT_DIGITS:
        raise ValidationError(f"Contact number must be exactly {CONTACT_DIGITS} digits.")
    return cleaned


def validate_required_text(raw, field, max_len=100):
    value = (raw or "").strip()
    if not value:
        raise ValidationError(f"{field} is required.")
    if len(value) > max_len:
        raise ValidationError(f"{field} must be {max_len} characters or fewer.")
    return value


def validate_weight_class(raw, allowed):
    value = (raw or "").strip()
    if value not in allowed:
        raise ValidationError("Please choose a valid weight class.")
    return value


def validate_fight_date(raw, today=None):
    """Must be a real ISO date, not in the past, and within MAX_FIGHT_DAYS_AHEAD."""
    today = today or date.today()
    value = (raw or "").strip()
    if not value:
        raise ValidationError("Fight date is required.")
    try:
        fight_date = date.fromisoformat(value)
    except ValueError:
        raise ValidationError("Fight date must be a valid date.")
    if fight_date < today:
        raise ValidationError("Fight date cannot be in the past.")
    if (fight_date - today).days > MAX_FIGHT_DAYS_AHEAD:
        raise ValidationError(
            f"Fight date cannot be more than {MAX_FIGHT_DAYS_AHEAD} days from today."
        )
    return value


def validate_record(wins_raw, losses_raw):
    """Wins and losses must be non-negative whole numbers."""
    wins = _to_number(wins_raw, "Wins", int)
    losses = _to_number(losses_raw, "Losses", int)
    if wins < 0 or losses < 0:
        raise ValidationError("Wins and losses cannot be negative.")
    return wins, losses
