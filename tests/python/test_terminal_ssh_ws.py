"""Tests terminal/ssh_ws — WebSocket PTY SSH (helpers + dispatch /ws/ssh/<host> + /ws/dev).

Couvre les 3 helpers (_ssh_reader, _ssh_connect, _ssh_handler) + le câblage
des 2 routes WS via init(). Tous les I/O paramiko + select + queue +
WebSocket sont mockés — pas de vraie connexion SSH.
"""
import queue as _queue
import threading
from unittest.mock import MagicMock, patch

import pytest
from terminal import ssh_ws

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def fake_cfg():
    """Config SSH fictive (clé/IP/port valides en structure, jamais utilisés)."""
    return {
        "ip":    "192.168.99.99",
        "port":  2272,
        "user":  "root",
        "key":   "/tmp/fake-key",
        "label": "fake-host",
    }


@pytest.fixture
def fake_ws():
    """WebSocket Flask-Sock mocké : .send / .receive."""
    ws = MagicMock()
    ws.send = MagicMock()
    ws.receive = MagicMock(return_value=None)
    return ws


# ── _ssh_reader ────────────────────────────────────────────────────────────


def test_ssh_reader_pousse_data_dans_queue():
    """select retourne le channel ready → recv(4096) → décode utf-8 → put en queue."""
    channel = MagicMock()
    channel.recv = MagicMock(side_effect=[b"hello", b""])  # 2e call vide = EOF
    out_queue = _queue.Queue()
    data_ready = threading.Event()
    running = [True]
    # select retourne le channel ready à chaque check
    with patch.object(ssh_ws.select, "select", return_value=([channel], [], [])):
        ssh_ws._ssh_reader(channel, out_queue, data_ready, running)
    assert running[0] is False  # EOF coupé le loop
    assert out_queue.get_nowait() == "hello"
    assert data_ready.is_set()


def test_ssh_reader_exception_arrete_le_thread():
    """Si channel.recv lance une exception → running[0] = False, exit."""
    channel = MagicMock()
    channel.recv = MagicMock(side_effect=OSError("connection reset"))
    out_queue = _queue.Queue()
    data_ready = threading.Event()
    running = [True]
    with patch.object(ssh_ws.select, "select", return_value=([channel], [], [])):
        ssh_ws._ssh_reader(channel, out_queue, data_ready, running)
    assert running[0] is False


def test_ssh_reader_pas_de_data_si_select_vide():
    """select retourne [] → pas de recv, loop ré-itère puis on coupe via running[0]=False."""
    channel = MagicMock()
    out_queue = _queue.Queue()
    data_ready = threading.Event()
    running = [False]  # exit immédiat avant le 1er check
    ssh_ws._ssh_reader(channel, out_queue, data_ready, running)
    channel.recv.assert_not_called()
    assert out_queue.empty()


# ── _ssh_connect ───────────────────────────────────────────────────────────


def test_ssh_connect_succes_retourne_client_channel(fake_cfg):
    """Connexion paramiko OK + invoke_shell OK → (client, channel, None)."""
    with patch.object(ssh_ws.paramiko, "SSHClient") as MockClient:
        mock_client = MagicMock()
        mock_channel = MagicMock()
        mock_client.invoke_shell.return_value = mock_channel
        MockClient.return_value = mock_client

        client, channel, err = ssh_ws._ssh_connect(fake_cfg)

    assert err is None
    assert client is mock_client
    assert channel is mock_channel
    mock_client.connect.assert_called_once()
    mock_client.invoke_shell.assert_called_once_with(term="xterm-256color", width=220, height=50)
    mock_channel.setblocking.assert_called_once_with(False)


