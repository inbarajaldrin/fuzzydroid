# Canonical Isaac Lab bridge + livestream launch shape

The verified way to run an Isaac Lab standalone script with the omni.kit.mcp
bridge live inside the training process AND the WebRTC livestream viewable
from a remote viewer (verified end-to-end 2026-07-05: Cartpole sb3 training,
64 envs, stream + bridge simultaneously):

```bash
LIVESTREAM=2 OMNI_KIT_MCP_PORT=<port> <lab-venv-python> <lab-script> \
  --kit_args '--ext-folder <omni-kit-mcp>/exts --enable omni.kit.mcp --/app/livestream/publicEndpointAddress=<box-ip>'
```

Fill-ins come from recorded facts, never literals in docs or code:

| placeholder | source |
|---|---|
| `<port>` | `mcp_port` in `~/.config/fuzzydroid/isaaclab.toml` (default 9010 — distinct from a full-app's 9009 bridge on the same box) |
| `<lab-venv-python>` | `lab_python` in the state file |
| `<omni-kit-mcp>` | `omni_kit_mcp` in the state file |
| `<box-ip>` | computed at launch time (the box's reachable IP, e.g. its tailnet address) — IPs drift, so never stored |
| `<lab-script>` | the standalone script you are running (e.g. a train.py) |

## The three traps this shape avoids (each cost a debugging session)

1. **Space-form kit args only.** `--enable omni.kit.mcp` must be two tokens
   inside `--kit_args`. The `=` form (`--enable=omni.kit.mcp`) is **silently
   ignored** — no error, no bridge.
2. **`publicEndpointAddress` must be an explicit kit arg.** The `PUBLIC_IP`
   env var does NOT map through on Isaac Lab / Isaac Sim 5.0. Without the
   explicit arg the SDP (the WebRTC session description) carries
   `0.0.0.0` / no ICE candidates: the track *negotiates* but media never
   flows — a connected-looking session with no frames.
3. **NEVER export the GLIBC static-TLS tunable for Lab standalone runs.**
   `GLIBC_TUNABLES=...optional_static_tls=2097152` makes glibc carve static
   TLS out of every new thread's stack; the PhysX GPU dispatcher thread's
   `pthread_create` fails and `PxThreadImpl::start` spins on `sched_yield`
   forever — the "reset() hang". That tunable belongs ONLY to full-app
   launcher profiles (isaac-ctl's isaacsim profile). The nvjitlink
   `LD_PRELOAD` is harmless either way. Guards are per-profile and
   launcher-scoped — never venv `activate`, never blanket env files, never
   Kit config (ld.so consumes env before the process exists).

No tunable and no preload are *needed* for the canonical shape above.

## Viewing the stream

Lab training streams speak the same WebRTC protocol on the same `:49100`
signaling port as full Isaac Sim, so any workstation entry in the Isaac
Viewer app (isaacsim plugin, macOS branch) can watch a Lab run. First frame
can take longer than 8 seconds on a training launch — if the viewer's
acquire-timeout reload loop cycles without latching, give it a moment or
raise the viewer's acquire timeout.
