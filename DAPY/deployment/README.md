# DAPY Deployment Guide

This directory contains deployment configurations for three environments: GCP VM, local Docker Compose, and LangChain Cloud.

## Overview

DAPY can be deployed in multiple ways depending on your needs:

| Environment | Use Case | Complexity | Cost |
|------------|----------|------------|------|
| **Local Docker** | Development, testing | Low | Free |
| **GCP VM** | Production, self-hosted | Medium | Pay-as-you-go |
| **LangChain Cloud** | Serverless, managed | Low | Usage-based |

## Prerequisites

All deployments require:
- **LangChain API Key** - Get from [LangSmith](https://smith.langchain.com)
- **OpenAI API Key** - Get from [OpenAI Platform](https://platform.openai.com)

## Deployment Options

### 1. Local Docker Compose (Development)

Best for local development with hot reload and interactive debugging.

**Setup:**

```bash
# 1. Create .env file
cp .env.example .env

# 2. Edit .env and add your API keys
nano .env

# 3. Start development container
docker-compose up -d

# 4. Enter container
docker-compose exec dapy-dev bash

# 5. Run DAPY
dapy ask "What's next?"
```

**Features:**
- Hot reload - code changes apply immediately
- SQLite persistence - no database setup needed
- Interactive shell access
- Volume-mounted repositories

**Directory Structure:**
```
.
├── docker-compose.yml       # Development configuration
├── Dockerfile.dev          # Development image
├── .env                    # Environment variables
├── data/                   # SQLite database
├── snapshots/              # State snapshots
└── logs/                   # Application logs
```

---

### 2. GCP VM (Production)

Best for production deployment with PostgreSQL, Nginx, and SSL.

**Setup:**

```bash
# 1. Create GCP VM (Ubuntu 22.04 recommended)
gcloud compute instances create dapy-vm \
  --machine-type=e2-standard-2 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB

# 2. SSH into VM
gcloud compute ssh dapy-vm

# 3. Clone repository
git clone https://github.com/akarelin/AGENTS.md.git
cd AGENTS.md/DAPY/deployment/gcp

# 4. Configure environment
cp .env.example .env
nano .env  # Add your API keys

# 5. Run deployment script
./deploy.sh
```

**Features:**
- PostgreSQL for durable state
- Nginx reverse proxy with SSL
- Auto-restart on failure
- Health checks
- Production-ready logging

**Architecture:**
```
Internet → Nginx (443) → DAPY (8000) → PostgreSQL (5432)
```

**Post-Deployment:**

```bash
# Test deployment
docker-compose exec dapy dapy version

# Run commands
docker-compose exec dapy dapy ask "What's next?"

# View logs
docker-compose logs -f dapy

# Stop services
docker-compose down

# Update deployment
git pull
docker-compose build
docker-compose up -d
```

**SSL Certificate Setup:**

For production, replace self-signed certificates:

```bash
# Using Let's Encrypt
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

---

### 3. LangChain Cloud (Serverless)

Best for serverless deployment with automatic scaling and managed infrastructure.

**Setup:**

```bash
# 1. Install LangChain CLI
pip install langchain-cli

# 2. Login to LangChain Cloud
langchain login

# 3. Navigate to deployment directory
cd deployment/langchain-cloud

# 4. Set secrets
langchain secrets set LANGCHAIN_API_KEY your_key_here
langchain secrets set OPENAI_API_KEY your_key_here
langchain secrets set POSTGRES_CONN_STRING your_postgres_url_here

# 5. Deploy
langchain deploy
```

**Features:**
- Automatic scaling (1-5 instances)
- Managed infrastructure
- Built-in monitoring via LangSmith
- Zero DevOps overhead
- Pay only for usage

**Configuration:**

Edit `langchain.yaml` to customize:
- Resources (memory, CPU)
- Scaling parameters
- Environment variables
- Health check settings

**Monitoring:**

View deployment status and traces at:
- **Deployment Dashboard**: https://cloud.langchain.com
- **LangSmith Traces**: https://smith.langchain.com

---

## Environment Variables

All deployments use these environment variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `LANGCHAIN_API_KEY` | Yes | LangSmith API key | `lsv2_pt_...` |
| `OPENAI_API_KEY` | Yes | OpenAI API key | `sk-...` |
| `LANGCHAIN_PROJECT` | No | LangSmith project name | `dapy-prod` |
| `DAPY_MODEL` | No | Model to use | `openai:gpt-4o` |
| `PERSISTENCE_BACKEND` | No | Database backend | `sqlite` or `postgres` |
| `POSTGRES_CONN_STRING` | Conditional | PostgreSQL connection | `postgresql://...` |
| `DB_PASSWORD` | Conditional | Database password | `secure_password` |
| `REPO_PATH` | No | Path to repositories | `/home/ubuntu/repos` |

---

## Comparison Matrix

| Feature | Local Docker | GCP VM | LangChain Cloud |
|---------|-------------|---------|-----------------|
| **Setup Time** | 5 minutes | 15 minutes | 10 minutes |
| **Persistence** | SQLite | PostgreSQL | Managed DB |
| **Scaling** | Manual | Manual | Automatic |
| **SSL/HTTPS** | No | Yes | Yes |
| **Cost** | Free | ~$30/month | Usage-based |
| **Monitoring** | Basic | LangSmith | LangSmith + Cloud |
| **Maintenance** | None | Medium | None |
| **Best For** | Development | Production | Serverless |

---

## Troubleshooting

### Common Issues

**1. Container won't start**
```bash
# Check logs
docker-compose logs dapy

# Verify environment variables
docker-compose config

# Rebuild image
docker-compose build --no-cache
```

**2. Database connection failed**
```bash
# Check PostgreSQL status
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U dapy -d dapy

# Reset database
docker-compose down -v
docker-compose up -d
```

**3. API keys not working**
```bash
# Verify .env file
cat .env

# Check environment inside container
docker-compose exec dapy env | grep API_KEY
```

**4. Git operations failing**
```bash
# Verify git config is mounted
docker-compose exec dapy git config --list

# Check SSH keys
docker-compose exec dapy ls -la /root/.ssh
```

### Performance Tuning

**For GCP VM:**
- Increase machine type for more CPU/memory
- Use SSD persistent disks for better I/O
- Enable Cloud Logging for centralized logs

**For LangChain Cloud:**
- Adjust `resources.memory` and `resources.cpu` in `langchain.yaml`
- Tune `scaling.max_instances` based on load
- Monitor costs in LangChain Cloud dashboard

---

## Security Best Practices

1. **Never commit .env files** - Use `.env.example` as template
2. **Rotate API keys regularly** - Update in deployment configuration
3. **Use SSL in production** - Configure proper certificates
4. **Restrict network access** - Use firewall rules
5. **Enable audit logging** - Track all agent actions
6. **Backup databases** - Regular PostgreSQL backups

---

## Monitoring and Observability

All deployments include:
- **LangSmith Tracing** - Full agent execution visibility
- **Snapshots** - State capture at each step
- **Logs** - Structured logging to files/stdout
- **Metrics** - Tool call statistics and timing

Access traces at: https://smith.langchain.com

---

## Support

For deployment issues:
1. Check logs: `docker-compose logs -f`
2. Run diagnostics: `dapy diag`
3. Review documentation: [DAPY](https://github.com/akarelin/AGENTS.md/tree/main/DAPY)
4. Open issue: [GitHub Issues](https://github.com/akarelin/AGENTS.md/issues)

---

## Next Steps

After deployment:
1. Test with `dapy version`
2. Run `dapy ask "What's next?"`
3. Review LangSmith traces
4. Configure git repositories
5. Set up scheduled tasks (optional)
