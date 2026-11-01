# Run the ngrok tunnel to the local webhook and restart it if it exits.
# Requires NGROK_DOMAIN in .env and `ngrok config add-authtoken` done once.
. "$PSScriptRoot\common.ps1"

$domain = Get-DotEnvValue 'NGROK_DOMAIN'
$port = Get-DotEnvValue 'PORT'
if (-not $port) { $port = '8000' }

while ($true) {
    $log = Get-LogFile 'tunnel'
    if (-not $domain) { Write-Log $log 'NGROK_DOMAIN is not set in .env'; Start-Sleep 300; continue }
    Write-Log $log "starting ngrok https://$domain -> 127.0.0.1:$port"
    & ngrok http "127.0.0.1:$port" --url "https://$domain" --log stdout --log-level warn 2>&1 |
        ForEach-Object { "$_" } | Out-File -Append -Encoding utf8 $log
    Write-Log $log "ngrok exited (code $LASTEXITCODE); restarting in 15s"
    Start-Sleep -Seconds 15
}
