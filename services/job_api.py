# services/job_api.py
import os
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Load environment variables from .env file
load_dotenv()


def extract_job_link(job: dict) -> str:
    """
    Try multiple strategies to find a usable job application URL.
    
    SerpAPI doesn't always provide direct links, so we try multiple
    fallback strategies to give users the best possible link.
    
    Args:
        job: Job dictionary from SerpAPI response
    
    Returns:
        A URL string (either direct link or Google search fallback)
    
    Priority order:
        1. Direct job link from SerpAPI
        2. Apply link from detected extensions
        3. Source-based Google search
        4. Generic Google search with job title + company
    """
    # ====================================================================
    # STRATEGY 1: Direct link from SerpAPI
    # ====================================================================
    if job.get("link"):
        return job["link"]

    # ====================================================================
    # STRATEGY 2: Check detected_extensions for apply link
    # ====================================================================
    # SerpAPI sometimes stores the 'via' site or apply link here
    detected = job.get("detected_extensions", {})
    
    if "apply_link" in detected:
        return detected["apply_link"]
    
    if "source" in detected:
        # Create a search link targeting the specific source
        title = job.get("title", "").replace(" ", "+")
        source = detected["source"].replace(" ", "+")
        return f"https://www.google.com/search?q={title}+{source}"

    # ====================================================================
    # STRATEGY 3: Last resort - Generic Google search link
    # ====================================================================
    # Build a search query with job title and company name
    title = job.get("title", "").replace(" ", "+")
    company = job.get("company_name", "").replace(" ", "+")
    return f"https://www.google.com/search?q={title}+{company}+job"


def search_jobs(
    query: str, 
    location: str = "Chicago, IL", 
    num_results: int = 5
) -> List[Dict[str, Optional[str]]]:
    """
    Fetch job listings from Google Jobs via SerpAPI.
    
    This service connects to SerpAPI to search for jobs matching the query
    and location. The results are then saved to the database by JobPlugin.
    
    Args:
        query: Job search keywords (e.g., "Python Developer", "Data Scientist")
        location: Geographic location for the search (default: "Chicago, IL")
        num_results: Number of results to fetch (max 5, enforced for cost control)
    
    Returns:
        List of job dictionaries with keys:
            - title: Job title
            - company: Company name
            - location: Job location
            - link: Application URL
            - description: Job description text
    
    Raises:
        ValueError: If SERPAPI_KEY is not set in environment variables
    
    Example:
        >>> jobs = search_jobs("Software Engineer", "New York, NY", 5)
        >>> print(f"Found {len(jobs)} jobs")
    """
    # ====================================================================
    # STEP 1: Validate API key exists
    # ====================================================================
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError(
            "Missing SERPAPI_KEY in .env file. "
            "Get your key from https://serpapi.com and add it to .env"
        )
    
    # ====================================================================
    # STEP 2: Enforce maximum results limit (cost control)
    # ====================================================================
    # SerpAPI charges per search, so we cap at 5 results to control costs
    # Even if the AI requests more, we enforce this limit
    num_results = min(num_results, 5)

    # ====================================================================
    # STEP 3: Build API request
    # ====================================================================
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_jobs",         # Use Google Jobs search engine
        "q": f"{query} in {location}",   # Combined query string
        "api_key": api_key,              # Authentication
        "num": num_results               # Number of results
    }

    # ====================================================================
    # STEP 4: Make API request with error handling
    # ====================================================================
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise exception for 4xx/5xx status codes
        
        # Parse JSON response
        data = response.json()
        
        # Check for SerpAPI-specific errors
        if "error" in data:
            print(f"[ERROR] SerpAPI error: {data['error']}")
            return []
        
        # Extract job results from response
        results = data.get("jobs_results", [])
        
    except requests.exceptions.Timeout:
        print(f"[ERROR] SerpAPI request timed out after 10 seconds")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] SerpAPI request failed: {e}")
        return []
    except ValueError as e:
        # JSON parsing error
        print(f"[ERROR] Failed to parse SerpAPI response: {e}")
        return []

    # ====================================================================
    # STEP 5: Format results into standardized structure
    # ====================================================================
    jobs = []
    for j in results:
        job_dict = {
            "title": j.get("title", "Unknown Title"),
            "company": j.get("company_name", "Unknown Company"),
            "location": j.get("location", "Unknown Location"),
            "link": extract_job_link(j),
            "description": j.get("description", "")
        }
        jobs.append(job_dict)

    # ====================================================================
    # STEP 6: Log success and return
    # ====================================================================
    print(f"[INFO] Retrieved {len(jobs)} job(s) for '{query}' in {location}")
    return jobs


def test_serpapi_connection() -> bool:
    """
    Test if SerpAPI is configured correctly and accessible.
    
    Useful for debugging API connection issues.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            print("[ERROR] SERPAPI_KEY not found in environment")
            return False
        
        # Make a minimal test request
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google",
            "q": "test",
            "api_key": api_key,
            "num": 1
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        print("[SUCCESS] SerpAPI connection test passed")
        return True
        
    except Exception as e:
        print(f"[ERROR] SerpAPI connection test failed: {e}")
        return False