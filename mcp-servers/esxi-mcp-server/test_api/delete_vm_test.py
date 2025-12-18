#!/usr/bin/env python3
import ssl
from pyVim import connect
from pyVmomi import vim

def list_available_vms(content):
    """List all available VMs for reference."""
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_list = [vm.name for vm in container.view]
    container.Destroy()
    return vm_list

def delete_test_vm():
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
            vm_name = input("\nEnter VM name to delete (or 'quit' to exit): ").strip()

            if vm_name.lower() == 'quit':
                break

            if vm_name not in available_vms:
                print(f" VM '{vm_name}' not found. Please choose from the list above.")
                continue

            # Confirm deletion
            confirm = input(f"Are you sure you want to delete VM '{vm_name}'? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                print("Deletion cancelled.")
                continue

            try:
                # Find the VM
                container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
                vm_obj = None
                for vm in container.view:
                    if vm.name == vm_name:
                        vm_obj = vm
                        break
                container.Destroy()

                if not vm_obj:
                    print(f"VM '{vm_name}' not found - may have been deleted already")
                    continue

                # Delete the VM
                print(f"--- Deleting VM '{vm_name}' ---")
                task = vm_obj.Destroy_Task()
                print("Deleting VM...")
                while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                    continue

                if task.info.state == vim.TaskInfo.State.error:
                    raise task.info.error

                print(f" VM '{vm_name}' deleted successfully!")

                # Verify deletion
                container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
                vm_still_exists = any(vm.name == vm_name for vm in container.view)
                container.Destroy()

                if vm_still_exists:
                    print(f" Warning: VM '{vm_name}' still exists after deletion attempt")
                else:
                    print(f" Confirmed: VM '{vm_name}' has been removed")

                # Update available VMs list
                available_vms = list_available_vms(content)
                print(f"\nUpdated VM list ({len(available_vms)}):")
                for i, vm_name in enumerate(available_vms, 1):
                    print(f"  {i:2d}. {vm_name}")

            except Exception as e:
                print(f" Error deleting VM '{vm_name}': {e}")

        # Clean up
        connect.Disconnect(si)
        print("\n VM deletion session completed!")

    except Exception as e:
        print(f" VM deletion test failed with error: {e}")
        return False

    return True

if __name__ == "__main__":
    delete_test_vm()
