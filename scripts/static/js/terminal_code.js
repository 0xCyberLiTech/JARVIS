// ══════════════════════════════════════════════════════════════
// TERMINAL CODE — SSH PTY xterm.js vers srv-dev-1
// ══════════════════════════════════════════════════════════════
// Extrait de jarvis_main.js — chantier dette technique 2026-05-14.
//
// Sous-système terminal SSH du mode CODE : connexion WebSocket PTY,
// rendu xterm.js, HUD ressources VM, analyse PTY, pont vers le chat JARVIS.
//
// Fichier .js classique (scope global, PAS un IIFE) — les fonctions
// devTerminal*/devJarvis* doivent rester globales pour les data-action du HTML.
// Chargé APRÈS jarvis_main.js : dépend de _devWs/_devXterm/_devFit/_devHostKey/
// _devSetStatus/_jarvisMode (restent dans jarvis_main.js) + Terminal/FitAddon (libs).

function _devTerminalReset() {
  if (_devWs)    { try { _devWs.close(); }    catch(x) {} _devWs = null; }
  if (_devXterm) { try { _devXterm.dispose(); } catch(x) {} _devXterm = null; }
  _devFit = null;
  _devPtyBuf = ''; _devPtyFull = ''; _devLastErr = ''; _devLastCtx = '';
  _devLastFilePath = ''; _devLastFileContent = '';
  var _deh = document.getElementById('dev-jarvis-err-hint'); if (_deh) _deh.style.display = 'none';
  var _dcs = document.getElementById('dev-ctx-section');     if (_dcs) _dcs.style.display = 'none';
}

function _devXtermCreate() {
  _devXterm = new Terminal({
    cursorBlink: true, cursorStyle: 'block', fontSize: 13, scrollback: 2000,
    fontFamily: '"Share Tech Mono", "Courier New", Courier, monospace',
    theme: { // NDT-XTERM-EXEMPT: palette ANSI 16 couleurs — format xterm.js, non convertible en var()
      background:    '#00020a', foreground:    '#00cfff',
      cursor:        '#00cfff', cursorAccent:  '#00020a', selection: '#00cfff28',
      black:         '#000000', red:           '#ff4444',
      green:         '#00ff88', yellow:        '#ffcc00',
      blue:          '#0088ff', magenta:       '#bb44ff',
      cyan:          '#00cfff', white:         '#c8f0ff',
      brightBlack:   '#00cfff22', brightRed:   '#ff6666',
      brightGreen:   '#44ffaa',  brightYellow: '#ffdd44',
      brightBlue:    '#44aaff',  brightMagenta:'#cc88ff',
      brightCyan:    '#44dfff',  brightWhite:  '#ffffff'
    }
  });
  _devFit = new FitAddon.FitAddon();
  _devXterm.loadAddon(_devFit);
  const container = document.getElementById('dev-xterm-container');
  if (container) {
    container.innerHTML = '';
    _devXterm.open(container);
    setTimeout(function() { if (_devFit) _devFit.fit(); }, 50);
    if (window.ResizeObserver)
      new ResizeObserver(function() { if (_devFit) _devFit.fit(); }).observe(container);
  }
}

function _devWsConnect() {
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
  _devWs = new WebSocket(wsProto + '://' + location.host + '/ws/ssh/' + _devHostKey);
  _devSetStatus('● CONNEXION…', '');
  _devWs.onopen = function() {
    _devSetStatus('● CONNECTÉ', 'dev-connected');
    if (_devXterm) { _devXterm.clear(); _devXterm.reset(); }
    if (_devFit) {
      var d = _devFit.proposeDimensions();
      if (d) _devWs.send(JSON.stringify({type:'resize', cols:d.cols, rows:d.rows}));
    }
    if (_devXterm) _devXterm.focus();
    setTimeout(function() {
      if (_devWs && _devWs.readyState === WebSocket.OPEN)
        _devWs.send("PROMPT_COMMAND='unset PROMPT_COMMAND; printf \"\\033[1A\\033[2K\\r\"' && export PS1='\\[\\e[01;32m\\]\\u@\\h\\[\\e[0m\\]:\\[\\e[01;34m\\]\\w\\[\\e[0m\\]\\$ ' && alias ls='ls --color=auto' grep='grep --color=auto' diff='diff --color=auto'\r");
    }, 700);
  };
  _devWs.onmessage = function(e) {
    if (_devXterm) _devXterm.write(e.data);
    _devPtyBuf  += e.data;
    _devPtyFull += e.data;
    if (_devPtyBuf.length  > 6000)  _devPtyBuf  = _devPtyBuf.slice(-6000);
    if (_devPtyFull.length > 20000) _devPtyFull = _devPtyFull.slice(-20000);
    if (_devPtyTimer) clearTimeout(_devPtyTimer);
    _devPtyTimer = setTimeout(_devPtyAnalyze, 900);
  };
  _devWs.onclose = function() {
    _devSetStatus('● DÉCONNECTÉ', 'dev-error');
    if (_devXterm) _devXterm.write('\r\n\x1b[31mDéconnecté\x1b[0m\r\n');
    _devWs = null;
    _devHudStop();
  };
  _devWs.onerror = function() {
    _devSetStatus('● ERREUR', 'dev-error');
    if (_devXterm) _devXterm.write('\r\n\x1b[31m✗ Erreur WebSocket\x1b[0m\r\n');
  };
  _devXterm.onData(function(data) {
    if (_devWs && _devWs.readyState === WebSocket.OPEN) _devWs.send(data);
  });
  _devXterm.onResize(function(size) {
    if (_devWs && _devWs.readyState === WebSocket.OPEN)
      _devWs.send(JSON.stringify({type:'resize', cols:size.cols, rows:size.rows}));
  });
}

