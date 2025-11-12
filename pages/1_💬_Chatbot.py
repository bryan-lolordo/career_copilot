"""
Enhanced AI Chatbot Page with Conversation Memory
"""

import streamlit as st
import sys
from pathlib import Path
import json
import re
from services.db import save_jobs

# Setup path to import from parent directory
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.enhanced_chatbot import EnhancedCareerCopilotChatbot

# Page config
st.set_page_config(
    page_title="AI Chatbot | Career Copilot",
    page_icon="💬",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        animation: fadeIn 0.3s;
    }
    .user-message {
        background: #e3f2fd;
        border-left: 4px solid #2196F3;
    }
    .assistant-message {
        background: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .context-card {
        background: #fff3e0;
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 1rem;
        border-left: 4px solid #ff9800;
    }
    .plugin-badge {
        background: #4caf50;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        display: inline-block;
        margin-top: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chatbot" not in st.session_state:
    # Use unique session ID per Streamlit session
    import uuid
    session_id = str(uuid.uuid4())
    st.session_state.chatbot = EnhancedCareerCopilotChatbot(session_id=session_id)

if "show_context" not in st.session_state:
    st.session_state.show_context = True

if "pending_job_save" not in st.session_state:
    st.session_state.pending_job_save = None

if "show_job_selector" not in st.session_state:
    st.session_state.show_job_selector = False

# Header with context toggle
col1, col2 = st.columns([4, 1])
with col1:
    st.title("💬 AI Career Assistant")
    st.markdown("Have a natural conversation with your AI career assistant")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🧠 " + ("Hide" if st.session_state.show_context else "Show") + " Context"):
        st.session_state.show_context = not st.session_state.show_context
        st.rerun()

# Sidebar with context and suggestions
with st.sidebar:
    st.markdown("### 🧠 Conversation Context")
    
    if st.session_state.show_context:
        context = st.session_state.chatbot.get_conversation_context()
        
        # Display current focus
        if context['current_resume_id']:
            st.info(f"📄 **Discussing Resume:** ID {context['current_resume_id']}")
        
        if context['current_job_id']:
            st.success(f"💼 **Discussing Job:** ID {context['current_job_id']}")
        
        if context['recent_jobs']:
            with st.expander("📋 Recently Viewed Jobs", expanded=False):
                for job_id in context['recent_jobs']:
                    st.write(f"• Job ID: {job_id}")
        
        if context['preferred_locations']:
            with st.expander("📍 Preferred Locations", expanded=False):
                for loc in context['preferred_locations']:
                    st.write(f"• {loc}")
        
        # Display intent
        st.caption(f"**Current Intent:** {context['intent']}")
        st.caption(f"**Last Action:** {context['last_action'] or 'None'}")
    
    st.markdown("---")
    
    st.markdown("### 💡 Try asking:")
    
    suggestions = [
        "Search for data science jobs in San Francisco",
        "Show me my saved jobs",
        "Match my resume against all saved jobs",
        "What companies have I saved jobs from?",
        "Why did I get that score?",
        "Show me more jobs",
        "Tell me about this job",
        "How can I improve my resume for this role?"
    ]
    
    for suggestion in suggestions:
        if st.button(suggestion, key=f"suggest_{suggestion}", use_container_width=True):
            st.session_state.messages.append({
                "role": "user", 
                "content": suggestion,
                "plugin": None
            })
            
            with st.spinner("🤔 Thinking..."):
                try:
                    result = st.session_state.chatbot.chat_detailed(suggestion)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result['response'],
                        "plugin": result.get('plugin_used'),
                        "intent": result.get('intent')
                    })
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "plugin": None
                    })
            st.rerun()
    
    st.markdown("---")
    
    # Action buttons
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chatbot.reset()
            st.rerun()
    
    with col_b:
        if st.button("📊 Stats", use_container_width=True):
            context = st.session_state.chatbot.get_conversation_context()
            st.info(context['summary'])
    
    st.markdown("---")
    st.markdown("""
    ### 🎯 What I Can Do
    - 🔍 Search for jobs
    - 💾 Manage saved jobs
    - 🎯 Match resumes to jobs
    - 📊 Query your data
    - ✏️ Tailor resumes
    - 💬 Answer follow-up questions
    """)

# Main chat area
chat_container = st.container()

