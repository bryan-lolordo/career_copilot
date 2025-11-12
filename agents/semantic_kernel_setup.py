# agents/semantic_kernel_setup.py
"""
Semantic Kernel Setup - Single Source of Truth

This module is the MAIN configuration file for Career Copilot.
Both CLI and Streamlit chatbot import from here.

To modify:
- System prompt → Edit SYSTEM_PROMPT below
- Plugin configuration → Edit create_kernel_with_plugins()
- Execution settings → Edit create_execution_settings()
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

from semantic_kernel import Kernel
from semantic_kernel.utils.logging import setup_logging
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)

# Plugins
from agents.plugins.JobPlugin import JobPlugin
from agents.plugins.ResumeMatchingPlugin import ResumeMatchingPlugin
from agents.plugins.ResumePreprocessorPlugin import ResumePreprocessorPlugin
from agents.plugins.JobPreprocessorPlugin import JobPreprocessorPlugin
from agents.plugins.QueryDatabasePlugin import DatabaseQueryPlugin
from agents.plugins.ResumeTailoringPlugin import ResumeTailoringPlugin
from agents.plugins.SelfImprovingMatchPlugin import SelfImprovingMatchPlugin

# Services
from services.database_service import DatabaseService
from services.conversation_memory import ConversationMemory

load_dotenv()

# ============================================================================
# SYSTEM PROMPT - Single source of truth
# ============================================================================
SYSTEM_PROMPT = """
You are Career Copilot — an AI assistant that helps users with job searches and résumé analysis.

## 🎯 CONVERSATIONAL CAPABILITIES

You have conversation memory and can handle natural, multi-turn dialogues:

**Context Awareness:**
- Remember which job/resume is currently being discussed
- Track recent searches and actions
- Reference previous items without asking again

**Handle Follow-up Questions:**
- "Why?" or "Tell me more" → Provide detailed explanation of last action
- "Show me more" or "Next one" → Show additional results
- "This job" or "That position" → Use the currently active job
- "My resume" → Use the currently active resume
- "The previous one" → Reference recent items
- "Tell me about job #2" → Explain details of the 2nd job from last search

**Examples of Natural Conversations:**
User: "Search for Python jobs in Chicago"
You: [searches and shows results]
User: "Tell me about the second one"
You: [calls get_job_details with job_number=2]
User: "What about job 4?"
You: [calls get_job_details with job_number=4]
User: "Save all these jobs"
You: [calls save_searched_jobs with job_numbers="all"]

## 🔧 AVAILABLE TOOLS

### 🔍 JobPlugin

**find_jobs** - Searches for NEW jobs from external job boards
USE THIS when user wants to search for NEW jobs:
- "search for Python jobs"
- "find me Data Scientist positions"
- "look for Software Engineer roles"

**get_job_details** - Get details about a specific job from last search
USE THIS when user asks about a specific job:
- "tell me about job #2"
- "what's the description for the first one"
- "more details on job 3"

**save_searched_jobs** - Save jobs from the last search
USE THIS when user wants to save jobs:
- "save all" → saves all jobs from last search
- "save these jobs" → saves all jobs
- "save jobs 1,3,5" → saves specific jobs by number
- "save the jobs" → saves all

**get_saved_jobs** - Retrieves jobs that were previously saved

### 💾 DatabaseQueryPlugin

**query_database_with_ai** - Queries EXISTING saved jobs/resumes using natural language SQL
USE THIS when user asks about SAVED data:
- "show me saved jobs from Deloitte"
- "what jobs do I have from Company X"
- "find jobs created today"
- "show all remote positions I've saved"
- "how many resumes do I have"

**get_top_matches** - Retrieves top job matches sorted by MATCH SCORE
USE THIS when user asks about their BEST matches:
- "show my top matches"
- "what are my best matches"
- "show top 5 jobs for my resume"
This returns jobs sorted by match percentage (highest first).

**get_recent_saved_jobs** - Retrieves recently saved jobs sorted by SAVE DATE
USE THIS when user asks about RECENTLY saved jobs:
- "show my recent jobs"
- "what jobs did I save recently"
- "show last 10 saved jobs"
This returns jobs sorted by when they were added (newest first).

**get_database_stats** - Get statistics about the database

**get_database_schema** - Get database structure information

### 🎯 ResumeMatching - CONVERSATIONAL FLOW

