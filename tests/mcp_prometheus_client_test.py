#!/usr/bin/env python3
"""
Prometheus MCP Client Test Script - Stateless HTTP JSON-RPC

Tests Prometheus MCP server connectivity and metrics querying using
stateless HTTP JSON-RPC protocol.

Connects to MCP server at: http://192.168.203.103:8080/jsonrpc
"""

import os
import sys
import json
import asyncio
import requests
from urllib3.exceptions import InsecureRequestWarning
from typing import Dict, Any, Optional

# Suppress SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
PURPLE = '\033[0;35m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

class PrometheusMCPTester:
    """Prometheus MCP tester using stateless HTTP JSON-RPC"""

    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

        # MCP server configuration for Prometheus
        self.mcp_url = "http://192.168.203.103:8080"
        self.mcp_endpoint = "/jsonrpc"
        self.full_url = f"{self.mcp_url}{self.mcp_endpoint}"

    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{CYAN}{'='*70}{NC}")
        print(f"{CYAN}{title.center(70)}{NC}")
        print(f"{CYAN}{'='*70}{NC}")

    def log_test(self, test_name: str, result: bool, message: str = "", details: str = ""):
        """Log a test result"""
        self.total_tests += 1

        if result:
            self.passed_tests += 1
            status = f"{GREEN} PASS{NC}"
        else:
            self.failed_tests += 1
            status = f"{RED} FAIL{NC}"

        print(f"{status} {test_name}")
        if message:
            print(f"   {BLUE}↳ {message}{NC}")
        if details:
            for line in details.split('\n'):
                print(f"      {PURPLE}{line}{NC}")

    def print_summary(self):
        """Print test summary"""
        print(f"\n{BLUE}{'='*70}{NC}")
        print(f"{CYAN}PROMETHEUS MCP TEST RESULTS SUMMARY{NC}".center(70))
        print(f"{BLUE}{'='*70}{NC}")

        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {GREEN}{self.passed_tests}{NC}")
        print(f"Failed: {RED}{self.failed_tests}{NC}")

        if self.failed_tests == 0:
            print(f"\n{GREEN} ALL PROMETHEUS MCP TESTS SUCCESSFUL!{NC}")
        else:
            print(f"\n{RED} SOME PROMETHEUS MCP TESTS FAILED{NC}")
            print(f"{YELLOW}Check the output above for details.{NC}")

    async def test_mcp_server_connectivity(self) -> bool:
        """Test basic MCP server connectivity using stateless HTTP JSON-RPC"""
        print(f"\n{PURPLE} Testing Prometheus MCP Server Connectivity (Stateless HTTP JSON-RPC){NC}")

        # Test 1: Basic HTTP connectivity
        try:
            response = requests.get(self.mcp_url, timeout=5, verify=False)
            if response.status_code == 200:
                self.log_test("MCP Server HTTP Connectivity", True, f"HTTP {response.status_code}")
            else:
                self.log_test("MCP Server HTTP Connectivity", False,
                            f"Unexpected HTTP status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("MCP Server HTTP Connectivity", False, f"Connection error: {str(e)}")
            return False

        # Test 2: MCP JSON-RPC endpoint
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            payload = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "prometheus-mcp-test", "version": "1.0.0"}
                },
                "id": 1
            }

            response = requests.post(self.full_url, json=payload, headers=headers, timeout=10, verify=False)

            if response.status_code == 200:
                self.log_test("MCP JSON-RPC Endpoint", True, f"HTTP {response.status_code}")
                return True
            else:
                self.log_test("MCP JSON-RPC Endpoint", False,
                            f"Unexpected HTTP status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("MCP JSON-RPC Endpoint", False, f"Error: {str(e)}")
            return False

    def execute_prometheus_query(self, query: str) -> Dict[str, Any]:
        """Execute a Prometheus query via MCP JSON-RPC"""
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "query_prometheus",
                "arguments": {
                    "query": query
                }
            },
            "id": 2
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = requests.post(self.full_url, json=payload, headers=headers, timeout=15, verify=False)

            if response.status_code == 200:
                result = response.json()

                # Check if it's a JSON-RPC response
                if "jsonrpc" in result and "id" in result:
                    if "result" in result:
                        # Success response - extract the MCP tool result
                        tool_result = result["result"]
                        if isinstance(tool_result, dict) and "content" in tool_result:
                            content = tool_result["content"]
                            if isinstance(content, list) and len(content) > 0:
                                first_content = content[0]
                                if isinstance(first_content, dict) and "text" in first_content:
                                    # Parse the JSON data from the text
                                    try:
                                        metrics_data = json.loads(first_content["text"])
                                        return {
                                            "status": "success",
                                            "query": query,
                                            "data": metrics_data,
                                            "raw_response": result
                                        }
                                    except json.JSONDecodeError:
                                        return {
                                            "status": "success",
                                            "query": query,
                                            "data": first_content["text"],
                                            "raw_response": result
                                        }

                        return {
                            "status": "success",
                            "query": query,
                            "data": tool_result,
                            "raw_response": result
                        }

                    elif "error" in result:
                        # Error response
                        error = result["error"]
                        return {
                            "status": "error",
                            "query": query,
                            "error": error.get("message", "Unknown error"),
                            "raw_response": result
                        }
                else:
                    # Not a JSON-RPC response
                    return {
                        "status": "success",
                        "query": query,
                        "data": result,
                        "raw_response": result
                    }

            else:
                return {
                    "status": "error",
                    "query": query,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "raw_response": response.text
                }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "query": query,
                "error": "Request timeout"
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "query": query,
                "error": "Connection failed"
            }
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }

    async def test_cpu_metrics(self) -> bool:
        """Test CPU metrics querying"""
        print(f"\n{PURPLE}️  Testing CPU Metrics Query{NC}")

        cpu_queries = [
            "100 - (avg by(instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",  # CPU usage %
            "node_cpu_seconds_total",  # Raw CPU seconds
            "cpu_usage_percent",  # Alternative metric name
        ]

        success_count = 0

        for query in cpu_queries:
            print(f"\n Testing CPU query: {query[:50]}...")
            result = self.execute_prometheus_query(query)

            if result["status"] == "success":
                success_count += 1
                self.log_test(f"CPU Query: {query[:30]}...", True, "Query executed successfully")

                # Display sample metrics if available
                data = result.get("data", {})
                if isinstance(data, dict) and "data" in data:
                    prometheus_data = data["data"]
                    if isinstance(prometheus_data, dict) and "result" in prometheus_data:
                        metrics = prometheus_data["result"]
                        if isinstance(metrics, list) and len(metrics) > 0:
                            print(f"   {BLUE}Sample CPU metrics:{NC}")
                            for i, metric in enumerate(metrics[:3]):  # Show first 3
                                metric_info = metric.get("metric", {})
                                value_info = metric.get("value", [])
                                if len(value_info) >= 2:
                                    timestamp = value_info[0]
                                    value = value_info[1]
                                    instance = metric_info.get("instance", "unknown")
                                    print(f"      • {instance}: {value}% CPU usage")
                        else:
                            print(f"   {YELLOW}No CPU metrics returned{NC}")
                else:
                    print(f"   {YELLOW}Metrics data format: {type(data)}{NC}")
            else:
                self.log_test(f"CPU Query: {query[:30]}...", False, result.get("error", "Unknown error"))

        return success_count > 0

    async def test_memory_metrics(self) -> bool:
        """Test memory metrics querying"""
        print(f"\n{PURPLE} Testing Memory Metrics Query{NC}")

        memory_queries = [
            "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes",  # Used memory
            "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100",  # Memory usage %
            "node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100",  # Available memory %
            "container_memory_usage_bytes",  # Container memory
        ]

        success_count = 0

        for query in memory_queries:
            print(f"\n Testing memory query: {query[:50]}...")
            result = self.execute_prometheus_query(query)

            if result["status"] == "success":
                success_count += 1
                self.log_test(f"Memory Query: {query[:30]}...", True, "Query executed successfully")

                # Display sample metrics if available
                data = result.get("data", {})
                if isinstance(data, dict) and "data" in data:
                    prometheus_data = data["data"]
                    if isinstance(prometheus_data, dict) and "result" in prometheus_data:
                        metrics = prometheus_data["result"]
                        if isinstance(metrics, list) and len(metrics) > 0:
                            print(f"   {BLUE}Sample memory metrics:{NC}")
                            for i, metric in enumerate(metrics[:3]):  # Show first 3
                                metric_info = metric.get("metric", {})
                                value_info = metric.get("value", [])
                                if len(value_info) >= 2:
                                    timestamp = value_info[0]
                                    value = value_info[1]
                                    instance = metric_info.get("instance", "unknown")
                                    # Convert bytes to MB/GB for readability
                                    try:
                                        value_float = float(value)
                                        if value_float > 1024**3:  # GB
                                            display_value = f"{value_float / (1024**3):.2f}GB"
                                        elif value_float > 1024**2:  # MB
                                            display_value = f"{value_float / (1024**2):.2f}MB"
                                        else:  # KB
                                            display_value = f"{value_float / 1024:.2f}KB"
                                    except (ValueError, TypeError):
                                        display_value = str(value)

                                    print(f"      • {instance}: {display_value}")
                        else:
                            print(f"   {YELLOW}No memory metrics returned{NC}")
                else:
                    print(f"   {YELLOW}Metrics data format: {type(data)}{NC}")
            else:
                self.log_test(f"Memory Query: {query[:30]}...", False, result.get("error", "Unknown error"))

        return success_count > 0

    async def test_basic_health_metrics(self) -> bool:
        """Test basic health metrics"""
        print(f"\n{PURPLE}️  Testing Basic Health Metrics{NC}")

        health_queries = [
            "up",  # Service health check
            "node_load1",  # System load
            "node_filesystem_avail_bytes / node_filesystem_size_bytes * 100",  # Disk usage %
        ]

        success_count = 0

        for query in health_queries:
            print(f"\n Testing health query: {query}")
            result = self.execute_prometheus_query(query)

            if result["status"] == "success":
                success_count += 1
                self.log_test(f"Health Query: {query[:20]}", True, "Query executed successfully")

                # Display sample metrics if available
                data = result.get("data", {})
                if isinstance(data, dict) and "data" in data:
                    prometheus_data = data["data"]
                    if isinstance(prometheus_data, dict) and "result" in prometheus_data:
                        metrics = prometheus_data["result"]
                        if isinstance(metrics, list) and len(metrics) > 0:
                            print(f"   {BLUE}Health metrics:{NC}")
                            for i, metric in enumerate(metrics[:3]):  # Show first 3
                                metric_info = metric.get("metric", {})
                                value_info = metric.get("value", [])
                                if len(value_info) >= 2:
                                    value = value_info[1]
                                    instance = metric_info.get("instance", "unknown")
                                    job = metric_info.get("job", "unknown")
                                    print(f"      • {job}@{instance}: {value}")
            else:
                self.log_test(f"Health Query: {query[:20]}", False, result.get("error", "Unknown error"))

        return success_count > 0

    async def run_all_tests(self):
        """Run all Prometheus MCP tests"""
        print(f"{BLUE} InfraAI Prometheus MCP JSON-RPC Test Suite{NC}")
        print(f"{BLUE}{'='*70}{NC}")

        start_time = asyncio.get_event_loop().time()

        # Test Prometheus metrics directly (MCP server connectivity verified by successful queries)
        await self.test_cpu_metrics()
        await self.test_memory_metrics()
        await self.test_basic_health_metrics()

        # Print results
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        print(f"\n{PURPLE}⏱️  Total test duration: {duration:.2f} seconds{NC}")

        self.print_summary()

        # Configuration notes
        print(f"\n{YELLOW}️  Configuration Used:{NC}")
        print(f"   MCP Server: {self.full_url}")
        print(f"   Transport: Stateless HTTP JSON-RPC")
        print(f"   Protocol: MCP tools/call with query_prometheus")

async def main():
    """Main test function"""
    tester = PrometheusMCPTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
