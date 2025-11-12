# agents/plugins/ResumeTailoringPlugin.py

from semantic_kernel.functions import kernel_function
from typing import Annotated
import json


class ResumeTailoringPlugin:
    
    def __init__(self, kernel, memory=None):
        """
        Args:
            kernel: Your Semantic Kernel instance for AI operations
            memory: ConversationMemory instance for context tracking
        """
        self.kernel = kernel
        self.memory = memory
    
    @kernel_function(
        name="improve_resume_bullet",
        description="Generate improved versions of a resume bullet point tailored to a specific job"
    )
    async def improve_resume_bullet(
        self,
        resume_text: Annotated[str, "The full resume text for context"],
        job_description: Annotated[str, "The job description to tailor towards"],
        job_title: Annotated[str, "The job title"],
        company: Annotated[str, "The company name"],
        user_request: Annotated[str, "The user's specific request for improvement"],
        matched_skills: Annotated[str, "Comma-separated list of skills that match the job"] = "",
        missing_skills: Annotated[str, "Comma-separated list of skills missing from resume"] = "",
        gaps: Annotated[str, "Key gaps identified in the match analysis"] = ""
    ) -> Annotated[str, "JSON string with 3 improved bullet point suggestions"]:
        """
        Takes a user request and generates 3 improved resume bullet point variations
        that are tailored to the specific job requirements.
        
        Returns JSON with format:
        {
            "suggestions": [
                {
                    "version": 1,
                    "bullet": "Improved bullet text",
                    "explanation": "Why this works"
                }
            ],
            "original_identified": "The original bullet being improved"
        }
        """
        
        # ====================================================================
        # STEP 1: Build context-aware prompt
        # ====================================================================
        prompt = f"""You are an expert resume writer helping tailor a resume for a specific job.

**Context:**
- Job Title: {job_title} at {company}
- Matched Skills: {matched_skills if matched_skills else "Not specified"}
- Missing Skills: {missing_skills if missing_skills else "None identified"}
- Key Gaps: {gaps if gaps else "None identified"}

**Job Description (first 1500 chars):**
{job_description[:1500]}

**Current Resume (first 2000 chars):**
{resume_text[:2000]}

**User's Request:**
{user_request}

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
      "explanation": "Brief explanation of why this version is strong (mention which job requirements it addresses)"
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

        try:
            # ================================================================
            # STEP 2: Send prompt to LLM
            # ================================================================
            result = await self.kernel.invoke_prompt(prompt)
            result_str = str(result).strip()
            
            # ================================================================
            # STEP 3: Clean up response - extract JSON
            # ================================================================
            # Remove markdown code blocks if present
            if '```json' in result_str:
                result_str = result_str.split('```json')[1].split('```')[0].strip()
            elif '```' in result_str:
                result_str = result_str.split('```')[1].split('```')[0].strip()
            
            # Extract JSON object
            start_idx = result_str.find('{')
            end_idx = result_str.rfind('}')
            if start_idx != -1 and end_idx != -1:
                result_str = result_str[start_idx:end_idx+1]
            
            # ================================================================
            # STEP 4: Parse and validate JSON
            # ================================================================
            suggestions_data = json.loads(result_str)
            
            # Validate structure
            if 'suggestions' not in suggestions_data:
                raise ValueError("Response missing 'suggestions' field")
            
            # ================================================================
            # NEW: Store suggestions in memory for "apply #2" commands
            # ================================================================
            if self.memory:
                self.memory.set_tailoring_suggestions(suggestions_data)
                self.memory.update_context(last_action="resume_tailoring")
            
            # Return as JSON string
            return json.dumps(suggestions_data, indent=2)
            
        except json.JSONDecodeError as e:
            # ================================================================
            # ERROR HANDLING: JSON parsing failed
            # ================================================================
            print(f"❌ JSON parsing error: {e}")
            print(f"Raw response: {result_str[:500]}")
            
            # Return error response in valid JSON format
            return json.dumps({
                "error": "Failed to parse AI response",
                "suggestions": [],
                "original_identified": "Error"
            })
        
        except Exception as e:
            # ================================================================
            # ERROR HANDLING: Other errors
            # ================================================================
            print(f"❌ Error generating suggestions: {type(e).__name__}: {e}")
            
            return json.dumps({
                "error": str(e),
                "suggestions": [],
                "original_identified": "Error"
            })
    
    @kernel_function(
        name="generate_change_report",
        description="Generate a formatted report of all approved resume changes"
    )
    async def generate_change_report(
        self,
        approved_changes: Annotated[str, "JSON string of approved changes"],
        resume_name: Annotated[str, "Name of the resume"],
        job_title: Annotated[str, "Job title being tailored for"],
        company: Annotated[str, "Company name"]
    ) -> Annotated[str, "Formatted markdown report of all changes"]:
        """
        Takes a list of approved changes and generates a clean, copy-paste ready report.
        """
        
        try:
            changes = json.loads(approved_changes)
            
            if not changes:
                return "No changes have been approved yet."
            
            # Build the report
            report = f"""# Resume Tailoring Report
## {resume_name}
**Tailored for:** {job_title} at {company}
**Date:** {import_datetime()}
**Total Changes:** {len(changes)}

---

"""
            
            for i, change in enumerate(changes, 1):
                report += f"""### Change {i}

**Original:**
{change.get('original', 'Not specified')}

**New Version:**
- {change.get('new', 'No text provided')}

**Why this improves your resume:**
{change.get('explanation', 'No explanation provided')}

---

"""
            
            report += f"""
## Quick Copy Section
Copy each improved bullet below and paste into your resume:

"""
            
            for i, change in enumerate(changes, 1):
                report += f"{i}. {change.get('new', '')}\n\n"
            
            return report
            
        except Exception as e:
            return f"Error generating report: {str(e)}"


def import_datetime():
    """Helper to get current datetime."""
    from datetime import datetime
    return datetime.now().strftime("%B %d, %Y at %I:%M %p")
