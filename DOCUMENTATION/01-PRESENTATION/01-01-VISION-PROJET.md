---
title: "Vision et objectifs du projet JARVIS"
code: "JARVIS-DOC-01-01"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Présentation"
mots_cles: ["vision", "objectifs", "jarvis", "ia-locale", "homelab"]
---

# Vision et objectifs du projet JARVIS

## Pourquoi JARVIS ?

JARVIS est un **assistant IA personnel local de type Iron Man** conçu et
opéré par Marc Sabater dans son homelab cybersécurité (0xCyberLiTech).
Il s'inscrit dans une démarche de **maîtrise technique complète** : pas
de dépendance à un service cloud LLM, traitement intégral des données en
local, contrôle total sur le pipeline modèle/voix/intégrations.

## Vision long terme

> Faire de JARVIS un **assistant IA spécialisé cybersécurité homelab**
> capable de :
> 1. **Analyser** en continu un SOC déployé sur srv-ngix (CrowdSec,
>    fail2ban, Suricata, nginx, ModSec) et alerter vocalement Marc en cas
>    de menace réelle (filtre RFC1918, anti-double-ban, crawlers FCrDNS
>    vérifiés)
> 2. **Agir** sur l'infrastructure (start/stop VM Proxmox, redémarrage
>    services, apt upgrade, ban CrowdSec/fail2ban) via SSH whitelist
>    stricte
> 3. **Conversationner** naturellement avec Marc dans 4 modes (SOC,
>    GENERAL, CODE, CODE-REASONING) pilotés par 5 modèles LLM Ollama
>    locaux (phi4:14b, gemma4, qwen2.5-coder, qwen3:8b, mxbai-embed)
> 4. **Coder** dans une VM dédiée (srv-dev-1) avec terminal interactif
>    xterm.js et SCP/exec piloté par LLM
> 5. **Apprendre** progressivement via RAG mxbai-embed (599 chunks
>    auto-refresh 6 h) sur les MEMORY.md des projets Marc

## Principes fondateurs

| Principe | Implémentation |
|---|---|
| **100 % local** | Ollama on-premise, aucun appel cloud LLM. Edge-TTS / Kokoro CUDA / Piper / SAPI5 chaîne de fallback locale (sauf Edge qui nécessite Internet) |
| **Zéro raw data vers cloud** | Architecture coût-LLM : JARVIS filtre/agrège/détecte en local, escalade uniquement les **escalations** vers Claude cloud (rare) |
| **Sécurité par défaut** | RFC1918 immuable jamais bannies · `_BLOCKED_SSH` 29 patterns · whitelists services source unique · auto-engine SOC actif **uniquement** en mode soc |
| **Code observable** | jarvis.log persistant (5 MB × 7) · tts.log · JS-DIAG v2 hooks · 6 garde-fous idempotence anti-cascade |
| **Architecture testable** | 24 tuiles autoportantes (Blueprint + DI) · 1294 tests pytest · ruff + eslint pre-commit · coverage 76 % |

## Objectifs mesurables

### Court terme (atteints au 2026-05-23)

- ✅ Refactor complet : monolithe `jarvis.py` 4814 L → **1821 L** (−62 %)
- ✅ 24 tuiles autoportantes avec pattern Blueprint+DI uniforme
- ✅ Bug UI reload aléatoire (15+ jours) résolu cause racine + validé
- ✅ Couverture 62 % → **76 %** avec modules critiques > 95 %
- ✅ Observabilité complète : tracebacks persistants + JS-DIAG actif

### Moyen terme (roadmap)

- 🔄 Tests E2E Playwright nettoyés (couverture Blueprints HTTP)
- 🔄 Documentation auto-générée à partir des docstrings
- 🔄 Réduction des aliases backward-compat dans jarvis.py
- 🔄 Sortie potentielle d'autres helpers (`stream_llm`, etc.) en tuiles dédiées

### Long terme (vision)

- 🌟 JARVIS comme **produit open source** réutilisable par d'autres homelabs
  cybersécurité (généricisation du pattern par tuiles)
- 🌟 Intégration Claude Desktop / Cursor / autres clients via MCP étendu
- 🌟 Mode multi-utilisateurs (admin + opérateurs) avec ACL granulaires
- 🌟 Plugin marketplace (tuiles communautaires : Grafana, Wazuh, etc.)

## Référence du projet

| Élément | Valeur |
|---|---|
| Nom du projet | JARVIS |
| Version actuelle | v3.3 (interface holographique) |
| Code organisation | 0xCyberLiTech |
| Auteur principal | Marc Sabater |
| Stack | Python 3.11 · Flask · Ollama · Web Audio · WebSocket |
| Plateforme | Windows 11 Pro · RTX 5080 16 GB · CUDA 12 |
| Repo | (privé Marc local — non publié à ce jour) |
| License | (à définir — candidat : MIT pour la diffusion future) |

## Sources de vérité documentaires

Les **chiffres courants du projet** (score dette, lignes, tests, coverage)
vivent dans une source unique : `06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md`
section §0. Toutes les autres docs y pointent — zéro dérive entre documents.
