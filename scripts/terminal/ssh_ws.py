"""WebSocket PTY SSH — terminaux interactifs xterm.js.

Extrait de jarvis.py étape 30 (2026-05-23). Fournit 2 routes WebSocket
Flask-Sock pour ouvrir des terminaux SSH bidirectionnels (paramiko
`invoke_shell()` PTY xterm-256color + queue thread reader + receive loop) :

- `/ws/ssh/<host>` : terminal SSH générique vers tout host de SSH_TERMINAL_MAP
- `/ws/dev`        : alias direct du terminal CODE srv-dev-1 (dev1)

Les helpers internes :
- `_ssh_reader`  : thread daemon qui lit le channel SSH et pousse en queue
- `_ssh_connect` : ouvre la connexion + invoke_shell PTY (timeout 10 s)
- `_ssh_handler` : boucle bidirectionnelle WS ↔ channel, gère resize PTY

DI : `init(sock, ssh_terminal_map)` enregistre les 2 routes WS via
`@sock.route(...)` au moment du câblage côté jarvis.py.
"""
import json
import queue as _queue
import select
import threading

import paramiko

_ssh_terminal_map: dict = {}


def _ssh_reader(channel, out_queue, data_ready, running) -> None:
    """Lit le channel SSH et pousse dans la queue (thread dédié)."""
    while running[0]:
        try:
            r, _, _ = select.select([channel], [], [], 0.1)
            if r:
                data = channel.recv(4096)
                if not data:
                    running[0] = False
                    break
                out_queue.put(data.decode("utf-8", errors="replace"))
                data_ready.set()
        except Exception:
            running[0] = False
            break


def _ssh_connect(cfg: dict):
    """Établit une connexion SSH PTY — retourne (client, channel, None) ou (None, None, err_msg)."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname     = cfg["ip"],
            port         = cfg["port"],
            username     = cfg.get("user", "root"),
            key_filename = cfg["key"],
            timeout      = 10,
            look_for_keys= False,
            allow_agent  = False,
        )
    except Exception as exc:
        return None, None, str(exc)
    channel = client.invoke_shell(term="xterm-256color", width=220, height=50)
    channel.setblocking(False)
    return client, channel, None


def _ssh_handler(ws, cfg: dict) -> None:
    """Corps commun WebSocket PTY SSH — terminal interactif (xterm.js)."""
    client, channel, err = _ssh_connect(cfg)
    if err:
        try:
            ws.send(f"\r\n\x1b[31m✗ SSH {cfg['label']} impossible : {err}\x1b[0m\r\n")
        except Exception:
            pass  # WebSocket déjà fermé côté client
        return

    running    = [True]
    out_queue  = _queue.Queue()
    data_ready = threading.Event()

    threading.Thread(target=_ssh_reader, args=(channel, out_queue, data_ready, running), daemon=True).start()

    try:
        while running[0]:
            while not out_queue.empty():
                try:
                    ws.send(out_queue.get_nowait())
                except Exception:
                    running[0] = False
                    break
            if not running[0]:
                break
            data_ready.clear()
            try:
                msg = ws.receive(timeout=0.3)
            except Exception:
                tr = channel.get_transport()
                if not tr or not tr.is_active() or not running[0]:
                    break
                data_ready.wait(timeout=0.05)
                continue
            if msg is None:
                continue
            if isinstance(msg, str) and msg.startswith('{"type":"resize"'):
                try:
                    _r = json.loads(msg)
                    channel.resize_pty(width=int(_r["cols"]), height=int(_r["rows"]))
                except Exception:
                    pass  # channel déjà fermé ou PTY non supporté
            else:
                try:
                    channel.sendall(msg if isinstance(msg, bytes) else msg.encode())
                except Exception:
                    break
    finally:
        running[0] = False
        try:
            channel.close()
        except Exception:
            pass  # channel may already be closed — ignore
        try:
            client.close()
        except Exception:
            pass  # client may already be closed — ignore


def init(*, sock, ssh_terminal_map: dict) -> None:
    """Enregistre les 2 routes WebSocket sur le `sock` Flask-Sock fourni."""
    global _ssh_terminal_map
    _ssh_terminal_map = ssh_terminal_map

    @sock.route("/ws/ssh/<host>")
    def ws_ssh_host(ws, host):
        """WebSocket PTY SSH — terminal générique vers tout hôte de _ssh_terminal_map."""
        cfg = _ssh_terminal_map.get(host)
        if cfg is None:
            try:
                ws.send(f"\r\n\x1b[31m✗ Hôte inconnu : {host}\x1b[0m\r\n")
            except Exception:
                pass  # WebSocket déjà fermé côté client
            return
        _ssh_handler(ws, cfg)

    @sock.route("/ws/dev")
    def ws_dev(ws):
        """WebSocket PTY SSH — terminal CODE srv-dev-1 (alias /ws/ssh/dev1)."""
        _ssh_handler(ws, _ssh_terminal_map["dev1"])
