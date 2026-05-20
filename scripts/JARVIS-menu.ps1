<#
.SYNOPSIS
    JARVIS - Menu maintenance et DR
    0xCyberLiTech - v1.5.0 - 2026-05-10

.DESCRIPTION
    --- CONTROLE ---
    [1]  Statut complet (Flask, Ollama, GPU, modele, DSP)
    [2]  Demarrer JARVIS
    [3]  Arreter JARVIS
    [4]  Redemarrer JARVIS

    --- CONFIGURATION ---
    [5]  Modeles LLM Ollama (lister / changer / pull / supprimer)
    [6]  Parametres LLM (temp, ctx, predict...)
    [7]  Profils prompt (voir profils + prompt actif)
    [8]  DSP Audio + moteur TTS (voir / changer moteur)

    --- MAINTENANCE ---
    [9]  Packages pip (lister / mettre a jour / installer)
    [10] Logs (start / stop / tts / backup)
    [11] Nettoyage (__pycache__, logs anciens)

    --- DR - SAUVEGARDE / RESTAURATION ---
    [12] Sauvegarde complete -> D:\BACKUP-WINDOWS
         (JARVIS + Ollama + SSH + Claude + installeurs)
    [13] Verification sauvegarde (DryRun - aucune action)
    [14] Restauration complete (zero intervention)
         (Python, Ollama, packages, PyTorch, JARVIS, SSH, Claude, raccourcis)

    --- ACCES RAPIDE ---
    [15] Test API JARVIS (routes cles)
    [16] Ouvrir interface http://localhost:5000

    [q]  Quitter

.NOTES
    Version : 1.4.0 - 2026-05-01
    Restauration : [14] appelle install-jarvis.ps1 -Unattended
    Aucune intervention manuelle requise pendant la restauration.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding            = [System.Text.Encoding]::UTF8

# ── Constantes ─────────────────────────────────────────────────
$JARVIS_ROOT    = "C:\Users\$env:USERNAME\Documents\0xCyberLiTech\JARVIS"
$JARVIS_SCR     = "$JARVIS_ROOT\scripts"
$PYTHON         = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
$BACKUP_ROOT    = "D:\BACKUP-WINDOWS"
$BACKUP_JARVIS  = "$BACKUP_ROOT\JARVIS"
$INSTALL_SCR    = "$JARVIS_SCR\install-jarvis.ps1"
$INSTALL_BAK    = "$BACKUP_JARVIS\scripts\install-jarvis.ps1"
$BACKUP_SCR     = "$JARVIS_SCR\backup-jarvis.ps1"
$JARVIS_URL     = "http://localhost:5000"
$OLLAMA_URL     = "http://localhost:11434"

