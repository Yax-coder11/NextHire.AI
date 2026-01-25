
import os
import sqlite3
import io
from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "placement_secret_key"

DB_NAME = "database.db"


# ---------------- DB CONNECTION ----------------
def get_db():
    return sqlite3.connect(DB_NAME)


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- SIGNUP PAGE ----------------
@app.route("/signup")
def signup_page():
    return render_template("signup.html")


# ---------------- LOGIN PAGE ----------------
@app.route("/login_page")
def login_page():
    return render_template("login.html")

# ---------------- RESUME DETAILS ----------------
@app.route("/dashboard")
def resume():
    return render_template("resume.html")

# ---------------- RESUME PREVIEW ----------------
@app.route("/resumePreview")
def preview():
    return render_template("resume_template.html")

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        # firstName = data["firstName"].strip()
        # lastName = data["lastName"].strip()
        email = data["email"].strip()
        password = data["password"].strip()

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT
        )
        """)

        cur.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, password)
        )

        conn.commit()
        conn.close()

        return jsonify({"success": True, "redirect": "/login_page"})

    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "User already exists"})
    except Exception as e:
        print("SIGNUP ERROR:", e)
        return jsonify({"success": False})


# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email = data["email"].strip()
        password = data["password"].strip()

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cur.fetchone()
        conn.close()

        if user:
            session["user_email"] = email
            return jsonify({"success": True, "redirect": "/"})

        return jsonify({"success": False})

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"success": False})

# ---------------- SAVE RESUME (TXT ONLY) ----------------
@app.route("/save_resume", methods=["POST"])
def save_resume():
    try:
        if "user_email" not in session:
            return jsonify({"success": False, "message": "Login required"})

        data = request.get_json()

        user_email = session["user_email"]
        name = data["name"]
        phone = data["phone"]
        email = data["email"]
        degree = data["degree"]
        cgpa = data["cgpa"]
        skills = data["skills"]
        projects = data["projects"]

        score, missing_skills = calculate_resume_score(
            cgpa=cgpa,
            skills=skills,
            projects=projects,
            fields_present=True
        )


        session["last_score"] = score
        session["last_missing_skills"] = missing_skills



        # -------- Resume Text --------
        resume_text = f"""{name.upper()}
----------------------------------------
{degree} | CGPA: {cgpa}

CONTACT
Phone: {phone}
Email: {email}

SKILLS
----------------------------------------
"""

        for s in skills.split(","):
            resume_text += f"- {s.strip()}\n"

        resume_text += f"""

PROJECTS
----------------------------------------
{projects}
"""

        # -------- Save TXT --------
        os.makedirs("resumes", exist_ok=True)
        file_name = name.replace(" ", "_") + ".txt"
        file_path = f"resumes/{file_name}"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(resume_text)

        # -------- Save DB --------
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            name TEXT,
            phone TEXT,
            email TEXT,
            degree TEXT,
            cgpa TEXT,
            skills TEXT,
            projects TEXT,
            file_path TEXT
        )
        """)

        cur.execute("""
        INSERT INTO resumes (
            user_email, name, phone, email,
            degree, cgpa, skills, projects, file_path
        )
        VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            user_email, name, phone, email,
            degree, cgpa, skills, projects, file_path
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "resume_text": resume_text,
            "txt_file": file_name,
            "score":score,
            "missing skills":missing_skills
        })

    except Exception as e:
        print("SAVE RESUME ERROR:", e)
        return jsonify({"success": False})
    

# ---------------- RESUME SCORE ----------------
def calculate_resume_score(cgpa, skills, projects, fields_present=True):
    score = 0

    # ----- CGPA SCORE (40) -----
    try:
        cgpa = float(cgpa)
        cgpa_score = min((cgpa / 10) * 40, 40)
    except:
        cgpa_score = 0

    score += cgpa_score

    # ----- SKILL SCORE (30) -----
    expected_skills = ["python", "java", "sql", "html", "css", "javascript"]

    user_skills = [s.strip().lower() for s in skills.split(",")]
    matched_skills = set(user_skills) & set(expected_skills)

    skill_score = (len(matched_skills) / len(expected_skills)) * 30
    score += skill_score

    # ----- PROJECT SCORE (20) -----
    if not projects.strip():
        project_score = 0
    elif len(projects.strip()) < 50:
        project_score = 10
    else:
        project_score = 20

    score += project_score

    # ----- COMPLETENESS SCORE (10) -----
    completeness_score = 10 if fields_present else 0
    score += completeness_score

    return round(score), list(set(expected_skills) - set(user_skills))


# ---------------- DOWNLOAD (TXT → PDF ON THE FLY) ----------------
@app.route("/download/<filename>")
def download_resume(filename):
    txt_path = os.path.join("resumes", filename)

    if not os.path.exists(txt_path):
        return "File not found", 404

    # Read TXT
    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Create PDF in memory
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4
    x, y = 50, height - 50

    for line in content.split("\n"):
        c.drawString(x, y, line)
        y -= 15
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()
    pdf_buffer.seek(0)

    pdf_name = filename.replace(".txt", ".pdf")

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=pdf_name,
        mimetype="application/pdf"
    )

# ---------------- ADMIN LOGIN ----------------
ADMIN_EMAIL = "admin@placement.com"
ADMIN_PASSWORD = "admin123"

@app.route("/admin_login", methods=["POST"])
def admin_login():
    data = request.get_json()
    if data["email"] == ADMIN_EMAIL and data["password"] == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"success": True})
    return jsonify({"success": False})


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return "Unauthorized", 401

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT email FROM users")
    users = cur.fetchall()

    cur.execute("""
    SELECT name, email, degree, cgpa, file_path
    FROM resumes
    """)
    resumes = cur.fetchall()

    conn.close()

    return render_template("admin.html", users=users, resumes=resumes)

# ---------------- RESUME EVALUATOR ----------------
@app.route("/evaluate_resume")
def evaluate_resume():
    score = session.get("last_score")
    missing_skills = session.get("last_missing_skills", [])

    if score is None:
        return jsonify({"success": False})

    # Placement readiness
    if score >= 80:
        status = "Ready"
    elif score >= 60:
        status = "Partially Ready"
    else:
        status = "Not Ready"

    return jsonify({
        "success": True,
        "score": score,
        "status": status,
        "missing_skills": missing_skills
    })


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
