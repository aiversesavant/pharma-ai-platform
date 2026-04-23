#!/bin/bash
set -e

echo "Setting up pharma-ai-platform..."

if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
  python3 -m venv venv
fi

if [ -d "venv" ]; then
  source venv/bin/activate
elif [ -d ".venv" ]; then
  source .venv/bin/activate
fi

pip install --upgrade pip
pip install -r requirements.txt

mkdir -p data/uploads data/audit data/review data/runtime/vector_store logs docs tests scripts infra

echo "Setup complete."
