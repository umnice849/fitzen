"""
Unit tests for validation.py — no Flask, no database, just the rules themselves.

Each test states the rule being checked so the output doubles as evidence that
a specific success criterion is enforced.
"""
from validation import (
    ValidationError, validate_age, validate_weight, validate_height,
    validate_skill_level, validate_username, validate_password, validate_contact,
    validate_fight_date, validate_record, validate_weight_class,
)
from matching import WEIGHT_CLASSES
from datetime import date, timedelta

passed = failed = 0


def check(label, fn, should_pass, expected=None):
    """Runs fn(); asserts it either passes (optionally returning `expected`)
    or raises ValidationError, depending on should_pass."""
    global passed, failed
    try:
        result = fn()
        if not should_pass:
            print(f"FAIL - {label}: expected rejection but it was accepted")
            failed += 1
            return
        if expected is not None and result != expected:
            print(f"FAIL - {label}: expected {expected!r}, got {result!r}")
            failed += 1
            return
        print(f"PASS - {label}")
        passed += 1
    except ValidationError as e:
        if should_pass:
            print(f"FAIL - {label}: unexpectedly rejected ({e})")
            failed += 1
        else:
            print(f"PASS - {label} (rejected: {e})")
            passed += 1


print("=== AGE (boundary testing: 15 / 16 / 80 / 81) ===")
check("age 15 rejected (below minimum)", lambda: validate_age(15), False)
check("age 16 accepted (exact minimum)", lambda: validate_age(16), True, 16)
check("age 80 accepted (exact maximum)", lambda: validate_age(80), True, 80)
check("age 81 rejected (above maximum)", lambda: validate_age(81), False)
check("age 150 rejected (typo)", lambda: validate_age(150), False)
check("age 'abc' rejected (non-numeric)", lambda: validate_age("abc"), False)
check("age empty rejected", lambda: validate_age(""), False)

print("\n=== WEIGHT ===")
check("weight 0 rejected", lambda: validate_weight(0), False)
check("weight -5 rejected (negative)", lambda: validate_weight(-5), False)
check("weight 70.5 accepted (normal)", lambda: validate_weight(70.5), True, 70.5)
check("weight 300 accepted (exact maximum)", lambda: validate_weight(300), True, 300.0)
check("weight 500 rejected (absurd)", lambda: validate_weight(500), False)

print("\n=== HEIGHT ===")
check("height blank accepted (optional)", lambda: validate_height(""), True, None)
check("height 175 accepted (cm)", lambda: validate_height(175), True, 175.0)
check("height 1.75 rejected (metres, not cm)", lambda: validate_height(1.75), False)
check("height 300 rejected (too tall)", lambda: validate_height(300), False)

print("\n=== SKILL LEVEL (schema says 1-10) ===")
check("skill 0 rejected", lambda: validate_skill_level(0), False)
check("skill 1 accepted (minimum)", lambda: validate_skill_level(1), True, 1)
check("skill 10 accepted (maximum)", lambda: validate_skill_level(10), True, 10)
check("skill 999 rejected", lambda: validate_skill_level(999), False)

print("\n=== USERNAME ===")
check("username 'ab' rejected (too short)", lambda: validate_username("ab"), False)
check("username 'aarav_k' accepted", lambda: validate_username("aarav_k"), True, "aarav_k")
check("username with space rejected", lambda: validate_username("aarav k"), False)
check("username with symbols rejected", lambda: validate_username("aarav!!"), False)
check("username 30 chars rejected (too long)", lambda: validate_username("a" * 30), False)

print("\n=== PASSWORD ===")
check("password 'short1' rejected (under 8)", lambda: validate_password("short1"), False)
check("password 'alllettersonly' rejected (no digit)", lambda: validate_password("alllettersonly"), False)
check("password '12345678' rejected (no letter)", lambda: validate_password("12345678"), False)
check("password 'fightPass1' accepted", lambda: validate_password("fightPass1"), True)

print("\n=== CONTACT NUMBER (exactly 10 digits) ===")
check("contact '9800000001' accepted", lambda: validate_contact("9800000001"), True, "9800000001")
check("contact '980-000-0001' accepted (dashes stripped)",
      lambda: validate_contact("980-000-0001"), True, "9800000001")
check("contact '980 000 0001' accepted (spaces stripped)",
      lambda: validate_contact("980 000 0001"), True, "9800000001")
check("contact '12345' rejected (too short)", lambda: validate_contact("12345"), False)
check("contact '98000000012' rejected (11 digits)", lambda: validate_contact("98000000012"), False)
check("contact 'abcdefghij' rejected (letters)", lambda: validate_contact("abcdefghij"), False)

print("\n=== FIGHT DATE ===")
today = date(2026, 6, 1)
check("yesterday rejected (past)",
      lambda: validate_fight_date((today - timedelta(days=1)).isoformat(), today=today), False)
check("today accepted (boundary)",
      lambda: validate_fight_date(today.isoformat(), today=today), True)
check("30 days ahead accepted",
      lambda: validate_fight_date((today + timedelta(days=30)).isoformat(), today=today), True)
check("366 days ahead rejected (too far)",
      lambda: validate_fight_date((today + timedelta(days=366)).isoformat(), today=today), False)
check("'not-a-date' rejected", lambda: validate_fight_date("not-a-date", today=today), False)

print("\n=== WIN/LOSS RECORD ===")
check("wins 5 losses 3 accepted", lambda: validate_record(5, 3), True, (5, 3))
check("negative wins rejected", lambda: validate_record(-1, 3), False)
check("negative losses rejected", lambda: validate_record(5, -2), False)

print("\n=== WEIGHT CLASS ===")
check("valid class accepted", lambda: validate_weight_class("Lightweight", WEIGHT_CLASSES), True)
check("made-up class rejected", lambda: validate_weight_class("Superheavy", WEIGHT_CLASSES), False)

print(f"\n{'=' * 50}")
print(f"Validation tests: {passed} passed, {failed} failed")
if failed:
    raise SystemExit(1)
print("All validation tests passed.")
