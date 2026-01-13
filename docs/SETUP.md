# Development Setup Guide

Complete setup instructions for the aws2openstack development environment.

## Prerequisites

- **macOS, Linux, or Windows** (WSL2 recommended for Windows)
- **Python 3.12+**
- **Git**
- **Docker** (for Serena MCP server)
- **Node.js 18+** (for GitHub MCP server)

---

## 1. Clone Repository

```bash
git clone https://github.com/scholih/aws2openstack.git
cd aws2openstack
```

After cloning, you'll have:
- `.beads/` - Pre-configured issue database with 18 Phase 2 tasks
- `.claude/` - Claude project settings
- `pyproject.toml` - Python dependencies

---

## 2. Python Environment

### Create Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Install Dependencies

```bash
# Install project with dev dependencies
pip install -e ".[dev]"

# Verify installation
aws2openstack --version
pytest --version
mypy --version
```

### Verify Installation

```bash
# Run tests
pytest

# Type check
mypy src/

# Lint
ruff check src/ tests/
```

---

## 3. Claude Desktop + MCP Servers

### Install Claude Desktop

Download from: https://claude.ai/download

### Configure MCP Servers

Create or edit the Claude Desktop configuration file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Linux:** `~/.config/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### Get GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (Full control of private repositories)
   - `read:org` (Read org and team membership)
4. Copy the token

### Configuration File

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    },
    "serena": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/Users/YOUR_USERNAME/repos:/workspace",
        "ghcr.io/emcie-co/serena:latest"
      ]
    }
  }
}
```

**Important:** Replace:
- `ghp_your_token_here` with your actual GitHub token
- `/Users/YOUR_USERNAME/repos` with your actual repos directory path

### Verify MCP Servers

1. Restart Claude Desktop
2. Open a new conversation
3. Check for MCP server indicators in the UI
4. Try: "Using Serena, list files in the aws2openstack project"

---

## 4. Beads Issue Tracker

### Install Beads CLI

```bash
pip install beads-project
```

Or download binary from: https://github.com/beadsprog/beads/releases

### Verify Installation

```bash
# Check version
bd --version

# View issues (should show 18 Phase 2 tasks)
bd list

# View ready work (no blockers)
bd ready

# View project stats
bd stats
```

### Beads Workflow

```bash
# View issue details
bd show aws2openstack-tae

# Start working on an issue
bd update aws2openstack-tae --status in_progress

# View dependencies
bd show aws2openstack-tae | grep -A 5 "Depends on"

# Mark complete when done
bd update aws2openstack-tae --status closed
```

### Beads Daemon

Beads runs a background daemon for performance. It starts automatically on first use.

```bash
# Check daemon status
bd daemon status

# Stop daemon (if needed)
bd daemon stop

# Restart daemon
bd daemon start
```

---

## 5. Superpowers Skills

### Install Superpowers Marketplace

```bash
# Create Claude plugins directory
mkdir -p ~/.claude/plugins/cache

# Clone superpowers marketplace
cd ~/.claude/plugins/cache
git clone https://github.com/coleridge-ai/superpowers-marketplace.git

# Create skills symlink
mkdir -p ~/.claude/skills
ln -s ~/.claude/plugins/cache/superpowers-marketplace/superpowers ~/.claude/skills/superpowers
```

### Verify Installation

```bash
# Check directory structure
ls -la ~/.claude/skills/superpowers/

# Should see directories like:
# brainstorming/
# test-driven-development/
# systematic-debugging/
# code-reviewer/
# etc.
```

### Using Skills in Claude

In Claude Desktop, use the `Skill` tool:

```
Use the superpowers:brainstorming skill to refine this idea
```

Or via slash commands (if configured):
```
/brainstorm
```

---

## 6. AWS Credentials

### Set Up AWS Profile

```bash
# Configure AWS CLI (if not already done)
aws configure --profile my-aws-profile

# Or manually edit ~/.aws/credentials
nano ~/.aws/credentials
```

Add your credentials:

```ini
[my-aws-profile]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-east-1
```

### Test AWS Access

```bash
# Test Glue permissions
aws glue get-databases --region us-east-1 --profile my-aws-profile
```

