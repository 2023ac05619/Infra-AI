# Artificial Intelligence with IT Infrastructure tools and services

A full-stack AIOps platform combining intelligent infrastructure management with a modern chat interface.

##  Quick Start

### One-Command Setup
```bash
# Make sure Docker is running, then:
./init-complete-app.sh
```

This will:
-  Start PostgreSQL, Redis, and Ollama
-  Initialize backend database with sample policies
-  Set up frontend with default admin user
-  Start both backend and frontend servers

##  Access Points

### Frontend (InfraChat)
- **URL**: http://localhost:3001 or http://0.0.0.0:3000
- **First-Time Setup**: Create your admin account on first visit
- **Features**: Modern chat UI, dynamic panes, user management

### Backend (InfraAI API)
- **URL**: http://localhost:8001 or http://0.0.0.0:8000
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## ️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   InfraChat     │    │    InfraAI      │
│   Frontend      │◄──►│   Backend       │
│                 │    │                 │
│ • Next.js       │    │ • FastAPI       │
│ • TypeScript    │    │ • LangGraph     │
│ • SQLite        │    │ • PostgreSQL    │
│ • NextAuth      │    │ • Redis Queue   │
│ • Socket.IO     │    │ • Ollama LLM    │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────────────────┘
         ┌───────────────────────┐
         │   MCP Integrations    │
         │                       │
         │ • VMware ESXi Server  │
         │ • Kubernetes Server   │
         │ • Prometheus Server   │
         │ • Grafana Server      │
         └───────────────────────┘
        
```

##  Features

### Frontend (InfraChat)
- **ChatGPT-like Interface** with persistent sessions
- **Dynamic Sliding Panes** for infrastructure data
- **User Authentication** with auto-registration
- **Real-time Communication** via Socket.IO
- **Modern UI** with dark/light themes

### Backend (InfraAI)
- **Intelligent AIOps** with LangGraph reasoning
- **Self-Healing Policies** for automated remediation
- **Network Discovery** with nmap scanning
- **Multi-Cloud Support** via MCP protocol implementations
- **REST & WebSocket APIs**

### MCP (Model Context Protocol) Integrations

#### VMware ESXi Integration
- **16 VM Management Tools**: Power operations, lifecycle management, snapshots, host info
- **Transport**: Stateless HTTP JSON-RPC
- **Endpoint**: `http://192.168.203.103:8090/mcp`
- **Capabilities**: VM creation, deletion, cloning, snapshots, datastore/network management

#### Kubernetes Integration
- **11 Kubernetes Tools**: Resource management, scaling, logging, exec, port-forwarding
- **Transport**: Streamable HTTP JSON-RPC
- **Endpoint**: `http://192.168.203.103:8080/mcp`
- **Capabilities**: kubectl operations, deployment scaling, pod management, taints

#### Prometheus Integration
- **6 Monitoring Tools**: Instant/range queries, metrics discovery, health checks
- **Transport**: Stateless HTTP JSON-RPC
- **Endpoint**: `http://192.168.203.103:8080/jsonrpc`
- **Capabilities**: PromQL queries, target monitoring, metric metadata

#### Grafana Integration
- **3 Dashboard Tools**: Dashboard and datasource management
- **Transport**: Stateless HTTP JSON-RPC
- **Endpoint**: `http://192.168.203.103:8000/mcp`
- **Capabilities**: Dashboard retrieval, datasource listing

##  Sample Data

### Backend Policies (Auto-loaded)
1. **Restart Crashed Pod** - Auto-restart crash-looping pods
2. **Scale Up on High CPU** - Scale deployments on CPU alerts
3. **Restart VM on Service Failure** - Restart VMs for critical services
4. **Query Metrics on Alert** - Query Prometheus for context

### User Registration
- **First-Time Setup**: Visit http://localhost:3001 to create your admin account
- **Registration**: Enter any username and password to register as the first user
- **Subsequent Logins**: Use your registered credentials to sign in

## ️ Manual Setup (Alternative)

