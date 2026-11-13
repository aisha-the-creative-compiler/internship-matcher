// All dynamic content is built with textContent (never innerHTML) so nothing a user
// types or uploads can inject HTML into the page.
const selected = new Set();
const $ = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setStatus(node, message, kind, loading) {
  node.className = "status" + (kind ? " " + kind : "");
  node.textContent = "";
  if (loading) node.appendChild(el("span", "spinner"));
  node.appendChild(document.createTextNode(message || ""));
}

async function getJSON(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (e) {
    throw new Error("Cannot reach the server. Check your internet connection and try again.");
  }
  let data = {};
  try { data = await res.json(); } catch (e) { /* non-JSON response */ }
  if (!res.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}

function updateCount() {
  $("skill-count").textContent = selected.size + " selected";
}

// ---------- Skills ----------
async function loadSkills() {
  const box = $("skills-box");
  try {
    const skills = await getJSON("/api/skills");
    box.textContent = "";
    const groups = {};
    skills.forEach((s) => (groups[s.category] = groups[s.category] || []).push(s.name));
    Object.keys(groups).forEach((cat) => {
      const group = el("div", "group");
      group.appendChild(el("div", "group-title", cat));
      const chips = el("div", "chips");
      groups[cat].forEach((name) => {
        const label = el("label", "chip");
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = name;
        input.dataset.skill = name;
        input.addEventListener("change", () => {
          input.checked ? selected.add(name) : selected.delete(name);
          updateCount();
        });
        label.appendChild(input);
        label.appendChild(el("span", null, name));
        chips.appendChild(label);
      });
      group.appendChild(chips);
      box.appendChild(group);
    });
  } catch (e) {
    box.textContent = "";
    box.appendChild(el("p", "status error", "Could not load skills. " + e.message));
  }
}

function setSkillChecked(name, checked) {
  const input = document.querySelector('input[data-skill="' + CSS.escape(name) + '"]');
  if (input) input.checked = checked;
  checked ? selected.add(name) : selected.delete(name);
}

// ---------- CV upload ----------
async function uploadCV() {
  const status = $("upload-status");
  const file = $("cv-file").files[0];
  if (!file) return setStatus(status, "Please choose a PDF or DOCX file first.", "error");
  const ext = file.name.split(".").pop().toLowerCase();
  if (!["pdf", "docx"].includes(ext))
    return setStatus(status, "Unsupported file type. Please upload a PDF or DOCX file.", "error");
  if (file.size > 5 * 1024 * 1024)
    return setStatus(status, "That file is too large. The maximum size is 5 MB.", "error");
  if (file.size === 0) return setStatus(status, "That file is empty.", "error");

  const btn = $("upload-btn");
  btn.disabled = true;
  setStatus(status, "Reading your CV…", "", true);
  try {
    const form = new FormData();
    form.append("cv", file);
    const data = await getJSON("/api/parse-cv", { method: "POST", body: form });
    data.skills.forEach((s) => setSkillChecked(s, true));
    updateCount();
    $("level").value = data.suggested_level;
    if (data.skills.length === 0) {
      setStatus(status, "We read your CV but found no known skills. Please select your skills below.", "error");
    } else {
      setStatus(status, "Found " + data.skills.length + " skills: " + data.skills.join(", ") +
        ". Review the selection below and adjust your level if needed.", "ok");
    }
  } catch (e) {
    setStatus(status, e.message, "error");
  } finally {
    btn.disabled = false;
  }
}

// ---------- Matching & results ----------
function tags(list, cls) {
  const wrap = el("div");
  list.forEach((t) => wrap.appendChild(el("span", "tag " + cls, t)));
  return wrap;
}

function renderRecommendation(r) {
  const card = el("article", "rec");
  const head = el("div", "rec-head");
  head.appendChild(el("h3", null, r.name));
  head.appendChild(el("span", "score", r.score + "% Match"));
  card.appendChild(head);
  card.appendChild(el("p", "muted small", "Track: " + r.track));

  const why = el("p");
  why.appendChild(el("strong", null, "Why it matches: "));
  why.appendChild(document.createTextNode(r.why));
  card.appendChild(why);

  const have = el("p");
  have.appendChild(el("strong", null, "Matching Skills: "));
  have.appendChild(r.matching_skills.length ? tags(r.matching_skills, "have") : document.createTextNode("None"));
  card.appendChild(have);

  const need = el("p");
  need.appendChild(el("strong", null, "Skills to Strengthen: "));
  need.appendChild(r.skills_to_strengthen.length
    ? tags(r.skills_to_strengthen, "need")
    : document.createTextNode("None. You have every required skill!"));
  card.appendChild(need);

  const pre = el("p");
  pre.appendChild(el("strong", null, "Prerequisites:"));
  card.appendChild(pre);
  const ul = el("ul");
  r.prerequisites.forEach((p) => ul.appendChild(el("li", null, p)));
  card.appendChild(ul);

  const details = el("details");
  details.appendChild(el("summary", null, "How was this score calculated?"));
  details.appendChild(el("p", "muted",
    "Score = matched skill weight ÷ total skill weight × 100 = " +
    r.matched_weight + " ÷ " + r.total_weight + " × 100 = " + r.score + "%."));
  const table = el("table");
  const hr = el("tr");
  ["Required skill", "Weight", "You have it?"].forEach((h) => hr.appendChild(el("th", null, h)));
  table.appendChild(hr);
  r.breakdown.forEach((b) => {
    const tr = el("tr");
    tr.appendChild(el("td", null, b.skill));
    tr.appendChild(el("td", null, String(b.weight)));
    tr.appendChild(el("td", null, b.matched ? "Yes" : "No"));
    table.appendChild(tr);
  });
  details.appendChild(table);
  card.appendChild(details);

  const actions = el("div", "rec-actions");
  if (r.apply_url) {
    const a = el("a", "btn", "Apply on official page");
    a.href = r.apply_url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    actions.appendChild(a);
  } else {
    actions.appendChild(el("span", "btn btn-disabled", "Apply link not available yet"));
  }
  card.appendChild(actions);
  return card;
}

async function runMatch() {
  const status = $("match-status");
  if (selected.size === 0)
    return setStatus(status, "Please select at least one skill (or upload your CV) first.", "error");

  const btn = $("match-btn");
  btn.disabled = true;
  setStatus(status, "Finding your best matches…", "", true);
  try {
    const interests = [...document.querySelectorAll("#interests input:checked")].map((i) => i.value);
    const data = await getJSON("/api/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skills: [...selected], level: $("level").value, interests }),
    });
    setStatus(status, "", "");
    renderResults(data);
  } catch (e) {
    setStatus(status, e.message, "error");
  } finally {
    btn.disabled = false;
  }
}

