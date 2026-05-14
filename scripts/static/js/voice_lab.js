// ══════════════════════════════════════════════════════════════
// VOICE LAB — onglet d'expérimentation vocale (presets, A/B, EQ voix)
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// IIFE auto-contenu (déjà encapsulé dans jarvis_main.js, manqué en session 33c).
// Fonctions publiques exposées via window.vlab*/window.initVoiceLab.
// Chargé APRÈS jarvis_main.js : dépend de audioCtx, escHtml, setDspLocalVoice,
// setTtsEngine, stopAudio (restent dans jarvis_main.js — scope global partagé).

// ═══════════════════════════════════════════════════════════
// VOICE LAB
// ═══════════════════════════════════════════════════════════

(function() {

/* ── State ── */
const _STORAGE_KEY = 'vlab_presets_v1';
let _vlPresets      = [];          // array of preset objects
let _vlSelected     = null;        // id of selected preset
let _vlEngine       = 'edge';
let _vlVoice        = '';
let _vlParams       = { speed:1.0, pitch:0, volume:100, eq:{low:0,mid:0,high:0,air:0} };
let _vlWaveRAF      = null;
let _vlWaveCtx      = null;
let _vlWaveAn       = null;
let _vlInited       = false;

/* ── Init ── */
window.initVoiceLab = async function() {
  if (_vlInited) { _vlRenderPresets(); return; }
  _vlInited = true;

  // Load presets from localStorage
  try { _vlPresets = JSON.parse(localStorage.getItem(_STORAGE_KEY)) || []; } catch(e) { _vlPresets = []; }
  if (!_vlPresets.length) _vlSeedDefaults();

  // Init waveform canvas
  const canvas = document.getElementById('vlab-wave');
  if (canvas) {
    _vlWaveCtx = canvas.getContext('2d');
    _vlResizeCanvas(canvas);
  }

  // Detect current engine from DSP state
  try {
    const d = await _fetchDspParams();
    const eng = d.tts_engine || 'edge';
    _vlEngine = eng;
    _vlVoice  = d.tts_local_voice || '';
    // Also sync sliders from DSP
    const spEl = document.getElementById('dsp-speed');
    const ptEl = document.getElementById('dsp-pitch');
    const vlEl = document.getElementById('dsp-vol');
    if (spEl) _vlParams.speed  = parseFloat(spEl.value);
    if (ptEl) _vlParams.pitch  = parseInt(ptEl.value);
    if (vlEl) _vlParams.volume = parseFloat(vlEl.value);
  } catch(e) { /* DOM not ready */ }

  _vlUpdateEngineUI(_vlEngine);
  await _vlLoadVoices(_vlEngine);
  _vlApplyParamsToUI();
  _vlRenderPresets();
  _vlRenderAbSelects();
};

/* ── Engine selection ── */
window.vlabSetEngine = async function(eng) {
  _vlEngine = eng;
  _vlUpdateEngineUI(eng);
  await _vlLoadVoices(eng);
  // sync to backend
  await setTtsEngine(eng);
  _vlStatus('engine', '● MOTEUR ' + eng.toUpperCase() + ' ACTIF');
};

function _vlUpdateEngineUI(eng) {
  ['kokoro','piper','sapi','edge'].forEach(k => {
    const btn = document.getElementById('vlab-eng-' + k);
    if (!btn) return;
    btn.classList.toggle('active', k === eng);
  });
}

async function _vlLoadVoices(eng) {
  const sel = document.getElementById('vlab-voice-sel');
  if (!sel) return;
  sel.innerHTML = '<option value="">— chargement… —</option>';
  try {
    if (eng === 'edge') {
      // Edge voices are available via browser's voice-select or from DSP panel
      const mainSel = document.getElementById('voice-select');
      if (mainSel && mainSel.options.length > 1) {
        sel.innerHTML = mainSel.innerHTML;
        sel.value = mainSel.value;
      } else {
        sel.innerHTML = '<option value="">— voix Edge (voir DSP) —</option>';
      }
    } else {
      const r = await fetch('/api/tts/local/voices');
      const d = await r.json();
      let voices = [];
      if (eng === 'kokoro' && d.kokoro?.voices?.length)
        voices = d.kokoro.voices.map(v => ({value:v.id, label:v.name}));
      else if (eng === 'piper' && d.piper?.models?.length)
        voices = d.piper.models.map(m => ({value:m, label:m}));
      else if (eng === 'sapi' && d.sapi?.voices?.length)
        voices = d.sapi.voices.map(v => ({value:v.id, label:v.name}));
      if (!voices.length)
        voices = [{value:'', label:'— aucune voix disponible pour ce moteur —'}];
      sel.innerHTML = voices.map(v =>
        `<option value="${v.value}"${v.value===_vlVoice?' selected':''}>${v.label}</option>`
      ).join('');
    }
    _vlVoice = sel.value;
  } catch(e) {
    sel.innerHTML = '<option value="">— erreur chargement —</option>';
  }
}

window.vlabSetVoice = async function(val) {
  _vlVoice = val;
  if (_vlEngine !== 'edge') {
    await fetch('/api/dsp-params', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ tts_local_voice: val })
    }).catch(()=>{});
  } else {
    // Edge: switch via existing function
    if (typeof switchVoice === 'function') await switchVoice(val);
  }
};

