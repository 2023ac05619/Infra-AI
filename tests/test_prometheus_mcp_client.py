#!/usr/bin/env python3
"""
Test client for Prometheus JSON-RPC Server
Demonstrates querying real pod CPU and memory metrics from microk8s cluster
"""

import asyncio
import httpx
import json
from typing import Dict, Any, List
from datetime import datetime


class PrometheusJSONRPCClient:
    """HTTP client for Prometheus JSON-RPC Server"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.request_id = 1

    async def call_method(self, method_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a JSON-RPC method"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/jsonrpc",
                headers={"Content-Type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "id": self.request_id,
                    "method": method_name,
                    "params": params or {}
                }
            )
            self.request_id += 1

            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}: {response.text}"}

            try:
                result = response.json()
                return result
            except:
                return {"error": response.text}

    async def get_pod_cpu_usage(self) -> Dict[str, Any]:
        """Get real-time pod CPU usage across all namespaces"""
        print("\n Querying pod CPU usage across all namespaces...")

        # Use our custom recording rule for pod CPU usage
        query = "pod:cpu_usage_cores:rate5m"
        result = await self.call_method("execute_query", {"query": query})

        if result.get("error"):
            print(f" Query failed: {result['error']}")
            return result

        return result

    async def get_pod_memory_usage(self) -> Dict[str, Any]:
        """Get real-time pod memory usage across all namespaces"""
        print("\n Querying pod memory usage across all namespaces...")

        # Use our custom recording rule for pod memory usage
        query = "pod:memory_usage_bytes:sum"
        result = await self.call_method("execute_query", {"query": query})

        if result.get("error"):
            print(f" Query failed: {result['error']}")
            return result

        return result

    async def get_pod_cpu_percentage(self) -> Dict[str, Any]:
        """Get pod CPU usage as percentage of limits"""
        print("\n Querying pod CPU usage % (vs limits)...")

        # Calculate CPU usage percentage against limits
        query = "sum(rate(container_cpu_usage_seconds_total[5m])) by (pod, namespace) / sum(kube_pod_container_resource_limits_cpu_cores) by (pod, namespace) * 100"
        result = await self.call_method("execute_query", {"query": query})

        if result.get("error"):
            print(f" Query failed: {result['error']}")
            return result

        return result

    async def get_pod_memory_percentage(self) -> Dict[str, Any]:
        """Get pod memory usage as percentage of limits"""
        print("\n Querying pod memory usage % (vs limits)...")

        # Calculate memory usage percentage against limits
        query = "sum(container_memory_usage_bytes) by (pod, namespace) / sum(kube_pod_container_resource_limits_memory_bytes) by (pod, namespace) * 100"
        result = await self.call_method("execute_query", {"query": query})

        if result.get("error"):
            print(f" Query failed: {result['error']}")
            return result

        return result

    async def get_namespace_resource_usage(self) -> Dict[str, Any]:
        """Get resource usage aggregated by namespace"""
        print("\n Querying namespace-level resource usage...")

        cpu_query = "sum(rate(container_cpu_usage_seconds_total[5m])) by (namespace)"
        memory_query = "sum(container_memory_usage_bytes) by (namespace)"

        cpu_result = await self.call_method("execute_query", {"query": cpu_query})
        memory_result = await self.call_method("execute_query", {"query": memory_query})

        return {
            "cpu_by_namespace": cpu_result,
            "memory_by_namespace": memory_result
        }

    async def get_cluster_resource_totals(self) -> Dict[str, Any]:
        """Get total cluster resource usage"""
        print("\n Querying cluster-wide resource totals...")

        cpu_query = "sum(rate(container_cpu_usage_seconds_total[5m]))"
        memory_query = "sum(container_memory_usage_bytes)"

        cpu_result = await self.call_method("execute_query", {"query": cpu_query})
        memory_result = await self.call_method("execute_query", {"query": memory_query})

        return {
            "total_cpu_cores": cpu_result,
            "total_memory_bytes": memory_result
        }

    async def check_alerts(self) -> Dict[str, Any]:
        """Check for active pod resource alerts"""
        print("\n Checking for active pod resource alerts...")

        alert_query = "ALERTS{alertname=~'PodHighCPUUsage|PodCriticalCPUUsage|PodHighMemoryUsage|PodCriticalMemoryUsage|PodRestartingFrequently'}"
        result = await self.call_method("execute_query", {"query": alert_query})

        if result.get("error"):
            print(f" Alert query failed: {result['error']}")
            return result

        return result

    async def get_pod_health_metrics(self) -> Dict[str, Any]:
        """Get pod health and lifecycle metrics"""
        print("\n️ Querying pod health metrics...")

        restart_query = "sum(kube_pod_container_status_restarts_total) by (pod, namespace)"
        uptime_query = "time() - kube_pod_created"

        restart_result = await self.call_method("execute_query", {"query": restart_query})
        uptime_result = await self.call_method("execute_query", {"query": uptime_query})

        return {
            "pod_restarts": restart_result,
            "pod_uptime": uptime_result
        }

    async def list_available_metrics(self, limit: int = 50) -> Dict[str, Any]:
        """List available metrics with better formatting"""
        print(f"\n Listing available metrics (limit: {limit})...")
        result = await self.call_method("list_metrics", {"limit": limit})
        return result

    async def get_health_status(self) -> Dict[str, Any]:
        """Get server health status"""
        print("\n️ Checking server health...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                return {"result": response.json()}
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}


def format_bytes(bytes_value: float) -> str:
    """Format bytes to human readable format"""
    if bytes_value >= 1024**3:
        return ",.2f"
    elif bytes_value >= 1024**2:
        return ",.2f"
    elif bytes_value >= 1024:
        return ",.2f"
    else:
        return ".0f"


def format_cpu(cpu_value: float) -> str:
    """Format CPU cores to readable format"""
    return ".4f"


def print_metric_results(title: str, result: Dict[str, Any], value_formatter=None, unit: str = ""):
    """Print formatted metric results"""
    if result.get("error"):
        print(f" {title}: {result['error']}")
        return

    data = result.get("result", {})
    values = data.get("result", [])

    if not values:
        print(f"️ {title}: No data available")
        return

    print(f" {title}: {len(values)} result(s)")

    # Sort by value (highest first) and show top results
    sorted_values = sorted(values, key=lambda x: float(x.get("value", [0, 0])[1]), reverse=True)

    for i, item in enumerate(sorted_values[:10]):  # Show top 10
        metric = item.get("metric", {})
        pod_name = metric.get("pod", "unknown")
        namespace = metric.get("namespace", "unknown")
        timestamp, value = item.get("value", [0, "N/A"])

        if value != "N/A":
            try:
                numeric_value = float(value)
                if value_formatter:
                    formatted_value = value_formatter(numeric_value)
                else:
                    formatted_value = ".4f"
            except (ValueError, TypeError):
                formatted_value = str(value)
        else:
            formatted_value = "N/A"

        print(f"  {i+1:2d}. {namespace}/{pod_name}: {formatted_value}{unit}")


async def main():
    """Main test function - now pulling real data from microk8s cluster"""
    print(" Prometheus MCP Client Test - Real Cluster Data")
    print("=" * 60)
    print("Pulling live metrics from microk8s cluster monitoring stack")
    print("=" * 60)

    # Use the correct MCP server endpoint
    client = PrometheusJSONRPCClient("http://localhost:8080")

    try:
        # Check server health
        health = await client.get_health_status()
        health_data = health.get("result", {})
        print(f"Health Status: {health_data.get('status', 'unknown')}")
        print(f"Prometheus URL: {health_data.get('prometheus_url', 'not configured')}")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

        # Get pod CPU usage
        cpu_result = await client.get_pod_cpu_usage()
        print_metric_results("Pod CPU Usage (cores)", cpu_result, format_cpu, " cores")

        # Get pod memory usage
        memory_result = await client.get_pod_memory_usage()
        print_metric_results("Pod Memory Usage", memory_result, format_bytes, "B")

        # Get CPU usage percentages
        cpu_pct_result = await client.get_pod_cpu_percentage()
        print_metric_results("Pod CPU Usage % (vs limits)", cpu_pct_result, lambda x: ".1f", "%")

        # Get memory usage percentages
        memory_pct_result = await client.get_pod_memory_percentage()
        print_metric_results("Pod Memory Usage % (vs limits)", memory_pct_result, lambda x: ".1f", "%")

        # Get namespace aggregations
        ns_results = await client.get_namespace_resource_usage()
        print_metric_results("CPU Usage by Namespace", ns_results["cpu_by_namespace"], format_cpu, " cores")
        print_metric_results("Memory Usage by Namespace", ns_results["memory_by_namespace"], format_bytes, "B")

        # Get cluster totals
        cluster_results = await client.get_cluster_resource_totals()
        print_metric_results("Total Cluster CPU Usage", cluster_results["total_cpu_cores"], format_cpu, " cores")
        print_metric_results("Total Cluster Memory Usage", cluster_results["total_memory_bytes"], format_bytes, "B")

        # Check for alerts
        alert_result = await client.check_alerts()
        alert_data = alert_result.get("result", {}).get("result", [])
        active_alerts = [alert for alert in alert_data if alert.get("value", [0, "0"])[1] != "0"]
        print(f" Active Pod Resource Alerts: {len(active_alerts)}")
        for alert in active_alerts[:5]:  # Show first 5 alerts
            metric = alert.get("metric", {})
            alert_name = metric.get("alertname", "unknown")
            pod = metric.get("pod", "unknown")
            namespace = metric.get("namespace", "unknown")
            severity = metric.get("severity", "unknown")
            print(f"  • {alert_name} [{severity}]: {namespace}/{pod}")

        # Get pod health metrics
        health_results = await client.get_pod_health_metrics()
        print_metric_results("Pod Restart Count", health_results["pod_restarts"], lambda x: ".0f", " restarts")

        # List some key metrics
        metrics_result = await client.list_available_metrics(30)
        metrics_data = metrics_result.get("result", {})
        available_metrics = metrics_data.get("metrics", [])
        print(f"\n Available Metrics: {len(available_metrics)} total")
        print("Sample metrics (showing first 15):")
        for i, metric in enumerate(available_metrics[:15]):
            print(f"  {i+1:2d}. {metric}")

        print(f"\n Test completed successfully! Data pulled from {len(available_metrics)} metrics across the cluster.")

    except Exception as e:
        print(f"\n Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
