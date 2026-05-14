# jarvis_watchdog.ps1 — Vérifie si JARVIS tourne, le redémarre automatiquement si KO
# Conçu pour être lancé par une tâche planifiée Windows toutes les 5 minutes.

$jarvisDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$jarvisScript = Join-Path $jarvisDir "jarvis.py"
$logFile    = Join-Path $jarvisDir "jarvis_watchdog.log"
$maxLogKb   = 512  # rotation à 512 Ko

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts  $msg"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

# Rotation log
if (Test-Path $logFile) {
    $sizeKb = (Get-Item $logFile).Length / 1KB
    if ($sizeKb -gt $maxLogKb) {
        $archive = $logFile -replace '\.log$', '_old.log'
        Move-Item $logFile $archive -Force
    }
}

# ── Test santé ──
$alive = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:5000/api/health" `
                               -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $data = $resp.Content | ConvertFrom-Json
    if ($data.status -eq "ok") { $alive = $true }
} catch {}

if ($alive) { exit 0 }

# ── JARVIS KO — nettoyage + redémarrage ──
Write-Log "[WATCHDOG] JARVIS hors ligne — redémarrage..."

# Kill les process python portant jarvis.py
Get-WmiObject Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*jarvis.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 3

# Vérifier qu'Ollama tourne
$ollamaRunning = $false
try {
    $ollamaResp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    if ($ollamaResp.StatusCode -eq 200) { $ollamaRunning = $true }
} catch {}

if (-not $ollamaRunning) {
    Write-Log "[WATCHDOG] Ollama absent — démarrage Ollama..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 8
}

# Redémarrer JARVIS
$pythonCmd = "cd `"$jarvisDir`"; python jarvis.py"
Start-Process powershell -WindowStyle Hidden -ArgumentList @(
    "-NonInteractive", "-ExecutionPolicy", "Bypass",
    "-Command", $pythonCmd
)

Start-Sleep -Seconds 5

# Vérification post-restart
$recovered = $false
try {
    $r2 = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop
    $d2 = $r2.Content | ConvertFrom-Json
    if ($d2.status -eq "ok") { $recovered = $true }
} catch {}

if ($recovered) {
    Write-Log "[WATCHDOG] JARVIS redémarré avec succès."
} else {
    Write-Log "[WATCHDOG] AVERTISSEMENT : JARVIS toujours KO après redémarrage."
}
