// ══════════════════════════════════════════════════════════════
// AI AUDIO RACK — DSP intégré, presets EQ/spec, helpers EQ
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-15.
//
// Contenu :
//  - Rack DSP intégré (faders gain/comp/EQ/stereo widener/Haas,
//    DeepFilterNet, master ON/OFF, VU-mètres temps réel, test voix).
//  - Presets EQ paramétrique (_EQ_PRESETS) et presets spectre
//    (SPEC_PRESETS jarvis/electronic/voice/full-range).
//  - Master DSP (_applyDspMaster, toggleDspMaster, dspSocReport).
//  - Helpers EQ partagés (setEqBand, eqSetFreq/Q/Type, eqPushNow,
//    eqToggleBypass, _eqUpdateCounters, _canvasCoords, mouseup
//    drag-end listener) appelés depuis dsp_audio.js / eq_parametric.js.
//  - escHtml (helper générique de templating).
//
// Fichier .js classique (scope global). Chargé APRÈS jarvis_main.js
// et AVANT boot_init.js.

let _rackOpen = true;

let _rackVuInterval = null;

function _rackUpdateVu() {
  // FX VU — runs unconditionally (no rack/analyser required)
  { const dbL = document.getElementById('fx-db-l');
    const dbR = document.getElementById('fx-db-r');
    if (!_fxActive) {
      for (let i = 0; i < 8; i++) {
        const l = document.getElementById('fvl-' + i);
        const r = document.getElementById('fvr-' + i);
        if (l) { l.classList.remove('g','y','r'); }
        if (r) { r.classList.remove('g','y','r'); }
      }
      if (dbL) { dbL.textContent = '-∞ dB'; dbL.classList.remove('warn','alert'); }
      if (dbR) { dbR.textContent = '-∞ dB'; dbR.classList.remove('warn','alert'); }
    } else {
      const level = _fxVuLevel;
      for (let i = 0; i < 8; i++) {
        const on = i < level;
        const cls = i >= 6 ? 'r' : i >= 4 ? 'y' : 'g';
        const l = document.getElementById('fvl-' + i);
        const r = document.getElementById('fvr-' + i);
        if (l) { l.className = 'fx-vu-led' + (on ? ' ' + cls : ''); }
        if (r) { r.className = 'fx-vu-led' + (on ? ' ' + cls : ''); }
      }
      if (dbL || dbR) {
        const dbTxt = level > 0 ? (20 * Math.log10(level / 7)).toFixed(1) + ' dB' : '-∞ dB';
        const isWarn  = level >= 4 && level < 6;
        const isAlert = level >= 6;
        [dbL, dbR].forEach(el => {
          if (!el) return;
          el.textContent = dbTxt;
          el.classList.toggle('warn',  isWarn);
          el.classList.toggle('alert', isAlert);
        });
      }
      _fxVuLevel = Math.max(0, _fxVuLevel - 0.15);
    }
  }
  // Rack VU — needs open rack + analyser
  if (!_rackOpen || !_dspAnalyser) return;
  const buf = new Uint8Array(_dspAnalyser.frequencyBinCount);
  _dspAnalyser.getByteFrequencyData(buf);
  const avg = buf.reduce((s, v) => s + v, 0) / buf.length / 255;
  const pct  = Math.min(100, avg * 260).toFixed(1);
  const pct2 = Math.min(100, avg * 240).toFixed(1);
  ['rack-vu-l','rack-vu-r'].forEach((id, i) => {
    const el = document.getElementById(id);
    if (el) el.style.width = (i === 0 ? pct : pct2) + '%';
  });
  // GR canvas meter (drawn each frame)
  _drawGrMeter(_dspCompressor ? _dspCompressor.reduction : 0);
  // Peak dB
  const maxVal = Math.max(...buf) / 255;
  const dbVal  = maxVal > 0.001 ? (20 * Math.log10(maxVal)).toFixed(1) : '-∞';
  const pk = document.getElementById('rack-peak-db');
  if (pk) { pk.textContent = dbVal + ' dB'; pk.classList.toggle('peak-clip', maxVal > 0.9); pk.classList.toggle('peak-warn', maxVal > 0.7 && maxVal <= 0.9); }
  // GR display
  const gr = document.getElementById('rack-comp-gr');
  if (gr && _dspCompressor) {
    const red = _dspCompressor.reduction != null ? _dspCompressor.reduction.toFixed(1) : '0.0';
    gr.textContent = red + ' dB';
    const absRed = Math.abs(parseFloat(red));
    gr.classList.toggle('alert', absRed > 12);
    gr.classList.toggle('warn',  absRed > 6 && absRed <= 12);
  }
  // VU-mètre MOTEUR VOCAL — même source _dspAnalyser
  const vuL = document.getElementById('vu-left');
  const vuR = document.getElementById('vu-right');
  const vuDb = document.getElementById('vu-db');
  if (vuL) vuL.style.width = pct + '%';
  if (vuR) vuR.style.width = pct2 + '%';
  if (vuDb) vuDb.textContent = dbVal + (maxVal > 0 ? ' dB' : '');
}

