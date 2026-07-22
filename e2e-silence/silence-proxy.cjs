/* ============================================================================
 * silence-proxy.cjs — LE VERROU DE SILENCE des tests E2E. 0xCyberLiTech 2026-07-22.
 *
 * POURQUOI IL EXISTE (mesuré, pas supposé). playwright.config.js pointe
 * `baseURL` sur l'instance de PRODUCTION de JARVIS. Le 2026-07-22, la spec
 * mobile-emergency-render.spec.js — qui intercepte proprement /api/mobile/** mais
 * PAS /api/tts — a fait prononcer TROIS FOIS à voix haute, dans le salon de Marc :
 *   « ARRÊT COMPLET TERMINÉ — VOUS POUVEZ COUPER LE COURANT »
 * (JARVIS/scripts/tts.log, 17:50:06 / 18:04:21 / 18:06:43, source=mobile), alors que
 * les 4 VMs tournaient. C'est l'écran d'urgence ORAGE que la FEMME de Marc lit.
 *
 * CE N'EST PAS UNE INSTANCE, C'EST UNE CLASSE : 19 des 25 specs (compté live) ne
 * citent même pas /api/tts. Corriger spec par spec laisserait parler la 26e.
 *
 * POURQUOI UN PROXY, ET PAS UNE FIXTURE (le choix, argumenté) :
 *   · un hook global posé dans la config est REFUSÉ par Playwright — mesuré :
 *     « Playwright Test did not expect test.beforeEach() to be called here » ;
 *   · une fixture partagée (`test.extend`) exige de modifier l'import des 25 specs,
 *     et la 26e réimporterait '@playwright/test' : le trou revient ;
 *   · un reverse-proxy en `baseURL` change l'ORIGINE (127.0.0.1:<autre port>) :
 *     security_origin.loopback_origins() est DÉRIVÉE du port 5000 -> tous les POST
 *     seraient refusés, les specs casseraient ;
 *   · `use.proxy` est ORIGIN-TRANSPARENT (Host et Origin restent localhost:5000) et
 *     couvre TOUT le trafic du navigateur, quelle que soit la spec — présente ou future.
 *   Un son coupé (--mute-audio) ne suffirait pas : le serveur travaillerait quand même,
 *   écrirait dans tts.log, et le jour où quelqu'un retire le mute, ça reparle.
 *
 * SOURCE UNIQUE : silence-channels.json (port, canaux, réponses). Zéro littéral ici.
 * FAIL-CLOSED : contrat illisible/invalide -> le proxy REFUSE de démarrer -> Playwright
 * ne lance AUCUNE spec (webServer en échec). Pas de verrou => pas de test => pas de voix.
 * ========================================================================== */
'use strict';

const http = require('http');
const net = require('net');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const CONTRACT_PATH = path.join(__dirname, 'silence-channels.json');

/** Charge le contrat. Toute anomalie = exception = refus de démarrer (fail-closed). */
function loadContract(file) {
  const raw = fs.readFileSync(file || CONTRACT_PATH, 'utf8');
  const c = JSON.parse(raw);
  if (!c.proxy_port || !c.proxy_host || !c.health_path) {
    throw new Error('silence-channels.json : proxy_host/proxy_port/health_path manquant');
  }
  if (!Array.isArray(c.blocked) || c.blocked.length === 0) {
    throw new Error('silence-channels.json : `blocked` vide — un verrou qui ne bloque rien est un mensonge');
  }
  for (const b of c.blocked) {
    if (!b.method || !b.path || !b.response) {
      throw new Error('silence-channels.json : canal incomplet (method/path/response) — ' + JSON.stringify(b));
    }
  }
  const bv = c.browser_voice;
  if (!bv || typeof bv.chromium_flag !== 'string' || !bv.chromium_flag.startsWith('--')) {
    throw new Error('silence-channels.json : browser_voice.chromium_flag manquant — la VOIX DU '
      + 'NAVIGATEUR (speechSynthesis, zero reseau) ne serait neutralisee par rien');
  }
  return c;
}

/** VOIX DU NAVIGATEUR — arguments de lancement qui SUPPRIMENT la capacite de parole du
 *  navigateur de test. Zero reseau => le proxy n'y peut RIEN ; le seul levier global au niveau
 *  de la config Playwright est `launchOptions.args` (aucun script d'init global n'existe en
 *  1.60 : `initScript` absent de TestOptions — verifie dans les types). Le drapeau vient du
 *  CONTRAT (source unique) : il n'est jamais ecrit en dur dans playwright.config.js.
 *  ⛔ PORTEE TESTS UNIQUEMENT : le code produit n'est pas touche — la voix de secours de Marc
 *  (edge-tts mort -> speechSynthesis) reste intacte dans SON navigateur. */
