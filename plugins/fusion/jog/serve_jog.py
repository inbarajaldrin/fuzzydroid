#!/usr/bin/env python3
"""Robot Jog — a browser control panel that drives the ACTIVE Fusion 360 design
live through the fusion_bridge add-in: joint sliders, named poses, analytic IK
(UR arms), and gripper open/close buttons.

Runs stdlib-only:

    python3 serve_jog.py [--port 8093] [--no-palette]

By default it also opens the page as a docked palette INSIDE Fusion
(ui.palettes.add pointing at this server). The same URL works in any browser.

Robot-specific knowledge lives in profiles/*.json (bundled) and
~/.config/fuzzydroid/jog_profiles/*.json (user overrides, matched by name).
A profile "matches" when enough of the active doc's joint names contain its
joint name fragments — so an assembly doc (arm + gripper) simply matches two
profiles and renders two sections. Unmatched revolute/slider joints always get
generic sliders, so an unrigged-profile robot is still jog-able.

Angle convention: fusion_value = sign * model_value + offset  (per profile
joint). model_value is the URDF/DH-side angle in radians; Fusion revolute
values are radians, slider values cm (converted to mm at the API boundary).
"""

import argparse
import json
import math
import os
import queue
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge_client  # noqa: E402
import fusion_ops  # noqa: E402
import ik_ur  # noqa: E402

USER_PROFILE_DIR = bridge_client._config_dir() / 'jog_profiles'


# ── State ────────────────────────────────────────────────────────────────────

