// ══════════════════════════════════════════════════════════════
// BOOT SEQUENCE + RACK FX + INIT — Démarrage et rack d'effets
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Trois sous-systèmes regroupés sous la bannière « BOOT SEQUENCE »
// de l'original :
//  1. Message vocal d'introduction (playWelcomeSpeech).
//  2. Rack d'effets FX UI : génération d'IR (reverb/echo/delay),
//     crossfade wet/dry, FX2 (modulation server-side), banques
//     mémoire FX 0-9, VU FX piloté par le hook fetch TTS.
//  3. INIT — point d'entrée unique DOMContentLoaded (_jarvisInit).
//
// Fichier .js classique (scope global). Chargé EN DERNIER dans
// jarvis.html : c'est le point d'entrée (registration DOMContentLoaded).

// ── Message vocal d'introduction ────────────────────────────────
const WELCOME_SPEECH = "Systèmes en ligne. Intelligence artificielle activée. Accélération CUDA Blackwell confirmée. Bonjour, Marc. JARVIS est prêt.";

async function playWelcomeSpeech() {
  // Passe par la queue unifiée pour ne jamais chevaucher d'autres prises de parole.
  if (typeof queueSpeech === 'function') queueSpeech(WELCOME_SPEECH);
}

// ── FX RACK control ─────────────────────────────────────────
let _fxActive     = false;
let _dfActive     = false;   // DeepFilterNet
let _compActive   = true;    // Compresseur (ON par défaut)
let _stereoActive = true;    // Stereo Widener (ON par défaut)

// Éteint les VU d'une unité bypassée
function _clearUnitVu(ids) {
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    // rack-meter-fill → width 0
    if (el.classList.contains('rack-meter-fill')) { el.style.width = '0%'; return; }
    // LED strip → enlève classes couleur
    if (el.classList.contains('fx-vu-strip')) {
      el.querySelectorAll('.fx-vu-led').forEach(l => l.classList.remove('g','y','r'));
      return;
    }
    // canvas → efface
    if (el.tagName === 'CANVAS') {
      const ctx = el.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, el.width, el.height);
    }
  });
}
let _fxType   = 'reverb';
let _fxPreset = 'room';

// Calibration SEND par type d'effet — pondération loudness perçue.
// La convolution avec N taps discrets (echo, delay) crée une perception de loudness
// supérieure à une réverbération diffuse à RMS égal. Ce trim compense.
const _FX_SEND_CAL = {
  reverb: 1.00,   //   0 dB — référence (réverb diffuse, perçue douce)
  echo:   0.35,   // -9 dB — N taps discrets stéréo, perception très forte
  delay:  0.45,   // -7 dB — N taps discrets mono, perception forte
};

// Equal-power crossfade wet/dry + calibration loudness par type FX.
// Le sendCal est appliqué directement sur _fxWetGain (chaîne simplifiée sans send séparé).
// smooth: true = setTargetAtTime (transitions live), false = .value direct (init/preset)
const _FX_XFADE_S = 0.003;  // time constant fade FX — 3ms (anti-clic mais réactif perceptible)
function _fxSetWetDry(wet, smooth) {
  if (!_fxWetGain || !_fxDryGain) return;
  var w = Math.max(0, Math.min(1, wet || 0));
  var sendCal = _FX_SEND_CAL[_fx2Type] !== undefined ? _FX_SEND_CAL[_fx2Type] : 1.0;
  var wetGain = Math.sin(w * Math.PI / 2) * sendCal;
  var dryGain = Math.cos(w * Math.PI / 2);
  if (smooth && audioCtx) {
    _fxWetGain.gain.setTargetAtTime(wetGain, audioCtx.currentTime, _FX_XFADE_S);
    _fxDryGain.gain.setTargetAtTime(dryGain, audioCtx.currentTime, _FX_XFADE_S);
  } else {
    _fxWetGain.gain.value = wetGain;
    _fxDryGain.gain.value = dryGain;
  }
}

// Normalise une AudioBuffer IR à un niveau RMS cible.
// NOTE : Avec _fxConvolver.normalize=true (config actuelle), Web Audio applique
// déjà sa propre normalisation equal-power. Ce helper reste disponible pour
// les cas où on désactiverait la normalisation native (debug, IR custom).
function _normalizeIrRms(buf, targetRms) {
  if (!buf) return;
  var energy = 0, totalSamples = 0;
  for (var ch = 0; ch < buf.numberOfChannels; ch++) {
    var d = buf.getChannelData(ch);
    for (var i = 0; i < d.length; i++) energy += d[i] * d[i];
    totalSamples += d.length;
  }
  if (totalSamples === 0) return;
  var rms = Math.sqrt(energy / totalSamples);
  if (rms <= 0) return;
  var scale = targetRms / rms;
  for (var ch2 = 0; ch2 < buf.numberOfChannels; ch2++) {
    var d2 = buf.getChannelData(ch2);
    for (var j = 0; j < d2.length; j++) d2[j] *= scale;
  }
}

