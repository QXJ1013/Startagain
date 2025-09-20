# app/services/ai_scoring_engine.py
from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import logging

@dataclass
class AIScoreResult:
    """Result of AI-powered scoring"""
    score: float                    # 0-7 scale matching question options
    confidence: float              # 0-1 confidence in scoring
    reasoning: str                 # Explanation of scoring rationale
    quality_of_life_impact: str   # Impact description
    extracted_insights: List[str] # Key insights from response

class AIFreeTextScorer:
    """
    Pure AI-powered scoring for free-text user responses.
    Uses IBM WatsonX LLM for intelligent evaluation without any fallbacks.
    """

    def __init__(self, ai_router=None):
        self.log = logging.getLogger(__name__)

        # Initialize real AI client for scoring
        from app.vendors.ibm_cloud import LLMClient
        self.llm_client = LLMClient()

        # Verify AI client is available
        if not self.llm_client.healthy():
            raise RuntimeError("AI scoring requires IBM WatsonX client to be properly configured")

    async def score_free_text_response(
        self,
        user_response: str,
        question_context: Dict[str, Any],
        pnm_domain: str,
        conversation_history: List[Dict] = None
    ) -> AIScoreResult:
        """
        Score free-text response using AI analysis only
        """
        try:
            # Build comprehensive scoring prompt
            scoring_prompt = self._build_scoring_prompt(
                user_response,
                question_context,
                pnm_domain,
                conversation_history
            )

            self.log.info(f"[AI SCORING] Analyzing response for {pnm_domain} using real AI")

            # Use IBM WatsonX AI for scoring
            ai_result = self.llm_client.generate_json(scoring_prompt)

            if not ai_result:
                raise ValueError("AI returned empty response")

            # Parse and validate AI scoring result
            score_result = self._parse_ai_result(ai_result, user_response)

            self.log.info(f"[AI SCORING] Completed: score={score_result.score}, confidence={score_result.confidence}")

            return score_result

        except Exception as e:
            self.log.error(f"[AI SCORING] Failed: {e}")
            # No fallbacks allowed - let it fail if AI doesn't work
            raise RuntimeError(f"AI scoring failed: {e}. No fallback scoring allowed.")

    def _build_scoring_prompt(
        self,
        user_response: str,
        question_context: Dict[str, Any],
        pnm_domain: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """Build comprehensive scoring prompt for AI using question-specific options"""

        # Extract question and options from context
        question_text = question_context.get('question', question_context.get('text', 'Assessment question'))
        options = question_context.get('options', [])
        term = question_context.get('term', 'general assessment')

        # Build question-specific scoring scale
        scoring_scale = self._build_question_specific_scale(options)

        prompt = f"""You're an ALS specialist scoring patient responses.

Question about {term}: {question_text}

Available scores:
{scoring_scale}

Patient said: "{user_response}"

Score their response (0-7) based on how well they're managing this situation. Return JSON with score, confidence, reasoning, quality_of_life_impact, and extracted_insights."""

        # Add conversation context if available
        if conversation_history:
            recent_context = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
            context_summary = "\n".join([f"- {msg.content if hasattr(msg, 'content') else str(msg)}" for msg in recent_context])
            prompt += f"\n\nRECENT CONVERSATION CONTEXT:\n{context_summary}"

        return prompt

    def _build_question_specific_scale(self, options: List[Dict]) -> str:
        """Build scoring scale text from question options"""
        if not options:
            return """Score 0-7 scale based on ALS impact assessment:
0: No impact, fully prepared/optimal situation
1-2: Minimal impact, excellent management
3-4: Moderate impact, some challenges
5-6: Significant impact, major difficulties
7: Severe impact, extreme challenges"""

        # Build scale from actual question options
        scale_lines = []
        for i, option in enumerate(options):
            if isinstance(option, dict):
                score = option.get('score', i)
                label = option.get('label', option.get('text', f'Option {i}'))
                scale_lines.append(f"Score {score}: {label}")
            else:
                scale_lines.append(f"Score {i}: {str(option)}")

        return "\n".join(scale_lines)

    def _parse_ai_result(self, ai_result: Dict[str, Any], original_response: str) -> AIScoreResult:
        """Parse AI JSON response into structured score result"""
        try:
            # Extract and validate score
            score = ai_result.get('score')
            if score is None:
                raise ValueError("AI result missing score field")

            score = int(score)
            if not (0 <= score <= 7):
                raise ValueError(f"AI score {score} outside valid range 0-7")

            # Extract and validate confidence
            confidence = float(ai_result.get('confidence', 0.8))
            confidence = max(0.0, min(1.0, confidence))

            # Extract other fields
            reasoning = ai_result.get('reasoning', 'AI analysis completed')
            if not reasoning or len(reasoning.strip()) < 10:
                raise ValueError("AI reasoning too short or missing")

            quality_impact = ai_result.get('quality_of_life_impact', 'Quality of life impact assessed')
            insights = ai_result.get('extracted_insights', [])

            # Ensure insights is a list
            if not isinstance(insights, list):
                insights = []

            return AIScoreResult(
                score=float(score),
                confidence=confidence,
                reasoning=reasoning,
                quality_of_life_impact=quality_impact,
                extracted_insights=insights
            )

        except Exception as e:
            self.log.error(f"Failed to parse AI result: {e}")
            self.log.error(f"AI result was: {ai_result}")
            raise ValueError(f"Invalid AI scoring result: {e}")


class EnhancedPNMScorer:
    """Enhanced PNM scoring with missing value handling"""

    def __init__(self):
        from app.services.pnm_scoring import PNMScoringEngine
        self.pnm_engine = PNMScoringEngine()
        self.ai_scorer = AIFreeTextScorer()
        self.log = logging.getLogger(__name__)


class StageScorer:
    """Stage-based scoring system"""

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.stages = ["Early", "Moderate", "Advanced", "Late"]