function _rackUpdateSignalPath(dfActive) {
  const dfNode = document.getElementById('rsp-df');
  if (dfNode) dfNode.classList.toggle('active', dfActive);
}

function _rackSyncFromDsp() {
  // Sync EQ
  const bands = ['low','mid','high','air'];
  bands.forEach(b => {
    const mainSl = document.getElementById('eq-' + b);
    const rackSl = document.getElementById('rack-eq-' + b);
    const rackVl = document.getElementById('rack-eq-' + b + '-val');
    if (mainSl && rackSl) {
      rackSl.value = mainSl.value;
      if (rackVl) rackVl.textContent = parseFloat(mainSl.value).toFixed(1) + ' dB';
      _syncRangeSlider(rackSl);
    }
    // Q
    if (typeof _eqState !== 'undefined' && _eqState) {
      const idx = ['low','mid','high','air'].indexOf(b);
      if (idx >= 0) {
        const qSl = document.getElementById('rack-eq-' + b + '-q');
        const qVl = document.getElementById('rack-eq-' + b + '-q-val');
        const typEl = document.getElementById('rack-eq-' + b + '-type');
        if (qSl) { qSl.value = _eqState[idx].q; if (qVl) qVl.textContent = _eqState[idx].q.toFixed(1); _syncRangeSlider(qSl); }
        if (typEl) typEl.textContent = (_eqState[idx].type || 'peaking').toUpperCase();
      }
    }
  });
  // Sync compressor — lecture directe depuis les nœuds WebAudio (plus de dépendance aux DOM dsp-*)
  if (_dspCompressor) {
    const cNodes = [
      ['rack-comp-thresh', _dspCompressor.threshold.value, v => v.toFixed(1) + ' dB', 'rack-comp-thresh-val'],
      ['rack-comp-ratio',  _dspCompressor.ratio.value,     v => v.toFixed(1) + ':1',  'rack-comp-ratio-val'],
      ['rack-comp-att',    _dspCompressor.attack.value * 1000,   v => Math.round(v) + ' ms', 'rack-comp-att-val'],
      ['rack-comp-rel',    _dspCompressor.release.value * 1000,  v => Math.round(v) + ' ms', 'rack-comp-rel-val'],
    ];
    cNodes.forEach(([rackId, val, fmt, valId]) => {
      const rs = document.getElementById(rackId);
      if (rs) { rs.value = val; const ve = document.getElementById(valId); if (ve) ve.textContent = fmt(val); _syncRangeSlider(rs); }
    });
  }
  // Gain — lecture depuis le nœud WebAudio
  if (_dspGainNode) {
    const rg = document.getElementById('rack-gain');
    const val = _dspGainNode.gain.value;
    if (rg) { rg.value = val; const rv = document.getElementById('rack-gain-val'); if (rv) rv.textContent = val.toFixed(1) + ' dB'; _syncRangeSlider(rg); }
  }
}

// ── Rack controls → sync vers DSP tab ────────────────────────
const _EQ_PRESETS = {
  'FLAT':      { low:[0,0.7],    mid:[0,0.8],   high:[0,0.9],    air:[0,0.7]   },
  'VOIX':      { low:[-2,0.7],   mid:[2,1.2],   high:[1,0.9],    air:[2,0.7]   },
  'RADIO':     { low:[-4,0.7],   mid:[3,1.5],   high:[2,0.9],    air:[3,0.7]   },
  'BROADCAST': { low:[-2,0.8],   mid:[4,1.8],   high:[2,1.0],    air:[4,0.8]   },
  'TELEPHONE': { low:[-8,0.7],   mid:[6,2.0],   high:[-6,0.9],   air:[-8,0.7]  },
  'CINEMA':    { low:[3,0.7],    mid:[1,0.8],   high:[2,0.9],    air:[4,0.7]   },
  'PRESENCE':  { low:[-1,0.7],   mid:[5,2.0],   high:[3,0.9],    air:[2,0.7]   },
  'STUDIO':    { low:[1,0.7],    mid:[0,0.8],   high:[0,0.9],    air:[2,0.7]   },
  'GRAVE':     { low:[6,0.7],    mid:[-1,0.8],  high:[-2,0.9],   air:[1,0.7]   },
  'SCIFI':     { low:[-4,0.7],   mid:[8,3.0],   high:[4,2.0],    air:[6,0.7]   },
};

