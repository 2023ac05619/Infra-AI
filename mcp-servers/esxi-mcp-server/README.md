# ESXi MCP Server

A VMware ESXi/vCenter management server based on MCP (Model Control Protocol), providing simple stateless HTTP JSON-RPC API interfaces for virtual machine management.

## Features

- Support for ESXi and vCenter Server connections
- Stateless HTTP JSON-RPC API for complete request/response cycles
- Complete virtual machine lifecycle management
- Real-time performance monitoring
- SSL/TLS secure connection support
- Flexible configuration options (YAML/JSON/Environment Variables)

## Core Functions

- Virtual Machine Management
  - Create VM
  - Clone VM
  - Delete VM
  - Power On/Off operations
  - List all VMs
- Performance Monitoring
  - CPU usage
  - Memory usage
  - Storage usage
  - Network traffic statistics

## Requirements

- Python 3.7+
- pyVmomi
- PyYAML
- uvicorn
- mcp-core (Machine Control Protocol core library)

## Quick Start

1. Install dependencies:

```bash
pip install pyvmomi pyyaml uvicorn mcp-core
```

2. Create configuration file `config.yaml`:

```yaml
vcenter_host: "your-vcenter-ip"
vcenter_user: "administrator@vsphere.local"
vcenter_password: "your-password"
datacenter: "your-datacenter"        # Optional
cluster: "your-cluster"              # Optional
datastore: "your-datastore"          # Optional
network: "VM Network"                # Optional
insecure: true                       # Skip SSL certificate verification
log_file: "./logs/vmware_mcp.log"   # Log file path
log_level: "INFO"                    # Log level
```

3. Run the server:

```bash
python server.py -c config.yaml
```

## API Interface

### Main Tool Interfaces

1. Create VM
```json
{
    "name": "vm-name",
    "cpu": 2,
    "memory": 4096,
    "datastore": "datastore-name",
    "network": "network-name"
}
```

2. Clone VM
```json
{
    "template_name": "source-vm",
    "new_name": "new-vm-name"
}
```

3. Delete VM
```json
{
    "name": "vm-name"
}
```

4. Power Operations
```json
{
    "name": "vm-name"
}
```

### HTTP JSON-RPC API

The server provides a stateless HTTP JSON-RPC API endpoint at `/mcp`. Send JSON-RPC requests to interact with VM management tools and resources.

#### Example JSON-RPC Request Format:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "listVMs"
  }
}
```

#### Available MCP Methods:
- `initialize` - Initialize the MCP session
- `tools/list` - List available tools
- `tools/call` - Execute a tool (createVM, deleteVM, powerOn, etc.)
- `resources/list` - List available resources
- `resources/read` - Read resource data (vmstats://{vm_name})

### Resource Access

VM performance data is accessible via the `resources/read` method with URI `vmstats://{vm_name}`.

## Configuration

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| vcenter_host | vCenter/ESXi server address | Yes | - |
| vcenter_user | Login username | Yes | - |
| vcenter_password | Login password | Yes | - |
| datacenter | Datacenter name | No | Auto-select first |
| cluster | Cluster name | No | Auto-select first |
| datastore | Storage name | No | Auto-select largest available |
| network | Network name | No | VM Network |
| insecure | Skip SSL verification | No | false |
| log_file | Log file path | No | Console output |
| log_level | Log level | No | INFO |

## Environment Variables

All configuration items support environment variable settings, following these naming rules:
- VCENTER_HOST
- VCENTER_USER
- VCENTER_PASSWORD
- VCENTER_DATACENTER
- VCENTER_CLUSTER
- VCENTER_DATASTORE
- VCENTER_NETWORK
- VCENTER_INSECURE
- MCP_LOG_FILE
- MCP_LOG_LEVEL

## Security Recommendations

1. Production Environment:
   - Use valid SSL certificates
   - Set appropriate log levels
   - Restrict API access scope

2. Testing Environment:
   - Set insecure: true to skip SSL verification
   - Use more detailed log level (DEBUG)

## License

MIT License

## Contributing

Issues and Pull Requests are welcome!

## Changelog

### v0.0.1
- Initial release
- Basic VM management functionality
- Stateless HTTP JSON-RPC API implementation
- Performance monitoring

## Author

Bright8192

## Acknowledgments

- VMware pyvmomi team
- MCP Protocol development team
