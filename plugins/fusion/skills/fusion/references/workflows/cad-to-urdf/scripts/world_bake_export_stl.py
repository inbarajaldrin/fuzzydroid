"""world_bake_export_stl.py  —  Fusion-side (run through the fzd-fusion bridge).

The merged-per-link / neutral-mesh export primitive. Copies each requested body (or the
bodies of an occurrence) into a TEMP component at the root, which bakes their WORLD
transform into the exported geometry, renames to the link name (dodging Fusion's "(1)"
suffix), exports one STL per link, then deletes the temp component. Nothing is saved.

Run:
    cat world_bake_export_stl.py | ~/.local/share/fuzzydroid/fusion/venv/bin/fzd-fusion --json exec -

Parameters — write this JSON to /tmp/export_params.json BEFORE running (env vars do NOT
cross into the Fusion process):

    {
      "doc_name": "rg2",                     # doc to activate by name (must be open)
      "out_dir": "/abs/path/to/meshes",      # STLs written here
      "refinement": "high",                  # low | medium | high (STL mesh density)
      "links": [
        {"link_name": "cover",  "bodies": ["rg2_l_cover_link:1/plate", "...:1/pin"]},
        {"link_name": "hand",   "occurrence": "hand:1"}   # all bodies under an occurrence
      ]
    }

Body paths are matched by occurrence-path + body name substring; adapt `find_bodies` to
your naming. STL export is in MILLIMETRES (Fusion API geometry is cm) — the caller scales
to metres downstream. Reference: references/exporter-recipe.md (in this skill).
"""
import adsk.core, adsk.fusion, traceback, json, os

PARAMS = "/tmp/export_params.json"

def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        with open(PARAMS) as f:
            p = json.load(f)

        # activate the target doc by name
        doc = None
        for i in range(app.documents.count):
            d = app.documents.item(i)
            if d.name.startswith(p["doc_name"]):
                d.activate(); doc = d; break
        if doc is None:
            raise RuntimeError("doc not open: " + p["doc_name"])

        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        em = design.exportManager
        os.makedirs(p["out_dir"], exist_ok=True)

        refine = {
            "low": adsk.fusion.MeshRefinementSettings.MeshRefinementLow,
            "medium": adsk.fusion.MeshRefinementSettings.MeshRefinementMedium,
            "high": adsk.fusion.MeshRefinementSettings.MeshRefinementHigh,
        }[p.get("refinement", "medium")]

        results = []
        for link in p["links"]:
            name = link["link_name"]
            src_bodies = find_bodies(root, link)

            # temp component at root bakes the world transform into the copied geometry
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            temp = occ.component
            temp.name = "__bake_" + name
            copied = []
            for b in src_bodies:
                nb = temp.bRepBodies.add(b)   # world-baked copy into temp
                copied.append(nb)

            # rename first copy to the link name so the STL filename is clean (no "(1)")
            if copied:
                copied[0].name = name

            out = os.path.join(p["out_dir"], name + ".stl")
            opts = em.createSTLExportOptions(temp, out)   # whole temp component -> one STL
            opts.meshRefinement = refine
            opts.sendToPrintUtility = False
            em.execute(opts)
            results.append({"link": name, "bodies": len(copied), "out": out})

            occ.deleteMe()   # discard temp; NOTHING saved

        print(json.dumps({"ok": True, "exported": results}))
    except Exception:
        print(json.dumps({"ok": False, "err": traceback.format_exc()}))


def find_bodies(root, link):
    """Return the BRepBodies for a link spec: either explicit 'bodies' path substrings
    or every body under a single 'occurrence'. Matching is by occurrence fullPathName +
    body name substring — adapt to your assembly's naming."""
    out = []
    occs = root.allOccurrences
    if "occurrence" in link:
        want = link["occurrence"]
        for i in range(occs.count):
            oc = occs.item(i)
            if want in oc.fullPathName:
                for j in range(oc.bRepBodies.count):
                    out.append(oc.bRepBodies.item(j))
        return out
    # explicit body substrings like "occ:1/bodyname"
    for spec in link["bodies"]:
        occ_part, _, body_part = spec.partition("/")
        for i in range(occs.count):
            oc = occs.item(i)
            if occ_part in oc.fullPathName:
                for j in range(oc.bRepBodies.count):
                    b = oc.bRepBodies.item(j)
                    if (not body_part) or (body_part in b.name):
                        out.append(b)
    return out
