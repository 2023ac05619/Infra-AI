import os
import json
import logging
import ssl
import argparse
from dataclasses import dataclass
from typing import Optional, Dict, Any

# MCP protocol related imports
from mcp.server.lowlevel import Server  # MCP server base class
from mcp import types  # MCP type definitions

# pyVmomi VMware API imports
from pyVim import connect
from pyVmomi import vim, vmodl

# Configuration data class for storing configuration options
@dataclass
class Config:
    vcenter_host: str
    vcenter_user: str
    vcenter_password: str
    datacenter: Optional[str] = None   # Datacenter name (optional)
    cluster: Optional[str] = None      # Cluster name (optional)
    datastore: Optional[str] = None    # Datastore name (optional)
    network: Optional[str] = None      # Virtual network name (optional)
    insecure: bool = False             # Whether to skip SSL certificate verification (default: False)
    log_file: Optional[str] = None     # Log file path (if not specified, output to console)
    log_level: str = "INFO"            # Log level
    port: int = 8080                   # Server port (default: 8080)

# VMware management class for stateless operations
# class VMwareManager:
#     def __init__(self, config: Config):
#         self.config = config

#     def _connect_vcenter(self):
#         """Connect to vCenter/ESXi and retrieve main resource object references."""
#         # if hasattr(self, 'si') and self.si and hasattr(self, 'content') and self.content:
#         #     try:
#         #         # 'about' is a lightweight property to test if the session is alive
#         #         session_manager = self.content.sessionManager
#         #         if session_manager.currentSession:
#         #             return  # Connection is healthy, no need to reconnect
#         #     except Exception:
#         #         # If checking fails, the session is dead. Clean up and continue to reconnect.
#         #         logging.warning("vCenter session stale. Reconnecting...")
#         #         try:
#         #             connect.Disconnect(self.si)
#         #         except:
#         #             pass
#         #         self.si = None

#         try:
#             if self.config.insecure:
#                 # Connection method without SSL certificate verification
#                 context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
#                 context.check_hostname = False  # Disable hostname checking
#                 context.verify_mode = ssl.CERT_NONE
#                 self.si = connect.SmartConnect(
#                     host=self.config.vcenter_host,
#                     user=self.config.vcenter_user,
#                     pwd=self.config.vcenter_password,
#                     sslContext=context)
#             else:
#                 # Standard SSL verification connection
#                 self.si = connect.SmartConnect(
#                     host=self.config.vcenter_host,
#                     user=self.config.vcenter_user,
#                     pwd=self.config.vcenter_password)

#             # Retrieve content root object
#             self.content = self.si.RetrieveContent()
#             logging.info("Successfully connected to VMware vCenter/ESXi API")

#             # Retrieve target datacenter object
#             if self.config.datacenter:
#                 # Find specified datacenter by name
#                 self.datacenter_obj = next((dc for dc in self.content.rootFolder.childEntity
#                                             if isinstance(dc, vim.Datacenter) and dc.name == self.config.datacenter), None)
#                 if not self.datacenter_obj:
#                     logging.error(f"Datacenter named {self.config.datacenter} not found")
#                     raise Exception(f"Datacenter {self.config.datacenter} not found")
#             else:
#                 # Default to the first available datacenter
#                 self.datacenter_obj = next((dc for dc in self.content.rootFolder.childEntity
#                                           if isinstance(dc, vim.Datacenter)), None)
#             if not self.datacenter_obj:
#                 raise Exception("No datacenter object found")

#             # Retrieve resource pool (if a cluster is configured, use the cluster's resource pool; otherwise, use the host resource pool)
#             compute_resource = None
#             if self.config.cluster:
#                 # Find specified cluster
#                 for folder in self.datacenter_obj.hostFolder.childEntity:
#                     if isinstance(folder, vim.ClusterComputeResource) and folder.name == self.config.cluster:
#                         compute_resource = folder
#                         break
#                 if not compute_resource:
#                     logging.error(f"Cluster named {self.config.cluster} not found")
#                     raise Exception(f"Cluster {self.config.cluster} not found")
#             else:
#                 # Default to the first ComputeResource (cluster or standalone host)
#                 compute_resource = next((cr for cr in self.datacenter_obj.hostFolder.childEntity
#                                       if isinstance(cr, vim.ComputeResource)), None)
#             if not compute_resource:
#                 raise Exception("No compute resource (cluster or host) found")
#             self.resource_pool = compute_resource.resourcePool
#             logging.info(f"Using resource pool: {self.resource_pool.name}")

#             # Retrieve datastore object
#             if self.config.datastore:
#                 # Find specified datastore in the datacenter
#                 self.datastore_obj = next((ds for ds in self.datacenter_obj.datastoreFolder.childEntity
#                                        if isinstance(ds, vim.Datastore) and ds.name == self.config.datastore), None)
#                 if not self.datastore_obj:
#                     logging.error(f"Datastore named {self.config.datastore} not found")
#                     raise Exception(f"Datastore {self.config.datastore} not found")
#             else:
#                 # Default to the datastore with the largest available capacity
#                 datastores = [ds for ds in self.datacenter_obj.datastoreFolder.childEntity if isinstance(ds, vim.Datastore)]
#                 if not datastores:
#                     raise Exception("No available datastore found in the datacenter")
#                 # Select the one with the maximum free space
#                 self.datastore_obj = max(datastores, key=lambda ds: ds.summary.freeSpace)
#             logging.info(f"Using datastore: {self.datastore_obj.name}")

