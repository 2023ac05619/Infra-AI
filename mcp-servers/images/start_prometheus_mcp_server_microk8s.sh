#!/bin/bash

# This script starts the Prometheus MCP server configured to connect to
# the Prometheus instance running in the microk8s cluster via NodePort 30909

# Configuration
PROMETHEUS_NODE_IP="192.168.203.103"
PROMETHEUS_NODEPORT="30909"
PROMETHEUS_URL="http://${PROMETHEUS_NODE_IP}:${PROMETHEUS_NODEPORT}"
CONTAINER_NAME="prometheus-mcp-server-microk8s"
IMAGE="prometheus-mcp-server:latest"

start() {
    echo "Starting Prometheus MCP server connected to microk8s Prometheus..."
    echo "Prometheus URL: ${PROMETHEUS_URL}"

    # Test Prometheus connectivity before starting
    echo "Testing Prometheus connectivity..."
    if curl -s "${PROMETHEUS_URL}/-/healthy" | grep -q "Prometheus Server is Healthy"; then
        echo " Prometheus is accessible and healthy"
    else
        echo " Prometheus is not accessible at ${PROMETHEUS_URL}"
        echo "Please ensure microk8s is running and the prometheus-service NodePort is available"
        exit 1
    fi

    # Check if container already exists
    if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "Container ${CONTAINER_NAME} already exists. Removing it first..."
        docker stop "${CONTAINER_NAME}" >/dev/null 2>&1
        docker rm "${CONTAINER_NAME}" >/dev/null 2>&1
    fi

    # Start the Prometheus MCP server
    echo "Starting container ${CONTAINER_NAME}..."
    docker run -d \
        --name "${CONTAINER_NAME}" \
        -e PROMETHEUS_URL="${PROMETHEUS_URL}" \
        -e PROMETHEUS_BIND_HOST="0.0.0.0" \
        -p 8080:8080 \
        "${IMAGE}"

    if [ $? -eq 0 ]; then
        echo " Prometheus MCP server started successfully"
        echo "  Container: ${CONTAINER_NAME}"
        echo "  Local access: http://localhost:8080"
        echo "  Health check: http://localhost:8080/health"
        echo "  JSON-RPC endpoint: http://localhost:8080/jsonrpc"

        # Wait a moment for the container to start
        sleep 2

        # Test the MCP server health
        echo "Testing MCP server health..."
        if curl -s http://localhost:8080/health | grep -q '"status": "healthy"'; then
            echo " MCP server is healthy and connected to Prometheus"
        else
            echo " MCP server started but health check failed"
            echo "Check logs with: docker logs ${CONTAINER_NAME}"
        fi
    else
        echo " Failed to start Prometheus MCP server"
        exit 1
    fi
}

stop() {
    echo "Stopping Prometheus MCP server..."
    if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker stop "${CONTAINER_NAME}" >/dev/null 2>&1
        docker rm "${CONTAINER_NAME}" >/dev/null 2>&1
        echo " Prometheus MCP server stopped and removed"
    else
        echo "Container ${CONTAINER_NAME} not found"
    fi
}

status() {
    echo "Checking Prometheus MCP server status..."
    if docker ps --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo " Container ${CONTAINER_NAME} is running"

        # Check if the service is responding
        if curl -s http://localhost:8080/health >/dev/null 2>&1; then
            echo " MCP server is responding on http://localhost:8080"
        else
            echo " Container is running but service is not responding"
        fi
    else
        echo " Container ${CONTAINER_NAME} is not running"
    fi

    echo ""
    echo "Prometheus connectivity:"
    if curl -s "${PROMETHEUS_URL}/-/healthy" | grep -q "Prometheus Server is Healthy"; then
        echo " Prometheus is accessible at ${PROMETHEUS_URL}"
    else
        echo " Prometheus is not accessible at ${PROMETHEUS_URL}"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the Prometheus MCP server"
        echo "  stop    - Stop and remove the Prometheus MCP server"
        echo "  status  - Check the status of both MCP server and Prometheus"
        echo "  restart - Restart the Prometheus MCP server"
        echo ""
        echo "Configuration:"
        echo "  Prometheus URL: ${PROMETHEUS_URL}"
        echo "  Container name: ${CONTAINER_NAME}"
        echo "  Local port: 8080"
        exit 1
esac
