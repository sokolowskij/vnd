# Git Setup for Docker Deployment

This guide ensures your repository is properly configured for Docker deployment on AWS.

## 1. Initialize Git (if needed)

```bash
cd /path/to/agentic-seller
git init
git add .
git commit -m "Initial commit: Docker deployment setup"
```

## 2. Ensure .env is NOT tracked

Add to `.gitignore` (create if it doesn't exist):

```gitignore
# Environment variables
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Data
data/
browser_profiles/
results/
*.db
*.log

# Docker volumes (local)
.container_volumes/
```

## 3. Create GitHub Repository

```bash
# If using GitHub CLI
gh repo create agentic-seller --public --source=. --remote=origin --push

# Or manually:
# 1. Go to https://github.com/new
# 2. Create repository "agentic-seller"
# 3. Add it as remote:
git remote add origin https://github.com/yourusername/agentic-seller.git
git branch -M main
git push -u origin main
```

## 4. Update deploy.sh

Open `deploy.sh` and update the repository URL:

```bash
# Find this line (~line 48)
REPO_URL="${1:-https://github.com/yourusername/agentic-your-repo.git}"

# Change to your actual repository
```

## 5. Verify Everything

```bash
# Check git status
git status
# Should show: .env (untracked, not staged)

# Check what would be committed
git diff --cached

# Verify .env is ignored
git check-ignore .env  # Should output: .env

# Push to GitHub
git push origin main
```

## 6. Ready for Deployment

Now you can use the deploy script on AWS:

```bash
# On EC2 instance:
bash <(curl -fsSL https://raw.githubusercontent.com/yourusername/agentic-seller/main/deploy.sh)

# Or with explicit repo URL:
bash <(curl -fsSL https://raw.githubusercontent.com/yourusername/agentic-seller/main/deploy.sh) \
  https://github.com/yourusername/agentic-seller.git
```

## Important Files for Deployment

✅ Tracked in Git:
- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `deploy.sh`
- `setup.py`
- `.env.example` ← Use this as template
- `requirements.txt`
- `src/agentic_seller/`
- `dashboard.py`
- `DEPLOYMENT.md`
- Documentation

❌ NOT in Git (use environment variables instead):
- `.env` ← Contains secrets!
- Local data files
- `browser_profiles/` (unless needed)

## Safe Secrets Management

### Local Development
```bash
# Create .env locally (not tracked)
cp .env.example .env
# Add your OPENAI_API_KEY
```

### AWS Deployment
```bash
# On EC2 instance
sudo nano /opt/agentic-seller/.env
# Add OPENAI_API_KEY and other secrets
# File is not tracked by git
```

### For Production (Best Practices)
1. **Use AWS Secrets Manager:**
   ```bash
   aws secretsmanager create-secret --name agentic-seller/openai-key \
     --secret-string "sk-..."
   ```

2. **Use environment variables in docker-compose:**
   ```yaml
   environment:
     - OPENAI_API_KEY=${OPENAI_API_KEY}
   ```

3. **Use IAM role for EC2 instances:**
   - Attach IAM role to EC2 instance
   - No credentials needed on instance

## Branch Protection (Optional)

On GitHub:

1. Go to Settings → Branches
2. Add branch protection rule for `main`
3. Require pull request reviews before merge
4. Require status checks to pass

```bash
# Local: Create feature branch
git checkout -b feature/new-feature
git push -u origin feature/new-feature
# Create pull request on GitHub
```

## Deployment Flow

```
Local Development:
  ✓ Make changes in feature branch
  ✓ Test with docker-compose up
  ✓ Push to GitHub
  ✓ Create pull request
  ✓ Merge to main
  ✓ Deploy to AWS

AWS Deployment:
  ✓ EC2 instance pulls from GitHub
  ✓ Reads .env from local file (secrets)
  ✓ Builds Docker images
  ✓ Starts services
  ✓ Services read environment variables
```

## Verify Git Setup

```bash
# Check repository is ready
git log --oneline | head -5

# Check remote is set
git remote -v

# Check .env is ignored
git ls-files | grep -E "\.env"
# Should show: .env.example (not .env)

# Check can clone
git clone https://github.com/yourusername/agentic-seller.git test-clone
cd test-clone
ls -la
# Should NOT see .env file
```

## After First Deployment

```bash
# On your machine, add deployment notes
git add .
git commit -m "Deployment configuration verified"
git push origin main

# Tag the deployment
git tag -a v1.0.0-docker -m "Docker deployment setup"
git push origin v1.0.0-docker
```

## Rollback Process

If deployment goes wrong:

```bash
# On AWS instance
cd /opt/agentic-seller

# Check git history
git log --oneline | head -10

# Revert to specific commit
git checkout COMMIT_HASH

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## Continuous Deployment (Optional)

Set up auto-deploy with GitHub Actions:

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to AWS
        env:
          AWS_KEY: ${{ secrets.AWS_KEY }}
          AWS_SECRET: ${{ secrets.AWS_SECRET }}
        run: |
          # Your deployment script here
          bash ./deploy-ci.sh
```

## Summary

✅ Repository structure is deployment-ready
✅ .env properly excluded from git
✅ Code pushable to GitHub
✅ Ready for deploy.sh execution
✅ Secrets managed safely
✅ Easy rollback capability

Your setup is complete! 🚀
