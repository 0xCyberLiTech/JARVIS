// ══════════════════════════════════════════════════════════════
// SETTINGS UI — panneaux de configuration + switchers + HUD
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-15.
//
// Cinq sous-systèmes UI regroupés (étaient bannières séparées) :
//
//  1. SETTINGS GPU HEALTH (~100 L) — onglet ⚙ SETTINGS GPU :
//     polling stats GPU/VRAM/temp, sliders limites, sauvegarde config.
//  2. MODELE SWITCHER (~140 L) — sélecteur modèle Ollama dans l'UI :
//     icônes par modèle, swap visuel, callback POST /api/model.
//  3. VOICE SWITCHER (~110 L) — sélecteur voix TTS (Antoine, etc.) :
//     liste voix, preview, persistance LocalStorage.
//  4. LLM HEADER (~17 L) — affichage modèle actif dans le header.
//  5. CHAT HUD EXTRAS (~85 L) — boutons HUD, raccourcis chat, helpers.
//
// State top-level : let _stgPollTimer = null, let ttsEnabled = true.
// Toutes ces fonctions sont consommées par les data-action des templates
// (jarvis.html + tabs/) — scope global partagé.
//
// Fichier .js classique. Position dans jarvis.html : peut charger après
// jarvis_main.js (les fonctions sont appelées via click handlers, pas top-level).

let _stgPollTimer = null;
function _vramCapGb() { return _VRAM_TOTAL ? (_VRAM_TOTAL / (1024 ** 3)) : 16; }
const MODEL_VRAM = { 'phi4:14b': 9.1, 'qwen2.5:14b': 8.7, 'gemma4:latest': 9.6, 'mistral-small3.1:latest': 6.2, 'deepseek-r1:14b': 9.0 };

function startSettingsPolling() {
  updateSettingsGpu();
  _stgPollTimer = setInterval(updateSettingsGpu, _STG_GPU_POLL_MS);
}
function stopSettingsPolling() {
  if (_stgPollTimer) { clearInterval(_stgPollTimer); _stgPollTimer = null; }
}

async function updateSettingsGpu() {
  try {
    const r = await fetch('/api/stats');
    const d = await r.json();
    const _vCap = _vramCapGb();
    setHealthBar('vram', d.vram_used_gb ?? 0, _vCap, 'GB',
      v => v < _vCap * 0.7 ? 'safe' : v < _vCap * 0.85 ? 'warn' : 'crit',
      v => `${v.toFixed(1)} / ${_vCap.toFixed(1)} GB`);
    setHealthBar('gpu',  d.gpu_util ?? 0, 100, '%',
      v => v < 70 ? 'safe' : v < 85 ? 'warn' : 'crit',
      v => `${Math.round(v)}%`);
    setHealthBar('temp', d.gpu_temp ?? 0, 100, '°C',
      v => v < 70 ? 'safe' : v < 85 ? 'warn' : 'crit',
      v => `${Math.round(v)}°C`);
    setHealthBar('pow',  d.gpu_power ?? 0, 360, 'W',
      v => v < 252 ? 'safe' : v < 306 ? 'warn' : 'crit',
      v => `${Math.round(v)} W`);
    updateImpactBars();
  } catch(e) { _jwarn('[JARVIS] updateRtxStats error', e); }
}

function setHealthBar(id, value, max, unit, levelFn, labelFn) {
  const pct   = Math.min(100, (value / max) * 100);
  const level = levelFn(value);
  const fill  = document.getElementById(`h-${id}-fill`);
  const val   = document.getElementById(`h-${id}-val`);
  if (fill) { fill.style.width = pct + '%'; fill.className = `health-fill ${level}`; }
  if (val)  { val.textContent = labelFn(value); val.className = `health-value ${level === 'safe' ? '' : level}`; }
}

