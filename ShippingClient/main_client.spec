# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# collect_all grabs submodules + data files + binaries for reportlab
# (hiddenimports alone is not enough because reportlab ships .pfb font
#  files and uses __import__() internally for barcode/graphics modules)
rl_datas, rl_binaries, rl_hiddenimports = collect_all('reportlab')

a = Analysis(
    ['main_client.py'],
    pathex=[],
    binaries=[] + rl_binaries,
    datas=[
        ('assets/images/logo.png', 'assets/images'),
        ('icon.ico', '.'),
    ] + rl_datas,
    hiddenimports=[] + rl_hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='main_client',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
