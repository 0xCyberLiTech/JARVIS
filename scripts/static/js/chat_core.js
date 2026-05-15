// ══════════════════════════════════════════════════════════════
// CHAT CORE — sendMessage, SSE, modes, diagnostic, vision, Ollama poll
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-15.
//
// Bloc historiquement banni « DIAGNOSTIC SYSTÈME » mais qui contient
// en réalité tout l'infrastructure chat :
//  - Diagnostic système (_diagAddRow, runSysDiag, _diagBuildContext).
//  - Vision (visionPick/Load/ShowPreview/Clear, _visionImage).
//  - Mode switching (setModeSoc/General/Code/CodeReasoning,
//    _setMode, _applyModeProfile, _updateModeBtn, constantes
//    _MODE_SOC/GENERAL/CODE/CODE_REASONING + _MODE_MODELS).
//  - Polling Ollama (_pollOllamaStatus) + CR task polling.
//  - SSE chat streaming (_handleSseChunk, _sendChatSSE, _sseStopAnim).
//  - sendMessage — point d'entrée envoi chat utilisateur.
//  - Listeners top-level : paste (image upload chat), keydown
//    (Enter-to-send), input (autoresize textarea).
//  - Fichiers de correction (_fileCorrect*).
//
// Fichier .js classique (scope global). Chargé APRÈS jarvis_main.js
// et AVANT boot_init.js.

