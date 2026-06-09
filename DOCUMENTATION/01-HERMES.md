<div align="center">

  <br></br>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="Titre dynamique JARVIS" />
  </a>

  <br></br>

  <h2>Assistant IA local · voix · interface holographique · automatisation SOC 24/7</h2>

  <p align="center">
    <a href="https://0xcyberlitech.github.io/">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    <a href="https://github.com/0xCyberLiTech">
      <img src="https://img.shields.io/badge/Profil-GitHub-181717?logo=github&style=flat-square" alt="Profil GitHub" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/releases/latest">
      <img src="https://img.shields.io/github/v/release/0xCyberLiTech/JARVIS?label=version&style=flat-square&color=blue" alt="Dernière version" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/%F0%9F%93%84%20Changelog-JARVIS-blue?style=flat-square" alt="Changelog" />
    </a>
    <a href="https://github.com/0xCyberLiTech?tab=repositories">
      <img src="https://img.shields.io/badge/D%C3%A9p%C3%B4ts-publics-blue?style=flat-square" alt="Dépôts publics" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/graphs/contributors">
      <img src="https://img.shields.io/badge/%F0%9F%91%A5%20Contributeurs-cliquez%20ici-007ec6?style=flat-square" alt="Contributeurs" />
    </a>
  </p>

</div>

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/cyber-security.png" alt="CyberSec" width="80"/>
</div>

<div align="center">
  <p>
    <strong>IA 100% locale</strong> <img src="https://img.icons8.com/color/24/000000/lock--v1.png"/> &nbsp;•&nbsp; <strong>Voix naturelle · STT · TTS</strong> <img src="https://img.icons8.com/color/24/000000/linux.png"/> &nbsp;•&nbsp; <strong>Automatisation SOC</strong> <img src="https://img.icons8.com/color/24/000000/shield-security.png"/>
  </p>
</div>

---
# Hermès — L'agent persistant

## Objectif
Hermès est la couche d'agentification de JARVIS.
Là où un assistant répond à des questions, un agent **observe, mémorise, apprend et agit** de façon autonome — sans être re-briefé à chaque session.

---

## Les 5 briques

| # | Brique | Rôle |
|---|--------|------|
| 1 | **Synoptique temps réel** | 6 couches moteur visibles dans l'interface : LLM actif, chunks RAG chargés, STT/TTS, auto-engine SOC, état mémoire |
| 2 | **Tuile Mémoire** | État de la mémoire vectorielle — échanges, résumés, leçons apprises — rechargeable depuis l'interface sans redémarrage |
| 3 | **Bypass déterministe** | Les commandes critiques sont interceptées avant le LLM — exécution < 100 ms, zéro hallucination possible |
| 4 | **Boucle d'apprentissage** | `"Souviens-toi que X"` → leçon persistée, indexée dans le RAG, réinjectée automatiquement dans les futures réponses |
| 5 | **Briefing matinal** | `"Bonjour JARVIS"` → briefing vocal : niveau de menace SOC, état des machines, alertes 24 h |

---

## Avant / Après Hermès

| Avant | Après |
|-------|-------|
| Chaque session recommence à zéro | JARVIS accumule le contexte entre les sessions |
| Le contexte disparaît au redémarrage | Leçons, conventions et préférences indexées dans le RAG |
| L'assistant répond seulement | L'agent surveille, alerte et agit sur seuil dépassé |
| Toutes les commandes passent par le LLM | Bypass déterministe pour les commandes critiques |

---

## Bypass déterministe

Le bypass intercepte les commandes **avant** le LLM. Aucun token Ollama n'est consommé.

| Commande vocale / texte | Action directe |
|------------------------|----------------|
| `"quelle heure est-il ?"` | Python `datetime.now()` → réponse immédiate |
| `"recharge le RAG"` | `rag_engine.reload()` direct |
| `"vide la mémoire"` | `memory.clear()` direct |
| `"bonjour JARVIS"` | Briefing matinal complet (SOC + infra + alertes) |
| `"vérifie le menu"` | Menu-lint → verdict lu vocalement |
| `"état des VMs"` | SSH Proxmox → `qm list` live |

---

## Boucle d'apprentissage