// Génère un Impulse Response synthétique pour le ConvolverNode WebAudio
// Supporte reverb, echo, delay — retourne null pour les effets de modulation (server-side)
function _generateFxIr(type, vals) {
  if (!audioCtx) return null;
  const sr = audioCtx.sampleRate;
  vals = vals || {};

  if (type === 'reverb') {
    const decay   = Math.max(0.1, Math.min(8,   vals.fx_decay        || 1.5));
    const preMs   = Math.max(0,   Math.min(100, vals.fx_predelay_ms  || 20));
    const diff    = Math.max(0,   Math.min(1,   vals.fx_diffusion    || 0.6));
    const len     = Math.max(512, Math.ceil(sr * decay * 1.1));
    const buf     = audioCtx.createBuffer(2, len, sr);
    const preSamp = Math.round(sr * preMs / 1000);
    for (var ch = 0; ch < 2; ch++) {
      var d = buf.getChannelData(ch);
      for (var i = preSamp; i < len; i++) {
        var t   = (i - preSamp) / sr;
        var env = Math.exp(-t * 6.91 / decay);
        d[i] = (Math.random() * 2 - 1) * env;
        if (diff > 0 && i < preSamp + Math.round(sr * 0.05)) d[i] *= (1 + diff * 3);
      }
    }
    _normalizeIrRms(buf, 0.18);  // RMS cible uniforme — reverb perçue équilibrée
    return buf;
  }

  if (type === 'echo') {
    var leftMs  = Math.max(50,  Math.min(800,  vals.fx_echo_left_ms   || 375));
    var rightMs = Math.max(50,  Math.min(800,  vals.fx_echo_right_ms  || 250));
    var fb      = Math.max(0,   Math.min(0.95, vals.fx_echo_feedback  || 0.55));
    var maxLen  = Math.ceil(sr * Math.max(leftMs, rightMs) / 1000 * 7);  // 6 taps max + marge → 7× suffit
    var buf2    = audioCtx.createBuffer(2, maxLen, sr);
    [[0, leftMs], [1, rightMs]].forEach(function(cfg) {
      var d  = buf2.getChannelData(cfg[0]);
      var ds = Math.round(sr * cfg[1] / 1000);
      var amp = 0.7;
      for (var tap = 1; tap <= 6 && amp > 0.01; tap++) {  // 6 taps max + seuil -40 dB (réaliste matériel)
        var pos = ds * tap;
        if (pos < maxLen) d[pos] = amp;
        amp *= fb;
      }
    });
    _normalizeIrRms(buf2, 0.18);  // RMS uniforme — même loudness que reverb
    return buf2;
  }

  if (type === 'delay') {
    var delayMs = Math.max(10,  Math.min(1000, vals.fx_delay_ms        || 350));
    var fb3     = Math.max(0,   Math.min(0.95, vals.fx_delay_feedback  || 0.55));
    var maxLen3 = Math.ceil(sr * delayMs / 1000 * 7);  // 6 taps max + marge → 7× suffit
    var buf3    = audioCtx.createBuffer(1, maxLen3, sr);
    var d3      = buf3.getChannelData(0);
    var ds3     = Math.round(sr * delayMs / 1000);
    var amp3    = 0.7;
    for (var tap3 = 1; tap3 <= 6 && amp3 > 0.01; tap3++) {  // 6 taps max + seuil -40 dB (réaliste matériel)
      var pos3 = ds3 * tap3;
      if (pos3 < maxLen3) d3[pos3] = amp3;
      amp3 *= fb3;
    }
    _normalizeIrRms(buf3, 0.18);  // RMS uniforme — même loudness que reverb
    return buf3;
  }

  // Chorus, Flanger, Phaser, Exciter — pas modélisables par convolution
  // Le wet gain restera à 0, l'effet reste server-side
  return null;
}

// Cache IR — évite de recalculer + reload buffer convolver à chaque toggle
// (Web Audio refait la FFT du buffer à chaque assignation = lag perceptible)
let _fxIrCacheKey = null;

function _fxIrKey(type, vals) {
  return type + ':' + JSON.stringify(vals || {});
}

// Force la régénération de l'IR + sync le cache.
// Appelé quand type/params/preset changent (cache devient invalide).
function _fxRefreshIr(type, vals) {
  if (!_fxConvolver) return false;
  const ir = _generateFxIr(type, vals || {});
  if (!ir) { _fxConvolver.buffer = null; _fxIrCacheKey = null; return false; }
  _fxConvolver.buffer = ir;
  _fxIrCacheKey = _fxIrKey(type, vals);
  return true;
}

// Lazy : régénère uniquement si paramètres ont changé. Utilisé au toggle ON.
function _fxEnsureIr() {
  const vals = _fx2Vals[_fx2Type] || {};
  const key  = _fxIrKey(_fx2Type, vals);
  if (key === _fxIrCacheKey && _fxConvolver && _fxConvolver.buffer) return true;
  return _fxRefreshIr(_fx2Type, vals);
}

function rackToggleFx() {
  _fxActive = !_fxActive;
  const unit = document.getElementById('rack-unit-fx');
  const btn  = document.getElementById('rack-fx-bypass');
  const label = document.getElementById('fx-proc-label');
  const node  = document.getElementById('rsp-fx');
  unit && unit.classList.toggle('bypassed', !_fxActive);
  btn  && btn.classList.toggle('on',  _fxActive);
  btn  && btn.classList.toggle('off', !_fxActive);
  if (label) label.textContent = _fxActive ? '◉ ACTIF' : 'BYPASS';
  if (node)  { node.classList.toggle('active', _fxActive); node.classList.remove('fx-bypass-node'); }
  if (!_fxActive) {
    _clearUnitVu(['fx-vu-l','fx-vu-r']);
    ['fx-db-l','fx-db-r'].forEach(id => { const e=document.getElementById(id); if(e){e.textContent='-∞ dB';e.classList.remove('warn','alert');} });
  }
  // WebAudio — switch wet/dry instantané (IR cachée si paramètres inchangés)
  if (_fxDryGain && _fxWetGain && audioCtx) {
    if (_fxActive) {
      if (_fxEnsureIr()) {
        const vals = _fx2Vals[_fx2Type] || {};
        const wet = (vals.fx_wet !== undefined) ? vals.fx_wet
                  : (_FX2[_fx2Type] ? _FX2[_fx2Type].params[0].def : 0.4);
        _fxSetWetDry(wet, true);
      }
      // Si IR null (chorus/flanger/…) : wet reste 0, effet server-side uniquement
    } else {
      _fxSetWetDry(0, true);
    }
  }
  _fxSendParam('fx_enabled', _fxActive);
}


