# Étape 3 — Pipeline audio : TTS, STT, DeepFilterNet

## Objectif
Donner une voix à JARVIS :
- **TTS** (Text-to-Speech) : JARVIS parle
- **STT** (Speech-to-Text) : JARVIS écoute
- **DeepFilterNet** : suppression de bruit micro en temps réel

```
Micro → DeepFilterNet (NR) → faster-whisper (STT) → texte → LLM → texte → edge-tts (TTS) → haut-parleurs
```

---

## Étape 3.1 — TTS avec edge-tts

`edge-tts` utilise les voix Microsoft Azure via le protocole WebSocket public.  
Aucun compte ni API key requis.

```python
import asyncio
import edge_tts
import os

TTS_VOICE  = "fr-CA-AntoineNeural"   # Voix française masculine naturelle
TTS_OUTPUT = "/tmp/jarvis_tts.mp3"

async def synthesize(text: str, voice: str = TTS_VOICE) -> str:
    """Génère un fichier MP3 depuis un texte."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(TTS_OUTPUT)
    return TTS_OUTPUT

# Voix disponibles en français
async def list_french_voices():
    voices = await edge_tts.list_voices()
    return [v for v in voices if v["Locale"].startswith("fr")]

# Utilisation
asyncio.run(synthesize("Bonjour, je suis JARVIS, votre assistant IA."))
```

### Voix françaises recommandées

| Voix | Genre | Qualité |
|------|-------|---------|
| `fr-CA-AntoineNeural` | Masculin | ⭐⭐⭐⭐⭐ Naturel |
| `fr-FR-HenriNeural` | Masculin | ⭐⭐⭐⭐ |
| `fr-FR-DeniseNeural` | Féminin | ⭐⭐⭐⭐ |

---

## Étape 3.2 — File d'attente TTS (anti-doublon)

```python
import threading, asyncio, queue

_tts_queue  = queue.Queue()
_tts_lock   = threading.Lock()
_tts_active = False

def speak(text: str, priority: bool = False):
    """
    Ajoute un texte à la file TTS.
    priority=True : vide la file et parle immédiatement.
    """
    global _tts_active
    if priority:
        # Vider la file
        while not _tts_queue.empty():
            try: _tts_queue.get_nowait()
            except queue.Empty: break

    _tts_queue.put(text)
    _ensure_tts_worker()

def _ensure_tts_worker():
    """Démarre le worker TTS s'il n'est pas actif."""
    global _tts_active
    if not _tts_active:
        threading.Thread(target=_tts_worker, daemon=True).start()

def _tts_worker():
    global _tts_active
    _tts_active = True
    try:
        while True:
            try:
                text = _tts_queue.get(timeout=2)
            except queue.Empty:
                break
            with _tts_lock:
                asyncio.run(synthesize(text))
                _play_audio(TTS_OUTPUT)
    finally:
        _tts_active = False

def _play_audio(filepath: str):
    """Lecture du fichier audio (cross-platform)."""
    import subprocess, sys
    if sys.platform == "win32":
        subprocess.run(["powershell", "-c", f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"],
                      capture_output=True)
    else:
        subprocess.run(["aplay", filepath], capture_output=True)
```

---

## Étape 3.3 — STT avec faster-whisper

```python
from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np

# Initialiser le modèle (une seule fois au démarrage)
# device="cuda" si GPU NVIDIA disponible, sinon "cpu"
STT_MODEL = WhisperModel(
    "small",
    device="cuda",       # ou "cpu"
    compute_type="float16"  # ou "int8" pour économiser la VRAM
)

def transcribe_audio(audio_array: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Transcrit un tableau numpy audio en texte.
    audio_array : float32, mono, 16kHz
    """
    segments, info = STT_MODEL.transcribe(
        audio_array,
        language="fr",
        beam_size=5,
        vad_filter=True,       # Filtre les silences automatiquement
        vad_parameters={"min_silence_duration_ms": 500},
    )
    text = " ".join(seg.text for seg in segments).strip()
    return text


def record_until_silence(
    sample_rate: int = 16000,
    silence_threshold: float = 0.01,
    silence_duration: float = 1.5,
    max_duration: float = 30.0
) -> np.ndarray:
    """
    Enregistre le micro jusqu'à détection d'un silence de silence_duration secondes.
    Retourne un tableau numpy float32.
    """
    chunk_size = int(sample_rate * 0.1)  # 100ms par chunk
    audio_chunks = []
    silent_chunks = 0
    silent_needed = int(silence_duration / 0.1)
    max_chunks = int(max_duration / 0.1)

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_size)
            audio_chunks.append(chunk)
            rms = np.sqrt(np.mean(chunk ** 2))
            if rms < silence_threshold:
                silent_chunks += 1
                if silent_chunks >= silent_needed:
                    break
            else:
                silent_chunks = 0

    return np.concatenate(audio_chunks, axis=0).flatten()
```

---

## Étape 3.4 — Réduction de bruit avec DeepFilterNet

```python
from df.enhance import enhance, init_df, load_audio, save_audio
import numpy as np

# Initialiser DeepFilterNet (une seule fois)
# device=-1 : CPU, device=0 : GPU (CUDA)
_df_model, _df_state, _df_sr = None, None, None

def _init_deepfilter(device: int = 0):
    global _df_model, _df_state, _df_sr
    if _df_model is None:
        _df_model, _df_state, _df_sr = init_df(device=device)

def denoise_audio(audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """
    Applique DeepFilterNet pour supprimer le bruit de fond.
    audio : float32, mono
    Retourne le signal nettoyé.
    """
    _init_deepfilter()
    # DeepFilterNet attend du float32 à 48kHz
    import librosa
    audio_48k = librosa.resample(audio, orig_sr=sample_rate, target_sr=_df_sr)
    enhanced  = enhance(_df_model, _df_state, audio_48k)
    # Remettre à 16kHz pour Whisper
    return librosa.resample(enhanced, orig_sr=_df_sr, target_sr=sample_rate)
```

---

## Étape 3.5 — Pipeline complet

```python
def listen_and_respond():
    """
    Boucle complète : écoute → NR → transcription → LLM → TTS
    """
    print("En écoute...")

    # 1. Enregistrement
    audio = record_until_silence()

    # 2. Réduction de bruit (si GPU disponible)
    try:
        audio = denoise_audio(audio)
    except Exception:
        pass  # Continuer sans NR si échec

    # 3. Transcription
    text = transcribe_audio(audio)
    if not text:
        return

    print(f"Vous : {text}")

    # 4. LLM (streaming)
    response = ""
    for token in chat_with_llm(text, model=get_active_model(), stream=True):
        response += token
        print(token, end="", flush=True)

    print()

    # 5. TTS
    speak(response)
```

---

**Étape suivante →** [04 — Backend Flask](./04-BACKEND-FLASK.md)
