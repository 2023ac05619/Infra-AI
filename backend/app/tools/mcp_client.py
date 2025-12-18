"""MCP (Multi-Cloud Protocol) clients for domain-specific actions

This module provides configurable MCP server connections for multi-cloud infrastructure management.
Connection parameters are configured via environment variables in .env file.

Configuration Templates:
  Docker Engine:     DOCKER_HOST, DOCKER_CERT_PATH, DOCKER_TLS_VERIFY
  Prometheus Server: PROMETHEUS_URL, PROMETHEUS_TIMEOUT
  Kubernetes:        KUBECONFIG, KUBERNETES_*
  VMware vSphere:    VMWARE_*
  Grafana:          GRAFANA_*

Example configuration in .env:
  # Docker Engine Connection
  DOCKER_HOST=unix:///var/run/docker.sock
  DOCKER_TLS_VERIFY=0

  # Prometheus Metrics Server
  PROMETHEUS_URL=http://192.168.203.103:8080
  PROMETHEUS_TIMEOUT=45
"""

import json
import os
import asyncio
import docker
from typing import Optional
import aiohttp


async def mcp_restart_vm(vm_name: str) -> str:
    """
    Restart a VM via VMware MCP protocol (stub implementation).
    
    Args:
        vm_name: Name of the VM to restart
        
    Returns:
        JSON string with action result
    """
    print(f"[MCP-VMWARE] Restarting VM: {vm_name}")
    
    result = {
        "status": "success",
        "action": "restart_vm",
        "target": vm_name,
        "message": f"VM '{vm_name}' restart initiated (simulated)"
    }
    
    return json.dumps(result)


async def mcp_restart_pod(pod_name: str, namespace: str = "default") -> str:
    """
    Restart a Kubernetes pod via K8s MCP protocol, or Docker container if no K8s.

    Uses environment variables from .env for Docker connection configuration.

    Args:
        pod_name: Name of the pod/container to restart
        namespace: Kubernetes namespace (ignored for Docker)

    Returns:
        JSON string with action result
    """
    print(f"[MCP-K8S] Attempting to restart container: {pod_name}")

    try:
        # Use Docker environment variables for connection
        client_kwargs = {}
        docker_host = os.getenv("DOCKER_HOST")
        docker_cert_path = os.getenv("DOCKER_CERT_PATH")
        docker_tls_verify = os.getenv("DOCKER_TLS_VERIFY")

        if docker_host:
            client_kwargs["base_url"] = docker_host
        if docker_cert_path:
            # Configure TLS certificates if specified
            import ssl
            tls_config = docker.tls.TLSConfig(
                client_cert=(f"{docker_cert_path}/cert.pem", f"{docker_cert_path}/key.pem"),
                ca_cert=f"{docker_cert_path}/ca.pem",
                verify=docker_tls_verify == "1"
            )
            client_kwargs["tls"] = tls_config

        client = docker.from_env(**client_kwargs)

        # Check if container exists and is running
        container_list = client.containers.list(all=True, filters={'name': pod_name})

        if not container_list:
            result = {
                "status": "error",
                "action": "restart_pod",
                "target": pod_name,
                "message": f"Container '{pod_name}' not found"
            }
            return json.dumps(result)

        container = container_list[0]

        # Restart the container
        container.restart(timeout=10)

        # Verify container is starting
        await asyncio.sleep(1)
        container.reload()

        status = container.status

        result = {
            "status": "success",
            "action": "restart_pod",
            "target": pod_name,
            "namespace": namespace,
            "container_status": status,
            "message": f"Container '{pod_name}' restart completed. Current status: {status}"
        }

        print(f"[MCP-K8S] Container {pod_name} restart successful, status: {status}")

    except Exception as e:
        result = {
            "status": "error",
            "action": "restart_pod",
            "target": pod_name,
            "namespace": namespace,
            "message": f"Failed to restart container: {str(e)}"
        }
        print(f"[MCP-K8S] Error restarting container {pod_name}: {e}")

    return json.dumps(result)