# ── Helpers ────────────────────────────────────────────────────
function Write-Title { param($msg)
    Write-Host "`n  +--------------------------------------------------+" -ForegroundColor Cyan
    Write-Host "  |  $($msg.PadRight(49))|" -ForegroundColor Cyan
    Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
}
function Write-OK   { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-WARN { param($msg) Write-Host "  [!!] $msg" -ForegroundColor Yellow }
function Write-FAIL { param($msg) Write-Host "  [XX] $msg" -ForegroundColor Red }
function Write-INFO { param($msg) Write-Host "  --> $msg" -ForegroundColor Gray }
function Write-SEP  { Write-Host "  --------------------------------------------------" -ForegroundColor DarkGray }

function Wait-Key {
    Write-Host ""
    Read-Host "  [Entree] retour menu"
}

function Confirm-Action { param($msg)
    Write-Host "  /!\ $msg" -ForegroundColor Yellow
    $r = Read-Host "  [oui] confirmer  [non] annuler"
    return ($r.ToLower() -eq "oui")
}

function Get-JarvisStatus {
    $s = @{ flask = $false; ollama = $false; model = "?"; gpu = "?"; uptime = "?" }
    try {
        $j = Invoke-RestMethod "$JARVIS_URL/api/stats" -TimeoutSec 3
        $s.flask  = $true
        $s.gpu    = "$($j.temp)C  $($j.gpu_util)%  $([math]::Round($j.mem_used,1))/$([math]::Round($j.mem_total,1)) GB"
        $s.uptime = $j.uptime
    } catch {}
    try { $null = Invoke-RestMethod "$OLLAMA_URL/api/tags" -TimeoutSec 3; $s.ollama = $true } catch {}
    try {
        $m = Get-Content "$JARVIS_SCR\jarvis_model.json" -Raw | ConvertFrom-Json
        $s.model = $m.model
    } catch {}
    return $s
}

function Show-StatusBar {
    $s = Get-JarvisStatus
    $fColor = if ($s.flask)  { "Green" } else { "Red" }
    $oColor = if ($s.ollama) { "Green" } else { "Red" }
    $fLabel = if ($s.flask)  { "ONLINE" } else { "OFFLINE" }
    $oLabel = if ($s.ollama) { "ONLINE" } else { "OFFLINE" }
    Write-Host ""
    Write-Host "  JARVIS : " -NoNewline; Write-Host $fLabel -ForegroundColor $fColor -NoNewline
    Write-Host "   Ollama : " -NoNewline; Write-Host $oLabel -ForegroundColor $oColor -NoNewline
    Write-Host "   Modele : " -NoNewline; Write-Host $s.model -ForegroundColor Cyan
    Write-Host ""
}

function Show-MainMenu {
    Clear-Host
    Write-Host ""
    Write-Host "  +==================================================+" -ForegroundColor Cyan
    Write-Host "  |   J A R V I S  --  Menu Maintenance  v1.5.0    |" -ForegroundColor Cyan
    Write-Host "  |   0xCyberLiTech                                 |" -ForegroundColor Cyan
    Write-Host "  +==================================================+" -ForegroundColor Cyan
    Show-StatusBar
    Write-Host "  --- Controle ---" -ForegroundColor DarkCyan
    Write-Host "  [1]  Statut complet" -ForegroundColor White
    Write-Host "  [2]  Demarrer JARVIS" -ForegroundColor White
    Write-Host "  [3]  Arreter JARVIS" -ForegroundColor White
    Write-Host "  [4]  Redemarrer JARVIS" -ForegroundColor White
    Write-Host ""
    Write-Host "  --- Configuration ---" -ForegroundColor DarkCyan
    Write-Host "  [5]  Modeles LLM Ollama" -ForegroundColor White
    Write-Host "  [6]  Parametres LLM" -ForegroundColor White
    Write-Host "  [7]  Profils prompt" -ForegroundColor White
    Write-Host "  [8]  DSP Audio + moteur TTS" -ForegroundColor White
    Write-Host ""
    Write-Host "  --- Maintenance ---" -ForegroundColor DarkCyan
    Write-Host "  [9]  Packages pip" -ForegroundColor White
    Write-Host "  [10] Logs JARVIS" -ForegroundColor White
    Write-Host "  [11] Nettoyage" -ForegroundColor White
    Write-Host ""
    Write-Host "  --- DR - Sauvegarde / Restauration ---" -ForegroundColor DarkCyan
    Write-Host "  [12] Sauvegarde complete     ->  D:\BACKUP-WINDOWS" -ForegroundColor Green
    Write-Host "       (JARVIS + Ollama + SSH + Claude + installeurs)" -ForegroundColor DarkGray
    Write-Host "  [13] Verification / Simulation   (DryRun + DryRunRestore)" -ForegroundColor Yellow
    Write-Host "  [14] Restauration complete       (zero intervention)" -ForegroundColor Red
    Write-Host "       (Python, Ollama, JARVIS, SSH, Claude, raccourcis)" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  --- Acces rapide ---" -ForegroundColor DarkCyan
    Write-Host "  [15] Test API JARVIS" -ForegroundColor White
    Write-Host "  [16] Ouvrir interface web" -ForegroundColor White
    Write-Host ""
    Write-Host "  [q]  Quitter" -ForegroundColor DarkGray
    Write-Host ""
}

# ══════════════════════════════════════════════════════════════
# [1] STATUT COMPLET
# ══════════════════════════════════════════════════════════════
function Invoke-Statut {
    Write-Title "STATUT JARVIS"
    Write-Host ""
    try {
        $s = Invoke-RestMethod "$JARVIS_URL/api/stats" -TimeoutSec 3
        Write-OK "Flask     : ONLINE  (localhost:5000)"
        Write-INFO "Uptime    : $($s.uptime)"
        Write-INFO "GPU       : $($s.name)"
        Write-INFO "GPU Temp  : $($s.temp)C  |  Util : $($s.gpu_util)%  |  P-state : P$($s.p_state)"
        Write-INFO "VRAM      : $([math]::Round($s.mem_used,2)) / $([math]::Round($s.mem_total,2)) GB"
        Write-INFO "CPU       : $($s.cpu)%  ($($s.cpu_count) coeurs @ $($s.cpu_freq) MHz)"
        Write-INFO "RAM       : $([math]::Round($s.ram_used,1)) / $([math]::Round($s.ram_total,1)) GB"
    } catch { Write-FAIL "Flask     : OFFLINE" }
    Write-Host ""
    try {
        $tags = Invoke-RestMethod "$OLLAMA_URL/api/tags" -TimeoutSec 3
        Write-OK "Ollama    : ONLINE  (localhost:11434)  -  $($tags.models.Count) modeles"
        foreach ($m in $tags.models) {
            Write-INFO "  $($m.name.PadRight(32)) $([math]::Round($m.size/1GB,1)) GB"
        }
    } catch { Write-FAIL "Ollama    : OFFLINE" }
    Write-Host ""
    try {
        $m = Get-Content "$JARVIS_SCR\jarvis_model.json" -Raw | ConvertFrom-Json
        Write-INFO "Modele actif : $($m.model)"
    } catch {}
    try {
        $d = Get-Content "$JARVIS_SCR\jarvis_dsp_params.json" -Raw | ConvertFrom-Json
        Write-INFO "TTS Engine   : $($d.tts_engine)  |  DSP : $($d.enabled)  |  DeepFilter : $($d.df_enabled)"
    } catch {}
    Write-INFO "Provider     : LOCAL // OLLAMA"
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [2] DEMARRER
# ══════════════════════════════════════════════════════════════
function Invoke-Demarrer {
    Write-Title "DEMARRER JARVIS"
    Write-Host ""
    try {
        $null = Invoke-RestMethod "$JARVIS_URL/api/stats" -TimeoutSec 2
        Write-OK "JARVIS est deja en cours d'execution"
        Write-INFO "Ouvrir : $JARVIS_URL"
        Wait-Key; return
    } catch {}
    try {
        $null = Invoke-RestMethod "$OLLAMA_URL/api/tags" -TimeoutSec 2
        Write-OK "Ollama deja actif"
    } catch {
        Write-INFO "Demarrage Ollama..."
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 4
        Write-OK "Ollama demarre"
    }
    Write-INFO "Demarrage JARVIS..."
    if (-not (Test-Path $PYTHON)) { Write-FAIL "Python introuvable : $PYTHON"; Wait-Key; return }
    Start-Process -FilePath $PYTHON -ArgumentList "$JARVIS_SCR\jarvis.py" `
        -WorkingDirectory $JARVIS_SCR -WindowStyle Minimized
    Write-INFO "Attente Flask (max 15s)..."
    $ok = $false
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        try { $null = Invoke-RestMethod "$JARVIS_URL/api/stats" -TimeoutSec 1; $ok = $true; break } catch {}
    }
    if ($ok) { Write-OK "JARVIS en ligne : $JARVIS_URL"; Start-Process $JARVIS_URL }
    else      { Write-WARN "JARVIS ne repond pas apres 15s - verifier jarvis-start.log" }
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [3] ARRETER
# ══════════════════════════════════════════════════════════════
function Invoke-Arreter {
    Write-Title "ARRETER JARVIS"
    Write-Host ""
    $pid5000 = (netstat -ano 2>$null | Select-String ":5000 " | Select-String "LISTENING" |
                ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
    if ($pid5000) {
        Stop-Process -Id $pid5000 -Force -ErrorAction SilentlyContinue
        Write-OK "JARVIS arrete (PID $pid5000)"
    } else { Write-WARN "JARVIS n'etait pas en cours d'execution" }
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [4] REDEMARRER
# ══════════════════════════════════════════════════════════════
function Invoke-Redemarrer {
    Write-Title "REDEMARRER JARVIS"
    Write-Host ""
    Write-INFO "Arret..."
    $pid5000 = (netstat -ano 2>$null | Select-String ":5000 " | Select-String "LISTENING" |
                ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
    if ($pid5000) { Stop-Process -Id $pid5000 -Force -ErrorAction SilentlyContinue; Write-OK "Arrete (PID $pid5000)"; Start-Sleep -Seconds 2 }
    Write-INFO "Redemarrage..."
    if (-not (Test-Path $PYTHON)) { Write-FAIL "Python introuvable : $PYTHON"; Wait-Key; return }
    Start-Process -FilePath $PYTHON -ArgumentList "$JARVIS_SCR\jarvis.py" `
        -WorkingDirectory $JARVIS_SCR -WindowStyle Minimized
    $ok = $false
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        try { $null = Invoke-RestMethod "$JARVIS_URL/api/stats" -TimeoutSec 1; $ok = $true; break } catch {}
    }
    if ($ok) { Write-OK "JARVIS en ligne : $JARVIS_URL" }
    else      { Write-WARN "JARVIS ne repond pas - verifier manuellement" }
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [5] MODELES LLM
# ══════════════════════════════════════════════════════════════
function Invoke-ModelesLLM {
    while ($true) {
        Clear-Host
        Write-Title "MODELES LLM OLLAMA"
        Write-Host ""
        try {
            $m = Get-Content "$JARVIS_SCR\jarvis_model.json" -Raw | ConvertFrom-Json
            Write-INFO "Modele actif : $($m.model)"
        } catch { Write-WARN "jarvis_model.json illisible" }
        Write-Host ""
        $liste = @()
        try {
            $tags = Invoke-RestMethod "$OLLAMA_URL/api/tags" -TimeoutSec 3
            Write-INFO "Modeles disponibles :"
            $i = 1
            foreach ($mod in $tags.models) {
                Write-Host "    [$i] $($mod.name.PadRight(32)) $([math]::Round($mod.size/1GB,1)) GB" -ForegroundColor White
                $liste += $mod.name; $i++
            }
        } catch { Write-WARN "Ollama non accessible"; Wait-Key; return }
        Write-Host ""
        Write-Host "  [c]  Changer modele actif" -ForegroundColor White
        Write-Host "  [p]  Telecharger modele (ollama pull)" -ForegroundColor White
        Write-Host "  [s]  Supprimer modele (ollama rm)" -ForegroundColor White
        Write-Host "  [r]  Retour" -ForegroundColor DarkGray
        Write-Host ""
        switch ((Read-Host "  Choix").ToLower()) {
            "c" {
                $num = Read-Host "  Numero"
                $idx = [int]$num - 1
                if ($idx -ge 0 -and $idx -lt $liste.Count) {
                    $newModel = @{ model = $liste[$idx] } | ConvertTo-Json
                    Set-Content "$JARVIS_SCR\jarvis_model.json" -Value $newModel -Encoding UTF8
                    Write-OK "Modele actif : $($liste[$idx])"
                    Write-WARN "Redemarrer JARVIS pour appliquer"
                } else { Write-WARN "Numero invalide" }
                Start-Sleep -Seconds 2
            }
            "p" { $n = Read-Host "  Nom (ex: llama3:8b)"; if ($n) { & ollama pull $n }; Wait-Key }
            "s" {
                $num = Read-Host "  Numero a supprimer"
                $idx = [int]$num - 1
                if ($idx -ge 0 -and $idx -lt $liste.Count) {
                    if (Confirm-Action "Supprimer $($liste[$idx]) ?") { & ollama rm $liste[$idx]; Write-OK "Supprime" }
                } else { Write-WARN "Numero invalide" }
                Start-Sleep -Seconds 2
            }
            "r" { return }
        }
    }
}

# ══════════════════════════════════════════════════════════════
# [6] PARAMETRES LLM
# ══════════════════════════════════════════════════════════════
function Invoke-ParamsLLM {
    Write-Title "PARAMETRES LLM"
    Write-Host ""
    $file = "$JARVIS_SCR\jarvis_llm_params.json"
    try {
        $p = Get-Content $file -Raw | ConvertFrom-Json
        Write-INFO "Fichier : $file"
        Write-Host ""
        Write-Host "  temperature    : $($p.temperature)" -ForegroundColor White
        Write-Host "  num_predict    : $($p.num_predict)" -ForegroundColor White
        Write-Host "  num_ctx        : $($p.num_ctx)" -ForegroundColor White
        Write-Host "  top_p          : $($p.top_p)" -ForegroundColor White
        Write-Host "  top_k          : $($p.top_k)" -ForegroundColor White
        Write-Host "  repeat_penalty : $($p.repeat_penalty)" -ForegroundColor White
        Write-Host ""
        Write-Host "  Presets SOC (auto-engine vocal) :" -ForegroundColor DarkGray
        Write-Host "  SILENCIEUX   voiceMinScore=70  cooldown=30min  tokens=1024  ctx=2048" -ForegroundColor DarkGray
        Write-Host "  STANDARD     voiceMinScore=50  cooldown=10min  tokens=1024  ctx=2048" -ForegroundColor DarkGray
        Write-Host "  VERBEUX      voiceMinScore=30  cooldown=5min   tokens=2048  ctx=4096" -ForegroundColor DarkGray
        Write-Host "  FULL ALERTE  voiceMinScore=5   cooldown=1min   tokens=4096  ctx=8192" -ForegroundColor DarkGray
        Write-Host ""
        Write-INFO "Mode SOC actif : temp=0.2 / num_ctx=8192 (adaptatif runtime)"
        Write-WARN "Modifier via l'interface JARVIS (onglet Settings)"
    } catch { Write-FAIL "Impossible de lire $file" }
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [7] PROFILS PROMPT
# ══════════════════════════════════════════════════════════════
function Invoke-ProfilsPrompt {
    Write-Title "PROFILS PROMPT"
    Write-Host ""
    $modelFile  = "$JARVIS_SCR\jarvis_model.json"
    $profFile   = "$JARVIS_SCR\jarvis_prompt_profiles.json"
    $promptFile = "$JARVIS_SCR\jarvis_system_prompt.txt"
    try {
        $m = Get-Content $modelFile -Raw | ConvertFrom-Json
        Write-INFO "Modele actif : $($m.model)"
    } catch {}
    Write-Host ""
    if (Test-Path $profFile) {
        try {
            $profs = Get-Content $profFile -Raw | ConvertFrom-Json
            Write-INFO "$($profs.Count) profils disponibles :"
            foreach ($pf in $profs) {
                $binding = if ($pf.model_binding) { "  <- $($pf.model_binding)" } else { "" }
                Write-Host "    $($pf.name.PadRight(40))$binding" -ForegroundColor White
            }
        } catch { Write-WARN "jarvis_prompt_profiles.json illisible" }
    } else { Write-WARN "jarvis_prompt_profiles.json absent" }
    Write-Host ""
    if (Test-Path $promptFile) {
        $lines = (Get-Content $promptFile -Encoding UTF8).Count
        Write-INFO "jarvis_system_prompt.txt : $lines lignes"
        Write-Host ""
        Write-Host "  --- Apercu (10 premieres lignes) ---" -ForegroundColor DarkGray
        Get-Content $promptFile -Encoding UTF8 | Select-Object -First 10 |
            ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        Write-Host "  ..." -ForegroundColor DarkGray
    } else { Write-WARN "jarvis_system_prompt.txt absent" }
    Write-Host ""
    Write-Host "  [e]  Editer jarvis_system_prompt.txt dans Notepad" -ForegroundColor White
    Write-Host "  [r]  Retour" -ForegroundColor DarkGray
    Write-Host ""
    if ((Read-Host "  Choix").ToLower() -eq "e") {
        Start-Process "notepad.exe" -ArgumentList $promptFile -Wait
        Write-WARN "Redemarrer JARVIS pour appliquer les modifications"
        Start-Sleep -Seconds 2
    }
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [8] DSP AUDIO + MOTEUR TTS
# ══════════════════════════════════════════════════════════════
function _Invoke-TtsSwitch {
    $file = "$JARVIS_SCR\jarvis_dsp_params.json"
    try { $p = Get-Content $file -Raw | ConvertFrom-Json } catch { Write-FAIL "jarvis_dsp_params.json illisible"; return }
    Write-Host ""
    Write-Host "  Moteur TTS actuel : $($p.tts_engine)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1]  edge-tts   (en ligne - fr-CA-AntoineNeural)" -ForegroundColor White
    Write-Host "  [2]  piper      (hors-ligne - fr_FR-upmc-medium)" -ForegroundColor White
    Write-Host "  [3]  sapi5      (Windows SAPI5 - pyttsx3)" -ForegroundColor White
    Write-Host "  [r]  Annuler" -ForegroundColor DarkGray
    Write-Host ""
    $engines = @{ "1" = "edge-tts"; "2" = "piper"; "3" = "sapi5" }
    $choix = Read-Host "  Choix"
    if ($engines.ContainsKey($choix)) {
        $p.tts_engine = $engines[$choix]
        $p | ConvertTo-Json -Depth 5 | Set-Content $file -Encoding UTF8
        Write-OK "Moteur TTS : $($engines[$choix])"
        Write-WARN "Redemarrer JARVIS pour appliquer"
        Start-Sleep -Seconds 2
    }
}

function Invoke-DspAudio {
    Write-Title "DSP AUDIO + MOTEUR TTS"
    Write-Host ""
    $file = "$JARVIS_SCR\jarvis_dsp_params.json"
    try {
        $p = Get-Content $file -Raw | ConvertFrom-Json
        Write-INFO "Fichier : $file"
        Write-Host ""
        Write-Host "  TTS Engine     : $($p.tts_engine)" -ForegroundColor Cyan
        Write-Host "  DSP Enabled    : $($p.enabled)" -ForegroundColor White
        Write-Host "  DeepFilterNet  : $($p.df_enabled)  (debruitage IA - CPU force)" -ForegroundColor White
        Write-Host "  FX Rack        : $($p.fx_enabled)" -ForegroundColor White
        Write-Host "  Stereo Haas    : $($p.stereo_enabled)" -ForegroundColor White
        Write-Host "  EQ Low/Mid/Hi  : $($p.eq_low) / $($p.eq_mid) / $($p.eq_high) dB" -ForegroundColor White
        Write-Host "  EQ Air         : $($p.eq_air) dB" -ForegroundColor White
        Write-Host "  Compressor     : threshold=$($p.comp_threshold)dB  ratio=$($p.comp_ratio):1" -ForegroundColor White
        Write-Host "  Gain           : $($p.gain) dB" -ForegroundColor White
        Write-Host ""
        Write-Host "  --- EQ Music TASCAM DAT ---" -ForegroundColor DarkGray
        Write-Host "  SUB (80Hz)   : $($p.dat_eq_sub) dB  |  BASS (300Hz) : $($p.dat_eq_bass) dB" -ForegroundColor White
        Write-Host "  MIDS (3kHz)  : $($p.dat_eq_mids) dB  |  TREBLE(10k) : $($p.dat_eq_treble) dB" -ForegroundColor White
        Write-Host ""
        Write-Host "  [t]  Changer moteur TTS" -ForegroundColor White
        Write-Host "  [r]  Retour" -ForegroundColor DarkGray
        Write-Host ""
        if ((Read-Host "  Choix").ToLower() -eq "t") { _Invoke-TtsSwitch }
    } catch { Write-FAIL "Impossible de lire $file" }
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [9] PACKAGES PIP
# ══════════════════════════════════════════════════════════════
function Invoke-Pip {
    $pkgsFilter  = "flask|edge.tts|faster|whisper|pynvml|psutil|piper|deepfilter|numpy|scipy|requests|pyttsx3|torch|ctranslate|paramiko|huggingface|cryptography"
    $pkgsUpgrade = "flask flask-cors flask-limiter edge-tts faster-whisper pynvml psutil requests pyttsx3 piper-tts DeepFilterNet numpy==1.26.4 scipy ctranslate2 paramiko cryptography huggingface_hub"
    while ($true) {
        Clear-Host
        Write-Title "PACKAGES PYTHON"
        Write-Host ""
        Write-Host "  [1]  Lister packages JARVIS installes" -ForegroundColor White
        Write-Host "  [2]  Mettre a jour packages (hors PyTorch)" -ForegroundColor White
        Write-Host "  [3]  Installer un package manquant" -ForegroundColor White
        Write-Host "  [r]  Retour" -ForegroundColor DarkGray
        Write-Host ""
        switch ((Read-Host "  Choix")) {
            "1" {
                Write-Host ""
                & $PYTHON -m pip list 2>$null | Select-String -Pattern $pkgsFilter -CaseSensitive:$false
                Write-Host ""
                Write-INFO "PyTorch (hors filtre) :"
                & $PYTHON -m pip list 2>$null | Select-String "torch"
                Wait-Key
            }
            "2" {
                if (Confirm-Action "Mettre a jour les packages pip (hors PyTorch) ?") {
                    Write-WARN "PyTorch NON mis a jour - index special cu128 - faire manuellement si besoin"
                    Write-Host ""
                    Invoke-Expression "& '$PYTHON' -m pip install --upgrade $pkgsUpgrade"
                    Write-OK "Mise a jour terminee"
                    Wait-Key
                }
            }
            "3" { $pkg = Read-Host "  Nom du package"; if ($pkg) { & $PYTHON -m pip install $pkg; Wait-Key } }
            "r" { return }
        }
    }
}

# ══════════════════════════════════════════════════════════════
# [10] LOGS
# ══════════════════════════════════════════════════════════════
function Invoke-Logs {
    $logsMap = @{
        "1" = @{ label = "jarvis_start.log (demarrage)";   path = "$JARVIS_SCR\jarvis_start.log";       last = 30 }
        "2" = @{ label = "stop_jarvis.bat log (arret)";     path = "$env:USERPROFILE\Desktop\jarvis-stop.log"; last = 20 }
        "3" = @{ label = "jarvis-backup.log (sauvegarde)";  path = "$env:USERPROFILE\Desktop\jarvis-backup.log"; last = 20 }
        "4" = @{ label = "tts.log (vocal - 30 dern.)";      path = "$JARVIS_SCR\tts.log";               last = 30 }
    }
    while ($true) {
        Clear-Host
        Write-Title "LOGS JARVIS"
        Write-Host ""
        foreach ($k in $logsMap.Keys | Sort-Object) {
            $l = $logsMap[$k]
            $exists = if (Test-Path $l.path) { "[present]" } else { "[absent] " }
            Write-Host "  [$k]  $exists  $($l.label)" -ForegroundColor White
        }
        Write-Host "  [r]  Retour" -ForegroundColor DarkGray
        Write-Host ""
        $choix = Read-Host "  Choix"
        if ($choix.ToLower() -eq "r") { return }
        if ($logsMap.ContainsKey($choix)) {
            $l = $logsMap[$choix]
            if (Test-Path $l.path) {
                Write-Host ""
                Write-Host "  --- $($l.label) ---" -ForegroundColor Cyan
                Get-Content $l.path -Encoding UTF8 | Select-Object -Last $l.last |
                    ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
                $sz = [math]::Round((Get-Item $l.path).Length / 1KB, 1)
                Write-Host ""
                Write-INFO "Fichier : $($l.path)  ($sz Ko)"
            } else { Write-WARN "Log absent : $($l.path)" }
            Wait-Key
        }
    }
}

# ══════════════════════════════════════════════════════════════
# [11] NETTOYAGE
# ══════════════════════════════════════════════════════════════
function Invoke-Nettoyage {
    Write-Title "NETTOYAGE"
    Write-Host ""
    $caches = Get-ChildItem $JARVIS_ROOT -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
    $nb = ($caches | Measure-Object).Count
    if ($nb -gt 0) {
        Write-INFO "$nb dossier(s) __pycache__ trouves"
        if (Confirm-Action "Supprimer les __pycache__ ?") {
            $caches | Remove-Item -Recurse -Force
            Write-OK "__pycache__ supprimes"
        }
    } else { Write-OK "Aucun __pycache__" }
    Write-Host ""
    $logsFixes  = @("$JARVIS_SCR\jarvis_start.log",
                    "$env:USERPROFILE\Desktop\jarvis-stop.log",
                    "$env:USERPROFILE\Desktop\jarvis-backup.log",
                    "$env:USERPROFILE\Desktop\jarvis-install.log")
    $logsDryRun = Get-ChildItem "$env:USERPROFILE\Desktop" -Filter "jarvis-dryrun-*.txt" -ErrorAction SilentlyContinue
    $logsExist  = $logsFixes | Where-Object { Test-Path $_ }
    $total      = @($logsExist) + @($logsDryRun)
    if ($total.Count -gt 0) {
        Write-INFO "Fichiers logs :"
        foreach ($l in $logsExist) { Write-INFO "  $([System.IO.Path]::GetFileName($l))  ($([math]::Round((Get-Item $l).Length/1KB,1)) Ko)" }
        foreach ($l in $logsDryRun) { Write-INFO "  $($l.Name)  ($([math]::Round($l.Length/1KB,1)) Ko)" }
        Write-Host ""
        if (Confirm-Action "Vider / supprimer ces fichiers ?") {
            $logsExist  | ForEach-Object { Clear-Content $_ -ErrorAction SilentlyContinue }
            $logsDryRun | Remove-Item -Force -ErrorAction SilentlyContinue
            Write-OK "Logs vides / rapports DryRun supprimes"
        }
    } else { Write-OK "Aucun log present" }
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [12] SAUVEGARDE COMPLETE
# ══════════════════════════════════════════════════════════════
function Invoke-Sauvegarde {
    Write-Title "SAUVEGARDE COMPLETE"
    Write-Host ""
    if (-not (Test-Path $BACKUP_SCR)) {
        Write-FAIL "Script introuvable : $BACKUP_SCR"; Wait-Key; return
    }
    Write-INFO "Contenu sauvegarde :"
    Write-Host "  JARVIS\         <- $JARVIS_ROOT" -ForegroundColor Gray
    Write-Host "  SSH\            <- C:\Users\$env:USERNAME\.ssh" -ForegroundColor Gray
    Write-Host "  CLAUDE-MEMORY\  <- C:\Users\$env:USERNAME\.claude" -ForegroundColor Gray
    Write-Host "  OLLAMA-MODELS\  <- C:\Users\$env:USERNAME\.ollama  (10-30 min)" -ForegroundColor Gray
    Write-Host "  INSTALLERS\     <- Python + NVIDIA (cache / telechargement)" -ForegroundColor Gray
    Write-Host ""
    Write-INFO "Destination : $BACKUP_ROOT"
    Write-Host ""
    Write-WARN "La sauvegarde des modeles Ollama peut prendre 10-30 min."
    Write-Host ""
    if (-not (Confirm-Action "Lancer la sauvegarde complete ?")) { Wait-Key; return }
    Write-Host ""
    & powershell -NoProfile -ExecutionPolicy Bypass -File $BACKUP_SCR
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [13] VERIFICATION / SIMULATION
# ══════════════════════════════════════════════════════════════
function Invoke-VerifSauvegarde {
    Write-Title "VERIFICATION / SIMULATION"
    Write-Host ""
    Write-Host "  [1]  Verifier sauvegarde          (DryRun)" -ForegroundColor Yellow
    Write-Host "       Verifie sources, packages, fichiers" -ForegroundColor DarkGray
    Write-Host "       Rapport : jarvis-dryrun-*.txt" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [2]  Simuler restauration complete (DryRunRestore)" -ForegroundColor Cyan
    Write-Host "       Simule chaque etape 0 a 8 sans rien executer" -ForegroundColor DarkGray
    Write-Host "       Rapport : jarvis-simrestore-*.txt" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [r]  Retour" -ForegroundColor DarkGray
    Write-Host ""
    $script = if (Test-Path $INSTALL_SCR) { $INSTALL_SCR }
              elseif (Test-Path $INSTALL_BAK) { $INSTALL_BAK }
              else { $null }
    switch ((Read-Host "  Choix").ToLower()) {
        "1" {
            if (-not $script) {
                Write-FAIL "install-jarvis.ps1 introuvable ($INSTALL_SCR)"
                Wait-Key; return
            }
            Write-INFO "Script : $script"
            Write-Host ""
            & powershell -NoProfile -ExecutionPolicy Bypass -File $script -DryRun
            Write-Host ""
            Write-INFO "Rapport sur le bureau : jarvis-dryrun-*.txt"
            Wait-Key
        }
        "2" {
            if (-not $script) {
                Write-FAIL "install-jarvis.ps1 introuvable ($INSTALL_SCR)"
                Wait-Key; return
            }
            Write-INFO "Script : $script"
            Write-INFO "Simule chaque etape sans modifier quoi que ce soit."
            Write-Host ""
            & powershell -NoProfile -ExecutionPolicy Bypass -File $script -DryRunRestore
            Write-Host ""
            Write-INFO "Rapport sur le bureau : jarvis-simrestore-*.txt"
            Wait-Key
        }
    }
}

# ══════════════════════════════════════════════════════════════
# [14] RESTAURATION COMPLETE (zero intervention)
# ══════════════════════════════════════════════════════════════
function Invoke-Restauration {
    Write-Title "RESTAURATION COMPLETE"
    Write-Host ""
    $script = if (Test-Path $INSTALL_BAK) { $INSTALL_BAK }
              elseif (Test-Path $INSTALL_SCR) { $INSTALL_SCR }
              else { $null }
    if (-not $script) {
        Write-FAIL "install-jarvis.ps1 introuvable"
        Write-INFO "Attendu dans backup  : $INSTALL_BAK"
        Write-INFO "Attendu dans JARVIS  : $INSTALL_SCR"
        Write-INFO "Lancer d'abord une sauvegarde [12] ou verifier D:\BACKUP-WINDOWS"
        Wait-Key; return
    }
    Write-INFO "Script source  : $script"
    Write-Host ""
    Write-Host "  Etapes executees automatiquement :" -ForegroundColor White
    Write-Host "    0. Pilote NVIDIA (depuis cache INSTALLERS\ ou winget)" -ForegroundColor Gray
    Write-Host "    1. Python 3.11.9 (depuis cache ou internet)" -ForegroundColor Gray
    Write-Host "    2. Ollama + modeles LLM (depuis $BACKUP_ROOT\OLLAMA-MODELS)" -ForegroundColor Gray
    Write-Host "    3. Packages Python (flask, edge-tts, whisper, pynvml...)" -ForegroundColor Gray
    Write-Host "    4. PyTorch CUDA 12.8 (cu128 - RTX 5080 Blackwell)" -ForegroundColor Gray
    Write-Host "    5. Fichiers JARVIS (depuis $BACKUP_JARVIS)" -ForegroundColor Gray
    Write-Host "    6. Cles SSH (depuis $BACKUP_ROOT\SSH - permissions auto)" -ForegroundColor Gray
    Write-Host "    7. Memoire Claude Code (depuis $BACKUP_ROOT\CLAUDE-MEMORY)" -ForegroundColor Gray
    Write-Host "    8. Raccourcis bureau (JARVIS Dashboard / Arret / Demarrage)" -ForegroundColor Gray
    Write-Host ""
    Write-WARN "Duree estimee : 10-90 min (selon cache vs internet)."
    Write-WARN "Droits Administrateur requis (elevation automatique)."
    Write-Host ""
    if (-not (Confirm-Action "Lancer la restauration complete SANS intervention ?")) { Wait-Key; return }
    Write-Host ""
    Write-INFO "Lancement avec elevation administrateur..."
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
                [Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $script -Unattended
    } else {
        Start-Process powershell `
            -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -Unattended" `
            -Verb RunAs -Wait
    }
    Write-Host ""
    Write-OK "Restauration terminee - log disponible : jarvis-install.log (bureau)"
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [15] TEST API
# ══════════════════════════════════════════════════════════════
function Invoke-TestAPI {
    Write-Title "TEST API JARVIS"
    Write-Host ""
    $endpoints = @(
        @{ url = "$JARVIS_URL/api/stats";        label = "/api/stats        (GPU, CPU, RAM, uptime)" },
        @{ url = "$JARVIS_URL/api/boot-id";      label = "/api/boot-id      (ID session)" },
        @{ url = "$JARVIS_URL/api/models";        label = "/api/models       (modeles Ollama)" },
        @{ url = "$JARVIS_URL/api/llm-params";   label = "/api/llm-params   (params LLM actifs)" },
        @{ url = "$JARVIS_URL/api/soc/test";     label = "/api/soc/test     (connectivite SOC)" },
        @{ url = "$JARVIS_URL/api/soc/monitor";  label = "/api/soc/monitor  (monitoring SOC)" }
    )
    foreach ($ep in $endpoints) {
        try { $null = Invoke-RestMethod $ep.url -TimeoutSec 4; Write-OK $ep.label }
        catch { Write-FAIL $ep.label }
    }
    Write-Host ""
    try {
        $t = Invoke-RestMethod "$JARVIS_URL/api/soc/test" -TimeoutSec 5
        Write-INFO "Detail SOC test :"
        Write-INFO "  JARVIS API  : $($t.jarvis_api.msg)"
        Write-INFO "  SSH ngix    : $($t.ssh_ngix.msg)"
        Write-INFO "  TTS         : $($t.tts.msg)"
        Write-INFO "  Overall     : $($t.overall)"
    } catch {}
    Wait-Key
}

# ══════════════════════════════════════════════════════════════
# [16] OUVRIR INTERFACE
# ══════════════════════════════════════════════════════════════
function Invoke-OuvrirUI {
    Write-Title "INTERFACE JARVIS"
    Write-Host ""
    try {
        $null = Invoke-RestMethod "$JARVIS_URL/api/stats" -TimeoutSec 2
        Write-OK "JARVIS en ligne - ouverture navigateur"
        Start-Process $JARVIS_URL
    } catch { Write-WARN "JARVIS offline - demarrer d'abord avec [2]" }
    Start-Sleep -Seconds 2
}

# ══════════════════════════════════════════════════════════════
# BOUCLE PRINCIPALE
# ══════════════════════════════════════════════════════════════
while ($true) {
    Show-MainMenu
    $choix = Read-Host "  Choix"
    switch ($choix.ToLower()) {
        "1"  { Invoke-Statut }
        "2"  { Invoke-Demarrer }
        "3"  { Invoke-Arreter }
        "4"  { Invoke-Redemarrer }
        "5"  { Invoke-ModelesLLM }
        "6"  { Invoke-ParamsLLM }
        "7"  { Invoke-ProfilsPrompt }
        "8"  { Invoke-DspAudio }
        "9"  { Invoke-Pip }
        "10" { Invoke-Logs }
        "11" { Invoke-Nettoyage }
        "12" { Invoke-Sauvegarde }
        "13" { Invoke-VerifSauvegarde }
        "14" { Invoke-Restauration }
        "15" { Invoke-TestAPI }
        "16" { Invoke-OuvrirUI }
        "q"  { Write-Host ""; exit }
        default { Write-WARN "Choix invalide"; Start-Sleep -Seconds 1 }
    }
}
