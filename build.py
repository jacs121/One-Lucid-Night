import subprocess
import tempfile
import os
import shutil
from pathlib import Path

# Files/folders to include
patterns = [
    "models/**/*",
    "textures/**/*",
    "audio/**/*",
    "*.py",
    "*.json"
]

script = "main.py"
exe_name = "one-lucid-night"

# Build the --add-data arguments
args = []
for pattern in patterns:
    for file in Path(".").glob(pattern):
        if file.as_posix().endswith("blend") or file.as_posix().endswith("blend0"):
            continue
        if file.is_file():
            dest = file.parent.as_posix()
            args.append(f'--add-data "{file};{dest}"')
        else:
            args.append(f'--add-data "{file.as_posix()};{file.as_posix()}"')

bat = f"""pyinstaller --onefile --noconfirm --windowed --clean --collect-data "ursina" --collect-data "PIL" --collect-data "numpy" --collect-data "panda3d" --collect-all "ursina" --collect-all "PIL" --collect-all "panda3d" --collect-all "numpy" --hidden-import "ursina" --hidden-import "PIL" --hidden-import "numpy" --hidden-import "panda3d"  --name "{exe_name}" {" ".join(args)} "{script}" """

print("running:", bat)
# subprocess.run(bat, shell=True)