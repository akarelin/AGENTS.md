# Pre-rewrite per-host sync for Windows. Scans USERPROFILE + all lettered drive mounts (incl. DevDrive).
# Usage: powershell.exe -File sync-host.ps1 -Repos "repo1,repo2,..." [-Owner akarelin]
param(
  [Parameter(Mandatory=$true)][string]$Repos,
  [string]$Owner = 'akarelin'
)

$RepoList = $Repos -split ','
$Host_ = $env:COMPUTERNAME
$Stamp = Get-Date -Format 'yyyy-MM-dd'

function Log($msg) { Write-Host "[$Host_] $msg" }

$Roots = @($env:USERPROFILE)
Get-Partition | ForEach-Object {
  foreach ($ap in ($_.AccessPaths | Where-Object { $_ -match '^[A-Z]:\\' -and $_ -notmatch 'Volume\{' })) {
    $Roots += $ap.TrimEnd('\')
  }
}
$Roots = $Roots | Select-Object -Unique

function Sync-Clone($wd, $repo) {
  Push-Location $wd
  try {
    $branch = (git symbolic-ref --short HEAD 2>$null)
    if (-not $branch) { Log "SKIP  $repo  $wd  (detached HEAD)"; return }
    $dirty = git status --porcelain 2>$null
    if ($dirty) {
      $n = ($dirty -split "`n").Count
      Log "DIRTY $repo  $wd  ($n files)"
      git add -A 2>&1 | Out-Null
      $name = (git config user.name); if (-not $name) { $name = 'Auto' }
      $email = (git config user.email); if (-not $email) { $email = 'auto@local' }
      git -c user.name="$name" -c user.email="$email" commit -m "auto: pre-rewrite snapshot $Stamp" 2>&1 | Out-Null
      if ($LASTEXITCODE -ne 0) { Log "FAIL  $repo  $wd  commit"; return }
      Log "COMMIT $repo  $wd"
    }
    git -c fetch.recurseSubmodules=no fetch origin 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Log "FAIL  $repo  $wd  fetch"; return }
    $upstream = git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>$null
    if (-not $upstream) { Log "SKIP  $repo  $wd  no upstream on $branch"; return }
    $rebaseOut = git pull --rebase 2>&1
    if ($LASTEXITCODE -ne 0) { Log "FAIL  $repo  $wd  pull --rebase: $rebaseOut"; return }
    $ahead = [int](git rev-list --count "$upstream..HEAD" 2>$null)
    if ($ahead -gt 0) {
      git push 2>&1 | Out-Null
      if ($LASTEXITCODE -ne 0) { Log "FAIL  $repo  $wd  push"; return }
      Log "PUSH  $repo  $wd  $ahead commits -> $upstream"
    }
    Log "OK    $repo  $wd  clean on $branch"
  } finally { Pop-Location }
}

foreach ($root in $Roots) {
  if (-not (Test-Path $root)) { continue }
  Get-ChildItem -Path $root -Recurse -Force -Depth 4 -Directory -Filter '.git' -ErrorAction SilentlyContinue | ForEach-Object {
    $wd = $_.Parent.FullName
    $url = git -C $wd config --get remote.origin.url 2>$null
    if (-not $url) { return }
    foreach ($repo in $RepoList) {
      if ($url -like "*$Owner/$repo.git*" -or $url -like "*$Owner/$repo") { Sync-Clone $wd $repo; break }
    }
  }
}
Log "done."
