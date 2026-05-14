// ══════════════════════════════════════════════════════════════
// SETTINGS LLM — Profils & paramètres LLM (RTX 5080)
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Onglet Settings — paramètres LLM (temp/num_ctx/num_predict), profils
// prompt, system prompt, faits persistants, mémoire long terme, base de
// connaissances RAG. Fichier .js classique (scope global). Chargé APRÈS
// jarvis_main.js.


const LLM_PROFILES = {
  rapide: {
    label: 'RAPIDE',
    params: { temperature: 0.5, top_p: 0.8, top_k: 20, num_predict: 512, repeat_penalty: 1.1 },
    desc: 'Réponses courtes et rapides — idéal pour les questions simples'
  },
  equilibre: {
    label: 'ÉQUILIBRÉ',
    params: { temperature: 0.7, top_p: 0.9, top_k: 40, num_predict: 1024, repeat_penalty: 1.1 },
    desc: 'Usage général — profil par défaut'
  },
  code: {
    label: 'CODE',
    params: { temperature: 0.15, top_p: 0.95, top_k: 15, num_predict: 4096, repeat_penalty: 1.2 },
    desc: 'Génération de code précise — réponses longues, très déterministe'
  },
  creatif: {
    label: 'CRÉATIF',
    params: { temperature: 1.2, top_p: 0.95, top_k: 60, num_predict: 2048, repeat_penalty: 1.05 },
    desc: 'Rédaction créative — imagination et diversité maximales'
  },
  precis: {
    label: 'PRÉCIS',
    params: { temperature: 0.2, top_p: 0.85, top_k: 20, num_predict: 2048, repeat_penalty: 1.15 },
    desc: 'Réponses factuelles — mode quasi-déterministe pour les faits'
  },
  rtx5080: {
    label: 'RTX 5080 MAX',
    params: { temperature: 0.72, top_p: 0.92, top_k: 50, num_predict: 4096, repeat_penalty: 1.08 },
    desc: 'VRAM 16 GB exploitée au maximum — qualité optimale pour RTX 5080'
  },
};

let _activeProfile = 'equilibre';
let _activePromptProfile = localStorage.getItem(_LS_PROMPT_PROFILE) || null;

function _updateActivePromptBadge(name) {
  _activePromptProfile = name;
  if (name) localStorage.setItem(_LS_PROMPT_PROFILE, name);
  else localStorage.removeItem(_LS_PROMPT_PROFILE);
  const badge = document.getElementById('active-prompt-profile-badge');
  if (!badge) return;
  if (name) {
    badge.textContent = '◈ ' + name.toUpperCase();
    badge.classList.add('profile-badge-active');
    badge.classList.remove('profile-badge-dim');
  } else {
    badge.textContent = '◈ PERSONNALISÉ';
    badge.classList.add('profile-badge-dim');
    badge.classList.remove('profile-badge-active');
  }
}
let _llmDefaults = {};

async function loadLlmParams() {
  try {
    const d = await _fetchLlmParams();
    _llmDefaults = d.defaults || {};
    const p = d.params || {};
    for (const [k, v] of Object.entries(p)) {
      const slider = document.getElementById('s-' + k);
      const valEl  = document.getElementById('v-' + k);
      if (slider) slider.value = v;
      if (valEl)  valEl.textContent = Number.isInteger(v) ? v : v.toFixed(2);
    }
    const ta = document.getElementById('system-prompt-editor');
    if (ta && d.system_prompt) ta.value = d.system_prompt;
    _updateActivePromptBadge(_activePromptProfile);
  } catch(e) { _jwarn('[JARVIS] loadPromptProfiles error', e); }
}

function updateSliderVal(key, val) {
  const el = document.getElementById('v-' + key);
  if (!el) return;
  el.textContent = ['top_k','num_predict','num_ctx'].includes(key)
    ? Math.round(val)
    : parseFloat(val).toFixed(2);
  updateImpactBars();
}

async function applyLlmParams() {
  const keys = ['temperature','top_p','top_k','num_predict','repeat_penalty','num_ctx'];
  const params = {};
  for (const k of keys) {
    const s = document.getElementById('s-' + k);
    if (s) params[k] = parseFloat(s.value);
  }
  try {
    await fetch('/api/llm-params', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({params})
    });
    const st = document.getElementById('stg-status');
    if (st) { st.textContent = '✓ Paramètres appliqués'; _stColor(st,'ok'); _clearAfter(st, 3000); }
  } catch(e) { _jwarn('[jarvis] applyLlmParams:', e); }
}

