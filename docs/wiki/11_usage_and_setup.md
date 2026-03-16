# 11 - Setup & Usage Examples

**Last Updated:** March 9, 2026  
**Purpose:** Provide clear, step-by-step usage instructions for developers and users of TigerResearchBuddy.

---

## Local Environment Setup

TigerResearchBuddy relies on a local LLM infrastructure using Ollama and Python 3.8+.

### 1. Install Dependencies
```bash
# Ensure you are on Python 3.8 or higher
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Ollama (Local AI)
You must have [Ollama](https://ollama.ai) installed and running locally for the system to process data without an API key.
```bash
# Start the Ollama background service if not already running
brew services start ollama
# Alternatively run: ollama serve

# Pull the primary pipeline model (Qwen 2.5 / llama2 variant)
ollama pull tigerbuddy
# Or fallback generic models
ollama pull llama3:8b
```

### 3. API Keys (Optional Fallback)
If you wish to use Gemini for complex graph queries or validation tasks:
1. Copy `.env.example` to `.env`
2. Insert your Google Gemini API key:
   ```env
   GEMINI_API_KEY=AIzaSy...
   ```

---

## Executing the Data Pipeline

The data pipeline can process hundreds of faculty members or be run in a restricted "dev" mode for quick testing. All orchestration is managed by `run_pipeline.py`.

### The Development/Restricted Run
If you only want to crawl the top 3 faculty profiles to test a new module, use restricted mode.
```bash
python run_pipeline.py --mode restricted
```

### Full Pipeline Orchestration
To execute the absolute full ingestion chain (Crawler -> Scholar metrics -> PDF Download -> LLM Distillation -> DB Injection):
```bash
python run_pipeline.py --mode full
```

### Skipping Specific Stages
You can control intermediate execution logic using skip flags. For instance, if you've already downloaded 500 PDFs and just want to re-run the `DeepDistiller` due to a prompt change:
```bash
python run_pipeline.py --mode full --skip-crawl --skip-scholar --skip-download
```

If you manually altered the `tiger_brain.json` relationships and merely want to rebuild the vector indexes and network map:
```bash
python run_pipeline.py --skip-crawl --skip-scholar --skip-download --skip-distill
```

---

## Running the Web UI

The user-facing chat and visualizer interface is powered by Streamlit.

```bash
streamlit run web_app.py
```
> **Access at:** `http://localhost:8501`

### UI Functionality Overview
- **Chat Interface**: Located on the main pane. Ask complex queries like "Who specializes in Spiking Neural Networks at RIT?" 
- **Persona Switching**: Use the sidebar to switch between `Tiger` (Encouraging Student Guide), `Analyzer` (Strict academic dataset), and `Critique` (Challenges standard definitions).
- **Prism View**: A separate tab to visually navigate the NetworkX graph in browser (Faculty nodes connected to Research nodes).

---

## Command Line Testing (CLI)

The `main.py` entry point acts as a legacy CLI tool for executing one-off isolated tests without booting Streamlit.

### Chat via CLI
To interact with the local LLM directly in terminal:
```bash
python main.py chat-offline
```
*(Optionally use `python main.py chat` to route to Gemini if configured).*

### Single Faculty Crawl
To test extraction logic against a specific URL:
```bash
python main.py crawl --url "https://www.rit.edu/computing/directory/example-user"
```

## Maintenance & Diagnostics
```bash
# Inspect duplicates in Vector Store or orphaned graph nodes
python scripts/debug_duplicates.py

# Auto-generate weekly quality health report
python scripts/weekly_quality_report.py
```
