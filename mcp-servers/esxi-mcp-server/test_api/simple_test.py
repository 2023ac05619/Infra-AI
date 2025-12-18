#!/usr/bin/env python3
import ssl
from pyVim import connect
from pyVmomi import vim

def test_list_vms():
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

        # List all VMs
        print("Listing VMs...")
        container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
        vm_list = []
        for vm in container.view:
            vm_list.append(vm.name)
        container.Destroy()

        print(f"Found {len(vm_list)} VMs:")
        for vm_name in vm_list:
            print(f"- {vm_name}")

        # Clean up
        connect.Disconnect(si)

        return vm_list

    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    test_list_vms()