class JogState:
    def __init__(self):
        self.lock = threading.Lock()          # serializes bridge traffic
        self.doc = None
        self.joints = []                       # raw scan entries
        self.values = {}                       # token → native fusion value
        self.sections = []                     # profile-matched UI model
        self.profiles = []

    # ── profiles ──
    def load_profiles(self):
        profiles = {}
        for d in (HERE / 'profiles', USER_PROFILE_DIR):
            if not d.is_dir():
                continue
            for f in sorted(d.glob('*.json')):
                try:
                    prof = json.loads(f.read_text())
                    profiles[prof['name']] = prof  # user dir overrides bundled
                except Exception as e:
                    print(f'profile {f}: {e}', file=sys.stderr)
        self.profiles = list(profiles.values())

    # ── scanning / matching ──
    def scan(self):
        data = fusion_ops.scan()
        self.doc = data.get('doc')
        self.joints = [j for j in data.get('joints', []) if j.get('kind') in ('revolute', 'slider')]
        self.values = {j['token']: j.get('value', 0.0) for j in self.joints}
        self._build_sections()

    def _find_joint(self, fragment):
        frag = fragment.lower()
        for j in self.joints:
            if frag in j['name'].lower():
                return j
        return None

    def _build_sections(self):
        self.sections = []
        claimed = set()
        for prof in self.profiles:
            m = prof.get('match', {})
            hits = [f for f in m.get('any_of_joints', []) if self._find_joint(f)]
            if len(hits) < m.get('min_matches', 1):
                continue
            section = {'profile': prof['name'], 'title': prof.get('title', prof['name']),
                       'kind': prof.get('kind', 'generic')}
            if prof.get('kind') == 'arm':
                joints = []
                for spec in prof.get('joints', []):
                    j = self._find_joint(spec['fusion_match'])
                    if not j:
                        joints = []
                        break
                    claimed.add(j['token'])
                    joints.append({
                        'id': spec['id'], 'label': spec.get('label', spec['id']),
                        'token': j['token'], 'fusion_name': j['name'],
                        'sign': spec.get('sign', 1), 'offset_deg': spec.get('offset_deg', 0.0),
                        'min_deg': spec.get('min_deg', -360), 'max_deg': spec.get('max_deg', 360),
                        'value_deg': self._model_deg(j['token'], spec),
                    })
                if not joints:
                    continue
                section['joints'] = joints
                section['poses'] = prof.get('poses', {})
                section['ik'] = bool(prof.get('ik'))
            elif prof.get('kind') == 'gripper':
                drive = prof.get('drive', {})
                j = self._find_joint(drive.get('fusion_match', ''))
                if not j:
                    continue
                claimed.add(j['token'])
                # Motion-linked passives follow the drive — claim them so they
                # don't render as generic sliders.
                for frag in prof.get('passive_matches', []):
                    frag = frag.lower()
                    for pj in self.joints:
                        if frag in pj['name'].lower():
                            claimed.add(pj['token'])
                val = self.values.get(j['token'], 0.0)
                f_closed = self._drive_fusion(prof, drive['closed_model_rad'])
                f_open = self._drive_fusion(prof, drive['open_model_rad'])
                has_w = bool(prof.get('width'))
                section['drive'] = {
                    'token': j['token'], 'fusion_name': j['name'],
                    'value_rad': val,
                    'width_mm': self._gripper_width_mm(prof, val),
                    'width_offset_mm': self._gripper_width_offset_mm(prof, val),
                    'width_range_mm': [self._gripper_width_mm(prof, f_closed),
                                       self._gripper_width_mm(prof, f_open)] if has_w else None,
                }
            self.sections.append(section)

        # Everything unclaimed gets a generic slider so unknown rigs still work.
        leftovers = []
        for j in self.joints:
            if j['token'] in claimed:
                continue
            if j['kind'] == 'revolute':
                lo = math.degrees(j['min']) if j.get('min') is not None else -180.0
                hi = math.degrees(j['max']) if j.get('max') is not None else 180.0
                val, unit = math.degrees(self.values.get(j['token'], 0.0)), 'deg'
            else:
                lo = j['min'] * 10.0 if j.get('min') is not None else -100.0
                hi = j['max'] * 10.0 if j.get('max') is not None else 100.0
                val, unit = self.values.get(j['token'], 0.0) * 10.0, 'mm'
            leftovers.append({'token': j['token'], 'label': j['name'], 'kind': j['kind'],
                              'unit': unit, 'min': lo, 'max': hi, 'value': val})
        if leftovers:
            self.sections.append({'profile': None, 'title': 'Other joints',
                                  'kind': 'generic', 'joints': leftovers})

    # ── unit / convention mapping ──
    def _spec_for(self, profile_name, joint_id):
        for prof in self.profiles:
            if prof['name'] == profile_name:
                for spec in prof.get('joints', []):
                    if spec['id'] == joint_id:
                        return prof, spec
        return None, None

    def _model_deg(self, token, spec):
        """Fusion native radians → model-side degrees for one arm joint."""
        fusion_rad = self.values.get(token, 0.0)
        sign = spec.get('sign', 1)
        off = math.radians(spec.get('offset_deg', 0.0))
        return math.degrees((fusion_rad - off) / sign)

    def _fusion_rad(self, spec, model_deg):
        return spec.get('sign', 1) * math.radians(model_deg) + math.radians(spec.get('offset_deg', 0.0))

    # Drive mapping: the CAD rig's drive angle need not equal the model
    # (URDF/firmware) theta — fusion_rad = sign * model_rad + offset.
    def _drive_fusion(self, prof, model_rad):
        d = prof['drive']
        return d.get('sign', 1) * model_rad + math.radians(d.get('offset_deg', 0.0))

    def _drive_model(self, prof, fusion_rad):
        d = prof['drive']
        return (fusion_rad - math.radians(d.get('offset_deg', 0.0))) / d.get('sign', 1)

    def _gripper_width_mm(self, prof, fusion_rad):
        """OnRobot RAW width (Modbus reg 267 convention)."""
        w = prof.get('width')
        if not w or w.get('model') != 'rg2_arc':
            return None
        alpha = math.radians(w['alpha0_deg']) + self._drive_model(prof, fusion_rad)
        return w['amp_mm'] * math.sin(alpha) + w['raw_offset_mm']

    def _gripper_width_offset_mm(self, prof, fusion_rad):
        """Width WITH fingertip offset (reg 275 convention) = pad-to-pad gap."""
        raw = self._gripper_width_mm(prof, fusion_rad)
        if raw is None:
            return None
        return raw - 2 * prof['width'].get('tip_offset_mm', 0.0)

    def _gripper_theta(self, prof, raw_width_mm):
        """RAW width → fusion drive value, clamped to the open/closed extremes."""
        w = prof['width']
        arg = (raw_width_mm - w['raw_offset_mm']) / w['amp_mm']
        arg = max(-1.0, min(1.0, arg))
        model = math.asin(arg) - math.radians(w['alpha0_deg'])
        fusion = self._drive_fusion(prof, model)
        lo = self._drive_fusion(prof, prof['drive']['closed_model_rad'])
        hi = self._drive_fusion(prof, prof['drive']['open_model_rad'])
        lo, hi = min(lo, hi), max(lo, hi)
        return max(lo, min(hi, fusion))

    # ── UI snapshot for live sync ──
    def ui_snapshot(self):
        """Current display values keyed the way the page keys its widgets."""
        vals, width = {}, {}
        for sec in self.sections:
            if sec['kind'] == 'arm':
                for j in sec['joints']:
                    vals[sec['profile'] + ':' + j['id']] = self._model_deg(j['token'], j)
            elif sec['kind'] == 'gripper':
                prof = next(p for p in self.profiles if p['name'] == sec['profile'])
                val = self.values.get(sec['drive']['token'], 0.0)
                w = self._gripper_width_mm(prof, val)
                if w is not None:
                    width[sec['profile']] = {'raw': w,
                                             'offset': self._gripper_width_offset_mm(prof, val)}
            else:
                for j in sec['joints']:
                    v = self.values.get(j['token'], 0.0)
                    vals['tok:' + j['token']] = math.degrees(v) if j['kind'] == 'revolute' else v * 10.0
        fk = {s['profile']: self.fk(s['profile']) for s in self.sections if s.get('ik')}
        return {'type': 'sync', 'values': vals, 'width': width, 'fk': fk}

    # ── FK for arm sections ──
    def fk(self, profile_name):
        prof = next((p for p in self.profiles if p['name'] == profile_name), None)
        if not prof or not prof.get('ik'):
            return None
        q = []
        for spec in prof.get('joints', []):
            j = self._find_joint(spec['fusion_match'])
            if not j:
                return None
            q.append(math.radians(self._model_deg(j['token'], spec)))
        T = ik_ur.fk(q, prof['ik'].get('variant', 'ur5e'))
        rpy = ik_ur.matrix_to_rpy(T)
        return {'xyz_mm': [T[0][3] * 1000, T[1][3] * 1000, T[2][3] * 1000],
                'rpy_deg': [math.degrees(a) for a in rpy],
                'q_deg': [math.degrees(v) for v in q]}


