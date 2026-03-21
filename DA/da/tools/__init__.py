"""DeepAgents tools — maps to real tools from Claude Code usage patterns.

Tool selection based on analysis of 5,809 prompts across 10 machines:
  Bash(docker): 926  -> docker_tools
  Bash(ssh):    786  -> ssh_tools
  Bash(git):    757  -> git_tools
  Bash(gh):     345  -> github_tools
  Bash(python): 612  -> python_tools
  Bash(chezmoi):121  -> config_tools
  Read/Edit:   7945  -> file_tools
  Grep/Glob:   1618  -> search_tools
"""

from da.tools.shell import shell_tool_defs, execute_shell_tool
from da.tools.git import git_tool_defs, execute_git_tool
from da.tools.docker import docker_tool_defs, execute_docker_tool
from da.tools.ssh import ssh_tool_defs, execute_ssh_tool
from da.tools.files import file_tool_defs, execute_file_tool
from da.tools.search import search_tool_defs, execute_search_tool

ALL_TOOL_DEFS = (
    shell_tool_defs
    + git_tool_defs
    + docker_tool_defs
    + ssh_tool_defs
    + file_tool_defs
    + search_tool_defs
)

EXECUTORS = {
    **{t["name"]: execute_shell_tool for t in shell_tool_defs},
    **{t["name"]: execute_git_tool for t in git_tool_defs},
    **{t["name"]: execute_docker_tool for t in docker_tool_defs},
    **{t["name"]: execute_ssh_tool for t in ssh_tool_defs},
    **{t["name"]: execute_file_tool for t in file_tool_defs},
    **{t["name"]: execute_search_tool for t in search_tool_defs},
}


def execute_tool(name: str, inputs: dict) -> str:
    """Route tool call to the right executor."""
    executor = EXECUTORS.get(name)
    if not executor:
        return f"Unknown tool: {name}"
    return executor(name, inputs)
