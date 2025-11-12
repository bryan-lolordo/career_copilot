"""
Career Copilot - Main Entry Point
A modern AI-powered career assistant for job searching and resume matching.
"""

import streamlit as st
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Career Copilot",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .feature-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        transition: transform 0.2s;
    }
    .feature-card:hover {
        transform: translateX(5px);
    }
    .stat-box {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-label {
        color: #6c757d;
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>🚀 Career Copilot</h1>
        <p>Your AI-Powered Career Assistant</p>
    </div>
""", unsafe_allow_html=True)

# Welcome message
st.markdown("""
### Welcome! 👋

Career Copilot is an intelligent assistant that helps you navigate your job search journey with AI-powered tools.
""")

# Features overview
st.markdown("### ✨ What You Can Do")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h4>💬 AI Chatbot</h4>
        <p>Have natural conversations with your AI assistant. Ask questions, get help, and let AI handle the heavy lifting.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <h4>🔍 Job Search</h4>
        <p>Search for jobs using Google Jobs API. Save interesting opportunities to your personal database.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <h4>📄 Resume Manager</h4>
        <p>Upload and manage your resumes. Support for PDF and DOCX formats with automatic text extraction.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h4>🎯 AI Resume Matching</h4>
        <p>Get AI-powered match scores between your resume and saved jobs. Understand why each match works.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <h4>📊 Match Results</h4>
        <p>View comprehensive rankings of job matches. Filter, sort, and export your results.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-card">
        <h4>💾 Saved Jobs</h4>
        <p>Manage your saved job listings. Filter by company, location, or title. Export to CSV.</p>
    </div>
    """, unsafe_allow_html=True)

# Quick stats (if database exists)
try:
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    from services.db import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get stats
    job_count = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    resume_count = cursor.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
    match_count = cursor.execute("SELECT COUNT(*) FROM resume_matches").fetchone()[0]
    
    conn.close()
    
    st.markdown("### 📊 Your Stats")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{job_count}</div>
            <div class="stat-label">Saved Jobs</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{resume_count}</div>
            <div class="stat-label">Resumes</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{match_count}</div>
            <div class="stat-label">Matches</div>
        </div>
        """, unsafe_allow_html=True)
        
except Exception as e:
    st.info("💡 Start by searching for jobs or uploading a resume!")

# Getting started
st.markdown("---")
st.markdown("""
### 🚀 Getting Started

1. **Search for Jobs** - Use the Job Search page to find opportunities
2. **Upload Your Resume** - Add your resume in the Resume Manager
3. **Match & Analyze** - Let AI match your resume to jobs
4. **Chat with AI** - Ask questions and get personalized help

Navigate using the sidebar to access all features! 👈
""")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    Made with ❤️ using Streamlit and Azure OpenAI | 
    <a href="https://github.com/yourusername/career-copilot" target="_blank">View on GitHub</a>
</div>
""", unsafe_allow_html=True)