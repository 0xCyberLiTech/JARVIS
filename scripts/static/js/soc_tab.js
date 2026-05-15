// ══════════════════════════════════════════════════════════════
// SOC TAB — onglet ◈ SOC + SOC GRAPHIQUES (canvas natif)
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-15.
//
// Deux sous-systèmes regroupés (étaient bannières séparées) :
//
//  1. ONGLET ◈ SOC (initSocTab, refreshSocTab, checkThreatLevel,
//     _buildChatPayload, socNarrativeAnalysis, clearSocActions,
//     socForceAutoban) — pull monitoring.json, calcul niveau menace,
//     alerte vocale TTS si ÉLEVÉ/CRITIQUE, narrative LLM via JARVIS.
//
//  2. SOC GRAPHIQUES (canvas natif) — _socBuildDayMap, _socBuildHourMap,
//     _socSparkline, _socLineChart, _socShowDetail/MonthDetail/WeekDetail/
//     HourDetail, _socDrawCharts, socMonthNav, _socRenderWeekCards.
//     Affichage des actions SOC sur 30j (sparkline tuile + Canvas modal).
//
// State top-level : _socAutoRefresh, _MON_ENDPOINT, window._jarvisMonData,
// _lastKnownThreatLevel, _SOC_ALERT_LEVELS, _socChartOffset, _socChartActions.
//
// Fichier .js classique (scope global). Chargé AVANT chat_ui.js /
// chat_core.js (chat_core utilise _buildChatPayload défini ici).

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
