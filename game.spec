from PyInstaller.utils.hooks import collect_all

datas = [
    ("assets", "assets"),
]

binaries = []
hiddenimports = [
    "panda3d.core",
    "panda3d.direct",
    "panda3d.physics",
    "panda3d.bullet",

    "direct.showbase.ShowBase",
    "direct.task.Task",

    "ursina",
    "ursina.prefabs",

    "PIL",
    "PIL.Image",
]

for package in [
    "ursina",
    "panda3d",
]:
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h


a = Analysis(
    [
        "main.py",
    ],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[],
)


pyz = PYZ(
    a.pure
)


exe = EXE(
    pyz,
    a.scripts,
    [],
    name="one-lucid-night",
    console=False,
    icon="assets/icon.icns",
)


coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="one-lucid-night",
)
