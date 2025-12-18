#!/bin/bash

# This script starts and stops the Grafana MCP HTTP JSON-RPC server.
# No authentication, no sessions - pure stateless HTTP JSON-RPC

# Configuration for Grafana running in microk8s cluster
GRAFANA_NODE_IP="192.168.203.103"
GRAFANA_NODEPORT="30300"
GRAFANA_URL="http://${GRAFANA_NODE_IP}:${GRAFANA_NODEPORT}"
GRAFANA_USERNAME="admin"
GRAFANA_PASSWORD="admin"
CONTAINER_NAME="grafana-mcp-server"
IMAGE="grafana-mcp-server:latest"

echo " Using Grafana admin/admin credentials"

start() {
    echo "Building Grafana MCP server image..."
    docker build -t grafana-mcp-server ./grafana-mcp-server

    echo "Testing Grafana connectivity at ${GRAFANA_URL}..."
    if curl -s "${GRAFANA_URL}/api/health" | grep -q '"database": "ok"'; then
        echo " Grafana is accessible and healthy"
    else
        echo " Grafana is not accessible at ${GRAFANA_URL}"
        echo "Please ensure Grafana is running in microk8s cluster with NodePort ${GRAFANA_NODEPORT}"
        exit 1
    fi

    echo "Starting the Grafana MCP server..."
    docker run -d --name "${CONTAINER_NAME}" \
      -p 8000:8000 \
      -e GRAFANA_URL="${GRAFANA_URL}" \
      -e GRAFANA_USERNAME="${GRAFANA_USERNAME}" \
      -e GRAFANA_PASSWORD="${GRAFANA_PASSWORD}" \
      ${IMAGE}
}

stop() {
    echo "Stopping the Grafana MCP HTTP server..."
    docker stop "${CONTAINER_NAME}"
    docker rm "${CONTAINER_NAME}"
}

restart() {
    stop
    sleep 2
    start
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
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
esac
