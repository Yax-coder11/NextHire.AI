import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import os
import sqlite3
import io
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from python_modules.resume_history_ds import ResumeLinkedList
from python_modules import role_evaluator, skill_roadmap, confidence_calculator, skill_simulator, role_comparator, resume_breakdown
from datetime import datetime


# RapidAPI JSearch configuration
RAPIDAPI_KEY = "dd39669e4fmsh5e0b28764b36855p10b159jsnad9ed342f1a2"
RAPIDAPI_HOST = "jsearch.p.rapidapi.com"



app = Flask(__name__)
app.secret_key = "placement_secret_key"

DB_NAME = os.path.join(os.path.dirname(__file__), "database.db")
print("DB IN USE ->", os.path.abspath(DB_NAME))

user_resume_history = {}

# ---------------- DB CONNECTION ----------------
def get_db():
    return sqlite3.connect(DB_NAME)

# ---------------- REBUILD DS FROM DB ----------------
def rebuild_resume_history():
    global user_resume_history
    user_resume_history = {}

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_email, id, 
            COALESCE(score, 'N/A'), 
            COALESCE(status, 'N/A')
        FROM resumes
        ORDER BY id
    """)


    rows = cur.fetchall()

    for row in rows:
        user_email = row[0]

        if user_email not in user_resume_history:
            user_resume_history[user_email] = ResumeLinkedList()

        user_resume_history[user_email].add_resume(
            resume_id=row[1],
            resume_score=row[2],
            readiness_status=row[3],
            created_at="Loaded from DB"
        )


    conn.close()


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

# ---------------- ENHANCED DASHBOARD ----------------
@app.route("/enhanced_dashboard")
def enhanced_dashboard():
    """Enhanced features dashboard"""
    if "user_email" not in session:
        return redirect("/login_page")
    return render_template("enhanced_dashboard.html")

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
    conn = None
    cur = None
    try:
        if "user_email" not in session:
            return jsonify({"success": False, "message": "Login required"})

        data = request.get_json()

        # ========== BACKEND VALIDATION - ALL REQUIRED FIELDS ==========
        # Define all required fields with their display names
        required_fields = {
            'name': 'Full Name',
            'phone': 'Phone',
            'email': 'Email',
            'city': 'City',
            'degree': 'Degree',
            'cgpa': 'CGPA',
            'about_yourself': 'About Yourself',
            'skills': 'Skills',
            'projects': 'Projects'
        }
        
        # Validate each required field
        for field_key, field_name in required_fields.items():
            field_value = data.get(field_key, '').strip() if data.get(field_key) else ''
            
            if not field_value:
                return jsonify({
                    "success": False,
                    "validation_error": f"{field_name} is required."
                })
        # ========== END REQUIRED FIELDS VALIDATION ==========

        user_email = session["user_email"]
        name = data["name"].strip()
        phone = data["phone"].strip()
        email = data["email"].strip()
        city = data.get("city", "").strip()
        degree = data["degree"].strip()
        github_username = data.get("github_username", "").strip()
        cgpa = data["cgpa"].strip()
        about_yourself = data.get("about_yourself", "").strip()
        skills = data["skills"].strip()
        projects = data["projects"].strip()
        education_data = data.get("education", [])

        # ========== BACKEND PHONE VALIDATION (STRICT) ==========
        # REQUIREMENT: Phone must be exactly 10 digits starting with 9, 8, 7, or 6
        # This validation cannot be bypassed even if frontend is disabled
        
        # Remove any whitespace
        phone_clean = phone.strip()
        
        # Validation Check 1: Must be exactly 10 characters
        if len(phone_clean) != 10:
            return jsonify({
                "success": False,
                "validation_error": "Phone number must be exactly 10 digits and start with 9, 8, 7, or 6."
            })
        
        # Validation Check 2: Must contain only digits (0-9)
        if not phone_clean.isdigit():
            return jsonify({
                "success": False,
                "validation_error": "Phone number must be exactly 10 digits and start with 9, 8, 7, or 6."
            })
        
        # Validation Check 3: Must start with 9, 8, 7, or 6
        first_digit = phone_clean[0]
        if first_digit not in ['9', '8', '7', '6']:
            return jsonify({
                "success": False,
                "validation_error": "Phone number must be exactly 10 digits and start with 9, 8, 7, or 6."
            })
        
        # If all validations pass, use the cleaned phone number
        phone = phone_clean
        # ========== END PHONE VALIDATION ==========

        # ========== BACKEND CGPA VALIDATION (STRICT) ==========
        # REQUIREMENT: CGPA must be numeric and between 0 and 10 (inclusive)
        # This validation cannot be bypassed even if frontend is disabled
        
        # Remove any whitespace
        cgpa_clean = cgpa.strip()
        
        # Validation Check 1: Must be a valid number
        try:
            cgpa_float = float(cgpa_clean)
        except ValueError:
            return jsonify({
                "success": False,
                "validation_error": "CGPA must be between 0 and 10."
            })
        
        # Validation Check 2: Must be between 0 and 10 (inclusive)
        if cgpa_float < 0:
            return jsonify({
                "success": False,
                "validation_error": "CGPA must be between 0 and 10."
            })
        
        if cgpa_float > 10:
            return jsonify({
                "success": False,
                "validation_error": "CGPA must be between 0 and 10."
            })
        
        # If all validations pass, use the cleaned CGPA
        cgpa = cgpa_clean
        # ========== END CGPA VALIDATION ==========

        # Calculate score with validation
        score, missing_skills, validation_error = calculate_resume_score(
            cgpa=cgpa,
            skills=skills,
            projects=projects,
            fields_present=True
        )
        
        # If validation failed, return error message
        if validation_error:
            return jsonify({
                "success": False,
                "validation_error": validation_error
            })

        session["last_score"] = score
        session["last_missing_skills"] = missing_skills
        session["user_skills"] = skills  # Store user skills for job fit calculation

        # -------- Resume Text --------
        resume_text = f"""{name.upper()}
----------------------------------------
{degree} | CGPA: {cgpa}

CONTACT
Phone: {phone}
Email: {email}"""

        if city:
            resume_text += f"\nCity: {city}"
        if github_username:
            resume_text += f"\nGitHub: {github_username}"

        if about_yourself:
            resume_text += f"""

