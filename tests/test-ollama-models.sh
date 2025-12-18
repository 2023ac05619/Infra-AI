#!/bin/bash
# InfraAI Ollama Models Test Script
# Tests all available Ollama models for inference capability

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
# Read Ollama URL from backend .env file
if [ -f "backend/.env" ]; then
    OLLAMA_URL=$(grep "^OLLAMA_API_URL=" backend/.env | cut -d'=' -f2)
else
    OLLAMA_URL="http://192.168.200.201:11434"
fi
TEST_PROMPT="Hello! Please respond with exactly one sentence describing what you are."

# Test counters
TOTAL_MODELS=0
WORKING_MODELS=0
FAILED_MODELS=0

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_failure() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

print_model() {
    echo -e "${CYAN}[MODEL]${NC} $1"
}

# Function to format file size
format_size() {
    local size=$1
    if [ $size -gt 1073741824 ]; then
        echo "$(( size / 1073741824 ))GB"
    elif [ $size -gt 1048576 ]; then
        echo "$(( size / 1048576 ))MB"
    elif [ $size -gt 1024 ]; then
        echo "$(( size / 1024 ))KB"
    else
        echo "${size}B"
    fi
}

# Function to test Ollama connectivity
test_ollama_connection() {
    print_status "Testing Ollama connectivity..."

    if ! curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        print_failure "Cannot connect to Ollama at $OLLAMA_URL"
        echo "Make sure Ollama is running: ollama serve"
        exit 1
    fi

    print_success "Ollama is accessible"
}

# Function to list available models
list_models() {
    print_header " Discovering Available Models"
    echo "========================================"

    local models_response=$(curl -s "$OLLAMA_URL/api/tags")

    if ! echo "$models_response" | jq -e '.models' > /dev/null 2>&1; then
        print_failure "Invalid response from Ollama API"
        echo "Response: $models_response"
        exit 1
    fi

    local model_count=$(echo "$models_response" | jq '.models | length')

    if [ "$model_count" -eq 0 ]; then
        print_warning "No models found in Ollama"
        echo "Pull some models first:"
        echo "  ollama pull llama3.1"
        echo "  ollama pull mistral"
        exit 1
    fi

    print_success "Found $model_count model(s)"

    # Display models in a table format
    echo ""
    printf "%-20s %-10s %-15s\n" "MODEL NAME" "SIZE" "MODIFIED"
    printf "%-20s %-10s %-15s\n" "--------------------" "----------" "---------------"

    echo "$models_response" | jq -r '.models[] | [.name, (.size | tostring), (.modified_at | split("T")[0])] | @tsv' | \
    while IFS=$'\t' read -r name size modified; do
        printf "%-20s %-10s %-15s\n" "$name" "$(format_size "$size")" "$modified"
    done

    echo ""
    TOTAL_MODELS=$model_count
}

