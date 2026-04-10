# TigerResearchBuddy Model Audit Report

## 1. MODEL IDENTITY

**Foundation Model and Selection Rationale**
The system is built upon the `qwen2.5:32b` foundation model, as explicitly defined in the first line of the system's Modelfile (`legacy/ollama/Modelfile:1`). The Qwen2.5 32B model is typically selected for local deployments because it offers a highly optimized balance of robust instruction-following capabilities, strong JSON formatting adherence, and advanced reasoning, while still fitting within the memory bounds of high-end consumer hardware (like Apple Silicon) when quantized.

**Model Creation (`tigerbuddy:latest`)**
The custom application model, `tigerbuddy:latest`, is built utilizing the Ollama deployment engine via a bespoke Modelfile (`legacy/ollama/Modelfile`). Because the `FROM` declaration (`legacy/ollama/Modelfile:1`) does not specify a distinct quantization tag, Ollama defaults to pulling the standard `Q4_K_M` (4-bit quantization) variant of the model from its registry. This builds the `tigerbuddy:latest` image by wrapping the quantized weights with the localized configuration parameters and system prompts defined in the file.

**Hardcoded Parameters and Implications**
Two critical LLM generation parameters are permanently baked into the model configuration (`legacy/ollama/Modelfile:4-5`):
- `PARAMETER temperature 0.7`: This statically sets the model's generation temperature to 0.7. For a Retrieval-Augmented Generation (RAG) system focused on factual academic data extraction, 0.7 is dangerously high. It encourages tokenizer deviation and creative extrapolation ("hallucination"), directly increasing the risk that the model might invent faculty members or hallucinate non-existent research papers when factual context is scarce. Note that `src/utils/config.py:127` attempts to define `TEMPERATURE = 0.2`, but this is not consistently mapped down to the `OllamaClient` in standard chat routing.
- `PARAMETER num_ctx 4096`: This enforces a strict, unyielding ingestion ceiling of 4,096 tokens for the model's context window. Any prompt data (system instructions + RAG retrieved documents + user query) that exceeds 4,096 tokens will be forcibly truncated by the Ollama execution engine before generation begins.

---

## 2. HARDWARE PROFILE & CONSTRAINTS

**Host Machine Specifications**
Based on the `system_profiler SPHardwareDataType` execution, the host server running the deployment possesses the following hardware:
- **Architecture**: Apple Silicon (Mac16,6)
- **Chip**: Apple M4 Max
- **Compute Cores**: 14 Total Cores (10 Performance, 4 Efficiency)
- **Memory Subsystem**: 36 GB Unified Memory Architecture (UMA)

**Theoretical System Memory Budget Breakdown**
Apple's Unified Memory Architecture shares the 36 GB pool dynamically between the CPU and the integrated Neural Engine/GPU. When analyzing the TigerResearchBuddy stack without explicit active runtime profiling, the estimated memory budget decomposes roughly as follows:
1. **Host OS & Backend Runtimes**: macOS background processes, the local frontend server (Streamlit or Next.js), and the FastAPI/Uvicorn Python backend combined consume approximately **~3-4 GB** of ambient memory.
2. **Database Overhead**: The localized ChromaDB vector store and the in-memory NetworkX knowledge graph (`tiger_brain.json`) consume an estimated **~1-2 GB** depending on the size of the ingested dataset.
3. **Embedding Model**: The `nomic-embed-text-v1.5` dense retrieval model loaded into CPU/Metal memory requires roughly **~0.5 GB** (`src/utils/config.py:113`).
4. **Primary LLM Footprint**: The `qwen2.5:32b` model, fully expanded in 4-bit (`Q4_K_M`) precision inside the Ollama runtime, requires an estimated **~19.5 GB** just to load the static weights into the Apple GPU memory address space.

