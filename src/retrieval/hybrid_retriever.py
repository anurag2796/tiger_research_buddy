"""
Hybrid Retriever combining Vector Search (ChromaDB) and Keyword Search (BM25).
"""

from typing import List, Dict, Any, Optional
import numpy as np
import re
from rank_bm25 import BM25Okapi
from rich.console import Console

from ..database.vector_store import VectorStore, process_data_into_documents
from .reranker import CrossEncoderReranker

console = Console()

class HybridRetriever:
    """
    Hybrid Retriever that combines Vector Search and BM25 using Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, vector_store: VectorStore, documents: Optional[List[Dict]] = None):
        """
        Initialize the HybridRetriever.

        Args:
            vector_store: The VectorStore instance (ChintdraDB wrapper).
            documents: List of documents to index for BM25. If None, valid documents
                      will be loaded from the vector store's source file if possible,
                      or an empty index will be created.
        """
        self.vector_store = vector_store
        self.bm25 = None
        self.bm25_corpus = []
        self.bm25_documents = [] # Keep reference to original docs to return content
        self._reranker: CrossEncoderReranker | None = None

        if documents:
            self.index_bm25(documents)

    def index_bm25(self, documents: List[Dict]):
        """
        Build the BM25 index from a list of documents.
        """
        console.print(f"[bold blue]Building BM25 index for {len(documents)} documents...[/]")

        self.bm25_documents = documents

        # Tokenize corpus for BM25
        # We use a simple whitespace tokenizer here, but could be more sophisticated
        self.bm25_corpus = [re.findall(r'\w+', doc["content"].lower()) for doc in documents]

        self.bm25 = BM25Okapi(self.bm25_corpus)
        console.print(f"[green]✓ BM25 index ready[/]")

    def add_documents_to_bm25(self, new_documents: List[Dict]):
        """
        Dynamically update the BM25 index with new documents.
        """
        if not new_documents:
            return

        if not self.bm25:
            self.index_bm25(new_documents)
            return

        console.print(f"[bold blue]Updating BM25 index with {len(new_documents)} new documents...[/]")

        self.bm25_documents.extend(new_documents)

        new_corpus = [re.findall(r'\w+', doc["content"].lower()) for doc in new_documents]
        self.bm25_corpus.extend(new_corpus)

        # BM25Okapi doesn't support incremental updates natively, so we must rebuild
        # the index, but we avoid re-tokenizing the existing corpus.
        self.bm25 = BM25Okapi(self.bm25_corpus)
        console.print(f"[green]✓ BM25 index updated (total documents: {len(self.bm25_documents)})[/]")

    def _search_bm25(self, query: str, k: int = 50) -> List[Dict]:
        """
        Perform BM25 search.
        """
        if not self.bm25:
            return []

        tokenized_query = re.findall(r'\w+', query.lower())

        # BM25 returns scores for all documents
        scores = self.bm25.get_scores(tokenized_query)

        # Get top k indices
        top_n_indices = np.argsort(scores)[::-1][:k]

        results = []
        for idx in top_n_indices:
            if scores[idx] > 0: # Only include relevant results
                 doc = self.bm25_documents[idx].copy()
                 doc["score"] = scores[idx]
                 results.append(doc)

        return results

    def _search_vector(self, query: str, k: int = 50) -> List[Dict]:
        """
        Perform Vector search using ChromaDB.
        """
        results = self.vector_store.search(query, n_results=k)
        return results

    def hybrid_search(self, query: str, k: int = 50, rrf_k: int = 60, rerank: bool = False) -> List[Dict]:
        """
        Perform Hybrid Search using Reciprocal Rank Fusion (RRF).

        Args:
            query: Search query string.
            k: Number of final results to return.
            rrf_k: Constant for RRF formula (default 60).
            rerank: If True, apply cross-encoder reranking after RRF fusion.

        Returns:
            List of reranked documents.
        """
        # 1. Get results from both retrievers
        vector_results = self._search_vector(query, k=50) # Get top 50 from vector
        bm25_results = self._search_bm25(query, k=50)   # Get top 50 from BM25

        # 2. Combine using RRF
        # Map doc_id -> RRF score
        doc_scores = {}

        # Default rank for missing documents in one of the sources
        # We assume if it didn't make the top 50, it would be around rank 51
        missing_rank = 50
        missing_score = 1 / (rrf_k + missing_rank + 1)

        # Pre-seed all document IDs that were found in either search
        for doc in vector_results:
            if doc.get("id"):
                doc_scores[doc["id"]] = {"doc": doc, "score": 0.0, "vector_rank": None, "bm25_rank": None}

        for doc in bm25_results:
            doc_id = doc.get("id")
            if doc_id:
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {"doc": doc, "score": 0.0, "vector_rank": None, "bm25_rank": None}
                else:
                    # BM25 docs often don't have full metadata if they were built from a reduced corpus.
                    # Merge to ensure we have the best document representation (usually Vector's).
                    # Avoid overwriting with missing fields.
                    for k_key, v_val in doc.items():
                        if k_key not in doc_scores[doc_id]["doc"]:
                            doc_scores[doc_id]["doc"][k_key] = v_val

        # Process Vector Results
        for rank, doc in enumerate(vector_results):
            doc_id = doc.get("id")
            if not doc_id: continue
            doc_scores[doc_id]["vector_rank"] = rank

        # Process BM25 Results
        for rank, doc in enumerate(bm25_results):
            doc_id = doc.get("id")
            if not doc_id: continue
            doc_scores[doc_id]["bm25_rank"] = rank

        # Calculate final RRF scores including penalties for missing ranks
        for doc_id, info in doc_scores.items():
            # Vector score
            v_rank = info["vector_rank"]
            v_score = 1 / (rrf_k + v_rank + 1) if v_rank is not None else missing_score

            # BM25 score
            b_rank = info["bm25_rank"]
            b_score = 1 / (rrf_k + b_rank + 1) if b_rank is not None else missing_score

            info["score"] = v_score + b_score

        # 3. Sort by combined score
        sorted_results = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)

        # 4. Format output
        final_results = []
        for item in sorted_results[:k if not rerank else 30]:
            doc = item["doc"]
            doc["rrf_score"] = item["score"]
            doc["vector_rank"] = item["vector_rank"]
            doc["bm25_rank"] = item["bm25_rank"]
            final_results.append(doc)

        # 5. Optional cross-encoder reranking for precision
        if rerank and final_results:
            try:
                if self._reranker is None:
                    self._reranker = CrossEncoderReranker()
                final_results = self._reranker.rerank(query, final_results, top_k=k)
            except Exception as e:
                console.print(f"[yellow]Rreranker unavailable, using RRF order: {e}[/]")
                final_results = final_results[:k]

        return final_results
