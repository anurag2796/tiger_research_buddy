# TigerResearchBuddy - Ideas from AI Agents

> 💡 Ideas gathered from Moltbook AI agent community on 2026-02-02
> Registration attempted but hit rate limit (1 agent/day). Will retry tomorrow.

## Ideas from Moltbook Agents

### 1. 🔬 AI Impact Analysis (from osmarks)
**Concept**: Incorporate a feature that analyzes the societal and ethical impact of research papers, specifically looking at how they influence the future of AGI and society.

**Implementation**:
- Add "impact analysis" field to paper indexing
- Use LLM to categorize papers by societal impact areas
- Flag papers with potentially transformative implications

---

### 2. 🔍 Meaning-Based Discovery (from MoltReg)
**Concept**: Enhance the search engine to focus on "semantic discovery" rather than just keyword matching, ensuring students find research related to the *intent* of their queries.

**Implementation**:
- Improve embedding model quality (consider larger models)
- Add query expansion with synonyms
- Implement "related research" suggestions
- Show WHY results are relevant

---

### 3. 📱 Autonomous Social Presence
**Concept**: Enable the buddy to autonomously summarize new RIT research papers and share them on platforms like Moltbook to gather peer feedback from other AI agents.

**Implementation**:
- Register on Moltbook as TigerResearchBuddy agent
- Daily job to post research summaries to m/technology
- Engage with other AI agents for cross-pollination
- Build credibility in AI research community

---

### 4. 🤖 Agent Interaction Interface (from MoltReg)
**Concept**: Create a clean abstraction layer for students to interact with multiple AI models (Llama, Claude, Gemini, etc.) to get different perspectives on a single research topic.

**Implementation**:
- Add model selection to chat interface
- Support Gemini (cloud) and Ollama (local) already ✅
- Consider adding Claude, GPT-4 via API keys
- Compare responses side-by-side
- "Consensus" feature combining multiple viewpoints

---

### 5. 🛡️ Security & Stability Focus
**Concept**: Implement robust rate-controlling and request validation (as discussed in Moltbook incident reports) to ensure the buddy remains stable when crawling academic databases like ArXiv and Semantic Scholar.

**Implementation**:
- ✅ Already have rate limiting in crawlers
- Add circuit breaker for failed API calls
- Graceful degradation when APIs are down
- Health check endpoint
- Auto-retry with exponential backoff

---

## My Own Enhancement Ideas

### 6. 🎓 Personalized Research Roadmaps
Generate personalized "learning paths" based on student interests:
- Input: Student's background, interests, career goals
- Output: Curated sequence of papers, professors, labs

### 7. 📊 Research Trend Analysis
Track and visualize trending research topics at RIT:
- Weekly "hot topics" based on new papers
- Faculty collaboration networks
- Emerging research areas

### 8. 💬 Office Hours Matching
Connect students with faculty based on:
- Research alignment scores
- Faculty availability
- Student preparation level

### 9. 🔔 Research Alerts
Subscribe to personalized research updates:
- New papers in your interest areas
- Faculty talks and seminars
- Research opportunity postings

### 10. 🌐 Cross-University Collaboration
Find similar research happening at other universities:
- Link RIT researchers with potential collaborators
- Compare research programs across institutions

---

## Moltbook Registration TODO

- [ ] Retry agent registration tomorrow (after 24hr cooldown)
- [ ] Post introduction in m/technology
- [ ] Ask for feedback on research discovery features
- [ ] Engage with other education/research AI agents
