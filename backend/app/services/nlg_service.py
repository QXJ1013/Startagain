# app/services/nlg_service.py
"""
Natural Language Generation Service for Enhanced Information Cards
Provides intelligent content enhancement, tone adaptation, and quality optimization
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import re
import logging

from app.config import get_settings
from app.vendors.ibm_cloud import LLMClient

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of content that can be enhanced"""
    INFO_CARD = "information_card"
    DIALOGUE = "dialogue_response"
    TRANSITION = "transition_message"
    EMPATHY = "empathy_response"
    CLARIFICATION = "clarification_request"


class ToneStyle(Enum):
    """Available tone styles for content adaptation"""
    PROFESSIONAL = "professional"
    EMPATHETIC = "empathetic"
    ENCOURAGING = "encouraging"
    INFORMATIVE = "informative"
    CONVERSATIONAL = "conversational"


@dataclass
class ContentContext:
    """Context information for content enhancement"""
    content_type: ContentType
    tone_style: ToneStyle
    user_emotional_state: str = "neutral"
    reading_level: str = "8th_grade"
    user_preferences: Dict[str, Any] = None
    cultural_context: str = "general"
    conversation_stage: str = "initial"
    specific_mentions: List[str] = None
    severity_level: str = "moderate"

    def __post_init__(self):
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.specific_mentions is None:
            self.specific_mentions = []


