# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Streamlit desktop build."""

import os

from PyInstaller.utils.hooks import collect_all, copy_metadata

block_cipher = None
project_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(project_dir, "app.py"), "."),
    (os.path.join(project_dir, "bridge_trainer"), "bridge_trainer"),
    (os.path.join(project_dir, ".streamlit", "config.toml"), ".streamlit"),
]
binaries = []
hiddenimports = [
    "bridge_trainer",
    "bridge_trainer.bidding",
    "bridge_trainer.cards",
    "bridge_trainer.evaluator",
    "bridge_trainer.training",
]

packages_to_collect = [
    "streamlit",
    "altair",
    "pandas",
    "pyarrow",
    "numpy",
    "PIL",
    "tornado",
    "click",
    "packaging",
    "pydeck",
    "watchdog",
    "git",
    "pytz",
    "dateutil",
]

for package_name in packages_to_collect:
    try:
        collected = collect_all(package_name)
        datas += collected[0]
        binaries += collected[1]
        hiddenimports += collected[2]
    except Exception:
        pass

for package_name in ("streamlit", "altair", "pandas", "pyarrow", "numpy"):
    try:
        datas += copy_metadata(package_name)
    except Exception:
        pass

a = Analysis(
    ["desktop_launcher.py"],
    pathex=[project_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BridgeBiddingTrainer",
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BridgeBiddingTrainer",
)
