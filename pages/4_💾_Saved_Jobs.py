"""
Saved Jobs Page - Manage and view saved job listings
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from services.db import get_db_connection

# Page config
st.set_page_config(
    page_title="Saved Jobs | Career Copilot",
    page_icon="💾",
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
        transition: transform 0.2s;
    }
    .job-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .job-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2c3e50;
    }
    .job-company {
        font-size: 1.1rem;
        color: #667eea;
        margin: 0.3rem 0;
    }
    .job-meta {
        color: #6c757d;
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("💾 Saved Jobs")
st.markdown("Manage your saved job listings")

# Get all saved jobs
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    jobs = cursor.execute("""
        SELECT id, title, company, location, description, link, created_at
        FROM jobs
        ORDER BY created_at DESC
    """).fetchall()
    
    conn.close()
    
except Exception as e:
    st.error(f"❌ Error loading jobs: {str(e)}")
    st.stop()

# Check if jobs exist
if not jobs:
    st.info("""
    📭 **No saved jobs yet**
    
    Go to the **Job Search** page to find and save jobs!
    """)
    
    if st.button("➡️ Go to Job Search"):
        st.switch_page("pages/2_🔍_Job_Search.py")
    
    st.stop()

# Convert to DataFrame
df = pd.DataFrame(jobs, columns=['id', 'title', 'company', 'location', 'description', 'link', 'created_at'])

# Filters and search
st.markdown("### 🔍 Filters & Search")

col1, col2, col3 = st.columns(3)

with col1:
    search_query = st.text_input(
        "Search jobs",
        placeholder="Search by title, company, or description..."
    )

with col2:
    company_filter = st.selectbox(
        "Filter by Company",
        options=['All'] + sorted(df['company'].unique().tolist())
    )

with col3:
    location_filter = st.selectbox(
        "Filter by Location",
        options=['All'] + sorted(df['location'].unique().tolist())
    )

# Apply filters
filtered_df = df.copy()

if search_query:
    filtered_df = filtered_df[
        filtered_df['title'].str.contains(search_query, case=False, na=False) |
        filtered_df['company'].str.contains(search_query, case=False, na=False) |
        filtered_df['description'].str.contains(search_query, case=False, na=False)
    ]

if company_filter != 'All':
    filtered_df = filtered_df[filtered_df['company'] == company_filter]

if location_filter != 'All':
    filtered_df = filtered_df[filtered_df['location'] == location_filter]

# Statistics
st.markdown("---")
st.markdown("### 📊 Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Jobs", len(filtered_df))

with col2:
    st.metric("Unique Companies", df['company'].nunique())

with col3:
    st.metric("Unique Locations", df['location'].nunique())

with col4:
    # Most common company
    if len(df) > 0:
        top_company = df['company'].value_counts().index[0]
        st.metric("Top Company", top_company)

# Bulk actions
st.markdown("---")

if st.button("🗑️ Delete All"):
    if st.session_state.get('confirm_delete_all', False):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs")
            conn.commit()
            conn.close()
            st.success("✅ All jobs deleted!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    else:
        st.session_state.confirm_delete_all = True
        st.warning("⚠️ Click again to confirm deletion")

# Display jobs
st.markdown("---")
st.markdown(f"### 📋 Jobs ({len(filtered_df)} results)")

if len(filtered_df) == 0:
    st.info("No jobs found with the current filters. Try adjusting your search or filters.")
else:
    # Sorting options
    sort_by = st.selectbox(
        "Sort by",
        options=['Newest First', 'Oldest First', 'Company (A-Z)', 'Title (A-Z)']
    )
    
    if sort_by == 'Newest First':
        filtered_df = filtered_df.sort_values('created_at', ascending=False, na_position='last')
    elif sort_by == 'Oldest First':
        filtered_df = filtered_df.sort_values('created_at', ascending=True, na_position='last')
    elif sort_by == 'Company (A-Z)':
        filtered_df = filtered_df.sort_values('company', ascending=True)
    else:  # Title (A-Z)
        filtered_df = filtered_df.sort_values('title', ascending=True)
    
    st.markdown("---")
    
    # Display each job
    for idx, row in filtered_df.iterrows():
        # Clean location
        location = row['location']
        if ',' in location:
            parts = location.split(',')
            location = ', '.join(parts[:2]).strip()
        
        with st.container():
            st.markdown(f"""
                <div class="job-card">
                    <div class="job-title">{row['title']}</div>
                    <div class="job-company">🏢 {row['company']}</div>
                    <div class="job-meta">📍 {location} | 📅 Saved: {row['created_at']}</div>  
                </div>
            """, unsafe_allow_html=True)

            # ADD THIS - Job Description Dropdown
            with st.expander("📄 View Full Job Description"):
                st.markdown(row['description'])
            
            # Actions
            col1, col2, col3 = st.columns([1, 1, 4])
            
            with col1:
                if row['link']:
                    st.link_button("🔗 View Job", row['link'])
            
            with col2:
                if st.button("🗑️ Delete", key=f"delete_{row['id']}"):
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM jobs WHERE id = ?", (row['id'],))
                        conn.commit()
                        conn.close()
                        st.success("✅ Job deleted!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            st.markdown("---")

# Sidebar info
with st.sidebar:
    st.markdown("### 📊 Job Analytics")
    
    # Top companies
    st.markdown("#### Top Companies")
    top_companies = df['company'].value_counts().head(5)
    
    for company, count in top_companies.items():
        st.write(f"**{company}**: {count} jobs")
    
    st.markdown("---")
    
    # Top locations
    st.markdown("#### Top Locations")
    top_locations = df['location'].value_counts().head(5)
    
    for location, count in top_locations.items():
        st.write(f"**{location}**: {count} jobs")
    
    st.markdown("---")
    
    # Tips
    st.markdown("""
    ### 💡 Tips
    
    - Use search to find specific jobs
    - Filter by company or location
    - Export jobs for offline review
    - Match jobs with resumes in **Resume Matching**
    """)
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    
    if st.button("🔍 Search More Jobs", use_container_width=True):
        st.switch_page("pages/2_🔍_Job_Search.py")
    
    if st.button("🎯 Match with Resume", use_container_width=True):
        st.switch_page("pages/4_🎯_Resume_Matching.py")