function updateImpactBars() {
  const predict = parseFloat(document.getElementById('s-num_predict')?.value ?? 1024);
  const topk    = parseFloat(document.getElementById('s-top_k')?.value ?? 40);
  const temp    = parseFloat(document.getElementById('s-temperature')?.value ?? 0.7);

  // num_predict → VRAM KV cache impact
  const kvGb  = (predict / 4096) * 3.2; // estimation KV cache pour 14B
  const pPred = Math.min(100, (predict / 4096) * 100);
  const pTopk = Math.min(100, (topk / 100) * 100);
  const pTemp = Math.min(100, (temp / 2) * 100);

  setImpactBar('imp-predict', pPred);
  setImpactBar('imp-topk',    pTopk);
  setImpactBar('imp-temp',    pTemp);

  // Estimation VRAM totale
  const sel = document.getElementById('model-select');
  const modelName = sel ? sel.value : 'phi4:14b';
  const modelGb   = MODEL_VRAM[modelName] ?? 9.1;
  const totalEst  = modelGb + kvGb;
  const _vc2      = _vramCapGb();
  const freeEst   = _vc2 - totalEst;

  const modelPct = (modelGb / _vc2) * 100;
  const kvPct    = (kvGb    / _vc2) * 100;

  const mf = document.getElementById('vram-model-fill');
  const kf = document.getElementById('vram-kv-fill');
  const lbl = document.getElementById('vram-free-label');
  const kvLbl = document.getElementById('vram-kv-label');

  if (mf)    mf.style.width = modelPct + '%';
  if (kf)    { kf.style.left = modelPct + '%'; kf.style.width = Math.min(kvPct, 100 - modelPct) + '%'; }
  if (kvLbl) kvLbl.textContent = `KV cache ~${kvGb.toFixed(1)} GB`;
  if (lbl) {
    const safe = freeEst > 3;
    lbl.classList.toggle('vram-safe', safe);
    lbl.textContent = freeEst > 0
      ? `Libre estimé : ~${freeEst.toFixed(1)} GB — ${safe ? 'ZONE SÛRE ✓' : '⚠ ATTENTION — VRAM CRITIQUE'}`
      : `⚠ VRAM INSUFFISANTE — risque de swap RAM`;
  }
}

function setImpactBar(id, pct) {
  const bar = document.getElementById(id);
  const tag = document.getElementById(id + '-tag');
  if (!bar) return;
  bar.style.width = pct + '%';
  let level, label;
  if (pct < 35)       { level = 'low';  label = 'LÉGER'; }
  else if (pct < 70)  { level = 'med';  label = 'MOYEN'; }
  else                { level = 'high'; label = 'LOURD'; }
  bar.classList.remove('impact-bar-lv-low', 'impact-bar-lv-med', 'impact-bar-lv-high');
  bar.classList.add(`impact-bar-lv-${level}`);
  if (tag) { tag.textContent = label; tag.className = `impact-tag tag-${level}`; }
}

// → SETTINGS LLM extrait — static/js/settings_llm.js (chantier dette 2026-05-14)
// ══════════════════════════════════════
// MODELE SWITCHER
// ══════════════════════════════════════
// Icône selon le modèle
function _modelIcon(name) {
  if (name.includes('gemma'))  return '◈';
  if (name.includes('qwen'))   return '◆';
  if (name.includes('phi'))    return '◇';
  if (name.includes('llava'))  return '◈';
  if (name.includes('llama'))  return '◉';
  if (name.includes('moondream') || name.includes('minicpm')) return '◈';
  return '○';
}

