"""
Confidence Index Calculator
Calculates confidence level based on multiple factors
"""

def calculate_confidence_index(resume_score, role_fit_score, missing_skills_count, role_requirements):
    """
    Calculate confidence index using rule-based logic
    
    Args:
        resume_score (int): Resume evaluation score (0-100)
        role_fit_score (int): Role fit score (0-100)
        missing_skills_count (int): Number of missing skills
        role_requirements (dict): Role requirements from role_evaluator
    
    Returns:
        dict: {
            'confidence_level': str ('Low', 'Medium', 'High'),
            'confidence_score': int (0-100),
            'factors': dict,
            'recommendations': list
        }
    """
    
    # Factor 1: Resume Score (30% weight)
    if resume_score >= 80:
        resume_factor = 30
    elif resume_score >= 60:
        resume_factor = 20
    else:
        resume_factor = 10
    
    # Factor 2: Role Fit Score (40% weight)
    if role_fit_score >= 80:
        role_fit_factor = 40
    elif role_fit_score >= 60:
        role_fit_factor = 30
    elif role_fit_score >= 40:
        role_fit_factor = 20
    else:
        role_fit_factor = 10
    
    # Factor 3: Missing Skills Impact (30% weight)
    if role_requirements:
        total_required_skills = (
            len(role_requirements.get('core_skills', [])) +
            len(role_requirements.get('secondary_skills', []))
        )
        
        if total_required_skills > 0:
            missing_ratio = missing_skills_count / total_required_skills
            
            if missing_ratio <= 0.2:  # 20% or less missing
                missing_factor = 30
            elif missing_ratio <= 0.4:  # 40% or less missing
                missing_factor = 20
            elif missing_ratio <= 0.6:  # 60% or less missing
                missing_factor = 10
            else:
                missing_factor = 5
        else:
            missing_factor = 30
    else:
        missing_factor = 15
    
    # Calculate total confidence score
    confidence_score = resume_factor + role_fit_factor + missing_factor
    
    # Determine confidence level
    if confidence_score >= 75:
        confidence_level = "High"
    elif confidence_score >= 50:
        confidence_level = "Medium"
    else:
        confidence_level = "Low"
    
    # Generate recommendations
    recommendations = []
    
    if resume_score < 70:
        recommendations.append("Improve resume quality by adding more projects and skills")
    
    if role_fit_score < 60:
        recommendations.append("Focus on acquiring role-specific skills")
    
    if missing_skills_count > 5:
        recommendations.append("Prioritize learning critical skills first")
    
    if confidence_level == "Low":
        recommendations.append("Consider gaining more experience before applying")
    elif confidence_level == "Medium":
        recommendations.append("You're on the right track - keep building skills")
    else:
        recommendations.append("You're well-prepared for this role!")
    
    return {
        'confidence_level': confidence_level,
        'confidence_score': confidence_score,
        'factors': {
            'resume_factor': resume_factor,
            'role_fit_factor': role_fit_factor,
            'missing_skills_factor': missing_factor
        },
        'recommendations': recommendations
    }


def get_confidence_color(confidence_level):
    """Get color code for confidence level"""
    colors = {
        'High': '#28a745',    # Green
        'Medium': '#ffc107',  # Yellow
        'Low': '#dc3545'      # Red
    }
    return colors.get(confidence_level, '#6c757d')


def get_confidence_emoji(confidence_level):
    """Get emoji for confidence level"""
    emojis = {
        'High': '😊',
        'Medium': '😐',
        'Low': '😟'
    }
    return emojis.get(confidence_level, '😐')
