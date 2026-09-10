from matching import find_opponent, compute_score, Matchmaker, InvalidFighterDataError

def f(id, age, skill, wins, losses, wc):
    return {"id": id, "age": age, "skill_level": skill, "wins": wins, "losses": losses, "weight_class": wc}

requester = f(1, 24, 7, 13, 7, "Lightweight")  # ratio = 0.65

print("--- Test 1: clear best match among several ---")
candidates = [
    f(2, 26, 6, 6, 4, "Lightweight"),   # ratio 0.60 -> score 0.915 (worked out earlier)
    f(3, 22, 8, 8, 2, "Lightweight"),   # ratio 0.80 -> score 0.945
    f(4, 40, 2, 1, 9, "Lightweight"),   # far off -> high score
]
result = find_opponent(requester, candidates)
assert result["result"] == "match", result
assert result["match"]["id"] == 2, "expected fighter 2 (lowest score) to win"
print("PASS - fighter", result["match"]["id"], "score", round(result["score"], 3))

print("\n--- Test 2: single candidate in class ---")
result = find_opponent(requester, [f(5, 25, 7, 10, 5, "Lightweight")])
assert result["result"] == "single"
assert result["match"]["id"] == 5
print("PASS - single candidate auto-suggested:", result["match"]["id"])

print("\n--- Test 3: tie between two candidates ---")
tie_candidates = [
    f(6, 24, 7, 13, 7, "Lightweight"),  # identical stats to requester -> score 0
    f(7, 24, 7, 13, 7, "Lightweight"),  # identical stats to requester -> score 0
]
result = find_opponent(requester, tie_candidates)
assert result["result"] == "tie"
assert len(result["matches"]) == 2
print("PASS - tie detected between", [m["fighter"]["id"] for m in result["matches"]])

print("\n--- Test 4: no one in class, falls back to nearby class ---")
fallback_candidates = [f(8, 24, 7, 10, 5, "Welterweight")]  # one class up from Lightweight
result = find_opponent(requester, fallback_candidates)
assert result["result"] == "fallback"
assert result["match"]["id"] == 8
print("PASS - fell back to", result["class"], "and found fighter", result["match"]["id"])

print("\n--- Test 5: nobody available anywhere nearby ---")
result = find_opponent(requester, [f(9, 24, 7, 10, 5, "Heavyweight")])
assert result["result"] == "none"
print("PASS - correctly reports no candidates available")

print("\nAll matching algorithm tests passed.")

print("\n--- Test 6: Matchmaker class with custom weights ---")
custom = Matchmaker(weight_skill=0.8, weight_ratio=0.1, weight_age=0.1)
score_custom = custom.compute_score(requester, f(2, 26, 6, 6, 4, "Lightweight"))
score_default = compute_score(requester, f(2, 26, 6, 6, 4, "Lightweight"))
assert score_custom != score_default, "custom weights should change the score"
print(f"PASS - custom-weighted score ({score_custom:.3f}) differs from default ({score_default:.3f})")

print("\n--- Test 7: missing field raises InvalidFighterDataError ---")
broken_fighter = {"id": 99, "age": 24, "skill_level": 7, "wins": 10}  # no 'losses', no 'weight_class'
try:
    find_opponent(broken_fighter, candidates)
    raise AssertionError("expected InvalidFighterDataError to be raised")
except InvalidFighterDataError as e:
    print(f"PASS - raised InvalidFighterDataError as expected: {e}")

print("\n--- Test 8: one malformed candidate is skipped, not fatal ---")
mixed_candidates = [
    f(2, 26, 6, 6, 4, "Lightweight"),
    {"id": 50, "age": 25, "weight_class": "Lightweight"},  # missing skill_level/wins/losses
]
result = find_opponent(requester, mixed_candidates)
assert result["result"] == "single"
assert result["match"]["id"] == 2
print("PASS - malformed candidate record skipped, remaining valid one auto-suggested")

print("\nAll OOP / exception-handling tests passed.")
