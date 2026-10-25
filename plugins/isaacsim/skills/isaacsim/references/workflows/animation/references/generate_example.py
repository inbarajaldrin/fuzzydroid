"""
Procedurally generate a two-part BAYONET LOCK and an animated 3D viewer.

Part A - socket : a tube with two J-slots (vertical entry -> circumferential hook)
Part B - plug   : a cylinder with a transverse through-pin

The pin drops down the entry slot (top-down), then a twist drives it along the
hook so it can't pull back out -> locked. Run:  uv run generate.py
"""
import base64
import numpy as np
import trimesh
from trimesh import creation, boolean

# ---------------------------------------------------------------- parameters (mm)
SOC_ID, SOC_OD, SOC_H = 25.0, 40.0, 45.0      # bore / outer dia / height
SLOT_DIA, SLOT_R = 7.0, 16.0                   # J-slot channel dia & radial position
Z_HOOK = 25.0                                  # height of the circumferential hook
HOOK_DEG = 40.0                                # hook sweep
PLUG_OD, PLUG_H = 24.0, 55.0
PIN_DIA, PIN_TIP_R, PIN_Z = 6.0, 18.0, 12.0    # pin dia / tip radius / height on plug
SEATED_PLUG_Z = Z_HOOK - PIN_Z                 # plug bottom Z when pin sits at hook

PIN_CLEAR = 0.7                                 # radial clearance carved around the pin


def _pin_solid(angle, z):
    """The pin (a diametral rod, +clearance) posed at a given clock angle & height.
    A single diametral rod carves BOTH 180-deg-opposed slots at once."""
    r = PIN_DIA / 2.0 + PIN_CLEAR
    length = SOC_OD + 8.0                       # spans the full diameter, through both walls
    rod = creation.cylinder(radius=r, height=length, sections=32)
    rod.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))  # -> X axis
    rod.apply_transform(trimesh.transformations.rotation_matrix(angle, [0, 0, 1]))       # clock it
    rod.apply_translation([0, 0, z])
    return rod


def pin_sweep_tool():
    """Union of the pin posed densely along its motion path:
    (1) straight DOWN the entry, then (2) TWIST along the hook.
    Subtracting this leaves a slot the pin traverses with zero collision."""
    parts = []
    for z in np.linspace(Z_HOOK - PIN_CLEAR, SOC_H + 15.0, 30):     # top-down entry
        parts.append(_pin_solid(0.0, z))
    for a in np.linspace(0.0, np.radians(HOOK_DEG), 30):            # twist along hook
        parts.append(_pin_solid(a, Z_HOOK))
    return boolean.union(parts)


def make_socket():
    tube = creation.annulus(r_min=SOC_ID / 2.0, r_max=SOC_OD / 2.0,
                            height=SOC_H, sections=96)
    tube.apply_translation([0, 0, SOC_H / 2.0])          # base at z=0
    socket = boolean.difference([tube, pin_sweep_tool()])
    socket.visual.face_colors = [150, 163, 173, 255]     # steel grey
    return socket


def make_plug():
    body = creation.cylinder(radius=PLUG_OD / 2.0, height=PLUG_H, sections=96)
    body.apply_translation([0, 0, PLUG_H / 2.0])         # bottom at z=0
    pin = creation.cylinder(radius=PIN_DIA / 2.0, height=2 * PIN_TIP_R, sections=48)
    pin.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    pin.apply_translation([0, 0, PIN_Z])                 # through-pin along X
    plug = boolean.union([body, pin])
    plug.visual.face_colors = [217, 130, 43, 255]        # warm orange
    return plug


def glb_b64(mesh):
    return base64.b64encode(mesh.export(file_type="glb")).decode()


def main():
    socket, plug = make_socket(), make_plug()
    socket.export("socket.stl")
    plug.export("plug.stl")
    print(f"socket: watertight={socket.is_watertight}  tris={len(socket.faces)}")
    print(f"plug  : watertight={plug.is_watertight}  tris={len(plug.faces)}")

    html = HTML_TEMPLATE.format(
        socket_b64=glb_b64(socket),
        plug_b64=glb_b64(plug),
        seated_z=SEATED_PLUG_Z,
        start_z=SOC_H + 20.0,
        hook_rad=np.radians(HOOK_DEG),
    )
    with open("index.html", "w") as f:
        f.write(html)
    print("wrote index.html, socket.stl, plug.stl")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Bayonet Lock - two parts</title>
