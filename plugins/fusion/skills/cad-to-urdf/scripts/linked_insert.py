"""linked_insert.py  —  Fusion-side (run through the fzd-fusion bridge).

Build a station/workstation assembly of LIVE-LINKED parts (external references), correctly.
The corrected recipe after a long fight with the API:

  root.occurrences.addByInsert(dataFile, transform, isReferencedComponent)
    - 3rd arg is **isReferencedComponent**, NOT isGroundToParent.
      True  -> LIVE external link (shows in document.documentReferences, isReferencedComponent==True)
      False -> embedded local COPY
    - FAILS (returns null) if dataFile is not in the SAME PROJECT as the target doc while True.
    - Resolve the DataFile by lineage urn:  app.data.findFileById(lineage_urn)

  CRITICAL: addByInsert into an ALREADY-BUILT assembly (parts placed by transform2) triggers an
  assembly re-solve that FLINGS the existing occurrences to the origin (their transform2 -> (0,0,0);
  measureManager confirms they physically moved). So:
    -> BUILD FRESH: new doc -> saveAs into the project -> insert ALL parts at IDENTITY -> position
       each via transform2 AFTER all inserts. Nothing positioned during inserts == nothing to corrupt.
    -> (fallback) if you must add to a built assembly: record every existing occurrence's transform2
       BEFORE the insert, then re-set them AFTER (transform2 SET on an already-present occurrence is
       safe; only the INSERT corrupts).
  Verify final geometry with measureManager WORLD distance, never transform2 right after an insert
  (it reads stale / (0,0,0)).

Params — /tmp/insert_params.json:
    {
      "new_doc_name": "ur5e_rg2_camera_station",
      "folder_marker": "ur5e_rg2_station",   # insert into the folder that contains this file
      "description": "fully-linked workstation",
      "parts": [                              # inserted in order, at identity, then positioned
        {"label":"ur5e",   "lineage":"urn:...", "transform":[16 floats world matrix, cm]},
        {"label":"qc",     "lineage":"urn:...", "transform":[...]},
        {"label":"rg2",    "lineage":"urn:...", "transform":[...]}
      ]
    }
"""
import adsk.core, adsk.fusion, traceback, json

PARAMS = "/tmp/insert_params.json"

def run(context):
    app = adsk.core.Application.get()
    try:
        with open(PARAMS) as f:
            p = json.load(f)
        # find the target folder (the folder in assembly-ingest that holds folder_marker)
        folder = _find_folder(app, p["folder_marker"])
        if folder is None:
            raise RuntimeError("target folder not found")
        # new doc + saveAs into the project (required so linked inserts satisfy same-project rule)
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        doc.activate()
        doc.saveAs(p["new_doc_name"], folder, p.get("description", ""), "")
        root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
        ident = adsk.core.Matrix3D.create()
        occs = {}
        # 1) insert ALL at identity (no corruption because nothing is positioned yet)
        for part in p["parts"]:
            df = app.data.findFileById(part["lineage"])
            oc = root.occurrences.addByInsert(df, ident, True)  # True = live reference
            adsk.doEvents()
            occs[part["label"]] = oc
        # 2) position each (transform2 set is safe)
        for part in p["parts"]:
            m = adsk.core.Matrix3D.create(); m.setWithArray(part["transform"])
            occs[part["label"]].transform2 = m
        adsk.doEvents()
        # verify links
        refs = []
        dr = adsk.fusion.Design.cast(app.activeProduct).parentDocument.documentReferences
        for i in range(dr.count):
            try: refs.append(dr.item(i).dataFile.name)
            except Exception: refs.append("?")
        allref = all(occs[l].isReferencedComponent for l in occs)
        result = {"ok": True, "isRef_all": allref, "documentReferences": refs,
                  "isRef": {l: occs[l].isReferencedComponent for l in occs}}
        if allref:
            doc.save("linked assembly built")
            result["saved_version"] = doc.dataFile.versionNumber
        else:
            result["saved"] = False
        print(json.dumps(result))
    except Exception:
        print(json.dumps({"ok": False, "err": traceback.format_exc()}))


def _find_folder(app, marker):
    for h in range(app.data.dataHubs.count):
        hub = app.data.dataHubs.item(h)
        for pi in range(hub.dataProjects.count):
            prj = hub.dataProjects.item(pi)
            found = [None]
            def walk(f, depth):
                if found[0]: return
                for k in range(f.dataFiles.count):
                    if f.dataFiles.item(k).name == marker:
                        found[0] = f; return
                if depth < 3:
                    for k in range(f.dataFolders.count):
                        walk(f.dataFolders.item(k), depth + 1)
            walk(prj.rootFolder, 0)
            if found[0]:
                return found[0]
    return None
