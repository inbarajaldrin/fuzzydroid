// Prune / collision / export overlay for the gkjohnson urdf-loaders viewer.
//
// Injected by serve_urdf.py alongside the built viewer bundle. It drives the
// <urdf-viewer> web component's public API (viewer.robot / camera / renderer),
// so it needs no rebuild of the minified bundle. Geometry math (picking + mesh
// overlap) runs on a locally-vendored three + three-mesh-bvh (see ./vendor/),
// fed only raw attribute arrays + world matrices read off the viewer's meshes —
// so the two three.js instances never have to share class identity.
//
// Reference: gkjohnson/urdf-loaders (<urdf-viewer>), gkjohnson/three-mesh-bvh.

import * as THREE from 'three';
import { MeshBVH } from 'three-mesh-bvh';

const GHOST_OPACITY = 0.12;   // pruned parts
const XRAY_OPACITY = 0.22;    // kept parts while x-ray is on (see internals)
const COLLIDE_COLOR = new THREE.Color(0xff3b30);
const HOVER_COLOR = new THREE.Color(0x00e5ff);

const viewer = document.querySelector('urdf-viewer');

let robot = null;
let units = [];               // prune units, one per <visual>
let unitById = new Map();
let adjacency = new Set();     // "linkA|linkB" (sorted) pairs joined by a joint
let pruneMode = false;
let xray = false;
let undoStack = [];
let redoStack = [];
let collisionPairs = [];
let collidersByLink = new Map();   // linkName -> [{ mesh, geom }] built from <collision> geometry
let linkRows = new Map();          // linkName -> tree row element (one row per link)

// ---------------------------------------------------------------- boot

function whenReady() {
    if (viewer.robot) { init(); return; }
    viewer.addEventListener('urdf-processed', () => setTimeout(init, 0), { once: false });
}

function init() {
    if (!viewer.robot) return;
    if (robot === viewer.robot) return;   // already initialised for this robot
    robot = viewer.robot;
    buildUnits();
    buildColliders();
    buildAdjacency();
    buildUI();
    refreshTree();
    status(`Loaded ${units.length} visuals across ${new Set(units.map(u => u.link)).size} links.`);
}

// ---------------------------------------------------------------- model

function buildUnits() {
    units = [];
    unitById = new Map();
    const links = robot.links || {};
    for (const linkName of Object.keys(links)) {
        const link = links[linkName];
        let visualIndex = 0;
        for (const child of link.children) {
            if (!child.isURDFVisual) continue;
            const meshes = [];
            child.traverse(o => { if (o.isMesh) meshes.push(o); });
            if (!meshes.length) { visualIndex++; continue; }
            const label = meshes.map(m => m.name).find(Boolean) || `visual ${visualIndex}`;
            const bvhs = meshes.map(m => ({ mesh: m, geom: makeBVHGeometry(m), orig: saveMaterial(m) }));
            const unit = {
                id: `${linkName}#${visualIndex}`,
                link: linkName,
                visualIndex,
                label,
                node: child,
                bvhs,
                pruned: false,
                colliding: false,
                hovered: false,
            };
            units.push(unit);
            unitById.set(unit.id, unit);
            visualIndex++;
        }
    }
}

// Collision-mesh BVHs, grouped by link. The loader runs with parseCollision=true,
// so every link's <collision> geometry is already in the scene graph (hidden) as
// URDFCollider nodes — the collision check runs on THESE, not the visual meshes,
// so it reflects the real collision model (e.g. the watertight per-link STLs).
function buildColliders() {
    collidersByLink = new Map();
    robot.traverse(n => {
        if (!(n.isURDFCollider || /Collider$/.test(n.type || ''))) return;
        const link = nearestAncestorLink(n);
        if (!link) return;
        const meshes = [];
        n.traverse(o => { if (o.isMesh && o.geometry && o.geometry.getAttribute('position')) meshes.push(o); });
        if (!meshes.length) return;
        if (!collidersByLink.has(link.name)) collidersByLink.set(link.name, []);
        for (const m of meshes) collidersByLink.get(link.name).push({ mesh: m, geom: makeBVHGeometry(m) });
    });
}

