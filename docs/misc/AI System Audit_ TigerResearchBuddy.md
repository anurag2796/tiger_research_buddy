# **Architectural and Security Audit of TigerResearchBuddy: Systemic Vulnerabilities in Local-First Hybrid RAG Pipelines**

The integration of local-first Large Language Models (LLMs) with Retrieval-Augmented Generation (RAG) pipelines presents profound architectural challenges, particularly concerning memory management, asynchronous execution, and distributed state synchronization. The TigerResearchBuddy architecture, designed to operate within the strict hardware constraints of Apple Silicon (Unified Memory Architecture) while simultaneously serving a multi-node knowledge graph, exhibits several critical anti-patterns. The system relies on a complex "Two-Lobe Brain" architecture combining a vector search database (ChromaDB) with a structural knowledge graph (NetworkX), orchestrated by a FastAPI backend and a Streamlit frontend.

This exhaustive audit evaluates the system across four primary vectors as requested: Concurrency and Asynchronous/Synchronous Mismatches, AI/LLM Token and Prompt Topologies, Data State and Thread Contention, and Brittle Lexical Parsing. The analysis identifies profound architectural shortcomings that will trigger catastrophic failures in production, including Out-Of-Memory (OOM) hardware panics, silent context truncation, thread deadlocks, and persistent state corruption during concurrent access.

## **1\. Concurrency & Async/Sync Mismatches**

The deployment of FastAPI as the Asynchronous Server Gateway Interface (ASGI) mandates strict adherence to non-blocking execution patterns. The fundamental advantage of ASGI is its ability to multiplex thousands of concurrent input/output operations over a single event loop thread. However, when heavy, blocking I/O operations or GPU-bound inference calls are introduced directly into this main event loop without proper delegation, the entire server architecture collapses. In the TigerResearchBuddy stack, the boundary between the ASGI event loop and synchronous LLM/database clients is severely compromised, leading to inevitable thread starvation and hardware resource exhaustion.

The application exposes a /api/chat endpoint defined via the async def keyword, which instructs the Uvicorn worker to execute the routine directly on the primary asyncio event loop. Within this asynchronous context, the code invokes a cascade of deeply synchronous, blocking functions. The most severe offenders are the LLM generation clients. The OllamaClient.generate method utilizes the standard, synchronous ollama.chat() function to communicate with the local daemon. Similarly, the fallback GeminiClient.generate method relies on the synchronous model.generate\_content() call from the google.generativeai SDK. When the ASGI event loop encounters these blocking calls, it cannot yield execution context to other incoming HTTP requests. A single LLM generation taking 15 to 45 seconds to stream its output completely paralyzes the backend for all other users, directly violating the concurrent design principles of the FastAPI framework.

Severity: Critical

The Vulnerability: Event Loop Starvation via Synchronous LLM Client Invocations

The FastAPI threading model is completely neutralized by synchronous calls to ollama.chat() and genai.GenerativeModel.generate\_content() inside asynchronous routes. Because api.py does not utilize starlette.concurrency.run\_in\_threadpool for these specific client calls, the main thread hangs. At scale, if ten users connect to the laboratory server, the first user's query will lock the event loop, causing the subsequent nine connections to timeout at the reverse proxy layer before their requests are even parsed. Furthermore, the HybridRetriever executes synchronous SQLite disk reads (via ChromaDB) and synchronous CPU/Metal embedding generations (via sentence-transformers) directly on the event loop, compounding the blocking behavior.

Code Location: src/chatbot/ollama\_client.py (generate method), src/chatbot/gemini\_client.py (generate method), and api.py (@app.post("/api/chat") routing).

The Fix:

Synchronous heavy-compute and I/O-bound routines must be explicitly relegated to the application's thread pool or transitioned entirely to their asynchronous equivalents.

Python

\# src/chatbot/gemini\_client.py  
import asyncio  
from typing import Optional  
from fastapi.concurrency import run\_in\_threadpool

class GeminiClient:  
    async def generate\_async(  
        self,   
        prompt: str,   
        context: Optional\[str\] \= None,  
        system\_prompt: Optional\[str\] \= None  
    ) \-\> str:  
        """Asynchronous wrapper for blocking Gemini API calls."""  
        if not self.\_initialized:  
            await run\_in\_threadpool(self.initialize)  
          
        full\_prompt \= ""  
        if system\_prompt:  
            full\_prompt \+= f"{system\_prompt}\\n\\n"  
        if context:  
            full\_prompt \+= f"Context:\\n{context}\\n\\n"  
        full\_prompt \+= f"User Query: {prompt}"  
          
        try:  
            \# Offload the blocking HTTP request to the threadpool  
            response \= await run\_in\_threadpool(self.model.generate\_content, full\_prompt)  
            return response.text  
        except Exception as e:  
            return f"Sorry, I encountered an error: {str(e)}"

Python

