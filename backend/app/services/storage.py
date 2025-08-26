# app/services/storage.py
from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from app.config import get_settings


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _json_dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _json_load(s: Optional[str]) -> Any:
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


class Storage:
    """
    Lightweight SQLite storage (single-node ready).
    - Initializes schema from app/data/schema.sql
    - Provides helpers for sessions, turns, scores, evidence log
    """

    def __init__(self, db_path: Optional[str] = None, schema_path: Optional[str] = None):
        s = get_settings()
        self.db_path = db_path or s.DB_PATH
        self.schema_path = schema_path or s.SCHEMA_PATH

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # isolation_level=None -> autocommit
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    # ---------- lifecycle ----------

    def _init_schema(self) -> None:
        self.conn.execute("PRAGMA foreign_keys = ON;")
        if not self.schema_path or not os.path.exists(self.schema_path):
            # Minimal fallback; normally schema.sql must exist.
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                " id TEXT PRIMARY KEY,"
                " email TEXT UNIQUE,"
                " display_name TEXT,"
                " created_at DATETIME DEFAULT (datetime('now')))"
            )
            return
        with open(self.schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        
        # Execute statements individually to avoid executescript issues
        # Remove comments and split properly
        lines = sql.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Skip comment lines
            if line.startswith('--') or not line:
                continue
            # Remove inline comments
            if '--' in line:
                line = line.split('--')[0].strip()
            if line:
                cleaned_lines.append(line)
        
        cleaned_sql = ' '.join(cleaned_lines)
        statements = [stmt.strip() for stmt in cleaned_sql.split(';') if stmt.strip()]
        
        for i, stmt in enumerate(statements):
            try:
                self.conn.execute(stmt)
            except Exception as e:
                print(f"Warning: Failed to execute SQL statement: {e}")
                print(f"Statement: {stmt[:200]}...")
        
        # Workaround: Ensure pnm_scores and evidence_count columns exist
        try:
            cursor = self.conn.cursor()
            cursor.execute('PRAGMA table_info(sessions)')
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'pnm_scores' not in columns:
                self.conn.execute('ALTER TABLE sessions ADD COLUMN pnm_scores TEXT DEFAULT "[]"')
                
            if 'evidence_count' not in columns:
                self.conn.execute('ALTER TABLE sessions ADD COLUMN evidence_count TEXT DEFAULT "{}"')
        except Exception as e:
            print(f"Warning: Failed to add missing columns: {e}")

    def ping(self) -> None:
        self.conn.execute("SELECT 1").fetchone()

    # ---------- sessions ----------

    def upsert_session(
        self,
        *,
        session_id: str,
        user_id: Optional[str] = None,
        status: str = "active",
        fsm_state: str = "ROUTE",
        current_pnm: Optional[str] = None,
        current_term: Optional[str] = None,
        current_qid: Optional[str] = None,
        asked_qids: Optional[List[str]] = None,
        followup_ptr: int = 0,
        lock_until_turn: int = 0,
        turn_index: int = 0,
        last_info_turn: int = -999,
        pnm_scores: Optional[List] = None,
        evidence_count: Optional[Dict] = None,
        keyword_pool: Optional[List[str]] = None,  # AI routing keywords
        ai_confidence: Optional[float] = None,  # AI routing confidence
        routing_method: Optional[str] = None,  # Routing method used
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO sessions (
                session_id, user_id, status, fsm_state,
                current_pnm, current_term, current_qid,
                asked_qids, followup_ptr, lock_until_turn,
                turn_index, last_info_turn, pnm_scores, evidence_count, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                user_id = excluded.user_id,
                status = excluded.status,
                fsm_state = excluded.fsm_state,
                current_pnm = excluded.current_pnm,
                current_term = excluded.current_term,
                current_qid = excluded.current_qid,
                asked_qids = excluded.asked_qids,
                followup_ptr = excluded.followup_ptr,
                lock_until_turn = excluded.lock_until_turn,
                turn_index = excluded.turn_index,
                last_info_turn = excluded.last_info_turn,
                pnm_scores = excluded.pnm_scores,
                evidence_count = excluded.evidence_count,
                updated_at = datetime('now')
            """,
            (
                session_id, user_id, status, fsm_state,
                current_pnm, current_term, current_qid,
                _json_dump(asked_qids or []), followup_ptr, lock_until_turn,
                turn_index, last_info_turn, _json_dump(pnm_scores or []), _json_dump(evidence_count or {})
            ),
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE session_id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        d["asked_qids"] = _json_load(d.get("asked_qids")) or []
        d["pnm_scores"] = _json_load(d.get("pnm_scores")) or []
        d["evidence_count"] = _json_load(d.get("evidence_count")) or {}
        return d

    def has_session(self, session_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        return bool(row)

    def ensure_session(self, session_id: str, fsm_state: str = "ROUTE") -> None:
        """Create a minimal session row if not exists (dev-friendly)."""
        if not self.has_session(session_id):
            self.conn.execute(
                "INSERT INTO sessions(session_id, status, fsm_state, asked_qids, updated_at) "
                "VALUES(?, 'active', ?, '[]', datetime('now'))",
                (session_id, fsm_state),
            )

    # ---------- turns ----------

    def add_turn(
        self,
        *,
        session_id: str,
        turn_index: int,
        role: str,
        content: str,
        meta: dict | None = None,
    ) -> int:
        """
        Insert a turn row. The session must exist in 'sessions'.
        Columns must match schema: (session_id, turn_index, role, text, meta)
        """
        if not self.has_session(session_id):
            raise ValueError(f"Session '{session_id}' not found; call /chat/route first.")

        cur = self.conn.execute(
            """
            INSERT INTO turns (session_id, turn_index, role, text, meta)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, turn_index, role, content, _json_dump(meta or {})),
        )
        return int(cur.lastrowid)

    def list_turns(self, session_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index ASC",
            (session_id,),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            d = _row_to_dict(r)
            # column is meta_json in schema
            d["meta"] = _json_load(d.get("meta_json")) or {}
            out.append(d)
        return out

    # ---------- term scores ----------

    def upsert_term_score(
        self,
        *,
        session_id: str,
        pnm: str,
        term: str,
        score_0_7: float,
        rationale: Optional[str],
        evidence_turn_ids: List[int],
        status: str,
        method_version: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO term_scores (
                session_id, pnm, term, score_0_7,
                rationale, evidence_turn_ids, status,
                method_version, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(session_id, pnm, term) DO UPDATE SET
                score_0_7 = excluded.score_0_7,
                rationale = excluded.rationale,
                evidence_turn_ids = excluded.evidence_turn_ids,
                status = excluded.status,
                method_version = excluded.method_version,
                updated_at = datetime('now')
            """,
            (
                session_id, pnm, term, float(score_0_7),
                rationale, _json_dump(evidence_turn_ids or []), status,
                method_version,
            ),
        )

    def list_term_scores(self, session_id: str, *, pnm: Optional[str] = None) -> List[Dict[str, Any]]:
        if pnm:
            rows = self.conn.execute(
                "SELECT * FROM term_scores WHERE session_id = ? AND pnm = ? ORDER BY updated_at DESC",
                (session_id, pnm),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM term_scores WHERE session_id = ? ORDER BY updated_at DESC",
                (session_id,),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            d = _row_to_dict(r)
            d["evidence_turn_ids"] = _json_load(d.get("evidence_turn_ids")) or []
            out.append(d)
        return out

    # ---------- dimension scores ----------

    def upsert_dimension_score(
        self,
        *,
        session_id: str,
        pnm: str,
        score_0_7: float,
        coverage_ratio: float,
        stage: Optional[str] = None,
        method_version: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO dimension_scores (
                session_id, pnm, score_0_7, coverage_ratio, stage, method_version, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(session_id, pnm) DO UPDATE SET
                score_0_7 = excluded.score_0_7,
                coverage_ratio = excluded.coverage_ratio,
                stage = excluded.stage,
                method_version = excluded.method_version,
                updated_at = datetime('now')
            """,
            (session_id, pnm, float(score_0_7), float(coverage_ratio), stage, method_version),
        )

    def get_dimension_score(self, session_id: str, pnm: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM dimension_scores WHERE session_id = ? AND pnm = ? LIMIT 1",
            (session_id, pnm),
        ).fetchone()
        return _row_to_dict(row) if row else None

    def list_dimension_scores(self, session_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM dimension_scores WHERE session_id = ? ORDER BY updated_at DESC",
            (session_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def list_dimensions_with_scores(self, session_id: str) -> List[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT pnm FROM dimension_scores WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        return [r["pnm"] for r in rows]

    # ---------- evidence log ----------

    def add_evidence_log(
        self,
        *,
        session_id: str,
        pnm: Optional[str],
        term: Optional[str],
        turn_id: Optional[int],
        snippet: str,
        tag: Optional[str] = None,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO evidence_log (session_id, pnm, term, turn_id, snippet, tag)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, pnm, term, turn_id, snippet, tag),
        )
        return int(cur.lastrowid)
