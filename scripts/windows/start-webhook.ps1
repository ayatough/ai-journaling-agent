# Run the LINE webhook server and restart it if it exits.
. "$PSScriptRoot\common.ps1"
Set-Location $RepoRoot

while ($true) {
    $log = Get-LogFile 'webhook'
    Write-Log $log "starting webhook on $($env:HOST)"
    & uv run python -m ai_journaling_agent.main 2>&1 | ForEach-Object { "$_" } | Out-File -Append -Encoding utf8 $log
    Write-Log $log "webhook exited (code $LASTEXITCODE); restarting in 10s"
    Start-Sleep -Seconds 10
}
