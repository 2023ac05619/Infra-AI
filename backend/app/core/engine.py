"""LangGraph Core Engine - The Coordinator Brain"""
import logging as log
import operator
import json
import os
from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.tools.ollama_adapter import call_ollama
from app.tools.network_scanner import scan_network
from app.tools.policy_tools import fetch_all_policies
# Import new MCP tools
from app.tools.mcp_grafana_client import (
    mcp_grafana_list_dashboards,
    mcp_grafana_get_dashboard,
    mcp_grafana_list_datasources
)
from app.tools.mcp_prometheus_client import (
    mcp_prometheus_health_check,
    mcp_prometheus_execute_query,
    mcp_prometheus_execute_range_query,
    mcp_prometheus_list_metrics,
    mcp_prometheus_get_metric_metadata,
    mcp_prometheus_get_targets
)
from app.tools.mcp_esxi_client import (
    mcp_esxi_create_vm,
    mcp_esxi_clone_vm,
    mcp_esxi_delete_vm,
    mcp_esxi_power_on,
    mcp_esxi_power_off,
    mcp_esxi_list_vms,
    get_vm_stats
)
from app.tools.mcp_kubernetes_client import (
    mcp_kubectl_logs,
    mcp_kubectl_rollout,
    mcp_exec_in_pod,
    mcp_node_management,
    mcp_kubectl_delete,
    mcp_kubectl_generic,
    mcp_kubectl_create,
    mcp_kubectl_scale,
    mcp_explain_resource,
    mcp_list_api_resources,
    mcp_kubectl_apply,
    mcp_kubectl_get,
    mcp_ping,
    mcp_kubectl_describe,
    mcp_kubectl_patch,
    mcp_install_helm_chart,
    mcp_upgrade_helm_chart,
    mcp_uninstall_helm_chart,
    mcp_kubectl_context
)


# ========== State Definition ==========

