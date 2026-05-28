<#
.SYNOPSIS
    JARVIS - Sauvegarde complète vers D:\BACKUP-WINDOWS\
    0xCyberLiTech - 2026-03-25

.DESCRIPTION
    Sauvegarde tout ce qu'il faut pour réinstaller JARVIS sur un Windows neuf :
    - Fichiers JARVIS (scripts, templates, configs, voices)
    - Modèles Ollama (~47 GB - optionnel, long)
    - Clés SSH
    - Mémoire Claude

    A lancer avant toute réinstallation Windows ou régulièrement.

.NOTES
    Lancer en tant qu'Administrateur.
    D:\BACKUP-WINDOWS doit exister.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Write-Title { param($msg) Write-Host "`n  [$msg]" -ForegroundColor Cyan }
function Write-OK    { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-WARN  { param($msg) Write-Host "  [!!] $msg" -ForegroundColor Yellow }
function Write-INFO  { param($msg) Write-Host "  --> $msg" -ForegroundColor Gray }
function Write-SIZE  { param($path)
    if (Test-Path $path) {
        $size = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue |
                 Measure-Object -Property Length -Sum).Sum
        $mb = [math]::Round($size / 1MB, 1)
        Write-Host "  --> Taille : $mb MB" -ForegroundColor DarkGray
    }
}

# ── Banniere ──────────────────────────────────────────────────
Clear-Host
Write-Host ""
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |   J A R V I S  --  Sauvegarde                   |" -ForegroundColor Cyan
Write-Host "  |   0xCyberLiTech  --  Windows 11 Pro             |" -ForegroundColor Cyan
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# ── Variables ─────────────────────────────────────────────────
$JARVIS_SRC    = "C:\Users\$env:USERNAME\Documents\0xCyberLiTech\JARVIS"
$BACKUP_ROOT   = "D:\BACKUP-WINDOWS"
$BACKUP_JARVIS = "$BACKUP_ROOT\JARVIS"
$BACKUP_OLLAMA = "$BACKUP_ROOT\OLLAMA-MODELS"
$BACKUP_SSH    = "$BACKUP_ROOT\SSH"
$BACKUP_CLAUDE = "$BACKUP_ROOT\CLAUDE-MEMORY"
$OLLAMA_SRC    = "C:\Users\$env:USERNAME\.ollama"
$SSH_SRC       = "C:\Users\$env:USERNAME\.ssh"
$CLAUDE_SRC    = "C:\Users\$env:USERNAME\.claude"
$LOG           = "$env:USERPROFILE\Desktop\jarvis-backup.log"

function Log { param($msg)
    Add-Content -Path $LOG -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" -Encoding UTF8
}

# Verifier destination
if (-not (Test-Path $BACKUP_ROOT)) {
    Write-WARN "D:\BACKUP-WINDOWS absent - creation..."
    New-Item -ItemType Directory -Path $BACKUP_ROOT -Force | Out-Null
    Write-OK "Dossier cree : $BACKUP_ROOT"
}

Log "=== Debut sauvegarde JARVIS ==="

# ══════════════════════════════════════════════════════════════
# 1 - JARVIS (scripts + templates + configs + voices)
# ══════════════════════════════════════════════════════════════
Write-Title "1 - Fichiers JARVIS"

if (-not (Test-Path $JARVIS_SRC)) {
    Write-WARN "Dossier JARVIS source absent : $JARVIS_SRC"
    Log "WARN JARVIS source absent"
} else {
    Write-INFO "Source      : $JARVIS_SRC"
    Write-INFO "Destination : $BACKUP_JARVIS"

    # Nettoyer __pycache__ avant copie
    Get-ChildItem -Path $JARVIS_SRC -Recurse -Directory -Filter "__pycache__" |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    if (Test-Path $BACKUP_JARVIS) {
        Remove-Item $BACKUP_JARVIS -Recurse -Force
    }

    Copy-Item -Path $JARVIS_SRC -Destination $BACKUP_JARVIS -Recurse -Force
    Write-OK "JARVIS sauvegarde"
    Write-SIZE $BACKUP_JARVIS
    Log "JARVIS sauvegarde OK"

    # Verifier les fichiers critiques
    $critiques = @(
        "scripts\start_dashboard.bat",
        "scripts\stop_jarvis.bat",
        "scripts\jarvis.py",
        "scripts\templates\jarvis.html",
        "scripts\jarvis_system_prompt.txt",
        "scripts\jarvis_prompt_profiles.json",
        "scripts\jarvis_model.json",
        "scripts\jarvis_llm_params.json",
        "scripts\jarvis_dsp_params.json",
        "scripts\jarvis_welcome.json"
    )

    Write-INFO "Verification fichiers critiques :"
    foreach ($f in $critiques) {
        $fp = Join-Path $BACKUP_JARVIS $f
        if (Test-Path $fp) {
            Write-OK "  $f"
        } else {
            Write-WARN "  $f ABSENT"
            Log "WARN fichier critique absent : $f"
        }
    }
}

