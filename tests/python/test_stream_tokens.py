"""Tests stream_tokens — découpe phrases TTS, préservation IPs/versions."""
import json

from stream_tokens import _DOT_SPLIT_RE, DEFAULT_PHRASE_MIN, stream_tokens_tts


def _stub_stream(tokens_with_done):
    """Construit un stub stream_llm_fn qui yield les tokens fournis."""
    def fn(messages, model_override=None, options_override=None):
        for t in tokens_with_done:
            yield t
    return fn


def _events(out):
    """Parse les events SSE du stream."""
    return [json.loads(o.replace("data: ", "").strip()) for o in out]


def _call(tokens, **overrides):
    args = dict(
        messages=[],
        active_model="phi4:14b",
        opts=None,
        stream_llm_fn=_stub_stream(tokens),
        clean_text_fn=lambda s: s,  # passe-plat par défaut
    )
    args.update(overrides)
    return list(stream_tokens_tts(**args))


# ── Token events ──────────────────────────────────────────────────────────


def test_chaque_token_emis_comme_event_token():
    tokens = [("hello", False), (" world", True)]
    out = _events(_call(tokens))
    token_events = [e for e in out if e["type"] == "token"]
    assert len(token_events) == 2
    assert token_events[0]["token"] == "hello"
    assert token_events[1]["done"] is True


# ── Découpe sur séparateurs forts (! ? \n) ───────────────────────────────


def test_split_sur_point_exclamation():
    tokens = [("Salut Marc!", True)]
    out = _events(_call(tokens))
    speak_events = [e for e in out if e["type"] == "speak"]
    assert len(speak_events) == 1
    assert speak_events[0]["text"] == "Salut Marc!"


def test_split_sur_point_interrogation():
    tokens = [("Comment vas-tu?", True)]
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    assert speak_events[0]["text"] == "Comment vas-tu?"


def test_split_sur_newline():
    tokens = [("Premier\nDeuxième", True)]
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    # "Premier" est splitté → speak yield, puis "Deuxième" reste dans buf jusqu'au flush final
    assert speak_events[0]["text"] == "Premier\n"
    assert speak_events[1]["text"] == "Deuxième"


def test_plusieurs_phrases_dans_un_token_emis_separement():
    """Note : le split se fait sep par sep sur le buffer entier, donc le "." de
    "Phrase un." reste dans le bloc émis avec "!" (jamais évalué isolément)."""
    tokens = [("Phrase un. Phrase deux! Phrase trois?", True)]
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    assert len(speak_events) == 2
    assert speak_events[0]["text"] == "Phrase un. Phrase deux!"
    assert speak_events[1]["text"] == "Phrase trois?"


def test_plusieurs_phrases_separees_par_des_points_sont_splittees():
    """3 phrases séparées par "." (avec espace après chiffres exclus) → 3 events."""
    tokens = [("Bonjour Marc. Ça va. Tout est OK", True)]
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    # "Bonjour Marc.", "Ça va.", "Tout est OK" (flush final)
    assert len(speak_events) == 3


# ── Préservation IPs (split "." hors chiffres) ───────────────────────────


def test_ip_preservee_pas_split_au_milieu():
    """`192.168.1.50` ne doit PAS être découpé sur les points."""
    tokens = [("Ban 192.168.1.50 maintenant.", True)]
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    # Split sur le point final UNIQUEMENT
    assert len(speak_events) == 1
    assert "192.168.1.50" in speak_events[0]["text"]


def test_version_preservee_pas_split_v3_44():
    tokens = [("Version v3.44 déployée.", True)]
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    assert "v3.44" in speak_events[0]["text"]


def test_dot_split_re_pattern_explicite():
    """Sanity check du pattern : split sur point sauf entre chiffres."""
    assert _DOT_SPLIT_RE.split("a.b.c") == ["a", "b", "c"]
    assert _DOT_SPLIT_RE.split("1.2.3") == ["1.2.3"]  # chiffres → pas split
    assert _DOT_SPLIT_RE.split("v1.2 fin.") == ["v1.2 fin", ""]


# ── Phrase min ────────────────────────────────────────────────────────────


def test_phrase_trop_courte_pas_emise_au_tts():
    """Phrase plus courte que phrase_min → skipped."""
    tokens = [("ok!", True)]  # "ok" = 2 chars < default 4
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    assert speak_events == []


def test_phrase_min_borne_exclusive():
    """`len > phrase_min` : phrase de longueur exactement phrase_min → skip."""
    # Default 4, "abcd" = 4 chars → strictement pas plus grand → skip
    tokens = [("abcd!", True)]
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    assert speak_events == []


def test_phrase_min_personnalise():
    tokens = [("ok ok!", True)]
    speak_events = [e for e in _events(_call(tokens, phrase_min=2)) if e["type"] == "speak"]
    assert len(speak_events) == 1


# ── clean_text_fn appelé ──────────────────────────────────────────────────


def test_clean_text_fn_appele_sur_chaque_phrase():
    captured = []

    def clean(s):
        captured.append(s)
        return s.upper()

    tokens = [("salut!", True)]
    speak_events = [e for e in _events(_call(tokens, clean_text_fn=clean, phrase_min=3))
                    if e["type"] == "speak"]
    assert speak_events[0]["text"] == "SALUT!"
    assert "salut" in captured


# ── Default constant ─────────────────────────────────────────────────────


def test_default_phrase_min_vaut_4():
    assert DEFAULT_PHRASE_MIN == 4


# ── Flush final ───────────────────────────────────────────────────────────


def test_buffer_final_flushe_si_assez_long():
    """Pas de séparateur final → flush au end (si > phrase_min)."""
    tokens = [("phrase sans terminaison", True)]
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    assert len(speak_events) == 1
    assert speak_events[0]["text"] == "phrase sans terminaison"


def test_buffer_final_skipe_si_trop_court():
    tokens = [("ok", True)]  # 2 chars < 4
    speak_events = [e for e in _events(_call(tokens)) if e["type"] == "speak"]
    assert speak_events == []
