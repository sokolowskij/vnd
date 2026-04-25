# Pre-Deployment Checklist

## ✅ Local Testing

- [ ] **Environment Setup**
  ```bash
  cp .env.example .env
  nano .env  # Set OPENAI_API_KEY
  ```

- [ ] **Docker Installation**
  ```bash
  docker --version           # Should show v20+
  docker-compose --version   # Should show v2+
  ```

- [ ] **Build Docker Images**
  ```bash
  docker-compose build
  ```

- [ ] **Start Services**
  ```bash
  docker-compose up -d
  sleep 10
  docker-compose ps  # All should be "running"
  ```

- [ ] **Verify Backend**
  ```bash
  curl http://localhost:8000/health
  # Expected: {"status":"healthy","timestamp":"..."}
  ```

- [ ] **Access Dashboard**
  ```
  Open: http://localhost:8501
  Should load Streamlit dashboard
  ```

- [ ] **Test Job Submission**
  ```bash
  curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{
      "data_dir": "/app/data/products",
      "mode": "dry_run",
      "marketplaces": ["olx"]
    }'
  # Should return job_id
  ```

- [ ] **Check Logs**
  ```bash
  docker-compose logs backend | head -20   # No errors
  docker-compose logs frontend | head -20  # No errors
  ```

- [ ] **Cleanup Test**
  ```bash
  docker-compose down
  # Should stop without errors
  docker-compose up -d
  # Should start cleanly
  ```

## ✅ Repository Setup

- [ ] **Create .gitignore**
  - [ ] .env (not .env.example)
  - [ ] __pycache__/
  - [ ] .venv/
  - [ ] *.pyc
  - [ ] data/
  - [ ] browser_profiles/

- [ ] **Verify .env not tracked**
  ```bash
  git status | grep .env
  # Should NOT show .env file
  # Should show .env.example only
  ```

- [ ] **Commit Docker files**
  ```bash
  git add Dockerfile* docker-compose* .dockerignore
  git add src/agentic_seller/api.py dashboard.py
  git add DOCKER* DEPLOYMENT* GIT-SETUP.md
  git add deploy.sh setup.py
  git add requirements.txt
  git commit -m "Add Docker deployment setup"
  ```

- [ ] **Push to GitHub**
  ```bash
  git push origin main
  # Or your default branch
  ```

- [ ] **Update deploy.sh**
  - [ ] Change line 48 from template URL to your repo:
    ```bash
    REPO_URL="https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    ```

- [ ] **Verify repository structure**
  ```bash
  On GitHub, check:
  - Dockerfile.backend ✓
  - Dockerfile.frontend ✓
  - docker-compose.yml ✓
  - .env.example (no .env) ✓
  - deploy.sh ✓
  - src/agentic_seller/api.py ✓
  - dashboard.py ✓
  - Documentation files ✓
  ```

## ✅ AWS Infrastructure

- [ ] **Create EC2 Instance**
  - [ ] OS: Ubuntu 22.04 LTS (free tier or small instance)
  - [ ] Instance type: t3.small or t3.medium (recommended)
  - [ ] Storage: 20+ GB (EBS gp3)
  - [ ] Region: Choose wisest for you
  - [ ] Save SSH key pair

