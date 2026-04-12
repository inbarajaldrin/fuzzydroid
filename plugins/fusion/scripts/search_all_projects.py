"""Recursively search all Fusion 360 projects for files matching a keyword.

Usage: Set SEARCH_TERM before executing, or leave as "" to dump all files.
Results saved to /tmp/f360_all_files.txt and /tmp/f360_matches.txt

Execute in Fusion's TEXT COMMANDS (Python mode):
  exec(open('/path/to/search_all_projects.py').read())
"""
import adsk.core

SEARCH_TERM = ""  # <-- Set this before running (e.g., "base", "assembly")

app = adsk.core.Application.get()
out = []

def scan_folder(folder, path=""):
    for f in folder.dataFiles:
        out.append(f"{path}/{f.name}")
    for sf in folder.dataFolders:
        scan_folder(sf, f"{path}/{sf.name}")

for p in app.data.dataProjects:
    try:
        scan_folder(p.rootFolder, p.name)
    except:
        out.append(f"ERROR scanning {p.name}")

with open("/tmp/f360_all_files.txt", "w") as f:
    f.write("\n".join(out))

if SEARCH_TERM:
    matches = [x for x in out if SEARCH_TERM.lower() in x.lower()]
    with open("/tmp/f360_matches.txt", "w") as f:
        f.write("\n".join(matches))
    print(f"Done! {len(out)} files, {len(matches)} matches for '{SEARCH_TERM}'")
    print("Matches: /tmp/f360_matches.txt")
else:
    print(f"Done! {len(out)} files listed")

print("All files: /tmp/f360_all_files.txt")