function _diagAddRow(rows, key, val, pct, warn) {
  const cls = pct !== null ? (pct > 90 ? 'crit' : pct > 70 ? 'warn' : '') : '';
  const barHtml = pct !== null ? `
    <div class="diag-bar-wrap">
      <span class="diag-val ${cls}">${val}</span>
      <div class="diag-bar"><div class="diag-bar-fill ${cls}" style="width:0%" data-w="${pct}%"></div></div>
    </div>` : `<span class="diag-val ${warn||''}">${val}</span>`;
  const row = document.createElement('div');
  row.className = 'diag-row';
  row.innerHTML = `<span class="diag-key">${key}</span>${barHtml}`;
  rows.appendChild(row);
  requestAnimationFrame(() => {
    row.classList.add('visible');
    const fill = row.querySelector('.diag-bar-fill');
    if (fill) setTimeout(() => fill.style.width = fill.dataset.w, 80);
  });
  return row;
}
function _diagAddSection(rows, title) {
  const s = document.createElement('div');
  s.className = 'diag-section-head';
  s.textContent = `// ${title}`;
  rows.appendChild(s);
}
async function runSysDiag() {
  const diagBtn = document.getElementById('btn-diag');
  if (diagBtn) diagBtn.classList.add('running');

  // Ajouter le message diagnostic dans le chat
  const bubble = addMessage('jarvis', '');
  bubble.innerHTML = `<div class="diag-card" id="diag-live">
    <div class="diag-title">◈ DIAGNOSTIC SYSTÈME</div>
    <div id="diag-rows"></div>
  </div>`;

  const rows = document.getElementById('diag-rows');
  const addRow     = (k, v, p, w) => _diagAddRow(rows, k, v, p, w);
  const addSection = t             => _diagAddSection(rows, t);

  try {
    // Fetch real data
    const r = await fetch('/api/sysdiag');
    const d = await r.json();

    addSection('PROCESSEUR');
    await _diagDelay(60); addRow('CPU CHARGE',  d.cpu_pct + ' %', d.cpu_pct);
    await _diagDelay(60); addRow('FRÉQUENCE',   d.cpu_freq + ' GHz', null);
    await _diagDelay(60); addRow('CŒURS / THREADS', `${d.cpu_cores} / ${d.cpu_threads}`, null);

    addSection('MÉMOIRE');
    await _diagDelay(60); addRow('RAM UTILISÉE', `${d.ram_used} / ${d.ram_total} GB`, d.ram_pct);
    await _diagDelay(60); addRow('DISPONIBLE',   `${(d.ram_total - d.ram_used).toFixed(1)} GB`, null);

    addSection('CARTE GRAPHIQUE');
    await _diagDelay(60); addRow('GPU',          d.gpu_name || 'N/A', null);
    await _diagDelay(60); addRow('GPU CHARGE',   d.gpu_pct + ' %', d.gpu_pct);
    await _diagDelay(60); addRow('VRAM',         `${d.vram_used} / ${d.vram_total} GB`, d.vram_total ? Math.round(d.vram_used/d.vram_total*100) : null);
    if (d.gpu_temp !== null) { await _diagDelay(60); addRow('TEMPÉRATURE', d.gpu_temp + ' °C', null, d.gpu_temp > 85 ? 'crit' : d.gpu_temp > 70 ? 'warn' : ''); }
    if (d.gpu_power !== null) { await _diagDelay(60); addRow('PUISSANCE', d.gpu_power + ' W', null); }

    addSection('STOCKAGE & RÉSEAU');
    await _diagDelay(60); addRow('DISQUE C:', `${d.disk_used} / ${d.disk_total} GB`, d.disk_pct);
    await _diagDelay(60); addRow('RÉSEAU ↑', d.net_sent + ' MB', null);
    await _diagDelay(60); addRow('RÉSEAU ↓', d.net_recv + ' MB', null);

    addSection('SWAP');
    await _diagDelay(60); addRow('SWAP UTILISÉ', `${d.swap_used} / ${d.swap_total} GB`, d.swap_pct);

    addSection('SYSTÈME & IA');
    await _diagDelay(60); addRow('UPTIME',     d.uptime, null);
    await _diagDelay(60); addRow('OS',         d.platform, null);
    await _diagDelay(60); addRow('LLM',        d.llm_model, null);
    await _diagDelay(60); addRow('PROVIDER',   d.llm_provider.toUpperCase(), null);
    await _diagDelay(60); addRow('VOIX',       d.llm_voice, null);
    await _diagDelay(60); addRow('MÉMOIRE',    `${d.memory_exchanges} / ${d.memory_limit} échanges`, Math.round(d.memory_exchanges/d.memory_limit*100));

    addSection('OLLAMA & LLM');
    await _diagDelay(60); addRow('OLLAMA',     d.ollama_ok ? 'EN LIGNE' : 'HORS LIGNE', null, d.ollama_ok ? '' : 'crit');
    await _diagDelay(60); addRow('LATENCE',    d.ollama_latency >= 0 ? d.ollama_latency + ' ms' : 'N/A', null);
    if (d.ollama_models && d.ollama_models.length) {
      await _diagDelay(60); addRow('MODÈLES',  d.ollama_models.join(', '), null);
    }

    addSection('DSP & IA AUDIO');
    await _diagDelay(60); addRow('MOTEUR DSP',     d.dsp_available ? 'SCIPY + NUMPY + MINIAUDIO' : 'NON DISPONIBLE', null, d.dsp_available ? '' : 'warn');
    await _diagDelay(60); addRow('DSP ACTIF',       d.dsp_enabled ? 'OUI' : 'NON', null);
    await _diagDelay(60); addRow('DEEPFILTERNET',   d.df_available ? 'DISPONIBLE' : 'ABSENT', null, d.df_available ? '' : 'warn');
    await _diagDelay(60); addRow('DF ACTIVÉ',       d.df_enabled ? 'OUI' : 'NON', null);
    if (d.df_available) {
      await _diagDelay(60); addRow('DF SAMPLE RATE', d.df_sr + ' Hz', null);
    }

    history.push({ role: 'user', content: _diagBuildContext(d) });
    history.push({ role: 'assistant', content: 'Diagnostic système complet reçu. Tous les paramètres sont intégrés dans mon contexte.' });

  } catch(e) {
    rows.innerHTML = '<div class="diag-row visible"><span class="diag-val crit">Erreur: '+_esc(e.message)+'</span></div>';
  }

  if (diagBtn) diagBtn.classList.remove('running');
}