function applyEqPreset(name) {
  const p = _EQ_PRESETS[name];
  if (!p) return;
  ['low','mid','high','air'].forEach(band => {
    const [gain, q] = p[band];
    // DSP EQ principal (courbe + sliders)
    const dspSl = document.getElementById('eq-' + band);
    if (dspSl) dspSl.value = gain;
    setEqBand(band, gain);
    // Rack EQ R2 (sliders + affichage)
    const rackSl = document.getElementById('rack-eq-' + band);
    const rackQ  = document.getElementById('rack-eq-' + band + '-q');
    if (rackSl) { rackSl.value = gain; rackSyncEq(band, gain); }
    if (rackQ)  { rackQ.value = q;     rackSyncEqQ(band, q);   }
  });
  // Highlight bouton actif dans les deux barres
  document.querySelectorAll('.rack-eq-preset-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll(`[data-eq-preset="${name}"]`).forEach(b => b.classList.add('active'));
  pushDspParamsToBackend();
}

function rackSyncEq(band, val) {
  const v = parseFloat(val).toFixed(1);
  const valEl = document.getElementById('rack-eq-' + band + '-val');
  if (valEl) valEl.textContent = v + ' dB';
  // Sync main DSP slider + appliquer au nœud WebAudio
  const mainSl = document.getElementById('eq-' + band);
  if (mainSl) mainSl.value = val;
  setEqBand(band, val);
  // Sync fill rack slider
  const rs = document.getElementById('rack-eq-' + band);
  if (rs) _syncRangeSlider(rs);
}

function rackSyncEqQ(band, val) {
  const v = parseFloat(val).toFixed(1);
  const valEl = document.getElementById('rack-eq-' + band + '-q-val');
  if (valEl) valEl.textContent = v;
  // Appliquer au nœud WebAudio + mettre à jour _eqState + redessiner courbe
  eqSetQ(band, val);
  // Sync fill rack slider
  const rs = document.getElementById('rack-eq-' + band + '-q');
  if (rs) _syncRangeSlider(rs);
}

function rackSyncComp(param, val) {
  setDspCompressor(param, val);
  const mapLbl = {'threshold':v=>parseFloat(v).toFixed(1)+' dB','ratio':v=>parseFloat(v).toFixed(1)+':1','attack':v=>Math.round(v)+' ms','release':v=>Math.round(v)+' ms'};
  const mapVid = {'threshold':'rack-comp-thresh-val','ratio':'rack-comp-ratio-val','attack':'rack-comp-att-val','release':'rack-comp-rel-val'};
  const ve = document.getElementById(mapVid[param]);
  if (ve && mapLbl[param]) ve.textContent = mapLbl[param](val);
  const rs = document.getElementById('rack-comp-' + (param==='threshold'?'thresh':param==='attack'?'att':param==='release'?'rel':param));
  if (rs) _syncRangeSlider(rs);
}

function rackSyncGain(val) {
  setDspGain(val);
  const ve = document.getElementById('rack-gain-val');
  if (ve) ve.textContent = parseFloat(val).toFixed(1) + ' dB';
  const rs = document.getElementById('rack-gain');
  if (rs) _syncRangeSlider(rs);
}

async function rackToggleDf() {
  const btn = document.getElementById('rack-df-bypass');
  const isOn = btn && btn.classList.toggle('on');
  btn && btn.classList.toggle('off', !isOn);
  _dfActive = !!isOn;
  document.getElementById('rack-unit-df').classList.toggle('bypassed', !isOn);
  document.getElementById('rsp-df')?.classList.toggle('active', isOn);
  _rackUpdateSignalPath(isOn);
  const stag = document.getElementById('rack-df-status-tag');
  if (stag) { stag.textContent = isOn ? 'ACTIF' : 'DISPONIBLE'; stag.className = 'rack-unit-tag ' + (isOn ? 'tag-ok' : ''); }
  const act = document.getElementById('rack-df-active');
  if (act) { act.textContent = isOn ? 'OUI' : 'NON'; _stColor(act, isOn ? 'ok' : 'err'); }
  if (!isOn) _clearUnitVu(['rack-df-vu-canvas','rack-df-spectrum']);
  await _patchDsp({df_enabled:isOn});
}

function rackDfParam(param, val) {
  if (param === 'atten') {
    const ve = document.getElementById('rack-df-atten-val');
    if (ve) ve.textContent = val + ' dB';
    _patchDsp({df_atten_lim:parseFloat(val)});
  }
  const rs = document.getElementById('rack-df-atten');
  if (rs) _syncRangeSlider(rs);
}

function rackDfTogglePost() {
  const tog = document.getElementById('rack-df-postfilter');
  const isOn = tog && tog.classList.toggle('on');
  const lbl = document.getElementById('rack-df-post-lbl');
  if (lbl) lbl.textContent = isOn ? 'ACTIVÉ' : 'DÉSACTIVÉ';
  _patchDsp({df_post_filter:isOn});
}


function rackToggleComp() {
  const btn = document.getElementById('rack-comp-bypass');
  const isOn = btn && btn.classList.toggle('on');
  btn && btn.classList.toggle('off', !isOn);
  _compActive = !!isOn;
  document.getElementById('rack-unit-comp').classList.toggle('bypassed', !isOn);
  document.getElementById('rsp-comp').classList.toggle('active', isOn);
  if (!isOn) _clearUnitVu(['rack-comp-meter-l','rack-comp-meter-r','rack-comp-gr']);
  // Déconnexion/reconnexion WebAudio réelle : _dspEqAir → compresseur → limiteur
  if (_dspEqAir && _dspCompressor && _dspLimiter) {
    try {
      if (isOn) {
        _dspEqAir.disconnect(_dspLimiter);
        _dspEqAir.connect(_dspCompressor);
      } else {
        _dspEqAir.disconnect(_dspCompressor);
        _dspEqAir.connect(_dspLimiter);
      }
    } catch(e) { /* node may not be connected */ }
  }
  _patchDsp({comp_enabled:isOn});
}

// ── Stéréo Widener (Haas) ──
function rackToggleStereo() {
  const btn = document.getElementById('rack-stereo-bypass');
  const isOn = btn && btn.classList.toggle('on');
  btn && btn.classList.toggle('off', !isOn);
  _stereoActive = !!isOn;
  if (_haasGainNode && audioCtx)
    _haasGainNode.gain.setTargetAtTime(isOn ? _stereoWidth / 100 : 0, audioCtx.currentTime, 0.02);
  document.getElementById('rack-unit-stereo').classList.toggle('bypassed', !isOn);
  document.getElementById('rsp-stereo').classList.toggle('active', isOn);
  const tag = document.getElementById('rack-stereo-tag');
  if (tag) { tag.textContent = isOn ? 'L + R' : 'MONO'; tag.className = 'rack-unit-tag ' + (isOn ? 'tag-ok' : ''); }
  if (!isOn) _clearUnitVu(['rack-vu-stereo-l','rack-vu-stereo-r']);
  _patchDsp({stereo_enabled:isOn});
}

function _rackFaderFill(id) {
  const sl = document.getElementById(id);
  if (!sl) return;
  const pct = ((parseFloat(sl.value)-parseFloat(sl.min))/(parseFloat(sl.max)-parseFloat(sl.min))*100).toFixed(1);
  sl.style.setProperty('--f-pct', pct + '%');
}

function rackSyncStereoWidth(val) {
  const v = document.getElementById('rack-stereo-width-val');
  if (v) v.textContent = Math.round(val) + '%';
  _stereoWidth = parseFloat(val);
  _rackFaderFill('rack-stereo-width');
  if (_haasGainNode && audioCtx && _stereoActive)
    _haasGainNode.gain.setTargetAtTime(_stereoWidth / 100, audioCtx.currentTime, 0.01);
  _patchDsp({stereo_width: _stereoWidth/100});
}

function rackSyncHaasDelay(val) {
  const v = document.getElementById('rack-haas-delay-val');
  if (v) v.textContent = parseFloat(val).toFixed(1) + ' ms';
  _rackFaderFill('rack-haas-delay');
  if (_haasDelayNode && audioCtx)
    _haasDelayNode.delayTime.setTargetAtTime(parseFloat(val) / 1000, audioCtx.currentTime, 0.01);
  // Mise à jour badge header
  const badge = document.querySelector('[id="rack-sr-badge"] ~ button')?.previousElementSibling?.previousElementSibling;
  // Cherche le badge HAAS dans le header rack
  document.querySelectorAll('.rack-header span').forEach(s => {
    if (s.textContent.includes('HAAS')) s.textContent = `▶ HAAS ${parseFloat(val).toFixed(0)}ms`;
  });
  _patchDsp({haas_delay_ms: parseFloat(val)});
}

// ── Analyseur spectral ──
function toggleEqPanel() {
  const btn   = document.getElementById('eq-panel-bypass');
  const panel = document.getElementById('dsp-panel-eq');
  if (!btn || !panel) return;
  const isOn = btn.classList.toggle('on');
  btn.classList.toggle('off', !isOn);
  btn.classList.add('pulse-anim');
  setTimeout(() => btn.classList.remove('pulse-anim'), 500);
  panel.classList.toggle('bypassed', !isOn);
  _eqPanelOn = isOn;
  if (!isOn) {
    // Figer le canvas sur un état statique (plus de spectrum animé)
    const cv = document.getElementById('eq-curve-canvas');
    if (cv && cv.offsetWidth > 0) {
      const ctx2 = cv.getContext('2d');
      const W = cv.width || cv.offsetWidth, H = cv.height || cv.offsetHeight;
      ctx2.fillStyle = '#010810';
      ctx2.fillRect(0, 0, W, H);
      ctx2.save();
      ctx2.font = `bold ${Math.round(H * 0.09)}px Orbitron, monospace`;
      ctx2.fillStyle = '#00cfff14';
      ctx2.textAlign = 'center';
      ctx2.textBaseline = 'middle';
      ctx2.fillText('BYPASS', W / 2, H / 2);
      ctx2.restore();
    }
  } else {
    drawEqCurve();
  }
}

/* ── Spectral color presets ──────────────────────────────────── */
const SPEC_PRESETS = {
  jarvis:  { top:'rgba(0,230,180,.30)',  mid:'rgba(0,180,255,.14)', bot:'rgba(0,60,120,.03)',  peak:'rgba(0,215,255,.45)' },
  plasma:  { top:'rgba(200,0,255,.32)',  mid:'rgba(120,0,200,.14)', bot:'rgba(40,0,80,.03)',   peak:'rgba(220,80,255,.50)' },
  fire:    { top:'rgba(255,60,0,.34)',   mid:'rgba(255,140,0,.16)', bot:'rgba(80,20,0,.03)',   peak:'rgba(255,200,60,.50)' },
  matrix:  { top:'rgba(0,255,80,.28)',   mid:'rgba(0,180,60,.12)',  bot:'rgba(0,40,10,.03)',   peak:'rgba(80,255,120,.45)' },
  void:    { top:'rgba(40,0,180,.30)',   mid:'rgba(20,0,120,.12)',  bot:'rgba(5,0,30,.03)',    peak:'rgba(80,60,255,.45)' },
  neon:    { top:'rgba(255,255,255,.28)',mid:'rgba(0,255,255,.16)', bot:'rgba(0,100,150,.03)', peak:'rgba(255,255,255,.60)' },
  sunset:  { top:'rgba(255,100,60,.32)', mid:'rgba(255,60,120,.14)',bot:'rgba(60,0,30,.03)',   peak:'rgba(255,180,80,.50)' },
  aurora:  { top:'rgba(0,255,160,.28)',  mid:'rgba(0,120,255,.14)', bot:'rgba(0,20,60,.03)',   peak:'rgba(120,255,200,.45)' },
  steel:   { top:'rgba(140,180,220,.26)',mid:'rgba(80,120,180,.12)',bot:'rgba(20,40,80,.03)',  peak:'rgba(180,210,255,.40)' },
  storm:   { top:'rgba(255,240,0,.28)',  mid:'rgba(0,200,255,.14)', bot:'rgba(0,40,80,.03)',   peak:'rgba(255,255,100,.50)' },
};
window._eqSpecPreset = 'jarvis';

function applySpecPreset(name) {
  if (!SPEC_PRESETS[name]) return;
  window._eqSpecPreset = name;
  window._eqSpecPeaks  = null;
  document.querySelectorAll('[id^="spr-"]').forEach(b => b.classList.remove('active'));
  document.getElementById('spr-' + name)?.classList.add('active');
  // Redraw immédiat + s'assurer que la RAF est active
  drawEqCurve();
  if (!_dspRafId) startDspDraw();
}

function rackToggleAnalyser() {
  const btn = document.getElementById('rack-analyser-bypass');
  const isOn = btn && btn.classList.toggle('on');
  btn && btn.classList.toggle('off', !isOn);
  document.getElementById('rack-unit-analyser').classList.toggle('bypassed', !isOn);
  document.getElementById('rsp-analyser').classList.toggle('active', isOn);
  _analyserEnabled = isOn;
  const cv = document.getElementById('rack-spectrum-canvas');
  if (cv) {
    if (!isOn) {
      const ctx2 = cv.getContext('2d');
      ctx2.fillStyle = '#01080f';
      ctx2.fillRect(0, 0, cv.width, cv.height);
      ctx2.save();
      ctx2.font = 'bold 32px Orbitron, monospace';
      ctx2.fillStyle = '#00cfff18';
      ctx2.textAlign = 'center';
      ctx2.textBaseline = 'middle';
      ctx2.letterSpacing = '10px';
      ctx2.fillText('BYPASS', cv.width / 2, cv.height / 2);
      ctx2.restore();
    }
  }
}

function rackApplyAll() {
  pushDspParamsToBackend();
  const btn = document.querySelector('[data-action="rackApplyAll"]');
  if (btn) { const o=btn.textContent; btn.textContent='✓ APPLIQUÉ'; _stColor(btn,'ok'); setTimeout(()=>{btn.textContent=o;_stColor(btn,null);},1500); }
}

var _dspMasterOn = true;

// Source de vérité unique pour le master DSP — appelé par toggleDspMaster ET rackToggleMaster
function _applyDspMaster(isOn) {
  _dspMasterOn = !!isOn;
  // WebAudio
  if (_dspGainNode && audioCtx) {
    if (isOn) {
      const sl = document.getElementById('rack-gain');
      const dB = sl ? parseFloat(sl.value) : 0;
      _dspGainNode.gain.linearRampToValueAtTime(Math.pow(10, dB / 20), audioCtx.currentTime + 0.05);
    } else {
      _dspGainNode.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.05);
    }
  }
  // UI — bouton ⏻ OUTPUT (rack)
  const btn = document.getElementById('dsp-master-pwr');
  if (btn) btn.className = 'rack-bypass-btn ' + (isOn ? 'on' : 'off');
  // UI — toggle header panel
  const mt = document.getElementById('dsp-master-toggle');
  if (mt) { if (isOn) mt.classList.add('on'); else mt.classList.remove('on'); }
  // UI — bordure OUTPUT
  const ro = document.querySelector('.rack-output');
  if (ro) ro.classList.toggle('dsp-off', !isOn);
  // UI — statut chaîne
  _updateDspChainStatus(isOn);
  // Backend
  fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({enabled: isOn})
  }).catch(()=>{});
}

