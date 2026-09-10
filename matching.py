"""
Matchmaking algorithm for FITZEN.

Given a fighter requesting a match, this module finds and ranks candidate
opponents using a weighted scoring formula:

    score = (skill_diff * 0.5) + (ratio_diff * 0.3) + (age_diff * 0.2)

A LOWER score means a CLOSER match. Candidates are pulled from the same
weight class first; if none are available, the algorithm falls back to the
next closest weight class (above, then below) in WEIGHT_CLASSES.

This module is deliberately independent of Flask and the database, so it
can be unit-tested on its own (see test_matching.py).
"""

WEIGHT_CLASSES = [
    "Flyweight",
    "Bantamweight",
    "Featherweight",
    "Lightweight",
    "Welterweight",
    "Middleweight",
    "Light Heavyweight",
    "Heavyweight",
]


class InvalidFighterDataError(Exception):
    """Raised when a fighter dict is missing a required field or has a
    value that can't be used in scoring (e.g. a non-numeric skill level)."""
    pass


class Matchmaker:
    """
    Encapsulates the matchmaking algorithm and its weighting scheme.

    Keeping this as a class (rather than free functions) means the scoring
    weights are configuration carried on the object, not scattered module
    constants — a future extension (e.g. a gym wanting to weight win/loss
    record more heavily) only needs a differently-configured Matchmaker,
    with no change to the matching logic itself.
    """

    def __init__(self, weight_skill=0.5, weight_ratio=0.3, weight_age=0.2):
        self.weight_skill = weight_skill
        self.weight_ratio = weight_ratio
        self.weight_age = weight_age

    @staticmethod
    def _validate_fighter(fighter, label="fighter"):
        required = ("age", "skill_level", "wins", "losses", "weight_class")
        missing = [field for field in required if field not in fighter]
        if missing:
            raise InvalidFighterDataError(
                f"{label} is missing required field(s): {', '.join(missing)}"
            )
        for field in ("age", "skill_level", "wins", "losses"):
            if not isinstance(fighter[field], (int, float)):
                raise InvalidFighterDataError(
                    f"{label}.{field} must be numeric, got {type(fighter[field]).__name__}"
                )

    @staticmethod
    def win_loss_ratio(fighter):
        """Wins / total fights. A fighter with 0 fights gets a ratio of 0."""
        total = fighter["wins"] + fighter["losses"]
        if total == 0:
            return 0.0
        return fighter["wins"] / total

    def compute_score(self, fighter, candidate):
        """Lower = closer match. Raises InvalidFighterDataError on bad input."""
        self._validate_fighter(fighter, "fighter")
        self._validate_fighter(candidate, "candidate")
        skill_diff = abs(fighter["skill_level"] - candidate["skill_level"])
        ratio_diff = abs(self.win_loss_ratio(fighter) - self.win_loss_ratio(candidate))
        age_diff = abs(fighter["age"] - candidate["age"])
        return (
            (skill_diff * self.weight_skill)
            + (ratio_diff * self.weight_ratio)
            + (age_diff * self.weight_age)
        )

    @staticmethod
    def _nearby_weight_classes(weight_class, distance):
        """Return weight classes `distance` steps above/below the given one."""
        if weight_class not in WEIGHT_CLASSES:
            return []
        idx = WEIGHT_CLASSES.index(weight_class)
        results = []
        if idx - distance >= 0:
            results.append(WEIGHT_CLASSES[idx - distance])
        if idx + distance < len(WEIGHT_CLASSES):
            results.append(WEIGHT_CLASSES[idx + distance])
        return results

    def find_opponent(self, fighter, all_candidates, weight_class=None):
        """
        fighter: dict with keys age, skill_level, wins, losses, id
        all_candidates: list of fighter dicts already filtered to exclude the
            requesting fighter and anyone they're already matched with on this date
        weight_class: the class to search in; defaults to the fighter's own class

        Returns a dict describing the outcome:
            {"result": "none"}
            {"result": "fallback", "class": <wc>, "match"/"matches": ...}
            {"result": "single", "match": <candidate>}
            {"result": "tie", "matches": [c1, c2]}
            {"result": "match", "match": <candidate>, "runner_ups": [...]}

        Raises InvalidFighterDataError if `fighter` itself is malformed
        (candidate-level errors are skipped rather than raised, so one bad
        record in the database doesn't take down the whole search).
        """
        self._validate_fighter(fighter, "fighter")
        target_class = weight_class or fighter["weight_class"]

        def in_class(wc):
            return [c for c in all_candidates if c.get("weight_class") == wc]

        pool = in_class(target_class)
        used_fallback = False
        fallback_class = None

        if not pool:
            for wc in self._nearby_weight_classes(target_class, 1):
                pool.extend(in_class(wc))
            if pool:
                used_fallback = True
                fallback_class = ", ".join(self._nearby_weight_classes(target_class, 1))

        if not pool:
            return {"result": "none"}

        scored = []
        for candidate in pool:
            try:
                scored.append({"fighter": candidate, "score": self.compute_score(fighter, candidate)})
            except InvalidFighterDataError:
                # Skip a malformed candidate record rather than crashing the
                # whole search — one bad row in the database shouldn't stop
                # every other fighter from finding a match.
                continue
        scored.sort(key=lambda entry: entry["score"])

        if not scored:
            return {"result": "none"}

        if len(scored) == 1:
            return {
                "result": "fallback" if used_fallback else "single",
                "class": fallback_class,
                "match": scored[0]["fighter"],
                "score": scored[0]["score"],
            }

        lowest_score = scored[0]["score"]
        tied = [entry for entry in scored if entry["score"] == lowest_score]

        if len(tied) > 1:
            return {
                "result": "tie",
                "class": fallback_class,
                "matches": [{"fighter": t["fighter"], "score": t["score"]} for t in tied],
            }

        return {
            "result": "fallback" if used_fallback else "match",
            "class": fallback_class,
            "match": scored[0]["fighter"],
            "score": scored[0]["score"],
            "runner_ups": [{"fighter": e["fighter"], "score": e["score"]} for e in scored[1:4]],
        }


# Module-level default instance + thin wrapper functions, so existing code
# (and existing tests) that calls find_opponent()/compute_score() directly
# keeps working unchanged.
_default_matchmaker = Matchmaker()


def compute_score(fighter, candidate):
    return _default_matchmaker.compute_score(fighter, candidate)


def win_loss_ratio(fighter):
    return _default_matchmaker.win_loss_ratio(fighter)


def find_opponent(fighter, all_candidates, weight_class=None):
    return _default_matchmaker.find_opponent(fighter, all_candidates, weight_class)