class NaturalLanguageGenerator:
    """
    Intelligent content enhancement service for information cards.
    Provides tone adaptation, readability optimization, and personalization.
    """
    
    def __init__(self):
        self.cfg = get_settings()
        self.enabled = getattr(self.cfg, "NLG_ENABLED", True)
        
        # Initialize LLM for content enhancement
        if self.enabled:
            self.llm = LLMClient(
                model_id=getattr(self.cfg, "NLG_MODEL_ID", "meta-llama/llama-3-3-70b-instruct"),
                params={
                    "max_new_tokens": 500,
                    "temperature": 0.3,  # Balanced creativity for enhancement
                    "top_p": 0.9,
                    "repetition_penalty": 1.1
                }
            )
        else:
            self.llm = None
    
    def enhance_content(
        self,
        content: str,
        context: ContentContext,
        original_content: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Main enhancement function - improves content quality and personalization.
        
        Args:
            content: Raw content to enhance
            context: Enhancement context with tone, style, and user info
            original_content: Original structured content for reference
            
        Returns:
            Enhanced content string
        """
        if not self.enabled:
            logger.info("NLG service disabled, returning original content")
            return content
        
        try:
            # Apply enhancement pipeline
            enhanced = self._enhance_with_llm(content, context, original_content)
            if enhanced:
                # Post-process for quality assurance
                enhanced = self._post_process_content(enhanced, context)
                logger.info(f"Content enhanced: {len(content)} -> {len(enhanced)} chars")
                return enhanced
            else:
                # Fallback to template-based enhancement
                return self._enhance_with_templates(content, context)
                
        except Exception as e:
            logger.warning(f"Content enhancement failed: {e}")
            return self._enhance_with_templates(content, context)
    
    def _enhance_with_llm(
        self,
        content: str,
        context: ContentContext,
        original_content: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Enhance content using LLM with intelligent prompting"""
        
        if not self.llm or not self.llm.healthy():
            return None
        
        # Build enhancement prompt based on context
        tone_description = self._get_tone_description(context.tone_style)
        readability_level = self._get_readability_instructions(context.reading_level)
        
        prompt = f"""Make this ALS information clearer and more supportive.

Original: {content}

Make it {tone_description} and {readability_level}. The person is feeling {context.user_emotional_state} and mentioned {', '.join(context.specific_mentions[:3]) if context.specific_mentions else 'general concerns'}.

Rewrite it to be more personal, less clinical, and encouraging while keeping the same information:"""

        try:
            response = self.llm.generate(prompt)
            if response and response.strip():
                return response.strip()
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
        
        return None
    
    def _enhance_with_templates(self, content: str, context: ContentContext) -> str:
        """Fallback template-based enhancement"""
        enhanced = content
        
        # Apply tone-specific enhancements
        if context.tone_style == ToneStyle.EMPATHETIC:
            enhanced = self._add_empathy_phrases(enhanced)
        elif context.tone_style == ToneStyle.ENCOURAGING:
            enhanced = self._add_encouraging_phrases(enhanced)
        elif context.tone_style == ToneStyle.PROFESSIONAL:
            enhanced = self._add_professional_structure(enhanced)
        
        # Apply readability improvements
        enhanced = self._simplify_medical_terms(enhanced)
        enhanced = self._personalize_pronouns(enhanced)
        
        return enhanced
    
    def _post_process_content(self, content: str, context: ContentContext) -> str:
        """Post-process enhanced content for quality assurance"""
        
        # Remove any unwanted formatting
        content = re.sub(r'Enhanced content:\s*', '', content)
        content = re.sub(r'Here\'s the enhanced version:\s*', '', content)
        
        # Ensure proper sentence structure
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Validate length appropriateness
        if context.content_type == ContentType.INFO_CARD:
            # Info cards should be concise but informative
            if len(content) > 1000:
                content = content[:900] + "..."
        
        return content
    
    def _get_tone_description(self, tone: ToneStyle) -> str:
        """Get description for tone style"""
        descriptions = {
            ToneStyle.PROFESSIONAL: "Clear, authoritative, medical professional tone",
            ToneStyle.EMPATHETIC: "Caring, understanding, supportive tone",
            ToneStyle.ENCOURAGING: "Positive, motivating, hopeful tone",
            ToneStyle.INFORMATIVE: "Educational, clear, straightforward tone",
            ToneStyle.CONVERSATIONAL: "Friendly, casual, approachable tone"
        }
        return descriptions.get(tone, "Clear and helpful tone")
    
    def _get_readability_instructions(self, level: str) -> str:
        """Get readability instructions for target level"""
        instructions = {
            "8th_grade": "Use simple words, short sentences, avoid medical jargon",
            "10th_grade": "Use moderate complexity, explain technical terms",
            "college": "Can use medical terminology with explanations"
        }
        return instructions.get(level, "Use clear, accessible language")
    
    def _add_empathy_phrases(self, content: str) -> str:
        """Add empathetic phrases to content"""
        empathy_starters = [
            "I understand this can be challenging.",
            "Many people find this helpful.",
            "This is a common concern.",
            "You're not alone in experiencing this."
        ]
        
        # Add an empathy phrase at the beginning if not present
        for starter in empathy_starters:
            if starter.lower() not in content.lower():
                return f"{starter} {content}"
        
        return content
    
    def _add_encouraging_phrases(self, content: str) -> str:
        """Add encouraging phrases to content"""
        encouraging_words = {
            "try": "you can try",
            "consider": "you might consider",
            "difficult": "manageable with the right approach",
            "problem": "challenge that can be addressed"
        }
        
        for word, replacement in encouraging_words.items():
            content = content.replace(word, replacement)
        
        return content
    
    def _add_professional_structure(self, content: str) -> str:
        """Add professional structure to content"""
        # Ensure proper medical terminology and structure
        if not content.startswith(("Based on", "According to", "Clinical")):
            content = f"Based on clinical guidance, {content.lower()}"
        
        return content
    
    def _simplify_medical_terms(self, content: str) -> str:
        """Simplify medical terminology"""
        simplifications = {
            "dysphagia": "difficulty swallowing",
            "dyspnea": "breathing difficulties",
            "fasciculations": "muscle twitching",
            "spasticity": "muscle stiffness",
            "bulbar": "speech and swallowing",
            "respiratory compromise": "breathing problems",
            "gastrostomy": "feeding tube",
            "non-invasive ventilation": "breathing support device"
        }
        
        for medical_term, simple_term in simplifications.items():
            content = re.sub(
                rf'\b{medical_term}\b',
                f"{simple_term} ({medical_term})",
                content,
                flags=re.IGNORECASE
            )
        
        return content
    
    def _personalize_pronouns(self, content: str) -> str:
        """Make content more personal by using appropriate pronouns"""
        # Replace generic terms with personal pronouns
        replacements = {
            "patients": "you",
            "individuals": "you",
            "people with ALS": "you",
            "the patient": "you",
            "one should": "you should",
            "it is recommended": "you should consider"
        }
        
        for generic, personal in replacements.items():
            content = re.sub(
                rf'\b{generic}\b',
                personal,
                content,
                flags=re.IGNORECASE
            )
        
        return content


# Utility functions for integration
def create_info_card_context(
    conversation_context: Dict[str, Any],
    user_profile: Optional[Dict[str, Any]] = None
) -> ContentContext:
    """Create ContentContext for information card enhancement"""
    
    # Extract context information
    emotional_state = conversation_context.get('emotional_state', 'neutral')
    severity_level = conversation_context.get('severity_level', 'moderate')
    conversation_stage = conversation_context.get('session_stage', 'initial')
    specific_mentions = conversation_context.get('specific_mentions', [])
    
    # Determine appropriate tone based on context
    tone_style = ToneStyle.EMPATHETIC
    if severity_level == 'high':
        tone_style = ToneStyle.PROFESSIONAL
    elif conversation_stage in ['detailed', 'comprehensive']:
        tone_style = ToneStyle.INFORMATIVE
    
    # Set reading level based on user profile
    reading_level = "8th_grade"
    if user_profile:
        reading_level = user_profile.get('reading_level', '8th_grade')
    
    return ContentContext(
        content_type=ContentType.INFO_CARD,
        tone_style=tone_style,
        user_emotional_state=emotional_state,
        reading_level=reading_level,
        conversation_stage=conversation_stage,
        specific_mentions=specific_mentions,
        severity_level=severity_level
    )


def enhance_info_card(
    raw_card: Dict[str, Any],
    conversation_context: Dict[str, Any],
    user_profile: Optional[Dict[str, Any]] = None,
    nlg_service: Optional[NaturalLanguageGenerator] = None
) -> Dict[str, Any]:
    """
    Enhance an information card using NLG service.
    
    Args:
        raw_card: Original card with title and bullets
        conversation_context: Context from conversation
        user_profile: User profile information
        nlg_service: NLG service instance (created if None)
        
    Returns:
        Enhanced information card
    """
    if nlg_service is None:
        nlg_service = NaturalLanguageGenerator()
    
    if not nlg_service.enabled:
        return raw_card
    
    try:
        # Create enhancement context
        context = create_info_card_context(conversation_context, user_profile)
        
        # Enhance title
        enhanced_title = raw_card.get('title', '')
        if enhanced_title:
            enhanced_title = nlg_service.enhance_content(enhanced_title, context)
        
        # Enhance bullets
        enhanced_bullets = []
        for bullet in raw_card.get('bullets', []):
            if bullet:
                enhanced_bullet = nlg_service.enhance_content(bullet, context)
                enhanced_bullets.append(enhanced_bullet)
        
        # Return enhanced card
        enhanced_card = raw_card.copy()
        enhanced_card.update({
            'title': enhanced_title,
            'bullets': enhanced_bullets,
            'enhanced': True,
            'enhancement_context': {
                'tone': context.tone_style.value,
                'reading_level': context.reading_level,
                'emotional_state': context.user_emotional_state
            }
        })
        
        return enhanced_card
        
    except Exception as e:
        logger.error(f"Card enhancement failed: {e}")
        return raw_card