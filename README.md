# Internlytic AI Internship Matcher

A Flask web app that reads a student's CV (PDF/DOCX) or manually selected skills and matches them against internship programs using a **transparent, rule-based scoring formula**. It shows the top 1-3 matches, matching skills, skills to strengthen, prerequisites and the official apply link.

## Run it on your computer (VS Code)

1. Open the `internship-matcher` folder in VS Code (File > Open Folder).
2. Open a terminal (Terminal > New Terminal) and run:

   **Windows**
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
   **Mac / Linux**
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```
3. Open http://127.0.0.1:5000 in your browser.

Run the tests with `python -m unittest discover tests`.

## Project structure

```
app.py              Flask server and API routes
matcher.py          Scoring and eligibility logic
cv_parser.py        PDF/DOCX text extraction and skill detection
data/programs.json  Program catalogue (EDIT THIS with the official programs)
data/skills.json    Skill dictionary with aliases (JS -> JavaScript, etc.)
templates/index.html, static/style.css, static/app.js   Frontend
tests/              Unit tests
```

## IMPORTANT: replace the sample catalogue

`data/programs.json` currently holds **sample placeholder programs** so the app runs. The brief requires recommendations to come from real, verified programs, so before submitting:

1. Get the official program list and apply links from the Internlytic portal or your mentor.
2. Edit `data/programs.json`: one entry per program with `name`, `track`, `required_skills` (skill: weight 1-3), `min_level`, `prerequisites`, `status` and `apply_url`.
3. Use skill names that exist in `data/skills.json` (add new skills and aliases there if needed).
4. Set `"catalogue_verified": true`. This removes the "sample catalogue" notices in the UI.

## How matching works

- A program is **excluded** if its status is not `active`, or the student's level is below `min_level`.
- Otherwise: `score = matched skill weight / total skill weight x 100`.
- Programs with a score of 0 are not recommended. The top 3 by score are shown.
- Interests only break ties between equal scores.
- Each result shows a table of every required skill, its weight, and whether the student has it, so every score can be checked by hand.

## Privacy

Uploaded CVs are read in memory to find skills and are never saved to disk or a database.

## Deploy on Render (free)

1. Push this folder to a GitHub repository.
2. On render.com: New > Web Service > connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. After it deploys, open the URL and test the whole flow (free instances sleep, so the first load can take about a minute).