\# api.py  
from fastapi.concurrency import run\_in\_threadpool  
import filelock

@app.post("/api/chat", response\_model=ChatResponse)  
async def handle\_chat(request: ChatRequest):  
    if not retriever or not synthesizer or not client:  
        raise HTTPException(status\_code=500, detail="Backend services offline.")  
          
    try:  
        client.set\_persona(request.persona)  
        session\_id \= request.session\_id or str(uuid.uuid4())  
        history \= memory.get\_context\_window(session\_id) if memory else

        \# Offload synchronous retrieval (ChromaDB \+ NetworkX) to the threadpool  
        def safe\_hybrid\_search(query, k):  
            lock\_path \= DATA\_DIR / ".pipeline.lock"  
            with filelock.FileLock(lock\_path, timeout=0):  
                return retriever.hybrid\_search(query, k=k)

        try:  
            results \= await run\_in\_threadpool(safe\_hybrid\_search, request.query, 7)  
        except filelock.Timeout:  
            raise HTTPException(status\_code=503, detail="Database locked.")

        \# Ensure the synthesizer utilizes the truly asynchronous methods  
        final\_answer \= await synthesizer.synthesize\_async(  
            request.query, results, use\_cod=request.use\_cod, history=history  
        )  
        \#... remainder of response handling

Compounding the event loop starvation is a severe hardware limitation regarding Video Random Access Memory (VRAM) management. The platform targets Apple Silicon hardware, specifically the M4 Max architecture featuring 36 GB of Unified Memory. Apple's Unified Memory Architecture (UMA) dynamically allocates the host's memory pool between the Central Processing Unit (CPU) and the integrated graphics cores. The target LLM, Qwen 2.5 32B, requires approximately 19.5 GB of memory just to load its static weights into the Apple GPU address space at 4-bit (Q4\_K\_M) quantization.

| Component Allocation | Estimated Memory Footprint | Description |
| :---- | :---- | :---- |
| macOS & Backend Runtimes | \~3.5 GB | Operating system overhead, Uvicorn, and Next.js/Streamlit servers. |
| Database & Graph In-Memory | \~1.5 GB | ChromaDB indexes and NetworkX tiger\_brain.json structures. |
| Dense Embedding Model | \~0.5 GB | nomic-embed-text-v1.5 executing on CPU/MPS. |
| Qwen 2.5 32B Weights | \~19.5 GB | Static LLM weights loaded into GPU addressing. |
| **Total Baseline Allocation** | **\~25.0 GB** | Minimum required memory at idle. |
| **Available Headroom** | **\~11.0 GB** | Remaining memory for KV caching and active inference. |

During inference, generating the Key-Value (KV) cache for an 8,000-token context window requires linear memory scaling. If two independent users submit a query to the /api/chat endpoint at the exact same millisecond, FastAPI processes both requests concurrently. The lack of a global, application-level queuing mechanism allows both worker threads to invoke ollama.chat() (or its async equivalent) simultaneously. The Apple hardware is instantaneously instructed to generate twin KV caches for a 19.5 GB model, pushing the instantaneous memory demand well over 39 GB. This physically exceeds the 36 GB limit of the hardware. The macOS kernel (kernel\_task) will violently thrash page memory to the NVMe SSD (Swap Memory), collapsing generation speed to less than 1 token per second, and ultimately leading to an Out-Of-Memory (OOM) daemon crash. Furthermore, the frontend utilizes an AbortController to cancel HTTP requests if a user navigates away. However, because the underlying ollama.chat call is a synchronous thread pool execution, the FastAPI cancellation does not propagate to the GPU. The hardware continues burning compute and holding the VRAM hostage for an aborted connection.

Severity: Critical

The Vulnerability: Unbounded VRAM Allocation and Hardware Panics

The absence of a global, centralized queuing mechanism allows unbounded concurrent requests to hit the local Ollama daemon. The FastAPI threading model permits parallel execution, which instantly overwhelms the 11 GB of available UMA headroom when multiple users request inference on a 32B parameter model. Concurrent KV cache generation triggers catastrophic NVMe swap thrashing and silent GPU crashes. Additionally, aborted frontend connections leak VRAM because the synchronous thread execution cannot be interrupted.

Code Location: src/chatbot/ollama\_client.py (Missing global queue logic) and api.py (Endpoint concurrency without rate limits).

The Fix:

A strict, singleton-bound asynchronous semaphore must wrap the LLM client to enforce a First-In-First-Out (FIFO) queue for inference processing, ensuring VRAM is never double-allocated. Furthermore, the synchronous calls must be replaced with the AsyncClient streaming API bound to a FastAPI request.is\_disconnected() cancellation token.

Python

\# src/chatbot/ollama\_client.py  
import asyncio  
from typing import Optional, AsyncGenerator  
from fastapi import Request  
from..utils.hardware import HW\_PROFILE

