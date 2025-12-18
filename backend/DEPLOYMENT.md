# InfraAI Deployment Guide

## Quick Start (Development)

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git

### Setup

```bash
# Clone repository
cd /app/backend

# Run setup script
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Start the API server
python -m app.main

# In another terminal, start the worker
python -m app.worker
```

The API will be available at `http://localhost:8001`

## Manual Setup

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3.10 python3-pip python3-venv nmap
```

**macOS:**
```bash
brew install python@3.10 nmap
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup PostgreSQL

**Using Docker:**
```bash
docker run -d \
  --name infraai-postgres \
  -e POSTGRES_USER=infraal \
  -e POSTGRES_PASSWORD=infraal \
  -e POSTGRES_DB=infraal \
  -p 5432:5432 \
  postgres:16-alpine
```

**Manual Installation:**
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE infraal;
CREATE USER infraal WITH PASSWORD 'infraal';
GRANT ALL PRIVILEGES ON DATABASE infraal TO infraal;
EOF
```

### 4. Setup Redis

**Using Docker:**
```bash
docker run -d \
  --name infraai-redis \
  -p 6379:6379 \
  redis:7-alpine
```

**Manual Installation:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

### 5. Setup Ollama

**Using Docker:**
```bash
docker run -d \
  --name infraai-ollama \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  ollama/ollama:latest

# Pull model
docker exec infraai-ollama ollama pull llama2
```

**Manual Installation:**
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve &

# Pull model
ollama pull llama2
```

### 6. Configure Environment

```bash
cp .env.example .env

# Edit .env with your settings
vim .env
```

### 7. Run Application

**Start API Server:**
```bash
python -m app.main
# or with uvicorn directly:
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Start Worker:**
```bash
python -m app.worker
```

## Production Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Using Kubernetes

Create Kubernetes manifests:

**1. Namespace:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: infraai
```

**2. ConfigMap:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: infraai-config
  namespace: infraai
data:
  POSTGRES_DSN: "postgresql+asyncpg://infraal:infraal@postgres:5432/infraal"
  REDIS_HOST: "redis"
  REDIS_PORT: "6379"
  OLLAMA_API_URL: "http://ollama:11434"
```

**3. API Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: infraai-api
  namespace: infraai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: infraai-api
  template:
    metadata:
      labels:
        app: infraai-api
    spec:
      containers:
      - name: api
        image: infraai-backend:latest
        command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
        ports:
        - containerPort: 8001
        envFrom:
        - configMapRef:
            name: infraai-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

**4. Worker Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: infraai-worker
  namespace: infraai
spec:
  replicas: 2
  selector:
    matchLabels:
      app: infraai-worker
  template:
    metadata:
      labels:
        app: infraai-worker
    spec:
      containers:
      - name: worker
        image: infraai-backend:latest
        command: ["python", "-m", "app.worker"]
        envFrom:
        - configMapRef:
            name: infraai-config
```

**5. Service:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: infraai-api
  namespace: infraai
spec:
  selector:
    app: infraai-api
  ports:
  - port: 80
    targetPort: 8001
  type: LoadBalancer
```

### Using Systemd (Linux)

**API Service (`/etc/systemd/system/infraai-api.service`):**
```ini
[Unit]
Description=InfraAI API Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=infraai
WorkingDirectory=/opt/infraai
Environment="PATH=/opt/infraai/venv/bin"
ExecStart=/opt/infraai/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Worker Service (`/etc/systemd/system/infraai-worker.service`):**
```ini
[Unit]
Description=InfraAI Worker
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=infraai
WorkingDirectory=/opt/infraai
Environment="PATH=/opt/infraai/venv/bin"
ExecStart=/opt/infraai/venv/bin/python -m app.worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable infraai-api infraai-worker
sudo systemctl start infraai-api infraai-worker
sudo systemctl status infraai-api infraai-worker
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `POSTGRES_DSN` | PostgreSQL connection string | `postgresql+asyncpg://infraal:infraal@localhost/infraal` | Yes |
| `REDIS_HOST` | Redis server hostname | `localhost` | Yes |
| `REDIS_PORT` | Redis server port | `6379` | Yes |
| `OLLAMA_API_URL` | Ollama API endpoint | `http://192.168.200.201:11434` | Yes |
| `OLLAMA_MODEL` | Ollama model name | `llama2` | No |
| `INFRAAL_API_KEY` | API authentication key | `dev-key-12345` | Yes |
| `PORT` | API server port | `8001` | No |

