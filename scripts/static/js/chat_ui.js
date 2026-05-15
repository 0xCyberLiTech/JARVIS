// ══════════════════════════════════════════════════════════════
// CHAT UI — historique, addMessage, markdown, Monaco, mémoire LT
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-15.
//
// État + UI du chat :
//  - Historique chat (const history) + état busy + abort controller SSE.
//  - addMessage / _esc / addToolEvent — entrées d'écriture chat.
//  - Long-term memory (loadMemory, saveMemory, clearMemory,
//    updateMemoryCount).
//  - STOP TTS button (stopJarvis, _setStopBtn) + raccourci global
//    keydown (Échap = stop).
//  - Markdown rendering (renderMarkdown, getLangColor, getLangIcon,
//    copyCodeInline, highlightCode) + LANG_COLORS / _LANG_EXT.
//  - Monaco code editor modal (openCodeModal, closeCodeModal,
//    toggleCodeDiff, saveCodeLocally, copyModalCode, fullscreen,
//    fontSize, wrap) + _codeStore.
//  - Web search toggle + diag (toggleWebSearch, checkWebStatus,
//    toggleWebDiag).
//
// Fichier .js classique (scope global). Chargé AVANT chat_core.js
// (chat_core utilise addMessage, history, _esc, _codeStore).

let busy = false;
let _chatAbortController = null;

function stopJarvis() {
  // Coupe le TTS immédiatement
  stopAudio();
  // Annule le stream LLM en cours
  if (_chatAbortController) { _chatAbortController.abort(); _chatAbortController = null; }
  // Remet l'UI en état prêt
  busy = false;
  _setAllReplayBusy(false);
  const btnSend = document.getElementById('btn-send');
  if (btnSend) btnSend.disabled = false;
  document.getElementById('m-ai-status').textContent = 'ONLINE';
  document.getElementById('m-ai-status').className = 'stat-val c-green';
  document.getElementById('btn-stop').classList.remove('active');
}

function _setStopBtn(visible) {
  const b = document.getElementById('btn-stop');
  if (b) b.classList.toggle('active', visible);
}

// ── Mémoire persistante ──────────────────────────────────────
async function loadMemory() {
  try {
    const res = await fetch('/api/memory');
    const saved = await res.json();
    if (!Array.isArray(saved) || saved.length === 0) return;

    const container = document.getElementById('chat-messages');
    container.innerHTML = '';

    // Injecter les messages sauvegardés dans history + DOM
    const sep = document.createElement('div');
    sep.className = 'chat-session-sep';
    sep.textContent = `─── SESSION PRÉCÉDENTE : ${saved.length} MESSAGES ───`;
    container.appendChild(sep);

    for (const msg of saved) {
      history.push(msg);
      const role = msg.role === 'user' ? 'user' : 'jarvis';
      const bubble = addMessage(role, '');
      if (msg.role === 'user') {
        bubble.textContent = msg.content;
      } else {
        bubble.innerHTML = renderMarkdown(msg.content);
        highlightCode(bubble);
      }
    }

    const sep2 = document.createElement('div');
    sep2.className = 'chat-session-sep';
    sep2.textContent = '─── SESSION ACTUELLE ───';
    container.appendChild(sep2);

    updateMemoryCount();
    container.scrollTop = container.scrollHeight;
  } catch(e) {
    console.error('loadMemory:', e);
  }
}

function updateMemoryCount() {
  const exchanges = Math.floor(history.length / 2);
  document.getElementById('memory-count').textContent = exchanges;
}

async function saveMemory() {
  try {
    await fetch('/api/memory', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({history})
    });
    updateMemoryCount();
  } catch(e) { _jwarn('[jarvis] saveMemory:', e); }
}

async function clearMemory() {
  if (!confirm('Effacer toute la mémoire de JARVIS ?')) return;
  try {
    await fetch('/api/memory', {method:'DELETE'});
    history.length = 0;
    updateMemoryCount();
    // Reset chat
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    const bubble = addMessage('jarvis', '');
    bubble.textContent = 'Mémoire effacée. Bonjour Monsieur.';
  } catch(e) { _jwarn('[jarvis] clearMemory:', e); }
}

