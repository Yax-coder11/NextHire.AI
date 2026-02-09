"""
Role Switch Impact Analysis
Compares resume across multiple roles
"""

def compare_roles(user_skills, cgpa, projects_count, role_names, role_evaluator):
    """
    Evaluate resume across multiple roles
    
    Args:
        user_skills (list): User's skills
        cgpa (float): User's CGPA
        projects_count (int): Number of projects
        role_names (list): List of role names to compare
        role_evaluator: Role evaluator module
    
    Returns:
        dict: {
            'comparisons': list of role comparison dicts,
            'best_fit_role': str,
            'best_fit_score': int,
            'worst_fit_role': str,
            'worst_fit_score': int
        }
    """
    comparisons = []
    
    for role_name in role_names:
        result = role_evaluator.calculate_role_fit_score(
            user_skills, cgpa, projects_count, role_name
        )
        
        if result:
            role_req = role_evaluator.get_role_requirements(role_name)
            missing_skills = role_evaluator.get_all_missing_skills(result)
            
            # Determine readiness status
            if result['role_fit_score'] >= 70:
                readiness = "Ready"
            elif result['role_fit_score'] >= 50:
                readiness = "Partially Ready"
            else:
                readiness = "Not Ready"
            
            # Determine eligibility
            if result['role_fit_score'] >= 70:
                eligibility = "Eligible"
            elif result['role_fit_score'] >= 40:
                eligibility = "Partially Eligible"
            else:
                eligibility = "Not Eligible"
            
            comparisons.append({
                'role_name': role_name,
                'role_fit_score': result['role_fit_score'],
                'readiness': readiness,
                'eligibility': eligibility,
                'missing_skills_count': len(missing_skills),
                'missing_skills': missing_skills,
                'core_match': result['core_match'],
                'secondary_match': result['secondary_match'],
                'bonus_match': result['bonus_match'],
                'cgpa_met': result['cgpa_met'],
                'projects_met': result['projects_met'],
                'description': role_req['description']
            })
    
    # Sort by role fit score (descending)
    comparisons.sort(key=lambda x: x['role_fit_score'], reverse=True)
    
    # Find best and worst fits
    best_fit = comparisons[0] if comparisons else None
    worst_fit = comparisons[-1] if comparisons else None
    
    return {
        'comparisons': comparisons,
        'best_fit_role': best_fit['role_name'] if best_fit else None,
        'best_fit_score': best_fit['role_fit_score'] if best_fit else 0,
        'worst_fit_role': worst_fit['role_name'] if worst_fit else None,
        'worst_fit_score': worst_fit['role_fit_score'] if worst_fit else 0,
        'total_roles_compared': len(comparisons)
    }


def get_role_switch_recommendation(comparison_result):
    """
    Get recommendation based on role comparison
    
    Returns:
        str: Recommendation message
    """
    best_score = comparison_result['best_fit_score']
    worst_score = comparison_result['worst_fit_score']
    score_gap = best_score - worst_score
    
    if score_gap >= 40:
        return f"Strong recommendation: Focus on {comparison_result['best_fit_role']} - it's your best match!"
    elif score_gap >= 20:
        return f"Consider {comparison_result['best_fit_role']} as your primary target."
    else:
        return "You have similar fit across multiple roles - choose based on interest."


def identify_common_missing_skills(comparison_result):
    """
    Identify skills missing across multiple roles
    
    Returns:
        dict: {
            'common_skills': list (skills missing in all roles),
            'frequent_skills': list (skills missing in most roles)
        }
    """
    comparisons = comparison_result['comparisons']
    
    if not comparisons:
        return {'common_skills': [], 'frequent_skills': []}
    
    # Count skill occurrences
    skill_count = {}
    total_roles = len(comparisons)
    
    for comp in comparisons:
        for skill in comp['missing_skills']:
            skill_count[skill] = skill_count.get(skill, 0) + 1
    
    # Skills missing in all roles
    common_skills = [skill for skill, count in skill_count.items() if count == total_roles]
    
    # Skills missing in at least 50% of roles
    frequent_skills = [skill for skill, count in skill_count.items() 
                      if count >= total_roles / 2 and skill not in common_skills]
    
    return {
        'common_skills': common_skills,
        'frequent_skills': frequent_skills
    }


def get_role_transition_path(current_role, target_role, comparison_result):
    """
    Suggest transition path from current role to target role
    
    Returns:
        dict: {
            'feasibility': str ('Easy', 'Moderate', 'Difficult'),
            'skills_to_acquire': list,
            'estimated_time': str
        }
    """
    current_comp = None
    target_comp = None
    
    for comp in comparison_result['comparisons']:
        if comp['role_name'] == current_role:
            current_comp = comp
        if comp['role_name'] == target_role:
            target_comp = comp
    
    if not current_comp or not target_comp:
        return None
    
    # Calculate score difference
    score_diff = abs(target_comp['role_fit_score'] - current_comp['role_fit_score'])
    
    # Determine feasibility
    if score_diff <= 20:
        feasibility = "Easy"
        estimated_time = "3-6 months"
    elif score_diff <= 40:
        feasibility = "Moderate"
        estimated_time = "6-12 months"
    else:
        feasibility = "Difficult"
        estimated_time = "12+ months"
    
    # Skills to acquire
    skills_to_acquire = target_comp['missing_skills']
    
    return {
        'feasibility': feasibility,
        'skills_to_acquire': skills_to_acquire,
        'estimated_time': estimated_time,
        'current_score': current_comp['role_fit_score'],
        'target_score': target_comp['role_fit_score'],
        'score_gap': score_diff
    }