STATE = JogState()

# ── live sync (SSE) ──────────────────────────────────────────────────────────
# Every mutation broadcasts a UI snapshot to subscribed pages, so the palette,
# external browsers, and API-driven moves (agents, curl) all stay in step.

_SUBS = []
_SUBS_LOCK = threading.Lock()


def broadcast(snapshot):
    with _SUBS_LOCK:
        for q in _SUBS:
            try:
                q.put_nowait(snapshot)
            except queue.Full:
                pass


def _poll_loop(period=4.0):
    """Catch joint changes made INSIDE Fusion (drag, Drive Joints dialog) by
    re-reading known joint values when idle and pushing a sync on change."""
    while True:
        time.sleep(period)
        with _SUBS_LOCK:
            has_subs = bool(_SUBS)
        if not has_subs or not STATE.joints:
            continue
        if not STATE.lock.acquire(blocking=False):
            continue  # a mutation is in flight — it will broadcast itself
        try:
            vals = fusion_ops.read_values(list(STATE.values.keys()), timeout=15)
            changed = any(abs(vals.get(t, v) - v) > 1e-6 for t, v in STATE.values.items())
            if changed:
                STATE.values.update(vals)
                snap = STATE.ui_snapshot()
            else:
                snap = None
        except Exception:
            snap = None  # Fusion busy — skip this tick
        finally:
            STATE.lock.release()
        if snap:
            broadcast(snap)