/* ── Sliders ── */
window.vlabSlider = function(param, val) {
  val = parseFloat(val);
  if (param === 'speed') {
    _vlParams.speed = val;
    const el = document.getElementById('vlab-speed-val');
    if (el) el.textContent = val.toFixed(2) + '×';
    _vlUpdateSliderBg('vlab-speed', 0.5, 2.0, val);
    // sync to DSP
    if (typeof setDspSpeed === 'function') setDspSpeed(val);
    const dspSl = document.getElementById('dsp-speed');
    if (dspSl) dspSl.value = val;
  } else if (param === 'pitch') {
    _vlParams.pitch = val;
    const el = document.getElementById('vlab-pitch-val');
    if (el) el.textContent = (val >= 0 ? '+' : '') + val + ' st';
    _vlUpdateSliderBg('vlab-pitch', -12, 12, val);
    if (typeof setDspPitch === 'function') setDspPitch(val);
    const dspSl = document.getElementById('dsp-pitch');
    if (dspSl) dspSl.value = val;
  } else if (param === 'volume') {
    _vlParams.volume = val;
    const el = document.getElementById('vlab-volume-val');
    if (el) el.textContent = Math.round(val) + '%';
    _vlUpdateSliderBg('vlab-volume', 0, 150, val);
    if (typeof setDspVolume === 'function') setDspVolume(val);
    const dspSl = document.getElementById('dsp-vol');
    if (dspSl) dspSl.value = val;
  }
};

window.vlabEq = function(band, val) {
  val = parseInt(val);
  _vlParams.eq[band] = val;
  const el = document.getElementById('vlab-eq-' + band + '-val');
  if (el) el.textContent = (val > 0 ? '+' : '') + val;
  _vlUpdateSliderBg('vlab-eq-' + band, -12, 12, val);
  // sync to DSP
  if (typeof setEqBand === 'function') setEqBand(band, val);
  const dspSl = document.getElementById('eq-' + band);
  if (dspSl) dspSl.value = val;
};

function _vlUpdateSliderBg(id, min, max, val) {
  const el = document.getElementById(id);
  if (!el) return;
  const pct = ((val - min) / (max - min) * 100).toFixed(1) + '%';
  el.style.setProperty('--f-pct', pct);  // --f-pct est lu par .rack-fader background
}