**Context Headroom & Bottlenecks**
Summing these theoretical allocations, the stack requires roughly **~24.5 GB** at absolute idle. Out of the total 36 GB, this leaves an estimated **~11.5 GB of flexible headroom**.
- **Theoretical Maximum Context**: For a 32B model, computing the Key-Value (KV) cache matrix for generation consumes memory linearly as the context size grows. With 11.5 GB of free headroom, the Apple M4 Max could theoretically support a context window of roughly **16,000 to 24,000 tokens** safely before utilizing swap memory.
- **What Breaks First**: If the system is pushed beyond its 36 GB physical limit (either via highly concurrent requests or artificially inflated context windows), Apple's `kernel_task` will violently page memory block transfers to the NVMe SSD disk (Swap Memory). When this occurs, LLM generation speeds will collapse immediately from a highly interactive >20 tokens/sec down to completely unusable <1 token/sec. If the Swap pressure causes the GPU to wait too long for tensors, the Ollama server process will crash with a silent Out Of Memory (OOM) interrupt.

---

## 3. HOW THE MODEL IS INVOKED

**Tracing the Code Paths**
The application relies on a localized interface wrapper, `OllamaClient` (`src/chatbot/ollama_client.py:26`), to manage API interactions. The invocation sequence operates entirely synchronously:
1. **The Chat Endpoint**: The frontend calls `POST /api/chat` (`api.py:70`).
2. **Context Retrieval**: The API triggers `retriever.hybrid_search(request.query, k=15)` (`api.py:81`), compiling a block of string text from the database.
3. **Synthesis**: The API passes this text to `synthesizer.synthesize(...)` (`api.py:84`).
4. **Invocation**: Inside the synthesizer (`src/generation/synthesizer.py:86-89`), the engine calls:
   ```python
   response = self.client.generate(prompt=user_prompt, system_prompt=system_prompt)
   ```
5. **Execution**: The `.generate()` method builds an array comprising `{"role": "system", "content": system_prompt}` and `{"role": "user", "content": <context+prompt>}` and passes it to the blocking `ollama.chat()` function (`src/chatbot/ollama_client.py:176-180`).

**Parameter Overrides and State Management**
- `api.py:78` attempts to dynamically switch roles by calling `client.set_persona(request.persona)`.
- However, the `generate()` function in `OllamaClient` contains a critical logic branch (`src/chatbot/ollama_client.py:156`):
  ```python
  if not system_prompt:
      system_prompt = self._load_persona_prompt()
  ```
- Because `synthesizer.py` *always* explicitly injects an enormous local `system_prompt` string payload (`src/generation/synthesizer.py:49-56`), the configured persona states ("tiger", "analyzer", "critique") established by the frontend are completely ignored and overwritten during runtime execution.

---

## 4. THE PERSONA CONFLICT

There is a deep architectural conflict between the base identity compiled into the model's weights and the identities forced upon it by backend endpoints during API routing.

**The Baked-in Foundation**
The `legacy/ollama/Modelfile:8-20` actively forces this identity into the root of the model:
> *SYSTEM """You are TigerResearchBuddy 🐅, the premier AI Research Assistant for the Rochester Institute of Technology (RIT)... Use emojis... Be encouraging..."""*

**The Endpoint Overrides**
When hitting specific endpoints, the python backend appends completely different (and often mutually exclusive) system directives into the same API call:
1. **Standard Synthesis** (`src/generation/synthesizer.py:50`): Instructs the model to act as a "knowledgeable Academic Advisor at RIT's Golisano College", demanding brutal adherence to index citations `[1], [2]`.
2. **Chain of Density Mode** (`src/generation/synthesizer.py:121`): When `use_cod=True` is triggered, the codebase demands: *"You are a JSON-speaking synthesis engine"*, forcing the model to strip away the friendly RIT persona entirely to output strict JSON blocks.
3. **Impact Analyzer Mode** (`src/analysis/impact_analyzer.py:36`): When a student explores an active idea, the endpoint sends: *"You are an impact analyst. Output JSON only."*

[UNDOCUMENTED RUNTIME HYPOTHESIS - requires empirical validation]: When Ollama receives a `messages` array containing a `system` role prompt parameter on a model that *already* contains a baked-in Modelfile `SYSTEM` declaration, its exact merging behavior isn't explicitly defined in this codebase. Static analysis heavily suggests it concatenates or overwrites the two text blocks. If it concatenates, the model is simultaneously being told to be an emoji-loving cheerful tiger AND a strict, data-only JSON parser. This explicit architectural conflict is notoriously responsible for severe formatting hallucinations. You must test `ollama.chat()` manually with tracing enabled to verify exactly how the context block is fed to the tensor execution before relying on this assumption.

