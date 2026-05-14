// ══════════════════════════════════════════════════════════════
// STT — Reconnaissance vocale locale (faster-whisper)
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Capture micro (MediaRecorder) → POST /api/stt → transcription dans le chat.
// Fichier .js classique (scope global) — sttToggle appelé via data-action.
// Chargé APRÈS jarvis_main.js.

// ═══════════════════════════════════════════════════════════
// STT — RECONNAISSANCE VOCALE LOCALE (WHISPER)
// ═══════════════════════════════════════════════════════════
let _sttRecorder = null, _sttChunks = [], _sttRecording = false, _sttStream = null;

async function sttToggle() {
  if (_sttRecording) {
    sttStop();
  } else {
    await sttStart();
  }
}

async function sttStart() {
  const btn = document.getElementById('btn-mic');
  try {
    // Larsen fix: echo cancellation + refuse si JARVIS parle vraiment (source audio active)
    if (_currentAudioSource !== null) return;
    _sttStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: false }
    });
    _sttChunks = [];
    _sttRecorder = new MediaRecorder(_sttStream, { mimeType: 'audio/webm;codecs=opus' });
    _sttRecorder.ondataavailable = e => { if (e.data.size > 0) _sttChunks.push(e.data); };
    _sttRecorder.onstop = () => sttSend();
    _sttRecorder.start();
    _sttRecording = true;
    if (btn) { btn.classList.add('recording'); btn.title = 'Cliquer pour arrêter'; }
    const inp = document.getElementById('user-input');
    if (inp) { inp.placeholder = '● REC — parlez…'; inp.disabled = true; }
  } catch(e) {
    alert('Accès micro refusé : ' + e.message);
    _sttRecording = false;
  }
}

function sttStop() {
  if (_sttRecorder && _sttRecording) {
    _sttRecorder.stop();
    _sttRecording = false;
    if (_sttStream) { _sttStream.getTracks().forEach(t => t.stop()); _sttStream = null; }
    const btn = document.getElementById('btn-mic');
    if (btn) { btn.classList.remove('recording'); btn.classList.add('processing'); btn.title = 'Transcription…'; }
    const inp = document.getElementById('user-input');
    if (inp) inp.placeholder = '⏳ Transcription Whisper…';
  }
}

async function sttSend() {
  const btn = document.getElementById('btn-mic');
  const inp = document.getElementById('user-input');
  try {
    const blob = new Blob(_sttChunks, { type: 'audio/webm' });
    const fd = new FormData();
    fd.append('audio', blob, 'record.webm');
    fd.append('lang', 'fr');
    const r = await fetch('/api/stt', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.error) {
      if (inp) { inp.placeholder = '⚠ ' + d.error; inp.disabled = false; }
    } else if (d.text) {
      const _txt = d.text.trim();
      // Commandes stop interceptées avant envoi au LLM
      const _stopWords = /^(stop|arrête|arrêtes|tais.?toi|silence|ça suffit|ferme.?la|coupe|interromps?|chut)[\s!.]*$/i;
      if (_stopWords.test(_txt)) {
        stopJarvis();
        if (inp) { inp.value = ''; inp.disabled = false; inp.placeholder = 'ENTREZ COMMANDE...'; }
        return;
      }
      if (inp) {
        // Mode vocal : préfixe pour forcer réponse courte et orale
        inp.value = '[VOCAL] ' + _txt;
        inp.disabled = false;
        inp.placeholder = 'ENTREZ COMMANDE...';
      }
      // Auto-envoi après transcription vocale
      setTimeout(() => sendMessage(), 120);
    } else {
      if (inp) { inp.placeholder = '— aucune voix détectée —'; inp.disabled = false; }
    }
  } catch(e) {
    if (inp) { inp.placeholder = '⚠ Erreur STT: ' + e.message; inp.disabled = false; }
  } finally {
    if (btn) { btn.classList.remove('processing', 'recording'); btn.title = 'Reconnaissance vocale locale (Whisper)'; }
    setTimeout(() => { if (inp && !inp.value) inp.placeholder = 'ENTREZ COMMANDE...'; }, 3000);
  }
}

// Vérif disponibilité STT au démarrage
async function sttCheckStatus() {
  try {
    const r = await fetch('/api/stt/status');
    const d = await r.json();
    const btn = document.getElementById('btn-mic');
    if (!btn) return;
    if (d.available === false) {
      btn.title = 'STT indisponible — pip install faster-whisper';
      btn.style.opacity = '.3';
      btn.onclick = () => alert('Installez faster-whisper :\npip install faster-whisper');
    } else {
      btn.title = d.loaded ? `Whisper '${d.model}' prêt` : `Whisper '${d.model}' (1er appel = chargement)`;
    }
  } catch(e) { /* silencieux */ }
}
