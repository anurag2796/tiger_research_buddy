# Implementation Guide: How to Use the Evaluation Framework

This guide shows you how to practically use the 100-question framework to improve TigerResearchBuddy.

---

## Quick Start (5 Minutes)

### Step 1: Run a Smoke Test
Pick 5 queries from the test dataset that represent core functionality:

1. "Who is Christopher Kanan?" (faculty lookup)
2. "Who works on machine learning?" (topic search)
3. "What's his email?" (follow-up - requires context)
4. "Recipe for cake" (off-topic - should refuse)
5. "Who is Professor Fake-Name?" (non-existent - should say "I don't know")

### Step 2: Score Each Response
For each response, check these 5 critical questions:
- ✅ No "Result 1:" or internal artifacts?
- ✅ No made-up faculty or information?
- ✅ Response in <30 seconds?
- ✅ Actually answers the question?
- ✅ Clean markdown formatting?

If any fail → You have critical issues to fix immediately.

### Step 3: Identify Top Issue
Look at what failed most:
- If artifacts present → Implement response post-processing
- If hallucinations → Add confidence thresholds
- If slow → Add timeout handling
- If off-topic not refused → Add intent classification

---

## Daily Testing Workflow (15 Minutes)

### Morning: Run Canary Tests
Keep 10-15 "canary queries" that should always pass. Run them daily:

```python
CANARY_QUERIES = [
    "Who is Christopher Kanan?",
    "Who works on robotics?",
    "What's the email for Prof Butler?",
    "Anyone else work on AI?",  # Follow-up
    "Recipe for cookies",  # Off-topic
]

for query in CANARY_QUERIES:
    response = your_rag_system.query(query)
    result = evaluator.evaluate_response(query, response, ...)
    if result.total_score < 70:
        ALERT("Canary test failed!")
```

### When You Make Changes
Before and after each improvement:

1. **Baseline Test** (before change):
   - Run 20 representative queries
   - Record scores in spreadsheet
   - Note specific failures

2. **Make Your Change** (e.g., add hybrid search)

3. **Regression Test** (after change):
   - Run same 20 queries
   - Compare scores side-by-side
   - Ensure no new failures introduced

4. **Document Improvement**:
   ```
   Change: Added BM25 hybrid search
   Queries Improved: 12/20 (+8 points avg)
   Queries Unchanged: 7/20
   Queries Degraded: 1/20 (-2 points) ← investigate this
   ```

---

## Weekly Deep Analysis (1 Hour)

### Run Full 100-Query Test Suite

```python
# Use the automated evaluator
from automated_evaluator import ResponseEvaluator

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

# Generate report
report = evaluator.generate_report(results)
print(report)

# Save results
with open('test_results.json', 'w') as f:
    json.dump([asdict(r) for r in results], f, indent=2)
```

### Analyze Patterns
Look for clusters of failures:

1. **By Query Type:**
   - Faculty lookups: 90% pass rate ✅
   - Topic searches: 60% pass rate ⚠️ ← Focus here
   - Follow-ups: 40% pass rate ❌ ← Critical issue

2. **By Failure Type:**
   - Internal artifacts: 15 occurrences ← Post-processing needed
   - Hallucinations: 8 occurrences ← Confidence threshold needed
   - Slow responses: 12 occurrences ← Timeout handling needed

3. **By Score Distribution:**
   ```
   Scores 90-100: 25 queries (Excellent)
   Scores 70-89:  40 queries (Good)
   Scores 50-69:  20 queries (Needs work)
   Scores <50:    15 queries (Failing)
   ```

### Prioritize Fixes
Create a priority list based on:
- **Impact:** How many queries does this affect?
- **Severity:** Critical failure vs. minor quality issue?
- **Difficulty:** Easy fix vs. major refactor?

