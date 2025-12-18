#!/usr/bin/env python

import os
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import time
from datetime import datetime

import dotenv
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_mcp_server.logging_config import get_logger

dotenv.load_dotenv()

# Create FastAPI app
app = FastAPI(title="Prometheus JSON-RPC Server", version="1.5.1")

# Cache for metrics list to improve completion performance
_metrics_cache = {"data": None, "timestamp": 0}
_CACHE_TTL = 300  # 5 minutes

# Get logger instance
logger = get_logger()

# JSON-RPC Models
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Return health status of the server and Prometheus connection.

    Returns:
        Health status including service information, configuration, and connectivity
    """
    try:
        health_status = {
            "status": "healthy",
            "service": "prometheus-jsonrpc-server",
            "version": "1.5.1",
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": {
                "prometheus_url_configured": bool(config.url)
            }
        }

        # Test Prometheus connectivity if configured
        if config.url:
            try:
                # Quick connectivity test
                make_prometheus_request("query", params={"query": "up", "time": str(int(time.time()))})
                health_status["prometheus_connectivity"] = "healthy"
                health_status["prometheus_url"] = config.url
            except Exception as e:
                health_status["prometheus_connectivity"] = "unhealthy"
                health_status["prometheus_error"] = str(e)
                health_status["status"] = "degraded"
        else:
            health_status["status"] = "unhealthy"
            health_status["error"] = "PROMETHEUS_URL not configured"

        logger.info("Health check completed", status=health_status["status"])
        return health_status

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "prometheus-jsonrpc-server",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# JSON-RPC endpoint
@app.post("/jsonrpc")
async def jsonrpc_endpoint(request: JSONRPCRequest) -> JSONRPCResponse:
    """Handle JSON-RPC requests"""
    try:
        # Validate JSON-RPC version
        if request.jsonrpc != "2.0":
            return JSONRPCResponse(
                error={"code": -32600, "message": "Invalid Request: JSON-RPC version must be 2.0"},
                id=request.id
            )

        # Route to appropriate method
        method_name = request.method
        params = request.params or {}

        if method_name == "health_check":
            result = await health_check_method()
        elif method_name == "execute_query":
            result = await execute_query_method(**params)
        elif method_name == "execute_range_query":
            result = await execute_range_query_method(**params)
        elif method_name == "list_metrics":
            result = await list_metrics_method(**params)
        elif method_name == "get_metric_metadata":
            result = await get_metric_metadata_method(**params)
        elif method_name == "get_targets":
            result = await get_targets_method(**params)
        else:
            return JSONRPCResponse(
                error={"code": -32601, "message": f"Method not found: {method_name}"},
                id=request.id
            )

        return JSONRPCResponse(result=result, id=request.id)

    except Exception as e:
        logger.error("JSON-RPC request failed", method=request.method, error=str(e))
        return JSONRPCResponse(
            error={"code": -32603, "message": f"Internal error: {str(e)}"},
            id=request.id
        )

# Method implementations
async def health_check_method() -> Dict[str, Any]:
    """Health check method"""
    return await health_check()

async def execute_query_method(query: str, time: Optional[str] = None) -> Dict[str, Any]:
    """Execute an instant query against Prometheus.

    Args:
        query: PromQL query string
        time: Optional RFC3339 or Unix timestamp (default: current time)

    Returns:
        Query result with type (vector, matrix, scalar, string) and values
    """
    params = {"query": query}
    if time:
        params["time"] = time

    logger.info("Executing instant query", query=query, time=time)
    data = make_prometheus_request("query", params=params)

    result = {
        "resultType": data["resultType"],
        "result": data["result"]
    }

    if not config.disable_prometheus_links:
        from urllib.parse import urlencode
        ui_params = {"g0.expr": query, "g0.tab": "0"}
        if time:
            ui_params["g0.moment_input"] = time
        prometheus_ui_link = f"{config.url.rstrip('/')}/graph?{urlencode(ui_params)}"
        result["links"] = [{
            "href": prometheus_ui_link,
            "rel": "prometheus-ui",
            "title": "View in Prometheus UI"
        }]

    logger.info("Instant query completed",
                query=query,
                result_type=data["resultType"],
                result_count=len(data["result"]) if isinstance(data["result"], list) else 1)

    return result

async def execute_range_query_method(query: str, start: str, end: str, step: str) -> Dict[str, Any]:
    """Execute a range query against Prometheus.

    Args:
        query: PromQL query string
        start: Start time as RFC3339 or Unix timestamp
        end: End time as RFC3339 or Unix timestamp
        step: Query resolution step width (e.g., '15s', '1m', '1h')

    Returns:
        Range query result with type (usually matrix) and values over time
    """
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": step
    }

    logger.info("Executing range query", query=query, start=start, end=end, step=step)

    data = make_prometheus_request("query_range", params=params)

    result = {
        "resultType": data["resultType"],
        "result": data["result"]
    }

    if not config.disable_prometheus_links:
        from urllib.parse import urlencode
        ui_params = {
            "g0.expr": query,
            "g0.tab": "0",
            "g0.range_input": f"{start} to {end}",
            "g0.step_input": step
        }
        prometheus_ui_link = f"{config.url.rstrip('/')}/graph?{urlencode(ui_params)}"
        result["links"] = [{
            "href": prometheus_ui_link,
            "rel": "prometheus-ui",
            "title": "View in Prometheus UI"
        }]

    logger.info("Range query completed",
                query=query,
                result_type=data["resultType"],
                result_count=len(data["result"]) if isinstance(data["result"], list) else 1)

    return result

async def list_metrics_method(
    limit: Optional[int] = None,
    offset: int = 0,
    filter_pattern: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a list of all metric names available in Prometheus.

    Args:
        limit: Maximum number of metrics to return (default: all metrics)
        offset: Number of metrics to skip for pagination (default: 0)
        filter_pattern: Optional substring to filter metric names (case-insensitive)

    Returns:
        Dictionary containing:
        - metrics: List of metric names
        - total_count: Total number of metrics (before pagination)
        - returned_count: Number of metrics returned
        - offset: Current offset
        - has_more: Whether more metrics are available
    """
    logger.info("Listing available metrics", limit=limit, offset=offset, filter_pattern=filter_pattern)

    data = make_prometheus_request("label/__name__/values")

    # Apply filter if provided
    if filter_pattern:
        filtered_data = [m for m in data if filter_pattern.lower() in m.lower()]
        logger.debug("Applied filter", original_count=len(data), filtered_count=len(filtered_data), pattern=filter_pattern)
        data = filtered_data

    total_count = len(data)

    # Apply pagination
    start_idx = offset
    end_idx = offset + limit if limit is not None else len(data)
    paginated_data = data[start_idx:end_idx]

    result = {
        "metrics": paginated_data,
        "total_count": total_count,
        "returned_count": len(paginated_data),
        "offset": offset,
        "has_more": end_idx < total_count
    }

    logger.info("Metrics list retrieved",
                total_count=total_count,
                returned_count=len(paginated_data),
                offset=offset,
                has_more=result["has_more"])

    return result

