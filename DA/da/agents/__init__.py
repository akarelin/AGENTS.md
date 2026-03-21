"""DeepAgents agent registry.

Agents derived from analysis of 5,809 prompts across 10 machines:
  - orchestrator: Routes to specialists, handles general queries
  - infra: Docker + SSH + deployment (3.7% deploy + multi-machine patterns)
  - git: Git + GitHub operations (6.3% of tasks)
  - files: File management + batch ops (13.1% - largest category)
  - pipeline: Airflow + ETL (3.7% of tasks)
  - config: Dotfiles + chezmoi + cross-machine sync (4.8%)
  - debug: Error analysis + troubleshooting (7.0%)
  - research: Web search + analysis (7.6%)
"""

AGENT_TYPES = [
    "orchestrator",
    "infra",
    "git",
    "files",
    "pipeline",
    "config",
    "debug",
    "research",
]
