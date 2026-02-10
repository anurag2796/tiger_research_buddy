"""
Automated Response Evaluation Script for TigerResearchBuddy
This script helps systematically evaluate response quality across the 100-question framework
"""

import re
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass
import json


@dataclass
class EvaluationResult:
    """Store evaluation results for a single response"""
    query: str
    response: str
    response_time: float
    critical_failures: List[str]
    scores: Dict[str, int]
    total_score: int
    grade: str
    issues: List[str]
    
    
class ResponseEvaluator:
    """Automated evaluator for TigerResearchBuddy responses"""
    
    # Critical failure patterns
    ARTIFACT_PATTERNS = [
        r'Result \d+:',
        r'Context:',
        r'professor:',
        r'research_area:',
        r'paper:',
        r'doc_type:',
        r'chunk_id:',
        r'similarity_score:',
        r'\{.*"metadata".*\}',  # JSON blobs
    ]
    
    # Faculty name pattern (basic)
    FACULTY_NAME_PATTERN = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
    
    # RIT email pattern
    RIT_EMAIL_PATTERN = r'\b\w+@rit\.edu\b'
    
    def __init__(self, known_faculty: List[str] = None):
        """
        Initialize evaluator
        
        Args:
            known_faculty: List of actual faculty names in database
        """
        self.known_faculty = set(known_faculty) if known_faculty else set()
        
    def evaluate_response(
        self,
        query: str,
        response: str,
        response_time: float,
        context_chunks: List[str] = None,
        expected_answer: str = None
    ) -> EvaluationResult:
        """
        Evaluate a single response against all criteria
        
        Returns:
            EvaluationResult object with scores and analysis
        """
        critical_failures = []
        issues = []
        scores = {}
        
        # === CRITICAL CHECKS ===
        
        # Check 1: Internal artifacts
        if self._has_internal_artifacts(response):
            critical_failures.append("Contains internal artifacts")
            issues.extend(self._find_artifacts(response))
            
        # Check 2: Hallucinated faculty
        if self.known_faculty:
            hallucinated = self._find_hallucinated_faculty(response)
            if hallucinated:
                critical_failures.append(f"Hallucinated faculty: {hallucinated}")
                
        # Check 3: Response time
        if response_time > 30:
            critical_failures.append(f"Response time too slow: {response_time:.1f}s")
            
        # Check 4: Off-topic handling
        if self._is_off_topic_query(query):
            if not self._has_appropriate_refusal(response):
                critical_failures.append("Failed to refuse off-topic query")
                
        # If critical failures, return early with failing grade
        if critical_failures:
            return EvaluationResult(
                query=query,
                response=response,
                response_time=response_time,
                critical_failures=critical_failures,
                scores={},
                total_score=0,
                grade="FAIL",
                issues=issues
            )
            
        # === QUALITY SCORING ===
        
        # Accuracy & Relevance (40 points)
        scores['factual_accuracy'] = self._score_accuracy(response, expected_answer) * 2
        scores['relevance'] = self._score_relevance(query, response) * 2
        
        # Formatting & Presentation (20 points)
        scores['formatting'] = self._score_formatting(response)
        scores['length'] = self._score_length(response)
        
        # User Experience (20 points)
        scores['actionability'] = self._score_actionability(response)
        scores['tone'] = self._score_tone(response)
        
        # Technical Performance (20 points)
        scores['speed'] = self._score_speed(response_time)
        scores['retrieval'] = self._score_retrieval(query, context_chunks) if context_chunks else 5
        
        # Calculate total
        total_score = sum(scores.values())
        grade = self._calculate_grade(total_score)
        
        # Identify specific issues
        issues.extend(self._identify_specific_issues(response, scores))
        
        return EvaluationResult(
            query=query,
            response=response,
            response_time=response_time,
            critical_failures=[],
            scores=scores,
            total_score=total_score,
            grade=grade,
            issues=issues
        )
        
    def _has_internal_artifacts(self, response: str) -> bool:
        """Check if response contains internal system artifacts"""
        for pattern in self.ARTIFACT_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        return False
        
    def _find_artifacts(self, response: str) -> List[str]:
        """Find specific artifacts in response"""
        artifacts = []
        for pattern in self.ARTIFACT_PATTERNS:
            matches = re.findall(pattern, response, re.IGNORECASE)
            artifacts.extend(matches)
        return artifacts
        
    def _find_hallucinated_faculty(self, response: str) -> List[str]:
        """Find faculty names mentioned that aren't in database"""
        mentioned_names = re.findall(self.FACULTY_NAME_PATTERN, response)
        hallucinated = [
            name for name in mentioned_names 
            if name not in self.known_faculty and name not in ['RIT', 'Computing']
        ]
        return hallucinated
        
    def _is_off_topic_query(self, query: str) -> bool:
        """Detect if query is off-topic"""
        off_topic_keywords = [
            'weather', 'recipe', 'cake', 'stock', 'movie', 'game',
            'super bowl', 'population', 'capital', 'president', 'sports'
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in off_topic_keywords)
        
    def _has_appropriate_refusal(self, response: str) -> bool:
        """Check if response appropriately refuses off-topic query"""
        refusal_phrases = [
            "don't have information",
            "outside my expertise",
            "specialize in rit",
            "can't help with",
            "not in my database"
        ]
        response_lower = response.lower()
        return any(phrase in response_lower for phrase in refusal_phrases)
        
    def _score_accuracy(self, response: str, expected: str = None) -> int:
        """Score factual accuracy (0-10)"""
        # If expected answer provided, check similarity
        if expected:
            # Simple keyword overlap (would use semantic similarity in production)
            expected_words = set(expected.lower().split())
            response_words = set(response.lower().split())
            overlap = len(expected_words & response_words) / len(expected_words)
            return int(overlap * 10)
        
        # Otherwise, check for accuracy markers
        score = 10
        
        # Deduct for uncertainty markers when making factual claims
        if re.search(r'\b(maybe|perhaps|possibly|might be)\b', response):
            score -= 2
            
        # Check for proper email format
        emails = re.findall(self.RIT_EMAIL_PATTERN, response)
        if emails and any('@rit.edu' not in email for email in emails):
            score -= 3
            
        return max(0, score)
        
    def _score_relevance(self, query: str, response: str) -> int:
        """Score relevance to query (0-10)"""
        # Extract key terms from query
        query_terms = set(query.lower().split())
        query_terms.discard('who')
        query_terms.discard('what')
        query_terms.discard('the')
        
        response_lower = response.lower()
        
        # Count how many query terms appear in response
        matches = sum(1 for term in query_terms if term in response_lower)
        relevance_ratio = matches / max(len(query_terms), 1)
        
        return int(relevance_ratio * 10)
        
    def _score_formatting(self, response: str) -> int:
        """Score markdown formatting quality (0-10)"""
        score = 10
        
        # Check for markdown elements
        has_bold = '**' in response or '__' in response
        has_email_icon = '📧' in response
        has_location_icon = '📍' in response
        has_paragraphs = '\n\n' in response
        
        if not has_bold:
            score -= 2
        if not has_paragraphs and len(response) > 200:
            score -= 3  # Wall of text
        if '@rit.edu' in response and not has_email_icon:
            score -= 1
            
        # Check for over-formatting
        if response.count('#') > 3:
            score -= 2  # Too many headers
            
        return max(0, score)
        
    def _score_length(self, response: str) -> int:
        """Score appropriate length (0-10)"""
        word_count = len(response.split())
        
        # Ideal: 50-200 words
        if 50 <= word_count <= 200:
            return 10
        elif 30 <= word_count < 50:
            return 7  # Bit short
        elif 200 < word_count <= 300:
            return 7  # Bit long
        elif word_count < 30:
            return 3  # Too short
        else:
            return 2  # Way too long
            
    def _score_actionability(self, response: str) -> int:
        """Score actionability - clear next steps (0-10)"""
        score = 5  # Base score
        
        # Has contact info
        if re.search(self.RIT_EMAIL_PATTERN, response):
            score += 3
            
        # Has action verbs
        action_verbs = ['email', 'contact', 'visit', 'check', 'reach out', 'ask']
        if any(verb in response.lower() for verb in action_verbs):
            score += 2
            
        # Has specific next steps
        if 'try:' in response.lower() or 'you can:' in response.lower():
            score += 2
            
        return min(10, score)
        
    def _score_tone(self, response: str) -> int:
        """Score tone appropriateness (0-10)"""
        score = 10
        
        # Check for issues
        if any(word in response.lower() for word in ['lol', 'omg', 'wtf']):
            score -= 5  # Too casual
            
        if response.count('!') > 3:
            score -= 2  # Too enthusiastic
            
        if any(word in response for word in ['shall', 'henceforth', 'whereby']):
            score -= 2  # Too formal
            
        return max(0, score)
        
    def _score_speed(self, response_time: float) -> int:
        """Score response speed (0-10)"""
        if response_time < 3:
            return 10
        elif response_time < 5:
            return 9
        elif response_time < 10:
            return 7
        elif response_time < 15:
            return 5
        elif response_time < 20:
            return 3
        else:
            return 1
            
    def _score_retrieval(self, query: str, chunks: List[str]) -> int:
        """Score quality of retrieved chunks (0-10)"""
        if not chunks:
            return 5
            
        # Extract key terms from query
        query_terms = set(query.lower().split())
        
        # Check how many chunks are relevant
        relevant_chunks = 0
        for chunk in chunks[:5]:  # Only check top 5
            chunk_lower = chunk.lower()
            if any(term in chunk_lower for term in query_terms):
                relevant_chunks += 1
                
        relevance_ratio = relevant_chunks / min(5, len(chunks))
        return int(relevance_ratio * 10)
        
    def _calculate_grade(self, total_score: int) -> str:
        """Convert score to letter grade"""
        if total_score >= 90:
            return "EXCELLENT"
        elif total_score >= 70:
            return "GOOD"
        elif total_score >= 50:
            return "NEEDS IMPROVEMENT"
        else:
            return "POOR"
            
    def _identify_specific_issues(self, response: str, scores: Dict[str, int]) -> List[str]:
        """Identify specific issues based on scores"""
        issues = []
        
        if scores.get('formatting', 10) < 7:
            if '**' not in response:
                issues.append("Missing markdown emphasis")
            if '\n\n' not in response and len(response) > 200:
                issues.append("Wall of text - needs paragraph breaks")
                
        if scores.get('length', 10) < 7:
            word_count = len(response.split())
            if word_count > 200:
                issues.append(f"Too long ({word_count} words, should be <200)")
            else:
                issues.append(f"Too short ({word_count} words, should be 50-200)")
                
        if scores.get('actionability', 10) < 5:
            issues.append("No clear next steps or contact information")
            
        if scores.get('speed', 10) < 7:
            issues.append("Response too slow")
            
        return issues
        
    def generate_report(self, results: List[EvaluationResult]) -> str:
        """Generate summary report across multiple evaluations"""
        total_tests = len(results)
        critical_failures = sum(1 for r in results if r.critical_failures)
        
        avg_score = sum(r.total_score for r in results) / total_tests if total_tests > 0 else 0
        avg_time = sum(r.response_time for r in results) / total_tests if total_tests > 0 else 0
        
        grade_counts = {}
        for r in results:
            grade_counts[r.grade] = grade_counts.get(r.grade, 0) + 1
            
        # Collect all issues
        all_issues = {}
        for r in results:
            for issue in r.issues:
                all_issues[issue] = all_issues.get(issue, 0) + 1
                
        report = f"""
=== TIGERRESEARCHBUDDY EVALUATION REPORT ===

Total Tests: {total_tests}
Critical Failures: {critical_failures} ({critical_failures/total_tests*100:.1f}%)

Average Score: {avg_score:.1f}/100
Average Response Time: {avg_time:.2f}s

Grade Distribution:
"""
        for grade, count in sorted(grade_counts.items()):
            report += f"  {grade}: {count} ({count/total_tests*100:.1f}%)\n"
            
        report += "\nMost Common Issues:\n"
        sorted_issues = sorted(all_issues.items(), key=lambda x: x[1], reverse=True)
        for issue, count in sorted_issues[:10]:
            report += f"  {count}x: {issue}\n"
            
        report += "\nFailed Tests:\n"
        for r in results:
            if r.critical_failures or r.total_score < 50:
                report += f"\nQuery: {r.query[:60]}...\n"
                report += f"  Score: {r.total_score}/100\n"
                if r.critical_failures:
                    report += f"  Critical: {', '.join(r.critical_failures)}\n"
                if r.issues:
                    report += f"  Issues: {', '.join(r.issues[:3])}\n"
                    
        return report