---

## 5. CONTEXT WINDOW BUDGET ANALYSIS

**The Token Ceiling**
As established, `legacy/ollama/Modelfile:5` limits the total prompt size to a rigid **4,096 tokens**.

**Realistic Token Distribution per Chat Request**
When a user asks a complex research question, the API formats a payload roughly aligning to this budget:
1. **The Overridden System Prompt**: The massive routing strictures demanded by `synthesizer.py:50-56` combined with the baked system prompt cost roughly **~250 tokens**.
2. **The Retrieval Context**: `api.py:81` rigidly dictates `k=15`, forcing the HybridRetriever to return the top 15 most relevant chunks from the database. A standard Research Card or Faculty profile in the DB (`src/database/vector_store.py:325-338`) spans roughly 200–350 tokens when converted to string syntax. 
   - Calculation: 15 chunks × ~275 tokens = **~4,125 tokens**.
3. **The User Formatting Envelope**: The strict `Task: Write a structured response...` markdown envelope surrounding the query (`src/generation/synthesizer.py:58-82`) costs roughly **~150 tokens**.
4. **The Response Buffer**: To generate a comprehensive, cited, multi-paragraph response without cutting off mid-sentence, the model requires an outbound generation runway of at least **~800 tokens**.

**Total Required Tokens: ~5,325**
**Hardcoded Budget Limit: 4,096**

**Inevitable Truncation Point**:
The system fundamentally requires more tokens just to frame the prompt than the model is legally allowed to ingest. Because the retrieval limit is static (`k=15`), truncation **always occurs on highly populated databases**. The tokenizer will forcibly slice the prompt midway through reading the retrieved VectorStore documents (usually throwing away Results 11 through 15 completely), blinding the LLM to the lower-ranked research citations regardless of their semantic relevance.

---

## 6. KNOWN FAILURE MODES

The system makes multiple brittle assumptions when parsing the natural language output returned by the LLM into software logic. 

**CRITICAL RISK: Impact Analyzer JSON Parsing**
- **Location:** `src/analysis/impact_analyzer.py:38-42`
- **Mechanism:** The code asks the LLM to output an evaluation of a student's idea, expecting a cleanly formatted string matching `{"score": X, "sdgs": [...], "summary": "..."}`. It naively searches for ```json tags using `.split("```json")`. 
- **Failure Condition:** If the LLM hallucinates conversational preamble (e.g., *"Here is the JSON analysis you requested: \n {..."*), forgets the backticks, or drops a closing bracket due to Token Truncation (see Section 5), the `.split()` operation will raise an `IndexError`, or the subsequent `json.loads(json_str)` will raise a `JSONDecodeError`.
- **Silent Failing Outcome:** The module catches this exception silently (`src/analysis/impact_analyzer.py:45-47`) and returns default zeroed metrics (`{"score": 0, "sdgs": []}`). The frontend Collaboration Hub will subsequently render an empty interface for the student without properly notifying them that the backend AI pipeline failed.

**MEDIUM RISK: Chain of Density Parsing**
- **Location:** `src/generation/synthesizer.py:126-139`
- **Mechanism:** Similar brittle JSON slicing logic applied to the deep CoD answer generation.
- **Silent Failing Outcome:** Unlike the Impact Analyzer, this module handles the `JSONDecodeError` slightly more gracefully by defaulting the output to the raw, unparsed string (`final_answer = raw_response`). While it won't crash the UI, it will dump raw, ugly JSON schema notation directly into the student's visual chat window.

**LOW RISK: Topology Graph Failure Masking**
- **Location:** `src/collaboration/matcher.py:220-222`
- **Mechanism:** The `find_collaborators` endpoint executes an expensive PageRank algorithm traversing the NetworkX graph. If `nx.pagerank()` raises an exception, the code catches it, logs it, and returns `{}`.
- **Silent Failing Outcome:** The matcher quietly degrades back to pure cosine-similarity Vector queries. The user gets a result, but the advanced "Topology-Enhanced Collaboration" features are invisibly disabled.

---

## 7. CONCURRENCY & RESOURCE RISKS

