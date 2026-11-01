# Send a check-in LINE message if one is needed now (port of scripts/run-checkin.sh).
# Scheduled every 30 minutes by register-tasks.ps1.
. "$PSScriptRoot\common.ps1"
Set-Location $RepoRoot
$log = Get-LogFile 'checkin'

$status = (& uv run checkin status 2>&1 | ForEach-Object { "$_" }) -join "`n"
if ($status -match '(?m)^(\w+) check-in needed') {
    $kind = $Matches[1]
    $prompt = if ($status -match '(?m)^Prompt: (.*)$') { $Matches[1] } else { '' }
    Write-Log $log "sending $kind check-in"
    $out = & uv run push-line --text $prompt 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { Write-Log $log "push-line failed: $($out -join ' ')"; exit 1 }
    & uv run checkin record --kind $kind --text $prompt 2>&1 | ForEach-Object { "$_" } | Out-File -Append -Encoding utf8 $log
    Write-Log $log 'done'
} elseif ($status -notmatch 'No check-in needed') {
    Write-Log $log "unexpected status output: $status"
    exit 1
}
exit 0
