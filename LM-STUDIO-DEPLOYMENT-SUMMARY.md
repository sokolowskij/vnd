# ✅ LM Studio + Docker Deployment - UPDATED SETUP

Your system is configured for **LM Studio** (local model) - no OpenAI API key needed!

## 📋 Files Updated for LM Studio

✅ `.env.example` - Already configured for LM Studio
✅ `docker-compose.yml` - Allows container access to host LM Studio  
✅ `deploy.sh` - Updated to include LM Studio setup for AWS
✅ `LM-STUDIO-SETUP.md` - Complete LM Studio guide (NEW)

---

## 🚀 Quick Start (Local Development)

### 1. Install LM Studio
- Download: https://lmstudio.ai/download
- Install on your machine
- Download a vision model (e.g., moondream2, llava)

### 2. Start LM Studio
- Open LM Studio app
- Load your model
- Click "Start Server" (runs on localhost:1234)

### 3. Start Docker Services
```bash
cp .env.example .env
# .env is already configured for LM Studio!

docker-compose build
docker-compose up -d

# Verify
curl http://localhost:8000/health
open http://localhost:8501
```

✅ Done! Dashboard at http://localhost:8501

---

## ☁️ AWS Deployment with LM Studio

### Option A: LM Studio on AWS EC2 (Recommended - Recommended)

**One-liner deployment:**
```bash
bash <(curl -fsSL https://your-repo-url/raw/main/deploy.sh)
```

**What happens:**
1. EC2 installs Docker
2. EC2 installs LM Studio
3. Docker container starts and connects to local LM Studio
4. Everything self-contained on one EC2 instance

**Requirements:**
- Ubuntu 22.04 LTS EC2
- **t3.medium or larger** (LM Studio is resource-heavy)
- 40+ GB storage

**Cost:** ~$30/month (t3.medium)

---

### Option B: Local LM Studio + AWS Docker (Budget)

**Uses your local machine's LM Studio:**
```bash
# On your machine: Keep LM Studio running
# On AWS: Docker connects to your local LM Studio
```

**Requirements:**
- AWS: t3.small ($8/month)
- Your machine: Always-on LM Studio

**Configure on AWS:**
```bash
sudo nano /opt/agentic-seller/.env

# Set your machine's public IP:
LOCAL_MODEL_API=http://YOUR_IP_HERE:1234/v1
```

---

## 🔧 Key Configuration

### .env File (Already Correct!)

```env
# Using local LM Studio - no API key needed!
LOCAL_MODEL_API=http://localhost:1234/v1
OPENAI_API_KEY=local-model
OPENAI_MODEL=model-identifier

# Other settings
POST_MODE=dry_run
HEADLESS=true
ENABLE_OLX=true
ENABLE_FACEBOOK=true
```

### Docker Networking

```yaml
# docker-compose.yml automatically:
extra_hosts:
  - "host.docker.internal:host-gateway"

# This allows Docker containers to reach
# LM Studio on localhost:1234
```

---

## ✨ What's Different

| Item | Before | Now |
|------|--------|-----|
| API Key | Required (OpenAI) | Not needed (LM Studio) |
| Model Provider | Cloud (OpenAI) | Local (LM Studio) |
| Dependencies | API Account + credit card | LM Studio + model file |
| Cost | $0.10-5.00 per 1M tokens | $0 (just electricity) |
| Privacy | Data sent to OpenAI | All local |

---

## 📚 Documentation

**Read these in order:**

1. **LM-STUDIO-SETUP.md** ← START HERE
   - LM Studio installation
   - Docker integration
   - Troubleshooting

2. **DOCKER-INDEX.md**
   - Navigation & quick start
   - Architecture overview

3. **DEPLOYMENT.md**
   - AWS deployment steps
   - SSL/HTTPS setup
   - Monitoring

4. **DOCKER-REFERENCE.md**
   - Docker commands
   - Troubleshooting

---

## ✅ Your Setup Checklist

### Local Testing (Today)
- [ ] Install LM Studio from https://lmstudio.ai
- [ ] Download a vision model
- [ ] Start LM Studio server (port 1234)
- [ ] Run: `docker-compose build && docker-compose up -d`
- [ ] Test: `curl http://localhost:8000/health`
- [ ] Access: http://localhost:8501

### AWS Deployment (This Week)
- [ ] Decide: Option A (LM Studio on EC2) or Option B (local LM Studio)
- [ ] Launch EC2 instance (Ubuntu 22.04 LTS)
- [ ] Run: `bash deploy.sh https://your-repo-url`
- [ ] Configure: `.env` with LM Studio settings
- [ ] Access: http://instance-ip:8501

---

## 🔍 Verify Setup

### Local
```bash
# Terminal 1: LM Studio (keep running)
# Open LM Studio app → Start Server

# Terminal 2: Docker
docker-compose up -d

# Terminal 3: Test
curl http://localhost:1234/v1/models      # LM Studio
curl http://localhost:8000/health         # Docker backend
open http://localhost:8501                # Dashboard
```

### AWS (Option A)
```bash
ssh -i key.pem ubuntu@your-ip

# Check LM Studio
curl http://localhost:1234/v1/models

# Check Docker
docker-compose ps
curl http://localhost:8000/health
```

### AWS (Option B)
```bash
ssh -i key.pem ubuntu@your-ip

# Check Docker can reach your machine
docker exec agentic-seller-backend \
  curl http://host.docker.internal:1234/v1/models
```

---

## 🆘 Troubleshooting

### "Cannot connect to LM Studio"

**Local:**
```bash
# Make sure LM Studio is running
curl http://localhost:1234/v1/models
```

**AWS:**
```bash
# Option A: Check LM Studio on EC2
ssh -i key.pem ubuntu@ip "curl http://localhost:1234/v1/models"

# Option B: Check connection to your machine
curl http://YOUR_LOCAL_IP:1234/v1/models
```

### Docker container can't reach host

**Local:**
Add to docker-compose.yml (already done):
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Use in .env:
```env
LOCAL_MODEL_API=http://host.docker.internal:1234/v1
```

---

## 💡 Pro Tips

### Performance
- **Lightweight models:** moondream2 (~3GB)
- **Balanced:** llava-1.5 (~7GB)  
- **Large:** llava-next (~15GB)

### Resource Monitoring
```bash
docker stats                    # Memory/CPU usage
docker-compose logs -f backend  # Check for errors
```

### Scaling Later
If you want to upgrade:
```bash
# Switch to OpenAI (just change .env)
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
```

---

## 🎯 Next Steps

1. **Download LM Studio:** https://lmstudio.ai/download

2. **Read full guide:** `cat LM-STUDIO-SETUP.md`

3. **Test locally:**
   ```bash
   docker-compose up -d
   curl http://localhost:8000/health
   ```

4. **Deploy to AWS:** Follow `LM-STUDIO-SETUP.md` - Option A or B

---

## 📝 Summary

✅ **LM Studio configured** - No API key needed
✅ **Docker ready** - Containers can access LM Studio
✅ **AWS-ready** - deploy.sh includes LM Studio setup
✅ **Cost-effective** - All local, no API fees
✅ **Documented** - Complete LM Studio guide included

**You're all set!** 🚀

Start with: `LM-STUDIO-SETUP.md`
Then: Local testing with `docker-compose up -d`
Finally: AWS deployment with `bash deploy.sh`
