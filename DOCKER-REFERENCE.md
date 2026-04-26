# Docker Quick Reference

## Local Development

### Initial Setup
```bash
# Configure environment
cp .env.example .env
nano .env  # Set your OPENAI_API_KEY

# Option 1: Interactive setup
python setup.py

# Option 2: Manual Docker Compose
docker-compose build
docker-compose up -d
```

### Development Workflow
```bash
# View logs in real-time
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Execute commands in containers
docker exec agentic-seller-backend python -m agentic_seller.cli --help
docker exec agentic-seller-frontend streamlit --version

# Shell access
docker exec -it agentic-seller-backend bash
docker exec -it agentic-seller-frontend bash

# Rebuild after code changes
docker-compose build
docker-compose restart
```

### Stopping & Cleanup
```bash
# Stop services (keeps data)
docker-compose stop

# Stop and remove containers
docker-compose down

# Full cleanup (DELETES VOLUME DATA)
docker-compose down -v

# Remove unused images/volumes
docker system prune -a
```

## Architecture

**Two-Container Design:**

```
Frontend (Streamlit)  ←→  Backend (FastAPI)
:8501                      :8000
User Dashboard             Job Orchestration
                          + Agent CLI
```

**Shared Volume:** `/app/data/` persists across restarts

## API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List all jobs
curl http://localhost:8000/jobs

# Get specific job
curl http://localhost:8000/jobs/{job_id}

# Submit new job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "data_dir": "/app/data/products",
    "mode": "dry_run",
    "marketplaces": ["olx", "facebook"]
  }'
```

## File Structure
```
agentic-seller/
├── src/
│   └── agentic_seller/
│       ├── api.py           # NEW: FastAPI backend
│       ├── cli.py           # CLI entry point
│       ├── config.py        # UPDATED: Environment config
│       ├── orchestrator.py  # Agent orchestration
│       └── ...
├── Dockerfile.backend       # NEW: Backend container
├── Dockerfile.frontend      # NEW: Frontend container
├── docker-compose.yml       # NEW: Orchestration
├── .dockerignore            # NEW: Build optimization
├── dashboard.py             # NEW: Streamlit dashboard
├── setup.py                 # NEW: Interactive setup
├── deploy.sh                # NEW: AWS deployment
├── DEPLOYMENT.md            # NEW: Deployment guide
├── requirements.txt         # UPDATED: Added FastAPI, Streamlit
├── .env.example             # UPDATED: Docker paths
└── README.md
```

## Environment Variables

Set these in `.env` for customization:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...              # Your API key
OPENAI_MODEL=google/gemma-4-e4b           # Model to use

# Behavior
POST_MODE=dry_run                  # or 'publish'
HEADLESS=true                      # Browser headless mode
DEFAULT_CURRENCY=PLN               # Default currency

# Marketplaces
ENABLE_OLX=true
ENABLE_FACEBOOK=true

# Paths (Docker)
USER_DATA_DIR=/app/data/browser_profiles

# Ports
API_PORT=8000
STREAMLIT_PORT=8501
```

## Why Two Containers?

| Aspect | Benefit |
|--------|---------|
| **Scalability** | Scale frontend/backend independently |
| **Isolation** | Crash in one doesn't affect the other |
| **Clarity** | Clear separation of concerns |
| **Debugging** | Easier to diagnose issues |
| **Deployment** | Can use different base images/configs |
| **Updates** | Update one service without rebuilding all |

## Persistent Storage

Volume: `agentic_data`

Contents:
- `browser_profiles/` - Selenium/Playwright cache
- `jobs/` - Job metadata and results
- `products/` - Input product data
- `results/` - Listing output

**Location:**
- Docker: `/app/data/`
- Host: `/var/lib/docker/volumes/agentic_data/_data/`

## Production Considerations

1. **Never commit `.env` to git** - use `.env.example`
2. **Use Docker secrets** for sensitive data in Swarm mode
3. **Enable restart policies** - already in docker-compose.yml
4. **Set resource limits** - prevent runaway containers
5. **Use health checks** - included for both services
6. **Monitor logs** - implement centralized logging
7. **Backup volumes** - automate data backups
8. **Use environment-specific configs** - docker-compose.prod.yml

## Common Issues & Fixes

**Backend won't start:**
```bash
docker-compose logs backend | tail -50
# Check .env has OPENAI_API_KEY set
```

**Frontend shows "Cannot reach backend":**
```bash
# Verify backend is healthy
docker-compose ps
curl http://backend:8000/health  # from within frontend container

# Check network
docker network inspect agentic-network
```

**Out of disk space:**
```bash
docker system prune -a          # Remove all unused
docker volume prune             # Remove unused volumes
```

**Need to rebuild:**
```bash
docker-compose build --no-cache
```

## Testing the Deployment

```bash
# 1. Check services running
docker-compose ps

# 2. Test backend API
curl http://localhost:8000/health

# 3. Access dashboard
open http://localhost:8501

# 4. Check logs
docker-compose logs | grep -i error

# 5. Submit test job from dashboard
# Uses /app/data/products as default directory
```

## AWS Deployment

See `DEPLOYMENT.md` for full AWS setup and production instructions.

Quick start:
```bash
# On fresh Ubuntu EC2 instance:
bash <(curl -fsSL https://raw.githubusercontent.com/yourusername/agentic-seller/main/deploy.sh)
```
