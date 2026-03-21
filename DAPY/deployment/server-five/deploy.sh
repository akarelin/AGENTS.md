#!/bin/bash
set -e

# DAPY Deployment Script for Server Five
# This script deploys DAPY with remote inspector service

echo "================================================"
echo "DAPY - Server Five Deployment"
echo "================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Load environment variables
source .env

# Verify required variables
if [ -z "$LANGCHAIN_API_KEY" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: Required API keys not set in .env"
    echo "Please configure LANGCHAIN_API_KEY and OPENAI_API_KEY"
    exit 1
fi

echo "✓ Environment configuration loaded"
echo ""

# Create data directories
echo "Creating data directories..."
sudo mkdir -p /data/dapy
sudo mkdir -p /data/dapy/snapshots
sudo mkdir -p /data/dapy/logs
sudo mkdir -p /data/dapy/debug-packages
sudo chown -R $USER:$USER /data/dapy
echo "✓ Data directories created"
echo ""

# Build and start services
echo "Building Docker images..."
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 5

# Check service status
echo ""
echo "Service Status:"
docker-compose ps

echo ""
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""
echo "Services:"
echo "  - DAPY: docker-compose exec dapy bash"
echo "  - Inspector: http://localhost:8888"
echo ""
echo "Data locations:"
echo "  - Snapshots: /data/dapy/snapshots"
echo "  - Logs: /data/dapy/logs"
echo "  - Debug packages: /data/dapy/debug-packages"
echo ""
echo "Usage:"
echo "  # Enter DAPY"
echo "  docker-compose exec dapy bash"
echo ""
echo "  # Inside container:"
echo "  cd /repos/your-project"
echo "  dapy next"
echo "  dapy ask 'What should I work on?'"
echo ""
echo "  # Export debug package when issues occur:"
echo "  dapy export-debug 'Description of issue'"
echo ""
echo "Inspector API:"
echo "  - Status: http://localhost:8888/api/status"
echo "  - Recent executions: http://localhost:8888/api/executions/recent"
echo "  - Create debug package: POST http://localhost:8888/api/debug-package/create"
echo ""
echo "Firewall: Ensure port 8888 is accessible for remote inspection"
echo ""