// A parallel BufferGeometry (copied arrays) with a BVH, in the mesh's LOCAL frame.
function makeBVHGeometry(mesh) {
    const src = mesh.geometry;
    const g = new THREE.BufferGeometry();
    const pos = src.getAttribute('position');
    g.setAttribute('position', new THREE.BufferAttribute(pos.array.slice(), pos.itemSize));
    const idx = src.getIndex();
    if (idx) g.setIndex(new THREE.BufferAttribute(idx.array.slice(), 1));
    g.boundsTree = new MeshBVH(g);
    return g;
}

function saveMaterial(mesh) {
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    return mats.map(m => ({
        m,
        transparent: m.transparent,
        opacity: m.opacity,
        depthWrite: m.depthWrite,
        emissive: m.emissive ? m.emissive.clone() : null,
    }));
}

function buildAdjacency() {
    adjacency = new Set();
    // Undirected link graph over the joint tree (parent link <-> child link).
    const graph = new Map();
    const addEdge = (a, b) => {
        if (!graph.has(a)) graph.set(a, new Set());
        if (!graph.has(b)) graph.set(b, new Set());
        graph.get(a).add(b); graph.get(b).add(a);
    };
    robot.traverse(n => {
        if (!(n.isURDFJoint || /Joint$/.test(n.type || ''))) return;
        const parentLink = nearestAncestorLink(n);
        const childLink = n.children.find(c => c.isURDFLink);
        if (parentLink && childLink) addEdge(parentLink.name, childLink.name);
    });
    // "Real" links = those that actually carry visual geometry (checked in the
    // collision loop). Frame-only links (tool0, flange, quick_changer_tool,
    // rg2_base_link, ...) have no meshes and never appear as a collision party.
    const real = new Set(units.map(u => u.link));
    // Adjacency = every pair of real links connected by a path that passes ONLY
    // through geometry-less frame links (the direct-joint case is the zero-hop
    // version). Such links are rigidly/kinematically the nearest geometry across
    // the joint chain, so contact between them is expected — never a collision.
    // BFS out from each real link, walking through empty links, stopping at the
    // first real link reached on each branch.
    for (const start of real) {
        const seen = new Set([start]);
        const queue = [...(graph.get(start) || [])];
        while (queue.length) {
            const cur = queue.shift();
            if (seen.has(cur)) continue;
            seen.add(cur);
            if (real.has(cur)) {
                adjacency.add(pairKey(start, cur));   // reached geometry — expected contact
                continue;                              // don't traverse THROUGH a real link
            }
            for (const nb of (graph.get(cur) || [])) if (!seen.has(nb)) queue.push(nb);
        }
    }
}

function nearestAncestorLink(node) {
    let p = node.parent;
    while (p) { if (p.isURDFLink) return p; p = p.parent; }
    return null;
}

const pairKey = (a, b) => (a < b ? `${a}|${b}` : `${b}|${a}`);

// ---------------------------------------------------------------- prune

function setPruned(unit, pruned, record = true) {
    if (unit.pruned === pruned) return;
    if (record) { undoStack.push({ id: unit.id, from: unit.pruned, to: pruned }); redoStack = []; }
    unit.pruned = pruned;
    if (unit.colliding) unit.colliding = false;
    applyUnit(unit);
    syncTreeRow(unit);
    updateCounts();
}

function setColliding(unit, on) {
    unit.colliding = on;
    applyUnit(unit);
    syncTreeRow(unit);
}

function setHovered(unit, on) {
    if (unit.hovered === on) return;
    unit.hovered = on;
    applyUnit(unit);
}

