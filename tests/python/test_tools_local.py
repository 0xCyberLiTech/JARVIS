"""Tests tools/local — 3 outils LLM (executer_code, soc_status, executer_script_windows)."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from tools import local as tools_local


@pytest.fixture(autouse=True)
def _reinit_tools():
    """Réinjecte un DI propre avant chaque test (les modules sont mutables)."""
    tools_local.init(
        blocked_hard            = ["shutil.rmtree"],
        blocked_args            = ["rm -rf", "qm destroy", "systemctl stop nginx"],
        sec_log                 = MagicMock(),
        fetch_monitoring        = MagicMock(return_value=(True, '{"k":"v"}')),
        build_monitoring_context= MagicMock(return_value="SOC CONTEXT"),
        allowed_scripts         = {"backup-jarvis": "C:/fake/path.ps1", "disk-report": "C:/disk.ps1"},
        proc_timeout_s          = 30,
    )
    yield


# ── executer_code — sécurité ───────────────────────────────────────────────


def test_executer_code_blocked_hard_refuse_avec_log():
    """`shutil.rmtree` dans le code → refus immédiat + audit sec_log('hard', ...)."""
    result = tools_local.executer_code({"code": "shutil.rmtree('/tmp')"})
    assert "refusée par sécurité" in result
    assert "shutil.rmtree" in result
    tools_local._sec_log.assert_called_once_with("hard", "shutil.rmtree", "shutil.rmtree('/tmp')")


def test_executer_code_blocked_args_refuse_avec_log():
    """`rm -rf` dans le code → refus + audit sec_log('args', ...)."""
    result = tools_local.executer_code({"code": "import os; os.system('rm -rf /')"})
    assert "refusé par sécurité" in result
    tools_local._sec_log.assert_called_once_with("args", "rm -rf", "import os; os.system('rm -rf /')")


def test_executer_code_blocked_args_case_insensitive():
    """Le check args est case-insensitive (RM -RF passe aussi)."""
    result = tools_local.executer_code({"code": "RM -RF /"})
    assert "refusé par sécurité" in result


# ── executer_code — exécution réelle subprocess ────────────────────────────


def test_executer_code_print_hello_capture_stdout():
    """Code Python simple → stdout capturé et retourné."""
    result = tools_local.executer_code({"code": "print('hello jarvis')"})
    assert "hello jarvis" in result


def test_executer_code_aucune_sortie_renvoie_placeholder():
    """Code qui ne print rien → '(aucune sortie)' explicite."""
    result = tools_local.executer_code({"code": "x = 1 + 1"})
    assert result == "(aucune sortie)"


def test_executer_code_erreur_python_renvoie_erreur():
    """Code Python invalide → message 'ERREUR:' avec stderr."""
    result = tools_local.executer_code({"code": "raise ValueError('boom')"})
    assert result.startswith("ERREUR:")
    assert "ValueError" in result


def test_executer_code_timeout_renvoie_message():
    """Code qui dépasse le timeout → message 'timeout dépassé'."""
    result = tools_local.executer_code({"code": "import time; time.sleep(5)", "timeout": 1})
    assert "timeout dépassé" in result
    assert "1s" in result


# ── soc_status ─────────────────────────────────────────────────────────────


def test_soc_status_fetch_ok_renvoie_contexte_formate():
    """fetch_monitoring OK → build_monitoring_context appelé avec header '=== SOC STATUS ==='."""
    result = tools_local.soc_status()
    assert result == "SOC CONTEXT"
    tools_local._build_monitoring_context.assert_called_once()
    # Vérifie le header SOC STATUS spécifique au tool (distinct de l'injection LLM normale)
    call_kwargs = tools_local._build_monitoring_context.call_args
    assert call_kwargs.kwargs.get("header") == "=== SOC STATUS ==="


def test_soc_status_fetch_ko_renvoie_erreur_ssh():
    """fetch_monitoring KO → message 'Erreur SSH srv-nginx : <raw>'."""
    tools_local._fetch_monitoring = MagicMock(return_value=(False, "timeout SSH"))
    result = tools_local.soc_status()
    assert "Erreur SSH srv-nginx" in result
    assert "timeout SSH" in result


def test_soc_status_json_invalide_renvoie_raw_tronque():
    """JSON parsing échoue → fallback 'monitoring.json brut' avec preview tronqué."""
    tools_local._fetch_monitoring = MagicMock(return_value=(True, "not-json-data"))
    result = tools_local.soc_status()
    assert "monitoring.json brut" in result
    assert "parse error" in result


# ── executer_script_windows ────────────────────────────────────────────────


def test_executer_script_windows_cle_non_autorisee():
    """Clé hors whitelist → refus + liste des clés autorisées."""
    result = tools_local.executer_script_windows({"script": "evil-script"})
    assert "non autorisé" in result
    assert "backup-jarvis" in result and "disk-report" in result


def test_executer_script_windows_cle_vide():
    """Clé vide ('') → refus (non trouvée dans whitelist)."""
    result = tools_local.executer_script_windows({"script": ""})
    assert "non autorisé" in result


def test_executer_script_windows_success_avec_mock_popen():
    """Mock subprocess.Popen → la fonction retourne 'Script ... terminé (code 0)'."""
    fake_proc = MagicMock()
    fake_proc.communicate.return_value = ("DONE 12 files", None)
    fake_proc.returncode = 0
    with patch("tools.local.subprocess.Popen", return_value=fake_proc) as mock_popen:
        result = tools_local.executer_script_windows({"script": "backup-jarvis"})
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert args[0] == "powershell.exe"
    assert args[-1] == "C:/fake/path.ps1"
    assert "Script 'backup-jarvis' terminé (code 0)" in result
    assert "DONE 12 files" in result


def test_executer_script_windows_returncode_non_zero_propage_dans_message():
    """returncode != 0 → reflété dans le message retourné."""
    fake_proc = MagicMock()
    fake_proc.communicate.return_value = ("erreur ligne 12", None)
    fake_proc.returncode = 3
    with patch("tools.local.subprocess.Popen", return_value=fake_proc):
        result = tools_local.executer_script_windows({"script": "disk-report"})
    assert "(code 3)" in result


def test_executer_script_windows_timeout_kill_proc():
    """TimeoutExpired → proc.kill() appelé + message timeout."""
    fake_proc = MagicMock()
    fake_proc.communicate.side_effect = subprocess.TimeoutExpired(cmd="ps", timeout=30)
    with patch("tools.local.subprocess.Popen", return_value=fake_proc):
        result = tools_local.executer_script_windows({"script": "backup-jarvis"})
    fake_proc.kill.assert_called_once()
    assert "timeout dépassé" in result
    assert "30s" in result


def test_executer_script_windows_aucune_sortie_renvoie_placeholder():
    """stdout vide → '(aucune sortie)' dans le message."""
    fake_proc = MagicMock()
    fake_proc.communicate.return_value = ("", None)
    fake_proc.returncode = 0
    with patch("tools.local.subprocess.Popen", return_value=fake_proc):
        result = tools_local.executer_script_windows({"script": "backup-jarvis"})
    assert "(aucune sortie)" in result
