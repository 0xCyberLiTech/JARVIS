import { test, expect } from '@playwright/test';

/**
 * Smoke tests du flux chat LLM réel — chantier dette technique 2026-05-14.
 *
 * Les 23 autres tests E2E couvrent l'UI uniquement (aucun n'envoie de message
 * au LLM). Ces tests-ci couvrent le CŒUR MÉTIER : le pipeline SSE /api/chat
 * de bout en bout (routing → Ollama → stream tokens → capture historique).
 *
 * On ne vérifie PAS le contenu de la réponse (non déterministe) — seulement
 * que le pipeline fonctionne : tokens émis, stream terminé proprement, échange
 * capturé. Timeout généreux car latence LLM réelle variable (3-30s+).
 */
test.describe('JARVIS · Chat LLM smoke (flux SSE réel)', () => {

  test('POST /api/chat — pipeline SSE émet des tokens et se termine proprement', async ({ request }) => {
    test.setTimeout(75_000); // LLM réel : latence variable, mode général le plus rapide

    // Mode général (gemma4) = réponse la plus rapide. On restaure le mode initial au finally.
    const initial = await (await request.get('/api/mode')).json();
    await request.post('/api/mode', { data: { mode: 'general' } });

    try {
      const res = await request.post('/api/chat', {
        data: { history: [{ role: 'user', content: 'Réponds uniquement par le mot OK.' }] },
        timeout: 70_000,
      });
      expect(res.status()).toBe(200);
      expect(res.headers()['content-type']).toContain('text/event-stream');

      // Le stream SSE est lu en entier (il se ferme quand le LLM a fini)
      const body = await res.text();

      // Parsing robuste : on parse chaque événement SSE en JSON
      // (le format json.dumps Python inclut des espaces — on ne fait pas
      //  de match sur sous-chaîne).
      const events = [...body.matchAll(/data: (.+)/g)]
        .map((m) => {
          try { return JSON.parse(m[1].trim()); } catch { return null; }
        })
        .filter(Boolean);

      // Au moins un événement token
      const tokenEvents = events.filter((ev) => ev.type === 'token');
      expect(tokenEvents.length).toBeGreaterThan(0);

      // Le stream s'est terminé proprement (événement done:true)
      expect(events.some((ev) => ev.done === true)).toBe(true);

      // Reconstitution : concaténation des tokens → contenu non vide
      const full = tokenEvents.map((ev) => ev.token || '').join('').trim();
      expect(full.length).toBeGreaterThan(0);
    } finally {
      await request.post('/api/mode', { data: { mode: initial.mode } });
    }
  });

  test('GET /api/history/last capture l\'échange chat précédent', async ({ request }) => {
    // Le test précédent a envoyé un message → la deque _LAST_EXCHANGES doit le refléter.
    const res = await request.get('/api/history/last?n=1');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.count).toBeGreaterThanOrEqual(1);
    expect(body.exchanges).toHaveLength(body.count);
    // L'échange capturé a la structure attendue (user + assistant + ts)
    const last = body.exchanges[body.exchanges.length - 1];
    expect(last).toHaveProperty('user');
    expect(last).toHaveProperty('assistant');
    expect(last).toHaveProperty('ts');
    expect(last.assistant.length).toBeGreaterThan(0);
  });

});
