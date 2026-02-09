"""
Role-Based Evaluation System
Provides predefined role requirements and skill matching logic
"""

# Predefined role requirements with skills categorized by importance
ROLE_REQUIREMENTS = {
    "Software Developer": {
        "core_skills": ["Python", "Java", "C++", "Data Structures", "Algorithms"],
        "secondary_skills": ["Git", "SQL", "Testing", "Debugging"],
        "bonus_skills": ["Docker", "CI/CD", "Agile"],
        "min_projects": 3,
        "min_cgpa": 6.5,
        "description": "Develops software applications using programming languages"
    },
    "Web Developer": {
        "core_skills": ["HTML", "CSS", "JavaScript", "React", "Node.js"],
        "secondary_skills": ["Git", "REST API", "Database", "Responsive Design"],
        "bonus_skills": ["TypeScript", "MongoDB", "AWS"],
        "min_projects": 3,
        "min_cgpa": 6.0,
        "description": "Creates and maintains websites and web applications"
    },
    "Data Analyst": {
        "core_skills": ["Python", "SQL", "Excel", "Statistics", "Data Visualization"],
        "secondary_skills": ["Tableau", "Power BI", "Pandas", "NumPy"],
        "bonus_skills": ["R", "Machine Learning", "Big Data"],
        "min_projects": 2,
        "min_cgpa": 7.0,
        "description": "Analyzes data to provide business insights"
    },
    "Data Scientist": {
        "core_skills": ["Python", "Machine Learning", "Statistics", "SQL", "Data Analysis"],
        "secondary_skills": ["TensorFlow", "PyTorch", "Pandas", "NumPy"],
        "bonus_skills": ["Deep Learning", "NLP", "Big Data", "Cloud"],
        "min_projects": 3,
        "min_cgpa": 7.5,
        "description": "Builds predictive models and analyzes complex data"
    },
    "Frontend Developer": {
        "core_skills": ["HTML", "CSS", "JavaScript", "React", "UI/UX"],
        "secondary_skills": ["TypeScript", "Redux", "Webpack", "Git"],
        "bonus_skills": ["Vue.js", "Angular", "Testing", "Accessibility"],
        "min_projects": 3,
        "min_cgpa": 6.0,
        "description": "Develops user-facing features of web applications"
    },
    "Backend Developer": {
        "core_skills": ["Python", "Java", "Node.js", "SQL", "REST API"],
        "secondary_skills": ["MongoDB", "PostgreSQL", "Redis", "Git"],
        "bonus_skills": ["Microservices", "Docker", "Kubernetes", "AWS"],
        "min_projects": 3,
        "min_cgpa": 6.5,
        "description": "Develops server-side logic and database management"
    },
    "Full Stack Developer": {
        "core_skills": ["HTML", "CSS", "JavaScript", "Python", "SQL", "React"],
        "secondary_skills": ["Node.js", "Git", "REST API", "Database Design"],
        "bonus_skills": ["Docker", "AWS", "MongoDB", "TypeScript"],
        "min_projects": 4,
        "min_cgpa": 7.0,
        "description": "Develops both frontend and backend of applications"
    },
    "Mobile App Developer": {
        "core_skills": ["Java", "Kotlin", "Swift", "React Native", "Mobile UI"],
        "secondary_skills": ["Android Studio", "Xcode", "Git", "REST API"],
        "bonus_skills": ["Flutter", "Firebase", "App Store", "Testing"],
        "min_projects": 3,
        "min_cgpa": 6.5,
        "description": "Develops mobile applications for iOS and Android"
    },
    "DevOps Engineer": {
        "core_skills": ["Linux", "Docker", "Kubernetes", "CI/CD", "Git"],
        "secondary_skills": ["Jenkins", "Ansible", "Terraform", "Monitoring"],
        "bonus_skills": ["AWS", "Azure", "Python", "Shell Scripting"],
        "min_projects": 2,
        "min_cgpa": 6.5,
        "description": "Manages deployment and infrastructure automation"
    },
    "Cloud Engineer": {
        "core_skills": ["AWS", "Azure", "Cloud Architecture", "Networking", "Security"],
        "secondary_skills": ["Docker", "Kubernetes", "Terraform", "Linux"],
        "bonus_skills": ["Python", "Monitoring", "Cost Optimization"],
        "min_projects": 2,
        "min_cgpa": 7.0,
        "description": "Designs and manages cloud infrastructure"
    },
    "QA Engineer": {
        "core_skills": ["Testing", "Selenium", "Test Cases", "Bug Tracking", "QA Process"],
        "secondary_skills": ["Java", "Python", "SQL", "API Testing"],
        "bonus_skills": ["Automation", "Performance Testing", "CI/CD"],
        "min_projects": 2,
        "min_cgpa": 6.0,
        "description": "Ensures software quality through testing"
    },
    "UI/UX Designer": {
        "core_skills": ["Figma", "Adobe XD", "UI Design", "UX Research", "Prototyping"],
        "secondary_skills": ["HTML", "CSS", "User Testing", "Wireframing"],
        "bonus_skills": ["JavaScript", "Animation", "Design Systems"],
        "min_projects": 3,
        "min_cgpa": 6.0,
        "description": "Designs user interfaces and experiences"
    }
}


