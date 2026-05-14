# Telechargement de 14 samples vocaux francais pour XTTS v2
# Sources : Coqui XTTS-v2 (officiel) + Kyutai CML-TTS FR enhanced
# Licences : CC-BY 4.0 / Apache 2.0

$base = Split-Path $MyInvocation.MyCommand.Path

$samples = @(
  # ── FRANCAIS (14 voix) ────────────────────────────────────────────
  @{ url="https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/fr_sample.wav"
     out="$base\fr\xtts_officiel_fr.wav";     label="XTTS officiel FR" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/10087_11650_000028-0002_enhanced.wav"
     out="$base\fr\cml_fr_01.wav";            label="CML-TTS FR 01 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/10177_10625_000134-0003_enhanced.wav"
     out="$base\fr\cml_fr_02.wav";            label="CML-TTS FR 02 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/10179_11051_000005-0001_enhanced.wav"
     out="$base\fr\cml_fr_03.wav";            label="CML-TTS FR 03 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/1406_1028_000009-0003_enhanced.wav"
     out="$base\fr\cml_fr_04.wav";            label="CML-TTS FR 04 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/1770_1028_000036-0002_enhanced.wav"
     out="$base\fr\cml_fr_05.wav";            label="CML-TTS FR 05 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/12080_11650_000047-0001_enhanced.wav"
     out="$base\fr\cml_fr_06.wav";            label="CML-TTS FR 06 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/12205_11650_000004-0002_enhanced.wav"
     out="$base\fr\cml_fr_07.wav";            label="CML-TTS FR 07 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/12977_10625_000037-0001_enhanced.wav"
     out="$base\fr\cml_fr_08.wav";            label="CML-TTS FR 08 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/1591_1028_000108-0004_enhanced.wav"
     out="$base\fr\cml_fr_09.wav";            label="CML-TTS FR 09 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/2114_1656_000053-0001_enhanced.wav"
     out="$base\fr\cml_fr_10.wav";            label="CML-TTS FR 10 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/2154_2576_000020-0003_enhanced.wav"
     out="$base\fr\cml_fr_11.wav";            label="CML-TTS FR 11 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/2216_1745_000007-0001_enhanced.wav"
     out="$base\fr\cml_fr_12.wav";            label="CML-TTS FR 12 (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/cml-tts/fr/2223_1745_000009-0002_enhanced.wav"
     out="$base\fr\cml_fr_13.wav";            label="CML-TTS FR 13 (enhanced)" },

  # ── ANGLAIS (4 voix) ──────────────────────────────────────────────
  @{ url="https://huggingface.co/coqui/XTTS-v2/resolve/main/samples/en_sample.wav"
     out="$base\en\xtts_officiel_en.wav";     label="XTTS officiel EN" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/vctk/p225_023_enhanced.wav"
     out="$base\en\vctk_p225_en.wav";         label="VCTK p225 EN female (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/vctk/p226_023_enhanced.wav"
     out="$base\en\vctk_p226_en.wav";         label="VCTK p226 EN male (enhanced)" },

  @{ url="https://huggingface.co/kyutai/tts-voices/resolve/main/vctk/p227_023_enhanced.wav"
     out="$base\en\vctk_p227_en.wav";         label="VCTK p227 EN male (enhanced)" }
)

$headers = @{ "User-Agent" = "Mozilla/5.0" }
$total = $samples.Count; $ok = 0; $fail = 0

foreach ($s in $samples) {
    Write-Host "  [$($ok+$fail+1)/$total] $($s.label)..." -NoNewline
    $dir = Split-Path $s.out
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    try {
        Invoke-WebRequest -Uri $s.url -OutFile $s.out -Headers $headers -UseBasicParsing -TimeoutSec 60 -ErrorAction Stop
        $size = [math]::Round((Get-Item $s.out).Length / 1KB, 0)
        Write-Host " OK ${size}Ko" -ForegroundColor Green
        $ok++
    } catch {
        Write-Host " ERREUR: $_" -ForegroundColor Red
        $fail++
    }
}

Write-Host ""
Write-Host "==> $ok/$total telecharges — $fail erreur(s)" -ForegroundColor Cyan
Write-Host "==> Dossier : $base" -ForegroundColor Cyan
