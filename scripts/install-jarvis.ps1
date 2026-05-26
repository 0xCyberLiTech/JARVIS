<#
.SYNOPSIS
    JARVIS  -  Script d'installation automatique Windows
    0xCyberLiTech  -  2026-04-14

.DESCRIPTION
    Installe et configure JARVIS depuis zero sur Windows 11 Pro :
    - Etape 0 : Pilotes NVIDIA + CUDA (detection automatique, winget si absent)
    - Python 3.11.9
    - Ollama + modeles LLM
    - Packages Python (Flask, edge-tts, Whisper, DeepFilterNet, etc.)
    - PyTorch CUDA 12.8 (cu128  -  RTX 5080 Blackwell sm_120)

.PARAMETER DryRun
    Mode simulation : verifie tous les prerequis et produit un rapport
    sans rien installer ni modifier. Rapport sauvegarde sur le bureau.
    Usage : .\install-jarvis.ps1 -DryRun

.PARAMETER DryRunRestore
    Simulation restauration : simule chaque etape (0-8) et affiche ce
    qui SERAIT execute, sans rien modifier. Rapport jarvis-simrestore-*.txt.
    Usage : .\install-jarvis.ps1 -DryRunRestore

.NOTES
    Lancer en tant qu'Administrateur.
    Connexion internet requise (ou sauvegarde D:\BACKUP-WINDOWS presente).
    Ordre de priorite : GPU/CUDA en premier (prerequis PyTorch CUDA).
#>