def test_ssh_connect_echec_connexion_renvoie_err_msg(fake_cfg):
    """Si connect() lance → (None, None, str_de_l'exception)."""
    with patch.object(ssh_ws.paramiko, "SSHClient") as MockClient:
        mock_client = MagicMock()
        mock_client.connect.side_effect = ConnectionRefusedError("refused")
        MockClient.return_value = mock_client

        client, channel, err = ssh_ws._ssh_connect(fake_cfg)

    assert client is None
    assert channel is None
    assert "refused" in err


def test_ssh_connect_user_default_root(fake_cfg):
    """Si cfg n'a pas de 'user', la valeur par défaut est 'root'."""
    del fake_cfg["user"]
    with patch.object(ssh_ws.paramiko, "SSHClient") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        ssh_ws._ssh_connect(fake_cfg)
    kwargs = mock_client.connect.call_args.kwargs
    assert kwargs["username"] == "root"


# ── _ssh_handler ───────────────────────────────────────────────────────────


def test_ssh_handler_echec_connect_envoie_msg_erreur_au_ws(fake_ws, fake_cfg):
    """Si _ssh_connect renvoie une erreur → envoi WS message rouge + return."""
    with patch.object(ssh_ws, "_ssh_connect", return_value=(None, None, "boom")):
        ssh_ws._ssh_handler(fake_ws, fake_cfg)
    fake_ws.send.assert_called_once()
    msg = fake_ws.send.call_args[0][0]
    assert "fake-host" in msg
    assert "boom" in msg
    assert "\x1b[31m" in msg  # rouge ANSI


def test_ssh_handler_echec_connect_ignore_ws_deja_ferme(fake_cfg):
    """Si _ssh_connect KO ET ws.send lance → exception swallowed, pas de crash."""
    ws = MagicMock()
    ws.send.side_effect = Exception("ws closed")
    with patch.object(ssh_ws, "_ssh_connect", return_value=(None, None, "boom")):
        ssh_ws._ssh_handler(ws, fake_cfg)  # ne doit pas raise


def test_ssh_handler_boucle_resize_pty(fake_ws, fake_cfg):
    """Réception d'un message JSON resize → channel.resize_pty(cols, rows) appelé."""
    mock_client = MagicMock()
    mock_channel = MagicMock()
    mock_channel.get_transport.return_value.is_active.return_value = True
    # Séquence : 1 message resize, puis None pour sortir
    fake_ws.receive.side_effect = [
        '{"type":"resize","cols":120,"rows":40}',
        Exception("force exit"),  # déclenche le check transport puis sort
    ]
    mock_channel.get_transport.return_value.is_active.return_value = False  # break

    with patch.object(ssh_ws, "_ssh_connect", return_value=(mock_client, mock_channel, None)), \
         patch.object(ssh_ws.threading, "Thread"):  # neutralise le reader thread
        ssh_ws._ssh_handler(fake_ws, fake_cfg)

    mock_channel.resize_pty.assert_called_once_with(width=120, height=40)
    mock_channel.close.assert_called_once()
    mock_client.close.assert_called_once()


def test_ssh_handler_message_str_envoye_sur_channel(fake_ws, fake_cfg):
    """Réception d'un str non-resize → channel.sendall(encoded)."""
    mock_client = MagicMock()
    mock_channel = MagicMock()
    # 1 message texte puis exception transport inactive
    fake_ws.receive.side_effect = ["ls -la\n", Exception("exit")]
    mock_channel.get_transport.return_value.is_active.return_value = False

    with patch.object(ssh_ws, "_ssh_connect", return_value=(mock_client, mock_channel, None)), \
         patch.object(ssh_ws.threading, "Thread"):
        ssh_ws._ssh_handler(fake_ws, fake_cfg)

    mock_channel.sendall.assert_called_once_with(b"ls -la\n")


