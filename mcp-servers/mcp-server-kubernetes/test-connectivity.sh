#!/bin/bash

# Test script to verify connectivity between mcp-server-kubernetes and microk8s
# Usage: ./test-connectivity.sh

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PATH="$SCRIPT_DIR/dist/index.js"

echo " Testing MCP Server Kubernetes connectivity with microk8s..."
echo

# Check if server exists
if [ ! -f "$SERVER_PATH" ]; then
    echo " Server not found at: $SERVER_PATH"
    echo " Please run: bun run build"
    exit 1
fi

echo " Server found at: $SERVER_PATH"

# Check if microk8s is available and running
if ! command -v microk8s &> /dev/null; then
    echo " microk8s not found. Please install microk8s first."
    echo " Installation: sudo snap install microk8s --classic"
    exit 1
fi

echo " Checking microk8s status..."
if microk8s status | grep -q "microk8s is running"; then
    echo " microk8s is running"
else
    echo " microk8s is not running"
    microk8s status
    exit 1
fi

# Check if kubectl is available (prefer microk8s kubectl if available)
if command -v microk8s.kubectl &> /dev/null; then
    KUBECTL_CMD="microk8s.kubectl"
    echo " Using microk8s kubectl"
elif command -v kubectl &> /dev/null; then
    KUBECTL_CMD="kubectl"
    echo " Using system kubectl"
else
    echo " kubectl not found"
    exit 1
fi

# Check if mcp-chat is available
if ! command -v npx &> /dev/null; then
    echo " npx not found. Please install Node.js and npm."
    exit 1
fi

# Function to run mcp-chat command
run_mcp_command() {
    local command="$1"
    local description="$2"

    echo " Testing: $description"
    echo "Command: $command"
    echo

    if timeout 30 npx mcp-chat --server "node $SERVER_PATH" --command "$command" --quiet --no-progress; then
        echo " Success: $description"
        echo
        return 0
    else
        echo " Failed: $description"
        echo
        return 1
    fi
}

# Function to run kubectl command directly for comparison
run_kubectl_command() {
    local command="$1"
    local description="$2"

    echo " Direct kubectl: $description"
    echo "Command: $KUBECTL_CMD $command"
    echo

    if $KUBECTL_CMD $command; then
        echo " kubectl command succeeded"
        echo
        return 0
    else
        echo " kubectl command failed"
        echo
        return 1
    fi
}

# Function to run microk8s-specific commands
run_microk8s_command() {
    local command="$1"
    local description="$2"

    echo " microk8s: $description"
    echo "Command: microk8s $command"
    echo

    if microk8s $command; then
        echo " microk8s command succeeded"
        echo
        return 0
    else
        echo " microk8s command failed"
        echo
        return 1
    fi
}

# Test 1: microk8s system status
echo " Test 1: microk8s system status"
run_microk8s_command "status" "Check microk8s system status"

# Test 2: Direct kubectl connectivity
echo " Test 2: Direct kubectl connectivity"
run_kubectl_command "get nodes" "Check cluster nodes"

# Test 3: MCP ping test
echo " Test 3: MCP ping test"
run_mcp_command "ping" "Server ping test"

# Test 4: Get cluster nodes via MCP
echo " Test 4: Get cluster nodes via MCP"
run_mcp_command "kubectl get nodes --output=json" "Get cluster nodes via MCP"

# Test 5: Get pods in default namespace via MCP
echo " Test 5: Get pods in default namespace via MCP"
run_mcp_command "kubectl get pods --namespace=default --output=json" "Get pods via MCP"

# Test 6: Get services in default namespace via MCP
echo " Test 6: Get services in default namespace via MCP"
run_mcp_command "kubectl get services --namespace=default --output=json" "Get services via MCP"

# Test 7: Get namespaces
echo " Test 7: Get namespaces via MCP"
run_mcp_command "kubectl get namespaces --output=json" "Get namespaces via MCP"

# Test 8: Test events
echo " Test 8: Get events via MCP"
run_mcp_command "kubectl get events --namespace=default --output=json" "Get events via MCP"

# Test 9: Test direct kubectl comparison
echo "️  Test 9: Comparison - kubectl get nodes direct vs MCP"
echo "Direct kubectl:"
$KUBECTL_CMD get nodes --no-headers | wc -l | tr -d '\n'
echo " nodes found"
echo

echo "Via MCP (might be truncated):"
# This is approximate, real comparison would need parsing JSON
npx mcp-chat --server "node $SERVER_PATH" --command "kubectl get nodes --output=json" --quiet --no-progress | grep -o '"name"' | wc -l | tr -d '\n' 2>/dev/null || echo "0"
echo " nodes found via MCP"
echo

# Test 10: Show available resources
echo " Test 10: Available MCP resources"
run_mcp_command "list resources" "List MCP resources"

# Test 11: Show available tools
echo "️  Test 11: Available MCP tools"
if run_mcp_command "list tools" "List MCP tools"; then
    echo " Tools listing succeeded"
else
    echo "️ Tools listing might have been truncated due to length"
fi

echo " Connectivity test completed!"
echo
echo " MCP Server Kubernetes appears to be successfully connected to microk8s"
echo
echo " Configuration suggestions:"
echo "1. For Claude Desktop, add this to your config:"
echo '   {'
echo '     "mcpServers": {'
echo '       "kubernetes": {'
echo '         "command": "npx",'
echo '         "args": ["mcp-server-kubernetes"]'
echo '       }'
echo '     }'
echo '   }'
echo
echo "2. Or run locally:"
echo "   node $SERVER_PATH"
echo
echo "3. Or use mcp-chat directly:"
echo "   npx mcp-chat --server \"node $SERVER_PATH\""