### PostgreSQL Connection String Format

```
postgresql+asyncpg://username:password@hostname:port/database
```

Examples:
- Local: `postgresql+asyncpg://infraal:infraal@localhost/infraal`
- Remote: `postgresql+asyncpg://user:pass@db.example.com:5432/infraai`
- Cloud: `postgresql+asyncpg://user:pass@aws-rds.amazonaws.com/infraai?ssl=require`

## Monitoring

### Health Checks

```bash
# API Health
curl http://localhost:8001/health

# Database connectivity
psql -h localhost -U infraal -d infraal -c "SELECT 1;"

# Redis connectivity
redis-cli ping

# Ollama availability
curl http://192.168.200.201:11434/api/tags
```

### Logs

**Docker Compose:**
```bash
docker-compose logs -f infraai-api
docker-compose logs -f infraai-worker
```

**Systemd:**
```bash
journalctl -u infraai-api -f
journalctl -u infraai-worker -f
```

**Application Logs:**
By default, logs go to stdout. In production, configure structured logging:

```python
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
```

## Security Hardening

### 1. Change Default API Key

```bash
# Generate a secure key
openssl rand -hex 32

# Update .env
INFRAAL_API_KEY=<generated-key>
```

### 2. Database Security

- Use strong passwords
- Enable SSL/TLS for connections
- Restrict network access
- Regular backups

```bash
# Backup
pg_dump -U infraal infraal > backup.sql

# Restore
psql -U infraal infraal < backup.sql
```

### 3. Redis Security

```bash
# Set password in redis.conf
requirepass <strong-password>

# Update connection in .env
REDIS_PASSWORD=<strong-password>
```

### 4. Network Security

- Use firewall rules
- Enable HTTPS with TLS certificates
- Restrict API access by IP
- Use VPN for sensitive operations

### 5. CORS Configuration

In production, restrict CORS origins in `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## Performance Tuning

### Database Connection Pool

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Worker Concurrency

Run multiple worker processes:

```bash
# Using supervisord
[program:infraai-worker]
command=/opt/infraai/venv/bin/python -m app.worker
process_name=%(program_name)s_%(process_num)02d
numprocs=4
```

### Redis Optimization

```bash
# Increase max memory
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Troubleshooting

### API Server Won't Start

```bash
# Check if port is already in use
lsof -i :8001

# Check PostgreSQL connection
psql -h localhost -U infraal -d infraal

# Check logs
journalctl -u infraai-api -n 50
```

### Worker Not Processing Tasks

```bash
# Check Redis connection
redis-cli ping

# Check queue depth
redis-cli LLEN remediation_queue

# Check worker logs
journalctl -u infraai-worker -n 50
```

### High Memory Usage

- Reduce database connection pool size
- Limit worker concurrency
- Enable Redis memory limits
- Monitor with `top` or `htop`

### Slow API Responses

- Check database query performance
- Enable database query logging
- Monitor Ollama response times
- Consider caching frequently accessed data

## Backup & Recovery

### Database Backup

```bash
# Full backup
pg_dump -U infraal -F c infraal > infraal_backup_$(date +%Y%m%d).dump

# Restore
pg_restore -U infraal -d infraal infraal_backup_20250101.dump
```

### Configuration Backup

```bash
# Backup .env and policies
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env scripts/sample_policies.json
```

## Scaling

### Horizontal Scaling

1. **API Servers**: Add more replicas behind a load balancer
2. **Workers**: Increase worker count based on queue depth
3. **Database**: Use read replicas for read-heavy workloads
4. **Redis**: Use Redis Cluster for high availability

### Vertical Scaling

- Increase CPU/RAM for compute-intensive operations
- Use faster storage (SSD) for database
- Optimize database indices

## Support

For issues and questions:
- Check logs first
- Review ARCHITECTURE.md for design details
- Check GitHub issues
- Contact support team
