#Requires -Version 5.1
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

try {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class JDwmS {
    [DllImport("dwmapi.dll")]
    public static extern int DwmSetWindowAttribute(IntPtr h, int a, ref int v, int s);
    public static void Dark(IntPtr h) { int v = 1; DwmSetWindowAttribute(h, 20, ref v, 4); }
}
"@ -ErrorAction SilentlyContinue
} catch {}

# ── Palette JARVIS ────────────────────────────────────────────────────────────
$C_BG     = [Drawing.Color]::FromArgb(8,  12, 20)
$C_CYAN   = [Drawing.Color]::FromArgb(0,  207,255)
$C_DIMTXT = [Drawing.Color]::FromArgb(38, 65, 88)
$C_WHITE  = [Drawing.Color]::FromArgb(175,205,230)
$C_GREEN  = [Drawing.Color]::FromArgb(0,  215,105)
$C_RED    = [Drawing.Color]::FromArgb(215, 50, 50)
$C_ORANGE = [Drawing.Color]::FromArgb(255,160,  0)
$C_PBOUT  = [Drawing.Color]::FromArgb(15,  25, 38)
$C_SEP    = [Drawing.Color]::FromArgb(20,  40, 55)
$C_SEP_H  = [Drawing.Color]::FromArgb(0,  140,185)
$C_MSG    = [Drawing.Color]::FromArgb(88, 148,192)

$F_TITLE  = New-Object Drawing.Font("Consolas", 13, [Drawing.FontStyle]::Bold)
$F_SUB    = New-Object Drawing.Font("Consolas",  8)
$F_STEP   = New-Object Drawing.Font("Consolas", 10)
$F_STATUS = New-Object Drawing.Font("Consolas",  9, [Drawing.FontStyle]::Bold)
$F_MSG    = New-Object Drawing.Font("Consolas",  8)

# ── Chemins ───────────────────────────────────────────────────────────────────
$rootDir    = Split-Path $PSScriptRoot -Parent
$scriptPath = Join-Path $PSScriptRoot "jarvis.py"
$venvPy     = Join-Path $rootDir ".venv\Scripts\python.exe"
$pythonExe  = if (Test-Path $venvPy) { $venvPy } else { "python" }
$LOG        = "$env:USERPROFILE\Desktop\jarvis-start.log"

# ── Formulaire ────────────────────────────────────────────────────────────────
$form = New-Object Windows.Forms.Form
$form.Text            = "JARVIS -- Demarrage"
$form.ClientSize      = New-Object Drawing.Size(500, 327)
$form.StartPosition   = "CenterScreen"
$form.BackColor       = $C_BG
$form.ForeColor       = $C_CYAN
$form.FormBorderStyle = "FixedSingle"
$form.MaximizeBox     = $false
$form.MinimizeBox     = $false
$form.ControlBox      = $false
$form.TopMost         = $true

$form.Add_Shown({ try { [JDwmS]::Dark($form.Handle) } catch {} })

# Titre
$lbl_title = New-Object Windows.Forms.Label
$lbl_title.Text      = "J A R V I S   " + [char]9672 + "   D" + [char]0xC9 + "MARRAGE"
$lbl_title.Font      = $F_TITLE
$lbl_title.ForeColor = $C_CYAN
$lbl_title.Location  = New-Object Drawing.Point(20, 16)
$lbl_title.AutoSize  = $true
$form.Controls.Add($lbl_title)

# Sous-titre
$lbl_sub = New-Object Windows.Forms.Label
$lbl_sub.Text      = "0xCyberLiTech  " + [char]0xB7 + "  RTX 5080  " + [char]0xB7 + "  Ollama local"
$lbl_sub.Font      = $F_SUB
$lbl_sub.ForeColor = $C_DIMTXT
$lbl_sub.Location  = New-Object Drawing.Point(20, 42)
$lbl_sub.AutoSize  = $true
$form.Controls.Add($lbl_sub)

# Separateur haut (cyan)
$s1 = New-Object Windows.Forms.Panel
$s1.BackColor = $C_SEP_H
$s1.Location  = New-Object Drawing.Point(20, 60)
$s1.Size      = New-Object Drawing.Size(460, 1)
$form.Controls.Add($s1)

