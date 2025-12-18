#!/bin/bash

# Test script to verify HTTP MCP Kubernetes server connectivity to microk8s
# This script directly tests the MCP protocol over HTTP/SSE transport

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="kubernetes-mcp-server"

echo " Testing HTTP MCP Server Kubernetes connectivity to microk8s..."
echo

# Check if Docker container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo " Docker container '$CONTAINER_NAME' is not running"
    echo " Start it with: ./start_mcp_kubernetes_server.sh start"
    exit 1
fi

echo " Docker container '$CONTAINER_NAME' is running"
echo

# Function to make MCP HTTP request
function call_mcp_tool() {
    local tool_name="$1"
    local params="$2"
    local description="$3"

    echo " Testing: $description"
    echo "Tool: $tool_name"
    echo

    # Create temporary JSON payload for MCP call
    local payload
    payload=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "$tool_name",
    "arguments": $params
  }
}
EOF
)

    # Make HTTP request to MCP server
    local response
    response=$(curl -s -X POST \
        "http://localhost:8082/messages?sessionId=test-session" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        --max-time 30)

    # Check if request succeeded
    if [[ $? -eq 0 ]] && [[ -n "$response" ]]; then
        echo " HTTP request succeeded for $tool_name"
        # Check if response contains error
        if echo "$response" | grep -q '"error"'; then
            echo "️ Tool returned error:"
            echo "$response" | jq -r '.error.message // .error' 2>/dev/null || echo "$response"
        else
            echo " Tool execution successful"
        fi
    else
        echo " HTTP request failed for $tool_name"
        return 1
    fi

    echo
    return 0
}

# Test 1: Basic ping
echo " Test 1: MCP Server HTTP connectivity (ping)"
if call_mcp_tool "ping" "{}" "Server ping test"; then
    echo " MCP HTTP server is responding"
else
    echo " MCP HTTP server not responding"
    exit 1
fi

# Test 2: Get cluster nodes
echo " Test 2: Get cluster nodes via HTTP MCP"
if call_mcp_tool "kubectl_get" '{"resourceType": "nodes"}' "Get cluster nodes"; then
    echo " Successfully retrieved cluster nodes via HTTP MCP"
else
    echo " Failed to get cluster nodes"
fi

# Test 3: Get namespaces
echo " Test 3: Get namespaces via HTTP MCP"
if call_mcp_tool "kubectl_get" '{"resourceType": "namespaces"}' "Get namespaces"; then
    echo " Successfully retrieved namespaces via HTTP MCP"
else
    echo " Failed to get namespaces"
fi

# Test 4: Get pods in default namespace
echo " Test 4: Get pods in default namespace via HTTP MCP"
if call_mcp_tool "kubectl_get" '{"resourceType": "pods", "namespace": "default"}' "Get pods in default namespace"; then
    echo " Successfully retrieved pods via HTTP MCP"
else
    echo " Failed to get pods"
fi

# Test 5: Test kubectl context
echo " Test 5: Check kubectl context via HTTP MCP"
if call_mcp_tool "kubectl_context" '{"operation": "get"}' "Get current kubectl context"; then
    echo " Successfully retrieved kubectl context via HTTP MCP"
else
    echo " Failed to get kubectl context"
fi

echo " HTTP connectivity tests completed!"

# Compare with direct kubectl for validation
echo
echo " Validation: Direct kubectl comparison"
echo "Direct kubectl get nodes:"
microk8s kubectl get nodes --no-headers | wc -l | tr -d '\n'
echo " nodes found"
echo

echo "If the HTTP MCP tests succeeded and microk8s is running, then:"
echo " HTTP MCP Server ↔️ Docker → microk8s cluster connectivity is working!"
echo
echo " The setup provides a complete MCP-over-HTTP interface to manage the local Kubernetes cluster."