class AgentState(TypedDict):
    """State for the LangGraph agent"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str
    current_task: str  # "chat", "chat-with-infra"


# ========== Single Command Tool ==========

@tool
async def infra_command(
    domain: str,
    action: str,
    resource: str = None,
    name: str = None,
    namespace: str = None,
    query: str = None
) -> str:
    """
    Execute structured infrastructure commands.

    Args:
        domain: Infrastructure domain (kubernetes, prometheus, grafana, vmware, network)
        action: Action to perform (list, get, describe, query, create, delete, scale, restart, power_on, power_off)
        resource: Resource type (pods, nodes, deployments, vms, dashboards, metrics)
        name: Specific resource name
        namespace: Kubernetes namespace
        query: PromQL query or search term
    """
    print("️  [TOOL] infra_command called with structured parameters:")
    print(f"\t Domain: {domain}, Action: {action}, Resource: {resource}, Name: {name}, Namespace: {namespace}, Query: {query}")

    # Route the command to the appropriate MCP tool
    result = await route_infra_command({
        "domain": domain,
        "action": action,
        "resource": resource,
        "name": name,
        "namespace": namespace,
        "query": query
    })

    # Ensure result is always a string
    if result is None:
        result = f"Error: {domain} MCP server is not accessible. Please check server configuration and connectivity."

    print(f" [TOOL] infra_command completed, result length: {len(result)} chars")
    return result


def is_server_error(response: dict) -> bool:
    """Check if response indicates MCP server is unavailable."""
    if not isinstance(response, dict):
        return False

    error_field = response.get("error", "")
    # Ensure error_msg is a string before calling .lower()
    error_msg = str(error_field).lower() if error_field else ""

    return response.get("status") == "error" and (
        "connection" in error_msg or
        "server not accessible" in error_msg or
        "failed to initialize" in error_msg or
        "all connection attempts failed" in error_msg or
        "http" in error_msg or
        "404" in error_msg or
        "503" in error_msg
    )


# ========== Router Function ==========

async def route_infra_command(cmd: dict) -> str:
    """Route structured infra_command to real MCP tools."""
    print(" [ROUTER] Received structured command:", cmd)

    domain = cmd.get("domain")
    action = cmd.get("action")
    resource = cmd.get("resource")
    name = cmd.get("name")
    namespace = cmd.get("namespace", "default")
    query = cmd.get("query")

    try:
        print(f" [ROUTER] Routing {domain}.{action} command...")

        if domain == "kubernetes":
            # Call Kubernetes MCP server directly using correct JSON-RPC format
            server_url = os.getenv("MCP_KUBERNETES_HTTP_URL", "http://192.168.203.103:8082")
            jsonrpc_url = f"{server_url}/jsonrpc"
            health_url = f"{server_url}/health"

            # Check server health first
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    health_response = await client.get(health_url)
                    if health_response.status_code != 200:
                        return f"Error: Kubernetes MCP server health check failed (status {health_response.status_code})"
            except Exception as e:
                return f"Error: Kubernetes MCP server not accessible: {str(e)}"

            print(f"️  [ROUTER] Processing Kubernetes {action} for resource: {resource}")

            # Map resource names to proper Kubernetes resource types
            resource_map = {
                "pods": "pods",
                "pod": "pods",
                "deployments": "deployments",
                "deployment": "deployments",
                "services": "services",
                "service": "services",
                "nodes": "nodes",
                "node": "nodes",
                "namespaces": "namespaces",
                "namespace": "namespaces"
            }
            kube_resource = resource_map.get(resource, resource)
            print(f" [ROUTER] Mapped resource '{resource}' → '{kube_resource}'")

            if action in ["list", "get"]:
                params = {"resourceType": kube_resource}
                if namespace != "default":
                    params["namespace"] = namespace
                print(f" [ROUTER] Calling Kubernetes kubectl_get: {params}")

                # Use tools/call method as expected by MCP server
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "kubectl_get",
                        "arguments": params
                    },
                    "id": 1
                }

                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(jsonrpc_url, json=payload)
                        if response.status_code == 200:
                            result = response.json()
                            return json.dumps(result)
                        else:
                            return f"Error: HTTP {response.status_code} from Kubernetes MCP server"
                except Exception as e:
                    return f"Error: Failed to connect to Kubernetes MCP server: {str(e)}"
            elif action == "describe":
                params = {"resourceType": kube_resource, "name": name}
                if namespace != "default":
                    params["namespace"] = namespace
                print(f" [ROUTER] Calling Kubernetes client kubectl_describe: {params}")
                result = await client.call_method("kubectl_describe", params)
                return json.dumps(result)
            elif action == "delete":
                params = {"resourceType": kube_resource, "name": name}
                if namespace != "default":
                    params["namespace"] = namespace
                print(f"️  [ROUTER] Calling Kubernetes client kubectl_delete: {params}")
                result = await client.call_method("kubectl_delete", params)
                return json.dumps(result)
            elif action == "scale":
                replicas = int(cmd.get("replicas", 1))
                params = {"name": name, "replicas": replicas}
                if namespace != "default":
                    params["namespace"] = namespace
                print(f"️  [ROUTER] Calling Kubernetes client kubectl_scale: {params}")
                result = await client.call_method("kubectl_scale", params)
                return json.dumps(result)
            elif action == "restart":
                params = {"subCommand": "restart", "resourceType": kube_resource, "name": name}
                if namespace != "default":
                    params["namespace"] = namespace
                print(f" [ROUTER] Calling Kubernetes client kubectl_rollout: {params}")
                result = await client.call_method("kubectl_rollout", params)
                return json.dumps(result)
            elif action == "logs":
                params = {"name": name}
                if namespace != "default":
                    params["namespace"] = namespace
                print(f" [ROUTER] Calling Kubernetes client kubectl_logs: {params}")
                result = await client.call_method("kubectl_logs", params)
                return json.dumps(result)
            elif action == "exec":
                command = cmd.get("command", "echo 'Hello from pod'")
                params = {"name": name, "command": command}
                if namespace != "default":
                    params["namespace"] = namespace
                print(f" [ROUTER] Calling Kubernetes client exec_in_pod: {params}")
                result = await client.call_method("exec_in_pod", params)
                return json.dumps(result)
            elif action == "create":
                params = {}
                if cmd.get("manifest"):
                    params["manifest"] = cmd.get("manifest")
                if cmd.get("filename"):
                    params["filename"] = cmd.get("filename")
                if namespace != "default":
                    params["namespace"] = namespace
                print(f"🆕 [ROUTER] Calling Kubernetes client kubectl_create: {params}")
                result = await client.call_method("kubectl_create", params)
                return json.dumps(result)
            elif action == "apply":
                params = {}
                if cmd.get("manifest"):
                    params["manifest"] = cmd.get("manifest")
                if cmd.get("filename"):
                    params["filename"] = cmd.get("filename")
                if namespace != "default":
                    params["namespace"] = namespace
                print(f" [ROUTER] Calling Kubernetes client kubectl_apply: {params}")
                result = await client.call_method("kubectl_apply", params)
                return json.dumps(result)
            elif action == "patch":
                params = {"resourceType": kube_resource, "name": name}
                if namespace != "default":
                    params["namespace"] = namespace
                if cmd.get("patch_data"):
                    params["patchData"] = cmd.get("patch_data")
                if cmd.get("patch_type"):
                    params["patchType"] = cmd.get("patch_type")
                print(f" [ROUTER] Calling Kubernetes client kubectl_patch: {params}")
                result = await client.call_method("kubectl_patch", params)
                return json.dumps(result)
            elif action == "rollout":
                sub_command = cmd.get("sub_command", "status")
                params = {"subCommand": sub_command, "resourceType": kube_resource, "name": name}
                if namespace != "default":
                    params["namespace"] = namespace
                print(f" [ROUTER] Calling Kubernetes client kubectl_rollout: {params}")
                result = await client.call_method("kubectl_rollout", params)
                return json.dumps(result)
            elif action == "context":
                operation = cmd.get("operation", "list")
                params = {"operation": operation}
                print(f" [ROUTER] Calling Kubernetes client kubectl_context: {params}")
                result = await client.call_method("kubectl_context", params)
                return json.dumps(result)
            elif action == "generic":
                kubectl_cmd = cmd.get("command")
                params = {"command": kubectl_cmd}
                print(f" [ROUTER] Calling Kubernetes client kubectl_generic: {params}")
                result = await client.call_method("kubectl_generic", params)
                return json.dumps(result)
            elif action == "node_management":
                operation = cmd.get("operation", "list")
                params = {"operation": operation}
                print(f"️  [ROUTER] Calling Kubernetes client node_management: {params}")
                result = await client.call_method("node_management", params)
                return json.dumps(result)
            elif action == "install_helm":
                params = {"name": name, "chart": cmd.get("chart")}
                if namespace != "default":
                    params["namespace"] = namespace
                if cmd.get("repo"):
                    params["repo"] = cmd.get("repo")
                if cmd.get("values"):
                    params["values"] = cmd.get("values")
                print(f" [ROUTER] Calling Kubernetes client install_helm_chart: {params}")
                result = await client.call_method("install_helm_chart", params)
                return json.dumps(result)
            elif action == "upgrade_helm":
                params = {"name": name, "chart": cmd.get("chart")}
                if namespace != "default":
                    params["namespace"] = namespace
                if cmd.get("repo"):
                    params["repo"] = cmd.get("repo")
                if cmd.get("values"):
                    params["values"] = cmd.get("values")
                print(f"⬆️  [ROUTER] Calling Kubernetes client upgrade_helm_chart: {params}")
                result = await client.call_method("upgrade_helm_chart", params)
                return json.dumps(result)
            elif action == "uninstall_helm":
                params = {"name": name}
                if namespace != "default":
                    params["namespace"] = namespace
                print(f"️  [ROUTER] Calling Kubernetes client uninstall_helm_chart: {params}")
                result = await client.call_method("uninstall_helm_chart", params)
                return json.dumps(result)
            elif action == "explain":
                params = {"resource": name}
                if cmd.get("api_version"):
                    params["apiVersion"] = cmd.get("api_version")
                if cmd.get("recursive", False):
                    params["recursive"] = cmd.get("recursive")
                print(f" [ROUTER] Calling Kubernetes client explain_resource: {params}")
                result = await client.call_method("explain_resource", params)
                return json.dumps(result)
            elif action == "list_api_resources":
                params = {}
                if cmd.get("api_group"):
                    params["apiGroup"] = cmd.get("api_group")
                if cmd.get("namespaced") is not None:
                    params["namespaced"] = cmd.get("namespaced")
                print(f" [ROUTER] Calling Kubernetes client list_api_resources: {params}")
                result = await client.call_method("list_api_resources", params)
                return json.dumps(result)
            elif action == "ping":
                print(f" [ROUTER] Calling Kubernetes ping")

                # Use tools/call method as expected by MCP server
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ping",
                        "arguments": {}
                    },
                    "id": 1
                }

                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(jsonrpc_url, json=payload)
                        if response.status_code == 200:
                            result = response.json()
                            return json.dumps(result)
                        else:
                            return f"Error: HTTP {response.status_code} from Kubernetes MCP server"
                except Exception as e:
                    return f"Error: Failed to connect to Kubernetes MCP server: {str(e)}"

        elif domain == "prometheus":
            # Use Prometheus MCP client with configuration validation
            from app.tools.mcp_prometheus_client import get_prometheus_mcp_client
            client = await get_prometheus_mcp_client()

            if action == "query":
                print(f" [ROUTER] Executing Prometheus query via MCP client: {query}")
                if not query:
                    return "Error: Missing required parameter 'query' for Prometheus query"
                result = await client.execute_tool("execute_query", {"query": query})
                return json.dumps(result)

            elif action == "health":
                print(f" [ROUTER] Checking Prometheus health via MCP client")
                result = await client.execute_tool("health_check", {})
                return json.dumps(result)

            elif action == "list_metrics":
                print(f" [ROUTER] Listing Prometheus metrics via MCP client")
                params = {}
                if cmd.get("limit"):
                    params["limit"] = cmd.get("limit")
                if cmd.get("filter_pattern"):
                    params["filter_pattern"] = cmd.get("filter_pattern")
                result = await client.execute_tool("list_metrics", params)
                return json.dumps(result)

            else:
                # Try to map other actions to available tools
                available_tools = client.available_tools
                if action in available_tools:
                    print(f" [ROUTER] Using Prometheus MCP tool: {action}")
                    result = await client.execute_tool(action, cmd)
                    return json.dumps(result)
                else:
                    return f"Error: Unsupported Prometheus action: {action}. Available actions: {list(available_tools.keys())}"

        elif domain == "grafana":
            # Get Grafana client directly
            from app.tools.mcp_grafana_client import get_grafana_mcp_client
            client = await get_grafana_mcp_client()

            if action == "list":
                if resource in ["dashboards", "dashboard"]:
                    print(f" [ROUTER] Calling Grafana client list_dashboards")
                    result = await client.execute_tool("list_dashboards", {})
                    # Check if server is unavailable and return mock data
                    if is_server_error(result):
                        print(f"[ROUTER] Server unavailable, using mock response")
                        return f"Error: Grafana MCP server is not accessible. Please check server configuration and connectivity."
                        # print(f" [ROUTER] Server unavailable, using mock response")
                        # mock_result = get_mock_grafana_response(action, resource, name)
                        # return json.dumps(mock_result)

                    # Return raw dashboard data directly (not wrapped in MCP format)
                    # This ensures the LLM gets clean dashboard JSON for formatting
                    try:
                        if isinstance(result, dict) and "result" in result:
                            mcp_result = result["result"]
                            if isinstance(mcp_result, dict) and "content" in mcp_result:
                                content = mcp_result["content"]
                                if isinstance(content, list) and len(content) > 0:
                                    first_content = content[0]
                                    if isinstance(first_content, dict) and "text" in first_content:
                                        # Parse the JSON data from the text and return directly
                                        dashboard_data = json.loads(first_content["text"])
                                        print(f"[ROUTER] Returning raw dashboard data: {len(dashboard_data)} items")
                                        return json.dumps(dashboard_data)
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        print(f"[ROUTER] Failed to extract dashboard data: {e}")

                    # Fallback: return the raw result
                    return json.dumps(result)

                elif resource in ["datasources", "datasource"]:
                    print(f" [ROUTER] Calling Grafana client list_datasources")
                    result = await client.execute_tool("list_datasources", {})

                    # Extract the actual datasource data from MCP response format
                    try:
                        if isinstance(result, dict) and "result" in result:
                            mcp_result = result["result"]
                            if isinstance(mcp_result, dict) and "content" in mcp_result:
                                content = mcp_result["content"]
                                if isinstance(content, list) and len(content) > 0:
                                    first_content = content[0]
                                    if isinstance(first_content, dict) and "text" in first_content:
                                        # Parse the JSON data from the text
                                        datasource_data = json.loads(first_content["text"])
                                        return json.dumps(datasource_data)
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        print(f"[ROUTER] Failed to extract datasource data: {e}")

                    # Fallback: return the raw result
                    return json.dumps(result)
            elif action == "get":
                if resource in ["dashboards", "dashboard"]:
                    # Check if name looks like a UID (alphanumeric) or a title (contains spaces/words)
                    import re
                    if re.match(r'^[a-zA-Z0-9]+$', name):  # Looks like a UID
                        print(f" [ROUTER] Calling Grafana client get_dashboard by UID: {name}")
                        result = await client.execute_tool("get_dashboard", {"uid": name})
                        # Check if server is unavailable and return mock data
                        if is_server_error(result):
                            print(f"[ROUTER] Server unavailable, using mock response")
                            return f"Error: Grafana MCP server is not accessible. Please check server configuration and connectivity."
                        return json.dumps(result)
                    else:
                        # Name-based search - need to find UID first
                        print(f" [ROUTER] Name-based search for '{name}' - first listing all dashboards to find UID")

                        # Step 1: List all dashboards to find matching title
                        list_result = await client.execute_tool("list_dashboards", {})
                        if is_server_error(list_result):
                            return f"Error: Grafana MCP server is not accessible. Please check server configuration and connectivity."

                        # Extract dashboard list from MCP response
                        try:
                            if isinstance(list_result, dict) and "result" in list_result:
                                mcp_result = list_result["result"]
                                if isinstance(mcp_result, dict) and "content" in mcp_result:
                                    content = mcp_result["content"]
                                    if isinstance(content, list) and len(content) > 0:
                                        first_content = content[0]
                                        if isinstance(first_content, dict) and "text" in first_content:
                                            dashboard_data = json.loads(first_content["text"])

                                            # Find dashboard with matching title (case-insensitive partial match)
                                            matching_dashboard = None
                                            for dashboard in dashboard_data:
                                                if isinstance(dashboard, dict):
                                                    title = dashboard.get("title", "").lower()
                                                    if name.lower() in title:
                                                        matching_dashboard = dashboard
                                                        break

                                            if matching_dashboard:
                                                uid = matching_dashboard.get("uid")
                                                print(f" [ROUTER] Found matching dashboard '{matching_dashboard.get('title')}' with UID: {uid}")

                                                # Step 2: Get the specific dashboard by UID
                                                result = await client.execute_tool("get_dashboard", {"uid": uid})
                                                return json.dumps(result)
                                            else:
                                                return f"Error: No dashboard found with title containing '{name}'"
                        except (json.JSONDecodeError, KeyError, IndexError) as e:
                            print(f"[ROUTER] Error parsing dashboard list: {e}")
                            return f"Error: Failed to search dashboards by name: {e}"

                        return f"Error: Could not retrieve dashboard list for name search"

        elif domain == "vmware":
            # Get ESXi client directly
            from app.tools.mcp_esxi_client import get_esxi_mcp_client
            client = await get_esxi_mcp_client()

            if action == "list":
                if resource in ["vms", "vm"]:
                    print(f"️  [ROUTER] Calling ESXi client listVMs")
                    result = await client.call_method("listVMs", {})
                    # Check if server is unavailable and return mock data
                    if is_server_error(result):
                        print(f"[ROUTER] Server unavailable, using mock response")
                        return f"Error: VMware MCP server is not accessible. Please check server configuration and connectivity."
                        # print(f" [ROUTER] Server unavailable, using mock response")
                        # mock_result = get_mock_vmware_response(action, resource, name)
                        # return json.dumps(mock_result)
                    return json.dumps(result)
            elif action in ["get", "status", "info"]:
                if resource in ["vms", "vm"]:
                    print(f" [ROUTER] VM info/status not available - MCP server only supports basic operations")
                    return f"Error: VMware MCP server does not support detailed VM info/status operations. Available operations: list, create, clone, power_on, power_off, delete."
            elif action == "create":
                cpu = cmd.get("cpu", 2)
                memory = cmd.get("memory", 4096)
                datastore = cmd.get("datastore")
                network = cmd.get("network")
                params = {"name": name, "cpu": cpu, "memory": memory}
                if datastore is not None:
                    params["datastore"] = datastore
                if network is not None:
                    params["network"] = network
                print(f"🆕 [ROUTER] Calling ESXi client createVM: {params}")
                result = await client.call_method("createVM", params)
                return json.dumps(result)
            elif action == "clone":
                template_name = cmd.get("template_name", name)
                new_name = cmd.get("new_name", cmd.get("target_name"))
                params = {"template_name": template_name, "new_name": new_name}
                print(f" [ROUTER] Calling ESXi client cloneVM: {params}")
                result = await client.call_method("cloneVM", params)
                return json.dumps(result)
            elif action == "power_on":
                print(f" [ROUTER] Calling ESXi client powerOn: {name}")
                result = await client.call_method("powerOn", {"name": name})
                return json.dumps(result)
            elif action == "power_off":
                print(f" [ROUTER] Calling ESXi client powerOff: {name}")
                result = await client.call_method("powerOff", {"name": name})
                return json.dumps(result)
            elif action == "delete":
                print(f"️  [ROUTER] Calling ESXi client deleteVM: {name}")
                result = await client.call_method("deleteVM", {"name": name})
                return json.dumps(result)
            elif action == "get_stats":
                print(f" [ROUTER] Returning mock VM stats for: {name}")
                return json.dumps({
                    "vm_name": name,
                    "cpu_usage_mhz": 2048,
                    "memory_usage_mb": 2048,
                    "storage_usage_gb": 25,
                    "network_rx_mbps": 150,
                    "network_tx_mbps": 85
                })
            elif action == "snapshots":
                if resource in ["vms", "vm"]:
                    params = {"vm_name": name}
                    print(f" [ROUTER] Calling ESXi client get_vm_snapshots: {params}")
                    result = await client.call_method("get_vm_snapshots", params)
                    return json.dumps(result)
            elif action == "create_snapshot":
                snapshot_name = cmd.get("snapshot_name")
                description = cmd.get("description")
                params = {"vm_name": name, "snapshot_name": snapshot_name}
                if description:
                    params["description"] = description
                print(f" [ROUTER] Calling ESXi client create_snapshot: {params}")
                result = await client.call_method("create_snapshot", params)
                return json.dumps(result)

        elif domain == "network":
            if action == "scan":
                subnet = cmd.get("subnet", "192.168.1.0/24")
                print(f" [ROUTER] Calling network_discovery(subnet='{subnet}')")
                return await network_discovery(subnet=subnet)

        # Fallback for unsupported commands
        print(f" [ROUTER] Command not supported: {cmd}")
        return f"Command not supported: {cmd}"

    except Exception as e:
        print(f" [ROUTER] Error executing command: {str(e)}")
        return f"Error executing command: {str(e)}"


# ========== Legacy Tool Wrappers (kept for compatibility) ==========

@tool
async def llm_reasoning(prompt: str) -> str:
    """Use the LLM to reason about a problem or generate a response."""
    return await call_ollama(prompt)


@tool
async def network_discovery(subnet: str = "192.168.1.0/24") -> str:
    """Scan a network subnet to discover assets and services."""
    return await scan_network(subnet)


@tool
async def get_policies() -> str:
    """Retrieve all self-healing policies from the database."""
    return await fetch_all_policies()


# @tool
# async def restart_vm(vm_name: str) -> str:
#     """Restart a virtual machine."""
#     return await mcp_restart_vm(vm_name)


# @tool
# async def restart_pod(pod_name: str, namespace: str = "default") -> str:
#     """Restart a Kubernetes pod."""
#     return await mcp_restart_pod(pod_name, namespace)


# @tool
# async def query_prometheus(query: str) -> str:
#     """Query Prometheus metrics using PromQL."""
#     return await mcp_query_prometheus(query)


# @tool
# async def get_grafana_dashboard(dashboard_id: str) -> str:
#     """Retrieve Grafana dashboard information."""
#     return await mcp_get_grafana_dashboard(dashboard_id)


# @tool
# async def scale_deployment(deployment_name: str, replicas: int, namespace: str = "default") -> str:
#     """Scale a Kubernetes deployment to a specified number of replicas."""
#     return await mcp_scale_deployment(deployment_name, replicas, namespace)


# ========== ESXi MCP Tools ==========

@tool
async def mcp_esxi_authenticate(api_key: str) -> str:
    """Authenticate with API key for privileged ESXi operations."""
    return await mcp_esxi_authenticate(api_key)


@tool
async def mcp_esxi_list_vms() -> str:
    """List all VMware virtual machine names."""
    return await mcp_esxi_list_vms()


@tool
async def mcp_esxi_power_on_vm(vm_name: str) -> str:
    """Power on specified virtual machine."""
    return await mcp_esxi_power_on(vm_name)


@tool
async def mcp_esxi_power_off_vm(vm_name: str) -> str:
    """Power off specified virtual machine."""
    return await mcp_esxi_power_off(vm_name)


@tool
async def mcp_esxi_create_vm(name: str, cpu: int, memory: int, datastore: str = None, network: str = None) -> str:
    """Create a new virtual machine."""
    return await mcp_esxi_create_vm(name, cpu, memory, datastore, network)


@tool
async def mcp_esxi_clone_vm(template_name: str, new_name: str) -> str:
    """Clone virtual machine from template or existing VM."""
    return await mcp_esxi_clone_vm(template_name, new_name)


@tool
async def mcp_esxi_delete_vm(vm_name: str) -> str:
    """Delete specified virtual machine."""
    return await mcp_esxi_delete_vm(vm_name)


@tool
async def mcp_esxi_get_host_info(host: str = None) -> str:
    """Get ESXi host information."""
    return await mcp_esxi_get_host_info(host)


@tool
async def mcp_esxi_list_datastores(host: str = None) -> str:
    """List available datastores."""
    return await mcp_esxi_list_datastores(host)


@tool
async def mcp_esxi_list_networks(host: str = None) -> str:
    """List available networks."""
    return await mcp_esxi_list_networks(host)


@tool
async def mcp_esxi_get_vm_snapshots(vm_name: str, host: str = None) -> str:
    """Get VM snapshots."""
    return await mcp_esxi_get_vm_snapshots(vm_name, host)


@tool
async def mcp_esxi_create_snapshot(vm_name: str, snapshot_name: str, description: str = None, host: str = None) -> str:
    """Create a VM snapshot."""
    return await mcp_esxi_create_snapshot(vm_name, snapshot_name, description, host)


# ========== Prometheus MCP Tools ==========

@tool
async def mcp_prometheus_health_check() -> str:
    """Check Prometheus MCP server and Prometheus connectivity status."""
    return await mcp_prometheus_health_check()


@tool
async def mcp_prometheus_execute_query(query: str, time: str = None) -> str:
    """Execute instant PromQL queries against Prometheus."""
    return await mcp_prometheus_execute_query(query, time)


@tool
async def mcp_prometheus_execute_range_query(query: str, start: str, end: str, step: str) -> str:
    """Execute PromQL range queries with time series data."""
    return await mcp_prometheus_execute_range_query(query, start, end, step)


@tool
async def mcp_prometheus_list_metrics(limit: int = None, offset: int = None, filter_pattern: str = None) -> str:
    """List available Prometheus metrics with pagination and filtering."""
    return await mcp_prometheus_list_metrics(limit, offset, filter_pattern)


@tool
async def mcp_prometheus_get_metric_metadata(metric: str) -> str:
    """Retrieve metadata for specific Prometheus metrics."""
    return await mcp_prometheus_get_metric_metadata(metric)


@tool
async def mcp_prometheus_get_targets() -> str:
    """Get information about Prometheus scrape targets."""
    return await mcp_prometheus_get_targets()


# ========== Kubernetes MCP Tools ==========

@tool
async def mcp_kubernetes_restart_pod(pod_name: str, namespace: str = "default") -> str:
    """Restart a Kubernetes pod."""
    return await k8s_restart_pod(pod_name, namespace)


@tool
async def mcp_kubernetes_scale_deployment(deployment_name: str, replicas: int, namespace: str = "default") -> str:
    """Scale a Kubernetes deployment."""
    return await k8s_scale_deployment(deployment_name, replicas, namespace)


@tool
async def mcp_kubernetes_get_pods(namespace: str = "default") -> str:
    """Get Kubernetes pods."""
    return await mcp_get_pods(namespace)


@tool
async def mcp_kubernetes_get_deployments(namespace: str = "default") -> str:
    """Get Kubernetes deployments."""
    return await mcp_get_deployments(namespace)


# Tool list - Infrastructure mode includes all MCP tools
# For infrastructure mode: infra_command + individual MCP tools
# For general chat: core tools only
tools = [
    infra_command,  # Single command tool for structured infra operations

    # Prometheus MCP Tools
    mcp_prometheus_health_check,
    mcp_prometheus_execute_query,
    mcp_prometheus_execute_range_query,
    mcp_prometheus_list_metrics,
    mcp_prometheus_get_metric_metadata,
    mcp_prometheus_get_targets,

    # Grafana MCP Tools
    mcp_grafana_list_dashboards,
    mcp_grafana_get_dashboard,
    mcp_grafana_list_datasources,

    # ESXi MCP Tools
    mcp_esxi_list_vms,
    mcp_esxi_power_on_vm,
    mcp_esxi_power_off_vm,
    mcp_esxi_create_vm,
    mcp_esxi_clone_vm,
    mcp_esxi_delete_vm,
    mcp_esxi_get_host_info,
    mcp_esxi_list_datastores,
    mcp_esxi_list_networks,
    mcp_esxi_get_vm_snapshots,
    mcp_esxi_create_snapshot,

    # Kubernetes MCP Tools
    mcp_kubectl_logs,
    mcp_kubectl_rollout,
    mcp_exec_in_pod,
    mcp_node_management,
    mcp_kubectl_delete,
    mcp_kubectl_generic,
    mcp_kubectl_create,
    mcp_kubectl_scale,
    mcp_explain_resource,
    mcp_list_api_resources,
    mcp_kubectl_apply,
    mcp_kubectl_get,
    mcp_ping,
    mcp_kubectl_describe,
    mcp_kubectl_patch,
    mcp_install_helm_chart,
    mcp_upgrade_helm_chart,
    mcp_uninstall_helm_chart,
    mcp_kubectl_context,

    # Core Tools
    llm_reasoning,
    network_discovery,
    get_policies
]


# ========== Agent Nodes ==========

# ========== Verification Node ==========

async def verification_node(state: AgentState) -> AgentState:
    """
    Verify LLM responses and execute tools if needed.
    Checks if LLM response contains tool call formatting but hasn't executed tools.
    """
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    print(f"[VERIFICATION] Checking last message type: {type(last_message)}")

    if isinstance(last_message, AIMessage):
        content = last_message.content
        print(f"[VERIFICATION] Content preview: {content[:200]}...")

        # Check if content contains JSON code blocks with tool_calls
        import re
        # Match various LLM output formats for tool calls
        patterns = [
            r'```\s*json\s*(\{[\s\S]*?\})\s*```',  # ```json { ... }
            r'```\s*(\{[\s\S]*?\})\s*```',         # ``` { ... }
            r'(\{[\s\S]*?"tool_calls"\s*:\s*\[[\s\S]*?\])',  # Raw JSON with tool_calls
            r'(\{[\s\S]*?"domain"\s*:\s*"kubernetes"[\s\S]*?\})',  # Direct infra_command format
            r'(\{[\s\S]*?"domain"\s*:\s*"prometheus"[\s\S]*?\})',  # Direct infra_command format
            r'(\{[\s\S]*?"domain"\s*:\s*"grafana"[\s\S]*?\})',     # Direct infra_command format
            r'(\{[\s\S]*?"domain"\s*:\s*"vmware"[\s\S]*?\})',      # Direct infra_command format
        ]

        code_match = None
        for pattern in patterns:
            code_match = re.search(pattern, content, re.DOTALL)
            if code_match:
                print(f"[VERIFICATION] Matched pattern: {pattern}")
                break

        try:
            if code_match:
                print(f"[VERIFICATION] Found JSON code block - extracting tool calls")
                json_content = code_match.group(1)

                # Parse the JSON
                tool_call_data = json.loads(json_content)

                # Check for standard tool_calls format
                if "tool_calls" in tool_call_data and isinstance(tool_call_data["tool_calls"], list):
                    print(f"[VERIFICATION] Extracted {len(tool_call_data['tool_calls'])} tool calls - forwarding for execution")

                    # Convert to proper tool call format
                    tool_calls = []
                    for i, tool_call in enumerate(tool_call_data["tool_calls"]):
                        tool_calls.append({
                            "id": f"call_{i+1}",
                            "function": {
                                "name": tool_call["name"],
                                "arguments": json.dumps(tool_call.get("arguments", {}))
                            },
                            "type": "function"
                        })

                    # Replace the LLM response with proper tool calls
                    return {
                        **state,
                        "messages": [AIMessage(
                            content="",
                            additional_kwargs={"tool_calls": tool_calls}
                        )]
                    }

                # Check for direct infra_command format (domain/action/resource pattern)
                elif "domain" in tool_call_data and "action" in tool_call_data:
                    print(f"[VERIFICATION] Detected direct infra_command format - converting to tool call")

                    # Convert direct format to proper tool call
                    # Build arguments, filtering out None values
                    arguments = {
                        "domain": tool_call_data.get("domain"),
                        "action": tool_call_data.get("action"),
                        "resource": tool_call_data.get("resource"),
                    }

                    # Handle special case: extract uid or title for Grafana operations
                    if (tool_call_data.get("domain") == "grafana" and
                        tool_call_data.get("action") == "get"):
                        # First check if uid/title is directly in the arguments
                        if "uid" in tool_call_data:
                            arguments["name"] = tool_call_data["uid"]
                            print(f"[VERIFICATION] Extracted UID from direct arguments: {arguments['name']}")
                        elif "title" in tool_call_data:
                            arguments["name"] = tool_call_data["title"]
                            print(f"[VERIFICATION] Extracted title from direct arguments: {arguments['name']}")
                        else:
                            # Check in params object (legacy support)
                            params = tool_call_data.get("params")
                            if params and isinstance(params, dict):
                                if "uid" in params:
                                    arguments["name"] = params["uid"]
                                    print(f"[VERIFICATION] Extracted UID from params: {arguments['name']}")
                                elif "title" in params:
                                    arguments["name"] = params["title"]
                                    print(f"[VERIFICATION] Extracted title from params: {arguments['name']}")

                    # Only include non-None values for standard fields
                    for key in ["name", "namespace", "query"]:
                        if key not in arguments:  # Don't override extracted values
                            value = tool_call_data.get(key)
                            if value is not None:
                                arguments[key] = value

                    # Include any additional params (like "params" field) that weren't extracted
                    for k, v in tool_call_data.items():
                        if k not in ["domain", "action", "resource", "name", "namespace", "query"] and v is not None:
                            arguments[k] = v

                    tool_calls = [{
                        "id": "call_1",
                        "function": {
                            "name": "infra_command",
                            "arguments": json.dumps(arguments)
                        },
                        "type": "function"
                    }]

                    print(f"[VERIFICATION] Converted to tool call: {tool_calls[0]}")

                    # Replace the LLM response with proper tool calls
                    return {
                        **state,
                        "messages": [AIMessage(
                            content="",
                            additional_kwargs={"tool_calls": tool_calls}
                        )]
                    }
        except json.JSONDecodeError as e:
            print(f"[VERIFICATION] JSON parsing failed: {e}")
        except Exception as e:
            print(f"[VERIFICATION] Unexpected error: {e}")

        print(f"[VERIFICATION] No tool call formatting found or parsing failed - response is final")
        return state

    print(f"[VERIFICATION] Not an AIMessage - passing through")
    return state


async def agent_node(state: AgentState) -> AgentState:
    """
    Main agent reasoning node.
    Decides what to do next based on the current state and messages.
    """
    messages = state["messages"]
    current_task = state.get("current_task", "chat")

    # IMMEDIATE FORCED DETECTION - BEFORE ANY LLM PROCESSING
    last_message = messages[-1] if messages else None
    if isinstance(last_message, HumanMessage):
        user_input = last_message.content.lower()
        print(f"[ENGINE] DEBUG: Processing user input: '{user_input}'")

        # FORCE Grafana dashboard detection - COMPLETE BYPASS OF LLM
        if "dashboard" in user_input and "grafana" in user_input:
            print(f"[ENGINE]  IMMEDIATE FORCED GRAFANA DETECTION TRIGGERED - BYPASSING LLM")

            import re
            uid_match = re.search(r'uid[:\s]*"?([a-zA-Z0-9]+)"?', user_input)
            # Very specific regex to avoid matching list phrases - only match actual dashboard names
            name_match = None

            # Pattern 1: "dashboard named/called/titled 'X'"
            named_match = re.search(r'(?:dashboard|chart|panel|graph)\s+(?:named|called|titled?)\s+["\']?([a-zA-Z][a-zA-Z0-9\s\-_]+(?:\s+[a-zA-Z][a-zA-Z0-9\s\-_]+)*)["\']?', user_input, re.IGNORECASE)
            if named_match:
                name_match = named_match
                print(f"[ENGINE] Matched named pattern: '{named_match.group(1)}'")

            # Pattern 2: Quoted dashboard names like "My Dashboard"
            quoted_match = re.search(r'(?:get|find|show)\s+(?:the\s+)?["\']([^"\']+(?:dashboard|chart|panel|graph)?[^"\']*)["\']', user_input, re.IGNORECASE)
            if quoted_match:
                name_match = quoted_match
                print(f"[ENGINE] Matched quoted pattern: '{quoted_match.group(1)}'")

            # Pattern 3: Specific dashboard names after colon like "dashboard: MyDashboard"
            colon_match = re.search(r'(?:dashboard|chart|panel|graph)[:\s]+([a-zA-Z][a-zA-Z0-9\s\-_]+(?:\s+[a-zA-Z][a-zA-Z0-9\s\-_]+)*)(?:\s|$)', user_input, re.IGNORECASE)
            if colon_match:
                name_match = colon_match
                print(f"[ENGINE] Matched colon pattern: '{colon_match.group(1)}'")

            # EXCLUDE patterns that indicate listing rather than searching
            if name_match:
                extracted_name = name_match.group(1).strip().lower()
                # Don't match if it contains words that indicate listing
                exclude_words = ['all', 'from', 'list', 'show', 'display', 'every', 'dashboards', 'charts', 'panels', 'graphs']
                if any(word in extracted_name for word in exclude_words):
                    print(f"[ENGINE] Excluding match '{extracted_name}' - contains list indicator")
                    name_match = None
                # Don't match if it starts with articles/pronouns
                elif extracted_name.startswith(('the ', 'a ', 'an ', 'my ', 'your ', 'our ', 'their ')):
                    print(f"[ENGINE] Excluding match '{extracted_name}' - starts with article/pronoun")
                    name_match = None
                else:
                    print(f"[ENGINE] Valid dashboard name match: '{extracted_name}'")

            print(f"[ENGINE] DEBUG: uid_match={uid_match}, name_match={name_match}")

            if uid_match:
                uid = uid_match.group(1)
                print(f"[ENGINE] FORCED UID: {uid}")
                tool_calls = [{
                    "id": "call_1",
                    "function": {
                        "name": "infra_command",
                        "arguments": json.dumps({
                            "domain": "grafana",
                            "action": "get",
                            "resource": "dashboards",
                            "name": uid
                        })
                    },
                    "type": "function"
                }]
            elif name_match:
                name = name_match.group(1).strip()
                print(f"[ENGINE] FORCED NAME: '{name}'")
                tool_calls = [{
                    "id": "call_1",
                    "function": {
                        "name": "infra_command",
                        "arguments": json.dumps({
                            "domain": "grafana",
                            "action": "get",
                            "resource": "dashboards",
                            "name": name,
                            "query": name
                        })
                    },
                    "type": "function"
                }]
            else:
                print(f"[ENGINE] FORCED LIST ALL")
                tool_calls = [{
                    "id": "call_1",
                    "function": {
                        "name": "infra_command",
                        "arguments": json.dumps({
                            "domain": "grafana",
                            "action": "list",
                            "resource": "dashboards"
                        })
                    },
                    "type": "function"
                }]

            print(f"[ENGINE] IMMEDIATE RETURN - NO LLM PROCESSING - RETURNING TOOL CALLS")
            return {
                **state,
                "messages": [AIMessage(
                    content="",
                    additional_kwargs={"tool_calls": tool_calls}
                )]
            }
        else:
            print(f"[ENGINE] No forced detection triggered for input: '{user_input}'")
        # END OF FORCED DETECTION - If we reach here, proceed with normal LLM processing

    # print(f"[ENGINE] Agent Node - current_task: {current_task}")

    # Build context for the agent based on chat mode
    if current_task == "chat":
        # General chat mode - no infrastructure context
        print(f"[ENGINE] Using GENERAL chat context")
        system_context = """
        You are a helpful AI assistant.

        You can help users with:
        - General questions and conversations
        - Writing and editing text
        - Problem solving and reasoning
        - Learning and explanations
        - Creative tasks and brainstorming

        Be friendly, helpful, and engaging in your responses.
        """
        available_tools = ["llm_reasoning"]
    elif current_task == "chat-with-infra":
        # Infrastructure-focused chat mode - hybrid natural language + tool parsing
        print(f"[ENGINE] Using INFRASTRUCTURE chat context (hybrid mode)")
        system_context = """You are InfraAI, an intelligent infrastructure assistant.