function _diagDelay(ms) { return new Promise(r => setTimeout(r, ms)); }
function _diagBuildContext(d) {
  return `[DIAGNOSTIC SYSTÈME — ${new Date().toLocaleTimeString('fr-FR')}]
CPU: ${d.cpu_pct}% @ ${d.cpu_freq}GHz (${d.cpu_cores}c/${d.cpu_threads}t)${d.cpu_temp != null ? ` ${d.cpu_temp}°C` : ''}
RAM: ${d.ram_used}/${d.ram_total}GB (${d.ram_pct}%) | SWAP: ${d.swap_used}/${d.swap_total}GB
GPU: ${d.gpu_name} — charge ${d.gpu_pct}% — VRAM ${d.vram_used}/${d.vram_total}GB${d.gpu_temp !== null ? ` — ${d.gpu_temp}°C` : ''}${d.gpu_power ? ` — ${d.gpu_power}W` : ''}
Disque C: ${d.disk_used}/${d.disk_total}GB (${d.disk_pct}%)
Réseau: ↑${d.net_sent}MB ↓${d.net_recv}MB | Uptime: ${d.uptime}
OS: ${d.platform} — ${d.hostname}
LLM: ${d.llm_model} (${d.llm_provider}) | Voix: ${d.llm_voice} | Mémoire: ${d.memory_exchanges}/${d.memory_limit}
Ollama: ${d.ollama_ok ? 'EN LIGNE '+d.ollama_latency+'ms' : 'HORS LIGNE'} | Modèles: ${(d.ollama_models||[]).join(', ')}
DSP: ${d.dsp_available?'disponible':'absent'} ${d.dsp_enabled?'(actif)':'(inactif)'} | DeepFilterNet: ${d.df_available?'disponible':'absent'} ${d.df_enabled?'(actif)':'(inactif)'}`;
}

// ── Model role popup ──────────────────────────────────────────
(function() {
  const el = document.createElement('div');
  el.id = 'model-role-popup';
  document.body.appendChild(el);
})();
function _showModelPopup(anchor, text) {
  const pop = document.getElementById('model-role-popup');
  if (!pop) return;
  pop.textContent = text;
  _disp(pop, true, 'block');
  const r = anchor.getBoundingClientRect();
  const pw = 260, ph = 50;
  let left = r.left - pw - 6;
  if (left < 4) left = r.right + 6;
  let top = r.top - ph / 2;
  if (top < 4) top = 4;
  pop.style.left = left + 'px';
  pop.style.top = top + 'px';
}
function _hideModelPopup() {
  const pop = document.getElementById('model-role-popup');
  _disp(pop, false);
}

// ── Vision LLaVA ──────────────────────────────────────────────
var _visionImage = null;
function visionPick() { document.getElementById('vision-file-input').click(); }
function visionLoadFile(inp) {
  var f = inp.files[0]; if (!f) return;
  var r = new FileReader();
  r.onload = function(e) { _visionImage = e.target.result; visionShowPreview(_visionImage); };
  r.readAsDataURL(f);
}
function visionShowPreview(dataUrl) {
  var w = document.getElementById('vision-preview-wrap');
  var i = document.getElementById('vision-preview-img');
  if (w && i) { i.src = dataUrl; _disp(w, true, 'flex'); }
  var btn = document.getElementById('btn-vision');
  if (btn) btn.classList.add('btn-vision--active');
}
function visionClear() {
  _visionImage = null;
  var w = document.getElementById('vision-preview-wrap'); _disp(w, false);
  var fi = document.getElementById('vision-file-input'); if (fi) fi.value = '';
  var btn = document.getElementById('btn-vision');
  if (btn) btn.classList.remove('btn-vision--active');
}
// ── Mode LLM : SOC / GÉNÉRAL / CODE ──────────────────────────
const _MODE_SOC            = 'Phi4 — Analyse Avancée';
const _MODE_GENERAL        = 'Gemma4 — Conversation Fluide';
const _MODE_CODE           = '◆ CODE — Qwen2.5-Coder';
const _MODE_CODE_REASONING = '⬡ CODE REASONING — qwen3:8b';
const _MODE_MODELS  = { soc: 'phi4:14b', general: 'gemma4:latest', code: 'qwen2.5-coder:14b', code_reasoning: 'qwen3:8b' };
const _LS_MODE           = 'jarvis_mode';
const _LS_PROMPT_PROFILE = 'jarvis_active_prompt_profile';
// Mode toujours SOC au démarrage — localStorage ignoré (code/general se choisissent manuellement)
var _jarvisMode = 'soc';
var _devWs      = null;
var _devXterm   = null;
var _devFit     = null;
var _devHostKey = 'dev1';