// Single source of truth for a unit's look: opacity (hover > prune > x-ray > normal)
// and emissive tint (hover cyan > collision red > original).
function applyUnit(unit) {
    for (const e of unit.bvhs) {
        const mats = Array.isArray(e.mesh.material) ? e.mesh.material : [e.mesh.material];
        mats.forEach((m, i) => {
            const o = e.orig[i];
            if (unit.hovered) { m.transparent = false; m.opacity = 1; m.depthWrite = true; }
            else if (unit.pruned) { m.transparent = true; m.opacity = GHOST_OPACITY; m.depthWrite = false; }
            else if (xray) { m.transparent = true; m.opacity = XRAY_OPACITY; m.depthWrite = false; }
            else { m.transparent = o.transparent; m.opacity = o.opacity; m.depthWrite = o.depthWrite; }

            if (o.emissive) {
                if (unit.hovered) { m.emissive.copy(HOVER_COLOR); m.emissiveIntensity = 1; }
                else if (unit.colliding && !unit.pruned) { m.emissive.copy(COLLIDE_COLOR); m.emissiveIntensity = 1; }
                else { m.emissive.copy(o.emissive); }
            }
            m.needsUpdate = true;
        });
    }
    viewer.redraw && viewer.redraw();
}

function applyAll() { for (const u of units) applyUnit(u); }

function undo() {
    const a = undoStack.pop();
    if (!a) return;
    redoStack.push(a);
    const u = unitById.get(a.id);
    u.pruned = a.from; applyUnit(u); syncTreeRow(u); updateCounts();
}

function redo() {
    const a = redoStack.pop();
    if (!a) return;
    undoStack.push(a);
    const u = unitById.get(a.id);
    u.pruned = a.to; applyUnit(u); syncTreeRow(u); updateCounts();
}

function restore() {
    clearCollisions();
    for (const u of units) if (u.pruned) { u.pruned = false; applyUnit(u); syncTreeRow(u); }
    undoStack = []; redoStack = [];
    updateCounts();
    status('Restored all visuals to the original loaded state.');
}

// ---------------------------------------------------------------- picking

function worldRayFromEvent(ev) {
    const dom = viewer.renderer.domElement;
    const rect = dom.getBoundingClientRect();
    const ndcX = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    const ndcY = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
    const cam = viewer.camera;
    const projInv = new THREE.Matrix4().fromArray(cam.projectionMatrixInverse.elements);
    const camWorld = new THREE.Matrix4().fromArray(cam.matrixWorld.elements);
    const origin = new THREE.Vector3().setFromMatrixPosition(camWorld);
    const far = new THREE.Vector3(ndcX, ndcY, 0.5).applyMatrix4(projInv).applyMatrix4(camWorld);
    const dir = far.sub(origin).normalize();
    return new THREE.Ray(origin, dir);
}

function pickUnit(ev) {
    robot.updateMatrixWorld(true);
    const ray = worldRayFromEvent(ev);
    const camPos = ray.origin.clone();
    let best = null, bestDist = Infinity;
    const world = new THREE.Matrix4();
    for (const u of units) {
        for (const e of u.bvhs) {
            if (!e.mesh.visible) continue;
            world.fromArray(e.mesh.matrixWorld.elements);
            const localRay = ray.clone().applyMatrix4(world.clone().invert());
            const hit = e.geom.boundsTree.raycastFirst(localRay, THREE.DoubleSide);
            if (!hit) continue;
            const wp = hit.point.clone().applyMatrix4(world);
            const d = wp.distanceTo(camPos);
            if (d < bestDist) { bestDist = d; best = u; }
        }
    }
    return best;
}

let downX = 0, downY = 0;
function onPointerDown(ev) { downX = ev.clientX; downY = ev.clientY; }
function onPointerUp(ev) {
    if (!pruneMode) return;
    if (ev.target !== viewer.renderer.domElement) return;
    if (Math.hypot(ev.clientX - downX, ev.clientY - downY) > 5) return;  // a drag, not a click
    const u = pickUnit(ev);
    if (!u) return;
    setPruned(u, !u.pruned);
    status(`${u.pruned ? 'Pruned' : 'Kept'} ${u.link} ▸ ${u.label}`);
    ev.stopPropagation();
}

