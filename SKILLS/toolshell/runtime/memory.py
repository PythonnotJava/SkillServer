"""
ToolShell 记忆管理器
===================
SQLite 基础存储 + 可选 Embedding 向量检索。
"""

import json
import sqlite3
import hashlib
import uuid
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict


class MemoryManager:
    def __init__(self, project_root: Path, config: dict):
        self.config = config
        self.root = Path(project_root).resolve()
        self.project_id = hashlib.md5(str(self.root).encode()).hexdigest()[:12]
        self.session_id = str(uuid.uuid4())

        # Embedding 配置
        self.embed_url = config.get("QDRANT_EMBED_MODEL_URL", "")
        self.embed_key = config.get("QDRANT_EMBED_MODEL_KEY", "")
        self.embed_model = config.get("QDRANT_EMBED_MODEL_NAME", "")
        self.qdrant_ok = bool(self.embed_url and self.embed_key and self.embed_model)

        # 初始化 SQLite
        db_dir = self.root / ".toolshell"
        db_dir.mkdir(exist_ok=True)
        self.db = sqlite3.connect(str(db_dir / "memory.db"))
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                type TEXT,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                embedding TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                accessed_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS file_ops_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                operation TEXT,
                path TEXT,
                detail TEXT,
                result TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_mem_project ON memories(project_id);
            CREATE INDEX IF NOT EXISTS idx_mem_importance ON memories(type, importance DESC);
        """)
        self.db.commit()

    # ─── Embedding ───────────────────────────────────────────

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """调用嵌入 API 获取向量"""
        if not self.qdrant_ok:
            return None
        req = urllib.request.Request(
            self.embed_url,
            data=json.dumps({"model": self.embed_model, "input": text}).encode(),
            headers={
                "Authorization": f"Bearer {self.embed_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return data["data"][0]["embedding"]
        except Exception:
            return None

    # ─── 存储 ────────────────────────────────────────────────

    def store(self, content: str, type: str = "context", importance: float = 0.5) -> int:
        """存储一条记忆"""
        expires = None
        if not self.config.get("MIND", True):
            expires = (datetime.now() + timedelta(hours=24)).isoformat()

        embedding = self.get_embedding(content)
        embed_json = json.dumps(embedding) if embedding else None

        cursor = self.db.execute("""
            INSERT INTO memories (project_id, session_id, type, content, importance, embedding, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (self.project_id, self.session_id, type, content, importance, embed_json, expires))
        self.db.commit()
        return cursor.lastrowid

    # ─── 召回 ────────────────────────────────────────────────

    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """混合检索: 关键词 + 向量相似度"""
        results = []

        # 关键词检索
        words = query.split()
        if words:
            conditions = " OR ".join(["content LIKE ?"] * len(words))
            params = [f"%{w}%" for w in words]
            rows = self.db.execute(f"""
                SELECT id, type, content, importance, created_at, embedding
                FROM memories
                WHERE project_id = ?
                  AND (expires_at IS NULL OR expires_at > datetime('now'))
                  AND ({conditions})
                ORDER BY importance DESC
                LIMIT ?
            """, [self.project_id] + params + [limit * 2]).fetchall()
            for row in rows:
                results.append({
                    "id": row["id"], "type": row["type"],
                    "content": row["content"], "importance": row["importance"],
                    "created_at": row["created_at"], "score": float(row["importance"]),
                    "_emb": row["embedding"],
                })

        # 向量重排
        query_emb = self.get_embedding(query)
        if query_emb:
            for r in results:
                if r["_emb"]:
                    r["score"] = self._cosine(query_emb, json.loads(r["_emb"]))

            # 补充: 纯语义检索
            all_rows = self.db.execute("""
                SELECT id, type, content, importance, created_at, embedding
                FROM memories
                WHERE project_id = ? AND embedding IS NOT NULL
                  AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (self.project_id,)).fetchall()
            seen = {r["id"] for r in results}
            for row in all_rows:
                if row["id"] in seen:
                    continue
                sim = self._cosine(query_emb, json.loads(row["embedding"]))
                if sim >= 0.6:
                    results.append({
                        "id": row["id"], "type": row["type"],
                        "content": row["content"], "importance": row["importance"],
                        "created_at": row["created_at"], "score": sim, "_emb": None,
                    })

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        for r in results:
            r.pop("_emb", None)
        return results[:limit]

    def _cosine(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    # ─── 审计日志 ────────────────────────────────────────────

    def log_op(self, operation: str, path: str, detail: str, result: str):
        self.db.execute("""
            INSERT INTO file_ops_log (session_id, operation, path, detail, result)
            VALUES (?, ?, ?, ?, ?)
        """, (self.session_id, operation, path, detail, result))
        self.db.commit()