function _devSetStatus(txt, cls) {
  var el = document.getElementById('dev-term-status');
  if (!el) return;
  el.textContent = txt;
  el.className = cls || '';
}

async function _setMode(mode) {
  _jarvisMode = mode;
  localStorage.setItem(_LS_MODE, _jarvisMode);
  await _applyModeProfile(_jarvisMode);
  await fetch('/api/mode', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({mode: _jarvisMode})
  }).catch(e => _jwarn('[jarvis] _setMode /api/mode:', e));
  _updateModeBtn();
  setTimeout(_refreshVramNow, 800);
}

async function setModeSoc()              { await _setMode('soc'); }
async function setModeGeneral()          { await _setMode('general'); }
async function setModeCode()             { await _setMode('code'); devTerminalOpen(); }
async function setModeCodeReasoning()    { await _setMode('code_reasoning'); }

async function _applyModeProfile(mode) {
  // Annonce vocale immédiate — indépendante du chargement du profil
  if (mode === 'code') queueSpeech('Mode code activé.');
  else if (mode === 'code_reasoning') queueSpeech('Mode code reasoning activé. Qwen 3 huit B.');
  else if (mode === 'general') queueSpeech('Mode général activé.');
  else queueSpeech('Mode S O C activé.');
  const profileName = mode === 'general' ? _MODE_GENERAL
    : mode === 'code' ? _MODE_CODE
    : mode === 'code_reasoning' ? _MODE_CODE_REASONING
    : _MODE_SOC;
  try {
    const profiles = await _fetchPromptProfiles();
    const content = profiles[profileName] && profiles[profileName].content;
    if (!content) return;
    await fetch('/api/llm-params', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({system_prompt: content})
    });
    const ta = document.getElementById('system-prompt-editor');
    if (ta) ta.value = content;
    _updateActivePromptBadge(profileName);
    loadPromptProfiles();
    // Synchronise le sélecteur de modèle avec le mode
    const modeModel = _MODE_MODELS[mode];
    if (modeModel) {
      const sel = document.getElementById('model-select');
      if (sel) sel.value = modeModel;
      document.querySelectorAll('#model-cards-grid .voice-card').forEach(c => {
        c.classList.toggle('active', c.dataset.modelId === modeModel);
      });
      _updateHeaderLLM();
    }
    addMessage('jarvis', `Mode ${profileName} activé.`);
  } catch(e) { _jwarn('[jarvis] _applyModeProfile:', e); }
}

// ── État pipeline "lis + corrige" du chat (file correction) ──
// Déplacées ici depuis le bloc Terminal CODE extrait (chantier 2026-05-14) :
// utilisées par _handleSseChunk, pas par le Terminal CODE.
var _fileCorrectMode = false;         // mode "lis+corrige"
var _fileCorrectMulti = false;        // mode multi-fichiers
var _fileCorrectFilesCount = 0;       // nombre de fichiers attendus
var _fileCorrectHeaderAdded = false;  // header "VERSIONS CORRIGÉES" déjà ajouté