ABOUT
----------------------------------------
{about_yourself}"""

        resume_text += f"""

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

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ----- Placement Readiness Status (same logic as evaluator) -----
        if score >= 80:
            status = "Ready"
        elif score >= 60:
            status = "Partially Ready"
        else:
            status = "Not Ready"

        # -------- Save DB --------
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Registered user (login identity)
            user_email TEXT NOT NULL,

            -- Resume details
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,          -- email written inside resume
            degree TEXT NOT NULL,
            cgpa TEXT NOT NULL,
            skills TEXT NOT NULL,
            projects TEXT NOT NULL,

            -- Additional fields
            about_yourself TEXT,
            github_username TEXT,
            city TEXT,

            -- File system
            file_path TEXT NOT NULL,

            -- Evaluation
            score INTEGER NOT NULL,
            status TEXT NOT NULL,
            job_fit_score INTEGER DEFAULT 0,

            -- Metadata
            created_at TEXT NOT NULL
        );
        """)

        # Create education table if it doesn't exist
        cur.execute("""
        CREATE TABLE IF NOT EXISTS education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER,
            degree TEXT,
            institution TEXT,
            start_year TEXT,
            end_year TEXT,
            description TEXT,
            FOREIGN KEY (resume_id) REFERENCES resumes (id)
        );
        """)

        cur.execute("""
            INSERT INTO resumes (user_email, name, phone, email, degree, cgpa, skills, projects, 
                               about_yourself, github_username, city, file_path, score, status, job_fit_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_email, name, phone, email, degree, cgpa, skills, projects,
            about_yourself, github_username, city, file_path, score, status, 0, created_at
        ))

        conn.commit()  
        resume_id = cur.lastrowid

        # Save education data
        for edu in education_data:
            if edu.get('degree') or edu.get('institution'):  # Only save if there's meaningful data
                cur.execute("""
                    INSERT INTO education (resume_id, degree, institution, start_year, end_year, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    resume_id,
                    edu.get('degree', ''),
                    edu.get('institution', ''),
                    edu.get('start_year', ''),
                    edu.get('end_year', ''),
                    edu.get('description', '')
                ))

        conn.commit()

        # ----- DS: Resume History Tracking -----
        if user_email not in user_resume_history:
            user_resume_history[user_email] = ResumeLinkedList()

        user_resume_history[user_email].add_resume(
            resume_id=resume_id,
            resume_score=score,
            readiness_status=status,
            created_at=created_at
        )

        conn.close()

        print(os.path.abspath(DB_NAME))

        # ----- DS DEBUG: Console Output -----
        print("\n[DS] Resume Linked List State:")
        for email, ll in user_resume_history.items():
            print(f"User: {email}")
            for node in ll.get_resume_history():
                print("   ", node)

        return jsonify({
            "success": True,
            "resume_text": resume_text,
            "txt_file": file_name,
            "score": score,
            "missing skills": missing_skills
        })

    except Exception as e:
        print("SAVE RESUME ERROR:", e)
        return jsonify({"success": False})
    
    finally:
        if cur:
            pass
        if conn:
            conn.close()

    

# ---------------- RESUME SCORE ----------------
def calculate_resume_score(cgpa, skills, projects, fields_present=True):
    """
    Calculate resume score with proper validation.
    Returns: (score, missing_skills, validation_error)
    """
    
    # ----- VALIDATION: SKILLS -----
    # Check if skills is empty or invalid
    if not skills or not skills.strip():
        return 0, [], "Please enter valid skills to proceed."
    
    # Check for invalid skill inputs
    skills_lower = skills.strip().lower()
    if skills_lower in ["none", "null", "n/a", "na"]:
        return 0, [], "Please enter valid skills to proceed."
    
    # ----- VALIDATION: PROJECTS -----
    # Extract project count from projects text
    project_count = 0
    projects_valid = False
    
    if projects and projects.strip():
        # Check for invalid project inputs
        projects_lower = projects.strip().lower()
        if projects_lower not in ["none", "null", "n/a", "na"]:
            # Count number of lines or bullet points as projects
            project_lines = [line.strip() for line in projects.split('\n') if line.strip()]
            project_count = len(project_lines)
            projects_valid = True
    
    # Minimum 3 projects required for job readiness
    if project_count < 3:
        return 0, [], "Minimum 3 projects are required for job readiness."
    
    # ----- START SCORING -----
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

    user_skills = [s.strip().lower() for s in skills.split(",") if s.strip()]
    matched_skills = set(user_skills) & set(expected_skills)

    skill_score = (len(matched_skills) / len(expected_skills)) * 30
    score += skill_score

    # ----- PROJECT SCORE (20) - CORRECTED LOGIC -----
    # Apply exact scoring rules:
    # 0 projects or invalid → 0 points
    # 1 project → 5 points
    # 2 projects → 10 points
    # 3+ projects → 20 points (FULL SCORE)
    
    if not projects_valid or project_count == 0:
        project_score = 0
    elif project_count == 1:
        project_score = 5
    elif project_count == 2:
        project_score = 10
    elif project_count >= 3:
        project_score = 20  # Full score for 3 or more projects
    else:
        project_score = 0

    score += project_score

    # ----- COMPLETENESS SCORE (10) -----
    completeness_score = 10 if fields_present else 0
    score += completeness_score

    return round(score), list(set(expected_skills) - set(user_skills)), None


# ---------------- PREPARE JOB GRAPH DATA (NumPy-based) ----------------
def prepare_job_graph_data(mock_jobs, selected_job_id=None):
    """
    Prepare numerical data for graph visualization using NumPy.
    
    Args:
        mock_jobs (list): List of job dictionaries from the mock database
        selected_job_id (str, optional): ID of a specific job to analyze skills for
    
    Returns:
        dict: Contains two datasets ready for plotting:
            - 'jobs_per_field': {'fields': array, 'counts': array}
            - 'skill_frequency': {'skills': array, 'frequencies': array}
    """
    
    # ===== PART 1: Count jobs per field =====
    # Extract job titles and categorize them into fields
    field_mapping = {
        'Software Development': ['software developer', 'frontend developer', 'backend developer', 
                                'full stack developer', 'mobile app developer'],
        'Data Science & AI': ['data scientist', 'machine learning engineer', 'ai research', 
                             'data analyst', 'data research analyst'],
        'Cloud & DevOps': ['cloud engineer', 'devops engineer', 'cloud solutions architect'],
        'Security': ['cybersecurity analyst', 'penetration tester'],
        'Design': ['ux/ui designer', 'product designer', 'graphic designer', 
                  'motion graphics designer'],
        'Content & Marketing': ['content writer', 'content creator', 'copywriter', 
                               'social media manager', 'digital marketing specialist', 
                               'technical writer'],
        'Management': ['product manager', 'operations manager', 'business analyst', 
                      'growth marketing manager'],
        'Engineering': ['electronics engineer', 'embedded systems developer', 'iot engineer', 
                       'robotics engineer', 'automation engineer', 'renewable energy engineer'],
        'Emerging Tech': ['blockchain developer', 'fintech product manager', 'healthtech developer', 
                         'edtech content developer']
    }
    
    # Initialize field counts using NumPy
    field_names = list(field_mapping.keys())
    field_counts = np.zeros(len(field_names), dtype=int)
    
    # Count jobs for each field
    for job in mock_jobs:
        job_title_lower = job['title'].lower()
        for idx, (field, keywords) in enumerate(field_mapping.items()):
            if any(keyword in job_title_lower for keyword in keywords):
                field_counts[idx] += 1
                break  # Each job belongs to only one field
    
    # Convert to NumPy arrays for graph-ready output
    fields_array = np.array(field_names)
    counts_array = field_counts
    
    # ===== PART 2: Skill frequency analysis =====
    skills_array = np.array([])
    frequencies_array = np.array([])
    
    if selected_job_id:
        # Find the selected job
        selected_job = None
        for job in mock_jobs:
            if job['id'] == selected_job_id:
                selected_job = job
                break
        
        if selected_job and 'missing_skills' in selected_job:
            # Extract all missing skills from the selected job
            missing_skills = selected_job['missing_skills']
            
            # Count frequency of each skill across ALL jobs
            skill_frequency_dict = {}
            
            for job in mock_jobs:
                if 'missing_skills' in job:
                    for skill in job['missing_skills']:
                        skill_frequency_dict[skill] = skill_frequency_dict.get(skill, 0) + 1
            
            # Filter to only include skills from the selected job
            selected_skill_frequencies = {
                skill: skill_frequency_dict.get(skill, 0) 
                for skill in missing_skills
            }
            
            # Convert to NumPy arrays sorted by frequency (descending)
            sorted_skills = sorted(selected_skill_frequencies.items(), 
                                 key=lambda x: x[1], reverse=True)
            
            if sorted_skills:
                skills_array = np.array([skill for skill, _ in sorted_skills])
                frequencies_array = np.array([freq for _, freq in sorted_skills], dtype=int)
    
    return {
        'jobs_per_field': {
            'fields': fields_array,
            'counts': counts_array
        },
        'skill_frequency': {
            'skills': skills_array,
            'frequencies': frequencies_array
        }
    }


# ---------------- GENERATE JOB FIELD CHART (Matplotlib) ----------------
def generate_job_field_chart(fields_array, counts_array, output_path=None):
    """
    Generate a bar chart showing job availability across fields using Matplotlib.
    
    Args:
        fields_array (numpy.ndarray): Array of field names
        counts_array (numpy.ndarray): Array of job counts per field
        output_path (str): Path where the PNG image will be saved
    
    Returns:
        str: Path to the saved chart image
    """
    
    # Use absolute path based on Flask app root
    if output_path is None:
        images_dir = os.path.join(app.root_path, 'static', 'images')
        os.makedirs(images_dir, exist_ok=True)
        output_path = os.path.join(images_dir, 'job_field_chart.png')
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create bar chart
    bars = ax.bar(range(len(fields_array)), counts_array, color='#4A90E2', alpha=0.8, edgecolor='black')
    
    # Customize the chart
    ax.set_xlabel('Job Fields', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Jobs', fontsize=12, fontweight='bold')
    ax.set_title('Job Availability Across Fields', fontsize=14, fontweight='bold', pad=20)
    
    # Set x-axis labels with rotation for readability
    ax.set_xticks(range(len(fields_array)))
    ax.set_xticklabels(fields_array, rotation=45, ha='right', fontsize=10)
    
    # Add value labels on top of each bar
    for i, (bar, count) in enumerate(zip(bars, counts_array)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count)}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Add grid for better readability
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the chart as PNG with absolute path
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    return output_path


# ---------------- GENERATE SKILL GAP CHART (Matplotlib) ----------------
def generate_skill_gap_chart(skills_array, frequencies_array, output_path=None):
    """
    Generate a pie chart showing skill gap IMPACT distribution using Matplotlib.
    Skills are weighted by importance/frequency.
    
    Args:
        skills_array (numpy.ndarray): Array of skill names
        frequencies_array (numpy.ndarray): Array of skill frequencies (used as weights)
        output_path (str): Path where the PNG image will be saved
    
    Returns:
        str: Path to the saved chart image
    """
    
    # Handle empty data
    if len(skills_array) == 0 or len(frequencies_array) == 0:
        return None
    
    # Use absolute path based on Flask app root
    if output_path is None:
        images_dir = os.path.join(app.root_path, 'static', 'images')
        os.makedirs(images_dir, exist_ok=True)
        output_path = os.path.join(images_dir, 'skill_gap_chart.png')
    
    # Weight skills by frequency (higher frequency = more important)
    # Normalize frequencies to create impact weights
    total_frequency = np.sum(frequencies_array)
    impact_weights = (frequencies_array / total_frequency) * 100
    
    # Sort by impact (descending) for better visualization
    sorted_indices = np.argsort(impact_weights)[::-1]
    skills_sorted = skills_array[sorted_indices]
    impact_sorted = impact_weights[sorted_indices]
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Define color palette (gradient from high to low impact)
    colors = ['#E74C3C', '#E67E22', '#F39C12', '#F1C40F', '#2ECC71', 
              '#3498DB', '#9B59B6', '#1ABC9C', '#34495E', '#95A5A6']
    
    # Create pie chart with weighted impact
    wedges, texts, autotexts = ax.pie(
        impact_sorted,
        labels=skills_sorted,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors[:len(skills_sorted)],
        explode=[0.1 if i == 0 else 0.03 for i in range(len(skills_sorted))],  # Emphasize most critical
        shadow=True,
        textprops={'fontsize': 10, 'weight': 'bold'}
    )
    
    # Customize percentage text
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(9)
        autotext.set_weight('bold')
    
    # Customize label text
    for text in texts:
        text.set_fontsize(11)
        text.set_weight('bold')
    
    # Set title
    ax.set_title('Skill Gap Impact Distribution', fontsize=14, fontweight='bold', pad=20)
    
    # Add subtitle explaining the weighting
    fig.text(0.5, 0.02, 
             'Larger slices indicate skills with higher importance for this role',
             ha='center', fontsize=9, style='italic', color='#7F8C8D')
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    ax.axis('equal')
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the chart as PNG with absolute path
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    return output_path


# ---------------- CALCULATE JOB FIT SCORE ----------------
def calculate_job_fit_score(user_skills, job_required_skills):
    """
    Calculate job fit score based on skill matching.
    
    Args:
        user_skills (list): List of user's skills
        job_required_skills (list): List of skills required for the job
    
    Returns:
        tuple: (job_fit_score, missing_skills_count, total_job_skills)
    """
    if not job_required_skills or len(job_required_skills) == 0:
        return 100, 0, 0  # No requirements = perfect fit
    
    # Normalize skills for comparison
    user_skills_lower = [skill.strip().lower() for skill in user_skills if skill.strip()]
    job_skills_lower = [skill.strip().lower() for skill in job_required_skills if skill.strip()]
    
    # Count matching skills
    matched_skills = 0
    for job_skill in job_skills_lower:
        for user_skill in user_skills_lower:
            if user_skill in job_skill or job_skill in user_skill:
                matched_skills += 1
                break
    
    # Calculate score
    total_job_skills = len(job_skills_lower)
    missing_skills_count = total_job_skills - matched_skills
    
    # Job fit score: (matched_skills / total_job_skills) * 100
    if total_job_skills > 0:
        job_fit_score = int((matched_skills / total_job_skills) * 100)
    else:
        job_fit_score = 100
    
    return job_fit_score, missing_skills_count, total_job_skills


# ---------------- GENERATE SKILL READINESS LINE CHART (Matplotlib) ----------------
def generate_skill_readiness_chart(job_title, missing_skills_count, current_job_fit_score, total_job_skills, output_path=None):
    """
    Generate a line chart showing CURRENT job fit readiness progress using Matplotlib.
    
    This chart represents job-specific readiness levels:
    - Stage 0: Baseline match (current resume vs job)
    - Stage 1: After acquiring some missing job skills
    - Stage 2: After acquiring most job-required skills
    - Stage 3: Near-perfect job readiness
    
    Args:
        job_title (str): Title of the selected job
        missing_skills_count (int): Number of missing skills for the job
        current_job_fit_score (int): Current job fit score (0-100) based on job requirements
        total_job_skills (int): Total number of skills required for the job
        output_path (str): Path where the PNG image will be saved
    
    Returns:
        str: Path to the saved chart image
    """
    
    # Use absolute path based on Flask app root
    if output_path is None:
        images_dir = os.path.join(app.root_path, 'static', 'images')
        os.makedirs(images_dir, exist_ok=True)
        output_path = os.path.join(images_dir, 'skill_readiness_chart.png')
    
    # Calculate current position based on missing skills
    # Stage 0 = baseline (all skills missing)
    # Stage 1 = current position (some skills acquired)
    # Stage 2 = most skills acquired
    # Stage 3 = near-perfect (all skills acquired)
    
    # Determine total stages based on missing skills
    if missing_skills_count == 0:
        # No missing skills - user is at final stage
        total_steps = 4  # Still show 4 stages for consistency
        current_step = 3  # At final stage
    elif missing_skills_count >= total_job_skills:
        # All skills missing - user is at baseline
        total_steps = 4
        current_step = 0  # At baseline
    else:
        # Some skills acquired - calculate position
        total_steps = 4
        # Current step based on skill acquisition progress
        skills_acquired = total_job_skills - missing_skills_count
        progress_ratio = skills_acquired / total_job_skills
        
        # Map progress to stages 0-3
        if progress_ratio <= 0.25:
            current_step = 0  # Baseline
        elif progress_ratio <= 0.5:
            current_step = 1  # Some skills
        elif progress_ratio <= 0.75:
            current_step = 2  # Most skills
        else:
            current_step = 3  # Near-perfect
    
    # Generate steps using NumPy - only up to current position
    steps_current = np.arange(0, current_step + 1)
    
    # Calculate job fit percentages for current progress
    # Start from baseline (30%) and progress to current job fit score
    baseline_score = 30  # Baseline job fit when no skills match
    
    if current_step > 0:
        readiness_current = np.linspace(baseline_score, current_job_fit_score, len(steps_current))
    else:
        readiness_current = np.array([current_job_fit_score])  # At baseline
    
    # Generate projected future steps (dotted line)
    if current_step < total_steps - 1:
        steps_future = np.arange(current_step, total_steps)
        # Project to 100% if all skills are acquired
        readiness_future = np.linspace(current_job_fit_score, 100, len(steps_future))
    else:
        steps_future = None
        readiness_future = None
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot CURRENT progress (solid line)
    ax.plot(steps_current, readiness_current, 
            color='#2ECC71', 
            linewidth=3, 
            marker='o', 
            markersize=8, 
            markerfacecolor='#27AE60',
            markeredgecolor='white',
            markeredgewidth=2,
            label='Current Progress',
            zorder=3)
    
    # Fill area under current progress
    ax.fill_between(steps_current, readiness_current, alpha=0.3, color='#2ECC71')
    
    # Plot PROJECTED future (dotted line) if not at 100%
    if steps_future is not None and current_job_fit_score < 100:
        ax.plot(steps_future, readiness_future, 
                color='#95A5A6', 
                linewidth=2, 
                linestyle='--',
                marker='o', 
                markersize=6, 
                markerfacecolor='#BDC3C7',
                markeredgecolor='white',
                markeredgewidth=1,
                label='Projected (if skills acquired)',
                alpha=0.6,
                zorder=2)
    
    # Highlight "You are here" marker
    ax.scatter([current_step], [current_job_fit_score], 
               s=300, 
               color='#E74C3C', 
               marker='*', 
               edgecolors='white',
               linewidths=2,
               label='You are here',
               zorder=4)
    
    # Add "You are here" annotation
    ax.annotate('You are here',
               xy=(current_step, current_job_fit_score),
               xytext=(15, 15),
               textcoords='offset points',
               ha='left',
               fontsize=10,
               fontweight='bold',
               color='#E74C3C',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#E74C3C', linewidth=2),
               arrowprops=dict(arrowstyle='->', color='#E74C3C', lw=2))
    
    # Customize the chart
    ax.set_xlabel('Skill Acquisition Stages', fontsize=12, fontweight='bold')
    ax.set_ylabel('Readiness Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Current Skill Readiness Progress for {job_title}', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Set axis limits and ticks
    ax.set_xlim(-0.5, total_steps - 0.5)
    ax.set_ylim(0, 105)
    ax.set_xticks(np.arange(0, total_steps))
    
    # Add grid for better readability
    ax.grid(axis='both', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Add current job fit score label
    ax.text(current_step, current_job_fit_score - 8,
            f'{current_job_fit_score}%',
            ha='center',
            fontsize=11,
            fontweight='bold',
            color='#E74C3C')
    
    # Add legend
    ax.legend(loc='lower right', fontsize=9)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the chart as PNG with absolute path
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory
    
    return output_path


# ---------------- DOWNLOAD (FORMATTED HTML → PDF) ----------------
def get_resume_data_by_filename(filename):
    """Retrieve resume data from database using filename"""
    try:
        # Extract name from filename (remove .txt extension and replace underscores with spaces)
        name_from_file = filename.replace(".txt", "").replace("_", " ")
        
        conn = get_db()
        cur = conn.cursor()
        
        # Get resume data - try by file_path first, then by name
        cur.execute("""
        SELECT name, phone, email, degree, cgpa, skills, projects, 
               about_yourself, github_username, city, id
        FROM resumes 
        WHERE file_path = ? OR name = ?
        ORDER BY id DESC LIMIT 1
        """, (f"resumes/{filename}", name_from_file))
        
        resume_row = cur.fetchone()
        if not resume_row:
            conn.close()
            return None
            
        # Get education data
        cur.execute("""
        SELECT degree, institution, start_year, end_year, description
        FROM education 
        WHERE resume_id = ?
        """, (resume_row[10],))  # resume_row[10] is the id
        
        education_rows = cur.fetchall()
        conn.close()
        
        # Structure the data
        resume_data = {
            'name': resume_row[0] or '',
            'phone': resume_row[1] or '',
            'email': resume_row[2] or '',
            'degree': resume_row[3] or '',
            'cgpa': resume_row[4] or '',
            'skills': resume_row[5] or '',
            'projects': resume_row[6] or '',
            'about_yourself': resume_row[7] or '',
            'github_username': resume_row[8] or '',
            'city': resume_row[9] or '',
            'education': []
        }
        
        # Add education entries
        for edu_row in education_rows:
            resume_data['education'].append({
                'degree': edu_row[0] or '',
                'institution': edu_row[1] or '',
                'start_year': edu_row[2] or '',
                'end_year': edu_row[3] or '',
                'description': edu_row[4] or ''
            })
            
        return resume_data
        
    except Exception as e:
        print(f"Error retrieving resume data: {e}")
        return None

@app.route("/download/<filename>")
def download_resume(filename):
    # Get resume data from database
    resume_data = get_resume_data_by_filename(filename)
    
    if not resume_data:
        return "Resume not found", 404
    
    # Generate HTML using Jinja template
    html_content = render_template('resume_pdf.html', resume_data=resume_data)
    
    # Try WeasyPrint first, fall back to ReportLab
    try:
        from weasyprint import HTML
        
        # Create PDF from HTML
        pdf_buffer = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
        pdf_name = filename.replace(".txt", ".pdf")
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=pdf_name,
            mimetype="application/pdf"
        )
        
    except (ImportError, OSError) as e:
        print(f"WeasyPrint not available ({e}), falling back to ReportLab")
        
        # Fallback to reportlab
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch
        
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, 
                              rightMargin=0.75*inch, leftMargin=0.75*inch,
                              topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            alignment=1,  # Center alignment
            textTransform='uppercase'
        )
        story.append(Paragraph(resume_data['name'], title_style))
        
        # Contact info
        contact_parts = [resume_data['email']]
        if resume_data['phone']:
            contact_parts.append(resume_data['phone'])
        if resume_data['github_username']:
            contact_parts.append(f"GitHub: {resume_data['github_username']}")
        if resume_data['city']:
            contact_parts.append(resume_data['city'])
        
        contact_style = ParagraphStyle(
            'Contact',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,  # Center alignment
            spaceAfter=12
        )
        story.append(Paragraph(" | ".join(contact_parts), contact_style))
        story.append(Spacer(1, 12))
        
        # Sections
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=6,
            textTransform='uppercase'
        )
        
        if resume_data['about_yourself']:
            story.append(Paragraph("Professional Summary", section_style))
            story.append(Paragraph(resume_data['about_yourself'], styles['Normal']))
            story.append(Spacer(1, 12))
        
        if resume_data['skills']:
            story.append(Paragraph("Core Skills", section_style))
            skills_text = "<br/>".join([f"• {skill.strip()}" for skill in resume_data['skills'].split(',') if skill.strip()])
            story.append(Paragraph(skills_text, styles['Normal']))
            story.append(Spacer(1, 12))
        
        if resume_data['projects']:
            story.append(Paragraph("Projects", section_style))
            story.append(Paragraph("Academic and Personal Projects", styles['Heading3']))
            project_lines = [line.strip() for line in resume_data['projects'].split('\n') if line.strip()]
            projects_text = "<br/>".join([f"• {line}" for line in project_lines])
            story.append(Paragraph(projects_text, styles['Normal']))
            story.append(Spacer(1, 12))
        
        if resume_data['education'] and len(resume_data['education']) > 0:
            story.append(Paragraph("Education", section_style))
            for edu in resume_data['education']:
                if edu['degree'] or edu['institution']:
                    edu_text = f"<b>{edu['degree']}</b><br/>{edu['institution']}<br/>{edu['start_year']} - {edu['end_year']}"
                    if edu['description']:
                        edu_text += f"<br/>{edu['description']}"
                    story.append(Paragraph(edu_text, styles['Normal']))
                    story.append(Spacer(1, 6))
        elif resume_data['degree'] and resume_data['cgpa']:
            story.append(Paragraph("Education", section_style))
            edu_text = f"<b>{resume_data['degree']}</b><br/>CGPA: {resume_data['cgpa']}"
            story.append(Paragraph(edu_text, styles['Normal']))
        
        doc.build(story)
        pdf_buffer.seek(0)
        
        pdf_name = filename.replace(".txt", ".pdf")
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=pdf_name,
            mimetype="application/pdf"
        )
    except Exception as e:
        print(f"PDF generation error: {e}")
        return "PDF generation failed", 500

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
    
    if not user_resume_history:
        rebuild_resume_history()


    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT email FROM users")
    users = cur.fetchall()

    cur.execute("""
    SELECT id, user_email, name, email, phone, degree, cgpa, score, status, file_path
    FROM resumes
    """)


    resumes = cur.fetchall()

    conn.close()

    return render_template("admin.html",users=users,resumes=resumes,ds_history=user_resume_history)


# ---------------- ADMIN DOWNLOAD EVALUATION REPORT ----------------
@app.route("/admin/download_report/<int:resume_id>")
def admin_download_report(resume_id):
    """
    Admin route to download evaluation report for a specific user.
    Fetches stored resume data and generates report without recalculating scores.
    """
    
    # Validate admin session
    if not session.get("admin"):
        return "Unauthorized - Admin access required", 401
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Fetch resume data by ID
        cur.execute("""
            SELECT id, user_email, name, email, phone, degree, cgpa, skills, projects, 
                   city, github_username, about_yourself, score, status, job_fit_score
            FROM resumes
            WHERE id = ?
        """, (resume_id,))
        
        row = cur.fetchone()
        conn.close()
        
        # Check if resume exists
        if not row:
            return "Evaluation report not available - Resume not found", 404
        
        # Extract data from database row
        resume_id_db = row[0]
        user_email = row[1]
        resume_data = {
            "name": row[2],
            "email": row[3],
            "phone": row[4],
            "degree": row[5],
            "cgpa": row[6],
            "skills": row[7],
            "projects": row[8],
            "city": row[9],
            "github_username": row[10],
            "about_yourself": row[11]
        }
        resume_score = row[12] if row[12] is not None else 0
        readiness_status = row[13] if row[13] else "Not Evaluated"
        job_fit_score = row[14] if row[14] is not None else 0
        
        # Calculate missing skills from stored data (simple logic)
        user_skills = resume_data.get('skills', '').lower().split(',')
        user_skills = [s.strip() for s in user_skills if s.strip()]
        
        # Basic missing skills detection (simplified for admin view)
        all_required_skills = ['Python', 'Java', 'SQL', 'JavaScript', 'React', 'Node.js', 
                               'Machine Learning', 'Data Structures', 'Algorithms', 'Git']
        missing_skills = [skill for skill in all_required_skills 
                         if not any(skill.lower() in us for us in user_skills)]
        
        # Job-specific data (default values if not stored)
        job_title = "Not Selected"
        job_company = "Not Selected"
        
        # ========== ANALYTICAL SECTIONS (Same as user download) ==========
        
        # 1. Role Based Evaluation
        role_readiness_status = "Not Evaluated"
        if job_fit_score > 0:
            if job_fit_score >= 70:
                role_readiness_status = "Ready for Role"
            elif job_fit_score >= 50:
                role_readiness_status = "Partially Ready"
            else:
                role_readiness_status = "Not Ready"
        
        # 2. Skill Gap Learning Roadmap
        skill_roadmap = None
        if missing_skills and len(missing_skills) > 0:
            phase1_skills = missing_skills[:3] if len(missing_skills) >= 3 else missing_skills
            phase2_skills = missing_skills[3:6] if len(missing_skills) > 3 else []
            phase3_skills = missing_skills[6:] if len(missing_skills) > 6 else []
            
            skill_roadmap = {
                'phase1': phase1_skills,
                'phase2': phase2_skills,
                'phase3': phase3_skills,
                'total_skills': len(missing_skills)
            }
        
        # 3. Role Switch Impact Analysis
        role_impact = None
        if job_fit_score > 0:
            score_difference = resume_score - job_fit_score
            
            if abs(score_difference) > 20:
                impact_level = "Significant"
                if score_difference > 0:
                    impact_message = "Significant role mismatch detected. General resume is stronger than role fit."
                else:
                    impact_message = "Strong role alignment! Better suited for this role than general resume suggests."
            elif abs(score_difference) >= 10:
                impact_level = "Moderate"
                if score_difference > 0:
                    impact_message = "Moderate skill alignment gap. Some role-specific skills need improvement."
                else:
                    impact_message = "Good role alignment with room for general resume improvement."
            else:
                impact_level = "Minimal"
                impact_message = "Strong alignment between resume and role. Skills match well with job requirements."
            
            role_impact = {
                'difference': score_difference,
                'impact_level': impact_level,
                'message': impact_message,
                'resume_score': resume_score,
                'job_fit_score': job_fit_score
            }
        
        # 4. Resume Strength Breakdown
        resume_breakdown_data = None
        try:
            breakdown = resume_breakdown.calculate_resume_breakdown(
                cgpa=resume_data.get('cgpa', '0'),
                skills=resume_data.get('skills', ''),
                projects=resume_data.get('projects', ''),
                education_count=1,
                extras={
                    'github_username': resume_data.get('github_username'),
                    'about_yourself': resume_data.get('about_yourself'),
                    'city': resume_data.get('city')
                }
            )
            resume_breakdown_data = breakdown
        except Exception as e:
            print(f"Error calculating resume breakdown: {e}")
            resume_breakdown_data = None
        
        # Render report template with all data
        return render_template(
            "report.html",
            resume_score=resume_score,
            readiness_status=readiness_status,
            missing_skills=missing_skills,
            resume_data=resume_data,
            job_title=job_title,
            job_company=job_company,
            job_fit_score=job_fit_score,
            # Analytical sections
            role_readiness_status=role_readiness_status,
            skill_roadmap=skill_roadmap,
            role_impact=role_impact,
            resume_breakdown_data=resume_breakdown_data,
            # Admin context
            is_admin_view=True,
            viewed_user_email=user_email
        )
        
    except Exception as e:
        print(f"Error generating admin report: {e}")
        return f"Evaluation report not available - Error: {str(e)}", 500


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


@app.route("/my_resumes")
def my_resumes():
    if "user_email" not in session:
        return redirect("/login_page")

    user_email = session["user_email"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, degree, cgpa, score, status, created_at, file_path, job_fit_score
        FROM resumes
        WHERE user_email = ?
        ORDER BY created_at DESC
    """, (user_email,))

    resumes = cur.fetchall()
    conn.close()

    return render_template("my_resumes.html", resumes=resumes)


