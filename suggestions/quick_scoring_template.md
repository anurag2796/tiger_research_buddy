# Quick Response Scoring Template
## Use this for rapid evaluation of each response

---

## Test Case Information
**Query:** _______________________________________
**Query Type:** [ ] Faculty Lookup  [ ] Topic Search  [ ] Follow-up  [ ] Off-topic
**Expected Response:** _______________________________________
**Actual Response Time:** _______ seconds

---

## Critical Checks (Must ALL Pass - Auto-Fail if Any Fail)

| Check | Pass? | Notes |
|-------|-------|-------|
| No "Result 1:" or similar artifacts | ☐ | |
| No hallucinated faculty/info | ☐ | |
| Response time < 30s | ☐ | |
| On-topic if query is on-topic | ☐ | |
| No fabricated contact info | ☐ | |

**CRITICAL FAILURE?** [ ] YES (Stop here) [ ] NO (Continue)

---

## Quality Assessment (Score Each 0-10)

### Accuracy & Relevance (40 points max)
| Criterion | Score (0-10) | Weight | Total |
|-----------|--------------|--------|-------|
| Factual accuracy of information | __/10 | x2 | __/20 |
| Relevance to actual query | __/10 | x2 | __/20 |

### Formatting & Presentation (20 points max)
| Criterion | Score (0-10) | Weight | Total |
|-----------|--------------|--------|-------|
| Clean markdown formatting | __/10 | x1 | __/10 |
| Appropriate length (150-200 words) | __/10 | x1 | __/10 |

### User Experience (20 points max)
| Criterion | Score (0-10) | Weight | Total |
|-----------|--------------|--------|-------|
| Actionability (clear next steps) | __/10 | x1 | __/10 |
| Tone & professionalism | __/10 | x1 | __/10 |

### Technical Performance (20 points max)
| Criterion | Score (0-10) | Weight | Total |
|-----------|--------------|--------|-------|
| Response speed (<10s = 10, <20s = 5) | __/10 | x1 | __/10 |
| Retrieval quality (right chunks) | __/10 | x1 | __/10 |

---

## Overall Score Calculation

**Total Points:** _____ / 100

**Grade:**
- 90-100: Excellent ✅
- 70-89: Good 👍
- 50-69: Needs Improvement ⚠️
- <50: Failing ❌

---

## Specific Issues Found

### Formatting Issues:
- [ ] Contains internal artifacts
- [ ] Wall of text (no paragraphs)
- [ ] Too long (>200 words)
- [ ] Too short (<50 words)
- [ ] Missing contact info formatting
- [ ] No markdown emphasis

### Content Issues:
- [ ] Wrong faculty mentioned
- [ ] Missing key information
- [ ] Irrelevant information included
- [ ] Doesn't answer the question
- [ ] Too vague/generic
- [ ] Overconfident about uncertain info

### Technical Issues:
- [ ] Slow response (>10s)
- [ ] Retrieved wrong chunks
- [ ] Should have used different search method
- [ ] No conversation context
- [ ] Timeout occurred

### UX Issues:
- [ ] No clear next steps
- [ ] Tone inappropriate
- [ ] Doesn't say "I don't know" when should
- [ ] No sources/citations
- [ ] Confusing or unclear

---

## Improvement Notes

**What should have happened:**


**Root cause of issues:**


**Suggested fix:**


---

## Comparison to Previous Version (if A/B testing)

| Metric | Old System | New System | Improvement |
|--------|-----------|------------|-------------|
| Response Time | | | |
| Accuracy Score | | | |
| Format Quality | | | |
| Overall Score | | | |

---

## Follow-up Actions

- [ ] Log this query for re-testing
- [ ] Add to regression test suite
- [ ] Update prompt engineering
- [ ] Improve retrieval strategy
- [ ] Add to manual Q&A training
- [ ] Report bug/issue

---

## Question Type Specific Checks

### For Faculty Lookup Queries:
- [ ] Faculty name correct
- [ ] Email included (if asked)
- [ ] Office location included
- [ ] Research areas mentioned
- [ ] Recent papers (if relevant)

### For Topic Search Queries:
- [ ] Multiple relevant faculty listed
- [ ] Research descriptions accurate
- [ ] Expertise levels indicated
- [ ] Contact info for top matches
- [ ] Breadth vs. depth appropriate

### For Follow-up Queries:
- [ ] Understood context from previous query
- [ ] Resolved pronouns correctly
- [ ] Didn't repeat previous info unnecessarily
- [ ] Built on previous conversation

### For Off-topic Queries:
- [ ] Politely declined to answer
- [ ] Explained scope limitations
- [ ] Suggested alternative topics
- [ ] Didn't attempt to force RIT data

---

## Red Flags Checklist (If Any True, Investigate Immediately)

- [ ] Response contains "Error:" or stack trace
- [ ] Faculty from different university mentioned
- [ ] Invented statistics or numbers
- [ ] Plagiarized text from source docs
- [ ] Offensive or inappropriate language
- [ ] Contradicts itself within response
- [ ] Mentions GPT/Claude/AI in response
- [ ] Shows system prompts or instructions