// ---------------------------------------------------------------- collisions

function clearCollisions() {
    for (const u of units) if (u.colliding) setColliding(u, false);
    collisionPairs = [];
    renderCollisionList();
}

function checkCollisions() {
    clearCollisions();
    robot.updateMatrixWorld(true);

    // Parties to check: the real <collision> geometry (the collision model that
    // MoveIt/Isaac use). Fall back to visual meshes only if a package ships none.
    let byLink, source;
    if (collidersByLink.size) {
        byLink = collidersByLink; source = 'collision';
    } else {
        byLink = new Map(); source = 'visual';
        for (const u of units) {
            if (u.pruned) continue;
            for (const e of u.bvhs) {
                if (!e.mesh.visible) continue;
                if (!byLink.has(u.link)) byLink.set(u.link, []);
                byLink.get(u.link).push({ mesh: e.mesh, geom: e.geom });
            }
        }
    }

    const links = [...byLink.keys()];
    const hitLinks = new Set();
    for (let i = 0; i < links.length; i++) {
        for (let j = i + 1; j < links.length; j++) {
            const a = links[i], b = links[j];
            if (adjacency.has(pairKey(a, b))) continue;   // rigidly linked — expected contact
            if (geomsIntersect(byLink.get(a), byLink.get(b))) {
                collisionPairs.push([a, b]);
                hitLinks.add(a); hitLinks.add(b);
            }
        }
    }
    // Colliders are hidden, so tint the colliding links' VISUALS red for feedback.
    for (const u of units) if (hitLinks.has(u.link)) setColliding(u, true);
    renderCollisionList();
    status(collisionPairs.length
        ? `${collisionPairs.length} collision pair(s) at the current pose (${source} geometry).`
        : `No collisions at the current pose (${source} geometry).`);
}

function geomsIntersect(A, B) {
    const invA = new THREE.Matrix4();
    const wB = new THREE.Matrix4();
    for (const a of A) {
        invA.fromArray(a.mesh.matrixWorld.elements).invert();
        for (const b of B) {
            wB.fromArray(b.mesh.matrixWorld.elements);
            if (a.geom.boundsTree.intersectsGeometry(b.geom, invA.clone().multiply(wB))) return true;
        }
    }
    return false;
}

// ---------------------------------------------------------------- export

async function exportPruned() {
    const prune = units.filter(u => u.pruned).map(u => ({ link: u.link, visualIndex: u.visualIndex }));
    status(`Exporting (${prune.length} visual(s) pruned)…`);
    try {
        const res = await fetch('/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urdf: viewer.robot.urdfRobotNode ? undefined : undefined, prune }),
        });
        const data = await res.json();
        if (data.ok) {
            status(`Exported → ${data.output_dir}  (kept ${data.kept_visuals} visuals, ${data.meshes_copied} meshes)`);
        } else {
            status(`Export failed: ${data.error || 'unknown error'}`);
        }
    } catch (err) {
        status(`Export failed: ${err.message}`);
    }
}

// ---------------------------------------------------------------- UI

let el = {};

