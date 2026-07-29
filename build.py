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
exe_name = "One Lucid Night"

# Build the --add-data arguments
args = []
for pattern in patterns:
    for file in Path(".").glob(pattern):
        if file.as_posix().endswith("blend") or file.as_posix().endswith("blend0"):
            continue
        if file.is_file():
            dest = file.parent.as_posix()
            args.append(f'--add-data "{file};{dest}"')
            print(file)
        else:
            args.append(f'--add-data "{file.as_posix()};{file.as_posix()}"')

bat = f"""@echo off
pyinstaller --onefile --noconfirm --windowed --clean --collect-data "ursina" --collect-data "PIL" --collect-data "numpy" --collect-data "panda3d" --collect-all "ursina" --collect-all "PIL" --collect-all "panda3d" --collect-all "numpy" --hidden-import "ursina" --hidden-import "PIL" --hidden-import "numpy" --hidden-import "panda3d"  --name "{exe_name}" {" ".join(args)} "{script}"
"""

if os.path.exists("dist"):
    shutil.rmtree("dist")

with tempfile.NamedTemporaryFile(
    "w",
    suffix=".bat",
    delete=False,
    encoding="utf-8"
) as f:
    f.write(bat)
    bat_path = f.name

if os.path.exists("build"):
    shutil.rmtree("build")

if os.path.exists("dist"):
    shutil.rmtree("dist")

try:
    print("running:", bat)
    subprocess.run(["cmd", "/c", bat_path], check=True)
    shutil.rmtree("build")
    os.remove(f"{exe_name}.spec")
finally:
    os.remove(bat_path)

if input("start executable? (Y/n)\n>>> ").lower() == "y":
    subprocess.run([f"dist/{exe_name}.exe"], check=True)
