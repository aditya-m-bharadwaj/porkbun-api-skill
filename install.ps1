# porkbun-api-skill installer for Windows (PowerShell 5.1+).
#
# Usage from a cloned checkout:
#   .\install.ps1
#
# One-liner (after the repo is published):
#   iwr -useb https://raw.githubusercontent.com/aditya-m-bharadwaj/porkbun-api-skill/main/install.ps1 | iex
#
# Env vars:
#   $env:PORKBUN_CTL_PREFIX  target dir for the shim   (default: $env:LOCALAPPDATA\porkbun-api-skill\bin)
#   $env:PORKBUN_CTL_HOME    where to clone the repo   (default: $env:LOCALAPPDATA\porkbun-api-skill\src)
#   $env:PORKBUN_CTL_REPO    git URL                   (default: aditya-m-bharadwaj/porkbun-api-skill placeholder)
#   $env:PORKBUN_CTL_REF     branch/tag/SHA            (default: main)
#   $env:INSTALL_SKILL       1 to install Claude skill (default: 0)
#   $env:RUN_SETUP           1 to run setup now        (default: 0)
#
# STATUS: this script is a SKELETON. It parallels `linode-api-skill/install.ps1`
# and has not been smoke-tested end-to-end.

$ErrorActionPreference = "Stop"

$DefaultRepo = "https://github.com/aditya-m-bharadwaj/porkbun-api-skill.git"

$Prefix = if ($env:PORKBUN_CTL_PREFIX) { $env:PORKBUN_CTL_PREFIX } else { Join-Path $env:LOCALAPPDATA "porkbun-api-skill\bin" }
$HomeDir = if ($env:PORKBUN_CTL_HOME) { $env:PORKBUN_CTL_HOME } else { Join-Path $env:LOCALAPPDATA "porkbun-api-skill\src" }
$RepoUrl = if ($env:PORKBUN_CTL_REPO) { $env:PORKBUN_CTL_REPO } else { $DefaultRepo }
$Ref = if ($env:PORKBUN_CTL_REF) { $env:PORKBUN_CTL_REF } else { "main" }

function Write-Info($m) { Write-Host "[install] $m" -ForegroundColor Cyan }
function Write-Warn($m) { Write-Host "[warn]    $m" -ForegroundColor Yellow }
function Die($m)        { Write-Host "[error]   $m" -ForegroundColor Red; exit 1 }

# --- Source dir
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path (Join-Path $ScriptDir "bin\porkbun-api-skill")) {
    $SourceDir = $ScriptDir
    Write-Info "Using current checkout: $SourceDir"
} else {
    Write-Info "Cloning $RepoUrl -> $HomeDir (ref=$Ref)"
    New-Item -ItemType Directory -Force -Path (Split-Path $HomeDir) | Out-Null
    if (Test-Path (Join-Path $HomeDir ".git")) {
        Push-Location $HomeDir
        git fetch --quiet
        git checkout --quiet $Ref
        git pull --quiet --ff-only
        Pop-Location
    } else {
        git clone --quiet --depth 1 --branch $Ref $RepoUrl $HomeDir
        if ($LASTEXITCODE -ne 0) { Die "git clone failed (is the repo published yet?)" }
    }
    $SourceDir = $HomeDir
}

# --- Verify Python 3.8+
$Python = $null
foreach ($cand in @("python", "python3", "py")) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) {
        try {
            & $cand -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { $Python = $cand; break }
        } catch {}
    }
}
if (-not $Python) { Die "Python 3.8+ not found." }
Write-Info "Python: $Python ($(& $Python --version 2>&1))"

# --- Create .cmd shim
New-Item -ItemType Directory -Force -Path $Prefix | Out-Null
$ShimPath = Join-Path $Prefix "porkbun-api-skill.cmd"
$Target = Join-Path $SourceDir "bin\porkbun-api-skill"
@"
@echo off
"$Python" "$Target" %*
"@ | Set-Content -Encoding ASCII $ShimPath
Write-Info "Created shim: $ShimPath -> $Python $Target"

# --- PATH note
if (-not ($env:Path -split ";" -contains $Prefix)) {
    Write-Warn "$Prefix is not on your PATH for this session."
    Write-Warn "Add it permanently: [Environment]::SetEnvironmentVariable('Path', `"$env:Path;$Prefix`", 'User')"
}

# --- Optional skill install
if ($env:INSTALL_SKILL -eq "1") {
    $SkillDir = Join-Path $env:USERPROFILE ".claude\skills\porkbun-api-skill"
    New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null
    Copy-Item -Force (Join-Path $SourceDir ".claude\skills\porkbun-api-skill\SKILL.md") $SkillDir
    Write-Info "Skill installed at: $SkillDir\SKILL.md"
}

# --- Optional setup
if ($env:RUN_SETUP -eq "1" -and -not $env:NO_SETUP) {
    & $Python $Target setup
}

Write-Info ""
Write-Info "Installed. Next steps:"
Write-Info "  1. porkbun-api-skill setup        # paste your API key pair (hidden input)"
Write-Info "  2. porkbun-api-skill whoami       # verify auth"
Write-Info "  - To change credentials later: porkbun-api-skill setup"
Write-Info "  - To remove credentials:       porkbun-api-skill uninstall-credentials --yes"
Write-Info "  - Read: $SourceDir\README.md"