async def mcp_query_prometheus(query: str) -> str:
    """
    Query Prometheus metrics via MCP server instead of direct connection.

    Uses MCP_PROMETHEUS_HTTP_URL environment variable to connect to MCP server.
    Falls back to simulated data if MCP server unavailable.

    Args:
        query: PromQL query string

    Returns:
        JSON string with query result
    """
    # Use MCP server instead of direct Prometheus connection
    mcp_url = os.getenv("MCP_PROMETHEUS_HTTP_URL", "http://192.168.203.103:8080")
    prometheus_timeout = int(os.getenv("PROMETHEUS_TIMEOUT", "30"))

    print(f"[MCP-PROMETHEUS] Querying via MCP server {mcp_url}: {query}")

    try:
        # Use the proper MCP client
        from app.tools.mcp_prometheus_client import get_prometheus_mcp_client
        client = await get_prometheus_mcp_client()

        # Execute the query through MCP
        result = await client.call_method("execute_query", {"query": query})

        if result.get("error"):
            print(f"[MCP-PROMETHEUS] MCP query failed: {result['error']}")
            raise Exception(result["error"])

        # Return the MCP result directly
        return json.dumps(result, indent=2)

    except Exception as e:
        print(f"[MCP-PROMETHEUS] MCP connection failed: {e}")

        # Fallback: try direct Prometheus connection as last resort
        prometheus_url = os.getenv("PROMETHEUS_URL", "http://192.168.203.103:8080")
        print(f"[MCP-PROMETHEUS] Falling back to direct Prometheus query: {prometheus_url}")

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=prometheus_timeout)) as session:
                params = {"query": query}
                url = f"{prometheus_url}/api/v1/query"

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["status"] == "success":
                            result = {
                                "status": "success",
                                "action": "query_prometheus",
                                "query": query,
                                "data": data["data"],
                                "message": f"Prometheus query successful from {prometheus_url}"
                            }
                            return json.dumps(result, indent=2)
        except Exception as fallback_error:
            print(f"[MCP-PROMETHEUS] Direct Prometheus fallback also failed: {fallback_error}")

    # Final fallback to simulated data
    result = {
        "status": "simulated",
        "action": "query_prometheus",
        "query": query,
        "data": {
            "resultType": "vector",
            "result": [{"metric": {"__name__": query, "instance": mcp_url}, "value": [1000000000, "42.5"]}]
        },
        "message": f"Using simulated data - MCP server {mcp_url} unavailable"
    }
    return json.dumps(result, indent=2)


def mcp_get_grafana_dashboard(dashboard_id: str) -> str:
    """
    Fetch Grafana dashboard info (configurable via GRAFANA_* env vars).
    """
    grafana_url = os.getenv("GRAFANA_URL", "http://192.168.203.103:8000/api")
    api_key = os.getenv("GRAFANA_API_KEY", "")

    result = {
        "status": "simulated",
        "action": "get_grafana_dashboard",
        "dashboard_id": dashboard_id,
        "dashboard_url": f"{grafana_url}/dashboards/db/{dashboard_id}",
        "message": "Grafana integration configured"
    }
    return json.dumps(result, indent=2)


def mcp_scale_deployment(deployment_name: str, replicas: int, namespace: str = "default") -> str:
    """
    Scale Kubernetes deployment (configurable via KUBERNETES_* env vars).
    """
    api_server = os.getenv("KUBERNETES_API_SERVER")
    token = os.getenv("KUBERNETES_TOKEN")

    if api_server and token:
        result = {
            "status": "simulated",
            "action": "scale_deployment",
            "target": deployment_name,
            "replicas": replicas,
            "message": f"K8s scaling configured via {api_server}"
        }
    else:
        result = {
            "status": "error",
            "action": "scale_deployment",
            "target": deployment_name,
            "message": "Kubernetes configuration missing"
        }

    return json.dumps(result)