window.vlabResetAll = function() {
  _vlParams = { speed:1.0, pitch:0, volume:100, eq:{low:0,mid:0,high:0,air:0} };
  // Sliders
  const sl = { 'vlab-speed':[0.5,2.0,1.0], 'vlab-pitch':[-12,12,0], 'vlab-volume':[0,150,100],
               'vlab-eq-low':[-12,12,0], 'vlab-eq-mid':[-12,12,0],
               'vlab-eq-high':[-12,12,0], 'vlab-eq-air':[-12,12,0] };
  Object.entries(sl).forEach(([id,[mn,mx,def]]) => {
    const el = document.getElementById(id);
    if (el) el.value = def;
    _vlUpdateSliderBg(id, mn, mx, def);
  });
  // Labels
  const sv = document.getElementById('vlab-speed-val');  if (sv) sv.textContent = '1.00×';
  const pv = document.getElementById('vlab-pitch-val');  if (pv) pv.textContent = '+0 st';
  const vv = document.getElementById('vlab-volume-val'); if (vv) vv.textContent = '100%';
  ['low','mid','high','air'].forEach(b => {
    const lbl = document.getElementById('vlab-eq-' + b + '-val');
    if (lbl) lbl.textContent = '0';
  });
  // Sync DSP
  if (typeof setDspSpeed  === 'function') setDspSpeed(1.0);
  if (typeof setDspPitch  === 'function') setDspPitch(0);
  if (typeof setDspVolume === 'function') setDspVolume(100);
  ['low','mid','high','air'].forEach(b => {
    if (typeof setEqBand === 'function') setEqBand(b, 0);
    const dspSl = document.getElementById('eq-' + b);
    if (dspSl) { dspSl.value = 0; updateSliderPct(dspSl); }
  });
  const stEl = document.getElementById('vlab-engine-status');
  if (stEl) stEl.textContent = '◉ RÉINITIALISÉ';
  setTimeout(() => { if (stEl) stEl.textContent = '◉ EN ATTENTE'; }, 1800);
};

function _vlApplyParamsToUI() {
  const p = _vlParams;
  const speedEl = document.getElementById('vlab-speed');
  if (speedEl) { speedEl.value = p.speed; }
  const pitchEl = document.getElementById('vlab-pitch');
  if (pitchEl) { pitchEl.value = p.pitch; }
  const volEl = document.getElementById('vlab-volume');
  if (volEl) { volEl.value = p.volume; }

  const svEl = document.getElementById('vlab-speed-val');
  if (svEl) svEl.textContent = parseFloat(p.speed).toFixed(2) + '×';
  const pvEl = document.getElementById('vlab-pitch-val');
  if (pvEl) pvEl.textContent = (p.pitch >= 0 ? '+' : '') + p.pitch + ' st';
  const vvEl = document.getElementById('vlab-volume-val');
  if (vvEl) vvEl.textContent = Math.round(p.volume) + '%';

  ['low','mid','high','air'].forEach(b => {
    const sl = document.getElementById('vlab-eq-' + b);
    const lb = document.getElementById('vlab-eq-' + b + '-val');
    const v  = p.eq[b] || 0;
    if (sl) sl.value = v;
    if (lb) lb.textContent = (v > 0 ? '+' : '') + v;
    _vlUpdateSliderBg('vlab-eq-' + b, -12, 12, v);
  });

  _vlUpdateSliderBg('vlab-speed',  0.5, 2.0, p.speed);
  _vlUpdateSliderBg('vlab-pitch',  -12, 12,  p.pitch);
  _vlUpdateSliderBg('vlab-volume', 0,   150,  p.volume);
}

/* ── Preview / Stop ── */
window.vlabPreview = async function() {
  const phrase = (document.getElementById('vlab-phrase')?.value || '').trim();
  if (!phrase) return;
  _vlStatus('play', '▶ SYNTHÈSE EN COURS…');
  _vlStartWave();
  try {
    // playSentence est la fonction TTS bas niveau (pas de gate ttsEnabled)
    if (typeof playSentence === 'function') {
      await playSentence(phrase);
      _vlStatus('play', '✓ LECTURE TERMINÉE');
    } else {
      // fallback : passer par l'API /api/tts directement
      const resp = await fetch('/api/tts', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({text: phrase})
      });
      if (!resp.ok) throw new Error('API TTS ' + resp.status);
      const buf = await resp.arrayBuffer();
      const ac = typeof audioCtx !== 'undefined' ? audioCtx
               : (typeof _ctx === 'function' ? _ctx() : null);
      if (!ac) throw new Error('AudioContext indisponible');
      if (ac.state === 'suspended') await ac.resume();
      const audioBuf = await ac.decodeAudioData(buf);
      const src = ac.createBufferSource();
      src.buffer = audioBuf;
      if (typeof _dspPlaybackRate !== 'undefined') src.playbackRate.value = _dspPlaybackRate;
      if (typeof _dspPitchSemi   !== 'undefined') src.detune.value = _dspPitchSemi * 100;
      // _connectStereoSource est défini globalement — pas de fallback bypass
      _connectStereoSource(src);
      src.start();
      await new Promise(res => { src.onended = res; });
      _vlStatus('play', '✓ LECTURE TERMINÉE');
    }
  } catch(e) {
    _vlStatus('play', '⚠ ' + (e.message || e));
  }
  setTimeout(() => _vlStopWave(), 500);
};

