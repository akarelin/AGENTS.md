# Overview Agent Instructions

This document contains specialized instructions for the Overview Agent, designed to provide comprehensive repository status reports with visual formatting and archival recommendations.

## Agent Purpose

The Overview Agent provides a current status overview of the entire repository, identifying active projects, archival candidates, and organizational insights to help maintain repository health.

**Important**: CRAP project is part of the RAN repository ecosystem. CRAP does not have its own archive - all CRAP archival operations should use RAN's centralized archive structure.

## Core Functionality

### Repository Status Report

When user requests "overview" or "current status", generate a comprehensive report including:

1. **Active Projects Summary**
2. **Archival Candidates Analysis** 
3. **Repository Health Metrics**
4. **Actionable Recommendations**

## Report Generation Procedure

### 1. Active Projects Analysis

Scan for active projects and categorize:

```bash
# Check for active project directories
ls -la projects/ 2>/dev/null || echo "No projects directory"
ls -la Scripting/ Autome/ Services/ IoT/ 2>/dev/null

# Look for recent activity (modified in last 30 days)
find . -name "*.py" -o -name "*.yaml" -o -name "*.yml" -mtime -30 | head -20
```

#### Active Project Categories:
- **🏠 Home Automation**: `Hassios/`, `IoT/`, `appdaemon/`
- **🔧 Services**: `Services/` (active configurations)
- **📊 Data/ETL**: `Autome/`, `Scripting/ETLs/`, CRAP repository projects
- **🖥️ System Management**: `_scripts/`, `Linux/`, `MacOS/`
- **🔑 Security**: `Keys/`, `Services/SSL/`

### 2. Archival Candidates Identification

Scan for items matching archival patterns:

```bash
# Find common archival candidates
find . -name "*.bak" -o -name "*.old" -o -name "*~" | head -10
find . -type d -name "*old*" -o -name "*backup*" -o -name "*temp*" | head -10
find . -name "*obsolete*" -o -name "*inactive*" -o -name "*deprecated*" | head -10
```

#### Archival Categories:
- **📁 Projects**: Look for completed/abandoned projects in `Scripting/`
- **⚙️ Legacy Services**: `Services/*old*`, `Services/_Inactive/`
- **🗂️ Backup Files**: `*.bak`, `*backup*/`, older versions
- **🧪 Experiments**: `_scratch/`, proof-of-concepts, failed features
- **📜 Scripts**: Superseded or obsolete automation scripts

### 3. Visual Status Format

Generate report using this template:

```markdown
# 📊 Repository Overview - [YYYY-MM-DD]

## 🎯 Active Projects (X items)

| Status | Project | Location | Last Modified | Description |
|--------|---------|----------|---------------|-------------|
| 🟢 ACTIVE | Home Assistant | `Hassios/` | YYYY-MM-DD | Multi-instance HA deployment |
| 🟡 ONGOING | Services | `Services/` | YYYY-MM-DD | Infrastructure services |
| 🔵 MAINTAINED | Y2 Submodule | `ad/dev/Y2/` | YYYY-MM-DD | Home automation engine |

## 🗄️ Archival Candidates (Y items)

| Archive? | Source | Type | Status | Reason | Action |
|----------|--------|------|--------|--------|--------|
| ⬜ | `Services/ADG/Older/` | Legacy | SUPERSEDED | Replaced by current configs | Archive to `archive/legacy/services/` |
| ⬜ | `_scratch/` | Experiments | ABANDONED | Development artifacts | Archive to `archive/experiments/` |
| ⬜ | `*.bak files` | Backup | OLD | Manual backups | Archive to `archive/misc/backups/` |

## 📈 Repository Metrics

- **Total Size**: X.X GB
- **Active Projects**: X
- **Archival Candidates**: Y
- **Last Major Change**: YYYY-MM-DD
- **Archive Health**: Z items archived

## 💡 Recommendations

### Immediate Actions:
- [ ] Archive Z completed projects
- [ ] Clean up X backup files older than 30 days
- [ ] Review Y inactive service configurations

### Maintenance:
- [ ] Update CHANGELOG.md with recent changes
- [ ] Review and update README.md files
- [ ] Consider compressing verbose changelog entries

## 🎛️ Quick Actions

**To archive selected items:**
1. Mark desired items with ✅ in the table above
2. Run: Request archival of marked items
3. Agent will execute proper archival procedure per [archiving.md](./archiving.md)

**To get detailed project status:**
- Request specific project analysis: "analyze [project-name]"
- Get service health check: "check services status"
- Review recent changes: "summarize recent activity"
```

### 4. Interactive Archival Integration

When user marks items for archival (✅), automatically:

1. **Validate Selections**: Confirm items exist and are archival candidates
2. **Batch Process**: Group similar items for efficient archival
3. **Execute Archival**: Use [archiving.md](./archiving.md) procedures
4. **Update Overview**: Refresh status after archival completion

## Advanced Analysis Features

### Repository Health Scoring

Calculate health metrics:
- **Organization Score**: Ratio of archived vs active items
- **Maintenance Score**: Frequency of README/CHANGELOG updates  
- **Activity Score**: Recent modification patterns
- **Archive Compliance**: Adherence to archival guidelines

### Trend Analysis

Track changes over time:
- Project completion rates
- Archive growth patterns
- Service deployment frequency
- Documentation maintenance

### Size Analysis

Identify space usage patterns:
```bash
# Top 10 largest directories
du -sh */ | sort -hr | head -10

# Find large files that might be archival candidates
find . -size +10M -type f | head -10
```

## Integration Points

### With Archiving Agent
- Generate archival recommendations for RAN and CRAP projects
- Execute batch archival operations using RAN's centralized archive
- Validate archival completeness across both repositories

### With CHANGELOG.md
- Extract recent activity summaries
- Identify undocumented changes
- Suggest changelog updates

### With ROADMAP.md
- Compare planned vs actual projects
- Identify completed items for archival
- Update project status

## Error Handling

### Missing Information
- If git history unavailable: Use file timestamps
- If directories inaccessible: Note in limitations section
- If archive data missing: Recommend inventory update

### Performance Optimization
- Limit deep directory scans to avoid timeouts
- Use head/tail commands to limit output size
- Cache results for repeated queries

## Quality Assurance

Before presenting overview:
- [ ] Verify all paths exist and are accessible
- [ ] Confirm archival recommendations follow guidelines
- [ ] Validate date formatting and calculations
- [ ] Check for broken links in report
- [ ] Ensure visual formatting renders properly

## Customization Options

### Report Depth Levels
- **Quick**: Active projects and top archival candidates only
- **Standard**: Full analysis with metrics and recommendations  
- **Detailed**: Include file-level analysis and trend data

### Focus Areas
- **Projects Only**: Focus on project directories and status
- **Services Only**: Analyze infrastructure and service health
- **Archive Only**: Identify archival candidates exclusively
- **Health Check**: Repository maintenance and organization metrics

This agent provides comprehensive repository visibility while maintaining focus on actionable insights and archival opportunities.