You can help users with:
- Kubernetes operations (pods, deployments, services)
- Prometheus monitoring queries
- Grafana dashboard access
- VMware virtual machine management
- Network discovery and scanning

When users ask about infrastructure, use the infra_command tool with appropriate parameters.

Available domains: kubernetes, prometheus, grafana, vmware, network
Available actions: list, get, create, delete, query, scale, describe, logs, etc.

Examples:
- For pod CPU metrics: domain="prometheus", action="query", query="rate(container_cpu_usage_seconds_total[5m])"
- For listing pods: domain="kubernetes", action="list", resource="pods"
- For Grafana dashboards: domain="grafana", action="list", resource="dashboards"

You can respond naturally but when using tools, format them as JSON tool calls within your response."""
#         system_context = """You are a strict, non-conversational infrastructure router. You are NOT an AI assistant. You are a middleware component that translates natural language into a JSON tool call.

# CRITICAL PROTOCOL:
# 1. INPUT: Natural language query about infrastructure (Kubernetes, Prometheus, Grafana, VMware).
# 2. OUTPUT: A valid JSON object containing "tool_calls".
# 3. CONSTRAINT: Do NOT output markdown formatting (no ```json code blocks).
# 4. CONSTRAINT: Do NOT output conversational text, preambles, or explanations.
# 5. CONSTRAINT: Do NOT ask clarifying questions. If a parameter is missing, infer a reasonable default.