function rackToggleMaster() {
  _applyDspMaster(!_dspMasterOn);
}

function rackTestVoice() {
  setTimeout(() => testDspVoice(), 150);
}

// ── Bouton SOC depuis DSP ────────────────────────────────────
let _dspSocBusy = false;
async function dspSocReport() {
  if (_dspSocBusy) return;
  _dspSocBusy = true;
  const btn = document.getElementById('dsp-soc-btn');
  const ico = document.getElementById('dsp-soc-ico');
  if (btn) { btn.style.opacity = '0.6'; btn.style.cursor = 'wait'; }
  if (ico) ico.textContent = '◌';

  try {
    // Envoyer la requête SOC au chat JARVIS (même endpoint que le chat)
    const history = [{ role: 'user', content: 'état du soc' }];
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(await _buildChatPayload(history))
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);

    // Lire le stream SSE et accumuler le texte
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let fullText = '';
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        try {
          const chunk = JSON.parse(line.slice(5).trim());
          if (chunk.type === 'token') fullText += chunk.token;
        } catch (_) { /* skip malformed SSE line */ }
      }
    }

    // Lire la réponse via TTS avec la chaîne DSP active
    if (fullText.trim()) {
      if (typeof queueSpeech === 'function') queueSpeech(fullText);
    }

    // Flash vert succès
    if (ico) ico.textContent = '✓';
    if (btn) _stColor(btn,'ok');
    setTimeout(() => {
      if (ico) ico.textContent = '⬡';
      if (btn) btn.style.opacity = '1'; btn && (btn.style.cursor = 'pointer');
    }, 2000);

  } catch (e) {
    if (ico) ico.textContent = '✕';
    if (btn) _stColor(btn,'err');
    setTimeout(() => {
      if (ico) ico.textContent = '⬡';
      if (btn) { _stColor(btn,'ok'); btn.style.opacity = '1'; btn.style.cursor = 'pointer'; }
    }, 2500);
  }
  _dspSocBusy = false;
}

