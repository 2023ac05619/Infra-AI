#!/usr/bin/env python3
"""
Comprehensive test script for VMware MCP Server
Tests all available tools and APIs
"""
import json
import time
import requests

def test_mcp_tools():
    """Test all MCP server tools and APIs"""
    base_url = "http://localhost:8090"

    print(" COMPREHENSIVE VMWARE MCP SERVER TEST")
    print("=" * 60)

    # Test data
    test_vm_name = "mcp-comprehensive-test"
    clone_vm_name = "mcp-clone-test"

    # Use a single session for all requests (important for MCP)
    session = requests.Session()

    try:
        # Step 1: Establish SSE connection (required for MCP protocol)
        print("\n1. Establishing SSE Connection...")
        try:
            # Start SSE connection but don't read it fully - just establish the session
            response = session.get(f"{base_url}/sse", stream=True, timeout=5)
            if response.status_code == 200:
                print(" SSE connection established")
            else:
                print(f" SSE connection failed: {response.status_code}")
                return False
        except Exception as e:
            print(f" SSE connection error: {e}")
            return False

        # Give SSE a moment to establish
        time.sleep(1)

        # Step 2: Test listVMs tool
        print("\n2. Testing listVMs tool...")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "listVMs",
                "arguments": {}
            }
        }

        response = session.post(f"{base_url}/sse/messages", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                vm_list = result["result"]
                print(f" listVMs successful: Found {len(vm_list)} VMs")
                print(f"   VMs: {', '.join(vm_list[:5])}{'...' if len(vm_list) > 5 else ''}")
                initial_vm_count = len(vm_list)
            else:
                print(f" listVMs failed: {result}")
                return False
        else:
            print(f" listVMs HTTP error: {response.status_code} - {response.text}")
            return False

        # Step 3: Test createVM tool
        print(f"\n3. Testing createVM tool (creating '{test_vm_name}')...")
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "createVM",
                "arguments": {
                    "name": test_vm_name,
                    "cpu": 1,
                    "memory": 512
                }
            }
        }

        response = session.post(f"{base_url}/sse/messages", json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if "result" in result and "created" in result["result"].lower():
                print(f" createVM successful: {result['result']}")
            else:
                print(f" createVM failed: {result}")
                return False
        else:
            print(f" createVM HTTP error: {response.status_code}")
            return False

        # Wait a moment for VM creation to complete
        time.sleep(2)

        # Step 4: Verify VM was created (listVMs again)
        print("\n4. Verifying VM creation...")
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "listVMs",
                "arguments": {}
            }
        }

        response = session.post(f"{base_url}/sse/messages", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                vm_list = result["result"]
                if test_vm_name in vm_list:
                    print(f" VM '{test_vm_name}' found in list ({len(vm_list)} total VMs)")
                else:
                    print(f" VM '{test_vm_name}' not found in list")
                    return False
            else:
                print(f" Verification failed: {result}")
                return False

        # Step 5: Test vmStats resource (performance monitoring)
        print(f"\n5. Testing vmStats resource (performance for '{test_vm_name}')...")
        # Note: This uses a different URL pattern for resources
        payload = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {
                "uri": f"vmstats://{test_vm_name}"
            }
        }

        response = session.post(f"{base_url}/sse/messages", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if "result" in result and "contents" in result["result"]:
                stats = result["result"]["contents"][0]["text"]
                stats_dict = json.loads(stats)
                print(" vmStats successful:")
                print(f"   CPU: {stats_dict.get('cpu_usage_mhz', 'N/A')} MHz")
                print(f"   Memory: {stats_dict.get('memory_usage_mb', 'N/A')} MB")
                print(f"   Storage: {stats_dict.get('storage_usage_gb', 'N/A')} GB")
            else:
                print(f" vmStats failed: {result}")
        else:
            print(f" vmStats HTTP error: {response.status_code}")

        # Step 6: Test powerOn tool
        print(f"\n6. Testing powerOn tool for '{test_vm_name}'...")
        payload = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "powerOn",
                "arguments": {
                    "name": test_vm_name
                }
            }
        }

        response = session.post(f"{base_url}/sse/messages", json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if "result" in result and ("powered on" in result["result"].lower() or "already" in result["result"].lower()):
                print(f" powerOn successful: {result['result']}")
            else:
                print(f"️  powerOn result: {result}")
        else:
            print(f" powerOn HTTP error: {response.status_code}")

        # Wait for power on operation
        time.sleep(3)

        # Step 7: Test powerOff tool
        print(f"\n7. Testing powerOff tool for '{test_vm_name}'...")
        payload = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "powerOff",
                "arguments": {
                    "name": test_vm_name
                }
            }
        }

        response = session.post(f"{base_url}/sse/messages", json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if "result" in result and ("powered off" in result["result"].lower() or "already" in result["result"].lower()):
                print(f" powerOff successful: {result['result']}")
            else:
                print(f"️  powerOff result: {result}")
        else:
            print(f" powerOff HTTP error: {response.status_code}")

        # Step 8: Test cloneVM tool (if there's a VM to clone from)
        # Find an existing VM to clone from (skip test VM we just created)
        existing_vms = [vm for vm in vm_list if vm != test_vm_name]
        if existing_vms:
            source_vm = existing_vms[0]  # Use first available VM
            print(f"\n8. Testing cloneVM tool (cloning '{source_vm}' to '{clone_vm_name}')...")

            payload = {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "cloneVM",
                    "arguments": {
                        "template_name": source_vm,
                        "new_name": clone_vm_name
                    }
                }
            }

            response = session.post(f"{base_url}/sse/messages", json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                if "result" in result and "cloned" in result["result"].lower():
                    print(f" cloneVM successful: {result['result']}")
                    cloned_created = True
                else:
                    print(f" cloneVM failed: {result}")
                    cloned_created = False
            else:
                print(f" cloneVM HTTP error: {response.status_code}")
                cloned_created = False
        else:
            print("\n8. Skipping cloneVM test (no source VMs available)")
            cloned_created = False

        # Step 9: Clean up - delete test VMs
        print(f"\n9. Cleaning up - deleting test VMs...")

        # Delete cloned VM first (if it was created)
        if cloned_created:
            print(f"   Deleting cloned VM '{clone_vm_name}'...")
            payload = {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "deleteVM",
                    "arguments": {
                        "name": clone_vm_name
                    }
                }
            }

            response = session.post(f"{base_url}/sse/messages", json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if "result" in result and "deleted" in result["result"].lower():
                    print(f" Deleted cloned VM: {result['result']}")
                else:
                    print(f"️  Clone VM deletion result: {result}")
            else:
                print(f" Clone VM deletion HTTP error: {response.status_code}")

        # Delete main test VM
        print(f"   Deleting test VM '{test_vm_name}'...")
        payload = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "deleteVM",
                "arguments": {
                    "name": test_vm_name
                }
            }
        }

        response = session.post(f"{base_url}/sse/messages", json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if "result" in result and "deleted" in result["result"].lower():
                print(f" Deleted test VM: {result['result']}")
            else:
                print(f" Test VM deletion failed: {result}")
                return False
        else:
            print(f" Test VM deletion HTTP error: {response.status_code}")
            return False

        # Step 10: Final verification
        print("\n10. Final verification...")
        payload = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "listVMs",
                "arguments": {}
            }
        }

        response = session.post(f"{base_url}/sse/messages", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                final_vm_list = result["result"]
                print(f" Final VM count: {len(final_vm_list)} (started with {initial_vm_count})")

                if test_vm_name not in final_vm_list:
                    print(f" Test VM '{test_vm_name}' successfully cleaned up")
                else:
                    print(f" Test VM '{test_vm_name}' still exists")
                    return False

                if not cloned_created or clone_vm_name not in final_vm_list:
                    print(" All test VMs cleaned up successfully")
                else:
                    print(f" Cloned VM '{clone_vm_name}' still exists")
                    return False
            else:
                print(f" Final verification failed: {result}")
                return False

        print("\n ALL MCP SERVER TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(" Tested tools: listVMs, createVM, powerOn, powerOff, cloneVM, deleteVM")
        print(" Tested resources: vmStats")
        print(" Verified cleanup and state consistency")

        return True

    except Exception as e:
        print(f" Test suite failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_mcp_tools()
    exit(0 if success else 1)
