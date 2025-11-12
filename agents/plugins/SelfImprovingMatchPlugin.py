"""
Self-Improving Match Plugin - AI reviews and improves its own matching
"""

from semantic_kernel.functions import kernel_function
from typing import Annotated
import json


class SelfImprovingMatchPlugin:
    
    def __init__(self, kernel, matching_plugin, context=None):
        """
        Args:
            kernel: Semantic Kernel instance
            matching_plugin: The ResumeMatchingPlugin instance
            context: Shared ConversationContext instance for memory and confirmation
        """
        self.kernel = kernel
        self.matching_plugin = matching_plugin
        self.context = context

    @kernel_function(
        name="self_improve_single_match",
        description="Self-improve matching for a single job-resume pair"
    )
    async def self_improve_single_match(
        self,
        resume_id: Annotated[str, "Resume ID"],
        job_id: Annotated[str, "Job ID"],
        max_iterations: Annotated[int, "Maximum refinement iterations"] = 2
    ) -> Annotated[str, "JSON with final match and improvement log"]:
        """
        Self-improve a single job match with AI quality control.
        
        Process:
        1. Deep analyze this specific job-resume pair
        2. AI critic reviews the analysis
        3. If issues found, refine and re-analyze
        4. Return updated match
        """
        
        print(f"\n🤖 Self-Improving Single Match: Resume {resume_id} + Job {job_id}")
        
        from services.database_service import DatabaseService
        db_service = DatabaseService()
        
        # Get resume and job data
        resume = db_service.get_resume_by_id(int(resume_id))
        job = db_service.get_job_by_id(int(job_id))
        
        if not resume or not job:
            return json.dumps({'error': 'Resume or job not found'})
        
        iteration = 0
        refinement_log = []
        current_analysis = None
        best_analysis = None  # Track best analysis
        best_score = 0  # Track best score
        quality_score = 0
        refinement_guidance = []  # Accumulate guidance across iterations
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n📊 === Iteration {iteration}/{max_iterations} ===")
            
            # ================================================================
            # STEP 1: Deep analyze with accumulated refinement guidance
            # ================================================================
            print(f"   ▶️ Analyzing match...")
            
            # Build guidance context for this iteration
            if refinement_guidance:
                guidance_text = "\n".join([
                    f"- {item}" for item in refinement_guidance
                ])
                print(f"   📝 Applying {len(refinement_guidance)} refinements...")
            else:
                guidance_text = ""
            
            analysis = await self._deep_analyze_with_guidance(
                resume_text=resume['text'],
                job=job,
                guidance=guidance_text,
                previous_analysis=current_analysis if iteration > 1 else None  # Use refinement mode on iteration 2+
            )
            
            # Only fallback if analysis completely failed (score 0 and no data)
            # If it has a score or good data, keep it even if some fields are missing
            if (analysis['score'] == 0 and 
                not analysis.get('matched_skills') and 
                not analysis.get('_parsing_failed') and
                current_analysis and 
                current_analysis['score'] > 0):
                print(f"   ⚠️ Analysis completely failed, keeping previous analysis")
                analysis = current_analysis
            elif analysis.get('_parsing_failed'):
                print(f"   ⚠️ Partial parsing - extracted score: {analysis['score']}")
            
            current_analysis = analysis
            
            print(f"   ✅ Score: {analysis['score']}/100")
            
            # ================================================================
            # Track best analysis so far
            # ================================================================
            if analysis['score'] > best_score:
                best_analysis = current_analysis.copy()
                best_score = analysis['score']
                print(f"   🏆 New best score: {best_score}/100")
            
            # ================================================================
            # STEP 2: AI Critic reviews this single match
            # ================================================================
            print(f"   🔍 AI Critic reviewing...")
            
            critique = await self._critique_single_match(analysis, resume, job)
            
            try:
                critique_data = json.loads(critique)
            except:
                print("   ⚠️ Critique parsing failed")
                break
            
            quality_score = critique_data.get('overall_quality', 0)
            issues = critique_data.get('issues', [])
            
            print(f"   📊 Quality: {quality_score}/100")
            print(f"   ⚠️ Issues: {len(issues)}")
            
            # Log iteration
            iteration_log = {
                'iteration': iteration,
                'score': analysis['score'],
                'quality_score': quality_score,
                'issues': issues,
                'strengths': critique_data.get('strengths', []),
                'weaknesses': critique_data.get('weaknesses', [])
            }
            
            # Add refinement stats if available
            if '_refinement_stats' in analysis:
                iteration_log['refinement_stats'] = analysis['_refinement_stats']
            
            refinement_log.append(iteration_log)
            
            # ================================================================
            # STEP 3: Check if acceptable
            # ================================================================
            if quality_score >= 85 and len(issues) == 0:
                print(f"   ✅ Quality acceptable!")
                break
            
            if iteration >= max_iterations:
                print(f"   ⏰ Max iterations reached")
                break
            
            # ================================================================
            # STEP 4: Generate refinements for NEXT iteration
            # ================================================================
            print(f"   🔧 Generating refinements...")
            
            refinements = await self._generate_refinements_for_single_match(
                critique_data,
                analysis,
                resume,
                job
            )
            
            try:
                refinements_data = json.loads(refinements)
                adjustments = refinements_data.get('adjustments', [])
                focus_areas = refinements_data.get('focus_areas', [])
                
                # Add to accumulated guidance
                for adj in adjustments:
                    guidance_item = f"{adj.get('area', 'General')}: {adj.get('change', 'N/A')}"
                    refinement_guidance.append(guidance_item)
                
                for focus in focus_areas:
                    refinement_guidance.append(f"Focus: {focus}")
                
                print(f"   📝 Added {len(adjustments)} adjustments for next iteration")
                
                refinement_log[-1]['refinements'] = adjustments
                
            except Exception as e:
                print(f"   ⚠️ Refinement parsing failed: {e}")
                break
    
        # ================================================================
        # FINAL: Save updated match using BEST analysis
        # ================================================================
        print(f"\n💾 Saving updated match...")
        print(f"   🏆 Using best analysis with score: {best_score}/100")
        
        # Use best_analysis if we have one, otherwise fall back to current_analysis
        final_analysis = best_analysis if best_analysis else current_analysis
        
        # Build detailed_analysis dict for saving - FIXED: Added confidence fields
        detailed_analysis_dict = {
            'score_breakdown': final_analysis.get('score_breakdown', {}),
            'matched_skills': final_analysis.get('matched_skills', []),
            'missing_skills': final_analysis.get('missing_skills', []),
            'matched_bullets': final_analysis.get('matched_bullets', []),
            'strengths': final_analysis.get('strengths', []),
            'gaps': final_analysis.get('gaps', []),
            'improvement_suggestions': final_analysis.get('improvement_suggestions', []),
            'summary': final_analysis.get('summary', final_analysis.get('reason', '')),
            'confidence': final_analysis.get('confidence', 0.85),  # Default to 0.85 for improved matches
            'confidence_reasoning': final_analysis.get('confidence_reasoning', f'Analysis refined through {iteration} iteration(s) of self-improvement with quality score: {quality_score}/100'),
            'uncertainty_factors': final_analysis.get('uncertainty_factors', [])
        }
        
        db_service.save_match(
            resume_id=int(resume_id),
            job_id=int(job_id),
            score=final_analysis['score'],
            reason=final_analysis.get('reason', 'Improved analysis'),
            detailed_analysis=json.dumps(detailed_analysis_dict)
        )
        
        return json.dumps({
            'success': True,
            'iterations': iteration,
            'final_score': final_analysis['score'],
            'final_quality': quality_score,
            'refinement_log': refinement_log,
            'summary': f"Completed {iteration} iterations. Best score: {final_analysis['score']}/100 (Quality: {quality_score}/100)"
        }, indent=2)

    # ====================================================================
    # NEW: Deep analyze WITH guidance from previous iterations
    # ====================================================================
    async def _deep_analyze_with_guidance(self, resume_text: str, job: dict, guidance: str, previous_analysis: dict = None) -> dict:
        """
        Deep analyze OR refine existing analysis with guidance applied.
        If previous_analysis provided, refine it. Otherwise, analyze from scratch.
        """
        
        # If we have a previous analysis, use REFINEMENT mode
        if previous_analysis and previous_analysis.get('matched_bullets'):
            return await self._refine_existing_analysis(
                resume_text=resume_text,
                job=job,
                previous_analysis=previous_analysis,
                guidance=guidance
            )
        
        # Otherwise, full analysis mode
        guidance_section = ""
        if guidance:
            guidance_section = f"""

🔧 IMPORTANT - Apply these refinements to your analysis:
{guidance}
"""
        
        prompt = f"""You are an expert resume matcher. Perform semantic analysis to find connections between job requirements and resume content.{guidance_section}

🎨 CRITICAL INSTRUCTIONS FOR HIGHLIGHT TEXT:

YOU MUST COPY EXACT TEXT FROM THE DOCUMENTS. DO NOT WRITE SUMMARIES.

RULE: job_requirement and job_highlight_text must be IDENTICAL.
RULE: resume_bullet and resume_highlight_text must be IDENTICAL.

STEP-BY-STEP PROCESS:
1. Read the job description below.
2. Find a COMPLETE sentence that states a requirement.
3. Copy that ENTIRE sentence word-for-word into BOTH fields (job_requirement and job_highlight_text).
4. Do the same for the resume (resume_bullet and resume_highlight_text).

✅ CORRECT EXAMPLE:
{{
  "job_requirement": "Design and implement scalable data pipelines using Python, SQL, and cloud technologies.",
  "job_highlight_text": "Design and implement scalable data pipelines using Python, SQL, and cloud technologies.",
  "resume_bullet": "Built data pipelines in Python and SQL to process large datasets across AWS infrastructure.",
  "resume_highlight_text": "Built data pipelines in Python and SQL to process large datasets across AWS infrastructure.",
  "match_strength": "strong",
  "explanation": "The resume bullet clearly demonstrates experience designing and implementing data pipelines using Python and SQL, directly reflecting the job requirement."
}}

❌ WRONG EXAMPLE:
{{
  "job_requirement": "Data pipeline experience",
  "job_highlight_text": "Design and implement scalable data pipelines using Python, SQL, and cloud technologies.",
  "resume_bullet": "Created ETL processes for analytics.",
  "resume_highlight_text": "Built data pipelines in Python and SQL to process large datasets across AWS infrastructure."
}}

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks.

Format:
{{
  "overall_score": 85,
  "confidence": 0.82,
  "confidence_reasoning": "High confidence due to explicit skill matches, but some uncertainty about experience depth",
  "uncertainty_factors": [
    "Resume mentions cloud experience but doesn't specify years",
    "Job requires 'senior level' but resume doesn't state seniority explicitly"
  ],
  "score_breakdown": {{
    "skills_match": 90,
    "experience_match": 80,
    "requirements_match": 85,
    "education_match": 75
  }},
  "matched_bullets": [
    {{
      "job_requirement": "...",
      "job_highlight_text": "...",
      "resume_bullet": "...",
      "resume_highlight_text": "...",
      "match_strength": "strong/moderate/weak",
      "explanation": "..."
    }}
  ],
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "strengths": ["strength1", "strength2"],
  "gaps": ["gap1", "gap2"],
  "improvement_suggestions": ["tip 1", "tip 2"],
  "summary": "Overall assessment"
}}

CONFIDENCE SCORING RULES:
- confidence: 0.9-1.0 = Very confident (clear, explicit evidence)
- confidence: 0.7-0.89 = Moderately confident (solid inference, minor ambiguity)
- confidence: 0.5-0.69 = Low confidence (significant assumptions made)
- confidence: <0.5 = Very uncertain (major gaps or contradictions)

List specific uncertainty_factors whenever confidence < 0.85

**RESUME:**
{resume_text[:4000]}

**JOB:**
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
{job.get('description', 'N/A')[:3500]}

Return 10 matched bullets with EXACT TEXT from both documents."""

        result = await self.kernel.invoke_prompt(prompt)
        result_str = str(result).strip()
        
        print(f"🔍 RAW LLM RESPONSE (first 500 chars):\n{result_str[:500]}")
        
        # Aggressive JSON cleaning
        if '```json' in result_str:
            result_str = result_str.split('```json')[1].split('```')[0].strip()
        elif '```' in result_str:
            result_str = result_str.split('```')[1].split('```')[0].strip()
        
        # Remove any text before first { and after last }
        start_idx = result_str.find('{')
        end_idx = result_str.rfind('}')
        if start_idx != -1 and end_idx != -1:
            result_str = result_str[start_idx:end_idx+1]
        
        try:
            parsed = json.loads(result_str)
            
            # Extract score from overall_score field (new format)
            score = parsed.get('overall_score', parsed.get('score', 0))
            
            # Ensure all required fields exist
            return {
                'score': int(score),
                'confidence': float(parsed.get('confidence', 0.5)),
                'confidence_reasoning': parsed.get('confidence_reasoning', ''),
                'uncertainty_factors': parsed.get('uncertainty_factors', []),
                'reason': parsed.get('summary', parsed.get('reason', 'No summary provided')),
                'matched_skills': parsed.get('matched_skills', []),
                'missing_skills': parsed.get('missing_skills', []),
                'matched_bullets': parsed.get('matched_bullets', []),
                'strengths': parsed.get('strengths', []),
                'gaps': parsed.get('gaps', []),
                'improvement_suggestions': parsed.get('improvement_suggestions', []),
                'summary': parsed.get('summary', parsed.get('reason', '')),
                'score_breakdown': parsed.get('score_breakdown', {})
            }
        except Exception as e:
            print(f"   ❌ JSON parsing failed: {e}")
            print(f"   Raw response (first 500 chars): {result_str[:500]}")
            
            # Try to extract score even from broken JSON
            import re
            score_match = re.search(r'"(?:overall_score|score)":\s*(\d+)', result_str)
            extracted_score = int(score_match.group(1)) if score_match else 0
            
            # Try to extract other fields with regex
            reason_match = re.search(r'"(?:summary|reason)":\s*"([^"]+)"', result_str)
            extracted_reason = reason_match.group(1) if reason_match else 'Analysis parsing failed'
            
            confidence_match = re.search(r'"confidence":\s*(0\.\d+)', result_str)
            extracted_confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            
            print(f"   🔧 Attempting partial extraction - Score: {extracted_score}, Confidence: {extracted_confidence}")
            
            # Return partial extraction
            return {
                'score': extracted_score,
                'confidence': extracted_confidence,
                'confidence_reasoning': '',
                'uncertainty_factors': [],
                'reason': extracted_reason,
                'matched_skills': [],
                'missing_skills': [],
                'matched_bullets': [],
                'strengths': [],
                'gaps': [],
                'improvement_suggestions': [],
                'summary': extracted_reason,
                'score_breakdown': {},
                '_parsing_failed': True  # Flag that this was partial
            }

    # ====================================================================
    # NEW: Refine existing analysis instead of regenerating
    # ====================================================================
    async def _refine_existing_analysis(self, resume_text: str, job: dict, previous_analysis: dict, guidance: str) -> dict:
        """
        Refine an existing analysis by fixing specific issues rather than regenerating.
        This preserves good work while improving weak areas.
        """
        
        existing_bullets = previous_analysis.get('matched_bullets', [])
        existing_score = previous_analysis.get('score', 0)
        
        prompt = f"""You are refining an existing resume-job match analysis. Your job is to IMPROVE what's already there, not start over.

**CURRENT ANALYSIS:**
- Score: {existing_score}/100
- Matched Bullets: {len(existing_bullets)}
- Strong matches: {len([b for b in existing_bullets if b.get('match_strength') == 'strong'])}
- Moderate matches: {len([b for b in existing_bullets if b.get('match_strength') == 'moderate'])}
- Weak matches: {len([b for b in existing_bullets if b.get('match_strength') == 'weak'])}

**EXISTING BULLETS:**
{json.dumps(existing_bullets, indent=2)}

**REFINEMENT GUIDANCE:**
{guidance}

**YOUR TASK:**
1. Review each existing bullet - keep good ones, improve weak ones
2. Fix any bullets with:
   - Wrong match_strength classification
   - Weak or generic explanations
   - Mismatches between job requirement and resume bullet
3. Add NEW bullets only if you find additional strong matches that were missed
4. Update the score if your refinements change the overall match quality
5. Keep all the good work that's already there!

**RULES:**
- If a bullet is already strong and accurate, KEEP IT AS-IS
- Only change bullets that have clear problems
- Add bullets for any major requirements that weren't matched yet
- Your refined score should reflect actual improvements (not arbitrary changes)

CRITICAL: Return ONLY valid JSON. No markdown, no explanations.

**JSON Format:**
{{
  "overall_score": 85,
  "confidence": 0.85,
  "confidence_reasoning": "Explanation of confidence level",
  "uncertainty_factors": ["factor1", "factor2"],
  "score_breakdown": {{
    "skills_match": 90,
    "experience_match": 85,
    "requirements_match": 80,
    "education_match": 75
  }},
  "matched_bullets": [
    {{
      "job_requirement": "exact text from job",
      "job_highlight_text": "exact text from job",
      "resume_bullet": "exact text from resume",
      "resume_highlight_text": "exact text from resume",
      "match_strength": "strong/moderate/weak",
      "explanation": "detailed explanation",
      "refinement_note": "what changed (if anything)"
    }}
  ],
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3"],
  "strengths": ["strength1"],
  "gaps": ["gap1"],
  "improvement_suggestions": ["suggestion1"],
  "summary": "Brief summary of refinements made",
  "bullets_kept": 5,
  "bullets_improved": 2,
  "bullets_added": 1
}}

**RESUME:**
{resume_text[:3000]}

**JOB:**
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
{job.get('description', 'N/A')[:2500]}"""

        result = await self.kernel.invoke_prompt(prompt)
        result_str = str(result).strip()
        
        print(f"🔍 REFINEMENT RESPONSE (first 500 chars):\n{result_str[:500]}")
        
        # Aggressive JSON cleaning
        if '```json' in result_str:
            result_str = result_str.split('```json')[1].split('```')[0].strip()
        elif '```' in result_str:
            result_str = result_str.split('```')[1].split('```')[0].strip()
        
        start_idx = result_str.find('{')
        end_idx = result_str.rfind('}')
        if start_idx != -1 and end_idx != -1:
            result_str = result_str[start_idx:end_idx+1]
        
        try:
            parsed = json.loads(result_str)
            
            score = parsed.get('overall_score', parsed.get('score', existing_score))
            
            # Log refinement stats
            bullets_kept = parsed.get('bullets_kept', 0)
            bullets_improved = parsed.get('bullets_improved', 0)
            bullets_added = parsed.get('bullets_added', 0)
            
            print(f"   📝 Refinement: Kept {bullets_kept}, Improved {bullets_improved}, Added {bullets_added}")
            
            return {
                'score': int(score),
                'confidence': float(parsed.get('confidence', previous_analysis.get('confidence', 0.5))),
                'confidence_reasoning': parsed.get('confidence_reasoning', ''),
                'uncertainty_factors': parsed.get('uncertainty_factors', []),
                'reason': parsed.get('summary', previous_analysis.get('reason', '')),
                'matched_skills': parsed.get('matched_skills', previous_analysis.get('matched_skills', [])),
                'missing_skills': parsed.get('missing_skills', previous_analysis.get('missing_skills', [])),
                'matched_bullets': parsed.get('matched_bullets', previous_analysis.get('matched_bullets', [])),
                'strengths': parsed.get('strengths', previous_analysis.get('strengths', [])),
                'gaps': parsed.get('gaps', previous_analysis.get('gaps', [])),
                'improvement_suggestions': parsed.get('improvement_suggestions', previous_analysis.get('improvement_suggestions', [])),
                'summary': parsed.get('summary', previous_analysis.get('summary', '')),
                'score_breakdown': parsed.get('score_breakdown', previous_analysis.get('score_breakdown', {})),
                '_refinement_stats': {
                    'bullets_kept': bullets_kept,
                    'bullets_improved': bullets_improved,
                    'bullets_added': bullets_added
                }
            }
        
        except Exception as e:
            print(f"   ❌ Refinement parsing failed: {e}")
            print(f"   ⚠️ Keeping previous analysis")
            # On error, return previous analysis unchanged
            return previous_analysis

    # ====================================================================
    # AI Critic - Reviews single match quality
    # ====================================================================
    async def _critique_single_match(self, analysis: dict, resume: dict, job: dict) -> str:
        """
        AI reviews a single match analysis.
        """
        
        matched_bullets = analysis.get('matched_bullets', [])
        
        prompt = f"""You are a quality control expert reviewing a single job-resume match analysis.

**Job:** {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}
**Match Score:** {analysis.get('score', 0)}/100

**Matched Skills:** {', '.join(analysis.get('matched_skills', [])[:10])}
**Missing Skills:** {', '.join(analysis.get('missing_skills', [])[:5])}

**Matched Bullets:** {len(matched_bullets)} matches found
- Strong: {len([b for b in matched_bullets if b.get('match_strength') == 'strong'])}
- Moderate: {len([b for b in matched_bullets if b.get('match_strength') == 'moderate'])}
- Weak: {len([b for b in matched_bullets if b.get('match_strength') == 'weak'])}

**Review This Match For:**
1. Is the score accurate given the matches?
2. Are strong/moderate/weak classifications correct?
3. Any key requirements missed?
4. Is reasoning specific enough?

CRITICAL: Return ONLY valid JSON. No markdown, no explanations.

**JSON Format:**
{{
  "overall_quality": 75,
  "issues": [
    {{
      "issue": "Score seems too high given weak matches",
      "severity": "high"
    }}
  ],
  "strengths": ["What's good about this analysis"],
  "weaknesses": ["What needs improvement"],
  "recommendations": ["Specific improvements"]
}}"""

        result = await self.kernel.invoke_prompt(prompt)
        result_str = str(result).strip()
        
        # Clean JSON
        if '```json' in result_str:
            result_str = result_str.split('```json')[1].split('```')[0].strip()
        
        start_idx = result_str.find('{')
        end_idx = result_str.rfind('}')
        if start_idx != -1 and end_idx != -1:
            result_str = result_str[start_idx:end_idx+1]
        
        return result_str

    # ====================================================================
    # Generate refinements for single match
    # ====================================================================
    async def _generate_refinements_for_single_match(
        self,
        critique: dict,
        analysis: dict,
        resume: dict,
        job: dict
    ) -> str:
        """
        Generate refinements for this specific match.
        """
        
        prompt = f"""You are improving a job-resume match analysis.

**Current Analysis Issues:**
{json.dumps(critique.get('weaknesses', []), indent=2)}

**Recommendations:**
{json.dumps(critique.get('recommendations', []), indent=2)}

**Your Task:** Generate specific guidance to improve THIS match analysis.

CRITICAL: Return ONLY valid JSON.

**JSON Format:**
{{
  "adjustments": [
    {{
      "area": "scoring",
      "change": "Lower score by 10 points due to experience gap",
      "reason": "Candidate has 3 years, job requires 5"
    }}
  ],
  "focus_areas": [
    "Re-evaluate years of experience match",
    "Check if leadership requirement is met"
  ]
}}"""

        result = await self.kernel.invoke_prompt(prompt)
        result_str = str(result).strip()
        
        # Clean JSON
        if '```json' in result_str:
            result_str = result_str.split('```json')[1].split('```')[0].strip()
        
        start_idx = result_str.find('{')
        end_idx = result_str.rfind('}')
        if start_idx != -1 and end_idx != -1:
            result_str = result_str[start_idx:end_idx+1]
        
        return result_str