window.vlabStop = function() {
  if (typeof stopAudio === 'function') stopAudio();
  _vlStatus('play', '⏹ ARRÊT');
  _vlStopWave();
};

/* ── Sync to DSP ── */
window.vlabSyncToDsp = function() {
  ['low','mid','high','air'].forEach(b => {
    const v = _vlParams.eq[b];
    if (typeof setEqBand === 'function') setEqBand(b, v);
    const sl = document.getElementById('eq-' + b);
    if (sl) sl.value = v;
  });
  if (typeof setDspSpeed  === 'function') setDspSpeed(_vlParams.speed);
  if (typeof setDspPitch  === 'function') setDspPitch(_vlParams.pitch);
  if (typeof setDspVolume === 'function') setDspVolume(_vlParams.volume);
  _vlStatus('play', '⇥ PARAMÈTRES APPLIQUÉS AU DSP');
  setTimeout(() => _vlStatus('play', ''), 2500);
};

/* ── Waveform ── */
function _vlStartWave() {
  if (_vlWaveRAF) return;
  const canvas = document.getElementById('vlab-wave');
  if (!canvas || !_vlWaveCtx) return;
  _vlResizeCanvas(canvas);

  const ac = (typeof _ctx === 'function') ? _ctx() : null;
  if (ac && typeof analyser !== 'undefined' && analyser) {
    _vlWaveAn = analyser;
  }

  function _draw() {
    _vlWaveRAF = requestAnimationFrame(_draw);
    const w = canvas.width, h = canvas.height;
    const ctx = _vlWaveCtx;
    ctx.clearRect(0,0,w,h);
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(0,0,w,h);

    if (_vlWaveAn) {
      const buf = new Uint8Array(_vlWaveAn.frequencyBinCount);
      _vlWaveAn.getByteTimeDomainData(buf);
      ctx.beginPath();
      ctx.strokeStyle = '#00cfff';
      ctx.lineWidth = 1.5;
      ctx.shadowColor = '#00cfff';
      ctx.shadowBlur = 6;
      for (let i = 0; i < buf.length; i++) {
        const x = (i / buf.length) * w;
        const y = (buf[i] / 255) * h;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
    } else {
      // idle flat line with noise
      ctx.beginPath();
      ctx.strokeStyle = '#00cfff33';
      ctx.lineWidth = 1;
      ctx.moveTo(0, h/2);
      ctx.lineTo(w, h/2);
      ctx.stroke();
    }
  }
  _draw();
}

function _vlStopWave() {
  if (_vlWaveRAF) { cancelAnimationFrame(_vlWaveRAF); _vlWaveRAF = null; }
  _vlWaveAn = null;
  const canvas = document.getElementById('vlab-wave');
  if (canvas && _vlWaveCtx) {
    const w = canvas.width, h = canvas.height;
    _vlWaveCtx.clearRect(0,0,w,h);
    _vlWaveCtx.fillStyle = 'rgba(0,0,0,0.6)';
    _vlWaveCtx.fillRect(0,0,w,h);
    _vlWaveCtx.beginPath();
    _vlWaveCtx.strokeStyle = '#00cfff22';
    _vlWaveCtx.lineWidth = 1;
    _vlWaveCtx.moveTo(0,h/2);
    _vlWaveCtx.lineTo(w,h/2);
    _vlWaveCtx.stroke();
  }
}

function _vlResizeCanvas(canvas) {
  canvas.width  = canvas.offsetWidth  || 400;
  canvas.height = canvas.offsetHeight || 60;
}

/* ── Presets ── */
function _vlSeedDefaults() {
  _vlPresets = [
    { id:'default-1', name:'JARVIS Standard',   engine:'edge',   voice:'fr-CA-AntoineNeural',  speed:1.0,  pitch:0,  volume:100, eq:{low:2, mid:0, high:3, air:2} },
    { id:'default-2', name:'Voix Grave',         engine:'edge',   voice:'fr-CA-AntoineNeural',  speed:0.9,  pitch:-4, volume:100, eq:{low:5, mid:0, high:0, air:0} },
    { id:'default-3', name:'Voix Aiguë',         engine:'edge',   voice:'fr-FR-DeniseNeural',   speed:1.1,  pitch:4,  volume:100, eq:{low:0, mid:0, high:4, air:3} },
    { id:'default-4', name:'Radio FM',            engine:'edge',   voice:'fr-CA-AntoineNeural',  speed:1.05, pitch:0,  volume:110, eq:{low:-2,mid:2, high:5, air:4} },
    { id:'default-5', name:'Kokoro Neural',       engine:'kokoro', voice:'',                     speed:1.0,  pitch:0,  volume:100, eq:{low:0, mid:0, high:0, air:0} },
  ];
  _vlSavePresets();
}

function _vlSavePresets() {
  try { localStorage.setItem(_STORAGE_KEY, JSON.stringify(_vlPresets)); } catch(e) {}
}

function _vlRenderPresets() {
  const list = document.getElementById('vlab-preset-list');
  if (!list) return;
  if (!_vlPresets.length) {
    list.innerHTML = '<div class="vlab-preset-empty">Aucun preset</div>';
    return;
  }
  list.innerHTML = _vlPresets.map(p => `
    <div class="vlab-preset-item ${p.id === _vlSelected ? 'selected' : ''}"
         onclick="vlabSelectPreset('${p.id}')">
      <div class="vlab-preset-dot"></div>
      <span class="vlab-preset-name">${escHtml(p.name)}</span>
      <span class="vlab-preset-engine">${p.engine.toUpperCase()}</span>
    </div>
  `).join('');
}

window.vlabSelectPreset = async function(id) {
  const p = _vlPresets.find(x => x.id === id);
  if (!p) return;
  _vlSelected = id;
  _vlEngine   = p.engine;
  _vlVoice    = p.voice;
  _vlParams   = { speed:p.speed, pitch:p.pitch, volume:p.volume, eq:{...p.eq} };

  _vlUpdateEngineUI(p.engine);
  await _vlLoadVoices(p.engine);
  const sel = document.getElementById('vlab-voice-sel');
  if (sel && p.voice) sel.value = p.voice;

  _vlApplyParamsToUI();
  _vlRenderPresets();
  _vlStatus('preset', `✓ PRESET «${p.name}» CHARGÉ`);
  setTimeout(() => _vlStatus('preset', ''), 2500);
};

window.vlabSavePreset = function() {
  const name = prompt('Nom du preset :', _vlPresets.find(x=>x.id===_vlSelected)?.name || 'Nouveau Preset');
  if (!name) return;
  const id = _vlSelected && !_vlSelected.startsWith('default-') ? _vlSelected
           : 'p_' + Date.now();
  const existing = _vlPresets.findIndex(x => x.id === id);
  const preset = {
    id, name,
    engine: _vlEngine, voice: _vlVoice,
    speed:   _vlParams.speed,
    pitch:   _vlParams.pitch,
    volume:  _vlParams.volume,
    eq:      { ..._vlParams.eq },
    created: Date.now()
  };
  if (existing >= 0) _vlPresets[existing] = preset;
  else               _vlPresets.push(preset);
  _vlSelected = id;
  _vlSavePresets();
  _vlRenderPresets();
  _vlRenderAbSelects();
  _vlStatus('preset', `✓ PRESET «${name}» SAUVEGARDÉ`);
  setTimeout(() => _vlStatus('preset', ''), 2500);
};

window.vlabDeletePreset = function() {
  if (!_vlSelected) return;
  const p = _vlPresets.find(x => x.id === _vlSelected);
  if (!p) return;
  if (!confirm(`Supprimer le preset «${p.name}» ?`)) return;
  _vlPresets = _vlPresets.filter(x => x.id !== _vlSelected);
  _vlSelected = _vlPresets.length ? _vlPresets[0].id : null;
  _vlSavePresets();
  _vlRenderPresets();
  _vlRenderAbSelects();
  _vlStatus('preset', '✕ PRESET SUPPRIMÉ');
  setTimeout(() => _vlStatus('preset', ''), 2000);
};

window.vlabExportPresets = function() {
  const json = JSON.stringify(_vlPresets, null, 2);
  const blob = new Blob([json], {type:'application/json'});
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'vlab_presets_' + Date.now() + '.json';
  a.click(); URL.revokeObjectURL(url);
  _vlStatus('preset', '⬇ EXPORT TERMINÉ');
  setTimeout(() => _vlStatus('preset', ''), 2000);
};

window.vlabImportPresets = function() {
  const inp = document.getElementById('vlab-import-file');
  if (inp) inp.click();
};

window.vlabDoImport = function(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const data = JSON.parse(e.target.result);
      if (!Array.isArray(data)) throw new Error('Format invalide');
      // Avoid duplicates by id
      data.forEach(p => {
        if (!_vlPresets.find(x => x.id === p.id)) _vlPresets.push(p);
      });
      _vlSavePresets();
      _vlRenderPresets();
      _vlRenderAbSelects();
      _vlStatus('preset', `✓ ${data.length} PRESETS IMPORTÉS`);
      setTimeout(() => _vlStatus('preset', ''), 2500);
    } catch(err) {
      _vlStatus('preset', '⚠ Fichier invalide : ' + err.message);
    }
  };
  reader.readAsText(file);
  input.value = '';
};

