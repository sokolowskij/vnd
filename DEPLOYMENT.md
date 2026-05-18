# Agentic Seller - Docker Deployment Guide

Current note: Docker is for AWS deployment only. The local Windows workflow uses Python venv, PowerShell, LM Studio, and Playwright directly. Do not use local Docker for the normal local workflow. See `README.md` and `FINAL_README.md`.

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
│  │  Dashboard       │  │  Review API      │ │
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
│         │  - products/              │       │
│         │  - ready_to_publish/      │       │
│         │  - auth/                  │       │
│         └───────────────────────────┘       │
└─────────────────────────────────────────────┘
```

## Local Setup

Do not use Docker locally for the normal workflow.

Local Windows uses Python venv, PowerShell, LM Studio, and Playwright directly:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

AWS Docker images are built on AWS through Docker Compose. Local Docker Desktop is not required.

## Environment Variables

Key AWS environment variables in `/opt/vnd/.env`:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SESSION_TTL_DAYS` | Browser session lifetime | `30` |
| `PENDING_RETENTION_DAYS` | In-review item retention | `90` |
| `READY_RETENTION_DAYS` | Approved item retention | `30` |
| `DAILY_BACKUP_ENABLED` | Enable email backups | `false` |
| `ADMIN_BACKUP_EMAIL` | Backup recipient | `admin@example.com` |

## AWS Deployment

### Quick Start (Recommended)

1. **Launch Ubuntu 22.04 LTS EC2/Lightsail instance**
   - Recommended: t3.small or higher for good performance
   - Open Security Group ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000, 8501

2. **SSH into your instance:**
   ```bash
   ssh -i your-key.pem ubuntu@your-instance-ip
   ```

3. **Clone and start the AWS dashboard/API app:**
   ```bash
   cd /opt
   sudo git clone https://github.com/sokolowskij/vnd.git vnd
   sudo chown -R ubuntu:ubuntu /opt/vnd
   cd /opt/vnd
   cp .env.example .env
   BUILD=1 ./scripts/aws-start.sh
   ```

4. **Configure environment:**
   ```bash
   nano /opt/vnd/.env
   # Configure retention/session/backup settings.
   
   # Restart services
   cd /opt/vnd
   BUILD=1 ./scripts/aws-start.sh
   ```

5. **Access your deployment:**
   - Dashboard: `http://your-instance-ip:8501`
   - API health: `http://your-instance-ip:8000/health` if port 8000 is exposed

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
sudo git clone https://github.com/sokolowskij/vnd.git vnd
sudo chown -R $USER:$USER vnd
cd vnd

# 6. Setup environment
cp .env.example .env
nano .env  # Configure retention/session/backup settings

# 7. Build and start
BUILD=1 ./scripts/aws-start.sh

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
cd /opt/vnd

# Pull latest changes
git pull

# Rebuild and restart dashboard/API containers
BUILD=1 ./scripts/aws-start.sh
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
env | grep -E "(SESSION_TTL|RETENTION|BACKUP|SMTP)"
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
