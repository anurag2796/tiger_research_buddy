# 🐅 TigerResearchBuddy - AI Agent for RIT Research

TigerResearchBuddy is an intelligent, AI-powered assistant designed to help RIT (Golisano College) students discover research opportunities, potential advisors, and interesting projects.

It combines **web scraping**, **vector databases** (RAG), and **local Large Language Models** (Ollama) to provide a private, offline-capable research companion.

## 🚀 Features

*   **🕵️‍♂️ Comprehensive Scraper**: Automatically collects faculty profiles, research interests, and contact info from the RIT directory.
*   **📚 Paper Analysis**: Downloads and indexes open-access PDFs (ArXiv, Semantic Scholar) to understand what professors *actually* work on.
*   **🧠 Intelligent Chat**: Ask natural language questions like *"Who works on computer vision?"* or *"What is Professor X's latest paper about?"*.
*   **💻 Web Interface**: A modern Streamlit web app for easy interaction.
*   **🔒 Privacy-First**: Runs locally using Ollama (Llama 3, Mistral, etc.) - no data leaves your machine.

---

## 🛠️ Installation & Setup

### Prerequisites
1.  **Python 3.10+** installed.
2.  **Ollama** installed and running (for the local LLM).
    *   Download from [ollama.com](https://ollama.com).
    *   Run `ollama pull llama3` (or your preferred model).

### 1. Clone & Install
```bash
git clone https://github.com/StartYourLoop/tiger_research_buddy.git
cd tiger_research_buddy

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Edit `.env` to add your optional API keys (not strictly required if running fully offline/local mode, but recommended for scraping):
```env
# Optional: For better scraping limits
# SEMANTIC_SCHOLAR_API_KEY=your_key_here
```

---

## 🏃‍♂️ How to Run

### Option A: The Web App (Recommended)
This launches the full graphical interface.

1.  Make sure Ollama is running (`ollama serve`).
2.  Run the app:
    ```bash
    streamlit run web_app.py
    ```
3.  Open your browser to `http://localhost:8501`.

### Option B: The CLI (Command Line)
You can also chat directly in the terminal.

```bash
python main.py chat-offline
```

---

## 🕷️ Data Collection (Scraping)

To populate the database with fresh data (this takes 30-60 mins):

```bash
# Full comprehensive scrape (Faculty + Papers + PDFs)
python main.py scrape-all

# For a quicker test (limit papers)
python main.py scrape-all --max-papers 5
```

The data is saved to `data/` and indexed into a local ChromaDB vector store.

---

## 📂 Project Structure

*   `src/`: Core source code.
    *   `crawlers/`: Scrapers for RIT, ArXiv, Semantic Scholar.
    *   `database/`: Vector store (ChromaDB) logic.
    *   `chatbot/`: RAG implementation and LLM interface.
*   `data/`: Stores downloaded JSONs and the vector DB.
*   `web_app.py`: The Streamlit frontend.
*   `main.py`: The CLI entry point.

---

## 🤝 Contributing
Built for **Imagine RIT**. Contributions welcome!
