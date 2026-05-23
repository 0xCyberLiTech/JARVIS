"""Schémas des outils LLM (tool-calling) — données pures, zéro dépendance.

Sous-module chat (refactor jarvis.py étape 24, 2026-05-23). Liste des 14
outils que le LLM peut appeler via Ollama tool-calling. Chaque entrée
décrit l'outil + ses paramètres au format OpenAI/Ollama function calling.

Consommé par `chat.orchestrator._run_tool_calls` (qui dispatche les appels
via `_TOOL_DISPATCH` dans jarvis.py).
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lire_fichier",
            "description": "Lit le contenu d'un fichier texte sur le PC",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin": {"type": "string", "description": "Chemin absolu ou relatif du fichier"}
                },
                "required": ["chemin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ecrire_fichier",
            "description": "Crée ou écrase un fichier avec le contenu fourni",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin":  {"type": "string", "description": "Chemin du fichier à écrire"},
                    "contenu": {"type": "string", "description": "Contenu à écrire dans le fichier"}
                },
                "required": ["chemin", "contenu"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modifier_fichier",
            "description": "Remplace une portion de texte dans un fichier existant",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin":    {"type": "string", "description": "Chemin du fichier"},
                    "ancien":    {"type": "string", "description": "Texte à remplacer"},
                    "nouveau":   {"type": "string", "description": "Nouveau texte"}
                },
                "required": ["chemin", "ancien", "nouveau"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lister_dossier",
            "description": "Liste le contenu d'un dossier",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin": {"type": "string", "description": "Chemin du dossier"}
                },
                "required": ["chemin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "executer_code",
            "description": "Exécute un script Python et retourne la sortie",
            "parameters": {
                "type": "object",
                "properties": {
                    "code":    {"type": "string", "description": "Code Python à exécuter"},
                    "timeout": {"type": "integer", "description": "Timeout en secondes (défaut 15)"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rechercher_dans_fichiers",
            "description": "Recherche un texte dans les fichiers d'un dossier",
            "parameters": {
                "type": "object",
                "properties": {
                    "dossier":  {"type": "string", "description": "Dossier racine de la recherche"},
                    "pattern":  {"type": "string", "description": "Texte ou regex à chercher"},
                    "extension":{"type": "string", "description": "Extension de fichier, ex: .py (optionnel)"}
                },
                "required": ["dossier", "pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "arborescence_projet",
            "description": "Retourne l'arborescence d'un dossier projet (récursif, 3 niveaux max). À utiliser en premier pour comprendre la structure avant de générer du code multi-fichiers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin":     {"type": "string",  "description": "Chemin du dossier racine du projet"},
                    "profondeur": {"type": "integer", "description": "Profondeur max (1-3, défaut 2)"}
                },
                "required": ["chemin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lire_plusieurs_fichiers",
            "description": "Lit plusieurs fichiers texte en une seule opération. Retourne leur contenu groupé. Utile pour analyser les interfaces d'un projet multi-fichiers avant de coder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemins": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste de chemins de fichiers à lire (max 5)"
                    }
                },
                "required": ["chemins"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "soc_status",
            "description": "Récupère l'état complet du SOC depuis srv-ngix (monitoring.json) : niveau de menace, IPs bannies CrowdSec/fail2ban, services, CPU/RAM, trafic, erreurs. Utiliser pour toute question sur la sécurité du serveur.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "commande_ssh_ngix",
            "description": "Exécute une commande shell sur srv-ngix (192.168.1.50) via SSH. Utiliser pour lire des logs, vérifier des services, interroger CrowdSec/fail2ban, etc. Commandes de lecture uniquement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commande": {"type": "string", "description": "Commande shell à exécuter sur srv-ngix (ex: 'tail -20 /var/log/nginx/access.log')"}
                },
                "required": ["commande"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "commande_ssh_proxmox",
            "description": "Exécute une commande shell sur Proxmox VE (192.168.1.20) via SSH. Utiliser pour : état des VMs (qm list), stockage (pvesm status), ressources (df -h), et gestion des VMs (qm stop <id>, qm start <id>). IDs : pa85=107, clt=106, srv-ngix=108.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commande": {"type": "string", "description": "Commande shell à exécuter sur Proxmox (ex: 'qm list', 'qm stop 107', 'qm start 106', 'pvesm status')"}
                },
                "required": ["commande"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "commande_ssh_clt",
            "description": "Exécute une commande shell sur clt (VM 106 — 192.168.1.12) via SSH. Utiliser pour vérifier Apache2, les logs d'erreur, l'état du site CLT cybersécurité. Commandes de lecture uniquement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commande": {"type": "string", "description": "Commande shell à exécuter sur clt (ex: 'systemctl status apache2', 'tail -20 /var/log/apache2/error.log')"}
                },
                "required": ["commande"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "commande_ssh_pa85",
            "description": "Exécute une commande shell sur pa85 (VM 107 — 192.168.1.13) via SSH. Utiliser pour vérifier Apache2, les logs d'erreur, l'état du site associatif PA85. Commandes de lecture uniquement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commande": {"type": "string", "description": "Commande shell à exécuter sur pa85 (ex: 'systemctl status apache2', 'tail -20 /var/log/apache2/error.log')"}
                },
                "required": ["commande"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "executer_script_windows",
            "description": "Exécute un script PowerShell local sur la machine Windows. Scripts disponibles : 'backup-auto' (sauvegarde automatique des 4 VMs Proxmox : srv-ngix 108 / clt 106 / pa85 107 / srv-dev-1 101 vers D:\\BACKUP-PROXMOX\\auto\\), 'disk-report' (rapport disque/GPU/CPU → dashboard SOC). Utiliser quand l'utilisateur demande de lancer une sauvegarde Proxmox ou un rapport système.",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "enum": ["backup-auto", "disk-report"],
                        "description": "Script à exécuter : 'backup-auto' ou 'disk-report'"
                    }
                },
                "required": ["script"]
            }
        }
    }
]