function _updateDspChainStatus(enabled) {
  const st = document.getElementById('dsp-chain-status');
  if (!st) return;
  if (enabled) {
    st.textContent = '◉ CHAÎNE ACTIVE';
    _stColor(st,'active');
  } else {
    st.textContent = '◌ DSP BYPASS';
    _stColor(st,'err');
  }
}

function toggleDspMaster() {
  _applyDspMaster(!_dspMasterOn);
}

function eqPushNow() {
  pushDspParamsToBackend();
  // Feedback visuel
  const btn = document.querySelector('[data-action="eqPushNow"]');
  if (btn) {
    const orig = btn.textContent;
    btn.textContent = '✓ ENVOYÉ';
    _stColor(btn,'ok');
    setTimeout(() => { btn.textContent = orig; _stColor(btn,null); }, 1500);
  }
}

function _updateEqCoupleBadges() {
  const off    = !_eqVoiceCoupled;
  const dot    = document.getElementById('eq-couple-dot');
  const label  = document.getElementById('eq-couple-label');
  const btn    = document.getElementById('eq-voice-couple-btn');
  const bdot   = document.getElementById('dsp-badge-dot');
  const blabel = document.getElementById('dsp-badge-label');
  const badge  = document.getElementById('dsp-voice-badge');
  if (dot)    dot.classList.toggle('decoupled', off);
  if (label)  label.textContent = _eqVoiceCoupled ? 'COUPLÉ VOIX JARVIS' : 'EQ DÉCOUPLÉ';
  if (btn)    btn.classList.toggle('decoupled', off);
  if (bdot)   bdot.classList.toggle('decoupled', off);
  if (blabel) blabel.textContent = _eqVoiceCoupled ? 'EQ ACTIF' : 'EQ OFF';
  if (badge)  badge.classList.toggle('decoupled', off);
}

