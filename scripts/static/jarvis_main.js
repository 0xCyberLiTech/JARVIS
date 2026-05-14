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

// ══════════════════════════════════════
// WEB AUDIO API — VOICE VISUALIZATION STÉRÉO
// ══════════════════════════════════════
// Création différée — évite un crash si le navigateur bloque avant interaction
let audioCtx = null, analyser = null, analyserL = null, analyserR = null;
let dataArray = new Uint8Array(128);
let fftL = new Uint8Array(512), fftR = new Uint8Array(512);
let timL = new Float32Array(1024), timR = new Float32Array(1024);

function _ensureAudioCtx() {
  if (audioCtx) return true;
  try {
    audioCtx  = new (window.AudioContext || window.webkitAudioContext)();
    analyser  = audioCtx.createAnalyser();
    analyser.fftSize = 256; analyser.smoothingTimeConstant = 0.75;
    analyser.connect(audioCtx.destination);
    analyserL = audioCtx.createAnalyser(); analyserL.fftSize = 4096; analyserL.smoothingTimeConstant = 0.8;
    analyserR = audioCtx.createAnalyser(); analyserR.fftSize = 4096; analyserR.smoothingTimeConstant = 0.8;
    // Merger stéréo : analyserL/R → analyser → destination (signal passe DANS les analyseurs)
    const _stereoMerger = audioCtx.createChannelMerger(2);
    analyserL.connect(_stereoMerger, 0, 0);
    analyserR.connect(_stereoMerger, 0, 1);
    _stereoMerger.connect(analyser);
    // Haas persistant : source mono → analyserL (direct) + _haasDelayNode → _haasGainNode → analyserR
    _haasDelayNode = audioCtx.createDelay(0.05);
    _haasDelayNode.delayTime.value = 0.018;
    _haasGainNode = audioCtx.createGain();
    _haasGainNode.gain.value = 0.85;
    _haasDelayNode.connect(_haasGainNode);
    _haasGainNode.connect(analyserR);
    dataArray = new Uint8Array(analyser.frequencyBinCount);
    fftL = new Uint8Array(analyserL.frequencyBinCount);
    fftR = new Uint8Array(analyserR.frequencyBinCount);
    timL = new Float32Array(analyserL.fftSize);
    timR = new Float32Array(analyserR.fftSize);
    return true;
  } catch(e) { return false; }
}

let speaking = false;
let _analyserEnabled = true;

// ── Resume audioCtx proactif quand l'onglet redevient actif ──
// Browser suspend l'AudioContext en background → latence au retour. Resume préventif évite ça.
function _audioCtxResumeProactive() {
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => { /* permission/policy denial — silencieux */ });
  }
}
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') _audioCtxResumeProactive();
});
window.addEventListener('focus', _audioCtxResumeProactive);

// ── Connexion source stéréo dans le graphe Web Audio ──
function _connectStereoSource(source) {
  const numCh = source.buffer ? source.buffer.numberOfChannels : 1;
  if (numCh >= 2) {
    // Stéréo : source → splitter → analyserL/R → stereoMerger → analyser → destination
    const splitter = audioCtx.createChannelSplitter(2);
    source.connect(splitter);
    splitter.connect(analyserL, 0);
    splitter.connect(analyserR, 1);
  } else {
    // Mono → Haas persistant sur R
    source.connect(analyserL);
    if (_haasDelayNode) source.connect(_haasDelayNode);
    else                source.connect(analyserR);
  }
}

// ══════════════════════════════════════
// STEREOGRAM 3D — PERSPECTIVE STEREO FIELD
// ══════════════════════════════════════
let _specRaf = null;
let _peakHoldL = null;
let _peakHoldR = null;
const _PEAK_DECAY  = 0.008;
const _SAMPLE_RATE    = 48000;  // taux d'échantillonnage cible DSP — edge-tts, DeepFilterNet, AudioContext fallback
const _FREQ_MIN    = 20;
const _FREQ_MAX    = _SAMPLE_RATE / 2;  // Nyquist 24kHz
let _freqLabelsInit = false;


// ── GR Meter canvas — compresseur gain reduction ──
let _grSmooth = 0;
function _drawGrMeter(reduction) {
  const cv = document.getElementById('rack-gr-canvas');
  if (!cv) return;
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  const GR_MAX = 24;   // max dB de réduction affichée
  const SEG = 80;
  const PAD_L = 8, PAD_R = 8, PAD_T = 6, PAD_B = 20;
  const MW = W - PAD_L - PAD_R;
  const MH = H - PAD_T - PAD_B;
  const SEG_W = MW / SEG;
  const GAP = 1;

  // Smooth
  const target = Math.min(GR_MAX, Math.abs(reduction || 0));
  _grSmooth += (target - _grSmooth) * 0.18;

  ctx.fillStyle = '#010608';
  ctx.fillRect(0, 0, W, H);

  // Background groove
  ctx.fillStyle = '#020c12';
  ctx.fillRect(PAD_L, PAD_T, MW, MH);

  // Lit segments (right→left as GR increases)
  const litSegs = Math.round((_grSmooth / GR_MAX) * SEG);
  for (let i = 0; i < SEG; i++) {
    const x = PAD_L + (SEG - 1 - i) * SEG_W;  // right to left
    const lit = i < litSegs;
    const pct = i / SEG;
    let color;
    if (!lit) {
      color = pct > 0.6 ? 'rgba(30,5,0,0.8)' : pct > 0.3 ? 'rgba(20,12,0,0.8)' : 'rgba(10,15,5,0.8)';
    } else {
      if (pct > 0.70) color = '#ff2200';
      else if (pct > 0.45) color = '#ff7700';
      else if (pct > 0.20) color = '#ffaa00';
      else color = '#ddcc00';
      ctx.shadowColor = color;
      ctx.shadowBlur = 5;
    }
    ctx.fillStyle = color;
    ctx.fillRect(x + GAP, PAD_T + 1, SEG_W - GAP - 1, MH - 2);
    ctx.shadowBlur = 0;
  }

  // Scale: 0, -3, -6, -9, -12, -18, -24 dB (right to left)
  const marks = [0, -3, -6, -9, -12, -18, -24];
  ctx.font = '8px Share Tech Mono, monospace';
  ctx.textAlign = 'center';
  marks.forEach(db => {
    const pct = Math.abs(db) / GR_MAX;
    const x = PAD_L + MW * (1 - pct);
    ctx.fillStyle = db < -12 ? 'rgba(255,80,0,.5)' : db < -6 ? 'rgba(255,150,0,.4)' : 'rgba(200,180,0,.35)';
    ctx.fillRect(x - 0.5, PAD_T + MH, 1, 4);
    ctx.fillStyle = 'rgba(140,120,60,.55)';
    ctx.fillText(db === 0 ? '0' : String(db), x, H - 4);
  });
  // "GR dB" label left
  ctx.textAlign = 'left';
  ctx.fillStyle = 'rgba(255,150,0,.2)';
  ctx.fillText('GR dB', PAD_L, H - 4);
}

// ── VU-mètre professionnel stéréo avec maintien des crêtes ──
let _vuHoldL = 0, _vuHoldR = 0;
let _vuHoldTL = 0, _vuHoldTR = 0;
let _vuHoldVL = 0, _vuHoldVR = 0;
let _vuSubL   = 0, _vuSubR   = 0;   // slow-decay peak for sub-bars
let _vuClipCL = 0, _vuClipCR = 0;   // near-clip hit counters
const _VU_HOLD_FRAMES = 55;
const _VU_HOLD_GRAV   = 0.00035;
const _VU_HOLD_VMAX   = 0.06;
const _VU_DB_MIN = -54, _VU_DB_MAX = 6;
function _vuLin2db(v) { return v > 1e-8 ? 20 * Math.log10(v) : -Infinity; }
function _vuFmt(db, plus) { return !isFinite(db) ? '-∞' : (db >= 0 && plus ? '+' : '') + db.toFixed(2); }

function _vuUpdHold(peak, hold, holdT, holdV) {
  if (peak > hold) return [peak, 0, 0];
  holdT++;
  if (holdT > _VU_HOLD_FRAMES) { holdV = Math.min(holdV + _VU_HOLD_GRAV, _VU_HOLD_VMAX); hold = Math.max(0, hold - holdV); }
  return [hold, holdT, holdV];
}
function _vuDrawMain({ lp, y, rms, hold, holdT, clipC, label }) {
  const {ctx, PAD_L, MW, BM, BS, xY, xR} = lp;
  const dRms = _vuLin2db(rms), dHold = _vuLin2db(hold);
  const xRms = lp.dbX(dRms), xHold = lp.dbX(dHold);
  ctx.fillStyle = '#010810'; ctx.fillRect(PAD_L, y, MW, BM);
  ctx.fillStyle = 'rgba(100,70,0,.10)'; ctx.fillRect(xY, y+1, xR-xY, BM-2);
  ctx.fillStyle = 'rgba(80,0,0,.14)';   ctx.fillRect(xR, y+1, PAD_L+MW-xR, BM-2);
  if (xRms > PAD_L) {
    const x1 = Math.min(xRms, xY);
    if (x1 > PAD_L) {
      const gB = ctx.createLinearGradient(PAD_L, 0, xY, 0);
      gB.addColorStop(0, '#004870'); gB.addColorStop(0.55, '#0090c0'); gB.addColorStop(1, '#00b8e0');
      ctx.fillStyle = gB; ctx.fillRect(PAD_L, y+1, x1-PAD_L, BM-2);
    }
    if (xRms > xY) {
      const x2 = Math.min(xRms, xR);
      const gY = ctx.createLinearGradient(xY, 0, xR, 0);
      gY.addColorStop(0, '#b09000'); gY.addColorStop(1, '#e0b800');
      ctx.fillStyle = gY; ctx.fillRect(xY, y+1, x2-xY, BM-2);
    }
    if (xRms > xR) { ctx.fillStyle = '#c01010'; ctx.fillRect(xR, y+1, xRms-xR, BM-2); }
    ctx.fillStyle = 'rgba(255,255,255,.04)'; ctx.fillRect(PAD_L, y+1, xRms-PAD_L, 2);
  }
  ctx.fillStyle = 'rgba(220,170,0,.25)'; ctx.fillRect(xY-.5, y, 1, BM);
  ctx.fillStyle = 'rgba(255,40,0,.35)';  ctx.fillRect(xR-.5, y, 1, BM);
  const showH = holdT < _VU_HOLD_FRAMES + 80 && hold > 1e-4;
  if (showH) {
    const hCol = dHold > 0 ? '#ff5522' : dHold > -6 ? '#ffe040' : '#ffffff';
    ctx.shadowColor = hCol; ctx.shadowBlur = 10;
    ctx.fillStyle = hCol; ctx.fillRect(xHold-1, y+1, 2, BM-2); ctx.shadowBlur = 0;
  }
  ctx.font = 'bold 11px Orbitron,monospace'; ctx.fillStyle = '#00cfff77'; ctx.textAlign = 'center';
  ctx.fillText(label, PAD_L/2, y+BM*.62+3);
  const rx = PAD_L+MW+8;
  if (showH) {
    const hStr = _vuFmt(dHold, true) + ' dB' + (clipC > 0 ? ` (${Math.min(clipC,99)})` : '');
    const hCol = dHold > 0 ? '#ff3300' : dHold > -6 ? '#ffcc00' : '#00cfff99';
    ctx.font = 'bold 11px Share Tech Mono,monospace'; ctx.fillStyle = hCol; ctx.textAlign = 'left';
    ctx.fillText(hStr, rx, y+Math.round(BM*0.36));
  }
  const rmsCol = !isFinite(dRms) ? '#1a2a30' : dRms > 0 ? '#ff220088' : dRms > -6 ? '#ffcc0088' : '#00a8d488';
  ctx.font = '9px Share Tech Mono,monospace'; ctx.fillStyle = rmsCol; ctx.textAlign = 'left';
  ctx.fillText(_vuFmt(dRms, true) + ' dB', rx, y+Math.round(BM*0.82));
}
function _vuDrawSub(lp, y, rms, slowPeak) {
  const {ctx, PAD_L, MW, BS} = lp;
  const dRms = _vuLin2db(rms), dSlow = _vuLin2db(slowPeak);
  const xRms = lp.dbX(dRms), xSlow = lp.dbX(dSlow);
  ctx.fillStyle = '#010810'; ctx.fillRect(PAD_L, y, MW, BS);
  if (xRms > PAD_L) { ctx.fillStyle = '#0a2e50'; ctx.fillRect(PAD_L, y+1, xRms-PAD_L, BS-2); }
  if (xSlow > xRms) {
    const g = ctx.createLinearGradient(xRms, 0, xSlow, 0);
    g.addColorStop(0, '#6a1200'); g.addColorStop(1, '#b02800');
    ctx.fillStyle = g; ctx.fillRect(xRms, y+1, xSlow-xRms, BS-2);
    const crest = dSlow - dRms;
    if (isFinite(crest) && crest > 0.5) {
      ctx.font = '8px Share Tech Mono,monospace'; ctx.fillStyle = '#cc441188'; ctx.textAlign = 'center';
      ctx.fillText('[' + crest.toFixed(1) + ' dB]', (xRms+xSlow)/2, y+BS*.72+1);
    }
  }
  ctx.font = '9px Share Tech Mono,monospace'; ctx.fillStyle = '#00cfff55'; ctx.textAlign = 'left';
  ctx.fillText(_vuFmt(dRms, true) + ' dB', PAD_L+MW+8, y+Math.round(BS*0.62)+2);
}
function _vuDrawScale(lp, y) {
  const {ctx, PAD_L, MW, SCL} = lp;
  ctx.fillStyle = '#010810'; ctx.fillRect(PAD_L, y, MW, SCL);
  [-54,-51,-48,-45,-42,-39,-36,-33,-30,-27,-24,-21,-18,-15,-12,-9,-6,-3,0,3,6].forEach(db => {
    const x = lp.dbX(db), major = db % 6 === 0;
    ctx.fillStyle = db >= 0 ? 'rgba(255,55,0,.55)' : db > -6 ? 'rgba(255,190,0,.38)' : 'rgba(0,200,255,.22)';
    ctx.fillRect(x-.5, y, 1, major ? 4 : 2);
    if (major) {
      ctx.font = '8px Share Tech Mono,monospace'; ctx.textAlign = 'center';
      ctx.fillStyle = db >= 0 ? 'rgba(255,80,0,.75)' : 'rgba(0,175,215,.52)';
      ctx.fillText(db === 0 ? '0' : (db > 0 ? '+' : '')+db, x, y+SCL-1);
    }
  });
  ctx.font = '7px Orbitron,monospace'; ctx.fillStyle = '#1a3040'; ctx.textAlign = 'right';
  ctx.fillText('dB', PAD_L+MW-2, y+SCL-1);
}
function _vuDrawBalance(lp, y, rmsL, rmsR) {
  const {ctx, PAD_L, MW} = lp;
  const dL = _vuLin2db(rmsL), dR = _vuLin2db(rmsR);
  if (!isFinite(dL) && !isFinite(dR)) return;
  const bal = isFinite(dL) && isFinite(dR) ? Math.max(-6, Math.min(6, dL-dR)) : 0;
  const cx = PAD_L+MW/2, bpx = MW/12;
  ctx.fillStyle = 'rgba(0,207,255,.08)'; ctx.fillRect(PAD_L, y, MW, 1);
  ctx.font = '7px Orbitron,monospace'; ctx.fillStyle = '#00cfff33'; ctx.textAlign = 'center';
  ctx.fillText('Balance', cx, y+9);
  [-6,-3,0,3,6].forEach(db => {
    const x = cx+db*bpx;
    ctx.fillStyle = 'rgba(0,180,210,.30)'; ctx.fillRect(x-.5, y+10, 1, 4);
    ctx.font = '7px Share Tech Mono,monospace'; ctx.fillStyle = 'rgba(0,175,210,.40)'; ctx.textAlign = 'center';
    ctx.fillText(db === 0 ? '0' : (db > 0 ? '+' : '')+db, x, y+21);
  });
  const bW = Math.abs(bal)*bpx, barY = y+23, barH = 10;
  ctx.fillStyle = '#010810'; ctx.fillRect(cx-6*bpx, barY, 12*bpx, barH);
  if (bW > 1) {
    const bx = bal >= 0 ? cx : cx-bW;
    const g = ctx.createLinearGradient(bx, 0, bx+bW, 0);
    g.addColorStop(0, bal >= 0 ? '#7a4200' : '#5a3800'); g.addColorStop(1, bal >= 0 ? '#c06800' : '#a05800');
    ctx.fillStyle = g; ctx.fillRect(bx, barY, bW, barH);
  }
  ctx.fillStyle = '#00cfff66'; ctx.fillRect(cx-.5, barY, 1, barH);
  const valY = y+37;
  ctx.font = '8px Share Tech Mono,monospace'; ctx.fillStyle = '#00cfff44';
  ctx.textAlign = 'left';  ctx.fillText(_vuFmt(dL, true)+' dB', PAD_L, valY);
  ctx.textAlign = 'right'; ctx.fillText(_vuFmt(dR, true)+' dB', PAD_L+MW, valY);
  if (bW > 1) { ctx.fillStyle = '#cc660077'; ctx.textAlign = 'center'; ctx.fillText((bal >= 0 ? '+' : '')+bal.toFixed(1)+' dB', cx, valY); }
}
function _drawVuMeter(rmsL, rmsR, peakL, peakR) {
  const cv = document.getElementById('rack-vu-meter');
  if (!cv) return;
  const W = cv.width, H = cv.height;
  const PAD_L = 28, MW = W - PAD_L - 156, BM = 26, BS = 14, SCL = 16;
  const GAP = 4;
  const lp = {
    ctx: cv.getContext('2d'), PAD_L, MW, BM, BS, SCL,
    dbX(db) { return PAD_L + Math.max(0, Math.min(1, (Math.max(_VU_DB_MIN, Math.min(_VU_DB_MAX, db)) - _VU_DB_MIN) / (_VU_DB_MAX - _VU_DB_MIN))) * MW; }
  };
  lp.xY = lp.dbX(-6); lp.xR = lp.dbX(0);
  lp.ctx.fillStyle = '#020508'; lp.ctx.fillRect(0, 0, W, H);
  [_vuHoldL, _vuHoldTL, _vuHoldVL] = _vuUpdHold(peakL, _vuHoldL, _vuHoldTL, _vuHoldVL);
  [_vuHoldR, _vuHoldTR, _vuHoldVR] = _vuUpdHold(peakR, _vuHoldR, _vuHoldTR, _vuHoldVR);
  _vuSubL = Math.max(peakL, _vuSubL * 0.975);
  _vuSubR = Math.max(peakR, _vuSubR * 0.975);
  if (peakL >= 0.944) _vuClipCL++; else _vuClipCL = Math.max(0, _vuClipCL - 1);
  if (peakR >= 0.944) _vuClipCR++; else _vuClipCR = Math.max(0, _vuClipCR - 1);
  const yLM = GAP, yLS = yLM+BM+GAP, ySC = yLS+BS+GAP, yRS = ySC+SCL+GAP, yRM = yRS+BS+GAP, yBL = yRM+BM+GAP+6;
  _vuDrawMain({ lp, y: yLM, rms: rmsL, hold: _vuHoldL, holdT: _vuHoldTL, clipC: _vuClipCL, label: 'L' });
  _vuDrawSub (lp, yLS, rmsL, _vuSubL);
  _vuDrawScale(lp, ySC);
  _vuDrawSub (lp, yRS, rmsR, _vuSubR);
  _vuDrawMain({ lp, y: yRM, rms: rmsR, hold: _vuHoldR, holdT: _vuHoldTR, clipC: _vuClipCR, label: 'R' });
  _vuDrawBalance(lp, yBL, rmsL, rmsR);
}

// Convertit une fréquence en position X (log scale)
function _logX(freq, W) {
  const lo = Math.log10(_FREQ_MIN), hi = Math.log10(_FREQ_MAX);
  return ((Math.log10(Math.max(freq, _FREQ_MIN)) - lo) / (hi - lo)) * W;
}

// Retourne la fréquence du bin i

// Couleur d'une barre selon son niveau normalisé (0=silence, 1=clip)

// Génère les labels de fréquences positionnés sur l'axe log
function _initFreqLabels(W) {
  const container = document.getElementById('rack-freq-labels');
  if (!container || _freqLabelsInit) return;
  _freqLabelsInit = true;
  const marks = [
    {f:20,'l':'20'},{f:50,'l':'50'},{f:100,'l':'100'},{f:200,'l':'200'},
    {f:500,'l':'500'},{f:1000,'l':'1k'},{f:2000,'l':'2k'},{f:5000,'l':'5k'},
    {f:10000,'l':'10k'},{f:20000,'l':'20k'},{f:24000,'l':'24k Hz'}
  ];
  container.style.position = 'relative';
  marks.forEach(({f, l}) => {
    const pct = (_logX(f, 100) ).toFixed(2);
    const span = document.createElement('span');
    span.textContent = l;
    span.className = 'freq-label-pos';
    span.style.left = pct + '%';
    container.appendChild(span);
  });
}

