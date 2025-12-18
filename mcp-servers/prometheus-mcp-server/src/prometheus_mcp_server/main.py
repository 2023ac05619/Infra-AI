#!/usr/bin/env python
import sys
import uvicorn
import dotenv
from prometheus_mcp_server.server import config, server_config
from prometheus_mcp_server.logging_config import setup_logging

# Initialize structured logging
logger = setup_logging()

def setup_environment():
    if dotenv.load_dotenv():
        logger.info("Environment configuration loaded", source=".env file")
    else:
        logger.info("Environment configuration loaded", source="environment variables", note="No .env file found")

    if not config.url:
        logger.error(
            "Missing required configuration",
            error="PROMETHEUS_URL environment variable is not set",
            suggestion="Please set it to your Prometheus server URL",
            example="http://your-prometheus-server:9090"
        )
        return False

    logger.info(
        "Prometheus configuration validated",
        server_url=config.url
    )

    return True

def run_server():
    """Main entry point for the Prometheus JSON-RPC Server"""
    # Setup environment
    if not setup_environment():
        logger.error("Environment setup failed, exiting")
        sys.exit(1)

    logger.info("Starting Prometheus JSON-RPC Server",
            host=server_config.bind_host,
            port=server_config.bind_port)

    # Start FastAPI server with uvicorn
    uvicorn.run(
        "prometheus_mcp_server.server:app",
        host=server_config.bind_host,
        port=server_config.bind_port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    run_server()