let _dspPushTimer = null;
function _dspSchedulePush() {
  clearTimeout(_dspPushTimer);
  if (_eqVoiceCoupled) _dspPushTimer = setTimeout(pushDspParamsToBackend, _DSP_PUSH_MS);
}

function setEqBand(band, val) {
  if (_eqLastCombined) {
    _eqGhost = new Float32Array(_eqLastCombined);
    _eqGhostAlpha = 0.55;
  }
  const idx = EQ_BANDS.findIndex(b => b.id === band);
  const v = parseFloat(val);
  if (idx >= 0) _eqState[idx].gain = v;
  const node = { low:_dspEqLow, mid:_dspEqMid, high:_dspEqHigh, air:_dspEqAir }[band];
  const noGainTypes = ['highpass','lowpass','notch','bandpass'];
  if (node && idx >= 0 && !_eqState[idx].bypassed && !noGainTypes.includes(_eqState[idx].type)) {
    node.gain.value = v;
  }
  const label = document.getElementById('eq-'+band+'-val');
  if (label) label.textContent = (v >= 0 ? '+' : '') + v.toFixed(1) + ' dB';
  const gc = document.getElementById('eq-gc-'+band);
  if (gc) gc.textContent = (v >= 0 ? '+' : '') + v.toFixed(1);
  const sl = document.getElementById('eq-'+band);
  if (sl) updateSliderPct(sl);
  drawEqCurve();
  _dspSchedulePush();
}

