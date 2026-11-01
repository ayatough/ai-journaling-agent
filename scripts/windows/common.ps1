# Shared environment setup for the Windows launcher scripts.
# Dot-source from the other scripts: . "$PSScriptRoot\common.ps1"

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$LogDir = Join-Path $env:USERPROFILE '.ai-journaling-agent\logs'
New-Item -ItemType Directory -Force $LogDir | Out-Null

# Make sure user-level tools (uv, ngrok) are on PATH even in a bare Task Scheduler session.
$env:Path = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\ngrok'),
    [Environment]::GetEnvironmentVariable('Path', 'Machine'),
    [Environment]::GetEnvironmentVariable('Path', 'User'),
    (Join-Path $env:USERPROFILE '.local\bin'),
    (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links')
) -join ';'

# Values from .env that must be real process env vars (pydantic-settings does not export them).
function Get-DotEnvValue([string]$Name) {
    $envFile = Join-Path $RepoRoot '.env'
    if (-not (Test-Path $envFile)) { return $null }
    foreach ($line in Get-Content $envFile) {
        if ($line -match "^\s*$Name\s*=\s*(.*?)\s*$") { return $Matches[1].Trim('"').Trim("'") }
    }
    return $null
}

# Avoid inheriting a parent Claude Code session or a foreign virtualenv.
Get-ChildItem env: | Where-Object { $_.Name -like 'CLAUDE*' -or $_.Name -eq 'VIRTUAL_ENV' } |
    ForEach-Object { Remove-Item "env:$($_.Name)" }

$token = Get-DotEnvValue 'CLAUDE_CODE_OAUTH_TOKEN'
if ($token) { $env:CLAUDE_CODE_OAUTH_TOKEN = $token }

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
if (-not $env:HOST) { $env:HOST = '127.0.0.1' }

function Write-Log([string]$LogFile, [string]$Message) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Encoding utf8 -Path $LogFile -Value "[$ts] $Message"
}

function Get-LogFile([string]$Prefix) {
    Join-Path $LogDir ("{0}-{1}.log" -f $Prefix, (Get-Date -Format 'yyyyMM'))
}
