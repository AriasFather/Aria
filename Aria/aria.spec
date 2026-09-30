# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH).resolve()
datas = []

# Keep source files alongside the frozen app: the host manager copies them to
# isolated child-instance folders when users connect hosted instances.
for path in ROOT.iterdir():
    if path.is_file() and path.suffix in {".py", ".html"}:
        datas.append((str(path), "."))

for directory in ("cogs", "core", "static", "utils", "web_ui"):
    path = ROOT / directory
    if path.is_dir():
        datas.append((str(path), directory))

hiddenimports = []
for package in ("aiohttp", "curl_cffi", "flask", "pymongo", "websocket", "websockets"):
    hiddenimports += collect_submodules(package)

a = Analysis(
    [str(ROOT / "aria_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Aria",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Aria",
)