function _specSetLcd(id, txt, val) {
  const e = document.getElementById(id); if (!e) return;
  e.textContent = txt;
  if (val !== undefined) {
    e.classList.toggle('alert', val > -6);
    e.classList.toggle('warn',  val > -18 && val <= -6);
  }
}
var _SPEC_NUM_BARS = 160;
function _specDrawMirror(ctx2, W, H, halfH, barW, MAX_H){
  ctx2.setLineDash([2,6]); ctx2.lineWidth=0.5;
  [0.33,0.66,1.0].forEach(v=>{
    const yU=halfH-v*halfH*0.93, yD=halfH+v*halfH*0.93;
    ctx2.strokeStyle=v===1.0?'rgba(0,207,255,0.14)':'rgba(0,160,200,0.07)';
    ctx2.beginPath(); ctx2.moveTo(0,yU); ctx2.lineTo(W,yU); ctx2.stroke();
    ctx2.beginPath(); ctx2.moveTo(0,yD); ctx2.lineTo(W,yD); ctx2.stroke();
  });
  ctx2.setLineDash([2,5]);
  [50,100,200,500,1000,2000,5000,10000,20000].forEach(freq=>{
    const x=Math.log10(freq/_FREQ_MIN)/Math.log10(_FREQ_MAX/_FREQ_MIN)*W;
    ctx2.strokeStyle='rgba(0,150,190,0.08)';
    ctx2.beginPath(); ctx2.moveTo(x,0); ctx2.lineTo(x,H); ctx2.stroke();
  });
  ctx2.setLineDash([]);
  for(let b=0;b<_SPEC_NUM_BARS;b++){
    const bm=_specBinMap[b], cnt=bm[1]-bm[0]+1;
    let sL=0,sR=0; for(let i=bm[0];i<=bm[1];i++){sL+=fftL[i];sR+=fftR[i];}
    const vL=Math.pow(sL/cnt/255,0.72), vR=Math.pow(sR/cnt/255,0.72);
    const hL=vL*MAX_H, hR=vR*MAX_H, x=b*barW;
    const [cr,cg,cb]=_specColorTable[b];
    if(hL>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.35+vL*0.65).toFixed(2)+')';ctx2.fillRect(x,halfH-hL,barW-0.5,hL);}
    if(hR>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.35+vR*0.65).toFixed(2)+')';ctx2.fillRect(x,halfH,barW-0.5,hR);}
    _peakHoldL[b]=Math.max(vL,_peakHoldL[b]-_PEAK_DECAY); _peakHoldR[b]=Math.max(vR,_peakHoldR[b]-_PEAK_DECAY);
    const phL=_peakHoldL[b]*MAX_H, phR=_peakHoldR[b]*MAX_H;
    if(phL>1.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+',0.95)';ctx2.fillRect(x,halfH-phL-1.5,barW-0.5,1.5);}
    if(phR>1.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+',0.95)';ctx2.fillRect(x,halfH+phR,barW-0.5,1.5);}
  }
  ctx2.fillStyle='rgba(0,207,255,0.35)'; ctx2.fillRect(0,halfH-0.5,W,1);
  ctx2.font='9px Share Tech Mono,monospace'; ctx2.textAlign='left';
  ctx2.fillStyle='rgba(0,207,255,0.55)'; ctx2.fillText('L',5,13); ctx2.fillText('R',5,H-6);
  ctx2.font='7px Share Tech Mono,monospace'; ctx2.textAlign='right'; ctx2.fillStyle='rgba(0,180,220,0.45)';
  [[-6,1.0],[-12,0.66],[-18,0.33]].forEach(([db,v])=>{ctx2.fillText(db+'dB',W-2,halfH-v*halfH*0.93+3);});
}
function _specDrawScope(ctx2, W, H, sr){
  const PAD=8, qH=(H-PAD*3)/2;
  const yL0=PAD, yR0=PAD*2+qH;
  const STEP=Math.max(1,Math.floor(timL.length/W));
  let peakAmp=1e-4;
  for(let i=0;i<timL.length;i++){const a=Math.abs(timL[i]);if(a>peakAmp)peakAmp=a;}
  for(let i=0;i<timR.length;i++){const a=Math.abs(timR[i]);if(a>peakAmp)peakAmp=a;}
  _scopeGain=_scopeGain*0.94+Math.min(10,0.82/peakAmp)*0.06;
  const SWING=qH*0.46*_scopeGain;
  for(let y=0;y<H;y+=3){ctx2.fillStyle='rgba(0,0,0,0.18)';ctx2.fillRect(0,y,W,1);}
  ctx2.setLineDash([4,6]); ctx2.lineWidth=0.5; ctx2.strokeStyle='rgba(0,207,255,0.08)';
  ctx2.beginPath(); ctx2.moveTo(0,yR0-PAD/2); ctx2.lineTo(W,yR0-PAD/2); ctx2.stroke();
  ctx2.setLineDash([]);
  [yL0+qH/2,yR0+qH/2].forEach((cy,ci)=>{
    ctx2.setLineDash([2,8]); ctx2.lineWidth=0.5;
    ctx2.strokeStyle=ci===0?'rgba(0,207,255,0.15)':'rgba(204,102,255,0.15)';
    ctx2.beginPath(); ctx2.moveTo(0,cy); ctx2.lineTo(W,cy); ctx2.stroke();
    ctx2.setLineDash([]);
  });
  for(let d=1;d<8;d++){
    const xd=W*d/8; ctx2.setLineDash([2,6]); ctx2.lineWidth=0.4;
    ctx2.strokeStyle='rgba(0,130,160,0.08)';
    ctx2.beginPath(); ctx2.moveTo(xd,0); ctx2.lineTo(xd,H); ctx2.stroke();
    ctx2.setLineDash([]);
  }
  const _drawWave=(tim,yBase,colRgb)=>{
    const cy=yBase+qH/2;
    ctx2.beginPath(); ctx2.moveTo(0,cy);
    for(let i=0;i<tim.length;i+=STEP) ctx2.lineTo((i/tim.length)*W,cy-tim[i]*SWING);
    ctx2.lineTo(W,cy); ctx2.closePath(); ctx2.fillStyle='rgba('+colRgb+',0.07)'; ctx2.fill();
    ctx2.shadowBlur=8; ctx2.shadowColor='rgba('+colRgb+',0.6)';
    ctx2.lineWidth=2.5; ctx2.strokeStyle='rgba('+colRgb+',0.35)';
    ctx2.beginPath();
    for(let i=0;i<tim.length;i+=STEP){const x=(i/tim.length)*W,y=cy-tim[i]*SWING;i===0?ctx2.moveTo(x,y):ctx2.lineTo(x,y);}
    ctx2.stroke(); ctx2.shadowBlur=0; ctx2.lineWidth=1.2; ctx2.strokeStyle='rgba('+colRgb+',0.95)';
    ctx2.beginPath();
    for(let i=0;i<tim.length;i+=STEP){const x=(i/tim.length)*W,y=cy-tim[i]*SWING;i===0?ctx2.moveTo(x,y):ctx2.lineTo(x,y);}
    ctx2.stroke();
  };
  _drawWave(timL,yL0,'0,207,255'); _drawWave(timR,yR0,'204,102,255'); ctx2.shadowBlur=0;
  const bufMs=((timL.length/(sr||_SAMPLE_RATE))*1000).toFixed(0);
  ctx2.font='9px Share Tech Mono,monospace'; ctx2.textAlign='left';
  ctx2.fillStyle='rgba(0,207,255,0.8)'; ctx2.fillText('L',5,yL0+12);
  ctx2.fillStyle='rgba(204,102,255,0.8)'; ctx2.fillText('R',5,yR0+12);
  ctx2.font='7px Share Tech Mono,monospace'; ctx2.textAlign='right'; ctx2.fillStyle='rgba(0,180,220,0.4)';
  ctx2.fillText(bufMs+' ms  ×'+_scopeGain.toFixed(1),W-4,10);
}
function _specDrawPiano(ctx2, W, H, sr, bins){
  const A0F=27.5,C8F=4186.0,logA0=Math.log10(A0F),logC8=Math.log10(C8F);
  const KEY_H=22,BAR_MAX=H-KEY_H-4,BLK=new Set([1,3,6,8,10]);
  for(let k=0;k<88;k++){
    const f0=A0F*Math.pow(2,k/12),f1=A0F*Math.pow(2,(k+1)/12);
    const x0=(Math.log10(f0)-logA0)/(logC8-logA0)*W,x1=(Math.log10(f1)-logA0)/(logC8-logA0)*W;
    const kw=Math.max(1,x1-x0-0.5);
    const bk0=Math.max(0,Math.floor(f0*bins/(sr/2))),bk1=Math.min(bins-1,Math.ceil(f1*bins/(sr/2)));
    let sum=0,cnt=0; for(let i=bk0;i<=bk1;i++){sum+=(fftL[i]+fftR[i])*0.5;cnt++;}
    const v=cnt>0?Math.pow(sum/cnt/255,0.72):0;
    const [cr,cg,cb]=_specColorTable[Math.min(159,Math.floor(k/88*160))];
    const bh=v*BAR_MAX;
    if(bh>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.3+v*0.7).toFixed(2)+')';ctx2.fillRect(x0,H-KEY_H-bh,kw,bh);}
    ctx2.fillStyle=BLK.has(k%12)?'rgba(0,0,0,0.75)':'rgba(15,25,45,0.75)';
    ctx2.fillRect(x0,H-KEY_H,kw,KEY_H-1);
  }
  ctx2.font='7px Share Tech Mono,monospace'; ctx2.textAlign='center';
  for(let oct=0;oct<=8;oct++){
    const fC=16.352*Math.pow(2,oct); if(fC<A0F||fC>C8F) continue;
    const xC=(Math.log10(fC)-logA0)/(logC8-logA0)*W;
    ctx2.fillStyle='rgba(0,207,255,0.4)'; ctx2.fillText('C'+oct,xC,H-KEY_H+11);
    ctx2.strokeStyle='rgba(0,207,255,0.07)'; ctx2.lineWidth=0.5;
    ctx2.beginPath(); ctx2.moveTo(xC,0); ctx2.lineTo(xC,H-KEY_H); ctx2.stroke();
  }
  ctx2.textAlign='left';
}
function _specDrawSplit(ctx2, W, H){
  const halfW=W/2, bw2=halfW/_SPEC_NUM_BARS, MAXH2=(H-4)*0.9;
  ctx2.setLineDash([2,5]); ctx2.lineWidth=0.5;
  [50,200,1000,5000,20000].forEach(freq=>{
    const rx=Math.log10(freq/_FREQ_MIN)/Math.log10(_FREQ_MAX/_FREQ_MIN)*halfW;
    ctx2.strokeStyle='rgba(0,150,190,0.07)';
    ctx2.beginPath(); ctx2.moveTo(rx,0); ctx2.lineTo(rx,H); ctx2.stroke();
    ctx2.beginPath(); ctx2.moveTo(halfW+rx,0); ctx2.lineTo(halfW+rx,H); ctx2.stroke();
  });
  ctx2.setLineDash([]);
  for(let b=0;b<_SPEC_NUM_BARS;b++){
    const bm=_specBinMap[b], cnt=bm[1]-bm[0]+1;
    let sL=0,sR=0; for(let i=bm[0];i<=bm[1];i++){sL+=fftL[i];sR+=fftR[i];}
    const vL=Math.pow(sL/cnt/255,0.72),vR=Math.pow(sR/cnt/255,0.72);
    const [cr,cg,cb]=_specColorTable[b];
    const xL=b*bw2,xR=halfW+b*bw2,hbL=vL*MAXH2,hbR=vR*MAXH2;
    if(hbL>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.35+vL*0.65).toFixed(2)+')';ctx2.fillRect(xL,H-hbL,bw2-0.5,hbL);}
    if(hbR>0.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+','+(0.35+vR*0.65).toFixed(2)+')';ctx2.fillRect(xR,H-hbR,bw2-0.5,hbR);}
    _peakHoldL[b]=Math.max(vL,_peakHoldL[b]-_PEAK_DECAY); _peakHoldR[b]=Math.max(vR,_peakHoldR[b]-_PEAK_DECAY);
    const phL=_peakHoldL[b]*MAXH2,phR=_peakHoldR[b]*MAXH2;
    if(phL>1.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+',0.95)';ctx2.fillRect(xL,H-phL-1.5,bw2-0.5,1.5);}
    if(phR>1.5){ctx2.fillStyle='rgba('+cr+','+cg+','+cb+',0.95)';ctx2.fillRect(xR,H-phR-1.5,bw2-0.5,1.5);}
  }
  ctx2.fillStyle='rgba(0,207,255,0.45)'; ctx2.fillRect(halfW-0.5,0,1,H);
  ctx2.font='9px Share Tech Mono,monospace'; ctx2.textAlign='left';
  ctx2.fillStyle='rgba(0,207,255,0.7)'; ctx2.fillText('L',5,13);
  ctx2.fillStyle='rgba(204,102,255,0.7)'; ctx2.fillText('R',halfW+5,13);
  ctx2.font='7px Share Tech Mono,monospace'; ctx2.textAlign='right'; ctx2.fillStyle='rgba(0,180,220,0.35)';
  [-6,-12,-18].forEach(db=>{const h2=Math.pow(10,db/20)*MAXH2;ctx2.fillText(db+'dB',halfW-4,H-h2+3);ctx2.fillText(db+'dB',W-4,H-h2+3);});
}
function _specUpdateMetrics(rmsL, rmsR, peakLinL, peakLinR, corrClamped){
  const pL=Math.min(100,rmsL*300), pR=Math.min(100,rmsR*300);
  ['rack-peak-l','rack-vu-l'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.width=pL+'%';});
  ['rack-peak-r','rack-vu-r'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.width=pR+'%';});
  const svL=document.getElementById('rack-vu-stereo-l'), svR=document.getElementById('rack-vu-stereo-r');
  if(svL) svL.style.width=_stereoActive?pL+'%':'0%';
  if(svR) svR.style.width=_stereoActive?pR+'%':'0%';
  const dbL=rmsL>1e-4?(20*Math.log10(rmsL)).toFixed(1):'-∞';
  const dbR=rmsR>1e-4?(20*Math.log10(rmsR)).toFixed(1):'-∞';
  const rmsAvg=(rmsL+rmsR)/2;
  const dbRms=rmsAvg>1e-4?(20*Math.log10(rmsAvg)).toFixed(1):'-∞';
  _specSetLcd('rack-peak-l-db',dbL+' dB',parseFloat(dbL));
  _specSetLcd('rack-peak-r-db',dbR+' dB',parseFloat(dbR));
  _specSetLcd('rack-rms-val',dbRms+' dB',parseFloat(dbRms));
  const epM=document.getElementById('rack-peak-db'); if(epM) epM.textContent=dbL+' dB';
  const eCorr=document.getElementById('rack-corr-fill'), eCorrVal=document.getElementById('rack-corr-val');
  const silent=(rmsL+rmsR)<0.002;
  if(eCorr){
    if(silent){eCorr.style.transition='none';eCorr.style.left='50%';eCorr.style.width='0%';}
    else{
      eCorr.style.transition='width .12s,left .12s,background .2s';
      const w=Math.abs(corrClamped)*50;
      eCorr.style.left=corrClamped>=0?'50%':(50-w)+'%'; eCorr.style.width=w+'%';
      const cGood=corrClamped>0.3, cWarn=corrClamped>-0.1;
      eCorr.classList.toggle('corr-good', cGood);
      eCorr.classList.toggle('corr-warn', !cGood&&cWarn);
      eCorr.classList.toggle('corr-bad',  !cGood&&!cWarn);
    }
  }
  if(eCorrVal){
    if(silent){eCorrVal.textContent='—';eCorrVal.className=(eCorrVal.className.replace(/\bcorr-val-\S+/g,'')+' corr-val-silent').trim();}
    else{eCorrVal.textContent=corrClamped.toFixed(2);const cv=corrClamped>0.3?'corr-val-good':corrClamped>-0.1?'corr-val-warn':'corr-val-bad';eCorrVal.className=(eCorrVal.className.replace(/\bcorr-val-\S+/g,'')+' '+cv).trim();}
  }
}
function _drawSpectrum() {
  _specRaf = requestAnimationFrame(_drawSpectrum);
  if (!_analyserEnabled || !analyserL || !analyserR) return;
  const _anlL = window._datActive?(window._datAnL||analyserL):analyserL;
  const _anlR = window._datActive?(window._datAnR||analyserR):analyserR;
  _anlL.getByteFrequencyData(fftL); _anlR.getByteFrequencyData(fftR);
  _anlL.getFloatTimeDomainData(timL); _anlR.getFloatTimeDomainData(timR);
  const cv = document.getElementById('rack-spectrum-canvas');
  if (!cv) return;
  const ctx2=cv.getContext('2d'), W=cv.width, H=cv.height, halfH=H/2;
  const bins=fftL.length, sr=audioCtx.sampleRate||_SAMPLE_RATE;
  if(!_peakHoldL||_peakHoldL.length!==_SPEC_NUM_BARS){_peakHoldL=new Float32Array(_SPEC_NUM_BARS);_peakHoldR=new Float32Array(_SPEC_NUM_BARS);}
  const _freqLblEl=document.getElementById('rack-freq-labels');
  _disp(_freqLblEl, _rackSpecMode==='mirror'||_rackSpecMode==='split');
  if(_rackSpecMode==='mirror'||_rackSpecMode==='split') _initFreqLabels(W);
  if(!_specColorTable){
    _specColorTable=new Array(_SPEC_NUM_BARS);
    for(let ci=0;ci<_SPEC_NUM_BARS;ci++){
      const h=ci/_SPEC_NUM_BARS; let cr,cg,cb;
      if(h<0.20){const t=h/0.20;cr=0;cg=Math.round(120+t*110);cb=Math.round(255-t*105);}
      else if(h<0.50){const t=(h-0.20)/0.30;cr=Math.round(t*55);cg=Math.round(230+t*25);cb=Math.round(150-t*150);}
      else if(h<0.75){const t=(h-0.50)/0.25;cr=Math.round(55+t*200);cg=Math.round(255-t*60);cb=0;}
      else{const t=(h-0.75)/0.25;cr=255;cg=Math.round(195-t*195);cb=0;}
      _specColorTable[ci]=[cr,cg,cb];
    }
  }
  if(!_specBinMap||_specBinMap.length!==_SPEC_NUM_BARS){
    _specBinMap=new Array(_SPEC_NUM_BARS);
    for(let b=0;b<_SPEC_NUM_BARS;b++){
      const f0=_FREQ_MIN*Math.pow(_FREQ_MAX/_FREQ_MIN,b/_SPEC_NUM_BARS);
      const f1=_FREQ_MIN*Math.pow(_FREQ_MAX/_FREQ_MIN,(b+1)/_SPEC_NUM_BARS);
      _specBinMap[b]=[Math.max(0,Math.floor(f0*bins/(sr/2))),Math.min(bins-1,Math.ceil(f1*bins/(sr/2)))];
    }
  }
  const barW=W/_SPEC_NUM_BARS, MAX_H=halfH*0.93;
  ctx2.fillStyle='#000508'; ctx2.fillRect(0,0,W,H);
  if(_rackSpecMode==='mirror')      _specDrawMirror(ctx2,W,H,halfH,barW,MAX_H);
  else if(_rackSpecMode==='scope')  _specDrawScope(ctx2,W,H,sr);
  else if(_rackSpecMode==='piano')  _specDrawPiano(ctx2,W,H,sr,bins);
  else if(_rackSpecMode==='split')  _specDrawSplit(ctx2,W,H);
  let sumL2=0,sumR2=0,sumLR=0,peakLinL=0,peakLinR=0;
  for(let i=0;i<timL.length;i++){
    const aL=Math.abs(timL[i]),aR=Math.abs(timR[i]);
    sumL2+=aL*aL;sumR2+=aR*aR;sumLR+=timL[i]*timR[i];
    if(aL>peakLinL)peakLinL=aL;if(aR>peakLinR)peakLinR=aR;
  }
  const rmsL=Math.sqrt(sumL2/timL.length), rmsR=Math.sqrt(sumR2/timR.length);
  const corr=sumLR/(Math.sqrt(sumL2*sumR2)+1e-9);
  _specUpdateMetrics(rmsL,rmsR,peakLinL,peakLinR,Math.max(-1,Math.min(1,corr)));
  _drawGonio(timL,timR);
  _drawVuMeter(rmsL,rmsR,peakLinL,peakLinR);
}

// ── Goniomètre à persistance phosphore ──
function _drawGonio(timL, timR) {
  const cv = document.getElementById('rack-gonio-canvas');
  if (!cv) return;
  const ctx2 = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  const cx = W / 2, cy = H / 2;

  // Fade phosphore : fond semi-transparent pour effet persistence
  ctx2.fillStyle = 'rgba(0,1,10,0.18)';
  ctx2.fillRect(0, 0, W, H);

  // Axes + diagonales fixes (redessinés chaque frame par-dessus le fade)
  ctx2.lineWidth = 0.5;
  ctx2.strokeStyle = 'rgba(0,207,255,0.12)';
  ctx2.beginPath(); ctx2.moveTo(cx, 4); ctx2.lineTo(cx, H-4); ctx2.stroke();
  ctx2.beginPath(); ctx2.moveTo(4, cy); ctx2.lineTo(W-4, cy); ctx2.stroke();
  ctx2.strokeStyle = 'rgba(0,207,255,0.07)';
  ctx2.beginPath(); ctx2.moveTo(4,4); ctx2.lineTo(W-4,H-4); ctx2.stroke();
  ctx2.beginPath(); ctx2.moveTo(W-4,4); ctx2.lineTo(4,H-4); ctx2.stroke();

  // Labels M / S
  ctx2.font = '7px Share Tech Mono, monospace';
  ctx2.fillStyle = 'rgba(0,207,255,0.25)';
  ctx2.textAlign = 'center';
  ctx2.fillText('M', cx, 11);
  ctx2.fillText('L', 9, cy+3);
  ctx2.fillText('R', W-9, cy+3);
  ctx2.fillText('S', cx, H-4);
  ctx2.textAlign = 'left';

  // Cercle de référence
  ctx2.beginPath();
  ctx2.arc(cx, cy, cx * 0.88, 0, Math.PI * 2);
  ctx2.strokeStyle = 'rgba(0,207,255,0.06)';
  ctx2.lineWidth = 1;
  ctx2.stroke();

  // Tracé Lissajous (rotation 45° = convention goniomètre)
  const step = Math.max(1, Math.floor(timL.length / 128));
  ctx2.lineWidth = 1.2;
  // Couleur selon énergie
  const energy = Math.sqrt((timL.reduce((a,v)=>a+v*v,0)+timR.reduce((a,v)=>a+v*v,0))/timL.length/2);
  const alpha = Math.min(0.9, 0.3 + energy * 4);
  ctx2.strokeStyle = `rgba(0,220,255,${alpha})`;

  ctx2.beginPath();
  let first = true;
  for (let i = 0; i < timL.length; i += step) {
    const m =  (timL[i] + timR[i]) * 0.707;
    const s =  (timL[i] - timR[i]) * 0.707;
    const x = cx + s * (cx - 5) * 0.9;
    const y = cy - m * (cy - 5) * 0.9;
    first ? ctx2.moveTo(x, y) : ctx2.lineTo(x, y);
    first = false;
  }
  ctx2.stroke();

  // Point central (silence = vert, signal = cyan)
  ctx2.beginPath();
  ctx2.arc(cx, cy, energy > 0.005 ? 1.5 : 2.5, 0, Math.PI * 2);
  ctx2.fillStyle = energy > 0.005 ? 'rgba(0,220,255,0.8)' : 'rgba(0,255,120,0.5)';
  ctx2.fill();
}

// Lancer le dessin du spectre
_drawSpectrum();

const speechQueue = [];
let isPlaying = false;
let _currentAudioSource = null; // source en cours pour stop immédiat
let _audioGen = 0; // incrémenté à chaque stop → invalide le onended de l'ancienne source

async function playSentence(text) {
  return new Promise(async (resolve) => {
    if (!_ensureAudioCtx()) { resolve(); return; }
    if (!_dspInited) try { initDsp(); } catch(e) {}
    try {
      const resp = await fetch('/api/tts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text})
      });
      if (!resp.ok) { resolve(); return; }
      const arrayBuffer = await resp.arrayBuffer();
      // Lire SR source depuis header WAV (offset 24, uint32 LE) avant decodeAudioData (qui détache le buffer)
      let _ttsSrcSR = audioCtx.sampleRate;
      try {
        const _hv = new DataView(arrayBuffer);
        if (arrayBuffer.byteLength >= 28 && _hv.getUint32(0, true) === 0x46464952 /*RIFF*/) {
          _ttsSrcSR = _hv.getUint32(24, true);
        }
      } catch(_) { /* skip SR detection on malformed WAV header */ }
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
      window._lastTtsBuf = audioBuffer;  // Capture pour DSP
      // Afficher SR source réelle (edge-tts 48kHz) vs SR AudioContext (resampling browser)
      const _srDisp = document.getElementById('rack-stereo-sr');
      if (_srDisp) _srDisp.textContent = _ttsSrcSR + ' Hz';
      const source = audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      // Apply DSP speed & pitch (playbackRate changes both; detune adjusts pitch without speed)
      if (typeof _dspPlaybackRate !== 'undefined') source.playbackRate.value = _dspPlaybackRate;
      if (typeof _dspPitchSemi   !== 'undefined') source.detune.value = _dspPitchSemi * 100;
      // Connexion stéréo L/R + master analyser
      _connectStereoSource(source);
      _currentAudioSource = source;
      const myGen = _audioGen;
      source.start();
      source.onended = () => {
        _currentAudioSource = null;
        if (_audioGen === myGen) resolve(); // ignoré si stopAudio() a été appelé entre-temps
      };
    } catch(e) {
      resolve();
    }
  });
}

async function queueSpeech(text) {
  if (!ttsEnabled) return;
  speechQueue.push(text);
  if (!isPlaying) processQueue();
}

async function processQueue() {
  if (speechQueue.length === 0) {
    isPlaying = false;
    speaking = false;
    document.getElementById('jarvis-state').classList.remove('speaking');
    if (typeof window._mixAutoDuck === 'function') window._mixAutoDuck(false);
    _clearAllReplayBtns();
    _updateAudioBtn();
    // Restore waveform bar CSS animations
    document.querySelectorAll('.waveform span').forEach(bar => {
      bar.style.animation = '';
      bar.style.height = '';
    });
    // Reset reactor rings + speaking class
    document.querySelector('.reactor-wrap')?.classList.remove('reactor-speaking');
    const ring1 = document.querySelector('.reactor-ring-1');
    const ring2 = document.querySelector('.reactor-ring-2');
    const ring3 = document.querySelector('.reactor-ring-3');
    const reticle = document.querySelector('.reactor-reticle');
    const scan = document.querySelector('.reactor-scan');
    if (ring1) ring1.style.animationDuration = '';
    if (ring2) ring2.style.animationDuration = '';
    if (ring3) ring3.style.animationDuration = '';
    if (reticle) reticle.style.animationDuration = '';
    if (scan) scan.style.animationDuration = '';
    const core = document.querySelector('.reactor-core');
    if (core) core.style.opacity = '.08';
    const glow = document.querySelector('.reactor-glow');
    if (glow) glow.style.boxShadow = '';
    return;
  }
  isPlaying = true;
  speaking = true;
  document.getElementById('jarvis-state').classList.add('speaking');
  document.querySelector('.reactor-wrap')?.classList.add('reactor-speaking');
  if (typeof window._mixAutoDuck === 'function') window._mixAutoDuck(true);
  _updateAudioBtn();
  // Disable CSS animation on waveform bars so JS can drive them
  document.querySelectorAll('.waveform span').forEach(bar => {
    bar.style.animation = 'none';
  });
  const text = speechQueue.shift();
  // Resume AudioContext if suspended (browser autoplay policy)
  if (audioCtx && audioCtx.state === 'suspended') await audioCtx.resume();
  await playSentence(text);
  processQueue();
}