function resetLlmParams() {
  for (const [k, v] of Object.entries(_llmDefaults)) {
    const s = document.getElementById('s-' + k);
    if (s) { s.value = v; updateSliderVal(k, v); }
  }
  applyLlmParams();
}

// Préréglages latence : RAPIDE / ÉQUILIBRÉ / QUALITÉ
function applyLatencyPreset(preset) {
  const PRESETS = {
    fast:     { temperature:0.5,  top_p:0.85, top_k:20, num_predict:512,  repeat_penalty:1.1,  num_ctx:1024 },
    balanced: { temperature:0.7,  top_p:0.9,  top_k:40, num_predict:1024, repeat_penalty:1.1,  num_ctx:2048 },
    quality:  { temperature:0.82, top_p:0.95, top_k:60, num_predict:2048, repeat_penalty:1.05, num_ctx:4096 },
  };
  const p = PRESETS[preset]; if (!p) return;
  for (const [k, v] of Object.entries(p)) {
    const s = document.getElementById('s-' + k);
    if (s) { s.value = v; updateSliderVal(k, v); }
  }
  applyLlmParams();
  const labels = {fast:'⚡ RAPIDE', balanced:'◈ ÉQUILIBRÉ', quality:'◉ QUALITÉ'};
  const st = document.getElementById('stg-status');
  if (st) { st.textContent = labels[preset]+' appliqué'; _stColor(st,'info'); _clearAfter(st, 2500); }
}

async function saveSystemPrompt() {
  const ta = document.getElementById('system-prompt-editor');
  if (!ta) return;
  try {
    await fetch('/api/llm-params', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({system_prompt: ta.value})
    });
    _promptStatus('✓ Prompt sauvegardé sur disque', 'ok');
  } catch(e) { _promptStatus('✗ Erreur sauvegarde', 'err'); }
}

function _promptStatus(msg, cls) {
  const st = document.getElementById('stg-prompt-status');
  if (!st) return;
  _stColor(st, cls); st.textContent = msg;
  _clearAfter(st, 3000);
}

async function reloadSystemPrompt() {
  try {
    const d = await _fetchLlmParams();
    const ta = document.getElementById('system-prompt-editor');
    if (ta && d.system_prompt !== undefined) {
      ta.value = d.system_prompt;
      _promptStatus('⟳ Rechargé depuis le disque', 'info');
    }
  } catch(e) { _jwarn('[jarvis] reloadSystemPrompt:', e); }
}

async function resetSystemPrompt() {
  if (!confirm('Remettre le prompt système par défaut ?')) return;
  try {
    const d = await fetch('/api/llm-params/reset-prompt', {method:'POST'}).then(r=>r.json());
    const ta = document.getElementById('system-prompt-editor');
    if (ta && d.system_prompt) { ta.value = d.system_prompt; }
    _promptStatus('↺ Prompt remis à zéro', 'load');
  } catch(e) { _jwarn('[jarvis] resetSystemPrompt:', e); }
}

// ── Gestion des profils prompt ────────────────────────────────
async function loadSecurityLog() {
  const list = document.getElementById('sec-events-list');
  const ctr  = document.getElementById('sec-counters');
  try {
    const d = await fetch('/api/security').then(r => r.json());
    const lvlColors = { hard: '#ff4444bb', args: '#ffaa00bb', terminal: '#ff6600bb' }; // NDT-ALPHA-EXEMPT: valeurs avec canal alpha non exprimables en var()
    const lvlLabels = { hard: 'INJECTION', args: 'ARGS', terminal: 'TERMINAL' };
    if (ctr) {
      const parts = Object.entries(d.by_level).filter(([,v])=>v>0).map(([k,v])=>`${lvlLabels[k]||k}:${v}`);
      ctr.textContent = `TOTAL:${d.total}` + (parts.length ? ' · ' + parts.join(' · ') : '');
    }
    if (!list) return;
    if (!d.last || d.last.length === 0) {
      list.innerHTML = '<span class="sec-empty-msg">Aucun événement depuis le démarrage</span>';
      return;
    }
    list.innerHTML = d.last.map(e => {
      const col = lvlColors[e.level] || '#00cfff66';
      const lbl = lvlLabels[e.level] || e.level.toUpperCase();
      const ts  = e.ts ? e.ts.split('T')[1]?.slice(0,8) || e.ts : '—';
      const snip = (e.snippet||'').slice(0,80).replace(/</g,'&lt;').replace(/>/g,'&gt;');
      return `<div class="sec-event-row" style="--ec:${col}">
        <span class="sec-event-ts">${ts}</span>
        <span class="sec-event-lbl">${lbl}</span>
        <span class="sec-event-snip">${snip||e.pattern||'—'}</span>
      </div>`;
    }).join('');
  } catch(e) {
    if (list) list.innerHTML = '<span class="sec-error-msg">Erreur de chargement</span>';
  }
}

