$ErrorActionPreference = 'Stop'
$src = Split-Path -Parent $MyInvocation.MyCommand.Path
$dst = Join-Path $HOME '.claude\skills\session-manager'

New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item "$src\SKILL.md" -Destination $dst -Force
Copy-Item "$src\claude_session_manager.py" -Destination $dst -Force
Copy-Item "$src\claude_session_map.json" -Destination $dst -Force
Copy-Item "$src\plugin.json" -Destination $dst -Force

Write-Host "Installed to $dst"