function buildUI() {
    if (el.panel) return;
    const style = document.createElement('style');
    style.textContent = `
    #prune-panel{position:fixed;top:0;right:0;width:290px;height:100%;background:rgba(20,22,26,.94);
      color:#e8e8ea;font-family:Roboto,system-ui,sans-serif;font-weight:300;font-size:13px;
      border-left:1px solid #333;display:flex;flex-direction:column;z-index:1000;box-shadow:-4px 0 16px rgba(0,0,0,.4)}
    #prune-panel h2{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#8a8f98;margin:0;padding:12px 14px 6px}
    #prune-panel .bar{display:flex;flex-wrap:wrap;gap:6px;padding:8px 12px 4px}
    #prune-panel .hint{padding:0 12px 8px;color:#7a7f88;font-size:11px;line-height:1.35;border-bottom:1px solid #2a2d33}
    #prune-panel button{background:#2b2f37;color:#e8e8ea;border:1px solid #3a3f47;border-radius:6px;
      padding:6px 9px;font-size:12px;cursor:pointer}
    #prune-panel button:hover{background:#353a44}
    #prune-panel button.active{background:#2196F3;border-color:#2196F3;color:#fff}
    #prune-panel button.warn{background:#E91E63;border-color:#E91E63;color:#fff}
    #prune-panel button:disabled{opacity:.4;cursor:default}
    #prune-tree{flex:1;overflow-y:auto;padding:4px 0}
    #prune-tree .lk{padding:6px 12px 2px;color:#9aa0aa;font-size:11px;letter-spacing:.04em}
    #prune-tree .vis{display:flex;align-items:center;gap:8px;padding:3px 12px 3px 22px;cursor:pointer}
    #prune-tree .vis:hover{background:#23262c}
    #prune-tree .vis .dot{width:8px;height:8px;border-radius:50%;background:#4caf50;flex:0 0 auto}
    #prune-tree .vis.pruned .name{color:#6a6f78;text-decoration:line-through}
    #prune-tree .vis.pruned .dot{background:#555}
    #prune-tree .vis.collide .dot{background:#ff3b30;box-shadow:0 0 6px #ff3b30}
    #prune-tree .name{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    #prune-collisions{max-height:150px;overflow-y:auto;border-top:1px solid #2a2d33;padding:6px 12px;font-size:12px}
    #prune-collisions .pair{color:#ff8a80;padding:2px 0}
    #prune-status{padding:8px 12px;border-top:1px solid #2a2d33;color:#9aa0aa;font-size:11px;min-height:32px}
    #prune-counts{padding:2px 12px 8px;color:#8a8f98;font-size:11px}
    body{margin-right:290px}
    `;
    document.head.appendChild(style);

    const panel = document.createElement('div');
    panel.id = 'prune-panel';
    panel.innerHTML = `
      <h2>Prune &amp; Collision</h2>
      <div class="bar">
        <button id="pb-mode">Prune Mode</button>
        <button id="pb-xray">X-Ray</button>
        <button id="pb-check">Check Collisions</button>
      </div>
      <div class="hint">Hover a row to spotlight that part in 3D (works through X-Ray for internal parts). Click a row to keep/prune.</div>
      <div class="bar">
        <button id="pb-undo">Undo</button>
        <button id="pb-redo">Redo</button>
        <button id="pb-restore">Restore</button>
        <button id="pb-export" class="warn">Export</button>
      </div>
      <div id="prune-counts"></div>
      <div id="prune-tree"></div>
      <div id="prune-collisions"></div>
      <div id="prune-status"></div>`;
    document.body.appendChild(panel);

    el = {
        panel,
        mode: panel.querySelector('#pb-mode'),
        xray: panel.querySelector('#pb-xray'),
        check: panel.querySelector('#pb-check'),
        undo: panel.querySelector('#pb-undo'),
        redo: panel.querySelector('#pb-redo'),
        restore: panel.querySelector('#pb-restore'),
        export: panel.querySelector('#pb-export'),
        tree: panel.querySelector('#prune-tree'),
        collisions: panel.querySelector('#prune-collisions'),
        status: panel.querySelector('#prune-status'),
        counts: panel.querySelector('#prune-counts'),
    };

    el.mode.addEventListener('click', () => {
        pruneMode = !pruneMode;
        el.mode.classList.toggle('active', pruneMode);
        status(pruneMode ? 'Prune mode ON — click a visual to keep/prune it.' : 'Prune mode off.');
    });
    el.xray.addEventListener('click', () => {
        xray = !xray;
        el.xray.classList.toggle('active', xray);
        applyAll();
        status(xray ? 'X-Ray ON — kept parts are see-through; hover a row to reveal internals.' : 'X-Ray off.');
    });
    el.check.addEventListener('click', checkCollisions);
    el.undo.addEventListener('click', undo);
    el.redo.addEventListener('click', redo);
    el.restore.addEventListener('click', restore);
    el.export.addEventListener('click', exportPruned);

    window.addEventListener('pointerdown', onPointerDown, true);
    window.addEventListener('pointerup', onPointerUp, true);
}

