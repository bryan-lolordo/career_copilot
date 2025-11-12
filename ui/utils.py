"""
UI Utilities for Career Copilot
"""

import streamlit as st
from typing import Any, Dict, List
import pandas as pd

def initialize_session_state(defaults: Dict[str, Any]):
    """
    Initialize session state variables with default values
    
    Args:
        defaults: Dictionary of key-value pairs for session state
    """
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_session_state(*keys: str):
    """
    Clear specific session state variables
    
    Args:
        keys: Variable names to clear
    """
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]


def paginate_dataframe(df: pd.DataFrame, page_size: int = 10):
    """
    Paginate a dataframe for display
    
    Args:
        df: DataFrame to paginate
        page_size: Number of rows per page
        
    Returns:
        Tuple of (current_page_df, total_pages, current_page)
    """
    total_pages = len(df) // page_size + (1 if len(df) % page_size > 0 else 0)
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    # Pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ Previous", disabled=st.session_state.current_page == 1):
            st.session_state.current_page -= 1
            st.rerun()
    
    with col2:
        st.markdown(f"<div style='text-align: center;'>Page {st.session_state.current_page} of {total_pages}</div>", 
                   unsafe_allow_html=True)
    
    with col3:
        if st.button("Next ➡️", disabled=st.session_state.current_page == total_pages):
            st.session_state.current_page += 1
            st.rerun()
    
    # Get current page data
    start_idx = (st.session_state.current_page - 1) * page_size
    end_idx = start_idx + page_size
    
    return df.iloc[start_idx:end_idx], total_pages, st.session_state.current_page


def create_download_link(data: str, filename: str, mime_type: str = "text/plain"):
    """
    Create a download link for data
    
    Args:
        data: Data to download
        filename: Name of file
        mime_type: MIME type of file
        
    Returns:
        Download button component
    """
    return st.download_button(
        label="📥 Download",
        data=data,
        file_name=filename,
        mime=mime_type
    )


def confirm_action(action_name: str, confirm_key: str):
    """
    Two-step confirmation for destructive actions
    
    Args:
        action_name: Name of the action (e.g., "Delete")
        confirm_key: Unique key for confirmation state
        
    Returns:
        True if action is confirmed, False otherwise
    """
    if st.session_state.get(confirm_key, False):
        if st.button(f"✅ Confirm {action_name}", type="primary"):
            st.session_state[confirm_key] = False
            return True
        if st.button("❌ Cancel"):
            st.session_state[confirm_key] = False
            st.rerun()
    else:
        if st.button(f"🗑️ {action_name}"):
            st.session_state[confirm_key] = True
            st.rerun()
    
    return False


def format_score_color(score: int) -> str:
    """
    Get color based on score value
    
    Args:
        score: Score value (0-100)
        
    Returns:
        Color hex code
    """
    if score >= 75:
        return "#28a745"  # Green
    elif score >= 50:
        return "#ffc107"  # Yellow
    else:
        return "#dc3545"  # Red


def format_date(date_string: str) -> str:
    """
    Format date string for display
    
    Args:
        date_string: Date string to format
        
    Returns:
        Formatted date string
    """
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(date_string)
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except:
        return date_string


def search_dataframe(df: pd.DataFrame, search_term: str, columns: List[str]) -> pd.DataFrame:
    """
    Search dataframe across multiple columns
    
    Args:
        df: DataFrame to search
        search_term: Search term
        columns: List of column names to search in
        
    Returns:
        Filtered dataframe
    """
    if not search_term:
        return df
    
    mask = pd.Series([False] * len(df))
    for col in columns:
        if col in df.columns:
            mask |= df[col].astype(str).str.contains(search_term, case=False, na=False)
    
    return df[mask]


def display_loading_spinner(message: str = "Loading..."):
    """
    Display a loading spinner with message
    
    Args:
        message: Loading message
        
    Returns:
        Context manager for spinner
    """
    return st.spinner(message)


def create_filter_widget(df: pd.DataFrame, column: str, label: str) -> str:
    """
    Create a filter selectbox for a dataframe column
    
    Args:
        df: DataFrame to filter
        column: Column name
        label: Label for selectbox
        
    Returns:
        Selected filter value
    """
    unique_values = ['All'] + sorted(df[column].unique().tolist())
    return st.selectbox(label, options=unique_values)


def export_to_csv(df: pd.DataFrame, filename: str = "export.csv"):
    """
    Export dataframe to CSV with download button
    
    Args:
        df: DataFrame to export
        filename: Name of CSV file
    """
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )


def show_notification(message: str, type: str = "info"):
    """
    Show a notification message
    
    Args:
        message: Notification message
        type: Type of notification (info, success, warning, error)
    """
    if type == "info":
        st.info(message)
    elif type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)


def create_tabs(tab_names: List[str]):
    """
    Create tabs with consistent styling
    
    Args:
        tab_names: List of tab names
        
    Returns:
        List of tab objects
    """
    return st.tabs(tab_names)


def render_sidebar_navigation():
    """
    Render sidebar navigation with page links
    """
    with st.sidebar:
        st.markdown("### 📱 Navigation")
        
        pages = {
            "🏠 Home": "streamlit_app.py",
            "💬 Chatbot": "pages/1_💬_Chatbot.py",
            "🔍 Job Search": "pages/2_🔍_Job_Search.py",
            "📄 Resume Manager": "pages/3_📄_Resume_Manager.py",
            "🎯 Resume Matching": "pages/4_🎯_Resume_Matching.py",
            "📊 Match Results": "pages/5_📊_Match_Results.py",
            "💾 Saved Jobs": "pages/6_💾_Saved_Jobs.py"
        }
        
        for page_name, page_path in pages.items():
            if st.button(page_name, use_container_width=True):
                st.switch_page(page_path)