# 06 - Deployment

**Last Updated:** February 23, 2026  
**Purpose:** Production deployment procedures and best practices

---

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment (Single Server)](#production-deployment-single-server)
4. [Docker Deployment](#docker-deployment)
5. [Monitoring & Logging](#monitoring--logging)
6. [Backup & Recovery](#backup--recovery)

---

## Deployment Overview

TigerBrain supports three deployment configurations:

| Mode | Use Case | Complexity |
|------|----------|------------|
| **Local Development** | Laptop for personal use/testing | Low |
| **Single-Server Production** | Self-hosted on-premise lab server | Medium |
| **Containerized (Docker)** | Cloud or reproducible deployments | High |

**All modes require Ollama running locally.** The system is intentionally local-first — no external API calls for core inference.

---

## Local Development Setup

### Prerequisites

```bash
# macOS
brew install ollama python@3.10

# Linux (Ubuntu 22.04+)
curl https://ollama.ai/install.sh | sh
sudo apt install python3.10 python3.10-venv
```

**Disk space:** 10GB minimum (PDFs + models + vector store)  
**RAM:** 8GB minimum, 16GB recommended (for model + graph in memory simultaneously)

### Step-by-Step Installation

**1. Clone Repository**
```bash
git clone <repo-url>
cd tiger_research_buddy
```

**2. Create & Activate Virtual Environment**
```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
# Includes: surya-ocr, gmft, chromadb, sentence-transformers
# On Apple Silicon, torch MPS support is included by default
```

**4. Configure Environment**
```bash
cp .env.example .env
# Edit .env:
#   GEMINI_API_KEY=...   (optional — only if using Gemini as LLM fallback)
#   OLLAMA_HOST=http://localhost:11434   (default, usually correct)
```

**5. Pull & Build Ollama Model**
```bash
ollama pull qwen2.5             # Base model (~4GB)
# Optional: faster quantized version
ollama pull qwen2.5:7b-q4_0    # 4-bit quantized (~2.5GB)

# Build the TigerBuddy personality
ollama create tigerbuddy -f Modelfile.tigerbuddy
ollama list    # Verify tigerbuddy is available
```

**6. Run the Pipeline (Restricted Mode — Fast)**
```bash
# Crawls ~10 faculty, downloads papers, distills, indexes
python run_pipeline.py --mode restricted
# Takes ~10–20 minutes depending on hardware and Ollama inference speed
```

**7. Launch the Application**
```bash
streamlit run web_app.py
# Access at: http://localhost:8501
```

### Quick Resume Commands

If pipeline stages have already run, skip them:
```bash
# Already crawled — just rebuild index and graph
python run_pipeline.py --skip-crawl --skip-scholar --skip-download

# Already have research cards — just re-index
python run_pipeline.py --skip-crawl --skip-scholar --skip-download --skip-distill
```

---

## Production Deployment (Single Server)

### Recommended Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 16GB | 32GB |
| Storage | 50GB SSD | 100GB NVMe |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Server Setup

```bash
# 1. Install system deps
sudo apt update && sudo apt install -y python3.10 python3.10-venv python3-pip git

# 2. Install & enable Ollama
curl https://ollama.ai/install.sh | sh
sudo systemctl enable ollama
sudo systemctl start ollama

# 3. Setup app user
sudo useradd -m -s /bin/bash tigerbrain
sudo su - tigerbrain

# 4. Deploy app
git clone <repo> ~/tiger_research_buddy
cd ~/tiger_research_buddy
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Configure .env
```

### Firewall Configuration

```bash
sudo ufw allow 8501/tcp    # Streamlit UI
sudo ufw allow 22/tcp      # SSH access
sudo ufw enable
```

### Systemd Service Setup

Create `/etc/systemd/system/tigerbrain.service`:
```ini
[Unit]
Description=TigerBrain Research Assistant
After=network.target ollama.service

[Service]
Type=simple
User=tigerbrain
WorkingDirectory=/home/tigerbrain/tiger_research_buddy
Environment="PATH=/home/tigerbrain/tiger_research_buddy/.venv/bin"
ExecStart=/home/tigerbrain/tiger_research_buddy/.venv/bin/streamlit run web_app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
WatchdogSec=60
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tigerbrain
sudo systemctl start tigerbrain
sudo systemctl status tigerbrain    # Verify running
journalctl -u tigerbrain -f         # Tail logs
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl https://ollama.ai/install.sh | sh

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8501

CMD ["bash", "-c", "ollama serve & sleep 5 && ollama pull tigerbuddy && python run_pipeline.py --mode restricted && streamlit run web_app.py --server.address 0.0.0.0"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  tigerbrain:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data          # Persist all pipeline data
      - ollama_data:/root/.ollama # Persist downloaded models
    environment:
      - OLLAMA_HOST=http://localhost:11434
      - LOG_LEVEL=INFO
    restart: unless-stopped

volumes:
  ollama_data:
```

```bash
docker-compose build
docker-compose up -d
docker-compose logs -f    # View live logs
docker-compose down       # Stop
```

---

## Monitoring & Logging

### Application Logs

**Location:** `logs/tigerbrain.log`

```bash
tail -f logs/tigerbrain.log       # Live tail
grep ERROR logs/tigerbrain.log    # Error scan  
```

**Logrotate Config (`/etc/logrotate.d/tigerbrain`):**
```
/home/tigerbrain/tiger_research_buddy/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
}
```

### Pipeline Performance Metrics

The pipeline runner outputs a summary table after every run — check it for stage-level timing:

```
╭────────────────────────────────────────────────────╮
│              🐅 Pipeline Summary                    │
├───────────────────┬─────────┬────────┬─────────────┤
│ Stage             │ Status  │ Time   │ Detail      │
│ 1. Crawl          │ ✓ Done  │ 0:02   │ 10 profiles │
│ 2. Scholar Enrich │ ✓ Done  │ 0:05   │ 8 enriched  │
│ 3. Download Papers│ ✓ Done  │ 0:15   │ 24 papers   │
│ 4. Distill Papers │ ✓ Done  │ 0:45   │ 24 cards    │
│ 5. Index          │ ✓ Done  │ 0:02   │ 120 docs    │
│ 6. Knowledge Graph│ ✓ Done  │ 0:03   │ graph built │
╰───────────────────┴─────────┴────────┴─────────────╯
```

### Performance Targets

| Operation | Target Latency |
|-----------|---------------|
| End-to-end query | < 10s |
| Vector search (top-5) | < 100ms |
| Graph traversal (2-hop) | < 1ms |
| LLM inference (q4_0) | < 3s |

---

## Backup & Recovery

### Critical Data Files

| File | Description | Priority |
|------|-------------|----------|
| `data/tiger_brain.json` | Knowledge graph | Critical |
| `data/chroma/` | Vector embeddings | Critical |
| `data/research_cards/` | Distilled paper cards | High |
| `data/rit_data.json` | Faculty profiles | High |
| `data/entity_mappings.json` | Canonical entity IDs | Medium |
| `.env` | Configuration secrets | High |

### Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backups/tigerbrain"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" \
    data/tiger_brain.json \
    data/chroma/ \
    data/research_cards/ \
    data/rit_data.json \
    data/entity_mappings.json \
    .env

echo "Backup created: $BACKUP_DIR/backup_$DATE.tar.gz"

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +7 -delete
```

**Cron (daily at 2 AM):**
```bash
0 2 * * * /home/tigerbrain/tiger_research_buddy/scripts/backup.sh
```

### Recovery

```bash
sudo systemctl stop tigerbrain
cd ~/tiger_research_buddy
tar -xzf /backups/tigerbrain/backup_20260220_020000.tar.gz
sudo systemctl start tigerbrain
```

---

**Next:** [Troubleshooting →](./07_troubleshooting.md)