// Specs techniques de chaque preset (correspond aux configs Python _gen_ir)
const _FX_PRESET_SPECS = {
  none:     { rt60:'—',    pre:'—',    diff:'—',   damp:'—',   er:'—',  dens:'—',      label:'BYPASS'    },
  room:     { rt60:'0.6s', pre:'8ms',  diff:'45%', damp:'72%', er:'10', dens:'HIGH',   label:'ROOM'      },
  studio:   { rt60:'0.9s', pre:'10ms', diff:'50%', damp:'80%', er:'12', dens:'HIGH',   label:'STUDIO'    },
  concert:  { rt60:'2.0s', pre:'25ms', diff:'70%', damp:'50%', er:'18', dens:'MEDIUM', label:'CONCERT'   },
  cathedral:{ rt60:'4.0s', pre:'40ms', diff:'90%', damp:'28%', er:'24', dens:'MAX',    label:'CATHEDRAL' },
  plate:    { rt60:'1.5s', pre:'5ms',  diff:'80%', damp:'88%', er:'16', dens:'MAX',    label:'PLATE'     },
  cave:     { rt60:'3.0s', pre:'60ms', diff:'65%', damp:'20%', er:'14', dens:'MEDIUM', label:'CAVE'      },
  spring:   { rt60:'0.9s', pre:'15ms', diff:'35%', damp:'60%', er:'8',  dens:'LOW',    label:'SPRING'    },
};



let _fxParamTimer = null;
function _fxSendParam(key, value) {
  clearTimeout(_fxParamTimer);
  _fxParamTimer = setTimeout(() => {
    fetch('/api/dsp-params', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({[key]: value})
    }).catch(() => {});
  }, 60);
}

// Mettre à jour l'indicateur CUDA sur l'écran FX depuis les stats
function _fxUpdateCudaScreen(cudaVer) {
  const el = document.getElementById('fx-scr-cuda');
  const tag = document.getElementById('fx-cuda-tag');
  if (!el) return;
  if (cudaVer && cudaVer !== 'N/A') {
    el.textContent = 'CUDA ' + cudaVer + ' ●';
    el.className = 'fx-screen-cuda on';
  } else {
    el.textContent = 'CUDA —';
    el.className = 'fx-screen-cuda off';
  }
  if (tag) tag.classList.toggle('fx-cuda-on', !!(cudaVer && cudaVer !== 'N/A'));
}

/* ═══════════════════════════════════════════════════════
   FX2 — Tile system (UNITÉ 05 FX RACK redesign)
   ═══════════════════════════════════════════════════════ */