class OllamaClient:  
    \# Class-level primitive ensures all instances share the exact same lock  
    \_global\_inference\_lock: Optional \= None

    def \_\_init\_\_(self, model: str \= "tigerbuddy", persona: str \= "tiger"):  
        self.model \= model  
        self.persona \= persona  
        self.\_initialized \= False

    @classmethod  
    def get\_lock(cls) \-\> asyncio.Semaphore:  
        """Thread-safe and event-loop-safe global lock retrieval."""  
        if cls.\_global\_inference\_lock is None:  
            \# HW\_PROFILE.chat\_concurrency must be exactly 1 for 32B models on 36GB RAM  
            limit \= HW\_PROFILE.chat\_concurrency   
            cls.\_global\_inference\_lock \= asyncio.Semaphore(limit)  
        return cls.\_global\_inference\_lock

    async def generate\_stream\_async(  
        self,   
        prompt: str,   
        request: Request,  
        context: Optional\[str\] \= None,   
        \*\*kwargs  
    ) \-\> AsyncGenerator\[str, None\]:  
        """Streaming generation with VRAM locking and client disconnect detection."""  
        messages \= self.\_build\_messages(prompt, context, kwargs.get('system\_prompt'))  
        lock \= self.get\_lock()  
          
        \# Strictly bound GPU access to the semaphore limit  
        async with lock:  
            from ollama import AsyncClient  
            client \= AsyncClient()  
              
            stream \= await client.chat(  
                model=self.model,  
                messages=messages,  
                stream=True,  
                \*\*kwargs.get("options", {})  
            )  
              
            async for chunk in stream:  
                \# Poll the ASGI interface to see if the user closed their browser  
                if await request.is\_disconnected():  
                    print("Client disconnected. Aborting inference to free VRAM.")  
                    \# Break the generator, closing the stream and freeing Ollama compute  
                    break   
                  
                yield chunk\['message'\]\['content'\]

## **2\. AI/LLM Anti-Patterns**

The efficacy of a Retrieval-Augmented Generation framework is contingent entirely upon the language model's capacity to ingest dense retrieved chunks and reliably follow formatting instructions without diverging into hallucination. Within the TigerResearchBuddy architecture, severe misconfigurations concerning token window mathematics and prompt injection dynamics cripple the model's reliability, resulting in silent data truncation and severe behavioral drift.

The foundational application model, tigerbuddy:latest, is compiled utilizing a bespoke Modelfile. Within this configuration, the architecture permanently bakes in two critical parameters: PARAMETER temperature 0.7 and PARAMETER num\_ctx 4096\. The temperature setting of 0.7 introduces excessive stochasticity for an academic RAG system, directly increasing the probability that the model will invent faculty members or hallucinate non-existent research papers when factual context is scarce. More egregiously, the num\_ctx 4096 directive enforces an unyielding ingestion ceiling of 4,096 tokens at the execution layer. Any prompt data—comprising system instructions, retrieved documents, and the user query—that exceeds this threshold will be forcibly and silently truncated by the inference engine before generation begins.

The retrieval parameters defined in the application logic are mathematically incompatible with this ceiling. The HybridRetriever is frequently invoked with a top-k limit of 15 chunks (k=15). A standard TigerCard or faculty profile stored in the ChromaDB instance spans approximately 200 to 350 tokens when serialized to string syntax.

| Prompt Component | Estimated Token Cost | Description |
| :---- | :---- | :---- |
| Overridden System Prompt | \~250 tokens | Routing strictures from synthesizer.py combined with baked prompts. |
| Retrieval Context (k=15) | \~4,125 tokens | 15 chunks averaging 275 tokens each. |
| User Formatting Envelope | \~150 tokens | Markdown framing surrounding the user's specific query. |
| Required Generation Buffer | \~800 tokens | Outbound runway required to complete a multi-paragraph response. |
| **Total Required Envelope** | **\~5,325 tokens** | The minimum token space required for successful execution. |
| **Hardcoded Budget Limit** | **4,096 tokens** | The artificial ceiling defined in legacy/ollama/Modelfile:5. |

Because the required envelope outstrips the budget limit by over 1,200 tokens, catastrophic truncation is a mathematical guarantee on highly populated databases. The tokenizer forcibly slices the prompt midway through processing the vector store documents, throwing away Results 11 through 15 completely. The language model is physically blinded to the lower-ranked research citations, regardless of their semantic relevance. The RAG engine effectively deceives the user, operating under the assumption that all 15 documents were weighed, when the LLM's attention matrix was never exposed to them.

Severity: High

The Vulnerability: Catastrophic Context Truncation and Token Math Invalidity

The hardcoded context window in the Modelfile is significantly smaller than the prompt payload generated by the synthesizer. Because the retrieval limit is static, the tail end of the retrieved documents is silently truncated before inference. Furthermore, the src/utils/config.py attempts to set a safer TEMPERATURE \= 0.2, but this variable is never explicitly mapped down to the OllamaClient, leaving the model to run at the highly stochastic default of 0.7.

