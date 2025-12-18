#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
SERVER_DIR="${SCRIPT_DIR}/mcp-server-kubernetes"
CONTAINER_NAME="kubernetes-mcp-server"
IMAGE_NAME="kubernetes-mcp-server-image:latest"

start() {
    # Navigate to the mcp-server-kubernetes directory
    # cd "${SERVER_DIR}" || { echo "Failed to change directory to ${SERVER_DIR}" >&2; exit 1; }

    echo "Checking for Kubernetes MCP server image..."
    if ! docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "${IMAGE_NAME}"; then
        echo "Building Kubernetes MCP server Docker image..."
        docker build -t "${IMAGE_NAME}" .
    else
        echo " Using existing ${IMAGE_NAME} image"
    fi

    echo "Starting Kubernetes MCP server in a Docker container..."
    docker run -d --name "${CONTAINER_NAME}" \
      -p 8082:8082 \
      -e ENABLE_UNSAFE_SSE_TRANSPORT=true \
      -e HOST=0.0.0.0 \
      -e PORT=8082 \
      -e KUBECONFIG=/home/appuser/.kube/config \
      --user root \
      -v ~/.kube:/home/appuser/.kube:ro \
      "${IMAGE_NAME}"

    echo "Kubernetes MCP server started in the background. Container name: ${CONTAINER_NAME}"
}

stop() {
    echo "Stopping Kubernetes MCP server container..."
    docker stop "${CONTAINER_NAME}" > /dev/null 2>&1
    docker rm "${CONTAINER_NAME}" > /dev/null 2>&1
    echo "Kubernetes MCP server container stopped and removed."
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
esac
