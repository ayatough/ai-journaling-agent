# Send the check-in due now (if any) to OWNER_USER_ID.
# Scheduled every 30 minutes by register-tasks.ps1. All logic lives in `checkin run`.
. "$PSScriptRoot\common.ps1"
Set-Location $RepoRoot
$log = Get-LogFile 'checkin'

$out = & uv run checkin run 2>&1 | ForEach-Object { "$_" }
$code = $LASTEXITCODE
$text = ($out -join ' ').Trim()
if ($code -ne 0) { Write-Log $log "checkin run failed ($code): $text"; exit 1 }
if ($text -notmatch 'No check-in needed') { Write-Log $log $text }
exit 0
