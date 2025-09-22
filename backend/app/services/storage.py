# app/services/storage.py - Document-based Storage Service
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from app.config import get_settings


@dataclass
class ConversationMessage:
    """Single message in conversation"""
    id: int
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    type: str = 'response'  # 'question' | 'response' | 'info' | 'system'
    timestamp: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ConversationDocument:
    """Complete conversation document"""
    id: str
    user_id: str
    title: str = None
    type: str = 'assessment'  # 'assessment' | 'general_chat' | 'follow_up'  
    dimension: str = None
    status: str = 'active'  # 'active' | 'completed' | 'paused' | 'archived'
    
    # Timestamps
    created_at: str = None
    updated_at: str = None
    completed_at: str = None
    
    # Assessment state
    assessment_state: Dict[str, Any] = None
    
    # Messages and content
    messages: List[ConversationMessage] = None
    info_cards: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.assessment_state is None:
            self.assessment_state = {
                'current_pnm': None,
                'current_term': None,
                'fsm_state': 'ROUTE',
                'turn_index': 0,
                'asked_questions': [],
                'completed_terms': [],
                'scores': {},
                'dialogue_mode': 'free_dialogue'  # Ensure new conversations start in dialogue mode
            }
        if self.messages is None:
            self.messages = []
        if self.info_cards is None:
            self.info_cards = []
        if self.metadata is None:
            self.metadata = {
                'total_messages': 0,
                'user_messages': 0,
                'assistant_messages': 0,
                'info_cards_count': 0,
                'session_duration': None,
                'completion_percentage': 0
            }