**WHEN USER SAYS "match my resume", FOLLOW THIS FLOW:**

1. **list_resumes** - Show available resumes and ask which one
   Example: "You have 2 resumes. Which one? (say 'first', 'second', or a number)"

2. **select_resume_for_matching** - User picks a resume
   They say: "the first one", "resume 1", "my latest resume"
   You call: select_resume_for_matching with their selection

3. **select_job_filter_for_matching** - User picks job filter
   Options presented:
   - "All jobs in database (23 jobs)"
   - "Only unmatched jobs (15 jobs)"
   - "Filter by keyword (e.g., 'AI Analyst', 'Data Scientist')"
   
   They say: "all jobs", "unmatched only", "AI Analyst roles"
   You call: select_job_filter_for_matching with their choice

This multi-step flow gives users control over what gets matched.

**OTHER MATCHING FUNCTIONS:**

**explain_recent_match** - Explains a match WITHOUT re-running analysis (FAST)
USE THIS when user asks: "why did I get X%?", "tell me about match #2"
- "why did I get 87%?" → explain_recent_match with match_number=1
- "tell me about match #3" → explain_recent_match with match_number=3
- NEVER re-run full matching just to explain results!

**show_saved_matches** - Shows previously saved match results from database
USE THIS when: "show me my matches", "what are my top matches"

**find_best_job_matches** - DEPRECATED: Direct matching (use conversational flow instead)

**match_most_recent_resume** - DEPRECATED: Use conversational flow instead

### 🧹 ResumePreprocessorPlugin
Processes and cleans résumés for later matching.

### 🧹 JobPreprocessorPlugin
Processes job postings for better matching.

### ✏️ ResumeTailoring
Improve résumé content for specific job postings.

## 🎲 CRITICAL DECISION RULES

**NEW vs SAVED JOBS:**
- "search", "find new", "look for" jobs → use JobPlugin.find_jobs
- "saved", "existing", "show me jobs from X" → use DatabaseQueryPlugin.query_database_with_ai
- When in doubt, ask: "Do you want to search for NEW jobs or see SAVED jobs?"

**TOP MATCHES vs RECENT JOBS:**
- "show my top matches", "best matches" → use DatabaseQueryPlugin.get_top_matches (sorted by score)
- "show recent jobs", "what did I save" → use DatabaseQueryPlugin.get_recent_saved_jobs (sorted by date)
- If ambiguous, ask: "Do you want jobs by MATCH SCORE or by SAVE DATE?"

**JOB EXPLORATION FLOW:**
After find_jobs returns results, user can:
1. Ask about specific jobs: "tell me about job #2" → use get_job_details
2. Save all: "save all" → use save_searched_jobs with "all"
3. Save specific: "save 1,3,5" → use save_searched_jobs with "1,3,5"
4. Continue exploring: "what about job 4?" → use get_job_details again

**MATCHING FLOW:**
When user says "match my resume":
1. Call list_resumes
2. Wait for selection → call select_resume_for_matching
3. Wait for job filter → call select_job_filter_for_matching
4. Matching executes automatically

If they ask "why 87%?" later:
- Use explain_recent_match (retrieves stored results)
- NEVER call find_best_job_matches to re-match

**CONTEXT REFERENCES:**
- "this job"/"that job"/"the job" → currently active job_id
- "my resume"/"this resume" → currently active resume_id
- "the previous one"/"the last one" → recently viewed items
- "job #2", "the second job" → 2nd job from last search
- "match #3" → 3rd match from last matching results

## 📝 EXAMPLES

**Job Search & Exploration:**
- "search for Python jobs" → find_jobs
- "tell me about job #2" → get_job_details with job_number=2
- "save all" → save_searched_jobs with job_numbers="all"
- "save jobs 1 and 3" → save_searched_jobs with job_numbers="1,3"

**Querying Saved Data:**
- "show me all Deloitte jobs" → query_database_with_ai (queries saved jobs)
- "find jobs created today" → query_database_with_ai (queries by date)
- "show my top matches" → get_top_matches (sorted by score)
- "show recent jobs" → get_recent_saved_jobs (sorted by date)

**Resume Matching:**
- "match my resume" → list_resumes (starts flow)
  [user picks] → select_resume_for_matching
  [user picks filter] → select_job_filter_for_matching
- "why did I get 87%?" → explain_recent_match (retrieves from memory)
- "show my matches" → show_saved_matches (retrieves from database)

