"""
Intent Classifier for TigerResearchBuddy

Detects query intent to:
1. Identify off-topic queries (should refuse)
2. Classify query type (faculty lookup, topic search, etc.)
3. Route to appropriate handling
"""

import re
from typing import Tuple
from enum import Enum


class QueryIntent(Enum):
    """Query intent types"""
    FACULTY_LOOKUP = "faculty_lookup"  # "Who is Christopher Kanan?"
    TOPIC_SEARCH = "topic_search"  # "Who works on machine learning?"
    CONTACT_INFO = "contact_info"  # "What's his email?"
    PUBLICATION_QUERY = "publication_query"  # "What papers has X published?"
    COMPARISON = "comparison"  # "Compare X and Y"
    FOLLOW_UP = "follow_up"  # "Anyone else?", "What about..."
    OFF_TOPIC = "off_topic"  # Weather, recipes, etc.
    GENERAL_HELP = "general_help"  # "How do I...", "Can you help..."


class IntentClassifier:
    """Classify user query intent"""
    
    # Off-topic keywords (non-RIT, non-research)
    OFF_TOPIC_KEYWORDS = [
        # General knowledge
        'weather', 'temperature', 'forecast', 'rain', 'snow',
        'stock', 'market', 'price', 'cost', 'buy', 'sell',
        'movie', 'film', 'theater', 'cinema',
        'restaurant', 'pizza', 'food', 'eat', 'dinner',
        'sports', 'game', 'team', 'score', 'player',
        'news', 'headline', 'president', 'election',
        
        # How-to (non-research)
        'recipe', 'cook', 'bake', 'cake', 'chocolate',
        'tie a tie', 'change a tire', 'learn spanish',
        'invest', 'travel', 'hotel', 'flight',
        
        # General facts
        'capital', 'population', 'country', 'state',
        'tall', 'mountain', 'ocean', 'river',
        'invent', 'discover', 'history', 'war',
        
        # Random
        'joke', 'story', 'poem', 'song',
        'meaning of life', 'universe', 'everything',
    ]
    
    # Faculty name patterns
    FACULTY_PATTERNS = [
        r'\b(?:professor|prof|dr|doctor)\s+[A-Z][a-z]+',
        r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Proper name
        r'who is\s+[A-Z]',
        r'tell me about\s+(?:professor|prof|dr)',
    ]
    
    # Topic search patterns
    TOPIC_PATTERNS = [
        r'who (?:works|researches|does research|focuses) on',
        r'(?:professors?|faculty|researchers?) (?:in|working on|doing)',
        r'research in\s+\w+',
        r'anyone (?:in|working on|doing)',
    ]
    
    # Contact info patterns
    CONTACT_PATTERNS = [
        r'(?:what|whats|what\'s).*?(?:email|phone|office|location)',
        r'(?:email|phone|office) (?:address|number|location)',
        r'how (?:can i|do i) (?:contact|reach|email)',
        r'where is (?:his|her|their) office',
    ]
    
    # Publication patterns
    PUBLICATION_PATTERNS = [
        r'papers?.*?published',
        r'publications?',
        r'research papers?',
        r'what (?:has|did).*?publish',
        r'citations?',
    ]
    
    # Follow-up patterns
    FOLLOW_UP_PATTERNS = [
        r'^(?:anyone|anybody) else',
        r'^what about',
        r'^(?:and |also )?(?:his|her|their|the)\s+(?:email|office|phone)',
        r'^(?:tell me )?more',
        r'^(?:any)?thing else',
    ]
    
    # Small talk / general help
    GENERAL_HELP_PATTERNS = [
        r'^(?:hello|hi|hey|good (?:morning|afternoon|evening))',
        r'^(?:thank|thanks)',
        r'^(?:can you|could you) help',
        r'^(?:i need|i want) (?:help|assistance)',
        r'^how are you',
        r'^what(?:\'s| is) up',
    ]
    
    def classify(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Classify query intent
        
        Args:
            query: User query string
            
        Returns:
            (intent, confidence) tuple where confidence is 0-1
        """
        query_lower = query.lower().strip()
        
        # Check off-topic first (highest priority)
        if self._is_off_topic(query_lower):
            return QueryIntent.OFF_TOPIC, 0.9
        
        # Check small talk / greetings
        if self._matches_patterns(query_lower, self.GENERAL_HELP_PATTERNS):
            return QueryIntent.GENERAL_HELP, 0.8
        
        # Check follow-up questions
        if self._matches_patterns(query_lower, self.FOLLOW_UP_PATTERNS):
            return QueryIntent.FOLLOW_UP, 0.85
        
        # Check contact info queries
        if self._matches_patterns(query_lower, self.CONTACT_PATTERNS):
            return QueryIntent.CONTACT_INFO, 0.85
        
        # Check publication queries
        if self._matches_patterns(query_lower, self.PUBLICATION_PATTERNS):
            return QueryIntent.PUBLICATION_QUERY, 0.8
        
        # Check topic search (PRIORITY OVER FACULTY NAME REGEX)
        if self._matches_patterns(query_lower, self.TOPIC_PATTERNS):
            return QueryIntent.TOPIC_SEARCH, 0.8
            
        # Check faculty lookup
        if self._matches_patterns(query, self.FACULTY_PATTERNS):
            return QueryIntent.FACULTY_LOOKUP, 0.8
        
        # Default: assume topic search with lower confidence
        return QueryIntent.TOPIC_SEARCH, 0.5
    
    def _is_off_topic(self, query_lower: str) -> bool:
        """Check if query is off-topic"""
        # Check for off-topic keywords
        words = query_lower.split()
        
        for keyword in self.OFF_TOPIC_KEYWORDS:
            if keyword in query_lower:
                # Make sure it's not part of a research topic
                # e.g., "machine learning" should not match "learning"
                if not self._is_research_context(query_lower, keyword):
                    return True
        
        return False
    
    def _is_research_context(self, query: str, keyword: str) -> bool:
        """Check if keyword appears in research context"""
        research_indicators = [
            'research', 'professor', 'faculty', 'paper', 'publication',
            'rit', 'computing', 'department', 'phd', 'master'
        ]
        
        return any(indicator in query for indicator in research_indicators)
    
    def _matches_patterns(self, text: str, patterns: list) -> bool:
        """Check if text matches any of the given patterns"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def should_refuse(self, intent: QueryIntent) -> bool:
        """Determine if query should be refused"""
        return intent == QueryIntent.OFF_TOPIC
    
    def get_refusal_message(self, query: str = None) -> str:
        """Get appropriate refusal message for off-topic queries"""
        return """I specialize in helping students find RIT Computing research opportunities and faculty information.

I can help you with:
• Finding professors by research area
• Getting faculty contact information
• Learning about research projects
• Discovering PhD/MS opportunities

Please feel free to ask me about RIT Computing research!"""


# Global instance
_classifier = None


def get_intent_classifier() -> IntentClassifier:
    """Get global classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


# Example usage
if __name__ == "__main__":
    classifier = IntentClassifier()
    
    test_queries = [
        "Who is Christopher Kanan?",
        "Who works on machine learning?",
        "What's his email?",
        "What's the weather today?",
        "How do I make a cake?",
        "Anyone else work on AI?",
        "Hello, can you help me?",
        "What papers has Dr. Kanan published?",
    ]
    
    print("=== Intent Classification Tests ===\n")
    for query in test_queries:
        intent, confidence = classifier.classify(query)
        should_refuse = classifier.should_refuse(intent)
        
        print(f"Query: \"{query}\"")
        print(f"  Intent: {intent.value}")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Refuse: {should_refuse}")
        
        if should_refuse:
            print(f"  Message: {classifier.get_refusal_message()[:60]}...")
        
        print()