async def get_metric_metadata_method(metric: str) -> List[Dict[str, Any]]:
    """Get metadata about a specific metric.

    Args:
        metric: The name of the metric to retrieve metadata for

    Returns:
        List of metadata entries for the metric
    """
    logger.info("Retrieving metric metadata", metric=metric)
    endpoint = f"metadata?metric={metric}"
    data = make_prometheus_request(endpoint, params=None)
    if "metadata" in data:
        metadata = data["metadata"]
    elif "data" in data:
        metadata = data["data"]
    else:
        metadata = data
    if isinstance(metadata, dict):
        metadata = [metadata]
    logger.info("Metric metadata retrieved", metric=metric, metadata_count=len(metadata))
    return metadata

async def get_targets_method() -> Dict[str, List[Dict[str, Any]]]:
    """Get information about all Prometheus scrape targets.

    Returns:
        Dictionary with active and dropped targets information
    """
    logger.info("Retrieving scrape targets information")
    data = make_prometheus_request("targets")

    result = {
        "activeTargets": data["activeTargets"],
        "droppedTargets": data["droppedTargets"]
    }

    logger.info("Scrape targets retrieved",
                active_targets=len(data["activeTargets"]),
                dropped_targets=len(data["droppedTargets"]))

    return result

@dataclass
class ServerConfig:
    """Global Configuration for the server."""
    bind_host: str = "127.0.0.1"
    bind_port: int = 8080