// ── Update freq/Q/type counters ──
function _eqUpdateCounters(idx) {
  const band = EQ_BANDS[idx];
  const s = _eqState[idx];
  const fc = document.getElementById('eq-fc-'+band.id);
  if (fc) fc.textContent = s.freq >= 1000 ? (s.freq/1000).toFixed(2)+'k' : s.freq.toFixed(0)+'Hz';
  const qc = document.getElementById('eq-qc-'+band.id);
  if (qc) qc.textContent = s.q.toFixed(2);
}

function _eqBandIdx(bandId)    { return EQ_BANDS.findIndex(b => b.id === bandId); }
function _datEqBandIdx(bandId) { return DAT_EQ_BANDS.findIndex(b => b.id === bandId); }
function _canvasCoords(e, id) {
  const canvas = document.getElementById(id); if (!canvas) return null;
  const r = canvas.getBoundingClientRect();
  return { mx: e.clientX - r.left, my: e.clientY - r.top, canvas };
}

function eqSetFreq(bandId, freq) {
  const idx = _eqBandIdx(bandId);
  if (idx < 0) return;
  const [fMin, fMax] = _eqFreqRange[idx];
  freq = Math.max(fMin, Math.min(fMax, freq));
  _eqState[idx].freq = freq;
  EQ_BANDS[idx].freq = freq;
  const node = {low:_dspEqLow,mid:_dspEqMid,high:_dspEqHigh,air:_dspEqAir}[bandId];
  if (node) node.frequency.value = freq;
  _eqUpdateCounters(idx);
  drawEqCurve();
  _dspSchedulePush();
}

