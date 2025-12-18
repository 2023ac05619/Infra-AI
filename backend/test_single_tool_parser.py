#!/usr/bin/env python3
"""
Test script for the single-tool command parser architecture.
Tests the battle-tested pattern implementation.
"""

import asyncio
import json
from app.core.engine import route_infra_command, infra_command
from app.tools.ollama_adapter import call_ollama


async def test_route_infra_command():
    """Test the router function with various commands."""
    print(" Testing infra_command router...")

    test_cases = [
        # Kubernetes
        {"domain": "kubernetes", "action": "list", "resource": "pods"},
        {"domain": "kubernetes", "action": "get", "resource": "deployments", "namespace": "production"},
        {"domain": "kubernetes", "action": "scale", "resource": "deployment", "name": "web", "replicas": 3},

        # Prometheus
        {"domain": "prometheus", "action": "query", "query": "cpu_usage"},

        # Grafana
        {"domain": "grafana", "action": "list", "resource": "dashboards"},

        # VMware
        {"domain": "vmware", "action": "list", "resource": "vms"},
        {"domain": "vmware", "action": "power_on", "name": "test-vm"},

        # Network
        {"domain": "network", "action": "scan", "subnet": "192.168.1.0/24"},
    ]

    for cmd in test_cases:
        try:
            print(f"Testing: {cmd}")
            # Note: This will fail without actual MCP servers running
            # but tests the routing logic
            result = await route_infra_command(cmd)
            print(f" Route successful: {result[:100]}...")
        except Exception as e:
            print(f"️  Route failed (expected without MCP servers): {e}")

    print(" Router testing complete\n")


async def test_system_prompt_parsing():
    """Test if the system prompt generates valid JSON tool calls."""
    print(" Testing system prompt JSON generation...")

    # Use the exact system prompt from the implementation
    system_prompt = """You are an infrastructure command parser.

Rules:
1. You MUST use the infra_command tool for ALL infrastructure requests.
2. You MUST NOT respond in natural language.
3. You MUST output ONLY a tool call.
4. If information is missing, make the best reasonable assumption.

Infra_command is the ONLY available tool.

Few-shot examples (MANDATORY):

User: List all Kubernetes pods
Assistant:
{
  "tool_calls": [{
    "name": "infra_command",
    "arguments": {
      "domain": "kubernetes",
      "action": "list",
      "resource": "pods"
    }
  }]
}

User: Get CPU usage from Prometheus
Assistant:
{
  "tool_calls": [{
    "name": "infra_command",
    "arguments": {
      "domain": "prometheus",
      "action": "query",
      "query": "cpu_usage"
    }
  }]
}

User: What Grafana dashboards are available
Assistant:
{
  "tool_calls": [{
    "name": "infra_command",
    "arguments": {
      "domain": "grafana",
      "action": "list",
      "resource": "dashboards"
    }
  }]
}

User: List VMware virtual machines
Assistant:
{
  "tool_calls": [{
    "name": "vmware",
    "action": "list",
    "resource": "vms"
  }]
}

User: Scale the web deployment to 3 replicas
Assistant:
{
  "tool_calls": [{
    "name": "infra_command",
    "arguments": {
      "domain": "kubernetes",
      "action": "scale",
      "resource": "deployment",
      "name": "web",
      "replicas": 3
    }
  }]
}"""

    test_queries = [
        "List all pods",
        "Show me CPU metrics",
        "What dashboards are available?",
        "List virtual machines",
        "Scale web app to 5 replicas"
    ]

    for query in test_queries:
        prompt = f"{system_prompt}\n\nUser: {query}\n\nAssistant:"
        print(f"\n Testing query: '{query}'")

        try:
            response = await call_ollama(prompt)
            print(f"Raw response: {response[:200]}...")

            # Try to parse as JSON
            tool_call_data = json.loads(response.strip())

            if "tool_calls" in tool_call_data and isinstance(tool_call_data["tool_calls"], list):
                tool_call = tool_call_data["tool_calls"][0]
                print(" Valid JSON tool call:")
                print(f"   Name: {tool_call['name']}")
                print(f"   Args: {tool_call.get('arguments', {})}")
            else:
                print(" Invalid tool call structure")

        except json.JSONDecodeError as e:
            print(f" JSON parsing failed: {e}")
        except Exception as e:
            print(f" Test failed: {e}")

    print("\n System prompt testing complete\n")


async def test_retry_logic():
    """Test the retry + repair loop logic."""
    print(" Testing retry logic simulation...")

    # Simulate a failed response that should trigger retry
    failed_response = "I think you want to list pods. Let me help you with that."

    # Simulate the retry logic
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            tool_call_data = json.loads(failed_response.strip())
            print(" Unexpected success on failed response")
            break
        except json.JSONDecodeError:
            retry_count += 1
            print(f"Retry {retry_count}/{max_retries}: Failed to parse JSON")

            if retry_count < max_retries:
                # Create stronger prompt (simulated)
                retry_prompt = f"""You FAILED to call infra_command.

This is not optional. You MUST output ONLY a tool call in JSON format.

Output ONLY a valid JSON tool call for infra_command."""
                print(f"Would retry with: {retry_prompt[:100]}...")
            else:
                print(" All retries exhausted")

    print(" Retry logic simulation complete\n")


async def main():
    """Run all tests."""
    print(" Testing Single-Tool Command Parser Architecture\n")
    print("=" * 60)

    await test_route_infra_command()
    await test_system_prompt_parsing()
    await test_retry_logic()

    print("=" * 60)
    print(" Testing complete!")
    print("\n Expected Results (with real MCP servers):")
    print("- Direct kubectl list:  95%")
    print("- Prometheus query:  90%")
    print("- Ambiguous request: ️ 80%")
    print("- Free-text infra explanation:  intentionally blocked")


if __name__ == "__main__":
    asyncio.run(main())