# ---------------- JOB SEARCH API (Mock Implementation) ----------------
@app.route("/api/jobs/search")
def search_jobs():
    """Mock job search API endpoint - maps interest fields to job listings"""
    query = request.args.get('q', '').lower()
    limit = int(request.args.get('limit', 10))
    location = request.args.get('location', '').lower()
    
    # Mock job database with India-based locations - simulates external API response
    mock_jobs = [
        {
            "id": "job_001",
            "title": "Software Developer",
            "company": "TechCorp Solutions",
            "location": "Bangalore, India",
            "type": "Full-time",
            "description": "Join our team to build cutting-edge software solutions using modern technologies.",
            "missing_skills": ["Python", "React", "Node.js"]
        },
        {
            "id": "job_002", 
            "title": "Frontend Developer",
            "company": "WebFlow Inc",
            "location": "Mumbai, India",
            "type": "Full-time",
            "description": "Create amazing user experiences with React, Vue.js, and modern frontend frameworks.",
            "missing_skills": ["Vue.js", "TypeScript", "SASS"]
        },
        {
            "id": "job_003",
            "title": "Data Scientist",
            "company": "DataVision Analytics",
            "location": "Hyderabad, India", 
            "type": "Full-time",
            "description": "Analyze complex datasets and build machine learning models to drive business insights.",
            "missing_skills": ["R", "TensorFlow", "Statistics"]
        },
        {
            "id": "job_004",
            "title": "Machine Learning Engineer",
            "company": "AI Innovations",
            "location": "Pune, India",
            "type": "Full-time", 
            "description": "Develop and deploy ML models at scale using Python, TensorFlow, and cloud platforms.",
            "missing_skills": ["PyTorch", "Kubernetes", "MLOps"]
        },
        {
            "id": "job_005",
            "title": "Cloud Engineer",
            "company": "CloudTech Systems",
            "location": "Chennai, India",
            "type": "Full-time",
            "description": "Design and manage cloud infrastructure using AWS, Azure, and containerization technologies.",
            "missing_skills": ["AWS", "Docker", "Terraform"]
        },
        {
            "id": "job_006",
            "title": "Cybersecurity Analyst",
            "company": "SecureNet Solutions",
            "location": "Delhi, India",
            "type": "Full-time",
            "description": "Protect organizational assets by implementing security measures and monitoring threats.",
            "missing_skills": ["Penetration Testing", "SIEM", "Incident Response"]
        },
        {
            "id": "job_007",
            "title": "DevOps Engineer", 
            "company": "DeployFast Inc",
            "location": "Gurgaon, India",
            "type": "Full-time",
            "description": "Streamline development workflows with CI/CD pipelines and infrastructure automation.",
            "missing_skills": ["Jenkins", "Ansible", "Monitoring"]
        },
        {
            "id": "job_008",
            "title": "Mobile App Developer",
            "company": "MobileFirst Studios",
            "location": "Noida, India",
            "type": "Full-time",
            "description": "Build native and cross-platform mobile applications for iOS and Android.",
            "missing_skills": ["Swift", "Kotlin", "React Native"]
        },
        {
            "id": "job_009",
            "title": "Product Manager",
            "company": "InnovatePro",
            "location": "Kolkata, India",
            "type": "Full-time",
            "description": "Drive product strategy and work with cross-functional teams to deliver user-centric solutions.",
            "missing_skills": ["Roadmapping", "Agile", "Stakeholder Management"]
        },
        {
            "id": "job_010",
            "title": "UX/UI Designer",
            "company": "DesignHub Creative",
            "location": "Ahmedabad, India",
            "type": "Full-time",
            "description": "Create intuitive and beautiful user interfaces that enhance user experience.",
            "missing_skills": ["Figma", "Prototyping", "User Research"]
        },
        {
            "id": "job_011",
            "title": "Backend Developer",
            "company": "ServerStack Technologies",
            "location": "Bangalore, India",
            "type": "Full-time",
            "description": "Build scalable backend systems and RESTful APIs using Java, Spring Boot, and microservices architecture.",
            "missing_skills": ["Spring Boot", "Microservices", "PostgreSQL"]
        },
        {
            "id": "job_012",
            "title": "Full Stack Developer",
            "company": "CodeCraft Solutions",
            "location": "Pune, India",
            "type": "Full-time",
            "description": "Work on end-to-end web applications using MERN stack and modern development practices.",
            "missing_skills": ["MongoDB", "Express.js", "Redux"]
        },
        {
            "id": "job_013",
            "title": "Data Analyst",
            "company": "InsightMetrics",
            "location": "Mumbai, India",
            "type": "Full-time",
            "description": "Transform raw data into actionable insights using SQL, Python, and visualization tools.",
            "missing_skills": ["Power BI", "Tableau", "Advanced Excel"]
        },
        {
            "id": "job_014",
            "title": "AI Research Intern",
            "company": "DeepMind Labs India",
            "location": "Hyderabad, India",
            "type": "Internship",
            "description": "Contribute to cutting-edge AI research projects in natural language processing and computer vision.",
            "missing_skills": ["Research Methodology", "PyTorch", "NLP"]
        },
        {
            "id": "job_015",
            "title": "Database Administrator",
            "company": "DataGuard Systems",
            "location": "Chennai, India",
            "type": "Full-time",
            "description": "Manage and optimize database systems ensuring high availability and performance.",
            "missing_skills": ["Oracle", "MySQL", "Database Tuning", "Backup Strategies"]
        },
        {
            "id": "job_016",
            "title": "Digital Marketing Specialist",
            "company": "GrowthHackers India",
            "location": "Delhi, India",
            "type": "Full-time",
            "description": "Drive online marketing campaigns across SEO, SEM, social media, and content marketing channels.",
            "missing_skills": ["Google Ads", "SEO", "Analytics"]
        },
        {
            "id": "job_017",
            "title": "Business Analyst",
            "company": "StrategyFirst Consulting",
            "location": "Bangalore, India",
            "type": "Full-time",
            "description": "Analyze business processes and requirements to deliver data-driven recommendations.",
            "missing_skills": ["Business Intelligence", "SQL", "Requirements Gathering"]
        },
        {
            "id": "job_018",
            "title": "Growth Marketing Manager",
            "company": "ScaleUp Ventures",
            "location": "Gurgaon, India",
            "type": "Full-time",
            "description": "Lead growth initiatives through experimentation, analytics, and customer acquisition strategies.",
            "missing_skills": ["A/B Testing", "Growth Hacking", "Marketing Automation"]
        },
        {
            "id": "job_019",
            "title": "Sales Engineer",
            "company": "TechSales Pro",
            "location": "Mumbai, India",
            "type": "Full-time",
            "description": "Bridge technical expertise with sales to demonstrate product value to enterprise clients.",
            "missing_skills": ["Technical Presentations", "CRM", "Solution Architecture"]
        },
        {
            "id": "job_020",
            "title": "Operations Manager",
            "company": "LogiFlow Systems",
            "location": "Pune, India",
            "type": "Full-time",
            "description": "Optimize operational processes and manage cross-functional teams to improve efficiency.",
            "missing_skills": ["Process Optimization", "Six Sigma", "Project Management"]
        },
        {
            "id": "job_021",
            "title": "Product Designer",
            "company": "PixelPerfect Studios",
            "location": "Bangalore, India",
            "type": "Full-time",
            "description": "Design end-to-end product experiences from concept to final implementation.",
            "missing_skills": ["Sketch", "Design Systems", "Interaction Design"]
        },
        {
            "id": "job_022",
            "title": "Graphic Designer",
            "company": "CreativeMinds Agency",
            "location": "Ahmedabad, India",
            "type": "Full-time",
            "description": "Create compelling visual designs for branding, marketing materials, and digital campaigns.",
            "missing_skills": ["Adobe Illustrator", "Photoshop", "Brand Identity"]
        },
        {
            "id": "job_023",
            "title": "Motion Graphics Designer",
            "company": "AnimateNow Studios",
            "location": "Mumbai, India",
            "type": "Full-time",
            "description": "Produce engaging motion graphics and animations for video content and digital media.",
            "missing_skills": ["After Effects", "Cinema 4D", "Animation Principles"]
        },
        {
            "id": "job_024",
            "title": "Video Editor",
            "company": "MediaCraft Productions",
            "location": "Hyderabad, India",
            "type": "Full-time",
            "description": "Edit and produce high-quality video content for various platforms and audiences.",
            "missing_skills": ["Premiere Pro", "Color Grading", "Sound Design"]
        },
        {
            "id": "job_025",
            "title": "Content Creator",
            "company": "SocialBuzz Media",
            "location": "Delhi, India",
            "type": "Full-time",
            "description": "Develop engaging content across multiple formats including video, blogs, and social media.",
            "missing_skills": ["Content Strategy", "Video Production", "Social Media Trends"]
        },
        {
            "id": "job_026",
            "title": "Content Writer",
            "company": "WordSmith Content Agency",
            "location": "Bangalore, India",
            "type": "Full-time",
            "description": "Write compelling content for websites, blogs, and marketing materials across industries.",
            "missing_skills": ["SEO Writing", "Copywriting", "Content Management Systems"]
        },
        {
            "id": "job_027",
            "title": "Technical Writer",
            "company": "DocuTech Solutions",
            "location": "Pune, India",
            "type": "Full-time",
            "description": "Create clear technical documentation, API guides, and user manuals for software products.",
            "missing_skills": ["API Documentation", "Markdown", "Technical Communication"]
        },
        {
            "id": "job_028",
            "title": "Copywriter",
            "company": "AdWords Creative",
            "location": "Mumbai, India",
            "type": "Full-time",
            "description": "Craft persuasive copy for advertising campaigns, websites, and marketing collateral.",
            "missing_skills": ["Creative Writing", "Brand Voice", "Campaign Strategy"]
        },
        {
            "id": "job_029",
            "title": "Social Media Manager",
            "company": "ViralReach Digital",
            "location": "Gurgaon, India",
            "type": "Full-time",
            "description": "Manage social media presence, create content calendars, and engage with online communities.",
            "missing_skills": ["Social Media Analytics", "Community Management", "Content Planning"]
        },
        {
            "id": "job_030",
            "title": "Research Scientist",
            "company": "Innovation Labs India",
            "location": "Bangalore, India",
            "type": "Full-time",
            "description": "Conduct advanced research in computer science and publish findings in top-tier conferences.",
            "missing_skills": ["Research Methodology", "Academic Writing", "Statistical Analysis"]
        },
        {
            "id": "job_031",
            "title": "Data Research Analyst",
            "company": "ResearchHub Analytics",
            "location": "Chennai, India",
            "type": "Full-time",
            "description": "Perform quantitative and qualitative research to support business decision-making.",
            "missing_skills": ["SPSS", "Survey Design", "Data Mining"]
        },
        {
            "id": "job_032",
            "title": "Electronics Engineer",
            "company": "CircuitTech Industries",
            "location": "Hyderabad, India",
            "type": "Full-time",
            "description": "Design and develop electronic circuits and embedded systems for consumer products.",
            "missing_skills": ["PCB Design", "Embedded C", "Circuit Simulation"]
        },
        {
            "id": "job_033",
            "title": "Embedded Systems Developer",
            "company": "EmbedCore Solutions",
            "location": "Pune, India",
            "type": "Full-time",
            "description": "Develop firmware and software for embedded systems in automotive and IoT applications.",
            "missing_skills": ["ARM Architecture", "RTOS", "Hardware Debugging"]
        },
        {
            "id": "job_034",
            "title": "IoT Engineer",
            "company": "SmartConnect Technologies",
            "location": "Bangalore, India",
            "type": "Full-time",
            "description": "Build IoT solutions connecting devices, sensors, and cloud platforms for smart applications.",
            "missing_skills": ["MQTT", "IoT Protocols", "Sensor Integration"]
        },
        {
            "id": "job_035",
            "title": "Robotics Engineer",
            "company": "RoboTech Innovations",
            "location": "Chennai, India",
            "type": "Full-time",
            "description": "Design and program robotic systems for industrial automation and autonomous applications.",
            "missing_skills": ["ROS", "Computer Vision", "Control Systems"]
        },
        {
            "id": "job_036",
            "title": "Blockchain Developer",
            "company": "CryptoChain Labs",
            "location": "Mumbai, India",
            "type": "Full-time",
            "description": "Develop decentralized applications and smart contracts on blockchain platforms.",
            "missing_skills": ["Solidity", "Web3.js", "Smart Contracts"]
        },
        {
            "id": "job_037",
            "title": "FinTech Product Manager",
            "company": "PayNext Solutions",
            "location": "Bangalore, India",
            "type": "Full-time",
            "description": "Lead product development for digital payment and financial technology solutions.",
            "missing_skills": ["Payment Systems", "Regulatory Compliance", "UPI Integration"]
        },
        {
            "id": "job_038",
            "title": "HealthTech Developer",
            "company": "MediCare Technologies",
            "location": "Hyderabad, India",
            "type": "Full-time",
            "description": "Build healthcare applications and telemedicine platforms to improve patient care.",
            "missing_skills": ["HIPAA Compliance", "Healthcare APIs", "Medical Informatics"]
        },
        {
            "id": "job_039",
            "title": "EdTech Content Developer",
            "company": "LearnSphere India",
            "location": "Delhi, India",
            "type": "Full-time",
            "description": "Create engaging educational content and interactive learning experiences for online platforms.",
            "missing_skills": ["Instructional Design", "LMS", "Educational Technology"]
        },
        {
            "id": "job_040",
            "title": "Automation Engineer",
            "company": "AutoFlow Systems",
            "location": "Pune, India",
            "type": "Full-time",
            "description": "Design and implement automation solutions for manufacturing and industrial processes.",
            "missing_skills": ["PLC Programming", "SCADA", "Industrial Automation"]
        },
        {
            "id": "job_041",
            "title": "Market Research Analyst",
            "company": "InsightPro Research",
            "location": "Mumbai, India",
            "type": "Full-time",
            "description": "Conduct market research studies and analyze consumer behavior to guide business strategy.",
            "missing_skills": ["Market Analysis", "Consumer Insights", "Survey Tools"]
        },
        {
            "id": "job_042",
            "title": "Startup Operations Associate",
            "company": "VentureHub Accelerator",
            "location": "Bangalore, India",
            "type": "Internship",
            "description": "Support startup operations including fundraising, partnerships, and growth initiatives.",
            "missing_skills": ["Startup Ecosystem", "Pitch Decks", "Investor Relations"]
        },
        {
            "id": "job_043",
            "title": "Renewable Energy Engineer",
            "company": "GreenPower Solutions",
            "location": "Ahmedabad, India",
            "type": "Full-time",
            "description": "Design and optimize solar and wind energy systems for sustainable power generation.",
            "missing_skills": ["Solar PV Design", "Energy Modeling", "Grid Integration"]
        },
        {
            "id": "job_044",
            "title": "Cloud Solutions Architect",
            "company": "CloudScale Technologies",
            "location": "Gurgaon, India",
            "type": "Full-time",
            "description": "Architect enterprise cloud solutions and lead cloud migration projects for large organizations.",
            "missing_skills": ["Azure", "Cloud Architecture", "Migration Strategies"]
        },
        {
            "id": "job_045",
            "title": "Penetration Tester",
            "company": "SecureShield Cybersecurity",
            "location": "Bangalore, India",
            "type": "Full-time",
            "description": "Conduct security assessments and penetration testing to identify vulnerabilities in systems.",
            "missing_skills": ["Ethical Hacking", "Kali Linux", "Vulnerability Assessment"]
        }
    ]
    
    # Filter jobs based on search query - maps field labels to relevant jobs
    filtered_jobs = []
    for job in mock_jobs:
        job_text = f"{job['title']} {job['company']} {job['description']}".lower()
        query_terms = query.split()
        
        # Check if any query term matches job content
        if any(term in job_text for term in query_terms if term):
            filtered_jobs.append(job)
    
    # If no matches found, return some default India jobs - fallback logic
    if not filtered_jobs and query:
        filtered_jobs = mock_jobs[:3]  # Return first 3 as fallback
    
    # Filter by location if specified - ensures India-only constraint
    if location and 'india' in location:
        # All mock jobs are already India-based, but this handles real API integration
        filtered_jobs = [job for job in filtered_jobs if 'india' in job['location'].lower()]
    
    # Limit results - respects API rate limits
    filtered_jobs = filtered_jobs[:limit]
    
    # Generate charts for visualization
    try:
        # Prepare graph data from all mock jobs
        graph_data = prepare_job_graph_data(mock_jobs)
        
        # Generate bar chart (job field distribution)
        generate_job_field_chart(
            graph_data['jobs_per_field']['fields'],
            graph_data['jobs_per_field']['counts']
        )
        
        # Generate pie chart (skill frequency) - use first job as example
        if filtered_jobs and len(filtered_jobs) > 0:
            selected_job_id = filtered_jobs[0]['id']
            graph_data_with_skills = prepare_job_graph_data(mock_jobs, selected_job_id)
            
            if len(graph_data_with_skills['skill_frequency']['skills']) > 0:
                generate_skill_gap_chart(
                    graph_data_with_skills['skill_frequency']['skills'],
                    graph_data_with_skills['skill_frequency']['frequencies']
                )
    except Exception as e:
        print(f"Chart generation error: {e}")
        # Continue even if chart generation fails
    
    return jsonify({
        "success": True,
        "jobs": filtered_jobs,
        "total": len(filtered_jobs),
        "query": query,
        "location": location
    })


