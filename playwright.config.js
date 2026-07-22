import { defineConfig, devices } from '@playwright/test';
import silence from './e2e-silence/silence-proxy.cjs';

// ⛔ VERROU DE SILENCE — POURQUOI IL EST ICI ET PAS DANS LES SPECS (2026-07-22).
// `baseURL` ci-dessous pointe sur l'instance de PRODUCTION : les specs pilotent le VRAI JARVIS
// de Marc, avec son VRAI haut-parleur. Le 2026-07-22, mobile-emergency-render.spec.js a fait
// prononcer 3 fois à voix haute « ARRÊT COMPLET TERMINÉ — VOUS POUVEZ COUPER LE COURANT »
// (tts.log 17:50:06 / 18:04:21 / 18:06:43) alors que les 4 VMs tournaient — l'écran d'urgence
// orage que la FEMME de Marc utilise. Elle interceptait /api/mobile/**, mais pas /api/tts.
// 19 des 25 specs ne citent même pas /api/tts : c'est une CLASSE, pas une instance.
// Playwright REFUSE tout hook global posé ici (mesuré : « did not expect test.beforeEach() to be
// called here ») et aucune fixture ne s'applique sans toucher l'import de chaque spec — donc le
// seul point de passage commun à toutes les specs, présentes ET FUTURES, est le RÉSEAU du
// navigateur. D'où `proxy` + `webServer` ci-dessous. Contrat et motifs : e2e-silence/silence-channels.json.
const SILENCE = silence.loadContract();                       // illisible => la config explose => 0 spec lancée
const SILENCE_ORIGIN = `http://${SILENCE.proxy_host}:${SILENCE.proxy_port}`;
// Budget de DÉMARRAGE du verrou. Nommé (et non littéral en ligne) pour ne pas fabriquer un second
// `timeout:` en tête de ligne : jarvis-visual-gate DÉRIVE le budget par test de ce fichier
// (regex `^\s*timeout:\s*(\d+)`) — deux valeurs dérivables, et il prendrait la mauvaise.
const SILENCE_BOOT_MS = 15_000;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],

  // Le verrou est un SERVEUR : Playwright le démarre AVANT la première spec, attend qu'il réponde,
  // et ÉCHOUE LE RUN s'il ne répond pas. Pas de verrou => pas de test => pas de voix (fail-closed).
  // L'URL de santé porte l'EMPREINTE DU CONTRAT : un proxy survivant d'un run précédent, chargé
  // d'une liste de canaux différente, ne répond pas — on ne repart jamais sur un verrou périmé.
  webServer: {
    command: 'node e2e-silence/silence-proxy.cjs',
    url: SILENCE_ORIGIN + silence.healthUrlPath(SILENCE),
    reuseExistingServer: true,
    stdout: 'pipe',                                           // a11y §5 : chaque blocage est ÉNONCÉ
    stderr: 'pipe',
    timeout: SILENCE_BOOT_MS,
  },

  use: {
    baseURL: 'http://localhost:5000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
    ignoreHTTPSErrors: true,

    // TOUT le trafic du navigateur traverse le verrou. Origin/Host restent `localhost:5000`
    // (transparent) : security_origin.loopback_origins() continue d'accepter les POST.
    proxy: { server: SILENCE_ORIGIN },
    launchOptions: {
      args: [
        // Chromium court-circuite tout proxy pour le loopback par défaut : sans ce drapeau, le
        // verrou serait CONTOURNÉ pour localhost:5000, c'est-à-dire pour la totalité des specs.
        '--proxy-bypass-list=<-loopback>',
        // Ceinture ET bretelles : coupe le son du navigateur (Web Audio, <audio>). Ne remplace
        // PAS le blocage réseau — une requête NON ÉMISE vaut mieux qu'un son coupé.
        '--mute-audio',
        // ⛔ VOIX DU NAVIGATEUR (2026-07-22, lot P1-bis) — le 2e canal d'émission réelle, celui que
        // Marc a reconnu à l'oreille (« ça disait chat chat »). ZÉRO RÉSEAU : le proxy ci-dessus n'y
        // peut RIEN. MESURÉ : 2 clics de nav sur /m => 2 appels à speechSynthesis.speak
        // (« Chat », « Actions ») via mobile.js:913 -> _say. Et le Chromium de test a bien 3 voix
        // SAPI FR (Hortense/Julie/Paul) EN HEADLESS : la prétendue atténuation par --mute-audio +
        // headless est FAUSSE, mesurée. Ce drapeau SUPPRIME l'API (pas seulement le son) — le
        // produit retombe alors dans sa propre branche muette (`'speechSynthesis' in window`).
        // Le drapeau vient du CONTRAT (source unique), jamais écrit en dur ici.
        ...silence.browserVoiceArgs(SILENCE),
      ],
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
