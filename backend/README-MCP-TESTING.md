# InfraAI MCP Connectivity Testing

## Overview

The `test_mcp_connectivity.py` script provides comprehensive testing for all MCP (Multi-Cloud Protocol) clients and servers used in InfraAI. This is essential for validating infrastructure management integrations.

## What it Tests

###  Configuration Files
- **ESXi MCP Tools Config**: `esxi_mcp_tools_config.json`
- **Kubernetes MCP Tools Config**: `kubernetes_mcp_tools_config.json`
- **Kubernetes Essentials Config**: `mcp_kubernetes_essentials.json`

###  ESXi MCP Server (VMware)
- **Server Connectivity**: HTTP connection to `192.168.203.103:8083`
- **MCP Endpoint**: JSON-RPC initialization request
- **Client Functions**: VM listing via `mcp_list_vms()`

### ️ Kubernetes MCP Server
- **API Server Access**: Connectivity to `https://192.168.203.103:6443`
- **Version Endpoint**: Public Kubernetes version API
- **Authentication**: RBAC-based API access testing
- **Client Functions**: Pod retrieval via `mcp_get_pods()`

### ️ General MCP Tools
- **Prometheus Queries**: Basic `up` metric queries
- **Network Discovery**: Safe local subnet scanning
- **Pod/Container Restart**: Function accessibility testing

## Usage

### Standalone Testing
```bash
# From backend directory
cd backend
python test_mcp_connectivity.py

# Or execute directly
./test_mcp_connectivity.py
```

### Integration with Full Test Suite
The MCP connectivity tests are automatically included in:
```bash
./test-complete-integration.sh
```

## Sample Output

```
 InfraAI MCP Connectivity Test Suite
======================================================================

 Checking MCP Configurations
 PASS ESXi MCP Tools Config
   ↳ 17 tools configured
 FAIL Kubernetes MCP Tools Config
   ↳ Configuration file not found

 Testing ESXi MCP Server (VMware)
 FAIL ESXi Server HTTP Connectivity
   ↳ Connection timeout - server not running

️  Testing Kubernetes MCP Server
 FAIL Kubernetes Version API
   ↳ Error: Connection refused

️  Testing General MCP Tools
 PASS Prometheus MCP Query (up)
   ↳ Query executed successfully

======================================================================
TEST RESULTS SUMMARY
======================================================================
Total Tests: 10
Passed: 4
Failed: 6

 SOME MCP CONNECTIONS FAILED
```

## Troubleshooting Guide

The script provides detailed troubleshooting steps for common issues:

### ESXi MCP Server Issues
1. Install: `npm install -g @bright8192/esxi-mcp-server`
2. Start server: `ENABLE_UNSAFE_STREAMABLE_HTTP_TRANSPORT=true HOST=0.0.0.0 PORT=8083 node dist/index.js`
3. Check firewall and networking
4. Update backend `.env` with correct server URL

### Kubernetes MCP Server Issues
1. Verify kubectl: `kubectl cluster-info`
2. Get token: `kubectl config view --minify`
3. Update `.env` with API server and authentication
4. Check RBAC permissions

### General Issues
1. Network connectivity to MCP servers
2. Firewall settings (ports 8083, 6443, 9090)
3. SSL/TLS certificate validation
4. MCP client logs and error messages

## Configuration

### Environment Variables
```bash
# ESXi MCP (for VMware)
ESXI_SERVER_URL=http://192.168.203.103:8083

# Kubernetes MCP
KUBERNETES_API_SERVER=https://192.168.203.103:6443
KUBERNETES_TOKEN=<your-service-account-token>

# Prometheus
PROMETHEUS_URL=http://192.168.203.103:9090
```

### MCP Server URLs
- **ESXi**: `http://192.168.203.103:8083/mcp`
- **Kubernetes API**: `https://192.168.203.103:6443/api`
- **Prometheus**: `http://192.168.203.103:9090`

## Integration Points

### Test Integration
The test script is integrated into the main testing pipeline:

1. **Individual MCP Testing**: `test_mcp_connectivity.py`
2. **Complete Integration**: `test-complete-integration.sh` (includes MCP tests)
3. **CI/CD Pipeline**: Can be added to automated testing workflows

### Alert System Integration
MCP connectivity issues trigger appropriate alerts:
- Failed server connections
- Authentication problems
- Configuration errors
- Network connectivity issues

## Dependencies

The test script uses these InfraAI components:
- `app.tools.mcp_esxi_client` - ESXi VMware MCP client
- `app.tools.mcp_kubernetes_client` - Kubernetes MCP client
- `app.tools.mcp_client` - General MCP operations
- `app.tools.network_scanner` - Network discovery tools

## Exit Codes

- **0**: All tests passed (successful MCP connectivity)
- **Non-zero**: Some tests failed (connectivity issues detected)

## Best Practices

1. **Pre-deployment Testing**: Always run before deploying to production
2. **Configuration Validation**: Test with actual server configurations
3. **Network Isolation**: Test in environments that mirror production
4. **Regular Monitoring**: Include in health check routines
5. **Documentation Updates**: Keep troubleshooting guide current
