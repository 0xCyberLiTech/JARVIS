#Requires -Version 5.1
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Dark title bar Windows 11
try {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class JDwm {
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

# ── Formulaire (5 etapes) ─────────────────────────────────────────────────────
$form = New-Object Windows.Forms.Form
$form.Text            = "JARVIS - Arret"
$form.ClientSize      = New-Object Drawing.Size(500, 318)
$form.StartPosition   = "CenterScreen"
$form.BackColor       = $C_BG
$form.ForeColor       = $C_CYAN
$form.FormBorderStyle = "FixedSingle"
$form.MaximizeBox     = $false
$form.MinimizeBox     = $false
$form.ControlBox      = $false
$form.TopMost         = $true

$form.Add_Shown({ try { [JDwm]::Dark($form.Handle) } catch {} })

$lbl_title = New-Object Windows.Forms.Label
$lbl_title.Text      = "J A R V I S   " + [char]9672 + "   A R R E T"
$lbl_title.Font      = $F_TITLE
$lbl_title.ForeColor = $C_CYAN
$lbl_title.Location  = New-Object Drawing.Point(20, 16)
$lbl_title.AutoSize  = $true
$form.Controls.Add($lbl_title)

$lbl_sub = New-Object Windows.Forms.Label
$lbl_sub.Text      = "0xCyberLiTech  " + [char]0xB7 + "  RTX 5080  " + [char]0xB7 + "  Ollama local"
$lbl_sub.Font      = $F_SUB
$lbl_sub.ForeColor = $C_DIMTXT
$lbl_sub.Location  = New-Object Drawing.Point(20, 42)
$lbl_sub.AutoSize  = $true
$form.Controls.Add($lbl_sub)

$s1 = New-Object Windows.Forms.Panel
$s1.BackColor = $C_SEP_H
$s1.Location  = New-Object Drawing.Point(20, 60)
$s1.Size      = New-Object Drawing.Size(460, 1)
$form.Controls.Add($s1)

# ── 5 etapes ──────────────────────────────────────────────────────────────────
$stepTexts = @(
    "Fermeture navigateur (localhost:5000)",
    "Sauvegarde memoire session IA",
    "Arret processus Flask (port 5000)",
    "Arret serveur MCP JARVIS",
    "Verification & nettoyage final"
)
$lblStep   = @()
$lblStatus = @()
$y0 = 70

for ($i = 0; $i -lt 5; $i++) {
    $yPos = [int]$y0 + $i * 30
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

# Zone sous les etapes
$yA  = [int]$y0 + 158   # = 228
$yPb = $yA + 16
$yMsg = $yA + 36
$yS2 = $yA + 60
$yFt = $yA + 68

$s2 = New-Object Windows.Forms.Panel
$s2.BackColor = $C_SEP
$s2.Location  = New-Object Drawing.Point(20, $yA)
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
$s3.Location  = New-Object Drawing.Point(20, $yS2)
$s3.Size      = New-Object Drawing.Size(460, 1)
$form.Controls.Add($s3)

$lbl_footer = New-Object Windows.Forms.Label
$lbl_footer.Text      = "Ne pas fermer cette fenetre  --  arret automatique a la fin de la sequence"
$lbl_footer.Font      = $F_SUB
$lbl_footer.ForeColor = $C_DIMTXT
$lbl_footer.Location  = New-Object Drawing.Point(20, $yFt)
$lbl_footer.AutoSize  = $true
$form.Controls.Add($lbl_footer)

# Protection fermeture prematuree
$script:done = $false
$form.Add_FormClosing({
    if (-not $script:done -and
        $_.CloseReason -ne [Windows.Forms.CloseReason]::WindowsShutDown -and
        $_.CloseReason -ne [Windows.Forms.CloseReason]::ApplicationExitCall) {
        $_.Cancel = $true
    }
})

# ── Helpers ───────────────────────────────────────────────────────────────────
function Invoke-UiEvents { [Windows.Forms.Application]::DoEvents() }

function Invoke-UiSleep([int]$ms) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $ms) { Invoke-UiEvents; Start-Sleep -Milliseconds 15 }
}

$ANIM = @("[  . . .  ]","[  : : :  ]","[  - - -  ]","[  ' ' '  ]")

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

# Kill un PID avec double verification + fallback Stop-Process
function Stop-JarvisPid([int]$pid_val) {
    if ($pid_val -le 0) { return $false }
    $p = Get-Process -Id $pid_val -ErrorAction SilentlyContinue
    if (-not $p) { return $true }   # deja mort = succes
    # Tentative 1 : taskkill /F
    & taskkill /F /PID $pid_val | Out-Null
    Invoke-UiSleep 900
    $p2 = Get-Process -Id $pid_val -ErrorAction SilentlyContinue
    if (-not $p2) { return $true }
    # Tentative 2 : Stop-Process
    Stop-Process -Id $pid_val -Force -ErrorAction SilentlyContinue
    Invoke-UiSleep 600
    $p3 = Get-Process -Id $pid_val -ErrorAction SilentlyContinue
    return ($null -eq $p3)
}

# Trouver les PIDs python liés a JARVIS via WMI (plus fiable que NetTCPConnection)
function Get-JarvisPids([string]$pattern) {
    $pids = @()
    try {
        Get-WmiObject Win32_Process | Where-Object {
            ($_.Name -eq "python.exe" -or $_.Name -eq "pythonw.exe") -and
            $_.CommandLine -like "*$pattern*"
        } | ForEach-Object { $pids += [int]$_.ProcessId }
    } catch {}
    return ($pids | Select-Object -Unique)
}

# ── Demarrage ─────────────────────────────────────────────────────────────────
$form.Show()
Invoke-UiEvents
Invoke-UiSleep 200

$LOG = "$env:USERPROFILE\Desktop\jarvis-stop.log"
Set-Content -Path $LOG -Value ("=" * 50) -Encoding UTF8
Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [STOP] Sequence demarree") -Encoding UTF8

# ── ETAPE 1 : Navigateur ──────────────────────────────────────────────────────
Set-Step 0 "running"
Set-Msg "Fermeture de l'onglet JARVIS dans le navigateur..."
Set-Prog 5
try {
    $sh = New-Object -ComObject Shell.Application
    $sh.Windows() | Where-Object { $_.LocationURL -like "*localhost:5000*" } | ForEach-Object { $_.Quit() }
} catch {}
Invoke-UiSleep 700
Set-Step 0 "ok"
Set-Prog 12

# ── ETAPE 2 : Memoire (max 45s) ──────────────────────────────────────────────
Set-Step 1 "running"
Set-Msg "Sauvegarde memoire session IA (max 45s)..."
Set-Prog 14
Invoke-UiEvents

$memJob = Start-Job -ScriptBlock {
    try {
        (Invoke-WebRequest -Uri "http://localhost:5000/api/memory/summarize-session" `
            -Method POST -TimeoutSec 45 -UseBasicParsing -ErrorAction Stop).Content
    } catch { '{"ok":false}' }
}

$elms = 0; $lastUpd = -400; $animIdx = 0
while ($memJob.State -eq "Running" -and $elms -lt 47000) {
    Invoke-UiSleep 100
    $elms += 100
    if (($elms - $lastUpd) -ge 400) {
        $lastUpd = $elms
        $lblStatus[1].Text      = $ANIM[$animIdx % 4]
        $lblStatus[1].ForeColor = $C_ORANGE
        $animIdx++
        $sec = [int]($elms / 1000)
        Set-Msg "Resume session en cours... (${sec}s / 45s max)"
        Set-Prog ([int](14 + ($elms / 47000.0) * 32))
    }
}
if ($memJob.State -eq "Running") { Stop-Job $memJob }
$memResult = Receive-Job $memJob -Wait 2>$null
Remove-Job $memJob 2>$null
if ([string]::IsNullOrEmpty($memResult)) { $memResult = '{"ok":false}' }
Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [MEMORY] " + $memResult) -Encoding UTF8

if ($memResult -match '"ok"\s*:\s*true') {
    Set-Step 1 "ok"; Set-Msg "Memoire session sauvegardee."
} elseif ($memResult -match 'not_enough_messages') {
    Set-Step 1 "ok"; Set-Msg "Session courte  - resume ignore."
} else {
    Set-Step 1 "skip"; Set-Msg "Memoire ignoree (JARVIS hors ligne ou timeout)."
}
Set-Prog 48

# ── ETAPE 3 : Arret Flask (port 5000) ────────────────────────────────────────
Set-Step 2 "running"
Set-Msg "Arret du serveur Flask JARVIS..."
Set-Prog 52
Invoke-UiEvents

# Methode 1 : WMI par nom de script (la plus fiable)
$flaskPids = Get-JarvisPids "jarvis.py"

# Methode 2 : via port 5000 si WMI echoue
if ($flaskPids.Count -eq 0) {
    try {
        Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.OwningProcess -gt 0) { $flaskPids += $_.OwningProcess }
        }
        $flaskPids = $flaskPids | Select-Object -Unique
    } catch {}
}

Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [FLASK] PIDs trouves: $($flaskPids -join ',')") -Encoding UTF8

$flaskKilled = $false
foreach ($pid_val in $flaskPids) {
    $ok = Stop-JarvisPid $pid_val
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [FLASK] PID $pid_val -> " + $(if ($ok){"OK"}else{"ECHEC"})) -Encoding UTF8
    if ($ok) { $flaskKilled = $true }
}

if ($flaskKilled) {
    Set-Step 2 "ok"; Set-Msg "Serveur JARVIS arrete."
} elseif ($flaskPids.Count -eq 0) {
    Set-Step 2 "skip"; Set-Msg "Flask non detecte sur port 5000."
} else {
    Set-Step 2 "error"; Set-Msg "Echec arret Flask  - voir jarvis-stop.log"
}
Set-Prog 66

# ── ETAPE 4 : Arret MCP server (port 5010) ───────────────────────────────────
Set-Step 3 "running"
Set-Msg "Arret du serveur MCP JARVIS (port 5010)..."
Set-Prog 70
Invoke-UiEvents

# Detection fiable : PID ecoutant sur le port 5010
$mcpPids = @()
try {
    Get-NetTCPConnection -LocalPort 5010 -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { if ($_.OwningProcess -gt 0) { $mcpPids += $_.OwningProcess } }
    $mcpPids = $mcpPids | Select-Object -Unique
} catch {}
Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [MCP] PIDs port 5010: $($mcpPids -join ',')") -Encoding UTF8

$mcpKilled = $false
foreach ($pid_val in $mcpPids) {
    $ok = Stop-JarvisPid $pid_val
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [MCP] PID $pid_val -> " + $(if ($ok){"OK"}else{"ECHEC"})) -Encoding UTF8
    if ($ok) { $mcpKilled = $true }
}

if ($mcpKilled) {
    Set-Step 3 "ok"; Set-Msg "Serveur MCP arrete."
} elseif ($mcpPids.Count -eq 0) {
    Set-Step 3 "skip"; Set-Msg "Serveur MCP non detecte sur port 5010."
} else {
    Set-Step 3 "error"; Set-Msg "Echec arret MCP  - voir jarvis-stop.log"
}
Set-Prog 82

# ── ETAPE 5 : Verification finale ─────────────────────────────────────────────
Set-Step 4 "running"
Set-Msg "Verification  - recherche de processus residuels..."
Set-Prog 86
Invoke-UiSleep 800

$residuals = @()
try {
    Get-WmiObject Win32_Process | Where-Object {
        ($_.Name -eq "python.exe" -or $_.Name -eq "pythonw.exe") -and
        ($_.CommandLine -like "*jarvis.py*" -or $_.CommandLine -like "*jarvis_mcp*")
    } | ForEach-Object { $residuals += [int]$_.ProcessId }
} catch {}

if ($residuals.Count -gt 0) {
    Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [RESIDUAL] PIDs: $($residuals -join ',')") -Encoding UTF8
    foreach ($pid_val in $residuals) {
        Stop-Process -Id $pid_val -Force -ErrorAction SilentlyContinue
    }
    Invoke-UiSleep 700
    # Recheck
    $still = @()
    try {
        Get-WmiObject Win32_Process | Where-Object {
            ($_.Name -eq "python.exe" -or $_.Name -eq "pythonw.exe") -and
            ($_.CommandLine -like "*jarvis.py*" -or $_.CommandLine -like "*jarvis_mcp*")
        } | ForEach-Object { $still += [int]$_.ProcessId }
    } catch {}
    if ($still.Count -eq 0) {
        Set-Step 4 "ok"; Set-Msg "Residuels nettoyes. Arret complet confirme."
    } else {
        Set-Step 4 "error"; Set-Msg "PIDs encore actifs: $($still -join ','). Redemarrer le PC si necessaire."
    }
} else {
    Set-Step 4 "ok"; Set-Msg "Verification OK  - aucun processus JARVIS residuel."
}

# Fermeture fenetres terminal JARVIS
Get-Process cmd -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowTitle -eq "JARVIS - Systeme IA" } |
    Stop-Process -Force -ErrorAction SilentlyContinue

# Port 5000 libere ?
$portStillOpen = $false
try {
    $portStillOpen = ($null -ne (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -First 1))
} catch {}

$finalStatus = if ($portStillOpen) { "PORT 5000 ENCORE OUVERT" } else { "Port 5000 libere" }
Add-Content -Path $LOG -Value ((Get-Date -f "yyyy-MM-dd HH:mm:ss") + " [DONE] $finalStatus") -Encoding UTF8
Add-Content -Path $LOG -Value ("=" * 50) -Encoding UTF8

Set-Prog 100
Set-Msg "Sequence terminee  - fermeture dans 3 secondes..."
Invoke-UiEvents
Invoke-UiSleep 3000

$script:done = $true
$form.Close()
