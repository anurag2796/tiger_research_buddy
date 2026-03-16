"""Graph-enhanced query engine with Dual-Level Retrieval.

Implements LightRAG-inspired hierarchical keyword extraction:
  - Low-level keywords  → BM25 (exact entity matching)
  - High-level keywords → ChromaDB (semantic) + ego-graph traversal (structural)

Results from both streams are fused via Reciprocal Rank Fusion (RRF).
"""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from .ollama_client import get_ollama_client
from ..knowledge_graph.graph_store import GraphStore
from ..knowledge_graph.queries import GraphQueries
from ..database.vector_store import get_vector_store, VectorStore
from ..retrieval.hybrid_retriever import HybridRetriever
from ..utils.config import GRAPH_DB_PATH, DATA_DIR
from ..utils.timer import Timer
from ..utils.db_logger import setup_db_logging

logger = setup_db_logging("GraphQueryEngine")

# ---------------------------------------------------------------------------
#  System prompt that forces Ollama to return strictly valid JSON.
#  The aggressive framing ("YOU MUST", repeated constraints) is intentional:
#  smaller local models need heavy-handed instruction to avoid prose leakage.
# ---------------------------------------------------------------------------
DUAL_KEYWORD_SYSTEM_PROMPT = """\
You are a JSON keyword-extraction engine. Your ONLY job is to read \
a user's research query and return a JSON object — nothing else.

RULES (violating ANY rule is a critical failure):
1. Return ONLY a single JSON object. No explanation, no markdown fences, no preamble.
2. The JSON object MUST have exactly two keys:
   "high_level_keywords" — a list of broad, abstract research themes \
(e.g. "deep learning", "computer vision", "reinforcement learning").
   "low_level_keywords"  — a list of specific entities such as person names, \
paper titles, dataset names, method acronyms \
(e.g. "Yann LeCun", "ImageNet", "ResNet-50").
3. Each list must contain 1-5 strings. Never return an empty list; \
if unsure, repeat the user's query terms.
4. Do NOT wrap the JSON in ```json``` fences or add ANY text outside the JSON.

EXAMPLE INPUT:  "Who is working on autonomous vehicles at RIT?"
EXAMPLE OUTPUT: {"high_level_keywords":["autonomous vehicles","robotics","self-driving systems"],"low_level_keywords":["RIT","autonomous vehicles"]}

Now process the following query and respond with ONLY the JSON object.\
"""