```
Utilisateur : "Souviens-toi que les backups se font le samedi soir"
    │
    ▼ JARVIS détecte le pattern "souviens-toi"
    │
    ▼ Leçon persistée dans jarvis_facts.json
    │
    ▼ Indexée dans la base vectorielle RAG
    │
    ▼ Réinjectée automatiquement dans les futures réponses pertinentes
    │
Résultat : JARVIS connaît cette règle dans toutes les sessions suivantes
           sans être re-briefé
```

---

## Pipeline de décision — ordre strict

```
Question reçue
    │
    ▼ 1. BYPASS DETERMINISTE (< 100 ms — zéro LLM)
    │   • commandes temporelles, VM, service, lecture fichier
    │
    ▼ 2. FACTS INJECT — date/heure + mémoire persistante (leçons)
    │
    ▼ 3. RAG CONDITIONNEL
    │   • requête ≥ 60 caractères OU mot-clé documentation
    │   → chunks pertinents injectés (BM25 + vecteur hybride)
    │
    ▼ 4. SOC INJECT (mode soc uniquement)
    │   • contexte monitoring live injecté en side-channel
    │   • n'entre JAMAIS dans l'historique chat
    │
    ▼ 5. ROUTING LLM
        • mode SOC    → phi4:14b (toujours chaud)
        • mode GÉNÉRAL → gemma4:latest
        • mode CODE   → qwen2.5-coder:14b
```

---

## Les 4 modes

| Mode | Modèle | Usage |
|------|--------|-------|
| **SOC** (défaut) | phi4:14b | Cybersécurité · analyse menaces · contexte monitoring injecté |
| **GÉNÉRAL** | gemma4:latest | Conversation fluide · questions générales · vision multimodale |
| **CODE** | qwen2.5-coder:14b | Développement · infogérance · SSH dev · SCP · exécution |
| **CR** | qwen2.5-coder:14b | Code avec raisonnement explicite · analyse multi-fichiers |

---

**Retour →** [README](../README.md) &nbsp;&nbsp; **Suivant →** [02 — Intégration SOC](02-SOC-INTEGRATION.md)

---

<div align="center">

<table>
<tr>
<td align="center"><b>🖥️ Infrastructure &amp; Sécurité</b></td>
<td align="center"><b>💻 Développement &amp; Web</b></td>
<td align="center"><b>🤖 Intelligence Artificielle</b></td>
</tr>
<tr>
<td align="center">
  <a href="https://www.kernel.org/"><img src="https://skillicons.dev/icons?i=linux" width="48" title="Linux" /></a>
  <a href="https://www.debian.org"><img src="https://skillicons.dev/icons?i=debian" width="48" title="Debian" /></a>
  <a href="https://www.gnu.org/software/bash/"><img src="https://skillicons.dev/icons?i=bash" width="48" title="Bash" /></a>
  <br/>
  <a href="https://nginx.org"><img src="https://skillicons.dev/icons?i=nginx" width="48" title="Nginx" /></a>
  <a href="https://git-scm.com"><img src="https://skillicons.dev/icons?i=git" width="48" title="Git" /></a>
</td>
<td align="center">
  <a href="https://www.python.org"><img src="https://skillicons.dev/icons?i=python" width="48" title="Python" /></a>
  <a href="https://flask.palletsprojects.com"><img src="https://skillicons.dev/icons?i=flask" width="48" title="Flask" /></a>
  <a href="https://developer.mozilla.org/docs/Web/HTML"><img src="https://skillicons.dev/icons?i=html" width="48" title="HTML5" /></a>
  <br/>
  <a href="https://developer.mozilla.org/docs/Web/CSS"><img src="https://skillicons.dev/icons?i=css" width="48" title="CSS3" /></a>
  <a href="https://developer.mozilla.org/docs/Web/JavaScript"><img src="https://skillicons.dev/icons?i=js" width="48" title="JavaScript" /></a>
  <a href="https://code.visualstudio.com"><img src="https://skillicons.dev/icons?i=vscode" width="48" title="VS Code" /></a>
</td>
<td align="center">
  <a href="https://ollama.com"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" /></a>
  <br/><br/>
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic" /></a>
</td>
</tr>
</table>

<br/>

<sub>🔒 Projets proposés par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Développés en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</sub>

</div>
