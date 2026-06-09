# Hermès — Modes & Routing

> Référence complète du système de routing JARVIS : 4 modes, bypass déterministe, règles de sécurité.

---

## Les 4 modes

| Mode | Modèle LLM | Usage |
|------|-----------|-------|
| **SOC** (défaut) | phi4:14b | Cybersécurité · analyse menaces · contexte monitoring injecté |
| **GÉNÉRAL** | gemma4:latest | Conversation fluide · questions générales · vision multimodale |
| **CODE** | qwen2.5-coder:14b | Développement · infogérance · SSH dev · SCP · exécution |
| **CR** | qwen2.5-coder:14b | Code avec raisonnement explicite · analyse multi-fichiers |

Le mode actif est affiché dans l'interface et persisté entre les requêtes.
Basculement : boutons SOC / GÉNÉRAL / CODE dans l'onglet Chat, ou `POST /api/mode`.

---

## Pipeline de décision — ordre strict

```
Question reçue
    │
    ▼
1. BYPASS DETERMINISTE (zéro LLM)
   • Commandes temporelles  → Python datetime direct
   • Commandes VM/infra     → SSH Proxmox direct
   • Commandes service      → SSH direct
   • Lecture fichier        → SSH + cat direct
   → Réponse < 100 ms, 0 hallucination possible
    │ Non → LLM nécessaire
    ▼
2. FACTS INJECT
   • Date et heure courante
   • Mémoire persistante (leçons RAG)
    │
    ▼
3. RAG CONDITIONNEL
   • Requête ≥ 60 caractères OU mot-clé documentation
   → Injecte chunks pertinents (BM25 + vecteur hybride)
   • Sinon : SKIP (économise 200-500 ms)
    │
    ▼
4. SOC INJECT (si mode SOC + mots-clés sécurité)
   • Contexte monitoring.json injecté côté serveur
   • N'entre JAMAIS dans l'historique chat (side-channel)
    │
    ▼
5. ROUTING LLM
   • mode GÉNÉRAL / VOCAL → gemma4:latest
   • mode CODE / CR       → qwen2.5-coder:14b
   • mode SOC (défaut)    → phi4:14b (toujours chaud)
```

---

## Bypass déterministe — 9 patterns

Les bypasses sont intercalés **avant** le LLM. Aucun token Ollama n'est consommé.

| Pattern | Action |
|---------|--------|
| `"quelle heure"` / `"quelle date"` | Python `datetime.now()` → réponse immédiate |
| `"démarre [VM]"` / `"arrête [VM]"` | SSH Proxmox → `qm start/shutdown` |
| `"sauvegarde jarvis"` | Script local backup |
| `"redémarre [service]"` | SSH → `systemctl restart` (whitelist stricte) |
| `"lis [fichier]"` | SSH + `cat` (lecture seule) |
| `"recharge le RAG"` | `rag_engine.reload()` direct |
| `"vide la mémoire"` | `memory.clear()` direct |
| `"vérifie le menu"` | Menu-lint → verdict lu vocalement |
| `"état des VMs"` | SSH Proxmox → `qm list` |

---

## Règles de sécurité absolues

| Règle | Implémentation |
|-------|----------------|
| **RFC1918 immuable** | Les IPs de plages privées ne peuvent jamais être bannies |
| **SSH bloqué par défaut** | 29 patterns dangereux bloqués (`rm`, `dd`, `chmod 777`, `> /dev/sda`...) |
| **Écriture SSH par whitelist** | Uniquement les services et paquets listés explicitement |
| **Audit forensique** | Toute opération d'écriture SSH journalisée dans `audit_writeops.jsonl` |
| **Auto-engine isolé** | L'auto-engine SOC est actif uniquement en mode `soc` |

---

## Configuration du mode

```bash
# Lire le mode actif
GET /api/mode

# Changer de mode
POST /api/mode
{"mode": "soc"}    # ou "general", "code", "cr"
```

Le mode revient à `soc` au redémarrage du serveur.

---

*ROUTING-MODES.md · 0xCyberLiTech · 2026-06-09*
