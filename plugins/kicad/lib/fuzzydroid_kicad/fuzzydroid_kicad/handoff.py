"""Validate one saved PCB revision, export fabrication data, optionally import STEP in Fusion."""

from __future__ import annotations

import hashlib
import json
import subprocess
import textwrap
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from .paths import cli_path
from .platform import config_dir, detect_os, venv_python

LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"
METADATA_CODE = """outline = pcbnew.SHAPE_POLY_SET()
if not board.GetBoardPolygonOutlines(outline, False):
    raise ValueError('A closed board outline is required')
box = outline.BBox()
result = {
    'width_mm': pcbnew.ToMM(box.GetWidth()),
    'height_mm': pcbnew.ToMM(box.GetHeight()),
    'thickness_mm': pcbnew.ToMM(board.GetDesignSettings().GetBoardThickness()),
    'copper_layers': board.GetCopperLayerCount(),
    'footprints': [
        {'reference': fp.GetReference(), 'value': fp.GetValue(),
         'footprint': fp.GetFPIDAsString(),
         'dnp': fp.IsDNP(),
         'models': [model.m_Filename for model in fp.Models()]}
        for fp in board.GetFootprints()
    ],
}
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fusion_cli() -> Path:
    state = tomllib.loads((config_dir() / "fusion.toml").read_text(encoding="utf-8"))
    python = venv_python(Path(state["venv_path"]))
    extension = ".exe" if detect_os() == "windows" else ""
    for name in ["fzd-fusion", "cli-anything-fusion"]:
        executable = python.with_name(name + extension)
        if executable.is_file():
            return executable
    raise FileNotFoundError("Run /fusion:setup before importing the PCB")


def run(
    board: str, output: str, schematic: str | None = None, import_fusion: bool = False, service=None
) -> dict:
    """Keep artifacts tied to source hashes; never order boards or save to a Fusion cloud project."""
    from .service import Service

    source = Path(board).expanduser().resolve()
    sch = Path(schematic).expanduser().resolve() if schematic else source.with_suffix(".kicad_sch")
    destination = Path(output).expanduser().resolve()
    if not source.is_file() or not sch.is_file():
        raise FileNotFoundError("Provide an existing PCB and its schematic")
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(
            "Use a new or empty output directory; existing handoffs are preserved"
        )
    destination.mkdir(parents=True, exist_ok=True)
    validation = destination / "validation"
    validation.mkdir()
    receipt = {
        "created_utc": datetime.now(UTC).isoformat(),
        "status": "in_progress",
        "commands": [],
        "files": {},
        "validation": {},
    }
    receipt_path = destination / "handoff.json"

    def persist():
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    def command(arguments, input_text=None):
        process = subprocess.run(
            [str(arg) for arg in arguments],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        receipt["commands"].append(
            {
                "argv": [str(arg) for arg in arguments],
                "returncode": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
            }
        )
        persist()
        if process.returncode:
            raise RuntimeError(
                f"Command failed ({process.returncode}): {process.stdout}\n{process.stderr}"
            )
        return process.stdout

    def kicad(*arguments):
        return command([cli_path(), *arguments])

    try:
        service = service or Service()
        service.call("ipc.save", {"board": str(source)})
        metadata = service.call("native.python", {"board": str(source), "code": METADATA_CODE})[
            "result"
        ]
        if metadata["copper_layers"] != 2:
            raise ValueError(
                "This fabrication preset is for two-layer boards; select a qualified layer preset first"
            )
        receipt["board"] = metadata
        receipt["board_name"] = source.stem
        inputs = [source, sch, source.with_suffix(".kicad_pro"), source.with_suffix(".kicad_dru")]
        receipt["source_sha256"] = {str(path): sha256(path) for path in inputs if path.is_file()}
        receipt["kicad_version"] = kicad("version").strip()
        if import_fusion:
            fusion = fusion_cli()
            ping = json.loads(command([fusion, "--json", "ping"]))
            if ping.get("status") != "ok":
                raise RuntimeError("Fusion bridge is unavailable")

        # Rule checks run against the original saved project, including its custom rules.
        kicad(
            "sch",
            "erc",
            "--exit-code-violations",
            "--format",
            "json",
            "-o",
            validation / "erc.json",
            sch,
        )
        receipt["validation"]["erc"] = "passed"
        kicad(
            "pcb",
            "drc",
            "--exit-code-violations",
            "--schematic-parity",
            "--format",
            "json",
            "-o",
            validation / "drc.json",
            source,
        )
        receipt["validation"].update(drc="passed", schematic_parity="passed")

        fabrication = destination / "fabrication"
        mechanical = destination / "mechanical"
        previews = destination / "preview"
        gerbers = fabrication / "gerbers"
        drills = fabrication / "drill"
        for folder in [gerbers, drills, mechanical, previews]:
            folder.mkdir(parents=True, exist_ok=True)
        kicad("pcb", "export", "gerbers", "-l", LAYERS, "-o", gerbers, source)
        kicad(
            "pcb",
            "export",
            "drill",
            "--format",
            "excellon",
            "--excellon-units",
            "mm",
            "--excellon-separate-th",
            "--generate-map",
            "--map-format",
            "pdf",
            "--generate-report",
            "--report-path",
            validation / "drill-report.txt",
            "-o",
            drills,
            source,
        )
        required = {".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1"}
        if not required.issubset({path.suffix for path in gerbers.iterdir()}):
            raise RuntimeError("Gerber layer set is incomplete")
        if not list(drills.glob("*.drl")):
            raise RuntimeError("No Excellon drill file was generated")
        archive = fabrication / (source.stem + "-fabrication.zip")
        step = mechanical / (source.stem + "-assembled.step")
        kicad(
            "pcb",
            "export",
            "step",
            "--subst-models",
            "--no-dnp",
            "--include-tracks",
            "--include-pads",
            "--include-zones",
            "--include-soldermask",
            "--no-extra-pad-thickness",
            "-o",
            step,
            source,
        )
        if not step.read_bytes().startswith(b"ISO-10303-21;"):
            raise RuntimeError("STEP export did not create a valid STEP carrier")
        receipt["files"]["step"] = str(step.relative_to(destination))
        receipt["step_sha256"] = sha256(step)
        kicad(
            "pcb",
            "export",
            "pdf",
            "--mode-single",
            "--scale",
            "1",
            "--black-and-white",
            "-l",
            "B.Cu,Edge.Cuts",
            "-o",
            previews / "bottom-copper-1to1.pdf",
            source,
        )
        kicad(
            "pcb",
            "render",
            "--background",
            "opaque",
            "--rotate",
            "35,0,25",
            "-o",
            previews / "kicad-3d.png",
            source,
        )
        receipt["files"].update(
            copper_pdf="preview/bottom-copper-1to1.pdf", kicad_render="preview/kicad-3d.png"
        )
        current = {path: sha256(Path(path)) for path in receipt["source_sha256"]}
        if current != receipt["source_sha256"]:
            raise RuntimeError("Source files changed during export; create a fresh handoff")
        receipt["validation"]["source_stable"] = "passed"
        receipt["artifact_sha256"] = {
            str(path.relative_to(destination)): sha256(path)
            for path in destination.rglob("*")
            if path.is_file() and path != receipt_path
        }
        persist()
        if import_fusion:
            script = Path(__file__).with_name("fusion_import.py").read_text(encoding="utf-8")
            payload = "HANDOFF_PATH = " + repr(str(receipt_path)) + "\n" + script
            code = "import json, traceback\ntry:\n" + textwrap.indent(payload, "    ")
            code += "\nexcept Exception as error:\n    print(json.dumps({'validated': False, 'error': str(error), 'traceback': traceback.format_exc()}))\n"
            response = json.loads(command([fusion, "--json", "exec", "-"], code))
            if response.get("status") != "ok":
                raise RuntimeError(
                    "Fusion returned an unsuccessful import response: " + str(response)
                )
            fusion_result = json.loads(response["output"].strip())
            if not fusion_result.get("validated"):
                raise RuntimeError("Fusion geometry validation failed: " + str(fusion_result))
            receipt["fusion"] = fusion_result
            receipt["files"].update(fusion_result["files"])
            receipt["validation"]["fusion_geometry"] = "passed"
        # Publish the fabrication ZIP only after all requested gates have passed.
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as stream:
            for path in sorted([*gerbers.iterdir(), *drills.glob("*.drl")]):
                if path.is_file():
                    stream.write(path, path.name)
        receipt["files"]["fabrication_zip"] = str(archive.relative_to(destination))
        receipt["artifact_sha256"] = {
            str(path.relative_to(destination)): sha256(path)
            for path in destination.rglob("*")
            if path.is_file() and path != receipt_path
        }
        receipt["status"] = "complete"
        persist()
        return {
            "receipt": str(receipt_path),
            "status": "complete",
            "files": receipt["files"],
            "validation": receipt["validation"],
            "fusion": receipt.get("fusion"),
        }
    except Exception as error:
        receipt.update(status="failed", error=str(error))
        persist()
        raise
