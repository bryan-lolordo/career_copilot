"""
Job Search Page - Search and save jobs from Google Jobs API
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from services.job_api import search_jobs
from services.db import save_job, get_db_connection

# Page config
st.set_page_config(
    page_title="Job Search | Career Copilot",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .job-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .job-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .job-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    .job-company {
        font-size: 1.1rem;
        color: #667eea;
        margin-bottom: 0.3rem;
    }
    .job-location {
        color: #6c757d;
        font-size: 0.9rem;
    }
    .job-snippet {
        margin-top: 1rem;
        color: #495057;
        line-height: 1.6;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("🔍 Job Search")
st.markdown("Search for jobs using Google Jobs API and save them to your database")

# Search form
with st.form("search_form"):
    query = st.text_input(
        "Job Title or Keywords",
        placeholder="e.g., Data Scientist, Software Engineer, Product Manager"
    )
    
    location = st.text_input(
        "Location",
        placeholder="e.g., San Francisco, CA"
    )
    
    search_button = st.form_submit_button("🔍 Search Jobs", use_container_width=True)

# Handle search
if search_button:
    if not query:
        st.warning("⚠️ Please enter a job title or keywords")
    else:
        with st.spinner(f"Searching for {query} jobs..."):
            try:
                jobs = search_jobs(query, location)
                
                if jobs:
                    st.success(f"✅ Found {len(jobs)} jobs!")
                    st.session_state.search_results = jobs
                else:
                    st.warning("No jobs found. Try different keywords or location.")
                    st.session_state.search_results = []
                    
            except Exception as e:
                st.error(f"❌ Error searching jobs: {str(e)}")
                st.session_state.search_results = []

# Display results
if hasattr(st.session_state, 'search_results') and st.session_state.search_results:
    st.markdown("---")
    st.markdown(f"### 📋 Results ({len(st.session_state.search_results)} jobs)")
    
    # Add "Save All" button
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("💾 Save All Jobs", use_container_width=True):
            saved_count = 0
            for job in st.session_state.search_results:
                try:
                    save_job(
                        title=job.get('title', ''),
                        company=job.get('company', ''),
                        location=job.get('location', ''),
                        description=job.get('description', ''),
                        link=job.get('link', '')
                    )
                    saved_count += 1
                except Exception:
                    pass
            
            st.success(f"✅ Saved {saved_count} jobs!")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.search_results = []
            st.rerun()
    
    st.markdown("---")
    
    # Display each job
    for idx, job in enumerate(st.session_state.search_results):
        # Clean location - keep only English parts
        location = job.get('location', 'N/A')
        if ',' in location:
            # Split by comma and take first 2 parts (City, State)
            parts = location.split(',')
            location = ', '.join(parts[:2]).strip()
        
        with st.container():
            st.markdown(f"""
                <div class="job-card">
                    <div class="job-title">{job.get('title', 'N/A')}</div>
                    <div>🏢 {job.get('company', 'N/A')}</div>
                    <div>📍 {location}</div> 
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📄 View Full Description"):
                st.markdown(job.get('description', 'No description available'))
            
            col1, col2, col3 = st.columns([1, 1, 4])
            
            with col1:
                if st.button("💾 Save", key=f"save_{idx}"):
                    try:
                        save_job(
                            title=job.get('title', ''),
                            company=job.get('company', ''),
                            location=job.get('location', ''),
                            description=job.get('description', ''),
                            link=job.get('link', '')
                        )
                        st.success("✅ Job saved!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            with col2:
                if job.get('link'):
                    st.link_button("🔗 View Job", job['link'])
            
            st.markdown("---")

else:
    # Show tips when no results
    st.info("""
    ### 💡 Search Tips
    
    - Use specific job titles like "Data Scientist" or "Software Engineer"
    - Add location to narrow down results
    - Try different keywords if you don't find what you're looking for
    - You can save jobs to your database for later analysis
    
    **Example searches:**
    - "Machine Learning Engineer" in "Seattle, WA"
    - "Product Manager" in "New York, NY"
    - "Full Stack Developer" in "Remote"
    """)

# Sidebar stats
with st.sidebar:
    st.markdown("### 📊 Your Stats")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        total_jobs = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        unique_companies = cursor.execute("SELECT COUNT(DISTINCT company) FROM jobs").fetchone()[0]
        
        conn.close()
        
        st.metric("Total Saved Jobs", total_jobs)
        st.metric("Unique Companies", unique_companies)
        
    except Exception as e:
        st.error(f"Error loading stats: {str(e)}")
    
    st.markdown("---")
    st.markdown("""
    ### 🎯 Next Steps
    
    After saving jobs:
    1. View them in **Saved Jobs**
    2. Upload a resume in **Resume Manager**
    3. Get AI match scores in **Resume Matching**
    """)
