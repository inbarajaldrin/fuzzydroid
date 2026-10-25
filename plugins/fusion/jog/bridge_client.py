# Minimal client for the fusion_bridge add-in socket (stdlib only).
#
# Endpoint discovery mirrors the add-in: ~/.config/fuzzydroid/fusion_bridge.json
# describes either a Unix domain socket (macOS/Linux) or TCP (Windows).

import json
import os
import socket
from pathlib import Path


def _config_dir():
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    else:
        base = Path.home() / '.config'
    return base / 'fuzzydroid'


def discover():
    """Return the endpoint dict from the discovery file, or raise."""
    path = _config_dir() / 'fusion_bridge.json'
    if not path.exists():
        raise ConnectionError(f'Bridge discovery file not found: {path} — is the '
                              f'fusion_bridge add-in running inside Fusion?')
    return json.loads(path.read_text())


def request(payload, timeout=60.0):
    """Send one JSON command to the bridge, return the parsed response dict."""
    info = discover()
    if info.get('transport') == 'tcp':
        sock = socket.create_connection((info['host'], info['port']), timeout=timeout)
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(info['path'])
    try:
        sock.sendall((json.dumps(payload) + '\n').encode('utf-8'))
        buf = b''
        while b'\n' not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                raise ConnectionError('Bridge closed the connection mid-response')
            buf += chunk
        return json.loads(buf.split(b'\n', 1)[0].decode('utf-8'))
    finally:
        sock.close()


def exec_python(code, timeout=60.0):
    """Run Python on Fusion's main thread; return captured stdout as a string.

    Raises RuntimeError when the bridge reports an error or the executed code
    printed an ERROR traceback (the bridge captures exceptions into stdout).
    """
    resp = request({'cmd': 'exec_python', 'code': code}, timeout=timeout)
    if resp.get('status') != 'ok':
        raise RuntimeError(resp.get('message', str(resp)))
    out = resp.get('output', '')
    if out.startswith('ERROR:'):
        raise RuntimeError(out)
    return out


def exec_json(code, timeout=60.0):
    """exec_python + parse the last stdout line as JSON (the code must print it)."""
    out = exec_python(code, timeout=timeout).strip()
    if not out:
        raise RuntimeError('Fusion code produced no output')
    return json.loads(out.splitlines()[-1])