function devTerminalOpen(hostKey, label, user) {
  var newHost  = hostKey || 'dev1';
  var newLabel = label   || 'srv-dev-1';
  var newUser  = user    || 'root';
  var hostChanged = newHost !== _devHostKey;
  _devHostKey = newHost;
  // Mettre à jour le subtitle et le HUD host
  var sub = document.getElementById('dev-term-subtitle');
  if (sub) sub.textContent = 'SSH // ' + newUser + '@' + newLabel + ' // PTY XTERM-256COLOR';
  var hhl = document.getElementById('dev-hud-host-label');
  if (hhl) hhl.textContent = '● ' + newLabel;
  var hud = document.getElementById('dev-vm-hud');
  if (hud) hud.style.display = _devHostKey === 'dev1' ? '' : 'none';
  const overlay = document.getElementById('dev-terminal-overlay');
  if (overlay) overlay.style.display = 'flex';
  // Si déjà connecté au même hôte — juste focus
  if (!hostChanged && _devXterm && _devWs && _devWs.readyState === WebSocket.OPEN) { _devXterm.focus(); return; }
  // Nouvel hôte ou pas encore connecté — réinitialiser
  if (hostChanged && _devWs) { try { _devWs.close(); } catch(x) {} _devWs = null; }
  _devTerminalReset();
  _devXtermCreate();
  _devWsConnect();
  if (_devHostKey === 'dev1') _devHudStart(); else _devHudStop();
  (function() {
    var dji = document.getElementById('dev-jarvis-input');
    if (dji && !dji._djKbd) {
      dji._djKbd = true;
      dji.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); devJarvisSend(); }
      });
    }
  })();
}

function devTerminalClose() {
  const overlay = document.getElementById('dev-terminal-overlay');
  if (overlay) overlay.style.display = 'none';
  if (_devWs)    { try { _devWs.close(); }    catch(x) {} _devWs = null; }
  if (_devXterm) { try { _devXterm.dispose(); } catch(x) {} _devXterm = null; }
  _devFit = null;
  _devHudStop();
  _devSetStatus('● CONNEXION…', '');
  setModeSoc();
}

function devTerminalClear() {
  if (_devXterm) _devXterm.clear();
}

function devTerminalSend(data) {
  if (_devWs && _devWs.readyState === WebSocket.OPEN) _devWs.send(data);
}

// ── HUD ressources VM srv-dev-1 ───────────────────────────────────────
var _devHudTimer = null;

