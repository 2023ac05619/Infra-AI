#!/usr/bin/env python3
"""
Kubernetes MCP Client Test Script
Tests the HTTP JSON-RPC interface of the Kubernetes MCP server
"""

import json
import requests
import sys
from typing import Dict, Any, Optional

class KubernetesMCPClient:
    def __init__(self, base_url: str = "http://localhost:8082"):
        self.base_url = base_url
        self.jsonrpc_url = f"{base_url}/jsonrpc"
        self.request_id = 1

    def _make_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a JSON-RPC request to the MCP server"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id
        }

        self.request_id += 1

        try:
            response = requests.post(self.jsonrpc_url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f" Request failed: {e}")
            return {"error": str(e)}

    def health_check(self) -> bool:
        """Check if the server is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200 and response.json().get("status") == "ok"
        except:
            return False

    def list_tools(self) -> Dict[str, Any]:
        """List all available tools"""
        return self._make_request("tools/list")

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a specific tool"""
        params = {
            "name": tool_name,
            "arguments": arguments or {}
        }
        return self._make_request("tools/call", params)

    def list_pods(self, namespace: str = "default") -> Dict[str, Any]:
        """List all pods in a namespace"""
        return self.call_tool("kubectl_get", {
            "resourceType": "pods",
            "namespace": namespace,
            "output": "json"
        })

    def ping(self) -> Dict[str, Any]:
        """Ping the server"""
        return self.call_tool("ping")

def main():
    client = KubernetesMCPClient()

    print(" Testing Kubernetes MCP Server (HTTP JSON-RPC)")
    print("=" * 50)

    # Health check
    print(" Health Check...")
    if client.health_check():
        print(" Server is healthy")
    else:
        print(" Server is not responding")
        sys.exit(1)

    print()

    # Test ping
    print(" Testing ping...")
    ping_response = client.ping()
    if "result" in ping_response and "content" in ping_response["result"]:
        content = ping_response["result"]["content"]
        if content and len(content) > 0:
            try:
                ping_data = json.loads(content[0]["text"])
                print(f" Ping successful: {ping_data}")
            except:
                print(" Ping response received")
        else:
            print(" No ping response")
    else:
        print(" Ping failed")
        print(f"Response: {ping_response}")
    print()

    # List available tools
    print("️  Available Tools...")
    tools_response = client.list_tools()
    if "result" in tools_response and "tools" in tools_response["result"]:
        tools = tools_response["result"]["tools"]
        print(f" Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description']}")
    else:
        print(" Failed to list tools")
        print(f"Response: {tools_response}")
    print()

    # Test: List pods in default namespace
    print(" Listing pods in 'default' namespace (real pods only)...")
    pods_response = client.list_pods("default")
    if "result" in pods_response and "content" in pods_response["result"]:
        content = pods_response["result"]["content"]
        if content and len(content) > 0:
            try:
                # Parse the JSON content
                pods_data = json.loads(content[0]["text"])
                
                if "items" in pods_data:
                    pods = pods_data["items"]
                    
                    # --- MODIFICATION START (Filtering for real pods) ---
                    real_pods = []
                    for pod in pods:
                        pod_name = pod.get("name", "")
                        # A pod is considered "real" if its name does NOT start with the known test prefix.
                        if not pod_name.startswith("test-pod-"):
                            real_pods.append(pod)
                    # --- MODIFICATION END ---

                    if real_pods:
                        print(f" Found {len(real_pods)} real pods in default namespace:")
                        for pod in real_pods:
                            # Handle simplified pod format returned by kubectl_get
                            name = pod.get("name", "unknown")
                            namespace = pod.get("namespace", "unknown")
                            status = pod.get("status", "unknown")  # This is already a string
                            kind = pod.get("kind", "Pod")
                            created_at = pod.get("createdAt", "unknown")
                            print(f"   - {name} (namespace: {namespace}, status: {status}, kind: {kind}, created: {created_at})")
                    else:
                        print(f"ℹ️  No real pods found (filtered out {len(pods)} simulated pods)")
                
                elif isinstance(pods_data, list):
                    # Handle direct list response (less common for kubectl get --output=json)
                    print(f" Found {len(pods_data)} real pods in default namespace (raw list):")
                    for pod in pods_data:
                        name = pod.get("metadata", {}).get("name", pod.get("name", "unknown"))
                        namespace = pod.get("metadata", {}).get("namespace", pod.get("namespace", "unknown"))
                        status = pod.get("status", {}).get("phase", pod.get("status", "unknown"))
                        kind = pod.get("kind", "Pod")
                        print(f"   - {name} (namespace: {namespace}, status: {status}, kind: {kind})")
                
                else:
                    print(f" Unexpected response format. Raw data: {pods_data}")
            except json.JSONDecodeError as e:
                print(f" JSON parsing failed: {e}")
                print(f" Raw response: {content[0]['text'][:500]}...")
        else:
            print(" No pods found in default namespace")
    else:
        print(" Failed to list pods")
        print(f" Full response: {json.dumps(pods_response, indent=2)}")
    print()

    # Test: List pods across ALL namespaces
    print(" Listing pods across ALL namespaces (real pods only)...")
    all_pods_response = client.call_tool("kubectl_get", {
        "resourceType": "pods",
        "allNamespaces": True,
        "output": "json"
    })

    if "result" in all_pods_response and "content" in all_pods_response["result"]:
        content = all_pods_response["result"]["content"]
        if content and len(content) > 0:
            try:
                pods_data = json.loads(content[0]["text"])

                if "items" in pods_data:
                    pods = pods_data["items"]
                    
                    # --- MODIFICATION START (Filtering for real pods) ---
                    real_pods = []
                    for pod in pods:
                        pod_name = pod.get("name", "")
                        # A pod is considered "real" if its name does NOT start with the known test prefix.
                        if not pod_name.startswith("test-pod-"):
                            real_pods.append(pod)
                    # --- MODIFICATION END ---

                    if real_pods:
                        print(f" Found {len(real_pods)} real pods across all namespaces:")
                        for pod in real_pods:
                            # Handle simplified pod format
                            name = pod.get("name", "unknown")
                            namespace = pod.get("namespace", "unknown")
                            status = pod.get("status", "unknown")
                            print(f"   - {name} (namespace: {namespace}, status: {status})")
                    else:
                        print(f"ℹ️  No real pods found (filtered out {len(pods)} simulated pods)")
                
                elif isinstance(pods_data, list):
                    # Handle direct list response
                    print(f" Found {len(pods_data)} real pods across all namespaces (raw list):")
                    for pod in pods_data:
                        name = pod.get("metadata", {}).get("name", pod.get("name", "unknown"))
                        namespace = pod.get("metadata", {}).get("namespace", pod.get("namespace", "unknown"))
                        status = pod.get("status", {}).get("phase", pod.get("status", "unknown"))
                        print(f"   - {name} (namespace: {namespace}, status: {status})")
                else:
                    print(f" Unexpected response format. Raw data: {pods_data}")
            except json.JSONDecodeError as e:
                print(f" JSON parsing failed: {e}")
                print(f" Raw response: {content[0]['text'][:500]}...")
        else:
            print(" No pods found across all namespaces")
    else:
        print(" Failed to list pods across all namespaces")
        print(f" Full response: {json.dumps(all_pods_response, indent=2)}")
    print()

    print(" Test completed!")
    
if __name__ == "__main__":
    main()
