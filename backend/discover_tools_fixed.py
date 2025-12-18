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
    print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
    
    # Print raw response for debugging
    raw_response = response.text
    print(f"Raw Response (first 500 chars):")
    print(f"'{raw_response[:500]}'")
    
    if response.status_code == 200:
        # Check if it's Server-Sent Events format
        if "event: message" in raw_response:
            print("\n Response is in SSE format")
            lines = raw_response.strip().split('\n')
            for line in lines:
                if line.startswith('data: '):
                    data = line[6:]
                    try:
                        result = import json; json.loads(data)
                        print(f"Parsed SSE JSON: {result}")
                        
                        if "result" in result and "tools" in result["result"]:
                            tools = result["result"]["tools"]
                            print(f"\n️  Available Tools ({len(tools)}):")
                            for tool in tools:
                                name = tool.get("name", "unknown")
                                desc = tool.get("description", "no description")
                                print(f"  • {name}: {desc}")
                                
                                # Show parameters if available
                                if "inputSchema" in tool and "properties" in tool["inputSchema"]:
                                    props = list(tool["inputSchema"]["properties"].keys())
                                    print(f"    Parameters: {', '.join(props)}")
                            break
                        elif "error" in result:
                            print(f"️ MCP Error: {result['error']}")
                            
                    except Exception as e:
                        print(f"Failed to parse JSON data: {e}")
                        continue
        
        else:
            # Try to parse as direct JSON
            try:
                result = response.json()
                print(f"Direct JSON response: {result}")
            except:
                print("Response is neither SSE nor valid JSON")
    
except requests.exceptions.Timeout:
    print("⏱️ Connection timeout")
except requests.exceptions.ConnectionError as e:
    print(f" Connection refused: {e}")
except Exception as e:
    print(f" Error: {e}")

print("\n Tool Discovery Complete!")
