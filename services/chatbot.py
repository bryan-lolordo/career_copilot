# services/chatbot.py
"""
Streamlit Chatbot Service

This module provides the chatbot interface for Streamlit.
All kernel setup is imported from agents.semantic_kernel_setup (the main source of truth).
"""

import asyncio
import json
import re
import time
from agents.semantic_kernel_setup import (
    create_kernel_with_plugins,
    create_execution_settings,
    create_chat_history_with_system_prompt,
    SYSTEM_PROMPT
)
from services.conversation_memory import ConversationMemory, get_memory_manager

# ============================================================================
# GLOBAL KERNEL INITIALIZATION
# ============================================================================
# Initialize globally so it persists between Streamlit calls
# This avoids recreating the kernel on every message

# Get or create memory for this session
memory_manager = get_memory_manager()
memory = memory_manager.get_session("streamlit_default")

kernel, chat_completion, db_service, memory = create_kernel_with_plugins(memory)
execution_settings = create_execution_settings()
history = create_chat_history_with_system_prompt()

# Quick access to context for backwards compatibility
context = memory.context


# ============================================================================
# MAIN CHAT FUNCTION
# ============================================================================
async def chat_with_kernel(message: str) -> tuple[str, str]:
    """
    Send a message to the chatbot and get a reply.

    Args:
        message: User's message

    Returns:
        Tuple of (response_text, plugin_used)
        - response_text: The chatbot's reply
        - plugin_used: Name of plugin that was called (or None)
    """
    start_time = time.time()

    # Add user message to chat history
    history.add_user_message(message)
    print(f"⏱️  [TIMER] Message added: {time.time() - start_time:.2f}s")


    # Send request to Semantic Kernel / Azure OpenAI
    response = await chat_completion.get_chat_message_content(
        chat_history=history,
        settings=execution_settings,
        kernel=kernel,
    )
    print(f"⏱️  [TIMER] LLM response received: {time.time() - start_time:.2f}s")

    # Detect which plugin was used (if any)
    plugin_used = None
    if hasattr(response, "metadata") and response.metadata:
        if "function_call" in response.metadata:
            plugin_used = response.metadata["function_call"].get("name")

    if not plugin_used and hasattr(response, "items"):
        for item in getattr(response, "items", []):
            if hasattr(item, "function_call") and item.function_call:
                plugin_used = item.function_call.name
                break

    # Get response text
    response_text = str(response)
    
    # Clean up any stray HTML tags from LLM response
    response_text = re.sub(r'</?div[^>]*>', '', response_text)
    response_text = re.sub(r'</?p[^>]*>', '', response_text)

    # Debug log
    print("─" * 60)
    print(f"[Context] Resume={context.active_resume_id} | Job={context.active_job_id} | LastAction={context.last_action}")
    print(f"[Plugin Used] {plugin_used or 'None'}")
    print("─" * 60)

    # Add assistant response to history
    history.add_message(response)
    
    return response_text, plugin_used


# ============================================================================
# HELPER: Reset conversation history
# ============================================================================
def reset_chat_history():
    """
    Reset the conversation history and memory.
    Useful for starting a fresh conversation in Streamlit.
    """
    global history, memory
    history = create_chat_history_with_system_prompt()
    # Reset memory context
    memory.context.awaiting_confirmation = False
    memory.context.pending_action = None
    memory.context.last_action = None
    memory.context.last_searched_jobs = None
    memory.context.available_resumes = None
    memory.context.selected_resume_for_matching = None
    memory.context.awaiting_resume_selection = False
    memory.context.awaiting_job_filter_selection = False


# ============================================================================
# HELPER: Get conversation history
# ============================================================================
def get_chat_history() -> list[dict]:
    """
    Get the current conversation history.
    
    Returns:
        List of message dictionaries with 'role' and 'content'
    """
    messages = []
    for msg in history.messages:
        messages.append({
            "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
            "content": str(msg.content)
        })
    return messages


class CareerCopilotChatbot:
    """Wrapper class for Streamlit compatibility"""
    
    async def chat_async(self, message: str) -> str:
        response, _ = await chat_with_kernel(message)
        return response
    
    def chat(self, message: str) -> str:
        return asyncio.run(self.chat_async(message))
    
    def reset(self):
        reset_chat_history()


# ============================================================================
# HELPER: Get kernel and database service for other pages
# ============================================================================
def get_kernel():
    """Get the global kernel instance for reuse across pages."""
    return kernel

def get_database_service():
    """Get the database service instance for reuse across pages."""
    return db_service