// ── Contrôle audio : Stop / Relecture ──────────────────────
function stopAudio() {
  _audioGen++; // invalide tout onended en attente
  speechQueue.length = 0;
  if (_currentAudioSource) {
    try { _currentAudioSource.stop(); } catch(e) {}
    _currentAudioSource = null;
  }
  isPlaying = false; speaking = false;
  document.getElementById('jarvis-state').classList.remove('speaking');
  document.querySelector('.reactor-wrap')?.classList.remove('reactor-speaking');
  if (typeof window._mixAutoDuck === 'function') window._mixAutoDuck(false);
  document.querySelectorAll('.waveform span').forEach(b => { b.style.animation = ''; b.style.height = ''; });
  const ring1 = document.querySelector('.reactor-ring-1');
  const ring2 = document.querySelector('.reactor-ring-2');
  const ring3 = document.querySelector('.reactor-ring-3');
  const reticle = document.querySelector('.reactor-reticle');
  if (ring1) ring1.style.animationDuration = '';
  if (ring2) ring2.style.animationDuration = '';
  if (ring3) ring3.style.animationDuration = '';
  if (reticle) reticle.style.animationDuration = '';
  const core = document.querySelector('.reactor-core');
  if (core) core.style.opacity = '.08';
  const glow = document.querySelector('.reactor-glow');
  if (glow) glow.style.boxShadow = '';
  _clearAllReplayBtns();
  _updateAudioBtn();
}

let _lastJarvisText = '';
let _activeReplayBtn = null; // bouton ▶ actuellement en lecture


function replayMessage(text, btn) {
  if (!text) return;
  // Bloqué si JARVIS est en train de streamer une réponse
  if (busy) return;
  // Reclique sur le bouton actif pendant lecture → stop
  if (btn && btn === _activeReplayBtn && isPlaying) {
    stopAudio();
    return;
  }
  // Reclique sur le bouton global pendant lecture → stop
  if (!btn && isPlaying) {
    stopAudio();
    return;
  }
  stopAudio(); // coupe tout + invalide onended
  if (btn) {
    _activeReplayBtn = btn;
    _setReplayBtnState(btn, true);
  }
  queueSpeech(text);
}

function _setAllReplayBusy(isBusy) {
  document.querySelectorAll('.msg-replay-btn').forEach(function(b) {
    b.classList.toggle('stream-busy', isBusy);
  });
}

function _setReplayBtnState(btn, playing) {
  if (!btn) return;
  btn.textContent = playing ? '⏹' : '▶';
  btn.classList.toggle('playing', playing);
}

function _clearAllReplayBtns() {
  document.querySelectorAll('.msg-replay-btn').forEach(b => _setReplayBtnState(b, false));
  _activeReplayBtn = null;
}

function _updateAudioBtn() {
  const btn = document.getElementById('btn-audio-stop');
  if (!btn) return;
  if (isPlaying) {
    btn.textContent = '⏹';
    btn.title = 'Arrêter la lecture audio';
    btn.classList.add('active');
  } else {
    btn.textContent = '▶';
    btn.title = 'Relire le dernier message';
    btn.classList.remove('active');
  }
}

// ── Spectral Analyzer canvas ─────────────────────────────────
const _sCanvas = document.getElementById('spectral-canvas');
const _sCtx    = _sCanvas ? _sCanvas.getContext('2d') : null;
const _sPeaks  = new Float32Array(48).fill(0); // peak hold per bar

function drawSpectral(active) {
  if (!_sCtx) return;
  const W = _sCanvas.offsetWidth || 200;
  const H = _sCanvas.offsetHeight || 52;
  if (_sCanvas.width !== W)  _sCanvas.width  = W;
  if (_sCanvas.height !== H) _sCanvas.height = H;

  // background
  _sCtx.clearRect(0, 0, W, H);
  _sCtx.fillStyle = '#010810';
  _sCtx.fillRect(0, 0, W, H);

  const BARS = 48;
  const gap  = 1;
  const bw   = (W - gap * (BARS - 1)) / BARS;

  for (let i = 0; i < BARS; i++) {
    let val;
    if (active) {
      // Use voice frequency data (first 80 bins = voice range)
      const binIdx = Math.floor(i * 80 / BARS);
      val = dataArray[binIdx] / 255;
    } else {
      // Idle: very subtle noise floor
      val = 0.02 + Math.random() * 0.04;
    }

    const barH = Math.max(1, val * H * 0.92);
    const x    = i * (bw + gap);

    // Peak hold
    if (val > _sPeaks[i]) _sPeaks[i] = val;
    else _sPeaks[i] = Math.max(0, _sPeaks[i] - 0.012);

    // Bar gradient: bottom=dark blue → top=cyan → tip=white when loud
    const grad = _sCtx.createLinearGradient(0, H, 0, H - barH);
    if (active && val > 0.6) {
      grad.addColorStop(0, '#003366');
      grad.addColorStop(0.5, '#00cfff');
      grad.addColorStop(1, '#ffffff');
    } else if (active) {
      grad.addColorStop(0, '#002244');
      grad.addColorStop(1, '#00cfff');
    } else {
      grad.addColorStop(0, '#001122');
      grad.addColorStop(1, '#00cfff22');
    }

    _sCtx.fillStyle = grad;
    _sCtx.fillRect(x, H - barH, bw, barH);

    // Peak dot
    if (active && _sPeaks[i] > 0.05) {
      const py = H - _sPeaks[i] * H * 0.92 - 1;
      _sCtx.fillStyle = _sPeaks[i] > 0.7 ? '#ffffff' : '#00cfff88';
      _sCtx.fillRect(x, py, bw, 1);
    }
  }

  // Glow overlay when speaking
  if (active) {
    const avg = dataArray.slice(0, 80).reduce((a, b) => a + b, 0) / 80;
    const gAlpha = (avg / 255) * 0.25;
    _sCtx.fillStyle = `rgba(0,207,255,${gAlpha})`;
    _sCtx.fillRect(0, 0, W, H);
  }
}

function visualize() {
  requestAnimationFrame(visualize);
  if (!analyser) return;
  analyser.getByteFrequencyData(dataArray);
  const avg  = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
  const norm = avg / 128;

  drawSpectral(speaking);
  // Reactor — actif en permanence (idle + speaking)
  _reactorDrive(norm, dataArray);

  if (!speaking) return;

  // Animate waveform bars with real frequency data
  const bars = document.querySelectorAll('.waveform span');
  bars.forEach((bar, i) => {
    const val = dataArray[i * 2] || 0;
    bar.style.height = Math.max(4, (val / 255) * 28) + 'px';
  });
}

// ── Système sonar réactif à la voix ──────────────────────────
var _rPeaks   = [];
var _rPrevNorm = 0;
var _rPeakCooldown = 0;
const _PEAK_THRESH   = 0.28;
const _PEAK_MIN_GAP  = 80;
const _PULSE_ELS = ['.reactor-pulse-1','.reactor-pulse-2','.reactor-pulse-3'];
const _R_MIN = 16, _R_MAX = 72;

// ── Visualiseur circulaire Canvas ──────────────────────────────
var _rvCtx = null;
var _rvCanvas = null;
var _rvIdlePhase = 0;
var _rvChevrons = null;
var _rvChevronFlash = 0;  // timestamp dernier flash

function _getChevrons() {
  if (_rvChevrons && _rvChevrons.length) return _rvChevrons;
  var grp = document.querySelector('.reactor-ring-1');
  if (!grp) return null;
  _rvChevrons = grp.querySelectorAll('polygon');
  return _rvChevrons.length ? _rvChevrons : null;
}

