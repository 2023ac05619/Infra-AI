#!/usr/bin/env python3
"""Kubernetes MCP Client - integrates with external kubernetes-mcp-server"""

import os
import json
import httpx
from typing import Dict, Any, Optional

class KubernetesMCPClient:
    """
    MCP client that integrates with the external kubernetes-mcp-server
    """

    def __init__(self):
        self.server_url = os.getenv("MCP_KUBERNETES_HTTP_URL", "http://192.168.203.103:8082")
        self.endpoint = "/mcp"
        self.full_url = f"{self.server_url}{self.endpoint}"
        self.health_url = f"{self.server_url}/health"
        self.request_id = 1

    async def start_server(self) -> bool:
        """Check if Kubernetes MCP server is accessible"""
        try:
            # Test basic connectivity via health endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(self.health_url, timeout=5.0)
                if response.status_code == 200:
                    print(f"[MCP-Kubernetes] Server accessible at {self.server_url}")
                    return True
                else:
                    print(f"[MCP-Kubernetes] Health check returned status {response.status_code}")
                    return False
        except Exception as e:
            print(f"[MCP-Kubernetes] Server not accessible: {e}")
            return False

    async def call_method(self, method_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call an MCP tool using the tools/call method"""
        if params is None:
            params = {}

        try:
            # Use MCP tools/call protocol
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": method_name,
                    "arguments": params
                },
                "id": self.request_id
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.full_url, json=payload, headers=headers)

                if response.status_code == 200:
                    try:
                        result = response.json()
                        self.request_id += 1
                        return result
                    except json.JSONDecodeError:
                        return {
                            "status": "error",
                            "error": "Invalid JSON response",
                            "method": method_name,
                            "raw_response": response.text[:500]
                        }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status_code}: {response.text[:200]}",
                        "method": method_name
                    }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "method": method_name
            }


# Global Kubernetes MCP client instance
_kubernetes_mcp_client: Optional[KubernetesMCPClient] = None


async def get_kubernetes_mcp_client() -> KubernetesMCPClient:
    """Get or create the Kubernetes MCP client"""
    global _kubernetes_mcp_client
    if _kubernetes_mcp_client is None:
        _kubernetes_mcp_client = KubernetesMCPClient()
        success = await _kubernetes_mcp_client.start_server()
        if not success:
            print("[MCP-Kubernetes] Failed to initialize Kubernetes MCP client")
            # Don't cache failed clients
            _kubernetes_mcp_client = None
            raise Exception("Kubernetes MCP server not accessible")
    return _kubernetes_mcp_client


async def mcp_kubectl_get(resourceType: str, name: str = None, namespace: str = "default", output: str = "json", allNamespaces: bool = False, labelSelector: str = None, fieldSelector: str = None, context: str = None) -> str:
    """Get or list Kubernetes resources - returns JSON/YAML resource data or formatted table output"""
    params = {"resourceType": resourceType}
    if name:
        params["name"] = name
    if namespace != "default":
        params["namespace"] = namespace
    if output != "json":
        params["output"] = output
    if allNamespaces:
        params["allNamespaces"] = allNamespaces
    if labelSelector:
        params["labelSelector"] = labelSelector
    if fieldSelector:
        params["fieldSelector"] = fieldSelector
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_get", params)
    return json.dumps(result)


async def mcp_kubectl_describe(resourceType: str, name: str, namespace: str = "default", context: str = None) -> str:
    """Describe Kubernetes resources - returns detailed resource description with events and status"""
    params = {
        "resourceType": resourceType,
        "name": name
    }
    if namespace != "default":
        params["namespace"] = namespace
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_describe", params)
    return json.dumps(result)


async def mcp_kubectl_apply(manifest: str = None, filename: str = None, namespace: str = "default", dryRun: bool = False, force: bool = False, context: str = None) -> str:
    """Apply Kubernetes manifests - returns apply operation results and status"""
    params = {}
    if manifest:
        params["manifest"] = manifest
    if filename:
        params["filename"] = filename
    if namespace != "default":
        params["namespace"] = namespace
    if dryRun:
        params["dryRun"] = dryRun
    if force:
        params["force"] = force
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_apply", params)
    return json.dumps(result)


async def mcp_kubectl_delete(resourceType: str, name: str, namespace: str = "default", force: bool = False, gracePeriod: int = None, context: str = None) -> str:
    """Delete Kubernetes resources - returns deletion confirmation and status"""
    params = {
        "resourceType": resourceType,
        "name": name
    }
    if namespace != "default":
        params["namespace"] = namespace
    if force:
        params["force"] = force
    if gracePeriod is not None:
        params["gracePeriod"] = gracePeriod
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_delete", params)
    return json.dumps(result)


async def mcp_kubectl_create(resourceType: str = None, manifest: str = None, filename: str = None, namespace: str = "default", dryRun: bool = False, context: str = None) -> str:
    """Create Kubernetes resources - returns creation results and resource information"""
    params = {}
    if resourceType:
        params["resourceType"] = resourceType
    if manifest:
        params["manifest"] = manifest
    if filename:
        params["filename"] = filename
    if namespace != "default":
        params["namespace"] = namespace
    if dryRun:
        params["dryRun"] = dryRun
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_create", params)
    return json.dumps(result)


async def mcp_kubectl_logs(name: str, resourceType: str = "pod", namespace: str = "default", container: str = None, follow: bool = False, previous: bool = False, tail: int = None, context: str = None) -> str:
    """Get container logs - returns container logs as text"""
    params = {
        "name": name
    }
    if resourceType != "pod":
        params["resourceType"] = resourceType
    if namespace != "default":
        params["namespace"] = namespace
    if container:
        params["container"] = container
    if follow:
        params["follow"] = follow
    if previous:
        params["previous"] = previous
    if tail is not None:
        params["tail"] = tail
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_logs", params)
    return json.dumps(result)


async def mcp_kubectl_scale(name: str, replicas: int, resourceType: str = "deployment", namespace: str = "default", context: str = None) -> str:
    """Scale Kubernetes resources - returns scaling operation results"""
    params = {
        "name": name,
        "replicas": replicas
    }
    if resourceType != "deployment":
        params["resourceType"] = resourceType
    if namespace != "default":
        params["namespace"] = namespace
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_scale", params)
    return json.dumps(result)


async def mcp_kubectl_patch(resourceType: str, name: str, namespace: str = "default", patchType: str = None, patchData: dict = None, patchFile: str = None, context: str = None) -> str:
    """Patch Kubernetes resources - returns patch operation results"""
    params = {
        "resourceType": resourceType,
        "name": name
    }
    if namespace != "default":
        params["namespace"] = namespace
    if patchType:
        params["patchType"] = patchType
    if patchData:
        params["patchData"] = patchData
    if patchFile:
        params["patchFile"] = patchFile
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_patch", params)
    return json.dumps(result)


async def mcp_kubectl_rollout(subCommand: str, resourceType: str, name: str, namespace: str = "default", revision: int = None, context: str = None) -> str:
    """Manage rollout operations - returns rollout operation results and status"""
    params = {
        "subCommand": subCommand,
        "resourceType": resourceType,
        "name": name
    }
    if namespace != "default":
        params["namespace"] = namespace
    if revision is not None:
        params["revision"] = revision
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_rollout", params)
    return json.dumps(result)


async def mcp_kubectl_context(operation: str, name: str = None, output: str = "json") -> str:
    """Manage kubectl contexts - returns context information and operations"""
    params = {"operation": operation}
    if name:
        params["name"] = name
    if output != "json":
        params["output"] = output

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_context", params)
    return json.dumps(result)


async def mcp_kubectl_generic(command: str, context: str = None) -> str:
    """Execute generic kubectl commands - returns generic kubectl command output"""
    params = {"command": command}
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("kubectl_generic", params)
    return json.dumps(result)


async def mcp_exec_in_pod(name: str, command: str, namespace: str = "default", container: str = None, shell: str = None, timeout: int = None, context: str = None) -> str:
    """Execute commands in pods - returns command execution results and stdout"""
    params = {
        "name": name,
        "command": command
    }
    if namespace != "default":
        params["namespace"] = namespace
    if container:
        params["container"] = container
    if shell:
        params["shell"] = shell
    if timeout is not None:
        params["timeout"] = timeout
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("exec_in_pod", params)
    return json.dumps(result)


async def mcp_node_management(operation: str, nodeName: str = None, force: bool = False, gracePeriod: int = None, timeout: str = None, dryRun: bool = False) -> str:
    """Manage cluster nodes - returns node management operation results"""
    params = {"operation": operation}
    if nodeName:
        params["nodeName"] = nodeName
    if force:
        params["force"] = force
    if gracePeriod is not None:
        params["gracePeriod"] = gracePeriod
    if timeout:
        params["timeout"] = timeout
    if dryRun:
        params["dryRun"] = dryRun

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("node_management", params)
    return json.dumps(result)


async def mcp_install_helm_chart(name: str, chart: str, namespace: str = "default", repo: str = None, values: dict = None, valuesFile: str = None, context: str = None) -> str:
    """Install Helm charts - returns Helm installation results"""
    params = {
        "name": name,
        "chart": chart
    }
    if namespace != "default":
        params["namespace"] = namespace
    if repo:
        params["repo"] = repo
    if values:
        params["values"] = values
    if valuesFile:
        params["valuesFile"] = valuesFile
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("install_helm_chart", params)
    return json.dumps(result)


async def mcp_upgrade_helm_chart(name: str, chart: str, namespace: str = "default", repo: str = None, values: dict = None, valuesFile: str = None, context: str = None) -> str:
    """Upgrade Helm charts - returns Helm upgrade results"""
    params = {
        "name": name,
        "chart": chart
    }
    if namespace != "default":
        params["namespace"] = namespace
    if repo:
        params["repo"] = repo
    if values:
        params["values"] = values
    if valuesFile:
        params["valuesFile"] = valuesFile
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("upgrade_helm_chart", params)
    return json.dumps(result)


async def mcp_uninstall_helm_chart(name: str, namespace: str = "default", context: str = None) -> str:
    """Uninstall Helm charts - returns Helm uninstallation results"""
    params = {"name": name}
    if namespace != "default":
        params["namespace"] = namespace
    if context:
        params["context"] = context

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("uninstall_helm_chart", params)
    return json.dumps(result)


async def mcp_explain_resource(resource: str, apiVersion: str = None, recursive: bool = False, context: str = None, output: str = "plaintext") -> str:
    """Get Kubernetes resource documentation - returns resource documentation"""
    params = {"resource": resource}
    if apiVersion:
        params["apiVersion"] = apiVersion
    if recursive:
        params["recursive"] = recursive
    if context:
        params["context"] = context
    if output != "plaintext":
        params["output"] = output

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("explain_resource", params)
    return json.dumps(result)


async def mcp_list_api_resources(apiGroup: str = None, namespaced: bool = None, context: str = None, verbs: list = None) -> str:
    """List available API resources - returns list of available API resources"""
    params = {}
    if apiGroup:
        params["apiGroup"] = apiGroup
    if namespaced is not None:
        params["namespaced"] = namespaced
    if context:
        params["context"] = context
    if verbs:
        params["verbs"] = verbs

    client = await get_kubernetes_mcp_client()
    result = await client.call_method("list_api_resources", params)
    return json.dumps(result)


async def mcp_ping() -> str:
    """Test connectivity - returns empty object (connectivity test)"""
    client = await get_kubernetes_mcp_client()
    result = await client.call_method("ping", {})
    return json.dumps(result)