// The tree lists the COLLISION model — one row per link, labelled by its
// <collision> mesh (the geometry the check runs on). Pruning is done upstream in
// Fusion, so the per-<visual> color-split is no longer surfaced here. Falls back
// to visual-bearing links if a package ships no collision geometry.
function refreshTree() {
    el.tree.innerHTML = '';
    linkRows = new Map();
    const usingCollision = collidersByLink.size > 0;
    const links = (usingCollision
        ? [...collidersByLink.keys()]
        : [...new Set(units.map(u => u.link))]).sort();
    for (const link of links) {
        const cols = collidersByLink.get(link) || [];
        const names = cols.map(c => c.mesh.name).filter(Boolean);
        const sub = usingCollision
            ? (names.length ? names.join(', ') : `${cols.length} collision mesh${cols.length === 1 ? '' : 'es'}`)
            : 'no collision — visual';
        const row = document.createElement('div');
        row.className = 'vis'; row.dataset.link = link;
        row.innerHTML = `<span class="dot"></span><span class="name"></span><span class="sub"></span>`;
        row.querySelector('.name').textContent = link;
        const s = row.querySelector('.sub');
        s.textContent = sub;
        s.style.cssText = 'opacity:.5;font-size:11px;margin-left:6px';
        row.addEventListener('mouseenter', () => hoverLink(link, true));
        row.addEventListener('mouseleave', () => hoverLink(link, false));
        row.addEventListener('click', () => toggleColliderVisible(link));  // click = show/hide this link's collision mesh
        el.tree.appendChild(row);
        linkRows.set(link, row);
        syncLinkRow(link);
    }
    updateCounts();
}

// tree rows are now per-LINK; a unit change syncs its link's row.
function syncTreeRow(u) { syncLinkRow(u.link); }

function syncLinkRow(link) {
    const row = linkRows.get(link);
    if (!row) return;
    row.classList.toggle('collide', units.some(u => u.link === link && u.colliding));
    const cols = collidersByLink.get(link) || [];
    row.classList.toggle('showcol', cols.some(c => c.mesh.visible));
}

function hoverLink(link, on) {
    for (const u of units) if (u.link === link) setHovered(u, on);
}

function toggleColliderVisible(link) {
    const cols = collidersByLink.get(link) || [];
    if (!cols.length) return;
    const show = !cols.some(c => c.mesh.visible);
    for (const c of cols) c.mesh.visible = show;
    syncLinkRow(link);
}

function renderCollisionList() {
    if (!collisionPairs.length) { el.collisions.innerHTML = ''; return; }
    el.collisions.innerHTML = '<strong>Colliding link pairs</strong>' +
        collisionPairs.map(([a, b]) => `<div class="pair">${a} ✕ ${b}</div>`).join('');
}

function updateCounts() {
    if (collidersByLink.size) {
        const nCol = [...collidersByLink.values()].reduce((s, a) => s + a.length, 0);
        el.counts.textContent = `${linkRows.size} links · ${nCol} collision mesh${nCol === 1 ? '' : 'es'}`;
    } else {
        el.counts.textContent = `${linkRows.size} links · no collision geometry`;
    }
    if (el.undo) el.undo.disabled = !undoStack.length;
    if (el.redo) el.redo.disabled = !redoStack.length;
}

function status(msg) { if (el.status) el.status.textContent = msg; }

whenReady();