class GraphEnhancedQueryEngine:
    """Enhanced query engine that combines vector search with knowledge graph.

    Public API additions (v2 — Dual-Level Retrieval):
        extract_dual_keywords(query) → dict with high/low keyword lists
        dual_level_search(query, …)  → fused retrieval results
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
    ):
        self.client = get_ollama_client()
        self.store = None
        self.queries = None
        self.analytics = None
        self.data_mining = None

        # Retrieval backends (lazy-initialised via singletons if not injected)
        self._vector_store = vector_store
        self._hybrid_retriever = hybrid_retriever

        # NetworkX graph for ego-graph traversals — loaded lazily
        self._nx_graph: Optional[nx.Graph] = None

        self._initialize_graph()

    # ------------------------------------------------------------------
    #  Initialisation helpers
    # ------------------------------------------------------------------

    def _initialize_graph(self):
        """Load KuzuDB knowledge graph and initialise query interfaces."""
        try:
            self.store = GraphStore(GRAPH_DB_PATH)
            self.queries = GraphQueries(self.store)
        except Exception as e:
            logger.error(f"Could not initialize knowledge graph: {e}")
            print(f"Warning: Could not initialize knowledge graph: {e}")

    def _get_vector_store(self) -> VectorStore:
        """Return the vector store, creating the singleton if needed."""
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store

    def _get_hybrid_retriever(self) -> HybridRetriever:
        """Return the hybrid retriever, constructing one if needed."""
        if self._hybrid_retriever is None:
            self._hybrid_retriever = HybridRetriever(self._get_vector_store())
        return self._hybrid_retriever

    def _load_networkx_graph(self) -> Optional[nx.Graph]:
        """Load the NetworkX graph exported by GraphBuilder (node-link JSON).

        The graph lives at ``data/tiger_brain.json`` and is produced by
        ``GraphBuilder.export()`` in the knowledge-graph pipeline.
        """
        if self._nx_graph is not None:
            return self._nx_graph

        graph_path = DATA_DIR / "tiger_brain.json"
        if not graph_path.exists():
            logger.warning(f"NetworkX graph not found at {graph_path}")
            return None

        try:
            with open(graph_path) as f:
                data = json.load(f)
            self._nx_graph = nx.node_link_graph(data)
            logger.info(
                f"Loaded NetworkX graph: {self._nx_graph.number_of_nodes()} nodes, "
                f"{self._nx_graph.number_of_edges()} edges"
            )
            return self._nx_graph
        except Exception as e:
            logger.error(f"Failed to load NetworkX graph: {e}")
            return None

    # ------------------------------------------------------------------
    #  Dual-Level Keyword Extraction (Task 2, Requirement 1 + 6)
    # ------------------------------------------------------------------

    def extract_dual_keywords(self, query: str) -> Dict[str, List[str]]:
        """Ask Ollama to decompose *query* into high- and low-level keywords.

        Returns a dict with keys ``"high_level_keywords"`` and
        ``"low_level_keywords"``, each a list of strings.
        Gracefully falls back if the LLM output is malformed.
        """
        if not self.client._initialized:
            self.client.initialize()

        try:
            with Timer("LLM Dual-Keyword Extraction", use_rich=False):
                raw = self.client.generate(
                    prompt=query,
                    system_prompt=DUAL_KEYWORD_SYSTEM_PROMPT,
                    options={"temperature": 0.1},   # near-deterministic for JSON
                )
            return self._parse_keyword_json(raw, query)
        except Exception as e:
            logger.error(f"Dual keyword extraction failed: {e}")
            return self._keyword_fallback(query)

    def _parse_keyword_json(
        self, raw: str, original_query: str
    ) -> Dict[str, List[str]]:
        """Parse the LLM response into the expected keyword dict.

        Handles several common failure modes:
          - Markdown fences around JSON
          - Trailing prose after the JSON object
          - Completely unparseable output
        """
        text = raw.strip()

        # Strip markdown code fences if the model added them anyway
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)

        # Attempt 1: direct parse
        try:
            parsed = json.loads(text)
            return self._validate_keywords(parsed, original_query)
        except json.JSONDecodeError:
            pass

        # Attempt 2: find the first { … } block in the output
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                return self._validate_keywords(parsed, original_query)
            except json.JSONDecodeError:
                pass

        # Attempt 3: give up and use fallback
        logger.warning(
            f"Malformed keyword JSON from LLM (falling back): {text[:200]}"
        )
        return self._keyword_fallback(original_query)

    @staticmethod
    def _validate_keywords(
        parsed: dict, original_query: str
    ) -> Dict[str, List[str]]:
        """Ensure the parsed object has the expected structure."""
        high = parsed.get("high_level_keywords", [])
        low = parsed.get("low_level_keywords", [])

        # Coerce scalar values to single-element lists
        if isinstance(high, str):
            high = [high]
        if isinstance(low, str):
            low = [low]

        # Guarantee non-empty lists
        if not high:
            high = [original_query]
        if not low:
            low = [original_query]

        return {
            "high_level_keywords": [str(k) for k in high],
            "low_level_keywords": [str(k) for k in low],
        }

    @staticmethod
    def _keyword_fallback(query: str) -> Dict[str, List[str]]:
        """Last-resort fallback: treat the raw query as both keyword types."""
        return {
            "high_level_keywords": [query],
            "low_level_keywords": [query],
        }

    # ------------------------------------------------------------------
    #  Ego-Graph Traversal (Task 2, Requirement 4)
    # ------------------------------------------------------------------

    def _traverse_ego_graph(
        self, keywords: List[str], radius: int = 2
    ) -> List[str]:
        """Walk the knowledge graph outward from nodes matching *keywords*.

        For each keyword, find nodes whose label contains the keyword
        (case-insensitive), then extract the ``nx.ego_graph`` with the
        given radius.  Returns a deduplicated list of human-readable
        context strings describing the neighbourhood.
        """
        graph = self._load_networkx_graph()
        if graph is None:
            return []

        context_lines: List[str] = []
        visited_nodes: set = set()

        for kw in keywords:
            kw_lower = kw.lower()

            # Find seed nodes whose label / name contains the keyword
            seed_nodes = [
                n
                for n, attrs in graph.nodes(data=True)
                if kw_lower in str(attrs.get("label", attrs.get("name", n))).lower()
            ]

            for seed in seed_nodes[:3]:  # cap seeds per keyword to avoid explosion
                if seed in visited_nodes:
                    continue
                visited_nodes.add(seed)

                try:
                    ego = nx.ego_graph(graph, seed, radius=radius)
                except nx.NetworkXError:
                    continue

                for node, attrs in ego.nodes(data=True):
                    if node in visited_nodes:
                        continue
                    visited_nodes.add(node)

                    label = attrs.get("label", attrs.get("name", str(node)))
                    ntype = attrs.get("type", "unknown")
                    context_lines.append(f"[{ntype}] {label}")

        return context_lines

    # ------------------------------------------------------------------
    #  Dual-Level Search  (Task 2, Requirements 2-5)
    # ------------------------------------------------------------------

    def dual_level_search(
        self,
        query: str,
        k: int = 10,
        rrf_k: int = 60,
        ego_radius: int = 2,
    ) -> Tuple[List[Dict], str]:
        """Primary retrieval entry-point for the v2 Hybrid RAG pipeline.

        Workflow
        --------
        1. Extract high- and low-level keywords via Ollama.
        2. Route low-level keywords → BM25 index.
        3. Route high-level keywords → ChromaDB semantic search.
        4. Traverse the knowledge graph (ego-graph) for structural context.
        5. Fuse BM25 + ChromaDB results with Reciprocal Rank Fusion (RRF).

        Parameters
        ----------
        query : str
            The user's natural-language research question.
        k : int
            Number of final documents to return after fusion.
        rrf_k : int
            Smoothing constant for the RRF formula.  A higher value
            dampens the influence of rank position.  60 is the standard
            default from the original RRF paper (Cormack et al., 2009).
        ego_radius : int
            Hop count for ``nx.ego_graph`` traversal (default 2).

        Returns
        -------
        (results, graph_context) : tuple
            *results* — a list of document dicts sorted by fused RRF score.
            *graph_context* — a newline-joined string of structural context
            extracted from the knowledge graph (to be appended to the LLM
            prompt, NOT ranked).
        """
        # --- Step 1: Keyword extraction -----------------------------------
        keywords = self.extract_dual_keywords(query)
        low_keys = keywords["low_level_keywords"]
        high_keys = keywords["high_level_keywords"]

        logger.info(f"Low-level keys: {low_keys}")
        logger.info(f"High-level keys: {high_keys}")

        # --- Step 2: Route LOW-level keywords → BM25 ---------------------
        #     BM25 excels at exact-match retrieval (names, acronyms).
        #     We join the keywords into a single query string because
        #     BM25Okapi scores across the full vocabulary of terms.
        retriever = self._get_hybrid_retriever()
        bm25_query = " ".join(low_keys)
        bm25_results = retriever._search_bm25(bm25_query, k=50)

        # --- Step 3: Route HIGH-level keywords → ChromaDB -----------------
        #     ChromaDB performs semantic (embedding-based) search, which is
        #     ideal for abstract themes that may not appear verbatim in docs.
        vs = self._get_vector_store()
        if not vs._initialized:
            vs.initialize()
        chroma_query = " ".join(high_keys)
        chroma_results = vs.search(chroma_query, n_results=50)

        # --- Step 4: Ego-graph traversal ----------------------------------
        #     Walk the NetworkX knowledge graph outward from concept nodes
        #     matching the high-level keywords.  This retrieves *structural*
        #     context (related topics, faculty, papers) that may not appear
        #     in any single document but is captured in the graph topology.
        graph_context_lines = self._traverse_ego_graph(high_keys, radius=ego_radius)
        graph_context = ""
        if graph_context_lines:
            graph_context = (
                "\n### Structural Context from Knowledge Graph:\n"
                + "\n".join(f"- {line}" for line in graph_context_lines[:20])
            )

        # ------------------------------------------------------------------
        # Step 5: Reciprocal Rank Fusion (RRF)
        #
        # RRF is a simple, parameter-light rank fusion method that combines
        # ranked lists from heterogeneous retrieval systems without needing
        # score normalisation.
        #
        # For each document that appears in *any* of the ranked lists, its
        # fused score is the sum of its per-list RRF contributions:
        #
        #     RRF_score(d) = Σ  1 / (rrf_k + rank_i(d))
        #                    i∈{BM25, ChromaDB}
        #
        # where rank_i(d) is the 1-based rank of document d in list i, and
        # rrf_k is a smoothing constant (default 60) that prevents the
        # top-ranked document from dominating the fused score.
        #
        # Documents appearing in both lists receive contributions from
        # each, naturally boosting items validated by both exact-match
        # (BM25) and semantic (ChromaDB) signals.
        #
        # Reference:
        #   Cormack, Gordon V., Charles LA Clarke, and Stefan Buettcher.
        #   "Reciprocal rank fusion outperforms condorcet and individual
        #    rank learning methods." SIGIR 2009.
        # ------------------------------------------------------------------

        # Accumulator: doc_id → {doc dict, cumulative score, per-source rank}
        fused: Dict[str, Dict] = {}

        # ---- Process BM25 results ----------------------------------------
        # BM25 captures the low-level (entity) retrieval signal.
        # Each document's RRF contribution is 1 / (rrf_k + rank).
        for rank, doc in enumerate(bm25_results):
            doc_id = doc.get("id")
            if not doc_id:
                continue

            # RRF contribution for this document from the BM25 list.
            # rank is 0-based, so we add 1 to make it 1-based.
            rrf_contribution = 1.0 / (rrf_k + rank + 1)

            if doc_id not in fused:
                # First time seeing this document — initialise its entry.
                fused[doc_id] = {
                    "doc": doc,
                    "score": 0.0,
                    "bm25_rank": rank,
                    "chroma_rank": None,
                }

            # Accumulate the BM25 contribution into the fused score.
            fused[doc_id]["score"] += rrf_contribution
            fused[doc_id]["bm25_rank"] = rank

        # ---- Process ChromaDB results ------------------------------------
        # ChromaDB captures the high-level (semantic) retrieval signal.
        # The same RRF formula is applied independently, and contributions
        # are *added* to any existing score for documents that also appeared
        # in the BM25 list — this is the core fusion mechanism.
        for rank, doc in enumerate(chroma_results):
            doc_id = doc.get("id")
            if not doc_id:
                continue

            # RRF contribution for this document from the ChromaDB list.
            rrf_contribution = 1.0 / (rrf_k + rank + 1)

            if doc_id not in fused:
                # Document only appeared in ChromaDB, not BM25.
                fused[doc_id] = {
                    "doc": doc,
                    "score": 0.0,
                    "bm25_rank": None,
                    "chroma_rank": rank,
                }

            # Accumulate the ChromaDB contribution.
            fused[doc_id]["score"] += rrf_contribution
            fused[doc_id]["chroma_rank"] = rank

        # ---- Sort by fused RRF score (descending) and trim to top-k ------
        # Documents that appeared in *both* lists will have a higher fused
        # score than those appearing in only one, all else being equal.
        sorted_results = sorted(
            fused.values(), key=lambda x: x["score"], reverse=True
        )

        # Build the final output list with provenance metadata attached
        # so downstream consumers can inspect which retrieval stream(s)
        # contributed each result.
        final_results: List[Dict] = []
        for item in sorted_results[:k]:
            doc = item["doc"]
            doc["rrf_score"] = item["score"]
            doc["bm25_rank"] = item["bm25_rank"]
            doc["chroma_rank"] = item["chroma_rank"]
            final_results.append(doc)

        return final_results, graph_context

    # ------------------------------------------------------------------
    #  Legacy public API (preserved for backward compatibility)
    # ------------------------------------------------------------------

    def expand_query(self, query: str) -> str:
        """Use LLM to generate related search terms.

        Example: "sustainable farming" → "sustainable farming agriculture crop optimization"

        .. note:: This is the *v1* expansion method.  New callers should
           prefer :meth:`dual_level_search` which subsumes this.
        """
        if not self.client._initialized:
            self.client.initialize()

        prompt = f"""
        You are a research assistant.
        Given the user search query: "{query}"
        Generate 3-5 related academic keywords or concepts that would help find relevant research papers or faculty.
        Output ONLY the keywords separated by spaces. Do not explain.
        """

        # Heuristic: If query looks like a specific name search, don't expand
        if any(x in query.lower() for x in ["professor", "dr.", "prof", "who is", "email", "contact"]):
            return query

        try:
            with Timer("LLM Query Expansion", use_rich=False):
                expansion = self.client.generate(prompt, system_prompt="You are a keyword generator.")
            expanded = f"{query} {expansion.strip()}"
            logger.debug(f"Expanded query: {expanded}")
            return expanded
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            print(f"Query expansion failed: {e}")
            return query

    def get_graph_insights(self, query: str) -> Dict[str, Any]:
        """Extract insights from knowledge graph based on query."""
        if not self.store:
            return {}

        try:
            with Timer("Graph Insights Extraction", use_rich=False):
                insights = {}
                query_lower = query.lower()

            # Detect query intent
            is_asking_about_faculty = any(word in query_lower for word in ["who", "faculty", "professor", "researcher", "expert"])
            is_asking_about_topics = any(word in query_lower for word in ["research", "work on", "study", "topic"])
            is_asking_about_collaboration = any(word in query_lower for word in ["collaborate", "collaboration", "work with", "partner"])

            # Try to find mentioned faculty
            name_candidates = self._extract_names(query)
            for name in name_candidates:
                faculty_id = self.queries.find_faculty_by_name(name)
                if faculty_id:
                    insights["faculty_id"] = faculty_id
                    insights["faculty_expertise"] = self.queries.get_faculty_expertise(faculty_id)
                    insights["faculty_papers"] = self.queries.get_faculty_papers(faculty_id)
                    break

            # Find topics mentioned
            topics_found = []
            for topic in query_lower.split():
                if len(topic) > 3:  # Skip short words
                    experts = self.queries.find_experts_in_topic(topic, top_k=5)
                    if experts:
                        topics_found.append({
                            "topic": topic,
                            "experts": experts
                        })

            if topics_found:
                insights["topics"] = topics_found

            # Get research clusters if asking about collaborations
            if is_asking_about_collaboration:
                clusters = self.queries.find_research_clusters(min_size=2)
                if clusters:
                    insights["research_clusters"] = clusters[:3]

            return insights
        except Exception as e:
            logger.error(f"Graph insights extraction failed: {e}")
            return {}

    def get_data_mining_insights(self) -> Dict[str, Any]:
        """Get general data mining insights (topics, patterns)."""
        if not self.data_mining:
            return {}

        insights = {}

        try:
            topics = self.data_mining.discover_topics_lda(n_topics=5, n_words=5)
            if topics:
                insights["research_themes"] = topics
        except Exception as e:
            logger.error(f"Data mining LDA failed: {e}")

        try:
            phrases = self.data_mining.extract_key_phrases(top_k=10)
            if phrases:
                insights["key_research_areas"] = [phrase for phrase, score in phrases]
        except Exception as e:
            logger.error(f"Data mining keywords failed: {e}")

        return insights

    def enrich_context(self, query: str, vector_results: List[Dict]) -> str:
        """Enrich vector search results with graph insights."""
        graph_insights = self.get_graph_insights(query)

        enriched_context = ""

        if "faculty_expertise" in graph_insights and graph_insights["faculty_expertise"]:
            enriched_context += "\n### Faculty Expertise:\n"
            for topic in graph_insights["faculty_expertise"][:5]:
                enriched_context += f"- {topic['topic']} (expertise level: {topic['weight']:.1f})\n"

        if "faculty_papers" in graph_insights and graph_insights["faculty_papers"]:
            enriched_context += "\n### Recent Papers:\n"
            for paper in graph_insights["faculty_papers"][:3]:
                enriched_context += f"- {paper['title']} ({paper['year']})\n"

        if "topics" in graph_insights:
            for topic_data in graph_insights["topics"][:2]:
                if topic_data["experts"]:
                    enriched_context += f"\n### Experts in {topic_data['topic']}:\n"
                    for expert in topic_data["experts"][:3]:
                        enriched_context += f"- {expert['name']} (expertise: {expert['expertise_weight']:.1f})\n"

        if "research_clusters" in graph_insights:
            enriched_context += "\n### Research Collaboration Groups:\n"
            for cluster in graph_insights["research_clusters"][:2]:
                members = ", ".join([m["name"] for m in cluster["members"][:3]])
                enriched_context += f"- Group with {cluster['size']} members: {members}\n"

        return enriched_context

    def _extract_names(self, text: str) -> List[str]:
        """Simple name extraction from text (looks for capitalised words)."""
        pattern = r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b'
        matches = re.findall(pattern, text)
        return [m for m in matches if len(m) > 3]


# Backwards compatibility
class QueryEngine(GraphEnhancedQueryEngine):
    """Alias for backwards compatibility."""
    pass