If you prefer to set up components individually:

### Backend Setup
```bash
cd backend
docker-compose up -d  # Start services
python scripts/init_db.py  # Initialize DB
python scripts/load_sample_policies.py  # Load policies
python -m app.main  # Start server
```

### Frontend Setup
```bash
cd frontend
npm install
npm run db:push  # Initialize DB
node setup-admin.js  # Create admin user
npm run dev  # Start server
```

##  Configuration

### Environment Variables

#### Backend (.env)
```env
POSTGRES_DSN=postgresql+asyncpg://infraal:infraal@localhost/infraal
REDIS_HOST=localhost
REDIS_PORT=6379
OLLAMA_API_URL=http://192.168.200.201:11434
OLLAMA_MODEL=llama3.1:latest
INFRAAL_API_KEY=dev-key-12345
PORT=8001
```

#### Frontend (.env)
```env
DATABASE_URL="file:./db/custom.db"
NEXTAUTH_URL="http://localhost:3001"
NEXTAUTH_SECRET="infraai-secret-key-2025"
BACKEND_URL="http://localhost:8001"
BACKEND_API_KEY="dev-key-12345"
```

##  Testing

### Quick Test Runner
```bash
# Run all tests (recommended)
./run-all-tests.sh

# Individual test suites
./test-ollama-models.sh         # Ollama AI models testing
./test-complete-integration.sh  # Full stack integration tests
./backend/scripts/test_api.sh   # Backend API tests
./frontend/test-frontend.sh     # Frontend tests
```

### Ollama Models Testing
```bash
# Test all available Ollama models
./test-ollama-models.sh
```

This will:
-  Check Ollama connectivity
-  List all available models with sizes
-  Test inference with each model
-  Validate responses and performance
-  Provide model recommendations


### Manual API Health Checks
```bash
# Backend
curl http://localhost:8001/health

# Frontend
curl http://localhost:3001/api/health
```

### Manual Chat API Test
```bash
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-key-12345" \
  -d '{"session_id": "test", "prompt": "Hello InfraAI"}'
```

### Test Coverage

#### Complete Integration Tests (`test-complete-integration.sh`)
-  Docker services (PostgreSQL, Redis, Ollama)
-  Database connectivity and schemas
-  Backend API endpoints and authentication
-  Frontend accessibility and APIs
-  Frontend-backend integration
-  Performance validation

#### Backend API Tests (`backend/scripts/test_api.sh`)
-  Health checks and basic endpoints
-  Authentication and security
-  Chat functionality with AI
-  Policy CRUD operations


### Database Issues
```bash
# Reset backend DB
cd backend && python scripts/init_db.py

# Reset frontend DB
cd frontend && rm db/custom.db && npm run db:push
```

### Reset Admin Credentials
```bash
# Reset admin user and all user data (WARNING: destructive)
./reset-admin_account_password.sh
```
This will:
- Delete all existing users
- Reset the database
- Create a fresh admin user (admin@infraai.com / admin123)


### Permission Issues
```bash
# Make scripts executable
chmod +x init-complete-app.sh
chmod +x backend/setup.sh
chmod +x reset-admin_account_password.sh
```

##  API Documentation

- **Backend APIs**: http://localhost:8001/docs (FastAPI auto-generated)
- **Frontend APIs**: Next.js API routes in `frontend/src/app/api/`

##  Security Notes

- **Default credentials** are for development only
- **Change passwords** in production
- **Use strong NEXTAUTH_SECRET** for production
- **Configure CORS** appropriately for production

##  Success!

Your InfraAI application is now running with:
-  Modern chat interface
-  Intelligent AIOps backend
-  Sample policies and data
-  User registration system (first user becomes admin)
-  Full integration between frontend and backend

### First-Time Setup
1. **Visit** http://localhost:3001
2. **Create Account**: Enter any username and password to register as admin
3. **Start Chatting**: Use the AI infrastructure assistant

Enjoy exploring AI-powered infrastructure assistant!