# ---------------- GENERATE CHARTS FOR SPECIFIC JOB ----------------
@app.route("/api/generate-job-charts/<job_id>")
def generate_job_charts(job_id):
    """Generate charts dynamically for a specific job"""
    try:
        # Check if user has skills in session
        if 'user_skills' not in session or not session.get('user_skills'):
            print("ERROR: No user_skills in session")
            return jsonify({
                "success": False,
                "error": "Please create and evaluate a resume first"
            }), 400
        
        print(f"DEBUG: Generating charts for job_id: {job_id}")
        print(f"DEBUG: User skills in session: {session.get('user_skills')}")
        # Mock job database (same as in search_jobs route)
        mock_jobs = [
            {"id": "job_001", "title": "Software Developer", "company": "TechCorp Solutions", "location": "Bangalore, India", "type": "Full-time", "description": "Join our team to build cutting-edge software solutions using modern technologies.", "missing_skills": ["Python", "React", "Node.js"]},
            {"id": "job_002", "title": "Frontend Developer", "company": "WebFlow Inc", "location": "Mumbai, India", "type": "Full-time", "description": "Create amazing user experiences with React, Vue.js, and modern frontend frameworks.", "missing_skills": ["Vue.js", "TypeScript", "SASS"]},
            {"id": "job_003", "title": "Data Scientist", "company": "DataVision Analytics", "location": "Hyderabad, India", "type": "Full-time", "description": "Analyze complex datasets and build machine learning models to drive business insights.", "missing_skills": ["R", "TensorFlow", "Statistics"]},
            {"id": "job_004", "title": "Machine Learning Engineer", "company": "AI Innovations", "location": "Pune, India", "type": "Full-time", "description": "Develop and deploy ML models at scale using Python, TensorFlow, and cloud platforms.", "missing_skills": ["PyTorch", "Kubernetes", "MLOps"]},
            {"id": "job_005", "title": "Cloud Engineer", "company": "CloudTech Systems", "location": "Chennai, India", "type": "Full-time", "description": "Design and manage cloud infrastructure using AWS, Azure, and containerization technologies.", "missing_skills": ["AWS", "Docker", "Terraform"]},
            {"id": "job_006", "title": "Cybersecurity Analyst", "company": "SecureNet Solutions", "location": "Delhi, India", "type": "Full-time", "description": "Protect organizational assets by implementing security measures and monitoring threats.", "missing_skills": ["Penetration Testing", "SIEM", "Incident Response"]},
            {"id": "job_007", "title": "DevOps Engineer", "company": "DeployFast Inc", "location": "Gurgaon, India", "type": "Full-time", "description": "Streamline development workflows with CI/CD pipelines and infrastructure automation.", "missing_skills": ["Jenkins", "Ansible", "Monitoring"]},
            {"id": "job_008", "title": "Mobile App Developer", "company": "MobileFirst Studios", "location": "Noida, India", "type": "Full-time", "description": "Build native and cross-platform mobile applications for iOS and Android.", "missing_skills": ["Swift", "Kotlin", "React Native"]},
            {"id": "job_009", "title": "Product Manager", "company": "InnovatePro", "location": "Kolkata, India", "type": "Full-time", "description": "Drive product strategy and work with cross-functional teams to deliver user-centric solutions.", "missing_skills": ["Roadmapping", "Agile", "Stakeholder Management"]},
            {"id": "job_010", "title": "UX/UI Designer", "company": "DesignHub Creative", "location": "Ahmedabad, India", "type": "Full-time", "description": "Create intuitive and beautiful user interfaces that enhance user experience.", "missing_skills": ["Figma", "Prototyping", "User Research"]},
            {"id": "job_011", "title": "Backend Developer", "company": "ServerStack Technologies", "location": "Bangalore, India", "type": "Full-time", "description": "Build scalable backend systems and RESTful APIs using Java, Spring Boot, and microservices architecture.", "missing_skills": ["Spring Boot", "Microservices", "PostgreSQL"]},
            {"id": "job_012", "title": "Full Stack Developer", "company": "CodeCraft Solutions", "location": "Pune, India", "type": "Full-time", "description": "Work on end-to-end web applications using MERN stack and modern development practices.", "missing_skills": ["MongoDB", "Express.js", "Redux"]},
            {"id": "job_013", "title": "Data Analyst", "company": "InsightMetrics", "location": "Mumbai, India", "type": "Full-time", "description": "Transform raw data into actionable insights using SQL, Python, and visualization tools.", "missing_skills": ["Power BI", "Tableau", "Advanced Excel"]},
            {"id": "job_014", "title": "AI Research Intern", "company": "DeepMind Labs India", "location": "Hyderabad, India", "type": "Internship", "description": "Contribute to cutting-edge AI research projects in natural language processing and computer vision.", "missing_skills": ["Research Methodology", "PyTorch", "NLP"]},
            {"id": "job_015", "title": "Database Administrator", "company": "DataGuard Systems", "location": "Chennai, India", "type": "Full-time", "description": "Manage and optimize database systems ensuring high availability and performance.", "missing_skills": ["Oracle", "MySQL", "Database Tuning", "Backup Strategies"]},
            {"id": "job_016", "title": "Digital Marketing Specialist", "company": "GrowthHackers India", "location": "Delhi, India", "type": "Full-time", "description": "Drive online marketing campaigns across SEO, SEM, social media, and content marketing channels.", "missing_skills": ["Google Ads", "SEO", "Analytics"]},
            {"id": "job_017", "title": "Business Analyst", "company": "StrategyFirst Consulting", "location": "Bangalore, India", "type": "Full-time", "description": "Analyze business processes and requirements to deliver data-driven recommendations.", "missing_skills": ["Business Intelligence", "SQL", "Requirements Gathering"]},
            {"id": "job_018", "title": "Growth Marketing Manager", "company": "ScaleUp Ventures", "location": "Gurgaon, India", "type": "Full-time", "description": "Lead growth initiatives through experimentation, analytics, and customer acquisition strategies.", "missing_skills": ["A/B Testing", "Growth Hacking", "Marketing Automation"]},
            {"id": "job_019", "title": "Sales Engineer", "company": "TechSales Pro", "location": "Mumbai, India", "type": "Full-time", "description": "Bridge technical expertise with sales to demonstrate product value to enterprise clients.", "missing_skills": ["Technical Presentations", "CRM", "Solution Architecture"]},
            {"id": "job_020", "title": "Operations Manager", "company": "LogiFlow Systems", "location": "Pune, India", "type": "Full-time", "description": "Optimize operational processes and manage cross-functional teams to improve efficiency.", "missing_skills": ["Process Optimization", "Six Sigma", "Project Management"]},
            {"id": "job_021", "title": "Product Designer", "company": "PixelPerfect Studios", "location": "Bangalore, India", "type": "Full-time", "description": "Design end-to-end product experiences from concept to final implementation.", "missing_skills": ["Sketch", "Design Systems", "Interaction Design"]},
            {"id": "job_022", "title": "Graphic Designer", "company": "CreativeMinds Agency", "location": "Ahmedabad, India", "type": "Full-time", "description": "Create compelling visual designs for branding, marketing materials, and digital campaigns.", "missing_skills": ["Adobe Illustrator", "Photoshop", "Brand Identity"]},
            {"id": "job_023", "title": "Motion Graphics Designer", "company": "AnimateNow Studios", "location": "Mumbai, India", "type": "Full-time", "description": "Produce engaging motion graphics and animations for video content and digital media.", "missing_skills": ["After Effects", "Cinema 4D", "Animation Principles"]},
            {"id": "job_024", "title": "Video Editor", "company": "MediaCraft Productions", "location": "Hyderabad, India", "type": "Full-time", "description": "Edit and produce high-quality video content for various platforms and audiences.", "missing_skills": ["Premiere Pro", "Color Grading", "Sound Design"]},
            {"id": "job_025", "title": "Content Creator", "company": "SocialBuzz Media", "location": "Delhi, India", "type": "Full-time", "description": "Develop engaging content across multiple formats including video, blogs, and social media.", "missing_skills": ["Content Strategy", "Video Production", "Social Media Trends"]},
            {"id": "job_026", "title": "Content Writer", "company": "WordSmith Content Agency", "location": "Bangalore, India", "type": "Full-time", "description": "Write compelling content for websites, blogs, and marketing materials across industries.", "missing_skills": ["SEO Writing", "Copywriting", "Content Management Systems"]},
            {"id": "job_027", "title": "Technical Writer", "company": "DocuTech Solutions", "location": "Pune, India", "type": "Full-time", "description": "Create clear technical documentation, API guides, and user manuals for software products.", "missing_skills": ["API Documentation", "Markdown", "Technical Communication"]},
            {"id": "job_028", "title": "Copywriter", "company": "AdWords Creative", "location": "Mumbai, India", "type": "Full-time", "description": "Craft persuasive copy for advertising campaigns, websites, and marketing collateral.", "missing_skills": ["Creative Writing", "Brand Voice", "Campaign Strategy"]},
            {"id": "job_029", "title": "Social Media Manager", "company": "ViralReach Digital", "location": "Gurgaon, India", "type": "Full-time", "description": "Manage social media presence, create content calendars, and engage with online communities.", "missing_skills": ["Social Media Analytics", "Community Management", "Content Planning"]},
            {"id": "job_030", "title": "Research Scientist", "company": "Innovation Labs India", "location": "Bangalore, India", "type": "Full-time", "description": "Conduct advanced research in computer science and publish findings in top-tier conferences.", "missing_skills": ["Research Methodology", "Academic Writing", "Statistical Analysis"]},
            {"id": "job_031", "title": "Data Research Analyst", "company": "ResearchHub Analytics", "location": "Chennai, India", "type": "Full-time", "description": "Perform quantitative and qualitative research to support business decision-making.", "missing_skills": ["SPSS", "Survey Design", "Data Mining"]},
            {"id": "job_032", "title": "Electronics Engineer", "company": "CircuitTech Industries", "location": "Hyderabad, India", "type": "Full-time", "description": "Design and develop electronic circuits and embedded systems for consumer products.", "missing_skills": ["PCB Design", "Embedded C", "Circuit Simulation"]},
            {"id": "job_033", "title": "Embedded Systems Developer", "company": "EmbedCore Solutions", "location": "Pune, India", "type": "Full-time", "description": "Develop firmware and software for embedded systems in automotive and IoT applications.", "missing_skills": ["ARM Architecture", "RTOS", "Hardware Debugging"]},
            {"id": "job_034", "title": "IoT Engineer", "company": "SmartConnect Technologies", "location": "Bangalore, India", "type": "Full-time", "description": "Build IoT solutions connecting devices, sensors, and cloud platforms for smart applications.", "missing_skills": ["MQTT", "IoT Protocols", "Sensor Integration"]},
            {"id": "job_035", "title": "Robotics Engineer", "company": "RoboTech Innovations", "location": "Chennai, India", "type": "Full-time", "description": "Design and program robotic systems for industrial automation and autonomous applications.", "missing_skills": ["ROS", "Computer Vision", "Control Systems"]},
            {"id": "job_036", "title": "Blockchain Developer", "company": "CryptoChain Labs", "location": "Mumbai, India", "type": "Full-time", "description": "Develop decentralized applications and smart contracts on blockchain platforms.", "missing_skills": ["Solidity", "Web3.js", "Smart Contracts"]},
            {"id": "job_037", "title": "FinTech Product Manager", "company": "PayNext Solutions", "location": "Bangalore, India", "type": "Full-time", "description": "Lead product development for digital payment and financial technology solutions.", "missing_skills": ["Payment Systems", "Regulatory Compliance", "UPI Integration"]},
            {"id": "job_038", "title": "HealthTech Developer", "company": "MediCare Technologies", "location": "Hyderabad, India", "type": "Full-time", "description": "Build healthcare applications and telemedicine platforms to improve patient care.", "missing_skills": ["HIPAA Compliance", "Healthcare APIs", "Medical Informatics"]},
            {"id": "job_039", "title": "EdTech Content Developer", "company": "LearnSphere India", "location": "Delhi, India", "type": "Full-time", "description": "Create engaging educational content and interactive learning experiences for online platforms.", "missing_skills": ["Instructional Design", "LMS", "Educational Technology"]},
            {"id": "job_040", "title": "Automation Engineer", "company": "AutoFlow Systems", "location": "Pune, India", "type": "Full-time", "description": "Design and implement automation solutions for manufacturing and industrial processes.", "missing_skills": ["PLC Programming", "SCADA", "Industrial Automation"]},
            {"id": "job_041", "title": "Market Research Analyst", "company": "InsightPro Research", "location": "Mumbai, India", "type": "Full-time", "description": "Conduct market research studies and analyze consumer behavior to guide business strategy.", "missing_skills": ["Market Analysis", "Consumer Insights", "Survey Tools"]},
            {"id": "job_042", "title": "Startup Operations Associate", "company": "VentureHub Accelerator", "location": "Bangalore, India", "type": "Internship", "description": "Support startup operations including fundraising, partnerships, and growth initiatives.", "missing_skills": ["Startup Ecosystem", "Pitch Decks", "Investor Relations"]},
            {"id": "job_043", "title": "Renewable Energy Engineer", "company": "GreenPower Solutions", "location": "Ahmedabad, India", "type": "Full-time", "description": "Design and optimize solar and wind energy systems for sustainable power generation.", "missing_skills": ["Solar PV Design", "Energy Modeling", "Grid Integration"]},
            {"id": "job_044", "title": "Cloud Solutions Architect", "company": "CloudScale Technologies", "location": "Gurgaon, India", "type": "Full-time", "description": "Architect enterprise cloud solutions and lead cloud migration projects for large organizations.", "missing_skills": ["Azure", "Cloud Architecture", "Migration Strategies"]},
            {"id": "job_045", "title": "Penetration Tester", "company": "SecureShield Cybersecurity", "location": "Bangalore, India", "type": "Full-time", "description": "Conduct security assessments and penetration testing to identify vulnerabilities in systems.", "missing_skills": ["Ethical Hacking", "Kali Linux", "Vulnerability Assessment"]}
        ]
        
        # Find the selected job
        selected_job = None
        for job in mock_jobs:
            if job['id'] == job_id:
                selected_job = job
                break
        
        if not selected_job:
            return jsonify({"success": False, "error": "Job not found"}), 404
        
        # Generate bar chart (all jobs field distribution)
        graph_data = prepare_job_graph_data(mock_jobs)
        generate_job_field_chart(
            graph_data['jobs_per_field']['fields'],
            graph_data['jobs_per_field']['counts']
        )
        
        # Generate pie chart for THIS specific job's missing skills
        graph_data_with_skills = prepare_job_graph_data(mock_jobs, selected_job_id=job_id)
        
        if len(graph_data_with_skills['skill_frequency']['skills']) > 0:
            generate_skill_gap_chart(
                graph_data_with_skills['skill_frequency']['skills'],
                graph_data_with_skills['skill_frequency']['frequencies']
            )
        else:
            # No skills data available
            return jsonify({
                "success": False,
                "error": "No skill data available for this job"
            }), 400
        
        # Generate line chart for skill readiness progress
        # Get user's skills from session to calculate job fit score
        user_skills_str = session.get('user_skills', '')
        user_skills = [s.strip() for s in user_skills_str.split(',') if s.strip()]
        
        # Get job required skills
        job_required_skills = selected_job.get('missing_skills', [])
        
        # Calculate job fit score based on skill matching
        job_fit_score, missing_skills_count, total_job_skills = calculate_job_fit_score(
            user_skills, 
            job_required_skills
        )
        
        # Generate line chart with job fit score
        generate_skill_readiness_chart(
            job_title=selected_job['title'],
            missing_skills_count=missing_skills_count,
            current_job_fit_score=job_fit_score,
            total_job_skills=total_job_skills
        )
        
        # Get resume score and status for frontend
        current_resume_score = session.get('last_score', 60)
        if current_resume_score >= 80:
            resume_status = "Ready"
        elif current_resume_score >= 60:
            resume_status = "Partially Ready"
        else:
            resume_status = "Not Ready"
        
        return jsonify({
            "success": True,
            "job_title": selected_job['title'],
            "job_company": selected_job['company'],
            "missing_skills_count": missing_skills_count,
            "resume_score": current_resume_score,
            "job_fit_score": job_fit_score,  # Add job fit score to response
            "resume_status": resume_status,
            "message": f"Charts generated for {selected_job['title']} at {selected_job['company']}"
        })
        
    except Exception as e:
        print(f"Chart generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- GET EVALUATION SUMMARY (SIMPLE) ----------------
@app.route("/api/get-summary")
def get_summary():
    """
    Simple route to get evaluation summary.
    Uses only basic Python - if/else logic.
    """
    
    # Get data from session (simple)
    resume_score = session.get("last_score", 0)
    missing_skills = session.get("last_missing_skills", [])
    job_fit_score = session.get("job_fit_score", 0)
    
    # Calculate resume status (simple if/else)
    if resume_score >= 80:
        resume_status = "Ready"
    elif resume_score >= 60:
        resume_status = "Partially Ready"
    else:
        resume_status = "Not Ready"
    
    # Calculate eligibility based on job fit score (simple if/else)
    if job_fit_score >= 70:
        eligibility = "Eligible"
    elif job_fit_score >= 40:
        eligibility = "Partially Eligible"
    else:
        eligibility = "Not Eligible"
    
    # Calculate confidence level (simple if/else)
    # Confidence should consider BOTH resume readiness AND job fit
    if resume_status == "Ready" and job_fit_score >= 70:
        confidence_level = "High"
    elif resume_status == "Partially Ready" or (resume_status == "Ready" and job_fit_score >= 40):
        confidence_level = "Medium"
    else:
        confidence_level = "Low"
    
    # Count missing skills (simple)
    missing_skills_count = len(missing_skills)
    
    # Return simple dictionary
    return jsonify({
        "success": True,
        "resume_score": resume_score,
        "resume_status": resume_status,
        "job_fit_score": job_fit_score,
        "eligibility": eligibility,
        "confidence_level": confidence_level,
        "missing_skills_count": missing_skills_count,
        "has_missing_skills": missing_skills_count > 0
    })


# ---------------- RESET EVALUATION (SIMPLE) ----------------
@app.route("/reset-evaluation")
def reset_evaluation():
    """
    Simple route to reset evaluation.
    Clears session data and redirects to home.
    """
    
    # Clear evaluation data from session (simple)
    session.pop("last_score", None)
    session.pop("last_missing_skills", None)
    session.pop("selected_job_title", None)
    session.pop("selected_job_company", None)
    session.pop("job_fit_score", None)
    
    # Redirect to home (simple)
    return redirect("/")


# ---------------- STORE JOB DATA IN SESSION ----------------
@app.route("/api/store-job-data", methods=["POST"])
def store_job_data():
    """
    Store job data in session AND update database with job_fit_score.
    """
    try:
        # Get data from request
        data = request.get_json()
        
        # Store in session
        session["selected_job_title"] = data.get("job_title", "Not Selected")
        session["selected_job_company"] = data.get("job_company", "Not Selected")
        job_fit_score = data.get("job_fit_score", 0)
        session["job_fit_score"] = job_fit_score
        
        # Update database with job_fit_score for the latest resume
        if "user_email" in session:
            user_email = session["user_email"]
            
            conn = get_db()
            cur = conn.cursor()
            
            # Get the latest resume ID for this user
            cur.execute("""
                SELECT id FROM resumes
                WHERE user_email = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_email,))
            
            result = cur.fetchone()
            if result:
                resume_id = result[0]
                
                # Update job_fit_score in database
                cur.execute("""
                    UPDATE resumes
                    SET job_fit_score = ?
                    WHERE id = ?
                """, (job_fit_score, resume_id))
                
                conn.commit()
            
            conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error storing job data: {e}")
        return jsonify({"success": False})


# ---------------- DOWNLOAD EVALUATION REPORT ----------------
@app.route("/download_report")
def download_report():
    """
    Simple route to display evaluation report.
    Uses only basic Python - no complex logic.
    """
    
    # Get data from session (already stored)
    resume_score = session.get("last_score", 0)
    missing_skills = session.get("last_missing_skills", [])
    user_email = session.get("user_email", "Guest")
    
    # Calculate readiness status using simple if/else
    if resume_score >= 80:
        readiness_status = "Ready"
    elif resume_score >= 60:
        readiness_status = "Partially Ready"
    else:
        readiness_status = "Not Ready"
    
    # Get resume details from database (simple query)
    resume_data = None
    if user_email != "Guest":
        conn = get_db()
        cur = conn.cursor()
        
        # Get latest resume for this user
        cur.execute("""
            SELECT name, email, phone, degree, cgpa, skills, projects, city, github_username, about_yourself
            FROM resumes
            WHERE user_email = ?
            ORDER BY id DESC
            LIMIT 1
        """, (user_email,))
        
        row = cur.fetchone()
        conn.close()
        
        # Store in simple dictionary
        if row:
            resume_data = {
                "name": row[0],
                "email": row[1],
                "phone": row[2],
                "degree": row[3],
                "cgpa": row[4],
                "skills": row[5],
                "projects": row[6],
                "city": row[7],
                "github_username": row[8],
                "about_yourself": row[9]
            }
    
    # Get job-specific data from session (if available)
    job_title = session.get("selected_job_title", "Not Selected")
    job_company = session.get("selected_job_company", "Not Selected")
    job_fit_score = session.get("job_fit_score", 0)
    
    # ========== NEW ANALYTICAL SECTIONS ==========
    
    # 1. Role Based Evaluation - Calculate role readiness status
    role_readiness_status = "Not Evaluated"
    if job_title != "Not Selected" and job_fit_score > 0:
        if job_fit_score >= 70:
            role_readiness_status = "Ready for Role"
        elif job_fit_score >= 50:
            role_readiness_status = "Partially Ready"
        else:
            role_readiness_status = "Not Ready"
    
    # 2. Skill Gap Learning Roadmap - Generate phases from missing skills
    skill_roadmap = None
    if missing_skills and len(missing_skills) > 0:
        # Categorize skills into phases based on priority
        # Phase 1: First 3 skills (Core)
        # Phase 2: Next 3 skills (Intermediate)
        # Phase 3: Remaining skills (Advanced)
        phase1_skills = missing_skills[:3] if len(missing_skills) >= 3 else missing_skills
        phase2_skills = missing_skills[3:6] if len(missing_skills) > 3 else []
        phase3_skills = missing_skills[6:] if len(missing_skills) > 6 else []
        
        skill_roadmap = {
            'phase1': phase1_skills,
            'phase2': phase2_skills,
            'phase3': phase3_skills,
            'total_skills': len(missing_skills)
        }
    
    # 3. Role Switch Impact Analysis - Calculate difference between scores
    role_impact = None
    if job_title != "Not Selected" and job_fit_score > 0:
        score_difference = resume_score - job_fit_score
        
        # Determine impact level
        if abs(score_difference) > 20:
            impact_level = "Significant"
            if score_difference > 0:
                impact_message = "Significant role mismatch detected. Your general resume is stronger than your fit for this specific role."
            else:
                impact_message = "Strong role alignment! You are better suited for this role than your general resume suggests."
        elif abs(score_difference) >= 10:
            impact_level = "Moderate"
            if score_difference > 0:
                impact_message = "Moderate skill alignment gap. Some role-specific skills need improvement."
            else:
                impact_message = "Good role alignment with room for general resume improvement."
        else:
            impact_level = "Minimal"
            impact_message = "Strong alignment between resume and role. Your skills match well with job requirements."
        
        role_impact = {
            'difference': score_difference,
            'impact_level': impact_level,
            'message': impact_message,
            'resume_score': resume_score,
            'job_fit_score': job_fit_score
        }
    
    # 4. Resume Strength Breakdown - Use resume_breakdown module
    resume_breakdown_data = None
    if resume_data:
        try:
            breakdown = resume_breakdown.calculate_resume_breakdown(
                cgpa=resume_data.get('cgpa', '0'),
                skills=resume_data.get('skills', ''),
                projects=resume_data.get('projects', ''),
                education_count=1,
                extras={
                    'github_username': resume_data.get('github_username'),
                    'about_yourself': resume_data.get('about_yourself'),
                    'city': resume_data.get('city')
                }
            )
            resume_breakdown_data = breakdown
        except Exception as e:
            print(f"Error calculating resume breakdown: {e}")
            resume_breakdown_data = None
    
    # Pass all data to template (simple variables)
    return render_template(
        "report.html",
        resume_score=resume_score,
        readiness_status=readiness_status,
        missing_skills=missing_skills,
        resume_data=resume_data,
        job_title=job_title,
        job_company=job_company,
        job_fit_score=job_fit_score,
        # New analytical sections
        role_readiness_status=role_readiness_status,
        skill_roadmap=skill_roadmap,
        role_impact=role_impact,
        resume_breakdown_data=resume_breakdown_data
    )




# ============================================================================
# ENHANCED FEATURES - RULE-BASED EVALUATION SYSTEM
# ============================================================================

# ---------------- GET ALL AVAILABLE ROLES ----------------
@app.route("/api/roles/list")
def get_roles_list():
    """Get list of all available roles"""
    try:
        roles = role_evaluator.get_all_roles()
        roles_with_desc = []
        
        for role in roles:
            req = role_evaluator.get_role_requirements(role)
            roles_with_desc.append({
                'name': role,
                'description': req['description'],
                'min_cgpa': req['min_cgpa'],
                'min_projects': req['min_projects']
            })
        
        return jsonify({
            "success": True,
            "roles": roles_with_desc,
            "total_roles": len(roles)
        })
    except Exception as e:
        print(f"Error getting roles: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- EVALUATE ROLE FIT ----------------
@app.route("/api/roles/evaluate", methods=["POST"])
def evaluate_role_fit():
    """Evaluate user's fit for a specific role"""
    try:
        data = request.get_json()
        role_name = data.get('role_name')
        
        # Get user data from session
        user_skills_str = session.get('user_skills', '')
        user_skills = [s.strip() for s in user_skills_str.split(',') if s.strip()]
        
        # Get CGPA and projects from session or data
        cgpa = float(data.get('cgpa', session.get('user_cgpa', 7.0)))
        projects_str = data.get('projects', session.get('user_projects', ''))
        
        # Count projects
        if projects_str:
            project_lines = [line.strip() for line in projects_str.split('\n') if line.strip()]
            projects_count = len(project_lines)
        else:
            projects_count = 0
        
        # Calculate role fit
        result = role_evaluator.calculate_role_fit_score(
            user_skills, cgpa, projects_count, role_name
        )
        
        if not result:
            return jsonify({"success": False, "error": "Role not found"}), 404
        
        # Get role requirements
        role_req = role_evaluator.get_role_requirements(role_name)
        
        # Categorize missing skills
        missing_categorized = role_evaluator.categorize_missing_skills(result)
        
        # Generate skill roadmap
        roadmap = skill_roadmap.generate_skill_roadmap(missing_categorized)
        roadmap_summary = skill_roadmap.get_roadmap_summary(roadmap)
        
        # Calculate confidence index
        resume_score = session.get('last_score', 70)
        confidence = confidence_calculator.calculate_confidence_index(
            resume_score,
            result['role_fit_score'],
            len(role_evaluator.get_all_missing_skills(result)),
            role_req
        )
        
        # Store in session
        session['selected_role'] = role_name
        session['role_fit_score'] = result['role_fit_score']
        session['user_cgpa'] = cgpa
        session['user_projects'] = projects_str
        
        return jsonify({
            "success": True,
            "role_name": role_name,
            "role_fit_score": result['role_fit_score'],
            "breakdown": result['breakdown'],
            "missing_skills": {
                'critical': result['missing_core'],
                'important': result['missing_secondary'],
                'nice_to_have': result['missing_bonus']
            },
            "requirements_met": {
                'cgpa': result['cgpa_met'],
                'projects': result['projects_met']
            },
            "roadmap_summary": roadmap_summary,
            "confidence": confidence
        })
        
    except Exception as e:
        print(f"Error evaluating role fit: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- GET SKILL ROADMAP ----------------
@app.route("/api/roadmap/generate", methods=["POST"])
def generate_roadmap():
    """Generate detailed skill learning roadmap"""
    try:
        data = request.get_json()
        role_name = data.get('role_name')
        
        # Get user data
        user_skills_str = session.get('user_skills', '')
        user_skills = [s.strip() for s in user_skills_str.split(',') if s.strip()]
        cgpa = float(session.get('user_cgpa', 7.0))
        projects_str = session.get('user_projects', '')
        projects_count = len([line for line in projects_str.split('\n') if line.strip()])
        
        # Calculate role fit
        result = role_evaluator.calculate_role_fit_score(
            user_skills, cgpa, projects_count, role_name
        )
        
        if not result:
            return jsonify({"success": False, "error": "Role not found"}), 404
        
        # Categorize missing skills
        missing_categorized = role_evaluator.categorize_missing_skills(result)
        
        # Generate roadmap
        roadmap = skill_roadmap.generate_skill_roadmap(missing_categorized)
        
        return jsonify({
            "success": True,
            "roadmap": roadmap,
            "summary": skill_roadmap.get_roadmap_summary(roadmap),
            "next_skill": skill_roadmap.get_next_skill_to_learn(roadmap)
        })
        
    except Exception as e:
        print(f"Error generating roadmap: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- SIMULATE SKILL ACQUISITION ----------------
@app.route("/api/simulator/simulate", methods=["POST"])
def simulate_skills():
    """Simulate adding skills and recalculate scores"""
    try:
        data = request.get_json()
        role_name = data.get('role_name')
        simulated_skills = data.get('simulated_skills', [])
        
        # Get user data
        user_skills_str = session.get('user_skills', '')
        current_skills = [s.strip() for s in user_skills_str.split(',') if s.strip()]
        cgpa = float(session.get('user_cgpa', 7.0))
        projects_str = session.get('user_projects', '')
        projects_count = len([line for line in projects_str.split('\n') if line.strip()])
        
        # Run simulation
        simulation_result = skill_simulator.simulate_skill_acquisition(
            current_skills, simulated_skills, role_name, cgpa, projects_count, role_evaluator
        )
        
        # Get recommendation
        recommendation = skill_simulator.get_simulation_recommendation(simulation_result)
        
        return jsonify({
            "success": True,
            "simulation": simulation_result,
            "recommendation": recommendation
        })
        
    except Exception as e:
        print(f"Error simulating skills: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- COMPARE MULTIPLE ROLES ----------------
@app.route("/api/roles/compare", methods=["POST"])
def compare_multiple_roles():
    """Compare user's fit across multiple roles"""
    try:
        data = request.get_json()
        role_names = data.get('role_names', [])
        
        # Get user data
        user_skills_str = session.get('user_skills', '')
        user_skills = [s.strip() for s in user_skills_str.split(',') if s.strip()]
        cgpa = float(session.get('user_cgpa', 7.0))
        projects_str = session.get('user_projects', '')
        projects_count = len([line for line in projects_str.split('\n') if line.strip()])
        
        # Compare roles
        comparison = role_comparator.compare_roles(
            user_skills, cgpa, projects_count, role_names, role_evaluator
        )
        
        # Get recommendation
        recommendation = role_comparator.get_role_switch_recommendation(comparison)
        
        # Identify common missing skills
        common_skills = role_comparator.identify_common_missing_skills(comparison)
        
        return jsonify({
            "success": True,
            "comparison": comparison,
            "recommendation": recommendation,
            "common_missing_skills": common_skills
        })
        
    except Exception as e:
        print(f"Error comparing roles: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- GET RESUME BREAKDOWN ----------------
@app.route("/api/resume/breakdown")
def get_resume_breakdown():
    """Get detailed resume strength breakdown"""
    try:
        # Get user data from session
        user_email = session.get('user_email')
        
        if not user_email:
            return jsonify({"success": False, "error": "Not logged in"}), 401
        
        # Get latest resume from database
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT cgpa, skills, projects, github_username, about_yourself, city, id
            FROM resumes
            WHERE user_email = ?
            ORDER BY id DESC
            LIMIT 1
        """, (user_email,))
        
        row = cur.fetchone()
        
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "No resume found"}), 404
        
        cgpa, skills, projects, github, about, city, resume_id = row
        
        # Get education count
        cur.execute("""
            SELECT COUNT(*) FROM education WHERE resume_id = ?
        """, (resume_id,))
        
        education_count = cur.fetchone()[0]
        conn.close()
        
        # Calculate breakdown
        extras = {
            'github_username': github,
            'about_yourself': about,
            'city': city
        }
        
        breakdown = resume_breakdown.calculate_resume_breakdown(
            cgpa, skills, projects, education_count, extras
        )
        
        # Get comparison with average
        comparison = resume_breakdown.compare_with_average(breakdown)
        
        # Get improvement priority
        priority = resume_breakdown.get_improvement_priority(breakdown['sections'])
        
        return jsonify({
            "success": True,
            "breakdown": breakdown,
            "comparison_with_average": comparison,
            "improvement_priority": priority
        })
        
    except Exception as e:
        print(f"Error getting resume breakdown: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- RANK SKILLS BY IMPACT ----------------
@app.route("/api/simulator/rank-skills", methods=["POST"])
def rank_skills_by_impact():
    """Rank missing skills by their impact on role fit"""
    try:
        data = request.get_json()
        role_name = data.get('role_name')
        
        # Get user data
        user_skills_str = session.get('user_skills', '')
        current_skills = [s.strip() for s in user_skills_str.split(',') if s.strip()]
        cgpa = float(session.get('user_cgpa', 7.0))
        projects_str = session.get('user_projects', '')
        projects_count = len([line for line in projects_str.split('\n') if line.strip()])
        
        # Get missing skills
        result = role_evaluator.calculate_role_fit_score(
            current_skills, cgpa, projects_count, role_name
        )
        
        if not result:
            return jsonify({"success": False, "error": "Role not found"}), 404
        
        missing_skills = role_evaluator.get_all_missing_skills(result)
        
        # Rank skills by impact
        ranked_skills = skill_simulator.rank_skills_by_impact(
            missing_skills, current_skills, role_name, cgpa, projects_count, role_evaluator
        )
        
        return jsonify({
            "success": True,
            "ranked_skills": [
                {"skill": skill, "impact": impact}
                for skill, impact in ranked_skills
            ]
        })
        
    except Exception as e:
        print(f"Error ranking skills: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
