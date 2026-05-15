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
// → SOC TAB + SOC GRAPHIQUES extraits — static/js/soc_tab.js (chantier dette 2026-05-15)
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

// → GPU MONITOR extrait (anneaux CPU/RAM/GPU/VRAM) — static/js/gpu_monitor.js (chantier dette 2026-05-15)
// → AUDIO VIZ extrait — static/js/audio_viz.js (chantier dette 2026-05-14)
// ══════════════════════════════════════
// → CHAT UI extrait (history, addMessage, _esc, markdown, Monaco, mémoire LT) — static/js/chat_ui.js (chantier dette 2026-05-15)
// → CHAT CORE extrait (sendMessage, SSE, modes, diagnostic, vision, Ollama poll) — static/js/chat_core.js (chantier dette 2026-05-15)
// → SETTINGS UI extrait (settings GPU + switchers modele/voice + LLM header + chat HUD extras) — static/js/settings_ui.js (chantier dette 2026-05-15)

// → DSP AUDIO SYSTEM extrait — static/js/dsp_audio.js (chantier dette 2026-05-14)
// → EQ PARAMÉTRIQUE extrait — static/js/eq_parametric.js (chantier dette 2026-05-14)
// → AI AUDIO RACK + helpers EQ extraits — static/js/audio_rack.js (chantier dette 2026-05-15)
// → TÂCHES TAB + WELCOME extraits — static/js/tasks_tab.js + static/js/welcome.js (chantier dette 2026-05-14)
// → BOOT SEQUENCE + RACK FX + INIT extraits — static/js/boot_init.js (chantier dette 2026-05-14)