def test_ssh_handler_message_bytes_envoye_directement(fake_ws, fake_cfg):
    """Réception bytes → channel.sendall(bytes) sans encode."""
    mock_client = MagicMock()
    mock_channel = MagicMock()
    fake_ws.receive.side_effect = [b"\x03", Exception("exit")]  # Ctrl-C en bytes
    mock_channel.get_transport.return_value.is_active.return_value = False

    with patch.object(ssh_ws, "_ssh_connect", return_value=(mock_client, mock_channel, None)), \
         patch.object(ssh_ws.threading, "Thread"):
        ssh_ws._ssh_handler(fake_ws, fake_cfg)

    mock_channel.sendall.assert_called_once_with(b"\x03")


def test_ssh_handler_drain_queue_envoie_au_ws(fake_ws, fake_cfg):
    """Données dans la queue (du reader) → envoyées au ws via send()."""
    mock_client = MagicMock()
    mock_channel = MagicMock()
    mock_channel.get_transport.return_value.is_active.return_value = False
    fake_ws.receive.side_effect = [Exception("exit")]

    # Simule reader qui pousse 1 entrée AVANT la boucle handler du _ssh_handler.
    # On intercepte threading.Thread pour ne pas lancer le vrai reader, et on
    # dépose directement dans la queue qu'il aurait remplie.
    with patch.object(ssh_ws, "_ssh_connect", return_value=(mock_client, mock_channel, None)), \
         patch.object(ssh_ws.threading, "Thread") as MockThread:
        # On capture la queue passée au reader pour y déposer du data
        def _capture(*args, **kwargs):
            # kwargs['args'] = (channel, out_queue, data_ready, running)
            out_queue = kwargs["args"][1]
            out_queue.put("hello from reader")
            t = MagicMock()
            t.start = MagicMock()
            return t
        MockThread.side_effect = _capture

        ssh_ws._ssh_handler(fake_ws, fake_cfg)

    # ws.send a été appelé au moins une fois avec le data du reader
    sent = [c.args[0] for c in fake_ws.send.call_args_list]
    assert "hello from reader" in sent


# ── init() + routes WS ─────────────────────────────────────────────────────


def test_init_enregistre_2_routes_ws():
    """init(sock, ssh_terminal_map) appelle @sock.route deux fois (/ws/ssh/<host>, /ws/dev)."""
    sock = MagicMock()
    routes_registered = []
    def _route_decorator(path):
        routes_registered.append(path)
        return lambda fn: fn
    sock.route = _route_decorator

    ssh_ws.init(sock=sock, ssh_terminal_map={"dev1": {"ip": "1.2.3.4"}})

    assert "/ws/ssh/<host>" in routes_registered
    assert "/ws/dev" in routes_registered
    assert ssh_ws._ssh_terminal_map == {"dev1": {"ip": "1.2.3.4"}}


def test_init_route_ws_ssh_host_hote_inconnu_envoie_erreur():
    """Route /ws/ssh/<host> avec host hors map → message rouge 'Hôte inconnu : X'."""
    sock = MagicMock()
    captured = {}
    def _route_decorator(path):
        def _capture(fn):
            captured[path] = fn
            return fn
        return _capture
    sock.route = _route_decorator
    ssh_ws.init(sock=sock, ssh_terminal_map={})

    ws = MagicMock()
    captured["/ws/ssh/<host>"](ws, "unknown-host")
    ws.send.assert_called_once()
    msg = ws.send.call_args[0][0]
    assert "Hôte inconnu" in msg
    assert "unknown-host" in msg


def test_init_route_ws_ssh_host_hote_inconnu_ws_ferme_silencieux():
    """Si ws.send lance Exception (ws closed) sur host inconnu → swallowed."""
    sock = MagicMock()
    captured = {}
    def _route_decorator(path):
        def _capture(fn):
            captured[path] = fn
            return fn
        return _capture
    sock.route = _route_decorator
    ssh_ws.init(sock=sock, ssh_terminal_map={})

    ws = MagicMock()
    ws.send.side_effect = Exception("closed")
    captured["/ws/ssh/<host>"](ws, "any")  # ne doit pas raise
