"""Générateurs de correction de fichier — sous-module chat.

Phase B du chat tuile, étape 21 (2026-05-23). 3 générateurs SSE + 1 helper +
1 validateur de directives nginx protégées, déplacés depuis jarvis.py.

Pourquoi dans chat/ : ces générateurs orchestrent un appel LLM streaming
(via `chat.orchestrator._chat_stream_inner`) pour produire une version
corrigée d'un fichier lu via SSH. La correction == un flow chat spécifique.

Public surface :
- `file_correct_gen(f_vm, f_ssh_fn, f_path, ctx)`       : 1 fichier
- `file_correct_multi_gen(f_vm, f_ssh_fn, f_paths, ctx)`: N fichiers interconnectés
- `validate_protect_directives(original, llm_code)`     : restore directives nginx
- `PROTECTED_DIRECTIVES`                                 : set de directives jamais modifiables
"""
import json
import re

from . import orchestrator

# ── Directives nginx protégées contre faux positifs LLM ──────────────────
PROTECTED_DIRECTIVES = {
    'ssl_prefer_server_ciphers',   # off = correct avec TLS 1.3 (Mozilla modern)
    # ssl_protocols retiré : le LLM améliore correctement (supprime TLSv1/TLSv1.1)
    # Ajouter ici tout nouveau faux positif découvert lors des tests
}

# Dépendances injectées par init() (depuis chat/__init__.py)
_log = None
_sse_tok = None


def init(*, log, sse_tok) -> None:
    global _log, _sse_tok
    _log = log
    _sse_tok = sse_tok


def validate_protect_directives(original_content: str, llm_code: str):
    """Compare llm_code avec original_content et restaure les directives protégées.
    Retourne (code_corrigé, liste_descriptions_changements)."""
    changes = []
    result = llm_code
    for directive in PROTECTED_DIRECTIVES:
        orig_m = re.search(
            r'^\s*' + re.escape(directive) + r'\s+(.+?)\s*;',
            original_content, re.M | re.I)
        if not orig_m:
            continue
        orig_value = orig_m.group(1).strip()
        llm_m = re.search(
            r'^(\s*' + re.escape(directive) + r'\s+)(.+?)(\s*;.*)$',
            result, re.M | re.I)
        if not llm_m:
            continue
        llm_value = llm_m.group(2).strip()
        if llm_value.lower() != orig_value.lower():
            result = (result[:llm_m.start(1)]
                      + llm_m.group(1) + orig_value + llm_m.group(3)
                      + result[llm_m.end():])
            changes.append(f'{directive} : `{llm_value}` → `{orig_value}` (restauré)')
    return result, changes


def file_correct_gen(f_vm, f_ssh_fn, f_path, ctx):
    """Lit un fichier SSH, affiche dans l'UI, puis génère la correction via LLM en un seul shot."""
    basename = f_path.rstrip('/').rsplit('/', 1)[-1]
    is_dir = f_path.endswith('/') or ('.' not in basename and basename != '')
    cmd = f"ls -la {f_path}" if is_dir else f"cat {f_path}"
    ok, content = f_ssh_fn(cmd)
    if not ok or not content:
        yield _sse_tok(f"Erreur : impossible de lire `{f_path}` sur {f_vm}.", done=True)
        return
    # 1. Signal mode "lis+corrige" → JS sait qu'un header ORIGINAL/CORRIGÉE doit être affiché
    yield f"data: {json.dumps({'type':'file_correct_start','path':f_path,'vm':f_vm})}\n\n"
    # 1b. Affiche le fichier dans l'UI (modal holographique)
    yield f"data: {json.dumps({'type':'ssh_file','vm':f_vm,'path':f_path,'content':content.rstrip(),'action':'read'})}\n\n"
    # 2. Injecte le contenu dans le dernier message utilisateur
    for i in range(len(ctx.messages) - 1, -1, -1):
        if ctx.messages[i].get("role") == "user":
            ctx.messages[i] = dict(ctx.messages[i])
            ctx.messages[i]["content"] = (
                ctx.messages[i]["content"]
                + f"\n\n[Contenu actuel de `{f_path}` sur {f_vm}, lu via SSH :]\n```\n{content.rstrip()}\n```"
                + "\n\nIMPORTANT : propose le fichier COMPLET corrigé, pas de résumé ni d'extrait. Reproduis l'intégralité du fichier avec les corrections appliquées. Décommente les directives qui sont commentées à tort (ex: gzip, multi_accept) si elles ont une valeur correcte."
                + "\nRÈGLE ABSOLUE : conserve TOUTES les valeurs existantes à l'identique sauf si elles contiennent une erreur de syntaxe ou une incohérence évidente avec le reste du fichier. NE MODIFIE PAS les paramètres selon tes préférences ou recommandations générales — ce fichier est une config de production délibérément choisie. Si une valeur te semble non-optimale mais est cohérente et fonctionnelle, reproduis-la EXACTEMENT telle quelle. Signale à la fin (hors du bloc de code) les seules modifications que tu as faites et pourquoi."
                + "\nEXCLUSIONS CRITIQUES (ne jamais modifier ces directives) : ssl_prefer_server_ciphers (off est délibéré et conforme Mozilla modern TLS 1.3), worker_processes si valeur numérique explicite (ne pas remplacer par auto)."
            )
            break
    # 3. Génère la réponse LLM — stream + accumulation pour validation post-génération
    original_content = content
    full_llm_text = ""
    orchestrator._chat_stream_active.set()
    try:
        for _sse in orchestrator._chat_stream_inner(ctx, temp_override=0.15):
            yield _sse
            if _sse.startswith("data: "):
                try:
                    _d = json.loads(_sse[6:].strip())
                    if _d.get("type") == "token":
                        full_llm_text += _d.get("token", "")
                except Exception:
                    pass
    except Exception as exc:
        import traceback as _tb
        _log.error(f"[file_correct] stream error: {_tb.format_exc()}")
        yield f"data: {json.dumps({'type':'token','token':f'[JARVIS] Erreur interne : {exc}','done':True})}\n\n"
        return
    finally:
        orchestrator._chat_stream_active.clear()
    # 4. Validation post-génération — restaure les directives protégées si le LLM les a modifiées
    code_blocks = re.findall(r'```(?:\w+)?\n?([\s\S]*?)```', full_llm_text)
    if code_blocks:
        llm_code = code_blocks[-1]
        fixed_code, changes = validate_protect_directives(original_content, llm_code)
        if changes:
            _log.warning(f"[FILE_CORRECT_FIX] {len(changes)} faux positif(s) restauré(s) : {changes}")
            yield f"data: {json.dumps({'type':'file_correct_fix','code':fixed_code,'changes':changes})}\n\n"