const _FX2 = {
  reverb: {
    label: 'REVERB', subtitle: 'CONVOLUTION IR',
    params: [
      { key:'fx_wet',        lbl:'WET MIX',    min:0,   max:1,    step:.01,  unit:'%',  scale:100, def:0.55 },
      { key:'fx_decay',      lbl:'DECAY',       min:0.1, max:8,    step:.1,   unit:'s',  scale:1,   def:1.5 },
      { key:'fx_predelay_ms',lbl:'PRE-DELAY',   min:0,   max:100,  step:1,    unit:'ms', scale:1,   def:20 },
      { key:'fx_diffusion',  lbl:'DIFFUSION',   min:0,   max:1,    step:.01,  unit:'%',  scale:100, def:0.6 },
    ],
    presets: [
      { id:'room',      lbl:'ROOM',      vals:{ fx_wet:0.35, fx_decay:0.6,  fx_predelay_ms:8,  fx_diffusion:0.45 } },
      { id:'studio',    lbl:'STUDIO',    vals:{ fx_wet:0.45, fx_decay:0.9,  fx_predelay_ms:10, fx_diffusion:0.5  } },
      { id:'concert',   lbl:'CONCERT',   vals:{ fx_wet:0.55, fx_decay:2.0,  fx_predelay_ms:25, fx_diffusion:0.70 } },
      { id:'cathedral', lbl:'CATHEDRAL', vals:{ fx_wet:0.65, fx_decay:4.0,  fx_predelay_ms:40, fx_diffusion:0.90 } },
      { id:'plate',     lbl:'PLATE',     vals:{ fx_wet:0.50, fx_decay:1.5,  fx_predelay_ms:5,  fx_diffusion:0.80 } },
      { id:'cave',      lbl:'CAVE',      vals:{ fx_wet:0.60, fx_decay:3.0,  fx_predelay_ms:60, fx_diffusion:0.65 } },
      { id:'spring',    lbl:'SPRING',    vals:{ fx_wet:0.40, fx_decay:0.9,  fx_predelay_ms:15, fx_diffusion:0.35 } },
    ]
  },
  delay: {
    label: 'DELAY', subtitle: 'TAPE ECHO',
    params: [
      { key:'fx_wet',           lbl:'WET MIX',  min:0,   max:1,    step:.01,  unit:'%',  scale:100, def:0.55 },
      { key:'fx_delay_ms',      lbl:'TIME',      min:10,  max:1000, step:1,    unit:'ms', scale:1,   def:350 },
      { key:'fx_delay_feedback',lbl:'FEEDBACK',  min:0,   max:0.95, step:.01,  unit:'%',  scale:100, def:0.55 },
      { key:'fx_delay_filter',  lbl:'FILTER HP', min:200, max:8000, step:50,   unit:'Hz', scale:1,   def:4000 },
    ],
    presets: [
      { id:'short',  lbl:'SHORT SLAP', vals:{ fx_wet:0.40, fx_delay_ms:120, fx_delay_feedback:0.30, fx_delay_filter:5000 } },
      { id:'medium', lbl:'MEDIUM',     vals:{ fx_wet:0.50, fx_delay_ms:350, fx_delay_feedback:0.55, fx_delay_filter:4000 } },
      { id:'long',   lbl:'LONG ECHO',  vals:{ fx_wet:0.60, fx_delay_ms:700, fx_delay_feedback:0.70, fx_delay_filter:3000 } },
      { id:'dotted', lbl:'DOTTED 8TH', vals:{ fx_wet:0.45, fx_delay_ms:225, fx_delay_feedback:0.50, fx_delay_filter:4500 } },
    ]
  },
  chorus: {
    label: 'CHORUS', subtitle: 'LFO MODULATION',
    params: [
      { key:'fx_wet',            lbl:'WET MIX',  min:0,   max:1,   step:.01,  unit:'%',  scale:100, def:0.55 },
      { key:'fx_chorus_rate',    lbl:'RATE',      min:0.1, max:5,   step:.01,  unit:'Hz', scale:1,   def:0.62 },
      { key:'fx_chorus_depth',   lbl:'DEPTH',     min:0.005,max:.04, step:.001, unit:'ms', scale:1000,def:0.018 },
      { key:'fx_chorus_feedback',lbl:'FEEDBACK',  min:0,   max:0.8, step:.01,  unit:'%',  scale:100, def:0.25 },
    ],
    presets: [
      { id:'subtle',   lbl:'SUBTLE',    vals:{ fx_wet:0.35, fx_chorus_rate:0.40, fx_chorus_depth:0.012, fx_chorus_feedback:0.15 } },
      { id:'classic',  lbl:'CLASSIC',   vals:{ fx_wet:0.55, fx_chorus_rate:0.62, fx_chorus_depth:0.018, fx_chorus_feedback:0.25 } },
      { id:'lush',     lbl:'LUSH',      vals:{ fx_wet:0.70, fx_chorus_rate:1.20, fx_chorus_depth:0.030, fx_chorus_feedback:0.40 } },
      { id:'vibrato',  lbl:'VIBRATO',   vals:{ fx_wet:1.00, fx_chorus_rate:3.00, fx_chorus_depth:0.035, fx_chorus_feedback:0.10 } },
    ]
  },
  flanger: {
    label: 'FLANGER', subtitle: 'COMB FILTER LFO',
    params: [
      { key:'fx_wet',              lbl:'WET MIX',  min:0,   max:1,   step:.01, unit:'%',  scale:100, def:0.55 },
      { key:'fx_flanger_rate',     lbl:'LFO RATE', min:0.05,max:4,   step:.01, unit:'Hz', scale:1,   def:0.30 },
      { key:'fx_flanger_depth',    lbl:'DEPTH',    min:.001,max:.01, step:.0005,unit:'ms', scale:1000,def:0.003 },
      { key:'fx_flanger_feedback', lbl:'FEEDBACK', min:0,   max:0.95,step:.01, unit:'%',  scale:100, def:0.70 },
    ],
    presets: [
      { id:'slow',   lbl:'SLOW SWEEP',  vals:{ fx_wet:0.55, fx_flanger_rate:0.10, fx_flanger_depth:0.003, fx_flanger_feedback:0.60 } },
      { id:'medium', lbl:'MEDIUM',      vals:{ fx_wet:0.55, fx_flanger_rate:0.30, fx_flanger_depth:0.003, fx_flanger_feedback:0.70 } },
      { id:'fast',   lbl:'FAST JET',    vals:{ fx_wet:0.65, fx_flanger_rate:1.50, fx_flanger_depth:0.008, fx_flanger_feedback:0.85 } },
      { id:'wide',   lbl:'WIDE',        vals:{ fx_wet:0.70, fx_flanger_rate:0.20, fx_flanger_depth:0.010, fx_flanger_feedback:0.80 } },
    ]
  },
  echo: {
    label: 'ECHO', subtitle: 'DUAL DELAY STEREO',
    params: [
      { key:'fx_wet',            lbl:'WET MIX',   min:0,  max:1,    step:.01, unit:'%',  scale:100, def:0.55 },
      { key:'fx_echo_left_ms',   lbl:'LEFT TIME', min:50, max:800,  step:5,   unit:'ms', scale:1,   def:375 },
      { key:'fx_echo_right_ms',  lbl:'RIGHT TIME',min:50, max:800,  step:5,   unit:'ms', scale:1,   def:250 },
      { key:'fx_echo_feedback',  lbl:'FEEDBACK',  min:0,  max:0.95, step:.01, unit:'%',  scale:100, def:0.55 },
    ],
    presets: [
      { id:'ping',   lbl:'PING-PONG',   vals:{ fx_wet:0.55, fx_echo_left_ms:375, fx_echo_right_ms:250, fx_echo_feedback:0.55 } },
      { id:'double', lbl:'DOUBLER',     vals:{ fx_wet:0.45, fx_echo_left_ms:80,  fx_echo_right_ms:60,  fx_echo_feedback:0.20 } },
      { id:'slapback',lbl:'SLAPBACK',   vals:{ fx_wet:0.50, fx_echo_left_ms:120, fx_echo_right_ms:90,  fx_echo_feedback:0.30 } },
      { id:'space',  lbl:'SPACE',       vals:{ fx_wet:0.65, fx_echo_left_ms:600, fx_echo_right_ms:450, fx_echo_feedback:0.70 } },
    ]
  },
  phaser: {
    label: 'PHASER', subtitle: 'ALL-PASS FILTER',
    params: [
      { key:'fx_wet',          lbl:'WET MIX', min:0,  max:1,  step:.01, unit:'%',   scale:100, def:0.55 },
      { key:'fx_phaser_rate',  lbl:'RATE',    min:.05,max:4,  step:.01, unit:'Hz',  scale:1,   def:0.50 },
      { key:'fx_phaser_depth', lbl:'DEPTH',   min:0,  max:1,  step:.01, unit:'%',   scale:100, def:0.70 },
      { key:'fx_phaser_stages',lbl:'STAGES',  min:2,  max:12, step:2,   unit:' st', scale:1,   def:6   },
    ],
    presets: [
      { id:'subtle',  lbl:'SUBTLE',   vals:{ fx_wet:0.40, fx_phaser_rate:0.30, fx_phaser_depth:0.40, fx_phaser_stages:4 } },
      { id:'classic', lbl:'CLASSIC',  vals:{ fx_wet:0.55, fx_phaser_rate:0.50, fx_phaser_depth:0.70, fx_phaser_stages:6 } },
      { id:'deep',    lbl:'DEEP',     vals:{ fx_wet:0.70, fx_phaser_rate:0.20, fx_phaser_depth:0.90, fx_phaser_stages:8 } },
      { id:'fast',    lbl:'FAST',     vals:{ fx_wet:0.65, fx_phaser_rate:2.00, fx_phaser_depth:0.80, fx_phaser_stages:6 } },
    ]
  },
  exciter: {
    label: 'EXCITER', subtitle: 'HARMONIC SATURATION',
    params: [
      { key:'fx_wet',            lbl:'WET MIX', min:0,   max:1,     step:.01, unit:'%',  scale:100, def:0.55 },
      { key:'fx_exciter_drive',  lbl:'DRIVE',   min:0,   max:24,    step:.5,  unit:'dB', scale:1,   def:6.0 },
      { key:'fx_exciter_tone',   lbl:'TONE',    min:1000,max:16000, step:100, unit:'Hz', scale:1,   def:5000 },
      { key:'fx_exciter_warmth', lbl:'WARMTH',  min:0,   max:1,     step:.01, unit:'%',  scale:100, def:0.30 },
    ],
    presets: [
      { id:'air',     lbl:'AIR',      vals:{ fx_wet:0.40, fx_exciter_drive:3,  fx_exciter_tone:8000, fx_exciter_warmth:0.10 } },
      { id:'presence',lbl:'PRESENCE', vals:{ fx_wet:0.55, fx_exciter_drive:6,  fx_exciter_tone:5000, fx_exciter_warmth:0.30 } },
      { id:'warmth',  lbl:'WARMTH',   vals:{ fx_wet:0.65, fx_exciter_drive:9,  fx_exciter_tone:3000, fx_exciter_warmth:0.60 } },
      { id:'saturate',lbl:'SATURATE', vals:{ fx_wet:0.75, fx_exciter_drive:18, fx_exciter_tone:4000, fx_exciter_warmth:0.50 } },
    ]
  }
};

