# jarvis_watchdog_install.ps1 — Installe la tâche planifiée Windows "JarvisWatchdog"
# Lance le watchdog toutes les 5 minutes, dès que l'utilisateur est connecté.
# Nécessite d'être exécuté en tant qu'Administrateur.

$taskName    = "JarvisWatchdog"
$watchdogPs1 = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "jarvis_watchdog.ps1"
$action      = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdogPs1`""

$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At (Get-Date)
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

# Supprimer l'ancienne tâche si elle existe
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Description "Surveille JARVIS (localhost:5000) et le redémarre automatiquement si KO." `
    -Force | Out-Null

Write-Host "Tâche '$taskName' installée — watchdog toutes les 5 minutes." -ForegroundColor Green
Write-Host "Log : $(Split-Path -Parent $watchdogPs1)\jarvis_watchdog.log"