function eqSetQ(bandId, q) {
  const idx = _eqBandIdx(bandId);
  if (idx < 0) return;
  q = Math.max(0.1, Math.min(12, q));
  _eqState[idx].q = q;
  EQ_BANDS[idx].Q = q;
  const node = {low:_dspEqLow,mid:_dspEqMid,high:_dspEqHigh,air:_dspEqAir}[bandId];
  if (node) node.Q.value = q;
  _eqUpdateCounters(idx);
  drawEqCurve();
}

function eqSetType(bandId, type) {
  const idx = _eqBandIdx(bandId);
  if (idx < 0) return;
  if (_eqLastCombined) { _eqGhost = new Float32Array(_eqLastCombined); _eqGhostAlpha = 0.55; }
  _eqState[idx].type = type;
  EQ_BANDS[idx].type = type;
  const node = {low:_dspEqLow,mid:_dspEqMid,high:_dspEqHigh,air:_dspEqAir}[bandId];
  if (node) {
    const waTypes = {highpass:'highpass',lowpass:'lowpass',notch:'notch',
                     peaking:'peaking',lowshelf:'lowshelf',highshelf:'highshelf',bandpass:'bandpass'};
    try { node.type = waTypes[type] || 'peaking'; } catch(e) { /* BiquadFilterNode.type throws on invalid value */ }
    const noGain = ['highpass','lowpass','notch','bandpass'].includes(type);
    if (noGain) { node.gain.value = 0; }
    else { node.gain.value = _eqState[idx].gain; }
  }
  // Update type button active state
  document.querySelectorAll(`.eq-type-btn[data-band="${bandId}"]`).forEach(b =>
    b.classList.toggle('active', b.dataset.type === type));
  drawEqCurve();
}

function eqToggleBypass(bandId) {
  const idx = _eqBandIdx(bandId);
  if (idx < 0) return;
  _eqState[idx].bypassed = !_eqState[idx].bypassed;
  const node = {low:_dspEqLow,mid:_dspEqMid,high:_dspEqHigh,air:_dspEqAir}[bandId];
  if (node) {
    const noGain = ['highpass','lowpass','notch','bandpass'].includes(_eqState[idx].type);
    if (_eqState[idx].bypassed) {
      // allpass = filtre plat réel pour tous les types (gain=0 n'a aucun effet sur HP/LP/NOTCH/BP)
      if (noGain) { node.type = 'allpass'; }
      else { node.gain.value = 0; }
    } else {
      node.type = _eqState[idx].type;
      if (noGain) { node.gain.value = 0; }
      else { node.gain.value = _eqState[idx].gain; }
    }
  }
  const btn = document.getElementById('eq-byp-'+bandId);
  if (btn) btn.classList.toggle('bypassed', _eqState[idx].bypassed);
  drawEqCurve();
}

// → EQ MUSIC + TTS engines extraits — static/js/eq_music.js (chantier dette 2026-05-14)
// → MIRE DE TEST AUDIO extraite — static/js/audio_mire.js (chantier dette 2026-05-14)
// Global mouseup: release EQ drag if cursor leaves canvas
document.addEventListener('mouseup', () => { if (_eqDrag) { _eqDrag = null; const c=document.getElementById('eq-curve-canvas'); if(c)c.style.cursor='crosshair'; } });

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

// → TÂCHES TAB + WELCOME extraits — static/js/tasks_tab.js + static/js/welcome.js (chantier dette 2026-05-14)
