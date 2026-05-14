// ── Lecture variables CSS (:root) ────────────────────────────────────────
function _cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }

// ── Debug logger — set _JARVIS_DEBUG=true dans la console pour activer ──
var _JARVIS_DEBUG = false;
var _jwarn = function() { if (_JARVIS_DEBUG) console.warn.apply(console, arguments); };

// ── Constantes de timing (ms) ──────────────────────────────────────────
var _FETCH_ABORT_MS    = 60000;  // timeout abort fetch global
var _SOC_REFRESH_MS    = 30000;  // intervalle auto-refresh SOC
var _BTN_COOLDOWN_MS   = 5000;   // cooldown bouton FORCER
var _POLL_STATS_MS     = 10000;  // délai initial poll stats
var _COPY_RESET_MS     = 2000;   // délai reset libellé COPIER
var _COVER_SAFE_MS     = 8000;   // fallback retrait voile noir si boot-id KO
var _VOIX_PULSE_MS     = 2000;   // délai pulse bouton VOIX au démarrage
var _DRAW_INTERVAL_MS  = 80;     // intervalle RAF draw (spectre, VU-mètres)
var _DSP_PUSH_MS       = 500;    // debounce pushDspParamsToBackend
var _TICK_INTERVAL_MS  = 1000;   // horloge secondes (uptime, timers)
var _EQ_REDRAW_MS      = 100;    // redraw courbe EQ après interaction
var _STG_GPU_POLL_MS   = 5000;   // poll GPU dans l'onglet Settings
var _DRIFT_INTERVAL_MS = 1800;   // animation drift preloader
var _UPD_INTERVAL_MS   = 2200;   // animation update preloader
var _TASKS_POLL_MS     = 60000;  // intervalle check tâches planifiées
var _DSP_INIT_DELAY_MS  = 60;    // délai init DSP à l'ouverture de l'onglet (EQ curve + sliders)
var _TTS_STATUS_POLL_MS = 15000; // intervalle poll statut TTS (Kokoro/Piper/SAPI5)
var _VRAM_POLL_MS       = 15000; // intervalle poll VRAM / modèles Ollama
var _CR_POLL_MS         = 2000;  // délai entre tentatives poll C·R task
var _BOOTID_POLL_MS     = 15000; // intervalle poll boot-id (reload si redémarrage JARVIS)

function _clearAfter(el, ms){ if(el) setTimeout(function(){ el.textContent=''; el.classList.remove('st-ok','st-active','st-load','st-err','st-info'); }, ms); }
function _stColor(el, state){ if(!el) return; el.classList.remove('st-ok','st-active','st-load','st-err','st-info'); if(state) el.classList.add('st-'+state); }
function _disp(el, show, type) { if (el) el.style.display = show ? (type || '') : 'none'; }

// ── Helpers fetch API (DRY) ──────────────────────────────────────────────────
async function _fetchDspParams()      { return fetch('/api/dsp-params').then(r => r.json()); }
async function _fetchLlmParams()      { return fetch('/api/llm-params').then(r => r.json()); }
async function _fetchPromptProfiles() { return fetch('/api/prompt-profiles').then(r => r.json()); }
async function _fetchFacts()          { return fetch('/api/facts').then(r => r.json()); }
function _patchDsp(patch)             { return fetch('/api/dsp-params',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(patch)}).catch(()=>{}); }

// ── NDT: fetch wrapper — AbortController par défaut (ignoré si signal déjà présent)
// Les streams SSE chat ont leur propre _chatAbortController → non affectés
;(function(){
'use strict';
  var _origFetch = window.fetch.bind(window);
  window.fetch = function(url, opts){
    opts = opts || {};
    if(!opts.signal){
      var _ac = new AbortController();
      setTimeout(function(){ _ac.abort(); }, _FETCH_ABORT_MS);
      opts = Object.assign({}, opts, {signal: _ac.signal});
    }
    return _origFetch(url, opts);
  };
})();

// ══════════════════════════════════════
// TABS
// ══════════════════════════════════════
function switchTab(name) {
  const names = ['monitor','chat','settings','dsp','taches','voicelab','soc'];
  document.querySelectorAll('.tab').forEach((t,i) => {
    t.classList.toggle('active', names[i] === name);
  });
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  if (name === 'settings') startSettingsPolling();
  else stopSettingsPolling();
  if (name === 'monitor') { clearTimeout(_statsPollTimer); pollStats(); }
  if (name === 'dsp') { startDspDraw(); setTimeout(() => { drawEqCurve(); _refreshDspSliders(); }, _DSP_INIT_DELAY_MS); }
  if (name !== 'soc' && _socAutoRefresh) { clearInterval(_socAutoRefresh); _socAutoRefresh = null; }
  // Note: RAF stays alive after initDsp() to keep VU meters + EQ pulse active on all tabs
}

// ══════════════════════════════════════
// ONGLET ◈ SOC
// ══════════════════════════════════════
var _socAutoRefresh = null;

function initSocTab() {
  refreshSocTab();
  if (_socAutoRefresh) clearInterval(_socAutoRefresh);
  _socAutoRefresh = setInterval(refreshSocTab, _SOC_REFRESH_MS);
}

async function refreshSocTab() {
  try {
    const [rAct, rMon] = await Promise.all([
      fetch('/api/soc/actions'),
      fetch('/api/soc/monitor')
    ]);
    const act = await rAct.json();
    const mon = await rMon.json();

    // Badge statut
    const badge = document.getElementById('soc-online-badge');
    if (badge) {
      const online = mon.dashboard_open;
      badge.textContent = online ? '● SOC DASHBOARD ACTIF' : '○ SOC DASHBOARD FERMÉ';
      badge.classList.toggle('soc-badge-online',  online);
      badge.classList.toggle('soc-badge-offline', !online);
    }

    // Compteurs — police standard pour éviter glyphe manquant Orbitron sur 0
    const set = (id, v) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = v;
    };
    set('soc-cnt-total',   act.total   != null ? act.total   : '—');
    set('soc-cnt-ban',     act.by_type ? (act.by_type.ban_ip          || 0) : '—');
    set('soc-cnt-restart', act.by_type ? (act.by_type.restart_service || 0) : '—');
    set('soc-cnt-ok',      act.success  != null ? act.success  : '—');
    set('soc-cnt-fail',    act.failed   != null ? act.failed   : '—');
    // Compteur IDS — bans Suricata + alertes sév.2
    if (act.actions) {
      const idsCnt = act.actions.filter(function(a){
        return a.type === 'suricata_alert' ||
               (a.type === 'ban_ip' && a.detail && a.detail.indexOf('Suricata') >= 0);
      }).length;
      set('soc-cnt-ids', idsCnt);
    }

    // Graphiques (utilise ts_list pour avoir tout l'historique)
    if (act.ts_list) {
      var histObjects = act.ts_list.map(function(ts){ return {ts:ts}; });
      _socDrawCharts(histObjects);
    }

    // Journal
    const list = document.getElementById('soc-actions-list');
    if (!list) return;
    if (!act.actions || act.actions.length === 0) {
      list.innerHTML = '<div class="soc-jrnl-empty">Aucune action enregistrée.</div>';
      return;
    }
    const typeIco  = { ban_ip:'⊛ BAN', unban_ip:'⊘ UNBAN', restart_service:'↺ RESTART', suricata_alert:'◈ IDS' };
    const typeCol  = { ban_ip:'var(--red)', unban_ip:'var(--cyan)', restart_service:'var(--amber)', suricata_alert:'var(--orange)' };
    list.innerHTML = act.actions.map(function(a) {
      // Bans Suricata : même type ban_ip mais détail contient "Suricata"
      const isSuricata = (a.type === 'ban_ip' && a.detail && a.detail.indexOf('Suricata') >= 0)
                      || a.type === 'suricata_alert';
      const ico = isSuricata ? '◈ IDS' : (typeIco[a.type] || _esc(a.type));
      const col = isSuricata ? 'var(--orange)' : (typeCol[a.type] || 'var(--muted)');
      const ok  = a.success
        ? '<span class="soc-action-ok">✓ OK</span>'
        : '<span class="soc-action-fail">✗ ÉCHEC</span>';
      return '<div class="soc-action-row">'
        + '<span class="soc-action-icon" style="--ac:'+col+'">'+ico+'</span>'
        + '<div class="soc-action-body">'
        + '<div class="soc-action-detail">'+_esc(a.detail)+'</div>'
        + (a.result ? '<div class="soc-action-result">'+_esc(a.result.slice(0,120))+'</div>' : '')
        + '</div>'
        + '<div class="soc-action-right">'
        + ok
        + '<div class="soc-action-ts">'+_esc(a.ts)+'</div>'
        + '</div>'
        + '</div>';
    }).join('');
  } catch(e) {
    const badge = document.getElementById('soc-online-badge');
    if (badge) { badge.textContent = '✗ JARVIS HORS LIGNE'; badge.classList.add('soc-badge-offline'); badge.classList.remove('soc-badge-online'); }
  }
}


