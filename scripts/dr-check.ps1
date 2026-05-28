#Requires -Version 5.1
<#
.SYNOPSIS
    dr-check.ps1 - Verification automatique du coffre DR JARVIS (feu vert / rouge).
.DESCRIPTION
    LECTURE SEULE : verifie que D:\BACKUP-WINDOWS contient tout pour restaurer
    JARVIS + backend SOC sur une autre machine Windows (reinstall hors-ligne).
    Ne touche a RIEN, ne lance aucune restauration. Concu pour une tache planifiee.

    Produit :
      - un statut clair sur le Bureau (DR-STATUT-JARVIS.txt) : GO ou NO-GO + details
      - un log cumulatif (jarvis-dr-check.log)
      - exit code 0 = GO (coffre complet) / 1 = NO-GO (element manquant)

    "Feu vert DR" : si GO, le coffre permet de remonter JARVIS sans stress.
.NOTES
    0xCyberLiTech - 2026-05-28 - chantier DR JARVIS/SOC inperdable (etape 5).
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ── Parametres ─────────────────────────────────────────────────
$BACKUP_ROOT  = "D:\BACKUP-WINDOWS"
$STATUT_FILE  = "$env:USERPROFILE\Desktop\DR-STATUT-JARVIS.txt"
$LOG          = "$env:USERPROFILE\Desktop\jarvis-dr-check.log"
$MAX_AGE_SOC  = 14    # jours max pour la copie backend SOC (sinon WARN)

# ── Definition des verifications du coffre ─────────────────────
# Type : CRITICAL (manquant => NO-GO) ou WARN (manquant => signale sans bloquer)
$checks = @(
    @{ label = "Frontend + serveur JARVIS"; type = "CRITICAL"; test = {
        (Test-Path "$BACKUP_ROOT\JARVIS\scripts\jarvis.py") -and
        (Test-Path "$BACKUP_ROOT\JARVIS\scripts\templates\jarvis.html") } }
    @{ label = "Modeles Ollama (cerveau)"; type = "CRITICAL"; test = {
        (Test-Path "$BACKUP_ROOT\OLLAMA-MODELS\models\manifests") } }
    @{ label = "Installeur Python (hors-ligne)"; type = "CRITICAL"; test = {
        Test-Path "$BACKUP_ROOT\INSTALLERS\python-3.11.9-amd64.exe" } }
    @{ label = "Installeur Ollama (hors-ligne)"; type = "CRITICAL"; test = {
        Test-Path "$BACKUP_ROOT\INSTALLERS\OllamaSetup.exe" } }
    @{ label = "Pilote NVIDIA (installeur ou reference)"; type = "WARN"; test = {
        (Get-ChildItem "$BACKUP_ROOT\INSTALLERS\*.exe" -ErrorAction SilentlyContinue |
         Where-Object { $_.Name -match 'nvidia|^\d{3}' }) -or
        (Test-Path "$BACKUP_ROOT\INSTALLERS\nvidia-driver-version.txt") } }
    @{ label = "Cles SSH"; type = "CRITICAL"; test = {
        (Get-ChildItem "$BACKUP_ROOT\SSH" -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0 } }
    @{ label = "Memoire Claude"; type = "WARN"; test = {
        Test-Path "$BACKUP_ROOT\CLAUDE-MEMORY" } }
    @{ label = "Backend SOC (copie froide < $MAX_AGE_SOC j)"; type = "WARN"; test = {
        $last = Get-ChildItem "$BACKUP_ROOT\SOC-BACKEND\soc-backend-*.tgz" -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $last -and ((New-TimeSpan -Start $last.LastWriteTime -End (Get-Date)).TotalDays -le $MAX_AGE_SOC) } }
    @{ label = "Scripts DR (backup + install) dans le coffre"; type = "CRITICAL"; test = {
        (Test-Path "$BACKUP_ROOT\JARVIS\scripts\install-jarvis.ps1") -and
        (Test-Path "$BACKUP_ROOT\JARVIS\scripts\backup-jarvis.ps1") } }
)

# ── Execution des verifications ────────────────────────────────
$results  = @()
$failCrit = 0
$warnCnt  = 0
foreach ($c in $checks) {
    $ok = $false
    try { $ok = [bool](& $c.test) } catch { $ok = $false }
    if (-not $ok) {
        if ($c.type -eq "CRITICAL") { $failCrit++; $sym = "[XX]" } else { $warnCnt++; $sym = "[!!]" }
    } else { $sym = "[OK]" }
    $results += [pscustomobject]@{ Sym = $sym; Type = $c.type; Label = $c.label; Ok = $ok }
}

$verdict = if ($failCrit -eq 0) { "GO" } else { "NO-GO" }
$now     = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# ── Ecriture du statut (Bureau) ────────────────────────────────
$lines = @()
$lines += "=============================================="
$lines += "  STATUT DR JARVIS  :  $verdict"
$lines += "  Verifie le        :  $now"
$lines += "  Coffre            :  $BACKUP_ROOT"
$lines += "=============================================="
$lines += ""
foreach ($r in $results) { $lines += ("  {0}  {1}" -f $r.Sym, $r.Label) }
$lines += ""
if ($verdict -eq "GO") {
    $lines += "  >> FEU VERT : le coffre permet de restaurer JARVIS sur une"
    $lines += "     autre machine Windows (reinstall hors-ligne possible)."
    if ($warnCnt -gt 0) { $lines += "     ($warnCnt avertissement(s) non bloquant(s) ci-dessus)" }
} else {
    $lines += "  >> NO-GO : $failCrit element(s) CRITIQUE(s) manquant(s) dans le coffre."
    $lines += "     Lancer une sauvegarde complete pour corriger :"
    $lines += "       - JARVIS    : JARVIS\scripts\backup-jarvis.ps1"
    $lines += "       - Backend SOC : SOC\scripts\backup-soc-backend.ps1"
}
$lines += ""
Set-Content -Path $STATUT_FILE -Value $lines -Encoding UTF8

# ── Log cumulatif ──────────────────────────────────────────────
$logLine = "$now  VERDICT=$verdict  fails_critiques=$failCrit  warns=$warnCnt"
Add-Content -Path $LOG -Value $logLine -Encoding UTF8

# ── Sortie console (si lance manuellement) ─────────────────────
$col = if ($verdict -eq "GO") { "Green" } else { "Red" }
Write-Host ""
Write-Host "  STATUT DR JARVIS : $verdict" -ForegroundColor $col
foreach ($r in $results) {
    $rc = if ($r.Ok) { "Green" } elseif ($r.Type -eq "CRITICAL") { "Red" } else { "Yellow" }
    Write-Host "  $($r.Sym) $($r.Label)" -ForegroundColor $rc
}
Write-Host ""
Write-Host "  Statut ecrit : $STATUT_FILE" -ForegroundColor Gray
Write-Host ""

if ($verdict -eq "GO") { exit 0 } else { exit 1 }