def _file_correct_multi_inject(files, f_vm, ctx):
    """Injecte le contenu multi-fichiers dans le dernier message user du contexte LLM."""
    injected = f"\n\n[MULTI-FICHIERS — {len(files)} fichiers interconnectés sur {f_vm}]\n"
    injected += "Corrige chaque fichier en tenant compte de leurs dépendances (classes CSS partagées, IDs HTML ciblés par JS, chemins de ressources, etc.).\n\n"
    for f_path, content in files:
        ext = f_path.rsplit('.', 1)[-1].lower() if '.' in f_path else ''
        injected += f"### {f_path}\n```{ext}\n{content}\n```\n\n"
    injected += "\nIMPORTANT : pour chaque fichier, propose le contenu COMPLET corrigé dans un bloc de code séparé, dans le même ordre que ci-dessus."
    injected += "\nRÈGLE ABSOLUE : conserve les valeurs cohérentes et fonctionnelles. Corrige uniquement les bugs, failles de sécurité et mauvaises pratiques. Respecte les dépendances entre fichiers."
    injected += "\nEXCLUSIONS CRITIQUES (ne jamais modifier) : ssl_prefer_server_ciphers, worker_processes si valeur numérique explicite."
    for i in range(len(ctx.messages) - 1, -1, -1):
        if ctx.messages[i].get("role") == "user":
            ctx.messages[i] = dict(ctx.messages[i])
            ctx.messages[i]["content"] = ctx.messages[i]["content"] + injected
            break


def file_correct_multi_gen(f_vm, f_ssh_fn, f_paths, ctx):
    """Lit N fichiers SSH interconnectés, les affiche, puis génère les corrections en un shot."""
    files = []
    for f_path in f_paths:
        basename = f_path.rstrip('/').rsplit('/', 1)[-1]
        cmd = f"cat {f_path}" if '.' in basename else f"ls -la {f_path}"
        ok, content = f_ssh_fn(cmd)
        if ok and content:
            files.append((f_path, content.rstrip()))
        else:
            yield _sse_tok(f"⚠ Impossible de lire `{f_path}` sur {f_vm} — ignoré.\n", done=False)
    if not files:
        yield _sse_tok("Aucun fichier lu.", done=True)
        return
    yield f"data: {json.dumps({'type':'file_correct_start','path':f_paths[0],'vm':f_vm,'multi':True,'count':len(files)})}\n\n"
    for f_path, content in files:
        yield f"data: {json.dumps({'type':'ssh_file','vm':f_vm,'path':f_path,'content':content,'action':'read'})}\n\n"
    _file_correct_multi_inject(files, f_vm, ctx)
    full_llm_text = ""
    orchestrator._chat_stream_active.set()
    try:
        for _sse in orchestrator._chat_stream_inner(ctx, temp_override=0.15):
            yield _sse
            if _sse.startswith("data: "):
                try:
                    _d = json.loads(_sse[6:].strip())
                    if _d.get("type") == "token":
                        full_llm_text += _d.get("token", "")
                except Exception:
                    pass
    except Exception as exc:
        _log.error(f"[file_correct_multi] stream error: {exc}")
        yield _sse_tok(f"Erreur : {exc}", done=True)
        return
    finally:
        orchestrator._chat_stream_active.clear()
    code_blocks = re.findall(r'```(?:\w+)?\n?([\s\S]*?)```', full_llm_text)
    all_changes = []
    for idx, (f_path, orig_content) in enumerate(files):
        if idx < len(code_blocks):
            _, changes = validate_protect_directives(orig_content, code_blocks[idx])
            all_changes.extend([f'[{f_path.rsplit("/",1)[-1]}] {c}' for c in changes])
    if all_changes:
        _log.warning(f"[FILE_CORRECT_MULTI_FIX] {all_changes}")
        yield f"data: {json.dumps({'type':'file_correct_fix','code':'','changes':all_changes})}\n\n"
