"""Topology-Enhanced Collaboration Matcher.

Fuses ChromaDB semantic similarity with Personalized PageRank graph
centrality via Reciprocal Rank Fusion (RRF) to surface interdisciplinary
faculty hubs — not just the closest vector neighbors.

Architecture
------------
1.  Parse idea tags → resolve to Concept nodes in the NetworkX graph.
2.  Run Personalized PageRank seeded from those concept nodes.
3.  Filter PageRank results to Faculty nodes only, normalize [0, 1].
4.  Retrieve baseline ChromaDB semantic similarity (existing path).
5.  Fuse both ranked lists with RRF.
6.  PageRank computation runs in a ThreadPoolExecutor so it never
    blocks the main thread on large graphs.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx

from ..database import get_vector_store, VectorStore
from ..database.models import Idea
from ..utils.config import DATA_DIR

logger = logging.getLogger(__name__)

# Reuse a module-level executor so we pay the thread-pool startup cost once.
_executor = ThreadPoolExecutor(max_workers=2)


class IdeaMatcher:
    """Matches student ideas with faculty using semantic + graph signals."""

    def __init__(self):
        self.store: VectorStore = get_vector_store()
        self._nx_graph: Optional[nx.Graph] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_collaborators(self, idea_text: str, n_results: int = 5) -> List[Dict]:
        """Find faculty members whose research matches the idea."""
        results = self.store.search(
            query=idea_text,
            n_results=n_results,
            doc_type="professor",
        )
        return results

    def find_related_ideas(self, idea_text: str, n_results: int = 3) -> List[Dict]:
        """Find other similar ideas."""
        results = self.store.search(
            query=idea_text,
            n_results=n_results,
            doc_type="idea",
        )
        return results

    def match_idea(self, idea: Idea) -> Dict:
        """Run full matching — semantic similarity fused with graph centrality.

        Pipeline
        --------
        1. Build a text query from the idea and kick off semantic search.
        2. Resolve idea tags to Concept nodes in the knowledge graph.
        3. Compute Personalized PageRank seeded from those concepts.
        4. Filter to Faculty nodes, normalize scores to [0, 1].
        5. Fuse semantic + PageRank via RRF.
        6. Fall back to pure semantic results when the graph is unavailable.
        """
        query = f"{idea.title} {idea.description} {', '.join(idea.tags)}"

        # Fire semantic search immediately — it's I/O-bound on ChromaDB.
        semantic_results = self.find_collaborators(query, n_results=20)

        # --- Graph centrality path (async) ---
        graph = self._load_graph()
        if graph is not None and idea.tags:
            concept_nodes = self._resolve_concept_nodes(idea.tags, graph)

            if concept_nodes:
                # Run PageRank off the main thread to keep the event loop
                # (or Streamlit / Gradio UI thread) responsive.
                pr_future: Future = _executor.submit(
                    self._compute_faculty_pagerank, graph, concept_nodes
                )
                pagerank_scores = pr_future.result()  # blocks, but on worker thread

                if pagerank_scores:
                    fused = self._fuse_with_rrf(semantic_results, pagerank_scores)
                    return {
                        "collaborators": fused,
                        "related_ideas": self.find_related_ideas(query),
                    }

        # Graceful degradation — graph absent or no tags resolved.
        return {
            "collaborators": semantic_results,
            "related_ideas": self.find_related_ideas(query),
        }

    # ------------------------------------------------------------------
    # Graph loading
    # ------------------------------------------------------------------

    def _load_graph(self) -> Optional[nx.Graph]:
        """Lazy-load the NetworkX knowledge graph from disk.

        Mirrors the loading logic in GraphEnhancedQueryEngine so both
        components stay in sync with the same serialisation format.
        """
        if self._nx_graph is not None:
            return self._nx_graph

        graph_path = DATA_DIR / "tiger_brain.json"
        if not graph_path.exists():
            logger.warning("NetworkX graph not found at %s — using semantic-only matching", graph_path)
            return None

        try:
            with open(graph_path) as f:
                data = json.load(f)
            self._nx_graph = nx.node_link_graph(data)
            logger.info(
                "Loaded NetworkX graph: %d nodes, %d edges",
                self._nx_graph.number_of_nodes(),
                self._nx_graph.number_of_edges(),
            )
            return self._nx_graph
        except Exception as e:
            logger.error("Failed to load NetworkX graph: %s", e)
            return None

    # ------------------------------------------------------------------
    # Concept resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_concept_nodes(
        tags: List[str], graph: nx.Graph
    ) -> List[str]:
        """Map idea tags to Concept node IDs in the knowledge graph.

        Resolution strategy (mirrors GraphBuilder conventions):
        1.  Direct ID match — ``tag.lower().replace(' ', '_')`` which is
            the normalised concept-ID convention in ``graph_builder.py``.
        2.  Substring match on node ``label`` or ``name`` attributes for
            concept-type nodes, catching cases where the tag wording
            differs slightly from the canonical ID.
        """
        resolved: List[str] = []

        # Pre-index concept nodes for the substring fallback pass.
        concept_index: Dict[str, str] = {}  # lowercase label → node_id
        for nid, attrs in graph.nodes(data=True):
            if attrs.get("type") == "concept":
                label = (attrs.get("label") or attrs.get("name") or "").lower()
                if label:
                    concept_index[label] = nid

        for tag in tags:
            normalised_id = tag.lower().replace(" ", "_")

            # Strategy 1: exact node-ID match (fast path).
            if graph.has_node(normalised_id) and graph.nodes[normalised_id].get("type") == "concept":
                resolved.append(normalised_id)
                continue

            # Strategy 2: substring match against concept labels.
            tag_lower = tag.lower()
            for label, nid in concept_index.items():
                if tag_lower in label or label in tag_lower:
                    resolved.append(nid)
                    break  # one match per tag is sufficient

        logger.info("Resolved %d / %d tags to concept nodes", len(resolved), len(tags))
        return resolved

    # ------------------------------------------------------------------
    # PageRank
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_faculty_pagerank(
        graph: nx.Graph,
        concept_nodes: List[str],
    ) -> Dict[str, float]:
        """Run Personalized PageRank and return normalised Faculty scores.

        Parameters
        ----------
        graph : nx.Graph
            The full TigerBrain knowledge graph.
        concept_nodes : list[str]
            Concept node IDs that seed the personalisation vector.

        Returns
        -------
        dict[str, float]
            Faculty node ID → normalised PageRank score (0–1).
        """
        # Build the personalisation dict: seed concepts at 1.0, everyone else 0.
        personalization = {n: 0.0 for n in graph.nodes()}
        for cid in concept_nodes:
            personalization[cid] = 1.0

        try:
            pr = nx.pagerank(graph, alpha=0.85, personalization=personalization)
        except nx.NetworkXException as e:
            logger.error("PageRank computation failed: %s", e)
            return {}

        # Filter to Faculty nodes only.
        faculty_scores = {
            nid: score
            for nid, score in pr.items()
            if graph.nodes[nid].get("type") == "faculty" and score > 0
        }

        if not faculty_scores:
            return {}

        # Normalise to [0, 1].
        max_score = max(faculty_scores.values())
        if max_score > 0:
            faculty_scores = {nid: s / max_score for nid, s in faculty_scores.items()}

        return faculty_scores

    # ------------------------------------------------------------------
    # RRF fusion
    # ------------------------------------------------------------------

    @staticmethod
    def _fuse_with_rrf(
        semantic_results: List[Dict],
        pagerank_scores: Dict[str, float],
        rrf_k: int = 60,
    ) -> List[Dict]:
        """Fuse semantic similarity and PageRank via Reciprocal Rank Fusion.

        The formula ``1 / (rrf_k + rank + 1)`` is consistent with the
        existing RRF implementations in ``hybrid_retriever.py`` and
        ``query_engine.py``.

        Parameters
        ----------
        semantic_results : list[dict]
            ChromaDB results ranked by ascending distance.  Each dict
            contains ``metadata.name`` identifying the faculty member.
        pagerank_scores : dict[str, float]
            Faculty node ID → normalised PageRank score.
        rrf_k : int
            Smoothing constant (default 60, per Cormack et al., 2009).

        Returns
        -------
        list[dict]
            Re-ranked results sorted by fused RRF score (descending).
        """
        # Accumulator: faculty_key → {score, doc}
        fused: Dict[str, Dict] = {}

        # --- Semantic stream (already sorted by ascending distance) --------
        for rank, doc in enumerate(semantic_results):
            faculty_key = _faculty_key(doc)
            if not faculty_key:
                continue

            rrf_contribution = 1.0 / (rrf_k + rank + 1)

            if faculty_key not in fused:
                fused[faculty_key] = {"score": 0.0, "doc": doc}
            fused[faculty_key]["score"] += rrf_contribution

        # --- PageRank stream (sorted by descending normalised score) -------
        ranked_pr = sorted(pagerank_scores.items(), key=lambda kv: kv[1], reverse=True)

        for rank, (nid, _pr_score) in enumerate(ranked_pr):
            # The faculty node ID is usually the canonical name or a slug.
            # We normalise to lowercase for matching against the semantic key.
            faculty_key = nid.lower().strip()

            rrf_contribution = 1.0 / (rrf_k + rank + 1)

            if faculty_key in fused:
                fused[faculty_key]["score"] += rrf_contribution
            else:
                # Faculty discovered *only* via the graph (no semantic hit).
                # We still surface them, but with only the graph-side score.
                fused[faculty_key] = {
                    "score": rrf_contribution,
                    "doc": {
                        "content": "",
                        "id": nid,
                        "metadata": {"name": nid, "doc_type": "professor", "source": "graph"},
                        "distance": None,
                    },
                }

        # --- Sort by fused score, attach it to the doc, return -------------
        ranked = sorted(fused.values(), key=lambda v: v["score"], reverse=True)

        results: List[Dict] = []
        for item in ranked:
            doc = item["doc"]
            doc["rrf_score"] = round(item["score"], 6)
            results.append(doc)

        return results


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _faculty_key(doc: Dict) -> Optional[str]:
    """Extract a stable, lowercase key for a faculty result.

    Tries ``metadata.name`` first (the canonical field populated during
    ingestion), then falls back to the document ``id``.
    """
    meta = doc.get("metadata", {})
    name = meta.get("name")
    if name:
        return name.lower().strip()
    doc_id = doc.get("id", "")
    return doc_id.lower().strip() if doc_id else None