async function loadModels() {
  try {
    const [r, rProf] = await Promise.all([fetch('/api/models'), fetch('/api/prompt-profiles')]);
    const d = await r.json();
    const profs = await rProf.json();
    const _modelRoles = {};
    Object.values(profs).forEach(p => { if (p.model_binding && p.role) _modelRoles[p.model_binding] = p.role; });

    // Hidden select (compat)
    const sel = document.getElementById('model-select');
    if (sel) {
      sel.innerHTML = '';
      d.models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m; opt.textContent = m;
        if (m === d.current) opt.selected = true;
        sel.appendChild(opt);
      });
    }

    // Model cards
    const grid = document.getElementById('model-cards-grid');
    if (grid) {
      grid.innerHTML = '';
      // Modèles raisonnement compatibles RTX 5080 16GB (tags >16GB exclus)
      const _LOC_R = new Set(['deepseek-r1','phi4-reasoning','phi4-mini-reasoning','cogito','exaone-deep','openthinker','granite3.3','qwq','qwen3']);
      const _LOC_V = new Set(['llava-phi3','llava','moondream','minicpm-v','bakllava']);
      const _BIG_TAGS = new Set(['32b','70b','671b']);
      d.models.forEach(m => {
        const [base, tag] = m.split(':');
        const isReasoning = _LOC_R.has(base) && !_BIG_TAGS.has(tag);
        const isVision    = _LOC_V.has(base);
        const card = document.createElement('div');
        card.className = 'voice-card' + (m === d.current ? ' active' : '');
        if (isReasoning) card.classList.add('voice-card-reasoning');
        if (isVision)    card.classList.add('voice-card-vision');
        card.dataset.modelId = m;
        const rBadge = isReasoning
          ? '<span class="vc-badge-reasoning">◈ R</span>'
          : isVision
          ? '<span class="vc-badge-vision">📷 V</span>'
          : '';
        const nameClass = isReasoning ? 'vc-name vc-name-reasoning' : isVision ? 'vc-name vc-name-vision' : 'vc-name';
        const roleText = _modelRoles[m] || '';
        const roleBtnHtml = roleText ? `<span class="vc-role-btn">◈</span>` : '';
        card.innerHTML = `<span class="vc-dot"></span><span class="vc-flag">${_modelIcon(m)}</span><span class="${nameClass}">${_esc(base)}</span><span class="vc-gender">${_esc(tag||'')}</span>${rBadge}${roleBtnHtml}`;
        card.onclick = () => switchModel(m);
        if (roleText) {
          const rb = card.querySelector('.vc-role-btn');
          rb.addEventListener('mouseenter', e => { e.stopPropagation(); _showModelPopup(e.currentTarget, roleText); });
          rb.addEventListener('mouseleave', _hideModelPopup);
        }
        grid.appendChild(card);
      });
    }

    const st = document.getElementById('model-status');
    if (st) { st.textContent = '● ' + d.current + ' — ACTIF'; _stColor(st,'active'); }
    _updateModeBtn(); // synchronise la carte JARVIS target après chargement des cartes
  } catch(e) { _jwarn('[JARVIS] loadModels error', e); }
}

async function testActiveModel() {
  const btn = document.getElementById('btn-model-test');
  const res = document.getElementById('model-test-result');
  if (!res) return;
  _stColor(res,'load');
  res.textContent = '··· TEST EN COURS';
  if (btn) btn.disabled = true;
  try {
    const sel = document.getElementById('model-select');
    const model = sel ? sel.value : '';
    const r = await fetch('/api/models/test', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({model})
    });
    const d = await r.json();
    if (d.ok) {
      _stColor(res,'ok');
      res.textContent = `✓ OPÉRATIONNEL — ${d.latency_ms} ms`;
    } else {
      _stColor(res,'err');
      res.textContent = `✗ ERREUR — ${d.error || 'indisponible'}`;
    }
  } catch(e) {
    _stColor(res,'err');
    res.textContent = '✗ CONNEXION ÉCHOUÉE';
  }
  if (btn) btn.disabled = false;
  _clearAfter(res, _COVER_SAFE_MS);
}

async function switchModel(model) {
  const statusEl = document.getElementById('model-status');
  if (statusEl) { statusEl.textContent = '···'; _stColor(statusEl,'load'); }
  try {
    const r = await fetch('/api/models', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({model})
    });
    const d = await r.json();
    if (d.ok) {
      // Cartes
      document.querySelectorAll('#model-cards-grid .voice-card').forEach(c => {
        c.classList.toggle('active', c.dataset.modelId === model);
      });
      const sel = document.getElementById('model-select');
      if (sel) sel.value = model;
      if (statusEl) { statusEl.textContent = '● ' + d.model + ' — ACTIF'; _stColor(statusEl,'active'); }
      updateSettingsGpu();
      _updateHeaderLLM();
      setTimeout(_refreshVramNow, 800);
      // Profil auto-chargé → mettre à jour l'UI profils
      if (d.auto_profile !== undefined) {
        _updateActivePromptBadge(d.auto_profile || null);
        loadPromptProfiles();
        const ta = document.getElementById('system-prompt-editor');
        if (ta) { const ld = await _fetchLlmParams(); if (ld.system_prompt) ta.value = ld.system_prompt; }
      }
    }
  } catch(e) {
    if (statusEl) { statusEl.textContent = 'ERREUR'; _stColor(statusEl,'err'); }
  }
}

loadModels();

// ══════════════════════════════════════
// VOICE SWITCHER
// ══════════════════════════════════════
let ttsEnabled = true;

