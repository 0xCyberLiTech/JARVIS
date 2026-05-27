"""Tests web/search.py + web/routes.py — recherche DDG + Wikipedia + route diagnostic.

Mocke `requests as req` au niveau du module pour eviter tout I/O reseau.
Couvre les branches succes/echec des 3 fonctions principales + la route Flask.
"""
import json
from unittest.mock import MagicMock

import pytest
from flask import Flask
from web import bp as web_bp
from web import routes as web_routes
from web import search as web_search


@pytest.fixture
def app():
    """Flask app de test avec le blueprint web + init logs."""
    app = Flask(__name__)
    app.testing = True
    _log = MagicMock()
    web_search.init(log=_log, web_search_timeout_s=10, web_fetch_timeout_s=8,
                    web_conn_timeout_s=5, web_fetch2_timeout_s=6)
    web_routes.init_routes(log=_log)
    app.register_blueprint(web_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _resp(json_data, ok=True, status=200):
    """Helper : mock minimal d'une reponse requests."""
    r = MagicMock()
    r.json.return_value = json_data
    r.status_code = status
    r.ok = ok
    return r


# Bloc init / config

def test_init_set_globals_correctement():
    log = MagicMock()
    web_search.init(log=log, web_search_timeout_s=11, web_fetch_timeout_s=22,
                    web_conn_timeout_s=33, web_fetch2_timeout_s=44)
    assert web_search._log is log
    assert web_search._web_search_timeout_s == 11
    assert web_search._web_fetch_timeout_s == 22
    assert web_search._web_conn_timeout_s == 33
    assert web_search._web_fetch2_timeout_s == 44


def test_web_headers_definis():
    """Constantes module : User-Agent + Accept-Language presentes."""
    assert "JARVIS" in web_search._WEB_HEADERS["User-Agent"]
    assert "fr" in web_search._WEB_HEADERS["Accept-Language"]


# Bloc search_ddg

def test_search_ddg_succes_abstract_seul(monkeypatch):
    monkeypatch.setattr(web_search.req, "get",
                        lambda *a, **k: _resp({"AbstractText": "L'IA c'est cool",
                                                "AbstractSource": "Wikipedia"}))
    out = web_search.search_ddg("ia", 3)
    assert len(out) == 1
    assert "Wikipedia" in out[0]
    assert "L'IA c'est cool" in out[0]


def test_search_ddg_abstract_plus_answer_plus_definition(monkeypatch):
    monkeypatch.setattr(web_search.req, "get",
                        lambda *a, **k: _resp({
                            "AbstractText": "abstract",
                            "Answer": "reponse directe",
                            "Definition": "definition",
                        }))
    out = web_search.search_ddg("q", 3)
    # 3 lignes : abstract + reponse + definition
    assert len(out) == 3
    assert any("Reponse" in r or "reponse" in r for r in out)
    assert any("Definition" in r or "definition" in r for r in out)


def test_search_ddg_related_topics(monkeypatch):
    monkeypatch.setattr(web_search.req, "get",
                        lambda *a, **k: _resp({
                            "AbstractText": "",
                            "RelatedTopics": [
                                {"Text": "topic1 long text"},
                                {"Text": "topic2"},
                                {"Text": "topic3"},
                            ],
                        }))
    out = web_search.search_ddg("q", 2)
    # max_results=2 → boucle prend [:2] = 2 topics
    assert len(out) == 2
    assert all(r.startswith("• ") for r in out)  # bullet


def test_search_ddg_related_topics_sans_text_ignores(monkeypatch):
    """Topics sans cle 'Text' ou non-dict ignores."""
    monkeypatch.setattr(web_search.req, "get",
                        lambda *a, **k: _resp({
                            "RelatedTopics": [
                                {"Text": "ok"},
                                {"NoText": "skip"},
                                "string_not_dict",
                            ],
                        }))
    out = web_search.search_ddg("q", 5)
    assert len(out) == 1
    assert "ok" in out[0]


def test_search_ddg_dedup_answer_dans_abstract(monkeypatch):
    """Si Answer est deja inclus dans AbstractText, ne pas dupliquer."""
    monkeypatch.setattr(web_search.req, "get",
                        lambda *a, **k: _resp({
                            "AbstractText": "abstract contient reponse",
                            "Answer": "reponse",
                        }))
    out = web_search.search_ddg("q", 3)
    assert len(out) == 1  # Answer absorbed dans Abstract


def test_search_ddg_exception_renvoie_liste_vide(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("network down")
    monkeypatch.setattr(web_search.req, "get", boom)
    assert web_search.search_ddg("q", 3) == []


def test_search_ddg_reponse_vide(monkeypatch):
    monkeypatch.setattr(web_search.req, "get", lambda *a, **k: _resp({}))
    assert web_search.search_ddg("q", 3) == []


# Bloc web_search

def test_web_search_combine_ddg_et_wikipedia(monkeypatch):
    calls = []

    def fake_get(url, **k):
        calls.append(url)
        if "duckduckgo" in url:
            return _resp({"AbstractText": "ddg result"})
        if "wikipedia" in url:
            # opensearch format : [query, [titles], [snippets], [urls]]
            return _resp(["q", ["Titre1", "Titre2"], ["snippet1", "snippet2"], []])
        return _resp({})

    monkeypatch.setattr(web_search.req, "get", fake_get)
    out = web_search.web_search("q", max_results=3)
    assert "ddg result" in out
    assert "Titre1" in out
    assert "snippet1" in out
    assert "RESULTATS WEB" in out or "RÉSULTATS WEB" in out


def test_web_search_wikipedia_exception_fallback(monkeypatch):
    """Si Wikipedia leve, le resultat DDG seul est renvoye."""
    def fake_get(url, **k):
        if "duckduckgo" in url:
            return _resp({"AbstractText": "ddg only"})
        raise ConnectionError("wiki down")
    monkeypatch.setattr(web_search.req, "get", fake_get)
    out = web_search.web_search("q", 3)
    assert "ddg only" in out


def test_web_search_aucun_resultat(monkeypatch):
    """Si DDG et Wikipedia retournent vide → message 'Aucun resultat'."""
    monkeypatch.setattr(web_search.req, "get",
                        lambda url, **k: _resp({}) if "duckduckgo" in url else _resp(["q", [], [], []]))
    out = web_search.web_search("query x", 3)
    assert "Aucun" in out
    assert "query x" in out


def test_web_search_wikipedia_dedup_avec_ddg(monkeypatch):
    """Si un titre Wikipedia est deja present dans le resultat DDG, ne pas le repeter."""
    def fake_get(url, **k):
        if "duckduckgo" in url:
            return _resp({"AbstractText": "Titre1 explication DDG"})
        return _resp(["q", ["Titre1", "TitreUnique"], ["snip1", "snip2"], []])
    monkeypatch.setattr(web_search.req, "get", fake_get)
    out = web_search.web_search("q", 3)
    # Titre1 deja dans DDG, mais l'algo verifie t not in str(results) — Titre1 EST dans abstract → skip
    # TitreUnique passe
    assert "TitreUnique" in out


def test_web_search_wikipedia_data_court(monkeypatch):
    """data Wikipedia tronque (len<2 ou <3) → pas de crash."""
    def fake_get(url, **k):
        if "duckduckgo" in url:
            return _resp({"AbstractText": "ddg"})
        return _resp(["q"])  # data[1]/data[2] absents
    monkeypatch.setattr(web_search.req, "get", fake_get)
    out = web_search.web_search("q", 3)
    assert "ddg" in out


# Bloc route /api/web-test

def test_route_web_test_tout_ok(client, monkeypatch):
    """Tous les services repondent : connectivity, ddg, wikipedia, search_ok."""
    def fake_get(url, **k):
        if "google" in url:
            return _resp({}, status=200)
        if "duckduckgo" in url:
            return _resp({"AbstractText": "ai is cool", "Answer": ""})
        if "wikipedia" in url:
            return _resp(["q", ["Titre"], ["snip"], []])
        return _resp({})
    monkeypatch.setattr(web_search.req, "get", fake_get)
    monkeypatch.setattr(web_routes.req, "get", fake_get)

    r = client.get("/api/web-test")
    assert r.status_code == 200
    data = json.loads(r.get_data(as_text=True))
    assert data["connectivity"] is True
    assert data["ddg"] is True
    assert data["wikipedia"] is True
    assert data["search_ok"] is True
    assert data["latency_ms"] is not None


def test_route_web_test_connectivity_ko(client, monkeypatch):
    """Google KO mais DDG + Wikipedia OK → connectivity False + error renseigne."""
    def fake_get(url, **k):
        if "google" in url:
            raise ConnectionError("no internet")
        if "duckduckgo" in url:
            return _resp({"AbstractText": "ok"})
        return _resp(["q", ["T"], ["s"], []])
    monkeypatch.setattr(web_search.req, "get", fake_get)
    monkeypatch.setattr(web_routes.req, "get", fake_get)

    r = client.get("/api/web-test")
    data = json.loads(r.get_data(as_text=True))
    assert data["connectivity"] is False
    assert data["error"] is not None
    assert "no internet" in data["error"]


def test_route_web_test_ddg_ko(client, monkeypatch):
    """DDG leve → ddg_error renseigne, ddg=False."""
    def fake_get(url, **k):
        if "google" in url:
            return _resp({}, status=200)
        if "duckduckgo" in url:
            raise RuntimeError("ddg fail")
        return _resp(["q", ["T"], ["s"], []])
    monkeypatch.setattr(web_search.req, "get", fake_get)
    monkeypatch.setattr(web_routes.req, "get", fake_get)

    r = client.get("/api/web-test")
    data = json.loads(r.get_data(as_text=True))
    assert data["ddg"] is False
    assert "ddg_error" in data