#             # Retrieve network object (network or distributed virtual portgroup)
#             if self.config.network:
#                 # Find specified network in the datacenter network list
#                 networks = self.datacenter_obj.networkFolder.childEntity
#                 self.network_obj = next((net for net in networks if net.name == self.config.network), None)
#                 if not self.network_obj:
#                     logging.error(f"Network {self.config.network} not found")
#                     raise Exception(f"Network {self.config.network} not found")
#                 logging.info(f"Using network: {self.network_obj.name}")
#             else:
#                 self.network_obj = None  # If no network is specified, VM creation can choose to not connect to a network
#         except Exception as e:
#             logging.error(f"Failed to connect to vCenter/ESXi: {e}")
#             raise Exception(f"Failed to connect to vCenter/ESXi: {e}")
        
        
#         logging.info("VMware connection successful..")
        
#     def _reset_connection_state(self):
#         """Reset connection state to force a fresh connection."""
#         if hasattr(self, 'si') and self.si:
#             try:
#                 connect.Disconnect(self.si)
#                 logging.info("Reset VMware connection state successful..")
#             except:
#                 pass
#         self.si = None
#         self.content = None
#         self.datacenter_obj = None
#         self.resource_pool = None
#         self.datastore_obj = None
#         self.network_obj = None

#     # def _check_connection(self):
#     #     """Check if the current connection is valid; if not, reconnect."""
#     #     if hasattr(self, 'si') and self.si:
#     #         try:
#     #             # Test if the connection is still valid
#     #             self.content.about  # Simple test to see if session is active
#     #         except:
#     #             # Connection is stale, disconnect and reconnect
#     #             try:
#     #                 connect.Disconnect(self.si)
#     #             except:
#     #                 pass
#     #             self._connect_vcenter()
                
#     def list_vms(self) -> list:
#         """List all virtual machine names."""
#         # Create new connection for this operation
#         self._reset_connection_state()
#         self._connect_vcenter()
#         if self.si == None or self.content == None or self.datacenter_obj == None or self.resource_pool == None or self.datastore_obj == None or self.network_obj == None:
#             raise Exception("VMware objects missing, connection not properly established..")
#         try:
#             vm_list = []
#             # Create a view to iterate over all virtual machines
#             container = self.content.viewManager.CreateContainerView(self.content.rootFolder, [vim.VirtualMachine], True)
#             for vm in container.view:
#                 vm_list.append(vm.name)
#             container.Destroy()
#             return vm_list
#         finally:
#             # Always disconnect after operation
#             if hasattr(self, 'si') and self.si:
#                 connect.Disconnect(self.si)

#     def find_vm(self, name: str) -> Optional[vim.VirtualMachine]:
#         """Find virtual machine object by name."""
#         # Create new connection for this operation
#         self._reset_connection_state()
#         self._connect_vcenter()
#         if self.si == None or self.content == None or self.datacenter_obj == None or self.resource_pool == None or self.datastore_obj == None or self.network_obj == None:
#             raise Exception("VMware objects missing, connection not properly established..")
#         try :
#             container = self.content.viewManager.CreateContainerView(self.content.rootFolder, [vim.VirtualMachine], True)
#             vm_obj = None
#             for vm in container.view:
#                 if vm.name == name:
#                     vm_obj = vm
#                     break
#             container.Destroy()
#             return vm_obj
#         finally:
#             # Always disconnect after operation
#             if hasattr(self, 'si') and self.si:
#                 connect.Disconnect(self.si)

#     def get_vm_performance(self, vm_name: str) -> Dict[str, Any]:
#         """Retrieve performance data (CPU, memory, storage, and network) for the specified virtual machine."""
#         # Create new connection for this operation
#         self._reset_connection_state()
#         self._connect_vcenter()
#         if self.si == None or self.content == None or self.datacenter_obj == None or self.resource_pool == None or self.datastore_obj == None or self.network_obj == None:
#             raise Exception("VMware objects missing, connection not properly established..")
#         try:
#             vm = self.find_vm(vm_name)
#             if not vm:
#                 raise Exception(f"VM {vm_name} not found")
#             # CPU and memory usage (obtained from quickStats)
#             stats = {}
#             qs = vm.summary.quickStats
#             stats["cpu_usage"] = qs.overallCpuUsage  # MHz
#             stats["memory_usage"] = qs.guestMemoryUsage  # MB
#             # Storage usage (committed storage, in GB)
#             committed = vm.summary.storage.committed if vm.summary.storage else 0
#             stats["storage_usage"] = round(committed / (1024**3), 2)  # Convert to GB
#             # Network usage (obtained from host or VM NIC statistics, latest sample)
#             # Here we simply obtain the latest performance counter for VM network I/O
#             net_bytes_transmitted = 0
#             net_bytes_received = 0
#             try:
#                 pm = self.content.perfManager
#                 # Define performance counter IDs to query: network transmitted and received bytes
#                 counter_ids = []
#                 for c in pm.perfCounter:
#                     counter_full_name = f"{c.groupInfo.key}.{c.nameInfo.key}.{c.rollupType}"
#                     if counter_full_name in ("net.transmitted.average", "net.received.average"):
#                         counter_ids.append(c.key)
#                 if counter_ids:
#                     query = vim.PerformanceManager.QuerySpec(maxSample=1, entity=vm, metricId=[vim.PerformanceManager.MetricId(counterId=cid, instance="*") for cid in counter_ids])
#                     stats_res = pm.QueryStats(querySpec=[query])
#                     for series in stats_res[0].value:
#                         # Sum data from each network interface
#                         if series.id.counterId == counter_ids[0]:
#                             net_bytes_transmitted = sum(series.value)
#                         elif series.id.counterId == counter_ids[1]:
#                             net_bytes_received = sum(series.value)
#                 stats["network_transmit_KBps"] = net_bytes_transmitted
#                 stats["network_receive_KBps"] = net_bytes_received
#             except Exception as e:
#                 # If obtaining performance counters fails, log the error but do not terminate
#                 logging.warning(f"Failed to retrieve network performance data: {e}")
#                 stats["network_transmit_KBps"] = None
#                 stats["network_receive_KBps"] = None
#             return stats
#         finally:
#             # Always disconnect after operation
#             if hasattr(self, 'si') and self.si:
#                 connect.Disconnect(self.si)