Code Location: legacy/ollama/Modelfile (Lines 4-5) and src/chatbot/ollama\_client.py (Kwargs unpacking logic).

The Fix:

The static boundary must be removed from the compiled image entirely, allowing the context window to be dynamically allocated at runtime. The backend configuration parameters must be explicitly mapped into the generation payload to ensure factual determinism.

Dockerfile

\# legacy/ollama/Modelfile  
FROM qwen2.5:32b  
SYSTEM """  
You are TigerResearchBuddy, an AI Research Advisor...  
"""  
\# REMOVED: PARAMETER temperature 0.7 (Allow runtime injection)  
\# REMOVED: PARAMETER num\_ctx 4096 (Allow dynamic runtime allocation)

Python

\# src/chatbot/ollama\_client.py  
from..utils.hardware import HW\_PROFILE  
from..utils.config import LLMConfig

async def generate\_async(self, prompt: str, \*\*kwargs) \-\> str:  
    options \= kwargs.get("options", {})  
      
    \# Dynamically inject the hardware-profiled context window (e.g., 16384 on M4 Max)  
    \# This prevents the silent truncation of k=15 retrieval payloads.  
    if "num\_ctx" not in options:  
        options\["num\_ctx"\] \= HW\_PROFILE.context\_window  
          
    \# Enforce strict determinism to prevent academic hallucination,  
    \# ensuring the model respects the config rather than the Modelfile default.  
    if "temperature" not in options:  
        options\["temperature"\] \= LLMConfig.TEMPERATURE

    kwargs\["options"\] \= options  
    \#... proceed with generation

Compounding the token overflow is a profound vulnerability regarding dynamic prompt injection and persona manipulation. The application allows users to select an AI persona (Tiger, Analyzer, Critique) via the Streamlit frontend, which alters the base system instructions. However, the response generation workflow inside src/generation/synthesizer.py initiates a destructive prompt injection sequence. The synthesizer manually constructs an enormous string payload: system\_prompt \= f"{base\_persona}\\n\\nTASK INSTRUCTIONS:\\n...". When this custom string is passed to OllamaClient.generate(), the internal routing logic dictates: if not system\_prompt: system\_prompt \= self.\_load\_persona\_prompt(). Because the synthesizer explicitly provides the payload, the client's internal, clean persona resolution is bypassed entirely.

Furthermore, the foundation model already possesses a SYSTEM instruction hardcoded within the Modelfile. When the Ollama engine receives an API call containing an overriding system role parameter via the REST API, the platform's exact merging behavior causes conflicting directives. The model is simultaneously instructed to act as a cheerful, emoji-using tiger via the baked weights, and as a strict, data-only academic analyst via the synthesizer's dynamic payload. This architectural dissonance directly destabilizes the output tokenizer. It forces the model into an ambiguous state where it attempts to satisfy both the instruction to "be friendly and conversational" and the instruction to "output strictly a markdown table." This conflict is the primary catalyst for the generation of internal artifacts (e.g., outputting "Result 1:..." or "Context:") leaking into the student-facing user interface.

Severity: High

The Vulnerability: Dynamic Prompt Injection and Persona Overwrite

By compiling a SYSTEM prompt into the Modelfile while simultaneously injecting massive, conflicting task directives into the API's system role, the tokenizer is subjected to attention matrix pollution. The model suffers from identity conflict, leading to severe formatting hallucinations and artifact leakage that the post-processor struggles to clean.

Code Location: src/generation/synthesizer.py (Lines 49-56).

The Fix:

Prompt engineering must be strictly layered. The Modelfile should define the overarching baseline identity. The system\_prompt passed via the API must be reserved strictly for the selected persona (Tone/Voice). RAG constraints, grounding rules, and task instructions must be injected safely into the user role boundary, where the LLM expects contextual variations.

Python

\# src/generation/synthesizer.py  
async def synthesize\_async(self, query: str, results: List, history: Optional\] \= None) \-\> str:  
    context\_str, sources \= self.\_format\_context(results)  
      
    \# Retrieve the pure persona string (Tone/Voice) without appending task logic  
    persona\_system\_prompt \= self.client.\_load\_persona\_prompt()  
      
    \# Move strict task instructions and RAG constraints into the USER prompt boundary.  
    \# This prevents the system role from becoming polluted with conflicting directives.  
    user\_prompt \= f"""  
\<context\_database\>  
{context\_str}  
\</context\_database\>

CRITICAL INSTRUCTIONS:  
Your goal is to connect students with faculty. You must cite your sources using square brackets (e.g., ). If the context does not contain the answer, output exactly: "I could not find relevant information." Do not hallucinate.

User Query: "{query}"  
Response:"""

    try:  
        \# The system role is preserved purely for the selected persona  
        response \= await self.client.generate\_async(  
            prompt=user\_prompt,  
            system\_prompt=persona\_system\_prompt   
        )  
        return self.\_format\_output(response, sources)  
    except Exception as e:  
        return "System error during synthesis."

