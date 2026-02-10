# TigerResearchBuddy Response Evaluation Framework
## 100 Questions for Systematic Response Analysis

---

## Category 1: Response Quality & Accuracy (20 questions)

### Factual Correctness
1. Does the response contain any factually incorrect information about faculty, research, or facilities?
2. Are all faculty names spelled correctly?
3. Are email addresses in the correct format (name@rit.edu)?
4. Are office locations accurate and current?
5. Are research area descriptions accurate based on source data?
6. Are publication titles and years correct?
7. Does the response confuse two different faculty members?
8. Are department affiliations accurate?

### Hallucination Detection
9. Does the response mention faculty who don't exist in the database?
10. Does the response invent research areas not present in source data?
11. Are there any fabricated paper titles or collaborations?
12. Does the response make up office hours, contact info, or availability?
13. Are there claims about "recent" work without temporal grounding?
14. Does the response attribute work to the wrong person?
15. Are there invented statistics or numbers (citation counts, lab sizes, etc.)?

### Completeness
16. Does the response answer the actual question asked?
17. Are critical pieces of information missing (e.g., email when asked for contact)?
18. If multiple faculty match, are all relevant ones mentioned?
19. If no match exists, does it clearly state that?
20. Are alternative suggestions provided when direct answer isn't available?

---

## Category 2: Response Structure & Formatting (15 questions)

### Internal Artifacts (Critical Issues)
21. Does the response contain "Result 1:", "Result 2:", etc.?
22. Are there visible "Context:" or "professor:" labels?
23. Does it show ChromaDB metadata like "doc_type:" or "chunk_id:"?
24. Are there raw JSON structures in the output?
25. Does it display similarity scores or confidence values?
26. Are there system prompts or internal reasoning leaked?

### Markdown & Readability
27. Is the response properly formatted with markdown?
28. Are faculty names bolded appropriately?
29. Are email addresses and locations clearly marked (📧, 📍)?
30. Is there proper paragraph spacing (not a wall of text)?
31. Are bullet points used appropriately (when listing multiple items)?
32. Are headers used correctly (not overused)?
33. Is the text hierarchy logical and scannable?

### Length & Conciseness
34. Is the response under 200 words (2-3 short paragraphs)?
35. Does it avoid unnecessary verbosity or repetition?
36. Could the same information be conveyed in fewer words?
37. Is every sentence adding value, or is there filler?
38. For simple queries (faculty lookup), is it concise (under 100 words)?

---

## Category 3: Relevance & Context Understanding (15 questions)

### Query Intent Recognition
39. Did the system correctly identify the query type (faculty lookup vs. topic search)?
40. For ambiguous queries, did it make a reasonable interpretation?
41. For follow-up questions ("Anyone else?"), does it maintain context?
42. For pronoun references ("What's their email?"), does it resolve correctly?
43. Does it distinguish between "Who works on X?" vs. "Tell me about Professor Y"?

### Topical Relevance
44. If asked about machine learning, are results actually ML-related?
45. Does it avoid topic drift (e.g., talking about robotics when asked about NLP)?
46. Are research area descriptions relevant to the query?
47. If multiple topics are mentioned, does it address all of them?
48. Does it prioritize the most relevant information first?

### Scope Appropriateness
49. For broad queries ("AI research"), does it acknowledge breadth and provide representative examples?
50. For specific queries ("CUDA programming"), does it give precise results?
51. Does it stay within RIT Computing scope (not mention random universities)?
52. Does it avoid going off-topic to unrelated RIT departments?
53. If a query is too vague, does it ask for clarification or make reasonable assumptions?

---

## Category 4: User Experience & Trust (15 questions)

### Tone & Professionalism
54. Is the tone appropriate for students seeking academic guidance?
55. Does it avoid being overly casual or using slang?
56. Does it avoid being overly formal or robotic?
57. Is the language inclusive and welcoming?
58. Does it maintain consistency in tone throughout the response?

### Actionability
59. Does the response provide next steps (e.g., "Email Prof X at...")?
60. If suggesting contact, is the contact method clearly stated?
61. Are there concrete actions the student can take?
62. If research opportunities exist, are they explicitly mentioned?
63. Does it avoid vague suggestions like "check the website" without specifics?

### Transparency & Citations
64. When factual claims are made, are sources indicated?
65. If uncertainty exists, does it acknowledge it?
66. Does it distinguish between direct database info vs. inferred connections?
67. Are citations formatted consistently (if implemented)?
68. Can the user verify the information independently?

### Confidence & Certainty
69. Does it confidently answer when information is available?
70. Does it clearly say "I don't know" when information is missing?
71. Does it avoid hedging excessively ("maybe," "possibly," "might") when facts are clear?
72. Does it indicate confidence level appropriately?
73. Does it avoid overconfident claims about unavailable data?