# === EXAMPLE USAGE ===

if __name__ == "__main__":
    # Example: Evaluate a set of responses
    
    known_faculty = [
        "Christopher Kanan",
        "Zack Butler",
        "Rajendra Raj",
        "Cecilia Ovesdotter Alm"
    ]
    
    evaluator = ResponseEvaluator(known_faculty=known_faculty)
    
    # Test case 1: Good response
    result1 = evaluator.evaluate_response(
        query="Who works on machine learning?",
        response="""**Christopher Kanan** (Computer Science)
Expert in deep learning and computer vision.

📧 kanan@rit.edu | 📍 GOL-3210

Dr. Kanan's research focuses on visual recognition and neural networks. He has published extensively in CVPR and ICCV.""",
        response_time=4.2,
        expected_answer="Christopher Kanan works on machine learning and computer vision"
    )
    
    print(f"Test 1: {result1.grade} ({result1.total_score}/100)")
    print(f"Issues: {result1.issues}\n")
    
    # Test case 2: Response with artifacts
    result2 = evaluator.evaluate_response(
        query="Tell me about Professor Raj",
        response="""Result 1 (professor): Rajendra Raj
Context: Faculty profile from database
research_area: Software Engineering
He works on software testing.""",
        response_time=3.5
    )
    
    print(f"Test 2: {result2.grade} ({result2.total_score}/100)")
    print(f"Critical Failures: {result2.critical_failures}")
    print(f"Issues: {result2.issues}\n")
    
    # Generate report
    results = [result1, result2]
    print(evaluator.generate_report(results))