function _rvDrawIdle(ctx, cx, cy, innerR, N) {
  _rvIdlePhase += 0.0035;
  for (var s = 0; s < 4; s++) {
    var sA = _rvIdlePhase * 0.4 + s * Math.PI / 2;
    ctx.beginPath(); ctx.arc(cx, cy, innerR+10, sA, sA+0.7);
    ctx.strokeStyle = 'rgba(0,160,210,0.10)'; ctx.lineWidth = 7; ctx.stroke();
  }
  for (var i = 0; i < N; i++) {
    var angle = (i/N)*Math.PI*2 - Math.PI/2;
    var wave = 0.04 + Math.sin(_rvIdlePhase+i*0.18)*0.03 + Math.cos(_rvIdlePhase*0.7+i*0.3)*0.02;
    var len = Math.max(1, wave*26);
    ctx.beginPath();
    ctx.moveTo(cx+Math.cos(angle)*innerR, cy+Math.sin(angle)*innerR);
    ctx.lineTo(cx+Math.cos(angle)*(innerR+len), cy+Math.sin(angle)*(innerR+len));
    ctx.strokeStyle = 'rgba(0,180,220,'+(wave*5).toFixed(2)+')'; ctx.lineWidth = 1; ctx.stroke();
  }
}
function _rvDrawGlows({ ctx, cx, cy, innerR, outerR, norm, bassNorm, dataArray }) {
  if (bassNorm > 0.05) {
    var bassG = ctx.createRadialGradient(cx, cy, 0, cx, cy, innerR-4);
    bassG.addColorStop(0, 'rgba(0,240,255,'+(bassNorm*0.85).toFixed(2)+')');
    bassG.addColorStop(0.5, 'rgba(0,120,220,'+(bassNorm*0.45).toFixed(2)+')');
    bassG.addColorStop(1, 'rgba(0,0,100,0)');
    ctx.fillStyle = bassG; ctx.beginPath(); ctx.arc(cx, cy, innerR-4, 0, Math.PI*2); ctx.fill();
  }
  var gAlpha = norm*0.20;
  var grad = ctx.createRadialGradient(cx, cy, innerR-8, cx, cy, outerR+16);
  grad.addColorStop(0,   'rgba(80,230,255,'+(gAlpha*3.8).toFixed(2)+')');
  grad.addColorStop(0.3, 'rgba(0,207,255,'+(gAlpha*2.5).toFixed(2)+')');
  grad.addColorStop(0.7, 'rgba(0,80,180,'+gAlpha.toFixed(2)+')');
  grad.addColorStop(1,   'rgba(0,20,80,0)');
  ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(cx, cy, outerR+16, 0, Math.PI*2); ctx.fill();
  for (var s = 0; s < 8; s++) {
    var startA = (s/8)*Math.PI*2 - Math.PI/2, endA = ((s+0.82)/8)*Math.PI*2 - Math.PI/2;
    var sIdx0 = Math.floor(s*dataArray.length/8), sIdx1 = Math.floor((s+1)*dataArray.length/8);
    var sSum = 0; for (var si = sIdx0; si < sIdx1; si++) sSum += (dataArray[si]||0);
    var sAmp = sSum/((sIdx1-sIdx0)*255);
    if (sAmp > 0.12) {
      ctx.beginPath(); ctx.arc(cx, cy, innerR+6, startA, endA);
      ctx.lineWidth = Math.max(3, sAmp*14);
      ctx.strokeStyle = 'rgba(0,207,255,'+(sAmp*0.38).toFixed(2)+')';
      ctx.shadowBlur = 10; ctx.shadowColor = '#00cfff'; ctx.stroke(); ctx.shadowBlur = 0;
    }
  }
  ctx.beginPath(); ctx.arc(cx, cy, innerR, 0, Math.PI*2);
  ctx.strokeStyle = 'rgba(0,207,255,'+(0.32+norm*0.58).toFixed(2)+')'; ctx.lineWidth = 1.5;
  ctx.shadowBlur = 12; ctx.shadowColor = '#00cfff'; ctx.stroke(); ctx.shadowBlur = 0;
}
function _rvDrawFreqBars({ ctx, cx, cy, innerR, maxBar, N, dataArray }) {
  for (var i = 0; i < N; i++) {
    var angle = (i/N)*Math.PI*2 - Math.PI/2;
    var amp = (dataArray[Math.floor(i*dataArray.length/N)]||0)/255;
    var lenOut = Math.max(1.5, amp*maxBar), lenIn = Math.max(1, amp*(maxBar*0.42));
    var alpha = 0.18+amp*0.82, isFrac = i/N, rr, gg;
    if      (isFrac < 0.25) { rr = Math.round(amp*70);       gg = Math.round(185+amp*70); }
    else if (isFrac < 0.60) { rr = Math.round(amp*35);       gg = Math.round(205+amp*50); }
    else                    { rr = Math.round(120+amp*130);  gg = Math.round(220+amp*35); }
    var col = 'rgba('+rr+','+gg+',255,'+alpha.toFixed(2)+')';
    ctx.lineWidth = amp > 0.65 ? 2.5 : amp > 0.38 ? 2 : 1.5;
    ctx.shadowBlur = amp > 0.6 ? 14 : amp > 0.35 ? 6 : 2; ctx.shadowColor = '#00cfff';
    var xo1 = cx+Math.cos(angle)*innerR, yo1 = cy+Math.sin(angle)*innerR;
    ctx.beginPath(); ctx.moveTo(xo1, yo1);
    ctx.lineTo(cx+Math.cos(angle)*(innerR+lenOut), cy+Math.sin(angle)*(innerR+lenOut));
    ctx.strokeStyle = col; ctx.stroke();
    if (amp > 0.10) {
      ctx.beginPath(); ctx.moveTo(xo1, yo1);
      ctx.lineTo(cx+Math.cos(angle)*(innerR-lenIn), cy+Math.sin(angle)*(innerR-lenIn));
      ctx.strokeStyle = 'rgba('+rr+','+gg+',255,'+(alpha*0.42).toFixed(2)+')';
      ctx.lineWidth = 1; ctx.shadowBlur = 3; ctx.stroke();
    }
    if (amp > 0.58) {
      ctx.beginPath(); ctx.arc(cx+Math.cos(angle)*(innerR+lenOut), cy+Math.sin(angle)*(innerR+lenOut), 2.2, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(255,255,255,'+(amp*0.97).toFixed(2)+')';
      ctx.shadowBlur = 18; ctx.shadowColor = '#ffffff'; ctx.fill();
    }
  }
  ctx.shadowBlur = 0;
}
function _drawReactorViz(dataArray, norm) {
  if (!_rvCanvas) {
    _rvCanvas = document.getElementById('reactor-viz-canvas');
    if (!_rvCanvas) return;
    _rvCtx = _rvCanvas.getContext('2d');
  }
  var ctx = _rvCtx, W = _rvCanvas.width, H = _rvCanvas.height;
  var cx = W/2, cy = H/2, N = 128, innerR = 40;
  var maxBar = speaking ? Math.round(30+norm*28) : 30;
  var outerR = innerR+maxBar;
  ctx.clearRect(0, 0, W, H);
  if (!speaking) { _rvDrawIdle(ctx, cx, cy, innerR, N); return; }
  var bassSum = 0; for (var b = 0; b < 20; b++) bassSum += (dataArray[b]||0);
  var trebleSum = 0; for (var t = 80; t < N; t++) trebleSum += (dataArray[t]||0);
  var bassNorm = bassSum/(20*255), trebleNorm = trebleSum/(48*255);
  _rvDrawGlows({ ctx, cx, cy, innerR, outerR, norm, bassNorm, dataArray });
  _rvDrawFreqBars({ ctx, cx, cy, innerR, maxBar, N, dataArray });
  ctx.beginPath(); ctx.arc(cx, cy, outerR+2, 0, Math.PI*2);
  ctx.strokeStyle = 'rgba(0,207,255,'+(0.07+norm*0.22).toFixed(2)+')'; ctx.lineWidth = 1; ctx.stroke();
  if (trebleNorm > 0.18) {
    ctx.beginPath(); ctx.arc(cx, cy, outerR+7, 0, Math.PI*2);
    ctx.strokeStyle = 'rgba(190,245,255,'+(trebleNorm*0.55).toFixed(2)+')'; ctx.lineWidth = 0.8;
    ctx.shadowBlur = 8; ctx.shadowColor = '#aaddff'; ctx.stroke(); ctx.shadowBlur = 0;
  }
}

function _reactorIdleReset({ core, glow, ring1, ring2, ring3, reticle, scan }) {
  _rPeaks = [];
  _PULSE_ELS.forEach(function(sel) {
    var el = document.querySelector(sel);
    if (el) { el.setAttribute('r', _R_MIN); el.style.opacity = '0'; el.style.strokeWidth = ''; }
  });
  if (core)    core.style.opacity = '.06';
  if (glow)    glow.style.boxShadow = '';
  if (ring1)   ring1.style.animationDuration = '';
  if (ring2)   ring2.style.animationDuration = '';
  if (ring3)   ring3.style.animationDuration = '';
  if (reticle) reticle.style.animationDuration = '';
  if (scan)    scan.style.animationDuration = '';
  var chv = _getChevrons();
  if (chv) { for (var ci = 0; ci < chv.length; ci++) { chv[ci].setAttribute('opacity','0.35'); chv[ci].setAttribute('fill','#00cfff'); } }
}
function _reactorChevrons(now, norm, dataArray) {
  var chv = _getChevrons();
  if (!chv) return;
  var flashAge = now - _rvChevronFlash, flashDur = 120;
  for (var ci = 0; ci < chv.length; ci++) {
    var cFrac = ci/chv.length;
    var cAmp = (dataArray[Math.floor(cFrac*dataArray.length)]||0)/255;
    var cOp, cFill;
    if (flashAge < flashDur) {
      var fProg = flashAge/flashDur;
      cOp = (0.9-fProg*0.5).toFixed(2); cFill = fProg < 0.5 ? '#ffffff' : '#aaddff';
    } else {
      cOp = (0.2+(norm*0.55)+(cAmp*0.25)).toFixed(2); cFill = norm > 0.65 ? '#aaddff' : '#00cfff';
    }
    chv[ci].setAttribute('opacity', cOp); chv[ci].setAttribute('fill', cFill);
  }
}
function _reactorCoreGlow(core, glow, norm) {
  if (core) {
    var peakFlash = _rPeaks.length > 0 ? _rPeaks[0].intensity*0.35 : 0;
    core.style.opacity = Math.min(0.88, 0.05+norm*0.6+peakFlash).toFixed(2);
    core.setAttribute('r', (14+norm*11).toFixed(1));
    core.setAttribute('fill', norm > 0.65 ? '#aaddff' : '#00cfff');
  }
  if (glow) {
    var gi = (10+norm*40).toFixed(0), gs = (32+norm*30).toFixed(0);
    var ga = Math.floor(norm*230).toString(16).padStart(2,'0');
    glow.style.width = gs+'px'; glow.style.height = gs+'px';
    glow.style.boxShadow = ['0 0 '+gi+'px '+Math.round(gi/2)+'px #00cfff'+ga,'0 0 '+(gi*2)+'px '+gi+'px #00cfff55','0 0 '+(gi*4)+'px '+(gi*1.5)+'px #00cfff28','0 0 '+(gi*6)+'px '+(gi*2)+'px #00cfff14'].join(',');
  }
}
function _reactorDrive(norm, dataArray) {
  _drawReactorViz(dataArray, norm);
  var now = performance.now();
  var glow = document.querySelector('.reactor-glow'), core = document.querySelector('.reactor-core');
  var ring1 = document.querySelector('.reactor-ring-1'), ring2 = document.querySelector('.reactor-ring-2');
  var ring3 = document.querySelector('.reactor-ring-3'), reticle = document.querySelector('.reactor-reticle');
  var scan = document.querySelector('.reactor-scan');
  if (!speaking) { _reactorIdleReset({ core, glow, ring1, ring2, ring3, reticle, scan }); return; }
  var rising = norm > _rPrevNorm+0.04;
  if (rising && norm > _PEAK_THRESH && now-_rPeakCooldown > _PEAK_MIN_GAP) {
    _rPeaks.push({t:now, dur:350+(1-norm)*280, intensity:norm});
    _rPeakCooldown = now; _rvChevronFlash = now;
  }
  _rPrevNorm = norm;
  _rPeaks = _rPeaks.filter(function(p) { return now-p.t < p.dur; });
  _PULSE_ELS.forEach(function(sel, i) {
    var el = document.querySelector(sel); if (!el) return;
    var peak = _rPeaks[i];
    if (!peak) { el.style.opacity = '0'; el.setAttribute('r', _R_MIN); return; }
    var progress = (now-peak.t)/peak.dur;
    el.setAttribute('r', (_R_MIN+progress*(_R_MAX-_R_MIN)).toFixed(1));
    el.style.opacity = ((1-progress)*Math.min(1,peak.intensity*1.4)).toFixed(2);
    el.style.strokeWidth = (2.5-progress*2.2).toFixed(1)+'px';
  });
  _reactorChevrons(now, norm, dataArray);
  _reactorCoreGlow(core, glow, norm);
  if (ring1)   ring1.style.animationDuration   = Math.max(0.6, 6-norm*5)+'s';
  if (ring2)   ring2.style.animationDuration   = Math.max(0.3, 4-norm*3.4)+'s';
  if (ring3)   ring3.style.animationDuration   = Math.max(0.2, 2.5-norm*2)+'s';
  if (reticle) reticle.style.animationDuration = Math.max(0.45, 8-norm*7.2)+'s';
  if (scan)    scan.style.animationDuration    = Math.max(0.25, 2.5-norm*2.2)+'s';
}
visualize();

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

// ══════════════════════════════════════
// SETTINGS LLM + PROFILS RTX 5080
// ══════════════════════════════════════

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

// ══════════════════════════════════════
// DSP AUDIO SYSTEM
// ══════════════════════════════════════
let _dspInited    = false;
let _dspRafId     = null;
let _eqPanelOn    = true;  // false quand le panel EQ est bypassed (⏻)
let _dspAnalyser  = null;
let _dspDataArray = null;
let _dspEqLow     = null;
let _dspEqMid     = null;
let _dspEqHigh    = null;
let _dspEqAir     = null;
let _dspCompressor= null;
let _dspGainNode   = null;
let _jarvisPreGain = null; // gain JARVIS uniquement (avant _dspAnalyser)
let _dspLimiter    = null; // limiteur global (après compresseur)
let _dspVoiceBypass   = null; // bypass voix DSP → destination (découplage voix/DSP)
let _dspVoiceDecoupled = false; // true = voix JARVIS bypass DSP
let _dspPlaybackRate = 1.0;
let _dspPitchSemi = 0;
let _dspVolume    = 1.0;
let _fxConvolver   = null;  // ConvolverNode WebAudio (reverb/echo/delay IR — normalize=true)
let _fxDryGain     = null;  // chemin direct (dry) vers destination
let _fxWetGain     = null;  // gain wet final (equal-power crossfade)
let _masterLimiter = null;  // brick-wall limiter final (-0.3 dBFS) — sécurité unique
let _haasDelayNode = null;  // noeud delay persistant mono→stéréo (Haas effect canal R)
let _haasGainNode  = null;  // gain canal R = stereo_width (0=mono, 1=max largeur)
let _stereoWidth   = 85;    // valeur courante en pourcents
let _specColorTable = null; // table couleurs barres spectrum (160 entrées, freq → [r,g,b])
let _specBinMap     = null; // mapping barres → plages bins FFT (160 entrées)
let _rackSpecMode   = 'mirror'; // mode affichage rack-spectrum-canvas
let _scopeGain      = 1.0;      // auto-gain oscilloscope (lissé)

const DSP_PROFILES = {
  flat:      { low:0,  mid:0,  high:0,  air:0,  thresh:-24, ratio:4,  attack:3,  release:250, gain:0 },
  clair:     { low:-2, mid:1,  high:3,  air:2,  thresh:-20, ratio:3,  attack:5,  release:200, gain:0 },
  studio:    { low:2,  mid:0,  high:2,  air:3,  thresh:-24, ratio:4,  attack:3,  release:250, gain:1 },
  robotic:   { low:-6, mid:8,  high:2,  air:0,  thresh:-30, ratio:8,  attack:2,  release:100, gain:0 },
  broadcast: { low:3,  mid:2,  high:4,  air:3,  thresh:-18, ratio:5,  attack:4,  release:200, gain:2 },
  jarvis:    { low:4,  mid:-1, high:5,  air:4,  thresh:-28, ratio:6,  attack:3,  release:300, gain:1 },
  deep:      { low:8,  mid:2,  high:-2, air:-3, thresh:-20, ratio:4,  attack:5,  release:300, gain:0 },
};

function _initDspApplyAudioParams(p){
  if(p.gain!==undefined){
    setDspGain(p.gain);
    const rg=document.getElementById('rack-gain');
    if(rg){rg.value=p.gain;_syncRangeSlider(rg);}
  }
  [['threshold',p.comp_threshold],['ratio',p.comp_ratio],
   ['attack',Math.round((p.comp_attack||0.003)*1000)],
   ['release',Math.round((p.comp_release||0.25)*1000)]
  ].forEach(function(pair){
    var param=pair[0],val=pair[1]; if(val===undefined) return;
    setDspCompressor(param,val);
    var rackId={threshold:'rack-comp-thresh',ratio:'rack-comp-ratio',attack:'rack-comp-att',release:'rack-comp-rel'};
    var rs2=document.getElementById(rackId[param]); if(rs2){rs2.value=val;_syncRangeSlider(rs2);}
  });
  ['low','mid','high','air'].forEach(function(id){
    var g=p['eq_'+id],sl=document.getElementById('eq-'+id);
    if(g!==undefined&&sl){sl.value=g;setEqBand(id,g);}
    if(p['eq_'+id+'_freq']) eqSetFreq(id,p['eq_'+id+'_freq']);
    if(p['eq_'+id+'_q'])    eqSetQ(id,p['eq_'+id+'_q']);
    if(p['eq_'+id+'_type']) eqSetType(id,p['eq_'+id+'_type']);
    if(p['eq_'+id+'_byp'])  eqToggleBypass(id);
  });
  ['sub','bass','mids','treble'].forEach(function(id){
    var g=p['dat_eq_'+id],sl=document.getElementById('dat-eq-'+id);
    if(g!==undefined&&sl){sl.value=g;setDatEqBand(id,g);}
    if(p['dat_eq_'+id+'_freq']) datEqSetFreq(id,p['dat_eq_'+id+'_freq']);
    if(p['dat_eq_'+id+'_q'])    datEqSetQ(id,p['dat_eq_'+id+'_q']);
    if(p['dat_eq_'+id+'_type']) datEqSetType(id,p['dat_eq_'+id+'_type']);
    if(p['dat_eq_'+id+'_byp'])  datEqToggleBypass(id);
  });
}
function _initDspApplyUiParams(p){
  const mt=document.getElementById('dsp-master-toggle');
  if(mt) mt.classList.toggle('on',!!p.enabled);
  _updateDspChainStatus(!!p.enabled);
  const dfOn=!!p.df_enabled, dfBtn=document.getElementById('rack-df-bypass');
  if(dfBtn){dfBtn.classList.toggle('on',dfOn);dfBtn.classList.toggle('off',!dfOn);}
  document.getElementById('rack-unit-df')?.classList.toggle('bypassed',!dfOn);
  document.getElementById('rsp-df')?.classList.toggle('active',dfOn);
  const swEl=document.getElementById('rack-stereo-width'), hdEl=document.getElementById('rack-haas-delay');
  const stereoOn=p.stereo_enabled!==false;
  if(swEl){swEl.value=Math.round((p.stereo_width??0.85)*100);rackSyncStereoWidth(swEl.value);}
  if(hdEl){hdEl.value=p.haas_delay_ms??18;rackSyncHaasDelay(hdEl.value);}
  const sBtn=document.getElementById('rack-stereo-bypass');
  if(sBtn){sBtn.classList.toggle('on',stereoOn);sBtn.classList.toggle('off',!stereoOn);}
  document.getElementById('rack-unit-stereo')?.classList.toggle('bypassed',!stereoOn);
  document.getElementById('rsp-stereo')?.classList.toggle('active',stereoOn);
  const sTag=document.getElementById('rack-stereo-tag');
  if(sTag){sTag.textContent=stereoOn?'L + R':'MONO';sTag.className='rack-unit-tag '+(stereoOn?'tag-ok':'');}
  const fxOn=!!p.fx_enabled; _fxActive=fxOn;
  const fxBtn=document.getElementById('rack-fx-bypass'), fxUnit=document.getElementById('rack-unit-fx');
  const fxNode=document.getElementById('rsp-fx'), fxLabel=document.getElementById('fx-proc-label');
  if(fxBtn){fxBtn.classList.toggle('on',fxOn);fxBtn.classList.toggle('off',!fxOn);}
  if(fxUnit) fxUnit.classList.toggle('bypassed',!fxOn);
  if(fxNode){fxNode.classList.toggle('active',fxOn);fxNode.classList.toggle('fx-bypass-node',!fxOn);}
  if(fxLabel) fxLabel.textContent=fxOn?'◉ ACTIF':'BYPASS';
  if(_fxDryGain&&_fxWetGain&&_fxConvolver){
    const fxType=p.fx_type||'reverb'; _fx2Type=fxType; _fxType=fxType;
    const savedVals={};
    if(_FX2[fxType]){_FX2[fxType].params.forEach(function(pm){if(p[pm.key]!==undefined)savedVals[pm.key]=p[pm.key];});}
    if(!_fx2Vals[fxType]) _fx2Vals[fxType]=savedVals;
    const wet=p.fx_wet!==undefined?p.fx_wet:0.4;
    if(!_fx2Vals[fxType].fx_wet) _fx2Vals[fxType].fx_wet=wet;
    if (typeof _fxRefreshIr === 'function') _fxRefreshIr(fxType, _fx2Vals[fxType]);
    if(fxOn) _fxSetWetDry(wet, false);
  }
  const srEl=document.getElementById('rack-stereo-sr');
  if(srEl) srEl.textContent=(audioCtx.sampleRate||_SAMPLE_RATE)+' Hz';
  document.querySelectorAll('.rack-fader').forEach(f=>{
    const pct=((parseFloat(f.value)-parseFloat(f.min))/(parseFloat(f.max)-parseFloat(f.min))*100).toFixed(1);
    f.style.setProperty('--f-pct',pct+'%');
  });
}
function _initDspCreateNodes(){
  _dspAnalyser = audioCtx.createAnalyser();
  _dspAnalyser.fftSize = 2048;
  _dspAnalyser.smoothingTimeConstant = 0.82;
  _dspDataArray = new Uint8Array(_dspAnalyser.frequencyBinCount);
  const _eqNodes = [null, null, null, null];
  [_dspEqLow, _dspEqMid, _dspEqHigh, _dspEqAir] = [0,1,2,3].map(i => {
    const f = audioCtx.createBiquadFilter();
    f.type = _eqState[i].type; f.frequency.value = _eqState[i].freq;
    f.Q.value = _eqState[i].q; f.gain.value = 0;
    return f;
  });
  window._dspEqLow=_dspEqLow; window._dspEqMid=_dspEqMid;
  window._dspEqHigh=_dspEqHigh; window._dspEqAir=_dspEqAir;
  // ── COMPRESSEUR VOIX — réglage doux type broadcast vocal ──
  // Threshold haut + ratio doux = peu d'action sauf pics > -12 dBFS
  // Compensation par makeup gain ci-dessous (sinon signal écrasé sans récupération)
  _dspCompressor = audioCtx.createDynamicsCompressor();
  _dspCompressor.threshold.value = -12;   // était -24 (trop bas → écrasement permanent)
  _dspCompressor.ratio.value     = 2;     // était 4:1 (trop agressif)
  _dspCompressor.attack.value    = 0.010; // 10ms — laisse passer transitoires courtes
  _dspCompressor.release.value   = 0.150; // 150ms — récupération naturelle
  _dspCompressor.knee.value      = 6;
  // Makeup gain compensatoire — restaure le niveau perçu après compression
  _dspGainNode = audioCtx.createGain();
  _dspGainNode.gain.value = 1.5;          // +3.5 dB — compense les ~3 dB de gain reduction max
  // ── LIMITER VOIX — brick-wall plus haut, laisse de la place au mix ──
  _dspLimiter = audioCtx.createDynamicsCompressor();
  _dspLimiter.threshold.value = -1.5;     // était -0.5 (trop proche du clip, déclenchait sur peanuts)
  _dspLimiter.ratio.value     = 20;
  _dspLimiter.attack.value    = 0.002;
  _dspLimiter.release.value   = 0.080;
  _dspLimiter.knee.value      = 0;
  // ── BUS FX SIMPLE — dry direct + wet via convolver, plus de routing intermédiaire ──
  _fxConvolver = audioCtx.createConvolver();
  _fxConvolver.normalize = true;       // Web Audio normalise l'IR nativement
  _fxConvolver.buffer = null;          // pas d'IR initiale → wet path silencieux jusqu'à activation FX
  _fxDryGain = audioCtx.createGain();  _fxDryGain.gain.value = 1.0;
  _fxWetGain = audioCtx.createGain();  _fxWetGain.gain.value = 0.0;

  // ── BRICK-WALL LIMITER FINAL (sécurité absolue, capture wet+dry en sortie) ──
  _masterLimiter = audioCtx.createDynamicsCompressor();
  _masterLimiter.threshold.value = -0.3;
  _masterLimiter.ratio.value     = 20;
  _masterLimiter.attack.value    = 0.001;
  _masterLimiter.release.value   = 0.05;
  _masterLimiter.knee.value      = 0;

  window._fxDryGain=_fxDryGain; window._fxWetGain=_fxWetGain; window._fxConvolver=_fxConvolver;
  window._masterLimiter=_masterLimiter;
}
function _initDspWireChain(){
  // ─────────────────────────────────────────────────────────────────────────
  // CHAÎNE AUDIO SIMPLIFIÉE — minimal routing, anti-bug duplication
  //
  // analyser → preGain → dspAnalyser → EQ4b → comp → voice limiter → outGain
  //                                                                     │
  //                                              ┌──────────────────────┤
  //                                              │                      │
  //                                              ▼                      ▼
  //                                         _fxDryGain (1.0)      _fxConvolver
  //                                              │                      │
  //                                              │                      ▼
  //                                              │               _fxWetGain (0.0 init)
  //                                              │                      │
  //                                              └──→ _masterLimiter ◄──┘
  //                                                          │
  //                                                          ▼
  //                                                  audioCtx.destination
  // ─────────────────────────────────────────────────────────────────────────
  _dspCompressor.connect(_dspLimiter); _dspLimiter.connect(_dspGainNode);

  // Sortie voice channel → DRY direct + WET via convolver
  _dspGainNode.connect(_fxDryGain);
  _dspGainNode.connect(_fxConvolver);
  _fxConvolver.connect(_fxWetGain);

  // Sommation finale : dry + wet → master limiter → destination (un seul path par signal)
  _fxDryGain.connect(_masterLimiter);
  _fxWetGain.connect(_masterLimiter);
  _masterLimiter.connect(audioCtx.destination);
  window._dspAnalyser=_dspAnalyser; window._dspCompressor=_dspCompressor;
  if(window._datPreDsp){
    try{window._datPreDsp.disconnect();}catch(e){}
    if(window._datEqSub&&window._datEqSub.context===audioCtx){
      try{window._datEqTreble.disconnect();}catch(e){}
      try{window._datEqTreble.connect(_dspCompressor);}catch(e){}
      try{window._datPreDsp.connect(window._datEqSub);}catch(e){}
    }else{try{window._datPreDsp.connect(_dspCompressor);}catch(e){}}
  }
  _jarvisPreGain=audioCtx.createGain(); _jarvisPreGain.gain.value=1.0;
  analyser.connect(_jarvisPreGain); _jarvisPreGain.connect(_dspAnalyser);
  _dspAnalyser.connect(_dspEqLow); _dspEqLow.connect(_dspEqMid);
  _dspEqMid.connect(_dspEqHigh); _dspEqHigh.connect(_dspEqAir); _dspEqAir.connect(_dspCompressor);
  try{analyser.disconnect(audioCtx.destination);}catch(e){}
  _dspVoiceBypass=audioCtx.createGain(); _dspVoiceBypass.gain.value=0;
  analyser.connect(_dspVoiceBypass); _dspVoiceBypass.connect(audioCtx.destination);
  window._dspVoiceBypass=_dspVoiceBypass;
}
function initDsp() {
  if (_dspInited) return;
  if (!_ensureAudioCtx()) return;
  _dspInited = true;
  _initDspCreateNodes();
  _initDspWireChain();
  syncDspVoices();
  document.querySelectorAll('.dsp-hslider').forEach(sl => updateSliderPct(sl));
  setTimeout(drawEqCurve, _EQ_REDRAW_MS);
  _updateEqCoupleBadges();
  startDspDraw();
  _fetchDspParams().then(p=>{
    if(!p) return;
    _initDspApplyAudioParams(p);
    _initDspApplyUiParams(p);
    // Pré-génération IR du type FX courant — 1er toggle ON instantané
    if (_fx2Type && typeof _fxRefreshIr === 'function') {
      _fxRefreshIr(_fx2Type, _fx2Vals[_fx2Type] || {});
    }
  }).catch(()=>{});
  rackInitFaders();
}

function updateSliderPct(sl) {
  if (!sl) return;
  const min = parseFloat(sl.min), max = parseFloat(sl.max), val = parseFloat(sl.value);
  const raw = (val - min) / (max - min);
  const w = sl.offsetWidth;
  const isDatEq = sl.classList.contains('dat-eq-slider');
  if (w > 20) {
    const pct = ((raw * (w - 18) + 9) / w * 100).toFixed(2);
    sl.style.setProperty('--pct', pct + '%');
    if (isDatEq) {
      const cRaw = (-min) / (max - min);
      const cPct = ((cRaw * (w - 18) + 9) / w * 100);
      const p = parseFloat(pct);
      const diff = Math.abs(p - cPct);
      if (diff < 0.8) {
        sl.style.setProperty('--fill-s', '49.3%');
        sl.style.setProperty('--fill-e', '50.7%');
      } else {
        sl.style.setProperty('--fill-s', Math.min(p, cPct).toFixed(2) + '%');
        sl.style.setProperty('--fill-e', Math.max(p, cPct).toFixed(2) + '%');
      }
    }
  } else {
    sl.dataset.rawPct = raw.toFixed(4);
    sl.style.setProperty('--pct', (raw * 100).toFixed(1) + '%');
    if (isDatEq) {
      sl.style.setProperty('--fill-s', '49.3%');
      sl.style.setProperty('--fill-e', '50.7%');
    }
  }
}

// Recalcule tous les curseurs DSP quand le tab devient visible
function _refreshDspSliders() {
  document.querySelectorAll('.dsp-hslider').forEach(sl => {
    if (sl.dataset.rawPct !== undefined && sl.offsetWidth > 20) {
      const raw = parseFloat(sl.dataset.rawPct);
      const w   = sl.offsetWidth;
      sl.style.setProperty('--pct', ((raw * (w - 18) + 9) / w * 100).toFixed(2) + '%');
      delete sl.dataset.rawPct;
    } else {
      updateSliderPct(sl);
    }
  });
}

// ══════════════════════════════════════
// EQ PARAMÉTRIQUE — COURBE DE RÉPONSE
// ══════════════════════════════════════
const EQ_SR = _SAMPLE_RATE;  // match Python DSP (edge-tts 48kHz)
// ── Spectrum analyzer state ──
let _specMode    = 'fill';
let _specFftSize = 4096;
let _specPeaks   = null;
let _wfCanvas    = null;
let _wfCtx2      = null;
let _specLogAxis  = false;  // axe fréquences logarithmique
let _specPeakVis  = true;   // afficher caps peak hold
let _specGridVis  = true;   // afficher grille dB
let _specGhostOn  = false;  // traces persistantes (ghost frames)
let _specGhostBuf = [];     // anneau de frames passées

function setRackSpecMode(mode) {
  _rackSpecMode = mode;
  ['mirror','scope','piano','split'].forEach(m => {
    const btn = document.getElementById('rspec-' + m);
    if (btn) btn.classList.toggle('active', m === mode);
  });
}

function setSpecMode(mode) {
  _specMode = mode;
  document.querySelectorAll('.spec-mode-btn[data-mode]').forEach(b =>
    b.classList.toggle('active', b.dataset.mode === mode));
  // Reset canvas when leaving persistent modes
  if (mode !== 'waterfall') { _wfCanvas = null; _wfCtx2 = null; }
  if (mode !== 'dots') {
    const cv = document.getElementById('dsp-canvas');
    if (cv) { cv.width = cv.offsetWidth; cv.height = cv.offsetHeight; }
  }
  // Static freq-labels strip only useful for classic bar/line modes
  const fl = document.querySelector('.dsp-freq-labels');
  _disp(fl, ['bars','line','fill','mirror'].includes(mode));
}

function setSpecFft(size) {
  _specFftSize = size;
  if (_dspAnalyser) {
    _dspAnalyser.fftSize = size;
    _dspDataArray = new Uint8Array(_dspAnalyser.frequencyBinCount);
    _specPeaks = null;
  }
  const lbl = document.getElementById('spec-fft-label');
  if (lbl) lbl.textContent = '◈ SPECTRAL ANALYZER — FFT ' + size;
  document.querySelectorAll('.spec-mode-btn[data-fft]').forEach(b =>
    b.classList.toggle('active', parseInt(b.dataset.fft) === size));
}

// Waterfall thermal color map
function _wfColor(v) {
  if (v < 0.01) return '#000508';
  if (v < 0.20) { const t = v / 0.20; return `rgb(0,0,${Math.round(t * 170)})`; }
  if (v < 0.40) { const t = (v-0.20)/0.20; return `rgb(0,${Math.round(t*150)},${Math.round(170*(1-t))})`; }
  if (v < 0.60) { const t = (v-0.40)/0.20; return `rgb(0,${Math.round(150+t*105)},0)`; }
  if (v < 0.80) { const t = (v-0.60)/0.20; return `rgb(${Math.round(t*255)},255,0)`; }
  const t = (v-0.80)/0.20; return `rgb(255,${Math.round(255-t*205)},${Math.round(t*50)})`;
}

// ── EQ ghost curve (peak hold) ──
let _eqGhost      = null;  // Float32Array: combined curve snapshot
let _eqGhostAlpha = 0;     // 0..1, decays each RAF frame
let _eqLastCombined = null; // previous combined array for ghost capture

// Mutable EQ band state (freq, Q, type, bypassed) — updated by drag/wheel/type buttons
const _eqState = [
  { freq:80,   q:0.7, type:'lowshelf',  bypassed:false, gain:0 },
  { freq:315,  q:0.8, type:'peaking',   bypassed:false, gain:0 },
  { freq:1250, q:0.9, type:'highshelf', bypassed:false, gain:0 },
  { freq:5000, q:0.7, type:'highshelf', bypassed:false, gain:0 },
];
// Frequency range limits per band [min, max]
const _eqFreqRange = [[20,400],[100,2000],[500,8000],[2000,24000]];

// Canvas drag state
let _eqDrag = null; // { idx, startFreq, startGain }

const EQ_BANDS = [
  { id:'low',  freq:80,   type:'lowshelf',  Q:0.7, color:_cssVar('--blue'),   label:'LOW' },
  { id:'mid',  freq:315,  type:'peaking',   Q:0.8, color:_cssVar('--cyan'),   label:'MID' },
  { id:'high', freq:1250, type:'highshelf', Q:0.9, color:_cssVar('--green'),  label:'HIGH' },
  { id:'air',  freq:5000, type:'highshelf', Q:0.7, color:_cssVar('--purple'), label:'AIR' },
];

function eqBqCoeffs(type, freq, gainDb, Q) {
  const A   = Math.pow(10, gainDb / 40);
  const w0  = 2 * Math.PI * freq / EQ_SR;
  const cosw= Math.cos(w0), sinw = Math.sin(w0);
  let b0,b1,b2,a0,a1,a2;
  if (type === 'lowshelf') {
    const alpha = sinw * Math.sqrt(2 * A) / 2;
    b0 =  A*((A+1)-(A-1)*cosw+2*Math.sqrt(A)*alpha);
    b1 =2*A*((A-1)-(A+1)*cosw);
    b2 =  A*((A+1)-(A-1)*cosw-2*Math.sqrt(A)*alpha);
    a0 =    (A+1)+(A-1)*cosw+2*Math.sqrt(A)*alpha;
    a1 = -2*((A-1)+(A+1)*cosw);
    a2 =    (A+1)+(A-1)*cosw-2*Math.sqrt(A)*alpha;
  } else if (type === 'highshelf') {
    const alpha = sinw * Math.sqrt(2 * A) / 2;
    b0 =  A*((A+1)+(A-1)*cosw+2*Math.sqrt(A)*alpha);
    b1 =-2*A*((A-1)+(A+1)*cosw);
    b2 =  A*((A+1)+(A-1)*cosw-2*Math.sqrt(A)*alpha);
    a0 =    (A+1)-(A-1)*cosw+2*Math.sqrt(A)*alpha;
    a1 =  2*((A-1)-(A+1)*cosw);
    a2 =    (A+1)-(A-1)*cosw-2*Math.sqrt(A)*alpha;
  } else if (type === 'highpass') {
    const qv = Q || 0.7071;
    const alpha = sinw / (2 * qv);
    b0 = (1+cosw)/2; b1 = -(1+cosw); b2 = (1+cosw)/2;
    a0 = 1+alpha; a1 = -2*cosw; a2 = 1-alpha;
  } else if (type === 'lowpass') {
    const qv = Q || 0.7071;
    const alpha = sinw / (2 * qv);
    b0 = (1-cosw)/2; b1 = 1-cosw; b2 = (1-cosw)/2;
    a0 = 1+alpha; a1 = -2*cosw; a2 = 1-alpha;
  } else if (type === 'notch') {
    const alpha = sinw / (2 * (Q || 0.8));
    b0 = 1; b1 = -2*cosw; b2 = 1;
    a0 = 1+alpha; a1 = -2*cosw; a2 = 1-alpha;
  } else if (type === 'bandpass') {
    const alpha = sinw / (2 * (Q || 0.8));
    b0 = sinw/2; b1 = 0; b2 = -sinw/2;
    a0 = 1+alpha; a1 = -2*cosw; a2 = 1-alpha;
  } else { // peaking (default)
    const alpha = sinw / (2 * (Q || 0.8));
    b0 = 1 + alpha * A;  b1 = -2*cosw;  b2 = 1 - alpha * A;
    a0 = 1 + alpha / A;  a1 = -2*cosw;  a2 = 1 - alpha / A;
  }
  return { b:[b0/a0, b1/a0, b2/a0], a:[1, a1/a0, a2/a0] };
}

function eqBqResponse(coeff, freq) {
  const w  = 2 * Math.PI * freq / EQ_SR;
  const cr = Math.cos(w), ci = Math.sin(w);
  const c2r = Math.cos(2*w), c2i = Math.sin(2*w);
  // numerator H(e^jw) = b0 + b1*e^-jw + b2*e^-2jw
  const nr = coeff.b[0] + coeff.b[1]*cr  + coeff.b[2]*c2r;
  const ni =               coeff.b[1]*ci  + coeff.b[2]*c2i;  // note: e^-jw → cos-jsin but we use +sin for inverse
  const dr = coeff.a[0] + coeff.a[1]*cr  + coeff.a[2]*c2r;
  const di =               coeff.a[1]*ci  + coeff.a[2]*c2i;
  const mag2 = (nr*nr + ni*ni) / (dr*dr + di*di);
  return 20 * Math.log10(Math.max(1e-10, Math.sqrt(mag2)));
}

function _eqDrawBackground(lp){
  const {ctx,W,H,ML,MR,MT,MB,PW,PH}=lp;
  const bgGrd=ctx.createRadialGradient(W/2,H/2,10,W/2,H/2,W*0.75);
  bgGrd.addColorStop(0,'#030e18'); bgGrd.addColorStop(1,'#010810');
  ctx.fillStyle=bgGrd; ctx.fillRect(0,0,W,H);
  const vig=ctx.createRadialGradient(W/2,H/2,PW*0.3,W/2,H/2,W*0.65);
  vig.addColorStop(0,'rgba(0,0,0,0)'); vig.addColorStop(1,'rgba(0,0,0,.55)');
  ctx.fillStyle=vig; ctx.fillRect(0,0,W,H);
  for(let y=MT;y<H-MB;y+=3){ctx.fillStyle='rgba(0,0,0,.08)';ctx.fillRect(ML,y,PW,1);}
}
function _eqDrawLiveSpectrum(lp){
  const {ctx,W,ML,MR,MT,MB,PW,PH,fMin,fMax}=lp;
  const hasData=typeof _dspDataArray!=='undefined'&&_dspDataArray&&_dspDataArray.length>0;
  const N=hasData?_dspDataArray.length:1024;
  const nyq=(typeof audioCtx!=='undefined'&&audioCtx?audioCtx.sampleRate:_SAMPLE_RATE)/2;
  if(!window._eqSpecPeaks||window._eqSpecPeaks.length!==W) window._eqSpecPeaks=new Float32Array(W);
  const peaks=window._eqSpecPeaks, sp=SPEC_PRESETS[window._eqSpecPreset]||SPEC_PRESETS.jarvis;
  ctx.beginPath(); let first=true;
  for(let px=ML;px<=W-MR;px++){
    let val=0.04;
    if(hasData){const f=fMin*Math.pow(fMax/fMin,(px-ML)/PW);const bin=Math.min(Math.round(f/nyq*N),N-1);val=Math.max(_dspDataArray[bin]/255,0.04);}
    peaks[px]=Math.max(peaks[px]*0.993,val);
    const sy=MT+PH*(1-val);
    if(first){ctx.moveTo(px,MT+PH);ctx.lineTo(px,sy);first=false;}else ctx.lineTo(px,sy);
  }
  ctx.lineTo(W-MR,MT+PH); ctx.closePath();
  const gSpec=ctx.createLinearGradient(0,MT,0,MT+PH);
  gSpec.addColorStop(0,sp.top); gSpec.addColorStop(0.45,sp.mid); gSpec.addColorStop(1,sp.bot);
  ctx.fillStyle=gSpec; ctx.fill();
  ctx.beginPath(); ctx.strokeStyle=sp.peak; ctx.lineWidth=1; first=true;
  for(let px=ML;px<=W-MR;px++){const sy=MT+PH*(1-peaks[px]);first?(ctx.moveTo(px,sy),first=false):ctx.lineTo(px,sy);}
  ctx.stroke();
}
function _eqDrawDbGrid(lp){
  const {ctx,W,ML,MR,MT,MB,PW,PH,dbToY}=lp;
  [-12,-9,-6,-3,-1,0,1,3,6,9,12].forEach(db=>{
    const y=dbToY(db),isZero=db===0,isMajor=db%3===0;
    ctx.strokeStyle=isZero?'rgba(255,255,255,.18)':isMajor?'rgba(0,180,220,.07)':'rgba(0,150,180,.03)';
    ctx.lineWidth=isZero?1.5:isMajor?0.8:0.4;
    ctx.setLineDash(isZero?[]:isMajor?[4,6]:[1,8]);
    ctx.beginPath(); ctx.moveTo(ML,y); ctx.lineTo(W-MR,y); ctx.stroke(); ctx.setLineDash([]);
  });
  ctx.font='9px Share Tech Mono'; ctx.textAlign='right';
  [-12,-9,-6,-3,0,3,6,9,12].forEach(db=>{
    const y=dbToY(db),lbl=(db>0?'+':'')+db;
    ctx.strokeStyle=db===0?'rgba(255,255,255,.3)':'rgba(0,180,220,.2)'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(ML-4,y); ctx.lineTo(ML,y); ctx.stroke();
    ctx.fillStyle=db===0?'rgba(255,255,255,.55)':'rgba(0,200,240,.35)'; ctx.fillText(lbl,ML-6,y+3);
  });
  ctx.save(); ctx.translate(10,MT+PH/2); ctx.rotate(-Math.PI/2);
  ctx.font='7px Orbitron'; ctx.textAlign='center'; ctx.fillStyle='rgba(0,180,220,.2)'; ctx.fillText('dBFS',0,0);
  ctx.restore();
  ctx.font='9px Share Tech Mono'; ctx.textAlign='left';
  [-12,-9,-6,-3,0,3,6,9,12].forEach(db=>{
    const y=dbToY(db);
    ctx.strokeStyle=db===0?'rgba(255,255,255,.3)':'rgba(0,180,220,.2)'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(W-MR,y); ctx.lineTo(W-MR+4,y); ctx.stroke();
    ctx.fillStyle=db===0?'rgba(255,255,255,.55)':'rgba(0,200,240,.35)';
    ctx.fillText((db>0?'+':'')+db,W-MR+6,y+3);
  });
}
function _eqDrawFreqGrid(lp){
  const {ctx,W,H,ML,MR,MT,MB,freqToX}=lp;
  const fMajor=[50,100,200,500,1000,2000,5000,10000,20000,24000];
  const fMinor=[30,70,150,300,700,1500,3000,7000,15000,18000];
  const fLbls={50:'50',100:'100',200:'200',500:'500',1000:'1k',2000:'2k',5000:'5k',10000:'10k',20000:'20k',24000:'24k'};
  fMinor.forEach(f=>{
    const x=freqToX(f); if(x<ML||x>W-MR) return;
    ctx.strokeStyle='rgba(0,150,180,.04)'; ctx.lineWidth=0.5; ctx.setLineDash([1,8]);
    ctx.beginPath(); ctx.moveTo(x,MT); ctx.lineTo(x,H-MB); ctx.stroke(); ctx.setLineDash([]);
  });
  fMajor.forEach(f=>{
    const x=freqToX(f); if(x<ML||x>W-MR) return;
    ctx.strokeStyle='rgba(0,170,210,.07)'; ctx.lineWidth=0.8; ctx.setLineDash([3,7]);
    ctx.beginPath(); ctx.moveTo(x,MT); ctx.lineTo(x,H-MB); ctx.stroke(); ctx.setLineDash([]);
    ctx.strokeStyle='rgba(0,180,220,.3)'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(x,H-MB); ctx.lineTo(x,H-MB+4); ctx.stroke();
    ctx.font='9px Share Tech Mono'; ctx.textAlign='center'; ctx.fillStyle='rgba(0,200,240,.38)';
    ctx.fillText(fLbls[f],x,H-5);
  });
  ctx.font='7px Orbitron'; ctx.textAlign='right'; ctx.fillStyle='rgba(0,180,220,.2)'; ctx.fillText('Hz',W-MR-2,H-5);
  ctx.strokeStyle='rgba(0,100,140,.25)'; ctx.lineWidth=1; ctx.strokeRect(ML-0.5,MT-0.5,lp.PW+1,lp.PH+1);
  ctx.strokeStyle='rgba(0,180,220,.08)'; ctx.lineWidth=1; ctx.strokeRect(ML,MT,lp.PW,lp.PH);
}
function _eqDrawBandCurves(lp, freqs){
  const {ctx,ML,MR,dbMin,dbMax,fMin,fMax,freqToX,dbToY}=lp;
  if(_eqGhost&&_eqGhostAlpha>0){
    ctx.beginPath(); ctx.strokeStyle='rgba(0,207,255,'+(_eqGhostAlpha*0.5).toFixed(3)+')';
    ctx.lineWidth=1.5; ctx.setLineDash([6,4]);
    _eqGhost.forEach((db,i)=>{const x=freqToX(freqs[i]),y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
    ctx.stroke(); ctx.setLineDash([]);
  }
  EQ_BANDS.forEach((band,i)=>{
    if(_eqState[i].bypassed) return;
    const gainDb=_eqState[i].gain, noGainType=['highpass','lowpass','notch','bandpass'].includes(_eqState[i].type);
    if(!noGainType&&Math.abs(gainDb)<0.05) return;
    const coeff=eqBqCoeffs(_eqState[i].type,_eqState[i].freq,gainDb,_eqState[i].q);
    ctx.beginPath();
    freqs.forEach((f,fi)=>{const db=eqBqResponse(coeff,f);const x=freqToX(f),y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));fi===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
    ctx.lineTo(freqToX(fMax),dbToY(0)); ctx.lineTo(freqToX(fMin),dbToY(0)); ctx.closePath();
    ctx.fillStyle=band.color+'18'; ctx.fill();
    ctx.beginPath(); ctx.strokeStyle=band.color+'44'; ctx.lineWidth=1;
    freqs.forEach((f,fi)=>{const db=eqBqResponse(coeff,f);const x=freqToX(f),y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));fi===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
    ctx.stroke();
  });
}
function _eqDrawCombinedCurve(lp, freqs, combined){
  const {ctx,dbMin,dbMax,freqToX,dbToY}=lp;
  const N=freqs.length, zeroY=dbToY(0);
  combined.forEach((db,i)=>{
    const x0=freqToX(freqs[i]),x1=i<N-1?freqToX(freqs[i+1]):x0+1,y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));
    if(db>0.1){
      const grd=ctx.createLinearGradient(0,y,0,zeroY);
      grd.addColorStop(0,'rgba(0,207,255,0.28)');grd.addColorStop(0.5,'rgba(0,160,220,0.12)');grd.addColorStop(1,'rgba(0,80,140,0.03)');
      ctx.fillStyle=grd;ctx.fillRect(x0,y,x1-x0,zeroY-y);
    }else if(db<-0.1){
      const grd=ctx.createLinearGradient(0,zeroY,0,y);
      grd.addColorStop(0,'rgba(0,100,200,0.22)');grd.addColorStop(1,'rgba(0,40,120,0.03)');
      ctx.fillStyle=grd;ctx.fillRect(x0,zeroY,x1-x0,y-zeroY);
    }
  });
  ctx.shadowColor='#00cfff'; ctx.shadowBlur=10;
  ctx.beginPath(); ctx.strokeStyle='#00cfff'; ctx.lineWidth=2;
  combined.forEach((db,i)=>{const x=freqToX(freqs[i]),y=dbToY(Math.max(dbMin,Math.min(dbMax,db)));i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.stroke(); ctx.shadowBlur=0;
}
function _eqDrawHandles(lp){
  const {ctx,dbMin,dbMax,freqToX,dbToY}=lp;
  EQ_BANDS.forEach((band,i)=>{
    const noGainT=['highpass','lowpass','notch','bandpass'].includes(_eqState[i].type);
    const gainDb=(_eqState[i].bypassed||noGainT)?0:_eqState[i].gain;
    const x=freqToX(_eqState[i].freq),y=dbToY(Math.max(dbMin,Math.min(dbMax,gainDb)));
    if(_eqState[i].bypassed){
      ctx.beginPath(); ctx.arc(x,y,7,0,Math.PI*2); ctx.fillStyle='#1a1a2a'; ctx.fill();
      ctx.strokeStyle='#333'; ctx.lineWidth=1; ctx.stroke();
      ctx.fillStyle='#444'; ctx.font='bold 8px Orbitron'; ctx.textAlign='center'; ctx.fillText(i+1,x,y+3);
      return;
    }
    ctx.beginPath(); ctx.arc(x,y,11,0,Math.PI*2); ctx.fillStyle=band.color+'20'; ctx.fill();
    ctx.beginPath(); ctx.arc(x,y,8,0,Math.PI*2); ctx.fillStyle=band.color; ctx.fill();
    ctx.strokeStyle='#000810'; ctx.lineWidth=1.5; ctx.stroke();
    ctx.fillStyle='#fff'; ctx.font='bold 8px Orbitron'; ctx.textAlign='center'; ctx.fillText(i+1,x,y+3);
    const lbl=(gainDb>=0?'+':'')+gainDb.toFixed(1);
    ctx.font='bold 7px Share Tech Mono'; ctx.fillStyle='#ffcc44';
    ctx.fillText(lbl,x,gainDb>=0?y-13:y+20);
  });
}
function _eqDrawHover(lp, freqs, combined){
  const {ctx,W,H,ML,MR,MT,MB,PW,dbMin,dbMax,fMin,fMax,freqToX,dbToY}=lp;
  if(_eqHoverX===null||_eqHoverX<ML||_eqHoverX>W-MR) return;
  const N=freqs.length, hoverFreq=fMin*Math.pow(fMax/fMin,(_eqHoverX-ML)/PW);
  ctx.strokeStyle='#ffffff18'; ctx.lineWidth=1; ctx.setLineDash([3,3]);
  ctx.beginPath(); ctx.moveTo(_eqHoverX,MT); ctx.lineTo(_eqHoverX,H-MB); ctx.stroke(); ctx.setLineDash([]);
  const hIdx=Math.round((_eqHoverX-ML)/PW*(N-1)), hDb=combined[Math.max(0,Math.min(N-1,hIdx))]||0;
  const label=(hoverFreq<1000?hoverFreq.toFixed(0)+' Hz':(hoverFreq/1000).toFixed(2)+' kHz')+'  '+(hDb>=0?'+':'')+hDb.toFixed(1)+' dB';
  ctx.fillStyle='#00cfff99'; ctx.font='9px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillText(label,_eqHoverX+6>W-120?_eqHoverX-130:_eqHoverX+6,MT+14);
}
function drawEqCurve() {
  const canvas = document.getElementById('eq-curve-canvas');
  if (!canvas) return;
  const W=canvas.width=canvas.offsetWidth||600, H=canvas.height=canvas.offsetHeight||200;
  const ctx=canvas.getContext('2d');
  const ML=42,MR=42,MT=14,MB=22, PW=W-ML-MR, PH=H-MT-MB;
  const dbMin=-15,dbMax=15,fMin=20,fMax=24000;
  const freqToX=f=>ML+PW*Math.log10(f/fMin)/Math.log10(fMax/fMin);
  const dbToY=db=>MT+PH*(1-(db-dbMin)/(dbMax-dbMin));
  const lp={ctx,W,H,ML,MR,MT,MB,PW,PH,dbMin,dbMax,fMin,fMax,freqToX,dbToY};
  _eqDrawBackground(lp);
  _eqDrawLiveSpectrum(lp);
  _eqDrawDbGrid(lp);
  _eqDrawFreqGrid(lp);
  const N=512;
  const freqs=Array.from({length:N},(_,i)=>fMin*Math.pow(fMax/fMin,i/(N-1)));
  _eqDrawBandCurves(lp,freqs);
  const combined=freqs.map(f=>EQ_BANDS.reduce((sum,band,i)=>{
    if(_eqState[i].bypassed) return sum;
    const g=_eqState[i].gain,ngt=['highpass','lowpass','notch','bandpass'].includes(_eqState[i].type);
    if(!ngt&&Math.abs(g)<0.05) return sum;
    return sum+eqBqResponse(eqBqCoeffs(_eqState[i].type,_eqState[i].freq,g,_eqState[i].q),f);
  },0));
  _eqLastCombined=new Float32Array(combined);
  _eqDrawCombinedCurve(lp,freqs,combined);
  _eqDrawHandles(lp);
  _eqDrawHover(lp,freqs,combined);
}

let _eqHoverX = null;

function eqReset() {
  EQ_BANDS.forEach(b => {
    const sl = document.getElementById('eq-'+b.id);
    if (sl) sl.value = 0;
    setEqBand(b.id, 0);
  });
}

// ── Mémoires EQ (10 slots, localStorage) ─────────────────────
const _EQ_MEM_KEY = 'jarvis_eq_mem';
const _EQ_MEM_HOLD = 800; // ms clic long = sauvegarde
let _eqMemTimer = null;
let _eqMemSlots = Array(10).fill(null);

function _eqMemLoad() {
  try { _eqMemSlots = JSON.parse(localStorage.getItem(_EQ_MEM_KEY)) || Array(10).fill(null); }
  catch(_) { _eqMemSlots = Array(10).fill(null); }
  _eqMemSlots.forEach((s, i) => _eqMemUpdateBtn(i));
}

function _eqMemSave() {
  localStorage.setItem(_EQ_MEM_KEY, JSON.stringify(_eqMemSlots));
}

function _eqMemSnapshot() {
  return EQ_BANDS.map((b, i) => ({
    id:       b.id,
    gain:     _eqState[i].gain,
    freq:     _eqState[i].freq,
    q:        _eqState[i].q,
    type:     _eqState[i].type,
    bypassed: _eqState[i].bypassed,
  }));
}

function _eqMemApply(snap) {
  snap.forEach((s, i) => {
    _eqState[i].freq     = s.freq;
    _eqState[i].q        = s.q;
    _eqState[i].type     = s.type;
    _eqState[i].bypassed = s.bypassed;
    const sl = document.getElementById('eq-'+s.id);
    if (sl) sl.value = s.gain;
    setEqBand(s.id, s.gain);
    // freq/Q/type counters
    const fc = document.getElementById('eq-fc-'+s.id);
    const gc = document.getElementById('eq-gc-'+s.id);
    const qc = document.getElementById('eq-qc-'+s.id);
    if (fc) fc.textContent = s.freq >= 1000 ? (s.freq/1000).toFixed(1)+'kHz' : s.freq+'Hz';
    if (gc) gc.textContent = (s.gain >= 0 ? '+' : '') + parseFloat(s.gain).toFixed(1);
    if (qc) qc.textContent = parseFloat(s.q).toFixed(1);
    // bypass state
    const byp = document.getElementById('eq-byp-'+s.id);
    if (byp) { byp.classList.toggle('bypassed', s.bypassed); }
    // type buttons
    document.querySelectorAll(`[data-band="${s.id}"]`).forEach(tb => {
      tb.classList.toggle('active', tb.dataset.type === s.type);
    });
  });
  if (typeof eqPushNow === 'function') eqPushNow();
}

function _eqMemUpdateBtn(idx) {
  const btn = document.getElementById('eq-mem-btn-'+idx);
  if (!btn) return;
  const filled = _eqMemSlots[idx] !== null;
  btn.classList.toggle('filled', filled);
  if (filled && _eqMemSlots[idx]._label) btn.title = _eqMemSlots[idx]._label;
}

function eqMemPress(idx) {
  const btn = document.getElementById('eq-mem-btn-'+idx);
  if (btn) {
    btn.classList.add('pressing');
    btn.style.transition = `--dummy 0s`; // force reflow
    btn.style.setProperty('transition', 'width ' + _EQ_MEM_HOLD + 'ms linear');
  }
  _eqMemTimer = setTimeout(() => {
    _eqMemTimer = null;
    // SAUVEGARDE
    const snap = _eqMemSnapshot();
    snap._label = 'M' + (idx+1) + ' — ' + new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
    _eqMemSlots[idx] = snap;
    _eqMemSave();
    if (btn) { btn.classList.remove('pressing'); btn.classList.add('saving'); }
    setTimeout(() => { if (btn) btn.classList.remove('saving'); _eqMemUpdateBtn(idx); }, 600);
  }, _EQ_MEM_HOLD);
}

function eqMemRelease(idx) {
  if (_eqMemTimer) {
    clearTimeout(_eqMemTimer);
    _eqMemTimer = null;
    const btn = document.getElementById('eq-mem-btn-'+idx);
    if (btn) btn.classList.remove('pressing');
    // RAPPEL (clic court)
    if (_eqMemSlots[idx]) {
      _eqMemApply(_eqMemSlots[idx]);
      // highlight actif
      document.querySelectorAll('.eq-mem-btn').forEach(b => b.classList.remove('active-mem'));
      if (btn) btn.classList.add('active-mem');
    }
  }
}

function eqMemClear(idx) {
  _eqMemSlots[idx] = null;
  _eqMemSave();
  _eqMemUpdateBtn(idx);
  const btn = document.getElementById('eq-mem-btn-'+idx);
  if (btn) btn.classList.remove('active-mem');
}

// → _jarvisInit()

// ── Couplage EQ ↔ Voix JARVIS ──
let _eqVoiceCoupled = true;  // actif par défaut

function toggleEqVoiceCouple() {
  _eqVoiceCoupled = !_eqVoiceCoupled;
  _updateEqCoupleBadges();
  // Envoyer enabled au backend
  fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ enabled: _eqVoiceCoupled })
  }).catch(()=>{});
  if (_eqVoiceCoupled) queueSpeech('Égaliseur couplé à la voix.');
}

