"""
Match Analysis Page - Deep dive into individual job matches
"""

import streamlit as st
import sys
from pathlib import Path
import json
import asyncio

# Setup path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.db import get_db_connection, init_db, get_match_by_ids, get_resume_by_id, get_job_by_id

# ADD THIS FUNCTION HERE
def get_confidence_badge(confidence):
    """Return emoji, label, background color, and text color based on confidence score"""
    if confidence >= 0.85:
        return "🟢", "High", "#d4edda", "#155724"
    elif confidence >= 0.70:
        return "🟡", "Medium", "#fff3cd", "#856404"
    else:
        return "🔴", "Low", "#f8d7da", "#721c24"

init_db()

# Page config
st.set_page_config(
    page_title="Match Analysis | Career Copilot",
    page_icon="🔬",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
    .strength-item {
        background: #d4edda;
        padding: 0.75rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .gap-item {
        background: #f8d7da;
        padding: 0.75rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #dc3545;
    }
    .suggestion-item {
        background: #fff3cd;
        padding: 0.75rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #ffc107;
    }
    .match-bullet {
        background: #e7f3ff;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        border-left: 4px solid #2196F3;
    }
    .skill-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .skill-matched {
        background: #d4edda;
        color: #155724;
    }
    .skill-missing {
        background: #f8d7da;
        color: #721c24;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("🔬 Deep Match Analysis")
st.markdown("Detailed breakdown of resume-to-job matching")

# Get all matches with detailed analysis
conn = get_db_connection()
cursor = conn.cursor()

matches_with_analysis = cursor.execute("""
    SELECT 
        m.resume_id,
        m.job_id,
        r.name as resume_name,
        j.title as job_title,
        j.company,
        m.score,
        m.confidence,
        m.detailed_analysis
    FROM resume_job_matches m
    JOIN resumes r ON m.resume_id = r.id
    JOIN jobs j ON m.job_id = j.id
    WHERE m.detailed_analysis IS NOT NULL
    ORDER BY m.score DESC
""").fetchall()

conn.close()

# Check if any detailed matches exist
if not matches_with_analysis:
    st.info("""
    📭 **No detailed analysis available yet**
    
    Run resume matching to generate detailed analysis for your top matches.
    Detailed analysis is performed on the top 5 matches only.
    """)
    
    if st.button("➡️ Go to Resume Matching"):
        st.switch_page("pages/4_🎯_Resume_Matching.py")
    st.stop()

# Select match to analyze
st.markdown("### 🎯 Select Match to Analyze")

# Get unique resumes
unique_resumes = {}
for m in matches_with_analysis:
    if m[0] not in unique_resumes:
        unique_resumes[m[0]] = m[2]  # resume_id: resume_name

# Check if coming from Resume Matching with pre-selected match
preselected_resume_id = None
preselected_job_id = None
if 'selected_match' in st.session_state:
    preselected_resume_id = st.session_state.selected_match['resume_id']
    preselected_job_id = st.session_state.selected_match['job_id']
    del st.session_state.selected_match

# Resume selector (with pre-selection if available)
if preselected_resume_id and preselected_resume_id in unique_resumes:
    default_resume_name = unique_resumes[preselected_resume_id]
    default_resume_index = list(unique_resumes.values()).index(default_resume_name)
else:
    default_resume_index = 0

selected_resume_name = st.selectbox(
    "Choose Resume",
    options=list(unique_resumes.values()),
    index=default_resume_index
)

# Get the resume_id for selected resume
selected_resume_id = [k for k, v in unique_resumes.items() if v == selected_resume_name][0]

# Filter matches for selected resume
filtered_matches = [m for m in matches_with_analysis if m[0] == selected_resume_id]

# Match selector (with pre-selection if available)
match_options = {
    f"{m[3]} at {m[4]} ({m[5]}/100)": (m[0], m[1]) 
    for m in filtered_matches
}

# Find default job index if pre-selected
if preselected_job_id:
    default_job_index = 0
    for idx, (label, (r_id, j_id)) in enumerate(match_options.items()):
        if j_id == preselected_job_id:
            default_job_index = idx
            break
else:
    default_job_index = 0

selected_label = st.selectbox(
    "Choose Job Match",
    options=list(match_options.keys()),
    index=default_job_index
)

resume_id, job_id = match_options[selected_label]

# Get full match details
match = get_match_by_ids(resume_id, job_id)
resume = get_resume_by_id(resume_id)
job = get_job_by_id(job_id)


if not match or not match.get('detailed_analysis'):
    st.error("❌ Detailed analysis not found for this match")
    st.stop()

# Parse detailed analysis JSON
try:
    analysis = json.loads(match['detailed_analysis'])
except:
    st.error("❌ Error parsing analysis data")
    st.stop()

# Display Confidence Banner
confidence = match.get('confidence', 0.5)
emoji, conf_label, bg_color, text_color = get_confidence_badge(confidence)

st.markdown("---")

if confidence < 0.7:
    st.warning(f"""
    {emoji} **{conf_label} Confidence ({confidence:.0%})**
    
    This match may need review. The system identified some uncertainties in the analysis.
    """)
elif confidence < 0.85:
    st.info(f"""
    {emoji} **{conf_label} Confidence ({confidence:.0%})**
    
    Solid match with minor ambiguities.
    """)
else:
    st.success(f"""
    {emoji} **{conf_label} Confidence ({confidence:.0%})**
    
    Strong, clear evidence for this match.
    """)

# Show uncertainty factors if confidence is not high
if confidence < 0.85:
    with st.expander("ℹ️ Why isn't confidence higher?", expanded=(confidence < 0.7)):
        # Try to get from detailed analysis first
        uncertainty_factors = analysis.get('uncertainty_factors', [])
        confidence_reasoning = analysis.get('confidence_reasoning', '')
        
        if uncertainty_factors:
            st.markdown("**Uncertainty factors identified:**")
            for factor in uncertainty_factors:
                st.markdown(f"- {factor}")
        else:
            st.markdown("No specific uncertainty factors recorded.")
        
        if confidence_reasoning:
            st.markdown(f"\n**Analysis:** {confidence_reasoning}")

# ====================================================================
# SELF-IMPROVEMENT SECTION - MOVED TO TOP
# ====================================================================
    
    st.markdown("---")
st.markdown("### 🤖 AI Self-Improvement")

col_improve1, col_improve2, col_improve3 = st.columns([2, 1, 1])

with col_improve1:
    st.markdown("Let the AI analyze and refine this match for higher quality")

with col_improve2:
    max_iterations = st.number_input(
        "Max Iterations",
        min_value=1,
        max_value=5,
        value=2,
        help="Number of refinement cycles"
    )

with col_improve3:
    if st.button("🚀 Improve Match", type="primary", use_container_width=True):
        with st.spinner("🤖 AI reviewing and refining this match..."):
            try:
                # Import plugins and get kernel/db_service from chatbot
                from agents.plugins.SelfImprovingMatchPlugin import SelfImprovingMatchPlugin
                from agents.plugins.ResumeMatchingPlugin import ResumeMatchingPlugin
                from services.chatbot import get_kernel, get_database_service
                
                # ✅ REUSE existing kernel and db_service from chatbot
                kernel = get_kernel()
                db_service = get_database_service()
                
                # Create plugin instances
                matching_plugin = ResumeMatchingPlugin(kernel, db_service)
                self_improving = SelfImprovingMatchPlugin(kernel, matching_plugin)
                
                # Run self-improvement for THIS SPECIFIC JOB only
                result_json = asyncio.run(self_improving.self_improve_single_match(
                    resume_id=str(resume_id),
                    job_id=str(job_id),
                    max_iterations=max_iterations
                ))
                
                result = json.loads(result_json)
                
                if result.get('success'):
                    st.success(f"✅ {result['summary']}")
                    
                    # Show improvement metrics
                    col_r1, col_r2, col_r3 = st.columns(3)
                    with col_r1:
                        st.metric("Iterations", result.get('iterations', 0))
                    with col_r2:
                        old_score = match['score']
                        new_score = result.get('final_score', 0)
                        st.metric("Final Score", f"{new_score}/100", delta=new_score - old_score)
                    with col_r3:
                        st.metric("Quality", f"{result.get('final_quality', 0)}/100")
                    
                    # Show refinement log
                    if result.get('refinement_log'):
                        with st.expander("🔍 View Improvement Details", expanded=True):
                            for log in result['refinement_log']:
                                st.markdown(f"#### Iteration {log['iteration']}")
                                
                                col_log1, col_log2 = st.columns(2)
                                
                                with col_log1:
                                    if log.get('strengths'):
                                        st.markdown("**💪 Strengths:**")
                                        for strength in log['strengths']:
                                            st.write(f"✅ {strength}")
                                
                                with col_log2:
                                    if log.get('weaknesses'):
                                        st.markdown("**⚠️ Weaknesses:**")
                                        for weakness in log['weaknesses']:
                                            st.write(f"⚠️ {weakness}")
                                
                                if log.get('issues'):
                                    st.markdown("**🔍 Issues Found:**")
                                    for issue in log['issues']:
                                        severity = issue.get('severity', 'medium')
                                        emoji = '🔴' if severity == 'high' else '🟡' if severity == 'medium' else '🟢'
                                        st.write(f"{emoji} {issue.get('issue', 'Unknown')}")
                                
                                if log.get('refinements'):
                                    st.markdown("**🔧 Refinements Applied:**")
                                    for ref in log['refinements']:
                                        st.write(f"🔄 **{ref.get('area', 'General')}**: {ref.get('change', 'N/A')}")
                                
                                st.markdown("---")
                    
                    st.info("🔄 Refreshing page to show updated analysis...")
                    import time
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(f"❌ {result.get('error', 'Unknown error')}")
            
            except Exception as e:
                st.error(f"❌ Error during improvement: {str(e)}")
                with st.expander("See full error"):
                    import traceback
                    st.code(traceback.format_exc())

# ====================================================================
# Display job info
# ====================================================================
st.markdown("---")
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(f"### {match['job_title']}")
    st.markdown(f"**🏢 {match['company']}** | 📍 {match['location']}")

with col2:
    st.markdown(f"""
        <div style="text-align: right;">
            <div style="font-size: 3rem; font-weight: bold; color: {'#28a745' if match['score'] >= 75 else '#ffc107' if match['score'] >= 50 else '#dc3545'};">
                {match['score']}/100
            </div>
            <div style="color: #666;">Overall Match Score</div>
        </div>
    """, unsafe_allow_html=True)

# Score breakdown
st.markdown("---")
st.markdown("### 📊 Score Breakdown")

breakdown = analysis.get('score_breakdown', {})
if breakdown:
    cols = st.columns(4)
    
    metrics = [
        ("Skills Match", breakdown.get('skills_match', 0)),
        ("Experience Match", breakdown.get('experience_match', 0)),
        ("Requirements Match", breakdown.get('requirements_match', 0)),
        ("Education Match", breakdown.get('education_match', 0))
    ]
    
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("Score breakdown not available")


# Matched bullets - grouped by strength
st.markdown("---")
st.markdown("### 🔄 Experience Alignment")

matched_bullets = analysis.get('matched_bullets', [])

if matched_bullets:
    # Group bullets by match strength
    strong_matches = [b for b in matched_bullets if b.get('match_strength') == 'strong']
    moderate_matches = [b for b in matched_bullets if b.get('match_strength') == 'moderate']
    weak_matches = [b for b in matched_bullets if b.get('match_strength') == 'weak']
    
    # STRONG MATCHES (GREEN)
    if strong_matches:
        st.markdown("#### 🟢 Strong Matches")
        for i, bullet in enumerate(strong_matches, 1):
            st.markdown(f"""
                <div style="background: #e7f3ff; padding: 0.75rem; border-radius: 5px; margin-bottom: 0.75rem; border-left: 4px solid #28a745;">
                    <strong style="font-size: 0.9rem;">Match {i}</strong><br>
                    <div style="margin-top: 0.25rem;">
                        <strong>💼 Job Requirement:</strong><br>
                        <span style="color: #333;">{bullet.get('job_requirement', 'N/A')}</span>
                    </div>
                    <div style="margin-top: 0.25rem;">
                        <strong>📄 Your Resume:</strong><br>
                        <span style="color: #333;">{bullet.get('resume_bullet', 'N/A')}</span>
                    </div>
                    <div style="margin-top: 0.25rem;">
                        <strong>💡 Why:</strong> <em style="color: #666;">{bullet.get('explanation', '')}</em>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # MODERATE MATCHES (YELLOW)
    if moderate_matches:
        st.markdown("#### 🟡 Moderate Matches")
        for i, bullet in enumerate(moderate_matches, 1):
            st.markdown(f"""
                <div style="background: #fff9e6; padding: 0.75rem; border-radius: 5px; margin-bottom: 0.75rem; border-left: 4px solid #ffc107;">
                    <strong style="font-size: 0.9rem;">Match {i}</strong><br>
                    <div style="margin-top: 0.25rem;">
                        <strong>💼 Job Requirement:</strong><br>
                        <span style="color: #333;">{bullet.get('job_requirement', 'N/A')}</span>
                    </div>
                    <div style="margin-top: 0.25rem;">
                        <strong>📄 Your Resume:</strong><br>
                        <span style="color: #333;">{bullet.get('resume_bullet', 'N/A')}</span>
                    </div>
                    <div style="margin-top: 0.25rem;">
                        <strong>💡 Why:</strong> <em style="color: #666;">{bullet.get('explanation', '')}</em>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # WEAK/MISSING MATCHES (RED)
    if weak_matches:
        st.markdown("#### 🔴 Missing or Weak Matches")
        for i, bullet in enumerate(weak_matches, 1):
            resume_text = bullet.get('resume_bullet', 'N/A')
            if '❌' in resume_text or 'No matching' in resume_text:
                resume_display = '<span style="color: #dc3545; font-weight: 500;">❌ No matching line found</span>'
            else:
                resume_display = f'<span style="color: #333;">{resume_text}</span>'
            
            st.markdown(f"""
                <div style="background: #ffe6e6; padding: 0.75rem; border-radius: 5px; margin-bottom: 0.75rem; border-left: 4px solid #dc3545;">
                    <strong style="font-size: 0.9rem;">Gap {i}</strong><br>
                    <div style="margin-top: 0.25rem;">
                        <strong>💼 Job Requirement:</strong><br>
                        <span style="color: #333;">{bullet.get('job_requirement', 'N/A')}</span>
                    </div>
                    <div style="margin-top: 0.25rem;">
                        <strong>📄 Your Resume:</strong><br>
                        {resume_display}
                    </div>
                    <div style="margin-top: 0.25rem;">
                        <strong>💡 Why:</strong> <em style="color: #666;">{bullet.get('explanation', '')}</em>
                    </div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("No specific bullet point matches identified")

# Improvement suggestions
st.markdown("---")
st.markdown("### 💡 How to Improve Your Match")

suggestions = analysis.get('improvement_suggestions', [])
if suggestions:
    for i, suggestion in enumerate(suggestions, 1):
        st.markdown(f"""
            <div class="suggestion-item">
                <strong>{i}.</strong> {suggestion}
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("No specific improvement suggestions available")

# Summary
st.markdown("---")
st.markdown("### 📝 Summary")
st.info(analysis.get('summary', match.get('reason', 'No summary available')))

# Action buttons
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔗 Apply to Job", type="primary", use_container_width=True):
        st.markdown(f"[Open Application Link]({match['link']})")

with col2:
    if st.button("📄 View Full Job Description", use_container_width=True):
        with st.expander("Job Description", expanded=True):
            st.text_area("", match['description'], height=300, disabled=True)

with col3:
    if st.button("📋 View Full Resume", use_container_width=True):
        with st.expander("Resume", expanded=True):
            formatted_text = resume['text'].replace('. ', '.\n\n')
            st.markdown(f"```\n{formatted_text}\n```")

# Sidebar
with st.sidebar:
    st.markdown("### 🔬 Analysis Info")
    st.info(f"""
    **Resume:** {match['resume_name']}
    
    **Job:** {match['job_title']}
    
    **Company:** {match['company']}
    
    **Analyzed:** {match['matched_at']}
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 Quick Stats")
    st.metric("Overall Score", f"{match['score']}/100")
    if breakdown:
        st.metric("Skills Match", f"{breakdown.get('skills_match', 0)}/100")
        st.metric("Experience Match", f"{breakdown.get('experience_match', 0)}/100")
    
    st.markdown("---")
    
    if st.button("🔙 Back to Match Results", use_container_width=True):
        st.switch_page("pages/5_📊_Match_Results.py")