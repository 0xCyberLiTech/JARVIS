// api-coverage.spec.js — extension E2E ciblée sur les 4 Blueprints HTTP
// sous-couverts en pytest (voice/routes 36% · settings/routes 44% ·
// dev/routes 27% · web/routes 26%).
//
// Stratégie : routes GET read-only uniquement → zéro effet de bord serveur,
// run rapide, vérifie la réalité bout-en-bout (le pytest mock le test_client,
// Playwright fait l'aller-retour HTTP réel sur JARVIS up).

import { test, expect } from '@playwright/test';

// --- voice/routes ---

test.describe('JARVIS · voice/routes coverage', () => {
  test('GET /api/stt/status — shape complète', async ({ request }) => {
    const r = await request.get('/api/stt/status');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    expect(j).toHaveProperty('available');
    expect(j).toHaveProperty('loaded');
    expect(j).toHaveProperty('model');
  });

  test('GET /api/speak/status — états voix', async ({ request }) => {
    const r = await request.get('/api/speak/status');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    expect(typeof j.speaking).toBe('boolean');
    expect(typeof j.queued).toBe('number');
    expect(typeof j.deferred).toBe('number');
    expect(typeof j.stream_active).toBe('boolean');
  });

  test('GET /api/speak/queue — items[]', async ({ request }) => {
    const r = await request.get('/api/speak/queue');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    expect(Array.isArray(j.items)).toBe(true);
  });

  test('GET /api/tts/status — 4 moteurs', async ({ request }) => {
    const r = await request.get('/api/tts/status');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    for (const engine of ['edge', 'kokoro', 'piper', 'sapi']) {
      expect(j).toHaveProperty(engine);
      expect(j[engine]).toHaveProperty('ok');
      expect(j[engine]).toHaveProperty('label');
    }
  });

  test('GET /api/voices — liste voix Edge non vide', async ({ request }) => {
    const r = await request.get('/api/voices');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    expect(Array.isArray(j.voices)).toBe(true);
    expect(j.voices.length).toBeGreaterThan(0);
    expect(j.voices[0]).toHaveProperty('id');
    expect(j.voices[0]).toHaveProperty('label');
  });

  test('GET /api/tts/local/voices — kokoro/piper/sapi', async ({ request }) => {
    const r = await request.get('/api/tts/local/voices');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    for (const engine of ['kokoro', 'piper', 'sapi']) {
      expect(j).toHaveProperty(engine);
      expect(j[engine]).toHaveProperty('available');
    }
  });

  test('GET /api/voice/prints — array', async ({ request }) => {
    const r = await request.get('/api/voice/prints');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    expect(Array.isArray(j)).toBe(true);
  });
});

// --- settings/routes ---

test.describe('JARVIS · settings/routes coverage', () => {
  test('GET /api/llm-params — params + defaults', async ({ request }) => {
    const r = await request.get('/api/llm-params');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    expect(j).toHaveProperty('params');
    expect(j).toHaveProperty('defaults');
    for (const k of ['temperature', 'num_predict', 'num_ctx']) {
      expect(j.params).toHaveProperty(k);
    }
  });

  test('GET /api/prompt-profiles — au moins un profil', async ({ request }) => {
    const r = await request.get('/api/prompt-profiles');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    const keys = Object.keys(j);
    expect(keys.length).toBeGreaterThan(0);
    const first = j[keys[0]];
    expect(typeof first.content === 'string' || typeof first === 'string').toBe(true);
  });

  test('GET /api/welcome — version + lines', async ({ request }) => {
    const r = await request.get('/api/welcome');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    expect(j).toHaveProperty('version');
    expect(j).toHaveProperty('lines');
    expect(Array.isArray(j.lines)).toBe(true);
  });

  test('GET /api/dsp-params — clés EQ/comp/stereo', async ({ request }) => {
    const r = await request.get('/api/dsp-params');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    for (const k of ['eq_low', 'eq_mid', 'eq_high', 'comp_threshold', 'comp_ratio', 'gain']) {
      expect(j).toHaveProperty(k);
    }
    expect(typeof j.enabled).toBe('boolean');
  });

  test('GET /api/models — liste + current', async ({ request }) => {
    const r = await request.get('/api/models');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    expect(Array.isArray(j.models)).toBe(true);
    expect(j.models.length).toBeGreaterThan(0);
    expect(typeof j.current).toBe('string');
  });
});

// --- dev/routes ---

test.describe('JARVIS · dev/routes coverage', () => {
  test('GET /api/dev/stats — disk/ram/uptime srv-dev-1', async ({ request }) => {
    const r = await request.get('/api/dev/stats');
    expect(r.ok()).toBe(true);
    const j = await r.json();
    for (const k of ['disk_pct', 'disk_total', 'ram_pct', 'ram_total', 'uptime']) {
      expect(j).toHaveProperty(k);
    }
  });
});

// --- web/routes ---

test.describe('JARVIS · web/routes coverage', () => {
  test('GET /api/web-test — DDG + Wikipedia connectivity', async ({ request }) => {
    test.setTimeout(15_000);
    const r = await request.get('/api/web-test', { timeout: 12_000 });
    expect(r.ok()).toBe(true);
    const j = await r.json();
    expect(j).toHaveProperty('connectivity');
    expect(j).toHaveProperty('ddg');
    expect(j).toHaveProperty('wikipedia');
    expect(typeof j.search_ok).toBe('boolean');
  });
});
