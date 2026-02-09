// Enhanced Features JavaScript
let currentRole = '';
let allRoles = [];

// Load roles on page load
document.addEventListener('DOMContentLoaded', function() {
    loadRoles();
});

// Load available roles
async function loadRoles() {
    try {
        const response = await fetch('/api/roles/list');
        const data = await response.json();
        
        if (data.success) {
            allRoles = data.roles;
            const select = document.getElementById('roleSelect');
            
            data.roles.forEach(role => {
                const option = document.createElement('option');
                option.value = role.name;
                option.textContent = `${role.name} - ${role.description}`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading roles:', error);
        alert('Error loading roles. Please refresh the page.');
    }
}

// FEATURE 1: Evaluate Role Fit
async function evaluateRole() {
    const roleName = document.getElementById('roleSelect').value;
    
    if (!roleName) {
        alert('Please select a role first');
        return;
    }
    
    currentRole = roleName;
    
    try {
        const response = await fetch('/api/roles/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role_name: roleName })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayRoleEvaluation(data);
            updateQuickStats(data);
        } else {
            alert('Error: ' + (data.error || 'Evaluation failed'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error evaluating role. Please try again.');
    }
}

function displayRoleEvaluation(data) {
    const resultsDiv = document.getElementById('roleEvalResults');
    
    let html = `
        <div class="row">
            <div class="col-md-6">
                <h5>Role Fit Score</h5>
                <div class="display-4 text-primary">${data.role_fit_score}/100</div>
                <div class="progress mt-2" style="height: 30px;">
                    <div class="progress-bar ${getScoreColor(data.role_fit_score)}" 
                         style="width: ${data.role_fit_score}%">
                        ${data.role_fit_score}%
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <h5>Score Breakdown</h5>
                <ul class="list-group">
                    <li class="list-group-item d-flex justify-content-between">
                        Core Skills <span class="badge bg-primary">${data.breakdown.core_score}/50</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        Secondary Skills <span class="badge bg-info">${data.breakdown.secondary_score}/30</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        Bonus Skills <span class="badge bg-success">${data.breakdown.bonus_score}/10</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        CGPA <span class="badge bg-warning">${data.breakdown.cgpa_score}/5</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        Projects <span class="badge bg-danger">${data.breakdown.projects_score}/5</span>
                    </li>
                </ul>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-md-12">
                <h5>Missing Skills</h5>
                ${displayMissingSkills(data.missing_skills)}
            </div>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
    
    // Display confidence
    displayConfidence(data.confidence);
}

function displayMissingSkills(missing) {
    let html = '';
    
    if (missing.critical && missing.critical.length > 0) {
        html += `<div class="mb-3">
            <h6 class="text-danger"><i class="bi bi-exclamation-triangle"></i> Critical Skills</h6>
            <div>`;
        missing.critical.forEach(skill => {
            html += `<span class="skill-chip bg-danger text-white">${skill}</span>`;
        });
        html += `</div></div>`;
    }
    
    if (missing.important && missing.important.length > 0) {
        html += `<div class="mb-3">
            <h6 class="text-warning"><i class="bi bi-exclamation-circle"></i> Important Skills</h6>
            <div>`;
        missing.important.forEach(skill => {
            html += `<span class="skill-chip bg-warning text-dark">${skill}</span>`;
        });
        html += `</div></div>`;
    }
    
    if (missing.nice_to_have && missing.nice_to_have.length > 0) {
        html += `<div class="mb-3">
            <h6 class="text-info"><i class="bi bi-info-circle"></i> Nice-to-Have Skills</h6>
            <div>`;
        missing.nice_to_have.forEach(skill => {
            html += `<span class="skill-chip bg-info text-white">${skill}</span>`;
        });
        html += `</div></div>`;
    }
    
    if (!html) {
        html = '<p class="text-success"><i class="bi bi-check-circle"></i> No missing skills! You meet all requirements.</p>';
    }
    
    return html;
}

function displayConfidence(confidence) {
    const section = document.getElementById('confidenceSection');
    const badge = document.getElementById('confidenceBadge');
    const text = document.getElementById('confidenceText');
    
    const colors = {
        'High': 'bg-success',
        'Medium': 'bg-warning',
        'Low': 'bg-danger'
    };
    
    badge.className = `confidence-badge ${colors[confidence.confidence_level]} text-white`;
    badge.textContent = confidence.confidence_level;
    
    text.innerHTML = `
        <strong>Score: ${confidence.confidence_score}/100</strong><br>
        ${confidence.recommendations.join('<br>')}
    `;
    
    section.style.display = 'block';
}

function updateQuickStats(data) {
    document.getElementById('quickStats').style.display = 'flex';
    document.getElementById('resumeScoreDisplay').textContent = data.confidence.factors.resume_factor || '--';
    document.getElementById('roleFitScoreDisplay').textContent = data.role_fit_score;
    
    const totalMissing = (data.missing_skills.critical?.length || 0) + 
                        (data.missing_skills.important?.length || 0) + 
                        (data.missing_skills.nice_to_have?.length || 0);
    document.getElementById('missingSkillsDisplay').textContent = totalMissing;
    document.getElementById('confidenceLevelDisplay').textContent = data.confidence.confidence_level;
}

function getScoreColor(score) {
    if (score >= 70) return 'bg-success';
    if (score >= 40) return 'bg-warning';
    return 'bg-danger';
}


// FEATURE 2: Generate Learning Roadmap
async function generateRoadmap() {
    if (!currentRole) {
        alert('Please evaluate a role first');
        return;
    }
    
    try {
        const response = await fetch('/api/roadmap/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role_name: currentRole })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayRoadmap(data);
        } else {
            alert('Error generating roadmap');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error generating roadmap. Please try again.');
    }
}

function displayRoadmap(data) {
    const resultsDiv = document.getElementById('roadmapResults');
    const roadmap = data.roadmap;
    const summary = data.summary;
    
    let html = `
        <div class="alert alert-info">
            <h5><i class="bi bi-clock"></i> Learning Timeline</h5>
            <p class="mb-0">
                Total Skills: ${summary.total_skills} | 
                Estimated Time: ${summary.estimated_months} months (${roadmap.total_weeks} weeks)
            </p>
        </div>
        
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h6><i class="bi bi-calendar-check"></i> Short-term (0-3 months)</h6>
                    </div>
                    <div class="card-body">
                        ${displayRoadmapSkills(roadmap.short_term)}
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-warning text-dark">
                        <h6><i class="bi bi-calendar"></i> Mid-term (3-6 months)</h6>
                    </div>
                    <div class="card-body">
                        ${displayRoadmapSkills(roadmap.mid_term)}
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-danger text-white">
                        <h6><i class="bi bi-calendar-event"></i> Long-term (6+ months)</h6>
                    </div>
                    <div class="card-body">
                        ${displayRoadmapSkills(roadmap.long_term)}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    if (data.next_skill) {
        html += `
            <div class="alert alert-primary mt-3">
                <h6><i class="bi bi-arrow-right-circle"></i> Next Skill to Learn</h6>
                <p class="mb-0">
                    <strong>${data.next_skill.skill}</strong> - 
                    ${data.next_skill.weeks} weeks (${data.next_skill.priority} priority)
                </p>
            </div>
        `;
    }
    
    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
}

function displayRoadmapSkills(skills) {
    if (!skills || skills.length === 0) {
        return '<p class="text-muted">No skills in this timeframe</p>';
    }
    
    let html = '<div class="roadmap-timeline">';
    skills.forEach(skill => {
        html += `
            <div class="roadmap-item">
                <strong>${skill.skill}</strong><br>
                <small class="text-muted">${skill.weeks} weeks | ${skill.priority}</small>
            </div>
        `;
    });
    html += '</div>';
    
    return html;
}

// FEATURE 4: Skill Simulator
async function simulateSkills(skills) {
    if (!currentRole) {
        alert('Please evaluate a role first');
        return;
    }
    
    try {
        const response = await fetch('/api/simulator/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                role_name: currentRole,
                simulated_skills: skills
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displaySimulation(data);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

function displaySimulation(data) {
    const sim = data.simulation;
    const improvement = sim.improvements.score_improvement;
    
    let html = `
        <div class="simulator-result">
            <h5 class="text-white">Simulation Results</h5>
            <div class="row text-center">
                <div class="col-md-4">
                    <h3>${sim.current_state.role_fit_score}</h3>
                    <p>Current Score</p>
                </div>
                <div class="col-md-4">
                    <h3><i class="bi bi-arrow-right"></i></h3>
                    <p>+${improvement}</p>
                </div>
                <div class="col-md-4">
                    <h3>${sim.simulated_state.role_fit_score}</h3>
                    <p>New Score</p>
                </div>
            </div>
            <p class="mt-3">${data.recommendation}</p>
        </div>
    `;
    
    return html;
}

// FEATURE 5: Compare Roles
async function compareRoles() {
    try {
        const roleNames = allRoles.map(r => r.name);
        
        const response = await fetch('/api/roles/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role_names: roleNames })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayComparison(data);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error comparing roles. Please try again.');
    }
}

function displayComparison(data) {
    const resultsDiv = document.getElementById('comparisonResults');
    const comparison = data.comparison;
    
    let html = `
        <div class="alert alert-success">
            <h5><i class="bi bi-trophy"></i> Best Fit: ${comparison.best_fit_role}</h5>
            <p class="mb-0">Score: ${comparison.best_fit_score}/100</p>
        </div>
        
        <p class="lead">${data.recommendation}</p>
        
        <div class="row">
    `;
    
    comparison.comparisons.forEach(role => {
        html += `
            <div class="col-md-6 mb-3">
                <div class="card role-comparison-card">
                    <div class="card-body">
                        <h6>${role.role_name}</h6>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Score:</span>
                            <strong class="text-primary">${role.role_fit_score}/100</strong>
                        </div>
                        <div class="progress mb-2" style="height: 20px;">
                            <div class="progress-bar ${getScoreColor(role.role_fit_score)}" 
                                 style="width: ${role.role_fit_score}%">
                            </div>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Status:</span>
                            <span class="badge ${getReadinessBadge(role.readiness)}">${role.readiness}</span>
                        </div>
                        <div class="d-flex justify-content-between mt-1">
                            <span>Missing Skills:</span>
                            <span class="badge bg-secondary">${role.missing_skills_count}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
}

function getReadinessBadge(status) {
    if (status === 'Ready') return 'bg-success';
    if (status === 'Partially Ready') return 'bg-warning text-dark';
    return 'bg-danger';
}

// FEATURE 6: Resume Breakdown
async function getResumeBreakdown() {
    try {
        const response = await fetch('/api/resume/breakdown');
        const data = await response.json();
        
        if (data.success) {
            displayBreakdown(data);
        } else {
            alert('Error: ' + (data.error || 'Please create a resume first'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error getting resume breakdown. Please try again.');
    }
}

function displayBreakdown(data) {
    const resultsDiv = document.getElementById('breakdownResults');
    const breakdown = data.breakdown;
    
    let html = `
        <div class="row">
            <div class="col-md-6">
                <h5>Total Resume Score</h5>
                <div class="display-4 text-primary">${breakdown.total_score}/100</div>
            </div>
            <div class="col-md-6">
                <h5>Section Scores</h5>
                ${displaySectionScores(breakdown.sections)}
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h6><i class="bi bi-check-circle"></i> Strengths</h6>
                    </div>
                    <div class="card-body">
                        <ul class="list-unstyled">
                            ${breakdown.strengths.map(s => `<li><i class="bi bi-check"></i> ${s}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-warning text-dark">
                        <h6><i class="bi bi-exclamation-triangle"></i> Recommendations</h6>
                    </div>
                    <div class="card-body">
                        <ul class="list-unstyled">
                            ${breakdown.recommendations.map(r => `<li><i class="bi bi-arrow-right"></i> ${r}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
}

function displaySectionScores(sections) {
    let html = '';
    
    for (const [name, data] of Object.entries(sections)) {
        const percentage = data.percentage;
        const color = percentage >= 80 ? 'success' : percentage >= 60 ? 'warning' : 'danger';
        
        html += `
            <div class="mb-3">
                <div class="d-flex justify-content-between mb-1">
                    <span class="text-capitalize">${name}</span>
                    <strong>${data.score}/${data.max_score}</strong>
                </div>
                <div class="section-score">
                    <div class="section-score-fill bg-${color}" style="width: ${percentage}%"></div>
                </div>
                <small class="text-muted">${data.details}</small>
            </div>
        `;
    }
    
    return html;
}