param(
    [switch]$DryRun,
    [switch]$DryRunRestore,
    [switch]$Unattended
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Couleurs ──────────────────────────────────────────────────
function Write-Title   { param($msg) Write-Host "`n  [$msg]" -ForegroundColor Cyan }
function Write-OK      { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-WARN    { param($msg) Write-Host "  [!!] $msg" -ForegroundColor Yellow }
function Write-FAIL    { param($msg) Write-Host "  [XX] $msg" -ForegroundColor Red }
function Write-INFO    { param($msg) Write-Host "  --> $msg" -ForegroundColor Gray }

# ── Banniere ──────────────────────────────────────────────────
Clear-Host
Write-Host ""
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |   J A R V I S  --  Installation automatique     |" -ForegroundColor Cyan
Write-Host "  |   0xCyberLiTech  --  Windows 11 Pro             |" -ForegroundColor Cyan
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# ── Variables ─────────────────────────────────────────────────
$PYTHON_VERSION   = "3.11.9"
$PYTHON_URL       = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$PYTHON_EXE       = "$env:TEMP\python-3.11.9-amd64.exe"
$PYTHON_PATH      = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"

$OLLAMA_URL       = "https://ollama.com/download/OllamaSetup.exe"
$OLLAMA_EXE       = "$env:TEMP\OllamaSetup.exe"

$JARVIS_ROOT      = "C:\Users\$env:USERNAME\Documents\0xCyberLiTech\JARVIS"
$BACKUP_ROOT      = "D:\BACKUP-WINDOWS"
$OLLAMA_MODELS    = "C:\Users\$env:USERNAME\.ollama"

$LOG              = "$env:USERPROFILE\Desktop\jarvis-install.log"

# ── Fonction log ──────────────────────────────────────────────
function Log { param($msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LOG -Value "$ts  $msg" -Encoding UTF8
}

Log "=== Debut installation JARVIS ==="

# ── Check administrateur (requis seulement hors DryRun) ───────
if (-not $DryRun) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-FAIL "Ce script doit etre lance en tant qu'Administrateur"
        Write-INFO "Clic droit sur JARVIS-menu.ps1 → Executer en tant qu'administrateur"
        Write-INFO "Ou mode simulation sans droits : .\install-jarvis.ps1 -DryRun"
        exit 1
    }
}

# ══════════════════════════════════════════════════════════════
# MODE SIMULATION (-DryRun)
# Verifie tous les prerequis, produit un rapport, sort sans
# rien installer ni modifier.
# ══════════════════════════════════════════════════════════════
if ($DryRun) {

    Clear-Host
    Write-Host ""
    Write-Host "  +--------------------------------------------------+" -ForegroundColor Magenta
    Write-Host "  |   J A R V I S  --  Simulation (DryRun)          |" -ForegroundColor Magenta
    Write-Host "  |   0xCyberLiTech  --  Aucune action effectuee    |" -ForegroundColor Magenta
    Write-Host "  +--------------------------------------------------+" -ForegroundColor Magenta
    Write-Host ""

    $REPORT_FILE = "$env:USERPROFILE\Desktop\jarvis-dryrun-$(Get-Date -Format 'yyyyMMdd-HHmm').txt"
    $report = [System.Collections.Generic.List[string]]::new()
    $report.Add("JARVIS - Rapport Simulation DryRun")
    $report.Add("Date : $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
    $report.Add("Machine : $env:COMPUTERNAME - Utilisateur : $env:USERNAME")
    $report.Add("=" * 60)

    $okCount   = 0
    $warnCount = 0
    $failCount = 0

    function Show-DrOk   { param($label,$detail)
        Write-Host ("  [OK]  {0,-38} {1}" -f $label, $detail) -ForegroundColor Green
        $script:report.Add(("[OK]  {0,-38} {1}" -f $label, $detail))
        $script:okCount++
    }
    function Show-DrWarn { param($label,$detail)
        Write-Host ("  [!!]  {0,-38} {1}" -f $label, $detail) -ForegroundColor Yellow
        $script:report.Add(("[!!]  {0,-38} {1}" -f $label, $detail))
        $script:warnCount++
    }
    function Show-DrFail { param($label,$detail)
        Write-Host ("  [XX]  {0,-38} {1}" -f $label, $detail) -ForegroundColor Red
        $script:report.Add(("[XX]  {0,-38} {1}" -f $label, $detail))
        $script:failCount++
    }
    function Show-DrHead { param($title)
        Write-Host "`n  --- $title ---" -ForegroundColor Cyan
        $script:report.Add("")
        $script:report.Add("--- $title ---")
    }

    # ── ETAPE 0 : GPU / Pilote NVIDIA ─────────────────────────
    Show-DrHead "ETAPE 0  -  GPU / Pilote NVIDIA"

    $nvSmi = $null
    foreach ($p in @("$env:SystemRoot\System32\nvidia-smi.exe",
                     "C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe")) {
        if (Test-Path $p) { $nvSmi = $p; break }
    }
    if (-not $nvSmi) { try { $nvSmi = (Get-Command nvidia-smi -ErrorAction Stop).Source } catch {} }

    if ($nvSmi) {
        $smiRaw   = & $nvSmi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1
        $smiLine  = ($smiRaw | Select-Object -First 1).Trim()
        $fields   = $smiLine -split ",\s*"
        $gpuName  = $fields[0].Trim()
        $drvStr   = if ($fields.Count -ge 2) { $fields[1].Trim() } else { "?" }
        $vramStr  = if ($fields.Count -ge 3) { $fields[2].Trim() } else { "?" }
        $drvVer   = 0.0
        [double]::TryParse($drvStr, [System.Globalization.NumberStyles]::Any,
            [System.Globalization.CultureInfo]::InvariantCulture, [ref]$drvVer) | Out-Null

        Show-DrOk "nvidia-smi" "$gpuName  -  $vramStr"

        if ($drvVer -lt 528.33) {
            Show-DrFail "Driver NVIDIA" "$drvStr  -  TROP VIEUX (min 528.33 pour CUDA 12.8)"
        } elseif ($drvVer -lt 572.00) {
            Show-DrWarn "Driver NVIDIA" "$drvStr  -  CUDA 12.8 OK mais RTX 5080 recommande >= 572"
        } else {
            Show-DrOk "Driver NVIDIA" "$drvStr  -  compatible CUDA 12.8 + RTX 5080"
        }
    } else {
        Show-DrFail "nvidia-smi" "ABSENT  -  pilote NVIDIA non installe"
        Show-DrFail "Driver NVIDIA" "Inconnu  -  installation requise avant PyTorch"
    }

    # nvcc
    $nvccVer = $null
    try {
        $nvccOut = & nvcc --version 2>&1
        if ($nvccOut -match "release\s+([\d\.]+)") { $nvccVer = $matches[1] }
    } catch {}
    if ($nvccVer) { Show-DrOk "nvcc (CUDA Toolkit)" $nvccVer }
    else          { Show-DrWarn "nvcc (CUDA Toolkit)" "Absent  -  non bloquant (PyTorch cu128 auto-suffisant)" }

    # Cache NVIDIA
    $nvCached = Get-ChildItem "$BACKUP_ROOT\INSTALLERS" -Filter "*.exe" -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -imatch "nvidia" -or $_.Name -imatch "^\d{3}.*\.exe" } |
                Select-Object -First 1
    if ($nvCached) { Show-DrOk "Cache pilote NVIDIA" $nvCached.Name }
    else           { Show-DrWarn "Cache pilote NVIDIA" "Absent dans INSTALLERS\  -  winget ou internet requis" }

    # ── ETAPE 1 : Python ──────────────────────────────────────
    Show-DrHead "ETAPE 1  -  Python"

    if (Test-Path $PYTHON_PATH) {
        $pyVer = (& $PYTHON_PATH --version 2>&1).ToString().Trim()
        Show-DrOk "Python 3.11" $pyVer
    } else {
        $pyCached = "$BACKUP_ROOT\INSTALLERS\python-3.11.9-amd64.exe"
        if (Test-Path $pyCached) {
            $pySize = [math]::Round((Get-Item $pyCached).Length / 1MB, 1)
            Show-DrWarn "Python 3.11" "Non installe  -  installeur en cache ($pySize MB)  -  OK pour install"
        } else {
            Show-DrWarn "Python 3.11" "Non installe  -  pas de cache  -  telechargement internet requis"
        }
    }

    # pip
    try {
        $pipVer = (& $PYTHON_PATH -m pip --version 2>&1 | Select-Object -First 1).ToString().Trim()
        Show-DrOk "pip" $pipVer
    } catch { Show-DrWarn "pip" "Non disponible (Python absent ?)" }

    # ── ETAPE 2 : Ollama + modeles ────────────────────────────
    Show-DrHead "ETAPE 2  -  Ollama + Modeles LLM"

    $ollamaOkDR = $false
    try { $ollamaVer = (& ollama --version 2>&1).ToString().Trim(); $ollamaOkDR = $true } catch {}
    if ($ollamaOkDR) { Show-DrOk "Ollama" $ollamaVer }
    else             { Show-DrWarn "Ollama" "Non installe  -  telechargement internet requis" }

    $backupOllamaPath = "$BACKUP_ROOT\OLLAMA-MODELS\models"
    if (Test-Path $backupOllamaPath) {
        $olSize = [math]::Round(
            (Get-ChildItem $backupOllamaPath -Recurse -ErrorAction SilentlyContinue |
             Measure-Object -Property Length -Sum).Sum / 1GB, 1)
        $manifests = Get-ChildItem "$backupOllamaPath\manifests\registry.ollama.ai\library" -ErrorAction SilentlyContinue
        $modelList = if ($manifests) { ($manifests | ForEach-Object { $_.Name }) -join ", " } else { "?" }
        Show-DrOk "Backup modeles Ollama" "$olSize GB  -  $modelList"
    } else {
        Show-DrFail "Backup modeles Ollama" "Absent  -  telechargement ~47 GB requis (30-90 min)"
    }

    # ── ETAPE 3 : Packages Python ─────────────────────────────
    Show-DrHead "ETAPE 3  -  Packages Python"

    $pkgList = @("flask","flask_cors","flask_limiter","edge_tts","faster_whisper",
                 "pynvml","psutil","requests","pyttsx3","numpy","scipy",
                 "ctranslate2","paramiko","cryptography","huggingface_hub")
    $pkgMissing = @()
    # Isoler ErrorActionPreference pour que les warnings stderr ne bloquent pas
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    foreach ($pkg in $pkgList) {
        $null = & $PYTHON_PATH -c "import $pkg" 2>$null
        if ($LASTEXITCODE -ne 0) { $pkgMissing += $pkg }
    }
    # piper-tts et DeepFilterNet ont des noms d'import differents
    foreach ($pair in @(@("piper","piper-tts"),@("df","DeepFilterNet"))) {
        $null = & $PYTHON_PATH -c "import $($pair[0])" 2>$null
        if ($LASTEXITCODE -ne 0) { $pkgMissing += $pair[1] }
    }
    $ErrorActionPreference = $prevEAP

    if ($pkgMissing.Count -eq 0) {
        Show-DrOk "Packages Python" "Tous installes ($($pkgList.Count + 2) packages)"
    } else {
        Show-DrWarn "Packages Python" "$($pkgMissing.Count) manquants : $($pkgMissing -join ', ')"
    }

    # ── ETAPE 4 : PyTorch CUDA ────────────────────────────────
    Show-DrHead "ETAPE 4  -  PyTorch CUDA"

    try {
        $torchVer  = & $PYTHON_PATH -c "import torch; print(torch.__version__)" 2>&1
        $cudaAvail = & $PYTHON_PATH -c "import torch; print(torch.cuda.is_available())" 2>&1
        $gpuDev    = & $PYTHON_PATH -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')" 2>&1

        if ($torchVer -match "cu128") {
            Show-DrOk "PyTorch" "$torchVer"
        } else {
            Show-DrWarn "PyTorch" "$torchVer  -  version cu128 recommandee pour RTX 5080"
        }

        if ($cudaAvail -match "True") {
            Show-DrOk "CUDA disponible" $gpuDev.Trim()
        } else {
            Show-DrFail "CUDA disponible" "False  -  GPU ne sera pas utilise (DeepFilterNet CPU seulement)"
        }
    } catch {
        Show-DrWarn "PyTorch" "Non installe  -  ~4 GB a telecharger depuis pytorch.org"
        Show-DrWarn "CUDA disponible" "Inconnu (PyTorch absent)"
    }

    # ── ETAPE 5 : Fichiers JARVIS ─────────────────────────────
    Show-DrHead "ETAPE 5  -  Fichiers JARVIS"

    $backupJarvisDR = "$BACKUP_ROOT\JARVIS"
    if (Test-Path $backupJarvisDR) {
        $jSize = [math]::Round(
            (Get-ChildItem $backupJarvisDR -Recurse -ErrorAction SilentlyContinue |
             Measure-Object -Property Length -Sum).Sum / 1MB, 1)
        Show-DrOk "Backup JARVIS" "$jSize MB  -  $backupJarvisDR"
    } elseif (Test-Path $JARVIS_ROOT) {
        Show-DrWarn "Backup JARVIS" "Absent mais dossier deja present sur C:  -  OK si recente"
    } else {
        Show-DrFail "Backup JARVIS" "Absent  -  aucune source disponible"
    }

    $criticalFiles = @(
        "scripts\jarvis.py",
        "scripts\jarvis_system_prompt.txt",
        "scripts\jarvis_prompt_profiles.json",
        "scripts\jarvis_model.json",
        "scripts\jarvis_llm_params.json",
        "scripts\jarvis_dsp_params.json"
    )
    $missingFiles = @()
    foreach ($f in $criticalFiles) {
        $fp = Join-Path $backupJarvisDR $f
        if (-not (Test-Path $fp)) { $missingFiles += $f }
    }
    if ($missingFiles.Count -eq 0) {
        Show-DrOk "Fichiers critiques JARVIS" "Tous presents ($($criticalFiles.Count))"
    } else {
        Show-DrFail "Fichiers critiques JARVIS" "Manquants : $($missingFiles -join ', ')"
    }

    # ── ETAPE 6 : Cles SSH ────────────────────────────────────
    Show-DrHead "ETAPE 6  -  Cles SSH"

    $backupSSHDR = "$BACKUP_ROOT\SSH"
    if (Test-Path $backupSSHDR) {
        $sshKeys = Get-ChildItem $backupSSHDR -File -ErrorAction SilentlyContinue |
                   Where-Object { $_.Name -notmatch "\.pub$" -and $_.Name -ne "known_hosts" }
        $keyNames = ($sshKeys | ForEach-Object { $_.Name }) -join ", "
        Show-DrOk "Backup SSH" "$($sshKeys.Count) cles : $keyNames"
    } else {
        Show-DrFail "Backup SSH" "Absent dans $backupSSHDR"
    }

    # ── ETAPE 7 : Memoire Claude ──────────────────────────────
    Show-DrHead "ETAPE 7  -  Memoire Claude Code"

    $backupClaudeDR = "$BACKUP_ROOT\CLAUDE-MEMORY"
    if (Test-Path $backupClaudeDR) {
        $clSize = [math]::Round(
            (Get-ChildItem $backupClaudeDR -Recurse -ErrorAction SilentlyContinue |
             Measure-Object -Property Length -Sum).Sum / 1MB, 1)
        Show-DrOk "Backup Claude" "$clSize MB  -  $backupClaudeDR"
    } else {
        Show-DrWarn "Backup Claude" "Absent  -  memoire Claude sera perdue (non bloquant)"
    }

    # ── ETAPE 8 : Raccourcis bureau ───────────────────────────
    Show-DrHead "ETAPE 8  -  Raccourcis bureau"

    $desktop = [Environment]::GetFolderPath("Desktop")
    foreach ($lnk in @("JARVIS Dashboard.lnk","JARVIS - Arret.lnk","JARVIS - Demarrage.lnk")) {
        if (Test-Path (Join-Path $desktop $lnk)) { Show-DrOk "Raccourci $lnk" "Present" }
        else                                      { Show-DrWarn "Raccourci $lnk" "Absent  -  sera cree" }
    }

    # ── CACHE INSTALLERS ──────────────────────────────────────
    Show-DrHead "CACHE D:\BACKUP-WINDOWS\INSTALLERS\"

    $instDir = "$BACKUP_ROOT\INSTALLERS"
    if (Test-Path $instDir) {
        $instFiles = Get-ChildItem $instDir -File -ErrorAction SilentlyContinue
        if ($instFiles) {
            foreach ($f in $instFiles) {
                $sz = [math]::Round($f.Length / 1MB, 1)
                Show-DrOk "Cache : $($f.Name)" "$sz MB"
            }
        } else { Show-DrWarn "Cache INSTALLERS\" "Dossier vide" }
    } else { Show-DrWarn "Cache INSTALLERS\" "Dossier absent" }

    # ── RAPPORT FINAL ─────────────────────────────────────────
    $total = $okCount + $warnCount + $failCount
    $report.Add("")
    $report.Add("=" * 60)
    $report.Add("SCORE : $okCount OK  /  $warnCount WARN  /  $failCount FAIL  (total $total checks)")

    $verdict = if ($failCount -eq 0 -and $warnCount -eq 0) { "DEPLOIEMENT PRET  -  100% OK" }
               elseif ($failCount -eq 0)                    { "DEPLOIEMENT POSSIBLE  -  verifier les WARN" }
               else                                          { "DEPLOIEMENT BLOQUE  -  corriger les FAIL avant" }
    $report.Add("VERDICT : $verdict")

    Write-Host ""
    Write-Host "  --------------------------------------------------" -ForegroundColor Cyan
    $scoreColor = if ($failCount -gt 0) { "Red" } elseif ($warnCount -gt 0) { "Yellow" } else { "Green" }
    Write-Host ("  SCORE : {0} OK  /  {1} WARN  /  {2} FAIL" -f $okCount, $warnCount, $failCount) -ForegroundColor $scoreColor
    Write-Host "  VERDICT : $verdict" -ForegroundColor $scoreColor
    Write-Host "  --------------------------------------------------" -ForegroundColor Cyan
    Write-Host ""

    # Sauvegarder le rapport
    $report | Set-Content -Path $REPORT_FILE -Encoding UTF8
    Write-Host "  Rapport sauvegarde : $REPORT_FILE" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Mode simulation  -  rien n'a ete installe ni modifie." -ForegroundColor Magenta
    Write-Host "  Pour lancer l'installation reelle : .\install-jarvis.ps1" -ForegroundColor White
    Write-Host ""

    exit 0
}

# ══════════════════════════════════════════════════════════════
# MODE SIMULATION RESTAURATION (-DryRunRestore)
# Simule chaque etape (0-8) de la restauration reelle, affiche
# ce qui SERAIT execute, sans rien modifier.
# ══════════════════════════════════════════════════════════════
if ($DryRunRestore) {

    Clear-Host
    Write-Host ""
    Write-Host "  +--------------------------------------------------+" -ForegroundColor Magenta
    Write-Host "  |   J A R V I S  --  Simulation Restauration      |" -ForegroundColor Magenta
    Write-Host "  |   0xCyberLiTech  --  Aucune action effectuee    |" -ForegroundColor Magenta
    Write-Host "  +--------------------------------------------------+" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "  [SIM ->] serait execute   [SIM !!] avertissement   [SIM XX] echec" -ForegroundColor Gray
    Write-Host ""

    $REPORT_SIM = "$env:USERPROFILE\Desktop\jarvis-simrestore-$(Get-Date -Format 'yyyyMMdd-HHmm').txt"
    $rptSim = [System.Collections.Generic.List[string]]::new()
    $rptSim.Add("JARVIS - Simulation Restauration (-DryRunRestore)")
    $rptSim.Add("Date : $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
    $rptSim.Add("Machine : $env:COMPUTERNAME - Utilisateur : $env:USERNAME")
    $rptSim.Add("=" * 60)
    $simOk = 0; $simWarn = 0; $simFail = 0

    function Show-SimOk { param($msg)
        Write-Host ("  [SIM ->] {0}" -f $msg) -ForegroundColor Green
        $script:rptSim.Add("[SIM ->] $msg"); $script:simOk++ }
    function Show-SimWn { param($msg)
        Write-Host ("  [SIM !!] {0}" -f $msg) -ForegroundColor Yellow
        $script:rptSim.Add("[SIM !!] $msg"); $script:simWarn++ }
    function Show-SimFl { param($msg)
        Write-Host ("  [SIM XX] {0}" -f $msg) -ForegroundColor Red
        $script:rptSim.Add("[SIM XX] $msg"); $script:simFail++ }
    function Show-SimNt { param($msg)
        Write-Host ("          {0}" -f $msg) -ForegroundColor Gray
        $script:rptSim.Add("          $msg") }
    function Show-SimHd { param($t)
        Write-Host "`n  --- $t ---" -ForegroundColor Cyan
        $script:rptSim.Add(""); $script:rptSim.Add("--- $t ---") }

    function Sim-Etape0 {
        Show-SimHd "ETAPE 0  -  Pilotes NVIDIA + CUDA"
        $nvSmi = $null
        foreach ($p in @("$env:SystemRoot\System32\nvidia-smi.exe",
                         "C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe")) {
            if (Test-Path $p) { $nvSmi = $p; break }
        }
        if (-not $nvSmi) { try { $nvSmi = (Get-Command nvidia-smi -ErrorAction Stop).Source } catch {} }
        if ($nvSmi) {
            $flds = ((& $nvSmi --query-gpu=name,driver_version --format=csv,noheader 2>&1 |
                      Select-Object -First 1).Trim()) -split ",\s*"
            $drv = if ($flds.Count -ge 2) { $flds[1].Trim() } else { "?" }
            $dv  = 0.0
            [double]::TryParse($drv, [Globalization.NumberStyles]::Any,
                [Globalization.CultureInfo]::InvariantCulture, [ref]$dv) | Out-Null
            if ($dv -ge 572.00)    { Show-SimOk "Driver $drv present et compatible - aucune action" }
            elseif ($dv -ge 528.33){ Show-SimWn "Driver $drv present mais < 572 recommande RTX 5080" }
            else                   { Show-SimFl "Driver $drv trop vieux (min 528.33) - mise a jour requise" }
        } else {
            $nvC = Get-ChildItem "$BACKUP_ROOT\INSTALLERS" -Filter "*.exe" -ErrorAction SilentlyContinue |
                   Where-Object { $_.Name -imatch "nvidia" -or $_.Name -imatch "^\d{3}.*\.exe" } |
                   Select-Object -First 1
            if ($nvC) {
                Show-SimWn "Driver absent - INSTALLERAIT cache : $($nvC.Name) (flags: -s -noreboot)"
                Show-SimNt "Redemarrage requis apres installation"
            } elseif ($null -ne (Get-Command winget -ErrorAction SilentlyContinue)) {
                Show-SimWn "Driver absent - INSTALLERAIT : winget install NVIDIA.CUDA --silent"
            } else {
                Show-SimFl "Driver absent  -  AUCUNE SOURCE (cache vide + winget absent)"
            }
        }
    }

    function Sim-Etape1 {
        Show-SimHd "ETAPE 1  -  Python 3.11"
        if (Test-Path $PYTHON_PATH) {
            $v = (& $PYTHON_PATH --version 2>&1).ToString().Trim()
            Show-SimOk "Python deja installe ($v) - aucune action"
            Show-SimNt "Mettrait a jour pip : python -m pip install --upgrade pip"
        } else {
            $cach = "$BACKUP_ROOT\INSTALLERS\python-3.11.9-amd64.exe"
            if (Test-Path $cach) {
                $sz = [math]::Round((Get-Item $cach).Length / 1MB, 1)
                Show-SimWn "Python absent - INSTALLERAIT depuis cache : python-3.11.9-amd64.exe ($sz MB)"
                Show-SimNt "Flags : /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1"
            } else {
                Show-SimWn "Python absent - TELECHARGERAIT depuis python.org/ftp/python/3.11.9/"
                Show-SimNt "Puis mettrait en cache dans $BACKUP_ROOT\INSTALLERS\"
            }
        }
    }

    function Sim-Etape2 {
        Show-SimHd "ETAPE 2  -  Ollama + Modeles LLM"
        try {
            $ov = (& ollama --version 2>&1).ToString().Trim()
            Show-SimOk "Ollama deja installe ($ov) - aucune action"
        } catch { Show-SimWn "Ollama absent - TELECHARGERAIT OllamaSetup.exe puis installerait (/S)" }
        $bkM = "$BACKUP_ROOT\OLLAMA-MODELS\models"
        if (Test-Path $bkM) {
            $sz  = [math]::Round(
                (Get-ChildItem $bkM -Recurse -ErrorAction SilentlyContinue |
                 Measure-Object -Property Length -Sum).Sum / 1GB, 1)
            $ml  = (Get-ChildItem "$bkM\manifests\registry.ollama.ai\library" -ErrorAction SilentlyContinue |
                    ForEach-Object { $_.Name }) -join ", "
            Show-SimOk "Backup modeles present ($sz GB) - COPIERAIT vers $OLLAMA_MODELS\models\"
            Show-SimNt "Modeles : $ml"
            Show-SimNt "Arret Ollama -> copie -> redemarrage Ollama (~10-30 min)"
        } else {
            Show-SimWn "Backup absent - TELECHARGERAIT ~47 GB via ollama pull (30-90 min) :"
            @("phi4:14b (8.4 GB) [ACTIF]","deepseek-r1:14b (8.4 GB)",
              "qwen2.5:14b (8.4 GB)","gemma4:latest (7.6 GB)","llava-phi3:latest (2.9 GB)",
              "mxbai-embed-large (670 MB) [embed RAG]") |
              ForEach-Object { Show-SimNt "  ollama pull $_" }
        }
    }

    function Sim-Etape3 {
        Show-SimHd "ETAPE 3  -  Packages Python"
        if (-not (Test-Path $PYTHON_PATH)) {
            Show-SimWn "Python absent - pip install impossible (dependance etape 1)"; return
        }
        $pkgs = @(
            @{ p = "flask==3.1.3";            m = "flask" },
            @{ p = "flask-cors==6.0.2";       m = "flask_cors" },
            @{ p = "flask-limiter==4.1.1";    m = "flask_limiter" },
            @{ p = "edge-tts==7.2.7";         m = "edge_tts" },
            @{ p = "faster-whisper==1.2.1";   m = "faster_whisper" },
            @{ p = "pynvml";                  m = "pynvml" },
            @{ p = "psutil==7.2.2";           m = "psutil" },
            @{ p = "requests==2.32.5";        m = "requests" },
            @{ p = "pyttsx3==2.99";           m = "pyttsx3" },
            @{ p = "piper-tts==1.4.1";        m = "piper" },
            @{ p = "DeepFilterNet==0.5.6";    m = "df" },
            @{ p = "numpy==1.26.4";           m = "numpy" },
            @{ p = "scipy==1.17.1";           m = "scipy" },
            @{ p = "ctranslate2";             m = "ctranslate2" },
            @{ p = "paramiko==4.0.0";         m = "paramiko" },
            @{ p = "cryptography==46.0.6";    m = "cryptography" },
            @{ p = "huggingface_hub==1.7.1";  m = "huggingface_hub" }
        )
        $eap = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
        foreach ($e in $pkgs) {
            $null = & $PYTHON_PATH -c "import $($e.m)" 2>$null
            if ($LASTEXITCODE -eq 0) { Show-SimOk "Deja installe : $($e.p) - aucune action" }
            else                      { Show-SimWn "INSTALLERAIT  : pip install $($e.p)" }
        }
        $ErrorActionPreference = $eap
    }

    function Sim-Etape4 {
        Show-SimHd "ETAPE 4  -  PyTorch CUDA 12.8"
        if (-not (Test-Path $PYTHON_PATH)) {
            Show-SimWn "Python absent - PyTorch impossible (dependance etape 1)"; return
        }
        $tv = $null
        try { $tv = (& $PYTHON_PATH -c "import torch; print(torch.__version__)" 2>&1).Trim() } catch {}
        if ($tv -and ($tv -match "cu128")) {
            Show-SimOk "PyTorch $tv deja installe - aucune action"
        } elseif ($tv) {
            Show-SimWn "PyTorch $tv present mais cu128 requis"
            Show-SimNt "REINSTALLERAIT : pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 torchvision==0.22.1+cu128"
            Show-SimNt "Index : https://download.pytorch.org/whl/cu128"
        } else {
            Show-SimWn "PyTorch absent - TELECHARGERAIT ~4 GB depuis download.pytorch.org/whl/cu128"
            Show-SimNt "pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 torchvision==0.22.1+cu128"
        }
    }

    function Sim-Etape5 {
        Show-SimHd "ETAPE 5  -  Fichiers JARVIS"
        $bkJ  = "$BACKUP_ROOT\JARVIS"
        $cfgs = @("scripts\jarvis_system_prompt.txt","scripts\jarvis_prompt_profiles.json",
                  "scripts\jarvis_model.json","scripts\jarvis_llm_params.json",
                  "scripts\jarvis_dsp_params.json")
        if (Test-Path $bkJ) {
            $sz = [math]::Round(
                (Get-ChildItem $bkJ -Recurse -ErrorAction SilentlyContinue |
                 Measure-Object -Property Length -Sum).Sum / 1MB, 1)
            if (Test-Path $JARVIS_ROOT) { Show-SimOk "ECRASERAIT $JARVIS_ROOT depuis backup ($sz MB)" }
            else                         { Show-SimOk "COPIERAIT $bkJ -> $JARVIS_ROOT ($sz MB) - creation dossier" }
            foreach ($f in $cfgs) {
                if (Test-Path (Join-Path $bkJ $f)) { Show-SimOk "Config dans backup : $f" }
                else                                { Show-SimWn "Config absente du backup : $f - cree au 1er demarrage" }
            }
        } elseif (Test-Path $JARVIS_ROOT) {
            Show-SimOk "JARVIS deja present sur C: - aucune copie (backup absent)"
            foreach ($f in $cfgs) {
                if (Test-Path (Join-Path $JARVIS_ROOT $f)) { Show-SimOk "Config presente : $f" }
                else                                        { Show-SimWn "Config absente : $f - cree au 1er demarrage" }
            }
        } else { Show-SimFl "Backup ABSENT et JARVIS_ROOT absent - ECHEC restauration" }
    }

    function Sim-Etape6 {
        Show-SimHd "ETAPE 6  -  Cles SSH"
        $bkS  = "$BACKUP_ROOT\SSH"
        $sshD = "C:\Users\$env:USERNAME\.ssh"
        if (Test-Path $bkS) {
            $keys = Get-ChildItem $bkS -File -ErrorAction SilentlyContinue
            Show-SimOk "COPIERAIT $($keys.Count) fichiers : $bkS -> $sshD"
            $keys | ForEach-Object { Show-SimNt "  $($_.Name)" }
            $priv = $keys | Where-Object { $_.Name -notmatch "\.pub$" -and
                                           $_.Name -notmatch "known_hosts|config" }
            Show-SimNt "icacls (lecture seule owner) sur $($priv.Count) cles privees :"
            Show-SimNt "  $($priv.Name -join ', ')"
        } else { Show-SimFl "Backup SSH absent ($bkS) - ECHEC restauration cles" }
    }

    function Sim-Etape7 {
        Show-SimHd "ETAPE 7  -  Memoire Claude Code"
        $bkC  = "$BACKUP_ROOT\CLAUDE-MEMORY"
        $clD  = "C:\Users\$env:USERNAME\.claude"
        if (Test-Path $bkC) {
            $sz = [math]::Round(
                (Get-ChildItem $bkC -Recurse -ErrorAction SilentlyContinue |
                 Measure-Object -Property Length -Sum).Sum / 1MB, 1)
            if (Test-Path $clD) {
                Show-SimOk "FUSIONNERAIT (Copy -Force) $bkC -> $clD ($sz MB)"
                Show-SimNt "Fichiers backup ecraseront les existants dans .claude"
            } else { Show-SimOk "COPIERAIT $bkC -> $clD ($sz MB) - creation dossier" }
        } else { Show-SimWn "Backup Claude absent ($bkC) - memoire sera perdue (non bloquant)" }
    }

    function Sim-Etape8 {
        Show-SimHd "ETAPE 8  -  Raccourcis bureau"
        Show-SimOk "CREERAIT raccourci : JARVIS Dashboard.lnk  ->  http://localhost:5000"
        $bkJ = "$BACKUP_ROOT\JARVIS"
        foreach ($pair in @(
            @{ lnk = "JARVIS - Arret.lnk";     bat = "stop_jarvis.bat" },
            @{ lnk = "JARVIS - Demarrage.lnk"; bat = "start_dashboard.bat" }
        )) {
            $local = Join-Path $JARVIS_ROOT $pair.bat
            $bkup  = Join-Path $bkJ         $pair.bat
            if ((Test-Path $local) -or (Test-Path $bkup)) {
                Show-SimOk "CREERAIT raccourci : $($pair.lnk)  ->  $($pair.bat)"
            } else { Show-SimWn "$($pair.bat) absent - raccourci $($pair.lnk) non cree" }
        }
    }

    Sim-Etape0; Sim-Etape1; Sim-Etape2; Sim-Etape3; Sim-Etape4
    Sim-Etape5; Sim-Etape6; Sim-Etape7; Sim-Etape8

    $rptSim.Add(""); $rptSim.Add("=" * 60)
    $rptSim.Add("SCORE : $simOk SIM-OK  /  $simWarn WARN  /  $simFail FAIL")
    $verdS = if ($simFail -eq 0 -and $simWarn -eq 0) { "RESTAURATION NOMINALE  -  toutes etapes sans obstacle" }
             elseif ($simFail -eq 0)                  { "RESTAURATION POSSIBLE  -  verifier les WARN" }
             else                                      { "RESTAURATION BLOQUEE   -  corriger les FAIL avant" }
    $rptSim.Add("VERDICT : $verdS")
    Write-Host ""
    Write-Host "  --------------------------------------------------" -ForegroundColor Cyan
    $colS = if ($simFail -gt 0) { "Red" } elseif ($simWarn -gt 0) { "Yellow" } else { "Green" }
    Write-Host ("  SCORE : {0} SIM-OK  /  {1} WARN  /  {2} FAIL" -f $simOk, $simWarn, $simFail) -ForegroundColor $colS
    Write-Host "  VERDICT : $verdS" -ForegroundColor $colS
    Write-Host "  --------------------------------------------------" -ForegroundColor Cyan
    Write-Host ""
    $rptSim | Set-Content -Path $REPORT_SIM -Encoding UTF8
    Write-Host "  Rapport sauvegarde : $REPORT_SIM" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Simulation terminee  -  aucune modification effectuee." -ForegroundColor Magenta
    Write-Host "  Pour restaurer reellement : [14] Restauration dans JARVIS-menu.ps1" -ForegroundColor White
    Write-Host ""
    exit 0
}

# ══════════════════════════════════════════════════════════════
# ETAPE 0  -  Pilotes NVIDIA + CUDA
# Prerequis GPU avant Python/PyTorch  -  sans driver valide,
# DeepFilterNet et PyTorch CUDA seront inutilisables.
# ══════════════════════════════════════════════════════════════
Write-Title "ETAPE 0  -  Pilotes NVIDIA + CUDA"

# Driver minimum pour CUDA 12.8 (Windows) et RTX 5080 Blackwell
$DRIVER_MIN_CUDA128 = 528.33
$DRIVER_MIN_RTX5080 = 572.00

# ── 0a : Localiser nvidia-smi ─────────────────────────────────
$nvidiaSmi = $null
$nvSmiCandidates = @(
    "$env:SystemRoot\System32\nvidia-smi.exe",
    "C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"
)
foreach ($p in $nvSmiCandidates) {
    if (Test-Path $p) { $nvidiaSmi = $p; break }
}
if (-not $nvidiaSmi) {
    try { $nvidiaSmi = (Get-Command nvidia-smi -ErrorAction Stop).Source } catch {}
}

if ($nvidiaSmi) {
    $smiOut = & $nvidiaSmi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1
    $smiLine = ($smiOut | Select-Object -First 1).Trim()
    Write-OK "nvidia-smi detecte"
    Write-INFO "GPU : $smiLine"
    Log "nvidia-smi OK : $smiLine"

    # Parser la version driver (2e champ CSV)
    $fields = $smiLine -split ",\s*"
    if ($fields.Count -ge 2) {
        $driverStr = $fields[1].Trim()
        $driverVer = 0.0
        if ([double]::TryParse($driverStr, [System.Globalization.NumberStyles]::Any,
            [System.Globalization.CultureInfo]::InvariantCulture, [ref]$driverVer)) {

            if ($driverVer -lt $DRIVER_MIN_CUDA128) {
                Write-FAIL  "Driver $driverVer < $DRIVER_MIN_CUDA128  -  CUDA 12.8 NON supporte"
                Write-WARN  "Mettre a jour depuis : https://www.nvidia.com/drivers"
                Write-WARN  "JARVIS / PyTorch CUDA NE FONCTIONNERA PAS sans mise a jour"
                Log "FAIL Driver trop vieux : $driverVer (min $DRIVER_MIN_CUDA128)"
            } elseif ($driverVer -lt $DRIVER_MIN_RTX5080) {
                Write-WARN  "Driver $driverVer  -  verifier compatibilite RTX 5080 (recommande >= $DRIVER_MIN_RTX5080)"
                Write-INFO  "Telecharger : https://www.nvidia.com/drivers"
                Log "WARN Driver recommande RTX5080 non atteint : $driverVer"
            } else {
                Write-OK    "Driver $driverVer  -  compatible CUDA 12.8 + RTX 5080 Blackwell"
                Log "Driver OK : $driverVer"
            }
        } else {
            Write-WARN "Impossible de parser la version driver : '$driverStr'"
            Log "WARN parse driver failed : $driverStr"
        }
    }
} else {
    # nvidia-smi absent  -  pilote non installe
    Write-WARN "nvidia-smi introuvable  -  pilote NVIDIA absent"
    Log "WARN nvidia-smi absent"

    $wingetOk = $false
    try { $null = Get-Command winget -ErrorAction Stop; $wingetOk = $true } catch {}

    # Priorite 1 : installeur en cache dans BACKUP INSTALLERS\
    $nvCached = Get-ChildItem "$BACKUP_ROOT\INSTALLERS" -Filter "*.exe" -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -imatch "nvidia" -or $_.Name -imatch "^\d{3}.*\.exe" } |
                Sort-Object LastWriteTime -Descending |
                Select-Object -First 1

    if ($nvCached) {
        Write-OK "Installeur NVIDIA en cache : $($nvCached.Name)"
        Write-INFO "Installation silencieuse en cours..."
        Log "NVIDIA driver depuis cache : $($nvCached.FullName)"
        Start-Process -FilePath $nvCached.FullName -ArgumentList "-s -noreboot" -Wait
        Write-OK "Pilote NVIDIA installe depuis cache"
        Write-WARN "REDEMARRAGE REQUIS  -  relancer ce script apres le reboot"
        Log "NVIDIA driver installe depuis cache  -  redemarrage requis"
        if (-not $Unattended) { Read-Host "`n  Appuyer sur Entree pour continuer (ou Ctrl+C pour redemarrer d'abord)" }
        else { Write-INFO "Mode sans interruption - poursuite automatique..."; Start-Sleep -Seconds 3 }

    # Priorite 2 : winget
    } elseif ($wingetOk) {
        Write-INFO "Pas de cache NVIDIA  -  tentative via winget..."
        Log "winget install NVIDIA.CUDA"
        winget install --id NVIDIA.CUDA --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Pilote installe via winget"
            Write-WARN "REDEMARRAGE REQUIS  -  relancer ce script apres le reboot"
            Log "Driver installe via winget  -  redemarrage requis"
        } else {
            Write-WARN "winget echec (code $LASTEXITCODE)  -  installation manuelle requise"
            Write-INFO "Telecharger depuis : https://www.nvidia.com/drivers"
            Write-INFO "GPU RTX 5080 Blackwell  -  choisir pilote >= $DRIVER_MIN_RTX5080"
            Log "WARN winget driver echec"
        }
        if (-not $Unattended) { Read-Host "`n  Appuyer sur Entree pour continuer (ou Ctrl+C pour redemarrer d'abord)" }
        else { Write-INFO "Mode sans interruption - poursuite automatique..."; Start-Sleep -Seconds 3 }

    # Priorite 3 : echec total
    } else {
        Write-FAIL "Pilote NVIDIA absent  -  cache vide et winget indisponible"
        Write-INFO "Placer l'installeur .exe NVIDIA dans : $BACKUP_ROOT\INSTALLERS\"
        Write-INFO "Ou telecharger depuis : https://www.nvidia.com/drivers"
        Write-INFO "GPU RTX 5080 Blackwell  -  pilote >= $DRIVER_MIN_RTX5080"
        Log "FAIL Driver absent  -  aucune source disponible"
        if (-not $Unattended) { Read-Host "`n  Appuyer sur Entree pour continuer quand meme (sans GPU)" }
        else { Write-INFO "Mode sans interruption - poursuite sans GPU..."; Start-Sleep -Seconds 3 }
    }
}

# ── 0b : CUDA Toolkit (nvcc)  -  optionnel ──────────────────────
# PyTorch cu128 embarque son propre runtime CUDA.
# nvcc n'est necessaire que pour compiler des extensions custom.
Write-INFO "Verification CUDA Toolkit (nvcc  -  optionnel)..."
$nvccFound = $false
try {
    $nvccOut = & nvcc --version 2>&1
    if ($nvccOut -match "release\s+([\d\.]+)") {
        Write-OK "nvcc $($matches[1]) detecte (CUDA Toolkit installe)"
        Log "nvcc $($matches[1]) OK"
        $nvccFound = $true
    }
} catch {}

if (-not $nvccFound) {
    Write-INFO "nvcc absent  -  non bloquant : PyTorch cu128 embarque son runtime CUDA"
    Write-INFO "Installer si besoin : https://developer.nvidia.com/cuda-downloads"
    Log "nvcc absent  -  non bloquant"
}

# ══════════════════════════════════════════════════════════════
# ETAPE 1  -  Python 3.11
# ══════════════════════════════════════════════════════════════
Write-Title "ETAPE 1  -  Python 3.11"

$pythonOk = $false
if (Test-Path $PYTHON_PATH) {
    $ver = & $PYTHON_PATH --version 2>&1
    if ($ver -match "3\.11") {
        Write-OK "Python 3.11 deja installe : $ver"
        Log "Python deja present : $ver"
        $pythonOk = $true
    }
}

if (-not $pythonOk) {
    # Priorite 1 : installeur en cache (backup INSTALLERS\)
    $pyCached = "$BACKUP_ROOT\INSTALLERS\python-3.11.9-amd64.exe"
    if (Test-Path $pyCached) {
        Write-OK "Python 3.11.9 en cache : $pyCached"
        $PYTHON_EXE = $pyCached
        Log "Python installeur depuis cache : $pyCached"
    } else {
        # Priorite 2 : telechargement internet
        Write-INFO "Pas de cache  -  telechargement Python $PYTHON_VERSION..."
        Log "Telechargement Python $PYTHON_URL"
        try {
            Invoke-WebRequest -Uri $PYTHON_URL -OutFile $PYTHON_EXE -UseBasicParsing -TimeoutSec 120
            Write-OK "Telechargement OK"
            # Mettre en cache pour la prochaine fois
            if (Test-Path "$BACKUP_ROOT\INSTALLERS") {
                Copy-Item -Path $PYTHON_EXE -Destination "$BACKUP_ROOT\INSTALLERS\python-3.11.9-amd64.exe" -Force
                Write-INFO "Installeur mis en cache : $BACKUP_ROOT\INSTALLERS\"
                Log "Python installeur mis en cache"
            }
        } catch {
            Write-FAIL "Echec telechargement Python : $_"
            Log "ERREUR telechargement Python : $_"
            exit 1
        }
    }

    Write-INFO "Installation Python (silencieuse)..."
    Log "Installation Python..."
    $pyInstallArgs = "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1"
    Start-Process -FilePath $PYTHON_EXE -ArgumentList $pyInstallArgs -Wait
    Remove-Item $PYTHON_EXE -Force -ErrorAction SilentlyContinue

    # Recharger PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH", "User")

    if (Test-Path $PYTHON_PATH) {
        Write-OK "Python installe avec succes"
        Log "Python installe OK"
    } else {
        Write-FAIL "Python introuvable apres installation"
        Log "ERREUR Python introuvable : $PYTHON_PATH"
        Write-WARN "Installer manuellement depuis : $PYTHON_URL"
        Write-WARN "Cocher 'Add Python to PATH' puis relancer ce script"
        exit 1
    }
}

# Mise a jour pip
Write-INFO "Mise a jour pip..."
& $PYTHON_PATH -m pip install --upgrade pip --quiet
Write-OK "pip a jour"
Log "pip mis a jour"

# ══════════════════════════════════════════════════════════════
# ETAPE 2  -  Ollama
# ══════════════════════════════════════════════════════════════
Write-Title "ETAPE 2  -  Ollama"

$ollamaOk = $false
try {
    $null = & ollama --version 2>&1
    Write-OK "Ollama deja installe"
    Log "Ollama deja present"
    $ollamaOk = $true
} catch {}

if (-not $ollamaOk) {
    Write-INFO "Telechargement Ollama..."
    Log "Telechargement Ollama"
    try {
        Invoke-WebRequest -Uri $OLLAMA_URL -OutFile $OLLAMA_EXE -UseBasicParsing -TimeoutSec 300
        Write-OK "Telechargement OK"
    } catch {
        Write-FAIL "Echec telechargement Ollama : $_"
        Log "ERREUR telechargement Ollama : $_"
        exit 1
    }

    Write-INFO "Installation Ollama (silencieuse)..."
    Start-Process -FilePath $OLLAMA_EXE -ArgumentList "/S" -Wait
    Remove-Item $OLLAMA_EXE -Force -ErrorAction SilentlyContinue

    # Recharger PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH", "User")

    Write-OK "Ollama installe"
    Log "Ollama installe OK"
}

# ── Modeles LLM  -  restauration depuis backup (independant du statut Ollama)
Write-Title "ETAPE 2b - Modeles LLM Ollama"

$backupOllama = "$BACKUP_ROOT\OLLAMA-MODELS\models"
if (Test-Path $backupOllama) {
    Write-INFO "Sauvegarde modeles trouvee : $backupOllama"
    Write-INFO "Restauration vers $OLLAMA_MODELS\models\ ..."
    Write-INFO "Cela peut prendre 10-30 min selon la vitesse du disque..."
    Log "Restauration modeles depuis $backupOllama"

    # Arreter Ollama avant copie pour eviter les verrous fichiers
    Write-INFO "Arret temporaire Ollama pour la copie..."
    Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    if (-not (Test-Path "$OLLAMA_MODELS\models")) {
        New-Item -ItemType Directory -Path "$OLLAMA_MODELS\models" -Force | Out-Null
    }
    Copy-Item -Path "$backupOllama\*" -Destination "$OLLAMA_MODELS\models" -Recurse -Force

    Write-OK "Modeles restaures"
    $size = (Get-ChildItem "$OLLAMA_MODELS\models" -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    Write-INFO "Taille restauree : $([math]::Round($size/1GB,1)) GB"
    Log "Modeles restaures OK"

    # Redemarrer Ollama
    Write-INFO "Redemarrage Ollama..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    try {
        $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
        $count = $tags.models.Count
        Write-OK "Ollama actif - $count modeles disponibles"
        Log "Ollama redemarre OK - $count modeles"
    } catch {
        Write-WARN "Ollama ne repond pas apres redemarrage - verifier manuellement"
        Log "WARN Ollama ne repond pas apres redemarrage"
    }

} else {
    # Pas de backup - telechargement via ollama pull
    Write-WARN "Pas de sauvegarde dans $backupOllama"
    Write-INFO "Telechargement des modeles depuis Internet (~47 GB, 30-90 min)..."
    Log "Telechargement modeles LLM"

    # Demarrer Ollama si pas actif
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
    } catch {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 5
    }

    $models = @(
        @{ name = "phi4:14b";            size = "8.4 GB";  actif = $true  },
        @{ name = "deepseek-r1:14b";     size = "8.4 GB";  actif = $false },
        @{ name = "qwen2.5:14b";         size = "8.4 GB";  actif = $false },
        @{ name = "gemma4:latest";       size = "7.6 GB";  actif = $false },
        @{ name = "llava-phi3:latest";   size = "2.9 GB";  actif = $false },
        @{ name = "mxbai-embed-large";   size = "670 MB";  actif = $false }
    )

    foreach ($m in $models) {
        $label = if ($m.actif) { " [ACTIF]" } else { "" }
        Write-INFO "Pull $($m.name) ($($m.size))$label..."
        Log "Pull $($m.name)"
        & ollama pull $m.name
        if ($LASTEXITCODE -eq 0) {
            Write-OK "$($m.name) OK"
            Log "$($m.name) OK"
        } else {
            Write-WARN "$($m.name) echec - relancer : ollama pull $($m.name)"
            Log "WARN $($m.name) echec"
        }
    }
}

# ══════════════════════════════════════════════════════════════
# ETAPE 3  -  Packages Python
# ══════════════════════════════════════════════════════════════
Write-Title "ETAPE 3  -  Packages Python"

$packages = @(
    "flask==3.1.3",
    "flask-cors==6.0.2",
    "flask-limiter==4.1.1",
    "edge-tts==7.2.7",
    "faster-whisper==1.2.1",
    "pynvml",
    "psutil==7.2.2",
    "requests==2.32.5",
    "pyttsx3==2.99",
    "piper-tts==1.4.1",
    "DeepFilterNet==0.5.6",
    "numpy==1.26.4",
    "scipy==1.17.1",
    "ctranslate2",
    "paramiko==4.0.0",
    "cryptography==46.0.6",
    "huggingface_hub==1.7.1"
)

foreach ($pkg in $packages) {
    Write-INFO "Installation $pkg..."
    & $PYTHON_PATH -m pip install $pkg --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-OK $pkg
        Log "pip install $pkg OK"
    } else {
        Write-WARN "$pkg echec  -  verifier manuellement"
        Log "WARN pip install $pkg echec"
    }
}

