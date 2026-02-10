"""
Response Post-Processor for TigerResearchBuddy

Cleans up LLM responses by:
1. Removing internal artifacts (Result 1:, Context:, etc.)
2. Filtering out skill.md examples that leak through
3. Ensuring consistent markdown formatting
4. Adding appropriate emojis for contact info
5. Limiting response length
"""

import re
from typing import List, Tuple


class ResponsePostProcessor:
    """Post-process LLM responses for clean, user-friendly output"""
    
    # Patterns for internal artifacts to remove - ENHANCED
    ARTIFACT_PATTERNS = [
        # Vector search artifacts
        (r'Result \d+\s*\(.*?\):\s*', ''),
        (r'Result \d+:\s*', ''),
        (r'Result:\s*', ''),  # Catch "Result:" without number
        (r'---\s*Result \d+.*?---\s*', ''),
        (r'\*\*Result \d+.*?\*\*\s*', ''),
        (r'\bResult\b(?!\s+(?:in|of|from))', ''),
        (r'The following information.*?:', ''), # Catch intros that precede artifacts
        
        # Context labels
        (r'Context:\s*', ''),
        (r'Relevant information from RIT Computing:?\s*', ''),
        (r'From the RIT Computing.*?:?\s*', ''),
        (r'Based on the context.*?:?\s*', ''),
        
        # Metadata labels
        (r'professor:\s*', ''),
        (r'research_area:\s*', ''),
        (r'paper:\s*', ''),
        (r'faculty:\s*', ''),
        (r'doc_type:\s*\w+\s*', ''),
        (r'URL:\s*http', 'http'),  # Keep URL but remove label
        (r'Tags:\s*[\w\s,]+\s*', ''),
        (r'Metadata:\s*', ''),
        
        # Section markers
        (r'---\s*\(.*?\)\s*---', ''),
        
        # JSON-like structures
        (r'\{[^}]*"metadata"[^}]*\}', ''),
        (r'\{[^}]*doc_type[^}]*\}', ''),
    ]
    
    # Skill example patterns (these leak from skills.md)
    SKILL_EXAMPLE_PATTERNS = [
        r'✅\s*GOOD Response:.*?(?=\n\n|\Z)',
        r'❌\s*BAD Response:.*?(?=\n\n|\Z)',
        r'\*\*When asked.*?\*\*.*?(?=\n\n|\Z)',
        r'Example:.*?".*?".*?(?=\n\n|\Z)',
        r'## Skill \d+:.*?(?=\n##|\Z)',
        r'```\s*Example:.*?```',
        r'\*\*Skill \d+.*?\*\*.*?(?=\n\n|\Z)',
        r'(?:When|If) asked about.*?:.*?(?=\n\n|\Z)',
        r'\*\*Good Response:\*\*.*?(?=\n\n|\Z)',  # Catch "**Good Response:**"
        r'Based on the information provided, here are a few possible responses:',
        r'Response \d+:.*?(?=\n\n|\Z)',
    ]
    
    def __init__(self):
        """Initialize post-processor"""
        self.stats = {
            'artifacts_removed': 0,
            'skill_examples_removed': 0,
            'responses_processed': 0
        }
    
    def process(self, response: str) -> str:
        """
        Main processing pipeline
        
        Args:
            response: Raw LLM response
            
        Returns:
            Cleaned and formatted response
        """
        self.stats['responses_processed'] += 1
        
        # Step 1: Remove internal artifacts
        cleaned = self._remove_artifacts(response)
        
        # Step 2: Remove skill examples that leaked through
        cleaned = self._remove_skill_examples(cleaned)
        
        # Step 3: Clean up whitespace
        cleaned = self._normalize_whitespace(cleaned)
        
        # Step 4: Ensure markdown formatting
        cleaned = self._ensure_markdown_formatting(cleaned)
        
        # Step 5: Add contact info emojis
        cleaned = self._add_contact_emojis(cleaned)
        
        # Step 6: Limit length if too verbose
        cleaned = self._limit_length(cleaned)
        
        # Final cleanup: Strip whitespace and leading punctuation (like commas or colons)
        cleaned = cleaned.strip()
        cleaned = re.sub(r'^[,:;\s]+', '', cleaned)
        
        return cleaned
    
    def _remove_artifacts(self, text: str) -> str:
        """Remove internal system artifacts"""
        original_length = len(text)
        
        for pattern, replacement in self.ARTIFACT_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.MULTILINE)
        
        if len(text) < original_length:
            self.stats['artifacts_removed'] += 1
            
        return text
    
    def _remove_skill_examples(self, text: str) -> str:
        """Remove skill.md examples that leak through"""
        original_length = len(text)
        
        for pattern in self.SKILL_EXAMPLE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.MULTILINE)
        
        if len(text) < original_length:
            self.stats['skill_examples_removed'] += 1
            
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Clean up excessive whitespace"""
        # Remove more than 2 consecutive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing whitespace from lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        
        # Remove spaces before punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        
        return text
    
    def _ensure_markdown_formatting(self, text: str) -> str:
        """Ensure consistent markdown formatting"""
        
        # Bold faculty names if not already bolded
        # Pattern: Capital letter followed by lowercase, space, Capital letter followed by lowercase
        # But only if not already in ** or surrounded by other markdown
        def bold_faculty_names(match):
            name = match.group(0)
            # Don't bold if already bolded or in a link
            if '**' in name or '[' in name or ']' in name:
                return name
            # Check if this looks like a sentence start (preceded by period/newline)
            # vs. a name in the middle of text
            return f"**{name}**"
        
        # This is a simplified version - only bold at start of sentences
        text = re.sub(r'(?<=\n)([A-Z][a-z]+\s+[A-Z][a-z]+)(?=\s+(?:is|works|focuses|teaches))',
                     bold_faculty_names, text)
        
        return text
    
    def _add_contact_emojis(self, text: str) -> str:
        """Add emojis for contact information"""
        
        # Add email emoji if not present
        if '@rit.edu' in text and '📧' not in text:
            text = re.sub(r'([a-zA-Z0-9._%+-]+@rit\.edu)', r'📧 \1', text)
        
        # Add location emoji for office locations (e.g., GOL-1234)
        if re.search(r'\b[A-Z]{2,3}-\d{3,4}\b', text) and '📍' not in text:
            text = re.sub(r'\b([A-Z]{2,3}-\d{3,4})\b', r'📍 \1', text)
        
        return text
    
    def _limit_length(self, text: str, max_words: int = 250) -> str:
        """
        Limit response length if too verbose
        
        Tries to find a natural stopping point rather than cutting mid-sentence.
        """
        words = text.split()
        
        if len(words) <= max_words:
            return text
        
        # Find the last sentence boundary before max_words
        truncated = ' '.join(words[:max_words])
        
        # Find last period, exclamation, or question mark
        last_sentence_end = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_sentence_end > 0:
            # Cut at sentence boundary
            return truncated[:last_sentence_end + 1]
        else:
            # No good boundary, just cut and add ellipsis
            return truncated + '...'
    
    def get_stats(self) -> dict:
        """Get processing statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            'artifacts_removed': 0,
            'skill_examples_removed': 0,
            'responses_processed': 0
        }