let _fx2Type   = 'reverb';
let _fx2Preset = null;
let _fx2Vals   = {};  // current param values per type

function fx2SetType(type) {
  _fx2Type = type;
  // update tabs
  Object.keys(_FX2).forEach(t => {
    const b = document.getElementById('fx2t-' + t);
    if (b) { b.classList.toggle('fx2-active', t === type); }
  });
  // also sync the old _fxType for API
  _fxType = type;
  _fxSendParam('fx_type', type);
  fx2Render();
  // WebAudio — pré-générer IR pour le nouveau type (proactif, même si FX off)
  // → toggle ON ultérieur sera instantané quel que soit l'ordre des actions user
  if (_fxConvolver && audioCtx) {
    _fxRefreshIr(type, _fx2Vals[type] || {});
    if (_fxActive && _fxDryGain && _fxWetGain) {
      const vals = _fx2Vals[type] || {};
      const isConvType = !!_fxConvolver.buffer;  // null pour chorus/flanger/phaser/exciter
      if (isConvType) {
        const wet = (vals.fx_wet !== undefined) ? vals.fx_wet
                  : (_FX2[type] ? _FX2[type].params[0].def : 0.4);
        _fxSetWetDry(wet, true);
      } else {
        // Type sans IR (modulation) — muter le chemin wet
        _fxSetWetDry(0, true);
      }
    }
  }
}

