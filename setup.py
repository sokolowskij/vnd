#!/usr/bin/env python3
"""
AWS Deployment Helper for Agentic Seller
Generates environment configuration and deployment checks
"""

import os
import sys
from pathlib import Path
from getpass import getpass


def print_header(text):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def print_step(number, text):
    print(f"[{number}/4] {text}")


def validate_env():
    """Check if .env file exists and is valid"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("⚠️  .env file not found!")
        return False
    
    # Read and validate
    env_vars = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
    
    if not env_vars.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set in .env")
        return False
    
    return True


def setup_env():
    """Interactive environment setup"""
    print_step(1, "Environment Configuration")
    
    env_path = Path(".env")
    
    if env_path.exists():
        response = input("✓ .env exists. Update it? (y/n): ").lower()
        if response != "y":
            return
    
    # Collect settings
    print("\nPlease provide your settings:")
    
    openai_key = getpass("OpenAI API Key: ")
    if not openai_key.startswith("sk-"):
        print("⚠️  API key should start with 'sk-'")
    
    openai_model = input("OpenAI Model [gpt-4o-mini]: ").strip() or "gpt-4o-mini"
    
    post_mode = input("Post Mode - dry_run or publish [dry_run]: ").strip() or "dry_run"
    
    headless = input("Headless Mode [true]: ").strip().lower() or "true"
    
    currency = input("Default Currency [PLN]: ").strip() or "PLN"
    
    enable_olx = input("Enable OLX [true]: ").strip().lower() or "true"
    enable_fb = input("Enable Facebook [true]: ").strip().lower() or "true"
    
    # Write .env
    env_content = f"""# Agentic Seller Configuration
OPENAI_API_KEY={openai_key}
OPENAI_MODEL={openai_model}
DEFAULT_CURRENCY={currency}
POST_MODE={post_mode}
HEADLESS={headless}
ENABLE_OLX={enable_olx}
ENABLE_FACEBOOK={enable_fb}
USER_DATA_DIR=/app/data/browser_profiles

# Docker API Configuration
API_HOST=0.0.0.0
API_PORT=8000
STREAMLIT_PORT=8501
"""
    
    env_path.write_text(env_content)
    print(f"\n✅ .env saved to {env_path}")


def check_docker():
    """Check if Docker and Docker Compose are installed"""
    print_step(2, "Docker Installation Check")
    
    # Check Docker
    docker_check = os.system("docker --version > /dev/null 2>&1")
    if docker_check == 0:
        print("✅ Docker is installed")
    else:
        print("❌ Docker not found. Install from https://docs.docker.com/get-docker/")
        return False
    
    # Check Docker Compose
    compose_check = os.system("docker-compose --version > /dev/null 2>&1")
    if compose_check == 0:
        print("✅ Docker Compose is installed")
    else:
        print("⚠️  Docker Compose v2 not found. Install from https://docs.docker.com/compose/install/")
        return False
    
    return True


def build_images():
    """Build Docker images"""
    print_step(3, "Building Docker Images")
    
    response = input("Build Docker images now? (y/n): ").lower()
    if response != "y":
        return True
    
    print("\nBuilding backend image...")
    backend_result = os.system("docker-compose build backend")
    
    print("\nBuilding frontend image...")
    frontend_result = os.system("docker-compose build frontend")
    
    if backend_result == 0 and frontend_result == 0:
        print("\n✅ Docker images built successfully")
        return True
    else:
        print("\n❌ Build failed")
        return False


def start_services():
    """Start Docker Compose services"""
    print_step(4, "Starting Services")
    
    response = input("Start services now? (y/n): ").lower()
    if response != "y":
        return
    
    print("\nStarting services with docker-compose up -d...")
    result = os.system("docker-compose up -d")
    
    if result == 0:
        print("\n✅ Services started!")
        print("\nWaiting for services to be ready...")
        os.system("sleep 5")
        os.system("docker-compose ps")
        
        print("\n" + "=" * 60)
        print("📍 Access your services:")
        print("   Backend API:  http://localhost:8000")
        print("   Dashboard:    http://localhost:8501")
        print("=" * 60)
    else:
        print("\n❌ Failed to start services")


def main():
    """Main setup workflow"""
    print_header("Agentic Seller - Docker Deployment Setup")
    
    # Step 1: Environment
    setup_env()
    
    if not validate_env():
        print("\n❌ Environment validation failed")
        sys.exit(1)
    
    # Step 2: Docker check
    if not check_docker():
        print("\n❌ Docker not available")
        sys.exit(1)
    
    # Step 3: Build
    if not build_images():
        print("\n⚠️  Continuing anyway...")
    
    # Step 4: Start
    start_services()
    
    print_header("Setup Complete!")
    print("Next steps:")
    print("1. Open http://localhost:8501 in your browser")
    print("2. Submit a job from the dashboard")
    print("3. For production AWS deployment, see DEPLOYMENT.md")
    print("\nUseful commands:")
    print("  docker-compose ps          # Check service status")
    print("  docker-compose logs -f     # View live logs")
    print("  docker-compose down        # Stop services")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