// ── Contexte SOC temps réel ───────────────────────────────────────────────
// Poll de fond 30s → window._jarvisMonData : sert UNIQUEMENT l'alerte vocale
// proactive (checkThreatLevel). L'injection du contexte SOC dans le chat est
// 100 % côté serveur (chat_soc_inject.py → system prompt, frais à chaque appel,
// jamais persisté dans l'historique) — source unique _build_monitoring_context.
var _MON_ENDPOINT  = (window.JARVIS_CONFIG && window.JARVIS_CONFIG.monEndpoint) || 'http://192.168.1.50:8080/monitoring.json';
window._jarvisMonData = null;

// ── Alerte vocale proactive SOC (piste 4 — checkThreatLevel) ────
var _lastKnownThreatLevel = null;
var _SOC_ALERT_LEVELS     = ['ÉLEVÉ', 'CRITIQUE'];

function checkThreatLevel(d) {
  var lvl  = d && d.threat_level;
  if (!lvl) return;
  var prev = _lastKnownThreatLevel;
  _lastKnownThreatLevel = lvl;
  if (prev === null) return; // premier chargement — pas d'alerte
  if (lvl === prev)  return; // niveau inchangé
  if (!_SOC_ALERT_LEVELS.includes(lvl)) return; // escalade vers FAIBLE/MOYEN → silencieux
  var score    = d.threat_score != null ? d.threat_score : '?';
  var ips      = ((d.kill_chain || {}).active_ips || []);
  var exploits = ips.filter(function(ip){ return ip.stage === 'EXPLOIT' && !ip.cs_decision; });
  var msg = 'Alerte S.O.C. Niveau ' + lvl + ', score ' + score + ' sur cent.';
  if (exploits.length > 0) {
    msg += ' ' + exploits.length + ' I.P.' + (exploits.length > 1 ? 's' : '') +
           ' en phase Exploit non bloquée' + (exploits.length > 1 ? 's' : '') + '.';
  }
  msg += lvl === 'CRITIQUE' ? ' Action immédiate requise.' : ' Intervention recommandée.';
  // Passe par la queue unifiée (speechQueue) — sérialise avec la voix Jarvis,
  // évite le chevauchement audio entre alerte SOC et réponse en cours.
  if (typeof queueSpeech === 'function') queueSpeech(msg);
}

(function(){
  async function _pollMon(){
    try{
      var r = await fetch(_MON_ENDPOINT);
      if(r.ok){
        window._jarvisMonData = await r.json();
        checkThreatLevel(window._jarvisMonData);
      }
    }catch(e){ _jwarn('[JARVIS] _pollMon fetch error', e); }
  }
  _pollMon();
  setInterval(_pollMon, _SOC_REFRESH_MS);
})();

// Payload chat : l'historique part TEL QUEL — aucune incrustation de contexte
// SOC côté client. Le serveur (chat_soc_inject.py) détecte les mots-clés SOC et
// injecte les données fraîches dans le system prompt à chaque appel. Avantages :
// zéro données périmées dans l'historique, source de formatage unique (Python).
async function _buildChatPayload(hist, opts){
  var base = {history: hist, web_search: window._webSearchEnabled || false, soc_ctx_injected: false};
  return opts ? Object.assign(base, opts) : base;
}

async function socNarrativeAnalysis() {
  const narDiv = document.getElementById('soc-narrative');
  if (!narDiv) return;
  _disp(narDiv, true, 'block');
  narDiv.textContent = '◈ Analyse en cours…';
  const prompt = 'Analyse soc. Donne directement :\n'
    + 'Score de menace et niveau.\n'
    + 'Les 2-3 menaces actives les plus critiques avec leurs IPs et stages.\n'
    + 'État des défenses crowdsec fail2ban.\n'
    + 'Recommandation prioritaire. Stop.';
  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(await _buildChatPayload([{role:'user', content: prompt}]))
    });
    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let text = '';
    narDiv.textContent = '';
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      dec.decode(value).split('\n').forEach(function(line) {
        if (!line.startsWith('data:')) return;
        try {
          const ev = JSON.parse(line.slice(5).trim());
          if (ev.type === 'token') { text += ev.token; narDiv.textContent = text; }
        } catch(e) { /* skip malformed SSE line */ }
      });
    }
    // Reconvertir IPs TTS "X tiret Y" → "X.Y" pour affichage visuel
    text = text.replace(/(\d+)\s+tiret\s+(\d+)\s+tiret\s+(\d+)\s+tiret\s+(\d+)/g, '$1.$2.$3.$4');
    if (!text) narDiv.textContent = '(pas de réponse — JARVIS hors ligne ?)';
  } catch(e) {
    narDiv.textContent = '✗ Erreur — JARVIS hors ligne.';
  }
}

async function clearSocActions() {
  try {
    await fetch('/api/soc/actions/clear', {method:'POST'});
    refreshSocTab();
  } catch(e) { _jwarn('[jarvis] clearSocActions:', e); }
}

async function socForceAutoban() {
  const btn = document.getElementById('soc-force-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⚡ EN COURS…'; }
  try {
    const r = await fetch('/api/soc/force-autoban', {method:'POST'});
    const d = await r.json();
    if (btn) {
      btn.textContent = d.new_actions > 0 ? ('⚡ +'+d.new_actions+' ACTION'+(d.new_actions>1?'S':'')) : '⚡ AUCUN BAN';
      btn.classList.toggle('soc-btn-amber--active', d.new_actions > 0);
      setTimeout(function(){ btn.disabled=false; btn.textContent='⚡ FORCER'; btn.classList.remove('soc-btn-amber--active'); }, _BTN_COOLDOWN_MS);
    }
    await refreshSocTab();
  } catch(e) {
    if (btn) { btn.disabled=false; btn.textContent='⚡ FORCER'; }
  }
}