#     def create_vm(self, name: str, cpus: int, memory_mb: int, datastore: Optional[str] = None, network: Optional[str] = None) -> str:
#         """Create a new virtual machine (from scratch, with an empty disk and optional network)."""
#         # Create new connection for this operation
#         self._reset_connection_state()
#         self._connect_vcenter()
#         if self.si == None or self.content == None or self.datacenter_obj == None or self.resource_pool == None or self.datastore_obj == None or self.network_obj == None:
#             raise Exception("VMware objects missing, connection not properly established..")
#         # If a specific datastore or network is provided, update the corresponding object accordingly
#         try:
#             datastore_obj = self.datastore_obj
#             network_obj = self.network_obj
#             if datastore:
#                 datastore_obj = next((ds for ds in self.datacenter_obj.datastoreFolder.childEntity
#                                     if isinstance(ds, vim.Datastore) and ds.name == datastore), None)
#                 if not datastore_obj:
#                     raise Exception(f"Specified datastore {datastore} not found")
#             if network:
#                 networks = self.datacenter_obj.networkFolder.childEntity
#                 network_obj = next((net for net in networks if net.name == network), None)
#                 if not network_obj:
#                     raise Exception(f"Specified network {network} not found")

#             # Build VM configuration specification
#             vm_spec = vim.vm.ConfigSpec(name=name, memoryMB=memory_mb, numCPUs=cpus, guestId="otherGuest")  # guestId can be adjusted as needed
#             vm_spec.files = vim.vm.FileInfo()
#             vm_spec.files.vmPathName = f"[{datastore_obj.name}] {name}/"
#             device_specs = []

#             # Add SCSI controller
#             controller_spec = vim.vm.device.VirtualDeviceSpec()
#             controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
#             controller_spec.device = vim.vm.device.ParaVirtualSCSIController()  # Using ParaVirtual SCSI controller
#             controller_spec.device.deviceInfo = vim.Description(label="SCSI Controller", summary="ParaVirtual SCSI Controller")
#             controller_spec.device.busNumber = 0
#             controller_spec.device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
#             # Set a temporary negative key for the controller for later reference
#             controller_spec.device.key = -101
#             device_specs.append(controller_spec)

#             # Add virtual disk
#             disk_spec = vim.vm.device.VirtualDeviceSpec()
#             disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
#             disk_spec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.create
#             disk_spec.device = vim.vm.device.VirtualDisk()
#             disk_spec.device.capacityInKB = 1024 * 1024 * 10  # Create a 10GB disk
#             disk_spec.device.deviceInfo = vim.Description(label="Hard Disk 1", summary="10 GB disk")
#             disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
#             disk_spec.device.backing.diskMode = "persistent"
#             disk_spec.device.backing.thinProvisioned = True  # Thin provisioning
#             disk_spec.device.backing.datastore = datastore_obj
#             # Attach the disk to the previously created controller
#             disk_spec.device.controllerKey = controller_spec.device.key
#             disk_spec.device.unitNumber = 0
#             device_specs.append(disk_spec)

#             # If a network is provided, add a virtual network adapter
#             if network_obj:
#                 nic_spec = vim.vm.device.VirtualDeviceSpec()
#                 nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
#                 nic_spec.device = vim.vm.device.VirtualVmxnet3()  # Using VMXNET3 network adapter
#                 nic_spec.device.deviceInfo = vim.Description(label="Network Adapter 1", summary=network_obj.name)
#                 if isinstance(network_obj, vim.Network):
#                     nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo(network=network_obj, deviceName=network_obj.name)
#                 elif isinstance(network_obj, vim.dvs.DistributedVirtualPortgroup):
#                     # Distributed virtual switch portgroup
#                     dvs_uuid = network_obj.config.distributedVirtualSwitch.uuid
#                     port_key = network_obj.key
#                     nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo(
#                         port=vim.dvs.PortConnection(portgroupKey=port_key, switchUuid=dvs_uuid)
#                     )
#                 nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo(startConnected=True, allowGuestControl=True)
#                 device_specs.append(nic_spec)

