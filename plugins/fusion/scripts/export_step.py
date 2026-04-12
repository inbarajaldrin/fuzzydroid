"""Export the currently open Fusion 360 document as a STEP file.

Usage: Set OUTPUT_PATH before executing. Defaults to /tmp/<docname>.step

Execute in Fusion's TEXT COMMANDS (Python mode):
  exec(open('/path/to/export_step.py').read())
"""
import adsk.core, adsk.fusion

OUTPUT_PATH = ""  # <-- Set this, or leave empty for auto-naming to /tmp/

app = adsk.core.Application.get()
doc = app.activeDocument
design = adsk.fusion.Design.cast(app.activeProduct)
root = design.rootComponent

if not OUTPUT_PATH:
    safe_name = doc.name.replace(" ", "_").replace("/", "_")
    OUTPUT_PATH = f"/tmp/{safe_name}.step"

exportMgr = design.exportManager
opts = exportMgr.createSTEPExportOptions(OUTPUT_PATH, root)
exportMgr.execute(opts)

result = f"STEP export successful!\nFile: {OUTPUT_PATH}\nDocument: {doc.name}\n"
with open("/tmp/f360_export_result.txt", "w") as f:
    f.write(result)

print(result)