# ══════════════════════════════════════════════════════════════
# 2 - Cles SSH  (C:\Users\mmsab\.ssh -> D:\BACKUP-WINDOWS\SSH)
# ══════════════════════════════════════════════════════════════
Write-Title "2 - Cles SSH"

if (Test-Path $SSH_SRC) {
    $srcFiles = Get-ChildItem $SSH_SRC -File | Select-Object -ExpandProperty Name
    if (Test-Path $BACKUP_SSH) { Remove-Item $BACKUP_SSH -Recurse -Force }
    Copy-Item -Path $SSH_SRC -Destination $BACKUP_SSH -Recurse -Force
    Write-OK "SSH sauvegarde"
    Log "SSH sauvegarde OK"

    # Verification : chaque fichier source doit etre present dans le backup
    $missing = @()
    foreach ($f in $srcFiles) {
        if (Test-Path (Join-Path $BACKUP_SSH $f)) {
            Write-INFO "  [OK] $f"
        } else {
            Write-WARN "  [!!] $f ABSENT du backup"
            $missing += $f
            Log "WARN SSH key absente du backup : $f"
        }
    }

    if ($missing.Count -eq 0) {
        Write-OK "Toutes les cles SSH copiees ($($srcFiles.Count) fichiers)"
    } else {
        Write-WARN "$($missing.Count) fichier(s) manquant(s) dans le backup"
        Log "SSH backup incomplet : $($missing -join ', ')"
    }
} else {
    Write-WARN "Dossier .ssh absent : $SSH_SRC"
    Log "WARN SSH absent"
}

# ══════════════════════════════════════════════════════════════
# 3 - Memoire Claude
# ══════════════════════════════════════════════════════════════
Write-Title "3 - Memoire Claude Code"

if (Test-Path $CLAUDE_SRC) {
    if (Test-Path $BACKUP_CLAUDE) { Remove-Item $BACKUP_CLAUDE -Recurse -Force }
    Copy-Item -Path $CLAUDE_SRC -Destination $BACKUP_CLAUDE -Recurse -Force
    Write-OK "Claude memory sauvegardee"
    Write-SIZE $BACKUP_CLAUDE
    Log "Claude memory OK"
} else {
    Write-WARN ".claude absent : $CLAUDE_SRC"
    Log "WARN Claude absent"
}

# ══════════════════════════════════════════════════════════════
# 4 - Modeles Ollama (copie complete - obligatoire)
# ══════════════════════════════════════════════════════════════
Write-Title "4 - Modeles Ollama"

if (Test-Path "$OLLAMA_SRC\models") {
    # Lister les modeles presents
    $modeles = Get-ChildItem "$OLLAMA_SRC\models\manifests\registry.ollama.ai\library" -ErrorAction SilentlyContinue
    if ($modeles) {
        Write-INFO "Modeles detectes :"
        foreach ($m in $modeles) { Write-INFO "  $($m.Name)" }
    }

    Write-INFO "Copie en cours... (peut prendre 10-30 min selon la taille)"
    Log "Sauvegarde modeles Ollama demarree"

    if (Test-Path $BACKUP_OLLAMA) { Remove-Item $BACKUP_OLLAMA -Recurse -Force }
    New-Item -ItemType Directory -Path $BACKUP_OLLAMA -Force | Out-Null
    Copy-Item -Path "$OLLAMA_SRC\models" -Destination "$BACKUP_OLLAMA\models" -Recurse -Force

    Write-OK "Modeles Ollama sauvegardes"
    Write-SIZE "$BACKUP_OLLAMA\models"
    Log "Modeles Ollama OK"
} else {
    Write-WARN "Aucun modele Ollama trouve dans $OLLAMA_SRC\models"
    Log "WARN modeles Ollama absents"
}

# ══════════════════════════════════════════════════════════════
# BILAN
# ══════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |   Sauvegarde terminee                            |" -ForegroundColor Cyan
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Contenu sauvegarde dans : $BACKUP_ROOT" -ForegroundColor White
Write-Host ""