#             vm_spec.deviceChange = device_specs

#             # Get the folder in which to place the VM (default is the datacenter's vmFolder)
#             vm_folder = self.datacenter_obj.vmFolder
#             # Create the VM in the specified resource pool
#             try:
#                 task = vm_folder.CreateVM_Task(config=vm_spec, pool=self.resource_pool)
#                 # Wait for the task to complete
#                 while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
#                     continue
#                 if task.info.state == vim.TaskInfo.State.error:
#                     raise task.info.error
#             except Exception as e:
#                 logging.error(f"Failed to create virtual machine: {e}")
#                 raise
            
#             logging.info(f"Virtual machine created: {name}")
#             return f"VM '{name}' created."
#         finally:
#             # Always disconnect after operation
#             if hasattr(self, 'si') and self.si:
#                 connect.Disconnect(self.si)
                

#     def clone_vm(self, template_name: str, new_name: str) -> str:
#         """Clone a new virtual machine from an existing template or VM."""
#        # Create new connection for this operation
#         self._reset_connection_state()
#         self._connect_vcenter()
#         if self.si == None or self.content == None or self.datacenter_obj == None or self.resource_pool == None or self.datastore_obj == None or self.network_obj == None:
#             raise Exception("VMware objects missing, connection not properly established..")
#         try:
            
#             template_vm = self.find_vm(template_name)
#             if not template_vm:
#                 raise Exception(f"Template virtual machine {template_name} not found")
#             vm_folder = template_vm.parent  # Place the new VM in the same folder as the template
#             if not isinstance(vm_folder, vim.Folder):
#                 vm_folder = self.datacenter_obj.vmFolder
#             # Use the resource pool of the host/cluster where the template is located
#             resource_pool = template_vm.resourcePool or self.resource_pool
#             relocate_spec = vim.vm.RelocateSpec(pool=resource_pool, datastore=self.datastore_obj)
#             clone_spec = vim.vm.CloneSpec(powerOn=False, template=False, location=relocate_spec)
#             try:
#                 task = template_vm.Clone(folder=vm_folder, name=new_name, spec=clone_spec)
#                 while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
#                     continue
#                 if task.info.state == vim.TaskInfo.State.error:
#                     raise task.info.error
#             except Exception as e:
#                 logging.error(f"Failed to clone virtual machine: {e}")
#                 raise
#             logging.info(f"Cloned virtual machine {template_name} to new VM: {new_name}")
#             return f"VM '{new_name}' cloned from '{template_name}'."
        
#         finally:
#                 # Always disconnect after operation
#                 if hasattr(self, 'si') and self.si:
#                     connect.Disconnect(self.si)

#     def delete_vm(self, name: str) -> str:
#         """Delete the specified virtual machine."""
#         # Create new connection for this operation
#         self._reset_connection_state()
#         self._connect_vcenter()
#         if self.si == None or self.content == None or self.datacenter_obj == None or self.resource_pool == None or self.datastore_obj == None or self.network_obj == None:
#             raise Exception("VMware objects missing, connection not properly established..")
#         try:
#             vm = self.find_vm(name)
#             if not vm:
#                 raise Exception(f"Virtual machine {name} not found")
#             try:
#                 task = vm.Destroy_Task()
#                 while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
#                     continue
#                 if task.info.state == vim.TaskInfo.State.error:
#                     raise task.info.error
#             except Exception as e:
#                 logging.error(f"Failed to delete virtual machine: {e}")
#                 raise
#             logging.info(f"Virtual machine deleted: {name}")
#             return f"VM '{name}' deleted."
#         finally:
#             # Always disconnect after operation
#             if hasattr(self, 'si') and self.si:
#                 connect.Disconnect(self.si)

#     def power_on_vm(self, name: str) -> str:
#         """Power on the specified virtual machine."""
#         # Create new connection for this operation
#         self._reset_connection_state()
#         self._connect_vcenter()
#         if self.si == None or self.content == None or self.datacenter_obj == None or self.resource_pool == None or self.datastore_obj == None or self.network_obj == None:
#             raise Exception("VMware objects missing, connection not properly established..")
#         try:
#             vm = self.find_vm(name)
#             if not vm:
#                 raise Exception(f"Virtual machine {name} not found")
#             if vm.runtime.powerState == vim.VirtualMachine.PowerState.poweredOn:
#                 return f"VM '{name}' is already powered on."
#             task = vm.PowerOnVM_Task()
#             while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
#                 continue
#             if task.info.state == vim.TaskInfo.State.error:
#                 raise task.info.error
#             logging.info(f"Virtual machine powered on: {name}")
#             return f"VM '{name}' powered on."
#         finally:
#             # Always disconnect after operation
#             if hasattr(self, 'si') and self.si:
#                 connect.Disconnect(self.si)

