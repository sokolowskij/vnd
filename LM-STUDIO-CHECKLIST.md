# LM Studio Setup Checklist

## Local Development - Quick Start

### Prerequisites
- [ ] Windows/Mac/Linux machine with 8+ GB RAM
- [ ] Docker installed locally
- [ ] LM Studio downloaded from https://lmstudio.ai/download

### 1. LM Studio Installation

- [ ] Download LM Studio from https://lmstudio.ai/download
- [ ] Install LM Studio
- [ ] Launch LM Studio application
- [ ] Wait for it to initialize

### 2. Download Vision Model

In LM Studio app:

- [ ] Click "Discover"
- [ ] Search for vision model (recommendations):
  - [ ] **moondream2** (smallest, ~3GB) ← Recommended for testing
  - [ ] **llava-1.5-7b** (~7GB) ← Good balance
  - [ ] **llava-1.5-13b** (~13GB) ← Higher quality
- [ ] Download and install your chosen model
- [ ] Wait for download to complete

### 3. Start LM Studio Server

- [ ] In LM Studio, select your downloaded model
- [ ] Click "Start Server" button (or play icon)
- [ ] Verify message: "Server running at http://localhost:1234/v1"
- [ ] **Keep LM Studio running** (don't close it)

### 4. Verify LM Studio is Accessible

Open a terminal:
```bash
curl http://localhost:1234/v1/models
# Should return JSON with your model listed
```

- [ ] Command returns model list (not error)
- [ ] LM Studio still running

## Docker Setup - Local Testing

### 5. Configure Environment

```bash
cd /path/to/agentic-seller
cp .env.example .env
# .env is already configured for LM Studio!
# No changes needed unless you want to customize
```

- [ ] `.env` file created
- [ ] Verified content has:
  - `LOCAL_MODEL_API=http://localhost:1234/v1`
  - `OPENAI_API_KEY=local-model`

### 6. Build Docker Images

```bash
docker-compose build
```

- [ ] Build completes without errors
- [ ] Backend image created
- [ ] Frontend image created

### 7. Start Docker Services

```bash
docker-compose up -d
sleep 10
docker-compose ps
```

- [ ] Both services show "running" status
- [ ] No obvious errors

### 8. Verify Backend Connection to LM Studio

```bash
curl http://localhost:8000/health
```

- [ ] Returns: `{"status":"healthy","timestamp":"..."}`
- [ ] NOT connection error to LM Studio

### 9. Test Streamlit Dashboard

```bash
open http://localhost:8501
# or: start http://localhost:8501
```

- [ ] Dashboard loads in browser
- [ ] No error messages
- [ ] Dashboard shows navigation menu

### 10. Test Job Submission

In dashboard:
- [ ] Click "Submit Job" tab
- [ ] Fill in fields:
  - Data Directory: `/app/data/products` (default OK)
  - Mode: `dry_run`
  - Marketplaces: Select at least one
- [ ] Click "Submit Job"
- [ ] Success message appears
- [ ] Job ID displayed

### 11. Verify Job Storage

```bash
curl http://localhost:8000/jobs
```

- [ ] Returns list of jobs
- [ ] Your submitted job appears in list

### 12. Check Logs for Issues

```bash
docker-compose logs backend | tail -20
docker-compose logs frontend | tail -20
```

- [ ] No ERROR messages
- [ ] No connection refused messages

## Local Testing - Verification

- [ ] LM Studio running and accessible: http://localhost:1234/v1/models
- [ ] Docker services running: `docker-compose ps` shows both "running"
- [ ] Backend health: `curl http://localhost:8000/health` returns healthy
- [ ] Dashboard loads: http://localhost:8501 opens in browser
- [ ] Job submission works: Can submit job via dashboard
- [ ] No error logs: `docker-compose logs` shows no ERROR messages

✅ **Local testing complete! Ready for AWS.**

---

## AWS Deployment - Option A (Recommended)

### Prerequisites

- [ ] AWS account
- [ ] EC2 instance ready:
  - OS: Ubuntu 22.04 LTS
  - Type: **t3.medium** (minimum for LM Studio)
  - Storage: 40+ GB
  - Security Group: Ports 22, 80, 443 open
- [ ] SSH key pair downloaded
- [ ] Code pushed to GitHub

### 1. Launch EC2 Instance

- [ ] Instance launched (Ubuntu 22.04 LTS, t3.medium)
- [ ] Security group configured:
  - [ ] SSH (22): from your IP or 0.0.0.0/0
  - [ ] HTTP (80): 0.0.0.0/0
  - [ ] HTTPS (443): 0.0.0.0/0
- [ ] SSH key pair saved and permissions set:
  ```bash
  chmod 600 your-key.pem
  ```
- [ ] Instance IP address noted

### 2. SSH Into Instance

```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

- [ ] Connected to instance
- [ ] Prompt shows: `ubuntu@ip:~$`

### 3. Run Deployment Script

```bash
bash <(curl -fsSL https://github.com/YOUR_USERNAME/agentic-seller/raw/main/deploy.sh)
# Or with explicit repo URL:
bash <(curl -fsSL https://github.com/YOUR_USERNAME/agentic-seller/raw/main/deploy.sh) \
  https://github.com/YOUR_USERNAME/agentic-seller.git
```

- [ ] Script starts running
- [ ] Watch output for errors
- [ ] Script completes (5-15 minutes)

### 4. Configure Environment on Server

```bash
sudo nano /opt/agentic-seller/.env
```

Verify/update:
```env
LOCAL_MODEL_API=http://localhost:1234/v1
OPENAI_API_KEY=local-model
OPENAI_MODEL=model-identifier
```

- [ ] .env file exists at `/opt/agentic-seller/.env`
- [ ] LM Studio settings correct
- [ ] Saved (Ctrl+O, Enter, Ctrl+X in nano)

### 5. Restart Docker Services

```bash
cd /opt/agentic-seller
docker-compose restart
```

- [ ] Services restart without errors

### 6. Verify AWS Deployment

```bash
docker-compose ps
```

- [ ] Both services show "running"

```bash
curl http://localhost:8000/health
```

- [ ] Returns healthy status

### 7. Access Dashboard

```
In browser: http://your-instance-ip:8501
```

- [ ] Dashboard loads
- [ ] Can see job submission form

### 8. Test Job Submission on AWS

- [ ] Submit test job via dashboard
- [ ] Job appears in jobs list
- [ ] Check backend logs:
  ```bash
  docker-compose logs -f backend | head -20
  ```
  No errors related to LM Studio connection

✅ **AWS deployment complete (Option A)!**

---

## AWS Deployment - Option B (Budget)

### Prerequisites

- [ ] AWS account
- [ ] EC2 instance ready:
  - OS: Ubuntu 22.04 LTS
  - Type: **t3.small** (sufficient for Docker only)
  - Storage: 20+ GB
  - Security Group: Ports 22, 80, 443 open
- [ ] SSH key pair downloaded
- [ ] LM Studio running on your local machine (keep running!)
- [ ] Your machine's public IP address

### 1. Get Your Machine's Public IP

```bash
curl ifconfig.me
# e.g., 203.0.113.45 (save this!)
```

- [ ] Public IP noted
- [ ] LM Studio still running on your machine

### 2. Launch EC2 Instance (t3.small)

- [ ] Instance launched (Ubuntu 22.04 LTS, t3.small)
- [ ] Security group configured
- [ ] SSH key ready
- [ ] Instance IP noted

### 3. SSH and Run Deployment

```bash
ssh -i your-key.pem ubuntu@your-instance-ip
bash <(curl -fsSL https://your-repo/raw/main/deploy.sh)
```

- [ ] Connected and deployment running
- [ ] Script completes

### 4. Configure .env with Your Machine's IP

```bash
sudo nano /opt/agentic-seller/.env
```

Update:
```env
LOCAL_MODEL_API=http://YOUR_PUBLIC_IP:1234/v1
# e.g., http://203.0.113.45:1234/v1
```

- [ ] Your public IP added
- [ ] File saved

### 5. Restart Services

```bash
cd /opt/agentic-seller
docker-compose restart
```

- [ ] Services restart successfully

### 6. Verify Connection

```bash
curl http://localhost:8000/health
docker-compose logs backend | grep -i error
```

- [ ] Health check passes
- [ ] No connection errors

### 7. Test Dashboard

```
Browser: http://your-instance-ip:8501
```

- [ ] Dashboard loads
- [ ] Can submit jobs

### Important Notes for Option B

⚠️ **Your machine must:**
- [ ] Keep LM Studio running (always-on)
- [ ] Have stable public IP (or update .env if IP changes)
- [ ] Have port 1234 accessible from internet
- [ ] Have firewall configured to allow port 1234 from AWS

✅ **AWS deployment complete (Option B)!**

---

## Post-Deployment Monitoring

### Check Service Status

```bash
docker-compose ps
# Both should show "running"
```

### View Logs

```bash
docker-compose logs -f
# Watch for any errors
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List jobs
curl http://localhost:8000/jobs

# Submit test job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"data_dir":"/app/data/products","mode":"dry_run","marketplaces":["olx"]}'
```

### Monitor Resource Usage

```bash
docker stats
# Check memory and CPU usage
```

- [ ] Memory usage reasonable (< 2GB)
- [ ] CPU usage not constantly at 100%

---

## Troubleshooting

### LM Studio Won't Start Locally

- [ ] Check RAM: `free -h` on Linux/Mac
- [ ] Close other applications
- [ ] Try smaller model (moondream2)
- [ ] Restart computer

### Cannot Connect to LM Studio

Local:
```bash
curl http://localhost:1234/v1/models
# Should return JSON, not connection error
```

AWS:
```bash
docker exec agentic-seller-backend \
  curl http://host.docker.internal:1234/v1/models
```

### Docker Services Won't Start

```bash
docker-compose logs backend
# Look for specific error messages
```

Check:
- [ ] Docker is installed and running
- [ ] Ports 8000, 8501 not in use
- [ ] Sufficient disk space: `df -h`

### Dashboard Shows "Cannot Reach Backend"

```bash
# Verify backend is running
docker-compose ps

# Check logs
docker-compose logs backend | tail -20

# Test directly
curl http://localhost:8000/health
```

---

## After Successful Setup

- [ ] Document your setup in notes
- [ ] Save .env configuration (securely)
- [ ] Note instance IP/domain
- [ ] Set up auto-restart on reboot (if needed)
- [ ] Schedule regular backups
- [ ] Test disaster recovery procedures

---

## Checklist Complete! ✅

You've successfully:
- [ ] Set up LM Studio locally
- [ ] Configured Docker with LM Studio
- [ ] Tested local deployment
- [ ] Deployed to AWS (Option A or B)
- [ ] Verified all systems working

**Your Agentic Seller system is live!** 🚀

Next: Monitor deployment and start submitting jobs.

See `LM-STUDIO-SETUP.md` for more detailed information.