Get-ChildItem $BACKUP_ROOT -ErrorAction SilentlyContinue | ForEach-Object {
    # Fix mode strict : Measure-Object retourne $null sur dossier vide → .Sum n'existe pas
    $measured = Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue |
                Measure-Object -Property Length -Sum
    $size = if ($measured) { [long]$measured.Sum } else { 0 }
    $mb = [math]::Round($size / 1MB, 1)
    Write-Host "  $($_.Name.PadRight(20)) $mb MB" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Log : $LOG" -ForegroundColor DarkGray
Write-Host ""

# ══════════════════════════════════════════════════════════════
# 5 - Scripts (auto-copie dans le backup)
# ══════════════════════════════════════════════════════════════
Write-Title "5 - Scripts backup + install"

$docDir = "$JARVIS_SRC\scripts"
$scripts = @("backup-jarvis.ps1", "install-jarvis.ps1")
foreach ($s in $scripts) {
    $src = Join-Path $docDir $s
    $dst = Join-Path $BACKUP_JARVIS $s
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Force
        Write-OK "$s mis a jour dans le backup"
        Log "$s copie OK"
    } else {
        Write-WARN "$s introuvable dans $docDir"
        Log "WARN $s absent"
    }
}

# ══════════════════════════════════════════════════════════════
# 6 - Installeurs (Python + NVIDIA driver)
# Cache les installeurs dans INSTALLERS\ pour reinstallation
# 100% hors-ligne sans avoir a re-telecharger.
# ══════════════════════════════════════════════════════════════
Write-Title "6 - Installeurs (Python + Ollama + pilote NVIDIA)"

$BACKUP_INST = "$BACKUP_ROOT\INSTALLERS"
if (-not (Test-Path $BACKUP_INST)) {
    New-Item -ItemType Directory -Path $BACKUP_INST -Force | Out-Null
}

# ── 6a : Python 3.11.9 ────────────────────────────────────────
$pyDest = "$BACKUP_INST\python-3.11.9-amd64.exe"
$pyUrl  = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"

if (Test-Path $pyDest) {
    $pySize = [math]::Round((Get-Item $pyDest).Length / 1MB, 1)
    Write-OK "Python 3.11.9 deja en cache ($pySize MB) — skip"
    Log "Python installeur deja present : $pyDest"
} else {
    Write-INFO "Telechargement Python 3.11.9 (~25 MB)..."
    Log "Telechargement Python : $pyUrl"
    try {
        Invoke-WebRequest -Uri $pyUrl -OutFile $pyDest -UseBasicParsing -TimeoutSec 120
        $pySize = [math]::Round((Get-Item $pyDest).Length / 1MB, 1)
        Write-OK "Python 3.11.9 cache ($pySize MB) : $pyDest"
        Log "Python installeur telecharge OK"
    } catch {
        Write-WARN "Echec telechargement Python : $_"
        Log "WARN Python telechargement echec : $_"
    }
}

# ── 6b : Pilote NVIDIA ────────────────────────────────────────
# Strategie :
#  1. Chercher un installeur NVIDIA deja present (Downloads + Bureau)
#  2. Copier si trouve
#  3. Sinon : noter la version driver actuelle dans nvidia-driver-version.txt
#     (l'utilisateur telecharge manuellement si besoin)
Write-INFO "Recherche installeur pilote NVIDIA..."

$nvDriverDest = $null
$nvDriverSrc  = $null

# Chercher d'abord dans le dossier backup (deja en cache), puis Downloads/Bureau
$searchDirs = @(
    $BACKUP_INST,
    "$env:USERPROFILE\Downloads",
    "$env:USERPROFILE\Desktop",
    "$env:TEMP"
)
$nvPatterns = @("*nvidia*setup*.exe", "*nvidia*driver*.exe", "*nvidia*game*.exe", "*nvidiagfxs*.exe", "522*.exe", "528*.exe", "537*.exe", "551*.exe", "560*.exe", "572*.exe", "576*.exe", "595*.exe", "600*.exe")

foreach ($dir in $searchDirs) {
    if (Test-Path $dir) {
        foreach ($pat in $nvPatterns) {
            $found = Get-ChildItem -Path $dir -Filter $pat -ErrorAction SilentlyContinue |
                     Sort-Object LastWriteTime -Descending |
                     Select-Object -First 1
            if ($found) { $nvDriverSrc = $found.FullName; break }
        }
    }
    if ($nvDriverSrc) { break }
}

