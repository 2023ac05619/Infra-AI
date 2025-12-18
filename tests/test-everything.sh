#!/bin/bash
# InfraAI Complete Test Suite Runner
# Runs all validation tests for the complete application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test results
OVERALL_TOTAL=0
OVERALL_PASSED=0
OVERALL_FAILED=0

# Function to print colored output
print_header() {
    echo -e "${PURPLE}$1${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_failure() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Function to run a test suite
run_test_suite() {
    local suite_name="$1"
    local script_path="$2"

    print_header " Running $suite_name Tests"
    echo "========================================"

    if [ -f "$script_path" ]; then
        # Capture the exit code and output
        set +e
        output=$($script_path 2>&1)
        exit_code=$?
        set -e

        echo "$output"
        echo ""

        # Parse results from output (this is a simple approach)
        if echo "$output" | grep -q "ALL.*TESTS PASSED"; then
            print_success "$suite_name: All tests passed"
            return 0
        elif echo "$output" | grep -q "TESTS PASSED"; then
            # Extract numbers if possible
            passed=$(echo "$output" | grep "Passed:" | sed 's/.*Passed:.*\([0-9]*\).*/\1/')
            failed=$(echo "$output" | grep "Failed:" | sed 's/.*Failed:.*\([0-9]*\).*/\1/')

            if [ -n "$passed" ] && [ -n "$failed" ]; then
                OVERALL_PASSED=$((OVERALL_PASSED + passed))
                OVERALL_FAILED=$((OVERALL_FAILED + failed))
                OVERALL_TOTAL=$((OVERALL_TOTAL + passed + failed))

                if [ "$failed" -eq 0 ]; then
                    print_success "$suite_name: $passed tests passed"
                else
                    print_failure "$suite_name: $passed passed, $failed failed"
                fi
            else
                print_status "$suite_name: Completed (results parsed)"
            fi
            return 0
        else
            print_failure "$suite_name: Tests failed or incomplete"
            return 1
        fi
    else
        print_failure "$suite_name: Test script not found at $script_path"
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_header " Checking Prerequisites"
    echo "========================================"

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_failure "Docker is not running. Please start Docker first."
        exit 1
    fi
    print_success "Docker is running"

    # Check if backend is running
    if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
        print_failure "Backend is not running. Please start with: ./setup-complete-app.sh"
        exit 1
    fi
    print_success "Backend is accessible"

    # Check if frontend is running
    if ! curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
        print_failure "Frontend is not running. Please start with: ./setup-complete-app.sh"
        exit 1
    fi
    print_success "Frontend is accessible"

    echo ""
}

# Main test execution
main() {
    echo "=========================================="
    echo "  InfraAI Complete Test Suite"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_prerequisites

    # Run individual test suites
    run_test_suite "Ollama Models" "tests/test-ollama-models.sh"
    echo ""

    run_test_suite "Complete Integration" "tests/test-complete-integration.sh"
    echo ""

    run_test_suite "Backend API" "tests/test-backend-apis.sh"
    echo ""

    run_test_suite "Frontend" "tests/test-frontend.sh"
    echo ""

    # Final summary
    echo "=========================================="
    echo "  FINAL TEST RESULTS SUMMARY"
    echo "=========================================="

    if [ "$OVERALL_TOTAL" -gt 0 ]; then
        echo "Parsed Test Results:"
        echo "Total Tests: $OVERALL_TOTAL"
        echo -e "Passed: ${GREEN}$OVERALL_PASSED${NC}"
        echo -e "Failed: ${RED}$OVERALL_FAILED${NC}"
        echo ""
    fi

    # Overall assessment
    if [ "$OVERALL_FAILED" -eq 0 ] && [ "$OVERALL_TOTAL" -gt 0 ]; then
        print_success " ALL TESTS PASSED!"
        echo ""
        echo "InfraAI Application Status:  FULLY OPERATIONAL"
        echo ""
        echo " Frontend (InfraChat): http://localhost:3001"
        echo " Backend (InfraAI API): http://localhost:8001"
        echo " Default Login: admin@infraai.com / admin123"
        echo " API Docs: http://localhost:8001/docs"
        echo ""
        echo " Services: PostgreSQL, Redis, Ollama"
        echo " Databases: Initialized and populated"
        echo " Authentication: Working"
        echo " Chat Integration: Functional"
        echo " Self-Healing Policies: Active"
        echo " Network Discovery: Ready"
    else
        print_failure " SOME TESTS FAILED"
        echo ""
        echo "Please check the output above for failed tests."
        echo "Common issues:"
        echo "  - Services not running: Run ./setup-complete-app.sh"
        echo "  - Database issues: Check Docker containers"
        echo "  - Network issues: Verify localhost connectivity"
        exit 1
    fi

    echo "=========================================="
}

# Run main function
main "$@"
