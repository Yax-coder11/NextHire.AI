"""
Resume Strength Breakdown
Provides detailed section-wise scoring
"""

def calculate_resume_breakdown(cgpa, skills, projects, education_count=1, extras=None):
    """
    Break down resume score into sections
    
    Args:
        cgpa (float): User's CGPA
        skills (str or list): User's skills
        projects (str): User's projects
        education_count (int): Number of education entries
        extras (dict): Extra information (github, certifications, etc.)
    
    Returns:
        dict: {
            'total_score': int,
            'sections': dict,
            'strengths': list,
            'weaknesses': list,
            'recommendations': list
        }
    """
    
    sections = {}
    
    # Section 1: Education (25 points)
    cgpa_float = float(cgpa) if cgpa else 0
    
    if cgpa_float >= 9.0:
        education_score = 25
    elif cgpa_float >= 8.0:
        education_score = 22
    elif cgpa_float >= 7.0:
        education_score = 18
    elif cgpa_float >= 6.0:
        education_score = 14
    else:
        education_score = 10
    
    # Bonus for multiple education entries
    if education_count > 1:
        education_score = min(education_score + 2, 25)
    
    sections['education'] = {
        'score': education_score,
        'max_score': 25,
        'percentage': int((education_score / 25) * 100),
        'details': f"CGPA: {cgpa_float}/10"
    }
    
    # Section 2: Skills (35 points)
    if isinstance(skills, str):
        skills_list = [s.strip() for s in skills.split(',') if s.strip()]
    else:
        skills_list = skills
    
    skill_count = len(skills_list)
    
    if skill_count >= 10:
        skills_score = 35
    elif skill_count >= 7:
        skills_score = 30
    elif skill_count >= 5:
        skills_score = 25
    elif skill_count >= 3:
        skills_score = 18
    else:
        skills_score = 10
    
    sections['skills'] = {
        'score': skills_score,
        'max_score': 35,
        'percentage': int((skills_score / 35) * 100),
        'details': f"{skill_count} skills listed"
    }
    
    # Section 3: Projects (30 points)
    if projects and projects.strip():
        # Count project lines
        project_lines = [line.strip() for line in projects.split('\n') if line.strip()]
        project_count = len(project_lines)
        
        # Check for invalid entries
        projects_lower = projects.lower()
        if projects_lower in ["none", "null", "n/a", "na"]:
            project_count = 0
        
        if project_count >= 5:
            projects_score = 30
        elif project_count >= 4:
            projects_score = 26
        elif project_count >= 3:
            projects_score = 22
        elif project_count >= 2:
            projects_score = 16
        elif project_count >= 1:
            projects_score = 10
        else:
            projects_score = 0
    else:
        project_count = 0
        projects_score = 0
    
    sections['projects'] = {
        'score': projects_score,
        'max_score': 30,
        'percentage': int((projects_score / 30) * 100) if projects_score > 0 else 0,
        'details': f"{project_count} projects"
    }
    
    # Section 4: Extras (10 points)
    extras_score = 0
    extras_details = []
    
    if extras:
        if extras.get('github_username'):
            extras_score += 3
            extras_details.append("GitHub profile")
        
        if extras.get('about_yourself'):
            extras_score += 2
            extras_details.append("Professional summary")
        
        if extras.get('city'):
            extras_score += 1
            extras_details.append("Location")
        
        # Check for certifications in projects or about
        text_to_check = f"{projects} {extras.get('about_yourself', '')}".lower()
        if 'certif' in text_to_check or 'course' in text_to_check:
            extras_score += 2
            extras_details.append("Certifications/Courses")
        
        # Check for achievements
        if 'award' in text_to_check or 'achievement' in text_to_check:
            extras_score += 2
            extras_details.append("Awards/Achievements")
    
    extras_score = min(extras_score, 10)
    
    sections['extras'] = {
        'score': extras_score,
        'max_score': 10,
        'percentage': int((extras_score / 10) * 100),
        'details': ', '.join(extras_details) if extras_details else "None"
    }
    
    # Calculate total score
    total_score = education_score + skills_score + projects_score + extras_score
    
    # Identify strengths and weaknesses
    strengths = []
    weaknesses = []
    recommendations = []
    
    # Education analysis
    if sections['education']['percentage'] >= 80:
        strengths.append("Strong academic background")
    elif sections['education']['percentage'] < 60:
        weaknesses.append("CGPA could be improved")
        recommendations.append("Focus on maintaining good grades")
    
    # Skills analysis
    if sections['skills']['percentage'] >= 80:
        strengths.append("Diverse skill set")
    elif sections['skills']['percentage'] < 60:
        weaknesses.append("Limited skills listed")
        recommendations.append("Learn and add more relevant skills")
    
    # Projects analysis
    if sections['projects']['percentage'] >= 80:
        strengths.append("Strong project portfolio")
    elif sections['projects']['percentage'] < 60:
        weaknesses.append("Insufficient projects")
        recommendations.append("Build more projects to demonstrate skills")
    
    # Extras analysis
    if sections['extras']['percentage'] >= 60:
        strengths.append("Good additional information")
    else:
        recommendations.append("Add GitHub profile and professional summary")
    
    # Overall recommendations
    if total_score < 60:
        recommendations.append("Overall resume needs significant improvement")
    elif total_score < 80:
        recommendations.append("Good foundation - focus on weak areas")
    else:
        recommendations.append("Strong resume - maintain and update regularly")
    
    return {
        'total_score': total_score,
        'sections': sections,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'recommendations': recommendations
    }


def get_section_color(percentage):
    """Get color code based on section percentage"""
    if percentage >= 80:
        return '#28a745'  # Green
    elif percentage >= 60:
        return '#ffc107'  # Yellow
    else:
        return '#dc3545'  # Red


def get_improvement_priority(sections):
    """
    Determine which section needs most improvement
    
    Returns:
        str: Section name with lowest score
    """
    section_scores = {
        name: data['percentage'] 
        for name, data in sections.items()
    }
    
    # Find section with lowest percentage
    min_section = min(section_scores, key=section_scores.get)
    
    return min_section


def compare_with_average(breakdown):
    """
    Compare user's scores with average scores
    
    Returns:
        dict: Comparison with average
    """
    # Average scores (based on typical student profiles)
    averages = {
        'education': 18,  # ~72%
        'skills': 25,     # ~71%
        'projects': 20,   # ~67%
        'extras': 5       # ~50%
    }
    
    comparisons = {}
    
    for section, avg_score in averages.items():
        user_score = breakdown['sections'][section]['score']
        difference = user_score - avg_score
        
        if difference > 0:
            status = "Above Average"
        elif difference == 0:
            status = "Average"
        else:
            status = "Below Average"
        
        comparisons[section] = {
            'user_score': user_score,
            'average_score': avg_score,
            'difference': difference,
            'status': status
        }
    
    return comparisons
