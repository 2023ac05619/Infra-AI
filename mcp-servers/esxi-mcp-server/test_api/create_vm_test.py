#!/usr/bin/env python3
import ssl
from pyVim import connect
from pyVmomi import vim

def create_test_vm():
    try:
        # Configuration from config.yaml
        vcenter_host = "192.168.203.178"
        vcenter_user = "root"
        vcenter_password = "TempP@ssw0rd"
        insecure = True
        test_vm_name = "mcp-test"

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

        # Get datacenter and other objects
        datacenter_obj = next((dc for dc in content.rootFolder.childEntity
                              if isinstance(dc, vim.Datacenter)), None)
        if not datacenter_obj:
            raise Exception("No datacenter object found")

        # Get resource pool
        compute_resource = next((cr for cr in datacenter_obj.hostFolder.childEntity
                              if isinstance(cr, vim.ComputeResource)), None)
        if not compute_resource:
            raise Exception("No compute resource (cluster or host) found")
        resource_pool = compute_resource.resourcePool

        # Get datastore (largest available)
        datastores = [ds for ds in datacenter_obj.datastoreFolder.childEntity if isinstance(ds, vim.Datastore)]
        if not datastores:
            raise Exception("No available datastore found in the datacenter")
        datastore_obj = max(datastores, key=lambda ds: ds.summary.freeSpace)

        # Get network
        networks = datacenter_obj.networkFolder.childEntity
        network_obj = next((net for net in networks if net.name == "VM Network"), None)

        print(f"Using resource pool: {resource_pool.name}")
        print(f"Using datastore: {datastore_obj.name}")
        print(f"Using network: {network_obj.name if network_obj else 'None'}")

        # Check if VM already exists
        container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
        existing_vm = None
        for vm in container.view:
            if vm.name == test_vm_name:
                existing_vm = vm
                break
        container.Destroy()

        if existing_vm:
            print(f"VM '{test_vm_name}' already exists!")
            connect.Disconnect(si)
            return True

        # Create test VM
        print(f"\n--- Creating test VM '{test_vm_name}' ---")
        print("Specifications: 1 CPU, 512MB RAM, 10GB disk")

        vm_spec = vim.vm.ConfigSpec(name=test_vm_name, memoryMB=512, numCPUs=1, guestId="otherGuest")
        # Set VM file location
        vm_spec.files = vim.vm.FileInfo()
        vm_spec.files.vmPathName = f"[{datastore_obj.name}] {test_vm_name}"
        device_specs = []

        # Add SCSI controller
        controller_spec = vim.vm.device.VirtualDeviceSpec()
        controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        controller_spec.device = vim.vm.device.ParaVirtualSCSIController()
        controller_spec.device.deviceInfo = vim.Description(label="SCSI Controller", summary="ParaVirtual SCSI Controller")
        controller_spec.device.busNumber = 0
        controller_spec.device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
        controller_spec.device.key = -101
        device_specs.append(controller_spec)

        # Add virtual disk
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.create
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.capacityInKB = 1024 * 1024 * 10  # 10GB disk
        disk_spec.device.deviceInfo = vim.Description(label="Hard Disk 1", summary="10 GB disk")
        disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_spec.device.backing.diskMode = "persistent"
        disk_spec.device.backing.thinProvisioned = True
        disk_spec.device.backing.datastore = datastore_obj
        disk_spec.device.controllerKey = controller_spec.device.key
        disk_spec.device.unitNumber = 0
        device_specs.append(disk_spec)

        # Add network adapter if network exists
        if network_obj:
            nic_spec = vim.vm.device.VirtualDeviceSpec()
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            nic_spec.device = vim.vm.device.VirtualVmxnet3()
            nic_spec.device.deviceInfo = vim.Description(label="Network Adapter 1", summary=network_obj.name)
            if isinstance(network_obj, vim.Network):
                nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo(network=network_obj, deviceName=network_obj.name)
            elif isinstance(network_obj, vim.dvs.DistributedVirtualPortgroup):
                dvs_uuid = network_obj.config.distributedVirtualSwitch.uuid
                port_key = network_obj.key
                nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo(
                    port=vim.dvs.PortConnection(portgroupKey=port_key, switchUuid=dvs_uuid)
                )
            nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo(startConnected=True, allowGuestControl=True)
            device_specs.append(nic_spec)

        vm_spec.deviceChange = device_specs

        # Create the VM
        vm_folder = datacenter_obj.vmFolder
        task = vm_folder.CreateVM_Task(config=vm_spec, pool=resource_pool)

        # Wait for task completion
        print("Creating VM...")
        while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
            continue

        if task.info.state == vim.TaskInfo.State.error:
            raise task.info.error

        print(f" VM '{test_vm_name}' created successfully!")

        # Clean up
        connect.Disconnect(si)

        print(f"\n VM '{test_vm_name}' is now ready for testing!")
        return True

    except Exception as e:
        print(f" VM creation failed with error: {e}")
        return False

if __name__ == "__main__":
    create_test_vm()