Example prioritization:
```
Priority 1 (High Impact + High Severity + Easy):
  → Add response post-processing to strip artifacts (fixes 15 queries)
  
Priority 2 (High Impact + Medium Severity + Medium):
  → Add conversation memory for follow-ups (fixes 10 queries)
  
Priority 3 (Medium Impact + High Severity + Hard):
  → Implement hybrid search (fixes 12 queries, but complex)
```

---

## Monthly Review (2 Hours)

### Compare Month-Over-Month
Track improvement trends:

```
October Results:
- Average Score: 62/100
- Critical Failures: 25%
- Avg Response Time: 12.3s

November Results (after fixes):
- Average Score: 78/100 (+16) ✅
- Critical Failures: 8% (-17%) ✅
- Avg Response Time: 6.2s (-6.1s) ✅

Key Improvements:
1. Added post-processing → Eliminated all artifact issues
2. Added confidence threshold → Hallucinations down 80%
3. Added caching → Response time cut in half
```

### Identify New Test Cases
As you get real user queries, add them to test suite:

```python
# Log actual user queries
user_query_log = [
    "Is Prof Kanan accepting students right now?",  # Good - add to test
    "Can you compare Butler vs Ludi?",  # Edge case - add to test
    "Who teaches the AI class?",  # New query type - add to test
]

# Continuously expand your test coverage
```

---

## A/B Testing New Features

### Example: Testing Hybrid Search

**Setup:**
```python
# Control group: Current system (vector search only)
control_results = []

# Treatment group: New system (hybrid search)
treatment_results = []

# Use same 50 test queries for both
for query in TEST_QUERIES:
    # Run control
    control_response = current_system.query(query)
    control_score = evaluate(control_response)
    control_results.append(control_score)
    
    # Run treatment
    treatment_response = new_system.query(query)
    treatment_score = evaluate(treatment_response)
    treatment_results.append(treatment_score)
```

**Analysis:**
```python
# Statistical comparison
control_avg = np.mean(control_results)
treatment_avg = np.mean(treatment_results)
improvement = treatment_avg - control_avg

print(f"Control:   {control_avg:.1f}/100")
print(f"Treatment: {treatment_avg:.1f}/100")
print(f"Lift:      {improvement:+.1f} points")

# Is improvement significant?
if improvement > 5:
    print("✅ Ship it!")
elif improvement > 0:
    print("⚠️ Marginal improvement")
else:
    print("❌ Don't ship - made things worse")
```

---

## Common Anti-Patterns to Avoid

### ❌ Don't: Only test happy path
```python
# Bad: Only testing ideal queries
test_queries = [
    "Who is Christopher Kanan?",
    "Who works on ML?",
]
```

```python
# Good: Include edge cases and failures
test_queries = [
    "Who is Christopher Kanan?",  # Happy path
    "Who is Christoper Kanan?",   # Typo
    "Who is Dr. Fake-Name?",      # Doesn't exist
    "Who works on ML?",           # Happy path
    "Who works on learning?",     # Ambiguous
    "Recipe for cake",            # Off-topic
]
```

### ❌ Don't: Manually inspect every response
```python
# Bad: Manual checking doesn't scale
for query in ALL_QUERIES:
    response = system.query(query)
    print(response)
    input("Does this look good? (y/n)")  # Tedious!
```

```python
# Good: Automated checks with manual review of failures
results = []
for query in ALL_QUERIES:
    result = automated_evaluator.evaluate(query, response)
    results.append(result)
    
# Only manually review failures
failures = [r for r in results if r.total_score < 50]
print(f"Review these {len(failures)} failing queries...")
```

### ❌ Don't: Change multiple things at once
```python
# Bad: Can't tell what helped
def improve_system():
    add_hybrid_search()
    add_reranking()
    add_confidence_threshold()
    add_conversation_memory()
    # Which one actually improved things?
```

```python
# Good: Change one thing, test, iterate
def improve_system():
    baseline = run_tests()
    
    add_hybrid_search()
    after_hybrid = run_tests()
    if after_hybrid > baseline:
        commit_change()
    else:
        rollback()
    
    # Then try next improvement...
```