# ── Sync via requirements.txt (source de vérité, garantit la complétude) ──
# Couvre les packages ajoutés depuis la dernière MAJ de cette liste :
# kokoro, mcp, starlette, uvicorn, httpx, flask-sock, rank-bm25,
# librosa, soundfile, miniaudio, loguru, nvidia-ml-py
$REQ_FILE = "$JARVIS_ROOT\requirements.txt"
if (Test-Path $REQ_FILE) {
    Write-Title "ETAPE 3b  -  Sync via requirements.txt"
    Write-INFO "Installation depuis $REQ_FILE (garantit packages a jour)..."
    & $PYTHON_PATH -m pip install -r $REQ_FILE --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-OK "requirements.txt sync"
        Log "pip install -r requirements.txt OK"
    } else {
        Write-WARN "Sync requirements.txt partiel - verifier log"
        Log "WARN pip install -r requirements.txt partiel"
    }
} else {
    Write-WARN "requirements.txt absent - skip sync (paquets ajoutes recents non installes)"
    Log "WARN requirements.txt absent"
}

# ══════════════════════════════════════════════════════════════
# ETAPE 4  -  PyTorch CUDA 12.4
# ══════════════════════════════════════════════════════════════
Write-Title "ETAPE 4  -  PyTorch CUDA 12.8 (RTX 5080 Blackwell sm_120)"

