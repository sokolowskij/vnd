#!/bin/bash
# AWS Deployment Script: Agentic Seller on EC2/Lightsail
# Run this on a fresh Ubuntu 22.04 LTS instance

set -e

echo "🚀 Starting Agentic Seller AWS Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Exit on error
trap 'echo -e "${RED}❌ Deployment failed${NC}"; exit 1' ERR

echo -e "${YELLOW}Step 1: Update system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

echo -e "${YELLOW}Step 2: Install Docker...${NC}"
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

echo -e "${YELLOW}Step 3: Install Docker Compose...${NC}"
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo -e "${YELLOW}Step 4: Add current user to docker group...${NC}"
sudo usermod -aG docker $USER
newgrp docker << EOF
echo "✅ Docker group configured"
EOF

echo -e "${YELLOW}Step 5: Install git...${NC}"
sudo apt-get install -y git curl

echo -e "${YELLOW}Step 6: Clone repository...${NC}"
# Replace with your actual repository URL
REPO_URL="${1:-https://github.com/yourusername/agentic-seller.git}"
DEPLOY_DIR="/opt/agentic-seller"

sudo mkdir -p $DEPLOY_DIR
sudo chown $USER:$USER $DEPLOY_DIR

cd $DEPLOY_DIR
if [ ! -d .git ]; then
    git clone $REPO_URL . || {
        echo -e "${RED}❌ Failed to clone repository${NC}"
        echo "Please ensure you've passed the correct repo URL"
        exit 1
    }
else
    git pull origin main || git pull origin master
fi

echo -e "${YELLOW}Step 7: Install LM Studio (Local Model Provider)...${NC}"
# Download LM Studio AppImage for Linux
LM_STUDIO_DIR="$HOME/.lm-studio"
mkdir -p $LM_STUDIO_DIR

if [ ! -f "$LM_STUDIO_DIR/LM_Studio-0.3.11-x64.AppImage" ]; then
    echo "Downloading LM Studio..."
    cd $LM_STUDIO_DIR
    # Using a reliable download URL - update version as needed
    curl -fsSL -o LM_Studio.AppImage \
        "https://releases.lmstudio.ai/linux/x64/LM%20Studio-0.3.11-x64.AppImage" || {
        echo -e "${YELLOW}⚠️  LM Studio download failed. Will need manual installation.${NC}"
        echo "Download from: https://lmstudio.ai/download"
    }
    chmod +x LM_Studio.AppImage
    cd -
fi

# Create systemd service for LM Studio (optional)
echo -e "${YELLOW}Creating LM Studio systemd service...${NC}"
sudo tee /etc/systemd/system/lm-studio.service > /dev/null <<EOF
[Unit]
Description=LM Studio - Local Model Provider
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=$LM_STUDIO_DIR/LM_Studio.AppImage --headless --port 1234
Restart=always
RestartSec=10
Environment="DISPLAY=:0"
Environment="LIBGL_ALWAYS_INDIRECT=1"

[Install]
WantedBy=multi-user.target
EOF

echo -e "${YELLOW}⚠️  Note: LM Studio requires a display server or headless mode.${NC}"
echo "For EC2 headless instance, you'll need to run LM Studio differently."
echo "See deployment guide for alternatives (Ollama, local Python scripts, etc.)"

echo -e "${YELLOW}Step 7: Create .env file...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env with your OpenAI API key and settings:${NC}"
    echo "   sudo nano $DEPLOY_DIR/.env"
    echo ""
    read -p "Press Enter once you've configured .env, or Ctrl+C to abort: "
fi

echo -e "${YELLOW}Step 8: Build Docker images...${NC}"
docker-compose build

echo -e "${YELLOW}Step 9: Start services with Docker Compose...${NC}"
docker-compose up -d

echo -e "${YELLOW}Step 10: Verify services are running...${NC}"
sleep 5

# Check backend health
BACKEND_HEALTH=$(curl -s http://localhost:8000/health || echo "{\"status\":\"down\"}")
echo "Backend status: $BACKEND_HEALTH"

# Check frontend is accessible
if curl -s http://localhost:8501 > /dev/null; then
    echo "Frontend status: ✅ Running on port 8501"
else
    echo "Frontend status: ⏳ Starting (may take a moment)"
fi

echo ""
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo ""
echo "📍 Access your services:"
echo "   Backend API:  http://$(hostname -I | awk '{print $1}'):8000"
echo "   Dashboard:    http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo "📚 Useful Docker Compose commands:"
echo "   View logs:              docker-compose logs -f"
echo "   Stop services:          docker-compose down"
echo "   Restart services:       docker-compose restart"
echo "   View running services:  docker-compose ps"
echo ""
echo "🔐 To update .env and restart:"
echo "   nano $DEPLOY_DIR/.env"
echo "   docker-compose restart"
echo ""
echo "📁 Persistent data location: $DEPLOY_DIR/data/"
