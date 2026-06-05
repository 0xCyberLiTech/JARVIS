"""Tests proc_guard — Job Object Windows kill-on-close (fin des MCP orphelins port 5010).

Vérifie le mécanisme qui lie le sous-processus MCP à la vie de JARVIS : quand le handle
du job se ferme (ce que fait l'OS quand le parent meurt par N'IMPORTE QUEL moyen),
l'enfant lié est tué. Test bout-en-bout avec un vrai sous-processus.
"""
import ctypes
import os
import subprocess
import sys

import proc_guard
import pytest


def test_none_proc_renvoie_none():
    """Entrée None / pas de process → None, sans lever (best-effort)."""
    assert proc_guard.kill_child_with_parent(None) is None


@pytest.mark.skipif(os.name != "nt", reason="Job Object kill-on-close = Windows uniquement")
def test_fermer_le_job_tue_l_enfant():
    """KILL_ON_JOB_CLOSE bout-en-bout : fermer le handle du job tue l'enfant lié.

    Fermer le handle simule exactement la mort du parent (l'OS ferme alors tous ses
    handles, dont celui du job → KILL_ON_JOB_CLOSE → l'enfant meurt avec le parent).
    """
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        job = proc_guard.kill_child_with_parent(proc)
        assert job, "le Job Object n'a pas été créé / l'enfant non lié"
        assert proc.poll() is None, "l'enfant ne doit pas mourir tant que le job est ouvert"

        # Fermer le handle du job → l'OS tue tous ses processus (ici l'enfant).
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        k32.CloseHandle.restype = ctypes.c_int
        assert k32.CloseHandle(ctypes.c_void_p(int(job))), "CloseHandle(job) a échoué"

        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pytest.fail("l'enfant a survécu à la fermeture du job (kill-on-close inopérant)")
        assert proc.returncode is not None
    finally:
        if proc.poll() is None:           # garde-fou : ne jamais laisser d'orphelin de test
            proc.kill()
            proc.wait(timeout=5)
