"""Open a Fusion 360 file by navigating the project/folder tree.

Usage: Set PROJECT_NAME and FILE_PATH before executing.
FILE_PATH is a list of folder names leading to the file, then the filename.

Example: To open Default Project > UR5 > FMB > board3 > base3:
  PROJECT_NAME = "Default Project"
  FILE_PATH = ["UR5", "FMB", "board3", "base3"]

Execute in Fusion's TEXT COMMANDS (Python mode):
  exec(open('/path/to/open_file.py').read())
"""
import adsk.core

PROJECT_NAME = "Default Project"  # <-- Set this
FILE_PATH = ["UR5", "FMB", "board3", "base3"]  # <-- folders + filename

app = adsk.core.Application.get()

# Find project
proj = [p for p in app.data.dataProjects if p.name == PROJECT_NAME][0]
folder = proj.rootFolder

# Navigate folder tree (all items except the last are folders)
for folder_name in FILE_PATH[:-1]:
    folder = [f for f in folder.dataFolders if f.name == folder_name][0]

# Find and open the file (last item in path)
file_name = FILE_PATH[-1]
target = [d for d in folder.dataFiles if d.name == file_name][0]
doc = app.documents.open(target)

result = f"Opened: {doc.name}\nFrom: {PROJECT_NAME}/{'/'.join(FILE_PATH)}\n"
with open("/tmp/f360_open_result.txt", "w") as f:
    f.write(result)

print(result)