# ── 5 etapes ──────────────────────────────────────────────────────────────────
$stepTexts = @(
    "Verification Ollama (localhost:11434)",
    "Lancement MCP server (port 5010)",
    "Lancement JARVIS (jarvis.py)",
    "Connexion Flask (/api/health)",
    "Ouverture navigateur (localhost:5000)"
)
$lblStep   = @()
$lblStatus = @()
$y0 = 72

for ($i = 0; $i -lt 5; $i++) {
    $yPos = [int]$y0 + $i * 32
    $ls = New-Object Windows.Forms.Label
    $ls.Text      = "  " + [char]0x25B8 + "  " + $stepTexts[$i]
    $ls.Font      = $F_STEP
    $ls.ForeColor = $C_WHITE
    $ls.Location  = New-Object Drawing.Point(20, $yPos)
    $ls.Size      = New-Object Drawing.Size(322, 26)
    $form.Controls.Add($ls)
    $lblStep += $ls

    $lt = New-Object Windows.Forms.Label
    $lt.Text      = "[  " + [char]0x2500 + [char]0x2500 + "  ]"
    $lt.Font      = $F_STATUS
    $lt.ForeColor = $C_SEP
    $lt.Location  = New-Object Drawing.Point(342, $yPos)
    $lt.Size      = New-Object Drawing.Size(138, 26)
    $lt.TextAlign = [Drawing.ContentAlignment]::MiddleRight
    $form.Controls.Add($lt)
    $lblStatus += $lt
}

$yA   = [int]$y0 + 160
$yS2  = $yA + 8
$yPb  = $yA + 18
$yMsg = $yA + 38
$yS3  = $yA + 62
$yFt  = $yA + 70

$s2 = New-Object Windows.Forms.Panel
$s2.BackColor = $C_SEP
$s2.Location  = New-Object Drawing.Point(20, $yS2)
$s2.Size      = New-Object Drawing.Size(460, 1)
$form.Controls.Add($s2)

$pb_out = New-Object Windows.Forms.Panel
$pb_out.BackColor   = $C_PBOUT
$pb_out.BorderStyle = "FixedSingle"
$pb_out.Location    = New-Object Drawing.Point(20, $yPb)
$pb_out.Size        = New-Object Drawing.Size(460, 14)
$form.Controls.Add($pb_out)

$pb_in = New-Object Windows.Forms.Panel
$pb_in.BackColor = $C_CYAN
$pb_in.Location  = New-Object Drawing.Point(1, 1)
$pb_in.Size      = New-Object Drawing.Size(0, 12)
$pb_out.Controls.Add($pb_in)

$lbl_msg = New-Object Windows.Forms.Label
$lbl_msg.Text      = "Initialisation..."
$lbl_msg.Font      = $F_MSG
$lbl_msg.ForeColor = $C_MSG
$lbl_msg.Location  = New-Object Drawing.Point(20, $yMsg)
$lbl_msg.Size      = New-Object Drawing.Size(460, 18)
$form.Controls.Add($lbl_msg)

$s3 = New-Object Windows.Forms.Panel
$s3.BackColor = $C_SEP
$s3.Location  = New-Object Drawing.Point(20, $yS3)
$s3.Size      = New-Object Drawing.Size(460, 1)
$form.Controls.Add($s3)

$lbl_footer = New-Object Windows.Forms.Label
$lbl_footer.Text      = "Lancement automatique  --  ne pas fermer cette fenetre"
$lbl_footer.Font      = $F_SUB
$lbl_footer.ForeColor = $C_DIMTXT
$lbl_footer.Location  = New-Object Drawing.Point(20, $yFt)
$lbl_footer.AutoSize  = $true
$form.Controls.Add($lbl_footer)

# ── Protection fermeture prematuree ───────────────────────────────────────────
$script:done = $false
$form.Add_FormClosing({
    if (-not $script:done -and
        $_.CloseReason -ne [Windows.Forms.CloseReason]::WindowsShutDown -and
        $_.CloseReason -ne [Windows.Forms.CloseReason]::ApplicationExitCall) {
        $_.Cancel = $true
    }
})

# ── Helpers ────────────────────────────────────────────────────────────────────
$ANIM = @("[  . . .  ]","[  : : :  ]","[  - - -  ]","[  ' ' '  ]")

function Invoke-UiEvents { [Windows.Forms.Application]::DoEvents() }