// ── Découplage voix JARVIS / chaîne DSP ──────────────────────
function toggleDspVoice() {
  _dspVoiceDecoupled = !_dspVoiceDecoupled;
  const ac = audioCtx;
  if (ac && _jarvisPreGain && _dspVoiceBypass) {
    const now = ac.currentTime;
    if (_dspVoiceDecoupled) {
      // Voix → sortie directe (bypass DSP)
      _jarvisPreGain.gain.setTargetAtTime(0, now, 0.02);
      _dspVoiceBypass.gain.setTargetAtTime(1, now, 0.02);
    } else {
      // Voix → chaîne DSP (mode normal)
      _jarvisPreGain.gain.setTargetAtTime(1, now, 0.02);
      _dspVoiceBypass.gain.setTargetAtTime(0, now, 0.02);
    }
  }
  // Mise à jour boutons
  const btn = document.getElementById('dsp-voice-decouple-btn');
  if (btn) {
    btn.classList.toggle('dsp-voice-decoupled', _dspVoiceDecoupled);
    btn.title = _dspVoiceDecoupled
      ? 'Voix JARVIS découplée du DSP — cliquer pour recoupler'
      : 'Voix JARVIS couplée au DSP — cliquer pour découpler';
  }
  const rackBtn = document.getElementById('rack-voice-bypass');
  if (rackBtn) {
    rackBtn.classList.toggle('on', !_dspVoiceDecoupled);
    rackBtn.classList.toggle('off', _dspVoiceDecoupled);
  }
}

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

// ═══════════════════════════════════════════════════════════
// ◈ EQ MUSIC — DAT PLAYER (bandes spécialisées musique)
// ═══════════════════════════════════════════════════════════

const DAT_EQ_BANDS = [
  { id:'sub',    freq:80,    type:'lowshelf',  Q:0.7, color:_cssVar('--orange3'), label:'SUB' },
  { id:'bass',   freq:300,   type:'peaking',   Q:0.8, color:_cssVar('--yellow2'), label:'BASS' },
  { id:'mids',   freq:3000,  type:'peaking',   Q:0.9, color:_cssVar('--teal'),    label:'MIDS' },
  { id:'treble', freq:10000, type:'highshelf', Q:0.7, color:_cssVar('--sky'),     label:'TREBLE' },
];
const _datEqState = [
  { freq:80,    q:0.7, type:'lowshelf',  bypassed:false, gain:0 },
  { freq:300,   q:0.8, type:'peaking',   bypassed:false, gain:0 },
  { freq:3000,  q:0.9, type:'peaking',   bypassed:false, gain:0 },
  { freq:10000, q:0.7, type:'highshelf', bypassed:false, gain:0 },
];
const _datEqFreqRange = [[20,400],[100,2000],[500,8000],[2000,24000]];

function _datEqNode(band) {
  return { sub:window._datEqSub, bass:window._datEqBass, mids:window._datEqMids, treble:window._datEqTreble }[band];
}

function _datEqUpdateCounters(idx) {
  const band = DAT_EQ_BANDS[idx];
  const s = _datEqState[idx];
  const fc = document.getElementById('dat-eq-fc-'+band.id);
  if (fc) fc.textContent = s.freq >= 1000 ? (s.freq/1000).toFixed(2)+'k' : s.freq.toFixed(0)+'Hz';
  const qc = document.getElementById('dat-eq-qc-'+band.id);
  if (qc) qc.textContent = s.q.toFixed(2);
}

function setDatEqBand(band, val) {
  const idx = _datEqBandIdx(band);
  const v = parseFloat(val);
  if (idx >= 0) _datEqState[idx].gain = v;
  const node = _datEqNode(band);
  const noGainTypes = ['highpass','lowpass','notch','bandpass'];
  if (node && idx >= 0 && !_datEqState[idx].bypassed && !noGainTypes.includes(_datEqState[idx].type))
    node.gain.value = v;
  const label = document.getElementById('dat-eq-'+band+'-val');
  if (label) label.textContent = (v >= 0 ? '+' : '') + v.toFixed(1) + ' dB';
  const gc = document.getElementById('dat-eq-gc-'+band);
  if (gc) gc.textContent = (v >= 0 ? '+' : '') + v.toFixed(1);
  const sl = document.getElementById('dat-eq-'+band);
  if (sl) updateSliderPct(sl);
  drawDatEqCurve();
  _datEqSchedulePush();
}

function datEqSetFreq(bandId, freq) {
  const idx = _datEqBandIdx(bandId);
  if (idx < 0) return;
  const [fMin, fMax] = _datEqFreqRange[idx];
  freq = Math.max(fMin, Math.min(fMax, freq));
  _datEqState[idx].freq = freq;
  DAT_EQ_BANDS[idx].freq = freq;
  const node = _datEqNode(bandId);
  if (node) node.frequency.value = freq;
  _datEqUpdateCounters(idx);
  drawDatEqCurve();
  _datEqSchedulePush();
}

function datEqSetQ(bandId, q) {
  const idx = _datEqBandIdx(bandId);
  if (idx < 0) return;
  q = Math.max(0.1, Math.min(12, q));
  _datEqState[idx].q = q;
  DAT_EQ_BANDS[idx].Q = q;
  const node = _datEqNode(bandId);
  if (node) node.Q.value = q;
  _datEqUpdateCounters(idx);
  drawDatEqCurve();
}

function datEqSetType(bandId, type) {
  const idx = _datEqBandIdx(bandId);
  if (idx < 0) return;
  _datEqState[idx].type = type;
  DAT_EQ_BANDS[idx].type = type;
  const node = _datEqNode(bandId);
  if (node) {
    const waTypes = {highpass:'highpass',lowpass:'lowpass',notch:'notch',
                     peaking:'peaking',lowshelf:'lowshelf',highshelf:'highshelf',bandpass:'bandpass'};
    try { node.type = waTypes[type] || 'peaking'; } catch(e) { /* BiquadFilterNode.type throws on invalid value */ }
    const noGain = ['highpass','lowpass','notch','bandpass'].includes(type);
    if (noGain) { node.gain.value = 0; }
    else { node.gain.value = _datEqState[idx].gain; }
  }
  document.querySelectorAll(`.dat-eq-type-btn[data-band="${bandId}"]`).forEach(b =>
    b.classList.toggle('active', b.dataset.type === type));
  drawDatEqCurve();
}