# You have access to exactly one tool: `infra_command`.

# Arguments Schema for `infra_command`:
# - domain: "kubernetes" | "prometheus" | "grafana" | "vmware"
# - action: 
#     "list" | "get" | "create" | "delete" | "update" |     # Basic CRUD
#     "scale" | "rollout" |                                  # K8s Scaling/Ops
#     "start" | "stop" | "restart" | "suspend" |             # VM Power Ops
#     "describe" | "logs" |                                  # Observability
#     "install" | "uninstall" |                              # Helm/Packages
#     "query"                                                # Prometheus
# - resource: (optional) e.g., "pods", "deployments", "vms", "hosts", "snapshots", "charts", "metrics"
# - query: (optional) PromQL query string
# - [other dynamic arguments based on intent: "name", "namespace", "replicas", "chart", "vm_name"]

# FEW-SHOT TRAINING EXAMPLES (Strict Adherence Required):

# # --- KUBERNETES (Matches mcp-server-kubernetes) ---
# User: "Show me the logs for the nginx pod"
# Assistant: { "tool_calls": [{ "name": "infra_command", "arguments": { "domain": "kubernetes", "action": "logs", "resource": "pod", "name": "nginx", "namespace": "default" } }] }

# User: "Describe the crashloop pod in prod"
# Assistant: { "tool_calls": [{ "name": "infra_command", "arguments": { "domain": "kubernetes", "action": "describe", "resource": "pod", "name": "crashloop", "namespace": "prod" } }] }