# Global instance
_postprocessor = None


def get_postprocessor() -> ResponsePostProcessor:
    """Get global postprocessor instance"""
    global _postprocessor
    if _postprocessor is None:
        _postprocessor = ResponsePostProcessor()
    return _postprocessor


def clean_response(response: str) -> str:
    """
    Convenience function to clean a response
    
    Args:
        response: Raw LLM response
        
    Returns:
        Cleaned response
    """
    processor = get_postprocessor()
    return processor.process(response)


# Example usage
if __name__ == "__main__":
    # Test case 1: Response with artifacts
    test_response_1 = """Result 1 (professor):
    **Christopher Kanan** works on computer vision.
    
    Context: From faculty database
    Tags: ai, ml, computer-vision
    
    📧 kanan@rit.edu | 📍 GOL-3210"""
    
    processor = ResponsePostProcessor()
    cleaned = processor.process(test_response_1)
    
    print("=== Test 1: Artifact Removal ===")
    print("BEFORE:")
    print(test_response_1)
    print("\nAFTER:")
    print(cleaned)
    print()
    
    # Test case 2: Response with skill examples
    test_response_2 = """Here are some examples:
    
    ✅ GOOD Response:
    "Professor Smith works on AI and machine learning."
    
    ❌ BAD Response:
    "I don't know anything about that."
    
    **Actual answer**: Christopher Kanan researches computer vision."""
    
    cleaned2 = processor.process(test_response_2)
    
    print("=== Test 2: Skill Example Removal ===")
    print("BEFORE:")
    print(test_response_2)
    print("\nAFTER:")
    print(cleaned2)
    print()
    
    # Print stats
    print("=== Processing Stats ===")
    print(processor.get_stats())