async function clearSecurityLog() {
  try {
    await fetch('/api/security/clear', {method:'POST'});
    loadSecurityLog();
  } catch(e) { _jwarn('[jarvis] clearSecurityLog:', e); }
}

// ── Faits persistants ────────────────────────────────────────────────────────
async function loadFacts() {
  var list = document.getElementById('facts-list');
  var ctr  = document.getElementById('facts-count');
  if (!list) return;
  try {
    var d = await _fetchFacts();
    var facts = d.facts || [];
    if (ctr) ctr.textContent = facts.length + ' fait' + (facts.length !== 1 ? 's' : '');
    if (facts.length === 0) { list.innerHTML = '<span class="stg-profiles-empty">Aucun fait enregistré</span>'; return; }
    list.innerHTML = facts.map(function(f, i) {
      return '<div class="stg-fact-row">'
        + '<span class="stg-fact-text">' + f.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</span>'
        + '<button class="stg-btn stg-btn-reset stg-btn-xs" data-action="deleteFact" data-args=\'[' + i + ']\'>✕</button>'
        + '</div>';
    }).join('');
  } catch(e) { list.innerHTML = '<span class="sec-error-msg">Erreur de chargement</span>'; }
}

async function addFact() {
  var input  = document.getElementById('fact-new-input');
  var status = document.getElementById('facts-status');
  var text   = input ? input.value.trim() : '';
  if (!text) return;
  try {
    var d = await _fetchFacts();
    var facts = (d.facts || []).concat([text]);
    await fetch('/api/facts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({facts:facts})});
    if (input) input.value = '';
    if (status) { status.textContent = 'Fait ajouté.'; _clearAfter(status, 2000); }
    loadFacts();
  } catch(e) { if (status) status.textContent = 'Erreur.'; }
}

async function deleteFact(idx) {
  try {
    var d = await _fetchFacts();
    var facts = (d.facts || []).filter(function(_, i){ return i !== idx; });
    await fetch('/api/facts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({facts:facts})});
    loadFacts();
  } catch(e) { _jwarn('[jarvis] deleteFact:', e); }
}

// ── Mémoire long terme (résumés) ─────────────────────────────────────────────
async function loadMemorySummary() {
  var list = document.getElementById('memory-summary-list');
  if (!list) return;
  try {
    var d = await fetch('/api/memory-summary').then(function(r){ return r.json(); });
    var summaries = d.summaries || [];
    if (summaries.length === 0) {
      list.innerHTML = '<span class="stg-profiles-empty">Aucun résumé — se génère automatiquement quand l\'historique dépasse 60 messages</span>';
      return;
    }
    list.innerHTML = summaries.map(function(s) {
      return '<div class="stg-summary-entry">'
        + '<div class="stg-summary-date">' + (s.date || '?') + '</div>'
        + '<div class="stg-summary-content">' + (s.content || '').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>') + '</div>'
        + '</div>';
    }).join('');
  } catch(e) { list.innerHTML = '<span class="sec-error-msg">Erreur de chargement</span>'; }
}

async function clearMemorySummary() {
  if (!confirm('Effacer tous les résumés de mémoire long terme ?')) return;
  try {
    await fetch('/api/memory-summary', {method:'DELETE'});
    loadMemorySummary();
  } catch(e) { _jwarn('[jarvis] clearMemorySummary:', e); }
}

// ── RAG — Base de connaissances ──────────────────────────────────────────────
async function loadRagStatus() {
  var ctr    = document.getElementById('rag-chunks-count');
  var srcDiv = document.getElementById('rag-sources-list');
  try {
    var d = await fetch('/api/rag/status').then(function(r){ return r.json(); });
    if (ctr) ctr.textContent = d.chunks + ' chunk' + (d.chunks !== 1 ? 's' : '') + ' indexé' + (d.chunks !== 1 ? 's' : '');
    if (srcDiv) {
      if (!d.sources || d.sources.length === 0) {
        srcDiv.innerHTML = '<span class="stg-profiles-empty">Index vide — aucune source indexée · modèle : ' + d.embed_model + '</span>';
      } else {
        srcDiv.innerHTML = '<div class="stg-section-lbl-dim">SOURCES</div>'
          + d.sources.map(function(s){ return '<div class="stg-rag-source">◈ ' + s.replace(/</g,'&lt;') + '</div>'; }).join('');
      }
    }
  } catch(e) { if (ctr) ctr.textContent = 'Non disponible'; }
}

async function ragIndexFile() {
  var input  = document.getElementById('rag-file-path');
  var status = document.getElementById('rag-status');
  var path   = input ? input.value.trim() : '';
  if (!path) return;
  if (status) status.textContent = 'Indexation en cours...';
  try {
    var d = await fetch('/api/rag/index-file', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path:path})}).then(function(r){ return r.json(); });
    if (d.error) { if (status) status.textContent = 'Erreur : ' + d.error; }
    else {
      if (input) input.value = '';
      if (status) { status.textContent = '✓ ' + d.chunks_added + ' chunks ajoutés — ' + d.file; _clearAfter(status, 3000); }
      loadRagStatus();
    }
  } catch(e) { if (status) status.textContent = 'Erreur réseau.'; }
}

