"""Tests bypass_backup — détection regex + parsing résumé + SSE generators (mock subprocess)."""
import json
from unittest.mock import MagicMock

import bypass_backup

# ── Constantes / Regex ──────────────────────────────────────────────────


def test_backup_proc_timeout_300s():
    assert bypass_backup.BACKUP_PROC_TIMEOUT_S == 300


def test_backup_proc_long_timeout_3600s():
    assert bypass_backup.BACKUP_PROC_LONG_TIMEOUT_S == 3600


def test_backup_re_match_sauvegarde_vm():
    assert bypass_backup.BACKUP_RE.search("lance une sauvegarde VM")
    assert bypass_backup.BACKUP_RE.search("backup proxmox maintenant")
    assert bypass_backup.BACKUP_RE.search("sauvegarde des machines virtuelles")


def test_backup_re_pas_match_sans_vm_ou_proxmox():
    """Sauvegarde sans mention VM/proxmox/machines → pas match."""
    assert not bypass_backup.BACKUP_RE.search("sauvegarde mes documents")


def test_diskreport_re_match_disk_report():
    assert bypass_backup.DISKREPORT_RE.search("lance disk-report")
    assert bypass_backup.DISKREPORT_RE.search("rapport disque windows")


def test_jarvis_backup_re_match_sauvegarde_jarvis():
    assert bypass_backup.JARVIS_BACKUP_RE.search("sauvegarde JARVIS")
    assert bypass_backup.JARVIS_BACKUP_RE.search("backup jarvis maintenant")


def test_jarvis_backup_log_re_match_etat_jarvis():
    assert bypass_backup.JARVIS_BACKUP_LOG_RE.search("où en est jarvis ?")
    assert bypass_backup.JARVIS_BACKUP_LOG_RE.search("statut jarvis")
    assert bypass_backup.JARVIS_BACKUP_LOG_RE.search("log jarvis")


# ── _sse_tok ────────────────────────────────────────────────────────────


def test_sse_tok_format():
    out = bypass_backup._sse_tok("hello", done=True)
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload == {"type": "token", "token": "hello", "done": True}


# ── parse_backup_summary ────────────────────────────────────────────────


def test_parse_summary_aucune_vm_renvoie_strings_vides():
    md, tts = bypass_backup.parse_backup_summary(["random line", "another"])
    assert md == ""
    assert tts == ""


def test_parse_summary_vms_ok_genere_md_et_tts():
    """Format réel : `nom HH:MM:SS taille_Go OK` (sans préfixe VM)."""
    lines = [
        "nginx 00:01:23 5.2 Go OK",
        "clt 00:00:45 3.1 Go OK",
        "QUOTA [auto] 8.3 Go / 300 Go (2.7%)",
    ]
    md, tts = bypass_backup.parse_backup_summary(lines)
    assert "nginx" in md
    assert "clt" in md
    assert "Quota :" in md
    assert "8.3 Go / 300 Go" in md
    # TTS contient les noms des VMs
    assert "nginx" in tts
    assert "clt" in tts


def test_parse_summary_vm_echec_genere_message_erreur():
    """Une VM ECHEC → message TTS d'erreur avec mention de la VM en échec."""
    lines = [
        "nginx 00:01:23 5.2 Go OK",
        "clt 00:00:45 0.0 Go ECHEC",
    ]
    md, tts = bypass_backup.parse_backup_summary(lines)
    assert "erreurs" in tts.lower()
    assert "clt" in tts


def test_parse_summary_quota_optionnel():
    """Sans ligne QUOTA → md sans 'Quota :'."""
    lines = ["nginx 00:01:00 1.0 Go OK"]
    md, _ = bypass_backup.parse_backup_summary(lines)
    assert "Quota" not in md


def test_parse_summary_garde_dernier_quota_si_plusieurs():
    lines = [
        "x 00:00:01 1.0 Go OK",
        "QUOTA [auto] 1.0 Go / 100 Go (1%)",
        "QUOTA [auto] 2.0 Go / 100 Go (2%)",
    ]
    md, _ = bypass_backup.parse_backup_summary(lines)
    assert "2.0 Go / 100 Go" in md


# ── detect_backup_command ───────────────────────────────────────────────


def test_detect_jarvis_backup_log_priorite_haute():
    """JARVIS_BACKUP_LOG_RE testé en premier — état/log/où en est."""
    assert bypass_backup.detect_backup_command("où en est jarvis") == "backup-jarvis-log"
    assert bypass_backup.detect_backup_command("statut jarvis") == "backup-jarvis-log"


def test_detect_jarvis_backup():
    assert bypass_backup.detect_backup_command("sauvegarde jarvis") == "backup-jarvis"


def test_detect_backup_auto():
    assert bypass_backup.detect_backup_command("sauvegarde vm proxmox") == "backup-auto"


def test_detect_disk_report():
    assert bypass_backup.detect_backup_command("disk-report maintenant") == "disk-report"