// ══════════════════════════════════════
// SOC GRAPHIQUES (canvas natif)
// ══════════════════════════════════════
var _socChartOffset = 0;    // 0 = mois courant, -1 = mois précédent, etc.
var _socChartActions = [];  // snapshot des actions reçues via refreshSocTab

function _socBuildDayMap(actions, year, month) {
  // Retourne {day: count} pour le mois donné (mois 1-12)
  var map = {};
  var prefix = year + '-' + String(month).padStart(2,'0') + '-';
  actions.forEach(function(a) {
    if (a.ts && a.ts.startsWith(prefix)) {
      var d = a.ts.slice(8,10);
      map[d] = (map[d]||0) + 1;
    }
  });
  return map;
}

function _socBuildHourMap(actions, dateStr) {
  // Retourne {hour(0-23): count} pour la date YYYY-MM-DD
  var map = {};
  actions.forEach(function(a) {
    if (a.ts && a.ts.startsWith(dateStr)) {
      var h = parseInt(a.ts.slice(11,13), 10);
      map[h] = (map[h]||0) + 1;
    }
  });
  return map;
}

function _socSparkline(canvas, values, isCurrent) {
  // Dessine une sparkline lisse (bezier) dans le canvas donné
  var ctx = canvas.getContext('2d');
  var W = canvas.width, H = canvas.height;
  ctx.clearRect(0,0,W,H);
  var n = values.length;
  if (n === 0) return;
  var maxVal = Math.max(1, Math.max.apply(null, values));
  var padL=4, padR=4, padT=6, padB=4;
  var aW = W-padL-padR, aH = H-padT-padB;
  // Points
  var pts = values.map(function(v,i){
    return { x: padL + (n===1 ? aW/2 : i/(n-1)*aW),
             y: padT + aH - (v/maxVal)*aH };
  });
  var col = isCurrent ? 'rgba(220,60,60,1)' : 'rgba(180,50,50,.8)';
  var fillCol0 = isCurrent ? 'rgba(220,60,60,.35)' : 'rgba(160,40,40,.2)';
  // Bezier smooth path
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (var i=1; i<n; i++) {
    var cpx = (pts[i-1].x + pts[i].x)/2;
    ctx.bezierCurveTo(cpx, pts[i-1].y, cpx, pts[i].y, pts[i].x, pts[i].y);
  }
  // Fill
  ctx.lineTo(pts[n-1].x, padT+aH);
  ctx.lineTo(pts[0].x,   padT+aH);
  ctx.closePath();
  var grad = ctx.createLinearGradient(0, padT, 0, padT+aH);
  grad.addColorStop(0, fillCol0);
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.fill();
  // Stroke
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (var i=1; i<n; i++) {
    var cpx = (pts[i-1].x + pts[i].x)/2;
    ctx.bezierCurveTo(cpx, pts[i-1].y, cpx, pts[i].y, pts[i].x, pts[i].y);
  }
  ctx.strokeStyle = col;
  ctx.lineWidth = 1.5;
  ctx.stroke();
  // Dots
  pts.forEach(function(p) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 2, 0, Math.PI*2);
    ctx.fillStyle = col;
    ctx.fill();
  });
}

function _socRenderWeekCards(actions, year, month) {
  var row = document.getElementById('soc-weeks-row');
  if (!row) return;
  row.innerHTML = '';
  var daysInMonth = new Date(year, month, 0).getDate();
  var map = _socBuildDayMap(actions, year, month);
  var totalMonth = 0;
  for (var k in map) totalMonth += map[k];

  // Semaine en cours
  var now = new Date();
  var isCurrentMonthYear = (now.getFullYear()===year && now.getMonth()+1===month);
  var todayDay = isCurrentMonthYear ? now.getDate() : 0;

  // Carte MOIS complet
  var cardMois = document.createElement('div');
  cardMois.className = 'stat-card-month';
  cardMois.title = 'Voir le mois complet';
  cardMois.innerHTML = '<div class="stat-card-hdr">MOIS</div>'
    + '<div class="stat-card-sub">complet</div>'
    + '<div class="stat-card-num">' + totalMonth + '</div>';
  (function(yr, mo){ cardMois.addEventListener('click', function() {
    _socShowMonthDetail(_socChartActions, yr, mo);
  }); })(year, month);
  row.appendChild(cardMois);

  // Semaines S1-S5
  var weeks = [];
  var d = 1;
  var si = 1;
  while (d <= daysInMonth) {
    var start = d;
    var end   = Math.min(d + 6, daysInMonth);
    weeks.push({si:si, start:start, end:end});
    d = end + 1; si++;
  }

  weeks.forEach(function(w) {
    var total = 0;
    var vals  = [];
    for (var dd=w.start; dd<=w.end; dd++) {
      var cnt = map[String(dd).padStart(2,'0')]||0;
      total += cnt;
      vals.push(cnt);
    }
    var isCurrent = isCurrentMonthYear && todayDay >= w.start && todayDay <= w.end;
    var isFuture    = isCurrentMonthYear && w.start > todayDay;
    var countState  = isCurrent ? 'current' : (total>0 ? 'active' : 'dim');
    var startStr    = String(w.start).padStart(2,'0');
    var endStr      = String(w.end).padStart(2,'0');
    var card = document.createElement('div');
    card.className  = 'stat-card-week' + (isCurrent ? ' stat-card-current' : '') + (isFuture ? ' stat-card-future' : '');
    card.innerHTML  = '<div class="stat-card-week-hdr">S'+w.si+'</div>'
      + '<div class="stat-card-week-range">'+startStr+'-'+endStr+'</div>'
      + '<canvas width="80" height="32" class="stat-card-canvas"></canvas>'
      + '<div class="stat-card-week-count" data-count-state="'+countState+'">'+(isFuture?'—':total)+'</div>';
    // Sparkline
    var cvs = card.querySelector('canvas');
    if (!isFuture && vals.length) _socSparkline(cvs, vals, isCurrent);
    // Click → graphique CVE-style semaine
    if (!isFuture) {
      (function(wk, yr, mo) {
        card.addEventListener('click', function() {
          _socShowWeekDetail(_socChartActions, yr, mo, wk.start, wk.end, 'S'+wk.si);
        });
      })(w, year, month);
    }
    row.appendChild(card);
  });
}

// ── Graphique CVE-style pleine largeur ────────────────────────────
function _socChartDrawGrid(ctx, lp, n, maxVal) {
  var ySteps = 4;
  ctx.font = '7px monospace'; ctx.textAlign = 'right';
  for (var g = 0; g <= ySteps; g++) {
    var gy = lp.padT + lp.aH - (g / ySteps) * lp.aH;
    ctx.strokeStyle = 'rgba(255,255,255,.06)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(lp.padL, gy); ctx.lineTo(lp.W - lp.padR, gy); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,.3)';
    ctx.fillText(Math.round((g / ySteps) * maxVal), lp.padL - 3, gy + 3);
  }
  if (n > 7) {
    for (var si = 7; si < n; si += 7) {
      var sx = lp.padL + (si / (n - 1)) * lp.aW;
      ctx.strokeStyle = 'rgba(255,255,255,.08)'; ctx.lineWidth = 1;
      ctx.setLineDash([3, 4]);
      ctx.beginPath(); ctx.moveTo(sx, lp.padT); ctx.lineTo(sx, lp.padT + lp.aH); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = 'rgba(255,255,255,.18)'; ctx.font = '7px monospace'; ctx.textAlign = 'center';
      ctx.fillText('S' + Math.ceil(si / 7), sx, lp.padT - 3);
    }
  }
}

