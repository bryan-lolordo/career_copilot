"""
Semantic Kernel Setup for Career Copilot
"""
import semantic_kernel as sk
from services.job_api import search_jobs

# Minimal skill registration example
def register_skills(kernel):
    """
    Register job search as a Semantic Kernel skill.
    """
    kernel.add_function("job_search", search_jobs)
    return kernel
