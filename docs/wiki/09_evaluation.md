# 09 - Evaluation & Testing

**Last Updated:** February 23, 2026  
**Purpose:** Systematic evaluation framework, test query dataset, scoring templates, and testing workflows for TigerBrain

---

## Table of Contents

1. [Evaluation Philosophy](#evaluation-philosophy)
2. [Automated Evaluator](#automated-evaluator)
3. [Response Evaluation Framework (100 Questions)](#response-evaluation-framework-100-questions)
4. [Test Query Dataset (100 Queries)](#test-query-dataset-100-queries)
5. [Quick Response Scoring Template](#quick-response-scoring-template)
6. [Implementation Guide: How to Use the Framework](#implementation-guide-how-to-use-the-framework)

---

## Evaluation Philosophy

The core cycle is: **Measure → Fix → Measure → Fix**

Never make improvements blindly. Always:
1. Establish a baseline score before any change.
2. Change **one thing** at a time.
3. Measure again and compare.
4. Only ship if the change improved scores without regressions.

**The 4 biggest ROI areas** (in priority order):
1. Ingestion fidelity (garbage in = garbage out)
2. Hybrid retrieval + reranking precision
3. Graph query scalability
4. Eval/observability to prevent regressions

---

## Automated Evaluator

The automated evaluator script lives at `tests/automated_evaluator.py`. It is the primary tool for batch and continuous testing.

### Basic Usage

```python
from tests.automated_evaluator import ResponseEvaluator

evaluator = ResponseEvaluator(known_faculty=YOUR_FACULTY_LIST)
results = []

for query in ALL_100_QUERIES:
    start_time = time.time()
    response = your_rag_system.query(query)
    response_time = time.time() - start_time
    
    result = evaluator.evaluate_response(
        query=query,
        response=response,
        response_time=response_time
    )
    results.append(result)

report = evaluator.generate_report(results)
print(report)

# Save for tracking over time
with open('tests/results/test_results.json', 'w') as f:
    json.dump([asdict(r) for r in results], f, indent=2)
```

### Canary Tests (Daily — 5 minutes)

```python
CANARY_QUERIES = [
    "Who is Christopher Kanan?",        # Faculty lookup
    "Who works on robotics?",           # Topic search
    "What's the email for Prof Butler?", # Contact info
    "Anyone else work on AI?",          # Follow-up (requires context)
    "Recipe for cookies",               # Off-topic (should refuse)
]

for query in CANARY_QUERIES:
    response = rag_system.query(query)
    result = evaluator.evaluate_response(query, response)
    if result.total_score < 70:
        raise Alert(f"Canary test failed! Query: {query}, Score: {result.total_score}")
```

### A/B Testing Workflow

```python
# Test a change (e.g., adding hybrid search)
control_results  = [evaluate(current_system.query(q)) for q in TEST_QUERIES]
treatment_results = [evaluate(new_system.query(q)) for q in TEST_QUERIES]

improvement = np.mean(treatment_results) - np.mean(control_results)

if improvement > 5:   print("✅ Ship it!")
elif improvement > 0: print("⚠️ Marginal improvement — decide carefully")
else:                 print("❌ Don't ship — made things worse")
```

---

## Response Evaluation Framework (100 Questions)

Use this 100-question checklist to systematically score any response.

### Category 1: Response Quality & Accuracy (20 questions)

**Factual Correctness**
1. Does the response contain factually incorrect information about faculty, research, or facilities?
2. Are all faculty names spelled correctly?
3. Are email addresses in the correct format (`name@rit.edu`)?
4. Are office locations accurate and current?
5. Are research area descriptions accurate based on source data?
6. Are publication titles and years correct?
7. Does the response confuse two different faculty members?
8. Are department affiliations accurate?

**Hallucination Detection**
9. Does the response mention faculty who don't exist in the database?
10. Does the response invent research areas not present in source data?
11. Are there any fabricated paper titles or collaborations?
12. Does the response make up office hours, contact info, or availability?
13. Are there claims about "recent" work without temporal grounding?
14. Does the response attribute work to the wrong person?
15. Are there invented statistics or numbers (citation counts, lab sizes, etc.)?

**Completeness**
16. Does the response answer the actual question asked?
17. Are critical pieces of information missing (e.g., email when asked for contact)?
18. If multiple faculty match, are all relevant ones mentioned?
19. If no match exists, does it clearly state that?
20. Are alternative suggestions provided when a direct answer isn't available?

---

### Category 2: Response Structure & Formatting (15 questions)

**Internal Artifacts (Critical Issues — must all be clean)**
21. Does the response contain "Result 1:", "Result 2:", etc.?
22. Are there visible "Context:" or "professor:" labels?
23. Does it show ChromaDB metadata like "doc_type:" or "chunk_id:"?
24. Are there raw JSON structures in the output?
25. Does it display similarity scores or confidence values?
26. Are there system prompts or internal reasoning leaked?

**Markdown & Readability**
27–33. Is the response properly formatted with markdown? Bold names? Proper emoji usage (📧, 📍)? Appropriate bullet points and headers? Non-wall-of-text?

**Length & Conciseness**
34. Is the response under 200 words (2–3 short paragraphs)?
35. Does it avoid unnecessary verbosity or repetition?
36–38. Is every sentence adding value? For simple queries, is it concise (<100 words)?

---

### Category 3: Relevance & Context Understanding (15 questions)

**Query Intent Recognition**
39–43. Did the system correctly identify the query type (faculty lookup vs. topic search vs. follow-up)? For pronoun references ("What's their email?"), does it resolve correctly?

**Topical Relevance**
44–48. If asked about ML, are results actually ML-related? Does it avoid topic drift? Prioritize most relevant first?

**Scope Appropriateness**
49–53. For broad queries, does it acknowledge breadth and sample? For specific queries, give precise results? Stay within RIT Computing scope?

---

### Category 4: User Experience & Trust (15 questions)

**Tone & Professionalism** — 54–58: Appropriate, inclusive, consistent, not robotic.

**Actionability** — 59–63: Concrete next steps, contact methods, research opportunities explicitly mentioned?

**Transparency & Citations** — 64–68: Sources indicated? Uncertainty acknowledged? Consistent citation format?

**Confidence & Certainty** — 69–73: Confidently answers when facts are available? Clearly says "I don't know" when not? No excessive hedging?

---

### Category 5: Technical Performance (10 questions)

74–77. Response time < 10s? Error handling? Proportional to complexity?

**Retrieval Quality**
78–82. Were retrieved context chunks actually relevant? Was the right retrieval method (vector vs. hybrid) used? Too much noise? Good recall?

**System Behavior**
83–86. Handles typos gracefully? Edge cases (multiple roles)? Graceful fallbacks? User-friendly error messages?

---

### Category 6: Conversation & Context (10 questions)

87–94. Remembers previous query? Resolves pronouns (he/she/they) to previously mentioned faculty? Handles "Also" / "Anyone else"? Doesn't repeat info already given?

---

### Category 7: Edge Cases & Error Handling (10 questions)

95–97. Off-topic queries politely declined and redirected?
98–100. Misspelled names: fuzzy match or clarification? Multiple interpretations: most likely chosen? No good answer: helpful alternatives rather than silent failure?

---

### Scoring System

**Critical Failures (Auto-Fail — check these first):**
- Contains internal artifacts (Result 1:, Context:, etc.)
- Hallucinated faculty or information
- Response time >30 seconds
- Off-topic answers to on-topic queries
- Fabricated contact information

**Quality Tiers:**

| Score | Grade | Characteristics |
|-------|-------|----------------|
| 90–100 | Excellent ✅ | All critical checks pass, concise, accurate, fast (<5s) |
| 70–89 | Good 👍 | No critical failures, minor formatting, <10s |
| 50–69 | Needs Work ⚠️ | Accuracy/formatting issues, 10–15s |
| <50 | Failing ❌ | Critical failures, multiple accuracy issues |

---

## Test Query Dataset (100 Queries)

### Category 1: Faculty Name Lookup — 15 queries

**Direct Name Queries:** `"Who is Christopher Kanan?"` / `"Tell me about Professor Zack Butler"` / `"What does Dr. Rajendra Raj work on?"` / `"Find information on Cecilia Alm"` / `"Who is Stephanie Ludi?"`

**Name Variations & Titles:** `"Prof. Kanan"` / `"Professor C. Kanan"` / `"Dr Butler"` / `"christopher kanan"` (lowercase) / `"ZACK BUTLER"` (uppercase)

**Typos & Fuzzy Matching:** `"Christoper Kanan"` (typo) / `"Chris Kanan"` (nickname) / `"Kanan Christopher"` (reversed) / `"Christopher Kanan-Smith"` (extra hyphen)

*Expected:* Faculty profile with name, email, office, research areas. Handle title variations and attempt fuzzy match for typos. Response time <5s.

---

### Category 2: Contact Information — 10 queries

`"What is Christopher Kanan's email?"` / `"How do I contact Professor Butler?"` / `"Where is Dr. Raj's office?"` / `"Office hours for Stephanie Ludi"` / `"Contact info for the robotics professor"` (vague) / `"Email address for machine learning faculty"` (multiple matches) / `"What building is Dr. Butler in?"`

*Expected:* 📧 email@rit.edu format, 📍 GOL-XXXX location. Don't fabricate contact information.

---

### Category 3: Research Topic — 15 queries

**Specific:** `"Who works on machine learning?"` / `"Faculty studying natural language processing"` / `"Who does research in robotics?"` / `"Professors working on cybersecurity"`

**Broad:** `"Who works on AI?"` / `"Tell me about software engineering research"` / `"Who studies algorithms?"`

**Interdisciplinary:** `"Who works on AI in healthcare?"` / `"Professors doing ML for accessibility"` / `"NLP for social media analysis"` / `"AI ethics research"`

*Expected:* 2–5 relevant faculty with brief descriptions, prioritized by relevance. Acknowledge if query is too broad.

---

### Category 4: Research Opportunities — 10 queries

`"Which professors are accepting PhD students?"` / `"Undergraduate research opportunities in AI"` / `"Can I do research with Professor Kanan?"` / `"Who is hiring research assistants?"` / `"How to get involved in ML research as an undergrad"`

*Expected:* Mention availability if known; provide contact email; suggest general process if info unavailable. Never make up availability status.

---

### Category 5: Publications — 10 queries

`"What has Christopher Kanan published recently?"` / `"Papers by Professor Butler on robotics"` / `"Co-authored papers by Kanan and Butler"` / `"Who has published in CVPR?"` / `"Papers on transfer learning"`

*Expected:* 2–3 papers with titles and years if available. Don't fabricate paper titles or venues.

---

### Category 6: Comparison & Multi-Faculty — 10 queries

`"Compare research of Kanan and Butler"` / `"Who collaborates with Professor Butler?"` / `"Which professor should I contact for AI projects?"` / `"Faculty who work together on projects"`

*Expected:* Factual comparisons only. Avoid subjective rankings ("better"). Use knowledge graph for collaboration insights.

---

### Category 7: Follow-up & Context-Dependent — 10 queries

**Pronoun resolution:**
- `"Tell me about Christopher Kanan"` → `"What's his email?"`
- `"Who works on robotics?"` → `"Tell me more about the first one"`
- `"Faculty in machine learning"` → `"Which of them accepts undergrads?"`

**Additive:** `"Who works on computer vision?"` → `"Anyone else?"`

**Clarification:** `"Who works on AI?"` → `"I meant specifically deep learning"`

*Expected:* Maintains last 3–5 exchanges context. Resolves pronouns. Understands "also", "anyone else". Doesn't repeat info.

---

### Category 8: Off-Topic (Should Refuse) — 10 queries

`"What's the weather today?"` / `"How do I bake a chocolate cake?"` / `"Who won the Super Bowl?"` / `"Latest movie releases"` / `"Best restaurants in Rochester"`

*Expected:* Politely decline. Explain scope. Suggest appropriate topics. Do NOT attempt to use RIT data to answer.

---

### Category 9: Edge Cases & Stress Tests — 10 queries

**Ambiguous:** `"Tell me about Professor Smith"` / `"Who works on learning?"` / `"Research in vision"`

**Non-existent:** `"Who is Professor Xylophone?"` / `"Tell me about Dr. Alan Turing at RIT"`

**Boundary:** `""` (empty) / `"????????"` (non-English) / `"asdfghjkl"` (gibberish) / `"a"` (single char)

*Expected:* "I don't know" for non-existent faculty. No hallucinations. Graceful handling without errors.

---

### Expected Response Templates

**Good Faculty Lookup:**
```
**Christopher Kanan** (Computer Science)
Expert in deep learning and computer vision.

📧 kanan@rit.edu | 📍 GOL-3210

Dr. Kanan's research focuses on visual recognition and continual learning. 
Recent work includes publications in CVPR and NeurIPS.
```

**Good Topic Search:**
```
Several faculty work on machine learning:

**Christopher Kanan** — Deep learning, computer vision  📧 kanan@rit.edu
**Cecilia Alm** — NLP, computational linguistics  📧 coagla@rit.edu

Each has different specializations — email them to discuss your interests!
```

**Good Off-Topic Refusal:**
```
I don't have information about weather in my RIT Computing research database.

I specialize in helping you find: faculty research areas, contact information, 
research opportunities, and publications.

Try asking: "Who works on machine learning?" or "Contact info for Prof Kanan"
```

---

## Quick Response Scoring Template

Copy this for each test run:

```
TEST CASE
Query: _______________________________________________
Query Type: [ ] Faculty Lookup  [ ] Topic Search  [ ] Follow-up  [ ] Off-topic
Response Time: _______ seconds

CRITICAL CHECKS (Auto-Fail if any fail)
[ ] No "Result 1:" or similar artifacts
[ ] No hallucinated faculty/info
[ ] Response time < 30s
[ ] On-topic if query is on-topic
[ ] No fabricated contact info
CRITICAL FAILURE? [ ] YES  [ ] NO (continue scoring)

QUALITY SCORES (0–10 each)
Factual accuracy     ___/10 × 2 = ___/20
Relevance            ___/10 × 2 = ___/20
Markdown formatting  ___/10 × 1 = ___/10
Appropriate length   ___/10 × 1 = ___/10
Actionability        ___/10 × 1 = ___/10
Tone                 ___/10 × 1 = ___/10
Response speed       ___/10 × 1 = ___/10
Retrieval quality    ___/10 × 1 = ___/10

TOTAL: ___/100  Grade: ______

ISSUES FOUND:
- Formatting: [ ] artifacts [ ] wall of text [ ] too long [ ] no markdown
- Content:    [ ] wrong faculty [ ] missing info [ ] irrelevant info
- Technical:  [ ] slow [ ] wrong chunks [ ] no context
Root cause: _____________________________________________
Suggested fix: __________________________________________
```

---

## Implementation Guide: How to Use the Framework

### Quick Start (5 minutes)

Run these 5 queries, check the 5 critical checks for each:
1. `"Who is Christopher Kanan?"` — faculty lookup
2. `"Who works on machine learning?"` — topic search
3. `"What's his email?"` — follow-up (requires context)
4. `"Recipe for cake"` — off-topic (should refuse)
5. `"Who is Professor Fake-Name?"` — non-existent (should say "I don't know")

If any critical check fails → you have P0 issues to fix immediately.

### Weekly Deep Analysis (1 hour)

1. Run full 100-query suite with `tests/automated_evaluator.py`
2. Analyze failures by category — focus on the biggest cluster
3. Create priority list: Impact × Severity ÷ Difficulty

```
Priority 1 (High Impact + Easy):
  → Strip artifacts via response post-processing (fixes many queries at once)

Priority 2 (High Impact + Medium):
  → Add conversation memory (fixes all follow-up failures)

Priority 3 (Medium Impact + Hard):
  → Implement cross-encoder re-ranking (complex, but high precision gain)
```

### Testing Anti-Patterns to Avoid

| ❌ Bad | ✅ Good |
|--------|---------|
| Only test happy path | Include typos, non-existent entities, off-topic |
| Manually inspect every response | Automated checks; manually review only failures |
| Change multiple things at once | One change at a time; verify before next change |
| Ignore regressions | Always run full regression suite after changes |

### Success Metrics (track over time)

| Metric | Target |
|--------|--------|
| Average score | > 80/100 |
| Critical failure rate | < 5% |
| Hallucination rate | 0% |
| Off-topic refusal rate | 100% |
| Average response time | < 5s |
| Cache hit rate | > 40% |

### Sample Weekly Report

```
=== TIGERBRAIN WEEKLY REPORT ===
Week of: Feb 17–20, 2026

SUMMARY:
✅ 78/100 avg score (+4 from last week)
✅ 5% critical failures (-3%)
✅ 6.2s avg response time (-0.8s)

TOP WINS:
1. Eliminated all artifact leakage (was 15 queries, now 0)
2. Added conversation memory → follow-ups improved 25%

TOP ISSUES REMAINING:
1. Still hallucinating on 3–4 edge case queries
2. Off-topic refusals inconsistent (8/10 correct)
3. Complex multi-faculty queries still slow (>8s)

ACTIONS FOR NEXT WEEK:
1. Implement confidence threshold to fix hallucinations
2. Strengthen intent classifier for off-topic
3. Add caching for multi-faculty queries
```

---

**Next:** [Architecture →](./01_architecture.md)  
**See also:** `tests/automated_evaluator.py`, `.github/workflows/test.yml`
