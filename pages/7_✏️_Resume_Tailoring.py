"""
Resume Tailoring Page - AI-powered resume optimization for specific jobs
"""

import streamlit as st
import sys
from pathlib import Path
from rapidfuzz import fuzz
import json
import asyncio


# Setup path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.db import get_db_connection, init_db, get_match_by_ids, get_resume_by_id, get_job_by_id
from services.chatbot import get_kernel

# Get the kernel
kernel = get_kernel()
init_db()

# Page config
st.set_page_config(
    page_title="Resume Tailoring | Career Copilot",
    page_icon="✏️",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .tailoring-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .suggestion-box {
        background: #fff3cd;
        padding: 1rem;
        border-left: 4px solid #ffc107;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .strength-box {
        background: #d4edda;
        padding: 1rem;
        border-left: 4px solid #28a745;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_and_fix_highlights(matched_bullets, resume_text, job_description):
    """
    Validates LLM highlights and fixes them with fuzzy matching if needed.
    
    Returns: matched_bullets with corrected highlight_text fields
    """

    
    def find_best_match(target_text, source_document, threshold=75):
        """Find actual text span in document that matches target."""
        if not target_text or target_text == "N/A":
            return target_text
        
        # Split into sentences
        sentences = source_document.replace('\n', '. ').split('. ')
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        best_match = target_text
        best_score = 0
        
        for sentence in sentences:
            score = fuzz.partial_ratio(target_text.lower(), sentence.lower())
            if score > best_score and score >= threshold:
                best_score = score
                best_match = sentence
        
        return best_match
    
    # Fix each matched bullet
    for bullet in matched_bullets:
        bullet['job_highlight_text'] = find_best_match(
            bullet.get('job_highlight_text', ''),
            job_description
        )
        
        bullet['resume_highlight_text'] = find_best_match(
            bullet.get('resume_highlight_text', ''),
            resume_text
        )
    
    return matched_bullets

def highlight_with_numbers(text: str, matched_bullets: list, side: str) -> str:
    """
    Highlight text with numbered badges showing which match it corresponds to,
    while preserving line breaks and spacing.
    """
    import re

    # Color mapping by match strength
    colors = {
        'strong': '#d4edda',    # green
        'moderate': '#fff3cd',  # yellow
        'weak': '#f8d7da'       # red (only on job side)
    }

    badge_colors = {
        'strong': '#155724',
        'moderate': '#856404',
        'weak': '#721c24'
    }

    # Wrap text to preserve newlines and bullet formatting
    highlighted = f'<div style="white-space: pre-wrap; line-height: 1.5;">{text}</div>'

    for idx, bullet in enumerate(matched_bullets, 1):
        # Get the appropriate highlight text based on side
        highlight_text = (
            bullet.get('job_highlight_text', '')
            if side == 'job'
            else bullet.get('resume_highlight_text', '')
        )

        # Skip if no text to highlight
        if not highlight_text or highlight_text == 'N/A':
            continue

        strength = bullet.get('match_strength', 'strong')
        bg_color = colors.get(strength, '#d4edda')
        badge_color = badge_colors.get(strength, '#155724')

        # Escape special regex characters
        escaped = re.escape(highlight_text)
        pattern = re.compile(escaped, re.IGNORECASE)

        # Simpler inline highlight — no layout shifting
        replacement = (
            f'<span style="background-color: {bg_color}; padding: 1px 3px; '
            f'border-radius: 3px;">'
            f'<span style="background: white; color: {badge_color}; border-radius: 50%; '
            f'padding: 0 5px; font-weight: bold; font-size: 0.7em; margin-right: 4px;">{idx}</span>'
            f'{highlight_text}</span>'
        )

        highlighted = pattern.sub(replacement, highlighted, count=1)

    return highlighted

# ============================================================================
# MAIN CONTENT
# ============================================================================

st.title("✏️ Resume Tailoring")
st.markdown("Optimize your resume for specific job opportunities")

# ============================================================================
# MATCH SELECTION
# ============================================================================

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
    st.warning("""
    ⚠️ **No detailed analysis available yet**
    
    Run resume matching to generate detailed analysis for your top matches.
    """)
    
    if st.button("➡️ Go to Resume Matching"):
        st.switch_page("pages/4_🎯_Resume_Matching.py")
    
    st.stop()

# Select match to tailor
st.markdown("### 🎯 Select Match to Tailor")

# Get unique resumes
unique_resumes = {}
for m in matches_with_analysis:
    if m[0] not in unique_resumes:
        unique_resumes[m[0]] = m[2]  # resume_id: resume_name

# Check if coming from another page with pre-selected match
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

# Get match data
match = get_match_by_ids(resume_id, job_id)
resume = get_resume_by_id(resume_id)
job = get_job_by_id(job_id)

if not match or not match.get('detailed_analysis'):
    st.error("❌ Detailed analysis not found for this match")
    st.stop()

# Parse detailed analysis
try:
    analysis = json.loads(match['detailed_analysis'])
except:
    st.error("❌ Error parsing analysis data")
    st.stop()

matched_bullets = analysis.get('matched_bullets', []) 

# Validate and fix highlights with fuzzy matching
matched_bullets = validate_and_fix_highlights(
    matched_bullets,
    resume['text'],
    job['description']
)

# Update analysis with corrected bullets
analysis['matched_bullets'] = matched_bullets

# ============================================================================
# HEADER INFO
# ============================================================================
st.markdown("---")
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown(f"### 🎯 {job['title']}")
    st.markdown(f"**🏢 {job['company']}** | 📍 {job['location']}")

with col2:
    score = match['score']
    if score >= 75:
        badge_color = "#28a745"
        emoji = "🟢"
    elif score >= 50:
        badge_color = "#ffc107"
        emoji = "🟡"
    else:
        badge_color = "#dc3545"
        emoji = "🔴"
    
    st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: {badge_color}20; border-radius: 10px;">
            <div style="font-size: 2rem;">{emoji}</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: {badge_color};">{score}/100</div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# SIDE-BY-SIDE COMPARISON
# ============================================================================
st.markdown("---")
st.markdown("## 📊 Side-by-Side Comparison")
st.markdown("*Numbers show which requirements match between job and resume*")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 Your Resume")
    highlighted_resume = highlight_with_numbers(
        resume['text'],
        analysis.get('matched_bullets', []),
        side='resume'
    )
    st.markdown(highlighted_resume, unsafe_allow_html=True)

with col2:
    st.markdown("### 📋 Job Description")
    highlighted_job = highlight_with_numbers(
        job['description'],
        analysis.get('matched_bullets', []),
        side='job'
    )
    st.markdown(
        f"""
        <div style="max-height: 1200px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 8px; background: #fff;">
            {highlighted_job}
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================================
# AI ASSISTANT SECTION
# ============================================================================
st.markdown("---")
st.markdown("### 💬 AI Resume Assistant")


# Initialize chat history in session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'approved_changes' not in st.session_state:
    st.session_state.approved_changes = []

col1, col2 = st.columns([2, 1])

with col1:
    user_input = st.text_area(
        "Ask AI to improve a section of your resume",
        placeholder="Example: 'Improve my AWS Bedrock bullet to emphasize multi-agent orchestration and add metrics'",
        height=100,
        key="ai_input"
    )
    
    if st.button("✨ Get AI Suggestions", type="primary"):
        if user_input:
            with st.spinner("🤔 AI is analyzing and generating suggestions..."):
                try:
                    # Get matched_bullets data
                    matched_skills = [b.get('job_requirement', '') for b in matched_bullets if b.get('match_strength') == 'strong']
                    missing_skills = [b.get('job_requirement', '') for b in matched_bullets if b.get('match_strength') == 'weak']
                    gaps = analysis.get('improvement_suggestions', [])
                    
                    # Build the prompt
                    prompt = f"""You are an expert resume writer helping tailor a resume for a specific job.

**Context:**
- Job Title: {job['title']} at {job['company']}
- Matched Skills: {', '.join(matched_skills[:5]) if matched_skills else 'Not specified'}
- Missing Skills: {', '.join(missing_skills[:5]) if missing_skills else 'None identified'}
- Key Gaps: {'; '.join(gaps[:3]) if gaps else 'None identified'}

**Job Description (first 1500 chars):**
{job['description'][:1500]}

**Current Resume (first 2000 chars):**
{resume['text'][:2000]}

**User's Request:**
{user_input}

**Your Task:**
Generate 3 improved resume bullet points that address the user's request. Each bullet should:
1. Be tailored to the job requirements above
2. Incorporate relevant skills from the "Missing Skills" list when appropriate
3. Use strong action verbs (Architected, Spearheaded, Implemented, etc.)
4. Include quantifiable metrics when possible (%, $, time saved, users served, etc.)
5. Be concise (1-2 lines maximum)
6. Sound natural and authentic to the candidate's experience

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no explanations outside the JSON.

Required JSON format:
{{
  "suggestions": [
    {{
      "version": 1,
      "bullet": "Your first improved bullet point",
      "explanation": "Brief explanation of why this version is strong"
    }},
    {{
      "version": 2,
      "bullet": "Your second alternative bullet point",
      "explanation": "Why this approach works"
    }},
    {{
      "version": 3,
      "bullet": "Your third variation",
      "explanation": "Reasoning for this version"
    }}
  ],
  "original_identified": "The original bullet point from the resume that you're improving, or 'New bullet point' if creating from scratch"
}}"""
                    
                    # Use kernel.invoke_prompt
                    result = asyncio.run(kernel.invoke_prompt(prompt))
                    result_str = str(result).strip()
                    
                    # Clean JSON response
                    if '```json' in result_str:
                        result_str = result_str.split('```json')[1].split('```')[0].strip()
                    elif '```' in result_str:
                        result_str = result_str.split('```')[1].split('```')[0].strip()
                    
                    start_idx = result_str.find('{')
                    end_idx = result_str.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        result_str = result_str[start_idx:end_idx+1]
                    
                    suggestions_data = json.loads(result_str)
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        'user_request': user_input,
                        'suggestions': suggestions_data.get('suggestions', []),
                        'original': suggestions_data.get('original_identified', 'Not specified')
                    })
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error generating suggestions: {str(e)}")
                    import traceback
                    print(f"Debug - Full error:\n{traceback.format_exc()}")
        else:
            st.warning("Please enter a request")

with col2:
    st.markdown("**Quick Actions:**")
    
    missing_skills_list = [b.get('job_requirement', '') for b in matched_bullets if b.get('match_strength') == 'weak']
    gaps = analysis.get('improvement_suggestions', [])
    
    if st.button("🎯 Analyze All Gaps", use_container_width=True):
        if gaps:
            gaps_text = "\n".join([f"- {gap}" for gap in gaps[:5]])
            st.info(f"Try asking:\n\nHelp me address these gaps:\n{gaps_text}")
    
    if st.button("💡 Add Missing Keywords", use_container_width=True):
        if missing_skills_list:
            missing = ", ".join([s[:50] for s in missing_skills_list[:3]])
            st.info(f"Try asking:\n\nHelp me incorporate these requirements: {missing}")
    
    if st.button("📊 View Match Details", use_container_width=True):
        st.switch_page("pages/6_🔬_Match_Analysis.py")

# Display chat history with approval buttons
if st.session_state.chat_history:
    st.markdown("---")
    st.markdown("### 💡 AI Suggestions")
    
    for i, chat in enumerate(reversed(st.session_state.chat_history)):
        with st.expander(f"Request: {chat['user_request'][:60]}...", expanded=(i==0)):
            if chat.get('original') and chat['original'] != 'Not specified':
                st.markdown(f"**Original identified:** {chat['original']}")
            
            st.markdown("**Choose a suggestion to approve:**")
            
            for sug in chat['suggestions']:
                col_a, col_b = st.columns([4, 1])
                
                with col_a:
                    st.markdown(f"""
                        <div style="background: #f8f9fa; padding: 1rem; border-radius: 5px; margin-bottom: 0.5rem;">
                            <strong>Version {sug.get('version', 'N/A')}:</strong><br>
                            • {sug.get('bullet', 'No text')}<br><br>
                            <small style="color: #666;"><em>💡 {sug.get('explanation', '')}</em></small>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col_b:
                    if st.button("✅ Approve", key=f"approve_{i}_{sug.get('version')}", use_container_width=True):
                        st.session_state.approved_changes.append({
                            'original': chat.get('original', 'Not specified'),
                            'new': sug.get('bullet'),
                            'explanation': sug.get('explanation')
                        })
                        st.success("✅ Added!")
                        st.rerun()

# Approved Changes Section
st.markdown("---")
st.markdown("### ✅ Approved Changes")

if len(st.session_state.approved_changes) == 0:
    st.info("No changes approved yet. Use the AI assistant above to generate suggestions, then approve them here.")
else:
    for i, change in enumerate(st.session_state.approved_changes):
        st.markdown(f"""
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #28a745; margin-bottom: 1rem;">
                <strong>Change {i+1}:</strong><br>
                <small style="color: #666;">Original:</small><br>
                {change['original']}<br><br>
                <small style="color: #28a745;">New:</small><br>
                • {change['new']}
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ Remove", key=f"remove_{i}"):
                st.session_state.approved_changes.pop(i)
                st.rerun()
    
    # Generate Report Button
    st.markdown("---")
    if st.button("📋 Generate Change Report", type="primary", use_container_width=True):
        st.session_state.show_report = True
        st.rerun()

# Show Report Modal/Expander
if 'show_report' in st.session_state and st.session_state.show_report:
    st.markdown("---")
    st.markdown("## 📋 Resume Tailoring Report")
    
    from datetime import datetime
    report_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    st.info(f"""
    **Resume:** {resume['name']}  
    **Tailored For:** {job['title']} at {job['company']}  
    **Date Generated:** {report_date}  
    **Total Changes:** {len(st.session_state.approved_changes)}
    """)
    
    st.markdown("---")
    st.markdown("### 📝 Detailed Changes")
    
    for i, change in enumerate(st.session_state.approved_changes, 1):
        with st.expander(f"**Change {i}**", expanded=True):
            st.markdown("**📄 Original:**")
            st.text_area("Original text", value=change.get('original', 'Not specified'), height=60, disabled=True, key=f"orig_{i}", label_visibility="collapsed")
            
            st.markdown("**✨ New Version:**")
            st.success(f"• {change.get('new', '')}")
            
            st.markdown("**💡 Why This Works:**")
            st.info(change.get('explanation', ''))
    
    # Quick Copy Section
    st.markdown("---")
    st.markdown("### 📋 Quick Copy - New Bullets Only")
    st.markdown("*Copy these improved bullets and paste them into your resume:*")
    
    quick_copy_text = ""
    for i, change in enumerate(st.session_state.approved_changes, 1):
        quick_copy_text += f"• {change.get('new', '')}\n\n"
    
    st.code(quick_copy_text, language=None)
    
    # Download Options
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        full_report = f"""RESUME TAILORING REPORT
{'='*60}

Resume: {resume['name']}
Tailored For: {job['title']} at {job['company']}
Date: {report_date}
Total Changes: {len(st.session_state.approved_changes)}

{'='*60}

DETAILED CHANGES:

"""
        for i, change in enumerate(st.session_state.approved_changes, 1):
            full_report += f"""
Change {i}:
-----------
Original:
{change.get('original', 'Not specified')}

New Version:
• {change.get('new', '')}

Why This Works:
{change.get('explanation', '')}

{'='*60}
"""
        
        full_report += f"\n\nQUICK COPY SECTION:\n{'-'*60}\n\n{quick_copy_text}"
        
        st.download_button(
            label="📥 Download Full Report (.txt)",
            data=full_report,
            file_name=f"resume_changes_{resume['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col2:
        st.download_button(
            label="📥 Download New Bullets Only (.txt)",
            data=quick_copy_text,
            file_name=f"new_bullets_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col3:
        if st.button("❌ Close Report", use_container_width=True):
            st.session_state.show_report = False
            st.rerun()

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("### 🎯 Quick Actions")
    
    if st.button("🔬 View Full Analysis", use_container_width=True):
        st.switch_page("pages/6_🔬_Match_Analysis.py")
    
    if st.button("📋 Back to Matches", use_container_width=True):
        st.switch_page("pages/4_🎯_Resume_Matching.py")
    
    st.markdown("---")
    
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Focus on strong and moderate matches
    - Address critical gaps first
    - Use exact keywords from job description
    - Quantify achievements with metrics
    - Tailor your resume for each application
    """)