function _syncRangeSlider(el) {
  const pct = ((el.value - el.min) / (el.max - el.min) * 100).toFixed(2) + '%';
  if (el.classList.contains('dsp-hslider')) el.style.setProperty('--pct', pct);
  else if (el.classList.contains('rack-fader')) el.style.setProperty('--f-pct', pct);
}

// Charger la mémoire au démarrage + initialiser badges DSP
// → _jarvisInit()

// ── Rendu Markdown + Code ───────────────────────────────────
const _codeStore = {};
let _codeIdx = 0;

// NDT-BRAND-EXEMPT: couleurs officielles des langages (Python blue, JS yellow…) — non soumises au thème
const LANG_COLORS = {
  python:     { c: '#3776ab', g: '#3776ab18' },
  bash:       { c: '#4eaa25', g: '#4eaa2518' },
  sh:         { c: '#4eaa25', g: '#4eaa2518' },
  shell:      { c: '#4eaa25', g: '#4eaa2518' },
  javascript: { c: '#f7df1e', g: '#f7df1e14' },
  js:         { c: '#f7df1e', g: '#f7df1e14' },
  typescript: { c: '#3178c6', g: '#3178c618' },
  ts:         { c: '#3178c6', g: '#3178c618' },
  html:       { c: '#e44d26', g: '#e44d2618' },
  css:        { c: '#a259ff', g: '#a259ff18' },
  json:       { c: '#ababab', g: '#ababab10' },
  sql:        { c: '#e38c00', g: '#e38c0018' },
  rust:       { c: '#ce422b', g: '#ce422b18' },
  go:         { c: '#00add8', g: '#00add818' },
  java:       { c: '#f89820', g: '#f8982018' },
  cpp:        { c: '#659ad2', g: '#659ad218' },
  c:          { c: '#659ad2', g: '#659ad218' },
  yaml:       { c: '#cc1018', g: '#cc101818' },
  default:    { c: '#00cfff', g: '#00cfff08' },
};

function getLangColor(lang) {
  return LANG_COLORS[lang.toLowerCase()] || LANG_COLORS.default;
}

const _LANG_EXT = {python:'py',javascript:'js',typescript:'ts',bash:'sh',shell:'sh',html:'html',css:'css',json:'json',sql:'sql',rust:'rs',go:'go',java:'java',cpp:'cpp',c:'c'};

function getLangIcon(lang) {
  const m = {python:'🐍',javascript:'⚡',typescript:'🔷',bash:'$_',shell:'$_',sql:'🗄',html:'🌐',css:'🎨',json:'{}',rust:'⚙',go:'🐹',java:'☕',cpp:'C+',c:'C·'};
  return m[lang] || '◈';
}

function renderMarkdown(text) {
  // 0. Masquer les blocs <think>...</think> (phi4-reasoning, deepseek-r1)
  text = text.replace(/<think>[\s\S]*?<\/think>/gi, '');
  // 1. Extraire blocs de code → placeholder, HTML généré à l'avance (trusted)
  const _cblks = {};
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const l = lang || 'plaintext';
    const idx = _codeIdx++;
    const trimmed = code.trim();
    _codeStore[idx] = { lang: l, code: trimmed };
    const lc = getLangColor(l);
    const lines = trimmed.split('\n').length;
    const ext  = _LANG_EXT[l] || l;
    _cblks[idx] = `<div class="code-card" style="--lc:${lc.c};--lg:${lc.g}" onclick="openCodeModal(${idx})">
  <div class="code-card-icon">${getLangIcon(l)}</div>
  <div class="code-card-info">
    <span class="code-card-lang">${l.toUpperCase()}</span>
    <span class="code-card-file">untitled.${ext}</span>
    <span class="code-card-lines">${lines} ligne${lines>1?'s':''}</span>
  </div>
  <div class="code-card-actions">
    <button class="code-card-btn primary" onclick="event.stopPropagation();openCodeModal(${idx})">◈ OUVRIR</button>
    <button class="code-card-btn" onclick="event.stopPropagation();copyCodeInline(${idx},this)">⎘ COPIER</button>
  </div>
</div>`;
    return `\x01BLK${idx}\x01`;
  });
  // 2. Échapper le HTML brut dans le texte restant (protection XSS)
  text = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // 2.5 Headers ## et ### (après escape HTML → injection HTML sûre)
  text = text.replace(/^## (.+)$/gm, function(_, c) {
    var cls = c.startsWith('✅') ? 'md-h2 md-h2-ok' : c.startsWith('⚠') ? 'md-h2 md-h2-warn' : 'md-h2';
    return '<div class="' + cls + '">' + c + '</div>';
  });
  text = text.replace(/^### (.+)$/gm, '<div class="md-h3">$1</div>');
  // 3. Code inline `...`
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  // 4. Gras **...**
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // 5. Italique *...*
  text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
  // 6. Sauts de ligne
  text = text.replace(/\n/g, '<br>');
  // 7. Restaurer blocs de code (HTML trusted, généré par nous)
  text = text.replace(/\x01BLK(\d+)\x01/g, (_, i) => _cblks[parseInt(i)] || '');
  return text;
}