/* ── A/B Comparator ── */
function _vlRenderAbSelects() {
  ['vlab-ab-a','vlab-ab-b'].forEach(selId => {
    const sel = document.getElementById(selId);
    if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = '<option value="">— sélectionner —</option>' +
      _vlPresets.map(p =>
        `<option value="${p.id}"${p.id===cur?' selected':''}>${escHtml(p.name)}</option>`
      ).join('');
    if (cur) sel.value = cur;
  });
}

window.vlabAbTest = async function(slot) {
  const selId = slot === 'a' ? 'vlab-ab-a' : 'vlab-ab-b';
  const sel   = document.getElementById(selId);
  if (!sel || !sel.value) { _vlStatus('ab', '⚠ Sélectionner un preset ' + slot.toUpperCase()); return; }
  const p = _vlPresets.find(x => x.id === sel.value);
  if (!p) return;
  _vlStatus('ab', `▶ TEST ${slot.toUpperCase()} — ${p.name}…`);

  // Apply preset temporarily
  await _vlApplyPresetToEngine(p);

  const phrase = (document.getElementById('vlab-phrase')?.value || '').trim()
               || 'Ceci est un test de voix.';
  try {
    if (typeof playSentence === 'function') await playSentence(phrase);
  } catch(e) { /* TTS playback failure — status shown above */ }
  _vlStatus('ab', `✓ ${slot.toUpperCase()} TERMINÉ — ${p.name}`);
};

