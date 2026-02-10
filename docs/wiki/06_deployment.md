# 06 - Deployment

**Last Updated:** February 9, 2026  
**Purpose:** Production deployment procedures and best practices

---

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment](#production-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Monitoring & Logging](#monitoring--logging)
6. [Backup & Recovery](#backup--recovery)

---

## Deployment Overview

TigerBrain supports three deployment modes:

1. **Local Development** - Laptop/workstation for testing
2. **Single-Server Production** - Self-hosted on-premise
3. **Containerized** - Docker for cloud deployment

---

## Local Development Setup

### Prerequisites

```bash
# System requirements
- Python 3.10+
- 8GB RAM minimum (16GB recommended)
- 10GB disk space

# macOS
brew install ollama

# Linux
curl https://ollama.ai/install.sh | sh
```

### Installation Steps

**1. Clone Repository**
```bash
git clone <repo-url>
cd tiger_research_buddy
```

**2. Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Setup Environment**
```bash
cp .env.template .env
# Edit .env with your settings
```

**5. Pull Ollama Models**
```bash
ollama pull qwen2.5
ollama create tigerbuddy -f Modelfile.tigerbuddy
```

**6. Initialize Data**
```bash
python scripts/setup_v2.py
```

**7. Run Application**
```bash
streamlit run src/ui/app.py
```

**Access:** `http://localhost:8501`

---

## Production Deployment

### Server Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 16GB
- Disk: 50GB SSD
- OS: Ubuntu 22.04 LTS

**Recommended:**
- CPU: 8 cores (Apple M1/M2 or Intel/AMD)
- RAM: 32GB
- Disk: 100GB NVMe SSD
- OS: Ubuntu 22.04 LTS

### System Setup

**1. Install System Dependencies**
```bash
sudo apt update
sudo apt install -y python3.10 python3-pip python3-venv git
```

**2. Install Ollama**
```bash
curl https://ollama.ai/install.sh | sh
sudo systemctl enable ollama
sudo systemctl start ollama
```

**3. Configure Firewall**
```bash
sudo ufw allow 8501/tcp  # Streamlit
sudo ufw allow 22/tcp    # SSH
sudo ufw enable
```

**4. Setup Application User**
```bash
sudo useradd -m -s /bin/bash tigerbrain
sudo su - tigerbrain
```

**5. Deploy Application**
```bash
git clone <repo> ~/tiger_research_buddy
cd ~/tiger_research_buddy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**6. Setup Systemd Service**

Create `/etc/systemd/system/tigerbrain.service`:
```ini
[Unit]
Description=TigerBrain Research Assistant
After=network.target ollama.service

[Service]
Type=simple
User=tigerbrain
WorkingDirectory=/home/tigerbrain/tiger_research_buddy
Environment="PATH=/home/tigerbrain/tiger_research_buddy/venv/bin"
ExecStart=/home/tigerbrain/tiger_research_buddy/venv/bin/streamlit run src/ui/app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

**7. Enable and Start Service**
```bash
sudo systemctl daemon-reload
sudo systemctl enable tigerbrain
sudo systemctl start tigerbrain
```

**8. Check Status**
```bash
sudo systemctl status tigerbrain
journalctl -u tigerbrain -f
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl https://ollama.ai/install.sh | sh

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose ports
EXPOSE 8501

# Start script
CMD ["bash", "-c", "ollama serve & sleep 5 && ollama pull tigerbuddy && streamlit run src/ui/app.py"]
```

### Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  tigerbrain:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=http://localhost:11434
      - LOG_LEVEL=INFO
    restart: unless-stopped

volumes:
  ollama_data:
```

### Build and Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Monitoring & Logging

### Application Logs

**Location:** `logs/tigerbrain.log`

**Log Format:**
```
2026-02-09 10:45:22 - INFO - Query received: "Who works on AI?"
2026-02-09 10:45:23 - DEBUG - Entity extraction found: concept_ai
2026-02-09 10:45:24 - INFO - Response generated: 200 tokens
```

**Viewing Logs:**
```bash
# Tail logs
tail -f logs/tigerbrain.log

# Search for errors
grep ERROR logs/tigerbrain.log

# Log rotation (logrotate)
sudo vim /etc/logrotate.d/tigerbrain
```

**Logrotate Config:**
```
/home/tigerbrain/tiger_research_buddy/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 tigerbrain tigerbrain
}
```

### Performance Monitoring

**Key Metrics:**
- Query latency (target: <4s)
- Graph load time (target: <3s)
- Vector search time (target: <100ms)
- LLM inference time (target: <2.5s)

**Monitoring Script:**
```python
# scripts/monitor.py
import time
from src.retrieval.hybrid_retriever import HybridRetriever

def benchmark_query(query: str):
    start = time.time()
    results = retriever.retrieve(query)
    elapsed = time.time() - start
    
    print(f"Query: {query}")
    print(f"Latency: {elapsed:.2f}s")
    print(f"Results: {len(results['graph_results'])} graph, {len(results['vector_results'])} vector")

if __name__ == "__main__":
    benchmark_query("Who works on computer vision?")
```

**Run Monitoring:**
```bash
python scripts/monitor.py | tee logs/performance.log
```

### Health Checks

**Endpoint:** `/healthz` (if using FastAPI - future)

**Manual Check:**
```bash
curl http://localhost:8501
# Should return 200 OK
```

**Systemd Watchdog:**
```ini
[Service]
WatchdogSec=60
Restart=on-failure
RestartSec=10
```

---

## Backup & Recovery

### Data to Backup

1. **Knowledge Graph:** `data/tiger_brain.json`
2. **Vector Store:** `data/chroma/`  
3. **Research Cards:** `data/research_cards/`
4. **Entity Mappings:** `data/entity_mappings.json`
5. **Configuration:** `.env`

### Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backups/tigerbrain"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

mkdir -p $BACKUP_DIR

# Backup data
tar -czf $BACKUP_FILE \
    data/tiger_brain.json \
    data/chroma/ \
    data/research_cards/ \
    data/entity_mappings.json \
    .env

echo "Backup created: $BACKUP_FILE"

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +7 -delete
```

**Cron Job (daily at 2 AM):**
```bash
0 2 * * * /home/tigerbrain/tiger_research_buddy/scripts/backup.sh
```

### Recovery

```bash
# 1. Stop service
sudo systemctl stop tigerbrain

# 2. Extract backup
cd ~/tiger_research_buddy
tar -xzf /backups/tigerbrain/backup_20260209_020000.tar.gz

# 3. Restart service
sudo systemctl start tigerbrain
```

---

**Next:** [Troubleshooting →](./07_troubleshooting.md)