def test_detect_aucune_correspondance_renvoie_none():
    assert bypass_backup.detect_backup_command("bonjour Marc") is None


# ── backup_sse — mocks subprocess.Popen ─────────────────────────────────


def _mock_popen_success(monkeypatch, output_lines, returncode=0):
    """Helper : mock subprocess.Popen pour simuler exécution PowerShell."""
    fake_proc = MagicMock()
    fake_proc.stdout = iter(output_lines)
    fake_proc.wait = MagicMock(return_value=returncode)
    fake_proc.returncode = returncode
    fake_proc.kill = MagicMock()
    monkeypatch.setattr(bypass_backup.subprocess, "Popen", lambda *a, **kw: fake_proc)
    return fake_proc


def test_backup_sse_script_path_vide_yield_erreur():
    events = list(bypass_backup.backup_sse("", "backup-auto"))
    assert len(events) == 1
    payload = json.loads(events[0].replace("data: ", "").strip())
    assert "Erreur" in payload["token"]
    assert payload["done"] is True


def test_backup_sse_succes_yield_lignes_et_status_ok(monkeypatch):
    _mock_popen_success(monkeypatch, ["ligne1\n", "ligne2\n"], returncode=0)
    events = list(bypass_backup.backup_sse("/path/script.ps1", "backup-auto"))
    # Doit contenir au moins : entête, lignes, status, token done, speak
    assert len(events) >= 4
    # Dernier event = speak
    last_event = json.loads(events[-1].replace("data: ", "").strip())
    assert last_event["type"] == "speak"
    # Status succès dans un des events (JSON-escape le 'è' → è)
    all_text = " ".join(events)
    assert "Succ" in all_text  # "Succès" → "Succès" dans JSON


def test_backup_sse_returncode_non_zero_yield_status_erreur(monkeypatch):
    _mock_popen_success(monkeypatch, ["x\n"], returncode=1)
    events = list(bypass_backup.backup_sse("/path/script.ps1", "backup-auto"))
    all_text = " ".join(events)
    assert "Code 1" in all_text


def test_backup_sse_disk_report_label_distinct(monkeypatch):
    """Le label 'Rapport disque Windows' apparaît pour disk-report."""
    _mock_popen_success(monkeypatch, [], returncode=0)
    events = list(bypass_backup.backup_sse("/path/x.ps1", "disk-report"))
    all_text = " ".join(events)
    assert "windows-disk-report.ps1" in all_text


def test_backup_sse_timeout_yield_message_timeout(monkeypatch):
    """proc.wait timeout → SubprocessTimeoutExpired → message timeout."""
    fake_proc = MagicMock()
    fake_proc.stdout = iter([])
    fake_proc.wait = MagicMock(side_effect=__import__("subprocess").TimeoutExpired(cmd="x", timeout=300))
    fake_proc.kill = MagicMock()
    monkeypatch.setattr(bypass_backup.subprocess, "Popen", lambda *a, **kw: fake_proc)
    events = list(bypass_backup.backup_sse("/path/script.ps1", "backup-auto"))
    all_text = " ".join(events)
    assert "Timeout" in all_text
    fake_proc.kill.assert_called_once()


def test_backup_sse_exception_yield_erreur_generique(monkeypatch):
    """Si Popen lève → message d'erreur générique."""
    monkeypatch.setattr(bypass_backup.subprocess, "Popen",
                        lambda *a, **kw: (_ for _ in ()).throw(OSError("popen failed")))
    events = list(bypass_backup.backup_sse("/path/x.ps1", "backup-auto"))
    all_text = " ".join(events)
    assert "Erreur" in all_text
    assert "popen failed" in all_text


# ── jarvis_backup_log_sse — lit Desktop\jarvis-backup.log ──────────────


def test_jarvis_backup_log_sse_log_inexistant(monkeypatch, tmp_path):
    """Si log inexistant → message + speak."""
    monkeypatch.setattr(bypass_backup.os.path, "expanduser", lambda x: str(tmp_path))
    # _ → log_path = tmp_path/Desktop/jarvis-backup.log → inexistant
    events = list(bypass_backup.jarvis_backup_log_sse())
    all_text = " ".join(events)
    # JSON-escape : 'é' devient 'é'
    assert "Aucun log trouv" in all_text


def test_jarvis_backup_log_sse_avec_log_en_cours(monkeypatch, tmp_path):
    """Log présent sans 'sauvegarde terminée' → status 'en cours'."""
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    log = desktop / "jarvis-backup.log"
    log.write_text("Démarrage sauvegarde\nVM 108 en cours...\n")
    monkeypatch.setattr(bypass_backup.os.path, "expanduser", lambda x: str(tmp_path))

    events = list(bypass_backup.jarvis_backup_log_sse())
    all_text = " ".join(events)
    assert "En cours" in all_text
    # Speak dit "en cours"
    speak_event = json.loads(events[-1].replace("data: ", "").strip())
    assert speak_event["type"] == "speak"
    assert "en cours" in speak_event["text"].lower()


