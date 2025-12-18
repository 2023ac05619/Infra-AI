#!/bin/bash

# InfraAI Backend Setup Script

set -e

echo "================================"
echo "  InfraAI Backend Setup"
echo "================================"
echo ""

# Check Python version
echo "[1/7] Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )[0-9]+\.[0-9]+')
echo "Found Python $PYTHON_VERSION"

if (( $(echo "$PYTHON_VERSION < 3.10" | bc -l) )); then
    echo "ERROR: Python 3.10+ is required"
    exit 1
fi

# Create virtual environment
echo ""
echo "[2/7] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "[3/7] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "[4/7] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup environment
echo ""
echo "[5/7] Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
    echo "Please edit .env with your configuration"
else
    echo ".env file already exists"
fi

# Check external services
echo ""
echo "[6/7] Checking external service connectivity..."
# Check Ollama connectivity (external service)
if [ -f ".env" ]; then
    OLLAMA_URL=$(grep "^OLLAMA_API_URL=" .env | cut -d'=' -f2)
else
    OLLAMA_URL="http://192.168.200.201:11434"
fi

echo "Checking Ollama connectivity at ${OLLAMA_URL}..."
if curl -s --max-time 10 "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    echo " Ollama is reachable"
else
    echo " Ollama not reachable at ${OLLAMA_URL} (this is expected if running externally)"
fi

# Start local services with Docker
echo ""
echo "[7/7] Starting local infrastructure services..."
if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
    echo "Starting PostgreSQL and Redis..."
    docker-compose up -d

    echo "Waiting for services to be ready..."
    sleep 10
else
    echo "Docker not found. Please install PostgreSQL and Redis manually."
fi

# Database initialization will happen on first run
echo ""
echo "[7/7] Setup complete!"
echo ""
echo "================================"
echo "  Next Steps:"
echo "================================"
echo "1. Edit .env file with your configuration"
echo "2. Start the backend: python -m app.main"
echo "3. Start the worker: python -m app.worker"
echo ""
echo "API will be available at: http://localhost:8001"
echo "API Documentation: http://localhost:8001/docs"
echo ""
