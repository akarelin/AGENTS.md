#!/bin/bash
set -e

echo "🚀 DAPY - GCP Deployment Script"
echo "=========================================="

# Check if running on GCP
if ! command -v gcloud &> /dev/null; then
    echo "⚠️  Warning: gcloud CLI not found. This script is designed for GCP VMs."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker installed"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed"
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    
    if [ -f .env.example ]; then
        echo "📝 Creating .env from .env.example..."
        cp .env.example .env
        echo ""
        echo "⚠️  IMPORTANT: Please edit .env and add your API keys:"
        echo "   - LANGCHAIN_API_KEY"
        echo "   - OPENAI_API_KEY"
        echo "   - DB_PASSWORD"
        echo ""
        read -p "Press Enter when you've updated .env..."
    else
        echo "❌ .env.example not found. Please create .env manually."
        exit 1
    fi
fi

# Source environment variables
set -a
source .env
set +a

# Validate required environment variables
REQUIRED_VARS=("LANGCHAIN_API_KEY" "OPENAI_API_KEY" "DB_PASSWORD")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '   - %s\n' "${MISSING_VARS[@]}"
    echo ""
    echo "Please update .env file with these values."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data snapshots logs ssl

# Build and start services
echo "🏗️  Building DAPY..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service status
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ DAPY deployed successfully!"
    echo ""
    echo "📊 Service Status:"
    docker-compose ps
    echo ""
    echo "📝 Next Steps:"
    echo "   1. Test the deployment:"
    echo "      docker-compose exec dapy dapy version"
    echo ""
    echo "   2. Run a command:"
    echo "      docker-compose exec dapy dapy ask \"What's next?\""
    echo ""
    echo "   3. View logs:"
    echo "      docker-compose logs -f dapy"
    echo ""
    echo "   4. Access LangSmith traces:"
    echo "      https://smith.langchain.com"
    echo ""
else
    echo "❌ Deployment failed. Check logs:"
    echo "   docker-compose logs"
    exit 1
fi