function copyCodeInline(idx, btn) {
  const entry = _codeStore[idx];
  if (!entry) return;
  navigator.clipboard.writeText(entry.code).then(() => {
    btn.textContent = '✓';
    setTimeout(() => btn.textContent = 'COPIER', _COPY_RESET_MS);
  });
}

function highlightCode(el) {
  if (typeof hljs === 'undefined') return;
  el.querySelectorAll('pre code').forEach(block => {
    hljs.highlightElement(block);
  });
}


// ── Code Modal — Monaco Editor ──────────────────────────────
let _modalFontSize  = 13;
let _modalWrap      = false;
let _monacoEditor   = null;
let _monacoDiffEditor = null;
let _monacoReady    = false;
let _monacoOrigCode = '';
let _monacoDiffMode = false;
const _MONACO_CDN   = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs';

function _loadMonaco() {
  if (_monacoReady) return Promise.resolve();
  return new Promise((resolve, reject) => {
    if (document.getElementById('_monaco-loader')) { resolve(); return; }
    const s = document.createElement('script');
    s.id = '_monaco-loader';
    s.src = _MONACO_CDN + '/loader.js';
    s.onload = () => {
      window.require.config({ paths: { vs: _MONACO_CDN } });
      window.require(['vs/editor/editor.main'], () => {
        _defineMonacoTheme();
        _monacoReady = true;
        resolve();
      });
    };
    s.onerror = () => reject(new Error('Monaco CDN unavailable'));
    document.head.appendChild(s);
  });
}

// NDT-EDITOR-EXEMPT: couleurs thème Monaco — format API éditeur (hex sans var() possible)
function _defineMonacoTheme() {
  monaco.editor.defineTheme('jarvis-dark', {
    base: 'vs-dark', inherit: true,
    rules: [
      { token: 'comment',  foreground: '3d6478', fontStyle: 'italic' },
      { token: 'keyword',  foreground: '00cfff', fontStyle: 'bold' },
      { token: 'string',   foreground: '00e676' },
      { token: 'number',   foreground: 'ff9900' },
      { token: 'type',     foreground: 'c792ea' },
      { token: 'function', foreground: '82aaff' },
    ],
    colors: {
      'editor.background':                  '#060c14',
      'editor.foreground':                  '#b0c4cc',
      'editorLineNumber.foreground':        '#1e3a4a',
      'editorLineNumber.activeForeground':  '#00cfff88',
      'editor.lineHighlightBackground':     '#0a1a24',
      'editorCursor.foreground':            '#00cfff',
      'editor.selectionBackground':         '#00cfff1a',
      'editorIndentGuide.background1':      '#0d2030',
      'scrollbarSlider.background':         '#00cfff18',
      'scrollbarSlider.hoverBackground':    '#00cfff33',
      'scrollbarSlider.activeBackground':   '#00cfff55',
      'editorWidget.background':            '#0a1520',
      'editorWidget.border':                '#00cfff22',
      'minimap.background':                 '#040a10',
    }
  });
}