function _socChartCalcPts(values, n, lp) {
  return values.map(function(v, i) {
    return { x: lp.padL + (n === 1 ? lp.aW / 2 : i / (n - 1) * lp.aW), y: lp.padT + lp.aH - (v / lp.maxVal) * lp.aH };
  });
}

function _socChartDrawCurve(ctx, pts, n, lp, color) {
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (var i = 1; i < n; i++) {
    var cpx = (pts[i-1].x + pts[i].x) / 2;
    ctx.bezierCurveTo(cpx, pts[i-1].y, cpx, pts[i].y, pts[i].x, pts[i].y);
  }
  ctx.lineTo(pts[n-1].x, lp.padT + lp.aH);
  ctx.lineTo(pts[0].x,   lp.padT + lp.aH);
  ctx.closePath();
  var grad = ctx.createLinearGradient(0, lp.padT, 0, lp.padT + lp.aH);
  grad.addColorStop(0, color.replace(/[\d.]+\)$/, '.3)'));
  grad.addColorStop(1, color.replace(/[\d.]+\)$/, '0)'));
  ctx.fillStyle = grad; ctx.fill();
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (var i = 1; i < n; i++) {
    var cpx = (pts[i-1].x + pts[i].x) / 2;
    ctx.bezierCurveTo(cpx, pts[i-1].y, cpx, pts[i].y, pts[i].x, pts[i].y);
  }
  ctx.strokeStyle = color; ctx.lineWidth = 1.8; ctx.stroke();
}