function _devHudUpdate() {
  fetch('/api/dev/stats').then(function(r){ return r.json(); }).then(function(d) {
    if (d.error) return;
    var el, bar;
    el = document.getElementById('dhud-load');
    if (el) { var l1 = d.load1 || '—', l5 = d.load5 || '—'; el.textContent = l1 + '·' + l5; }
    el = document.getElementById('dhud-ram');
    if (el) el.textContent = d.ram_used + ' / ' + d.ram_total + ' MB (' + d.ram_pct + '%)';
    bar = document.getElementById('dhud-ram-bar');
    if (bar) { bar.style.width = d.ram_pct + '%'; bar.className = 'dev-hud-bar' + (d.ram_pct > 90 ? ' hud-crit' : d.ram_pct > 75 ? ' hud-warn' : ''); }
    el = document.getElementById('dhud-disk');
    if (el) el.textContent = d.disk_used + ' / ' + d.disk_total + ' GB (' + d.disk_pct + '%)';
    bar = document.getElementById('dhud-disk-bar');
    if (bar) { bar.style.width = d.disk_pct + '%'; bar.className = 'dev-hud-bar' + (d.disk_pct > 90 ? ' hud-crit' : d.disk_pct > 75 ? ' hud-warn' : ''); }
    el = document.getElementById('dhud-net');
    if (el) el.innerHTML = '<span class="dev-hud-rx">↓' + (d.net_rx || '—') + '</span> <span class="dev-hud-tx">↑' + (d.net_tx || '—') + '</span>';
    el = document.getElementById('dhud-uptime');
    if (el) el.textContent = d.uptime || '—';
  }).catch(function(){});
}

function _devHudStart() {
  _devHudUpdate();
  if (_devHudTimer) clearInterval(_devHudTimer);
  _devHudTimer = setInterval(_devHudUpdate, _SOC_REFRESH_MS);
}

function _devHudStop() {
  if (_devHudTimer) { clearInterval(_devHudTimer); _devHudTimer = null; }
}

// ── JARVIS inline chat (barre bas du terminal) ────────────────────────
var _devJarvisCtrl = null;

// Injecte une commande directement dans le PTY
function _devInjectCmd(cmd) {
  if (!_devWs || _devWs.readyState !== WebSocket.OPEN) return;
  _devWs.send(cmd + '\r');
  var h = document.getElementById('dev-jarvis-err-hint');
  if (h) h.style.display = 'none';
}

// Rend la réponse JARVIS avec boutons ▶ sur chaque commande détectée
function _devJarvisRender(text, el) {
  if (!el) return;
  var safe = text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // Code blocks multi-lignes ```...```
  safe = safe.replace(/```([^`]+)```/g, function(m, code) {
    var cmd = code.trim();
    var btnId  = 'dij_'  + Math.random().toString(36).slice(2);
    var cpyId  = 'dcpy_' + Math.random().toString(36).slice(2);
    setTimeout(function() {
      var b = document.getElementById(btnId);
      if (b) b.onclick = function() { _devInjectCmd(cmd.trim().split('\n').join('\r')); };
      var c = document.getElementById(cpyId);
      if (c) c.onclick = function() {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(cmd).then(function() {
            c.textContent = '✓'; setTimeout(function(){ c.textContent = '📋'; }, 1200);
          });
        }
      };
    }, 0);
    return '<code>' + cmd.replace(/\n/g,'<br>') + '</code>'
         + ' <button class="dev-inject-btn" id="' + btnId + '" title="Injecter dans le terminal">▶</button>'
         + ' <button class="dev-copy-btn"   id="' + cpyId + '" title="Copier dans le presse-papiers">📋</button>';
  });
  // Code inline `commande`
  safe = safe.replace(/`([^`\n]{2,80})`/g, function(m, cmd) {
    var btnId = 'dij_' + Math.random().toString(36).slice(2);
    setTimeout(function() {
      var b = document.getElementById(btnId);
      if (b) b.onclick = function() { _devInjectCmd(cmd); };
    }, 0);
    return '<code>' + cmd + '</code>'
         + ' <button class="dev-inject-btn" id="' + btnId + '" title="Injecter dans le terminal">▶</button>';
  });
  el.innerHTML = safe;
}

function devJarvisSend(_opts) {
  var input    = document.getElementById('dev-jarvis-input');
  var respEl   = document.getElementById('dev-jarvis-response');
  var respText = document.getElementById('dev-jarvis-resp-text');
  if (!input || !input.value.trim() || !respEl || !respText) return;
  var msg = input.value.trim();
  input.value = '';
  var hint = document.getElementById('dev-jarvis-err-hint');
  if (hint) hint.style.display = 'none';
  respEl.style.display = 'block';
  respText.innerHTML = '';
  if (_devJarvisCtrl) { try { _devJarvisCtrl.abort(); } catch(x) {} }
  _devJarvisCtrl = new AbortController();
  var buf = '';
  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg, history: [], no_tools: true }),
    signal: _devJarvisCtrl.signal
  }).then(function(r) {
    var reader = r.body.getReader(), dec = new TextDecoder();
    function pump() {
      reader.read().then(function(chunk) {
        if (chunk.done) { _devJarvisRender(buf, respText); return; }
        dec.decode(chunk.value).split('\n').forEach(function(line) {
          if (!line.startsWith('data: ')) return;
          try { var d = JSON.parse(line.slice(6)); if (d.token) buf += d.token; }
          catch(e) { /* skip malformed SSE line */ }
        });
        respText.textContent = buf;
        respEl.scrollTop = respEl.scrollHeight;
        pump();
      }).catch(function() { _devJarvisRender(buf, respText); });
    }
    pump();
  }).catch(function() {
    if (_devJarvisCtrl && !_devJarvisCtrl.signal.aborted) respText.textContent = '[Erreur JARVIS]';
  });
}