function renderResults(data) {
  $("results-section").hidden = false;
  const box = $("results");
  box.textContent = "";

  const warn = $("catalogue-warning");
  warn.hidden = data.catalogue_verified;
  warn.textContent = data.catalogue_verified ? "" :
    "Note: this demo is using a sample program catalogue, not the official Internlytic list.";

  if (data.results.length === 0) {
    const empty = el("div", "card empty");
    empty.appendChild(el("h3", null, "No matching programs found"));
    empty.appendChild(el("p", "muted",
      "None of the active programs match your current skills and level. Try adding more skills, " +
      "or explore the catalogue below to see what each program requires."));
    const a = el("a", "btn btn-ghost", "Explore the catalogue");
    a.href = "#catalogue";
    empty.appendChild(a);
    box.appendChild(empty);
  } else {
    data.results.forEach((r) => box.appendChild(renderRecommendation(r)));
  }

  const ex = $("excluded");
  ex.textContent = "";
  ex.hidden = data.excluded.length === 0;
  if (data.excluded.length) {
    ex.appendChild(el("h3", null, "Programs you do not qualify for yet"));
    const ul = el("ul");
    data.excluded.forEach((p) => ul.appendChild(el("li", null, p.name + ": " + p.reason)));
    ex.appendChild(ul);
  }
  $("results-section").scrollIntoView({ behavior: "smooth" });
}