The architecture of the FastAPI application relies on a blocking, purely synchronous flow that exposes the deployment to immense hardware risks if deployed in a multi-user classroom environment.

**Architectural Bottleneck**
The system spins up a single global `OllamaClient` instance (`api.py:37`). This instance is simultaneously shared by the `retriever`, `synthesizer`, and `impact_analyzer`. 

**The Simultaneous Hit Scenario**
FastAPI natively uses a thread-pool to handle multiple incoming HTTP requests simultaneously. 
- If Student A submits a question to `/api/chat` and Student B submits an idea to `/api/idea` at the exact same millisecond, FastAPI spins up two worker threads.
- Both threads will immediately invoke `ollama.chat()` concurrently.
- Because `ollama.chat` is a blocking call mapping down to the underlying metal GPU architecture, the Apple M4 Max is suddenly forced to perform dual-inference generation simultaneously across two massive 32B model cache allocations.
- **Outcome:** The GPU memory (`VRAM`) budget instantly skyrockets by computing two separate Key-Value inference caches. Given the 11.5 GB of flexible headroom (Section 2), the system will panic, swapping out to the NVMe disk natively, collapsing generation time to minutes, or flat-out crashing the Ollama daemon.

**Missing Safeguards**
There is **absolutely zero queuing, semaphore locking, or rate limiting** anywhere in `api.py` or `ollama_client.py` to prevent multiple execution threads from hammering the singular inference endpoint concurrently. The realistic maximum concurrent user threshold before catastrophic performance degradation is **exactly 1 active user**.

---

## 8. DEPLOYMENT REALITY

The static code analysis reveals that the architecture is built strictly as a set of disconnected development scripts, rather than a cohesive production-ready system. 

**Fractured Frontends**
The repository contains dual UI implementations:
- A Streamlit interface (`web_app.py`) which acts sequentially and forces Pythonic render-blocking.
- A Node-based interface (`frontend/package.json`) utilizing `next dev` hot-reloading.
Neither of these interfaces natively share connection pools or state with the `api.py` backend efficiently. If deployed, the `web_app.py` Streamlit instance will initiate its own direct connections to ChromaDB and Ollama separately from `api.py`, fracturing the hardware limits even further.

**The FastAPI `startup_event` Trap**
In `api.py:41-59`, the backend immediately initializes the entire suite of retrieval and synthesis classes globally upon startup. 
- **The Threat:** If this backend is ever launched in a live deployment setting using a process manager configured for hot-reloads (e.g., standard `uvicorn --reload` behavior), every single syntax typo or file save will cause the server to restart, abruptly re-loading the giant ChromaDB embedding models and re-initializing the NetworkX graph structures entirely. This will cause catastrophic startup latency and spike background RAM usage aggressively during Active Development.

**Local Host Restrictions**
- **CORS Scope:** The FastAPI application strictly expects the frontend to operate at `http://localhost:3000` (`api.py:28`), prohibiting network-level campus access immediately out of the box.

**Missing Pipeline Locks for Database Mutations**
The `run_pipeline.py` script actively parses, embeds, and mutates the ChromaDB vector database. There are no explicit file-locking mechanisms or concurrency blocks actively protecting the ChromaDB `.sq3` files. If a developer runs `run_pipeline.py --mode crawl` while `api.py` is actively querying the exact same Vector database location, it is highly likely to cause SQLite database lock exceptions or corpus corruption.

**The Frontend Cancellation Trap (`AbortController`)**
The frontend architecture explicitly utilizes an `AbortController` to cancel HTTP requests to the backend if a user navigates away or stops generating a response. 
- **The Threat:** When the React client aborts the fetch call, FastAPI cancels the HTTP TCP connection, but the underlying `client.generate()` (`ollama.chat`) function call executing on the thread pool **is not natively cancellable**. The Apple GPU will continue to burn compute and hold the 19.5 GB VRAM hostage until the `qwen2.5` model finishes generating the entire aborted response silently in the background. If a user spam-clicks "Cancel" and "Regenerate", they will silently stack multiple unstoppable GPU inference jobs in the background, instantaneously causing the hardware crash detailed in Section 7.

---

## 9. RECOMMENDATIONS & SEQUENCING ACTION PLAN

