"""Cross-Encoder Reranker for second-stage precision filtering.

Phase B: After RRF fusion returns ~30 candidates, the cross-encoder
scores each (query, document) pair jointly and returns the top-k by
relevance.  This provides 20-40% precision improvement over raw RRF
because the cross-encoder attends to both query and document tokens
simultaneously, unlike the bi-encoder (embedding) first stage.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (~80 MB, ~50ms on CPU)
"""

import logging
from typing import Dict, List, Optional

from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


class CrossEncoderReranker:
    """Lazy-loaded cross-encoder for second-stage reranking."""

    # Light, fast model — sufficient for academic search precision
    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None

    def _load_model(self):
        """Lazy-load the CrossEncoder model on first use."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import CrossEncoder

            console.print(f"[cyan]Loading reranker: {self.model_name}...[/]")
            self._model = CrossEncoder(self.model_name)
            console.print(f"[green]✓ Reranker loaded[/]")
        except ImportError:
            logger.error(
                "sentence-transformers is required for cross-encoder reranking. "
                "Install with: pip install sentence-transformers"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            raise

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 7,
        content_key: str = "content",
    ) -> List[Dict]:
        """Score each (query, document) pair and return top-k by relevance.

        Parameters
        ----------
        query : str
            The user's search query.
        documents : list[dict]
            Candidate documents from RRF fusion.  Each must have a
            ``content_key`` field with text to score.
        top_k : int
            Number of results to return.
        content_key : str
            Dict key containing the document text (default: "content").

        Returns
        -------
        list[dict]
            Top-k documents sorted by cross-encoder relevance score
            (descending).  Each document gets a ``ce_score`` field.
        """
        if not documents:
            return []

        self._load_model()

        # Build (query, doc_text) pairs for scoring
        pairs = []
        valid_docs = []
        for doc in documents:
            text = doc.get(content_key, "")
            if text:
                pairs.append((query, text))
                valid_docs.append(doc)

        if not pairs:
            return documents[:top_k]

        try:
            scores = self._model.predict(pairs)

            # Attach scores and sort
            for doc, score in zip(valid_docs, scores):
                doc["ce_score"] = float(score)

            valid_docs.sort(key=lambda d: d["ce_score"], reverse=True)

            logger.info(
                "Reranked %d → %d docs (best ce_score=%.4f)",
                len(valid_docs),
                min(top_k, len(valid_docs)),
                valid_docs[0]["ce_score"] if valid_docs else 0,
            )

            return valid_docs[:top_k]

        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}. Returning RRF order.")
            return documents[:top_k]
