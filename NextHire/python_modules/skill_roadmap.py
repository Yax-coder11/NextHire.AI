"""
Skill Gap Roadmap Generator
Creates learning roadmaps based on missing skills
"""

# Learning time estimates (in weeks) for different skills
SKILL_LEARNING_TIME = {
    # Programming Languages
    "Python": 8, "Java": 10, "C++": 12, "JavaScript": 6,
    "TypeScript": 4, "Kotlin": 8, "Swift": 8, "R": 6,
    
    # Web Technologies
    "HTML": 2, "CSS": 3, "React": 6, "Node.js": 6,
    "Angular": 8, "Vue.js": 6, "Redux": 4,
    
    # Databases
    "SQL": 4, "MongoDB": 4, "PostgreSQL": 4, "Redis": 3,
    "Database": 4, "Database Design": 5,
    
    # Data Science & ML
    "Machine Learning": 12, "Deep Learning": 16, "NLP": 10,
    "Statistics": 8, "Data Analysis": 6, "Data Visualization": 4,
    "TensorFlow": 8, "PyTorch": 8, "Pandas": 4, "NumPy": 3,
    
    # Cloud & DevOps
    "AWS": 8, "Azure": 8, "Docker": 4, "Kubernetes": 8,
    "CI/CD": 6, "Jenkins": 4, "Terraform": 6, "Ansible": 6,
    "Linux": 6, "Shell Scripting": 4,
    
    # Tools & Frameworks
    "Git": 2, "Testing": 4, "Selenium": 5, "REST API": 4,
    "Microservices": 8, "Agile": 2, "Debugging": 3,
    
    # Design
    "Figma": 3, "Adobe XD": 3, "UI Design": 6, "UX Research": 6,
    "Prototyping": 4, "Wireframing": 3,
    
    # Mobile
    "React Native": 8, "Flutter": 8, "Android Studio": 6,
    "Xcode": 6, "Mobile UI": 5,
    
    # Other
    "Data Structures": 8, "Algorithms": 10, "Networking": 6,
    "Security": 8, "Excel": 3, "Tableau": 4, "Power BI": 4,
    "UI/UX": 8, "Responsive Design": 3, "QA Process": 4,
    "Bug Tracking": 2, "Test Cases": 3, "API Testing": 4,
    "Monitoring": 4, "Cloud Architecture": 10, "Performance Testing": 5,
    "Automation": 6, "User Testing": 4, "Design Systems": 6,
    "Animation": 5, "App Store": 2, "Firebase": 4,
    "Cost Optimization": 4, "Accessibility": 4, "Webpack": 4
}


def get_learning_time(skill):
    """Get estimated learning time for a skill (in weeks)"""
    # Try exact match first
    if skill in SKILL_LEARNING_TIME:
        return SKILL_LEARNING_TIME[skill]
    
    # Try case-insensitive match
    for known_skill, time in SKILL_LEARNING_TIME.items():
        if skill.lower() == known_skill.lower():
            return time
    
    # Default time for unknown skills
    return 6


def generate_skill_roadmap(missing_skills_categorized):
    """
    Generate a learning roadmap based on missing skills
    
    Args:
        missing_skills_categorized (dict): {
            'critical': list,
            'important': list,
            'nice_to_have': list
        }
    
    Returns:
        dict: {
            'short_term': list (0-3 months),
            'mid_term': list (3-6 months),
            'long_term': list (6+ months),
            'total_weeks': int,
            'roadmap_phases': list
        }
    """
    short_term = []  # 0-12 weeks
    mid_term = []    # 13-24 weeks
    long_term = []   # 25+ weeks
    
    cumulative_weeks = 0
    roadmap_phases = []
    
    # Phase 1: Critical skills (must learn first)
    critical_skills = missing_skills_categorized.get('critical', [])
    for skill in critical_skills:
        weeks = get_learning_time(skill)
        cumulative_weeks += weeks
        
        skill_info = {
            'skill': skill,
            'weeks': weeks,
            'priority': 'Critical',
            'start_week': cumulative_weeks - weeks,
            'end_week': cumulative_weeks
        }
        
        if cumulative_weeks <= 12:
            short_term.append(skill_info)
        elif cumulative_weeks <= 24:
            mid_term.append(skill_info)
        else:
            long_term.append(skill_info)
        
        roadmap_phases.append(skill_info)
    
    # Phase 2: Important skills (learn after critical)
    important_skills = missing_skills_categorized.get('important', [])
    for skill in important_skills:
        weeks = get_learning_time(skill)
        cumulative_weeks += weeks
        
        skill_info = {
            'skill': skill,
            'weeks': weeks,
            'priority': 'Important',
            'start_week': cumulative_weeks - weeks,
            'end_week': cumulative_weeks
        }
        
        if cumulative_weeks <= 12:
            short_term.append(skill_info)
        elif cumulative_weeks <= 24:
            mid_term.append(skill_info)
        else:
            long_term.append(skill_info)
        
        roadmap_phases.append(skill_info)
    
    # Phase 3: Nice-to-have skills (learn last)
    nice_to_have_skills = missing_skills_categorized.get('nice_to_have', [])
    for skill in nice_to_have_skills:
        weeks = get_learning_time(skill)
        cumulative_weeks += weeks
        
        skill_info = {
            'skill': skill,
            'weeks': weeks,
            'priority': 'Nice-to-have',
            'start_week': cumulative_weeks - weeks,
            'end_week': cumulative_weeks
        }
        
        if cumulative_weeks <= 12:
            short_term.append(skill_info)
        elif cumulative_weeks <= 24:
            mid_term.append(skill_info)
        else:
            long_term.append(skill_info)
        
        roadmap_phases.append(skill_info)
    
    return {
        'short_term': short_term,
        'mid_term': mid_term,
        'long_term': long_term,
        'total_weeks': cumulative_weeks,
        'roadmap_phases': roadmap_phases
    }


def get_roadmap_summary(roadmap):
    """
    Get a summary of the roadmap
    
    Returns:
        dict: {
            'short_term_count': int,
            'mid_term_count': int,
            'long_term_count': int,
            'total_skills': int,
            'estimated_months': int
        }
    """
    return {
        'short_term_count': len(roadmap['short_term']),
        'mid_term_count': len(roadmap['mid_term']),
        'long_term_count': len(roadmap['long_term']),
        'total_skills': len(roadmap['roadmap_phases']),
        'estimated_months': int(roadmap['total_weeks'] / 4)
    }


def get_next_skill_to_learn(roadmap):
    """Get the next skill user should focus on"""
    if roadmap['roadmap_phases']:
        return roadmap['roadmap_phases'][0]
    return None
