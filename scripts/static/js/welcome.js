// ══════════════════════════════════════════════════════════════
// WELCOME — Présentation, animation de boot & preloader
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Couche visuelle d'introduction : écran de présentation JARVIS (loadWelcome
// — chargement/édition/reset/évolution du texte), animation de séquence de
// boot, et preloader (typewriter + barre de progression — _startPreloader).
// Fichier .js classique (scope global). Chargé APRÈS jarvis_main.js.

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