async function ragAddNote() {
  var ta     = document.getElementById('rag-note-input');
  var status = document.getElementById('rag-status');
  var content = ta ? ta.value.trim() : '';
  if (!content) return;
  if (status) status.textContent = 'Mémorisation en cours...';
  try {
    var d = await fetch('/api/rag/note', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({content:content})}).then(function(r){ return r.json(); });
    if (d.error) { if (status) status.textContent = 'Erreur : ' + d.error; }
    else {
      if (ta) ta.value = '';
      if (status) { status.textContent = '✓ Note mémorisée — ' + d.chunks_added + ' chunk' + (d.chunks_added !== 1 ? 's' : ''); _clearAfter(status, 3000); }
      loadRagStatus();
    }
  } catch(e) { if (status) status.textContent = 'Erreur réseau.'; }
}

async function ragClear() {
  if (!confirm('Vider l\'index RAG ? Tous les documents indexés seront supprimés.')) return;
  try {
    await fetch('/api/rag/clear', {method:'DELETE'});
    var status = document.getElementById('rag-status');
    if (status) { status.textContent = 'Index vidé.'; _clearAfter(status, 2000); }
    loadRagStatus();
  } catch(e) { _jwarn('[jarvis] ragClear:', e); }
}

async function loadPromptProfiles() {
  try {
    const profiles = await _fetchPromptProfiles();
    const list = document.getElementById('prompt-profiles-list');
    const sidebar = document.getElementById('sidebar-prompt-profiles');
    if (!list) return;
    const keys = Object.keys(profiles);
    if (keys.length === 0) {
      list.innerHTML = '<span class="profiles-empty-msg">Aucun profil sauvegardé</span>';
      if (sidebar) sidebar.innerHTML = '';
      return;
    }
    list.innerHTML = keys.map(name => {
      const p = profiles[name];
      const isActive = name === _activePromptProfile;
      const rowMod  = isActive ? 'pp-row--active'      : 'pp-row--inactive';
      const nameMod = isActive ? 'pp-row-name--active'  : 'pp-row-name--inactive';
      const activeMark = isActive ? '<span class="pp-active-mark">▶</span>' : '';
      const args = JSON.stringify([name]).replace(/'/g, '&#39;');
      const titleEsc = name.replace(/"/g, '&quot;');
      return `<div class="pp-row ${rowMod}">
        <div class="pp-row-meta">
          <div class="pp-row-name ${nameMod}">${activeMark}${name}</div>
          <div class="pp-row-date">${p.saved_at||''}</div>
        </div>
        <button class="stg-btn stg-btn-apply stg-btn-xs" data-action="loadPromptProfile" data-args='${args}' title="Charger ce profil">CHARGER</button>
        <button class="stg-btn stg-btn-reset stg-btn-xs" data-action="deletePromptProfile" data-args='${args}' title="Supprimer ${titleEsc}">✕</button>
      </div>`;
    }).join('');
    // Badges rapides dans la sidebar locale
    if (sidebar) {
      sidebar.innerHTML = keys.map(name => {
        const isActive = name === _activePromptProfile;
        const mod = isActive ? 'pp-badge--active' : 'pp-badge--inactive';
        const label = name.replace(/ SOC$/, '').replace(/ Code.*$/, '').replace(/ Général.*$/, '').replace(/ Conversation.*$/, '').replace(/ Technique$/, '');
        const args = JSON.stringify([name]).replace(/'/g, '&#39;');
        const titleEsc = name.replace(/"/g, '&quot;');
        return `<button class="pp-badge ${mod}" data-action="loadPromptProfile" data-args='${args}' title="${titleEsc}">${label}</button>`;
      }).join('');
    }
  } catch(e) { _jwarn('[JARVIS] renderPromptProfiles error', e); }
}

async function loadPromptProfile(name) {
  try {
    const profiles = await _fetchPromptProfiles();
    const ta = document.getElementById('system-prompt-editor');
    if (ta && profiles[name]) {
      ta.value = profiles[name].content;
      _updateActivePromptBadge(name);
      _promptStatus(`◈ Profil "${name}" chargé`, 'info');
      loadPromptProfiles();
    }
  } catch(e) { _jwarn('[jarvis] loadPromptProfile:', e); }
}

async function deletePromptProfile(name) {
  if (!confirm(`Supprimer le profil "${name}" ?`)) return;
  try {
    await fetch(`/api/prompt-profiles/${encodeURIComponent(name)}`, {method:'DELETE'});
    loadPromptProfiles();
    _promptStatus(`✕ Profil "${name}" supprimé`, 'err');
  } catch(e) { _jwarn('[jarvis] deletePromptProfile:', e); }
}

function openSavePromptProfile() {
  const form = document.getElementById('save-profile-form');
  if (form) { _disp(form, true, 'block'); document.getElementById('profile-name-input').focus(); }
}

function closeSavePromptProfile() {
  const form = document.getElementById('save-profile-form');
  _disp(form, false);
}

async function confirmSavePromptProfile() {
  const name = document.getElementById('profile-name-input').value.trim();
  if (!name) return;
  const ta = document.getElementById('system-prompt-editor');
  if (!ta) return;
  try {
    await fetch('/api/prompt-profiles', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name, content: ta.value})
    });
    closeSavePromptProfile();
    document.getElementById('profile-name-input').value = '';
    loadPromptProfiles();
    _promptStatus(`✓ Profil "${name}" sauvegardé`, 'ok');
  } catch(e) { _jwarn('[JARVIS] savePromptProfile error', e); }
}

async function applyProfile(key) {
  const profile = LLM_PROFILES[key];
  if (!profile) return;
  _activeProfile = key;

  // Mettre à jour les sliders
  for (const [k, v] of Object.entries(profile.params)) {
    const s = document.getElementById('s-' + k);
    if (s) { s.value = v; updateSliderVal(k, v); }
  }

  // Envoyer au serveur
  await fetch('/api/llm-params', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({params: profile.params})
  });

  // Feedback UI
  document.querySelectorAll('.profile-btn').forEach(b => b.classList.remove('active-profile'));
  const btns = document.querySelectorAll('.profile-btn');
  const keys = ['rapide','equilibre','code','creatif','precis','rtx5080'];
  const idx  = keys.indexOf(key);
  if (idx >= 0 && btns[idx]) btns[idx].classList.add('active-profile');

  const lbl = document.getElementById('profile-active');
  if (lbl) lbl.textContent = `PROFIL ACTIF : ${profile.label}`;

  const st = document.getElementById('stg-status');
  if (st) {
    st.dataset.profile = key;
    st.textContent = `✓ ${profile.label} — ${profile.desc}`;
    _clearAfter(st, 5000);
  }
}