## **3\. Data & State Race Conditions**

The Python runtime environment is governed by the Global Interpreter Lock (GIL), which prevents multiple native threads from executing Python bytecodes simultaneously. While the GIL protects basic interpreter state, it explicitly yields execution context during I/O operations, such as network requests or disk reads. In a FastAPI ecosystem processing concurrent API requests across a thread pool, this yielding behavior surfaces highly destructive race conditions when managing singletons and in-memory data structures. The TigerResearchBuddy architecture contains several critical state management flaws that will corrupt data at scale.

The most prominent vulnerability involves the vector database instantiation. The application accesses the ChromaDB vector database via a global singleton pattern :

Python

\_vector\_store: Optional \= None  
def get\_vector\_store() \-\> VectorStore:  
    global \_vector\_store  
    if \_vector\_store is None:  
        \_vector\_store \= VectorStore()  
    return \_vector\_store

FastAPI routes non-async requests and background processing through a thread pool. If Thread A requests get\_vector\_store(), it evaluates the condition if \_vector\_store is None: as True. Thread A then begins initializing the VectorStore() class. This initialization process requires reading SQLite index files from the persistent disk path at data/chroma/. As Thread A encounters this I/O-bound disk read, the Python GIL yields execution to Thread B.

Thread B, processing a parallel user request, also calls get\_vector\_store(). Because Thread A has not yet completed the instantiation and has not yet assigned the initialized object to the global \_vector\_store variable, Thread B also evaluates the condition as True. Thread B proceeds to initialize a secondary, overlapping instance of the database over the exact same directory. This duplicate instantiation attempts to acquire parallel write locks on the underlying persistent SQLite backend. This race condition triggers a sqlite3.OperationalError: database is locked exception, instantly crashing the retrieval layer for all active users and potentially corrupting the vector embeddings.

Severity: High

The Vulnerability: Vector Database Singleton Thread Contention

The global singleton pattern used for the VectorStore lacks thread synchronization. Concurrent access during application startup or cold-cache retrieval causes multiple threads to instantiate the ChromaDB client simultaneously over the same persistent disk directory. This circumvents SQLite's file-locking mechanisms and crashes the database driver.

Code Location: src/database/vector\_store.py (Singleton instantiation logic).

The Fix:

Standard double-checked locking utilizing the threading library is required to ensure atomic instantiation of the database client across the ASGI thread pool.

Python

\# src/database/vector\_store.py  
import threading  
from typing import Optional

\_vector\_store: Optional \= None  
\_vector\_store\_lock \= threading.Lock()

def get\_vector\_store() \-\> 'VectorStore':  
    global \_vector\_store  
      
    \# First check (unlocked) allows fast access for subsequent calls  
    if \_vector\_store is None:  
        \# Acquire lock to prevent race condition during I/O yield  
        with \_vector\_store\_lock:  
            \# Second check (locked) ensures a yielding thread didn't already instantiate it  
            if \_vector\_store is None:  
                \_vector\_store \= VectorStore()  
                \# Initialize connections safely within the lock boundary  
                \_vector\_store.initialize()  
                  
    return \_vector\_store

A parallel race condition exists within the initialization of asynchronous concurrency primitives. In src/chatbot/ollama\_client.py, the generate\_async method attempts to lazily instantiate an asyncio.Semaphore to throttle API requests.

Python

if self.\_async\_lock is None:  
    limit \= HW\_PROFILE.chat\_concurrency  
    self.\_async\_lock \= asyncio.Semaphore(limit)

