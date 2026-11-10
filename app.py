from flask import Flask, jsonify, render_template, request

from cv_parser import CVError, get_skill_catalogue, parse_cv
from matcher import LEVELS, load_catalogue, match_programs

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit


def error(message, status=400):
    return jsonify({"error": message}), status


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/skills")
def api_skills():
    return jsonify(get_skill_catalogue())


@app.route("/api/programs")
def api_programs():
    cat = load_catalogue()
    return jsonify({
        "catalogue_verified": cat.get("catalogue_verified", False),
        "programs": cat["programs"],
    })


@app.route("/api/parse-cv", methods=["POST"])
def api_parse_cv():
    file = request.files.get("cv")
    if file is None or not file.filename:
        return error("Please choose a file to upload.")
    data = file.read()
    if not data:
        return error("The uploaded file is empty.")
    try:
        return jsonify(parse_cv(file.filename, data))
    except CVError as e:
        return error(str(e), 422)


@app.route("/api/match", methods=["POST"])
def api_match():
    body = request.get_json(silent=True) or {}
    skills = body.get("skills")
    level = body.get("level", "beginner")
    interests = body.get("interests", [])

    if not isinstance(skills, list) or not [s for s in skills if isinstance(s, str) and s.strip()]:
        return error("Please select at least one skill before matching.")
    if len(skills) > 60:
        return error("Too many skills selected.")
    if level not in LEVELS:
        return error("Please choose a valid experience level.")
    if not isinstance(interests, list):
        interests = []
    return jsonify(match_programs(skills, level, interests))


@app.errorhandler(413)
def too_large(_):
    return error("That file is too large. The maximum size is 5 MB.", 413)


@app.errorhandler(404)
def not_found(_):
    return error("Not found.", 404)


@app.errorhandler(500)
def server_error(_):
    return error("Something went wrong on our side. Please try again.", 500)


if __name__ == "__main__":
    app.run(debug=True)