#     def power_off_vm(self, name: str) -> str:
#         """Power off the specified virtual machine."""
#         # Create new connection for this operation
#         self._reset_connection_state()
#         self._connect_vcenter()
#         if self.si == None or self.content == None or self.datacenter_obj == None or self.resource_pool == None or self.datastore_obj == None or self.network_obj == None:
#             raise Exception("VMware objects missing, connection not properly established..")
#         try:
#             vm = self.find_vm(name)
#             if not vm:
#                 raise Exception(f"Virtual machine {name} not found")
#             if vm.runtime.powerState == vim.VirtualMachine.PowerState.poweredOff:
#                 return f"VM '{name}' is already powered off."
#             task = vm.PowerOffVM_Task()
#             while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
#                 continue
#             if task.info.state == vim.TaskInfo.State.error:
#                 raise task.info.error
#             logging.info(f"Virtual machine powered off: {name}")
#             return f"VM '{name}' powered off."
#         finally:
#             # Always disconnect after operation
#             if hasattr(self, 'si') and self.si:
#                 connect.Disconnect(self.si)
# VMware management class for stateless operations
class VMwareManager:
    def __init__(self, config: Config):
        self.config = config
        self.si = None
        self.content = None
        self.datacenter_obj = None
        self.resource_pool = None
        self.datastore_obj = None
        self.network_obj = None

    def _connect_vcenter(self):
        """Connect to vCenter/ESXi and retrieve main resource object references."""
        # Check if we already have a healthy session
        if self.si and self.content:
            try:
                session_manager = self.content.sessionManager
                if session_manager.currentSession:
                    return 
            except:
                self._reset_connection_state()

        try:
            if self.config.insecure:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.si = connect.SmartConnect(
                    host=self.config.vcenter_host,
                    user=self.config.vcenter_user,
                    pwd=self.config.vcenter_password,
                    sslContext=context)
            else:
                self.si = connect.SmartConnect(
                    host=self.config.vcenter_host,
                    user=self.config.vcenter_user,
                    pwd=self.config.vcenter_password)

            self.content = self.si.RetrieveContent()
            
            # Setup Datacenter
            if self.config.datacenter:
                self.datacenter_obj = next((dc for dc in self.content.rootFolder.childEntity
                                            if isinstance(dc, vim.Datacenter) and dc.name == self.config.datacenter), None)
            else:
                self.datacenter_obj = next((dc for dc in self.content.rootFolder.childEntity
                                          if isinstance(dc, vim.Datacenter)), None)
            
            if not self.datacenter_obj:
                raise Exception("No datacenter object found")

            # Setup Compute Resource / Resource Pool
            if self.config.cluster:
                compute_resource = next((folder for folder in self.datacenter_obj.hostFolder.childEntity 
                                       if isinstance(folder, vim.ClusterComputeResource) and folder.name == self.config.cluster), None)
            else:
                compute_resource = next((cr for cr in self.datacenter_obj.hostFolder.childEntity
                                      if isinstance(cr, vim.ComputeResource)), None)
            
            if not compute_resource:
                raise Exception("No compute resource found")
            self.resource_pool = compute_resource.resourcePool

            # Setup Datastore
            if self.config.datastore:
                self.datastore_obj = next((ds for ds in self.datacenter_obj.datastoreFolder.childEntity
                                       if isinstance(ds, vim.Datastore) and ds.name == self.config.datastore), None)
            else:
                datastores = [ds for ds in self.datacenter_obj.datastoreFolder.childEntity if isinstance(ds, vim.Datastore)]
                if datastores:
                    self.datastore_obj = max(datastores, key=lambda ds: ds.summary.freeSpace)
            
            # Setup Network
            if self.config.network:
                networks = self.datacenter_obj.networkFolder.childEntity
                self.network_obj = next((net for net in networks if net.name == self.config.network), None)

            logging.info("VMware connection established.")

        except Exception as e:
            logging.error(f"Failed to connect: {e}")
            raise

    def _reset_connection_state(self):
        """Reset connection state to force a fresh connection."""
        if self.si:
            try:
                connect.Disconnect(self.si)
            except:
                pass
        self.si = None
        self.content = None

    def list_vms(self) -> list:
        """List all virtual machine names."""
        self._connect_vcenter()
        
        vm_list = []
        container = None
        try:
            container = self.content.viewManager.CreateContainerView(
                self.datacenter_obj, [vim.VirtualMachine], True
            )
            for vm in container.view:
                vm_list.append(vm.name)
        finally:
            if container:
                container.Destroy()
            # Note: Do NOT disconnect here if you plan to reuse the manager, 
            # but since your tools create a fresh manager each time, it's okay to let python GC handle it
            # or explicitly disconnect in the Tool function wrapper.
        return vm_list

    def find_vm(self, name: str) -> Optional[vim.VirtualMachine]:
        """Find virtual machine object by name."""
        # Check connection first
        self._connect_vcenter()
        
        vm_obj = None
        container = None
        try:
            container = self.content.viewManager.CreateContainerView(
                self.datacenter_obj, [vim.VirtualMachine], True
            )
            for vm in container.view:
                if vm.name == name:
                    vm_obj = vm
                    break
        finally:
            if container:
                container.Destroy()
            # CRITICAL FIX: Do NOT Disconnect(self.si) here!
            # Returning the vm_obj requires the session to stay open.

        return vm_obj

    def get_vm_performance(self, vm_name: str) -> Dict[str, Any]:
        """Retrieve performance data."""
        self._connect_vcenter()
        
        vm = self.find_vm(vm_name)
        if not vm:
            raise Exception(f"VM {vm_name} not found")

        stats = {}
        qs = vm.summary.quickStats
        stats["cpu_usage"] = qs.overallCpuUsage
        stats["memory_usage"] = qs.guestMemoryUsage
        
        committed = vm.summary.storage.committed if vm.summary.storage else 0
        stats["storage_usage"] = round(committed / (1024**3), 2)
        
        return stats

    def create_vm(self, name: str, cpus: int, memory_mb: int, datastore: Optional[str] = None, network: Optional[str] = None) -> str:
        """Create a new virtual machine."""
        self._connect_vcenter()
        
        # Use existing objects setup in _connect_vcenter, or override if args provided
        ds_obj = self.datastore_obj
        if datastore:
            ds_obj = next((ds for ds in self.datacenter_obj.datastoreFolder.childEntity
                         if isinstance(ds, vim.Datastore) and ds.name == datastore), None)
            if not ds_obj:
                raise Exception(f"Datastore {datastore} not found")

        net_obj = self.network_obj
        if network:
             networks = self.datacenter_obj.networkFolder.childEntity
             net_obj = next((net for net in networks if net.name == network), None)

        # Build ConfigSpec (kept largely the same as your code)
        vm_spec = vim.vm.ConfigSpec(name=name, memoryMB=memory_mb, numCPUs=cpus, guestId="otherGuest")
        vm_spec.files = vim.vm.FileInfo(vmPathName=f"[{ds_obj.name}] {name}/")
        
        # Add Devices (Disk/Network) logic here...
        # [Abbreviated for brevity, paste your specific device creation code here]
        # ...

        # Execute
        vm_folder = self.datacenter_obj.vmFolder
        task = vm_folder.CreateVM_Task(config=vm_spec, pool=self.resource_pool)
        self._wait_for_task(task)
        
        return f"VM '{name}' created."

    def clone_vm(self, template_name: str, new_name: str) -> str:
        """Clone a new virtual machine."""
        self._connect_vcenter()
        
        template_vm = self.find_vm(template_name)
        if not template_vm:
            raise Exception(f"Template {template_name} not found")

        relocate_spec = vim.vm.RelocateSpec(pool=self.resource_pool, datastore=self.datastore_obj)
        clone_spec = vim.vm.CloneSpec(powerOn=False, template=False, location=relocate_spec)

        task = template_vm.Clone(folder=self.datacenter_obj.vmFolder, name=new_name, spec=clone_spec)
        self._wait_for_task(task)
        
        return f"VM '{new_name}' cloned from '{template_name}'."

    def delete_vm(self, name: str) -> str:
        """Delete the specified virtual machine."""
        self._connect_vcenter()
        
        # This now works because find_vm does NOT disconnect the session
        vm = self.find_vm(name)
        if not vm:
            raise Exception(f"VM {name} not found")
            
        task = vm.Destroy_Task()
        self._wait_for_task(task)
        
        return f"VM '{name}' deleted."

    def power_on_vm(self, name: str) -> str:
        """Power on the specified virtual machine."""
        self._connect_vcenter()
        
        vm = self.find_vm(name)
        if not vm:
            raise Exception(f"VM {name} not found")
            
        if vm.runtime.powerState == vim.VirtualMachine.PowerState.poweredOn:
            return f"VM '{name}' is already powered on."
            
        task = vm.PowerOnVM_Task()
        self._wait_for_task(task)
        
        return f"VM '{name}' powered on."

    def power_off_vm(self, name: str) -> str:
        """Power off the specified virtual machine."""
        self._connect_vcenter()
        
        vm = self.find_vm(name)
        if not vm:
            raise Exception(f"VM {name} not found")

        if vm.runtime.powerState == vim.VirtualMachine.PowerState.poweredOff:
            return f"VM '{name}' is already powered off."
            
        task = vm.PowerOffVM_Task()
        self._wait_for_task(task)
        
        return f"VM '{name}' powered off."

    def _wait_for_task(self, task):
        """Helper to wait for task completion"""
        while task.info.state in [vim.TaskInfo.State.running, vim.TaskInfo.State.queued]:
            continue
        if task.info.state == vim.TaskInfo.State.error:
            raise task.info.error
