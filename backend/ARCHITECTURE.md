# InfraAI Architecture

## System Overview

InfraAI is an intelligent AIOps platform that combines conversational AI with autonomous infrastructure remediation. The system is built on three core pillars:

1. **LangGraph Core Engine** - The reasoning coordinator
2. **Self-Healing Engine** - Policy-driven remediation
3. **Domain Adapters (MCP)** - Multi-cloud protocol clients

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Web Server                        │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Chat API   │  │ Policy CRUD  │  │ Prometheus Webhook    │  │
│  │ (REST/WS)  │  │              │  │ (Alert Receiver)      │  │
│  └─────┬──────┘  └──────┬───────┘  └──────────┬─────────────┘  │
└────────┼─────────────────┼──────────────────────┼────────────────┘
         │                 │                      │
         ▼                 ▼                      ▼
┌────────────────┐  ┌─────────────┐    ┌──────────────────────┐
│   LangGraph    │  │  PostgreSQL │    │  Self-Healing        │
│  Core Engine   │◄─┤  (Policies, │    │  Policy Evaluator    │
│                │  │   Assets,   │    │                      │
│  ┌──────────┐  │  │   History)  │    └──────────┬───────────┘
│  │  Agent   │  │  └─────────────┘               │
│  │  (LLM)   │  │                                 ▼
│  └────┬─────┘  │                        ┌────────────────┐
│       │        │                        │  Redis Queue   │
│       ▼        │                        │  (async tasks) │
│  ┌──────────┐  │                        └────────┬───────┘
│  │  Tools   │  │                                 │
│  └────┬─────┘  │                                 ▼
└───────┼────────┘                        ┌────────────────┐
        │                                 │  Worker Pool   │
        │                                 │  (Remediation) │
        │                                 └────────┬───────┘
        │                                          │
        └──────────────────┬───────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │        Domain Adapters (MCP)        │
        ├─────────────┬──────────┬────────────┤
        │   VMware    │   K8s    │ Prometheus │
        │   Client    │  Client  │   Client   │
        └─────────────┴──────────┴────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │      Infrastructure Platforms       │
        │  (VMs, Pods, Clusters, Services)    │
        └─────────────────────────────────────┘
```

## Data Flow

### 1. Conversational Mode (Chat)

```
User → POST /api/chat
  ↓
LangGraph Core Engine
  ↓
Agent Node (Reasoning)
  ↓
Tool Selection
  ↓
[mcp_esxi | mcp_kubernetes | mcp_monitoring | network_discovery | get_policies | llm_reasoning | ...]
  ↓
Tool Execution
  ↓
Agent Node (Process Results)
  ↓
AI Response → User
```

### 2. Self-Healing Mode (Alert)

```
Prometheus → POST /api/alerts
  ↓
Self-Healing Engine
  ↓
Policy Evaluator (match condition)
  ↓
Action Identified
  ↓
Redis Queue (enqueue task)
  ↓
Background Worker (dequeue)
  ↓
MCP Tool Execution
  ↓
[restart_pod | restart_vm | scale_deployment | ...]
  ↓
Log to Database
```

## LangGraph State Machine

```
┌──────────────┐
│  User Input  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Agent Node  │ ◄──────────┐
│  (Reasoning) │            │
└──────┬───────┘            │
       │                    │
       ├─ Should call tool? │
       │                    │
       ├─ Yes ──►┌──────────┴────────┐
       │         │  Tool Executor    │
       │         │  (Execute Action) │
       │         └───────────────────┘
       │
       └─ No ───►┌──────────────┐
                 │  END (Reply) │
                 └──────────────┘
```

## Database Schema

### policies
```sql
CREATE TABLE policies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    condition JSONB NOT NULL,
    action JSONB NOT NULL,
    priority INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### system_assets
```sql
CREATE TABLE system_assets (
    id SERIAL PRIMARY KEY,
    ip VARCHAR(45) UNIQUE NOT NULL,
    hostname VARCHAR(255),
    type VARCHAR(50) NOT NULL,
    services JSONB DEFAULT '[]',
    last_seen TIMESTAMP DEFAULT NOW()
);
```

### chat_history
```sql
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### job_logs
```sql
CREATE TABLE job_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    target VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    result TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Policy System

### Policy Structure