function fx2Render() {
  const def   = _FX2[_fx2Type];
  if (!def) return;
  const plug  = document.getElementById('fx2-plugin');
  const prst  = document.getElementById('fx2-presets');
  if (!plug || !prst) return;

  // ── Plugin tile ──
  let html = `<div class="fx2-plugin-title">${def.label}<span class="fx2-subtitle">${def.subtitle}</span></div>`;
  def.params.forEach(p => {
    const stored = _fx2Vals[_fx2Type] && _fx2Vals[_fx2Type][p.key] !== undefined
                   ? _fx2Vals[_fx2Type][p.key] : p.def;
    const display = _fx2FormatVal(stored * p.scale, p.unit, p);
    const pct = ((stored - p.min) / (p.max - p.min)) * 100;
    html += `<div class="fx2-param-row">
      <span class="fx2-param-lbl">${p.lbl}</span>
      <input type="range" class="rack-fader rack-fader--green" id="fx2s-${p.key}"
        min="${p.min}" max="${p.max}" step="${p.step}" value="${stored}"
        style="--f-pct:${pct.toFixed(1)}%"
        oninput="fx2Param('${p.key}',this.value,this)">
      <span class="fx2-param-val" id="fx2v-${p.key}">${display}</span>
    </div>`;
  });
  plug.innerHTML = html;

  // ── Presets ──
  let phtml = `<div class="fx2-preset-lbl">PRESETS</div>`;
  def.presets.forEach(pr => {
    const act = _fx2Preset === pr.id ? ' fx2-preset-active' : '';
    phtml += `<button class="fx2-preset-btn${act}" id="fx2p-${pr.id}" onclick="fx2SetPreset('${pr.id}')">${pr.lbl}</button>`;
  });
  prst.innerHTML = phtml;
}

function _fx2FormatVal(v, unit, p) {
  if (unit === '%') return Math.round(v) + '%';
  if (unit === 's') return v.toFixed(1) + 's';
  if (unit === 'ms') return Math.round(v) + 'ms';
  if (unit === 'Hz') return v >= 1000 ? (v/1000).toFixed(1) + 'kHz' : Math.round(v) + 'Hz';
  if (unit === 'dB') return (v >= 0 ? '+' : '') + v.toFixed(1) + 'dB';
  if (unit === ' st') return Math.round(v) + ' st';
  return parseFloat(v).toFixed(2);
}

function fx2Param(key, rawVal, sliderEl) {
  const def = _FX2[_fx2Type];
  if (!def) return;
  const param = def.params.find(p => p.key === key);
  if (!param) return;
  const val = parseFloat(rawVal);
  // store
  if (!_fx2Vals[_fx2Type]) _fx2Vals[_fx2Type] = {};
  _fx2Vals[_fx2Type][key] = val;
  // update value display
  const vEl = document.getElementById('fx2v-' + key);
  if (vEl) vEl.textContent = _fx2FormatVal(val * param.scale, param.unit, param);
  // update rack-fader fill gradient
  const s = sliderEl || document.getElementById('fx2s-' + key);
  if (s) {
    const pct = ((val - param.min) / (param.max - param.min)) * 100;
    s.style.setProperty('--f-pct', pct.toFixed(1) + '%');
  }
  // deselect preset
  _fx2Preset = null;
  document.querySelectorAll('.fx2-preset-btn').forEach(b => b.classList.remove('fx2-preset-active'));
  // WebAudio — mise à jour temps réel
  if (_fxActive && _fxDryGain && _fxWetGain && audioCtx) {
    if (key === 'fx_wet') {
      _fxSetWetDry(val, true);
    } else if (_fxConvolver) {
      _fxRefreshIr(_fx2Type, _fx2Vals[_fx2Type] || {});
    }
  }
  // send to API
  _fxSendParam(key, val);
}

function fx2SetPreset(presetId) {
  const def = _FX2[_fx2Type];
  if (!def) return;
  const pr = def.presets.find(p => p.id === presetId);
  if (!pr) return;
  _fx2Preset = presetId;
  // update preset btn highlight
  def.presets.forEach(p => {
    const b = document.getElementById('fx2p-' + p.id);
    if (b) b.classList.toggle('fx2-preset-active', p.id === presetId);
  });
  // store + apply each param
  if (!_fx2Vals[_fx2Type]) _fx2Vals[_fx2Type] = {};
  const batch = {};
  Object.entries(pr.vals).forEach(([key, val]) => {
    _fx2Vals[_fx2Type][key] = val;
    batch[key] = val;
    const param = def.params.find(p => p.key === key);
    // update rack-fader slider
    const s = document.getElementById('fx2s-' + key);
    if (s && param) {
      s.value = val;
      const pct = ((val - param.min) / (param.max - param.min)) * 100;
      s.style.setProperty('--f-pct', pct.toFixed(1) + '%');
    }
    // update value display
    const v = document.getElementById('fx2v-' + key);
    if (v && param) v.textContent = _fx2FormatVal(val * param.scale, param.unit, param);
  });
  // WebAudio — mettre à jour l'IR et le wet pour ce preset (refresh cache)
  if (_fxActive && _fxConvolver && _fxDryGain && _fxWetGain && audioCtx) {
    if (_fxRefreshIr(_fx2Type, _fx2Vals[_fx2Type] || {})) {
      const wet = (pr.vals.fx_wet !== undefined) ? pr.vals.fx_wet : 0.4;
      _fxSetWetDry(wet, true);
    }
  }
  // send entire batch in one fetch
  fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(batch)
  }).catch(() => {});
}

// ── FX RACK — MÉMOIRES M1-M10 ────────────────────────────────
const _FX_MEM_KEY  = 'jarvis_fx_mem_v1';
const _FX_MEM_HOLD = 800;
let _fxMemSlots = Array(10).fill(null);
let _fxMemTimer = null;

function _fxMemLoad() {
  try { _fxMemSlots = JSON.parse(localStorage.getItem(_FX_MEM_KEY)) || Array(10).fill(null); }
  catch(_) { _fxMemSlots = Array(10).fill(null); }
  _fxMemSlots.forEach((s, i) => _fxMemUpdateBtn(i));
}

