#!/usr/bin/env bash
# wait-and-test.sh — attend le restart JARVIS (changement timestamp /api/health)
# puis lance la suite Playwright complète.
#
# Usage : bash tests/wait-and-test.sh [max_attempts]
#   - max_attempts : nombre de tentatives polling (défaut 60 = 4 min @ 4s/poll)
#
# Détection restart : on enregistre `ts` initial, on poll toutes les 4s,
# si le ts change → JARVIS a redémarré → on lance les tests.

set -e
cd "$(dirname "$0")/.."  # JARVIS/

MAX_ATTEMPTS="${1:-60}"

get_ts() {
    curl -s --max-time 2 http://localhost:5000/api/health 2>/dev/null \
        | python -c "import sys,json
try:
    d=json.loads(sys.stdin.read())
    print(d.get('ts',''))
except Exception:
    pass" 2>/dev/null || echo ""
}

echo "[poll] waiting for JARVIS restart on :5000 (max ${MAX_ATTEMPTS} attempts × 4s)..."
prev_ts=$(get_ts)
echo "[poll] current ts: $prev_ts (will detect change)"

for i in $(seq 1 "$MAX_ATTEMPTS"); do
    sleep 4
    cur_ts=$(get_ts)
    if [ -n "$cur_ts" ] && [ "$cur_ts" != "$prev_ts" ]; then
        echo "[poll] JARVIS restart détecté (new ts=$cur_ts) après ${i} attempts (~$((i*4))s)"
        sleep 5
        echo ""
        echo "=== running 23 E2E tests ==="
        exec npx playwright test --reporter=list
    fi
done

echo "[poll] TIMEOUT — pas de restart détecté en $((MAX_ATTEMPTS*4))s"
exit 1