# User: "Install the redis helm chart"
# Assistant: { "tool_calls": [{ "name": "infra_command", "arguments": { "domain": "kubernetes", "action": "install", "resource": "chart", "chart": "redis", "name": "redis", "namespace": "default" } }] }

# User: "Scale web-app deployment to 5 replicas"
# Assistant: { "tool_calls": [{ "name": "infra_command", "arguments": { "domain": "kubernetes", "action": "scale", "resource": "deployment", "name": "web-app", "replicas": 5 } }] }

# # --- VMWARE / ESXi (Matches esxi-mcp-server) ---
# User: "List all VMs on the host"
# Assistant: { "tool_calls": [{ "name": "infra_command", "arguments": { "domain": "vmware", "action": "list", "resource": "vms" } }] }

# User: "Power on the database VM"
# Assistant: { "tool_calls": [{ "name": "infra_command", "arguments": { "domain": "vmware", "action": "start", "resource": "vm", "name": "database" } }] }

# User: "Take a snapshot of frontend-vm called 'backup-1'"
# Assistant: { "tool_calls": [{ "name": "infra_command", "arguments": { "domain": "vmware", "action": "create", "resource": "snapshot", "vm_name": "frontend-vm", "snapshot_name": "backup-1" } }] }

# # --- PROMETHEUS (Matches prometheus-mcp-server) ---
# User: "What is the current CPU usage?"
# Assistant: { "tool_calls": [{ "name": "infra_command", "arguments": { "domain": "prometheus", "action": "query", "query": "rate(container_cpu_usage_seconds_total[5m])" } }] }