function datEqToggleBypass(bandId) {
  const idx = _datEqBandIdx(bandId);
  if (idx < 0) return;
  _datEqState[idx].bypassed = !_datEqState[idx].bypassed;
  const node = _datEqNode(bandId);
  if (node) {
    const noGain = ['highpass','lowpass','notch','bandpass'].includes(_datEqState[idx].type);
    if (_datEqState[idx].bypassed) {
      if (noGain) { node.type = 'allpass'; }
      else { node.gain.value = 0; }
    } else {
      node.type = _datEqState[idx].type;
      if (noGain) { node.gain.value = 0; }
      else { node.gain.value = _datEqState[idx].gain; }
    }
  }
  const btn = document.getElementById('dat-eq-byp-'+bandId);
  if (btn) btn.classList.toggle('bypassed', _datEqState[idx].bypassed);
  drawDatEqCurve();
}

// Canvas drag — DAT EQ (même logique que eqCanvasDown/Move voix)
let _datEqDrag = null; // { idx, startFreq, startGain }
const _DAT_EQ_ML=42, _DAT_EQ_MR=42, _DAT_EQ_MT=14, _DAT_EQ_MB=22;

function _datEqGetHandle(mx, my, canvas) {
  const W = canvas.width, H = canvas.height;
  const PW=W-_DAT_EQ_ML-_DAT_EQ_MR, PH=H-_DAT_EQ_MT-_DAT_EQ_MB;
  const fMin=20, fMax=24000, dbMin=-15, dbMax=15;
  let closest=-1, closestDist=28; // rayon légèrement plus grand (canvas moins haut)
  DAT_EQ_BANDS.forEach((band,i) => {
    const bx = _DAT_EQ_ML + PW*Math.log10(_datEqState[i].freq/fMin)/Math.log10(fMax/fMin);
    const gainDb = _datEqState[i].bypassed ? 0 : _datEqState[i].gain;
    const by = _DAT_EQ_MT + PH*(1-(gainDb-dbMin)/(dbMax-dbMin));
    const d = Math.sqrt((mx-bx)**2+(my-by)**2);
    if (d<closestDist) { closestDist=d; closest=i; }
  });
  return closest;
}
function datEqCanvasDown(e) {
  const c = _canvasCoords(e, 'dat-eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  const idx = _datEqGetHandle(mx, my, canvas);
  if (idx >= 0) {
    const gainDb = parseFloat(document.getElementById('dat-eq-'+DAT_EQ_BANDS[idx].id)?.value||0);
    _datEqDrag = { idx, startFreq:_datEqState[idx].freq, startGain:gainDb };
    canvas.style.cursor = 'grabbing';
    e.preventDefault();
  }
}
function datEqCanvasMove(e) {
  const c = _canvasCoords(e, 'dat-eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  if (_datEqDrag !== null) {
    const W = canvas.width, H = canvas.height;
    const PW=W-_DAT_EQ_ML-_DAT_EQ_MR, PH=H-_DAT_EQ_MT-_DAT_EQ_MB;
    const fMin=20, fMax=24000, dbMin=-15, dbMax=15;
    const nx = Math.max(0, Math.min(1, (mx-_DAT_EQ_ML)/PW));
    const newFreq = Math.round(fMin * Math.pow(fMax/fMin, nx));
    const ny = Math.max(0, Math.min(1, (my-_DAT_EQ_MT)/PH));
    const newGain = Math.max(-12, Math.min(12, dbMax - ny*(dbMax-dbMin)));
    const band = DAT_EQ_BANDS[_datEqDrag.idx];
    const sl = document.getElementById('dat-eq-'+band.id);
    if (sl) sl.value = newGain.toFixed(1);
    datEqSetFreq(band.id, newFreq);
    setDatEqBand(band.id, newGain.toFixed(1));
    e.preventDefault();
  } else {
    const idx = _datEqGetHandle(mx, my, canvas);
    canvas.style.cursor = idx >= 0 ? 'grab' : 'crosshair';
  }
}
function datEqCanvasUp() {
  _datEqDrag = null;
  const canvas = document.getElementById('dat-eq-curve-canvas');
  if (canvas) canvas.style.cursor = 'crosshair';
}
function datEqCanvasWheel(e) {
  const c = _canvasCoords(e, 'dat-eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  const idx = _datEqGetHandle(mx, my, canvas);
  if (idx < 0) return;
  e.preventDefault();
  const step = e.shiftKey ? 0.1 : 0.15;
  const q = Math.max(0.1, Math.min(12, _datEqState[idx].q + (e.deltaY > 0 ? -step : step)));
  datEqSetQ(DAT_EQ_BANDS[idx].id, q);
}

// ── Presets EQ Music ──
const _DAT_EQ_PRESETS = {
  'FLAT':      { sub:[0,0.7],   bass:[0,0.8],    mids:[0,0.9],    treble:[0,0.7]  },
  'BASS':      { sub:[8,0.7],   bass:[4,0.8],    mids:[-1,0.9],   treble:[0,0.7]  },
  'BRIGHT':    { sub:[0,0.7],   bass:[-1,0.8],   mids:[2,0.9],    treble:[6,0.7]  },
  'WARM':      { sub:[4,0.7],   bass:[3,0.8],    mids:[-1,0.9],   treble:[-3,0.7] },
  'CLUB':      { sub:[7,0.7],   bass:[2,0.8],    mids:[-1,0.9],   treble:[5,0.7]  },
  'ACOUSTIQUE':{ sub:[-2,0.7],  bass:[1,0.8],    mids:[3,1.2],    treble:[2,0.7]  },
  'ROCK':      { sub:[4,0.7],   bass:[2,0.8],    mids:[-2,0.9],   treble:[4,0.7]  },
  'JAZZ':      { sub:[2,0.7],   bass:[3,0.8],    mids:[1,0.9],    treble:[3,0.7]  },
};

function applyDatEqPreset(name) {
  const p = _DAT_EQ_PRESETS[name];
  if (!p) return;
  ['sub','bass','mids','treble'].forEach(band => {
    const [gain, q] = p[band];
    const sl = document.getElementById('dat-eq-' + band);
    if (sl) sl.value = gain;
    setDatEqBand(band, gain);
    datEqSetQ(band, q);
  });
  document.querySelectorAll('.dat-eq-preset-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll(`[data-dat-eq-preset="${name}"]`).forEach(b => b.classList.add('active'));
  _datEqSchedulePush();
}

let _datEqPushTimer = null;
function _datEqSchedulePush() {
  clearTimeout(_datEqPushTimer);
  _datEqPushTimer = setTimeout(pushDspParamsToBackend, _DSP_PUSH_MS);
}

function _datEqDrawSpectrum(ctx, eq) {
  const {W, ML, MR, MT, MB, PW, PH, fMin, fMax} = eq;
  const anL = window._datAnL;
  let hasData = false, specBuf = null;
  if (anL && window._datActive) { specBuf = new Uint8Array(anL.frequencyBinCount); anL.getByteFrequencyData(specBuf); hasData = true; }
  const N = specBuf ? specBuf.length : 1024;
  const nyq = (typeof audioCtx!=='undefined'&&audioCtx?audioCtx.sampleRate:_SAMPLE_RATE)/2;
  if (!window._datEqSpecPeaks||window._datEqSpecPeaks.length!==W) window._datEqSpecPeaks=new Float32Array(W);
  const peaks=window._datEqSpecPeaks;
  ctx.beginPath(); let first=true;
  for(let px=ML;px<=W-MR;px++){
    let val=0.04;
    if(hasData){const f=fMin*Math.pow(fMax/fMin,(px-ML)/PW);val=Math.max(specBuf[Math.min(Math.round(f/nyq*N),N-1)]/255,0.04);}
    peaks[px]=Math.max(peaks[px]*0.993,val);
    const sy=MT+PH*(1-val);
    if(first){ctx.moveTo(px,MT+PH);ctx.lineTo(px,sy);first=false;}else ctx.lineTo(px,sy);
  }
  ctx.lineTo(W-MR,MT+PH);ctx.closePath();
  const gSpec=ctx.createLinearGradient(0,MT,0,MT+PH);
  gSpec.addColorStop(0,'rgba(0,200,255,.25)');gSpec.addColorStop(0.45,'rgba(0,150,180,.12)');gSpec.addColorStop(1,'rgba(0,80,120,.04)');
  ctx.fillStyle=gSpec;ctx.fill();
  ctx.beginPath();ctx.strokeStyle='rgba(0,200,255,.35)';ctx.lineWidth=1;first=true;
  for(let px=ML;px<=W-MR;px++){const sy=MT+PH*(1-peaks[px]);first?(ctx.moveTo(px,sy),first=false):ctx.lineTo(px,sy);}
  ctx.stroke();
}
function _datEqDrawGrid(ctx, eq) {
  const {W, H, ML, MR, MT, MB, PH, freqToX, dbToY} = eq;
  [-12,-9,-6,-3,-1,0,1,3,6,9,12].forEach(db=>{
    const y=dbToY(db),isZero=db===0,isMajor=db%3===0;
    ctx.strokeStyle=isZero?'rgba(255,255,255,.18)':isMajor?'rgba(0,180,220,.07)':'rgba(0,150,180,.03)';
    ctx.lineWidth=isZero?1.5:isMajor?0.8:0.4;
    ctx.beginPath();ctx.moveTo(ML,y);ctx.lineTo(W-MR,y);ctx.stroke();
    if(isMajor){ctx.fillStyle='rgba(100,200,255,.55)';ctx.font='9px Share Tech Mono';ctx.textAlign='right';ctx.fillText((db>0?'+':'')+db,ML-5,y+3);}
  });
  [20,50,100,200,500,1000,2000,5000,10000,20000].forEach(f=>{
    const x=freqToX(f);
    ctx.strokeStyle='rgba(0,150,200,.06)';ctx.lineWidth=0.4;
    ctx.beginPath();ctx.moveTo(x,MT);ctx.lineTo(x,H-MB);ctx.stroke();
    ctx.fillStyle='rgba(100,200,255,.45)';ctx.font='9px Share Tech Mono';ctx.textAlign='center';
    ctx.fillText(f>=1000?f/1000+'k':f,x,H-MB+12);
  });
  ctx.fillStyle='rgba(100,200,255,.55)';ctx.font='9px Share Tech Mono';ctx.textAlign='right';
  ctx.fillText('0',ML-5,dbToY(0)+3);
}
function _datEqDrawCurve(ctx, eq) {
  const {W, fMin, fMax, dbMin, dbMax, dbToY} = eq;
  const combined = new Float32Array(W);
  DAT_EQ_BANDS.forEach((band,i)=>{
    const s=_datEqState[i]; if(s.bypassed) return;
    const coeff=eqBqCoeffs(s.type,s.freq,s.gain,s.q);
    for(let px=0;px<W;px++){combined[px]+=eqBqResponse(coeff,fMin*Math.pow(fMax/fMin,px/W));}
  });
  window._datEqLastCombined=combined;
  ctx.beginPath();let fp=true;
  for(let px=0;px<W;px++){const y=dbToY(Math.max(dbMin,Math.min(dbMax,combined[px])));fp?(ctx.moveTo(px,y),fp=false):ctx.lineTo(px,y);}
  ctx.strokeStyle='rgba(255,200,0,.9)';ctx.lineWidth=2;ctx.stroke();
}
function _datEqDrawHandles(ctx, eq) {
  const {freqToX, dbToY} = eq;
  DAT_EQ_BANDS.forEach((band,i)=>{
    const s=_datEqState[i];
    const gainDb=s.bypassed||['highpass','lowpass','notch','bandpass'].includes(s.type)?0:s.gain;
    const bx=freqToX(s.freq), by=dbToY(gainDb);
    ctx.beginPath();ctx.arc(bx,by,8,0,Math.PI*2);
    ctx.fillStyle=s.bypassed?'rgba(100,100,100,.4)':band.color+'99';ctx.fill();
    ctx.strokeStyle=s.bypassed?'#555':band.color;ctx.lineWidth=1.5;ctx.stroke();
    ctx.fillStyle=s.bypassed?'#555':'#fff';ctx.font='bold 8px Orbitron';ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillText(band.label[0],bx,by);
  });
  ctx.textBaseline='alphabetic';
}
function drawDatEqCurve() {
  const canvas = document.getElementById('dat-eq-curve-canvas');
  if (!canvas) return;
  const W = canvas.width = canvas.offsetWidth||600, H = canvas.height = canvas.offsetHeight||160;
  const ctx = canvas.getContext('2d');
  const ML=_DAT_EQ_ML, MR=_DAT_EQ_MR, MT=_DAT_EQ_MT, MB=_DAT_EQ_MB;
  const PW=W-ML-MR, PH=H-MT-MB, dbMin=-15, dbMax=15, fMin=20, fMax=24000;
  const eq = {
    ctx, W, H, ML, MR, MT, MB, PW, PH, fMin, fMax, dbMin, dbMax,
    freqToX: f  => ML+PW*Math.log10(f/fMin)/Math.log10(fMax/fMin),
    dbToY:   db => MT+PH*(1-(db-dbMin)/(dbMax-dbMin))
  };
  const bgGrd = ctx.createRadialGradient(W/2,H/2,10,W/2,H/2,W*0.75);
  bgGrd.addColorStop(0,'#030e18');bgGrd.addColorStop(1,'#010810');
  ctx.fillStyle=bgGrd;ctx.fillRect(0,0,W,H);
  const vig=ctx.createRadialGradient(W/2,H/2,PW*0.3,W/2,H/2,W*0.65);
  vig.addColorStop(0,'rgba(0,0,0,0)');vig.addColorStop(1,'rgba(0,0,0,.55)');
  ctx.fillStyle=vig;ctx.fillRect(0,0,W,H);
  for(let y=MT;y<H-MB;y+=3){ctx.fillStyle='rgba(0,0,0,.08)';ctx.fillRect(ML,y,PW,1);}
  _datEqDrawSpectrum(ctx, eq);
  _datEqDrawGrid(ctx, eq);
  _datEqDrawCurve(ctx, eq);
  _datEqDrawHandles(ctx, eq);
}

// ── Canvas drag interaction ──
function _eqGetHandle(mx, my, canvas) {
  const W = canvas.width, H = canvas.height;
  const ML=34, MR=6, MT=8, MB=18;
  const PW=W-ML-MR, PH=H-MT-MB;
  const fMin=20, fMax=24000, dbMin=-15, dbMax=15;
  let closest=-1, closestDist=22;
  EQ_BANDS.forEach((band,i) => {
    const bx = ML + PW*Math.log10(_eqState[i].freq/fMin)/Math.log10(fMax/fMin);
    const gainDb = _eqState[i].bypassed ? 0 : parseFloat(document.getElementById('eq-'+band.id)?.value||0);
    const by = MT + PH*(1-(gainDb-dbMin)/(dbMax-dbMin));
    const d = Math.sqrt((mx-bx)**2+(my-by)**2);
    if (d<closestDist) { closestDist=d; closest=i; }
  });
  return closest;
}

function eqCanvasDown(e) {
  const c = _canvasCoords(e, 'eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  const idx = _eqGetHandle(mx, my, canvas);
  if (idx >= 0) {
    const gainDb = parseFloat(document.getElementById('eq-'+EQ_BANDS[idx].id)?.value||0);
    _eqDrag = { idx, startFreq:_eqState[idx].freq, startGain:gainDb };
    canvas.style.cursor = 'grabbing';
    e.preventDefault();
  }
}

function eqCanvasMove(e) {
  const c = _canvasCoords(e, 'eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;

  if (_eqDrag !== null) {
    const W = canvas.width, H = canvas.height;
    const ML=34, MR=6, MT=8, MB=18;
    const PW=W-ML-MR, PH=H-MT-MB;
    const fMin=20, fMax=24000, dbMin=-15, dbMax=15;

    // X → frequency (log)
    const nx = Math.max(0, Math.min(1, (mx-ML)/PW));
    const newFreq = Math.round(fMin * Math.pow(fMax/fMin, nx));

    // Y → gain
    const ny = Math.max(0, Math.min(1, (my-MT)/PH));
    const newGain = Math.max(-12, Math.min(12, dbMax - ny*(dbMax-dbMin)));

    const band = EQ_BANDS[_eqDrag.idx];
    const sl = document.getElementById('eq-'+band.id);
    if (sl) sl.value = newGain;
    eqSetFreq(band.id, newFreq);
    setEqBand(band.id, newGain);
    e.preventDefault();
  } else {
    // Hover: show crosshair
    const idx = _eqGetHandle(mx, my, canvas);
    canvas.style.cursor = idx >= 0 ? 'grab' : 'crosshair';
    _eqHoverX = mx;
    drawEqCurve();
  }
}

function eqCanvasUp(e) {
  _eqDrag = null;
  const canvas = document.getElementById('eq-curve-canvas');
  if (canvas) canvas.style.cursor = 'crosshair';
}

function eqCanvasLeave(e) {
  if (_eqDrag) { _eqDrag = null; }
  _eqHoverX = null;
  drawEqCurve();
  const canvas = document.getElementById('eq-curve-canvas');
  if (canvas) canvas.style.cursor = 'crosshair';
}

function eqCanvasWheel(e) {
  const c = _canvasCoords(e, 'eq-curve-canvas'); if (!c) return;
  const {mx, my, canvas} = c;
  const idx = _eqGetHandle(mx, my, canvas);
  if (idx >= 0) {
    const delta = e.deltaY > 0 ? -0.15 : 0.15;
    eqSetQ(EQ_BANDS[idx].id, _eqState[idx].q + delta);
    e.preventDefault();
  }
}

function setDspGain(val) {
  const v = parseFloat(val);
  if (_dspGainNode) _dspGainNode.gain.value = Math.pow(10, v / 20);
  _dspSchedulePush();
}

function setDspCompressor(param, val) {
  const v = parseFloat(val);
  if (!_dspCompressor) return;
  if      (param === 'threshold') _dspCompressor.threshold.value = v;
  else if (param === 'ratio')     _dspCompressor.ratio.value = v;
  else if (param === 'attack')    _dspCompressor.attack.value = v / 1000;
  else if (param === 'release')   _dspCompressor.release.value = v / 1000;
  _dspSchedulePush();
}

function setDspSpeed(val) {
  _dspPlaybackRate = parseFloat(val);
  const sl = document.getElementById('dsp-speed');
  if (sl) _syncRangeSlider(sl);
}

function setDspPitch(val) {
  _dspPitchSemi = parseInt(val);
  const sl = document.getElementById('dsp-pitch');
  if (sl) _syncRangeSlider(sl);
}

function setDspVolume(val) {
  _dspVolume = parseFloat(val) / 100;
  const sl = document.getElementById('dsp-vol');
  if (sl) _syncRangeSlider(sl);
}

function syncDspVoices() {
  const mainSel = document.getElementById('voice-select');
  const dspSel  = document.getElementById('dsp-voice-sel');
  if (!mainSel || !dspSel) return;
  dspSel.innerHTML = mainSel.innerHTML;
  dspSel.value = mainSel.value;
  // Init TTS local panel in parallel
  initTtsLocal();
}

function setDspVoice(val) {
  const mainSel = document.getElementById('voice-select');
  if (mainSel) { mainSel.value = val; switchVoice(val); }
}

// ── TTS engine management ──────────────────────────────────────
let _ttsCurrentEngine = 'edge';

function initTtsLocal() {
  _ttsShowEngine('edge');
}

function _ttsShowEngine(eng) {
  _ttsCurrentEngine = eng;
  // Chat sidebar buttons
  const edgeBtn   = document.getElementById('voice-eng-edge');
  const kokoroBtn = document.getElementById('voice-eng-kokoro');
  const label     = document.getElementById('voice-mode-cloud');
  const cloudPanel  = document.getElementById('voice-cloud-panel');
  const kokoroPanel = document.getElementById('voice-kokoro-panel');
  if (edgeBtn)   edgeBtn.classList.toggle('active', eng === 'edge');
  if (kokoroBtn) kokoroBtn.classList.toggle('active', eng === 'kokoro');
  if (label) {
    if (eng === 'kokoro') label.textContent = '◈ KOKORO — NEURAL LOCAL';
    else                  label.textContent = '◉ EDGE — MICROSOFT CLOUD';
  }
  _disp(cloudPanel,  eng === 'edge',   'block');
  _disp(kokoroPanel, eng === 'kokoro', 'block');
  // DSP tab buttons + panels
  const dspEdge   = document.getElementById('dsp-eng-edge');
  const dspKokoro = document.getElementById('dsp-eng-kokoro');
  const panelEdge   = document.getElementById('dsp-panel-edge');
  const panelKokoro = document.getElementById('dsp-panel-kokoro');
  if (dspEdge)   dspEdge.classList.toggle('active', eng === 'edge');
  if (dspKokoro) dspKokoro.classList.toggle('active', eng === 'kokoro');
  _disp(panelEdge,   eng === 'edge');
  _disp(panelKokoro, eng === 'kokoro');
}

async function setDefaultTtsEngine(eng) {
  // Persiste le moteur par défaut (utilisé au démarrage et par la boucle connectivité)
  await fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ tts_default_engine: eng })
  }).catch(() => {});
  _syncDefaultEngineButtons(eng);
}

function _syncDefaultEngineButtons(eng) {
  const defEdge   = document.getElementById('dsp-def-edge');
  const defKokoro = document.getElementById('dsp-def-kokoro');
  if (defEdge)   defEdge.classList.toggle('active', eng === 'edge');
  if (defKokoro) defKokoro.classList.toggle('active', eng === 'kokoro');
}

// ── Polling statut moteurs TTS ──────────────────────────────────
async function _ttsStatusPoll() {
  try {
    const r = await fetch('/api/tts/status');
    const d = await r.json();
    ['edge','kokoro','piper','sapi'].forEach(eng => {
      const st = d[eng];
      if (!st) return;
      // Tous les boutons portant data-args contenant cet engine
      document.querySelectorAll(`[data-args*='"${eng}"'] .veng-dot`).forEach(dot => {
        dot.classList.remove('ok','err');
        const btn = dot.closest('button');
        if (btn && btn.classList.contains('active')) {
          dot.classList.add(st.ok ? 'ok' : 'err');
        }
      });
    });
  } catch(e) { /* network error — skip poll cycle */ }
}
_ttsStatusPoll();
setInterval(_ttsStatusPoll, _TTS_STATUS_POLL_MS);

function setKokoroSpeed(val) {
  const v = parseFloat(val);
  const lbl = document.getElementById('dsp-kokoro-speed-val');
  if (lbl) lbl.textContent = v.toFixed(2) + '×';
  fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ tts_kokoro_speed: v })
  }).catch(() => {});
}


async function setTtsEngine(eng) {
  if (eng !== 'edge') _lastLocalEngine = eng;
  _ttsShowEngine(eng);
  await fetch('/api/dsp-params', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ tts_engine: eng })
  }).catch(() => {});
  _ttsStatusPoll();
}

async function setDspLocalVoice(val) {
  await fetch('/api/dsp-params', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ tts_local_voice: val })
  }).catch(() => {});
}


// Push DSP params to backend so TTS server applies them
function pushDspParamsToBackend() {
  const p = {
    enabled:        true,
    eq_low:         _eqState[0].gain,
    eq_mid:         _eqState[1].gain,
    eq_high:        _eqState[2].gain,
    eq_air:         _eqState[3].gain,
    comp_threshold: _dspCompressor ? _dspCompressor.threshold.value : -24,
    comp_ratio:     _dspCompressor ? _dspCompressor.ratio.value     : 4,
    comp_attack:    _dspCompressor ? _dspCompressor.attack.value    : 0.003,
    comp_release:   _dspCompressor ? _dspCompressor.release.value   : 0.25,
    gain: _dspGainNode ? (20 * Math.log10(Math.max(0.001, _dspGainNode.gain.value))) : 0,
  };
  // Voice EQ — état complet depuis _eqState (source de vérité)
  ['low','mid','high','air'].forEach(function(id,i){
    p['eq_'+id+'_type'] = _eqState[i].type;
    p['eq_'+id+'_freq'] = _eqState[i].freq;
    p['eq_'+id+'_q']    = _eqState[i].q;
    p['eq_'+id+'_byp']  = _eqState[i].bypassed;
  });
  // DAT EQ music — état complet depuis _datEqState (source de vérité)
  ['sub','bass','mids','treble'].forEach(function(id,i){
    p['dat_eq_'+id]          = _datEqState[i].gain;
    p['dat_eq_'+id+'_type']  = _datEqState[i].type;
    p['dat_eq_'+id+'_freq']  = _datEqState[i].freq;
    p['dat_eq_'+id+'_q']     = _datEqState[i].q;
    p['dat_eq_'+id+'_byp']   = _datEqState[i].bypassed;
  });
  fetch('/api/dsp-params', {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(p)
  }).catch(()=>{});
}