Below is the definitive action plan for stabilizing the TigerResearchBuddy architecture, ranked by severity and explicitly sequenced for deployment. 

| Sequence | Component | Current Behavior | Recommended Technical Action | Owner / Effort |
|:---|:---|:---|:---|:---|
| **Step 1** | Global Sync Concurrency Panics | FastAPI workers invoke parallel, unqueued blocks of `ollama.chat`, bringing VRAM to panic under simultaneous demands. | Import `asyncio.Lock` or a strict `asyncio.Semaphore(1)` constraint wrapping every invocation of `.generate()`. This forces API requests into a first-in-first-out line, capping GPU use at 1 inference per tick. | Platform Eng. (Medium) |
| **Step 2** | Context Window Default Limits | Model is artificially capped at a maximum ingestion size of `4096` tokens, guaranteeing retrieval data loss during long reads. | Delete `PARAMETER num_ctx 4096` from the Modelfile. Pass `options={"num_ctx": 16384}` directly via the Python runtime kwargs. | AI/ML Eng. (Low) |
| **Step 3** | Top-K Truncation Spacing | Top-K `k=15` guarantees an oversaturated context, bleeding out recent chunks due to standard LLM attention degradation. | *Dependent on Step 2*. Once context is raised, reduce vector retrieval depth limit `k` map bounds to 5-8 chunks to fit the new context bounds safely. | AI/ML Eng. (Low) |
| **Step 4** | Ignored Configuration Overrides | `src/utils/config.py:127` dictates `TEMPERATURE = 0.2`, but it is never passed to `OllamaClient`, letting the Modelfile default to an overly-creative `0.7` hallucination hazard. | Explicitly map backend `config.LLMConfig` parameters directly into the `options` dict inside `OllamaClient.generate()`. | Backend Eng. (Low) |
| **Step 5** | Impact Analyzer Payload Crash | Returns zeroed, silent dictionary schemas when `.split()` fails upon unexpected LLM token formatting, breaking UI renders. | Abandon manual `.split()` regex hacking. Utilize explicitly typed `Pydantic` schemas attached to standard `json.loads` extraction with retry logic. | Frontend Eng. (Low) |
| **Step 6** | Orphaned Background Inferences | When the frontend cancels an HTTP request, the FastAPI thread silently abandons the `ollama.chat` call, leaking VRAM in the background until it finishes. | Transition the standard `ollama.chat` blocking call to the async Ollama Streaming API wrapper. Bind the stream generator to a FastAPI `Cancellation Token`, allowing graceful closure of the specific inference stream without sending a nuclear `SIGINT` to the daemon (which would kill all active users). | Platform Eng. (High) |

---

### Executive Summary

The TigerResearchBuddy prototype effectively demonstrates deep Vector retrieval and semantic Graph logic operating entirely locally on Apple Silicon. However, statically auditing the core Python infrastructure reveals it is fundamentally unready for multi-user academic deployments without immediate architectural stabilization.

**Critical System Risks Identified:**
- **Context Suffocation:** The AI is instructed to read 15 dense research documents simultaneously, yet its internal memory buffer is rigidly bounded at exactly 4,096 tokens. The system is mathematically forced to suffer LLM attention decay and instantly "forget" lower-ranked research during every query.
- **Concurrency & VRAM Hostages:** The backend lacks queuing. If two students submit a query at the exact same millisecond, the Apple hardware will attempt to process twin 19.5GB mega-calculations simultaneously, resulting in a VRAM crash. Worse, the current architecture ignores frontend cancellation intents (`AbortControllers`); if a user hits "Cancel", the backend will blindly continue consuming full GPU loads in the background until completion, enabling trivial denial-of-service vulnerabilities.
- **Deployment & Locking Traps:** The codebase is critically fractured across dual UIs, relies entirely on aggressive hot-reload configurations that repeatedly dump giant vector databases into memory upon minor syntax saves, and lacks the basic file-level thread locking required to safely mutate the ChromaDB sqlite indexes during active reads.

Upgrading the LLM's context token limits, migrating the monolithic `OllamaClient` onto async Streaming execution blocks bound to cancellation tokens, and consolidating the frontend deployment paradigm are absolute prerequisites before the platform can safely exit the isolated backend development phase.
