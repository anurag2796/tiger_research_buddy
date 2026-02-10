# TigerResearchBuddy: Project Pitch 🐅

## 1. The "Elevator Pitch" (30 Seconds)
**Hook**: "Finding a research mentor at RIT shouldn't be harder than doing the actual research."

**Problem**: Students want to do research but struggle to navigate hundreds of faculty profiles, publications, and lab websites to find a good match.

**Solution**: TigerResearchBuddy is an AI-powered assistant specifically for RIT's Golisano College. Unlike generic ChatGPT, it uses a **Retrieval-Augmented Generation (RAG)** engine built on actual RIT faculty data. Students can ask, *"Who works on computer vision?"* or *"What is Dr. Kanan's email?"* and get instant, accurate, fact-checked answers with contact info.

**Impact**: It bridges the gap between students and faculty, increasing research participation.

---

## 2. The "Professor Pitch" (Technical Focus - 2 Minutes)
*Use this when speaking to a technical audience or your advisor.*

**Concept**:
"I've built a specialized RAG (Retrieval-Augmented Generation) system designed to index and retrieve RIT Golisano research data."

**Technical Architecture**:
1.  **Data Layer**: I scraped/indexed faculty profiles and papers into a **ChromaDB vector store** using high-dimensional embeddings (Sentence-Transformers).
2.  **Intelligence Layer**:
    *   It's not just a wrapper. I built a custom **Intent Classifier** (Faculty Lookup vs. Topic Search vs. Off-topic).
    *   It uses **Dynamic Sentiment & Confidence Thresholds** to prevent hallucinations—if the vector distance is too high (unknown professor), it refuses to guess, ensuring academic integrity.
3.  **Safety & Quality**:
    *   Implemented a Regex-based **Response Post-Processor** to clean clean artifacts.
    *   Includes a **Canary Test Suite** that runs automated regression tests to ensure reliability.

**Current Status**:
"The prototype is live with a Streamlit interface. It successfully handles complex queries like 'Compare the research of Professor X and Y' and correctly refuses off-topic questions to stay focused on RIT research."

---

## 3. Demo Script (If you show the app)

1.  **Show Safety**: Ask *"What is the weather?"*
    *   *Result*: Bot refuses politely (demonstrates Intent Classification).
2.  **Show Knowledge**: Ask *"Who works on Machine Learning?"*
    *   *Result*: Bot lists verified faculty with descriptions (demonstrates Vector Search).
3.  **Show Precision**: Ask *"What is Christopher Kanan's email?"*
    *   *Result*: Bot retrieves specific metadata (demonstrates Context Awareness).