Write-INFO "Installation PyTorch 2.7.1 + torchaudio + torchvision (CUDA 12.8)..."
Write-INFO "Taille ~4 GB  -  patience..."
Log "Installation PyTorch CUDA 12.8"

& $PYTHON_PATH -m pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 torchvision==0.22.1+cu128 `
    --index-url https://download.pytorch.org/whl/cu128 --quiet

if ($LASTEXITCODE -eq 0) {
    Write-OK "PyTorch CUDA 12.8 installe"
    Log "PyTorch CUDA OK"
} else {
    Write-WARN "PyTorch echec  -  installer manuellement :"
    Write-WARN "pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 torchvision==0.22.1+cu128 --index-url https://download.pytorch.org/whl/cu128"
    Log "WARN PyTorch echec"
}

# ══════════════════════════════════════════════════════════════
# ETAPE 5  -  Restauration fichiers JARVIS
# ══════════════════════════════════════════════════════════════
Write-Title "ETAPE 5  -  Fichiers JARVIS"

$backupJarvis = "$BACKUP_ROOT\JARVIS"
if (Test-Path $backupJarvis) {
    Write-INFO "Sauvegarde JARVIS trouvee : $backupJarvis"
    Write-INFO "Restauration vers $JARVIS_ROOT..."
    if (-not (Test-Path $JARVIS_ROOT)) {
        New-Item -ItemType Directory -Path $JARVIS_ROOT -Force | Out-Null
    }
    Copy-Item -Path "$backupJarvis\*" -Destination $JARVIS_ROOT -Recurse -Force
    Write-OK "Fichiers JARVIS restaures"
    Log "JARVIS restaure depuis $backupJarvis"
} elseif (Test-Path $JARVIS_ROOT) {
    Write-OK "Dossier JARVIS deja present : $JARVIS_ROOT"
    Log "JARVIS deja present"
} else {
    Write-WARN "Dossier JARVIS absent et pas de sauvegarde dans $backupJarvis"
    Write-WARN "Cloner depuis Git ou copier manuellement le dossier JARVIS"
    Log "WARN JARVIS absent"
}

# Verifier les fichiers config critiques
Write-INFO "Verification des fichiers de configuration..."
$configs = @(
    "scripts\jarvis_system_prompt.txt",
    "scripts\jarvis_prompt_profiles.json",
    "scripts\jarvis_model.json",
    "scripts\jarvis_llm_params.json",
    "scripts\jarvis_dsp_params.json"
)

foreach ($f in $configs) {
    $fullPath = Join-Path $JARVIS_ROOT $f
    if (Test-Path $fullPath) {
        Write-OK $f
    } else {
        Write-WARN "$f ABSENT  -  sera cree au premier demarrage"
        Log "WARN config absente : $f"
    }
}

# ══════════════════════════════════════════════════════════════
# ETAPE 6  -  Cles SSH
# ══════════════════════════════════════════════════════════════
Write-Title "ETAPE 6  -  Cles SSH"

$backupSSH = "$BACKUP_ROOT\SSH"
$sshDest   = "C:\Users\$env:USERNAME\.ssh"

if (Test-Path $backupSSH) {
    if (-not (Test-Path $sshDest)) {
        New-Item -ItemType Directory -Path $sshDest -Force | Out-Null
    }
    Copy-Item -Path "$backupSSH\*" -Destination $sshDest -Recurse -Force
    Write-OK "Cles SSH restaurees dans $sshDest"
    Log "SSH restaure OK"

    # Lister les cles copiees
    Get-ChildItem $sshDest | ForEach-Object { Write-INFO "  $($_.Name)" }

    # Appliquer les permissions via Git Bash (icacls)
    Write-INFO "Application des permissions SSH (lecture seule owner)..."
    $keys = @("id_nginx","id_clt","id_pa85","id_proxmox")
    foreach ($k in $keys) {
        $kpath = Join-Path $sshDest $k
        if (Test-Path $kpath) {
            icacls $kpath /inheritance:r /grant:r "${env:USERNAME}:R" | Out-Null
            Write-OK "  permissions $k"
            Log "chmod $k OK"
        }
    }
    Write-WARN "Verifier known_hosts apres premier SSH : ssh srv-nginx"
} else {
    Write-WARN "Pas de sauvegarde SSH dans $backupSSH"
    Write-WARN "Copier manuellement les cles dans $sshDest"
    Log "WARN SSH backup absent"
}

# ══════════════════════════════════════════════════════════════
# ETAPE 7  -  Memoire Claude Code
# ══════════════════════════════════════════════════════════════
Write-Title "ETAPE 7  -  Memoire Claude Code"

$backupClaude = "$BACKUP_ROOT\CLAUDE-MEMORY"
$claudeDest   = "C:\Users\$env:USERNAME\.claude"

if (Test-Path $backupClaude) {
    if (Test-Path $claudeDest) {
        Write-INFO ".claude existant  -  fusion (pas d'ecrasement)..."
        Copy-Item -Path "$backupClaude\*" -Destination $claudeDest -Recurse -Force
    } else {
        Copy-Item -Path $backupClaude -Destination $claudeDest -Recurse -Force
    }
    Write-OK "Memoire Claude restauree dans $claudeDest"
    Log "Claude memory restauree OK"
} else {
    Write-WARN "Pas de sauvegarde Claude dans $backupClaude"
    Log "WARN Claude backup absent"
}

# ══════════════════════════════════════════════════════════════
# ETAPE 8  -  Raccourcis bureau
# ══════════════════════════════════════════════════════════════
Write-Title "ETAPE 8  -  Raccourcis bureau"

$desktop = [Environment]::GetFolderPath("Desktop")

# Raccourci JARVIS Dashboard
$wsh = New-Object -ComObject WScript.Shell

$lnkDashboard = $wsh.CreateShortcut("$desktop\JARVIS Dashboard.lnk")
$lnkDashboard.TargetPath = "http://localhost:5000"
$lnkDashboard.Description = "Ouvre JARVIS dans le navigateur"
$lnkDashboard.Save()
Write-OK "Raccourci 'JARVIS Dashboard' cree"
Log "Raccourci JARVIS Dashboard OK"

# Raccourci Arret JARVIS
$stopBat = "$JARVIS_ROOT\stop_jarvis.bat"
if (Test-Path $stopBat) {
    $lnkStop = $wsh.CreateShortcut("$desktop\JARVIS - Arret.lnk")
    $lnkStop.TargetPath = $stopBat
    $lnkStop.WorkingDirectory = $JARVIS_ROOT
    $lnkStop.Description = "Arrete JARVIS (port 5000)"
    $lnkStop.Save()
    Write-OK "Raccourci 'JARVIS - Arret' cree"
    Log "Raccourci JARVIS Arret OK"
} else {
    Write-WARN "stop_jarvis.bat absent  -  raccourci Arret non cree"
    Log "WARN stop_jarvis.bat absent"
}

# Raccourci Demarrage JARVIS
$startBat = "$JARVIS_ROOT\start_dashboard.bat"
if (Test-Path $startBat) {
    $lnkStart = $wsh.CreateShortcut("$desktop\JARVIS - Demarrage.lnk")
    $lnkStart.TargetPath = $startBat
    $lnkStart.WorkingDirectory = $JARVIS_ROOT
    $lnkStart.Description = "Demarre JARVIS (Flask + Ollama)"
    $lnkStart.Save()
    Write-OK "Raccourci 'JARVIS - Demarrage' cree"
    Log "Raccourci JARVIS Demarrage OK"
} else {
    Write-WARN "start_dashboard.bat absent  -  raccourci Demarrage non cree"
    Log "WARN start_dashboard.bat absent"
}

# ══════════════════════════════════════════════════════════════
# BILAN
# ══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |   Installation terminee                          |" -ForegroundColor Cyan
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Etapes effectuees :" -ForegroundColor White
Write-Host "    0. Pilotes NVIDIA + CUDA (detection / winget)" -ForegroundColor Gray
Write-Host "    1. Python 3.11.9" -ForegroundColor Gray
Write-Host "    2. Ollama + modeles LLM" -ForegroundColor Gray
Write-Host "    3. Packages Python (Flask, edge-tts, Whisper...)" -ForegroundColor Gray
Write-Host "    4. PyTorch CUDA 12.8 (cu128  -  RTX 5080 Blackwell)" -ForegroundColor Gray
Write-Host "    5. Fichiers JARVIS" -ForegroundColor Gray
Write-Host "    6. Cles SSH" -ForegroundColor Gray
Write-Host "    7. Memoire Claude Code" -ForegroundColor Gray
Write-Host "    8. Raccourcis bureau" -ForegroundColor Gray
Write-Host ""
Write-Host "  Pour demarrer JARVIS :" -ForegroundColor White
Write-Host "    Double-clic sur 'JARVIS - Demarrage' sur le bureau" -ForegroundColor Yellow
Write-Host "    Ou : $JARVIS_ROOT\start_dashboard.bat" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Puis ouvrir : http://localhost:5000" -ForegroundColor White
Write-Host ""
Write-Host "  Log complet : $LOG" -ForegroundColor Gray
Write-Host ""

Log "=== Installation terminee ==="