# ---------------- MCP Server Definition ----------------

# Initialize MCP Server object
mcp_server = Server(name="VMware-MCP-Server", version="0.0.1")
# Define supported tools (executable operations) and resources (data interfaces)
# The implementation of tools and resources will call methods in VMwareManager
# Note: For each operation, perform API key authentication check, and only execute sensitive operations if the authenticated flag is True
# If not authenticated, an exception is raised

# Tool 1: Create virtual machine
def tool_create_vm(name: str, cpu: int, memory: int, datastore: str = None, network: str = None) -> str:
    """Create a new virtual machine."""
    # Authentication disabled for open access
    # fresh_manager = VMwareManager(config)
    # return fresh_manager.create_vm(name, cpu, memory, datastore, network)
    return manager.create_vm(name, cpu, memory, datastore, network)

# Tool 3: Clone virtual machine
def tool_clone_vm(template_name: str, new_name: str) -> str:
    """Clone a virtual machine from a template."""
    # Authentication disabled for open access
    # fresh_manager = VMwareManager(config)
    return manager.clone_vm(template_name, new_name)

# Tool 4: Delete virtual machine
def tool_delete_vm(name: str) -> str:
    """Delete the specified virtual machine."""
    # Authentication disabled for open access
    # fresh_manager = VMwareManager(config)
    return manager.delete_vm(name)