function _tvBar(pct) {
  const f = Math.round(Math.min(pct,100)/5);
  return '<span class="tv-bar-bk">[</span><span class="tv-bar-fill">'+'█'.repeat(f)+'</span><span class="tv-bar-empty">'+'░'.repeat(20-f)+'</span><span class="tv-bar-bk">]</span>';
}
const _tvSep = '<span class="tv-sep-line">────────────────────────────────────────────</span>';
function _tvSec(t) { return `<div class="tv-sec">◈ ${t}</div>`; }
function _tvRow(lbl, val, ok=null) {
  const dot = ok===null ? '<span class="tv-dot-null">◎</span>' : ok ? '<span class="tv-dot-ok">◉</span>' : '<span class="tv-dot-err">◉</span>';
  return `${dot} <span class="tv-row-lbl">${lbl}</span> <span class="tv-row-val">${val}</span><br>`;
}
function _tvEqSign(v) { return v > 0.05 ? `+${v.toFixed(1)}` : v < -0.05 ? `${v.toFixed(1)}` : '0.0'; }
function _tvDiagBuildHardware(d) {
  let h = '';
  h += _tvSec('MATÉRIEL');
  h += _tvRow('CPU', `${d.cpu_cores}c/${d.cpu_threads}t @ ${d.cpu_freq} GHz &nbsp; ${d.cpu_pct}% ${_tvBar(d.cpu_pct)}`, d.cpu_pct < 80);
  if (d.cpu_temp != null) h += _tvRow('CPU TEMP', `${d.cpu_temp} °C`, d.cpu_temp < 80);
  h += _tvRow('RAM', `${d.ram_used} / ${d.ram_total} GB &nbsp; ${d.ram_pct}% ${_tvBar(d.ram_pct)}`, d.ram_pct < 85);
  if (d.swap_total > 0) h += _tvRow('SWAP', `${d.swap_used} / ${d.swap_total} GB &nbsp; ${d.swap_pct}% ${_tvBar(d.swap_pct)}`, d.swap_pct < 50);
  h += _tvSep + '<br>';
  h += _tvSec('CARTE GRAPHIQUE');
  if (d.gpu_name !== 'N/A') {
    h += _tvRow('GPU', d.gpu_name, true);
    h += _tvRow('CHARGE GPU', `${d.gpu_pct}% ${_tvBar(d.gpu_pct)}`, d.gpu_pct < 90);
    h += _tvRow('VRAM', `${d.vram_used} / ${d.vram_total} GB ${_tvBar(Math.round(d.vram_used/d.vram_total*100))}`, d.vram_used/d.vram_total < 0.9);
    if (d.gpu_temp !== null) h += _tvRow('GPU TEMP', `${d.gpu_temp} °C`, d.gpu_temp < 85);
    if (d.gpu_power !== null) h += _tvRow('PUISSANCE', `${d.gpu_power} W`, null);
    if (d.gpu_clock !== null) h += _tvRow('HORLOGE', `${d.gpu_clock} MHz`, null);
  } else { h += _tvRow('GPU', 'Non détecté', false); }
  h += _tvSep + '<br>';
  h += _tvSec('STOCKAGE & RÉSEAU');
  h += _tvRow('DISQUE C:', `${d.disk_used} / ${d.disk_total} GB &nbsp; ${d.disk_pct}% ${_tvBar(d.disk_pct)}`, d.disk_pct < 80);
  h += _tvRow('RÉSEAU', `↑ ${d.net_sent} MB &nbsp; ↓ ${d.net_recv} MB`, null);
  h += _tvRow('UPTIME', d.uptime, null); h += _tvRow('PLATEFORME', `${d.platform} — ${d.hostname}`, null);
  h += _tvSep + '<br>';
  h += _tvSec('IA STACK');
  h += _tvRow('OLLAMA', d.ollama_ok ? `<span class="tv-ok-txt">EN LIGNE</span> &nbsp; latence ${d.ollama_latency} ms` : '<span class="tv-err-txt">HORS LIGNE</span>', d.ollama_ok);
  h += _tvRow('LLM ACTIF', d.llm_model, null); h += _tvRow('PROVIDER', d.llm_provider.toUpperCase(), null);
  if (d.ollama_models && d.ollama_models.length) h += _tvRow('MODÈLES DISPO', d.ollama_models.join(' · '), null);
  h += _tvRow('VOIX TTS', d.llm_voice || '—', null);
  h += _tvRow('MÉMOIRE', `${d.memory_exchanges} échanges / ${d.memory_limit} max`, d.memory_exchanges < d.memory_limit * 0.9);
  h += _tvSep + '<br>';
  return h;
}
function _tvDiagBuildAudio({ d, dspP, acOk, acState, acSR, acLat, chainOk, eqBands }) {
  let h = '';
  h += _tvSec('CHAÎNE AUDIO WEB API');
  h += _tvRow('AudioContext', `${acState.toUpperCase()} ${acOk?'':'(non initialisé — ouvrir DSP)'}`, acOk && acState === 'running');
  h += _tvRow('SAMPLE RATE', acSR ? acSR+' Hz' : '—', acSR >= 44100);
  h += _tvRow('LATENCE BASE', acLat, null);
  h += _tvRow('CHAÎNE DSP', chainOk ? 'AnalyserNode → EQ×4 → Compressor → Gain → Destination' : acOk ? 'Partielle ou non connectée' : 'Inactive', chainOk);
  h += _tvRow('ANALYSER FFT', typeof _dspAnalyser!=='undefined'&&_dspAnalyser ? `2048 pts — ${_dspAnalyser.fftSize} Hz` : 'Absent', !!_dspAnalyser);
  h += _tvSep + '<br>';
  h += _tvSec('DSP — PARAMÈTRES ACTIFS');
  if (dspP) {
    h += _tvRow('DSP ACTIF', dspP.enabled ? '<span class="tv-ok-txt">OUI</span>' : '<span class="tv-err-txt">NON</span>', dspP.enabled);
    h += _tvRow('EQ LOW 250Hz', _tvEqSign(dspP.eq_low)+' dB', Math.abs(dspP.eq_low)<=12);
    h += _tvRow('EQ MID 1kHz', _tvEqSign(dspP.eq_mid)+' dB', Math.abs(dspP.eq_mid)<=12);
    h += _tvRow('EQ HIGH 4kHz', _tvEqSign(dspP.eq_high)+' dB', Math.abs(dspP.eq_high)<=12);
    h += _tvRow('EQ AIR 12kHz', _tvEqSign(dspP.eq_air)+' dB', Math.abs(dspP.eq_air)<=12);
    h += _tvRow('COMPRESSEUR', `Seuil ${dspP.comp_threshold} dB &nbsp;|&nbsp; Ratio ${dspP.comp_ratio}:1 &nbsp;|&nbsp; Att ${Math.round(dspP.comp_attack*1000)}ms &nbsp;|&nbsp; Rel ${Math.round(dspP.comp_release*1000)}ms`, null);
    h += _tvRow('GAIN SORTIE', _tvEqSign(dspP.gain)+' dB', Math.abs(dspP.gain)<=6);
  }
  if (eqBands) { h += '<br>'; ['LOW','MID','HIGH','AIR'].forEach((n,i) => { const b=eqBands[i]; h += _tvRow(`EQ BANDE ${n}`, `${b.freq} Hz &nbsp;|&nbsp; Q ${b.q.toFixed(2)} &nbsp;|&nbsp; ${b.type.toUpperCase()} &nbsp;|&nbsp; ${b.bypassed?'<span class="tv-warn-txt">BYPASS</span>':'<span class="tv-ok-txt">ACTIF</span>'}`, !b.bypassed); }); }
  h += _tvSep + '<br>';
  h += _tvSec('DEEPFILTERNET — IA DÉBRUITAGE');
  if (d) {
    h += _tvRow('DISPONIBLE', d.df_available ? '<span class="tv-ok-txt">OUI</span>' : '<span class="tv-warn-txt">NON (pip install deepfilternet)</span>', d.df_available);
    h += _tvRow('ACTIF', d.df_enabled ? '<span class="tv-ok-txt">OUI</span>' : '<span class="tv-dim-txt">NON</span>', d.df_enabled !== false);
    if (d.df_available) {
      h += _tvRow('SAMPLE RATE', d.df_sr+' Hz', null);
      h += _tvRow('PROCESSEUR', 'CPU (PyTorch — RTX 5080 sm_120 non supporté par cu121)', null);
      if (dspP) { h += _tvRow('ATTÉNUATION', dspP.df_atten_lim+' dB', null); h += _tvRow('POST-FILTRE', dspP.df_post_filter?'Activé':'Désactivé', null); }
    }
  } else { h += _tvRow('STATUT', 'API inaccessible', false); }
  return h;
}
async function testDspVoice() {
  let d = null;
  try { d = await fetch('/api/sysdiag').then(r => r.json()); } catch(e) {}
  let dspP = null;
  try { dspP = await _fetchDspParams(); } catch(e) {}
  const acOk = !!audioCtx, acState = acOk ? audioCtx.state : 'absent';
  const acSR = acOk ? audioCtx.sampleRate : 0;
  const acLat = acOk && audioCtx.baseLatency != null ? Math.round(audioCtx.baseLatency*1000)+' ms' : '—';
  const chainOk = acOk && !!_dspGainNode && !!_dspCompressor && !!_dspAnalyser;
  const eqBands = typeof _eqState !== 'undefined' ? _eqState : null;
  let html = `<div class="tv-diag-wrap"><div class="tv-diag-title">◈ DIAGNOSTIC DSP AUDIO — JARVIS VOICE ENGINE</div>`;
  if (d) html += _tvDiagBuildHardware(d);
  html += _tvDiagBuildAudio({ d, dspP, acOk, acState, acSR, acLat, chainOk, eqBands });
  html += '</div>';
  switchTab('chat');
  const bubble = addMessage('jarvis', '');
  bubble.innerHTML = html;
  if (d) {
    history.push({role:'user', content:`[DIAGNOSTIC DSP AUDIO — ${new Date().toLocaleTimeString('fr-FR')}]\nMatériel: CPU ${d.cpu_pct}% @ ${d.cpu_freq}GHz | RAM ${d.ram_used}/${d.ram_total}GB (${d.ram_pct}%) | GPU ${d.gpu_name} ${d.gpu_pct}% VRAM ${d.vram_used}/${d.vram_total}GB${d.gpu_temp?` ${d.gpu_temp}°C`:''}\nOllama: ${d.ollama_ok?'EN LIGNE '+d.ollama_latency+'ms':'HORS LIGNE'} | Modèle: ${d.llm_model} | Voix: ${d.llm_voice}\nDeepFilterNet: ${d.df_available?'disponible':'absent'} ${d.df_enabled?'(actif)':'(inactif)'}\nAudioContext: ${acState} ${acSR}Hz | Chaîne DSP: ${chainOk?'complète':'incomplète'}\nMémoire: ${d.memory_exchanges}/${d.memory_limit} échanges`});
    history.push({role:'assistant', content:'Diagnostic DSP et système reçu. Contexte intégré.'});
  }
  const issues = [];
  if (d) {
    if (d.cpu_pct >= 80)  issues.push(`CPU chargé à ${d.cpu_pct} pourcent`);
    if (d.ram_pct >= 85)  issues.push(`mémoire RAM à ${d.ram_pct} pourcent`);
    if (!d.ollama_ok)     issues.push('serveur Ollama hors ligne');
    if (!chainOk)         issues.push('chaîne audio DSP incomplète');
  }
  if (issues.length === 0) {
    const dfTxt = d?.df_available && d?.df_enabled ? ' DeepFilterNet actif.' : '';
    queueSpeech(`Diagnostic audio nominal.${dfTxt} AudioContext ${acState}. Chaîne D.S.P. complète. ${d ? 'Ollama en ligne, latence '+d.ollama_latency+' millisecondes.' : ''} Tous les systèmes vocaux sont opérationnels.`);
  } else {
    queueSpeech(`Attention. Diagnostic audio: ${issues.join(', ')}. Intervention recommandée.`);
  }
}

// ══════════════════════════════════════
// MIRE DE TEST AUDIO — 30 secondes
// ══════════════════════════════════════
let _mireSource = null;
let _mirePlaying = false;

const MIRE_SEQUENCE = [
  { freq: 1000, dur: 2,   label: '1 kHz — Référence 0 dB' },
  { freq: 100,  dur: 2,   label: '100 Hz — Basses' },
  { freq: 250,  dur: 2,   label: '250 Hz — Bas-médiums' },
  { freq: 500,  dur: 2,   label: '500 Hz — Médiums graves' },
  { freq: 1000, dur: 2,   label: '1 kHz — Médiums' },
  { freq: 2000, dur: 2,   label: '2 kHz — Médiums aigus' },
  { freq: 4000, dur: 2,   label: '4 kHz — Présence' },
  { freq: 8000, dur: 2,   label: '8 kHz — Aigus' },
  { freq: 12000,dur: 2,   label: '12 kHz — Air' },
  { freq: 16000,dur: 2,   label: '16 kHz — Brillance' },
  // Sweep + bruit rose simulé via multi-sinusoïde
  { sweep: true, dur: 4,  label: 'Sweep 20Hz → 20kHz' },
  { noise: true, dur: 3,  label: 'Bruit rose (spectre plat)' },
  { freq: 1000, dur: 1,   label: '1 kHz — Référence finale' },
];

async function playMire() {
  if (_mirePlaying) { stopMire(); return; }
  if (!_dspInited) initDsp();
  if (audioCtx.state === 'suspended') await audioCtx.resume();
  _mirePlaying = true;

  const btn = document.getElementById('mire-btn');
  if (btn) btn.textContent = '⏹ STOP MIRE';

  for (let i = 0; i < MIRE_SEQUENCE.length && _mirePlaying; i++) {
    const step = MIRE_SEQUENCE[i];
    const mireLabel = document.getElementById('mire-label');
    if (mireLabel) mireLabel.textContent = '▶ ' + step.label;

    if (step.noise) {
      // Bruit rose via nœuds de bruit blanc filtré
      await _playPinkNoise(step.dur);
    } else if (step.sweep) {
      await _playSweep(20, 20000, step.dur);
    } else {
      await _playTone(step.freq, step.dur);
    }
  }
  if (_mirePlaying) {
    stopMire();
    const lbl = document.getElementById('mire-label');
    if (lbl) lbl.textContent = '✓ MIRE TERMINÉE';
  }
}

function stopMire() {
  _mirePlaying = false;
  if (_mireSource) { try { _mireSource.stop(); } catch(e){/* AudioNode déjà stoppé */} _mireSource = null; }
  const btn = document.getElementById('mire-btn');
  if (btn) btn.textContent = '▶ MIRE 30s';
}

async function _playTone(freq, dur) {
  return new Promise(resolve => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.value = 0.3;
    osc.connect(gain);
    gain.connect(analyser);
    _mireSource = osc;
    osc.start();
    osc.stop(audioCtx.currentTime + dur);
    osc.onended = () => resolve();
  });
}

async function _playSweep(f0, f1, dur) {
  return new Promise(resolve => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(f0, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(f1, audioCtx.currentTime + dur);
    gain.gain.value = 0.25;
    osc.connect(gain);
    gain.connect(analyser);
    _mireSource = osc;
    osc.start();
    osc.stop(audioCtx.currentTime + dur);
    osc.onended = () => resolve();
  });
}

async function _playPinkNoise(dur) {
  return new Promise(resolve => {
    const bufSize = Math.ceil(audioCtx.sampleRate * dur);
    const buf = audioCtx.createBuffer(1, bufSize, audioCtx.sampleRate);
    const data = buf.getChannelData(0);
    // Pink noise approximation (Voss algorithm)
    let b0=0,b1=0,b2=0,b3=0,b4=0,b5=0,b6=0;
    for (let i=0; i<bufSize; i++) {
      const w = Math.random()*2-1;
      b0=0.99886*b0+w*0.0555179; b1=0.99332*b1+w*0.0750759;
      b2=0.96900*b2+w*0.1538520; b3=0.86650*b3+w*0.3104856;
      b4=0.55000*b4+w*0.5329522; b5=-0.7616*b5-w*0.0168980;
      data[i]=(b0+b1+b2+b3+b4+b5+b6+w*0.5362)*0.07;
      b6=w*0.115926;
    }
    const src = audioCtx.createBufferSource();
    src.buffer = buf;
    src.connect(analyser);
    _mireSource = src;
    src.start();
    src.onended = () => resolve();
  });
}

