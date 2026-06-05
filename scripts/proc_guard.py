"""Garde-fou processus enfant — Windows : tuer l'enfant quand le parent meurt.

JARVIS lance le serveur MCP en sous-processus (`subprocess.Popen`). Sous Windows un
enfant NE meurt PAS quand son parent est tué de force (taskkill /F, fermeture de la
fenêtre, crash) : seul un arrêt gracieux (Ctrl+C) déclenche le nettoyage `finally`.
Résultat observé dans jarvis.log : un MCP **orphelin** sur le port 5010 que le boot
suivant doit nettoyer ([MCP] kill orphelin à chaque démarrage).

`kill_child_with_parent` attache l'enfant à un **Job Object** Windows marqué
`KILL_ON_JOB_CLOSE` : quand le parent disparaît PAR N'IMPORTE QUEL MOYEN, l'OS ferme
le handle du job → l'OS tue tous les processus du job → l'enfant meurt avec le parent.
Plus jamais d'orphelin. Best-effort : ne lève jamais — un échec laisse simplement les
filets existants (cleanup `finally` + nettoyage orphelin au boot) prendre le relais.
No-op gracieux hors Windows (POSIX gère via groupes de processus / le `finally` suffit).
"""
import os

# Constantes API Windows (faits stables documentés — winnt.h, pas de l'infra à externaliser)
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JobObjectExtendedLimitInformation = 9   # JOBOBJECTINFOCLASS


def kill_child_with_parent(proc):
    """Attache `proc` (subprocess.Popen) à un Job Object KILL_ON_JOB_CLOSE.

    Renvoie le handle du job (int) ou None si non-Windows / proc absent / échec.
    Tant que le handle reste ouvert (jusqu'à la mort du parent, l'OS le ferme alors
    automatiquement), l'enfant est lié à la vie du parent. Best-effort : toute erreur
    renvoie None sans lever (les filets existants restent actifs).
    """
    if os.name != "nt" or proc is None:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        _LARGE_INTEGER = ctypes.c_int64
        _ULONG_PTR = ctypes.c_size_t
        _SIZE_T = ctypes.c_size_t

        class _BASIC(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", _LARGE_INTEGER),
                ("PerJobUserTimeLimit", _LARGE_INTEGER),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", _SIZE_T),
                ("MaximumWorkingSetSize", _SIZE_T),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", _ULONG_PTR),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _IO(ctypes.Structure):
            _fields_ = [(_n, ctypes.c_uint64) for _n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class _EXT(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BASIC),
                ("IoInfo", _IO),
                ("ProcessMemoryLimit", _SIZE_T),
                ("JobMemoryLimit", _SIZE_T),
                ("PeakProcessMemoryUsed", _SIZE_T),
                ("PeakJobMemoryUsed", _SIZE_T),
            ]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # restype/argtypes EXPLICITES — sinon un HANDLE 64 bits est tronqué à 32 bits (corruption)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        k32.SetInformationJobObject.restype = wintypes.BOOL
        k32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        k32.AssignProcessToJobObject.restype = wintypes.BOOL
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]

        job = k32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = _EXT()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k32.SetInformationJobObject(
                job, _JobObjectExtendedLimitInformation,
                ctypes.byref(info), ctypes.sizeof(info)):
            k32.CloseHandle(job)
            return None
        # proc._handle = handle ouvert par Popen (CreateProcess, droits suffisants),
        # pas de course de réutilisation de PID contrairement à OpenProcess(pid).
        if not k32.AssignProcessToJobObject(job, int(proc._handle)):
            k32.CloseHandle(job)
            return None
        return job
    except Exception:
        return None
