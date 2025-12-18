#!/bin/bash

# This script starts and stops the ESXi MCP HTTP JSON-RPC server.
# No authentication, no sessions - pure stateless HTTP JSON-RPC

# Configuration for ESXi server
VCENTER_HOST="192.168.203.178"
VCENTER_USER="root"
VCENTER_PASSWORD="TempP@ssw0rd"
CONTAINER_NAME="esxi-mcp-server"
IMAGE="esxi-mcp-server:latest"

echo " Using ESXi credentials: ${VCENTER_USER}@${VCENTER_HOST}"

start() {
    echo "Checking for ESXi MCP server image..."
    if ! docker images | grep -q "esxi-mcp-server"; then
        echo "Building ESXi MCP server image..."
        if [ -d "esxi-mcp-server" ]; then
            docker build -t esxi-mcp-server ./esxi-mcp-server
        else
            echo " Error: esxi-mcp-server directory not found and image not available"
            exit 1
        fi
    else
        echo " Using existing esxi-mcp-server image"
    fi

    echo "Testing ESXi connectivity at ${VCENTER_HOST}..."
    # Simple connectivity test - try to connect to ESXi host
    if timeout 10 bash -c "</dev/tcp/${VCENTER_HOST}/443" 2>/dev/null; then
        echo " ESXi host is reachable at ${VCENTER_HOST}"
    else
        echo " ESXi host is not reachable at ${VCENTER_HOST}"
        echo "Please ensure ESXi server is running and accessible"
        exit 1
    fi

    echo "Starting the ESXi MCP server using docker run..."
    docker run -d --name "${CONTAINER_NAME}" \
      -p 8090:8090 \
      -v "$(pwd)/esxi_config.yaml:/app/config/config.yaml:ro" \
      -v "$(pwd)/logs:/app/logs" \
      -e VCENTER_HOST="${VCENTER_HOST}" \
      -e VCENTER_USER="${VCENTER_USER}" \
      -e VCENTER_PASSWORD="${VCENTER_PASSWORD}" \
      -e VCENTER_DATACENTER="" \
      -e VCENTER_CLUSTER="" \
      -e VCENTER_DATASTORE="" \
      -e VCENTER_NETWORK="VM Network" \
      -e VCENTER_INSECURE=true \
      -e MCP_LOG_LEVEL=DEBUG \
      -e MCP_PORT=8090 \
      ${IMAGE}
}

stop() {
    echo "Stopping the ESXi MCP HTTP server..."
    docker stop "${CONTAINER_NAME}"
    docker rm "${CONTAINER_NAME}"
}

restart() {
    stop
    sleep 2
    start
}

status() {
    echo "Checking ESXi MCP server status..."
    if docker ps --filter "name=${CONTAINER_NAME}" --filter "status=running" | grep -q "${CONTAINER_NAME}"; then
        echo " ESXi MCP server is running"
        docker ps --filter "name=${CONTAINER_NAME}"
    else
        echo " ESXi MCP server is not running"
        if docker ps -a --filter "name=${CONTAINER_NAME}" | grep -q "${CONTAINER_NAME}"; then
            echo "Container exists but is stopped:"
            docker ps -a --filter "name=${CONTAINER_NAME}"
        fi
    fi
}

logs() {
    echo "Showing ESXi MCP server logs..."
    docker logs -f "${CONTAINER_NAME}"
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
esac
