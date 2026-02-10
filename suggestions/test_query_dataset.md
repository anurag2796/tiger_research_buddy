# Comprehensive Test Query Dataset for TigerResearchBuddy
## 100 Test Queries Organized by Type and Difficulty

---

## Category 1: Faculty Name Lookup (Simple) - 15 queries

### Direct Name Queries
1. "Who is Christopher Kanan?"
2. "Tell me about Professor Zack Butler"
3. "What does Dr. Rajendra Raj work on?"
4. "Find information on Cecilia Alm"
5. "Who is Stephanie Ludi?"

### Name Variations & Titles
6. "Prof. Kanan" (abbreviated title)
7. "Professor C. Kanan" (first initial only)
8. "Dr Butler" (no period after title)
9. "christopher kanan" (lowercase)
10. "ZACK BUTLER" (uppercase)

### Typos & Fuzzy Matching
11. "Christopher Kanan" (correct - baseline)
12. "Christoper Kanan" (typo - one letter)
13. "Chris Kanan" (nickname)
14. "Kanan Christopher" (reversed)
15. "Christopher Kanan-Smith" (extra hyphen)

**Expected Behavior:**
- Should return faculty profile with name, email, office, research areas
- Should handle title variations gracefully
- Should attempt fuzzy matching for typos
- Response time: <5 seconds

---

## Category 2: Contact Information Queries - 10 queries

16. "What is Christopher Kanan's email?"
17. "How do I contact Professor Butler?"
18. "Where is Dr. Raj's office?"
19. "What's the email for Cecilia Alm?"
20. "Office hours for Stephanie Ludi"
21. "How to reach Prof Kanan"
22. "Contact info for the robotics professor" (vague)
23. "Email address for machine learning faculty" (multiple matches)
24. "Where can I find Professor Kanan?" (location)
25. "What building is Dr. Butler in?"

**Expected Behavior:**
- Should include 📧 email@rit.edu format
- Should include 📍 GOL-XXXX office location
- Should handle vague queries by listing all relevant contacts
- Should not fabricate contact information

---

## Category 3: Research Topic Queries (Medium Complexity) - 15 queries

### Specific Technical Topics
26. "Who works on machine learning?"
27. "Who researches computer vision?"
28. "Faculty studying natural language processing"
29. "Who does research in robotics?"
30. "Professors working on cybersecurity"

### Broad Topics
31. "Who works on AI?" (very broad)
32. "Tell me about software engineering research"
33. "Who does theory work?" (theoretical CS)
34. "Faculty in systems research"
35. "Who studies algorithms?"

### Interdisciplinary Topics
36. "Who works on AI in healthcare?"
37. "Professors doing machine learning for accessibility"
38. "Research in computer vision for robotics"
39. "NLP for social media analysis"
40. "AI ethics research"

**Expected Behavior:**
- Should list 2-5 relevant faculty with brief descriptions
- Should prioritize by relevance (specific matches first)
- Should acknowledge if topic is too broad
- Should mention interdisciplinary connections when relevant

---

## Category 4: Research Opportunity Queries - 10 queries

41. "Which professors are accepting PhD students?"
42. "Undergraduate research opportunities in AI"
43. "Can I do research with Professor Kanan?"
44. "Who is hiring research assistants?"
45. "Graduate opportunities in computer vision"
46. "Is Dr. Butler taking on new students?"
47. "Research positions available in robotics"
48. "Summer research programs in CS"
49. "How to get involved in ML research as an undergrad"
50. "Faculty with funded projects"

**Expected Behavior:**
- Should mention if availability information exists
- Should provide contact email for inquiry
- Should suggest general process if specific info unavailable
- Should not make up availability status

---

## Category 5: Publication & Paper Queries - 10 queries

51. "What has Christopher Kanan published recently?"
52. "Papers by Professor Butler on robotics"
53. "Dr. Raj's most cited work"
54. "Recent publications in computer vision"
55. "Who has published in CVPR?"
56. "What conferences does Prof Kanan publish in?"
57. "Co-authored papers by Kanan and Butler" (collaboration)
58. "Faculty with Nature publications"
59. "Most prolific researchers in the department"
60. "Papers on transfer learning"

**Expected Behavior:**
- Should list recent papers if available (2-3 examples)
- Should include paper titles and years
- Should acknowledge if publication data is limited
- Should not fabricate paper titles or venues

---

## Category 6: Comparison & Multi-Faculty Queries - 10 queries

61. "Compare research of Kanan and Butler"
62. "Differences between Raj and Ludi's work"
63. "Who is better for ML research - Kanan or Alm?"
64. "Faculty working on similar topics to Kanan"
65. "Who collaborates with Professor Butler?"
66. "Which professor should I contact for AI projects?"
67. "Rank faculty by computer vision expertise"
68. "Most active researchers in the department"
69. "Who publishes more - Kanan or Raj?"
70. "Faculty who work together on projects"

**Expected Behavior:**
- Should present factual comparisons (research areas, publications)
- Should avoid subjective rankings ("better")
- Should use knowledge graph for collaboration insights
- Should suggest both faculty if question implies choice

---

## Category 7: Follow-up & Context-Dependent Queries - 10 queries

### Pronoun Resolution
71. First: "Tell me about Christopher Kanan"
    Follow-up: "What's his email?"
72. First: "Who works on robotics?"
    Follow-up: "Tell me more about the first one"
73. First: "Faculty in machine learning"
    Follow-up: "Which of them accepts undergrads?"

### Additive Queries
74. First: "Who works on computer vision?"
    Follow-up: "Anyone else?"
