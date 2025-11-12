"""
Resume Manager Page - Upload and manage resumes
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Setup path to import from parent directory
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.resume_parser import parse_resume
from services.db import save_resume, delete_resume, get_db_connection

# Page config
st.set_page_config(
    page_title="Resume Manager | Career Copilot",
    page_icon="📄",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .upload-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .resume-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    .resume-name {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2c3e50;
    }
    .resume-meta {
        color: #6c757d;
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("📄 Resume Manager")
st.markdown("Upload new resumes and manage your existing ones")

# ============================================================================
# UPLOAD SECTION
# ============================================================================
st.markdown("""
    <div class="upload-section">
        <h3>📤 Upload New Resume</h3>
        <p>Upload your resume in PDF or DOCX format</p>
    </div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Choose a file",
    type=['pdf', 'docx'],
    help="Upload your resume in PDF or DOCX format",
    key="resume_uploader"
)

resume_name = st.text_input(
    "Resume Name (optional)",
    placeholder="e.g., Software Engineer Resume",
    key="resume_name_input"
)

if uploaded_file:
    st.info(f"📄 **Selected:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")
    
    if st.button("💾 Upload Resume", type="primary"):
        with st.spinner("Processing resume..."):
            try:
                # Parse resume
                resume_text = parse_resume(uploaded_file)
                
                if not resume_text:
                    st.error("❌ Could not extract text from resume. Please check the file.")
                else:
                    # Save to database
                    name = resume_name if resume_name else uploaded_file.name
                    save_resume(name=name, path=uploaded_file.name, text=resume_text)
                    
                    st.success(f"✅ Resume '{name}' uploaded successfully!")
                    st.balloons()
                    
                    # Show preview
                    with st.expander("👀 Preview Resume Text"):
                        st.text_area(
                            "Extracted Text",
                            resume_text[:1000] + "..." if len(resume_text) > 1000 else resume_text,
                            height=200,
                            disabled=True
                        )
                    
                    # Clear the file uploader
                    st.rerun()
            
            except Exception as e:
                st.error(f"❌ Error uploading resume: {str(e)}")

st.markdown("---")

# ============================================================================
# SAVED RESUMES SECTION
# ============================================================================
st.markdown("### 📚 Your Resumes")

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    resumes = cursor.execute("""
        SELECT id, name, path, created_at, text, word_count
        FROM resumes
        ORDER BY created_at DESC
    """).fetchall()
    
    conn.close()
    
    if resumes:
        st.markdown(f"**{len(resumes)} resume(s) saved**")
        st.markdown("")
        
        for resume in resumes:
            resume_id, name, path, created_at, text, word_count = resume
            
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"""
                        <div class="resume-card">
                            <div class="resume-name">📄 {name}</div>
                            <div class="resume-meta">
                                📅 Uploaded: {created_at} 
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.write("")  # Spacing
                    st.write("")
                
                # Action buttons in columns
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if st.button("👀 View", key=f"view_{resume_id}"):
                        st.session_state[f"show_resume_{resume_id}"] = not st.session_state.get(f"show_resume_{resume_id}", False)
            
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{resume_id}"):
                        try:
                            delete_resume(resume_id)
                            st.success("✅ Resume deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                
                # Show resume content if toggled
                if st.session_state.get(f"show_resume_{resume_id}", False):
                    with st.expander("📄 Resume Content", expanded=True):
                        # Format text with line breaks for better readability
                        formatted_text = text.replace('. ', '.\n\n')
                        st.markdown(f"```\n{formatted_text}\n```")

                
                st.markdown("---")
    
    else:
        st.info("""
        📭 **No resumes uploaded yet**
        
        Upload your first resume above to get started!
        
        **Tips:**
        - PDF format works best
        - Make sure text is selectable (not scanned images)
        - You can upload multiple versions of your resume
        """)

except Exception as e:
    st.error(f"❌ Error loading resumes: {str(e)}")

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("### 📊 Resume Stats")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        total_resumes = cursor.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
        
        if total_resumes > 0:
            # Get latest resume info
            latest = cursor.execute("""
                SELECT name, created_at 
                FROM resumes 
                ORDER BY created_at DESC 
                LIMIT 1
            """).fetchone()
            
            st.metric("Total Resumes", total_resumes)
            
            if latest:
                st.markdown("**Latest Upload:**")
                st.info(f"📄 {latest[0]}\n\n📅 {latest[1]}")
        else:
            st.info("No resumes yet")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    st.markdown("""
    ### 🎯 Next Steps
    
    After uploading resumes:
    1. Go to **Resume Matching**
    2. Match against saved jobs
    3. View results in **Match Results**
    """)
    
    st.markdown("---")
    
    st.markdown("""
    ### 💡 Tips
    
    - Upload multiple resume versions
    - Name them descriptively
    - Keep them updated
    - Use for different job types
    """)