def test_jarvis_backup_log_sse_termine(monkeypatch, tmp_path):
    """Log avec 'sauvegarde terminée' → status terminée + speak."""
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    log = desktop / "jarvis-backup.log"
    log.write_text("VM 108 OK\nsauvegarde terminée\n", encoding="utf-8")
    monkeypatch.setattr(bypass_backup.os.path, "expanduser", lambda x: str(tmp_path))

    events = list(bypass_backup.jarvis_backup_log_sse())
    # Le speak final indique "terminée" si finished=True (parse JSON pour décoder)
    speak_event = json.loads(events[-1].replace("data: ", "").strip())
    assert speak_event["type"] == "speak"
    assert "terminée" in speak_event["text"].lower()


def test_jarvis_backup_log_sse_tronque_a_30_dernieres():
    """Si > 30 lignes → seules les 30 dernières affichées."""
    # Simulation simple : on ne vérifie pas les lignes mais le helper fait un slice [-30:]
    # Test indirect : log avec 50 lignes
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        desktop = __import__("pathlib").Path(td) / "Desktop"
        desktop.mkdir()
        log = desktop / "jarvis-backup.log"
        log.write_text("\n".join(f"line{i}" for i in range(50)) + "\n")

        import unittest.mock
        with unittest.mock.patch.object(bypass_backup.os.path, "expanduser", return_value=td):
            events = list(bypass_backup.jarvis_backup_log_sse())
            all_text = " ".join(events)
            # line0 ne devrait PAS être dans la sortie (< 30 dernières)
            assert "line0\\n" not in all_text  # protection contre faux positif
            # line49 doit être dans la sortie
            assert "line49" in all_text


# ── jarvis_backup_sse ───────────────────────────────────────────────────


def test_jarvis_backup_sse_script_path_inexistant_yield_erreur(tmp_path):
    """Script inexistant → message d'erreur."""
    events = list(bypass_backup.jarvis_backup_sse(str(tmp_path / "absent.ps1")))
    all_text = " ".join(events)
    assert "introuvable" in all_text


def test_jarvis_backup_sse_script_path_vide_yield_erreur():
    events = list(bypass_backup.jarvis_backup_sse(""))
    all_text = " ".join(events)
    assert "introuvable" in all_text


def test_jarvis_backup_sse_succes(monkeypatch, tmp_path):
    """Script existe + Popen succès → status terminé + speak."""
    script = tmp_path / "backup-jarvis.ps1"
    script.write_text("Write-Host hello")
    fake_proc = MagicMock()
    fake_proc.stdout = iter(["ligne1\n", "ligne2\n"])
    fake_proc.wait = MagicMock(return_value=0)
    fake_proc.returncode = 0
    monkeypatch.setattr(bypass_backup.subprocess, "Popen", lambda *a, **kw: fake_proc)

    events = list(bypass_backup.jarvis_backup_sse(str(script)))
    # Décoder le JSON du dernier event (speak) pour vérifier UTF-8
    speak = json.loads(events[-1].replace("data: ", "").strip())
    assert "Sauvegarde JARVIS terminée" in speak["text"]


def test_jarvis_backup_sse_returncode_non_zero(monkeypatch, tmp_path):
    """Script échoue → message avec code retour."""
    script = tmp_path / "backup-jarvis.ps1"
    script.write_text("x")
    fake_proc = MagicMock()
    fake_proc.stdout = iter([])
    fake_proc.wait = MagicMock(return_value=42)
    fake_proc.returncode = 42
    monkeypatch.setattr(bypass_backup.subprocess, "Popen", lambda *a, **kw: fake_proc)

    events = list(bypass_backup.jarvis_backup_sse(str(script)))
    all_text = " ".join(events)
    assert "Code 42" in all_text


def test_jarvis_backup_sse_timeout_60min(monkeypatch, tmp_path):
    """Timeout long_timeout (3600s) → message timeout."""
    script = tmp_path / "backup-jarvis.ps1"
    script.write_text("x")
    fake_proc = MagicMock()
    fake_proc.stdout = iter([])
    fake_proc.wait = MagicMock(side_effect=__import__("subprocess").TimeoutExpired(cmd="x", timeout=3600))
    fake_proc.kill = MagicMock()
    monkeypatch.setattr(bypass_backup.subprocess, "Popen", lambda *a, **kw: fake_proc)

    events = list(bypass_backup.jarvis_backup_sse(str(script)))
    all_text = " ".join(events)
    assert "Timeout" in all_text
    assert "60 min" in all_text


def test_jarvis_backup_sse_exception_generique(monkeypatch, tmp_path):
    """Popen lève → message d'erreur générique."""
    script = tmp_path / "backup-jarvis.ps1"
    script.write_text("x")
    monkeypatch.setattr(bypass_backup.subprocess, "Popen",
                        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("popen broken")))
    events = list(bypass_backup.jarvis_backup_sse(str(script)))
    all_text = " ".join(events)
    assert "Erreur" in all_text
    assert "popen broken" in all_text
