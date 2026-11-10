"""Run with:  python -m unittest discover tests   (from the project folder)"""
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
        self.assertEqual(top["name"], "Frontend Development Internship")
        # HTML 3 + CSS 3 + JS 3 = 9 out of 14 total weight -> 64%
        self.assertEqual(top["score"], 64)
        self.assertEqual(top["matching_skills"], ["HTML", "CSS", "JavaScript"])
        self.assertIn("Responsive Layouts", top["skills_to_strengthen"])

    def test_level_filter_excludes_intermediate_programs_for_beginners(self):
        out = match_programs(["Python", "Machine Learning"], "beginner")
        names = [r["name"] for r in out["results"]]
        self.assertNotIn("AI & Machine Learning Internship", names)
        self.assertTrue(any("AI & Machine Learning" in e["name"] for e in out["excluded"]))

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

    def test_bad_files_raise_friendly_errors(self):
        with self.assertRaises(CVError):
            extract_text("cv.txt", b"hello")
        with self.assertRaises(CVError):
            extract_text("cv.pdf", b"not really a pdf")
        with self.assertRaises(CVError):
            extract_text("cv.docx", b"not really a docx")


if __name__ == "__main__":
    unittest.main()
