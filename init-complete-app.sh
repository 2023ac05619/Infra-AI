#!/bin/bash
# InfraAI Complete Application Setup Script
# This script sets up both the backend (InfraAI) and frontend (InfraChat) for a fresh start

set -e

echo " InfraAI Complete Application Setup"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    print_success "Docker is running"
}

# Check Ollama connectivity (external service)
check_ollama() {
    print_status "Checking Ollama connectivity..."

    # Get Ollama URL from backend .env
    if [ -f "backend/.env" ]; then
        OLLAMA_URL=$(grep "^OLLAMA_API_URL=" backend/.env | cut -d'=' -f2)
    else
        # Fallback to default if .env doesn't exist
        OLLAMA_URL="http://192.168.200.201:11434"
    fi

    # Try to connect to Ollama API
    if curl -s --max-time 10 "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
        print_success "Ollama is reachable at ${OLLAMA_URL}"
    else
        print_warning "Ollama is not reachable at ${OLLAMA_URL}"
        print_warning "Please ensure Ollama server is running on the configured server"
        print_warning "Current OLLAMA_API_URL: ${OLLAMA_URL}"
        echo ""
    fi
}

# Setup backend
setup_backend() {
    print_status "Setting up InfraAI Backend..."

    cd backend

    # Start Docker services
    print_status "Starting PostgreSQL and Redis..."
    docker-compose up -d

    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 10

    # Initialize database
    print_status "Initializing backend database..."
    python3 scripts/init_db.py

    # Load sample policies
    print_status "Loading sample policies..."
    python3 scripts/load_sample_policies.py

    cd ..
    print_success "Backend setup complete!"
}

# Setup frontend
setup_frontend() {
    print_status "Setting up InfraChat Frontend..."

    cd frontend

    # Reset database
    print_status "Resetting frontend database..."
    rm -f db/custom.db
    npm run db:push

    print_status "Frontend database initialized (no default users)"

    cd ..
    print_success "Frontend setup complete!"
}

# Start services
start_services() {
    print_status "Starting all services..."

    # Start backend in background
    print_status "Starting InfraAI backend..."
    cd backend
    python3 -m app.main &
    BACKEND_PID=$!
    cd ..

    # Start frontend in background
    print_status "Starting InfraChat frontend..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    print_success "All services started!"
    echo ""
    echo "=========================================="
    echo " APPLICATION READY!"
    echo "=========================================="
    echo ""
    echo " Frontend (InfraChat): http://localhost:3001"
    echo " Backend (InfraAI API): http://localhost:8001"
    echo ""
    echo " First-Time Setup:"
    echo "   Visit http://localhost:3001 to create your admin account"
    echo "   Enter any username and password to register as the first user"
    echo ""
    echo " API Documentation: http://localhost:8001/docs"
    echo ""
    echo " To stop: kill $BACKEND_PID $FRONTEND_PID"
    echo ""
    echo "=========================================="

    # Wait for services
    wait $BACKEND_PID $FRONTEND_PID
}

# Main setup
main() {
    print_status "Starting complete InfraAI application setup..."

    # Check prerequisites
    check_docker
    check_ollama

    # Setup components
    setup_backend
    setup_frontend

    # Start everything
    start_services
}

# Run main function
main "$@"
