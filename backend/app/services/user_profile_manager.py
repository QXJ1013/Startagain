# app/services/user_profile_manager.py
from __future__ import annotations
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from app.config import get_settings

@dataclass
class UserProfileData:
    """Comprehensive user profile data"""
    user_id: str
    
    # Basic demographics and ALS info
    basic_info: Dict[str, Any] = None
    diagnosis_info: Dict[str, Any] = None
    
    # PNM assessment data
    pnm_profile: Dict[str, Any] = None  # Current PNM scores and assessments
    pnm_history: List[Dict[str, Any]] = None  # Historical PNM assessments
    
    # Stage progression tracking
    stage_profile: Dict[str, Any] = None
    progression_history: List[Dict[str, Any]] = None
    
    # Direct routing preferences
    preferred_dimensions: List[str] = None
    completed_assessments: List[str] = None
    priority_areas: List[str] = None
    
    # Conversation patterns and preferences
    interaction_patterns: Dict[str, Any] = None
    
    # Timestamps
    created_at: str = None
    updated_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.basic_info is None:
            self.basic_info = {}
        if self.diagnosis_info is None:
            self.diagnosis_info = {}
        if self.pnm_profile is None:
            self.pnm_profile = {}
        if self.pnm_history is None:
            self.pnm_history = []
        if self.stage_profile is None:
            self.stage_profile = {}
        if self.progression_history is None:
            self.progression_history = []
        if self.preferred_dimensions is None:
            self.preferred_dimensions = []
        if self.completed_assessments is None:
            self.completed_assessments = []
        if self.priority_areas is None:
            self.priority_areas = []
        if self.interaction_patterns is None:
            self.interaction_patterns = {}

