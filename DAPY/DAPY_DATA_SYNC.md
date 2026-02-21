# DAPY Data Sync Architecture

## Problem Statement

DAPY needs access to your live data to perform tasks:
- **Git repositories:** RAN, CRAP, _, gppu (working copies, not just code)
- **Live files:** Current 2Do.md, CHANGELOG.md (not just committed versions)
- **Write access:** To update files, commit, push
- **Non-git data:** Configs, databases, logs, Google Drive files

**Current limitation:** LangChain Cloud deployment only has access to code from GitHub, not your live working data.

---

## Solution: Bidirectional Data Sync

### Architecture

```
Your Local Machine
    (sync)
DAPY Filesystem (/repos/)
    (git push/pull)
GitHub
```

### Data Flow

**Initial Setup:**
1. Clone your repos to DAPY filesystem
2. Sync non-git data from your machine
3. Configure git credentials for push access

**During Operation:**
1. You make changes locally
2. Sync pushes changes to DAPY
3. DAPY reads/writes files
4. DAPY commits and pushes to GitHub
5. You pull from GitHub to stay in sync

---

## Sync Methods

### Method 1: GitHub (Code Only)

**What it syncs:**
- Code in git repos
- NOT uncommitted changes
- NOT non-git data

**How it works:**
```bash
# DAPY clones repos
git clone https://github.com/akarelin/RAN.git /repos/RAN
git clone https://github.com/akarelin/CRAP.git /repos/CRAP
git clone https://github.com/akarelin/_.git /repos/_
git clone https://github.com/akarelin/gppu.git /repos/gppu

# Configure git for push
git config --global user.name "DAPY"
git config --global user.email "dapy@example.com"
```

**Pros:**
- Simple
- Already set up (GitHub token)
- Two-way sync via git

**Cons:**
- Only syncs committed changes
- No access to work-in-progress
- No non-git data

**Use case:** Basic testing with committed data only

### Method 2: rsync (Full Sync)

**What it syncs:**
- All files (git and non-git)
- Uncommitted changes
- Working directory state
- Bidirectional

**How it works:**
```bash
# Your machine -> DAPY
rsync -avz --delete \
  /path/to/your/repos/ \
  user@dapy-server:/repos/

# DAPY -> Your machine (after changes)
rsync -avz --delete \
  user@dapy-server:/repos/ \
  /path/to/your/repos/
```

**Setup required:**
- SSH access to DAPY server
- rsync installed on both sides
- Cron job or manual sync

**Pros:**
- Full filesystem sync
- Fast and efficient
- Bidirectional
- Preserves permissions

**Cons:**
- Requires SSH access
- Manual or scheduled sync
- Potential conflicts if both sides change

**Use case:** Full development workflow with live data

### Method 3: scp (Manual Transfer)

**What it syncs:**
- Individual files or directories
- Manual control

**How it works:**
```bash
# Upload specific files
scp /path/to/RAN/2Do.md user@dapy-server:/repos/RAN/

# Upload entire directory
scp -r /path/to/RAN/ user@dapy-server:/repos/

# Download changes
scp user@dapy-server:/repos/RAN/CHANGELOG.md /path/to/RAN/
```

**Pros:**
- Simple
- Selective sync
- No additional tools

**Cons:**
- Manual process
- Not automated
- Tedious for many files

**Use case:** Quick file transfers, testing specific changes

### Method 4: Google Drive (Cloud Storage)

**What it syncs:**
- Non-git data
- Large files
- Shared documents
- Automatic sync

**How it works:**
```bash
# Install rclone on DAPY
apt-get install rclone

# Configure Google Drive
rclone config

# Sync from Google Drive to DAPY
rclone sync gdrive:/DAPY/repos /repos/

# Sync from DAPY to Google Drive
rclone sync /repos/ gdrive:/DAPY/repos
```

**Setup required:**
- Google Drive account
- rclone configured
- OAuth credentials

**Pros:**
- Cloud-based (accessible anywhere)
- Automatic sync
- Version history
- Good for non-git data

**Cons:**
- Slower than rsync
- Requires OAuth setup
- Not ideal for git repos

**Use case:** Non-git data, configs, databases

### Method 5: Hybrid (Recommended)

**Combine methods:**
- **GitHub:** For code and git repos
- **rsync:** For live working directory sync
- **Google Drive:** For large non-git data

**How it works:**
1. Clone repos from GitHub (initial setup)
2. rsync working directory changes (frequent)
3. DAPY commits and pushes to GitHub
4. Google Drive for non-git data (as needed)

**Pros:**
- Best of all methods
- Flexible
- Efficient

**Cons:**
- More complex setup

---

## Implementation

### Option A: LangChain Cloud Deployment

**Challenge:** LangChain Cloud is serverless, no persistent filesystem or SSH access.