class DocumentStorage:
    """Document-based storage service for conversations"""
    
    def __init__(self, db_path: str = None, schema_path: str = None):
        self.cfg = get_settings()
        self.db_path = db_path or self.cfg.DB_PATH
        self.schema_path = schema_path or self.cfg.SCHEMA_PATH
        self.conn = self._get_connection()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _init_db(self):
        """Initialize database with schema"""
        # Skip schema initialization if using existing als.db database
        # Comment out to avoid conflicts with existing table structure
        pass
        # if os.path.exists(self.schema_path):
        #     with open(self.schema_path, 'r', encoding='utf-8') as f:
        #         schema = f.read()
        #         self.conn.executescript(schema)
        #         self.conn.commit()
    
    def ping(self) -> bool:
        """Test database connection"""
        try:
            self.conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False
    
    # ---------- Conversation Document Operations ----------
    
    def create_conversation(self, user_id: str, **kwargs) -> ConversationDocument:
        """Create new conversation document"""
        # Validate user exists
        user_exists = self.conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user_exists:
            raise ValueError(f"User {user_id} does not exist")
        
        conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        doc = ConversationDocument(
            id=conversation_id,
            user_id=user_id,
            **kwargs
        )
        
        # Insert into database
        self.conn.execute("""
            INSERT INTO conversation_documents (
                id, user_id, title, type, dimension, status,
                document, created_at, updated_at, message_count,
                current_pnm, current_term, fsm_state, turn_index
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc.id, doc.user_id, doc.title, doc.type, doc.dimension, doc.status,
            json.dumps(asdict(doc)), doc.created_at, doc.updated_at, 0,
            doc.assessment_state.get('current_pnm'),
            doc.assessment_state.get('current_term'),
            doc.assessment_state.get('fsm_state'),
            doc.assessment_state.get('turn_index')
        ))
        self.conn.commit()

        return doc

    def create_conversation_with_id(self, conversation_id: str, user_id: str, **kwargs) -> ConversationDocument:
        """Create new conversation document with specific ID"""
        # Validate user exists
        user_exists = self.conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user_exists:
            raise ValueError(f"User {user_id} does not exist")

        # Check if conversation ID already exists
        existing = self.conn.execute("SELECT id FROM conversation_documents WHERE id = ?", (conversation_id,)).fetchone()
        if existing:
            raise ValueError(f"Conversation {conversation_id} already exists")

        doc = ConversationDocument(
            id=conversation_id,
            user_id=user_id,
            **kwargs
        )

        # Insert into database
        self.conn.execute("""
            INSERT INTO conversation_documents (
                id, user_id, title, type, dimension, status,
                document, created_at, updated_at, message_count,
                current_pnm, current_term, fsm_state, turn_index
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc.id, doc.user_id, doc.title, doc.type, doc.dimension, doc.status,
            json.dumps(asdict(doc)), doc.created_at, doc.updated_at, 0,
            doc.assessment_state.get('current_pnm'),
            doc.assessment_state.get('current_term'),
            doc.assessment_state.get('fsm_state'),
            doc.assessment_state.get('turn_index', 0)
        ))
        self.conn.commit()

        return doc

    def get_conversation(self, conversation_id: str) -> Optional[ConversationDocument]:
        """Get conversation by ID"""
        row = self.conn.execute(
            "SELECT document FROM conversation_documents WHERE id = ?",
            (conversation_id,)
        ).fetchone()
        
        if not row:
            return None
            
        doc_data = json.loads(row['document'])
        # Convert messages back to ConversationMessage objects
        if 'messages' in doc_data and doc_data['messages']:
            doc_data['messages'] = [
                ConversationMessage(**msg) if isinstance(msg, dict) else msg 
                for msg in doc_data['messages']
            ]
        
        return ConversationDocument(**doc_data)
    
    def update_conversation(self, doc: ConversationDocument) -> ConversationDocument:
        """Update conversation document"""
        doc.updated_at = datetime.now().isoformat()
        doc.metadata['total_messages'] = len(doc.messages)
        doc.metadata['user_messages'] = sum(1 for m in doc.messages if m.role == 'user')
        doc.metadata['assistant_messages'] = sum(1 for m in doc.messages if m.role == 'assistant')
        doc.metadata['info_cards_count'] = len(doc.info_cards)
        
        self.conn.execute("""
            UPDATE conversation_documents SET
                title = ?, status = ?, document = ?, updated_at = ?,
                message_count = ?, last_message_at = ?,
                current_pnm = ?, current_term = ?, fsm_state = ?, turn_index = ?
            WHERE id = ?
        """, (
            doc.title, doc.status, json.dumps(asdict(doc)), doc.updated_at,
            len(doc.messages), doc.messages[-1].timestamp if doc.messages else None,
            doc.assessment_state.get('current_pnm'),
            doc.assessment_state.get('current_term'),
            doc.assessment_state.get('fsm_state'),
            doc.assessment_state.get('turn_index'),
            doc.id
        ))
        self.conn.commit()
        
        return doc
    
    def list_conversations(self, user_id: str, status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List conversations for user"""
        query = """
            SELECT id, user_id, title, type, dimension, status,
                   created_at, updated_at, message_count, last_message_at
            FROM conversation_documents 
            WHERE user_id = ?
        """
        params = [user_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
            
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    
    def get_active_conversation(self, user_id: str) -> Optional[ConversationDocument]:
        """Get user's active conversation"""
        row = self.conn.execute(
            "SELECT document FROM conversation_documents WHERE user_id = ? AND status = 'active' ORDER BY updated_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        
        if not row:
            return None
            
        doc_data = json.loads(row['document'])
        if 'messages' in doc_data and doc_data['messages']:
            doc_data['messages'] = [
                ConversationMessage(**msg) if isinstance(msg, dict) else msg 
                for msg in doc_data['messages']
            ]
        
        return ConversationDocument(**doc_data)
    
    # ---------- Message Operations ----------
    
    def add_message(self, conversation_id: str, message_or_role, content: str = None, **kwargs) -> ConversationDocument:
        """Add message to conversation - accepts ConversationMessage object or individual parameters"""
        doc = self.get_conversation(conversation_id)
        if not doc:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Handle both ConversationMessage object and individual parameters
        if isinstance(message_or_role, ConversationMessage):
            # Called with ConversationMessage object
            message = message_or_role
        else:
            # Called with individual parameters (role, content)
            if content is None:
                raise ValueError("Content is required when passing role as string")
            message = ConversationMessage(
                id=len(doc.messages) + 1,
                role=message_or_role,
                content=content,
                type=kwargs.get('type', 'text'),
                **{k: v for k, v in kwargs.items() if k != 'type'}
            )
        
        # Ensure message has correct ID
        message.id = len(doc.messages) + 1
        
        doc.messages.append(message)
        doc.assessment_state['turn_index'] = len(doc.messages)
        
        return self.update_conversation(doc)
    
    def get_messages(self, conversation_id: str, limit: int = None) -> List[ConversationMessage]:
        """Get messages for conversation"""
        doc = self.get_conversation(conversation_id)
        if not doc:
            return []
        
        messages = doc.messages
        if limit:
            messages = messages[-limit:]  # Get last N messages
            
        return messages
    
    # ---------- Assessment State Operations ----------
    
    def update_assessment_state(self, conversation_id: str, **state_updates) -> ConversationDocument:
        """Update assessment state"""
        doc = self.get_conversation(conversation_id)
        if not doc:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        doc.assessment_state.update(state_updates)
        return self.update_conversation(doc)
    
    def add_score(self, conversation_id: str, pnm: str, term: str, score: float, **kwargs) -> ConversationDocument:
        """Add score to conversation"""
        doc = self.get_conversation(conversation_id)
        if not doc:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        if pnm not in doc.assessment_state['scores']:
            doc.assessment_state['scores'][pnm] = {}
            
        doc.assessment_state['scores'][pnm][term] = {
            'score': score,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        # Update index table
        self.conn.execute("""
            INSERT OR REPLACE INTO conversation_scores
            (conversation_id, pnm, term, score, status, updated_at, scoring_method, rationale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (conversation_id, pnm, term, score, kwargs.get('status', 'completed'),
              datetime.now().isoformat(), kwargs.get('scoring_method'), kwargs.get('rationale')))
        
        return self.update_conversation(doc)
    
    def get_scores(self, conversation_id: str) -> Dict[str, Any]:
        """Get scores for conversation"""
        doc = self.get_conversation(conversation_id)
        if not doc:
            return {'term_scores': [], 'dimension_scores': []}
        
        term_scores = []
        dimension_scores = []
        
        for pnm, terms in doc.assessment_state['scores'].items():
            for term, score_data in terms.items():
                term_scores.append({
                    'pnm': pnm,
                    'term': term,
                    'score_0_7': score_data['score'],
                    'rationale': score_data.get('rationale'),
                    'status': score_data.get('status', 'completed')
                })
        
        return {'term_scores': term_scores, 'dimension_scores': dimension_scores}
    
    # ---------- Info Cards Operations ----------
    
    def add_info_card(self, conversation_id: str, card_type: str, card_data: Dict[str, Any]) -> ConversationDocument:
        """Add info card to conversation"""
        doc = self.get_conversation(conversation_id)
        if not doc:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        info_card = {
            'id': f"info_{len(doc.info_cards) + 1}",
            'type': card_type,
            'title': card_data.get('title', ''),
            'content': card_data,
            'triggered_at_turn': len(doc.messages),
            'timestamp': datetime.now().isoformat()
        }
        
        doc.info_cards.append(info_card)
        return self.update_conversation(doc)
    
    # ---------- Legacy Compatibility (minimal) ----------
    
    def has_session(self, session_id: str) -> bool:
        """Legacy compatibility - check if conversation exists"""
        row = self.conn.execute(
            "SELECT id FROM conversation_documents WHERE id = ? OR current_pnm IS NOT NULL",
            (session_id,)
        ).fetchone()
        return row is not None
    
    def verify_session_owner(self, session_id: str, user_id: str) -> bool:
        """Legacy compatibility - verify session owner"""
        row = self.conn.execute(
            "SELECT user_id FROM conversation_documents WHERE id = ?",
            (session_id,)
        ).fetchone()
        return row and row['user_id'] == user_id
    
    # ---------- User Management ----------
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address"""
        row = self.conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        return dict(row) if row else None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        row = self.conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    
    def create_user(self, user_id: str, email: str, password_hash: str, display_name: str) -> None:
        """Create new user"""
        self.conn.execute(
            """INSERT INTO users (id, email, password_hash, display_name, is_active, created_at, updated_at)
               VALUES (?, ?, ?, ?, 1, datetime('now'), datetime('now'))""",
            (user_id, email, password_hash, display_name)
        )
        self.conn.commit()
    
    def update_user_last_login(self, user_id: str) -> None:
        """Update user last login timestamp"""
        self.conn.execute(
            "UPDATE users SET last_login = datetime('now'), updated_at = datetime('now') WHERE id = ?",
            (user_id,)
        )
        self.conn.commit()


# Create singleton instance (for compatibility)
Storage = DocumentStorage