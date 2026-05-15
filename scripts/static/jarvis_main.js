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
// → CHAT UI extrait (history, addMessage, _esc, markdown, Monaco, mémoire LT) — static/js/chat_ui.js (chantier dette 2026-05-15)
// → CHAT CORE extrait (sendMessage, SSE, modes, diagnostic, vision, Ollama poll) — static/js/chat_core.js (chantier dette 2026-05-15)
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
// → AI AUDIO RACK + helpers EQ extraits — static/js/audio_rack.js (chantier dette 2026-05-15)
// → TÂCHES TAB + WELCOME extraits — static/js/tasks_tab.js + static/js/welcome.js (chantier dette 2026-05-14)
// → BOOT SEQUENCE + RACK FX + INIT extraits — static/js/boot_init.js (chantier dette 2026-05-14)
