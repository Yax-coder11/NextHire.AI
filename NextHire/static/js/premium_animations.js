/**
 * NextHire.AI - Premium Animations & Interactions
 * Smooth, engaging, professional animations
 */

// ========== FADE IN ON SCROLL ==========
function initScrollAnimations() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-on-load');
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  // Observe all panels and cards
  document.querySelectorAll('.panel, .card, .section-heading-container').forEach(el => {
    observer.observe(el);
  });
}

// ========== SCORE COUNTER ANIMATION ==========
function animateScore(element, targetScore, duration = 1500) {
  const start = 0;
  const startTime = performance.now();
  
  function updateScore(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // Easing function for smooth animation
    const easeOutQuart = 1 - Math.pow(1 - progress, 4);
    const currentScore = Math.floor(start + (targetScore - start) * easeOutQuart);
    
    element.textContent = currentScore;
    
    // Apply color based on score
    element.classList.remove('score-high', 'score-medium', 'score-low');
    if (currentScore >= 80) {
      element.classList.add('score-high');
    } else if (currentScore >= 60) {
      element.classList.add('score-medium');
    } else {
      element.classList.add('score-low');
    }
    
    if (progress < 1) {
      requestAnimationFrame(updateScore);
    }
  }
  
  requestAnimationFrame(updateScore);
}

// ========== CIRCULAR PROGRESS ANIMATION ==========
function animateCircularProgress(progressElement, percentage, duration = 1500) {
  const circle = progressElement.querySelector('.progress-bar');
  if (!circle) return;
  
  const circumference = 440; // 2 * PI * radius (70)
  const offset = circumference - (percentage / 100) * circumference;
  
  // Animate from full offset to target offset
  circle.style.strokeDashoffset = circumference;
  
  setTimeout(() => {
    circle.style.transition = `stroke-dashoffset ${duration}ms ease-out`;
    circle.style.strokeDashoffset = offset;
  }, 100);
}

// ========== BUTTON RIPPLE EFFECT ==========
function addRippleEffect(button, event) {
  const ripple = document.createElement('span');
  const rect = button.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const x = event.clientX - rect.left - size / 2;
  const y = event.clientY - rect.top - size / 2;
  
  ripple.style.width = ripple.style.height = size + 'px';
  ripple.style.left = x + 'px';
  ripple.style.top = y + 'px';
  ripple.classList.add('ripple');
  
  button.appendChild(ripple);
  
  setTimeout(() => ripple.remove(), 600);
}

// ========== SMOOTH SCROLL TO SECTION ==========
function smoothScrollTo(targetId) {
  const target = document.querySelector(targetId);
  if (target) {
    const headerOffset = 80;
    const elementPosition = target.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
    
    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  }
}

// ========== INITIALIZE ON PAGE LOAD ==========
document.addEventListener('DOMContentLoaded', () => {
  // Initialize scroll animations
  initScrollAnimations();
  
  // Animate scores if present
  const scoreElements = document.querySelectorAll('.score-number');
  scoreElements.forEach(el => {
    const targetScore = parseInt(el.textContent) || 0;
    if (targetScore > 0) {
      animateScore(el, targetScore);
    }
  });
  
  // Animate circular progress if present
  const circularProgress = document.querySelectorAll('.circular-progress');
  circularProgress.forEach(el => {
    const percentage = parseInt(el.dataset.percentage) || 0;
    if (percentage > 0) {
      animateCircularProgress(el, percentage);
    }
  });
  
  // Add ripple effect to buttons
  document.querySelectorAll('.btn-primary, .comic-button, .btn-secondary').forEach(button => {
    button.addEventListener('click', (e) => {
      if (!button.classList.contains('loading')) {
        addRippleEffect(button, e);
      }
    });
  });
  
  // Smooth scroll for navigation links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href !== '#' && document.querySelector(href)) {
        e.preventDefault();
        smoothScrollTo(href);
      }
    });
  });
});

// ========== EXPORT FUNCTIONS ==========
window.NextHireAnimations = {
  animateScore,
  animateCircularProgress,
  smoothScrollTo
};