75. First: "Dr. Kanan's research"
    Follow-up: "Also tell me about his publications"

### Clarification Queries
76. First: "Who works on AI?"
    Follow-up: "I meant specifically deep learning"
77. First: "Contact for robotics professor"
    Follow-up: "I meant Zack Butler"

### Comparative Follow-ups
78. First: "Tell me about Kanan"
    Follow-up: "How does Butler's work compare?"
79. First: "Who works on NLP?"
    Follow-up: "Which one is better for sentiment analysis?"
80. First: "Faculty in cybersecurity"
    Follow-up: "Do any of them teach undergraduate courses?"

**Expected Behavior:**
- Should maintain conversation context (last 3-5 exchanges)
- Should resolve pronouns correctly (he/she/they/them)
- Should understand "also", "anyone else", "more"
- Should not repeat information unnecessarily

---

## Category 8: Off-Topic Queries (Should Refuse) - 10 queries

81. "What's the weather today?"
82. "How do I bake a chocolate cake?"
83. "Who won the Super Bowl?"
84. "What's the stock price of Apple?"
85. "Capital of France?"
86. "Who is the president of the United States?"
87. "Recipe for pasta carbonara"
88. "Latest movie releases"
89. "How to fix my car"
90. "Best restaurants in Rochester"

**Expected Behavior:**
- Should politely decline to answer
- Should explain scope ("I specialize in RIT Computing research")
- Should suggest appropriate topics
- Should NOT attempt to use RIT data to answer

---

## Category 9: Edge Cases & Stress Tests - 10 queries

### Ambiguous Queries
91. "Tell me about Professor Smith" (common name, may not exist)
92. "Who works on learning?" (ambiguous - machine learning? education?)
93. "Research in vision" (computer vision? general vision science?)

### Non-existent Entities
94. "Who is Professor Xylophone?" (fabricated name)
95. "Tell me about Dr. Alan Turing at RIT" (famous but not at RIT)
96. "Contact info for John Smith in CS" (may not exist)

### Boundary Cases
97. "" (empty query)
98. "????????" (non-English)
99. "asdfghjkl" (gibberish)
100. "a" (single character)

**Expected Behavior:**
- Should say "I don't know" for non-existent faculty
- Should not hallucinate information
- Should ask for clarification on ambiguous queries
- Should handle edge cases gracefully without errors

---

## Scoring Rubric for Test Results

### Per Query Evaluation
- **Critical Pass (Required):**
  - No internal artifacts
  - No hallucinations
  - Response time <30s
  - Appropriate off-topic handling
  
- **Quality Scores (0-10 each):**
  - Accuracy: Is the information correct?
  - Relevance: Does it answer the question?
  - Formatting: Clean, readable markdown?
  - Length: 50-200 words?
  - Actionability: Clear next steps?
  - Speed: <10s response time?

### Overall Test Suite Success Criteria

**Excellent (90-100% pass rate):**
- All critical checks pass
- Average quality score >8/10
- No hallucinations
- Average response time <5s

**Good (70-89% pass rate):**
- <5 critical failures
- Average quality score >6/10
- Minimal hallucinations
- Average response time <10s

**Needs Improvement (50-69% pass rate):**
- 5-15 critical failures
- Average quality score >4/10
- Some hallucinations
- Average response time <15s

**Failing (<50% pass rate):**
- >15 critical failures
- Average quality score <4/10
- Frequent hallucinations
- Slow response times

---

## Recommended Testing Strategy

### Phase 1: Smoke Test (10 queries)
Run queries: 1, 16, 26, 41, 51, 61, 71, 81, 91, 97
**Purpose:** Quick check for critical failures

### Phase 2: Core Functionality (25 queries)
Run all Category 1, 2, and 3 queries
**Purpose:** Validate basic faculty lookup and topic search

### Phase 3: Advanced Features (25 queries)
Run all Category 4, 5, 6, and 7 queries
**Purpose:** Test complex reasoning and context

### Phase 4: Robustness (20 queries)
Run all Category 8 and 9 queries
**Purpose:** Ensure graceful failure handling

### Phase 5: Full Suite (100 queries)
Run all queries
**Purpose:** Comprehensive baseline before/after improvements

---

## Expected Response Templates

### Good Faculty Lookup Response:
```
**Christopher Kanan** (Computer Science)
Expert in deep learning and computer vision.

📧 kanan@rit.edu | 📍 GOL-3210

Dr. Kanan's research focuses on visual recognition, continual learning, and neural 
network interpretability. Recent work includes publications in CVPR and NeurIPS.
```

### Good Topic Search Response:
```
Several faculty work on machine learning:

**Christopher Kanan** - Deep learning, computer vision
📧 kanan@rit.edu

**Cecilia Alm** - NLP, computational linguistics  
📧 coagla@rit.edu

**Stephanie Ludi** - Accessible AI, human-computer interaction
📧 salvse@rit.edu

Each has different specializations - email them to discuss your interests!
```

### Good Off-Topic Refusal:
```
I don't have information about weather in my RIT Computing research database. 

I specialize in helping you find:
• Faculty and their research areas
• Contact information
• Research opportunities
• Publications and collaborations

Try asking: "Who works on machine learning?" or "Contact info for Prof Kanan"
```

### Good "I Don't Know" Response:
```
I don't have information about Professor Xylophone in my database. 

This could mean:
• The name is misspelled (try searching by research area)
• They're not in the Computing department
• They may be new or not yet in my system

Try: "Who works on [topic]?" or check the RIT Computing website directly.
```