function _updateModeBtn() {
  const modeEl = document.getElementById('m-llm-mode');
  const btnSoc = document.getElementById('btn-mode-soc');
  const btnGen = document.getElementById('btn-mode-general');
  const btnCode= document.getElementById('btn-mode-code');
  if (btnSoc)  { btnSoc.classList.toggle('mode-active-soc',     _jarvisMode === 'soc'); }
  if (btnGen)  { btnGen.classList.toggle('mode-active-general',  _jarvisMode === 'general'); }
  if (btnCode) { btnCode.classList.toggle('mode-active-code',    _jarvisMode === 'code'); }
  const btnCR = document.getElementById('btn-mode-code-reasoning');
  if (btnCR)   { btnCR.classList.toggle('mode-active-code',      _jarvisMode === 'code_reasoning'); }
  if (modeEl)  {
    modeEl.textContent = _jarvisMode === 'general'        ? 'GÉNÉRAL · gemma4'
      : _jarvisMode === 'code'                            ? 'CODE · qwen2.5-coder'
      : _jarvisMode === 'code_reasoning'                  ? 'C·R · qwen3'
      : 'SOC · phi4';
  }
  // Highlight le modèle que JARVIS utilisera — grise les autres même si chargés Ollama
  const jarvisTarget = _jarvisMode === 'general'       ? 'gemma4:latest'
    : _jarvisMode === 'code'                           ? 'qwen2.5-coder:14b'
    : _jarvisMode === 'code_reasoning'                 ? 'qwen3:8b'
    : null; // null = modèle Ollama actif (SOC → phi4:14b)
  document.querySelectorAll('.voice-card[data-model-id]').forEach(c => {
    const mid = c.dataset.modelId || '';
    const isTarget = jarvisTarget ? mid === jarvisTarget : c.classList.contains('active');
    c.classList.toggle('voice-card-jarvis', isTarget);
    c.classList.toggle('voice-card-idle', !isTarget && c.classList.contains('active'));
  });
}

function _pollOllamaStatus() {
  fetch('/api/ollama-status').then(r => r.json()).then(d => {
    const dot = document.getElementById('ollama-dot');
    const lbl = document.getElementById('m-ollama-status');
    const cls = d.running ? 'ollama-on' : 'ollama-off';
    const txt = d.running ? 'ACTIF' : 'ARRÊTÉ';
    if (dot) dot.className = 'ollama-dot ' + cls;
    if (lbl) lbl.innerHTML = `<span class="ollama-dot ${cls}"></span>${txt}`;
    // Indicateur circuit breaker dans le header (vert = closed, orange = half_open, rouge = open)
    const cb = document.getElementById('ollama-circuit');
    const cbLabel = document.getElementById('ollama-label');
    if (cb && d.state) {
      cb.className = 'ollama-circuit cb-' + d.state;
      if (cbLabel) cbLabel.className = 'ollama-label cb-' + d.state;
      const titles = {
        closed:    'Circuit Ollama fermé — fonctionnement normal',
        half_open: 'Circuit Ollama semi-ouvert — test recovery',
        open:     `Circuit Ollama OUVERT — Ollama indisponible (retry dans ${d.retry_in_s||0}s)`,
      };
      cb.title = titles[d.state] || 'État circuit breaker Ollama';
      if (cbLabel) cbLabel.title = cb.title;
    }
  }).catch(e => _jwarn('[jarvis] _pollOllamaStatus:', e));
}

// → _jarvisInit()

document.addEventListener('paste', function(e) {
  var items = (e.clipboardData || e.originalEvent.clipboardData || {}).items || [];
  for (var i = 0; i < items.length; i++) {
    if (items[i].type.indexOf('image') !== -1) {
      var blob = items[i].getAsFile();
      var rdr = new FileReader();
      rdr.onload = function(ev) { _visionImage = ev.target.result; visionShowPreview(_visionImage); };
      rdr.readAsDataURL(blob);
      break;
    }
  }
});

async function _pollCRTask(taskId, bubble) {
  const _crStart = Date.now();
  while (true) {
    try {
      const r = await fetch('/api/cr-poll/' + taskId);
      const d = await r.json();
      if (d.text) {
        const sec = Math.round((Date.now() - _crStart) / 1000);
        const t = sec < 60 ? sec + 's' : Math.floor(sec / 60) + 'm ' + (sec % 60) + 's';
        const disp = d.text.replace(/\b(\d{1,3})-(\d{1,3})-(\d{1,3})-(\d{1,3})\b/g, '$1.$2.$3.$4');
        const suffix = d.status === 'done' ? '' : '<span class="cr-task-elapsed"> (' + t + ')</span><span class="cursor"></span>';
        bubble.innerHTML = renderMarkdown(disp) + suffix;
        if (d.status === 'done') highlightCode(bubble);
        document.getElementById('chat-messages').scrollTop = 999999;
      }
      if (d.status === 'done' || d.status === 'error') return d.text || '';
    } catch(e) { _jwarn('[CR] poll:', e); }
    await new Promise(res => setTimeout(res, _CR_POLL_MS));
  }
}