# Tool 5: Power on virtual machine
def tool_power_on(name: str) -> str:
    """Power on the specified virtual machine."""
    # Authentication disabled for open access
    # fresh_manager = VMwareManager(config)
    return manager.power_on_vm(name)

# Tool 6: Power off virtual machine
def tool_power_off(name: str) -> str:
    """Power off the specified virtual machine."""
    # Authentication disabled for open access
    # fresh_manager = VMwareManager(config)
    return manager.power_off_vm(name)

# Tool 7: List all virtual machines
def tool_list_vms() -> list:
    """Return a list of all virtual machine names."""
    # Authentication disabled for open access
    # fresh_manager = VMwareManager(config)
    return manager.list_vms()
# def tool_list_vms() -> list:
#     """Return a list of all virtual machine names."""
#     # Reset any stale state
#     manager._reset_connection_state()
#     # Establish fresh connection for this operation
#     manager._connect_vcenter()
#     try:
#         return manager.list_vms()
#     finally:
#         # Clean disconnect after operation
#         if hasattr(manager, 'si') and manager.si:
#             connect.Disconnect(manager.si)


# Resource 1: Retrieve virtual machine performance data
def resource_vm_performance(vm_name: str) -> dict:
    """Retrieve CPU, memory, storage, and network usage for the specified virtual machine."""
    # Authentication disabled for open access
    return manager.get_vm_performance(vm_name)

# Register the above functions as tools and resources for the MCP Server
# Encapsulate using mcp.types.Tool and mcp.types.Resource
tools = {
    "createVM": types.Tool(
        name="createVM",
        description="Create a new virtual machine",
        parameters={"name": str, "cpu": int, "memory": int, "datastore": Optional[str], "network": Optional[str]},
        handler=lambda params: tool_create_vm(**params),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "cpu": {"type": "integer"},
                "memory": {"type": "integer"},
                "datastore": {"type": "string", "nullable": True},
                "network": {"type": "string", "nullable": True}
            },
            "required": ["name", "cpu", "memory"]
        }
    ),
    "cloneVM": types.Tool(
        name="cloneVM",
        description="Clone a virtual machine from a template or existing VM",
        parameters={"template_name": str, "new_name": str},
        handler=lambda params: tool_clone_vm(**params),
        inputSchema={
            "type": "object",
            "properties": {
                "template_name": {"type": "string"},
                "new_name": {"type": "string"}
            },
            "required": ["template_name", "new_name"]
        }
    ),
    "deleteVM": types.Tool(
        name="deleteVM",
        description="Delete a virtual machine",
        parameters={"name": str},
        handler=lambda params: tool_delete_vm(**params),
        inputSchema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
    ),
    "powerOn": types.Tool(
        name="powerOn",
        description="Power on a virtual machine",
        parameters={"name": str},
        handler=lambda params: tool_power_on(**params),
        inputSchema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
    ),
    "powerOff": types.Tool(
        name="powerOff",
        description="Power off a virtual machine",
        parameters={"name": str},
        handler=lambda params: tool_power_off(**params),
        inputSchema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
    ),
    "listVMs": types.Tool(
        name="listVMs",
        description="List all virtual machines",
        parameters={},
        handler=lambda params: tool_list_vms(),
        inputSchema={"type": "object", "properties": {}}
    )
}
resources = {
    "vmStats": types.Resource(
        name="vmStats",
        uri="vmstats://{vm_name}",
        description="Get CPU, memory, storage, network usage of a VM",
        parameters={"vm_name": str},
        handler=lambda params: resource_vm_performance(**params),
        inputSchema={
            "type": "object",
            "properties": {
                "vm_name": {"type": "string"}
            },
            "required": ["vm_name"]
        }
    )
}

# Add tools and resources to the MCP Server object
for name, tool in tools.items():
    setattr(mcp_server, f"tool_{name}", tool)
for name, res in resources.items():
    setattr(mcp_server, f"resource_{name}", res)

# Set the MCP Server capabilities, declaring that the tools and resources list is available
mcp_server.capabilities = {
    "tools": {"listChanged": True},
    "resources": {"listChanged": True}
}