**Solution:** Use init container or sidecar to sync data at startup.

```yaml
# deployment/langchain-cloud/langchain.yaml
apiVersion: langchain.com/v1
kind: LangGraphApp
metadata:
  name: dapy
spec:
  initContainers:
    - name: sync-repos
      image: alpine/git
      command:
        - sh
        - -c
        - |
          git clone https://github.com/akarelin/RAN.git /repos/RAN
          git clone https://github.com/akarelin/CRAP.git /repos/CRAP
          git clone https://github.com/akarelin/_.git /repos/_
          git clone https://github.com/akarelin/gppu.git /repos/gppu

          # Configure git
          git config --global user.name "DAPY"
          git config --global user.email "dapy@example.com"
      volumeMounts:
        - name: repos
          mountPath: /repos

  volumes:
    - name: repos
      emptyDir: {}

  volumeMounts:
    - name: repos
      mountPath: /repos
```

**Limitations:**
- Only syncs at startup
- No live sync during operation
- Loses changes on restart
- Only git data (no uncommitted changes)

**Verdict:** Not ideal for live development workflow

### Option B: Server Five Deployment (Recommended)

**Advantage:** Full control over filesystem and sync.

**Setup:**
1. Deploy DAPY to server five (Docker Compose)
2. Set up rsync from your machine to server five
3. Configure bidirectional sync
4. DAPY has full access to live data

```yaml
# deployment/server-five/docker-compose.yaml
services:
  dapy:
    volumes:
      - /path/on/server-five/repos:/repos
    environment:
      - REPOS_PATH=/repos
```

**Sync script:**
```bash
#!/bin/bash
# sync-to-dapy.sh

# Sync your local repos to server five
rsync -avz --delete \
  --exclude '.git' \
  /path/to/your/repos/ \
  user@server-five:/path/on/server-five/repos/

echo "Synced to DAPY"
```

**Pros:**
- Full filesystem access
- Live sync
- Bidirectional
- Persistent storage

**Cons:**
- Requires server five setup
- Not using LangChain Cloud

**Verdict:** Best for development and testing

### Option C: Hybrid Deployment

**Approach:**
1. **Development:** Use server five with rsync
2. **Production:** Use LangChain Cloud with GitHub only

**Workflow:**
1. Test on server five with live data
2. Commit changes to GitHub
3. Deploy to LangChain Cloud for production
4. LangChain Cloud uses GitHub data only

**Pros:**
- Best of both worlds
- Live data for testing
- Managed deployment for production

**Cons:**
- Two deployment targets
- More complex

---

## Recommended Setup

### For Initial Testing (This Week)

**Use Server Five + rsync:**

1. Deploy DAPY to server five
2. Set up rsync from your machine
3. Sync repos before each test
4. DAPY has full access to live data

**Why:**
- Need live data for realistic testing
- Need write access for git operations
- Need uncommitted changes for "document" command
- Server five gives full control

### For Production (Later)

**Use LangChain Cloud + GitHub:**

1. Commit all changes to GitHub
2. Deploy to LangChain Cloud
3. DAPY works with committed data only
4. Simpler, managed deployment

**Why:**
- Production doesn't need uncommitted changes
- All data should be in git
- Managed infrastructure
- Scalable

---

## Implementation Plan

### Phase 1: Server Five Setup

**Step 1: Deploy DAPY to Server Five**
```bash
cd /path/to/dapy/deployment/server-five
./deploy.sh
```

**Step 2: Create Repos Directory**
```bash
ssh user@server-five
mkdir -p /data/dapy/repos
chown dapy:dapy /data/dapy/repos
```

**Step 3: Initial Sync**
```bash
# From your machine
rsync -avz --delete \
  ~/RAN/ \
  user@server-five:/data/dapy/repos/RAN/

rsync -avz --delete \
  ~/CRAP/ \
  user@server-five:/data/dapy/repos/CRAP/

rsync -avz --delete \
  ~/_/ \
  user@server-five:/data/dapy/repos/_/

rsync -avz --delete \
  ~/gppu/ \
  user@server-five:/data/dapy/repos/gppu/
```

**Step 4: Configure Git**
```bash
ssh user@server-five
cd /data/dapy/repos/RAN
git config user.name "DAPY"
git config user.email "dapy@example.com"

# Repeat for other repos
```

**Step 5: Test Access**
```bash
# SSH into DAPY container
docker exec -it dapy bash

# Check repos
ls -la /repos/
cat /repos/RAN/2Do.md
git -C /repos/RAN status
```

### Phase 2: Automated Sync