function _sseStopAnim(hexTimer, ring1, ring2) {
  clearInterval(hexTimer);
  if (ring1) ring1.style.animationDuration = '';
  if (ring2) ring2.style.animationDuration = '';
}

async function _handleSseChunk(ctx, chunk) {
  const { bubble, hexTimer, ring1, ring2 } = ctx;
  if (chunk.type === 'token') {
    if (ctx.firstToken) { ctx.firstToken = false; _sseStopAnim(hexTimer, ring1, ring2); }
    if (_fileCorrectMulti && !_fileCorrectHeaderAdded) { _fileCorrectHeaderAdded = true; ctx.fullText += '## ✅ VERSIONS CORRIGÉES\n\n'; }
    ctx.fullText += chunk.token;
    if (!ctx.fullText && chunk.done && bubble.querySelector('.sshf-panel')) return 'break';
    const disp = ctx.fullText.replace(/\b(\d{1,3})-(\d{1,3})-(\d{1,3})-(\d{1,3})\b/g, '$1.$2.$3.$4');
    const vdesc = bubble.dataset.visionDesc ? '<div class="vision-desc-block"><span class="vision-desc-label">◈ gemma4</span><span class="vision-desc-text">'+bubble.dataset.visionDesc.replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</span></div>' : '';
    bubble.innerHTML = vdesc + renderMarkdown(disp) + (chunk.done ? '' : '<span class="cursor"></span>');
    if (chunk.done) highlightCode(bubble);
    document.getElementById('chat-messages').scrollTop = 999999;
  } else if (chunk.type === 'cr_task') {
    _sseStopAnim(hexTimer, ring1, ring2); ctx.firstToken = false;
    ctx.fullText = await _pollCRTask(chunk.task_id, bubble);
  } else if (chunk.type === 'vision_desc') {
    bubble.dataset.visionDesc = chunk.text;
    bubble.innerHTML = '<div class="vision-desc-block"><span class="vision-desc-label">◈ gemma4</span><span class="vision-desc-text">'+chunk.text.replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</span></div><span class="cursor"></span>';
    document.getElementById('chat-messages').scrollTop = 999999;
  } else if (chunk.type === 'speak')       { queueSpeech(chunk.text);
  } else if (chunk.type === 'tool')        { addToolEvent('EXÉCUTION', chunk.name, JSON.stringify(chunk.args));
  } else if (chunk.type === 'tool_result') { addToolEvent('RÉSULTAT', chunk.name, chunk.result);
  } else if (chunk.type === 'open_dev_terminal') {
    if (ctx.firstToken) { ctx.firstToken = false; _sseStopAnim(hexTimer, ring1, ring2); }
    devTerminalOpen('dev1', 'srv-dev-1', 'root');
  } else if (chunk.type === 'open_ssh_terminal') {
    if (ctx.firstToken) { ctx.firstToken = false; _sseStopAnim(hexTimer, ring1, ring2); }
    devTerminalOpen(chunk.host, chunk.label, chunk.user || 'root');
  } else if (chunk.type === 'file_correct_fix') {
    var cards = bubble.querySelectorAll('.code-card');
    if (cards.length > 0) {
      var idxMatch = (cards[cards.length-1].getAttribute('onclick')||'').match(/openCodeModal\((\d+)\)/);
      if (idxMatch && _codeStore[parseInt(idxMatch[1])]) _codeStore[parseInt(idxMatch[1])].code = chunk.code;
    }
    var warnDiv = document.createElement('div');
    warnDiv.className = 'fc-validation-warning';
    warnDiv.innerHTML = '<span class="fc-warn-icon">⚠</span><strong>Auto-correction</strong> · '
      + chunk.changes.length + ' faux positif(s) LLM restauré(s) : '
      + chunk.changes.map(function(c) { return '<code>' + _esc(c) + '</code>'; }).join(' · ');
    bubble.appendChild(warnDiv);
    document.getElementById('chat-messages').scrollTop = 999999;
  } else if (chunk.type === 'file_correct_start') {
    _fileCorrectMode = true; _fileCorrectMulti = chunk.multi || false;
    _fileCorrectFilesCount = chunk.count || 1; _fileCorrectHeaderAdded = false;
    if (_fileCorrectMulti) ctx.fullText = '';
  } else if (chunk.type === 'ssh_file') {
    if (ctx.firstToken) { ctx.firstToken = false; _sseStopAnim(hexTimer, ring1, ring2); }
    if (_fileCorrectMode) {
      ctx.fullText += _fileCorrectMulti
        ? '## ◈ ORIGINAL · ' + chunk.path + '\n\n```\n' + (chunk.content||'') + '\n```\n\n'
        : '## ◈ FICHIER ORIGINAL — ' + chunk.vm.toUpperCase() + ' · ' + chunk.path + '\n\n```\n' + (chunk.content||'') + '\n```\n\n## ✅ VERSION CORRIGÉE\n\n';
      bubble.innerHTML = renderMarkdown(ctx.fullText) + '<span class="cursor"></span>';
    } else {
      bubble.innerHTML = _renderSshFile(chunk.vm, chunk.path, chunk.content, chunk.action);
      ctx.fullText += 'Fichier lu : ' + chunk.path + ' sur ' + chunk.vm + '\n```\n' + (chunk.content||'') + '\n```';
    }
    document.getElementById('chat-messages').scrollTop = 999999;
  }
}