In modern Python asyncio implementations (Python 3.10+), concurrency primitives such as Semaphores, Locks, and Events are tightly bound to the specific running event loop in which they are created. If this lazy instantiation occurs inside a background thread, or prior to the proper initiation of the ASGI event loop (for instance, during module import or Uvicorn's pre-fork worker phase), the Semaphore will attach to a dead or incorrect loop.

When the actual asynchronous endpoint attempts to acquire the lock during a user query (async with self.\_async\_lock:), the interpreter will violently reject the operation, raising a RuntimeError: Task attached to a different loop. This failure completely disables the asynchronous capabilities of the LLM client, resulting in persistent 500 Internal Server Errors for all chat functionalities.

Severity: Medium

The Vulnerability: Asynchronous Semaphore Initialization Failures

Lazily instantiating asyncio primitives outside of the active execution scope guarantees loop-attachment errors in multi-worker ASGI frameworks. The OllamaClient will crash attempting to acquire a lock bound to the initialization thread rather than the request-handling thread.

Code Location: src/chatbot/ollama\_client.py (Line 124).

The Fix:

Asynchronous primitives must never be lazily instantiated in a global context. They must be explicitly created during the FastAPI lifespan context manager, guaranteeing that they are inextricably bound to the active Uvicorn worker's event loop.

Python

\# api.py  
from contextlib import asynccontextmanager

@asynccontextmanager  
async def lifespan(app: FastAPI):  
    print(" Initializing services...")  
    global client  
    client \= get\_ollama\_client()  
      
    \# Explicitly invoke a setup method that builds the asyncio.Semaphore  
    \# within the context of the active, running event loop.  
    client.setup\_async\_primitives()  
    yield  
    \# Cleanup logic

\# src/chatbot/ollama\_client.py  
import asyncio

class OllamaClient:  
    def setup\_async\_primitives(self):  
        """Must be called inside the running event loop (e.g., FastAPI lifespan)"""  
        limit \= HW\_PROFILE.chat\_concurrency  
        self.\_async\_lock \= asyncio.Semaphore(limit)  
          
    async def generate\_async(self, prompt: str, \*\*kwargs) \-\> str:  
        if self.\_async\_lock is None:  
            raise RuntimeError("Async primitives not initialized in lifespan.")  
              
        async with self.\_async\_lock:  
            \#... proceed with generation

Beyond standard database and thread locking, the architecture heavily relies on an in-memory NetworkX knowledge graph stored at data/tiger\_brain.json. The GraphEnhancedQueryEngine loads this structural data into an active nx.Graph object for ego-graph traversals and centrality scoring during dual\_level\_search. However, the system also features a run\_pipeline.py script that actively parses, embeds, and mutates the dataset. The backend entirely lacks an application-level ReadWriteLock for this shared memory object. If a developer or a scheduled background task triggers the GraphBuilder.export() method to update the graph while the FastAPI backend is actively traversing it, the underlying Python dictionary representing the node links will be mutated during iteration. This concurrent modification will throw a RuntimeError: dictionary changed size during iteration, killing active semantic queries and requiring a complete reboot of the web server to flush the corrupted memory state.

Severity: High

The Vulnerability: NetworkX Knowledge Graph Mutation Deadlocks

The in-memory nx.Graph instance is read by the FastAPI application but can be overwritten by external pipeline runs. Because there is no inter-process communication or shared lock managing the tiger\_brain.json state, concurrent reads and writes will corrupt the graph topology in memory.

Code Location: src/chatbot/query\_engine.py (\_load\_networkx\_graph method).

The Fix:

Implement a global file-lock utilizing the filelock library whenever the graph is loaded into memory or exported, ensuring atomic updates. Furthermore, the QueryEngine must implement a TTL (Time-To-Live) cache invalidation to reload the graph cleanly if the underlying file changes.

Python

\# src/chatbot/query\_engine.py  
import filelock  
import os  
from..utils.config import DATA\_DIR

class GraphEnhancedQueryEngine:  
    def \_\_init\_\_(self):  
        self.\_nx\_graph \= None  
        self.\_graph\_last\_modified \= 0.0  
        self.\_lock\_path \= DATA\_DIR / ".graph.lock"

    def \_load\_networkx\_graph(self):  
        graph\_path \= DATA\_DIR / "tiger\_brain.json"  
          
        \# Check if file has been updated since last load  
        current\_mtime \= os.path.getmtime(graph\_path) if graph\_path.exists() else 0.0  
        if self.\_nx\_graph is not None and self.\_graph\_last\_modified \>= current\_mtime:  
            return self.\_nx\_graph

        try:  
            \# Acquire inter-process lock before reading to prevent partial reads  
            with filelock.FileLock(self.\_lock\_path, timeout=5):  
                with open(graph\_path) as f:  
                    data \= json.load(f)  
                self.\_nx\_graph \= nx.node\_link\_graph(data)  
                self.\_graph\_last\_modified \= current\_mtime  
                return self.\_nx\_graph  
        except filelock.Timeout:  
            logger.error("Graph file is locked by a pipeline update.")  
            return None

## **4\. Brittle Data Parsing**

The extraction of structured intelligence from natural language outputs is inherently volatile. While foundational models like Qwen 2.5 32B exhibit robust instruction-following capabilities, RAG pipelines built around manual string manipulation rather than rigorous parsing libraries are highly susceptible to silent data corruption and presentation-layer crashes.

Within the TigerResearchBuddy ecosystem, the ImpactAnalyzer module is tasked with evaluating a student's research alignment with UN Sustainable Development Goals (SDGs). The code asks the LLM to output a JSON string detailing this impact and attempts to extract the payload via brittle string surgery. The implementation naively attempts json.loads(response.strip()). If this fails, it falls back to a rudimentary brace-depth tracking mechanism:

Python

start\_idx \= response.find("{")  
\#... brace counting loop

If the LLM includes conversational preamble (e.g., *"Here is the JSON you requested: \\n {..."*) or omits closing brackets due to the severe context window truncation documented in Vulnerability 2.1, this logic fails to isolate a valid schema. The fallback execution then applies a blanket exception catch:

Python

except Exception as e:  
    return {"score": 0, "sdgs":, "summary": "Could not analyze impact.", "error": str(e)}

By silently swallowing the parser failure and returning a default dictionary containing {"score": 0}, the frontend UI renders a zero-impact score for the student's research without triggering any error state. The student receives no indication that the AI pipeline failed due to a tokenizer error; instead, they are presented with a false, demoralizing metric indicating their academic proposal has absolutely zero societal value.

Severity: High

The Vulnerability: Unhandled KeyErrors and Silent Failures in JSON Extraction

The impact\_analyzer.py module utilizes flawed string manipulation to extract JSON. When the LLM deviates slightly in formatting or is truncated, the parser fails. The broad exception block hides this failure, returning a hardcoded 0 score. This silent data corruption fundamentally breaks the user experience of the Collaboration Hub.

Code Location: src/analysis/impact\_analyzer.py (Lines 38-47).

The Fix:

LLM generation must be forced into strict, deterministic schema formats, and extraction must utilize robust regular expressions paired with explicit Pydantic validation. The system must never swallow the error; it must either retry the generation or explicitly notify the UI layer of the failure.

Python

\# src/analysis/impact\_analyzer.py  
import json  
import re  
from pydantic import BaseModel, ValidationError

class ImpactSchema(BaseModel):  
    score: float  
    sdgs: list\[str\]  
    summary: str

async def analyze\_impact\_async(self, title: str, description: str) \-\> dict:  
    prompt \= f"""...""" \# Setup prompt  
      
    max\_retries \= 2  
    for attempt in range(max\_retries):  
        try:  
            \# Enforce JSON mode natively via Ollama API options  
            response \= await self.client.generate\_async(  
                prompt,   
                system\_prompt="Output strictly valid JSON.",  
                options={"format": "json", "temperature": 0.1}  
            )  
              
            \# Utilize regex to isolate the JSON block reliably  
            json\_match \= re.search(r'\\{.\*\\}', response, re.DOTALL)  
            if not json\_match:  
                raise ValueError("No JSON object found in payload.")  
                  
            parsed\_dict \= json.loads(json\_match.group(0))  
              
            \# Validate schema integrity using Pydantic  
            validated\_data \= ImpactSchema(\*\*parsed\_dict)  
            return validated\_data.model\_dump()  
              
        except (json.JSONDecodeError, ValidationError, ValueError) as e:  
            if attempt \== max\_retries \- 1:  
                \# Do not fail silently. Raise to the API layer for proper HTTP 500 handling.  
                raise RuntimeError(f"Impact Analysis generation failed: {str(e)}")  
            continue \# Retry deterministic generation

This brittleness extends into the core retrieval mechanism via the GraphEnhancedQueryEngine. To support the "Dual-Level Retrieval" architecture, the engine queries the LLM to extract broad themes and specific entities from the user's prompt. The expected output is validated against the KeywordExtractionSchema:

Python

class KeywordExtractionSchema(BaseModel):  
    high\_level\_keywords: List\[str\] \= Field(default\_factory=list)  
    low\_level\_keywords: List\[str\] \= Field(default\_factory=list)

While this module correctly utilizes Pydantic for validation, the fallback logic is fundamentally flawed. If the LLM outputs a string instead of a list (e.g., "high\_level\_keywords": "deep learning" instead of \["deep learning"\]), Pydantic throws a ValidationError. The code catches this error and logs: "Malformed keyword JSON from LLM (falling back): %s". The fallback mechanism simply treats the original, raw query string as both the high-level and low-level keyword.

This completely neutralizes the advanced routing logic. If a user asks, "Who is working on autonomous vehicles at RIT?", and the LLM slightly misformats the JSON, the engine searches the vector database and the exact-match BM25 index for the exact phrase "Who is working on autonomous vehicles at RIT?" rather than extracting the core entities. Because BM25 relies on exact term frequency, searching for long natural language questions severely degrades retrieval accuracy.

Severity: Medium

The Vulnerability: Dual-Level Keyword Extraction Brittleness

The query\_engine.py validation logic does not attempt to coerce or repair slightly malformed LLM outputs. When validation fails, it defaults to injecting the entire raw query into the BM25 search engine, collapsing the precision of the hybrid search layer.

Code Location: src/chatbot/query\_engine.py (\_parse\_keyword\_json and \_keyword\_fallback methods).

The Fix:

Pydantic features powerful pre-validation validators that can coerce scalar strings into lists, salvaging minor LLM hallucinations without sacrificing the entire search pipeline.

Python

\# src/chatbot/query\_engine.py  
from pydantic import BaseModel, Field, field\_validator  
from typing import List, Union

class KeywordExtractionSchema(BaseModel):  
    high\_level\_keywords: List\[str\] \= Field(default\_factory=list)  
    low\_level\_keywords: List\[str\] \= Field(default\_factory=list)

    @field\_validator('high\_level\_keywords', 'low\_level\_keywords', mode='before')  
    @classmethod  
    def coerce\_to\_list(cls, v: Union\[str, List\[str\]\]) \-\> List\[str\]:  
        """Automatically repairs LLM outputs that provide a string instead of a list."""  
        if isinstance(v, str):  
            \# Split comma-separated strings if the LLM hallucinates a CSV format  
            return \[item.strip() for item in v.split(',') if item.strip()\]  
        return v

def \_parse\_keyword\_json(self, raw: str, original\_query: str) \-\> Dict\[str, List\[str\]\]:  
    try:  
        \# Utilize the robust json isolation regex defined earlier  
        import re  
        json\_match \= re.search(r'\\{.\*\\}', raw, re.DOTALL)  
        if json\_match:  
            parsed \= json.loads(json\_match.group(0))  
            validated \= KeywordExtractionSchema(\*\*parsed)  
            return validated.model\_dump()  
    except Exception as e:  
        logger.warning(f"Keyword validation failed: {e}. Falling back.")  
          
    return self.\_keyword\_fallback(original\_query)

Finally, the DeepDistiller pipeline utilized in src/processors/pdf\_distiller.py relies on the Chain-of-Density pattern to summarize academic texts. The schema expected is deeply nested, mapping bibliographic data alongside novelty claims. If the underlying vision-language model hallucinates an extra trailing comma or unescaped quote within a paper's abstract, the standard json.loads invocation throws an unhandled JSONDecodeError. Because this distillation process occurs within an automated batch pipeline spanning thousands of PDFs, an unhandled parsing error on a single malformed PDF abruptly halts the entire vectorization loop, requiring developers to manually isolate the problematic document before restarting the pipeline from scratch.

Severity: High

The Vulnerability: Pipeline Halts via Schema Drift in PDF Distillation

The batch ingestion process lacks granular fault tolerance regarding LLM schema drift. A single invalid JSON output from the DeepDistiller crashes the pipeline orchestration, preventing thousands of subsequent valid PDFs from being processed.

Code Location: src/processors/pdf\_distiller.py (JSON extraction logic during batch processing).

The Fix:

Implement the extract\_and\_validate utility universally across the ingestion pipeline and ensure that parsing failures yield a structured "Failed Document" schema rather than raising fatal exceptions to the orchestrator.

Python

\# src/processors/pdf\_distiller.py  
from..utils.json\_utils import extract\_and\_validate

async def distill\_async(self, text: str, filename: str) \-\> Optional\[dict\]:  
    prompt \= self.\_build\_prompt(text)  
    try:  
        raw\_response \= await self.llm\_client.generate\_async(  
            prompt,   
            system\_prompt="You are a JSON schema extractor."  
        )  
          
        \# Utilize the robust parsing utility  
        card\_data \= extract\_json(raw\_response)  
        if card\_data is None:  
            logger.error(f"Failed to isolate JSON from LLM response for {filename}")  
            return self.\_generate\_error\_card(filename, "json\_isolation\_failed")  
              
        return card\_data  
          
    except Exception as e:  
        logger.error(f"Distillation crashed for {filename}: {e}")  
        \# Return a safe fallback card to keep the pipeline moving  
        return self.\_generate\_error\_card(filename, str(e))

def \_generate\_error\_card(self, filename: str, reason: str) \-\> dict:  
    """Safe schema representation for failed extractions to prevent pipeline halts."""  
    return {  
        "card\_id": filename,  
        "bibliographic\_data": {"title": f"Failed Extraction: {filename}"},  
        "core\_content": {"error": reason},  
        "knowledge\_graph": {"nodes":, "edges":}  
    }

By systematically addressing these parsing brittlenesses, the TigerResearchBuddy architecture ensures that the stochastic nature of language models does not compromise the deterministic logic of the backend application.

## **Conclusion**

The TigerResearchBuddy platform demonstrates an ambitious attempt to unify localized semantic vector search with explicit knowledge graph traversal. The deployment of a 32-billion parameter model on consumer-grade Apple Silicon represents a significant engineering achievement. However, the codebase is fundamentally compromised by the inherent complexities of translating synchronous data science scripts into a highly concurrent, asynchronous web framework.

The vulnerabilities identified in this audit are not superficial syntax errors; they represent deep structural incompatibilities between the ASGI event loop, the hardware memory manager, and the stochastic behavior of LLM prompt engineering. Remediating these vulnerabilities requires a systemic shift away from global mutable state and implicit blocking mechanics. By encapsulating GPU resources behind strict asynchronous semaphores, shifting I/O constraints to isolated thread pools, eliminating hardcoded token ceilings, and adopting Pydantic-driven data coercion, the architecture can achieve the enterprise-grade stability required for a multi-user academic environment.