@dataclass
class PrometheusConfig:
    url: str
    url_ssl_verify: bool = True
    disable_prometheus_links: bool = False

config = PrometheusConfig(
    url=os.environ.get("PROMETHEUS_URL", ""),
    url_ssl_verify=os.environ.get("PROMETHEUS_URL_SSL_VERIFY", "True").lower() in ("true", "1", "yes"),
    disable_prometheus_links=os.environ.get("PROMETHEUS_DISABLE_LINKS", "False").lower() in ("true", "1", "yes"),
)

server_config = ServerConfig(
    bind_host=os.environ.get("PROMETHEUS_BIND_HOST", "127.0.0.1"),
    bind_port=int(os.environ.get("PROMETHEUS_BIND_PORT", "8080"))
)

def make_prometheus_request(endpoint, params=None):
    """Make a request to the Prometheus API."""
    if not config.url:
        logger.error("Prometheus configuration missing", error="PROMETHEUS_URL not set")
        raise ValueError("Prometheus configuration is missing. Please set PROMETHEUS_URL environment variable.")
    if not config.url_ssl_verify:
        logger.warning("SSL certificate verification is disabled. This is insecure and should not be used in production environments.", endpoint=endpoint)

    url = f"{config.url.rstrip('/')}/api/v1/{endpoint}"

    try:
        logger.debug("Making Prometheus API request", endpoint=endpoint, url=url, params=params)

        # Make the request
        response = requests.get(url, params=params, verify=config.url_ssl_verify)

        response.raise_for_status()
        result = response.json()

        if result["status"] != "success":
            error_msg = result.get('error', 'Unknown error')
            logger.error("Prometheus API returned error", endpoint=endpoint, error=error_msg, status=result["status"])
            raise ValueError(f"Prometheus API error: {error_msg}")

        data_field = result.get("data", {})
        if isinstance(data_field, dict):
            result_type = data_field.get("resultType")
        else:
            result_type = "list"
        logger.debug("Prometheus API request successful", endpoint=endpoint, result_type=result_type)
        return result["data"]

    except requests.exceptions.RequestException as e:
        logger.error("HTTP request to Prometheus failed", endpoint=endpoint, url=url, error=str(e), error_type=type(e).__name__)
        raise
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Prometheus response as JSON", endpoint=endpoint, url=url, error=str(e))
        raise ValueError(f"Invalid JSON response from Prometheus: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error during Prometheus request", endpoint=endpoint, url=url, error=str(e), error_type=type(e).__name__)
        raise

def get_cached_metrics() -> List[str]:
    """Get metrics list with caching to improve performance.

    Returns cached metrics if available and not expired, otherwise fetches fresh data.
    """
    current_time = time.time()

    # Check if cache is valid
    if _metrics_cache["data"] is not None and (current_time - _metrics_cache["timestamp"]) < _CACHE_TTL:
        logger.debug("Using cached metrics list", cache_age=current_time - _metrics_cache["timestamp"])
        return _metrics_cache["data"]

    # Fetch fresh metrics
    try:
        data = make_prometheus_request("label/__name__/values")
        _metrics_cache["data"] = data
        _metrics_cache["timestamp"] = current_time
        logger.debug("Refreshed metrics cache", metric_count=len(data))
        return data
    except Exception as e:
        logger.error("Failed to fetch metrics for cache", error=str(e))
        # Return cached data if available, even if expired
        return _metrics_cache["data"] if _metrics_cache["data"] is not None else []
