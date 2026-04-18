#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TigerResearchBuddy — Jetson Orin First-Time Setup
# ═══════════════════════════════════════════════════════════════════════════════
# Run this ONCE on the Jetson Orin BEFORE handing off to Claude Code.
#
# Usage:
#   chmod +x ORIN_SETUP.sh
#   ./ORIN_SETUP.sh
#
# Prerequisites:
#   - JetPack 6+ installed (Ubuntu 22.04 based)
#   - Internet access for pulling models & pip packages
#   - Git configured with access to your repo
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

if [ -d ".git" ]; then
    PROJECT_DIR="$(pwd)"
else
    PROJECT_DIR="$(pwd)/tiger_research_buddy"
fi
BRANCH="orin"

echo "═══════════════════════════════════════════════════════════"
echo " 🐅 TigerResearchBuddy — Jetson Orin Setup"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ── 1. Clone / Pull Repo ─────────────────────────────────────────────────────
echo "[1/7] Cloning or updating repository..."
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "  → Repo exists, pulling latest from $BRANCH..."
    cd "$PROJECT_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    echo "  → Cloning fresh..."
    git clone https://github.com/anurag2796/tiger_research_buddy.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    git checkout "$BRANCH"
fi
echo "  ✓ Repository ready at $PROJECT_DIR"
echo ""

# ── 2. System Dependencies ──────────────────────────────────────────────────
echo "[2/7] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv libffi-dev libxml2-dev \
    libxslt1-dev libjpeg-dev zlib1g-dev tesseract-ocr lxml 2>/dev/null || true
echo "  ✓ System deps installed"
echo ""

# ── 3. Python Virtual Environment ───────────────────────────────────────────
echo "[3/7] Creating Python virtual environment..."
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    python3 -m venv "$PROJECT_DIR/.venv"
fi
source "$PROJECT_DIR/.venv/bin/activate"
pip install --upgrade pip setuptools wheel -q
echo "  ✓ Virtual environment ready: $PROJECT_DIR/.venv"
echo ""

# ── 4. Install Python Dependencies ──────────────────────────────────────────
echo "[4/7] Installing Python dependencies..."
echo "  (This may take several minutes on ARM64)"
pip install -r "$PROJECT_DIR/requirements.txt" -q 2>&1 | tail -5
echo "  ✓ Python dependencies installed"
echo ""

# ── 5. Copy Jetson-Optimized .env ────────────────────────────────────────────
echo "[5/7] Setting up Jetson environment..."
cp "$PROJECT_DIR/.env.jetson" "$PROJECT_DIR/.env"
echo "  ✓ Copied .env.jetson → .env"
echo ""

# ── 6. Install & Configure Ollama ────────────────────────────────────────────
echo "[6/7] Setting up Ollama..."
if command -v ollama &>/dev/null; then
    echo "  → Ollama already installed: $(ollama --version 2>/dev/null || echo 'unknown')"
else
    echo "  → Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Ensure Ollama service is running
if systemctl is-active --quiet ollama 2>/dev/null; then
    echo "  → Ollama service is running"
else
    echo "  → Starting Ollama service..."
    sudo systemctl enable ollama 2>/dev/null || true
    sudo systemctl start ollama 2>/dev/null || true
    sleep 3
fi

# Pull the best model based on available memory
TOTAL_MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
echo "  → Detected ${TOTAL_MEM_GB}GB total memory"

if [ "$TOTAL_MEM_GB" -ge 48 ]; then
    MODEL="llama3.1:8b"
elif [ "$TOTAL_MEM_GB" -ge 24 ]; then
    MODEL="llama3.2:3b"
elif [ "$TOTAL_MEM_GB" -ge 12 ]; then
    MODEL="llama3.2:1b"
else
    MODEL="tinyllama:1.1b"
fi

echo "  → Pulling model: $MODEL (this may take a while)..."
ollama pull "$MODEL"
echo "  ✓ Ollama ready with model: $MODEL"
echo ""

# ── 7. Verify Hardware Detection ────────────────────────────────────────────
echo "[7/7] Verifying hardware detection..."
cd "$PROJECT_DIR"
source .venv/bin/activate
python3 -c "
from src.utils.hardware import HW_PROFILE
print(f'  Platform:    {HW_PROFILE.platform}')
print(f'  CUDA:        {HW_PROFILE.has_cuda}')
print(f'  Embedding:   {HW_PROFILE.embedding_device}')
print(f'  Concurrency: {HW_PROFILE.chat_concurrency}')
print(f'  Context:     {HW_PROFILE.context_window}')
print(f'  PDF Engine:  {HW_PROFILE.pdf_engine}')
" 2>/dev/null || echo "  ⚠ Hardware detection failed (deps may be missing — Claude Code will fix)"
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════"
echo " ✅ Setup Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo " Project:  $PROJECT_DIR"
echo " Branch:   $BRANCH"
echo " Model:    $MODEL"
echo " Python:   $PROJECT_DIR/.venv/bin/python3"
echo ""
echo " ┌─────────────────────────────────────────────────────┐"
echo " │  IMPORTANT: Update src/utils/config.py with the    │"
echo " │  pulled model name before starting the chatbot:     │"
echo " │                                                     │"
echo " │  LLMConfig.CHAT_MODEL = \"$MODEL\"         │"
echo " │  LLMConfig.PIPELINE_MODEL = \"$MODEL\"     │"
echo " └─────────────────────────────────────────────────────┘"
echo ""
echo " Next: Hand off to Claude Code with CLAUDE_CODE_PROMPT.md"
echo "   cat CLAUDE_CODE_PROMPT.md | claude"
echo ""