def get_all_roles():
    """Get list of all available roles"""
    return list(ROLE_REQUIREMENTS.keys())


def get_role_requirements(role_name):
    """Get requirements for a specific role"""
    return ROLE_REQUIREMENTS.get(role_name, None)


def calculate_role_fit_score(user_skills, user_cgpa, user_projects_count, role_name):
    """
    Calculate job fit score for a specific role using rule-based logic
    
    Args:
        user_skills (list): List of user's skills
        user_cgpa (float): User's CGPA
        user_projects_count (int): Number of projects
        role_name (str): Target role name
    
    Returns:
        dict: {
            'role_fit_score': int (0-100),
            'core_match': int,
            'secondary_match': int,
            'bonus_match': int,
            'missing_core': list,
            'missing_secondary': list,
            'missing_bonus': list,
            'cgpa_met': bool,
            'projects_met': bool,
            'breakdown': dict
        }
    """
    role_req = ROLE_REQUIREMENTS.get(role_name)
    if not role_req:
        return None
    
    # Normalize user skills
    user_skills_lower = [skill.strip().lower() for skill in user_skills if skill.strip()]
    
    # Check core skills (50% weight)
    core_skills = [s.lower() for s in role_req['core_skills']]
    core_matched = []
    core_missing = []
    
    for core_skill in role_req['core_skills']:
        matched = False
        for user_skill in user_skills_lower:
            if core_skill.lower() in user_skill or user_skill in core_skill.lower():
                core_matched.append(core_skill)
                matched = True
                break
        if not matched:
            core_missing.append(core_skill)
    
    core_score = (len(core_matched) / len(core_skills)) * 50 if core_skills else 0
    
    # Check secondary skills (30% weight)
    secondary_skills = [s.lower() for s in role_req['secondary_skills']]
    secondary_matched = []
    secondary_missing = []
    
    for sec_skill in role_req['secondary_skills']:
        matched = False
        for user_skill in user_skills_lower:
            if sec_skill.lower() in user_skill or user_skill in sec_skill.lower():
                secondary_matched.append(sec_skill)
                matched = True
                break
        if not matched:
            secondary_missing.append(sec_skill)
    
    secondary_score = (len(secondary_matched) / len(secondary_skills)) * 30 if secondary_skills else 0
    
    # Check bonus skills (10% weight)
    bonus_skills = [s.lower() for s in role_req['bonus_skills']]
    bonus_matched = []
    bonus_missing = []
    
    for bonus_skill in role_req['bonus_skills']:
        matched = False
        for user_skill in user_skills_lower:
            if bonus_skill.lower() in user_skill or user_skill in bonus_skill.lower():
                bonus_matched.append(bonus_skill)
                matched = True
                break
        if not matched:
            bonus_missing.append(bonus_skill)
    
    bonus_score = (len(bonus_matched) / len(bonus_skills)) * 10 if bonus_skills else 0
    
    # Check CGPA requirement (5% weight)
    cgpa_met = user_cgpa >= role_req['min_cgpa']
    cgpa_score = 5 if cgpa_met else 0
    
    # Check projects requirement (5% weight)
    projects_met = user_projects_count >= role_req['min_projects']
    projects_score = 5 if projects_met else 0
    
    # Calculate total score
    total_score = int(core_score + secondary_score + bonus_score + cgpa_score + projects_score)
    
    return {
        'role_fit_score': total_score,
        'core_match': len(core_matched),
        'secondary_match': len(secondary_matched),
        'bonus_match': len(bonus_matched),
        'missing_core': core_missing,
        'missing_secondary': secondary_missing,
        'missing_bonus': bonus_missing,
        'cgpa_met': cgpa_met,
        'projects_met': projects_met,
        'breakdown': {
            'core_score': int(core_score),
            'secondary_score': int(secondary_score),
            'bonus_score': int(bonus_score),
            'cgpa_score': int(cgpa_score),
            'projects_score': int(projects_score)
        }
    }


def get_all_missing_skills(role_fit_result):
    """Get all missing skills from role fit result"""
    if not role_fit_result:
        return []
    
    all_missing = []
    all_missing.extend(role_fit_result['missing_core'])
    all_missing.extend(role_fit_result['missing_secondary'])
    all_missing.extend(role_fit_result['missing_bonus'])
    
    return all_missing


def categorize_missing_skills(role_fit_result):
    """
    Categorize missing skills into priority levels
    
    Returns:
        dict: {
            'critical': list (core skills),
            'important': list (secondary skills),
            'nice_to_have': list (bonus skills)
        }
    """
    if not role_fit_result:
        return {'critical': [], 'important': [], 'nice_to_have': []}
    
    return {
        'critical': role_fit_result['missing_core'],
        'important': role_fit_result['missing_secondary'],
        'nice_to_have': role_fit_result['missing_bonus']
    }