function devJarvisCloseResponse() {
  var el = document.getElementById('dev-jarvis-response');
  if (el) el.style.display = 'none';
  if (_devJarvisCtrl) { try { _devJarvisCtrl.abort(); } catch(x) {} _devJarvisCtrl = null; }
}

// Envoie le contenu d'un fichier capturé dans le chat principal pour analyse
function devSendFileToChat(fpath, content) {
  var label = _devLastFilePath || fpath || 'fichier';
  var msg = 'Voici le contenu du fichier `' + label + '` sur ' + (_devHostKey || 'srv') + ' :\n```\n' + (content || _devLastFileContent).slice(0, 12000) + '\n```\n\nAnalyse ce fichier. Indique les problèmes éventuels et propose les modifications avec le code complet prêt à copier-coller.';
  _sendToMainChat(msg);
}

// Envoie la sortie complète du terminal (buffer) dans le chat principal
function devSendToMainChat() {
  var raw = _devPtyFull || _devPtyBuf;
  if (!raw || !raw.trim()) { alert('Terminal vide — exécute une commande d\'abord.'); return; }
  var plain = raw.replace(/\x1b\[[0-9;?]*[A-Za-z]/g, '').replace(/\r/g, '').trim();
  // Chercher si c'est un fichier détecté
  if (_devLastFilePath && _devLastFileContent) {
    devSendFileToChat(_devLastFilePath, _devLastFileContent);
    return;
  }
  var host = _devHostKey || 'srv';
  var inp  = document.getElementById('dev-jarvis-input');
  var q    = inp ? inp.value.trim() : '';
  var msg  = 'Sortie terminal `' + host + '` :\n```\n' + plain.slice(-10000) + '\n```';
  if (q) msg += '\n\n' + q;
  else   msg += '\n\nAnalyse cette sortie et dis-moi quoi faire.';
  _sendToMainChat(msg);
}

// Injecte un message dans le chat principal et l'envoie
function _sendToMainChat(msg) {
  devTerminalClose();
  var inp = document.getElementById('user-input');
  if (!inp) return;
  inp.value = msg;
  sendMessage();
}

// ── Analyse PTY unifiée : erreurs + contexte + audit ─────────────────
var _devPtyBuf  = '', _devPtyTimer = null;
var _devPtyFull = '';          // accumulation complète session — max 20000 chars
var _devLastErr = '', _devLastCtx = '';
var _devLastFilePath = '';     // dernier fichier détecté via cat
var _devLastFileContent = '';  // contenu du dernier fichier capturé
// Note : _fileCorrect* (état pipeline "lis+corrige" du chat) restent dans
// jarvis_main.js — non utilisées par le Terminal CODE.

var _DEV_ERR_RE = /(?:error:|failed|permission denied|no such file|command not found|fatal:|E: |not found|cannot|refused)/i;

var _DEV_CTX_RULES = [
  { re: /systemctl\s+(?:status|start|stop|restart|reload)\s+([a-zA-Z0-9._@-]+)/,
    cmds: function(m) { var s = m[1];
      return [
        { label:'journal', cmd:'journalctl -u '+s+' -n 40 --no-pager\n' },
        { label:'restart', cmd:'systemctl restart '+s+'\n' },
        { label:'enable',  cmd:'systemctl enable '+s+'\n' },
      ];
    }
  },
  { re: /\bnginx\b/i, cmds: function() { return [
      { label:'test',     cmd:'nginx -t\n' },
      { label:'reload',   cmd:'systemctl reload nginx\n' },
      { label:'err log',  cmd:'tail -20 /var/log/nginx/error.log\n' },
      { label:'acc log',  cmd:'tail -20 /var/log/nginx/access.log\n' },
    ];}
  },
  { re: /fail2ban/i, cmds: function() { return [
      { label:'status',   cmd:'fail2ban-client status\n' },
      { label:'sshd',     cmd:'fail2ban-client status sshd\n' },
    ];}
  },
  { re: /cscli|crowdsec/i, cmds: function() { return [
      { label:'decisions', cmd:'cscli decisions list\n' },
      { label:'alerts',    cmd:'cscli alerts list -l 10\n' },
      { label:'metrics',   cmd:'cscli metrics\n' },
    ];}
  },
  { re: /\bapt\b.*(?:install|upgrade|update)/i, cmds: function() { return [
      { label:'autoremove', cmd:'apt autoremove -y\n' },
      { label:'fix broken', cmd:'apt --fix-broken install\n' },
    ];}
  },
  { re: /\bdocker\b/i, cmds: function() { return [
      { label:'ps all',   cmd:'docker ps -a\n' },
      { label:'images',   cmd:'docker images\n' },
      { label:'prune',    cmd:'docker system prune -f\n' },
    ];}
  },
];

function _devPtyAnalyze() {
  var raw = _devPtyBuf;
  _devPtyBuf = '';
  var plain = raw.replace(/\x1b\[[0-9;?]*[A-Za-z]/g,'').replace(/\r/g,'');

  // 1. Erreurs
  if (_DEV_ERR_RE.test(plain)) {
    var lines = plain.split('\n'), errLine = '';
    for (var i = 0; i < lines.length; i++) {
      if (_DEV_ERR_RE.test(lines[i])) { errLine = lines[i].trim().slice(0,110); break; }
    }
    if (errLine && errLine !== _devLastErr) {
      _devLastErr = errLine;
      var hint = document.getElementById('dev-jarvis-err-hint');
      var inp = document.getElementById('dev-jarvis-input');
      if (hint && inp) {
        hint.textContent = '⚠ ' + errLine + '  — cliquer pour analyser';
        hint.style.display = 'block';
        hint.onclick = function() {
          inp.value = 'Erreur terminal : ' + errLine + '\nExplique la cause et donne la correction.';
          hint.style.display = 'none';
          devJarvisSend();
        };
      }
    }
  }

  // 2. Détection cat /fichier → capture contenu + bouton analyser
  var catM = plain.match(/\$\s+cat\s+(\/[^\s\r\n]+)/);
  if (!catM) catM = plain.match(/^cat\s+(\/[^\s\r\n]+)/m);
  if (catM) {
    var fpath = catM[1];
    // Extraire le contenu après la ligne cat
    var afterCmd = plain.slice(plain.indexOf(catM[0]) + catM[0].length).trim();
    // Supprimer le prompt final (root@host:...)
    afterCmd = afterCmd.replace(/\r?\n?[\w@\-]+:[^\n]*[$#]\s*$/, '').trim();
    if (afterCmd.length > 20 && fpath !== _devLastFilePath) {
      _devLastFilePath    = fpath;
      _devLastFileContent = afterCmd;
      _devUpdateCtx([
        { label: '◈ analyser fichier', fn: function() { devSendFileToChat(_devLastFilePath, _devLastFileContent); } },
        { label: '📋 copier contenu',  fn: function() { navigator.clipboard && navigator.clipboard.writeText(_devLastFileContent); } },
      ]);
    }
  }

  // 3. Contexte commande → sidebar dynamique
  if (!catM) {
    for (var r = 0; r < _DEV_CTX_RULES.length; r++) {
      var m = plain.match(_DEV_CTX_RULES[r].re);
      if (m) {
        var ck = m[0].slice(0, 40);
        if (ck !== _devLastCtx) { _devLastCtx = ck; _devUpdateCtx(_DEV_CTX_RULES[r].cmds(m)); }
        break;
      }
    }
  }
}

function _devUpdateCtx(cmds) {
  var sec = document.getElementById('dev-ctx-section');
  var container = document.getElementById('dev-ctx-btns');
  if (!sec || !container) return;
  container.innerHTML = '';
  cmds.forEach(function(c) {
    var btn = document.createElement('button');
    btn.className = 'dev-ctx-btn';
    btn.innerHTML = '<span class="dsb-icon">▸</span>' + c.label;
    btn.title = c.cmd.trim();
    if (c.fn) {
      btn.onclick = c.fn;
    } else {
      btn.onclick = (function(cmd){ return function() { if (_devWs && _devWs.readyState === WebSocket.OPEN) _devWs.send(cmd.replace(/\n/g, '\r')); }; })(c.cmd);
    }
    container.appendChild(btn);
  });
  sec.style.display = 'block';
}