function _socChartDrawDotsAndPeak({ ctx, pts, values, labels, n, lp, color }) {
  var peakIdx = 0;
  pts.forEach(function(p, i) {
    if (values[i] > values[peakIdx]) peakIdx = i;
    ctx.beginPath(); ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = color; ctx.fill();
    var showLabel = n <= 10 || i === 0 || (i + 1) % Math.ceil(n / 8) === 0 || i === n - 1;
    if (showLabel) {
      ctx.fillStyle = 'rgba(255,255,255,.35)'; ctx.font = '7px monospace'; ctx.textAlign = 'center';
      ctx.fillText(labels[i], p.x, lp.H - 5);
    }
  });
  var pk = pts[peakIdx];
  if (values[peakIdx] > 0) {
    ctx.fillStyle = color;
    ctx.font = 'bold 8px monospace'; ctx.textAlign = 'center';
    ctx.fillText(values[peakIdx], pk.x, pk.y - 7);
    ctx.beginPath(); ctx.arc(pk.x, pk.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = color; ctx.fill();
  }
}

function _socLineChart(cvs, labels, values, color, onPointClick) {
  var ctx = cvs.getContext('2d');
  ctx.clearRect(0, 0, cvs.width, cvs.height);
  var n = values.length; if (n === 0) return;
  var lp = { padL:34, padR:14, padT:14, padB:22, W:cvs.width, H:cvs.height,
             maxVal:Math.max(1, Math.max.apply(null, values)) };
  lp.aW = lp.W - lp.padL - lp.padR; lp.aH = lp.H - lp.padT - lp.padB;
  _socChartDrawGrid(ctx, lp, n, lp.maxVal);
  var pts = _socChartCalcPts(values, n, lp);
  _socChartDrawCurve(ctx, pts, n, lp, color);
  _socChartDrawDotsAndPeak({ ctx, pts, values, labels, n, lp, color });
  cvs._socPts = pts; cvs._socLabels = labels; cvs._socVals = values;
  if (onPointClick && !cvs._socLineClickBound) {
    cvs._socLineClickBound = true;
    cvs.addEventListener('click', function(e) {
      if (!cvs._socPts) return;
      var rect = cvs.getBoundingClientRect();
      var mx = (e.clientX - rect.left) * (cvs.width / rect.width);
      var best = -1, bestDist = 999;
      cvs._socPts.forEach(function(p, i) {
        var d = Math.abs(mx - p.x);
        if (d < bestDist) { bestDist = d; best = i; }
      });
      if (best >= 0 && bestDist < 30) onPointClick(best);
    });
    cvs.style.cursor = 'pointer';
  }
}

function _socShowDetail(title, info, labels, values, color, onPointClick) {
  var wrap=document.getElementById('soc-detail-wrap');
  var titleEl=document.getElementById('soc-detail-title');
  var infoEl=document.getElementById('soc-detail-info');
  var cvs=document.getElementById('soc-chart-detail');
  var hourCvs=document.getElementById('soc-chart-day');
  var hourLbl=document.getElementById('soc-day-label');
  if(!wrap||!cvs) return;
  _disp(wrap, true, 'block');
  if(titleEl) titleEl.textContent=title;
  if(infoEl) infoEl.textContent=info;
  _disp(hourCvs, false);
  _disp(hourLbl, false);
  _socLineChart(cvs, labels, values, color, onPointClick);
}

function _socShowMonthDetail(actions, year, month) {
  var daysInMonth=new Date(year,month,0).getDate();
  var map=_socBuildDayMap(actions,year,month);
  var labels=[], values=[], total=0;
  for(var d=1;d<=daysInMonth;d++){
    labels.push(String(d).padStart(2,'0'));
    var v=map[String(d).padStart(2,'0')]||0;
    values.push(v); total+=v;
  }
  var mo=['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc'];
  _socShowDetail(
    mo[month-1]+' '+year+' — Mois complet',
    total+' actions · Pic : '+Math.max.apply(null,values),
    labels, values, 'rgba(0,200,180,1)',
    function(idx){
      var ds=year+'-'+String(month).padStart(2,'0')+'-'+labels[idx];
      _socShowHourDetail(actions,ds);
    }
  );
}

function _socShowWeekDetail(actions, year, month, startDay, endDay, weekLabel) {
  var labels=[], values=[], total=0;
  for(var d=startDay;d<=endDay;d++){
    labels.push(String(d).padStart(2,'0'));
    var ds=year+'-'+String(month).padStart(2,'0')+'-'+String(d).padStart(2,'0');
    var v=0; actions.forEach(function(a){if(a.ts&&a.ts.startsWith(ds)) v++;});
    values.push(v); total+=v;
  }
  _socShowDetail(
    weekLabel+' — '+String(startDay).padStart(2,'0')+' au '+String(endDay).padStart(2,'0'),
    total+' actions · cliquer sur un point pour le détail horaire',
    labels, values, 'rgba(220,60,60,1)',
    function(idx){
      var ds=year+'-'+String(month).padStart(2,'0')+'-'+labels[idx];
      _socShowHourDetail(actions,ds);
    }
  );
}

function _socShowHourDetail(actions, dateStr) {
  var map=_socBuildHourMap(actions, dateStr);
  var labels=[], values=[];
  for(var h=0;h<24;h++){
    labels.push(String(h).padStart(2,'0')+'h');
    values.push(map[h]||0);
  }
  var total=values.reduce(function(a,b){return a+b;},0);
  var hourCvs=document.getElementById('soc-chart-day');
  var hourLbl=document.getElementById('soc-day-label');
  var hourDate=document.getElementById('soc-day-label-date');
  if(!hourCvs) return;
  if(total===0){ _disp(hourCvs, false); _disp(hourLbl, false); return; }
  _disp(hourCvs, true, 'block');
  _disp(hourLbl, true, 'block');
  if(hourDate) hourDate.textContent=dateStr+' — '+total+' actions';
  _socLineChart(hourCvs, labels, values, 'rgba(100,200,255,1)', null);
}

function socMonthNav(dir) {
  _socChartOffset += dir;
  if (_socChartOffset > 0) _socChartOffset = 0;
  var nextBtn = document.getElementById('soc-next-month');
  if (nextBtn) nextBtn.disabled = (_socChartOffset >= 0);
  var now=new Date();
  var y=now.getFullYear(), m=now.getMonth()+1+_socChartOffset;
  while(m<1){m+=12;y--;} while(m>12){m-=12;y++;}
  var el=document.getElementById('soc-month-label');
  if(el) el.textContent=y+'-'+String(m).padStart(2,'0');
  _socRenderWeekCards(_socChartActions, y, m);
  var dw=document.getElementById('soc-detail-wrap');
  _disp(dw, false);
}

function _socDrawCharts(actions) {
  _socChartActions = actions || [];
  var now=new Date();
  var y=now.getFullYear(), m=now.getMonth()+1+_socChartOffset;
  while(m<1){m+=12;y--;} while(m>12){m-=12;y++;}
  var el=document.getElementById('soc-month-label');
  if(el) el.textContent=y+'-'+String(m).padStart(2,'0');
  var nextBtn=document.getElementById('soc-next-month');
  if(nextBtn) nextBtn.disabled=(_socChartOffset>=0);
  _socRenderWeekCards(_socChartActions, y, m);
  // Affiche le mois complet par défaut
  _socShowMonthDetail(_socChartActions, y, m);
}

// ══════════════════════════════════════
// HORLOGE
// ══════════════════════════════════════
function tick() {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('fr-FR',{hour12:false});
}
setInterval(tick, _TICK_INTERVAL_MS); tick();

// ══════════════════════════════════════
// GRAPHIQUES
// ══════════════════════════════════════
const HISTORY = 60;
const graphs = {
  gpu:   {id:'chart-gpu',  lbl:'g-lbl-gpu',  color:_cssVar('--cyan'),   data:[], max:100},
  vram:  {id:'chart-vram', lbl:'g-lbl-vram', color:_cssVar('--blue'),   data:[], max:1},
  temp:  {id:'chart-temp', lbl:'g-lbl-temp', color:_cssVar('--green'),  data:[], max:100},
  power: {id:'chart-power',lbl:'g-lbl-power',color:_cssVar('--purple'), data:[], max:1},
};

function drawChart(key, value) {
  const g = graphs[key];
  g.data.push(value);
  if (g.data.length > HISTORY) g.data.shift();
  if (g.max < value * 1.1) g.max = value * 1.1;

  const canvas = document.getElementById(g.id);
  if (!canvas) return;
  const dpr = window.devicePixelRatio||1;
  const W = canvas.offsetWidth, H = canvas.offsetHeight||70;
  canvas.width = W*dpr; canvas.height = H*dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr,dpr);

  ctx.strokeStyle='#00cfff08'; ctx.lineWidth=1;
  for(let i=1;i<4;i++){const y=(H/4)*i;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
  if(g.data.length<2)return;

  const step=W/(HISTORY-1);
  const pts=g.data.map((v,i)=>({x:i*step,y:H-(v/g.max)*H*0.92}));

  const grad=ctx.createLinearGradient(0,0,0,H);
  grad.addColorStop(0,g.color+'55'); grad.addColorStop(1,g.color+'00');
  ctx.beginPath();ctx.moveTo(pts[0].x,H);
  pts.forEach(p=>ctx.lineTo(p.x,p.y));
  ctx.lineTo(pts[pts.length-1].x,H);ctx.closePath();
  ctx.fillStyle=grad;ctx.fill();

  ctx.beginPath();ctx.moveTo(pts[0].x,pts[0].y);
  for(let i=1;i<pts.length;i++){
    const mx=(pts[i-1].x+pts[i].x)/2;
    ctx.bezierCurveTo(mx,pts[i-1].y,mx,pts[i].y,pts[i].x,pts[i].y);
  }
  ctx.strokeStyle=g.color;ctx.lineWidth=1.5;ctx.shadowColor=g.color;ctx.shadowBlur=6;ctx.stroke();ctx.shadowBlur=0;

  const last=pts[pts.length-1];
  ctx.beginPath();ctx.arc(last.x,last.y,3,0,Math.PI*2);
  ctx.fillStyle='#fff';ctx.shadowColor=g.color;ctx.shadowBlur=10;ctx.fill();ctx.shadowBlur=0;
}

// ══════════════════════════════════════
// GPU MONITOR
// ══════════════════════════════════════
const CIRC=289.0;
function setArc(id,pct){const el=document.getElementById(id);if(el)el.style.strokeDashoffset=CIRC-(Math.min(pct,100)/100)*CIRC;}
function setArcColor(id,color){const el=document.getElementById(id);if(el){el.style.stroke=color;el.style.filter=`drop-shadow(0 0 5px ${color})`;}}
function dynColor(v,w,c){if(v>=c)return{text:'c-red',bar:'b-red',hex:_cssVar('--red')};if(v>=w)return{text:'c-yellow',bar:'b-yellow',hex:_cssVar('--yellow')};return{text:'c-green',bar:'b-green',hex:_cssVar('--green')};}
function setBar(id,pct,cls){const el=document.getElementById(id);if(el){el.style.width=Math.min(pct,100)+'%';el.className='bar-fill '+cls;}}
function setMiniBar(id,pct,cls){const el=document.getElementById(id);if(el){el.style.width=Math.min(pct,100)+'%';el.className='mini-gauge-fill '+cls;}}

let ticks=0;
function _updateMonArcs(d){
  const gc=dynColor(d.gpu_util,50,85);
  setArc('arc-gpu',d.gpu_util); setArcColor('arc-gpu',gc.hex);
  const _tgu=document.getElementById('txt-gpu-util'); if(_tgu){_tgu.textContent=d.gpu_util+'%';_tgu.style.fill=gc.hex;}
  const vp=d.mem_used/d.mem_total*100;
  setArc('arc-vram',vp);
  document.getElementById('txt-vram-used').textContent=d.mem_used.toFixed(1)+' GB';
  document.getElementById('txt-vram-total').textContent='/ '+d.mem_total.toFixed(0)+' GB';
  const tc=dynColor(d.temp,60,80);
  setArc('arc-temp',d.temp); setArcColor('arc-temp',tc.hex);
  const _ttt=document.getElementById('txt-temp'); if(_ttt){_ttt.textContent=d.temp+'°';_ttt.style.fill=tc.hex;}
  const pp=d.power_draw/d.power_limit*100;
  setArc('arc-power',pp);
  document.getElementById('txt-power').textContent=d.power_draw.toFixed(0)+'W';
  const cc=dynColor(d.cpu,50,85);
  setArc('arc-cpu',d.cpu); setArcColor('arc-cpu',cc.hex);
  const _tcu=document.getElementById('txt-cpu'); if(_tcu){_tcu.textContent=d.cpu.toFixed(0)+'%';_tcu.style.fill=cc.hex;}
  const rp=d.ram_used/d.ram_total*100;
  setArc('arc-ram',rp);
  document.getElementById('txt-ram-used').textContent=d.ram_used.toFixed(1)+' GB';
  document.getElementById('txt-ram-total').textContent='/ '+d.ram_total.toFixed(0)+' GB';
  return {gc,vp,tc,pp,cc,rp};
}
function _updateMonGraphsAndPanels(d,gc,vp,tc,pp,cc){
  graphs.vram.max=d.mem_total; graphs.power.max=d.power_limit||500;
  drawChart('gpu',d.gpu_util); drawChart('vram',d.mem_used);
  drawChart('temp',d.temp);   drawChart('power',d.power_draw);
  document.getElementById('g-lbl-gpu').textContent=d.gpu_util+'%';
  document.getElementById('g-lbl-vram').textContent=d.mem_used.toFixed(1)+' GB';
  document.getElementById('g-lbl-temp').textContent=d.temp+'°C';
  document.getElementById('g-lbl-power').textContent=d.power_draw.toFixed(0)+' W';
  document.getElementById('d-gpu-util').textContent=d.gpu_util+'%'; setBar('b-gpu-util',d.gpu_util,gc.bar);
  document.getElementById('d-enc').textContent=d.enc_util+'%';       setBar('b-enc',d.enc_util,'b-cyan');
  document.getElementById('d-dec').textContent=d.dec_util+'%';       setBar('b-dec',d.dec_util,'b-blue');
  document.getElementById('d-clk-gpu').textContent=d.clk_gpu+' MHz';setBar('b-clk-gpu',d.clk_gpu/30,'b-cyan');
  document.getElementById('d-clk-mem').textContent=d.clk_mem+' MHz';setBar('b-clk-mem',d.clk_mem/150,'b-blue');
  document.getElementById('d-temp').textContent=d.temp+'°C';         setBar('b-temp',d.temp,tc.bar);
  document.getElementById('d-power').textContent=d.power_draw.toFixed(0)+' W / '+d.power_limit.toFixed(0)+' W'; setBar('b-power',pp,'b-purple');
  document.getElementById('d-fan').textContent=d.fan!==null?d.fan+'%':'N/A'; setBar('b-fan',d.fan||0,'b-blue');
  document.getElementById('d-vram').textContent=d.mem_used.toFixed(1)+' GB'; setBar('b-vram',vp,'b-blue');
  document.getElementById('d-vram-total').textContent=d.mem_total.toFixed(1)+' GB';
  document.getElementById('d-vram-free').textContent=d.mem_free.toFixed(1)+' GB';
  document.getElementById('d-cpu').textContent=d.cpu.toFixed(0)+'%'; setBar('b-cpu-p',d.cpu,cc.bar);
  document.getElementById('d-cpu-count').textContent=d.cpu_count;
  document.getElementById('d-cpu-freq').textContent=d.cpu_freq+' MHz';
  document.getElementById('d-uptime').textContent=d.uptime;
  document.getElementById('d-net-up').textContent=d.net_up.toFixed(2)+' MB/s'; setBar('b-net-up',Math.min(d.net_up/10*100,100),'b-green');
  document.getElementById('d-net-dn').textContent=d.net_dn.toFixed(2)+' MB/s'; setBar('b-net-dn',Math.min(d.net_dn/10*100,100),'b-cyan');
  document.getElementById('d-disk-r').textContent=d.disk_r.toFixed(0)+' MB/s'; setBar('b-disk-r',Math.min(d.disk_r/5*100,100),'b-cyan');
  document.getElementById('d-disk-w').textContent=d.disk_w.toFixed(0)+' MB/s'; setBar('b-disk-w',Math.min(d.disk_w/5*100,100),'b-purple');
}
function _updateMonSidebar(d,vp,pp,rp){
  setMiniBar('m-gpu',d.gpu_util,'b-cyan');   document.getElementById('mv-gpu').textContent=d.gpu_util+'%';
  const _nf=document.getElementById('hud-neural-fill');
  const _nv=document.getElementById('hud-neural-val');
  if(_nf) _nf.style.width=d.gpu_util+'%';
  if(_nv) _nv.textContent=d.gpu_util+'%';
  setMiniBar('m-vram',vp,'b-blue');           document.getElementById('mv-vram').textContent=d.mem_used.toFixed(1)+' GB';
  setMiniBar('m-temp',d.temp,'b-green');      document.getElementById('mv-temp').textContent=d.temp+'°';
  setMiniBar('m-power',pp,'b-purple');        document.getElementById('mv-power').textContent=d.power_draw.toFixed(0)+'W';
  setMiniBar('m-cpu',d.cpu,'b-green');        document.getElementById('mv-cpu').textContent=d.cpu.toFixed(0)+'%';
  setMiniBar('m-ram',rp,'b-blue');            document.getElementById('mv-ram').textContent=d.ram_used.toFixed(1)+' GB';
}
function _updateMonRtxPanel(d,pp){
  const mu=d.mem_util??0;
  const bw=d.clk_mem?Math.round(d.clk_mem*256*2/8/1000):0;
  const marge=d.power_limit?(d.power_limit-d.power_draw):0;
  const eff=d.power_draw>1?(d.gpu_util/d.power_draw*100).toFixed(1):'—';
  document.getElementById('d-mem-util').textContent=mu+'%';         setBar('b-mem-util',mu,'b-blue');
  document.getElementById('d-membw').textContent=bw+' GB/s';        setBar('b-membw',Math.min(bw/960*100,100),'b-cyan');
  document.getElementById('d-pow-budget').textContent=pp.toFixed(0)+'%'; setBar('b-pow-budget',pp,'b-purple');
  const pst=d.p_state!==null&&d.p_state!==undefined?'P'+d.p_state:'—';
  document.getElementById('d-pstate').textContent=pst;
  const thrEl=document.getElementById('d-throttle');
  if(thrEl){thrEl.textContent=d.throttle?'⚠ ACTIF':'✓ NORMAL';thrEl.className='stat-val '+(d.throttle?'c-warn':'c-green');}
  const pcieEl=document.getElementById('d-pcie');
  if(pcieEl) pcieEl.textContent=d.pcie_gen&&d.pcie_width?`Gen${d.pcie_gen} ×${d.pcie_width}`:'—';
  document.getElementById('d-pow-adv').textContent=d.power_draw.toFixed(0)+' W';  setBar('b-pow-adv',pp,'b-purple');
  document.getElementById('d-pow-limit').textContent=d.power_limit?d.power_limit.toFixed(0)+' W':'—';
  document.getElementById('d-pow-marge').textContent=marge>0?'+'+marge.toFixed(0)+' W':marge.toFixed(0)+' W';
  document.getElementById('d-eff').textContent=eff!=='—'?eff+' %/W':'—';
  document.getElementById('d-vram-adv').textContent=d.mem_free?d.mem_free.toFixed(1)+' GB':'—';
}
function _updateMonCuda(d){
  const cudaVerEl=document.getElementById('d-cuda-ver');
  if(cudaVerEl&&d.cuda_ver) cudaVerEl.textContent=d.cuda_ver;
  const drvVerEl=document.getElementById('d-drv-ver');
  if(drvVerEl&&d.driver_ver) drvVerEl.textContent=d.driver_ver;
  if(d.max_clk_gpu){
    document.getElementById('d-max-clk-gpu').textContent=d.max_clk_gpu+' MHz';
    setBar('b-max-clk-gpu',Math.min(d.max_clk_gpu/30,100),'b-cyan');
  }
  if(d.max_clk_mem){
    document.getElementById('d-max-clk-mem').textContent=d.max_clk_mem+' MHz';
    setBar('b-max-clk-mem',Math.min(d.max_clk_mem/150,100),'b-blue');
  }
  const trEl2=document.getElementById('d-throttle-reason');
  if(trEl2&&d.throttle_reason!==null&&d.throttle_reason!==undefined){
    trEl2.textContent=d.throttle_reason;
    trEl2.className='stat-val '+(d.throttle_reason==='NONE'||d.throttle_reason==='IDLE'?'c-green':'c-warn');
  }
  if(d.temp_warn!=null){
    var tw=document.getElementById('d-temp-warn');
    tw.textContent=d.temp_warn+' °C';
    tw.classList.toggle('temp-danger', d.temp>=d.temp_warn);
    tw.classList.toggle('temp-warn',   d.temp< d.temp_warn);
  }
  if(d.temp_slow) document.getElementById('d-temp-slow').textContent=d.temp_slow+' °C';
  if(d.temp_shut) document.getElementById('d-temp-shut').textContent=d.temp_shut+' °C';
  if(d.cuda_proc_count!==undefined) document.getElementById('d-cuda-procs-count').textContent=d.cuda_proc_count;
  if(d.cuda_procs!==undefined) document.getElementById('d-cuda-procs').textContent=d.cuda_procs;
  const cudaBadge=document.getElementById('dsp-cuda-badge');
  const cudaLabel=document.getElementById('dsp-cuda-label');
  const cudaState=document.getElementById('dsp-cuda-state');
  const cudaDot=document.getElementById('dsp-cuda-dot');
  if(cudaBadge&&d.cuda_ver&&d.cuda_ver!=='N/A'){
    cudaBadge.classList.remove('dsp-cuda-cpu'); cudaBadge.classList.add('dsp-cuda-on');
    if(cudaDot){cudaDot.classList.add('cuda-dot-on');cudaDot.classList.remove('cuda-dot-cpu');}
    if(cudaLabel) cudaLabel.textContent='CUDA '+d.cuda_ver;
    if(cudaState){cudaState.textContent='● ON';cudaState.classList.add('cuda-lbl-on');cudaState.classList.remove('cuda-lbl-cpu');}
  }else if(cudaBadge){
    cudaBadge.classList.remove('dsp-cuda-on'); cudaBadge.classList.add('dsp-cuda-cpu');
    if(cudaDot){cudaDot.classList.add('cuda-dot-cpu');cudaDot.classList.remove('cuda-dot-on');}
    if(cudaLabel) cudaLabel.textContent='CUDA';
    if(cudaState){cudaState.textContent='○ CPU';cudaState.classList.add('cuda-lbl-cpu');cudaState.classList.remove('cuda-lbl-on');}
  }
  _fxUpdateCudaScreen(d.cuda_ver);
}
function updateMonitor(d){
  ticks++;
  const el=document.getElementById('gpu-name'); if(el)el.textContent=d.name;
  const fu=document.getElementById('f-uptime'); if(fu)fu.textContent='REFRESH : '+ticks+'s';
  const {gc,vp,tc,pp,cc,rp}=_updateMonArcs(d);
  _updateMonGraphsAndPanels(d,gc,vp,tc,pp,cc);
  _updateMonSidebar(d,vp,pp,rp);
  _updateMonRtxPanel(d,pp);
  _updateMonCuda(d);
}

var _statsPollTimer = null;
async function pollStats(){
  try{const r=await fetch('/api/stats');const d=await r.json();updateMonitor(d);}catch(e){}
  _statsPollTimer = setTimeout(pollStats,_POLL_STATS_MS);
}
pollStats();

// ── VRAM LLM Ollama ────────────────────────────────────────────────────
var _VRAM_TOTAL  = 0; // sera rempli par l'API (pynvml réel)
var _VRAM_MODEL_COLORS = {
  'phi4':     _cssVar('--cyan'),
  'qwen':     _cssVar('--orange2'),
  'gemma':    _cssVar('--green'),
  'mxbai':    _cssVar('--purple'),
  'deepseek': _cssVar('--yellow'),
  'llava':    _cssVar('--pink'),
};
function _vramColor(name) {
  var n = name.toLowerCase();
  for (var k in _VRAM_MODEL_COLORS) { if (n.indexOf(k) !== -1) return _VRAM_MODEL_COLORS[k]; }
  return '#4488ff';
}

function _fmtBytes(b) {
  if (b >= 1073741824) return (b/1073741824).toFixed(1)+' GB';
  if (b >= 1048576)    return (b/1048576).toFixed(0)+' MB';
  return b+' B';
}

function _vramRenderSwap(totalSwap) {
  var swWrap = document.getElementById('vram-llm-swap-wrap');
  var swBar  = document.getElementById('vram-llm-swap-bar');
  var swLbl  = document.getElementById('vram-llm-swap-lbl');
  if (!swWrap || !swBar || !swLbl) return;
  if (totalSwap > 0) {
    swWrap.style.display = 'flex';
    var swPct = Math.min(100, (totalSwap / (32 * 1024**3)) * 100);
    swBar.style.setProperty('--swap-pct', swPct + '%');
    swLbl.textContent = 'SWAP ' + _fmtBytes(totalSwap);
  } else {
    swWrap.style.display = 'none';
  }
}

var _VRAM_ROLE_COLORS = {SOC:'#00e5ff', GÉNÉRAL:'#4caf50', CODE:'#ff9800', RAG:'#cc66ff'};

function _vramBuildModelRows(models, cap, totalVram) {
  var rows = models.map(function(m) {
    var col = _vramColor(m.name);
    var rc  = _VRAM_ROLE_COLORS[m.role] || col;
    var pct = m.pct || 0;
    var meta = [];
    if (m.params) meta.push(m.params);
    if (m.quant)  meta.push(m.quant);
    var keep = (m.expires_at && m.expires_at !== '0001-01-01T00:00:00Z')
      ? 'exp. ' + new Date(m.expires_at).toLocaleTimeString('fr-FR', {hour:'2-digit',minute:'2-digit'})
      : '∞';
    var swapTxt = m.size_swap > 0 ? ' · <span class="vram-swap-txt">SWAP '+_fmtBytes(m.size_swap)+'</span>' : '';
    var label = '<span class="vram-role-lbl" style="--rc:'+rc+'">['+m.role+']</span>'
              + ' <span class="vram-model-name">'+m.name.split('/').pop()+'</span>'
              + (meta.length ? ' <span class="vram-model-meta">'+meta.join(' · ')+'</span>' : '')
              + ' <span class="vram-model-keep">'+keep+'</span>';
    var val   = '<span class="vram-size-val" style="--vc:'+col+'">'+_fmtBytes(m.size_vram)+'</span>'
              + ' <span class="vram-model-pct">'+pct+'%</span>'
              + swapTxt;
    var swapPct = cap ? Math.min(100 - pct, Math.round(m.size_swap / cap * 100)) : 0;
    var swapSeg = swapPct > 0
      ? '<div class="bar-fill vram-swap-seg" style="width:'+swapPct+'%"><div class="vram-swap-shimmer"></div></div>'
      : '';
    return '<div class="bar-row">'
         +   '<div class="bar-head">'+label+'<span>'+val+'</span></div>'
         +   '<div class="bar-track bar-track--flex">'
         +     '<div class="bar-fill'+(m.is_embed?' bar-fill--embed':'')+'" style="width:'+pct+'%;--bar-col:'+col+'"></div>'
         +     swapSeg
         +   '</div>'
         + '</div>';
  });
  var freePct = cap ? Math.max(0, Math.round((cap - totalVram) / cap * 100)) : 0;
  rows.push('<div class="bar-row bar-row--libre">'
    + '<div class="bar-head"><span class="vram-libre-lbl">LIBRE</span><span class="vram-libre-val">'+_fmtBytes(Math.max(0, cap - totalVram))+' · '+freePct+'%</span></div>'
    + '<div class="bar-track"><div class="bar-fill vram-libre-fill" style="width:'+freePct+'%"></div></div>'
    + '</div>');
  return rows;
}

function _vramRenderLegend(d, models, legend, cap, totalVram) {
  if (models.length === 0) {
    if (d.active_model) {
      var col2 = _vramColor(d.active_model);
      legend.innerHTML = '<span class="vram-llm-item vram-llm-item--pending"><span class="vram-llm-dot" style="--mc-bg:'+col2+'55;--mc-border:'+col2+'"></span>'
                       + d.active_model.split('/').pop() + ' &nbsp;<b class="vram-llm-pending-lbl">en attente</b></span>';
    } else {
      legend.innerHTML = '<span class="vram-llm-idle">Aucun modèle chargé</span>';
    }
  } else {
    legend.innerHTML = _vramBuildModelRows(models, cap, totalVram).join('');
  }
}

function _vramUpdateStats(d) {
  var modeEl = document.getElementById('vram-stat-mode');
  var toksEl = document.getElementById('vram-stat-toks');
  var ctxEl  = document.getElementById('vram-stat-ctx');
  if (modeEl) {
    var mLabel = {soc:'SOC → phi4:14b', general:'GÉNÉRAL → gemma4:latest', code:'CODE → qwen2.5-coder:14b', code_reasoning:'C·R → qwen3:8b'};
    modeEl.textContent = mLabel[_jarvisMode] || _jarvisMode.toUpperCase();
  }
  if (toksEl && d.tokens_per_sec != null) toksEl.textContent = d.tokens_per_sec > 0 ? d.tokens_per_sec + ' tok/s' : '—';
  if (ctxEl  && d.num_ctx        != null) ctxEl.textContent  = d.num_ctx > 0 ? d.num_ctx.toLocaleString('fr-FR') + ' tok' : '—';
}

function updateVramLlm(d) {
  var bar    = document.getElementById('vram-llm-bar');
  var legend = document.getElementById('vram-llm-legend');
  var usedEl = document.getElementById('vram-llm-used');
  var swapEl = document.getElementById('vram-llm-swap');
  var alert  = document.getElementById('vram-llm-alert');
  if (!bar) return;

  var models    = d.models || [];
  var totalVram = d.total_vram || 0;
  var totalSwap = d.total_swap || 0;
  if (d.vram_total_bytes) _VRAM_TOTAL = d.vram_total_bytes;
  var cap      = _VRAM_TOTAL || 1;
  var overflow = totalVram > cap;

  // Barre segmentée
  bar.innerHTML = '';
  if (models.length === 0) {
    if (d.active_model) {
      var col = _vramColor(d.active_model);
      var lbl = d.active_model.split(':')[0].replace('phi4-reasoning','phi4').replace('qwen2.5-coder','qwen').slice(0,10);
      bar.innerHTML = '<div class="vram-llm-seg vram-llm-pending" style="--seg-bg:'+col+'18;--seg-border:'+col+'66" title="'+d.active_model+' — en attente">'+lbl+'</div><div class="vram-llm-free" style="width:42%"></div>';
    } else {
      bar.innerHTML = '<div class="vram-llm-free" title="Libre"></div>';
    }
  } else {
    models.forEach(function(m) {
      var pct = Math.min(100, (m.size_vram / cap) * 100);
      var col = _vramColor(m.name);
      var label = m.name.split(':')[0].replace('phi4-reasoning','phi4').replace('qwen2.5-coder','qwen').replace('mxbai-embed','embed').replace('nomic-embed','embed').slice(0,10);
      var seg = document.createElement('div');
      seg.className = 'vram-llm-seg' + (overflow ? ' overflow' : '') + (m.is_embed ? ' embed' : '');
      seg.style.width = pct + '%';
      seg.style.background = col;
      var ttParts = ['['+m.role+'] ' + m.name, _fmtBytes(m.size_vram) + ' VRAM (' + (m.pct||0) + '%)'];
      if (m.params)  ttParts.push(m.params);
      if (m.quant)   ttParts.push(m.quant);
      if (m.size_swap > 0) ttParts.push('swap: ' + _fmtBytes(m.size_swap));
      if (m.expires_at && m.expires_at !== '0001-01-01T00:00:00Z') ttParts.push('expire: ' + new Date(m.expires_at).toLocaleTimeString('fr-FR'));
      seg.title = ttParts.join(' · ');
      seg.textContent = pct > 8 ? label : '';
      bar.appendChild(seg);
    });
    var freePct = Math.max(0, ((cap - totalVram) / cap) * 100);
    var free = document.createElement('div');
    free.className = 'vram-llm-free';
    free.style.width = freePct + '%';
    bar.appendChild(free);
  }

  // Légende bar-row
  _vramRenderLegend(d, models, legend, cap, totalVram);

  // Footer
  if (usedEl) usedEl.textContent = _fmtBytes(totalVram);
  var capEl = document.getElementById('vram-llm-cap');
  if (capEl && cap) capEl.textContent = '/ ' + _fmtBytes(cap);
  if (swapEl) swapEl.textContent = totalSwap > 0 ? _fmtBytes(totalSwap) : '0 MB';

  // Alerte débordement
  if (alert) alert.style.display = overflow ? 'inline' : 'none';
  if (bar.parentElement) bar.parentElement.parentElement && (bar.parentElement.style.borderColor = overflow ? '#ff444466' : '');

  // Stats + SWAP
  _vramUpdateStats(d);
  _vramRenderSwap(totalSwap);
}

var _vramPollTimer = null;
async function pollVramLlm() {
  try { var r = await fetch('/api/vram'); var d = await r.json(); updateVramLlm(d); } catch(e) {}
  _vramPollTimer = setTimeout(pollVramLlm, _VRAM_POLL_MS);
}
function _refreshVramNow() { clearTimeout(_vramPollTimer); pollVramLlm(); }
pollVramLlm();

// → AUDIO VIZ extrait — static/js/audio_viz.js (chantier dette 2026-05-14)
// ══════════════════════════════════════
// CHAT
// ══════════════════════════════════════
const history = [];
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

// ══════════════════════════════════════
// DIAGNOSTIC SYSTÈME
// ══════════════════════════════════════
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

// ══════════════════════════════════════
// SETTINGS GPU HEALTH
// ══════════════════════════════════════
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

// → DSP AUDIO SYSTEM extrait — static/js/dsp_audio.js (chantier dette 2026-05-14)
// → EQ PARAMÉTRIQUE extrait — static/js/eq_parametric.js (chantier dette 2026-05-14)
// ══════════════════════════════════════
// AI AUDIO RACK — DSP INTÉGRÉ
// ══════════════════════════════════════
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
// → BOOT SEQUENCE + RACK FX + INIT extraits — static/js/boot_init.js (chantier dette 2026-05-14)