async function openCodeModal(idx) {
  const entry = _codeStore[idx];
  if (!entry) return;
  const { lang, code } = entry;

  try { await _loadMonaco(); } catch(e) {
    _jwarn('[jarvis] Monaco CDN KO — éditeur indisponible hors ligne'); return;
  }

  _monacoOrigCode = code;
  _monacoDiffMode = false;
  document.getElementById('monaco-container').style.display      = '';
  document.getElementById('monaco-diff-container').style.display = 'none';
  const diffBtn = document.getElementById('modal-diff-btn');
  if (diffBtn) diffBtn.classList.remove('active');

  const ext = _LANG_EXT[lang] || lang;
  document.getElementById('modal-tab-name').textContent    = `untitled.${ext}`;
  document.getElementById('modal-status-lang').textContent = lang.toUpperCase();
  document.querySelector('.code-modal-box')?.style.setProperty('--mlc', getLangColor(lang).c);

  const container = document.getElementById('monaco-container');
  if (_monacoEditor) {
    monaco.editor.setModelLanguage(_monacoEditor.getModel(), lang);
    _monacoEditor.setValue(code);
  } else {
    _monacoEditor = monaco.editor.create(container, {
      value: code, language: lang, theme: 'jarvis-dark',
      minimap: { enabled: true, scale: 1 },
      fontSize: _modalFontSize,
      fontFamily: '"Cascadia Code","JetBrains Mono","Fira Code",monospace',
      fontLigatures: true,
      lineNumbers: 'on',
      scrollBeyondLastLine: false,
      wordWrap: _modalWrap ? 'on' : 'off',
      automaticLayout: true,
      scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
      renderLineHighlight: 'all',
      cursorBlinking: 'smooth',
      cursorSmoothCaretAnimation: 'on',
      bracketPairColorization: { enabled: true },
      padding: { top: 12, bottom: 12 },
    });
    _monacoEditor.onDidChangeModelContent(() => _updateMonacoStats());
    _monacoEditor.onDidChangeCursorPosition(e => {
      const el = document.getElementById('modal-cursor');
      if (el) el.textContent = `Ln ${e.position.lineNumber}, Col ${e.position.column}`;
    });
    _monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, saveCodeLocally);
  }

  _updateMonacoStats();
  document.getElementById('code-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
  setTimeout(() => _monacoEditor && _monacoEditor.focus(), 150);
}

function _updateMonacoStats() {
  if (!_monacoEditor) return;
  const code = _monacoEditor.getValue();
  const lines = code.split('\n').length;
  const el   = document.getElementById('modal-stats');
  const pill = document.getElementById('modal-stats-pill');
  if (el)   el.textContent   = `${lines} LIGNES // ${code.length} CARACTÈRES`;
  if (pill) pill.textContent = `${lines}L · ${code.length}C`;
}

function modalFontSize(delta) {
  _modalFontSize = Math.min(22, Math.max(9, _modalFontSize + delta));
  if (_monacoEditor)     _monacoEditor.updateOptions({ fontSize: _modalFontSize });
  if (_monacoDiffEditor) _monacoDiffEditor.updateOptions({ fontSize: _modalFontSize });
}

function toggleModalWrap() {
  _modalWrap = !_modalWrap;
  if (_monacoEditor) _monacoEditor.updateOptions({ wordWrap: _modalWrap ? 'on' : 'off' });
  const btn = document.getElementById('modal-wrap-btn');
  if (btn) btn.classList.toggle('active', _modalWrap);
}

