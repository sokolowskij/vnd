# LM Studio Setup with Docker Deployment

Since you're using **LM Studio** (local model) instead of OpenAI API, here's how to set it up with Docker.

## Local Development Setup

### 1. Install LM Studio
- Download from: https://lmstudio.ai/download
- Install on your machine
- Download a vision-capable model (e.g., moondream2, llava, etc.)

### 2. Configure .env for Local Development

```bash
cp .env.example .env
nano .env
```

Your `.env` should already have the correct settings:

```env
LOCAL_MODEL_API=http://localhost:1234/v1
OPENAI_API_KEY=local-model
OPENAI_MODEL=google/gemma-4-e4b
```

### 3. Start LM Studio

1. Open LM Studio application
2. Load your vision model
3. Start the local server (usually port 1234)
4. You should see: "Server running at http://localhost:1234/v1"

### 4. Verify LM Studio is accessible

```bash
curl http://localhost:1234/v1/models
# Should return list of available models
```

### 5. Start Docker Services

```bash
docker-compose build
docker-compose up -d

# Verify backend can reach LM Studio
curl http://localhost:8000/health
# Should return: {"status":"healthy"...}
```

✅ **Local setup complete!**

---

## AWS Deployment with LM Studio

There are two approaches:

### Option A: Run LM Studio on EC2 Host (Recommended)

**Pros:**
- Fully self-contained
- No external dependencies
- Uses EC2 instance resources

**Cons:**
- LM Studio is heavy (~2-4GB RAM for large models)
- Requires larger instance (t3.medium or larger)

#### Step-by-Step:

1. **Launch EC2 Instance**
   - Ubuntu 22.04 LTS
   - **t3.medium or t3.large** (LM Studio is resource-intensive)
   - 40+ GB storage
   - GPU support (optional, but recommended for LM Studio)

2. **SSH into instance:**
   ```bash
   ssh -i your-key.pem ubuntu@your-instance-ip
   ```

3. **Install LM Studio on EC2:**
   ```bash
   # Install dependencies
   sudo apt-get update
   sudo apt-get install -y libfuse2 libgl1-mesa-glx

   # Download LM Studio
   cd /opt
   sudo wget -O lm-studio.AppImage \
     "https://releases.lmstudio.ai/linux/x64/LM%20Studio-0.3.11-x64.AppImage"
   
   sudo chmod +x lm-studio.AppImage
   
   # Create a directory for LM Studio
   mkdir -p ~/.lm-studio
   ```

4. **Run LM Studio in headless mode:**
   ```bash
   # First time (downloads model and starts server)
   /opt/lm-studio.AppImage --headless --port 1234 &
   
   # Or create systemd service for auto-start
   sudo tee /etc/systemd/system/lm-studio.service > /dev/null <<EOF
   [Unit]
   Description=LM Studio Server
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu
   ExecStart=/opt/lm-studio.AppImage --headless --port 1234
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   EOF
   
   sudo systemctl daemon-reload
   sudo systemctl enable lm-studio
   sudo systemctl start lm-studio
   ```

5. **Verify LM Studio is running:**
   ```bash
   curl http://localhost:1234/v1/models
   # Should return model list
   ```

6. **Continue with Docker deployment:**
   ```bash
   # Follow normal deployment steps
   bash <(curl -fsSL https://your-repo/raw/main/deploy.sh)
   ```

7. **Configure .env on server:**
   ```bash
   sudo nano /opt/agentic-seller/.env
   ```
   
   Should have:
   ```env
   LOCAL_MODEL_API=http://localhost:1234/v1
   OPENAI_API_KEY=local-model
   OPENAI_MODEL=google/gemma-4-e4b
   ```

8. **Restart Docker services:**
   ```bash
   cd /opt/agentic-seller
   docker-compose restart backend
   ```

9. **Verify:**
   ```bash
   curl http://localhost:8000/health
   # Should return healthy status
   ```

---

### Option B: Run LM Studio on Local Machine + AWS Docker

**Pros:**
- Smaller AWS instance (t3.small is fine)
- Lower AWS costs

**Cons:**
- Depends on local machine running LM Studio
- Requires network access from AWS to your machine

#### Step-by-Step:

1. **Keep LM Studio running on your local machine**

2. **Configure AWS Security Group**
   - Allow outbound traffic on port 1234
   - Or allow outbound traffic generally