**Create sync script:**
```bash
#!/bin/bash
# ~/bin/sync-dapy.sh

REPOS=(RAN CRAP _ gppu)
LOCAL_BASE=~/
REMOTE_BASE=user@server-five:/data/dapy/repos

for repo in "${REPOS[@]}"; do
  echo "Syncing $repo..."
  rsync -avz --delete \
    --exclude '.git/objects' \
    --exclude '.git/logs' \
    "$LOCAL_BASE/$repo/" \
    "$REMOTE_BASE/$repo/"
done

echo "All repos synced to DAPY"
```

**Make executable:**
```bash
chmod +x ~/bin/sync-dapy.sh
```

**Run before testing:**
```bash
~/bin/sync-dapy.sh
```

### Phase 3: Bidirectional Sync

**Pull changes from DAPY:**
```bash
#!/bin/bash
# ~/bin/pull-from-dapy.sh

REPOS=(RAN CRAP _ gppu)
LOCAL_BASE=~/
REMOTE_BASE=user@server-five:/data/dapy/repos

for repo in "${REPOS[@]}"; do
  echo "Pulling $repo..."
  rsync -avz --delete \
    "$REMOTE_BASE/$repo/" \
    "$LOCAL_BASE/$repo/"
done

echo "All changes pulled from DAPY"
```

**Workflow:**
1. Make changes locally
2. Run `sync-dapy.sh`
3. DAPY runs tests
4. Run `pull-from-dapy.sh`
5. Review changes
6. Commit to git

---

## Data Organization

### Filesystem Layout on DAPY

```
/repos/
├── RAN/                    # Main repository
│   ├── 2Do.md
│   ├── ROADMAP.md
│   ├── CHANGELOG.md
│   ├── AGENTS.md
│   ├── agents/
│   └── .git/
├── CRAP/                   # Secondary repository
│   ├── DAPY/              # DAPY code
│   └── .git/
├── _/                      # Knowledge base
│   ├── KB/
│   └── .git/
└── gppu/                   # Additional repo
    └── .git/
```

### Git Configuration

**Each repo needs:**
- Git user name/email
- SSH key or token for push
- Remote configured

**Setup:**
```bash
cd /repos/RAN
git config user.name "DAPY"
git config user.email "dapy@example.com"
git remote set-url origin git@github.com:akarelin/RAN.git
```

---

## Security Considerations

### SSH Access

**Server Five needs:**
- SSH key from your machine
- Firewall rule for your IP
- User account for rsync

**Setup:**
```bash
# Generate SSH key (if needed)
ssh-keygen -t ed25519 -C "dapy-sync"

# Copy to server five
ssh-copy-id user@server-five

# Test
ssh user@server-five "echo 'Connection successful'"
```

### Git Credentials

**For push access:**
- Use SSH keys (recommended)
- Or use GitHub token

**SSH key setup:**
```bash
# On server five
ssh-keygen -t ed25519 -C "dapy@server-five"

# Add to GitHub
cat ~/.ssh/id_ed25519.pub
# Copy and add to https://github.com/settings/keys
```

### Data Privacy

**What's synced:**
- Your repos (code and data)
- Uncommitted changes
- Local configs

**Not synced:**
- .git/objects (too large, use git push/pull)
- Sensitive files (use .rsyncignore)

---

## Monitoring

### Sync Status

**Check last sync:**
```bash
ssh user@server-five "ls -la /data/dapy/repos/RAN/"
```

**Check git status:**
```bash
ssh user@server-five "git -C /data/dapy/repos/RAN status"
```

### Disk Usage

**Check space:**
```bash
ssh user@server-five "du -sh /data/dapy/repos/*"
```

---

## Troubleshooting

### Sync Conflicts

**If both sides change same file:**
1. Pull from DAPY first
2. Resolve conflicts locally
3. Sync back to DAPY

### Permission Issues

**If rsync fails:**
```bash
ssh user@server-five "chown -R dapy:dapy /data/dapy/repos"
```

### Git Push Failures

**If DAPY can't push:**
1. Check SSH key is added to GitHub
2. Check git remote URL
3. Check network access

---

## Summary

### Recommended Approach

**For testing (now):**
- Deploy to server five
- Use rsync for full sync
- DAPY has live data access

**For production (later):**
- Deploy to LangChain Cloud
- Use GitHub only
- All data committed to git

### Setup Steps

1. Deploy DAPY to server five
2. Create sync script
3. Initial rsync of all repos
4. Configure git credentials
5. Test access
6. Run tests with live data

### Maintenance

- Sync before each test session
- Pull changes after testing
- Commit changes to git
- Monitor disk usage

---

## Next Steps

1. Decide: Server five or LangChain Cloud for initial testing?
2. If server five: Provide SSH access details
3. If LangChain Cloud: Accept GitHub-only limitation
4. Set up sync mechanism
5. Test data access
6. Run 10 test cases

**Recommendation:** Start with server five for realistic testing with live data.