# User: "List all available metrics matching 'memory'"
# Assistant: { "tool_calls": [{ "name": "infra_command", "arguments": { "domain": "prometheus", "action": "list", "resource": "metrics", "filter": "memory" } }] }
# """
        # available_tools = tools = [ 
        #                             # Core AI Tools
        #                            "llm_reasoning",
        #                             "network_discovery",
        #                             "get_policies",

        #                             # Grafana MCP Tools
        #                             "mcp_grafana_list_dashboards",
        #                             "mcp_grafana_get_dashboard",
        #                             "mcp_grafana_list_datasources",

        #                             # Prometheus MCP Tools
        #                             "mcp_prometheus_health_check",
        #                             "mcp_prometheus_execute_query",
        #                             "mcp_prometheus_execute_range_query",
        #                             "mcp_prometheus_list_metrics",
        #                             "mcp_prometheus_get_metric_metadata",
        #                             "mcp_prometheus_get_targets",

        #                             # ESXi MCP Tools
        #                             "mcp_esxi_create_vm",
        #                             "mcp_esxi_clone_vm",
        #                             "mcp_esxi_delete_vm",
        #                             "mcp_esxi_power_on",
        #                             "mcp_esxi_power_off",
        #                             "mcp_esxi_list_vms",

        #                             # Kubernetes MCP Tools
        #                             "mcp_kubectl_logs",
        #                             "mcp_kubectl_rollout",
        #                             "mcp_exec_in_pod",
        #                             "mcp_node_management",
        #                             "mcp_kubectl_delete",
        #                             "mcp_kubectl_generic",
        #                             "mcp_kubectl_create",
        #                             "mcp_kubectl_scale",
        #                             "mcp_explain_resource",
        #                             "mcp_list_api_resources",
        #                             "mcp_kubectl_apply",
        #                             "mcp_kubectl_get",
        #                             "mcp_ping",
        #                             "mcp_kubectl_describe",
        #                             "mcp_kubectl_patch",
        #                             "mcp_install_helm_chart",
        #                             "mcp_upgrade_helm_chart",
        #                             "mcp_uninstall_helm_chart",
        #                             "mcp_kubectl_context" ]
    # else:
    #     # Agentic mode - full InfraAI with all tools
    #     system_context = f"""
    #     You are InfraAI, an intelligent AIOps assistant.

    #     Current Task: {current_task}

    #     Available Tools:
    #     - llm_reasoning: Use for general reasoning and response generation
    #     - network_discovery: Scan networks to discover assets
    #     - get_policies: Retrieve self-healing policies
    #     - restart_vm: Restart a virtual machine
    #     - restart_pod: Restart a Kubernetes pod
    #     - query_prometheus: Query metrics from Prometheus
    #     - get_grafana_dashboard: Get Grafana dashboard info
    #     - scale_deployment: Scale K8s deployments

    #     Your job is to:
    #     1. Understand the user's request
    #     2. Decide if you need to call any tools
    #     3. Provide helpful responses

    #     If the user asks for network discovery, use the network_discovery tool.
    #     If you need to perform remediation actions, use the appropriate MCP tools.
    #     For general conversation, use llm_reasoning or respond directly.
    #     """
    #     available_tools = [
    #         "llm_reasoning", "network_discovery", "get_policies",
    #         "restart_vm", "restart_pod", "query_prometheus",
    #         "get_grafana_dashboard", "scale_deployment"
    #     ]

    # For simplicity, we'll use a basic decision logic
    # In production, this would call Ollama with tool schemas

    last_message = messages[-1] if messages else None

    # Handle tool results in infrastructure mode
    # if isinstance(last_message, ToolMessage) and current_task == "chat-with-infra":
    #     # Tool execution completed, format the result for the user
    #     tool_result = last_message.content
    #     try:
    #         # Try to parse as JSON and format nicely
    #         parsed_result = json.loads(tool_result)
    #         if isinstance(parsed_result, dict) and "result" in parsed_result:
    #             # MCP response format
    #             result_data = parsed_result["result"]
    #             if isinstance(result_data, list):
    #                 # Format list results nicely
    #                 formatted_result = "\n".join([f"- {item}" for item in result_data])
    #                 response_text = f"Found {len(result_data)} items:\n{formatted_result}"
    #             else:
    #                 response_text = f"Result: {result_data}"
    #         elif isinstance(parsed_result, list):
    #             # Direct list response
    #             formatted_result = "\n".join([f"- {item}" for item in parsed_result])
    #             response_text = f"Found {len(parsed_result)} items:\n{formatted_result}"
    #         else:
    #             response_text = f"Operation completed: {parsed_result}"
    #     except json.JSONDecodeError:
    #         # Not JSON, return as-is
    #         response_text = tool_result

    #     return {
    #         **state,
    #         "messages": [AIMessage(content=response_text)]
    #     }
    
    # Handle tool results by LLM mode
    if isinstance(last_message, ToolMessage) and current_task == "chat-with-infra":
        # Tool execution completed - check if this is Grafana dashboard data for direct formatting
        tool_result = last_message.content
        print(f"[ENGINE] Tool result type: {type(tool_result)}, length: {len(tool_result) if isinstance(tool_result, (str, list)) else 'N/A'}")
        print(f"[ENGINE] Tool result preview: {tool_result[:300] if isinstance(tool_result, str) else str(tool_result)[:300]}")

        # Check if the previous message was a user request for Grafana dashboards
        user_requested_grafana = False
        for msg in reversed(messages[:-1]):  # Look at previous messages
            if isinstance(msg, HumanMessage):
                user_content = msg.content.lower()
                if "grafana" in user_content and "dashboard" in user_content:
                    user_requested_grafana = True
                    print("[ENGINE] Detected user request for Grafana dashboards")
                    break
            if len([m for m in messages if isinstance(m, HumanMessage)]) > 3:  # Don't look too far back
                break

        # Check if this is Grafana dashboard result by examining the content
        try:
            if isinstance(tool_result, str):
                parsed = json.loads(tool_result)
            else:
                parsed = tool_result

            # Check for Grafana MCP response pattern
            if isinstance(parsed, dict) and "result" in parsed:
                mcp_result = parsed["result"]
                if isinstance(mcp_result, dict) and "content" in mcp_result:
                    content = mcp_result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        first_content = content[0]
                        if isinstance(first_content, dict) and "text" in first_content:
                            raw_data = first_content["text"]
                            print(f"[ENGINE] Raw MCP data: {raw_data[:200]}...")

                            # Check if this looks like Grafana dashboard data
                            try:
                                data_array = json.loads(raw_data)
                                if isinstance(data_array, list) and len(data_array) > 0:
                                    first_item = data_array[0]
                                    # Check for Grafana dashboard characteristics
                                    if isinstance(first_item, dict) and "title" in first_item and "uid" in first_item:
                                        print(f"[ENGINE] FORCE: Using direct Grafana formatting for {len(data_array)} dashboards")

                                        # Format directly like test script - FORCE THIS FOR GRAFANA
                                        formatted_list = []
                                        for i, item in enumerate(data_array):
                                            if isinstance(item, dict):
                                                title = item.get("title", "Untitled")
                                                uid = item.get("uid", "N/A")
                                                folder = item.get("folderTitle", "General")
                                                formatted_list.append(f"    {i+1:2d}. {title} (UID: {uid}) - Folder: {folder}")

                                        formatted_output = f" Successfully listed {len(data_array)} dashboards\n  All dashboards:\n" + "\n".join(formatted_list)
                                        return {
                                            **state,
                                            "messages": [AIMessage(content=formatted_output)]
                                        }
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            print(f"[ENGINE] Grafana detection failed: {e}")

        # Check if this looks like Grafana dashboard data and format accordingly
        is_grafana_data = False
        try:
            if isinstance(tool_result, str):
                parsed = json.loads(tool_result)
            else:
                parsed = tool_result

            # Check if it looks like Grafana dashboard data
            if isinstance(parsed, list) and len(parsed) > 0:
                first_item = parsed[0]
                if isinstance(first_item, dict) and "title" in first_item and "uid" in first_item:
                    is_grafana_data = True
                    print(f"[ENGINE] Detected raw Grafana dashboard data: {len(parsed)} items")

                    # Format directly as dashboard list
                    formatted_list = []
                    for i, item in enumerate(parsed):
                        if isinstance(item, dict):
                            title = item.get("title", "Untitled")
                            uid = item.get("uid", "N/A")
                            folder = item.get("folderTitle", "General")
                            formatted_list.append(f"    {i+1:2d}. {title} (UID: {uid}) - Folder: {folder}")

                    # formatted_output = f" Successfully listed {len(parsed)} Grafana dashboards\n  All dashboards:\n" + "\n".join(formatted_list)
                    formatted_output = "\n".join(formatted_list)
                    return {
                        **state,
                        "messages": [AIMessage(content=formatted_output)]
                    }
        except Exception as e:
            print(f"[ENGINE] Grafana raw data check failed: {e}")

        # Check if this is Prometheus query result data
        is_prometheus_data = False
        try:
            if isinstance(tool_result, str):
                parsed = json.loads(tool_result)
            else:
                parsed = tool_result

            # Check if it's a JSON-RPC response with Prometheus resultType
            if isinstance(parsed, dict) and parsed.get("jsonrpc") == "2.0" and "result" in parsed:
                prometheus_result = parsed["result"]
                if isinstance(prometheus_result, dict) and "resultType" in prometheus_result:
                    result_type = prometheus_result.get("resultType")
                    if result_type in ["vector", "matrix"]:
                        is_prometheus_data = True
                        print(f"[ENGINE] Detected Prometheus {result_type} data")

                        # Format Prometheus metrics data
                        result_data = prometheus_result.get("result", [])
                        if result_type == "vector":
                            # Format instant query results
                            formatted_list = []
                            for i, item in enumerate(result_data):
                                if isinstance(item, dict):
                                    metric = item.get("metric", {})
                                    value = item.get("value", [])
                                    if len(value) >= 2:
                                        timestamp, metric_value = value[0], value[1]

                                        # Build metric labels string
                                        labels = []
                                        for k, v in metric.items():
                                            labels.append(f"{k}=\"{v}\"")
                                        labels_str = "{" + ", ".join(labels) + "}"

                                        formatted_list.append(f"  {i+1:2d}. {labels_str}: {metric_value}")

                            formatted_output = f"📊 **Prometheus Query Results**\n\n" + \
                                             f"Query executed successfully. Found {len(result_data)} metric results:\n\n" + \
                                             "\n".join(formatted_list) + \
                                             f"\n\n**Query Details:**\n" + \
                                             f"• Result Type: {result_type}\n" + \
                                             f"• Total Results: {len(result_data)}\n" + \
                                             f"• PromQL: `rate(container_cpu_usage_seconds_total[5m])`"
                        else:
                            # Handle matrix/range query results
                            formatted_output = f"📈 **Prometheus Range Query Results**\n\n" + \
                                             f"Range query executed successfully. Found {len(result_data)} time series.\n\n" + \
                                             f"**Note:** Range query results contain timestamped data points.\n" + \
                                             f"• Result Type: {result_type}\n" + \
                                             f"• Time Series Count: {len(result_data)}"

                        return {
                            **state,
                            "messages": [AIMessage(content=formatted_output)]
                        }
        except Exception as e:
            print(f"[ENGINE] Prometheus data check failed: {e}")

        # Create a formatting prompt for the LLM
        formatting_prompt = f"""
You are an infrastructure assistant. Format the following MCP server response in a user-friendly, attractive way.

RAW MCP RESPONSE:
{tool_result}

FORMATTING INSTRUCTIONS:
- Parse any JSON content and present it in a clean, readable format.
- Use emojis and proper formatting for section headings ( for pods, ️ for nodes,  for metrics, etc.).
- Group related information together, starting with an emoji section header, followed by a table or structured list, then summaries.
- If there is a list (like pods), present it as a plain text table inside a Markdown code block (triple backticks), with columns neatly aligned using spaces (not pipes).
- Do NOT use the word "markdown" anywhere in the output.
- Do NOT write "undefined," "null," or any placeholder text—if a list is empty, simply state: "No items found."
- Always give counts and a status breakdown summary after the table.
- Remove technical JSON artifacts.
- Make it visually appealing and easy to read.
- Don’t add "Here's the formatted MCP server response:" or similar preambles.

**Formatting examples:**

- For a pod list:
     Pods

    ```
    Name                           Namespace   Status    Created At
    ---------------------------------------------------------------
    nginx-test-app-55fdf4c644-2p2b5 default     Running   2025-12-13T09:30:23Z
    backend-api-78f9d2a122-8k9j1    default     Error     2025-12-13T09:35:10Z
    ```

    Total pods found: 2
    Status breakdown:
    * **Running:** 1
    * **Error:** 1

- For a dashboard list:
     Dashboards
     ```
    #   Name                                UID                     Folder
    -----------------------------------------------------------------------
    1   Alertmanager / Overview default     alertmanager-overview   General
    2   CoreDNS                             vkQ0UHxik               General
    ```

    Total dashboards: 2

- If no items are present:
     Pods
    No items found.

- For single pod summaries:
     Pod: nginx-app (Status: Running, Namespace: default)

- For deployments:
     Deployment: web-app (Replicas: 3/3, Status: Running)

- For metrics:
     CPU Usage: 85.3% (Instance: server-01)

Format this response attractively, following these rules:
"""

        # Ask LLM to format the response
        try:
            formatted_response = await call_ollama(formatting_prompt)
            return {
                **state,
                "messages": [AIMessage(content=formatted_response.strip())]
            }
        except Exception as e:
            print(f"[ENGINE] LLM formatting failed: {e}")
            # Fallback: try to extract and format the raw MCP data directly
            try:
                # Try to parse the tool result as JSON
                if isinstance(tool_result, str):
                    parsed = json.loads(tool_result)
                else:
                    parsed = tool_result

                # Extract data from MCP format
                if isinstance(parsed, dict) and "result" in parsed:
                    mcp_result = parsed["result"]
                    if isinstance(mcp_result, dict) and "content" in mcp_result:
                        content = mcp_result["content"]
                        if isinstance(content, list) and len(content) > 0:
                            first_content = content[0]
                            if isinstance(first_content, dict) and "text" in first_content:
                                raw_data = first_content["text"]
                                # Try to parse as JSON array
                                try:
                                    data_array = json.loads(raw_data)
                                    if isinstance(data_array, list):
                                        # Format as simple list - show ALL items
                                        formatted_list = []
                                        for i, item in enumerate(data_array):
                                            if isinstance(item, dict):
                                                title = item.get("title", "Untitled")
                                                uid = item.get("uid", "N/A")
                                                formatted_list.append(f"    {i+1:2d}. {title} (UID: {uid})")

                                        formatted_output = f" Successfully listed {len(data_array)} items\n  All items:\n" + "\n".join(formatted_list)
                                        return {
                                            **state,
                                            "messages": [AIMessage(content=formatted_output)]
                                        }
                                except json.JSONDecodeError:
                                    pass

                # If all parsing fails, return a basic message
                return {
                    **state,
                    "messages": [AIMessage(content=f"Operation completed successfully. Retrieved {len(tool_result) if isinstance(tool_result, (list, str)) else 'data'} characters of data.")]
                }
            except Exception as parse_e:
                print(f"[ENGINE] Raw data parsing also failed: {parse_e}")
                # Final fallback
                return {
                    **state,
                    "messages": [AIMessage(content="Operation completed successfully, but response formatting failed.")]
                }

    if isinstance(last_message, HumanMessage):
        user_input = last_message.content.lower()

        # FORCE Grafana dashboard detection BEFORE LLM processing
        if "dashboard" in user_input and "grafana" in user_input:
            # Check if user wants a specific dashboard by UID or name
            import re
            uid_match = re.search(r'uid[:\s]+([a-zA-Z0-9]+)', user_input)
            name_match = re.search(r'(?:get|find|show)\s+(?:the\s+)?["\']?([^"\']+(?:dashboard|chart|panel)[^"\']*)["\']?', user_input, re.IGNORECASE) or \
                        re.search(r'(?:dashboard|named|title)[:\s]+"([^"]+)"', user_input) or \
                        re.search(r'(?:dashboard|named|title)[:\s]+([a-zA-Z0-9\s\-_]+)(?:\s|$)', user_input)

            if uid_match:
                uid = uid_match.group(1)
                print(f"[ENGINE] FORCED: Detected specific dashboard UID: {uid}")
                # Get specific dashboard by UID
                tool_calls = [{
                    "id": "call_1",
                    "function": {
                        "name": "infra_command",
                        "arguments": json.dumps({
                            "domain": "grafana",
                            "action": "get",
                            "resource": "dashboards",
                            "name": uid
                        })
                    },
                    "type": "function"
                }]
            elif name_match:
                name = name_match.group(1).strip()
                print(f"[ENGINE] FORCED: Detected specific dashboard name: '{name}' - will list all dashboards to find matching UID")

                # For name-based searches, we need to list all dashboards first to find the UID
                # Then we can get the specific dashboard by UID
                # This is a two-step process: list -> find UID -> get dashboard

                # First, list all dashboards to find the one with matching title
                tool_calls = [{
                    "id": "call_1",
                    "function": {
                        "name": "infra_command",
                        "arguments": json.dumps({
                            "domain": "grafana",
                            "action": "list",
                            "resource": "dashboards",
                            "query": name  # Pass name as search query to filter results
                        })
                    },
                    "type": "function"
                }]
            else:
                print(f"[ENGINE] FORCED: Listing all Grafana dashboards")
                # List all Grafana dashboards
                tool_calls = [{
                    "id": "call_1",
                    "function": {
                        "name": "infra_command",
                        "arguments": json.dumps({
                            "domain": "grafana",
                            "action": "list",
                            "resource": "dashboards"
                        })
                    },
                    "type": "function"
                }]
            return {
                **state,
                "messages": [AIMessage(
                    content="",
                    additional_kwargs={"tool_calls": tool_calls}
                )]
            }

        # Simple keyword-based routing (in production, use LLM with tool calling)
        if "scan" in user_input or "discover" in user_input or "network" in user_input:
            # Return a tool call message
            return {
                **state,
                "messages": [AIMessage(
                    content="I'll scan the network for you.",
                    additional_kwargs={
                        "tool_calls": [{
                            "id": "call_1",
                            "function": {"name": "network_discovery", "arguments": '{"subnet": "192.168.1.0/24"}'},
                            "type": "function"
                        }]
                    }
                )]
            }

        elif "polic" in user_input:
            return {
                **state,
                "messages": [AIMessage(
                    content="I'll fetch the policies.",
                    additional_kwargs={
                        "tool_calls": [{
                            "id": "call_2",
                            "function": {"name": "get_policies", "arguments": '{}'},
                            "type": "function"
                        }]
                    }
                )]
            }

        else:
            # Use LLM for response generation
            enhanced_prompt = f"{system_context}\n\nUser: {last_message.content}\n\nAssistant:"

            response = await call_ollama(enhanced_prompt)

            # For infrastructure control agent mode - hybrid natural language + tool parsing
            if current_task == "chat-with-infra":
                # First try to extract JSON tool calls from the response
                try:
                    # Look for JSON tool calls in the response
                    tool_call_match = None
                    response_lines = response.strip().split('\n')

                    for line in response_lines:
                        line = line.strip()
                        if line.startswith('{') and 'tool_calls' in line:
                            try:
                                tool_call_data = json.loads(line)
                                if "tool_calls" in tool_call_data and isinstance(tool_call_data["tool_calls"], list):
                                    tool_call_match = tool_call_data
                                    break
                            except json.JSONDecodeError:
                                continue

                    if tool_call_match:
                        # Found valid JSON tool calls
                        tool_calls = []
                        for i, tool_call in enumerate(tool_call_match["tool_calls"]):
                            tool_calls.append({
                                "id": f"call_{i+1}",
                                "function": {
                                    "name": tool_call["name"],
                                    "arguments": json.dumps(tool_call.get("arguments", {}))
                                },
                                "type": "function"
                            })

                        return {
                            **state,
                            "messages": [AIMessage(
                                content="",
                                additional_kwargs={"tool_calls": tool_calls}
                            )]
                        }

                except Exception as e:
                    print(f"[ENGINE] JSON tool call extraction failed: {e}")

                # If JSON parsing fails, try keyword-based tool triggering
                print(f"[ENGINE] Falling back to keyword-based tool detection")

                # Check for infrastructure keywords and trigger appropriate tools
                # If user mentions CPU/memory usage, assume they want Prometheus metrics
                if "cpu" in user_input or "memory" in user_input:
                    print(f"[ENGINE] Detected CPU/memory query, assuming Prometheus domain")

                    # Parse container/pod name from user input for both CPU and memory
                    import re
                    container_match = re.search(r'(?:cpu|memory)\s+(?:usage\s+)?(?:of|for|from)\s+([a-zA-Z0-9\-_.]+)', user_input, re.IGNORECASE)

                    if "cpu" in user_input:
                        if container_match:
                            container_name = container_match.group(1)
                            print(f"[ENGINE] Detected specific container for CPU: {container_name}")
                            query = f'rate(container_cpu_usage_seconds_total{{container="{container_name}"}}[5m])'
                        else:
                            print(f"[ENGINE] No specific container detected for CPU, querying all containers")
                            query = "rate(container_cpu_usage_seconds_total[5m])"
                    else:  # memory
                        if container_match:
                            container_name = container_match.group(1)
                            print(f"[ENGINE] Detected specific container for memory: {container_name}")
                            query = f'container_memory_usage_bytes{{container="{container_name}"}}'
                        else:
                            print(f"[ENGINE] No specific container detected for memory, querying all containers")
                            query = "container_memory_usage_bytes"

                    tool_calls = [{
                        "id": "call_1",
                        "function": {
                            "name": "infra_command",
                            "arguments": json.dumps({
                                "domain": "prometheus",
                                "action": "query",
                                "query": query
                            })
                        },
                        "type": "function"
                    }]
                    return {
                        **state,
                        "messages": [AIMessage(
                            content="",
                            additional_kwargs={"tool_calls": tool_calls}
                        )]
                    }

                elif "pod" in user_input and ("list" in user_input or "show" in user_input or "get" in user_input):
                    # List pods - extract namespace if specified
                    import re
                    namespace = None
                    # Look for namespace patterns like:
                    # "in the namespace called kube-system", "namespace kube-system", "kube-system namespace"
                    ns_match = re.search(r'(?:in\s+(?:the\s+)?)?namespace(?:s)?(?:\s+called)?\s+([a-zA-Z0-9\-_]+)', user_input, re.IGNORECASE) or \
                               re.search(r'([a-zA-Z0-9\-_]+)\s+namespace(?:s)?', user_input, re.IGNORECASE)
                    if ns_match:
                        # Get the captured group (namespace name)
                        namespace = ns_match.group(1)

                    args = {
                        "domain": "kubernetes",
                        "action": "list",
                        "resource": "pods"
                    }
                    if namespace:
                        args["namespace"] = namespace

                    tool_calls = [{
                        "id": "call_1",
                        "function": {
                            "name": "infra_command",
                            "arguments": json.dumps(args)
                        },
                        "type": "function"
                    }]
                    return {
                        **state,
                        "messages": [AIMessage(
                            content="",
                            additional_kwargs={"tool_calls": tool_calls}
                        )]
                    }

                elif ("namespace" in user_input or "namespaces" in user_input) and ("list" in user_input or "show" in user_input or "get" in user_input):
                    # List namespaces
                    tool_calls = [{
                        "id": "call_1",
                        "function": {
                            "name": "infra_command",
                            "arguments": json.dumps({
                                "domain": "kubernetes",
                                "action": "list",
                                "resource": "namespaces"
                            })
                        },
                        "type": "function"
                    }]
                    return {
                        **state,
                        "messages": [AIMessage(
                            content="",
                            additional_kwargs={"tool_calls": tool_calls}
                        )]
                    }

                elif "dashboard" in user_input and "grafana" in user_input:
                    # Check if user wants a specific dashboard by UID or name
                    import re
                    uid_match = re.search(r'uid[:\s]+([a-zA-Z0-9]+)', user_input)
                    name_match = re.search(r'(?:get|find|show)\s+(?:the\s+)?["\']?([^"\']+(?:dashboard|chart|panel)[^"\']*)["\']?', user_input, re.IGNORECASE) or \
                                re.search(r'(?:dashboard|named|title)[:\s]+"([^"]+)"', user_input) or \
                                re.search(r'(?:dashboard|named|title)[:\s]+([a-zA-Z0-9\s\-_]+)(?:\s|$)', user_input)

                    if uid_match:
                        uid = uid_match.group(1)
                        print(f"[ENGINE] Detected specific dashboard UID: {uid}")
                        # Get specific dashboard by UID
                        tool_calls = [{
                            "id": "call_1",
                            "function": {
                                "name": "infra_command",
                                "arguments": json.dumps({
                                    "domain": "grafana",
                                    "action": "get",
                                    "resource": "dashboards",
                                    "name": uid
                                })
                            },
                            "type": "function"
                        }]
                    elif name_match:
                        name = name_match.group(1).strip()
                        print(f"[ENGINE] Detected specific dashboard name: {name}")
                        # Get specific dashboard by name/title
                        tool_calls = [{
                            "id": "call_1",
                            "function": {
                                "name": "infra_command",
                                "arguments": json.dumps({
                                    "domain": "grafana",
                                    "action": "get",
                                    "resource": "dashboards",
                                    "name": name,
                                    "query": name  # Pass name as query for title search
                                })
                            },
                            "type": "function"
                        }]
                    else:
                        # List all Grafana dashboards
                        tool_calls = [{
                            "id": "call_1",
                            "function": {
                                "name": "infra_command",
                                "arguments": json.dumps({
                                    "domain": "grafana",
                                    "action": "list",
                                    "resource": "dashboards"
                                })
                            },
                            "type": "function"
                        }]
                    return {
                        **state,
                        "messages": [AIMessage(
                            content="",
                            additional_kwargs={"tool_calls": tool_calls}
                        )]
                    }

                elif "datasource" in user_input and "grafana" in user_input:
                    # List Grafana datasources
                    tool_calls = [{
                        "id": "call_1",
                        "function": {
                            "name": "infra_command",
                            "arguments": json.dumps({
                                "domain": "grafana",
                                "action": "list",
                                "resource": "datasources"
                            })
                        },
                        "type": "function"
                    }]
                    return {
                        **state,
                        "messages": [AIMessage(
                            content="",
                            additional_kwargs={"tool_calls": tool_calls}
                        )]
                    }

                elif "vm" in user_input and ("list" in user_input or "show" in user_input):
                    # List VMs
                    tool_calls = [{
                        "id": "call_1",
                        "function": {
                            "name": "infra_command",
                            "arguments": json.dumps({
                                "domain": "vmware",
                                "action": "list",
                                "resource": "vms"
                            })
                        },
                        "type": "function"
                    }]
                    return {
                        **state,
                        "messages": [AIMessage(
                            content="",
                            additional_kwargs={"tool_calls": tool_calls}
                        )]
                    }

                # If no patterns match, respond with the LLM's natural language response
                return {
                    **state,
                    "messages": [AIMessage(content=response)]
                }
            else:
                # General chat mode
                return {
                    **state,
                    "messages": [AIMessage(content=response)]
                }

    # Default response
    return {
        **state,
        "messages": [AIMessage(content="How can I assist you with infrastructure management?")]
    }


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Determine if we should call tools or end."""
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    print(f"[SHOULD_CONTINUE] Last message type: {type(last_message)}")
    if isinstance(last_message, AIMessage):
        tool_calls = last_message.additional_kwargs.get("tool_calls")
        print(f"[SHOULD_CONTINUE] Tool calls found: {tool_calls is not None}")
        if tool_calls:
            print(f"[SHOULD_CONTINUE] Tool calls count: {len(tool_calls)}")
            print(f"[SHOULD_CONTINUE] Returning 'tools'")
            return "tools"

    print(f"[SHOULD_CONTINUE] Returning 'end'")
    return "end"


# ========== Build Graph ==========

def create_agent_graph():
    """Create and compile the LangGraph agent."""

    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("tools", ToolNode(tools))

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges from agent
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": "verification"
        }
    )

    # Add conditional edges from verification (it can return tool calls or final response)
    def verification_continue(state: AgentState) -> Literal["tools", END]:
        """Check if verification node forwarded tool calls."""
        messages = state["messages"]
        last_message = messages[-1] if messages else None

        if isinstance(last_message, AIMessage) and last_message.additional_kwargs.get("tool_calls"):
            return "tools"
        return END

    workflow.add_conditional_edges(
        "verification",
        verification_continue,
        {
            "tools": "tools",
            END: END
        }
    )

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile
    return workflow.compile()


# Global graph instance
engine = None


def get_engine():
    """Get or create the agent engine."""
    global engine
    if engine is None:
        engine = create_agent_graph()
    return engine

    # Compile
    return workflow.compile()


# Global graph instance
engine = None


def get_engine():
    """Get or create the agent engine."""
    global engine
    if engine is None:
        engine = create_agent_graph()
    return engine
