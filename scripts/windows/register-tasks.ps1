# Register Task Scheduler entries so everything comes back after a reboot/logon.
#   AIJournaling-Webhook : at logon, webhook server (self-restarting)
#   AIJournaling-Tunnel  : at logon, ngrok tunnel (self-restarting)
#   AIJournaling-Checkin : every 30 minutes, check-in sender
# Run once in a normal (non-admin) PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\scripts\windows\register-tasks.ps1
# Remove with: .\scripts\windows\register-tasks.ps1 -Unregister
param([switch]$Unregister)

$names = 'AIJournaling-Webhook', 'AIJournaling-Tunnel', 'AIJournaling-Checkin'
foreach ($n in $names) { Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue }
if ($Unregister) { 'Unregistered.'; return }

$user = "$env:USERDOMAIN\$env:USERNAME"
$ps = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$conhost = Join-Path $env:WINDIR 'System32\conhost.exe'
# conhost --headless runs the console without ever showing a window (Windows 10 21H2+ / 11).
function New-Action([string]$Script) {
    New-ScheduledTaskAction -Execute $conhost `
        -Argument "--headless `"$ps`" -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\$Script`""
}
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited

$longRunning = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew -StartWhenAvailable
$logon = New-ScheduledTaskTrigger -AtLogOn -User $user

Register-ScheduledTask -TaskName 'AIJournaling-Webhook' -Action (New-Action 'start-webhook.ps1') `
    -Trigger $logon -Principal $principal -Settings $longRunning | Out-Null
Register-ScheduledTask -TaskName 'AIJournaling-Tunnel' -Action (New-Action 'start-tunnel.ps1') `
    -Trigger $logon -Principal $principal -Settings $longRunning | Out-Null

$every30 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 30)
$short = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'AIJournaling-Checkin' -Action (New-Action 'run-checkin.ps1') `
    -Trigger $every30 -Principal $principal -Settings $short | Out-Null

Get-ScheduledTask -TaskName 'AIJournaling-*' | Select-Object TaskName, State
