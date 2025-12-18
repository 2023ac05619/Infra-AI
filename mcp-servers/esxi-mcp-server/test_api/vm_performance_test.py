#!/usr/bin/env python3
import ssl
from pyVim import connect
from pyVmomi import vim

def get_vm_performance(content, vm_name):
    """Retrieve performance data for the specified virtual machine."""
    # Find VM
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_obj = None
    for vm in container.view:
        if vm.name == vm_name:
            vm_obj = vm
            break
    container.Destroy()

    if not vm_obj:
        raise Exception(f"VM {vm_name} not found")

    # CPU and memory usage (obtained from quickStats)
    stats = {}
    qs = vm_obj.summary.quickStats
    stats["cpu_usage_mhz"] = qs.overallCpuUsage  # MHz
    stats["memory_usage_mb"] = qs.guestMemoryUsage  # MB

    # Storage usage (committed storage, in GB)
    committed = vm_obj.summary.storage.committed if vm_obj.summary.storage else 0
    stats["storage_usage_gb"] = round(committed / (1024**3), 2)  # Convert to GB

    # Network usage (obtained from host or VM NIC statistics, latest sample)
    net_bytes_transmitted = 0
    net_bytes_received = 0
    try:
        pm = content.perfManager
        # Define performance counter IDs to query: network transmitted and received bytes
        counter_ids = []
        for c in pm.perfCounter:
            counter_full_name = f"{c.groupInfo.key}.{c.nameInfo.key}.{c.rollupType}"
            if counter_full_name in ("net.transmitted.average", "net.received.average"):
                counter_ids.append(c.key)
        if counter_ids:
            query = vim.PerformanceManager.QuerySpec(maxSample=1, entity=vm_obj, metricId=[vim.PerformanceManager.MetricId(counterId=cid, instance="*") for cid in counter_ids])
            stats_res = pm.QueryStats(querySpec=[query])
            for series in stats_res[0].value:
                # Sum data from each network interface
                if series.id.counterId == counter_ids[0]:
                    net_bytes_transmitted = sum(series.value)
                elif series.id.counterId == counter_ids[1]:
                    net_bytes_received = sum(series.value)
        stats["network_transmit_kbps"] = net_bytes_transmitted
        stats["network_receive_kbps"] = net_bytes_received
    except Exception as e:
        print(f"Warning: Failed to retrieve network performance data: {e}")
        stats["network_transmit_kbps"] = None
        stats["network_receive_kbps"] = None

    return stats

def display_performance_stats(vm_name, stats):
    """Display performance statistics in a formatted way."""
    print(f"\n{'='*60}")
    print(f"PERFORMANCE STATISTICS FOR VM: {vm_name}")
    print(f"{'='*60}")

    print(f"CPU Usage:     {stats['cpu_usage_mhz']} MHz")
    print(f"Memory Usage:  {stats['memory_usage_mb']} MB")
    print(f"Storage Usage: {stats['storage_usage_gb']} GB")

    if stats['network_transmit_kbps'] is not None and stats['network_receive_kbps'] is not None:
        print(f"Network TX:    {stats['network_transmit_kbps']} KB/s")
        print(f"Network RX:    {stats['network_receive_kbps']} KB/s")
    else:
        print("Network Usage: Not available")

    print(f"{'='*60}\n")

def list_available_vms(content):
    """List all available VMs for reference."""
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_list = [vm.name for vm in container.view]
    container.Destroy()
    return vm_list

def test_vm_performance():
    try:
        # Configuration from config.yaml
        vcenter_host = "192.168.203.178"
        vcenter_user = "root"
        vcenter_password = "TempP@ssw0rd"
        insecure = True

        print(f"Connecting to ESXi at {vcenter_host}...")

        if insecure:
            # Connection method without SSL certificate verification
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False  # Disable hostname checking
            context.verify_mode = ssl.CERT_NONE
            si = connect.SmartConnect(
                host=vcenter_host,
                user=vcenter_user,
                pwd=vcenter_password,
                sslContext=context)
        else:
            # Standard SSL verification connection
            si = connect.SmartConnect(
                host=vcenter_host,
                user=vcenter_user,
                pwd=vcenter_password)

        print("Successfully connected to ESXi")

        # Retrieve content root object
        content = si.RetrieveContent()

        # List available VMs
        available_vms = list_available_vms(content)
        print(f"\nAvailable VMs ({len(available_vms)}):")
        for i, vm_name in enumerate(available_vms, 1):
            print(f"  {i:2d}. {vm_name}")

        # Prompt for VM name
        while True:
            vm_name = input("\nEnter VM name to check performance (or 'quit' to exit): ").strip()

            if vm_name.lower() == 'quit':
                break

            if vm_name not in available_vms:
                print(f" VM '{vm_name}' not found. Please choose from the list above.")
                continue

            try:
                # Get performance data
                stats = get_vm_performance(content, vm_name)

                # Display results
                display_performance_stats(vm_name, stats)

            except Exception as e:
                print(f" Error retrieving performance data for VM '{vm_name}': {e}")

        # Clean up
        connect.Disconnect(si)
        print("Disconnected from ESXi")

    except Exception as e:
        print(f" Test failed with error: {e}")
        return False

    return True

if __name__ == "__main__":
    test_vm_performance()