### ❌ Don't: Ignore regression
```python
# Bad: Only check if new queries work
def test_new_feature():
    new_queries = ["Who collaborates with Prof X?"]
    for q in new_queries:
        assert system.query(q).score > 70
    # But did we break existing queries?
```

```python
# Good: Always run regression suite
def test_new_feature():
    # Test new functionality
    new_queries = ["Who collaborates with Prof X?"]
    for q in new_queries:
        assert system.query(q).score > 70
    
    # Ensure old functionality still works
    run_regression_suite()  # All previous passing tests
```

---

## Recommended Tools & Setup

### Spreadsheet for Tracking
Create a Google Sheet with columns:
- Query ID
- Query Text
- Query Type
- Expected Answer
- Actual Response (link to full text)
- Score (0-100)
- Critical Failures (Y/N)
- Issues Found
- Status (Pass/Fail)
- Notes
- Date Tested
- System Version

### Git Commit Strategy
```bash
# Before making changes
python run_tests.py > baseline_results.json
git add baseline_results.json
git commit -m "Baseline: 62/100 avg score before hybrid search"

# After changes
python run_tests.py > after_hybrid_results.json
git add after_hybrid_results.json
git commit -m "After hybrid search: 78/100 avg score (+16)"

# Can now diff the results
git diff baseline_results.json after_hybrid_results.json
```

### Continuous Integration
```yaml
# .github/workflows/test.yml
name: Quality Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run canary tests
        run: python canary_tests.py
      - name: Check score threshold
        run: |
          score=$(python run_tests.py --output score)
          if [ $score -lt 70 ]; then
            echo "Score $score below threshold!"
            exit 1
          fi
```

---

## Success Metrics

Track these over time:

### Quality Metrics
- **Average Score:** Should trend upward (target: 80+/100)
- **Critical Failure Rate:** Should trend downward (target: <5%)
- **Hallucination Rate:** Should be near zero (target: 0%)
- **Off-Topic Refusal Rate:** Should be 100%

### Performance Metrics
- **Average Response Time:** Should trend downward (target: <5s)
- **Timeout Rate:** Should be zero
- **Cache Hit Rate:** Should trend upward (target: >50%)

### User Satisfaction (if collecting feedback)
- **Thumbs Up Rate:** Target >70%
- **Conversation Length:** Longer = users engaged
- **Repeat Usage:** Users coming back

---

## Sample Weekly Report Format

```
=== TIGERRESEARCHBUDDY WEEKLY REPORT ===
Week of: Nov 1-7, 2024

SUMMARY:
✅ 78/100 avg score (+4 from last week)
✅ 5% critical failures (-3% from last week)
✅ 6.2s avg response time (-0.8s from last week)

TOP WINS:
1. Eliminated all artifact leakage (was 15 queries, now 0)
2. Added conversation memory (follow-ups improved 25%)
3. Improved topic search accuracy (+12 points)

TOP ISSUES REMAINING:
1. Still hallucinating on 3-4 edge case queries
2. Off-topic refusals are inconsistent (8/10 correct)
3. Response times spike for complex multi-faculty queries

ACTIONS FOR NEXT WEEK:
1. Implement confidence threshold to fix hallucinations
2. Strengthen intent classification for off-topic
3. Add caching for multi-faculty queries

DETAILED METRICS:
- Queries tested: 100
- Pass rate: 82% (82/100)
- By category:
  * Faculty lookup: 92% (23/25)
  * Topic search: 78% (19/25)
  * Follow-ups: 85% (17/20)
  * Off-topic: 80% (8/10)
```

---

## Next Steps

1. **Today:** Run the 5-minute smoke test
2. **This Week:** Run full 100-query suite, establish baseline
3. **Next Week:** Fix top 3 issues, re-test
4. **Ongoing:** Daily canary tests + weekly deep analysis

Remember: **Measure → Fix → Measure → Fix**

Don't make improvements blindly. Always baseline, change one thing, and measure improvement.