with chat_container:
    # Display chat history
    for idx, message in enumerate(st.session_state.messages):
        css_class = "user-message" if message["role"] == "user" else "assistant-message"
        icon = "🧑" if message["role"] == "user" else "🤖"
        
        st.markdown(f"""
            <div class="chat-message {css_class}">
                <strong>{icon} {message["role"].title()}</strong><br>
                {message["content"]}
            </div>
        """, unsafe_allow_html=True)
        
        # Show action buttons for the most recent assistant message with pending actions
        if (message["role"] == "assistant" and 
            idx == len(st.session_state.messages) - 1 and
            st.session_state.pending_job_save is not None):
            
            st.markdown("---")
            st.markdown("**💾 Quick Actions:**")
            
            job_data = st.session_state.pending_job_save
            num_jobs = len(job_data.get("jobs", []))
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button(f"💾 Save All ({num_jobs})", key="save_all_jobs"):
                    try:
                        save_jobs(
                            job_data["jobs"],
                            job_data.get("query", "search"),
                            job_data.get("location", "Unknown")
                        )
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"✅ Saved all {num_jobs} jobs!"
                        })
                        st.session_state.pending_job_save = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving jobs: {str(e)}")
            
            with col2:
                if st.button("🎯 Select Specific Jobs", key="select_jobs_btn"):
                    st.session_state.show_job_selector = True
                    st.rerun()
            
            with col3:
                if st.button("❌ Skip Saving", key="skip_save"):
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "❌ Skipped saving jobs."
                    })
                    st.session_state.pending_job_save = None
                    st.session_state.show_job_selector = False
                    st.rerun()
            
            with col4:
                if st.button("🔄 Match to Resume", key="match_these_jobs"):
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "match my resume"
                    })
                    st.rerun()
            
            # Job selector interface
            if st.session_state.show_job_selector:
                st.markdown("**Select which jobs to save:**")
                
                job_options = []
                for i, job in enumerate(job_data.get("jobs", []), 1):
                    job_options.append(f"{i}. {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
                
                selected = st.multiselect(
                    "Choose jobs:",
                    options=range(len(job_options)),
                    format_func=lambda x: job_options[x],
                    key="job_multiselect"
                )
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 Save Selected", key="save_selected_confirm"):
                        if selected:
                            selected_jobs = [job_data["jobs"][i] for i in selected]
                            try:
                                save_jobs(
                                    selected_jobs,
                                    job_data.get("query", "search"),
                                    job_data.get("location", "Unknown")
                                )
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": f"✅ Saved {len(selected)} selected jobs: #{', #'.join(str(i+1) for i in selected)}"
                                })
                                st.session_state.pending_job_save = None
                                st.session_state.show_job_selector = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving jobs: {str(e)}")
                        else:
                            st.warning("Please select at least one job")
                
                with col_b:
                    if st.button("Cancel", key="cancel_selection"):
                        st.session_state.show_job_selector = False
                        st.rerun()

# Chat input
if prompt := st.chat_input("Ask me anything about your job search..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get AI response
    with st.spinner("🤔 Thinking..."):
        try:
            response = st.session_state.chatbot.chat(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Check if response contains job search results
            if "Found" in response and "jobs" in response.lower():
                try:
                    # Extract JSON from response
                    if "{" in response and "}" in response:
                        json_start = response.find("{")
                        json_end = response.rfind("}") + 1
                        json_str = response[json_start:json_end]
                        job_data = json.loads(json_str)
                        
                        if "jobs" in job_data and len(job_data["jobs"]) > 0:
                            st.session_state.pending_job_save = job_data
                            st.session_state.show_job_selector = False
                except Exception as e:
                    # If JSON parsing fails, no action buttons
                    pass
                    
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    st.rerun()

# Show welcome message if no chat history
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="context-card">
        <h3>👋 Welcome to Your AI Career Assistant!</h3>
        <p>I can help you with:</p>
        <ul>
            <li><strong>🔍 Job Search:</strong> Find and save jobs from across the web</li>
            <li><strong>🎯 Resume Matching:</strong> See how well your resume matches opportunities</li>
            <li><strong>📊 Data Analysis:</strong> Query your saved jobs and resumes</li>
            <li><strong>✏️ Resume Tailoring:</strong> Improve your resume for specific roles</li>
            <li><strong>💬 Follow-ups:</strong> Ask "why?", "tell me more", or reference "this job"</li>
        </ul>
        <p><strong>Try one of the suggestions in the sidebar, or just ask me anything!</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show conversation context capabilities
    st.markdown("### 🧠 Conversation Memory Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🎯 Context Awareness**
        - Remembers what job/resume you're discussing
        - Tracks recent searches
        - Learns your preferences
        """)
    
    with col2:
        st.markdown("""
        **💬 Natural Follow-ups**
        - "Why did I get that score?"
        - "Tell me more about this job"
        - "Show me the next one"
        """)
    
    with col3:
        st.markdown("""
        **🔄 Smart References**
        - "this job" → current job
        - "my resume" → active resume
        - "the previous one" → recent item
        """)