- [ ] **Configure Security Group**
  - [ ] SSH (22): Your IP only OR 0.0.0.0/0 (less secure)
  - [ ] HTTP (80): 0.0.0.0/0 (required for Let's Encrypt)
  - [ ] HTTPS (443): 0.0.0.0/0 (for production)
  - [ ] Custom (8000): Optional (for direct API access)
  - [ ] Custom (8501): Optional (for direct dashboard access)

- [ ] **Test SSH Connection**
  ```bash
  ssh -i your-key.pem ubuntu@your-instance-ip
  # Should connect without password
  exit
  ```

## ✅ AWS Deployment

- [ ] **Run Deployment Script**
  ```bash
  ssh -i your-key.pem ubuntu@your-instance-ip
  bash <(curl -fsSL https://github.com/YOUR_USERNAME/YOUR_REPO/raw/main/deploy.sh)
  ```

- [ ] **Wait for Script Completion**
  - [ ] Should take 5-10 minutes
  - [ ] Watch for any errors
  - [ ] Note final instance IP address

- [ ] **Configure .env on Server**
  ```bash
  ssh -i your-key.pem ubuntu@your-instance-ip
  sudo nano /opt/agentic-seller/.env
  # Add: OPENAI_API_KEY=sk-...
  # Save and exit
  
  docker-compose -C /opt/agentic-seller restart
  ```

- [ ] **Verify Services Running**
  ```bash
  ssh -i your-key.pem ubuntu@your-instance-ip
  cd /opt/agentic-seller
  docker-compose ps
  # Should show both backend and frontend as "running"
  ```

- [ ] **Test API Endpoint**
  ```bash
  curl http://your-instance-ip:8000/health
  # Expected: {"status":"healthy"...}
  ```

- [ ] **Access Dashboard**
  ```
  Open: http://your-instance-ip:8501
  Should load Streamlit dashboard with job form
  ```

- [ ] **Submit Test Job**
  - [ ] Use dashboard to submit dry_run job
  - [ ] Verify job appears in job list
  - [ ] Check backend logs for activity

## ✅ Post-Deployment

- [ ] **Monitor Services**
  ```bash
  ssh -i your-key.pem ubuntu@your-instance-ip
  cd /opt/agentic-seller
  docker-compose logs -f
  # Watch for errors or issues
  ```

- [ ] **Backup Configuration**
  ```bash
  # Local copy
  ssh -i your-key.pem ubuntu@your-instance-ip "cat /opt/agentic-seller/.env" > agentic-seller.env.backup
  # Store securely (this has your API key!)
  chmod 600 agentic-seller.env.backup
  ```

- [ ] **Setup SSH Key Access** (Optional but recommended)
  - [ ] Create deployment user on EC2
  - [ ] Add SSH public key to ~/.ssh/authorized_keys
  - [ ] Disable password auth
  - [ ] Use SSH config for easier access

- [ ] **Enable Auto-Backups** (Optional)
  ```bash
  # Set up AWS EBS snapshots
  # Or use: docker run --rm -v agentic_data:/data ...
  ```

## ✅ Production Setup (Optional)

- [ ] **SSL/HTTPS with Let's Encrypt**
  ```bash
  ssh -i your-key.pem ubuntu@your-instance-ip
  sudo apt-get install certbot python3-certbot-nginx
  sudo certbot --nginx -d your-domain.com
  # Follow prompts
  ```

- [ ] **Configure Nginx Reverse Proxy**
  ```bash
  # See DEPLOYMENT.md for Nginx configuration
  sudo nano /etc/nginx/sites-available/agentic-seller
  sudo ln -s /etc/nginx/sites-available/agentic-seller /etc/nginx/sites-enabled/
  sudo nginx -t
  sudo systemctl restart nginx
  ```

- [ ] **Configure Custom Domain**
  - [ ] Point DNS A record to instance IP
  - [ ] Test: nslookup your-domain.com
  - [ ] Wait for DNS propagation (5-30 minutes)

- [ ] **Set Up Monitoring**
  ```bash
  # AWS CloudWatch
  # Or use: docker stats, systemd monitoring
  ```

- [ ] **Enable CloudTrail Logging** (AWS)
  - [ ] For audit trail of all API calls
  - [ ] Useful for debugging

## ✅ Disaster Recovery

- [ ] **Document Access**
  - [ ] Instance IP: ___________
  - [ ] SSH key location: ___________
  - [ ] Domain name: ___________
  - [ ] Backup .env location: ___________

- [ ] **Set Up Backup Procedure**
  ```bash
  # Monthly backup
  docker run --rm -v agentic_data:/data -v /tmp:/backup \
    ubuntu tar czf /backup/agentic_data_$(date +%Y%m%d).tar.gz -C / data
  
  # Download locally
  scp -i your-key.pem ubuntu@your-instance-ip:/tmp/agentic_data_*.tar.gz .
  ```

- [ ] **Test Rollback Procedure**
  - [ ] Document how to roll back code
  - [ ] Document how to restore data from backup
  - [ ] Keep old deploy scripts

- [ ] **Create Incident Response Plan**
  - [ ] What to do if services stop
  - [ ] How to access logs
  - [ ] Who to contact for help

## ✅ Final Verification

- [ ] **All services accessible**
  - [ ] Dashboard: http://your-ip:8501
  - [ ] API: http://your-ip:8000
  - [ ] Health: curl http://your-ip:8000/health

- [ ] **Data persistence verified**
  ```bash
  # Submit job, restart container, verify job still there
  docker-compose restart
  curl http://localhost:8000/jobs
  # Should list previously submitted job
  ```

- [ ] **Logs are clean**
  ```bash
  docker-compose logs | grep -i error
  # Should return minimal or no errors
  ```

- [ ] **Performance acceptable**
  ```bash
  docker stats
  # Memory usage reasonable
  # CPU usage normal
  ```

- [ ] **Documentation reviewed**
  - [ ] DOCKER-INDEX.md ✓
  - [ ] DEPLOYMENT.md sections read ✓
  - [ ] Troubleshooting guide reviewed ✓

## 🎉 Congratulations!

Your system is now:
✓ Containerized
✓ Deployed on AWS
✓ Production-ready
✓ Backed up
✓ Monitored
✓ Documented

🚀 **You're live!**

## 📞 Quick Reference

| Issue | Solution |
|-------|----------|
| API won't respond | `docker-compose logs backend` |
| Dashboard won't load | `docker-compose ps` check status |
| Out of space | `docker system prune -a` |
| Need to restart | `docker-compose restart` |
| Lost connection | `ssh -i key.pem ubuntu@ip` reconnect |

## 📚 Further Reading

- DEPLOYMENT.md - Deep dive into AWS setup
- DOCKER-REFERENCE.md - Docker troubleshooting
- GIT-SETUP.md - Repository management
- AWS documentation on EC2, RDS, CloudWatch

---

**Deployment Date:** ___________
**Instance IP:** ___________
**Deployed By:** ___________
**Contact:** ___________

Good luck! 🚀
