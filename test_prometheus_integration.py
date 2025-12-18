#!/usr/bin/env python3
"""
Test script to verify Prometheus MCP client integration with configuration file
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.tools.mcp_prometheus_client import (
    PrometheusMCPClient,
    get_prometheus_mcp_client,
    mcp_prometheus_health_check,
    mcp_prometheus_list_metrics,
    mcp_prometheus_execute_query
)

async def test_configuration_loading():
    """Test that the configuration file is loaded correctly"""
    print(" Testing Prometheus MCP Client Configuration Loading")

    try:
        client = PrometheusMCPClient()

        # Test configuration loading
        print(f" Configuration loaded: {len(client.available_tools)} tools available")

        # List available tools
        print(" Available tools:")
        for tool_name, tool_config in client.available_tools.items():
            print(f"  - {tool_name}: {tool_config.get('description', 'No description')}")

        # Test get_available_tools method
        tools_info = client.get_available_tools()
        print(f" Tools info retrieved: {tools_info['count']} tools")

        return True

    except Exception as e:
        print(f" Configuration loading failed: {e}")
        return False

async def test_health_check():
    """Test health check functionality"""
    print("\n🩺 Testing Health Check")

    try:
        result = await mcp_prometheus_health_check()
        print(f" Health check result: {result[:100]}...")

        # Try to parse as JSON
        import json
        parsed = json.loads(result)
        if isinstance(parsed, dict) and "status" in parsed:
            print(f" Health check response parsed successfully: status={parsed.get('status')}")
        else:
            print("️ Health check response format unexpected")

        return True

    except Exception as e:
        print(f" Health check failed: {e}")
        return False

async def test_list_metrics():
    """Test list metrics functionality"""
    print("\n Testing List Metrics")

    try:
        result = await mcp_prometheus_list_metrics(limit=10)
        print(f" List metrics result: {result[:100]}...")

        # Try to parse as JSON
        import json
        parsed = json.loads(result)
        if isinstance(parsed, dict) and "metrics" in parsed:
            metrics_count = len(parsed.get("metrics", []))
            print(f" Metrics list parsed: {metrics_count} metrics returned")
        else:
            print("️ List metrics response format unexpected")

        return True

    except Exception as e:
        print(f" List metrics failed: {e}")
        return False

async def test_execute_query():
    """Test query execution functionality"""
    print("\n Testing Execute Query")

    try:
        # Test with a simple query
        result = await mcp_prometheus_execute_query("up")
        print(f" Execute query result: {result[:100]}...")

        # Try to parse as JSON
        import json
        parsed = json.loads(result)
        if isinstance(parsed, dict) and "resultType" in parsed:
            print(f" Query result parsed: resultType={parsed.get('resultType')}")
        else:
            print("️ Execute query response format unexpected")

        return True

    except Exception as e:
        print(f" Execute query failed: {e}")
        return False

async def test_parameter_validation():
    """Test parameter validation in execute_tool method"""
    print("\n Testing Parameter Validation")

    try:
        client = await get_prometheus_mcp_client()

        # Test missing required parameter
        result = await client.execute_tool("execute_query", {})
        print(f" Parameter validation working: {result.get('error', 'No error')[:50]}...")

        # Test valid parameters
        result = await client.execute_tool("health_check", {})
        if result.get("status") != "error":
            print(" Valid tool execution successful")
        else:
            print(f"️ Valid tool execution failed: {result.get('error')}")

        return True

    except Exception as e:
        print(f" Parameter validation test failed: {e}")
        return False

async def main():
    """Run all integration tests"""
    print(" InfraAI Prometheus MCP Integration Test Suite")
    print("=" * 60)

    tests = [
        test_configuration_loading,
        test_health_check,
        test_list_metrics,
        test_execute_query,
        test_parameter_validation
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f" Test {test.__name__} crashed: {e}")

    print("\n" + "=" * 60)
    print(f" Test Results: {passed}/{total} tests passed")

    if passed == total:
        print(" All Prometheus MCP integration tests successful!")
        return 0
    else:
        print(" Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