function _fxMemSaveStorage() {
  localStorage.setItem(_FX_MEM_KEY, JSON.stringify(_fxMemSlots));
}

function _fxMemSnapshot() {
  return {
    type:   _fx2Type,
    preset: _fx2Preset,
    vals:   JSON.parse(JSON.stringify(_fx2Vals)),
    _label: '',
  };
}

function _fxMemApply(snap) {
  _fx2Vals = JSON.parse(JSON.stringify(snap.vals));
  _fx2Preset = snap.preset;
  fx2SetType(snap.type);   // met à jour tabs + re-render + envoie fx_type
  // Renvoyer tous les params au serveur
  const def = _FX2[snap.type];
  if (def) {
    const batch = {};
    def.params.forEach(p => {
      const val = (_fx2Vals[snap.type] || {})[p.key] ?? p.def;
      batch[p.key] = val;
    });
    _patchDsp(batch);
  }
}

function _fxMemUpdateBtn(idx) {
  const btn = document.getElementById('fx-mem-btn-' + idx);
  if (!btn) return;
  const filled = _fxMemSlots[idx] !== null;
  btn.classList.toggle('filled', filled);
  if (filled && _fxMemSlots[idx]._label) btn.title = _fxMemSlots[idx]._label;
}

function _fxMemAlignSpacer() {
  const sep    = document.getElementById('fx-mem-sep');
  const spacer = document.getElementById('fx-mem-spacer');
  if (!sep || !spacer) return;
  const sepRect    = sep.getBoundingClientRect();
  const parentRect = sep.parentElement.getBoundingClientRect();
  spacer.style.width = (sepRect.right - parentRect.left + 4) + 'px';
}

function fxMemPress(idx) {
  const btn = document.getElementById('fx-mem-btn-' + idx);
  if (btn) btn.classList.add('pressing');
  _fxMemTimer = setTimeout(() => {
    _fxMemTimer = null;
    const snap = _fxMemSnapshot();
    snap._label = 'M' + (idx+1) + ' — ' + new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
    _fxMemSlots[idx] = snap;
    _fxMemSaveStorage();
    if (btn) { btn.classList.remove('pressing'); btn.classList.add('saving'); }
    setTimeout(() => { if (btn) btn.classList.remove('saving'); _fxMemUpdateBtn(idx); }, 600);
  }, _FX_MEM_HOLD);
}

function fxMemRelease(idx) {
  if (_fxMemTimer) {
    clearTimeout(_fxMemTimer);
    _fxMemTimer = null;
    const btn = document.getElementById('fx-mem-btn-' + idx);
    if (btn) btn.classList.remove('pressing');
    if (_fxMemSlots[idx]) {
      _fxMemApply(_fxMemSlots[idx]);
      document.querySelectorAll('[id^="fx-mem-btn-"]').forEach(b => b.classList.remove('active-mem'));
      if (btn) btn.classList.add('active-mem');
    }
  }
}

function fxMemClear(idx) {
  _fxMemSlots[idx] = null;
  _fxMemSaveStorage();
  _fxMemUpdateBtn(idx);
  const btn = document.getElementById('fx-mem-btn-' + idx);
  if (btn) btn.classList.remove('active-mem');
}

// → _jarvisInit()

// FX VU level (decay driven by _rackUpdateVu)
let _fxVuLevel = 0;
if (!_rackVuInterval) _rackVuInterval = setInterval(_rackUpdateVu, _DRAW_INTERVAL_MS);

// Déclencher VU quand JARVIS parle (hook sur fetch TTS)
const _origFetch = window.fetch;
window.fetch = function(...args) {
  const p = _origFetch.apply(this, args);
  if (typeof args[0] === 'string' && args[0].includes('/api/tts') && _fxActive) {
    _fxVuLevel = 7;
    const tick = setInterval(() => {
      if (_fxVuLevel <= 0) { clearInterval(tick); return; }
      _fxVuLevel = Math.max(0, _fxVuLevel - 0.05);
    }, 100);
    setTimeout(() => clearInterval(tick), _COVER_SAFE_MS);
  }
  return p;
};

let _speechPending = false;
let _userGestured  = false;

// Déverrouillage audio — politique autoplay navigateur : aucun son sans geste
// utilisateur. Les écouteurs sont armés TÔT (dès _jarvisInit) et sur PLUSIEURS
// types de gestes : le tout premier geste (même pendant l'écran de boot)
// débloque l'annonce de bienvenue, quel que soit l'ordre vs /api/boot-id.
const _GESTURE_EVENTS = ['click', 'keydown', 'pointerdown', 'touchstart'];

function _onUserGesture() {
  if (_userGestured) return;
  _userGestured = true;
  _GESTURE_EVENTS.forEach(ev => document.removeEventListener(ev, _onUserGesture, true));
  if (typeof audioCtx !== 'undefined' && audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => { /* refus politique navigateur — silencieux */ });
  }
  // _tryPlayPendingSpeech → playWelcomeSpeech → queueSpeech → processQueue : la
  // file (y compris ce qui a été mis en attente pendant le verrou audio) est
  // drainée ici dès le 1er geste, car queueSpeech relance processQueue si idle.
  _tryPlayPendingSpeech();  // no-op si _speechPending pas encore vrai
}

function _armGestureUnlock() {
  _GESTURE_EVENTS.forEach(ev =>
    document.addEventListener(ev, _onUserGesture, { capture: true, passive: true }));
}

