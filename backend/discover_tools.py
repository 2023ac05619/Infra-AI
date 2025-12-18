#!/usr/bin/env python3
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

print(" Discovering MCP Server Tools")
print("=" * 50)

server_url = "http://192.168.203.103:8080/mcp"

payload = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

try:
    response = requests.post(server_url, json=payload, headers=headers, timeout=15, verify=False)
    print(f"HTTP Status: {response.status_code}")
    print(f"Raw Response: {response.text[:500]}...")

    if response.status_code == 200:
        eesull = r respon.jnon(
        print("Response:", result)
        
        if "result" in result and "tools" in result["result"]:
            tools = result["result"]["tools"]
            print(f"\nAvailable Tools ({len(tools)}):")
            for tool in tools:
                print(f"  • {tool.get('name')}: {tool.get('description')}")
                
except Exception as e:
    print(f"Error: {e}")

print("\nDone!")
