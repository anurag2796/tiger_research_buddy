"""
Hybrid Retriever combining Vector Search (ChromaDB) and Keyword Search (BM25).
"""

from typing import List, Dict, Any, Optional
import numpy as np
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
            vector_store: The VectorStore instance (ChromaDB wrapper).
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
        self.bm25_corpus = [doc["content"].lower().split() for doc in documents]
        
        self.bm25 = BM25Okapi(self.bm25_corpus)
        console.print(f"[green]✓ BM25 index ready[/]")
        
    def _search_bm25(self, query: str, k: int = 50) -> List[Dict]:
        """
        Perform BM25 search.
        """
        if not self.bm25:
            return []
            
        tokenized_query = query.lower().split()
        
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
        
        # Helper to process results
        def process_results(results, weight=1.0):
            for rank, doc in enumerate(results):
                doc_id = doc.get("id")
                if not doc_id:
                    continue
                    
                # RRF Formula: 1 / (k + rank)
                score = 1 / (rrf_k + rank + 1)
                
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "doc": doc,
                        "score": 0.0,
                        "vector_rank": None,
                        "bm25_rank": None
                    }
                
                doc_scores[doc_id]["score"] += score
                
                # specific rank tracking (optional, for debugging)
                if weight == 1.0: # Vector results (assumption)
                     # We can't strictly know source here if calling generic process, 
                     # so let's do it explicitly in loop below
                     pass

        # Process Vector Results
        for rank, doc in enumerate(vector_results):
            doc_id = doc.get("id")
            if not doc_id: continue
            
            # ChromaDB usually returns distance. If it's too high (low similarity), skip it.
            # E.g. L2 distance > 1.4 or Cosine distance > 0.5 depending on config.
            # By default nomic-embed-text uses cosine distance where 0 is identical and >1 is unrelated.
            dist = doc.get("distance")
            if dist is not None and float(dist) > 1.0:
                continue
            
            score = 1 / (rrf_k + rank + 1)
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"doc": doc, "score": 0.0, "vector_rank": rank, "bm25_rank": None}
            else:
                 doc_scores[doc_id]["doc"].update(doc) # Merge metadata if needed
                 doc_scores[doc_id]["vector_rank"] = rank
                 
            doc_scores[doc_id]["score"] += score
            
        # Process BM25 Results
        for rank, doc in enumerate(bm25_results):
            doc_id = doc.get("id")
            if not doc_id: continue
            
            score = 1 / (rrf_k + rank + 1)
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"doc": doc, "score": 0.0, "vector_rank": None, "bm25_rank": rank}
            else:
                doc_scores[doc_id]["bm25_rank"] = rank
                # Keep the content from the source that might be better? 
                # Usually vector store has structure, bm25 doc is from same source file.
                
            doc_scores[doc_id]["score"] += score

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
                console.print(f"[yellow]Reranker unavailable, using RRF order: {e}[/]")
                final_results = final_results[:k]

        return final_results
