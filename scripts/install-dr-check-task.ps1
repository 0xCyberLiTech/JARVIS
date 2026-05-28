#Requires -Version 5.1
<#
.SYNOPSIS
    install-dr-check-task.ps1 - Cree/MAJ la tache planifiee hebdo du "feu vert DR".
.DESCRIPTION
    Enregistre la tache Windows "JARVIS-DR-Check" qui lance dr-check.ps1 chaque
    dimanche a 9h, en S4U (sans fenetre console qui flashe), lecture seule.
    Idempotent : -Force recree/met a jour si la tache existe deja.

    A LANCER EN ADMINISTRATEUR (la creation de tache planifiee l'exige).
    Reutilisable : apres une reinstall, relancer ce script recree le feu vert DR.
.NOTES
    0xCyberLiTech - 2026-05-28 - chantier DR JARVIS/SOC inperdable (etape 5).
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ── Verif droits administrateur ────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
            [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "  [XX] Ce script doit etre lance EN ADMINISTRATEUR." -ForegroundColor Red
    Write-Host "       -> Windows + X  puis  'Terminal (administrateur)'" -ForegroundColor Yellow
    Write-Host "       -> puis relancer ce script." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# ── Parametres tache ───────────────────────────────────────────
$TASK_NAME  = "JARVIS-DR-Check"
$scriptPath = "C:\Users\$env:USERNAME\Documents\0xCyberLiTech\JARVIS\scripts\dr-check.ps1"

if (-not (Test-Path $scriptPath)) {
    Write-Host "  [XX] dr-check.ps1 introuvable : $scriptPath" -ForegroundColor Red
    exit 1
}

# ── Definition + enregistrement (S4U, sans fenetre) ────────────
$action    = New-ScheduledTaskAction -Execute "powershell.exe" `
                -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
$trigger   = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 9am
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TASK_NAME -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description "Verif hebdo du coffre DR JARVIS (feu vert/rouge) - dr-check.ps1, lecture seule" `
    -Force | Out-Null

Write-Host ""
Write-Host "  [OK] Tache '$TASK_NAME' enregistree." -ForegroundColor Green
Write-Host "       Declenchement : chaque dimanche a 09h00 (S4U, sans fenetre)" -ForegroundColor Gray
Write-Host "       Action        : dr-check.ps1 (lecture seule du coffre)" -ForegroundColor Gray
Write-Host "       Statut ecrit  : Bureau\DR-STATUT-JARVIS.txt (GO / NO-GO)" -ForegroundColor Gray
Write-Host ""
Get-ScheduledTask -TaskName $TASK_NAME | Select-Object TaskName, State,
    @{N='LogonType';E={$_.Principal.LogonType}} | Format-List