# Simple HTTP JSON-RPC handler for stateless MCP operations
async def handle_mcp_request(request_data: dict) -> dict:
    """Handle a single MCP JSON-RPC request and return response."""
    try:
        # Initialize server for this request
        init_opts = mcp_server.create_initialization_options()

        # Process the request through MCP server
        # For stateless operation, we'll handle the message directly
        method = request_data.get("method")
        params = request_data.get("params", {})
        request_id = request_data.get("id")

        if method == "initialize":
            # Handle initialization
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": mcp_server.capabilities,
                    "serverInfo": {
                        "name": "VMware-MCP-Server",
                        "version": "0.0.1"
                    }
                }
            }
        elif method == "tools/list":
            # Return list of available tools
            tool_list = []
            for tool_name in tools.keys():
                tool = tools[tool_name]
                tool_list.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                })
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tool_list}
            }
        elif method == "tools/call":
            # Execute a tool
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name in tools:
                tool = tools[tool_name]
                try:
                    result = tool.handler(tool_args)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
                except Exception as e:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{tool_name}' not found"
                    }
                }
        elif method == "resources/list":
            # Return list of available resources
            resource_list = []
            for res_name in resources.keys():
                res = resources[res_name]
                resource_list.append({
                    "uri": res.uri,
                    "name": res.name,
                    "description": res.description,
                    "mimeType": "application/json"
                })
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"resources": resource_list}
            }
        elif method == "resources/read":
            # Read a resource
            uri = params.get("uri")
            if uri and uri.startswith("vmstats://"):
                vm_name = uri.replace("vmstats://", "")
                try:
                    result = resource_vm_performance(vm_name)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(result)}]}
                    }
                except Exception as e:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Resource '{uri}' not found"
                    }
                }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }

        return response

    except Exception as e:
        logging.error(f"Error handling MCP request: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

# Simple ASGI application routing: dispatch requests to stateless MCP operations
async def app(scope, receive, send):
    if scope["type"] == "http":
        path = scope.get("path", "")
        method = scope.get("method", "").upper()

        if path == "/" and method == "GET":
            # Root endpoint - basic server info for health checks
            server_info = {
                "name": "ESXi MCP Server",
                "version": "0.0.1",
                "status": "running",
                "endpoints": {
                    "mcp": "/mcp"
                }
            }
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": json.dumps(server_info).encode()})

        elif path == "/mcp" and method == "POST":
            # MCP JSON-RPC endpoint - handle stateless MCP requests
            # Read the request body
            body = b""
            while True:
                message = await receive()
                body += message.get("body", b"")
                if not message.get("more_body", False):
                    break

            try:
                request_data = json.loads(body.decode())
                response_data = await handle_mcp_request(request_data)

                await send({"type": "http.response.start", "status": 200,
                           "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": json.dumps(response_data).encode()})

            except json.JSONDecodeError:
                await send({"type": "http.response.start", "status": 400,
                           "headers": [(b"content-type", b"application/json")]})
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None
                }
                await send({"type": "http.response.body", "body": json.dumps(error_response).encode()})

        elif path == "/mcp" and method == "OPTIONS":
            # CORS preflight request
            headers = [
                (b"access-control-allow-methods", b"POST, OPTIONS"),
                (b"access-control-allow-headers", b"Content-Type"),
                (b"access-control-allow-origin", b"*")
            ]
            await send({"type": "http.response.start", "status": 204, "headers": headers})
            await send({"type": "http.response.body", "body": b""})

        else:
            # Route not found
            await send({"type": "http.response.start", "status": 404,
                        "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"Not Found"})
    else:
        # Non-HTTP event, do not process
        return

# Parse command-line arguments and environment variables, and load configuration
parser = argparse.ArgumentParser(description="MCP VMware ESXi Management Server")
parser.add_argument("--config", "-c", help="Configuration file path (JSON or YAML)", default=None)
args = parser.parse_args()

# Attempt to load configuration from a file or environment variables
config_data = {}
config_path = args.config or os.environ.get("MCP_CONFIG_FILE")
if config_path:
    # Parse JSON or YAML based on the file extension
    if config_path.endswith((".yml", ".yaml")):
        import yaml
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        print(f"DEBUG: config_data after YAML load: {config_data}") # DEBUG LINE
    elif config_path.endswith(".json"):
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    else:
        raise ValueError("Unsupported configuration file format. Please use JSON or YAML")
# Override configuration from environment variables (higher priority than file)
env_map = {
    "VCENTER_HOST": "vcenter_host",
    "VCENTER_USER": "vcenter_user",
    "VCENTER_PASSWORD": "vcenter_password",
    "VCENTER_DATACENTER": "datacenter",
    "VCENTER_CLUSTER": "cluster",
    "VCENTER_DATASTORE": "datastore",
    "VCENTER_NETWORK": "network",
    "VCENTER_INSECURE": "insecure",
    "MCP_LOG_FILE": "log_file",
    "MCP_LOG_LEVEL": "log_level",
    "MCP_PORT": "port"
}
for env_key, cfg_key in env_map.items():
    if env_key in os.environ and os.environ[env_key] != "":
        val = os.environ[env_key]
        # Type conversion based on field type
        if cfg_key == "insecure":
            config_data[cfg_key] = val.lower() in ("1", "true", "yes")
        elif cfg_key == "port":
            config_data[cfg_key] = int(val)
        else:
            config_data[cfg_key] = val

# Construct Config object from config_data
required_keys = ["vcenter_host", "vcenter_user", "vcenter_password"]
# Temporarily comment out validation for testing
# for k in required_keys:
#     if k not in config_data or not config_data[k]:
#         raise Exception(f"Missing required configuration item: {k}")
config = Config(**config_data)

# Initialize logging
log_level = getattr(logging, config.log_level.upper(), logging.INFO)
logging.basicConfig(level=log_level,
                    format="%(asctime)s [%(levelname)s] %(message)s")
if not config.log_file:
    # If no log file is specified, output logs to the console
    logging.getLogger().addHandler(logging.StreamHandler())

logging.info("Starting VMware ESXi Management MCP Server...")
# Create VMware Manager instance and connect
manager = VMwareManager(config)

# Start ASGI server to listen for MCP SSE connections
if __name__ == "__main__":
    # Start ASGI application using the built-in uvicorn server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.port)
