#!/bin/bash
# 🚀 FileDrop Scaling Setup Script (Ubuntu VPS) - Global Debug LOGS Mode

# Redirect ALL output to a log file on critical nodes
exec > /root/deploy_docker.log 2>&1

# 🛠️ Fix PATH for Snap/Other installations
export PATH=$PATH:/usr/bin:/usr/local/bin:/snap/bin
export DEBIAN_FRONTEND=noninteractive

echo "----------------------------------------"
echo "   FileDrop Node Bootstrap Service       "
echo "----------------------------------------"

# 0. Heal Interrupted dpkg state
echo "[0/4] Healing packager locks..."
export DEBIAN_FRONTEND=noninteractive
dpkg --configure -a

# 1. Update System
echo "[1/4] Updating server packages..."
apt-get update

# 2. Install Docker & Utilities
echo "[2/4] Installing Docker and Docker Compose..."
apt-get install -y docker.io docker-compose

# 4. Create bucket volume path and Launch
echo "[4/4] Building and launching Application Stack..."
if [ -f "docker-compose.yml" ]; then
    docker-compose down
    docker-compose up -d --build
else
    echo "❌ ERROR: docker-compose.yml not found in current directory!"
fi

echo "--- CONTAINERS ---"
docker ps

echo "--- FLASK LOGS ---"
docker logs filedrop-flask

echo "✅ SCRIPT FINISHED!"