```json
{
  "name": "Policy Name",
  "condition": {
    "labels": {"alertname": "PodCrashLoop"},
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

### Condition Matching

The policy evaluator supports multiple condition formats:

1. **Label Matching**: Match specific alert labels
   ```json
   {"labels": {"alertname": "HighCPU", "severity": "critical"}}
   ```

2. **Simple Key-Value**: Match a single label
   ```json
   {"label": "alertname", "value": "PodCrashLoop"}
   ```

3. **Status Matching**: Match alert status
   ```json
   {"status": "firing"}
   ```

### Parameter Interpolation

Actions can use placeholders to extract values from alerts:

- `${label.pod_name}` - Extracts from alert labels
- `${annotation.summary}` - Extracts from alert annotations

## Tool System

### Available Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `llm_reasoning` | General reasoning and response generation | `prompt: str` |
| `network_discovery` | Scan network for assets | `subnet: str` |
| `get_policies` | Retrieve all policies | None |
| `restart_vm` | Restart a virtual machine | `vm_name: str` |
| `restart_pod` | Restart a Kubernetes pod | `pod_name: str`, `namespace: str` |
| `query_prometheus` | Query Prometheus metrics | `query: str` |
| `get_grafana_dashboard` | Get dashboard information | `dashboard_id: str` |
| `scale_deployment` | Scale K8s deployment | `deployment_name: str`, `replicas: int`, `namespace: str` |

### Adding New Tools

1. **Create the function** in `app/tools/`
2. **Wrap with @tool** decorator in `app/core/engine.py`
3. **Register in tools list** in `app/core/engine.py`
4. **Add to TOOL_MAP** in `app/worker.py` (if used by self-healing)

## Security Considerations

### Current Implementation

- Simple API key authentication (`X-API-KEY` header)
- CORS enabled for all origins (development mode)
- MCP tools are stubs (no real infrastructure access)

### Production Recommendations

1. **Authentication**: Implement OAuth2 or JWT-based auth
2. **Authorization**: Role-based access control (RBAC)
3. **Rate Limiting**: Prevent abuse of API endpoints
4. **Input Validation**: Strict validation on all inputs
5. **Encryption**: TLS/SSL for all communications
6. **Audit Logging**: Log all policy changes and actions
7. **Network Segmentation**: Isolate worker processes
8. **Secret Management**: Use vault for credentials

## Deployment Architecture

### Recommended Production Setup

```
┌─────────────────────────────────────────────┐
│         Load Balancer (NGINX/HAProxy)       │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐    ┌───────▼────────┐
│  FastAPI Pod 1 │    │  FastAPI Pod 2 │
│  (API Server)  │    │  (API Server)  │
└────────┬───────┘    └────────┬───────┘
         │                     │
         └──────────┬──────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐    ┌────────▼────────┐
│   PostgreSQL   │    │   Redis Cluster │
│   (Primary +   │    │   (Sentinel)    │
│    Replica)    │    │                 │
└────────────────┘    └─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ┌───────▼────────┐  ┌───────▼────────┐
            │  Worker Pod 1  │  │  Worker Pod 2  │
            │  (Remediation) │  │  (Remediation) │
            └────────────────┘  └────────────────┘
```

## Scaling Considerations

### Horizontal Scaling

- **API Servers**: Stateless, can scale to N replicas
- **Workers**: Scale based on queue depth
- **Database**: Use read replicas for queries
- **Redis**: Use Redis Cluster for high availability

### Performance Optimization

1. **Database Connection Pooling**: Configure appropriate pool sizes
2. **Caching**: Cache policies and static data
3. **Async I/O**: All I/O operations are async
4. **Batch Processing**: Process multiple alerts in parallel
5. **Tool Parallelization**: Execute independent tools concurrently

## Monitoring & Observability

### Metrics to Track

- API request rate and latency
- Worker task processing time
- Policy evaluation success rate
- Tool execution success/failure rate
- Database query performance
- Redis queue depth

### Recommended Tools

- **Metrics**: Prometheus + Grafana
- **Logging**: ELK Stack or Loki
- **Tracing**: Jaeger or Tempo
- **Alerting**: Prometheus Alertmanager

## Future Enhancements

1. **Advanced LLM Integration**: Use OpenAI/Anthropic for better reasoning
2. **Real MCP Implementations**: Connect to actual infrastructure
3. **Multi-tenancy**: Support multiple organizations
4. **Policy Templates**: Pre-built policy library
5. **Machine Learning**: Learn from past remediations
6. **Simulation Mode**: Test policies before deployment
7. **Approval Workflows**: Human-in-the-loop for critical actions
8. **Cost Optimization**: Track and optimize cloud costs
9. **Incident Management**: Integration with PagerDuty, Opsgenie
10. **Custom Tool Framework**: Allow users to add custom tools
