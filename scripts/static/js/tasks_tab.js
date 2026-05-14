// ══════════════════════════════════════════════════════════════
// TÂCHES TAB — Planificateur de tâches JARVIS
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Onglet « Tâches » : liste, ajout, exécution et planification cron-like
// des tâches JARVIS (initTaches appelé par _hudInit).
// Fichier .js classique (scope global). Chargé APRÈS jarvis_main.js.

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