async function loadVoices() {
  try {
    const r = await fetch('/api/voices');
    const d = await r.json();

    // Hidden select (compatibility)
    const sel = document.getElementById('voice-select');
    if (sel) {
      sel.innerHTML = '';
      d.voices.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = `${v.flag} ${v.label}`;
        if (v.id === d.current) opt.selected = true;
        sel.appendChild(opt);
      });
    }

    // Voice cards grid
    const grid = document.getElementById('voice-cards-grid');
    if (grid) {
      grid.innerHTML = '';
      d.voices.forEach(v => {
        const card = document.createElement('div');
        card.className = 'voice-card' + (v.id === d.current ? ' active' : '');
        card.dataset.voiceId = v.id;
        card.innerHTML = `<span class="vc-dot"></span><span class="vc-flag">${v.flag}</span><span class="vc-name">${v.label}</span><span class="vc-gender">${v.gender === 'M' ? '♂' : '♀'}</span>`;
        card.onclick = () => switchVoice(v.id);
        grid.appendChild(card);
      });
    }

    document.getElementById('tts-toggle').classList.add('on');
    syncDspVoices();
  } catch(e) { _jwarn('[JARVIS] loadTtsSettings error', e); }
}

// ── Mode voix : cloud uniquement (EDGE) ──────────────────────
let _voiceMode = 'cloud';
let _lastLocalEngine = 'edge';

async function setVoiceMode(mode) {
  _voiceMode = 'cloud';
  const cloudPanel = document.getElementById('voice-cloud-panel');
  _disp(cloudPanel, true, 'block');
  await setTtsEngine('edge');
}

async function switchVoice(voiceId) {
  const st = document.getElementById('voice-status');
  if (st) { st.textContent = '···'; _stColor(st,'load'); }
  try {
    const r = await fetch('/api/voices', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({voice: voiceId})
    });
    const d = await r.json();
    if (d.ok) {
      // Mettre à jour les cartes visuelles
      document.querySelectorAll('.voice-card').forEach(c => {
        const active = c.dataset.voiceId === voiceId;
        c.classList.toggle('active', active);
      });
      // Hidden select sync
      const sel = document.getElementById('voice-select');
      if (sel) sel.value = voiceId;
      // Status
      const card = document.querySelector(`.voice-card[data-voice-id="${voiceId}"]`);
      const label = card ? card.querySelector('.vc-name').textContent : voiceId;
      if (st) { st.textContent = '● ' + label + ' — ACTIF'; _stColor(st,'active'); }
      // Test audio
      if (ttsEnabled) {
        const name = label.split(' ')[0];
        queueSpeech(`Voix ${name} activée.`);
      }
    }
  } catch(e) {
    if (st) { st.textContent = 'ERREUR'; _stColor(st,'err'); }
  }
}

function toggleTTS() {
  ttsEnabled = !ttsEnabled;
  const tog = document.getElementById('tts-toggle');
  tog.classList.toggle('on', ttsEnabled);
}

loadVoices();
// Initialiser le moteur TTS depuis la config DSP (kokoro reste kokoro au rechargement)
setTimeout(async () => {
  try {
    const d = await _fetchDspParams();
    const def = d.tts_default_engine || 'edge';
    _syncDefaultEngineButtons(def);
    // Restaure les sliders de vitesse depuis DSP_PARAMS sauvegardé
    if (d.tts_kokoro_speed != null) {
      const ksl = document.getElementById('dsp-kokoro-speed');
      if (ksl) { ksl.value = d.tts_kokoro_speed; setKokoroSpeed(d.tts_kokoro_speed); }
    }
    // Au démarrage : utiliser le moteur par défaut (pas le dernier moteur de session)
    if (def === 'edge') { setVoiceMode('cloud'); }
    else { await setTtsEngine(def); }
  } catch(e) { setVoiceMode('cloud'); }
}, 300);

