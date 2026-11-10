"""Transparent, rule-based matching engine.

How a score is calculated (no randomness, no hidden model):

    score = (sum of weights of the program's required skills the student has)
            / (sum of weights of ALL the program's required skills) * 100

Before scoring, a program is EXCLUDED if:
  * its status is not "active", or
  * the student's experience level is below the program's min_level.

Every result lists exactly which skills were matched / missing, so the score
can always be checked by hand.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVELS = {"beginner": 1, "intermediate": 2, "advanced": 3}


def load_catalogue():
    path = os.path.join(BASE_DIR, "data", "programs.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _score_program(program, student_skills_lower):
    required = program["required_skills"]
    total = sum(required.values())
    matched, missing, breakdown = [], [], []
    matched_weight = 0
    for skill, weight in required.items():
        has = skill.lower() in student_skills_lower
        breakdown.append({"skill": skill, "weight": weight, "matched": has})
        if has:
            matched.append(skill)
            matched_weight += weight
        else:
            missing.append(skill)
    score = round(matched_weight / total * 100) if total else 0
    return score, matched, missing, matched_weight, total, breakdown


def _why(program, matched, matched_weight, total):
    n_req = len(program["required_skills"])
    if not matched:
        return "None of your selected skills are required by this program."
    return (
        f"You have {len(matched)} of the {n_req} skills this program requires "
        f"({', '.join(matched)}). Your matched skill weight is "
        f"{matched_weight} out of {total}."
    )


def match_programs(skills, level, interests=None, top_n=3):
    """Return the top matches plus the programs that were excluded and why."""
    catalogue = load_catalogue()
    student = {s.strip().lower() for s in skills if isinstance(s, str) and s.strip()}
    interests = {i.strip().lower() for i in (interests or []) if isinstance(i, str)}
    student_rank = LEVELS.get(level, 1)

    results, excluded = [], []
    for p in catalogue["programs"]:
        if p.get("status", "").lower() != "active":
            excluded.append({"name": p["name"], "reason": "Not currently accepting applications."})
            continue
        if student_rank < LEVELS.get(p.get("min_level", "beginner"), 1):
            excluded.append({
                "name": p["name"],
                "reason": f"Requires {p['min_level']} level or above.",
            })
            continue

        score, matched, missing, mw, total, breakdown = _score_program(p, student)
        if score == 0:
            continue  # nothing in common, do not recommend
        results.append({
            "id": p["id"],
            "name": p["name"],
            "track": p["track"],
            "score": score,
            "matching_skills": matched,
            "skills_to_strengthen": missing,
            "prerequisites": p.get("prerequisites", []),
            "why": _why(p, matched, mw, total),
            "apply_url": p.get("apply_url", ""),
            "breakdown": breakdown,
            "matched_weight": mw,
            "total_weight": total,
            "_interest": p["track"].lower() in interests,
        })

    # Highest score first; interest in the program's track only breaks ties.
    results.sort(key=lambda r: (-r["score"], not r["_interest"], r["name"]))
    for r in results:
        r.pop("_interest")

    return {
        "results": results[:top_n],
        "excluded": excluded,
        "catalogue_verified": bool(catalogue.get("catalogue_verified", False)),
    }