class UserProfileManager:
    """
    Direct user profile management with database persistence.
    Replaces unreliable routing with direct data storage and retrieval.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.db_path = self.settings.DB_PATH
        self.log = logging.getLogger(__name__)
        self._ensure_profile_tables()
    
    def _ensure_profile_tables(self):
        """Ensure user profile tables exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT NOT NULL,  -- JSON UserProfileData
                    version INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Quick access tables for routing decisions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_pnm_status (
                    user_id TEXT,
                    pnm_dimension TEXT,
                    completion_status TEXT DEFAULT 'not_started',  -- 'not_started' | 'in_progress' | 'completed'
                    last_score REAL,
                    last_assessment_date DATETIME,
                    priority_level INTEGER DEFAULT 5,  -- 1-10 priority for routing
                    PRIMARY KEY(user_id, pnm_dimension),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_direct_routes (
                    user_id TEXT,
                    route_type TEXT,  -- 'pnm_dimension' | 'term' | 'stage_focus'  
                    route_value TEXT,  -- actual PNM/term/stage
                    priority INTEGER DEFAULT 5,
                    last_used DATETIME,
                    success_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(user_id, route_type, route_value),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Indexes for fast routing
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_pnm_priority ON user_pnm_status(user_id, priority_level DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_routes_priority ON user_direct_routes(user_id, priority DESC)")
            
            conn.commit()
    
    def get_or_create_profile(self, user_id: str) -> UserProfileData:
        """Get existing profile or create new one"""
        try:
            existing_profile = self.get_profile(user_id)
            if existing_profile:
                return existing_profile
        except Exception as e:
            self.log.warning(f"Error loading existing profile for {user_id}: {e}")
        
        # Create new profile
        new_profile = UserProfileData(user_id=user_id)
        self.save_profile(new_profile)
        self._initialize_pnm_status(user_id)
        return new_profile
    
    def get_profile(self, user_id: str) -> Optional[UserProfileData]:
        """Get user profile by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT profile_data FROM user_profiles WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                try:
                    profile_dict = json.loads(row[0])
                    return UserProfileData(**profile_dict)
                except Exception as e:
                    self.log.error(f"Error deserializing profile for {user_id}: {e}")
                    return None
            return None
    
    def save_profile(self, profile: UserProfileData):
        """Save user profile to database"""
        profile.updated_at = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profiles (user_id, profile_data, updated_at)
                VALUES (?, ?, ?)
            """, (
                profile.user_id,
                json.dumps(asdict(profile)),
                datetime.now()
            ))
            conn.commit()
            
        self.log.info(f"User profile saved for {profile.user_id}")
    
    def _initialize_pnm_status(self, user_id: str):
        """Initialize PNM status for new user"""
        pnm_dimensions = [
            "Physiological", "Safety", "Love & Belonging", "Esteem",
            "Self-Actualisation", "Cognitive", "Aesthetic", "Transcendence"
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for i, pnm in enumerate(pnm_dimensions):
                # Higher priority for basic needs (lower index)
                priority = 10 - i  # Physiological=10, Transcendence=3
                
                conn.execute("""
                    INSERT OR IGNORE INTO user_pnm_status 
                    (user_id, pnm_dimension, priority_level)
                    VALUES (?, ?, ?)
                """, (user_id, pnm, priority))
            conn.commit()
    
    def get_next_recommended_pnm(self, user_id: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Get next recommended PNM dimension based on direct database priorities.
        Replaces unreliable AI routing with database-driven decisions.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT pnm_dimension, completion_status, last_score, priority_level
                FROM user_pnm_status 
                WHERE user_id = ? 
                ORDER BY 
                    CASE completion_status 
                        WHEN 'not_started' THEN 1 
                        WHEN 'in_progress' THEN 2 
                        ELSE 3 
                    END,
                    priority_level DESC,
                    last_assessment_date ASC NULLS FIRST
                LIMIT 1
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                pnm_dimension, status, last_score, priority = row
                return pnm_dimension, {
                    'completion_status': status,
                    'last_score': last_score,
                    'priority_level': priority,
                    'routing_method': 'database_priority'
                }
        
        # Fallback to first dimension if nothing found
        return "Physiological", {'routing_method': 'fallback'}
    
    def update_pnm_status(
        self, 
        user_id: str, 
        pnm_dimension: str, 
        status: str, 
        score: Optional[float] = None
    ):
        """Update PNM dimension status directly"""
        with sqlite3.connect(self.db_path) as conn:
            if score is not None:
                conn.execute("""
                    UPDATE user_pnm_status 
                    SET completion_status = ?, last_score = ?, last_assessment_date = ?
                    WHERE user_id = ? AND pnm_dimension = ?
                """, (status, score, datetime.now(), user_id, pnm_dimension))
            else:
                conn.execute("""
                    UPDATE user_pnm_status 
                    SET completion_status = ?, last_assessment_date = ?
                    WHERE user_id = ? AND pnm_dimension = ?
                """, (status, datetime.now(), user_id, pnm_dimension))
            conn.commit()
            
        self.log.info(f"Updated PNM status: {user_id} -> {pnm_dimension} = {status}")
    
    def record_successful_route(
        self, 
        user_id: str, 
        route_type: str, 
        route_value: str
    ):
        """Record successful routing decision for future optimization"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_direct_routes 
                (user_id, route_type, route_value, last_used, success_count)
                VALUES (
                    ?, ?, ?, ?, 
                    COALESCE((SELECT success_count FROM user_direct_routes 
                             WHERE user_id = ? AND route_type = ? AND route_value = ?), 0) + 1
                )
            """, (user_id, route_type, route_value, datetime.now(), 
                  user_id, route_type, route_value))
            conn.commit()
    
    def get_user_preferred_routes(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's most successful routing patterns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT route_type, route_value, priority, success_count, last_used
                FROM user_direct_routes
                WHERE user_id = ?
                ORDER BY success_count DESC, priority DESC
                LIMIT 10
            """, (user_id,))
            
            return [
                {
                    'route_type': row[0],
                    'route_value': row[1], 
                    'priority': row[2],
                    'success_count': row[3],
                    'last_used': row[4]
                }
                for row in cursor.fetchall()
            ]
    
    def update_interaction_patterns(
        self, 
        user_id: str, 
        interaction_data: Dict[str, Any]
    ):
        """Update user interaction patterns in profile"""
        profile = self.get_or_create_profile(user_id)
        
        # Update interaction patterns
        if not profile.interaction_patterns:
            profile.interaction_patterns = {}
            
        # Track conversation patterns
        profile.interaction_patterns.update({
            'last_interaction': datetime.now().isoformat(),
            'total_conversations': profile.interaction_patterns.get('total_conversations', 0) + 1,
            'preferred_mode': interaction_data.get('conversation_mode', 'assessment'),
            'average_session_length': interaction_data.get('session_length', 0),
            'response_style_preference': interaction_data.get('response_style', 'detailed')
        })
        
        self.save_profile(profile)
    
    def store_comprehensive_assessment_results(
        self, 
        user_id: str, 
        pnm_scores: Dict[str, Any], 
        stage_analysis: Dict[str, Any]
    ):
        """Store complete assessment results directly in user profile"""
        profile = self.get_or_create_profile(user_id)
        
        # Update PNM profile with latest results
        profile.pnm_profile = pnm_scores
        
        # Add to PNM history
        assessment_record = {
            'timestamp': datetime.now().isoformat(),
            'pnm_scores': pnm_scores,
            'stage_analysis': stage_analysis,
            'assessment_type': 'comprehensive'
        }
        profile.pnm_history.append(assessment_record)
        
        # Update stage profile
        profile.stage_profile = stage_analysis
        
        # Keep only last 10 assessment records
        if len(profile.pnm_history) > 10:
            profile.pnm_history = profile.pnm_history[-10:]
        
        # Update PNM status table for routing optimization
        if 'overall' in pnm_scores:
            overall_percentage = pnm_scores['overall'].get('percentage', 50.0)
            for pnm_dim in ['Physiological', 'Safety', 'Love & Belonging', 'Esteem', 
                           'Self-Actualisation', 'Cognitive', 'Aesthetic', 'Transcendence']:
                if pnm_dim in pnm_scores:
                    dim_score = pnm_scores[pnm_dim].get('percentage', 50.0)
                    status = 'completed' if pnm_scores[pnm_dim].get('domains_assessed', 0) > 0 else 'in_progress'
                    self.update_pnm_status(user_id, pnm_dim, status, dim_score)
        
        self.save_profile(profile)
        
        self.log.info(f"Comprehensive assessment results stored for user {user_id}")
        
        return profile
    
    def get_user_assessment_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user assessment summary for routing decisions"""
        profile = self.get_or_create_profile(user_id)
        
        # Get current PNM status from database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT pnm_dimension, completion_status, last_score, priority_level
                FROM user_pnm_status 
                WHERE user_id = ?
                ORDER BY priority_level DESC
            """, (user_id,))
            
            pnm_status = [
                {
                    'dimension': row[0],
                    'status': row[1], 
                    'score': row[2],
                    'priority': row[3]
                }
                for row in cursor.fetchall()
            ]
        
        return {
            'user_id': user_id,
            'profile_exists': profile is not None,
            'last_updated': profile.updated_at if profile else None,
            'pnm_status': pnm_status,
            'current_pnm_profile': profile.pnm_profile if profile else {},
            'stage_profile': profile.stage_profile if profile else {},
            'preferred_routes': self.get_user_preferred_routes(user_id),
            'interaction_patterns': profile.interaction_patterns if profile else {},
            'next_recommended_pnm': self.get_next_recommended_pnm(user_id)
        }


class ReliableRoutingEngine:
    """
    Reliable routing engine that uses direct database queries instead of AI/keyword matching.
    Designed to replace the failing term/PNM/stage routing system.
    """
    
    def __init__(self):
        self.profile_manager = UserProfileManager()
        self.log = logging.getLogger(__name__)
        
        # Standard term mappings for each PNM (fallback routing)
        self.pnm_standard_terms = {
            "Physiological": ["Breathing exercises", "Nutrition management", "Mobility support"],
            "Safety": ["Emergency preparedness", "Home modifications", "Medical equipment"],
            "Love & Belonging": ["Communication with support network", "Family relationships", "Social connections"],
            "Esteem": ["Maintaining independence", "Self-care strategies", "Professional identity"],
            "Self-Actualisation": ["Personal goals", "Creative expression", "Life purpose"],
            "Cognitive": ["Information processing", "Decision making", "Learning adaptation"],
            "Aesthetic": ["Environment quality", "Sensory comfort", "Beauty and harmony"],
            "Transcendence": ["Spiritual meaning", "Legacy planning", "Transcendent purpose"]
        }
    
    def get_reliable_route(self, user_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get reliable routing decision based on direct database queries.
        No dependency on AI or keyword matching - purely database-driven.
        """
        try:
            # Get next recommended PNM from database
            recommended_pnm, pnm_context = self.profile_manager.get_next_recommended_pnm(user_id)
            
            # Get standard term for this PNM
            available_terms = self.pnm_standard_terms.get(recommended_pnm, ["General assessment"])
            selected_term = available_terms[0]  # Use first available term
            
            # Build routing decision
            routing_decision = {
                'pnm_dimension': recommended_pnm,
                'term': selected_term,
                'routing_method': 'database_direct',
                'confidence': 0.95,  # High confidence in database-driven decisions
                'pnm_context': pnm_context,
                'available_terms': available_terms,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
            
            self.log.info(f"Reliable route determined: {user_id} -> {recommended_pnm} / {selected_term}")
            
            return routing_decision
            
        except Exception as e:
            self.log.error(f"Reliable routing failed for {user_id}: {e}")
            
            # Ultimate fallback
            return {
                'pnm_dimension': 'Physiological',
                'term': 'General assessment',
                'routing_method': 'emergency_fallback',
                'confidence': 0.5,
                'error': str(e)
            }
    
    def record_routing_success(self, user_id: str, routing_decision: Dict[str, Any]):
        """Record successful routing for future optimization"""
        self.profile_manager.record_successful_route(
            user_id,
            'pnm_dimension', 
            routing_decision['pnm_dimension']
        )
        self.profile_manager.record_successful_route(
            user_id,
            'term',
            routing_decision['term']
        )
    
    def force_pnm_route(self, user_id: str, pnm_dimension: str, term: str = None) -> Dict[str, Any]:
        """Force specific PNM route (for Data page triggers)"""
        if not term:
            available_terms = self.pnm_standard_terms.get(pnm_dimension, ["General assessment"])
            term = available_terms[0]
        
        routing_decision = {
            'pnm_dimension': pnm_dimension,
            'term': term,
            'routing_method': 'forced_route',
            'confidence': 1.0,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Update PNM status to in_progress
        self.profile_manager.update_pnm_status(user_id, pnm_dimension, 'in_progress')
        
        return routing_decision