"""Ollama Circuit Breaker — protection cascade panne (3 états).

Phase 4 chantier dette technique 2026-05-15.

Pattern circuit breaker classique pour protéger JARVIS contre les pannes Ollama.

États :
- CLOSED      : état normal, requêtes passent normalement.
- OPEN        : Ollama considéré down. Toutes les requêtes échouent IMMÉDIATEMENT
                avec OllamaUnavailable (1 ms au lieu de timeout 30 s) → JARVIS
                reste réactif, pas de cascade saturation.
- HALF_OPEN   : après RECOVERY_TIMEOUT_S, on autorise UN test. Si succès → CLOSED.
                Si échec → retour OPEN avec backoff exponentiel (×2 max).

Configuration :
- FAILURE_THRESHOLD : 3 erreurs consécutives → OPEN
- RECOVERY_TIMEOUT_S : 30 s avant test HALF_OPEN
- BACKOFF_MAX_S : 300 s plafond backoff exponentiel

Thread-safe via lock module-level.

Usage :
    from ollama_circuit import circuit, OllamaUnavailable
    try:
        result = circuit.call(requests.post, url, json=payload, timeout=10)
    except OllamaUnavailable:
        return "Ollama indisponible, réessai dans 30s"
"""
import threading
import time

# ── Configuration ─────────────────────────────────────────────
FAILURE_THRESHOLD = 3        # 3 erreurs consécutives → OPEN
RECOVERY_TIMEOUT_S = 30      # délai avant test HALF_OPEN
BACKOFF_MAX_S = 300          # plafond backoff exponentiel (5 min)

# ── États ─────────────────────────────────────────────────────
STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"


class OllamaUnavailable(Exception):
    """Levée par circuit.call() quand le circuit est OPEN."""


class _CircuitBreaker:
    """Circuit breaker thread-safe avec backoff exponentiel."""

    def __init__(self):
        self._state = STATE_CLOSED
        self._failures = 0           # compteur erreurs consécutives
        self._opened_at = 0.0        # timestamp ouverture circuit
        self._current_timeout = RECOVERY_TIMEOUT_S  # timeout courant (backoff)
        self._lock = threading.Lock()

    def call(self, fn, *args, **kwargs):
        """Appelle fn(*args, **kwargs) si CLOSED/HALF_OPEN, sinon raise OllamaUnavailable.

        En HALF_OPEN, autorise UN seul test. Le résultat décide CLOSED (succès) ou OPEN (échec).
        """
        with self._lock:
            now = time.monotonic()
            # Transition OPEN → HALF_OPEN si timeout expiré
            if self._state == STATE_OPEN and (now - self._opened_at) >= self._current_timeout:
                self._state = STATE_HALF_OPEN
            # Refus immédiat si toujours OPEN
            if self._state == STATE_OPEN:
                raise OllamaUnavailable(
                    f"Ollama indisponible — circuit ouvert (retry dans {int(self._current_timeout - (now - self._opened_at))}s)"
                )
        # Tentative d'appel (hors lock pour ne pas bloquer les autres threads)
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        """Succès : reset failures, retour CLOSED si HALF_OPEN."""
        with self._lock:
            self._failures = 0
            if self._state in (STATE_HALF_OPEN, STATE_OPEN):
                self._state = STATE_CLOSED
                self._current_timeout = RECOVERY_TIMEOUT_S  # reset backoff

    def _on_failure(self):
        """Échec : incrément, ouverture si seuil atteint, backoff exponentiel si HALF_OPEN→OPEN."""
        with self._lock:
            self._failures += 1
            if self._state == STATE_HALF_OPEN:
                # Test HALF_OPEN raté → backoff exponentiel
                self._current_timeout = min(self._current_timeout * 2, BACKOFF_MAX_S)
                self._state = STATE_OPEN
                self._opened_at = time.monotonic()
            elif self._state == STATE_CLOSED and self._failures >= FAILURE_THRESHOLD:
                self._state = STATE_OPEN
                self._opened_at = time.monotonic()
                self._current_timeout = RECOVERY_TIMEOUT_S  # 1er ouverture = timeout de base

    def get_status(self) -> dict:
        """Retourne l'état complet pour exposition API/UI.

        Format : {state, failures, retry_in_s, current_timeout_s}
        retry_in_s : secondes avant test HALF_OPEN (0 si CLOSED).
        """
        with self._lock:
            now = time.monotonic()
            retry_in_s = 0
            if self._state == STATE_OPEN:
                elapsed = now - self._opened_at
                retry_in_s = max(0, int(self._current_timeout - elapsed))
            return {
                "state": self._state,
                "failures": self._failures,
                "retry_in_s": retry_in_s,
                "current_timeout_s": int(self._current_timeout),
            }

    def reset(self):
        """Force le reset complet (debug/maintenance)."""
        with self._lock:
            self._state = STATE_CLOSED
            self._failures = 0
            self._opened_at = 0.0
            self._current_timeout = RECOVERY_TIMEOUT_S


# ── Singleton instance ────────────────────────────────────────
circuit = _CircuitBreaker()