# Function to test inference with a specific model
test_model_inference() {
    local model_name="$1"
    local model_size="$2"

    print_model "Testing inference: $model_name ($model_size)"

    # Prepare the request
    local request_data=$(cat <<EOF
{
  "model": "$model_name",
  "prompt": "$TEST_PROMPT",
  "stream": false,
  "options": {
    "temperature": 0.7,
    "num_predict": 100
  }
}
EOF
)

    # Make the inference request with timeout (increased to 60s for large models)
    local start_time=$(date +%s%3N)
    local response=$(timeout 60 curl -s -X POST "$OLLAMA_URL/api/generate" \
        -H "Content-Type: application/json" \
        -d "$request_data" 2>/dev/null)

    local end_time=$(date +%s%3N)
    local response_time=$((end_time - start_time))

    # Check if request timed out
    if [ $? -eq 124 ]; then
        print_failure "TIMEOUT: Model $model_name took too long to respond (>60s)"
        echo "  This may indicate insufficient RAM or slow loading"
        ((FAILED_MODELS++))
        return 1
    fi

    # Validate response
    if ! echo "$response" | jq -e '.response' > /dev/null 2>&1; then
        print_failure "INVALID RESPONSE: Model $model_name returned invalid JSON"
        echo "  Raw response preview: ${response:0:200}..."
        ((FAILED_MODELS++))
        return 1
    fi

    # Extract response content and metadata
    local model_response=$(echo "$response" | jq -r '.response // empty')
    local response_length=${#model_response}
    local total_duration=$(echo "$response" | jq -r '.total_duration // 0' | awk '{print int($1/1000000)}') # Convert to ms
    local load_duration=$(echo "$response" | jq -r '.load_duration // 0' | awk '{print int($1/1000000)}') # Convert to ms

    # Check if response is meaningful
    if [ $response_length -lt 5 ]; then
        print_failure "EMPTY RESPONSE: Model $model_name returned very short response (${response_length} chars)"
        echo "  Response: '$model_response'"
        ((FAILED_MODELS++))
        return 1
    fi

    # Success! Show detailed results
    print_success "SUCCESS: $model_name responded in ${response_time}ms"
    echo "   Response length: ${response_length} characters"
    if [ $total_duration -gt 0 ]; then
        echo "  ⏱️  Model load time: ${load_duration}ms"
        echo "   Total inference time: ${total_duration}ms"
    fi
    echo "   Response preview: ${model_response:0:120}..."

    # Special handling for code models
    if [[ "$model_name" == *"coder"* ]] || [[ "$model_name" == *"code"* ]]; then
        echo "   Specialized model detected - response may contain code"
    fi

    ((WORKING_MODELS++))
    return 0
}

# Function to test all models
test_all_models() {
    print_header " Testing Model Inference"
    echo "========================================"

    local models_response=$(curl -s "$OLLAMA_URL/api/tags")
    local tested_models=0

    echo "$models_response" | jq -r '.models[] | [.name, (.size | tostring)] | @tsv' | \
    while IFS=$'\t' read -r model_name model_size; do
        # Skip embedding models that don't support text generation
        if [[ "$model_name" == *"embed"* ]] || [[ "$model_name" == *"mxbai"* ]]; then
            print_warning "Skipping embedding model: $model_name (doesn't support text generation)"
            continue
        fi

        ((tested_models++))
        echo ""
        test_model_inference "$model_name" "$(format_size "$model_size")"
        # Small delay between tests to avoid overwhelming Ollama
        sleep 1
    done

    echo ""
    print_header " Inference Test Results"
    echo "========================================"
    echo "Models tested: $tested_models"
    echo -e "Working: ${GREEN}$WORKING_MODELS${NC}"
    echo -e "Failed: ${RED}$FAILED_MODELS${NC}"

    if [ $WORKING_MODELS -eq $tested_models ]; then
        print_success " ALL TEXT GENERATION MODELS WORKING CORRECTLY!"
    elif [ $WORKING_MODELS -gt 0 ]; then
        print_warning "️  SOME MODELS WORKING: $WORKING_MODELS/$tested_models functional"
    else
        print_failure " NO MODELS WORKING"
        return 1
    fi
}

# Function to show model recommendations
show_recommendations() {
    print_header " Model Recommendations"
    echo "========================================"

    local models_response=$(curl -s "$OLLAMA_URL/api/tags")

    echo "Based on your available models:"
    echo ""

    # Check for general purpose models
    if echo "$models_response" | jq -e '.models[] | select(.name | contains("llama3"))' > /dev/null 2>&1; then
        echo " General Purpose: Llama 3 models available"
    fi

    if echo "$models_response" | jq -e '.models[] | select(.name | contains("mistral"))' > /dev/null 2>&1; then
        echo " Fast Inference: Mistral models available"
    fi

    if echo "$models_response" | jq -e '.models[] | select(.name | contains("qwen"))' > /dev/null 2>&1; then
        echo " Multilingual: Qwen models available"
    fi

    if echo "$models_response" | jq -e '.models[] | select(.name | contains("sqlcoder") or contains("code"))' > /dev/null 2>&1; then
        echo " Code/Specialized: SQL/Coding models available"
    fi

    echo ""
    echo "For InfraAI, recommended models:"
    echo "  • llama3.1:latest - Best general purpose model"
    echo "  • mistral:latest - Fast and efficient"
    echo "  • qwen3:latest - Good multilingual support"
}

# Main function
main() {
    echo "=========================================="
    echo "  InfraAI Ollama Models Test Suite"
    echo "=========================================="
    echo ""

    # Test Ollama connectivity
    test_ollama_connection
    echo ""

    # List available models
    list_models

    # Test inference for all models
    test_all_models

    # Show recommendations
    echo ""
    show_recommendations

    # Final summary
    echo ""
    echo "=========================================="
    echo "  TEST SUMMARY"
    echo "=========================================="
    echo "Ollama Status:  Connected"
    echo "Models Available: $TOTAL_MODELS"
    echo -e "Models Working: ${GREEN}$WORKING_MODELS${NC}"
    echo -e "Models Failed: ${RED}$FAILED_MODELS${NC}"

    if [ $FAILED_MODELS -eq 0 ] && [ $WORKING_MODELS -gt 0 ]; then
        echo ""
        print_success " OLLAMA IS READY FOR INFRAI!"
        echo ""
        echo "You can now use any of the working models in your InfraAI backend."
        echo "Update your .env file with the desired model:"
        echo "  OLLAMA_MODEL=llama3.1:latest"
    else
        echo ""
        print_failure " OLLAMA NEEDS ATTENTION"
        echo ""
        echo "Some models failed testing. Check Ollama logs or try pulling different models."
        exit 1
    fi

    echo "=========================================="
}

# Run main function
main "$@"