3. **Get your machine's public IP:**
   ```bash
   curl ifconfig.me
   # e.g., 203.0.113.45
   ```

4. **On EC2, configure .env:**
   ```bash
   sudo nano /opt/agentic-seller/.env
   ```
   
   Set:
   ```env
   LOCAL_MODEL_API=http://203.0.113.45:1234/v1
   OPENAI_API_KEY=local-model
   OPENAI_MODEL=google/gemma-4-e4b
   ```

5. **Restart Docker:**
   ```bash
   docker-compose restart backend
   ```

⚠️ **Warning:** Your local machine IP must be stable and accessible. Not recommended for production.

---

## Troubleshooting LM Studio + Docker

### Docker can't reach LM Studio

**Error:** `requests.exceptions.ConnectionError: Failed to connect to Local Model API`

**Solution:**

```bash
# From backend container, test connection
docker exec agentic-seller-backend curl http://host.docker.internal:1234/v1/models

# Or test from host
curl http://localhost:1234/v1/models
```

### LM Studio crashes on startup

**Solution:**

LM Studio requires significant resources. If it crashes:

1. Check available memory:
   ```bash
   free -h
   ```

2. Check if port 1234 is in use:
   ```bash
   lsof -i :1234
   ```

3. Try with smaller model:
   - Download a smaller vision model in LM Studio
   - Or reduce other running services

### Docker container can't access host

**Solution:**

The docker-compose.yml includes:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

This allows containers to access `host.docker.internal:1234` instead of `localhost:1234`.

### Verify connectivity

```bash
# From host
curl http://localhost:1234/v1/models

# From container
docker exec agentic-seller-backend \
  curl http://host.docker.internal:1234/v1/models

# From different machine (if on same network)
curl http://YOUR_MACHINE_IP:1234/v1/models
```

---

## Performance Tips

### Local Machine (Development)

```bash
# Monitor resource usage
docker stats

# If slow, check if LM Studio is using resources
ps aux | grep -i "lm studio"
```

### AWS EC2 Instance

For t3.medium or t3.large:

```bash
# Monitor
docker stats

# Check memory
free -h

# Check CPU
top

# Limit Docker memory if needed
# Edit docker-compose.yml:
# services:
#   backend:
#     deploy:
#       resources:
#         limits:
#           memory: 2G
```

### Model Selection

**Lightweight (< 4GB):**
- moondream2
- TinyLlava
- Phi-2

**Medium (4-8GB):**
- Llava 1.5
- Mistral 7B

**Heavy (> 8GB):**
- Llava-NeXT
- GPT4V
- Larger models

---

## FAQ

**Q: Can I use Ollama instead of LM Studio?**
A: Yes! Just change `LOCAL_MODEL_API=http://localhost:11434/v1` and install Ollama instead.

**Q: What if I want to switch to OpenAI later?**
A: Just add your API key to .env:
```env
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=google/gemma-4-e4b
```

**Q: Can I run multiple models simultaneously?**
A: LM Studio typically runs one model at a time. For multiple models, consider Ollama or custom solution.

**Q: Is LM Studio suitable for production?**
A: It's designed for local development. For production, consider:
- Ollama (more stable, open-source)
- vLLM (optimized inference server)
- OpenAI API (managed service)
- AWS SageMaker (managed ML service)

**Q: How much disk space do I need?**
A: 
- LM Studio + models: 20-30GB
- Docker images: 2-3GB
- Data/state: varies
- **Recommendation: 40+ GB total**

---

## Your Current Setup Summary

✅ **Local Development:**
- Your machine: LM Studio (port 1234)
- Docker: Connects to localhost:1234
- .env already configured correctly

✅ **AWS Production (Option A - Recommended):**
- EC2 instance: LM Studio + Docker
- Single location, no external dependencies
- Requires t3.medium or larger

✅ **AWS Production (Option B - Budget):**
- EC2 instance: Docker only
- Your machine: LM Studio
- Lower AWS costs, requires always-on local setup

---

## Next Steps

1. **Test locally:**
   ```bash
   docker-compose build
   docker-compose up -d
   curl http://localhost:8000/health
   ```

2. **For AWS, decide on Option A or B**

3. **Configure .env** with LM Studio settings (already in .env.example)

4. **Deploy** using deploy.sh

**Your setup is ready!** 🚀
