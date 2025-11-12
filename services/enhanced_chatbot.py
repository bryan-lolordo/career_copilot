# services/enhanced_chatbot.py
"""
Enhanced chatbot service that wraps your existing chatbot with conversation memory.
This adds multi-turn conversation awareness without breaking existing functionality.
"""

import asyncio
from typing import Dict, Any, Optional
from services.chatbot import chat_with_kernel, get_chat_history, reset_chat_history
from services.conversation_memory import get_memory_manager, ConversationIntent


class EnhancedCareerCopilotChatbot:
    """
    Enhanced wrapper around your existing chatbot that adds:
    - Conversation memory and context tracking
    - Intent detection
    - Better follow-up question handling
    - Action tracking for UI integration
    """
    
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.memory_manager = get_memory_manager()
        self.memory = self.memory_manager.get_session(session_id)
    
    async def chat_async(self, message: str) -> Dict[str, Any]:
        """
        Enhanced chat method that wraps your existing chat_with_kernel.
        
        Returns:
            Dict with:
            - response: The assistant's text response
            - plugin_used: Which plugin was called
            - context: Current conversation context
            - actions: Any UI actions to perform
            - intent: Detected user intent
        """
        
        # Detect intent before processing
        intent = self.memory.detect_intent(message)
        self.memory.update_context(intent=intent)
        
        # Enhance message with context if needed
        enhanced_message = self._enhance_message_with_context(message)
        
        # Call your existing chatbot
        response, plugin_used = await chat_with_kernel(enhanced_message)
        
        # Extract and update context from the interaction
        self._update_context_from_response(message, response, plugin_used)
        
        # Record this conversation turn
        self.memory.add_turn(
            user_message=message,
            assistant_message=response,
            plugins_used=[plugin_used] if plugin_used else [],
            intent=intent
        )
        
        # Get any pending UI actions
        actions = self.memory.get_pending_actions()
        
        return {
            'response': response,
            'plugin_used': plugin_used,
            'context': self.memory.get_context_for_prompt(),
            'actions': actions,
            'intent': intent.value,
            'conversation_summary': self.memory.get_conversation_summary()
        }
    
    def _enhance_message_with_context(self, message: str) -> str:
        """
        Enhance user message with context for better understanding.
        
        Handles references like:
        - "this job" -> references current_job_id
        - "the previous one" -> references recent items
        - "why?" -> asks for explanation of last action
        """
        message_lower = message.lower().strip()
        
        # Handle "why?" or "tell me more" questions
        if message_lower in ["why?", "why", "tell me more", "explain"]:
            if self.memory.context.last_action:
                return f"Why did {self.memory.context.last_action} happen? Please explain in detail."
        
        # Handle "this job" / "that job" references
        if any(phrase in message_lower for phrase in ["this job", "that job", "the job"]):
            if self.memory.context.current_job_id:
                message = message.replace("this job", f"job ID {self.memory.context.current_job_id}")
                message = message.replace("that job", f"job ID {self.memory.context.current_job_id}")
                message = message.replace("the job", f"job ID {self.memory.context.current_job_id}")
        
        # Handle "my resume" / "this resume" references
        if any(phrase in message_lower for phrase in ["my resume", "this resume", "the resume"]):
            if self.memory.context.current_resume_id:
                message = message.replace("my resume", f"resume ID {self.memory.context.current_resume_id}")
                message = message.replace("this resume", f"resume ID {self.memory.context.current_resume_id}")
                message = message.replace("the resume", f"resume ID {self.memory.context.current_resume_id}")
        
        # Handle "show me more" / "next one" requests
        if any(phrase in message_lower for phrase in ["show me more", "next one", "more results"]):
            recent_jobs = self.memory.get_recent_jobs(limit=5)
            if recent_jobs:
                return f"Show me more results. I recently viewed job IDs: {', '.join(map(str, recent_jobs))}"
        
        return message
    
    def _update_context_from_response(self, user_message: str, response: str, plugin_used: Optional[str]):
        """
        Extract context from the conversation to update memory.
        """
        message_lower = user_message.lower()
        response_lower = response.lower()
        
        # Track what action was performed
        if plugin_used:
            self.memory.context.last_action = plugin_used
        
        # Detect if we're discussing specific jobs
        if "job id" in response_lower or "job #" in response_lower:
            # Try to extract job IDs from response
            import re
            job_ids = re.findall(r'job (?:id|#)\s*(\d+)', response_lower)
            for job_id in job_ids:
                self.memory.set_current_focus(job_id=int(job_id))
        
        # Learn location preferences
        if "in" in message_lower and ("search" in message_lower or "find" in message_lower):
            # Extract location from phrases like "in Chicago" or "in New York"
            import re
            location_match = re.search(r'\bin\s+([A-Z][a-zA-Z\s,]+?)(?:\s|$|,)', user_message)
            if location_match:
                location = location_match.group(1).strip()
                self.memory.learn_preference("location", location)
        
        # Track match results
        if "match" in plugin_used.lower() if plugin_used else False:
            if "%" in response or "score" in response_lower:
                # Store that we ran a match
                self.memory.context.last_action = "resume_matching"
    
    def chat(self, message: str) -> str:
        """
        Synchronous wrapper for Streamlit compatibility.
        Returns just the response text.
        """
        result = asyncio.run(self.chat_async(message))
        return result['response']
    
    def chat_detailed(self, message: str) -> Dict[str, Any]:
        """
        Synchronous wrapper that returns full details.
        Use this for the enhanced Streamlit UI.
        """
        return asyncio.run(self.chat_async(message))
    
    def get_conversation_context(self) -> Dict[str, Any]:
        """Get current conversation context for display in UI."""
        return {
            'current_resume_id': self.memory.context.current_resume_id,
            'current_job_id': self.memory.context.current_job_id,
            'recent_jobs': self.memory.get_recent_jobs(limit=5),
            'last_action': self.memory.context.last_action,
            'intent': self.memory.context.intent.value,
            'summary': self.memory.get_conversation_summary(),
            'preferred_locations': self.memory.context.preferred_locations,
        }
    
    def reset(self):
        """Reset both the chatbot and conversation memory."""
        reset_chat_history()
        self.memory_manager.clear_session(self.session_id)
        self.memory = self.memory_manager.get_session(self.session_id)
    
    def set_resume_focus(self, resume_id: int):
        """Manually set which resume is being discussed."""
        self.memory.set_current_focus(resume_id=resume_id)
    
    def set_job_focus(self, job_id: int):
        """Manually set which job is being discussed."""
        self.memory.set_current_focus(job_id=job_id)