function browserVoiceArgs(c) {
  const bv = (c || {}).browser_voice;
  if (!bv || !bv.chromium_flag) {
    throw new Error('browserVoiceArgs : contrat sans browser_voice.chromium_flag (fail-closed)');
  }
  return [bv.chromium_flag];
}

/** Empreinte du CONTRAT (pas du fichier entier) : elle voyage dans l'URL de santé, si bien
 *  qu'un proxy SURVIVANT d'un run précédent, chargé d'un contrat DIFFÉRENT, ne répond pas —
 *  Playwright le voit et refuse de partir sur un verrou périmé (reuseExistingServer). */
function contractFingerprint(c) {
  const canon = JSON.stringify(c.blocked.map((b) => [b.method, b.path, b.response.status]));
  return crypto.createHash('sha256').update(canon).digest('hex').slice(0, 16);
}

function healthUrlPath(c) {
  return c.health_path + '/' + contractFingerprint(c);
}

function matches(c, method, pathname) {
  return c.blocked.find((b) => b.method.toUpperCase() === String(method).toUpperCase() && b.path === pathname);
}

function createServer(contract, log) {
  const say = log || ((m) => process.stdout.write(m + '\n'));
  const HEALTH = healthUrlPath(contract);
  let blockedCount = 0;

  const server = http.createServer((req, res) => {
    // Sonde de santé : requête en forme ORIGINE (Playwright interroge le proxy directement).
    if (req.url === HEALTH) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, blocked: blockedCount, channels: contract.blocked.length }));
      return;
    }
    // Trafic proxifié : requête en forme ABSOLUE (http://hote:port/chemin).
    let u;
    try { u = new URL(req.url); } catch { res.writeHead(400); res.end(); return; }

    const hit = matches(contract, req.method, u.pathname);
    if (hit) {
      blockedCount += 1;
      say('[SILENCE] BLOQUE ' + req.method + ' ' + u.pathname + ' -> ' + hit.response.status
          + '   (' + String(hit.canal || '').split('.')[0] + ')');
      req.resume();                       // on vide le corps : pas de socket qui pend
      res.writeHead(hit.response.status, { 'Content-Type': hit.response.content_type });
      res.end(hit.response.body);
      return;
    }

    // family: 4 — JARVIS écoute 127.0.0.1 SEUL (jarvis.py) : `localhost` résolu en ::1
    // donnerait ECONNREFUSED sur tout le trafic (piège connu, cf jarvis_localhost_ipv6_watchdog).
    const fwd = http.request({
      host: u.hostname, port: u.port || 80, family: 4,
      path: u.pathname + u.search, method: req.method, headers: req.headers,
    }, (up) => { res.writeHead(up.statusCode, up.headers); up.pipe(res); });
    fwd.on('error', (e) => {
      try { res.writeHead(502, { 'Content-Type': 'text/plain' }); res.end('proxy: ' + e.message); } catch { /* socket déjà fermé */ }
    });
    req.pipe(fwd);
  });

  // CONNECT (https) : tunnel opaque — le CDN Monaco de l'éditeur de code passe par là.
  server.on('connect', (req, socket, head) => {
    const i = req.url.lastIndexOf(':');
    const host = req.url.slice(0, i);
    const port = Number(req.url.slice(i + 1)) || 443;
    const up = net.connect(port, host, () => {
      socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
      up.write(head); up.pipe(socket); socket.pipe(up);
    });
    up.on('error', () => socket.destroy());
    socket.on('error', () => up.destroy());
  });

  // UPGRADE (WebSocket) : sans ce relais, le terminal PTU (ws://…/ws/ssh/…) casserait.
  server.on('upgrade', (req, socket, head) => {
    let u;
    try { u = new URL(req.url); } catch { socket.destroy(); return; }
    const up = net.connect({ port: Number(u.port) || 80, host: u.hostname, family: 4 }, () => {
      const head_ = req.method + ' ' + u.pathname + u.search + ' HTTP/1.1\r\n'
        + Object.entries(req.headers).map(([k, v]) => k + ': ' + v).join('\r\n') + '\r\n\r\n';
      up.write(head_); up.write(head); up.pipe(socket); socket.pipe(up);
    });
    up.on('error', () => socket.destroy());
    socket.on('error', () => up.destroy());
  });

  return server;
}

module.exports = { loadContract, contractFingerprint, healthUrlPath, matches, createServer,
  browserVoiceArgs, CONTRACT_PATH };

if (require.main === module) {
  const contract = loadContract();          // illisible => exception => webServer en échec => 0 spec
  const server = createServer(contract);
  server.listen(contract.proxy_port, contract.proxy_host, () => {
    process.stdout.write('[SILENCE] verrou actif sur ' + contract.proxy_host + ':' + contract.proxy_port
      + ' — ' + contract.blocked.length + ' canal(aux) d\'emission reelle bloque(s)\n');
    process.stdout.write('[SILENCE] sonde : ' + healthUrlPath(contract) + '\n');
  });
}
