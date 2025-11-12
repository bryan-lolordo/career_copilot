"""
Reusable UI Components for Career Copilot
"""

import streamlit as st
from typing import Dict, List, Optional

def render_job_card(
    title: str,
    company: str,
    location: str,
    description: str = "",
    link: Optional[str] = None,
    show_actions: bool = True,
    job_id: Optional[int] = None
):
    """
    Render a job card with consistent styling
    
    Args:
        title: Job title
        company: Company name
        location: Job location
        description: Job description
        link: URL to job posting
        show_actions: Whether to show action buttons
        job_id: Job ID for actions
    """
    st.markdown(f"""
        <div style="
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        ">
            <div style="font-size: 1.3rem; font-weight: bold; color: #2c3e50;">{title}</div>
            <div style="font-size: 1.1rem; color: #667eea; margin: 0.3rem 0;">🏢 {company}</div>
            <div style="color: #6c757d; font-size: 0.9rem;">📍 {location}</div>
        </div>
    """, unsafe_allow_html=True)
    
    if description:
        with st.expander("📄 View Description"):
            st.write(description[:500] + "..." if len(description) > 500 else description)
    
    if show_actions:
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if link:
                st.link_button("🔗 View", link)
        
        with col2:
            if job_id:
                if st.button("💾 Save", key=f"save_job_{job_id}"):
                    return "save"
                if st.button("🗑️ Delete", key=f"delete_job_{job_id}"):
                    return "delete"
    
    return None


def render_resume_card(
    name: str,
    file_type: str,
    uploaded_at: str,
    content: str,
    resume_id: int
):
    """
    Render a resume card with consistent styling
    
    Args:
        name: Resume name
        file_type: File type (PDF, DOCX, etc.)
        uploaded_at: Upload timestamp
        content: Resume text content
        resume_id: Resume ID for actions
    """
    st.markdown(f"""
        <div style="
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
            border-left: 4px solid #667eea;
        ">
            <div style="font-size: 1.2rem; font-weight: bold; color: #2c3e50;">📄 {name}</div>
            <div style="color: #6c757d; font-size: 0.9rem; margin-top: 0.5rem;">
                Uploaded: {uploaded_at} | Type: {file_type}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("👀 View", key=f"view_resume_{resume_id}"):
            return "view"
    
    with col2:
        st.download_button(
            label="📥 Download",
            data=content,
            file_name=f"{name}.txt",
            mime="text/plain",
            key=f"download_resume_{resume_id}"
        )
    
    with col3:
        if st.button("🗑️ Delete", key=f"delete_resume_{resume_id}"):
            return "delete"
    
    return None


def render_match_result(
    job_title: str,
    company: str,
    location: str,
    score: int,
    reasoning: str,
    match_id: int,
    resume_name: str = "",
    matched_at: str = ""
):
    """
    Render a match result card with score visualization
    
    Args:
        job_title: Job title
        company: Company name
        location: Job location
        score: Match score (0-100)
        reasoning: AI reasoning for the match
        match_id: Match ID for actions
        resume_name: Name of the resume used
        matched_at: Timestamp of match
    """
    # Determine score styling
    if score >= 75:
        badge_class = "excellent"
        badge_color = "#d4edda"
        badge_text_color = "#155724"
        bar_color = "#28a745"
        emoji = "🟢"
    elif score >= 50:
        badge_class = "good"
        badge_color = "#fff3cd"
        badge_text_color = "#856404"
        bar_color = "#ffc107"
        emoji = "🟡"
    else:
        badge_class = "poor"
        badge_color = "#f8d7da"
        badge_text_color = "#721c24"
        bar_color = "#dc3545"
        emoji = "🔴"
    
    st.markdown(f"""
        <div style="
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 1.3rem; font-weight: bold; color: #2c3e50;">
                        {emoji} {job_title}
                    </div>
                    <div style="font-size: 1rem; color: #667eea; margin: 0.3rem 0;">
                        🏢 {company} | 📍 {location}
                    </div>
                </div>
                <div style="
                    background: {badge_color};
                    color: {badge_text_color};
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 1.2rem;
                ">
                    {score}/100
                </div>
            </div>
            <div style="
                height: 20px;
                border-radius: 10px;
                background: #e9ecef;
                margin-top: 1rem;
                overflow: hidden;
            ">
                <div style="
                    height: 100%;
                    width: {score}%;
                    background: {bar_color};
                    transition: width 0.3s;
                "></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if resume_name:
        st.caption(f"📄 Resume: {resume_name}")
    if matched_at:
        st.caption(f"📅 Matched: {matched_at}")
    
    with st.expander("💡 View AI Reasoning"):
        st.write(reasoning)
    
    if st.button("🗑️ Delete Match", key=f"delete_match_{match_id}"):
        return "delete"
    
    return None


def render_stats_card(label: str, value: str, icon: str = "📊"):
    """
    Render a statistics card
    
    Args:
        label: Stat label
        value: Stat value
        icon: Emoji icon
    """
    st.markdown(f"""
        <div style="
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        ">
            <div style="font-size: 0.9rem; color: #6c757d; margin-bottom: 0.5rem;">
                {icon} {label}
            </div>
            <div style="font-size: 2.5rem; font-weight: bold; color: #667eea;">
                {value}
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_empty_state(
    title: str,
    message: str,
    button_text: Optional[str] = None,
    button_page: Optional[str] = None
):
    """
    Render an empty state message
    
    Args:
        title: Title of empty state
        message: Descriptive message
        button_text: Optional CTA button text
        button_page: Optional page to navigate to
    """
    st.info(f"""
    ### {title}
    
    {message}
    """)
    
    if button_text and button_page:
        if st.button(button_text):
            st.switch_page(button_page)


def render_error_message(error: Exception, context: str = ""):
    """
    Render a formatted error message
    
    Args:
        error: Exception object
        context: Additional context about the error
    """
    error_msg = f"❌ Error"
    if context:
        error_msg += f" {context}"
    error_msg += f": {str(error)}"
    
    st.error(error_msg)


def render_success_message(message: str, show_balloons: bool = False):
    """
    Render a success message
    
    Args:
        message: Success message
        show_balloons: Whether to show celebration balloons
    """
    st.success(f"✅ {message}")
    if show_balloons:
        st.balloons()


def apply_custom_css():
    """Apply custom CSS styling for the entire app"""
    st.markdown("""
        <style>
        /* Global styles */
        .stApp {
            background: #f8f9fa;
        }
        
        /* Card hover effects */
        .element-container:has(.job-card):hover {
            transform: translateY(-2px);
        }
        
        /* Button styling */
        .stButton button {
            border-radius: 8px;
            transition: all 0.2s;
        }
        
        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            border-radius: 8px;
            background: #f8f9fa;
        }
        
        /* Metrics */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            color: #667eea;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        [data-testid="stSidebar"] * {
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)