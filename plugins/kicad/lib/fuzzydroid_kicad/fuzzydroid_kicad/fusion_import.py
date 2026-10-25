"""Executed inside Fusion by handoff.py, which supplies HANDOFF_PATH."""

import hashlib
import json
from pathlib import Path

import adsk.cam
import adsk.core
import adsk.fusion

handoff_path = Path(HANDOFF_PATH)  # noqa: F821 - supplied by the trusted bridge caller
folder = handoff_path.parent
handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
step_file = folder / handoff["files"]["step"]
if hashlib.sha256(step_file.read_bytes()).hexdigest() != handoff["step_sha256"]:
    raise ValueError("STEP file no longer matches the validated handoff")
app = adsk.core.Application.get()
document = None
reused = False
for index in range(app.documents.count):
    candidate = app.documents.item(index)
    candidate_design = adsk.fusion.Design.cast(
        candidate.products.itemByProductType("DesignProductType")
    )
    if candidate_design:
        tag = candidate_design.rootComponent.attributes.itemByName(
            "fuzzydroid", "kicad_step_sha256"
        )
        if tag and tag.value == handoff["step_sha256"]:
            document = candidate
            reused = True
            break
if document is None:
    options = app.importManager.createSTEPImportOptions(str(step_file))
    options.isViewFit = True
    document = app.importManager.importToNewDocument(options)
    if document is None:
        raise RuntimeError("Fusion did not create a document for the STEP file")
document.activate()
if not reused:
    document.name = handoff["board_name"] + " - KiCad PCB"
design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
if design is None:
    raise RuntimeError("Imported document has no Fusion design product")
root = design.rootComponent
root.attributes.add("fuzzydroid", "kicad_step_sha256", handoff["step_sha256"])
if hasattr(design.unitsManager, "distanceDisplayUnits"):
    design.unitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits


def dimensions(body):
    box = body.boundingBox
    return [
        (box.maxPoint.x - box.minPoint.x) * 10,
        (box.maxPoint.y - box.minPoint.y) * 10,
        (box.maxPoint.z - box.minPoint.z) * 10,
    ]


components = [{"name": root.name, "path": root.name, "body_count": root.bRepBodies.count}]
bodies = [root.bRepBodies.item(i) for i in range(root.bRepBodies.count)]
board_bodies = []
for index in range(root.allOccurrences.count):
    occurrence = root.allOccurrences.item(index)
    components.append(
        {
            "name": occurrence.component.name,
            "path": occurrence.fullPathName,
            "body_count": occurrence.bRepBodies.count,
        }
    )
    bodies.extend(occurrence.bRepBodies.item(i) for i in range(occurrence.bRepBodies.count))
    board_prefix = handoff["board_name"].replace(" ", "_") + "_"
    if occurrence.component.name.startswith(board_prefix):
        board_bodies.extend(
            occurrence.bRepBodies.item(i) for i in range(occurrence.bRepBodies.count)
        )
expected = handoff["board"]
target = [expected["width_mm"], expected["height_mm"], expected["thickness_mm"]]
board_matches = [
    body
    for body in board_bodies
    if body.isSolid
    and all(abs(actual - wanted) < 0.05 for actual, wanted in zip(dimensions(body)[:2], target[:2]))
    and target[2] / 2 < dimensions(body)[2] <= target[2] + 0.05
]
if not board_matches:
    raise ValueError("No solid PCB core matches KiCad's board outline: " + str(target))
boxes = [body.boundingBox for body in board_bodies]
finished_dimensions = [
    (
        max(getattr(box.maxPoint, axis) for box in boxes)
        - min(getattr(box.minPoint, axis) for box in boxes)
    )
    * 10
    for axis in ["x", "y", "z"]
]
if not all(abs(actual - wanted) < 0.05 for actual, wanted in zip(finished_dimensions, target)):
    raise ValueError("Finished PCB stack does not match KiCad: " + str(finished_dimensions))


def normalize(text):
    return "".join(character.lower() for character in text if character.isalnum())


modeled = [fp for fp in expected["footprints"] if fp["models"] and not fp["dnp"]]
missing = []
available_geometry = [component for component in components if component["body_count"] > 0]
for footprint in modeled:
    tokens = [footprint["reference"], footprint["footprint"].split(":")[-1]]
    tokens.extend(Path(model).stem for model in footprint["models"])
    match = next(
        (
            component
            for component in available_geometry
            if any(
                normalize(token) in normalize(component["path"] + component["name"])
                for token in tokens
            )
        ),
        None,
    )
    if match is None:
        missing.append(footprint["reference"])
    else:
        available_geometry.remove(match)
if missing:
    raise ValueError("Component geometry missing from Fusion: " + ", ".join(missing))

fusion_folder = folder / "fusion"
fusion_folder.mkdir(exist_ok=True)
archive = fusion_folder / (step_file.stem + ".f3d")
export_options = design.exportManager.createFusionArchiveExportOptions(str(archive))
if not design.exportManager.execute(export_options):
    raise RuntimeError("Fusion archive export failed")
viewport = app.activeViewport
box = root.boundingBox
center = adsk.core.Point3D.create(
    (box.minPoint.x + box.maxPoint.x) / 2,
    (box.minPoint.y + box.maxPoint.y) / 2,
    (box.minPoint.z + box.maxPoint.z) / 2,
)
span = max(
    box.maxPoint.x - box.minPoint.x,
    box.maxPoint.y - box.minPoint.y,
    box.maxPoint.z - box.minPoint.z,
)
camera = viewport.camera
camera.isSmoothTransition = False
camera.target = center
camera.eye = adsk.core.Point3D.create(center.x + span, center.y - span, center.z + span)
camera.upVector = adsk.core.Vector3D.create(0, 0, 1)
camera.isFitView = True
viewport.camera = camera
viewport.fit()
screenshot = folder / "preview/fusion-3d.png"
if not viewport.saveAsImageFile(str(screenshot), 1600, 1100):
    raise RuntimeError("Fusion viewport capture failed")
report = {
    "validated": True,
    "document": document.name,
    "reused_document": reused,
    "board_dimensions_mm": finished_dimensions,
    "nominal_board_dimensions_mm": target,
    "dimension_tolerance_mm": 0.05,
    "dimension_error_mm": [actual - wanted for actual, wanted in zip(finished_dimensions, target)],
    "dielectric_core_dimensions_mm": dimensions(board_matches[0]),
    "board_core_is_solid": True,
    "solid_body_count": sum(body.isSolid for body in bodies),
    "components": components,
    "modeled_references_verified": [fp["reference"] for fp in modeled],
    "unmodeled_references": [fp["reference"] for fp in expected["footprints"] if not fp["models"]],
    "files": {
        "fusion_archive": str(archive.relative_to(folder)),
        "fusion_render": str(screenshot.relative_to(folder)),
        "fusion_report": "fusion/validation.json",
    },
    "note": "Mechanical STEP handoff; electrical nets and PCB authoring remain in KiCad.",
}
(fusion_folder / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
