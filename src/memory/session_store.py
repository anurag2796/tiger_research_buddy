"""Session-based conversational memory for TigerResearchBuddy.

Dual-tier architecture:
  Tier 1 — Sliding Window (always active, safe on Jetson Orin):
    collections.deque with maxlen=HW_PROFILE.memory_window
    Keyed by session_id, protected by per-session asyncio.Lock

  Tier 2 — LanceDB long-term (optional, set ENABLE_LONG_TERM_MEMORY=true):
    Embeds each message turn and persists to data/memory/lancedb/
    Semantic retrieval via nomic-embed-text — returns most relevant past turns
    Only recommended on M4 Max (> 32 GB unified memory)

Usage
-----
    from src.memory.session_store import MemoryModule
    from src.utils.hardware import HW_PROFILE

    memory = MemoryModule(HW_PROFILE)

    # Add a turn
    await memory.add_turn(session_id, "user", "Who works on NLP at RIT?")
    await memory.add_turn(session_id, "assistant", "Prof. Smith...")

    # Get sliding window for prompt injection
    history = memory.get_context_window(session_id)

    # Optional: semantic recall from long-term storage
    recalled = await memory.semantic_recall(session_id, query="NLP faculty")
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)

# We import HardwareProfile by type annotation only to avoid circular imports.
# The actual value is passed in at construction time.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.utils.hardware import HardwareProfile


# ---------------------------------------------------------------------------
# Turn schema (lightweight dict — no Pydantic overhead for in-memory ops)
# ---------------------------------------------------------------------------

def _make_turn(role: str, content: str) -> dict:
    return {"role": role, "content": content, "timestamp": time.time()}


# ---------------------------------------------------------------------------
# MemoryModule
# ---------------------------------------------------------------------------

class MemoryModule:
    """Dual-tier session memory manager.

    Parameters
    ----------
    hw_profile : HardwareProfile
        Hardware profile determines the sliding window size and whether
        long-term LanceDB storage is activated.
    """

    def __init__(self, hw_profile: "HardwareProfile") -> None:
        self._window_size: int = hw_profile.memory_window
        self._sessions: dict[str, deque] = {}
        self._locks: dict[str, asyncio.Lock] = {}

        # Tier 2: LanceDB (activated only if env var is explicitly set)
        self._lancedb_enabled: bool = (
            os.getenv("ENABLE_LONG_TERM_MEMORY", "false").strip().lower() == "true"
        )
        self._lancedb_table = None  # lazy-initialised
        self._embed_fn = None       # lazy-initialised embedding function

        if self._lancedb_enabled:
            logger.info("Long-term LanceDB memory enabled.")
            self._init_lancedb(hw_profile)
        else:
            logger.info(
                "Long-term memory disabled (set ENABLE_LONG_TERM_MEMORY=true to enable). "
                "Using sliding window only (size=%d).",
                self._window_size,
            )

    # ------------------------------------------------------------------
    # Tier 1: sliding-window (sync accessors — deque ops are thread-safe)
    # ------------------------------------------------------------------

    def _get_or_create_deque(self, session_id: str) -> deque:
        if session_id not in self._sessions:
            self._sessions[session_id] = deque(maxlen=self._window_size)
        return self._sessions[session_id]

    def _get_or_create_lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    def get_context_window(self, session_id: str) -> list[dict]:
        """Return the current sliding window as an ordered list of turn dicts.

        Safe to call synchronously — returns a snapshot of the deque.
        Suitable for direct injection into the LLM messages list.
        """
        dq = self._sessions.get(session_id)
        if dq is None:
            return []
        return list(dq)

    async def add_turn(self, session_id: str, role: str, content: str) -> None:
        """Append a turn to the sliding window (async-safe via per-session lock).

        Also persists to LanceDB if long-term memory is enabled.
        """
        lock = self._get_or_create_lock(session_id)
        async with lock:
            dq = self._get_or_create_deque(session_id)
            turn = _make_turn(role, content)
            dq.append(turn)

            if self._lancedb_enabled and self._lancedb_table is not None:
                try:
                    await asyncio.to_thread(self._persist_turn, session_id, turn)
                except Exception as exc:
                    logger.warning("LanceDB persist failed (non-fatal): %s", exc)

    def add_turn_sync(self, session_id: str, role: str, content: str) -> None:
        """Append a turn to the sliding window (synchronous version).

        Also persists to LanceDB if long-term memory is enabled.
        Used by the blocking RAG Engine.
        """
        dq = self._get_or_create_deque(session_id)
        turn = _make_turn(role, content)
        dq.append(turn)

        if self._lancedb_enabled and self._lancedb_table is not None:
            try:
                self._persist_turn(session_id, turn)
            except Exception as exc:
                logger.warning("LanceDB persist failed (non-fatal): %s", exc)

    def clear_session(self, session_id: str) -> None:
        """Wipe all in-memory history for a session."""
        self._sessions.pop(session_id, None)
        self._locks.pop(session_id, None)
        logger.info("Session %s cleared.", session_id)

    def active_sessions(self) -> list[str]:
        """Return a list of all live session IDs."""
        return list(self._sessions.keys())

    # ------------------------------------------------------------------
    # Tier 2: LanceDB long-term (optional)
    # ------------------------------------------------------------------

    def _init_lancedb(self, hw_profile: "HardwareProfile") -> None:
        """Initialise the LanceDB table and embedding function.

        Called only when ENABLE_LONG_TERM_MEMORY=true.
        Failures are non-fatal — we degrade gracefully to Tier 1 only.
        """
        try:
            import lancedb
            import pyarrow as pa
            from src.utils.config import DATA_DIR

            db_path = DATA_DIR / "memory" / "lancedb"
            db_path.mkdir(parents=True, exist_ok=True)

            db = lancedb.connect(str(db_path))

            schema = pa.schema([
                pa.field("session_id", pa.string()),
                pa.field("role", pa.string()),
                pa.field("content", pa.string()),
                pa.field("timestamp", pa.float64()),
                pa.field("vector", pa.list_(pa.float32(), 768)),  # nomic-embed-text-v1.5 dim
            ])

            if "chat_history" in db.table_names():
                self._lancedb_table = db.open_table("chat_history")
            else:
                self._lancedb_table = db.create_table("chat_history", schema=schema)

            # Load embedding function on the correct device
            from sentence_transformers import SentenceTransformer
            from src.utils.hardware import get_embedding_device
            from src.utils.config import EMBEDDING_MODEL

            device = get_embedding_device()
            self._embed_fn = SentenceTransformer(
                EMBEDDING_MODEL, trust_remote_code=True, device=device
            )
            logger.info("LanceDB memory initialized at %s (device=%s).", db_path, device)

        except ImportError as exc:
            logger.warning(
                "LanceDB or PyArrow not installed — disabling long-term memory. "
                "Install with: pip install lancedb pyarrow. Error: %s",
                exc,
            )
            self._lancedb_enabled = False
        except Exception as exc:
            logger.warning("LanceDB init failed — disabling long-term memory: %s", exc)
            self._lancedb_enabled = False

    def _persist_turn(self, session_id: str, turn: dict) -> None:
        """Write a turn to LanceDB (runs in a thread pool via asyncio.to_thread)."""
        if self._lancedb_table is None or self._embed_fn is None:
            return
        try:
            vector = self._embed_fn.encode(turn["content"]).tolist()
            self._lancedb_table.add([{
                "session_id": session_id,
                "role": turn["role"],
                "content": turn["content"],
                "timestamp": turn["timestamp"],
                "vector": vector,
            }])
        except Exception as exc:
            logger.warning("LanceDB write failed: %s", exc)

    async def semantic_recall(
        self, session_id: str, query: str, k: int = 3
    ) -> list[dict]:
        """Retrieve the *k* most semantically relevant past turns for *query*.

        Only returns results when long-term memory is enabled and the session
        has persisted turns.  Returns an empty list on Orin (disabled by default).
        """
        if not self._lancedb_enabled or self._lancedb_table is None or self._embed_fn is None:
            return []

        try:
            results = await asyncio.to_thread(self._search_lancedb, session_id, query, k)
            return results
        except Exception as exc:
            logger.warning("LanceDB semantic recall failed: %s", exc)
            return []

    def semantic_recall_sync(self, session_id: str, query: str, k: int = 3) -> list[dict]:
        """Retrieve the *k* most semantically relevant past turns for *query* (synchronous version).

        Only returns results when long-term memory is enabled.
        """
        if not self._lancedb_enabled or self._lancedb_table is None or self._embed_fn is None:
            return []

        try:
            return self._search_lancedb(session_id, query, k)
        except Exception as exc:
            logger.warning("LanceDB semantic recall failed (sync): %s", exc)
            return []

    def _search_lancedb(self, session_id: str, query: str, k: int) -> list[dict]:
        """Synchronous LanceDB vector search (runs in thread pool)."""
        vector = self._embed_fn.encode(query).tolist()
        df = (
            self._lancedb_table
            .search(vector)
            .where(f"session_id = '{session_id}'")
            .limit(k)
            .to_pandas()
        )
        return [
            {"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]}
            for _, row in df.iterrows()
        ]