// ══════════════════════════════════════
// LLM HEADER — local uniquement
// ══════════════════════════════════════
function _updateHeaderLLM() {
  const el = document.getElementById('hdr-llm');
  if (!el) return;
  const sel = document.getElementById('model-select');
  const fullModel = sel ? (sel.value || '—') : '—';
  const [mBase, mTag] = fullModel.split(':');
  const _LOC_R = new Set(['deepseek-r1','phi4-reasoning','phi4-mini-reasoning','cogito','exaone-deep','openthinker','granite3.3','qwq','qwen3']);
  const _LOC_V = new Set(['llava-phi3','llava','moondream','minicpm-v','bakllava']);
  const _BIG  = new Set(['32b','70b','671b']);
  const isReasoning = _LOC_R.has(mBase) && !_BIG.has(mTag);
  const isVision    = _LOC_V.has(mBase);
  const model = mBase + (isReasoning ? ' ◈R' : isVision ? ' 📷V' : '');
  el.dataset.llmType = isReasoning ? 'r' : isVision ? 'v' : 'l';
  el.innerHTML = 'LLM // LOCAL<br><span class="hdr-llm-model">'+_esc(model)+'</span>';
}

// ══════════════════════════════════════
// CHAT HUD EXTRAS
// ══════════════════════════════════════

// ── Data stream: falling hex digits on right side canvas ──
(function initDataStream() {
  const canvas = document.getElementById('data-stream-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const HEX = '0123456789ABCDEF';
  let cols = 1, drops = [0];
  function resize() {
    canvas.width  = canvas.offsetWidth  || 16;
    canvas.height = canvas.offsetHeight || 600;
    cols  = Math.max(1, Math.floor(canvas.width / 10));
    drops = Array(cols).fill(0);
  }
  resize();
  window.addEventListener('resize', resize);
  function draw() {
    ctx.fillStyle = 'rgba(0,2,10,0.18)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#00cfff';
    ctx.font = '9px Share Tech Mono, monospace';
    for (let i = 0; i < drops.length; i++) {
      const ch = HEX[Math.floor(Math.random() * HEX.length)];
      const x = i * 10;
      const y = drops[i] * 11;
      ctx.globalAlpha = 0.6 + Math.random() * 0.4;
      ctx.fillText(ch, x, y);
      if (y > canvas.height && Math.random() > 0.97) drops[i] = 0;
      drops[i] += Math.random() < 0.5 ? 1 : 0;
    }
    ctx.globalAlpha = 1;
  }
  setInterval(draw, _DRAW_INTERVAL_MS);
})();

// ── Telemetry header drift ──
(function initTelemetry() {
  const el = document.getElementById('hdr-coords');
  if (!el) return;
  let lat = 48.8566, lon = 2.3522, alt = 312;
  function drift() {
    lat += (Math.random() - 0.5) * 0.0002;
    lon += (Math.random() - 0.5) * 0.0002;
    alt += Math.round((Math.random() - 0.5) * 2);
    el.innerHTML =
      'LAT: ' + lat.toFixed(4) + ' // LON: ' + lon.toFixed(4) + '<br>' +
      'ALT: ' + alt + 'm // ACC: \u00b12m<br>' +
      'SIG: STRONG // ENC: ON';
  }
  setInterval(drift, _DRIFT_INTERVAL_MS);
})();

// ── Coordinates sidebar drift ──
(function initCoords() {
  let lat = 48.8566, lon = 2.3522, alt = 312;
  const latEl = document.getElementById('coord-lat');
  const lonEl = document.getElementById('coord-lon');
  const altEl = document.getElementById('coord-alt');
  if (!latEl) return;
  function update() {
    lat += (Math.random() - 0.5) * 0.0003;
    lon += (Math.random() - 0.5) * 0.0003;
    alt += Math.round((Math.random() - 0.5) * 3);
    latEl.textContent = lat.toFixed(4) + '\u00b0 N';
    lonEl.textContent = lon.toFixed(4) + '\u00b0 E';
    altEl.textContent = alt + ' m';
  }
  setInterval(update, _UPD_INTERVAL_MS);
})();

function rackInitFaders() {
  document.querySelectorAll('.rack-fader').forEach(f => {
    const update = () => {
      const pct = ((f.value - f.min) / (f.max - f.min) * 100).toFixed(1);
      f.style.setProperty('--f-pct', pct + '%');
    };
    f.addEventListener('input', update);
    update();
  });
  // Sync rack sliders from current DSP state
  _rackSyncFromDsp();
  // Start VU meter for integrated rack
  if (!_rackVuInterval) _rackVuInterval = setInterval(_rackUpdateVu, _DRAW_INTERVAL_MS);
}
