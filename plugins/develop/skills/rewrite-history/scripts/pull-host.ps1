# Post-force-push per-host pull for Windows. Resets matching clones to origin/<current branch>.
# Usage: powershell.exe -File pull-host.ps1 -Repos "repo1,..." [-Owner akarelin]
param(
  [Parameter(Mandatory=$true)][string]$Repos,
  [string]$Owner = 'akarelin'
)

$RepoList = $Repos -split ','
$Host_ = $env:COMPUTERNAME
function Log($msg) { Write-Host "[$Host_] $msg" }

$Roots = @($env:USERPROFILE)
Get-Partition | ForEach-Object {
  foreach ($ap in ($_.AccessPaths | Where-Object { $_ -match '^[A-Z]:\\' -and $_ -notmatch 'Volume\{' })) {
    $Roots += $ap.TrimEnd('\')
  }
}
$Roots = $Roots | Select-Object -Unique

function Pull-Clone($wd, $repo) {
  Push-Location $wd
  try {
    $branch = (git symbolic-ref --short HEAD 2>$null)
    if (-not $branch) { Log "SKIP  $repo  $wd  (detached HEAD)"; return }
    $dirty = git status --porcelain 2>$null
    if ($dirty) {
      $n = ($dirty -split "`n").Count
      Log "SKIP  $repo  $wd  DIRTY ($n files)"; return
    }
    $fout = git -c fetch.recurseSubmodules=no fetch origin --prune --prune-tags --tags --force 2>&1
    if ($LASTEXITCODE -ne 0) { Log "FAIL  $repo  $wd  fetch: $fout"; return }
    $upstream = git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>$null
    if (-not $upstream) { Log "SKIP  $repo  $wd  no upstream on $branch"; return }
    $before = git rev-parse HEAD 2>$null
    git reset --hard $upstream 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Log "FAIL  $repo  $wd  reset"; return }
    $after = git rev-parse HEAD 2>$null
    if ((Test-Path "$wd\.gitattributes") -and ((git lfs env 2>$null) -ne $null)) {
      git lfs pull 2>&1 | Out-Null
    }
    if ($before -eq $after) {
      Log "SAME  $repo  $wd  at $upstream ($($after.Substring(0,8)))"
    } else {
      Log "OK    $repo  $wd  $($before.Substring(0,8)) -> $($after.Substring(0,8)) on $branch"
    }
  } finally { Pop-Location }
}

foreach ($root in $Roots) {
  if (-not (Test-Path $root)) { continue }
  Get-ChildItem -Path $root -Recurse -Force -Depth 4 -Directory -Filter '.git' -ErrorAction SilentlyContinue | ForEach-Object {
    $wd = $_.Parent.FullName
    $url = git -C $wd config --get remote.origin.url 2>$null
    if (-not $url) { return }
    foreach ($repo in $RepoList) {
      if ($url -like "*$Owner/$repo.git*" -or $url -like "*$Owner/$repo") { Pull-Clone $wd $repo; break }
    }
  }
}
Log "done."
