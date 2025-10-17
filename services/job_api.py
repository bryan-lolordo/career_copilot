"""
Job API Service for Career Copilot
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Dummy job search function
def search_jobs(query, location=None):
    """
    Simulate a job search API call. Returns dummy job data as JSON.
    """
    # In production, replace with real API call (Indeed, Google Jobs, etc.)
    return {
        "results": [
            {"title": "Software Engineer", "company": "TechCorp", "location": "Remote", "url": "https://example.com/job/1"},
            {"title": "Data Scientist", "company": "DataWorks", "location": "New York, NY", "url": "https://example.com/job/2"}
        ],
        "query": query,
        "location": location
    }
