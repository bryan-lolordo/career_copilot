"""
Resume Matching & Results - Match resumes to jobs and view results
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import asyncio
import json

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.db import (
    get_db_connection, 
    init_db, 
    has_matches_for_resume,
    get_matches_for_resume,
    get_match_stats_for_resume,
    clear_matches_for_resume
)
from services.chatbot import get_kernel

init_db()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_confidence_badge(confidence):
    """Return emoji, label, background color, and text color based on confidence score"""
    if confidence >= 0.85:
        return "🟢", "High", "#d4edda", "#155724"
    elif confidence >= 0.70:
        return "🟡", "Medium", "#fff3cd", "#856404"
    else:
        return "🔴", "Low", "#f8d7da", "#721c24"

# Page config
st.set_page_config(
    page_title="Resume Matching | Career Copilot",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .result-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .score-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .badge-excellent {
        background: #d4edda;
        color: #155724;
    }
    .badge-good {
        background: #fff3cd;
        color: #856404;
    }
    .badge-poor {
        background: #f8d7da;
        color: #721c24;
    }
    .stat-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("🎯 Resume Matching & Results")
st.markdown("Match your resume to jobs and view detailed results")

# Get all resumes
conn = get_db_connection()
cursor = conn.cursor()

resumes = cursor.execute("""
    SELECT id, name, created_at
    FROM resumes
    ORDER BY created_at DESC
