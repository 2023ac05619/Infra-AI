#!/bin/bash
# InfraAI Admin Credentials Reset Script
# This script resets the admin user credentials for development/testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

# Check if frontend is running
check_frontend() {
    if ! curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
        print_error "Frontend is not running. Please start it first:"
        echo "  cd frontend && npm run dev"
        exit 1
    fi
    print_success "Frontend is running"
}

# Reset admin credentials
reset_admin() {
    print_header " Resetting Admin Credentials"
    echo "========================================"

    cd frontend

    # Remove existing database
    print_status "Removing existing database..."
    rm -f db/custom.db

    # Reinitialize database
    print_status "Reinitializing database..."
    npm run db:push

    # Create new admin user
    print_status "Creating new admin user..."
    node setup-admin.js

    cd ..
    print_success "Admin credentials reset complete!"
}

# Main function
main() {
    echo "=========================================="
    echo "  InfraAI Admin Credentials Reset"
    echo "=========================================="
    echo ""

    print_warning "️  WARNING: This will delete all existing users and data!"
    echo "   Make sure you want to reset the admin credentials."
    echo ""

    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Operation cancelled."
        exit 0
    fi

    echo ""

    # Check prerequisites
    check_frontend

    # Reset admin credentials
    reset_admin

    # Print results
    echo ""
    echo "=========================================="
    echo "  RESET COMPLETE!"
    echo "=========================================="
    echo ""
    print_success " Admin credentials have been reset"
    echo ""
    echo " Frontend: http://localhost:3001"
    echo " New Admin Login:"
    echo "   Email: admin@infraai.com"
    echo "   Password: admin123"
    echo ""
    print_warning "Note: All existing user accounts have been removed"
    echo "      The first user to register will become the new admin"
    echo ""
    echo "=========================================="
}

# Run main function
main "$@"