// ---------- Catalogue ----------
async function loadCatalogue() {
  const list = $("catalogue-list");
  try {
    const data = await getJSON("/api/programs");
    list.textContent = "";
    const note = $("catalogue-note");
    note.hidden = Boolean(data.catalogue_verified);
    note.textContent = data.catalogue_verified
      ? ""
      : "Sample catalogue shown for demo purposes. Replace data/programs.json with the official programs.";
    if (!data.programs.length) {
      list.appendChild(el("p", "muted", "No programs are available right now."));
      return;
    }
    data.programs.forEach((p) => {
      const card = el("article", "prog");
      if (p.image_url) {
        const image = document.createElement("img");
        image.className = "prog-image";
        image.src = p.image_url;
        image.alt = p.name + " internship track";
        image.loading = "lazy";
        card.appendChild(image);
      }
      const meta = el("div", "prog-meta");
      meta.appendChild(el("span", "verified", "Verified"));
      meta.appendChild(el("span", "muted small", "Internship"));
      card.appendChild(meta);
      card.appendChild(el("h3", null, p.name));
      if (p.description) card.appendChild(el("p", "prog-description", p.description));
      card.appendChild(el("p", "muted small", p.track + " · " + p.min_level + " level"));
      card.appendChild(tags(Object.keys(p.required_skills), "have"));
      if (p.apply_url) {
        const actions = el("div", "rec-actions");
        const a = el("a", "btn", "Apply Now");
        a.href = p.apply_url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        actions.appendChild(a);
        card.appendChild(actions);
      }
      list.appendChild(card);
    });
    const journey = el("div", "catalogue-cta");
    const journeyLink = el("a", "btn", "Begin your journey");
    journeyLink.href = "https://forms.gle/zNGnQWfTZMxNCuRc9";
    journeyLink.target = "_blank";
    journeyLink.rel = "noopener noreferrer";
    journey.appendChild(journeyLink);
    list.appendChild(journey);
  } catch (e) {
    list.textContent = "";
    list.appendChild(el("p", "status error", "Could not load programs. " + e.message));
  }
}

// ---------- Paste text ----------
async function analyseText() {
  const status = $("text-status");
  const text = $("cv-text").value;
  if (!text.trim()) return setStatus(status, "Please paste some text from your CV first.", "error");
  const btn = $("text-btn");
  btn.disabled = true;
  setStatus(status, "Reading your text…", "", true);
  try {
    const data = await getJSON("/api/parse-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    data.skills.forEach((s) => setSkillChecked(s, true));
    updateCount();
    $("level").value = data.suggested_level;
    if (data.skills.length === 0) {
      setStatus(status, "No known skills found in that text. Please select your skills below.", "error");
    } else {
      setStatus(status, "Found " + data.skills.length + " skills: " + data.skills.join(", ") +
        ". Review the selection below.", "ok");
    }
  } catch (e) {
    setStatus(status, e.message, "error");
  } finally {
    btn.disabled = false;
  }
}

// ---------- Demo profiles ----------
const DEMO_PROFILES = [
  { name: "AI/ML student", level: "intermediate",
    note: "Python, ML, data libraries",
    skills: ["Python", "Pandas", "NumPy", "Machine Learning", "scikit-learn", "Statistics", "Git"] },
  { name: "Web developer", level: "beginner",
    note: "HTML, CSS, JavaScript",
    skills: ["HTML", "CSS", "JavaScript", "Git"] },
  { name: "Data analyst", level: "beginner",
    note: "SQL, Excel, charts",
    skills: ["SQL", "Excel", "Python", "Data Visualization"] },
  { name: "UI/UX designer", level: "beginner",
    note: "Figma, wireframes, user research",
    skills: ["UI/UX Design", "Figma", "Wireframing", "Prototyping", "User Research"] },
  { name: "Full-stack builder", level: "intermediate",
    note: "React, Node, SQL, APIs",
    skills: ["HTML", "CSS", "JavaScript", "React", "Node.js", "SQL", "REST APIs", "Git"] },
];

function loadDemoProfile(profile) {
  document.querySelectorAll("#skills-box input[data-skill]").forEach((i) => (i.checked = false));
  selected.clear();
  profile.skills.forEach((s) => setSkillChecked(s, true));
  updateCount();
  $("level").value = profile.level;
  setStatus($("demo-status"), "Loaded the \"" + profile.name + "\" profile. Now press \"Match me with programs\".", "ok");
}

function renderDemoProfiles() {
  const box = $("demo-profiles");
  DEMO_PROFILES.forEach((p) => {
    const b = el("button", "demo-btn");
    b.type = "button";
    b.appendChild(el("strong", null, p.name));
    b.appendChild(el("span", null, p.note));
    b.addEventListener("click", () => loadDemoProfile(p));
    box.appendChild(b);
  });
}

$("upload-btn").addEventListener("click", uploadCV);
$("match-btn").addEventListener("click", runMatch);
loadSkills();
loadCatalogue();