---

## Category 5: Technical Performance (10 questions)

### Speed & Efficiency
74. Was the response generated in under 10 seconds?
75. If it took longer than 10s, was there a timeout/partial result?
76. Does the response time seem proportional to query complexity?
77. Are there unnecessary delays or hanging?

### Retrieval Quality
78. Were the retrieved context chunks actually relevant to the query?
79. If vector search was used, was it the right approach for this query type?
80. Should hybrid search have been used but wasn't?
81. Were too many irrelevant chunks retrieved (noise)?
82. Were important chunks missed (recall issue)?

### System Behavior
83. Did the system gracefully handle typos in faculty names?
84. Did it handle edge cases (e.g., faculty with multiple roles)?
85. If ChromaDB returned no results, was there a proper fallback?
86. Did error states display user-friendly messages?

---

## Category 6: Conversation & Context (10 questions)

### Multi-Turn Capability
87. For follow-up questions, does it remember the previous query?
88. Can it handle "Also" or "Additionally" questions?
89. Does it correctly resolve "he/she/they" pronouns to previously mentioned faculty?
90. Can it compare two faculty members if asked in sequence?

### Context Maintenance
91. If a user asks "Who works on ML?" then "Anyone in robotics?", does it keep both topics in mind?
92. Does it avoid repeating information already provided in the conversation?
93. Can it synthesize across multiple exchanges (e.g., building a list)?
94. Does conversation history improve relevance of later responses?

---

## Category 7: Edge Cases & Error Handling (10 questions)

### Off-Topic Queries
95. For completely off-topic queries (weather, recipes), does it politely decline?
96. Does it avoid attempting to answer non-RIT questions with RIT data?
97. Does the refusal message guide users back to appropriate topics?

### Ambiguity & Errors
98. For misspelled names, does it attempt fuzzy matching or ask for clarification?
99. If a query has multiple valid interpretations, does it address the most likely one?
100. For queries with no good answer, does it provide helpful alternatives rather than failing silently?

---

## Scoring System

### Critical Failures (Auto-Fail)
- Contains internal artifacts (Result 1:, Context:, etc.)
- Hallucinated faculty or information
- Response time >30 seconds
- Off-topic answers to on-topic questions
- Fabricated contact information

### Quality Tiers
**Excellent (90-100 points):**
- All critical questions pass
- Response is concise, accurate, and actionable
- Proper formatting and citations
- Fast (<5s response time)

**Good (70-89 points):**
- No critical failures
- Minor formatting issues or slight verbosity
- Accurate but could be more concise
- Acceptable response time (5-10s)

**Needs Improvement (50-69 points):**
- Some accuracy issues or missing information
- Poor formatting or length issues
- Slow response time (10-15s)
- Lacks citations or actionability

**Failing (<50 points):**
- Contains critical failures
- Multiple accuracy issues
- Unusable formatting
- Extremely slow or timeout

---

## How to Use This Framework

### For Individual Response Evaluation:
1. Copy this checklist for each test query
2. Mark Yes/No/N/A for each applicable question
3. Note specific issues in comments
4. Calculate score based on critical failures + quality tier
5. Identify patterns across similar queries

### For Batch Analysis:
1. Select 20 representative queries covering different types
2. Run all 100 questions on each
3. Create a spreadsheet tracking pass/fail rates per question
4. Identify the top 10 failing questions
5. Prioritize fixes for most common failures

### For A/B Testing:
1. Run same queries through old vs. new system
2. Compare scores question-by-question
3. Measure improvement in specific categories
4. Focus on questions where new system should excel

### For Continuous Monitoring:
1. Select 10-15 "canary" questions (most important)
2. Run daily/weekly automated tests
3. Alert when scores drop below threshold
4. Track trends over time

---

## Quick Reference: Question Categories by Priority

### Must-Pass (P0):
- Questions 21-26 (Internal artifacts)
- Questions 1-8 (Factual correctness)
- Questions 9-15 (Hallucination detection)
- Question 70 (Says "I don't know" when appropriate)
- Question 95-96 (Off-topic handling)

### High Priority (P1):
- Questions 34-38 (Length/conciseness)
- Questions 39-43 (Intent recognition)
- Questions 59-63 (Actionability)
- Questions 74-77 (Speed)

### Medium Priority (P2):
- Questions 27-33 (Formatting)
- Questions 44-53 (Relevance)
- Questions 87-94 (Conversation memory)

### Nice-to-Have (P3):
- Questions 64-68 (Citations)
- Questions 54-58 (Tone)
- Questions 98-100 (Error handling)
