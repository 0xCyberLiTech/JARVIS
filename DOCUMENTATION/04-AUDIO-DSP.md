<div align="center">

  <br></br>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="Titre dynamique JARVIS" />
  </a>

  <br></br>

  <h2>Assistant IA local · voix · interface holographique · automatisation SOC 24/7</h2>

  <p align="center">
    <a href="https://0xcyberlitech.github.io/">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    <a href="https://github.com/0xCyberLiTech">
      <img src="https://img.shields.io/badge/Profil-GitHub-181717?logo=github&style=flat-square" alt="Profil GitHub" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/releases/latest">
      <img src="https://img.shields.io/github/v/release/0xCyberLiTech/JARVIS?label=version&style=flat-square&color=blue" alt="Dernière version" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/%F0%9F%93%84%20Changelog-JARVIS-blue?style=flat-square" alt="Changelog" />
    </a>
    <a href="https://github.com/0xCyberLiTech?tab=repositories">
      <img src="https://img.shields.io/badge/D%C3%A9p%C3%B4ts-publics-blue?style=flat-square" alt="Dépôts publics" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/graphs/contributors">
      <img src="https://img.shields.io/badge/%F0%9F%91%A5%20Contributeurs-cliquez%20ici-007ec6?style=flat-square" alt="Contributeurs" />
    </a>
  </p>

</div>

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/cyber-security.png" alt="CyberSec" width="80"/>
</div>

<div align="center">
  <p>
    <strong>IA 100% locale</strong> <img src="https://img.icons8.com/color/24/000000/lock--v1.png"/> &nbsp;•&nbsp; <strong>Voix naturelle · STT · TTS</strong> <img src="https://img.icons8.com/color/24/000000/linux.png"/> &nbsp;•&nbsp; <strong>Automatisation SOC</strong> <img src="https://img.icons8.com/color/24/000000/shield-security.png"/>
  </p>
</div>

---
# Audio DSP — Chaîne broadcast

## Objectif
La chaîne audio de JARVIS est inspirée d'un **processeur voix broadcast** (Symetrix 528).
3 étages : Voice Channel Strip → FX Send/Return → Master Bus.

---

## Topologie des 3 étages

```
SOURCE TTS (edge-tts Antoine / Kokoro)
       │
   Analyseur VU · pré-gain
       │
┌─────────────────────────────────────────┐
│  ÉTAGE 1 — VOICE CHANNEL STRIP          │
│  EQ 4 bandes (Low · Mid · High · Air)   │
│  Compresseur : -24 dBFS · ratio 4:1     │
│  Limiter voix : -0.5 dBFS · ratio 20:1  │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   DRY PATH              ÉTAGE 2 — AUX FX
   (cos x-fade)          Reverb · Echo · Delay
                         _fxConvolver (normalize=true)
                         Calibration loudness par type
        └──────────┬──────────┘
                   ▼
┌──────────────────────────────────────────┐
│  ÉTAGE 3 — MASTER BUS                    │
│  Sommation dry + wet                     │
│  Limiter final : -0.3 dBFS · ratio 20:1  │
└─────────────────┬────────────────────────┘
                  ▼
        audioCtx.destination
```

<div align="center">
  <img src="../Images/Jarvis-05.png" alt="JARVIS — rack DSP audio broadcast" width="300" />
  &nbsp;
  <img src="../Images/Jarvis-06.png" alt="JARVIS — analyseur spectre et étages DSP" width="300" />
  <br/>
  <sub>Le rack DSP en interface : waveform, EQ, compresseur, analyseur de spectre — chaîne voix de type broadcast, entièrement en Web Audio.</sub>
</div>

---

## Chaîne TTS — cascade automatique

| # | Moteur | Mode | Notes |
|---|--------|------|-------|
| 1 | **edge-tts** fr-CA-AntoineNeural | Défaut | Voix naturelle — nécessite internet |
| 2 | **Kokoro** ff_siwis CUDA | Repli local | 100 % local — GPU NVIDIA, fonctionne hors-ligne |

La cascade est automatique : si Edge échoue (hors ligne), Kokoro neural prend le relais sans interruption.

---

## Cache TTS — restitution instantanée

Les phrases récurrentes (confirmations, menu vocal, réponses figées) sont
mémorisées après leur première synthèse et resservies sans re-génération.

| Aspect | Choix de conception |
|--------|--------------------|
| **Clé** | `sha256(texte + voix + moteur + paramètres DSP)` — un changement de voix/DSP invalide l'entrée, jamais d'audio périmé |
| **Robustesse** | Best-effort intégral : tout échec du cache est avalé → repli sur la génération normale, la voix ne casse jamais |
| **Volume** | LRU borné (éviction des plus anciennes par `mtime`) — disque maîtrisé |
| **Priorité** | Interrogé *après* l'anti-double-lecture → la déduplication reste prioritaire |