async function _sendChatSSE({ bubble, text, visionImg, ring1, ring2, hexTimer, abortCtrl }) {
  const ctx = { bubble, hexTimer, ring1, ring2, fullText: '', firstToken: true };
  try {
    const resp = visionImg
      ? await fetch('/api/vision', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({image_b64:visionImg, prompt:text, pipeline:true}), signal:abortCtrl?.signal})
      : await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(await _buildChatPayload(history)), signal:abortCtrl?.signal});
    const reader = resp.body.getReader(), decoder = new TextDecoder();
    let buf = '';
    outer: while (true) {
      const {done, value} = await reader.read(); if (done) break;
      buf += decoder.decode(value, {stream:true});
      const lines = buf.split('\n'); buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        if (await _handleSseChunk(ctx, JSON.parse(line.slice(5).trim())) === 'break') break outer;
      }
    }
  } catch(e) {
    if (e.name !== 'AbortError') bubble.innerHTML = '<span class="c-red">Erreur de connexion a JARVIS.</span>';
  }
  return ctx.fullText;
}

function _renderSshFile(vm, path, content, action) {
  const lines = content ? content.split('\n') : [];
  const ext = (path.split('.').pop() || '').toLowerCase();
  const langMap = {conf:'CONF',cfg:'CONF',sh:'BASH',py:'PYTHON',json:'JSON',yaml:'YAML',yml:'YAML',js:'JS',html:'HTML',css:'CSS',txt:'TEXT',log:'LOG'};
  const lang = langMap[ext] || 'TEXT';
  const linesHtml = lines.map(function(line, i) {
    return '<div class="sshf-line"><span class="sshf-num">' + String(i+1).padStart(2,'0') + '</span><span class="sshf-content">' + _esc(line || ' ') + '</span></div>';
  }).join('');
  let opsHtml = '';
  if (action === 'edit' || action === 'add') {
    opsHtml = '<div class="sshf-ops"><div class="sshf-ops-title">◈ OPÉRATIONS DISPONIBLES</div>' +
      '<div class="sshf-op"><span class="sshf-op-key">AJOUTER</span><code>ajoute \'ta ligne\' dans ' + _esc(path) + ' sur ' + _esc(vm) + '</code></div>' +
      '<div class="sshf-op"><span class="sshf-op-key">REMPLACER</span><code>remplace \'ancienne\' par \'nouvelle\' dans ' + _esc(path) + ' sur ' + _esc(vm) + '</code></div>' +
      '<div class="sshf-op"><span class="sshf-op-key">SUPPRIMER</span><code>supprime ligne contenant \'motif\' dans ' + _esc(path) + ' sur ' + _esc(vm) + '</code></div>' +
      '</div>';
  }
  return '<div class="sshf-panel">' +
    '<div class="sshf-header">' +
      '<span class="sshf-icon">◈</span>' +
      '<span class="sshf-vm">SSH → ' + _esc(vm).toUpperCase() + '</span>' +
      '<span class="sshf-sep">//</span>' +
      '<span class="sshf-path">' + _esc(path) + '</span>' +
      '<span class="sshf-meta">' + lines.length + ' L · ' + lang + '</span>' +
    '</div>' +
    '<div class="sshf-body">' + linesHtml + '</div>' +
    opsHtml + '</div>';
}