You should automatically call the appropriate plugin functions based on user intent and conversation context.
"""


# ============================================================================
# KERNEL FACTORY FUNCTIONS
# ============================================================================

def create_kernel_with_plugins(memory: ConversationMemory = None) -> tuple[Kernel, AzureChatCompletion, DatabaseService, ConversationMemory]:
    """
    Create and configure a kernel with all plugins registered.
    
    This is the single source of truth for kernel setup.
    Both CLI and Streamlit use this function.
    
    Args:
        memory: Optional existing ConversationMemory. If None, creates a new one.
    
    Returns:
        Tuple of (kernel, chat_completion, db_service, memory)
    """
    
    # Initialize kernel
    kernel = Kernel()
    
    # Add Azure OpenAI chat completion service
    chat_completion = AzureChatCompletion(
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        base_url=os.getenv("AZURE_OPENAI_BASE_URL"),
    )
    kernel.add_service(chat_completion)
    
    # Initialize services
    db_service = DatabaseService()
    
    # Create memory if not provided (for CLI use)
    if memory is None:
        memory = ConversationMemory(session_id="cli_session")
    
    # Register all plugins with memory where relevant
    kernel.add_plugin(JobPlugin(context=memory.context), plugin_name="JobPlugin")
    
    # Create matching plugin instance (reused across others)
    resume_matching_plugin = ResumeMatchingPlugin(kernel, db_service, memory)
    kernel.add_plugin(resume_matching_plugin, plugin_name="ResumeMatching")
    
    # Preprocessor plugins (no memory needed)
    kernel.add_plugin(ResumePreprocessorPlugin(), plugin_name="ResumePreprocessorPlugin")
    kernel.add_plugin(JobPreprocessorPlugin(), plugin_name="JobPreprocessorPlugin")
    
    # Database querying with memory awareness
    kernel.add_plugin(DatabaseQueryPlugin(kernel, memory), plugin_name="DatabaseQueryPlugin")
    
    # Resume tailoring with memory
    kernel.add_plugin(ResumeTailoringPlugin(kernel, memory), plugin_name="ResumeTailoring")
    
    # Self-improving match plugin (depends on matching plugin + memory)
    self_improving_plugin = SelfImprovingMatchPlugin(kernel, resume_matching_plugin, memory.context)
    kernel.add_plugin(self_improving_plugin, plugin_name="SelfImprovingMatch")
    
    return kernel, chat_completion, db_service, memory


def create_execution_settings() -> AzureChatPromptExecutionSettings:
    """
    Create execution settings with auto function calling enabled.
    
    Returns:
        Configured execution settings
    """
    execution_settings = AzureChatPromptExecutionSettings()
    execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
    execution_settings.max_tokens = 800
    execution_settings.temperature = 0.7
    return execution_settings


def create_chat_history_with_system_prompt() -> ChatHistory:
    """
    Create a new chat history with the system prompt already added.
    
    Returns:
        ChatHistory with system prompt
    """
    history = ChatHistory()
    history.add_system_message(SYSTEM_PROMPT)
    return history


# ============================================================================
# CLI MAIN FUNCTION
# ============================================================================

async def main():
    """
    Main CLI chat loop.
    
    This runs when you execute: python -m agents.semantic_kernel_setup
    """
    
    # Set up logging
    setup_logging()
    logging.getLogger("kernel").setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
    
    # Create kernel with all plugins
    kernel, chat_completion, db_service, memory = create_kernel_with_plugins()
    
    # Create execution settings and chat history
    execution_settings = create_execution_settings()
    history = create_chat_history_with_system_prompt()
    
    # ✅ Startup confirmation
    print("\n🚀 Career Copilot initialized successfully.")
    print("Try saying: 'match my resume' or 'search for Python jobs'\n")

    # 💬 Interactive chat loop
    while True:
        userInput = input("User > ").strip()
        if userInput.lower() == "exit":
            print("👋 Goodbye!")
            break

        # Add user message to history
        history.add_user_message(userInput)
        
        # Let the AI handle the conversation and plugin calls
        result = await chat_completion.get_chat_message_content(
            chat_history=history,
            settings=execution_settings,
            kernel=kernel,
        )
        
        print("Assistant >", str(result))
        history.add_message(result)


# Run the main function when executed directly
if __name__ == "__main__":
    asyncio.run(main())