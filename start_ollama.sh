#!/bin/bash
# Start Ollama with Jetson-optimized settings
# Models are stored on NVMe for speed; parallel slots match DISTILLER_CONCURRENCY

pkill -f "ollama serve" 2>/dev/null
fuser -k 11434/tcp 2>/dev/null
sleep 2

OLLAMA_MODELS=/mnt/nvme/ollama_models \
OLLAMA_NUM_PARALLEL=3 \
ollama serve > /tmp/ollama.log 2>&1 &

sleep 4
ollama list && echo "Ollama ready"