### Required IAM Permissions

Your AWS user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabases",
        "glue:GetTables",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 7. PostgreSQL (Optional - Phase 2)

Phase 2 requires PostgreSQL for persistence layer.

### macOS (Homebrew)

```bash
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb aws2openstack
```

### Linux (Ubuntu/Debian)

```bash
sudo apt-get install postgresql-15
sudo systemctl start postgresql

# Create database
sudo -u postgres createdb aws2openstack
```

### Docker

```bash
docker run -d \
  --name aws2openstack-postgres \
  -e POSTGRES_DB=aws2openstack \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15
```

### Test Connection

```bash
# Set connection string
export DATABASE_URL="postgresql://user:password@localhost:5432/aws2openstack"

# Test with psql
psql $DATABASE_URL -c "SELECT version();"
```

---

## 8. Development Workflow

### Daily Workflow

```bash
# 1. Activate environment
cd aws2openstack
source .venv/bin/activate

# 2. Sync with main
git pull origin main

# 3. Check ready work
bd ready

# 4. Create feature branch
git checkout -b feature/your-feature-name

# 5. Start working on an issue
bd update <issue-id> --status in_progress

# 6. Work with Claude Desktop
# - Use Serena MCP for semantic code navigation
# - Use GitHub MCP for repository operations
# - Use Superpowers skills for structured workflows

# 7. Run tests frequently
pytest
mypy src/

# 8. Commit when ready
git add .
git commit -m "feat: your feature description"

# 9. Push and create PR
git push origin feature/your-feature-name
gh pr create
```

### Using Claude Effectively

**With Serena (semantic code navigation):**
```
Show me the GlueCatalogAssessor class
Find all references to migration_readiness
Rename the method list_databases to get_databases
```

**With GitHub MCP:**
```
Create a PR for the current branch
List open issues in this repository
Search code for "transformation pipeline"
```

**With Superpowers:**
```
Use superpowers:brainstorming to design the transformation engine
Use superpowers:test-driven-development to implement table classification
Use superpowers:code-reviewer to review my last commit
```

---

## 9. Troubleshooting

### Claude Desktop Can't Find MCP Servers

**Check logs:**
- macOS: `~/Library/Logs/Claude/mcp*.log`
- Linux: `~/.config/Claude/logs/mcp*.log`

**Common fixes:**
- Restart Claude Desktop
- Verify JSON syntax in `claude_desktop_config.json`
- Check Docker is running (for Serena)
- Verify GitHub token has correct permissions

### Beads Daemon Issues

```bash
# Stop daemon
bd daemon stop

# Delete socket file
rm .beads/bd.sock

# Restart
bd daemon start
```

### Python Import Errors

```bash
# Reinstall in editable mode
pip install -e ".[dev]"

# Verify installation
python -c "import aws2openstack; print(aws2openstack.__version__)"
```

### Docker Permission Errors (Linux)

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then test
docker run hello-world
```

---

## 10. Next Steps

After setup is complete:

1. **Read the design docs:**
   ```bash
   cat docs/plans/2026-01-09-persistence-mcp-dashboard-design.md
   ```

2. **Review Phase 1 code:**
   ```bash
   # Explore with Serena in Claude
   "Show me the structure of src/aws2openstack/"
   ```

3. **Check Phase 2 tasks:**
   ```bash
   bd list --format=table
   bd show aws2openstack-tae
   ```

4. **Run a test assessment (if you have AWS access):**
   ```bash
   aws2openstack assess glue-catalog \
     --region us-east-1 \
     --profile my-profile \
     --output-dir ./test-assessment
   ```

5. **Join the conversation:**
   - Review the README
   - Explore the codebase
   - Pick an issue from `bd ready`
   - Start contributing!

---

## Additional Resources

- **Claude Desktop:** https://claude.ai/download
- **MCP Documentation:** https://modelcontextprotocol.io/
- **Serena MCP:** https://github.com/emcie-co/serena
- **Beads:** https://github.com/beadsprog/beads
- **Superpowers:** https://github.com/coleridge-ai/superpowers-marketplace
- **Project Design:** `docs/plans/2026-01-09-persistence-mcp-dashboard-design.md`