function toggleCodeDiff() {
  if (!_monacoEditor) return;
  _monacoDiffMode = !_monacoDiffMode;
  const btn = document.getElementById('modal-diff-btn');
  const mc  = document.getElementById('monaco-container');
  const dc  = document.getElementById('monaco-diff-container');
  if (_monacoDiffMode) {
    if (btn) btn.classList.add('active');
    mc.style.display = 'none';
    dc.style.display = '';
    if (!_monacoDiffEditor) {
      _monacoDiffEditor = monaco.editor.createDiffEditor(dc, {
        theme: 'jarvis-dark', readOnly: true, automaticLayout: true,
        fontSize: _modalFontSize, fontFamily: '"Cascadia Code",monospace',
        renderSideBySide: true, ignoreTrimWhitespace: false,
      });
    }
    const lg = _monacoEditor.getModel().getLanguageId();
    _monacoDiffEditor.setModel({
      original: monaco.editor.createModel(_monacoOrigCode, lg),
      modified: monaco.editor.createModel(_monacoEditor.getValue(), lg),
    });
  } else {
    if (btn) btn.classList.remove('active');
    mc.style.display = '';
    dc.style.display = 'none';
  }
}

async function saveCodeLocally() {
  if (!_monacoEditor) return;
  const code     = _monacoEditor.getValue();
  const filename = document.getElementById('modal-tab-name')?.textContent || 'untitled.py';
  const btn      = document.getElementById('modal-save-btn');
  try {
    await fetch('/api/save-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename, code })
    });
    if (btn) { const t = btn.textContent; btn.textContent = '✓ SAUVÉ'; setTimeout(() => btn.textContent = t, 1500); }
  } catch(e) { _jwarn('[jarvis] saveCodeLocally:', e); }
}

function toggleCodeFullscreen() {
  const box = document.querySelector('.code-modal-box');
  if (!box) return;
  box.classList.toggle('code-modal-fullscreen');
  const btn = document.getElementById('modal-fs-btn');
  if (btn) btn.textContent = box.classList.contains('code-modal-fullscreen') ? '⛶ EXIT' : '⛶';
  setTimeout(() => { if (_monacoEditor) _monacoEditor.layout(); }, 100);
}

function closeCodeModal() {
  document.getElementById('code-modal').classList.remove('open');
  document.body.style.overflow = '';
}

function copyModalCode() {
  const code = _monacoEditor ? _monacoEditor.getValue() : '';
  if (!code) return;
  navigator.clipboard.writeText(code).then(() => {
    const btn = document.getElementById('modal-copy-btn');
    if (btn) { btn.textContent = '✓ COPIÉ'; setTimeout(() => btn.textContent = '⎘ COPIER', _COPY_RESET_MS); }
  });
}

// Fermer modal avec Échap
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeCodeModal();
});
// Fermer en cliquant outside (modal ajouté après ce script → attendre le DOM)
// → _jarvisInit()

function _esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function addToolEvent(type, name, detail) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'tool-event';
  const icons = {lire_fichier:'📄', ecrire_fichier:'💾', modifier_fichier:'✏️', lister_dossier:'📁'};
  const icon = icons[name] || '⚙️';
  const safeDetail = _esc(detail.substring(0, 200)) + (detail.length > 200 ? '...' : '');
  div.innerHTML = `
    <div class="tool-header">${icon} TOOL // <span class="tool-name">${_esc(name)}</span> <span class="tool-type">${_esc(type)}</span></div>
    <div class="tool-detail">${safeDetail.replace(/\n/g,'<br>')}</div>
  `;
  container.appendChild(div);
  container.scrollTop = 999999;
}

function addMessage(role, text) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  const bubbleId = 'bubble-' + Date.now();
  const replayBtn = role === 'jarvis'
    ? `<button class="msg-replay-btn" onclick="replayMessage(this.closest('.msg').dataset.text,this)" title="Relire / Arrêter">▶</button>`
    : '';
  // Messages utilisateur : échapper le HTML. Réponses JARVIS : HTML rendu (markdown)
  const safeText = role === 'user' ? _esc(text) : text;
  div.innerHTML = `<div class="msg-label">${role === 'user' ? 'VOUS' : 'JARVIS'}</div><div class="msg-bubble" id="${bubbleId}">${safeText}</div>${replayBtn}`;
  if (role === 'jarvis' && text) div.dataset.text = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div.querySelector('.msg-bubble');
}

function toggleWebSearch() {
  window._webSearchEnabled = !window._webSearchEnabled;
  const btn = document.getElementById('btn-web');
  if (btn) btn.classList.toggle('active', window._webSearchEnabled);
  // Fermer le tooltip si ouvert
  const tt = document.getElementById('web-diag-tooltip');
  if (tt) tt.classList.remove('open');
}