if ($nvDriverSrc) {
    $nvFileName = Split-Path $nvDriverSrc -Leaf
    $nvDriverDest = "$BACKUP_INST\$nvFileName"
    if (Test-Path $nvDriverDest) {
        Write-OK "Pilote NVIDIA deja en cache : $nvFileName — skip"
        Log "NVIDIA installeur deja present : $nvDriverDest"
    } else {
        $nvSize = [math]::Round((Get-Item $nvDriverSrc).Length / 1MB, 0)
        Write-INFO "Copie $nvFileName ($nvSize MB)..."
        Copy-Item -Path $nvDriverSrc -Destination $nvDriverDest -Force
        Write-OK "Pilote NVIDIA cache : $nvDriverDest"
        Log "NVIDIA installeur copie OK : $nvFileName"
    }
} else {
    Write-WARN "Aucun installeur NVIDIA trouve dans Downloads/Bureau"

    # Sauvegarder la version driver actuelle pour reference
    $nvVerFile = "$BACKUP_INST\nvidia-driver-version.txt"
    $nvSmi = $null
    try { $nvSmi = (Get-Command nvidia-smi -ErrorAction Stop).Source } catch {}
    if (-not $nvSmi -and (Test-Path "$env:SystemRoot\System32\nvidia-smi.exe")) {
        $nvSmi = "$env:SystemRoot\System32\nvidia-smi.exe"
    }

    if ($nvSmi) {
        $smiOut  = & $nvSmi --query-gpu=name,driver_version --format=csv,noheader 2>&1
        $verLine = ($smiOut | Select-Object -First 1).Trim()
        $content = @"
GPU detecte    : $verLine
Date backup    : $(Get-Date -Format 'yyyy-MM-dd HH:mm')
URL drivers    : https://www.nvidia.com/drivers
Minimum CUDA12.8 : driver >= 528.33
Recommande RTX5080 : driver >= 572.00

Pour recuperer l'installeur manuellement :
  1. Aller sur https://www.nvidia.com/drivers
  2. Selectionner RTX 5080 + Windows 11 + Studio/Game Driver
  3. Telecharger et copier ici : D:\BACKUP-WINDOWS\INSTALLERS\
"@
        Set-Content -Path $nvVerFile -Value $content -Encoding UTF8
        Write-OK "Version driver sauvegardee : $verLine → $nvVerFile"
        Log "NVIDIA version notee : $verLine"
    } else {
        "nvidia-smi absent au moment du backup — telecharger manuellement depuis https://www.nvidia.com/drivers" |
            Set-Content -Path $nvVerFile -Encoding UTF8
        Write-WARN "nvidia-smi absent — fichier de reference cree : $nvVerFile"
        Log "WARN nvidia-smi absent au backup"
    }
    Write-INFO "Placer l'installeur .exe NVIDIA dans : $BACKUP_INST\"
}

# ── 6c : Ollama (installeur OllamaSetup.exe) ──────────────────
# Cache l'installeur Ollama (le binaire) pour une reinstall 100% hors-ligne.
# Les modeles, eux, sont dans OLLAMA-MODELS\. install-jarvis.ps1 utilise ce
# cache en priorite avant tout telechargement internet.
$olDest = "$BACKUP_INST\OllamaSetup.exe"
$olUrl  = "https://ollama.com/download/OllamaSetup.exe"
if (Test-Path $olDest) {
    $olSize = [math]::Round((Get-Item $olDest).Length / 1MB, 1)
    Write-OK "Ollama installeur deja en cache ($olSize MB) — skip"
    Log "Ollama installeur deja present : $olDest"
} else {
    Write-INFO "Telechargement installeur Ollama (~700 MB, peut prendre quelques min)..."
    Log "Telechargement Ollama installeur : $olUrl"
    try {
        Invoke-WebRequest -Uri $olUrl -OutFile $olDest -UseBasicParsing -TimeoutSec 600
        $olSize = [math]::Round((Get-Item $olDest).Length / 1MB, 1)
        Write-OK "Ollama installeur cache ($olSize MB) : $olDest"
        Log "Ollama installeur telecharge OK"
    } catch {
        Write-WARN "Echec telechargement Ollama installeur : $_"
        Log "WARN Ollama installeur telechargement echec : $_"
    }
}

# ── Bilan installeurs ─────────────────────────────────────────
Write-INFO "Contenu INSTALLERS\ :"
Get-ChildItem $BACKUP_INST -ErrorAction SilentlyContinue | ForEach-Object {
    $sz = [math]::Round($_.Length / 1MB, 1)
    Write-INFO "  $($_.Name.PadRight(45)) $sz MB"
}

Log "=== Sauvegarde terminee ==="

