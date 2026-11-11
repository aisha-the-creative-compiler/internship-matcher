"""Transparent, rule-based matching engine.

A program score is the percentage of its required-skill weight matched by the
student. Inactive programs and programs above the student's experience level
are excluded before scoring. Every result includes a skill-by-skill breakdown.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVELS = {"beginner": 1, "intermediate": 2, "advanced": 3}
MAX_RESULTS = 3


def load_catalogue():
    """Load the program catalogue from data/programs.json."""
    path = os.path.join(BASE_DIR, "data", "programs.json")
    with open(path, encoding="utf-8") as f:
        catalogue = json.load(f)
    if not isinstance(catalogue, dict) or not isinstance(catalogue.get("programs"), list):
        raise ValueError("The program catalogue must contain a 'programs' list.")
    return catalogue


def _score_program(program, student_skills_lower):
    """Return score details for one program, safely handling an empty skill list."""
    required = program.get("required_skills") or {}
    if not isinstance(required, dict):
        required = {}

    matched, missing, breakdown = [], [], []
    matched_weight = 0
    total = 0

    for skill, raw_weight in required.items():
        # Catalogue weights are expected to be positive numbers. Invalid weights
        # are treated as zero so a bad entry cannot crash matching or inflate scores.
        weight = raw_weight if (
            isinstance(raw_weight, (int, float))
            and not isinstance(raw_weight, bool)
            and raw_weight > 0
        ) else 0
        has = str(skill).strip().lower() in student_skills_lower
        breakdown.append({"skill": skill, "weight": weight, "matched": has})
        total += weight
        if has:
            matched.append(skill)
            matched_weight += weight
        else:
            missing.append(skill)

    score = round(matched_weight / total * 100) if total else 0
    return score, matched, missing, matched_weight, total, breakdown


def _why(program, matched, matched_weight, total):
    required = program.get("required_skills") or {}
    n_req = len(required) if isinstance(required, dict) else 0
    if not matched:
        return "None of your selected skills are required by this program."
    return (
        f"You have {len(matched)} of the {n_req} skills this program requires "
        f"({', '.join(matched)}). Your matched skill weight is "
        f"{matched_weight} out of {total}."
    )


def match_programs(skills, level, interests=None, top_n=MAX_RESULTS):
    """Return up to three eligible matches and a list of excluded programs."""
    catalogue = load_catalogue()

    if not isinstance(skills, (list, tuple, set)):
        skills = []
    student = {
        skill.strip().lower()
        for skill in skills
        if isinstance(skill, str) and skill.strip()
    }

    if isinstance(interests, str):
        interests = [interests]
    if not isinstance(interests, (list, tuple, set)):
        interests = []
    normalized_interests = {
        interest.strip().lower()
        for interest in interests
        if isinstance(interest, str) and interest.strip()
    }

    student_rank = LEVELS.get(str(level).strip().lower(), LEVELS["beginner"])
    try:
        result_limit = max(0, min(int(top_n), MAX_RESULTS))
    except (TypeError, ValueError):
        result_limit = MAX_RESULTS

    results, excluded = [], []
    for program in catalogue["programs"]:
        if not isinstance(program, dict):
            continue

        name = program.get("name", "Unnamed program")
        status = str(program.get("status", "")).strip().lower()
        if status != "active":
            excluded.append({
                "name": name,
                "reason": "Not currently accepting applications.",
            })
            continue

        min_level = str(program.get("min_level", "beginner")).strip().lower()
        required_rank = LEVELS.get(min_level, LEVELS["beginner"])
        if student_rank < required_rank:
            excluded.append({
                "name": name,
                "reason": f"Requires {min_level} level or above.",
            })
            continue

        score, matched, missing, matched_weight, total, breakdown = _score_program(
            program, student
        )
        if score == 0:
            continue

        track = str(program.get("track", ""))
        results.append({
            "id": program.get("id"),
            "name": name,
            "track": track,
            "score": score,
            "matching_skills": matched,
            "skills_to_strengthen": missing,
            "prerequisites": program.get("prerequisites", []),
            "why": _why(program, matched, matched_weight, total),
            "apply_url": program.get("apply_url", ""),
            "breakdown": breakdown,
            "matched_weight": matched_weight,
            "total_weight": total,
            "_interest": track.strip().lower() in normalized_interests,
        })

    # Track interest is only a tie-breaker; score remains the primary ranking.
    results.sort(key=lambda result: (
        -result["score"],
        not result["_interest"],
        str(result["name"]).lower(),
    ))
    for result in results:
        result.pop("_interest")

    return {
        "results": results[:result_limit],
        "excluded": excluded,
        "catalogue_verified": bool(catalogue.get("catalogue_verified", False)),
    }