// ── Indicateur & Diagnostic Web ─────────────────────────────────
let _webDiagOpen = false;
let _webStatusChecked = false;

async function checkWebStatus(silent = true) {
  const dot = document.getElementById('web-status-dot');
  if (dot) dot.className = 'web-status-dot checking';
  try {
    const r = await fetch('/api/web-test');
    const d = await r.json();
    _webStatusChecked = true;
    let status = 'error';
    if (d.search_ok)      status = 'ok';
    else if (d.connectivity || d.wikipedia) status = 'warn';
    if (dot) dot.className = 'web-status-dot ' + status;
    return d;
  } catch(e) {
    if (dot) dot.className = 'web-status-dot error';
    return null;
  }
}

function toggleWebDiag(e) {
  e.preventDefault();
  const tt = document.getElementById('web-diag-tooltip');
  if (!tt) return;
  _webDiagOpen = !_webDiagOpen;
  tt.classList.toggle('open', _webDiagOpen);
  if (_webDiagOpen) {
    tt.innerHTML = '<div class="web-diag-loading">Diagnostic en cours…</div>';
    checkWebStatus(false).then(d => {
      if (!d) { tt.innerHTML = '<div class="web-diag-error-msg">Erreur — réseau inaccessible</div>'; return; }
      const row = (k, v, cls) =>
        `<div class="web-diag-row"><span class="web-diag-key">${k}</span><span class="web-diag-val ${cls}">${v}</span></div>`;
      tt.innerHTML =
        row('CONNECTIVITÉ',    d.connectivity ? '✓ OK' : '✗ KO',     d.connectivity ? 'ok' : 'err') +
        row('LATENCE',         d.latency_ms ? d.latency_ms + ' ms' : '—', d.latency_ms < 300 ? 'ok' : 'warn') +
        row('DUCKDUCKGO',      d.ddg         ? '✓ Accessible' : '✗ Bloqué', d.ddg ? 'ok' : 'warn') +
        row('WIKIPEDIA FR',    d.wikipedia   ? '✓ Accessible' : '✗ KO',     d.wikipedia ? 'ok' : 'warn') +
        row('RÉSULTATS',       d.results_count > 0 ? '✓ ' + d.results_count + ' résultats' : '✗ Aucun', d.results_count > 0 ? 'ok' : 'warn') +
        (d.sample ? `<div class="web-diag-sample">${d.sample.replace(/</g,'&lt;').slice(0,180)}…</div>` : '') +
        `<div class="web-diag-hint">Clic-droit pour fermer • Clic pour activer/désactiver</div>`;
    });
    // Clic ailleurs pour fermer
    setTimeout(() => {
      document.addEventListener('click', function _close(ev) {
        const btn = document.getElementById('btn-web');
        if (btn && !btn.contains(ev.target)) {
          tt.classList.remove('open'); _webDiagOpen = false;
          document.removeEventListener('click', _close);
        }
      });
    }, 100);
  }
}

// → _jarvisInit()


// ── Message line number counter ──
let _msgCount = 1;
const _origAddMessage = addMessage;
// Patch addMessage to inject line numbers
(function patchAddMessage() {
  // Wrap the existing addMessage that was already defined above
  // We do this by hooking into the DOM observer instead
  const msgContainer = document.getElementById('chat-messages');
  if (!msgContainer) return;
  const observer = new MutationObserver(mutations => {
    mutations.forEach(m => {
      m.addedNodes.forEach(node => {
        if (node.nodeType === 1 && node.classList && node.classList.contains('msg')) {
          // Check if linenum already exists
          if (!node.querySelector('.msg-linenum')) {
            const ln = document.createElement('div');
            ln.className = 'msg-linenum';
            ln.textContent = String(_msgCount).padStart(3, '0');
            node.insertBefore(ln, node.firstChild);
            _msgCount++;
          }
        }
      });
    });
  });
  observer.observe(msgContainer, { childList: true });
})();

