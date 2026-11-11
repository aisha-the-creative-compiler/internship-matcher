
"""Run with: python -m unittest discover tests (from the project folder)"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matcher import match_programs  # noqa: E402
from cv_parser import CVError, estimate_level, extract_skills, extract_text  # noqa: E402


class MatcherTests(unittest.TestCase):

    def test_frontend_student_gets_frontend_first(self):
        out = match_programs(["HTML", "CSS", "JavaScript"], "beginner")
        top = out["results"][0]
        self.assertEqual(top["name"], "Front End Development")

        # HTML 3 + CSS 3 + JS 3 = 9 out of 17 total weight -> 53%
        self.assertEqual(top["score"], 53)

        self.assertEqual(top["matching_skills"], ["HTML", "CSS", "JavaScript"])
        self.assertIn("Responsive Layouts", top["skills_to_strengthen"])

    def test_level_filter_excludes_programs_above_student_level(self):
        import matcher
        original = matcher.load_catalogue
        cat = original()
        cat["programs"][0]["min_level"] = "advanced"  # Artificial Intelligence
        matcher.load_catalogue = lambda: cat
        try:
            out = match_programs(["Python", "Machine Learning"], "beginner")
        finally:
            matcher.load_catalogue = original
        self.assertNotIn("Artificial Intelligence", [r["name"] for r in out["results"]])
        self.assertTrue(any(e["name"] == "Artificial Intelligence" for e in out["excluded"]))

    def test_inactive_programs_are_excluded(self):
        import matcher
        original = matcher.load_catalogue
        cat = original()
        cat["programs"][1]["status"] = "closed"  # Full Stack Web Development
        matcher.load_catalogue = lambda: cat
        try:
            out = match_programs(["JavaScript", "Node.js"], "advanced")
        finally:
            matcher.load_catalogue = original
        self.assertNotIn("Full Stack Web Development", [r["name"] for r in out["results"]])

    def test_designer_gets_ui_ux(self):
        out = match_programs(["Figma", "Wireframing", "UI/UX Design"], "beginner")
        self.assertEqual(out["results"][0]["name"], "UI/UX Design")

    def test_prompt_engineer_gets_prompt_engineering(self):
        out = match_programs(["Prompt Engineering", "LLMs"], "beginner")
        self.assertEqual(out["results"][0]["name"], "Prompt Engineering")

    def test_no_overlap_means_no_results(self):
        out = match_programs(["Tableau"], "advanced")
        self.assertEqual(out["results"], [])

    def test_never_more_than_three(self):
        out = match_programs(["Python", "Git", "SQL", "HTML", "CSS", "JavaScript"], "advanced")
        self.assertLessEqual(len(out["results"]), 3)

    def test_same_input_same_output(self):
        a = match_programs(["Python", "SQL"], "intermediate")
        b = match_programs(["Python", "SQL"], "intermediate")
        self.assertEqual(a, b)


class ParserTests(unittest.TestCase):

    def test_skill_aliases(self):
        found = extract_skills("Built apps with JS, ReactJS and sklearn. Used GitHub daily.")
        for s in ["JavaScript", "React", "scikit-learn", "Git"]:
            self.assertIn(s, found)

    def test_no_partial_word_matches(self):
        self.assertNotIn("Git", extract_skills("I am digital and legitimate"))

    def test_level_estimate(self):
        self.assertEqual(estimate_level("Student with class projects"), "beginner")
        self.assertEqual(estimate_level("2 years experience"), "intermediate")
        self.assertEqual(estimate_level("5+ years of work"), "advanced")

    def test_parse_text(self):
        from cv_parser import parse_text
        out = parse_text("Skills: Python, SQL and Git. 2 years experience.")
        self.assertEqual(set(out["skills"]), {"Git", "SQL", "Python"})
        self.assertEqual(out["suggested_level"], "intermediate")
        with self.assertRaises(CVError):
            parse_text("   ")
        with self.assertRaises(CVError):
            parse_text("x" * 20001)

    def test_demo_profiles_only_use_known_skills(self):
        import json
        import re
        known = {s["name"] for s in json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "skills.json"), encoding="utf-8"))}
        js = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "app.js"), encoding="utf-8").read()
        block = js[js.index("const DEMO_PROFILES"):js.index("function loadDemoProfile")]
        for arr in re.findall(r"skills:\s*\[(.*?)\]", block, re.S):
            for s in re.findall(r'"([^"]+)"', arr):
                self.assertIn(s, known)

    def test_bad_files_raise_friendly_errors(self):
        with self.assertRaises(CVError):
            extract_text("cv.txt", b"hello")
        with self.assertRaises(CVError):
            extract_text("cv.pdf", b"not really a pdf")
        with self.assertRaises(CVError):
            extract_text("cv.docx", b"not really a docx")


if __name__ == "__main__":
    unittest.main()