window.vlabAbSwitch = function() {
  const selA = document.getElementById('vlab-ab-a');
  const selB = document.getElementById('vlab-ab-b');
  if (!selA || !selB) return;
  const tmp = selA.value;
  selA.value = selB.value;
  selB.value = tmp;
  _vlStatus('ab', '↔ A/B INVERSÉ');
};

async function _vlApplyPresetToEngine(p) {
  if (p.engine !== _vlEngine) {
    _vlEngine = p.engine;
    _vlUpdateEngineUI(p.engine);
    await setTtsEngine(p.engine);
  }
  if (p.voice && p.voice !== _vlVoice) {
    _vlVoice = p.voice;
    if (p.engine === 'edge' && typeof switchVoice === 'function') await switchVoice(p.voice);
    else if (typeof setDspLocalVoice === 'function') await setDspLocalVoice(p.voice);
  }
  if (typeof setDspSpeed  === 'function') setDspSpeed(p.speed);
  if (typeof setDspPitch  === 'function') setDspPitch(p.pitch);
  if (typeof setDspVolume === 'function') setDspVolume(p.volume);
  ['low','mid','high','air'].forEach(b => {
    if (typeof setEqBand === 'function') setEqBand(b, p.eq[b] || 0);
  });
}

/* ── Helpers ── */
function _vlStatus(area, msg) {
  const ids = { engine:'vlab-engine-status', play:'vlab-play-status', preset:'vlab-preset-status', ab:'vlab-ab-status' };
  const el = document.getElementById(ids[area]);
  if (el) el.textContent = msg;
}

})(); // end VOICE LAB IIFE
