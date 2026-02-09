"""
What-If Skill Simulator
Simulates skill acquisition and recalculates scores
"""

def simulate_skill_acquisition(current_skills, simulated_skills, role_name, cgpa, projects_count, role_evaluator):
    """
    Simulate adding new skills and recalculate scores
    
    Args:
        current_skills (list): User's current skills
        simulated_skills (list): Skills to simulate adding
        role_name (str): Target role
        cgpa (float): User's CGPA
        projects_count (int): Number of projects
        role_evaluator: Role evaluator module
    
    Returns:
        dict: {
            'current_state': dict,
            'simulated_state': dict,
            'improvements': dict,
            'new_missing_skills': list
        }
    """
    
    # Calculate current state
    current_result = role_evaluator.calculate_role_fit_score(
        current_skills, cgpa, projects_count, role_name
    )
    
    # Combine current and simulated skills
    combined_skills = list(set(current_skills + simulated_skills))
    
    # Calculate simulated state
    simulated_result = role_evaluator.calculate_role_fit_score(
        combined_skills, cgpa, projects_count, role_name
    )
    
    # Calculate improvements
    score_improvement = simulated_result['role_fit_score'] - current_result['role_fit_score']
    core_improvement = simulated_result['core_match'] - current_result['core_match']
    secondary_improvement = simulated_result['secondary_match'] - current_result['secondary_match']
    bonus_improvement = simulated_result['bonus_match'] - current_result['bonus_match']
    
    # Determine new eligibility
    current_eligibility = get_eligibility_status(current_result['role_fit_score'])
    simulated_eligibility = get_eligibility_status(simulated_result['role_fit_score'])
    
    return {
        'current_state': {
            'role_fit_score': current_result['role_fit_score'],
            'eligibility': current_eligibility,
            'core_match': current_result['core_match'],
            'secondary_match': current_result['secondary_match'],
            'bonus_match': current_result['bonus_match']
        },
        'simulated_state': {
            'role_fit_score': simulated_result['role_fit_score'],
            'eligibility': simulated_eligibility,
            'core_match': simulated_result['core_match'],
            'secondary_match': simulated_result['secondary_match'],
            'bonus_match': simulated_result['bonus_match']
        },
        'improvements': {
            'score_improvement': score_improvement,
            'core_improvement': core_improvement,
            'secondary_improvement': secondary_improvement,
            'bonus_improvement': bonus_improvement,
            'eligibility_changed': current_eligibility != simulated_eligibility
        },
        'new_missing_skills': role_evaluator.get_all_missing_skills(simulated_result),
        'skills_acquired': simulated_skills
    }


def get_eligibility_status(role_fit_score):
    """Get eligibility status based on role fit score"""
    if role_fit_score >= 70:
        return "Eligible"
    elif role_fit_score >= 40:
        return "Partially Eligible"
    else:
        return "Not Eligible"


def get_simulation_recommendation(simulation_result):
    """
    Get recommendation based on simulation result
    
    Returns:
        str: Recommendation message
    """
    improvement = simulation_result['improvements']['score_improvement']
    
    if improvement >= 30:
        return "Excellent! These skills would significantly boost your profile."
    elif improvement >= 15:
        return "Good choice! These skills would notably improve your fit."
    elif improvement >= 5:
        return "These skills would provide a modest improvement."
    else:
        return "These skills have minimal impact. Consider focusing on core skills."


def rank_skills_by_impact(missing_skills, current_skills, role_name, cgpa, projects_count, role_evaluator):
    """
    Rank missing skills by their impact on role fit score
    
    Returns:
        list: Sorted list of (skill, impact_score) tuples
    """
    skill_impacts = []
    
    for skill in missing_skills:
        # Simulate adding this single skill
        simulation = simulate_skill_acquisition(
            current_skills, [skill], role_name, cgpa, projects_count, role_evaluator
        )
        
        impact = simulation['improvements']['score_improvement']
        skill_impacts.append((skill, impact))
    
    # Sort by impact (descending)
    skill_impacts.sort(key=lambda x: x[1], reverse=True)
    
    return skill_impacts