# ── HTTP layer ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = 'fzd-jog/1.0'

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _fail(self, e):
        self._send({'status': 'error', 'message': str(e)}, code=500)

    def log_message(self, fmt, *args):  # quiet
        pass

    def do_OPTIONS(self):
        if not self._check_origin():
            return
        self.send_response(204)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if not self._check_origin():
            return
        path = self.path.split('?')[0]
        if path == '/':
            html = (HERE / 'ui' / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        elif path == '/api/events':
            self._sse()
        elif path == '/api/state':
            try:
                with STATE.lock:
                    STATE.scan()
                    payload = {'status': 'ok', 'doc': STATE.doc, 'sections': STATE.sections}
                    for s in STATE.sections:
                        if s.get('ik'):
                            payload.setdefault('fk', {})[s['profile']] = STATE.fk(s['profile'])
                self._send(payload)
            except Exception as e:
                self._fail(e)
        else:
            self._send({'status': 'error', 'message': 'not found'}, code=404)

    def _sse(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        q = queue.Queue(maxsize=64)
        with _SUBS_LOCK:
            _SUBS.append(q)
        try:
            with STATE.lock:
                snap = STATE.ui_snapshot() if STATE.sections else None
            if snap:
                self._sse_write(snap)
            while True:
                try:
                    item = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b': keepalive\n\n')
                    self.wfile.flush()
                    continue
                self._sse_write(item)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _SUBS_LOCK:
                if q in _SUBS:
                    _SUBS.remove(q)

    def _sse_write(self, obj):
        self.wfile.write(f'data: {json.dumps(obj)}\n\n'.encode('utf-8'))
        self.wfile.flush()

    def _body(self):
        n = int(self.headers.get('Content-Length', 0))
        if not 0 <= n <= 1024 * 1024:
            raise ValueError('Request exceeds 1 MiB')
        return json.loads(self.rfile.read(n) or b'{}')

    def _check_origin(self):
        origin = self.headers.get('Origin')
        if origin is not None and origin != f'http://{self.headers.get("Host")}':
            self._send({'status': 'error', 'message': 'Cross-origin requests are not allowed'}, code=403)
            return False
        return True

    def do_POST(self):
        if not self._check_origin():
            return
        try:
            data = self._body()
            if self.path == '/api/set':
                self._api_set(data)
            elif self.path == '/api/pose':
                self._api_pose(data)
            elif self.path == '/api/ik':
                self._api_ik(data)
            elif self.path == '/api/gripper':
                self._api_gripper(data)
            elif self.path == '/api/open-palette':
                with STATE.lock:
                    r = fusion_ops.open_palette(data.get('url') or self.server.jog_url)
                self._send({'status': 'ok', **r})
            else:
                self._send({'status': 'error', 'message': 'not found'}, code=404)
        except Exception as e:
            self._fail(e)

    def _api_set(self, data):
        """sets: [{token, kind, value}] — deg for revolute, mm for slider.
        For profile arm joints pass profile+id instead of token to apply the
        sign/offset convention."""
        native = []
        with STATE.lock:
            for s in data.get('sets', []):
                if 'profile' in s and 'id' in s:
                    prof, spec = STATE._spec_for(s['profile'], s['id'])
                    j = STATE._find_joint(spec['fusion_match'])
                    tok = j['token']
                    val = STATE._fusion_rad(spec, float(s['value']))
                else:
                    tok = s['token']
                    val = float(s['value'])
                    val = math.radians(val) if s.get('kind') != 'slider' else val / 10.0
                native.append((tok, val))
            r = fusion_ops.set_joints(native)
            actual = r.get('actual', {})
            for tok, val in native:
                STATE.values[tok] = actual.get(tok, val)
            snap = STATE.ui_snapshot()
        broadcast(snap)
        self._send({'status': 'ok', **r, 'fk': snap['fk']})

    def _api_pose(self, data):
        prof = next(p for p in STATE.profiles if p['name'] == data['profile'])
        pose = prof['poses'][data['pose']]
        sets = [{'profile': prof['name'], 'id': spec['id'], 'value': pose[i]}
                for i, spec in enumerate(prof['joints'])]
        self._api_set({'sets': sets})

    def _api_ik(self, data):
        prof = next(p for p in STATE.profiles if p['name'] == data['profile'])
        variant = prof['ik'].get('variant', 'ur5e')
        xyz = [v / 1000.0 for v in data['xyz_mm']]
        rpy = [math.radians(v) for v in data['rpy_deg']]
        T = ik_ur.pose_matrix(xyz, rpy)
        sols = ik_ur.ik(T, variant)
        if not sols:
            self._send({'status': 'error', 'message': 'pose unreachable (no IK solution)'})
            return
        with STATE.lock:
            current = [math.radians(STATE._model_deg(STATE._find_joint(s['fusion_match'])['token'], s))
                       for s in prof['joints']]
        q = ik_ur.select_nearest(sols, current)
        sets = [{'profile': prof['name'], 'id': spec['id'], 'value': math.degrees(q[i])}
                for i, spec in enumerate(prof['joints'])]
        self._api_set({'sets': sets})

    def _api_gripper(self, data):
        prof = next(p for p in STATE.profiles if p['name'] == data['profile'])
        drive = prof['drive']
        action = data.get('action')
        if action == 'open':
            theta = STATE._drive_fusion(prof, drive['open_model_rad'])
        elif action == 'close':
            theta = STATE._drive_fusion(prof, drive['closed_model_rad'])
        else:
            theta = STATE._gripper_theta(prof, float(data['width_mm']))
        with STATE.lock:
            j = STATE._find_joint(drive['fusion_match'])
            r = fusion_ops.set_joints([(j['token'], theta)])
            theta_actual = r.get('actual', {}).get(j['token'], theta)
            STATE.values[j['token']] = theta_actual
            snap = STATE.ui_snapshot()
        broadcast(snap)
        self._send({'status': 'ok', **r, 'theta_rad': theta_actual,
                    'model_theta_rad': STATE._drive_model(prof, theta_actual),
                    'width_mm': STATE._gripper_width_mm(prof, theta_actual),
                    'width_offset_mm': STATE._gripper_width_offset_mm(prof, theta_actual)})


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--port', type=int, default=8093)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--no-palette', action='store_true',
                    help='do not open the docked palette inside Fusion')
    ap.add_argument('--browser', action='store_true',
                    help='also open the page in the default browser')
    args = ap.parse_args()

    STATE.load_profiles()
    print(f'profiles: {[p["name"] for p in STATE.profiles]}')

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.jog_url = f'http://127.0.0.1:{args.port}/'
    print(f'robot jog serving on {srv.jog_url}')

    threading.Thread(target=_poll_loop, daemon=True).start()

    if not args.no_palette:
        def open_pal():
            try:
                fusion_ops.open_palette(srv.jog_url)
                print('palette opened inside Fusion (docked right)')
            except Exception as e:
                print(f'could not open palette in Fusion ({e}) — '
                      f'open {srv.jog_url} in a browser instead', file=sys.stderr)
        threading.Thread(target=open_pal, daemon=True).start()
    if args.browser:
        webbrowser.open(srv.jog_url)

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