function Invoke-UiSleep([int]$ms) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $ms) { Invoke-UiEvents; Start-Sleep -Milliseconds 15 }
}

function Set-Step([int]$i, [string]$st) {
    switch ($st) {
        "running" { $lblStatus[$i].Text = $ANIM[0]; $lblStatus[$i].ForeColor = $C_ORANGE }
        "ok"      { $lblStatus[$i].Text = "[    OK    ]"; $lblStatus[$i].ForeColor = $C_GREEN  }
        "skip"    { $lblStatus[$i].Text = "[   ----   ]"; $lblStatus[$i].ForeColor = $C_DIMTXT }
        "error"   { $lblStatus[$i].Text = "[ ERREUR   ]"; $lblStatus[$i].ForeColor = $C_RED    }
    }
    Invoke-UiEvents
}

function Set-Msg([string]$msg) { $lbl_msg.Text = $msg; Invoke-UiEvents }

function Set-Prog([int]$pct) {
    $w = [int]([Math]::Max(0,[Math]::Min($pct,100)) / 100.0 * 458)
    $pb_in.Width = $w
    Invoke-UiEvents
}

function Test-Port5000 {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 5000)
        $tcp.Close()
        return $true
    } catch { return $false }
}


# ── Affichage ─────────────────────────────────────────────────────────────────
$form.Show()
Invoke-UiEvents
Invoke-UiSleep 200

Set-Content -Path $LOG -Value ("=" * 44)
Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [START] Demarrage demande")

# ── CAS : JARVIS deja actif ───────────────────────────────────────────────────
if (Test-Port5000) {
    Set-Step 0 "skip"
    Set-Step 1 "skip"
    Set-Step 2 "skip"
    Set-Step 3 "ok"
    Set-Step 4 "running"
    Set-Prog 82
    Set-Msg "JARVIS deja actif -- ouverture navigateur..."
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [DEJA_ACTIF] navigateur ouvert")
    Start-Process "http://localhost:5000"
    Invoke-UiSleep 1500
    Set-Step 4 "ok"
    Set-Prog 100
    Set-Msg "Navigateur ouvert. Fermeture dans 2 secondes..."
    Invoke-UiSleep 2000
    $script:done = $true; $form.Close(); return
}

# ── ETAPE 0 : Ollama ──────────────────────────────────────────────────────────
Set-Step 0 "running"
Set-Msg "Verification Ollama..."
Set-Prog 5
Invoke-UiEvents

$ollamaProc = Get-Process ollama -ErrorAction SilentlyContinue
if ($null -eq $ollamaProc) {
    Set-Msg "Ollama absent -- demarrage..."
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [OLLAMA] Demarrage...")
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
}

if ($null -eq $ollamaProc) {
    $idx = 0
    for ($s = 1; $s -le 6; $s++) {
        Invoke-UiSleep 500
        $lblStatus[0].Text = $ANIM[$idx % 4]; $idx++
        $lblStatus[0].ForeColor = $C_ORANGE
        Set-Msg ("Ollama en cours de demarrage... (${s}s)")
        Set-Prog ([int](5 + $s / 6.0 * 17))
    }
} else {
    Set-Msg "Ollama operationnel."
    Invoke-UiSleep 400
}
Set-Step 0 "ok"
Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [OLLAMA] OK")
Set-Prog 20

# ── ETAPE 1 : Lancement MCP server ───────────────────────────────────────────
Set-Step 1 "running"
Set-Msg "Lancement MCP server (port 5010)..."
Set-Prog 22
Invoke-UiEvents

