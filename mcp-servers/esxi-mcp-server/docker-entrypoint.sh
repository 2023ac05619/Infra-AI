#!/bin/bash

# Docker entrypoint script for ESXi MCP Server
set -e

# Function to wait for configuration file
wait_for_config() {
    local config_file="/app/config/config.yaml"
    local max_wait=30
    local count=0
    
    echo "Waiting for configuration file..."
    while [ ! -f "$config_file" ] && [ $count -lt $max_wait ]; do
        echo "Configuration file not found, waiting... ($count/$max_wait)"
        sleep 2
        count=$((count + 1))
    done
    
    if [ ! -f "$config_file" ]; then
        echo "Warning: Configuration file not found. Using environment variables."
        return 1
    fi
    
    echo "Configuration file found: $config_file"
    return 0
}

# Main execution
echo "Starting ESXi MCP Server..."

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Check if configuration file exists
wait_for_config


# Print configuration info (without sensitive data)
echo "Server starting with configuration:"
echo "  Host: ${VCENTER_HOST:-'from config file'}"
echo "  User: ${VCENTER_USER:-'from config file'}"
echo "  Log Level: ${MCP_LOG_LEVEL:-INFO}"
echo "  Port: ${MCP_PORT:-8090}"

# Execute the command passed to the container
exec "$@"
