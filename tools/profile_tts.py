"""Profiling TTS détaillé — compare les 4 moteurs (edge / kokoro / piper / sapi).

Phase 4 chantier dette technique — 2026-05-15.

Pour chaque moteur :
- 3 textes (court / moyen / long)
- Mesure TTFB (premier byte audio) + total + taille bytes
- 2 runs (1er = COLD load, 2e = WARM si lazy load)

Restaure le tts_engine d'origine en fin de run (try/finally).

Usage : python tools/profile_tts.py
Pré-requis : JARVIS lancé sur localhost:5000.
"""
import json
import time
import urllib.request
from urllib.error import URLError

JARVIS = "http://127.0.0.1:5000"

# Textes variés (évite dedup 60s) + représentatifs des cas réels
TEXTS = [
    ("court (12 c.)",  "Bonjour Marc."),
    ("court (24 c.)",  "Test du moteur TTS."),
    ("court (36 c.)",  "Vérification audio en cours."),
    ("moyen (95 c.)",  "JARVIS effectue un test du moteur de synthèse vocale pour mesurer sa latence."),
    ("moyen (110 c.)", "Le système de défense SOC a détecté trois nouvelles tentatives de scan sur le serveur srv-nginx."),
    ("moyen (120 c.)", "Analyse en temps réel des logs CrowdSec : aucun ban critique sur les dernières vingt-quatre heures."),
    ("long (290 c.)",
     "Rapport quotidien JARVIS : l'auto-engine SOC reste actif, les services nginx, fail2ban et CrowdSec "
     "fonctionnent normalement. Le score de menace est stable en niveau MOYEN, deux IPs ont été bannies "
     "pendant la nuit suite à des tentatives de scan répétées sur les ports SSH non standards."),
]

ENGINES = ["edge", "kokoro", "piper", "sapi"]


def _http_get(url, timeout=10):
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
        return r.status, body, time.monotonic() - t0
    except URLError as e:
        return 0, str(e).encode(), time.monotonic() - t0


def _http_post_json(url, payload, timeout=30):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
        return r.status, body, time.monotonic() - t0
    except URLError as e:
        return 0, str(e).encode(), time.monotonic() - t0


def _http_post_first_byte(url, payload, timeout=60):
    """POST JSON → TTFB (1er byte) + taille totale + total."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            first = r.read(1)
            ttfb = time.monotonic() - t0
            rest = r.read()
            total_t = time.monotonic() - t0
            return r.status, len(first) + len(rest), ttfb, total_t
    except URLError as e:
        return 0, 0, time.monotonic() - t0, str(e)


def section(title):
    print(f"\n## {title}\n")


# ── 0. Health + état initial DSP ────────────────────────────────────────


section("0. État initial")
status, _, t = _http_get(f"{JARVIS}/api/health", timeout=5)
print(f"- Health JARVIS : HTTP {status} ({t * 1000:.0f}ms)")
if status != 200:
    print("\n⚠ JARVIS non joignable. Abort.")
    raise SystemExit(1)

status, body, _ = _http_get(f"{JARVIS}/api/dsp-params", timeout=5)
dsp = json.loads(body)
ORIGINAL_ENGINE = dsp.get("tts_engine", "edge")
ORIGINAL_VOICE  = dsp.get("tts_local_voice", "")
print(f"- Engine actuel : {ORIGINAL_ENGINE!r}")
print(f"- Voice locale  : {ORIGINAL_VOICE!r}")

status, body, _ = _http_get(f"{JARVIS}/api/tts/status", timeout=5)
try:
    tts_st = json.loads(body)
    print(f"- Disponibilité : edge={tts_st.get('edge')} kokoro={tts_st.get('kokoro')} "
          f"piper={tts_st.get('piper')} sapi={tts_st.get('sapi')}")
except Exception as e:
    print(f"- /api/tts/status parse fail: {e}")


# ── 1. Profil par moteur ────────────────────────────────────────────────


def _set_engine(engine):
    return _http_post_json(f"{JARVIS}/api/dsp-params", {"tts_engine": engine})


results = {}  # engine -> [(label, ttfb, total, size, status)]

try:
    for engine in ENGINES:
        section(f"1. {engine.upper()}")
        status, _, t = _set_engine(engine)
        if status != 200:
            print(f"  ⚠ Bascule moteur {engine} échec (HTTP {status}) — skip")
            continue
        print(f"  Bascule moteur OK ({t * 1000:.0f}ms)")
        time.sleep(0.3)  # laisser DSP_PARAMS être pris en compte par /api/tts
        engine_results = []
        for i, (label, text) in enumerate(TEXTS):
            # Run unique : pas de retry car dedup 60s sur même texte
            status, size, ttfb, total = _http_post_first_byte(
                f"{JARVIS}/api/tts", {"text": text, "source": f"profile_{engine}_{i}"},
                timeout=60,
            )
            if status == 200:
                kbps = (size * 8) / (total * 1000) if total > 0 else 0
                print(f"  - {label:18s} TTFB={ttfb * 1000:>5.0f}ms · total={total * 1000:>5.0f}ms · "
                      f"size={size:>7d}o · {kbps:.0f}kbps · HTTP {status}")
                engine_results.append((label, ttfb, total, size, status))
            else:
                err = total if isinstance(total, str) else f"timeout/err total={total:.1f}s"
                print(f"  - {label:18s} ÉCHEC ({err})")
                engine_results.append((label, 0, 0, 0, status))
        results[engine] = engine_results
finally:
    # Restauration impérative de l'engine d'origine
    print(f"\n## Restauration engine d'origine : {ORIGINAL_ENGINE!r}")
    status, _, _ = _set_engine(ORIGINAL_ENGINE)
    print(f"  HTTP {status}")


# ── 2. Tableau comparatif ───────────────────────────────────────────────


section("2. Comparatif synthétique (TTFB médiane par moteur)")

print("| Moteur          | Médiane TTFB | Médiane total | Réussite |")
print("|-----------------|--------------|---------------|----------|")
for engine, runs in results.items():
    successful = [r for r in runs if r[4] == 200]
    if not successful:
        print(f"| {engine.ljust(15)} | n/a          | n/a           | 0/{len(runs)}      |")
        continue
    ttfbs = sorted(r[1] for r in successful)
    totals = sorted(r[2] for r in successful)
    med_ttfb = ttfbs[len(ttfbs) // 2] * 1000
    med_total = totals[len(totals) // 2] * 1000
    print(f"| {engine.ljust(15)} | {med_ttfb:>9.0f} ms | {med_total:>10.0f} ms | "
          f"{len(successful)}/{len(runs)}      |")


# ── 3. Analyse texte ────────────────────────────────────────────────────


section("3. Analyse par taille de texte")
for engine, runs in results.items():
    ok = [r for r in runs if r[4] == 200]
    if not ok:
        continue
    short  = [r for r in ok if r[0].startswith("court")]
    medium = [r for r in ok if r[0].startswith("moyen")]
    long_  = [r for r in ok if r[0].startswith("long")]
    print(f"\n### {engine.upper()}")
    for label, group in [("court", short), ("moyen", medium), ("long", long_)]:
        if group:
            avg_ttfb = sum(r[1] for r in group) / len(group) * 1000
            avg_total = sum(r[2] for r in group) / len(group) * 1000
            avg_size = sum(r[3] for r in group) / len(group)
            print(f"  - {label}: TTFB moy {avg_ttfb:.0f}ms · total moy {avg_total:.0f}ms · "
                  f"taille moy {avg_size:.0f}o")


print("\n## Résumé")
print("Voir analyse + recommandations dans le commit suivant.\n")