async function sendMessage() {
  if (busy) return;
  const input = document.getElementById('user-input');
  const text  = input.value.trim();
  if (!text && !_visionImage) return;
  input.value = '';
  input.style.height = 'auto';
  busy = true;
  _chatAbortController = new AbortController();
  _setStopBtn(true); _setAllReplayBusy(true);
  document.getElementById('btn-send').disabled = true;
  document.getElementById('m-ai-status').textContent = 'THINKING...';
  document.getElementById('m-ai-status').className = 'stat-val c-yellow';
  const _userDisplay = text || '📷 Analyse image';
  history.push({role:'user', content:_userDisplay});
  addMessage('user', _userDisplay.replace(/^\[VOCAL\]\s*/i, ''));
  const bubble = addMessage('jarvis', '');
  bubble.innerHTML = `<div class="jarvis-thinking"><div class="thinking-header"><span class="thinking-label">// ANALYSE EN COURS</span><div class="thinking-dots"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div></div><div class="thinking-scan"></div><div class="thinking-hex" id="thinking-hex-stream">00 FF A3 7C 1B E0 44 91 D2 6F 38 B5</div></div>`;
  const _hexTimer = setInterval(() => {
    const el = document.getElementById('thinking-hex-stream');
    if (el) el.textContent = Array.from({length:12}, () => Math.floor(Math.random()*256).toString(16).padStart(2,'0').toUpperCase()).join(' ');
  }, 120);
  const ring1 = document.querySelector('.reactor-ring-1'), ring2 = document.querySelector('.reactor-ring-2');
  if (ring1) ring1.style.animationDuration = '1.5s'; if (ring2) ring2.style.animationDuration = '1s';
  const _visionImg = _visionImage; if (_visionImg) visionClear();
  const fullText = await _sendChatSSE({ bubble, text, visionImg: _visionImg, ring1, ring2, hexTimer: _hexTimer, abortCtrl: _chatAbortController });
  _fileCorrectMode = false; _fileCorrectMulti = false; _fileCorrectHeaderAdded = false;
  clearInterval(_hexTimer);
  if (ring1) ring1.style.animationDuration = ''; if (ring2) ring2.style.animationDuration = '';
  _chatAbortController = null; _setStopBtn(false);
  if (fullText) {
    history.push({role:'assistant', content:fullText});
    _lastJarvisText = fullText.replace(/<[^>]+>/g,'').trim();
    const msgDiv = bubble?.closest?.('.msg'); if (msgDiv) msgDiv.dataset.text = _lastJarvisText;
  }
  await saveMemory();
  busy = false; _setAllReplayBusy(false);
  document.getElementById('btn-send').disabled = false;
  document.getElementById('m-ai-status').textContent = 'ONLINE';
  document.getElementById('m-ai-status').className = 'stat-val c-green';
}

document.getElementById('user-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
document.getElementById('user-input').addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