<style>
  html,body{{margin:0;height:100%;background:#0f1216;color:#e7e9ec;
    font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;overflow:hidden}}
  #c{{position:fixed;inset:0}}
  #hud{{position:fixed;left:20px;top:18px;z-index:10;max-width:340px}}
  h1{{font-size:17px;margin:0 0 4px;font-weight:600;letter-spacing:.2px}}
  p{{font-size:12px;line-height:1.5;color:#9aa3ad;margin:0 0 12px}}
  .phase{{display:inline-flex;align-items:center;gap:8px;font-size:13px;
    background:#1b2027;border:1px solid #2a313b;border-radius:999px;padding:6px 13px}}
  .dot{{width:9px;height:9px;border-radius:50%;background:#d9822b;box-shadow:0 0 10px #d9822b}}
  .legend{{position:fixed;left:20px;bottom:18px;z-index:10;font-size:12px;color:#9aa3ad}}
  .legend span{{display:inline-flex;align-items:center;gap:7px;margin-right:16px}}
  .sw{{width:14px;height:14px;border-radius:3px;display:inline-block}}
  #replay{{cursor:pointer;color:#e7e9ec;text-decoration:underline;text-underline-offset:2px}}
</style>
</head>
<body>
<div id="hud">
  <h1>Bayonet lock &mdash; two parts</h1>
  <p>A round bayonet: the plug drops <b>top-down</b> so its pins ride down the entry
     slots, then a short <b>twist</b> drives them along the hooks &mdash; now it can't pull
     back out. <span id="replay">replay &#8635;</span></p>
  <div class="phase"><span class="dot" id="dot"></span><span id="ptxt">&nbsp;</span></div>
</div>
<div class="legend">
  <span><span class="sw" style="background:#96a3ad"></span>socket (J-slot)</span>
  <span><span class="sw" style="background:#d9822b"></span>plug (pin)</span>
  <span>drag to orbit &middot; scroll to zoom</span>
</div>
<canvas id="c"></canvas>

<script type="importmap">
{{ "imports": {{
  "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
  "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
}} }}
</script>
<script type="module">
import * as THREE from "three";
import {{ OrbitControls }} from "three/addons/controls/OrbitControls.js";
import {{ GLTFLoader }} from "three/addons/loaders/GLTFLoader.js";

const SEATED_Z = {seated_z};
const START_Z  = {start_z};
const HOOK_RAD = {hook_rad};

const renderer = new THREE.WebGLRenderer({{canvas:document.getElementById('c'),antialias:true}});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.setSize(innerWidth,innerHeight);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f1216);

const camera = new THREE.PerspectiveCamera(45, innerWidth/innerHeight, 0.1, 2000);
camera.position.set(95, -95, 78);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0,0,28); controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0x2a2f38, 1.15));
const key = new THREE.DirectionalLight(0xffffff, 1.5); key.position.set(60,-40,90); scene.add(key);
const fill= new THREE.DirectionalLight(0x9fb4cc, 0.6); fill.position.set(-70,50,40); scene.add(fill);

// ground grid for orientation
const grid = new THREE.GridHelper(300, 30, 0x2a313b, 0x1b2027);
grid.rotation.x = Math.PI/2; scene.add(grid);

function b64ToBuf(b64){{
  const bin = atob(b64); const u8 = new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) u8[i]=bin.charCodeAt(i);
  return u8.buffer;
}}
const loader = new GLTFLoader();
function loadGLB(b64){{
  return new Promise((res,rej)=>loader.parse(b64ToBuf(b64), '', g=>res(g.scene), rej));
}}

const SOCKET_B64 = "{socket_b64}";
const PLUG_B64   = "{plug_b64}";

let plug;   // group we animate
const clock = new THREE.Clock();
let t0 = 0;

Promise.all([loadGLB(SOCKET_B64), loadGLB(PLUG_B64)]).then(([soc, plg])=>{{
  soc.traverse(o=>{{ if(o.isMesh){{o.material.metalness=0.35;o.material.roughness=0.5;o.castShadow=true;}}}});
  plg.traverse(o=>{{ if(o.isMesh){{o.material.metalness=0.35;o.material.roughness=0.45;}}}});
  scene.add(soc);
  plug = plg; scene.add(plug);
  t0 = clock.getElapsedTime();
  animate();
}});

const PERIOD = 6.0;
const dot = document.getElementById('dot');
const ptxt = document.getElementById('ptxt');
document.getElementById('replay').onclick = ()=>{{ t0 = clock.getElapsedTime(); }};

function ease(x){{ return x<0.5 ? 2*x*x : 1-Math.pow(-2*x+2,2)/2; }}

function pose(t){{ // t in [0,1) -> {{z, rot, label}}
  let z, rot, label;
  if(t < 0.30){{                 // lower in (top-down)
    const k = ease(t/0.30);
    z = START_Z + (SEATED_Z-START_Z)*k; rot = 0; label = "1 - lower straight down";
  }} else if(t < 0.55){{          // twist to lock
    const k = ease((t-0.30)/0.25);
    z = SEATED_Z; rot = HOOK_RAD*k; label = "2 - twist to lock";
  }} else if(t < 0.72){{          // locked, hold
    z = SEATED_Z; rot = HOOK_RAD; label = "✓ locked - can't pull out";
  }} else if(t < 0.85){{          // untwist
    const k = ease((t-0.72)/0.13);
    z = SEATED_Z; rot = HOOK_RAD*(1-k); label = "3 - twist back to release";
  }} else {{                      // lift out
    const k = ease((t-0.85)/0.15);
    z = SEATED_Z + (START_Z-SEATED_Z)*k; rot = 0; label = "4 - lift straight out";
  }}
  return {{z, rot, label}};
}}

function animate(){{
  requestAnimationFrame(animate);
  const t = ((clock.getElapsedTime()-t0) % PERIOD)/PERIOD;
  const p = pose(t);
  if(plug){{ plug.position.z = p.z; plug.rotation.z = p.rot; }}
  ptxt.textContent = p.label;
  dot.style.background = p.label.startsWith("✓") ? "#3fb950" : "#d9822b";
  dot.style.boxShadow  = "0 0 10px " + (p.label.startsWith("✓") ? "#3fb950":"#d9822b");
  controls.update();
  renderer.render(scene,camera);
}}

addEventListener('resize',()=>{{
  camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth,innerHeight);
}});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