function _removeInitCover() {
  const c = document.getElementById('init-cover');
  if (!c) return;
  c.style.opacity = '0';
  setTimeout(() => { c.parentNode && c.parentNode.removeChild(c); }, 260);
}

function _tryPlayPendingSpeech() {
  if (!_speechPending) return;
  _speechPending = false;
  // Stopper le pulse du bouton VOIX
  const voixBtn = document.querySelector('.welcome-btn[data-action="playWelcomeSpeech"]');
  if (voixBtn) voixBtn.classList.remove('wm-voix-pulse');
  playWelcomeSpeech();
}

// → _jarvisInit()

// ══════════════════════════════════════════════════════════════
// INIT — point d'entrée unique DOMContentLoaded
// ══════════════════════════════════════════════════════════════
function _hudInit() {
  // Live clock
  const clockEl = document.getElementById('hud-clock');
  if (clockEl) {
    const tick = () => {
      clockEl.textContent = new Date().toLocaleTimeString('fr-FR', { hour12: false });
      setTimeout(tick, _TICK_INTERVAL_MS);
    };
    tick();
  }
  // Hex data stream
  const streamEl = document.getElementById('hud-stream');
  if (streamEl) {
    const rh = () => Math.floor(Math.random() * 256).toString(16).padStart(2,'0').toUpperCase();
    const upd = () => { streamEl.textContent = Array.from({length:14}, rh).join(' '); setTimeout(upd, 200); };
    upd();
  }
}

function _jarvisInitBootSeq() {
  sttCheckStatus();
  fetch('/api/dsp-params', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fx_enabled: false })
  }).catch(() => {});
  const _coverSafe = setTimeout(() => { _removeInitCover(); }, _COVER_SAFE_MS);
  fetch('/api/boot-id').then(r => r.json()).then(d => {
    clearTimeout(_coverSafe);
    const stored = sessionStorage.getItem('jarvis_boot_id');
    if (stored !== d.boot_id) {
      sessionStorage.setItem('jarvis_boot_id', d.boot_id);
      _removeInitCover();
      _startPreloader();
      _speechPending = true;
      // Si l'utilisateur a déjà interagi avant la résolution de /api/boot-id,
      // jouer immédiatement ; sinon _onUserGesture s'en charge au 1er geste.
      if (_userGestured) _tryPlayPendingSpeech();
      setTimeout(() => {
        const voixBtn = document.querySelector('.welcome-btn[data-action="playWelcomeSpeech"]');
        if (voixBtn && _speechPending) voixBtn.classList.add('wm-voix-pulse');
      }, _VOIX_PULSE_MS);
    } else {
      _removeInitCover();
      loadWelcome();
    }
  }).catch(() => { clearTimeout(_coverSafe); _removeInitCover(); loadWelcome(); });
}
function _jarvisInitMode() {
  fetch('/api/mode').then(r => r.json()).then(d => {
    if (d.mode && d.mode !== 'soc') {
      fetch('/api/mode', { method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({mode:'soc'}) }).catch(() => {});
    }
    localStorage.setItem(_LS_MODE, 'soc');
    _updateModeBtn();
    _applyModeProfile('soc');
  }).catch(() => { _updateModeBtn(); });
  fetch('/api/mode').then(r => r.json()).then(d => {
    if (d.mode && d.mode !== 'soc') {
      _jarvisMode = d.mode;
      const profileName = d.mode === 'general' ? _MODE_GENERAL
        : d.mode === 'code' ? _MODE_CODE
        : d.mode === 'code_reasoning' ? _MODE_CODE_REASONING : null;
      if (profileName) localStorage.setItem(_LS_PROMPT_PROFILE, profileName);
      _updateModeBtn();
    }
  }).catch(() => {});
}
function _jarvisInit() {
  _armGestureUnlock();
  _hudInit();
  loadMemory();
  if (typeof _updateEqCoupleBadges === 'function') _updateEqCoupleBadges();
  document.querySelectorAll('input[type=range].dsp-hslider, input[type=range].rack-fader')
    .forEach(_syncRangeSlider);
  document.addEventListener('input', e => {
    const el = e.target;
    if (el.type === 'range' && (el.classList.contains('dsp-hslider') || el.classList.contains('rack-fader')))
      _syncRangeSlider(el);
  });
  window._syncRangeSlider = _syncRangeSlider;

  const modal = document.getElementById('code-modal');
  if (modal) modal.addEventListener('click', e => {
    if (e.target === modal) closeCodeModal();
  });
  document.addEventListener('click', function _dspFirstInit() {
    document.removeEventListener('click', _dspFirstInit);
    if (!_dspInited) try { initDsp(); } catch(e) {}
  }, { capture: true, once: true });

  setTimeout(() => checkWebStatus(true), 3000);

  _jarvisInitMode();
  _pollOllamaStatus();
  setInterval(_pollOllamaStatus, _SOC_REFRESH_MS);

  _eqMemLoad();
  _fxMemLoad();
  requestAnimationFrame(() => requestAnimationFrame(_fxMemAlignSpacer));
  if (document.getElementById('fx2-plugin')) fx2SetType('reverb');

  _jarvisInitBootSeq();

  setInterval(function _pollBootId() {
    const stored = sessionStorage.getItem('jarvis_boot_id');
    if (!stored) return;
    fetch('/api/boot-id', { cache: 'no-store' }).then(r => r.json()).then(d => {
      if (d.boot_id && d.boot_id !== stored) location.reload();
    }).catch(() => {});
  }, _BOOTID_POLL_MS);
}
document.addEventListener('DOMContentLoaded', _jarvisInit);