> Un hit cache se journalise `total=0.00s` contre ~0,5–3 s de synthèse — gain
> net sur les interactions répétées, sans complexité ajoutée au chemin critique.

---

## STT — Transcription vocale

| Paramètre | Valeur |
|-----------|--------|
| Modèle | faster-whisper `large-v3-turbo` |
| Accélération | CUDA float16 (GPU NVIDIA) |
| Langue | Français |
| VAD filter | True (filtre silence) |
| initial_prompt | Vocabulaire SOC spécialisé |

---

## Calibration loudness FX (`_FX_SEND_CAL`)

La convolution avec taps discrets (echo, delay) crée une perception loudness plus élevée
qu'une réverb diffuse à RMS égal. Chaque effet est calibré :

| Effet | Send gain | dB |
|-------|-----------|-----|
| reverb | 1.00 | 0 dB — référence |
| echo | 0.35 | -9 dB — taps stéréo forts |
| delay | 0.45 | -7 dB — taps mono forts |

---

## Crossfade equal-power (dry/wet)

Évite le creux de -3 dB d'un crossfade linéaire :

```
wet_gain = sin(wet × π/2)
dry_gain = cos(wet × π/2)
→ puissance totale constante quelle que soit la valeur du wet
```

---

## DSP avancé

| Bloc | Rôle |
|------|------|
| **DeepFilterNet** | Débruitage IA GPU (désactivé par défaut — activer manuellement) |
| **Haas stéréo** | Élargissement image (canal R retardé 18 ms) |
| **Analyseur FFT** | 4 modes : mirror / scope / piano / split |

---

## Règles absolues

| # | Règle | Raison |
|---|-------|--------|
| 1 | Ne jamais reconnecter analyser → analyserL/R | Boucle de rétroaction — sifflement |
| 2 | Tout nouveau FX doit avoir une entrée `_FX_SEND_CAL` | Sinon loudness incohérente |
| 3 | Ne jamais connecter directement à `audioCtx.destination` | Bypass du brick-wall |

---

**Précédent ←** [03 — Architecture](03-ARCHITECTURE.md) &nbsp;&nbsp; **Suivant →** [05 — Installation](05-INSTALLATION.md)

---

<div align="center">

<table>
<tr>
<td align="center"><b>🖥️ Infrastructure &amp; Sécurité</b></td>
<td align="center"><b>💻 Développement &amp; Web</b></td>
<td align="center"><b>🤖 Intelligence Artificielle</b></td>
</tr>
<tr>
<td align="center">
  <a href="https://www.kernel.org/"><img src="https://skillicons.dev/icons?i=linux" width="48" title="Linux" /></a>
  <a href="https://www.debian.org"><img src="https://skillicons.dev/icons?i=debian" width="48" title="Debian" /></a>
  <a href="https://www.gnu.org/software/bash/"><img src="https://skillicons.dev/icons?i=bash" width="48" title="Bash" /></a>
  <br/>
  <a href="https://nginx.org"><img src="https://skillicons.dev/icons?i=nginx" width="48" title="Nginx" /></a>
  <a href="https://git-scm.com"><img src="https://skillicons.dev/icons?i=git" width="48" title="Git" /></a>
</td>
<td align="center">
  <a href="https://www.python.org"><img src="https://skillicons.dev/icons?i=python" width="48" title="Python" /></a>
  <a href="https://flask.palletsprojects.com"><img src="https://skillicons.dev/icons?i=flask" width="48" title="Flask" /></a>
  <a href="https://developer.mozilla.org/docs/Web/HTML"><img src="https://skillicons.dev/icons?i=html" width="48" title="HTML5" /></a>
  <br/>
  <a href="https://developer.mozilla.org/docs/Web/CSS"><img src="https://skillicons.dev/icons?i=css" width="48" title="CSS3" /></a>
  <a href="https://developer.mozilla.org/docs/Web/JavaScript"><img src="https://skillicons.dev/icons?i=js" width="48" title="JavaScript" /></a>
  <a href="https://code.visualstudio.com"><img src="https://skillicons.dev/icons?i=vscode" width="48" title="VS Code" /></a>
</td>
<td align="center">
  <a href="https://ollama.com"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" /></a>
  <br/><br/>
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic" /></a>
</td>
</tr>
</table>

<br/>

<sub>🔒 Projets proposés par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Développés en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</sub>

</div>
