# KnowledgeDaemon: Autonomous Graph Maintenance 🧠 🛡️

## Goal
To create a self-healing, self-improving knowledge graph that "learns" from new data and corrects its own mistakes without manual patching.

## Architecture

The `KnowledgeDaemon` runs as a background process (or scheduled job) with three main loops:

### 1. The Watcher (Ingestion) 👁️
**Trigger:** New PDF added to `data/papers`.
**Action:**
1.  Run `DeepDistiller` to extract text & metadata.
2.  **Cross-Check:** "Does this paper mention authors not in my Graph?"
3.  **Update:** Create new Author/Concept nodes immediately.

### 2. The Audrey (Auditor) 🕵️‍♀️
**Trigger:** Periodic (e.g., every hour) or Low Confidence Score.
**Action:**
1.  **Scan for Holes:** "Find all Faculty nodes with empty bios." (e.g., Thomas Kinsman).
2.  **Investigate:**
    *   Search the Vector Store for that name.
    *   Read the "About Authors" section of their papers.
    *   Visit their RIT URL (if available in `site_graph`).
3.  **Patch:** Update the node with the new findings.

### 3. The Critic (Reflection) ⚖️
**Trigger:** User Feedback (e.g., "That answer was wrong") or Hallucination Check.
**Action:**
1.  **Trace:** Retrieve the nodes used to generate the bad answer.
2.  **Verify:** Ask the LLM: "Does Source Document X actually support Claim Y?"
3.  **Prune/Refine:** If false, delete the edge or update the node.

## Example Scenario: "The Thomas Kinsman Incident"

**Current State (Manual):**
1.  User notices Kinsman is missing.
2.  Developer writes `patch_kinsman.py`.
3.  Developer runs script.

**Future State (KnowledgeDaemon):**
1.  **Ingestion:** Daemon reads *Paper A*. It sees "Thomas Kinsman" in Acknowledgements.
2.  **Hypothesis:** Daemon creates a "Proto-Node" for Kinsman (Confidence: Low).
3.  **Auditor:** Daemon notices `faculty_kinsman` has low confidence and no bio.
4.  **Investigation:** Daemon searches its own index for "Thomas Kinsman". It finds a URL in `site_graph`.
5.  **Resolution:** Daemon merges the URL data + Paper stats into a full `Faculty` node.
6.  **Result:** Kinsman is live in the graph before the user even asks.

## Implementation Roadmap

1.  **`src/daemon/auditor.py`**: The logic to find "sparse nodes".
2.  **`src/daemon/patcher.py`**: The LLM agent that fixes them.
3.  **`scripts/start_daemon.py`**: The loop that runs them.

## "Does it keep autopatching?"
**Yes.** As long as the daemon is running, it will continuously cycle through the graph, looking for ways to improve data quality (adding missing dates, refining concept taxonomies, deduplicating entities).
