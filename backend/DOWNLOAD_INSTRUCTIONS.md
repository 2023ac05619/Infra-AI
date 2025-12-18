# InfraAI Backend - Download & Setup Instructions

## Option 1: GitHub Integration (RECOMMENDED)

This is the fastest and most reliable method:

1. **In Emergent UI:**
   - Click the "Save to GitHub" button (usually in top right)
   - If prompted, connect your GitHub account
   - Create a new repository named "infraai-backend"
   - Click "Push to GitHub"

2. **On Your Local Machine:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/infraai-backend.git
   cd infraai-backend
   ```

3. **Setup & Run:**
   ```bash
   ./setup.sh
   # Or follow manual setup below
   ```

---

## Option 2: Manual File Transfer

If you need to manually recreate the project:

### Step 1: Create Project Directory
```bash
mkdir -p infraai-backend
cd infraai-backend
mkdir -p app/core app/tools scripts
```

### Step 2: Copy Files from Emergent

In Emergent, use the VS Code view to access and copy these files:

**Root Files:**
- `/app/backend/requirements.txt`
- `/app/backend/README.md`
- `/app/backend/ARCHITECTURE.md`
- `/app/backend/DEPLOYMENT.md`
- `/app/backend/PROJECT_SUMMARY.md`
- `/app/backend/Dockerfile`
- `/app/backend/docker-compose.yml`
- `/app/backend/Makefile`
- `/app/backend/setup.sh`
- `/app/backend/.env.example`
- `/app/backend/.gitignore`

**App Directory (`app/`):**
- `__init__.py`
- `main.py`
- `api.py`
- `models.py`
- `db.py`
- `worker.py`

**App Core (`app/core/`):**
- `__init__.py`
- `engine.py`
- `self_healing.py`

**App Tools (`app/tools/`):**
- `__init__.py`
- `ollama_adapter.py`
- `network_scanner.py`
- `policy_tools.py`
- `mcp_client.py`

**Scripts (`scripts/`):**
- `test_api.sh`
- `init_db.py`
- `load_sample_policies.py`
- `test_self_healing.py`
- `sample_policies.json`

### Step 3: Local Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Start infrastructure (Docker)
docker-compose up -d

# Wait for services to start
sleep 10

# Pull Ollama model
docker exec infraai-ollama ollama pull llama2

# Initialize database
python scripts/init_db.py

# Load sample policies
python scripts/load_sample_policies.py
```

### Step 4: Run Application

**Terminal 1 - API Server:**
```bash
python -m app.main
```

**Terminal 2 - Worker:**
```bash
python -m app.worker
```

**Access:**
- API: http://localhost:8001
- Docs: http://localhost:8001/docs
- Health: http://localhost:8001/health

---

## Option 3: Archive Download (If Available)

If Emergent provides a download option:

1. Look for "Download Project" or "Export" button
2. Download the ZIP file
3. Extract and follow setup instructions above

---

## Quick Test

```bash
# Test health endpoint
curl http://localhost:8001/health

# Test chat API (requires API key from .env)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-key-12345" \
  -d '{"session_id": "test", "prompt": "Hello"}'
```

---

## Prerequisites

**Required:**
- Python 3.10+
- Docker & Docker Compose
- PostgreSQL (via Docker or manual)
- Redis (via Docker or manual)
- Ollama (via Docker or manual)

**Optional:**
- nmap (for network scanning)
- Git (for version control)

---

## Deployment Options

### Development
```bash
python -m app.main  # API
python -m app.worker  # Worker
```

### Production (Docker)
```bash
docker-compose up -d
```

### Production (Kubernetes)
See `DEPLOYMENT.md` for complete K8s manifests

---

## Troubleshooting

### Services Won't Start
```bash
# Check if ports are available
lsof -i :8001  # API
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :11434 # Ollama

# Check Docker services
docker-compose ps
docker-compose logs
```

### Database Issues
```bash
# Reinitialize database
docker-compose down -v
docker-compose up -d
python scripts/init_db.py
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## Support

For issues:
1. Check logs in `/var/log/supervisor/` (if using supervisor)
2. Review `ARCHITECTURE.md` for system design
3. Check `DEPLOYMENT.md` for deployment details
4. Verify environment variables in `.env`

---

## Project Structure

```
infraai-backend/
├── app/
│   ├── core/          # LangGraph engine
│   ├── tools/         # Tool adapters
│   ├── main.py        # FastAPI app
│   ├── api.py         # API routes
│   ├── models.py      # Data models
│   ├── db.py          # Database ops
│   └── worker.py      # Background worker
├── scripts/           # Utilities
├── docker-compose.yml # Docker setup
├── Dockerfile         # Container image
├── requirements.txt   # Dependencies
└── README.md          # Documentation
```

---

**Ready to Deploy!** 

Choose your preferred method above and get started with InfraAI.
