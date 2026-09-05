#!/usr/bin/env bash
# ==============================================================================
# Shikshak AI — 1-Step Environment Bootstrap Script
# Usage:
#   chmod +x scripts/setup_env.sh
#   ./scripts/setup_env.sh
# ==============================================================================

set -e

echo "======================================================================"
echo "  SHIKSHAK AI — REPOSITORY BOOTSTRAP & DEPENDENCY INSTALLER"
echo "======================================================================"

# 1. Virtual Environment Setup
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# 2. Upgrade pip and install dependencies
echo "Installing Python dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Run model downloader and directory setup
echo "Running model downloader and directory verification..."
python scripts/setup_and_download_models.py "$@"

echo "======================================================================"
echo "  Setup Complete! To activate the environment in your shell, run:"
echo "    source .venv/bin/activate"
echo "======================================================================"
