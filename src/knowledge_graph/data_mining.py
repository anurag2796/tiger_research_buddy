"""Data mining techniques for research insights."""

import json
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter, defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.cluster import AgglomerativeClustering
from mlxtend.frequent_patterns import apriori, association_rules
import pandas as pd

DATA_DIR = Path("data")
PAPERS_DIR = DATA_DIR / "papers"


class DataMining:
    """Data mining techniques for enhanced research insights."""
    
    def __init__(self):
        self.papers = []
        self._load_papers()
    
    def _load_papers(self):
        """Load all paper data."""
        if not PAPERS_DIR.exists():
            return
        
        for paper_file in PAPERS_DIR.glob("*.json"):
            try:
                with open(paper_file) as f:
                    self.papers.append(json.load(f))
            except:
                pass
    
    def find_frequent_topic_patterns(self, min_support: float = 0.05) -> List[Dict]:
        """Find frequent research topic combinations using Apriori.
        
        Returns patterns like: ['AI', 'Machine Learning', 'Deep Learning']
        """
        if not self.papers:
            return []
        
        # Build transaction database (papers × topics)
        transactions = []
        for paper in self.papers:
            topics = set()
            for tag_data in paper.get("tags", [])[:15]:
                if isinstance(tag_data, list) and len(tag_data) >= 1:
                    topics.add(tag_data[0])
            if topics:
                transactions.append(topics)
        
        if not transactions:
            return []
        
        # Convert to one-hot DataFrame
        all_topics = sorted(set(topic for trans in transactions for topic in trans))
        df = pd.DataFrame(
            [[topic in trans for topic in all_topics] for trans in transactions],
            columns=all_topics
        )
        
        try:
            # Find frequent itemsets
            frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)
            
            results = []
            for _, row in frequent_itemsets.iterrows():
                if len(row['itemsets']) >= 2:  # Only combinations
                    results.append({
                        "topics": list(row['itemsets']),
                        "support": row['support'],
                        "count": int(row['support'] * len(transactions)),
                    })
            
            return sorted(results, key=lambda x: x['support'], reverse=True)
        except:
            return []
    
    def find_topic_associations(self, min_confidence: float = 0.6) -> List[Dict]:
        """Find association rules: 'If topic X, then likely topic Y'.
        
        Returns rules like: 'Machine Learning → Deep Learning' (confidence: 85%)
        """
        if not self.papers:
            return []
        
        # Build transaction database
        transactions = []
        for paper in self.papers:
            topics = set()
            for tag_data in paper.get("tags", [])[:15]:
                if isinstance(tag_data, list) and len(tag_data) >= 1:
                    topics.add(tag_data[0])
            if topics:
                transactions.append(topics)
        
        if not transactions or len(transactions) < 10:
            return []
        
        # Convert to DataFrame
        all_topics = sorted(set(topic for trans in transactions for topic in trans))
        if len(all_topics) < 2:
            return []
        
        df = pd.DataFrame(
            [[topic in trans for topic in all_topics] for trans in transactions],
            columns=all_topics
        )
        
        try:
            frequent_itemsets = apriori(df, min_support=0.03, use_colnames=True)
            
            if len(frequent_itemsets) < 2:
                return []
            
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence, num_itemsets=len(frequent_itemsets))
            
            results = []
            for _, rule in rules.iterrows():
                results.append({
                    "antecedent": list(rule['antecedents']),
                    "consequent": list(rule['consequents']),
                    "confidence": rule['confidence'],
                    "support": rule['support'],
                    "lift": rule['lift'],
                })
            
            return sorted(results, key=lambda x: x['confidence'], reverse=True)[:20]
        except:
            return []
    
    def extract_key_phrases(self, top_k: int = 50) -> List[Tuple[str, float]]:
        """Extract important key phrases using TF-IDF."""
        if not self.papers:
            return []
        
        # Combine title + abstract for each paper
        documents = []
        for paper in self.papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            if text.strip():
                documents.append(text)
        
        if len(documents) < 2:
            return []
        
        # TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 3),  # Unigrams, bigrams, trigrams
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform(documents)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get average TF-IDF scores
            avg_scores = np.asarray(tfidf_matrix.mean(axis=0)).ravel()
            
            # Sort by score
            top_indices = avg_scores.argsort()[-top_k:][::-1]
            
            return [(feature_names[i], avg_scores[i]) for i in top_indices]
        except:
            return []
    
    def discover_topics_lda(self, n_topics: int = 10, n_words: int = 10) -> List[Dict]:
        """Discover latent research themes using LDA topic modeling."""
        if not self.papers:
            return []
        
        # Prepare documents
        documents = []
        for paper in self.papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            if text.strip():
                documents.append(text)
        
        if len(documents) < n_topics:
            return []
        
        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            min_df=2,
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform(documents)
            feature_names = vectorizer.get_feature_names_out()
            
            # LDA
            lda = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42,
                max_iter=20,
            )
            lda.fit(tfidf_matrix)
            
            # Extract topics
            topics = []
            for topic_idx, topic in enumerate(lda.components_):
                top_word_indices = topic.argsort()[-n_words:][::-1]
                top_words = [feature_names[i] for i in top_word_indices]
                
                topics.append({
                    "topic_id": topic_idx,
                    "keywords": top_words,
                    "weight": float(topic.sum()),
                })
            
            return topics
        except:
            return []
    
    def cluster_similar_papers(self, n_clusters: int = 5) -> Dict[int, List[Dict]]:
        """Cluster papers by similarity using hierarchical clustering."""
        if not self.papers or len(self.papers) < n_clusters:
            return {}
        
        # Prepare documents
        documents = []
        valid_papers = []
        for paper in self.papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            if text.strip():
                documents.append(text)
                valid_papers.append(paper)
        
        if len(documents) < n_clusters:
            return {}
        
        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        
        try:
            tfidf_matrix = vectorizer.fit_transform(documents)
            
            # Hierarchical clustering
            clustering = AgglomerativeClustering(n_clusters=n_clusters)
            labels = clustering.fit_predict(tfidf_matrix.toarray())
            
            # Group papers by cluster
            clusters = defaultdict(list)
            for paper, label in zip(valid_papers, labels):
                clusters[int(label)].append({
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", []),
                    "year": paper.get("year", ""),
                })
            
            return dict(clusters)
        except:
            return {}
    
    def get_topic_trends(self) -> Dict[str, Dict[str, int]]:
        """Analyze research topic trends over time (basic version)."""
        trends = defaultdict(lambda: defaultdict(int))
        
        for paper in self.papers:
            year = paper.get("year", "Unknown")
            if year and year != "Unknown":
                try:
                    year_int = int(str(year)[:4])  # Extract year
                    if 2000 <= year_int <= 2030:
                        for tag_data in paper.get("tags", [])[:5]:
                            if isinstance(tag_data, list) and len(tag_data) >= 1:
                                topic = tag_data[0]
                                trends[topic][str(year_int)] += 1
                except:
                    pass
        
        return dict(trends)
