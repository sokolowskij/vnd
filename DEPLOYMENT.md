# Agentic Seller - Docker Deployment Guide

This guide covers containerizing and deploying your Agentic Seller system to AWS (EC2/Lightsail) using Docker and Docker Compose.

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│         Internet / AWS Security Group       │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Frontend (8501) │  │  Backend (8000)  │ │
│  │  Streamlit       │  │  FastAPI         │ │
│  │  Dashboard       │  │  + Agent CLI     │ │
│  └────────┬─────────┘  └────────┬─────────┘ │
│           │                      │          │
│           └──────────┬───────────┘          │
│                      │                      │
│         ┌────────────▼──────────────┐       │
│         │  Docker Network Bridge    │       │
│         │  (agentic-network)        │       │
│         └────────────┬──────────────┘       │
│                      │                      │
│         ┌────────────▼──────────────┐       │
│         │  Persistent Volume        │       │
│         │  /app/data/               │       │
│         │  - browser_profiles/      │       │
│         │  - jobs/                  │       │
│         │  - products/              │       │
│         │  - results/               │       │
│         └───────────────────────────┘       │
└─────────────────────────────────────────────┘
```

## Local Setup (Before Docker)

1. **Ensure dependencies are installed:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **For LM Studio users (recommended - no API key needed):**
   ```bash
   # Install LM Studio from https://lmstudio.ai
   # Download a vision-capable model (moondream2, llava, etc.)
   # Start the local server (port 1234)
   
   # .env is already configured for LM Studio
   cp .env.example .env
   # LOCAL_MODEL_API, OPENAI_API_KEY=local-model already set
   ```

3. **Or use OpenAI API (optional):**
   ```bash
   cp .env.example .env
   nano .env  # Set OPENAI_API_KEY=sk-your-api-key
   ```

**See `LM-STUDIO-SETUP.md` for detailed LM Studio configuration.**

## Building Docker Images Locally

### Build individually:
```bash
# Backend
docker build -f Dockerfile.backend -t agentic-seller-backend:latest .

# Frontend
docker build -f Dockerfile.frontend -t agentic-seller-frontend:latest .
```

### Or use Docker Compose (recommended):
```bash
docker-compose build
```

## Running Locally with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Environment Variables

Key environment variables in `.env`:

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |
| `OPENAI_MODEL` | Model to use | `google/gemma-4-e4b` |
| `POST_MODE` | Publishing mode | `dry_run` or `publish` |
| `HEADLESS` | Run browser headless | `true` |
| `ENABLE_OLX` | Enable OLX marketplace | `true` |
| `ENABLE_FACEBOOK` | Enable Facebook marketplace | `true` |
| `USER_DATA_DIR` | Path to browser profiles | `/app/data/browser_profiles` |

## AWS Deployment

### Quick Start (Recommended)

1. **Launch Ubuntu 22.04 LTS EC2/Lightsail instance**
   - Recommended: t3.small or higher for good performance
   - Open Security Group ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000, 8501

2. **SSH into your instance:**
   ```bash
   ssh -i your-key.pem ubuntu@your-instance-ip
   ```

3. **Run deployment script:**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/yourusername/agentic-seller/main/deploy.sh | bash -s https://github.com/yourusername/agentic-seller.git
   ```

4. **Configure environment:**
   ```bash
   sudo nano /opt/agentic-seller/.env
   # Add your OPENAI_API_KEY and other settings
   
   # Restart services
   docker-compose -f /opt/agentic-seller/docker-compose.yml restart
   ```

5. **Access your deployment:**
   - Dashboard: `http://your-instance-ip:8501`
   - API: `http://your-instance-ip:8000`

### Manual Steps

If you prefer manual setup:

```bash
# 1. Connect to EC2 instance
ssh -i key.pem ubuntu@your-instance-ip

# 2. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 3. Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# 4. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. Clone repository
cd /opt
sudo git clone https://github.com/yourusername/agentic-seller.git
sudo chown -R $USER:$USER agentic-seller
cd agentic-seller

# 6. Setup environment
cp .env.example .env
nano .env  # Configure your API keys

# 7. Build and start
docker-compose build
docker-compose up -d

# 8. View logs
docker-compose logs -f
```

## Nginx Reverse Proxy Setup (Optional)

For production, use Nginx to proxy requests:

```bash
sudo apt-get install -y nginx
```

Create `/etc/nginx/sites-available/agentic-seller`:

```nginx
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:8501;
}

server {
    listen 80;
    server_name your-domain.com;

    # API endpoints
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Streamlit dashboard
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/agentic-seller /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL/HTTPS with Let's Encrypt (Recommended)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo systemctl enable certbot.timer
```

## Monitoring & Logs

```bash
# View all service logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Check container stats
docker stats

# Container shell access
docker exec -it agentic-seller-backend bash
docker exec -it agentic-seller-frontend bash
```

## Persistent Storage

Your data is stored in a Docker named volume: `agentic_data`

Location on host: `/var/lib/docker/volumes/agentic_data/_data/`

Contents:
- `browser_profiles/` - Playwright browser cache
- `jobs/` - Job metadata and results
- `products/` - Product data
- `results/` - Listing results

## Backup & Recovery

```bash
# Backup data volume
docker run --rm -v agentic_data:/data -v $(pwd):/backup ubuntu tar czf /backup/agentic_data.tar.gz /data

# Restore data volume
docker run --rm -v agentic_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/agentic_data.tar.gz -C /

# Backup entire deployment
cd /opt/agentic-seller
tar czf agentic-seller-backup.tar.gz .
```

## Troubleshooting

### Backend won't start
```bash
docker-compose logs backend
# Check OPENAI_API_KEY is set in .env
# Check Docker has enough disk space
```

### Frontend can't connect to backend
```bash
# Verify backend is healthy
docker-compose ps

# Check network connectivity
docker exec agentic-seller-frontend curl http://backend:8000/health
```

### Out of disk space
```bash
docker system prune -a  # Remove unused images
docker volume prune      # Remove unused volumes
```

### High memory usage
```bash
docker stats
# Restart problematic container
docker-compose restart backend
```

## Updating Your Deployment

```bash
cd /opt/agentic-seller

# Pull latest changes
git pull origin main

# Rebuild images
docker-compose build

# Restart services
docker-compose restart

# Or full restart
docker-compose down
docker-compose up -d
```

## Performance Tuning

### For larger workloads, adjust docker-compose.yml:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M
```

### For high concurrency:
- Use AWS Application Load Balancer (ALB) for multiple instances
- Consider AWS RDS for centralized database
- Use S3 for distributed storage

## Cost Optimization (AWS)

1. **Use t3.small or t3.medium** for variable workloads (burstable)
2. **Enable auto-scaling** if using load balancer
3. **Set up CloudWatch** monitoring and alarms
4. **Use spot instances** for non-critical batch jobs
5. **Consider Lightsail** for simpler deployments with predictable costs

## Support & Debugging

For issues, provide:
```bash
# Collect debug info
docker-compose version
docker --version
docker-compose ps
docker-compose logs backend | head -100
env | grep -E "(OPENAI|POST_MODE|HEADLESS)"
```

## Next Steps

1. ✅ Deploy to AWS
2. ✅ Configure custom domain (optional)
3. ✅ Set up SSL/HTTPS
4. ✅ Configure backups
5. ✅ Monitor with CloudWatch
6. ✅ Integrate with CI/CD pipeline for auto-updates

---

**Questions?** Check logs with `docker-compose logs -f` for detailed error messages.
