# InfraAI AIOps Backend

Intelligent AIOps platform with autonomous remediation capabilities powered by FastAPI and LangGraph.

## Architecture

### Core Components

1. **LangGraph Core Engine** (`app/core/engine.py`)
   - Coordinator brain for all operations
   - Tool-based architecture with reasoning loop
   - Supports network discovery, policy management, and remediation actions

2. **Self-Healing Engine** (`app/core/self_healing.py`)
   - Evaluates Prometheus alerts against policies
   - Triggers remediation actions automatically
   - Priority-based policy matching

3. **Background Worker** (`app/worker.py`)
   - Processes async remediation tasks from Redis queue
   - Executes MCP protocol actions
   - Logs all job executions

4. **Tools & Adapters** (`app/tools/`)
   - Ollama LLM adapter for reasoning
   - Network scanner using nmap
   - **MCP Server Integrations**: VMware ESXi (16 tools), Kubernetes (11 tools), Prometheus (6 tools), Grafana (3 tools)
   - Policy management tools

### API Endpoints

#### Chat
- `POST /api/chat` - Chat with InfraAI agent
- `GET /api/chat/history/{session_id}` - Get chat history
- `WS /api/ws/chat/{session_id}` - WebSocket chat

#### Monitoring
- `POST /api/alerts` - Prometheus webhook endpoint

#### Discovery
- `POST /api/discover` - Trigger network scan
- `GET /api/topology` - Get discovered assets

#### Policies
- `POST /api/policies` - Create policy
- `GET /api/policies` - List all policies
- `GET /api/policies/{id}` - Get specific policy
- `DELETE /api/policies/{id}` - Delete policy

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Ollama (with a model installed, e.g., llama2)
- nmap (for network scanning)

### Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Setup PostgreSQL**
   ```bash
   # Create database
   createdb infraal
   
   # Create user
   psql -c "CREATE USER infraal WITH PASSWORD 'infraal';"
   psql -c "GRANT ALL PRIVILEGES ON DATABASE infraal TO infraal;"
   ```

4. **Start Redis**
   ```bash
   redis-server
   ```

5. **Start Ollama**
   ```bash
   ollama serve
   ollama pull llama2
   ```

### Running the Application

1. **Start the FastAPI Server**
   ```bash
   python -m app.main
   # or
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

2. **Start the Background Worker**
   ```bash
   python -m app.worker
   ```

### Testing

**Health Check**
```bash
curl http://localhost:8001/health
```

**Chat with Agent**
```bash
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-key-12345" \
  -d '{"session_id": "test", "prompt": "Scan the network"}'
```

**Create a Policy**
```bash
curl -X POST http://localhost:8001/api/policies \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-key-12345" \
  -d '{
    "name": "Restart Pod on Crash",
    "condition": {"labels": {"alertname": "PodCrashLoop"}},
    "action": {
      "tool": "mcp_restart_pod",
      "params": {
        "pod_name": "${label.pod_name}",
        "namespace": "${label.namespace}"
      }
    },
    "priority": 10
  }'
```

**Simulate Prometheus Alert**
```bash
curl -X POST http://localhost:8001/api/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-key-12345" \
  -d '{
    "status": "firing",
    "alerts": [{
      "labels": {
        "alertname": "PodCrashLoop",
        "pod_name": "app-pod-123",
        "namespace": "production"
      },
      "annotations": {
        "summary": "Pod is crash looping"
      }
    }]
  }'
```

## Database Schema

### Tables

- **policies** - Self-healing policies
- **system_assets** - Discovered infrastructure assets
- **chat_history** - Agent conversation history
- **job_logs** - Remediation job execution logs

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|--------|
| `POSTGRES_DSN` | PostgreSQL connection string | `postgresql+asyncpg://infraal:infraal@localhost/infraal` |
| `REDIS_HOST` | Redis server host | `localhost` |
| `REDIS_PORT` | Redis server port | `6379` |
| `OLLAMA_API_URL` | Ollama API endpoint | `http://192.168.200.201:11434` |
| `OLLAMA_MODEL` | Ollama model name | `llama2` |
| `INFRAAL_API_KEY` | API authentication key | `dev-key-12345` |
| `PORT` | FastAPI server port | `8001` |

## Development

### Project Structure

```
/app
├── __init__.py
├── main.py              # FastAPI application
├── api.py               # API routes
├── models.py            # Data models
├── db.py                # Database operations
├── worker.py            # Background worker
├── /core
│   ├── engine.py        # LangGraph agent
│   └── self_healing.py  # Policy evaluator
└── /tools
    ├── ollama_adapter.py
    ├── network_scanner.py
    ├── policy_tools.py
    └── mcp_client.py     # MCP server integrations
```

### MCP Server Integrations

The backend includes comprehensive MCP (Model Context Protocol) server integrations for infrastructure management:

#### VMware ESXi Integration (16 tools)
- VM lifecycle: `create_vm`, `delete_vm`, `clone_vm`
- Power management: `power_on_vm`, `power_off_vm`, `suspend_vm`, `reset_vm`, `shutdown_vm`, `reboot_vm`
- Information: `get_vm_info`, `get_host_info`, `list_vms`
- Storage: `list_datastores`
- Networking: `list_networks`
- Snapshots: `get_vm_snapshots`, `create_snapshot`, `delete_snapshot`

#### Kubernetes Integration (11 tools)
- Resource management: `kubectl_get`, `kubectl_describe`, `kubectl_delete`
- Operations: `kubectl_apply`, `kubectl_scale`, `kubectl_rollout_status`
- Debugging: `kubectl_logs`, `kubectl_exec`
- Networking: `kubectl_port_forward`
- Node management: `kubectl_taint`
- Cleanup: `cleanup`

#### Prometheus Integration (6 tools)
- Queries: `execute_query`, `execute_range_query`
- Discovery: `list_metrics`, `get_metric_metadata`
- Monitoring: `get_targets`, `health_check`

#### Grafana Integration (3 tools)
- Dashboards: `list_dashboards`, `get_dashboard`
- Datasources: `list_datasources`

### Adding New MCP Actions

1. Add the function to `app/tools/mcp_client.py`
2. Register it in `app/core/engine.py` tool list
3. Add it to `TOOL_MAP` in `app/worker.py`

### Policy Format

Policies define when and how to perform remediation:

```json
{
  "name": "Policy Name",
  "condition": {
    "labels": {"alertname": "AlertName"},
    "status": "firing"
  },
  "action": {
    "tool": "mcp_restart_pod",
    "params": {
      "pod_name": "${label.pod_name}",
      "namespace": "${label.namespace}"
    }
  },
  "priority": 10
}
```

## Production Deployment

### Recommendations

1. **Use a production ASGI server** (e.g., Gunicorn with Uvicorn workers)
2. **Configure proper CORS** in `main.py`
3. **Use environment-specific .env files**
4. **Set up monitoring** for the worker process
5. **Implement proper logging** (structured logs)
6. **Add authentication middleware** beyond simple API key
7. **Use connection pooling** for PostgreSQL
8. **Implement rate limiting**
9. **Configure MCP server endpoints** for production infrastructure
10. **Add comprehensive error handling**

## License

MIT