// ── DSP Canvas drawing ──
// _dspRafId: runs continuously once initDsp() completes (not just on DSP tab)
function _dspBarColor(v, alpha) {
  const r = v/255;
  let cr, cg, cb;
  if (r < 0.45) {
    cr = Math.round(r/0.45*50);
    cg = Math.round(180 + r/0.45*50);
    cb = Math.round(255 - r/0.45*180);
  } else if (r < 0.75) {
    const t = (r-0.45)/0.3;
    cr = Math.round(50 + t*200); cg = Math.round(230-t*80); cb = Math.round(75-t*40);
  } else {
    const t = (r-0.75)/0.25;
    cr = 250; cg = Math.round(150-t*100); cb = Math.round(35);
  }
  return `rgba(${cr},${cg},${cb},${alpha})`;
}
function _specComputeVals(barCount, N, nyq) {
  if (!_specPeaks || _specPeaks.length !== barCount) _specPeaks = new Float32Array(barCount);
  const vals = new Float32Array(barCount);
  let peakVal = 0;
  for (let i = 0; i < barCount; i++) {
    const f0 = Math.pow(20000/20, i/barCount) * 20;
    const f1 = Math.pow(20000/20, (i+1)/barCount) * 20;
    const bin0 = Math.floor(f0/nyq*N), bin1 = Math.ceil(f1/nyq*N);
    let sum = 0, cnt = 0;
    for (let b = bin0; b < bin1 && b < N; b++) { sum += _dspDataArray[b]; cnt++; }
    vals[i] = cnt > 0 ? sum/cnt : 0;
    if (vals[i] > peakVal) peakVal = vals[i];
    if (vals[i] > _specPeaks[i]) _specPeaks[i] = vals[i];
    else _specPeaks[i] = Math.max(0, _specPeaks[i] - 0.8);
  }
  return {vals, peakVal};
}
function _specDrawGrid(ctx, W, H) {
  const dBLines = [0, -6, -12, -18, -24, -36, -48];
  ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'right';
  dBLines.forEach(db => {
    const y = H * (1 - (db+60)/60);
    ctx.strokeStyle = db === 0 ? '#00cfff22' : '#00cfff0c';
    ctx.lineWidth = db === 0 ? 1.2 : 0.8;
    ctx.setLineDash(db === 0 ? [] : [4,4]);
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke();
    ctx.setLineDash([]); ctx.fillStyle = '#00cfff44'; ctx.fillText(db+'dB', W-4, y-2);
  });
  const fLabels = [[20,'20Hz'],[100,'100'],[500,'500'],[1000,'1k'],[2000,'2k'],[5000,'5k'],[10000,'10k'],[20000,'20k']];
  ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'center'; ctx.fillStyle = '#00cfff33';
  fLabels.forEach(([f,lbl]) => {
    ctx.fillText(lbl, W * Math.log10(f/20) / Math.log10(20000/20), H-3);
  });
}
function _specDrawBars(ctx, vals, W, H, bw) {
  for (let i = 0; i < vals.length; i++) {
    const v = vals[i], x = i*bw, bH = (v/255)*(H-12);
    const grd = ctx.createLinearGradient(0, H-bH, 0, H);
    grd.addColorStop(0, _dspBarColor(v, 0.95)); grd.addColorStop(1, _dspBarColor(v, 0.15));
    ctx.fillStyle = grd; ctx.fillRect(x+0.5, H-bH-12, bw-1, bH);
    const py = H - (_specPeaks[i]/255)*(H-12) - 14;
    ctx.fillStyle = _dspBarColor(_specPeaks[i], 0.9); ctx.fillRect(x+0.5, py, bw-1, 2);
  }
}
function _specDrawLineFill(ctx, vals, W, H, bw, mode) {
  const barCount = vals.length;
  const pts = Array.from({length:barCount}, (_,i) => ({x:(i+0.5)*bw, y:H-(vals[i]/255)*(H-12)-12}));
  ctx.beginPath(); ctx.moveTo(pts[0].x, H-12); ctx.lineTo(pts[0].x, pts[0].y);
  for (let i = 1; i < barCount; i++) {
    const mx = (pts[i-1].x + pts[i].x)/2;
    ctx.bezierCurveTo(mx, pts[i-1].y, mx, pts[i].y, pts[i].x, pts[i].y);
  }
  if (mode === 'fill') {
    ctx.lineTo(pts[barCount-1].x, H-12); ctx.closePath();
    const grd = ctx.createLinearGradient(0, 0, 0, H);
    grd.addColorStop(0, '#00cfff33'); grd.addColorStop(0.5, '#00ff8822'); grd.addColorStop(1, '#00cfff05');
    ctx.fillStyle = grd; ctx.fill();
  }
  ctx.strokeStyle = '#00cfff99'; ctx.lineWidth = 1.5; ctx.stroke();
  ctx.beginPath(); ctx.strokeStyle = '#00cfff44'; ctx.lineWidth = 1;
  for (let i = 0; i < barCount; i++) {
    const px = (i+0.5)*bw, py = H-(_specPeaks[i]/255)*(H-12)-12;
    i === 0 ? ctx.moveTo(px,py) : ctx.lineTo(px,py);
  }
  ctx.stroke();
}
function _dspDrawMirror(ctx, vals, W, H, bw) {
  const cy = H/2;
  for (let i = 0; i < vals.length; i++) {
    const v = vals[i], x = i*bw, bH = (v/255)*(cy-8);
    const grd = ctx.createLinearGradient(0, cy-bH, 0, cy+bH);
    grd.addColorStop(0, _dspBarColor(v, 0.15)); grd.addColorStop(0.5, _dspBarColor(v, 0.9)); grd.addColorStop(1, _dspBarColor(v, 0.15));
    ctx.fillStyle = grd; ctx.fillRect(x+0.5, cy-bH, bw-1, bH*2);
    const ph = (_specPeaks[i]/255)*(cy-8);
    ctx.fillStyle = _dspBarColor(_specPeaks[i], 0.8);
    ctx.fillRect(x+0.5, cy-ph-2, bw-1, 2); ctx.fillRect(x+0.5, cy+ph, bw-1, 2);
  }
  ctx.strokeStyle = '#00cfff18'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(0,cy); ctx.lineTo(W,cy); ctx.stroke();
}
function _specDrawWaterfall(ctx, vals, W, H, barCount) {
  if (!_wfCanvas || _wfCanvas.width !== W || _wfCanvas.height !== H) {
    const nwf = document.createElement('canvas'); nwf.width = W; nwf.height = H;
    const nctx = nwf.getContext('2d');
    nctx.fillStyle = '#000508'; nctx.fillRect(0, 0, W, H);
    if (_wfCanvas && _wfCanvas.width > 0) nctx.drawImage(_wfCanvas, 0, 0, W, H);
    _wfCanvas = nwf; _wfCtx2 = nctx;
  }
  const imgD = _wfCtx2.getImageData(2, 0, W-2, H); _wfCtx2.putImageData(imgD, 0, 0);
  const binH = H / barCount;
  for (let i = 0; i < barCount; i++) {
    _wfCtx2.fillStyle = _wfColor(vals[i]/255);
    _wfCtx2.fillRect(W-2, Math.floor((barCount-1-i)*binH), 2, Math.ceil(binH)+1);
  }
  ctx.drawImage(_wfCanvas, 0, 0, W, H);
  ctx.font = '7px Share Tech Mono'; ctx.textAlign = 'right';
  [[0,'20k'],[0.25,'5k'],[0.5,'1k'],[0.75,'100'],[0.98,'20Hz']].forEach(([pct,lbl]) => {
    ctx.fillStyle = 'rgba(0,207,255,0.5)'; ctx.fillText(lbl, W-4, pct*H+8);
  });
  for (let i = 0; i < H; i++) { ctx.fillStyle = _wfColor(1-i/H); ctx.fillRect(0, i, 4, 1); }
}
function _specDrawWave(ctx, W, H) {
  const waveArr = new Uint8Array(_dspAnalyser.fftSize);
  _dspAnalyser.getByteTimeDomainData(waveArr);
  const cy = H/2;
  ctx.strokeStyle = '#00cfff0a'; ctx.lineWidth = 0.5;
  for (let d = 1; d < 4; d++) {
    ctx.beginPath(); ctx.moveTo(0, cy-cy*d/4); ctx.lineTo(W, cy-cy*d/4); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, cy+cy*d/4); ctx.lineTo(W, cy+cy*d/4); ctx.stroke();
  }
  ctx.strokeStyle = '#00cfff18'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(W, cy); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, cy);
  for (let x = 0; x < W; x++) {
    const y = (waveArr[Math.min(waveArr.length-1, Math.floor(x*waveArr.length/W))]/128-1)*(cy-10)+cy;
    ctx.lineTo(x, y);
  }
  ctx.lineTo(W, cy); ctx.closePath();
  const wGrd = ctx.createLinearGradient(0, 0, 0, H);
  wGrd.addColorStop(0, 'rgba(0,207,255,0.28)'); wGrd.addColorStop(0.5, 'rgba(0,207,255,0.08)'); wGrd.addColorStop(1, 'rgba(0,207,255,0.28)');
  ctx.fillStyle = wGrd; ctx.fill();
  ctx.beginPath();
  for (let x = 0; x < W; x++) {
    const y = (waveArr[Math.min(waveArr.length-1, Math.floor(x*waveArr.length/W))]/128-1)*(cy-10)+cy;
    x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.strokeStyle = '#00cfff'; ctx.lineWidth = 1.5; ctx.shadowColor = '#00cfff'; ctx.shadowBlur = 6;
  ctx.stroke(); ctx.shadowBlur = 0;
  ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'right'; ctx.fillStyle = '#00cfff44';
  ctx.fillText('+1.0', W-4, 14); ctx.fillText(' 0.0', W-4, cy+4); ctx.fillText('-1.0', W-4, H-4);
}
function _specDrawDots(ctx, vals, W, H, bw, barCount) {
  ctx.fillStyle = 'rgba(0,5,8,0.35)'; ctx.fillRect(0, 0, W, H);
  const dotBw = W / barCount;
  for (let i = 0; i < barCount; i++) {
    const v = vals[i]/255;
    if (v < 0.015) continue;
    const x = (i+0.5)*dotBw, y = H-v*(H-16)-14, r = Math.max(1.5, v*5);
    ctx.strokeStyle = _dspBarColor(vals[i], v*0.5); ctx.lineWidth = dotBw*0.35;
    ctx.beginPath(); ctx.moveTo(x, H-12); ctx.lineTo(x, y+r); ctx.stroke();
    ctx.shadowColor = _dspBarColor(vals[i], 1); ctx.shadowBlur = r*3;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI*2);
    ctx.fillStyle = _dspBarColor(vals[i], 0.9); ctx.fill(); ctx.shadowBlur = 0;
  }
  ctx.beginPath(); ctx.strokeStyle = '#00cfff33'; ctx.lineWidth = 0.8;
  for (let i = 0; i < barCount; i++) {
    const px = (i+0.5)*dotBw, py = H-(_specPeaks[i]/255)*(H-16)-14;
    i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
  }
  ctx.stroke();
}
function _specDrawRadial(ctx, vals, W, H, barCount) {
  const cx = W/2, cy = H/2, maxR = Math.min(cx,cy)-8, minR = maxR*0.22;
  const linePW = (2*Math.PI*maxR)/barCount*0.72;
  ctx.beginPath(); ctx.arc(cx, cy, maxR, 0, Math.PI*2);
  const radBg = ctx.createRadialGradient(cx, cy, minR, cx, cy, maxR);
  radBg.addColorStop(0, '#010c14'); radBg.addColorStop(1, '#000408');
  ctx.fillStyle = radBg; ctx.fill();
  [0.33, 0.66, 1].forEach(p => {
    ctx.beginPath(); ctx.arc(cx, cy, minR+p*(maxR-minR), 0, Math.PI*2);
    ctx.strokeStyle = 'rgba(0,180,220,0.07)'; ctx.lineWidth = 0.7; ctx.stroke();
  });
  for (let i = 0; i < barCount; i++) {
    const angle = (i/barCount)*Math.PI*2 - Math.PI/2;
    const r1 = minR + (vals[i]/255)*(maxR-minR);
    ctx.beginPath();
    ctx.moveTo(cx+minR*Math.cos(angle), cy+minR*Math.sin(angle));
    ctx.lineTo(cx+r1*Math.cos(angle), cy+r1*Math.sin(angle));
    ctx.strokeStyle = _dspBarColor(vals[i], 0.85); ctx.lineWidth = Math.max(1.5, linePW); ctx.stroke();
  }
  ctx.beginPath();
  for (let i = 0; i <= barCount; i++) {
    const angle = (i%barCount/barCount)*Math.PI*2 - Math.PI/2;
    const r = minR + (_specPeaks[i%barCount]/255)*(maxR-minR);
    i === 0 ? ctx.moveTo(cx+r*Math.cos(angle), cy+r*Math.sin(angle)) : ctx.lineTo(cx+r*Math.cos(angle), cy+r*Math.sin(angle));
  }
  ctx.strokeStyle = 'rgba(0,207,255,0.45)'; ctx.lineWidth = 1; ctx.shadowColor = '#00cfff'; ctx.shadowBlur = 4;
  ctx.stroke(); ctx.shadowBlur = 0;
  ctx.beginPath(); ctx.arc(cx, cy, minR, 0, Math.PI*2);
  ctx.strokeStyle = 'rgba(0,207,255,0.2)'; ctx.lineWidth = 1; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI*2); ctx.fillStyle = '#00cfff55'; ctx.fill();
  ctx.font = '7px Share Tech Mono'; ctx.textAlign = 'center'; ctx.fillStyle = 'rgba(0,200,240,0.4)';
  ctx.fillText('0dB', cx, cy-maxR-3); ctx.fillText('-∞', cx, cy-minR+4);
}
function _specUpdateMeters(peakVal) {
  const db = peakVal > 0 ? (20*Math.log10(peakVal/255)).toFixed(1) : '-∞';
  const dbEl = document.getElementById('dsp-db-val');
  if (dbEl) dbEl.textContent = db + ' dB';
  const vuBar = document.getElementById('dsp-vu-bar');
  if (vuBar) vuBar.style.width = ((peakVal/255)*100).toFixed(1) + '%';
  const vuPct = (peakVal/255*100).toFixed(1) + '%';
  const vuL = document.getElementById('vu-left');
  const vuR = document.getElementById('vu-right');
  const vuDb = document.getElementById('vu-db');
  if (vuL) vuL.style.width = vuPct;
  if (vuR) vuR.style.width = vuPct;
  if (vuDb) vuDb.textContent = db + (peakVal > 0 ? 'dB' : '');
}
function startDspDraw() {
  if (_dspRafId) return;
  let _eqPulsePhase = 0;
  function draw() {
    _dspRafId = requestAnimationFrame(draw);
    _eqPulsePhase += 0.08;
    if (_eqGhostAlpha > 0) _eqGhostAlpha = Math.max(0, _eqGhostAlpha - 0.006);
    const eqCanvas = document.getElementById('eq-curve-canvas');
    if (eqCanvas && eqCanvas.offsetWidth > 0 && _eqPanelOn) drawEqCurve();
    const datEqCanvas = document.getElementById('dat-eq-curve-canvas');
    if (datEqCanvas && datEqCanvas.offsetWidth > 0) drawDatEqCurve();
    if (!_dspAnalyser) return;
    _dspAnalyser.getByteFrequencyData(_dspDataArray);
    const canvas = document.getElementById('dsp-canvas');
    if (!canvas || canvas.offsetWidth === 0) return;
    let W, H;
    if (_specMode === 'dots') {
      W = canvas.width  || canvas.offsetWidth;
      H = canvas.height || canvas.offsetHeight;
      if (canvas.width !== canvas.offsetWidth || canvas.height !== canvas.offsetHeight) {
        canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight;
        W = canvas.width; H = canvas.height;
      }
    } else {
      W = canvas.width = canvas.offsetWidth;
      H = canvas.height = canvas.offsetHeight;
    }
    const ctx = canvas.getContext('2d');
    if (_specMode !== 'dots' && _specMode !== 'waterfall') ctx.clearRect(0, 0, W, H);
    const barCount = 96;
    const {vals, peakVal} = _specComputeVals(barCount, _dspDataArray.length, audioCtx.sampleRate/2);
    const bw = W / barCount;
    if (['bars','line','fill','mirror'].includes(_specMode)) _specDrawGrid(ctx, W, H);
    if      (_specMode === 'bars')                         _specDrawBars(ctx, vals, W, H, bw);
    else if (_specMode === 'line' || _specMode === 'fill') _specDrawLineFill(ctx, vals, W, H, bw, _specMode);
    else if (_specMode === 'mirror')                       _dspDrawMirror(ctx, vals, W, H, bw);
    else if (_specMode === 'waterfall')                    _specDrawWaterfall(ctx, vals, W, H, barCount);
    else if (_specMode === 'wave')                         _specDrawWave(ctx, W, H);
    else if (_specMode === 'dots')                         _specDrawDots(ctx, vals, W, H, bw, barCount);
    else if (_specMode === 'radial')                       _specDrawRadial(ctx, vals, W, H, barCount);
    _specUpdateMeters(peakVal);
  }
  draw();
}



// Global mouseup: release EQ drag if cursor leaves canvas
document.addEventListener('mouseup', () => { if (_eqDrag) { _eqDrag = null; const c=document.getElementById('eq-curve-canvas'); if(c)c.style.cursor='crosshair'; } });

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

// ═══════════════════════════════════════════════════════════
// TÂCHES TAB
// ═══════════════════════════════════════════════════════════
let _taches = [];

function initTaches() {
  tachesLoad();
  setInterval(tachesCheckScheduled, _TASKS_POLL_MS);
}

async function tachesLoad() {
  try {
    const r = await fetch('/api/tasks');
    const d = await r.json();
    _taches = Array.isArray(d) ? d : (d.tasks || []);
    tachesRender();
  } catch(e) { /* network error — retry next interval */ }
}

function tachesRender() {
  const list = document.getElementById('task-list');
  if (!list) return;
  if (!_taches.length) { list.innerHTML='<div class="taches-empty">Aucune tâche</div>'; return; }
  list.innerHTML = _taches.map(t => `
    <div class="task-card ${t.enabled===false?'task-disabled':''}" id="task-${t.id}">
      <div class="task-card-header">
        <span class="task-name">${escHtml(t.name)}</span>
        <div class="task-card-actions">
          <button class="task-btn task-btn-run" onclick="tacheRun('${t.id}')" title="Exécuter">▶</button>
          <button class="task-btn task-btn-toggle" onclick="tacheToggle('${t.id}')">${t.enabled===false?'●':'◉'}</button>
          <button class="task-btn task-btn-del" onclick="tacheDelete('${t.id}')" title="Supprimer">✕</button>
        </div>
      </div>
      <div class="task-cmd">${escHtml(t.cmd)}</div>
      ${t.schedule?'<div class="task-schedule">⏱ '+escHtml(t.schedule)+'</div>':''}
      <div class="task-output d-none" id="task-out-${t.id}"></div>
    </div>
  `).join('');
}

async function tacheCreate() {
  const name = (document.getElementById('task-new-name')||{}).value || '';
  const cmd  = (document.getElementById('task-new-cmd')||{}).value || '';
  const sched= (document.getElementById('task-new-sched')||{}).value || '';
  if (!name || !cmd) { alert('Nom et commande requis'); return; }
  try {
    await fetch('/api/tasks', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name,cmd,schedule:sched})});
    document.getElementById('task-new-name').value='';
    document.getElementById('task-new-cmd').value='';
    document.getElementById('task-new-sched').value='';
    tachesLoad();
  } catch(e) { alert('Erreur: '+e.message); }
}

async function tacheRun(id) {
  const outEl = document.getElementById('task-out-'+id);
  if (outEl) { _disp(outEl, true, 'block'); outEl.innerHTML='<span class="task-running">Exécution…</span>'; }
  try {
    const r = await fetch('/api/tasks/'+id+'/run', {method:'POST'});
    const d = await r.json();
    const out = [d.output, d.error].filter(Boolean).join('\n');
    if (outEl) outEl.innerHTML = '<pre>'+escHtml(out||'OK')+'</pre>';
  } catch(e) { if(outEl) outEl.innerHTML='<span class="task-error">Erreur</span>'; }
}

async function tacheDelete(id) {
  if (!confirm('Supprimer cette tâche?')) return;
  await fetch('/api/tasks/'+id, {method:'DELETE'});
  tachesLoad();
}

async function tacheToggle(id) {
  const t = _taches.find(x=>x.id===id);
  if (!t) return;
  await fetch('/api/tasks', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id, name:t.name, cmd:t.cmd, schedule:t.schedule, enabled:t.enabled===false})});
  tachesLoad();
}


async function tacheInsertSuggestion() {
  const el = document.getElementById('task-ia-suggestion');
  if (el) el.textContent = '…';
  try {
    const r = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(await _buildChatPayload([{role:'user', content:'Suggère 3 tâches utiles à automatiser pour un système JARVIS (monitoring, backup, nettoyage). Format JSON: [{name,cmd,schedule}]. Réponds uniquement avec le JSON.'}]))
    });
    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let text = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const line of dec.decode(value).split('\n')) {
        if (!line.startsWith('data:')) continue;
        try { const ev = JSON.parse(line.slice(5).trim()); if (ev.type==='token') text += ev.token; } catch {}
      }
    }
    const match = text.match(/\[[\s\S]*\]/);
    if (match) {
      const suggestions = JSON.parse(match[0]);
      if (el) el.innerHTML = suggestions.map(s =>
        `<div class="task-suggestion" onclick='tacheInsertForm(${JSON.stringify(s)})'>${escHtml(s.name)}: <code>${escHtml(s.cmd)}</code></div>`
      ).join('');
    } else if (el) el.textContent = text.slice(0,200);
  } catch(e) { if(el) el.textContent = 'Erreur IA'; }
}

function tacheInsertForm(s) {
  const n = document.getElementById('task-new-name'); if(n) n.value=s.name||'';
  const c = document.getElementById('task-new-cmd');  if(c) c.value=s.cmd||'';
  const sc= document.getElementById('task-new-sched');if(sc)sc.value=s.schedule||'';
}

function tachesCheckScheduled() {
  const now = new Date();
  const min = now.getMinutes(), hr = now.getHours();
  _taches.forEach(t => {
    if (t.enabled===false || !t.schedule) return;
    const m = t.schedule.match(/^\*\/(\d+)$/);
    if (m && min % parseInt(m[1]) === 0) tacheRun(t.id);
  });
}


// ═══════════════════════════════════════════════════════════
// WELCOME — PRÉSENTATION JARVIS
// ═══════════════════════════════════════════════════════════
let _welcomeData = null;
let _welcomeEditOpen = false;

async function loadWelcome() {
  try {
    const r = await fetch('/api/welcome');
    _welcomeData = await r.json();
    _renderWelcome();
  } catch(e) { /* network error — welcome stays empty */ }
}

function _renderWelcome() {
  if (!_welcomeData) return;
  const body = document.getElementById('welcome-body');
  if (body) {
    body.innerHTML = (_welcomeData.lines || []).map(line => {
      if (!line) return '<div class="w-line-empty"></div>';
      if (line.startsWith('▸')) return '<div class="w-line-bullet">'+escHtml(line)+'</div>';
      if (line.startsWith('—')) return '<div class="w-line-sign">'+escHtml(line)+'</div>';
      return '<div>'+escHtml(line)+'</div>';
    }).join('');
  }
  const dateEl = document.getElementById('welcome-meta-date');
  if (dateEl) dateEl.textContent = 'Mise à jour : ' + (_welcomeData.last_updated || '—');
  const byEl = document.getElementById('welcome-meta-by');
  if (byEl) byEl.textContent = 'par : ' + (_welcomeData.updated_by || 'système');
  const verEl = document.getElementById('welcome-version');
  if (verEl) verEl.textContent = 'VERSION ' + (_welcomeData.version||1) + ' — DÉVELOPPEMENT ACTIF';
}

function _showModal(el) {
  _disp(el, true, 'flex');
}

// ── Boot sequence animation ──────────────────────────────────────────
async function _wmBootSequence() {
  const defs = [
    { fill:'wm-bf-0', pct:'wm-bp-0', stat:'wm-bs-0', label:'ONLINE', dur:640 },
    { fill:'wm-bf-1', pct:'wm-bp-1', stat:'wm-bs-1', label:'READY',  dur:520 },
    { fill:'wm-bf-2', pct:'wm-bp-2', stat:'wm-bs-2', label:'ACTIVE', dur:580 },
    { fill:'wm-bf-3', pct:'wm-bp-3', stat:'wm-bs-3', label:'SYNCED', dur:460 },
  ];
  // Tick timer display
  const tsEl = document.getElementById('wm-boot-ts');
  const t0 = performance.now();
  const tickId = setInterval(() => {
    if (!tsEl) return;
    const ms = Math.round(performance.now() - t0);
    const h = String(Math.floor(ms/3600000)).padStart(2,'0');
    const m = String(Math.floor(ms/60000)%60).padStart(2,'0');
    const s = String(Math.floor(ms/1000)%60).padStart(2,'0');
    const cs = String(ms%1000).padStart(3,'0');
    tsEl.textContent = h+':'+m+':'+s+'.'+cs;
  }, 33);
  for (const d of defs) {
    const fill = document.getElementById(d.fill);
    const pctEl = document.getElementById(d.pct);
    const statEl = document.getElementById(d.stat);
    if (statEl) { statEl.textContent = 'LOAD'; statEl.className = 'wm-boot-status wait'; }
    await new Promise(resolve => {
      const start = performance.now();
      function step(now) {
        const t = Math.min((now - start) / d.dur, 1);
        const pct = Math.round(t * 100);
        if (fill) fill.style.width = pct + '%';
        if (pctEl) pctEl.textContent = pct + '%';
        if (t < 1) { requestAnimationFrame(step); }
        else {
          if (statEl) { statEl.textContent = d.label; statEl.className = 'wm-boot-status ok'; }
          resolve();
        }
      }
      requestAnimationFrame(step);
    });
    await new Promise(r => setTimeout(r, _EQ_REDRAW_MS));
  }
  clearInterval(tickId);
}

function _wmBootInstant() {
  const defs = [
    { fill:'wm-bf-0', pct:'wm-bp-0', stat:'wm-bs-0', label:'ONLINE' },
    { fill:'wm-bf-1', pct:'wm-bp-1', stat:'wm-bs-1', label:'READY'  },
    { fill:'wm-bf-2', pct:'wm-bp-2', stat:'wm-bs-2', label:'ACTIVE' },
    { fill:'wm-bf-3', pct:'wm-bp-3', stat:'wm-bs-3', label:'SYNCED' },
  ];
  defs.forEach(d => {
    const fill = document.getElementById(d.fill);
    const pctEl = document.getElementById(d.pct);
    const statEl = document.getElementById(d.stat);
    if (fill) fill.style.width = '100%';
    if (pctEl) pctEl.textContent = '100%';
    if (statEl) { statEl.textContent = d.label; statEl.className = 'wm-boot-status ok'; }
  });
  const tsEl = document.getElementById('wm-boot-ts');
  if (tsEl) tsEl.textContent = '00:00:02.187';
}

// ── Preloader : typewriter + barre de progression ──────────────────
async function _wmTypewriter(lines) {
  const body = document.getElementById('welcome-body');
  const statusR = document.getElementById('wm-status-r');
  const progress = document.getElementById('wm-progress');
  const footer = document.getElementById('welcome-footer');
  if (!body) return;

  body.innerHTML = '';
  if (statusR) statusR.textContent = 'CHARGEMENT...';

  const total = lines.length;
  for (let i = 0; i < total; i++) {
    const line = lines[i];
    await new Promise(r => setTimeout(r, i === 0 ? 0 : 90));
    let cls = '', txt = escHtml(line);
    if (!line) { body.insertAdjacentHTML('beforeend','<div class="w-line-empty"></div>'); continue; }
    if (line.startsWith('▸')) cls = 'w-line-bullet';
    else if (line.startsWith('—')) cls = 'w-line-sign';
    body.insertAdjacentHTML('beforeend', `<div class="${cls}">${txt}</div>`);
    // Barre progression
    if (progress) progress.style.width = Math.round((i+1)/total*85)+'%';
    if (statusR) statusR.textContent = 'LIGNE '+(i+1)+' / '+total;
  }

  // Dernière phase : compléter la barre
  if (progress) progress.style.width = '100%';
  if (statusR) statusR.textContent = '● SYSTÈME PRÊT';

  await new Promise(r => setTimeout(r, _DSP_PUSH_MS));
  if (footer) footer.classList.add('wm-visible');
}

function openWelcome() {
  const el = document.getElementById('welcome-modal');
  if (!el) return;
  _showModal(el);
  // Réouverture manuelle — boot bars instantanées
  _wmBootInstant();
  const footer = document.getElementById('welcome-footer');
  const progress = document.getElementById('wm-progress');
  if (footer) { footer.classList.add('wm-visible'); }
  if (progress) progress.style.width = '100%';
  const statusR = document.getElementById('wm-status-r');
  if (statusR) statusR.textContent = '● SYSTÈME PRÊT';
  if (!_welcomeData) {
    loadWelcome();
  } else {
    _renderWelcome();
  }
}

async function _startPreloader() {
  const el = document.getElementById('welcome-modal');
  if (!el) return;
  _showModal(el);
  const footer = document.getElementById('welcome-footer');
  if (footer) footer.classList.remove('wm-visible');
  const progress = document.getElementById('wm-progress');
  if (progress) progress.style.width = '0%';
  await _wmBootSequence();
  await loadWelcome();
  if (_welcomeData) {
    const verEl = document.getElementById('welcome-version');
    if (verEl) verEl.textContent = 'VERSION '+(_welcomeData.version||1)+' — DÉVELOPPEMENT ACTIF';
    const dateEl = document.getElementById('welcome-meta-date');
    if (dateEl) dateEl.textContent = 'Mise à jour : '+(_welcomeData.last_updated||'—');
    const byEl = document.getElementById('welcome-meta-by');
    if (byEl) byEl.textContent = 'par : '+(_welcomeData.updated_by||'système');
    await _wmTypewriter(_welcomeData.lines || []);
  }
  // Toujours afficher le footer — évite l'écran noir si loadWelcome() échoue
  if (footer) footer.classList.add('wm-visible');
  if (progress) progress.style.width = '100%';
  const statusR = document.getElementById('wm-status-r');
  if (statusR && statusR.textContent !== '● SYSTÈME PRÊT') statusR.textContent = '● SYSTÈME PRÊT';
}

function closeWelcome() {
  const el = document.getElementById('welcome-modal');
  if (!el) return;
  el.style.opacity = '0';
  el.style.transition = 'opacity .4s ease';
  setTimeout(() => { _disp(el, true); }, 420);
}

function welcomeToggleEdit() {
  _welcomeEditOpen = !_welcomeEditOpen;
  const area = document.getElementById('welcome-edit-area');
  if (area) area.classList.toggle('open', _welcomeEditOpen);
  if (_welcomeEditOpen && _welcomeData) {
    const ta = document.getElementById('welcome-edit-ta');
    if (ta) ta.value = (_welcomeData.lines || []).join('\n');
  }
}

async function welcomeSaveEdit() {
  const ta = document.getElementById('welcome-edit-ta');
  if (!ta || !_welcomeData) return;
  _welcomeData.lines = ta.value.split('\n');
  try {
    await fetch('/api/welcome', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({lines: _welcomeData.lines, updated_by: 'Marc'})});
    _renderWelcome();
    welcomeToggleEdit();
  } catch(e) { alert('Erreur sauvegarde'); }
}

async function welcomeReset() {
  if (!confirm('Réinitialiser le message par défaut ?')) return;
  try {
    await fetch('/api/welcome/reset', {method:'POST'});
    await loadWelcome();
  } catch(e) { alert('Erreur reset'); }
}

async function welcomeEvolve() {
  const inp = document.getElementById('welcome-evolve-input');
  const context = inp ? inp.value.trim() : '';
  if (!context) { alert('Décrivez la nouveauté à intégrer.'); return; }
  const btn = document.querySelector('#welcome-edit-area .welcome-btn');
  const origText = btn ? btn.textContent : '';
  if (btn) btn.textContent = '… IA EN COURS';
  try {
    const r = await fetch('/api/welcome/evolve', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({context})});
    const d = await r.json();
    if (d.ok) {
      _welcomeData = d.data;
      const ta = document.getElementById('welcome-edit-ta');
      if (ta) ta.value = (_welcomeData.lines||[]).join('\n');
      _renderWelcome();
      if (inp) inp.value = '';
    } else alert('Erreur IA: '+(d.error||'inconnu'));
  } catch(e) { alert('Erreur réseau'); }
  if (btn) btn.textContent = origText;
}


// ═══════════════════════════════════════════════════════════
// BOOT SEQUENCE
// ═══════════════════════════════════════════════════════════
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
      document.addEventListener('click', function _unlockAudio() {
        document.removeEventListener('click', _unlockAudio);
        _tryPlayPendingSpeech();
      }, { once: true });
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