$mcpScript = Join-Path $PSScriptRoot "jarvis_mcp_server.py"
if (Test-Path $mcpScript) {
    # Chemin Python complet (plus fiable depuis un raccourci .lnk)
    $pythonFull = try { (Get-Command python -ErrorAction Stop).Source } catch { $pythonExe }
    $mcpBat = "$env:TEMP\jarvis_mcp_start.bat"
    @("@echo off","cd /d `"$PSScriptRoot`"","`"$pythonFull`" `"$mcpScript`" --port 5010") | Set-Content $mcpBat -Encoding ASCII
    $mcpProc = Start-Process cmd -ArgumentList "/c `"$mcpBat`"" -WindowStyle Hidden -PassThru -ErrorAction SilentlyContinue
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [MCP] Lancement PID=$($mcpProc.Id) python=$pythonFull")
    # Attente port 5010 (max 30s)
    $mElms = 0; $mAnimIdx = 0; $mLastUpd = -400; $mcpReady = $false
    while ($mElms -lt 30000) {
        try {
            $t = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 5010); $t.Close()
            $mcpReady = $true; break
        } catch {}
        Invoke-UiSleep 500
        $mElms += 500
        if (($mElms - $mLastUpd) -ge 400) {
            $mLastUpd = $mElms
            $lblStatus[1].Text = $ANIM[$mAnimIdx % 4]; $mAnimIdx++
            $lblStatus[1].ForeColor = $C_ORANGE
        }
    }
    if ($mcpReady) {
        Set-Step 1 "ok"; Set-Msg "MCP server operationnel sur port 5010."
        Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [MCP] OK port 5010")
    } else {
        Set-Step 1 "error"; Set-Msg "MCP server non repondu (port 5010) -- JARVIS continue."
        Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [MCP] WARN timeout port 5010")
    }
} else {
    Set-Step 1 "skip"; Set-Msg "jarvis_mcp_server.py introuvable -- etape ignoree."
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [MCP] SKIP introuvable")
}
Set-Prog 38

# ── ETAPE 2 : Lancement Flask ─────────────────────────────────────────────────
Set-Step 2 "running"
Set-Msg "Lancement JARVIS (Flask)..."
Set-Prog 40
Invoke-UiEvents

if (-not (Test-Path $scriptPath)) {
    Set-Step 2 "error"
    Set-Msg "ERREUR : jarvis.py introuvable dans $PSScriptRoot"
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [ERROR] jarvis.py introuvable")
    Invoke-UiSleep 5000
    $script:done = $true; $form.Close(); return
}

Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [FLASK] Lancement : $scriptPath")

$helperBat = "$env:TEMP\jarvis_start.bat"
@(
    "@echo off",
    "cd /d `"$PSScriptRoot`"",
    "`"$pythonExe`" `"$scriptPath`""
) | Set-Content -Path $helperBat -Encoding ASCII
Start-Process -FilePath "cmd.exe" -ArgumentList "/c start `"JARVIS - Systeme IA`" cmd /k `"$helperBat`""

Set-Step 2 "ok"
Set-Prog 55

# ── ETAPE 3 : Health check ────────────────────────────────────────────────────
Set-Step 3 "running"
Set-Msg "Attente connexion Flask (/api/health)..."
Set-Prog 58
Invoke-UiEvents

$elms = 0; $animIdx = 0; $lastUpd = -400
$jarvisReady = $false
while ($elms -lt 60000) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 5000)
        $tcp.Close()
        $jarvisReady = $true
        break
    } catch {}
    Invoke-UiSleep 500
    $elms += 500
    if (($elms - $lastUpd) -ge 400) {
        $lastUpd = $elms
        $lblStatus[3].Text = $ANIM[$animIdx % 4]; $animIdx++
        $lblStatus[3].ForeColor = $C_ORANGE
        Set-Msg ("JARVIS en cours de demarrage... (" + [int]($elms / 1000) + "s / max 60s)")
        Set-Prog ([int](58 + $elms / 60000.0 * 24))
    }
}

if ($jarvisReady) {
    Set-Step 3 "ok"
    Set-Msg "JARVIS operationnel."
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [OK] JARVIS repond sur port 5000")
} else {
    Set-Step 3 "error"
    Set-Msg "Timeout 60s -- verifiez jarvis-start.log sur le bureau."
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [ERROR] Timeout 60s port 5000")
    Invoke-UiSleep 5000
    $script:done = $true; $form.Close(); return
}
Set-Prog 86

# ── ETAPE 4 : Navigateur ──────────────────────────────────────────────────────
Set-Step 4 "running"
Set-Msg "Ouverture navigateur..."
Set-Prog 92
Invoke-UiSleep 400
Start-Process "http://localhost:5000"
Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [OK] Navigateur ouvert")
Add-Content -Path $LOG -Value ("=" * 44)
Set-Step 4 "ok"
Set-Prog 100
Set-Msg "JARVIS demarre. Fermeture dans 3 secondes..."
Invoke-UiEvents

Invoke-UiSleep 3000
$script:done = $true
$form.Close()