""").fetchall()

conn.close()

if not resumes:
    st.warning("""
    ⚠️ **No resumes found**
    
    Please upload a resume first before matching.
    """)
    
    if st.button("➡️ Go to Resume Manager"):
        st.switch_page("pages/3_📄_Resume_Manager.py")
    
    st.stop()

# Resume Selection
st.markdown("### 📄 Select Resume")

resume_options = {f"{r[1]} (uploaded {r[2][:10]})": r[0] for r in resumes}

# ADD THIS - Remember selected resume across page switches
if 'selected_resume_id' not in st.session_state:
    st.session_state.selected_resume_id = list(resume_options.values())[0]  # Default to first

selected_resume_label = st.selectbox(
    "Choose a resume to match",
    options=list(resume_options.keys()),
    index=list(resume_options.values()).index(st.session_state.selected_resume_id)  # Use saved selection
)

selected_resume_id = resume_options[selected_resume_label]
st.session_state.selected_resume_id = selected_resume_id  # Save the selection
selected_resume_name = selected_resume_label.split(" (uploaded")[0]  # ADD THIS LINE TOO

# Check if matches exist - ADD THIS
has_matches = has_matches_for_resume(selected_resume_id)

st.markdown("---")

# ============================================================================
# STATE 1: NO MATCHES - Show matching button
# ============================================================================
if not has_matches:
    st.info(f"""
    📭 **No matches found for "{selected_resume_name}"**
    
    Click below to match this resume against all saved jobs.
    """)
    
    # Get job count
    conn = get_db_connection()
    cursor = conn.cursor()
    job_count = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    
    if job_count == 0:
        st.warning("⚠️ No jobs found in database. Please search and save jobs first.")
        if st.button("➡️ Go to Job Search"):
            st.switch_page("pages/2_🔍_Job_Search.py")
        st.stop()
    
    st.metric("Jobs Available", job_count)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🎯 Run Matching", type="primary", use_container_width=True):
            with st.spinner(f"🔍 Matching '{selected_resume_name}' against {job_count} jobs..."):
                try:
                    # Import and run matching directly
                    from agents.plugins.ResumeMatchingPlugin import ResumeMatchingPlugin
                    from services.database_service import DatabaseService
                    
                    # Get kernel
                    kernel = get_kernel()
                    db_service = DatabaseService()
                    
                    # Create plugin instance
                    matching_plugin = ResumeMatchingPlugin(kernel, db_service)
                    
                    # Run matching
                    result = asyncio.run(matching_plugin.find_best_job_matches(
                        resume_id=str(selected_resume_id),
                        top_n=5,
                        save_to_db=True
                    ))
                    
                    st.success("✅ Matching complete!")
                    st.balloons()
                    
                    # Auto-refresh to show results
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error during matching: {str(e)}")

                
                    import traceback
                    st.code(traceback.format_exc())

# ============================================================================
# STATE 2: HAS MATCHES - Show results and stats
# ============================================================================
else:
    # Get match statistics
    stats = get_match_stats_for_resume(selected_resume_id)
    
    # Display stats
    st.markdown("### 📊 Match Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="stat-box">
                <h2>{stats['total_matches']}</h2>
                <p style="color: #666; margin: 0;">Total Matches</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stat-box">
                <h2>{stats['avg_score']:.1f}</h2>
                <p style="color: #666; margin: 0;">Average Score</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="stat-box">
                <h2>{stats['top_score']}</h2>
                <p style="color: #666; margin: 0;">Top Score</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        last_matched = stats['last_matched'][:10] if stats['last_matched'] else 'N/A'
        st.markdown(f"""
            <div class="stat-box">
                <h3 style="font-size: 1.2rem;">{last_matched}</h3>
                <p style="color: #666; margin: 0;">Last Updated</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 Re-match All Jobs", use_container_width=True):
            with st.spinner("🔍 Re-matching..."):
                try:
                    # Clear old matches
                    clear_matches_for_resume(selected_resume_id)
                    
                    # Import and run matching
                    from agents.plugins.ResumeMatchingPlugin import ResumeMatchingPlugin
                    from services.database_service import DatabaseService
                    
                    kernel = get_kernel()
                    db_service = DatabaseService()
                    matching_plugin = ResumeMatchingPlugin(kernel, db_service)
                    
                    result = asyncio.run(matching_plugin.find_best_job_matches(
                        resume_id=str(selected_resume_id),
                        top_n=5,
                        save_to_db=True
                    ))
                    
                    st.success("✅ Re-matching complete!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col2:
        if st.button("⚡ Quick Match New Jobs", use_container_width=True):
            with st.spinner("⚡ Quick matching unmatched jobs..."):
                try:
                    from agents.plugins.ResumeMatchingPlugin import ResumeMatchingPlugin
                    from services.database_service import DatabaseService
                    from services.db import save_job_match, get_db_connection
                    import json
                    
                    # Get ALL jobs that haven't been matched yet for this resume
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    unmatched_jobs = cursor.execute("""
                        SELECT j.id, j.title, j.company, j.location, j.description, j.link
                        FROM jobs j
                        WHERE NOT EXISTS (
                            SELECT 1 FROM resume_job_matches m 
                            WHERE m.job_id = j.id AND m.resume_id = ?
                        )
                        ORDER BY j.created_at DESC
                    """, (selected_resume_id,)).fetchall()
                    
                    conn.close()
                    
                    if not unmatched_jobs:
                        st.info("✅ All jobs are already matched!")
                    else:
                        kernel = get_kernel()
                        db_service = DatabaseService()
                        matching_plugin = ResumeMatchingPlugin(kernel, db_service)
                        
                        # Get resume
                        resume = db_service.get_resume_by_id(selected_resume_id)
                        
                        # Quick score only (no deep analysis)
                        for job_row in unmatched_jobs:
                            job = {
                                'id': job_row[0],
                                'title': job_row[1],
                                'company': job_row[2],
                                'location': job_row[3],
                                'description': job_row[4],
                                'link': job_row[5]
                            }
                            
                            result = asyncio.run(
                                matching_plugin._quick_score_job_match(resume['text'], job)
                            )
                            
                            # Save quick score
                            save_job_match(
                                resume_id=selected_resume_id,
                                job_id=job['id'],
                                score=result['score'],
                                reason=json.dumps(result['reason']) if isinstance(result['reason'], list) else result['reason'],
                                detailed_analysis=None
                            )
                        
                        st.success(f"✅ Quick matched {len(unmatched_jobs)} unmatched jobs!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col3:
        if st.button("🗑️ Clear Matches", use_container_width=True):
            if st.session_state.get('confirm_clear', False):
                deleted = clear_matches_for_resume(selected_resume_id)
                st.success(f"✅ Cleared {deleted} matches!")
                st.session_state.confirm_clear = False
                st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("⚠️ Click again to confirm")
    
    # Get match results
    matches = get_matches_for_resume(selected_resume_id)
    
    # Convert to DataFrame
    df = pd.DataFrame(matches, columns=[
        'score', 'reason', 'matched_at', 'detailed_analysis',
        'job_id', 'job_title', 'company', 'location', 'link', 'description'
    ])
    
    # Filters
    st.markdown("---")
    st.markdown("### 🔍 Filters & Sorting")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        company_filter = st.selectbox(
            "Company",
            options=['All'] + df['company'].unique().tolist()
        )
    
    with col2:
        location_filter = st.selectbox(
            "Location",
            options=['All'] + df['location'].unique().tolist()
        )
    
    with col3:
        min_score = st.slider(
            "Minimum Score",
            min_value=0,
            max_value=100,
            value=0
        )
    
    with col4:
        sort_by = st.selectbox(
            "Sort By",
            options=['Score (High to Low)', 'Score (Low to High)', 'Date (Newest)', 'Date (Oldest)']
        )
    
    # Apply filters
    filtered_df = df.copy()
    
    if company_filter != 'All':
        filtered_df = filtered_df[filtered_df['company'] == company_filter]
    
    if location_filter != 'All':
        filtered_df = filtered_df[filtered_df['location'] == location_filter]
    
    filtered_df = filtered_df[filtered_df['score'] >= min_score]
    
    # Apply sorting
    if sort_by == 'Score (High to Low)':
        filtered_df = filtered_df.sort_values('score', ascending=False)
    elif sort_by == 'Score (Low to High)':
        filtered_df = filtered_df.sort_values('score', ascending=True)
    elif sort_by == 'Date (Newest)':
        filtered_df = filtered_df.sort_values('matched_at', ascending=False)
    else:
        filtered_df = filtered_df.sort_values('matched_at', ascending=True)
    
    # Export button
    st.markdown("---")
    if len(filtered_df) > 0:
        csv = filtered_df[['job_title', 'company', 'location', 'score', 'reason']].to_csv(index=False)
        st.download_button(
            label="📥 Export Results to CSV",
            data=csv,
            file_name=f"match_results_{selected_resume_name.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    
    # Display results
    st.markdown("---")
    st.markdown(f"### 📋 Match Results ({len(filtered_df)} jobs)")
    
    if len(filtered_df) == 0:
        st.info("No matches found with current filters.")
    else:
        for idx, row in filtered_df.iterrows():
            score = row['score']
            
            if score >= 75:
                badge_class = "badge-excellent"
                emoji = "🟢"
            elif score >= 50:
                badge_class = "badge-good"
                emoji = "🟡"
            else:
                badge_class = "badge-poor"
                emoji = "🔴"
            
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"### {emoji} {row['job_title']}")
                    st.markdown(f"**🏢 {row['company']}** | 📍 {row['location']}")
                
                with col2:
                    st.markdown(f"""
                        <div class="score-badge {badge_class}">
                            {score}/100
                        </div>
                    """, unsafe_allow_html=True)
                
                # Show brief reason (bullet points)
                with st.expander("💡 Why This Match?"):
                    reasons = row['reason']
                    
                    # Parse JSON string if needed
                    if isinstance(reasons, str):
                        try:
                            reasons = json.loads(reasons)
                        except:
                            pass  # Keep as string if parsing fails
                    
                    # Display as bullets if it's a list
                    if isinstance(reasons, list):
                        for bullet in reasons:
                            st.markdown(f"• {bullet}")
                    else:
                        st.write(reasons)
                # ADD THIS - Job Description Dropdown
                with st.expander("📄 View Full Job Description"):
                    st.markdown(row['description'])
                
                # Action buttons
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    # Check if detailed analysis exists
                    has_detailed = row['detailed_analysis'] is not None and row['detailed_analysis'] != ''
                    
                    if has_detailed:
                        if st.button("🔬 View Deep Analysis", key=f"analysis_{row['job_id']}", use_container_width=True):
                            # Explicitly use the selected_resume_id from this page's scope
                            st.session_state.selected_match = {
                                'resume_id': selected_resume_id,  # This IS defined on line 110
                                'job_id': row['job_id']
                            }
                            st.switch_page("pages/6_🔬_Match_Analysis.py")
                    else:
                        # REPLACE THIS SECTION (lines 422-424)
                        if st.button("🔬 Run Deep Analysis", key=f"run_analysis_{row['job_id']}", use_container_width=True):
                            with st.spinner("🔬 Running deep analysis..."):
                                try:
                                    from agents.plugins.ResumeMatchingPlugin import ResumeMatchingPlugin
                                    from services.database_service import DatabaseService
                                    from services.db import save_job_match
                                    
                                    kernel = get_kernel()
                                    db_service = DatabaseService()
                                    matching_plugin = ResumeMatchingPlugin(kernel, db_service)
                                    
                                    # Get resume and job data
                                    resume = db_service.get_resume_by_id(selected_resume_id)
                                    job = db_service.get_job_by_id(row['job_id'])
                                    
                                    # Run deep analysis with original score
                                    detailed = asyncio.run(
                                        matching_plugin._deep_analyze_job_match(
                                            resume_text=resume['text'],
                                            job=job,
                                            original_score=row['score']
                                        )
                                    )
                                    
                                    # Save the updated match
                                    save_job_match(
                                        resume_id=selected_resume_id,
                                        job_id=row['job_id'],
                                        score=detailed['score'],
                                        reason=json.dumps(detailed['reason']) if isinstance(detailed['reason'], list) else detailed['reason'],
                                        detailed_analysis=detailed.get('detailed_analysis')
                                    )
                                    
                                    st.success("✅ Deep analysis complete!")
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
                        st.caption("(Click to analyze)")
                
                with col_b:
                    if has_detailed:
                        if st.button("✏️ Tailor Resume", key=f"tailor_{row['job_id']}", use_container_width=True):
                            st.session_state.selected_match = {
                                'resume_id': selected_resume_id,
                                'job_id': row['job_id']
                            }
                            st.switch_page("pages/7_✏️_Resume_Tailoring.py")
                    else:
                        st.button("✏️ Tailor Resume", key=f"no_tailor_{row['job_id']}", disabled=True, use_container_width=True)
                        st.caption("(Requires deep analysis)")
                
                with col_c:
                    if st.button("🔗 Apply Now", key=f"apply_{row['job_id']}", use_container_width=True):
                        st.markdown(f"[Open Application]({row['link']})")
                
                st.caption(f"Matched: {row['matched_at']}")
                st.markdown("---")

# Sidebar
with st.sidebar:
    st.markdown("### 📊 Analytics")
    
    if has_matches:
        st.markdown("#### Score Distribution")
        excellent = len(df[df['score'] >= 75])
        good = len(df[(df['score'] >= 50) & (df['score'] < 75)])
        poor = len(df[df['score'] < 50])
        
        st.write(f"🟢 Excellent (75-100): {excellent}")
        st.write(f"🟡 Good (50-74): {good}")
        st.write(f"🔴 Poor (0-49): {poor}")
        
        st.markdown("---")
        
        st.markdown("#### Top Companies")
        if len(df) > 0:
            top_companies = df.groupby('company')['score'].mean().sort_values(ascending=False).head(5)
            for company, avg_score in top_companies.items():
                st.write(f"**{company}**: {avg_score:.1f}")
    else:
        st.info("Run matching to see analytics")