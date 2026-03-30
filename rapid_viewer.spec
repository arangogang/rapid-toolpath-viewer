# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# PyQt6 Qt 플랫폼 플러그인 수집 (windows, styles 등)
datas = collect_data_files('PyQt6', includes=['Qt6/plugins/**'])

# rapid_viewer 패키지 모든 서브모듈 수집 (parser, ui 등)
hidden_imports = (
    collect_submodules('rapid_viewer')
    + [
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'PyQt6.QtCore',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        # OpenGL — 향후 PyOpenGL 추가 시 활성화
        # 'OpenGL',
        # 'OpenGL.GL',
        # 'OpenGL.arrays.numpymodule',
        # 'OpenGL_accelerate',
        'numpy',
    ]
)

a = Analysis(
    ['src/rapid_viewer/main.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'PIL',
        'IPython',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='rapid_viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX 압축 — 바이러스 오탐 방지를 위해 비활성화
    console=False,      # 콘솔 창 없이 GUI 앱으로 실행
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,          # 아이콘 없음 (향후 추가 가능: icon='assets/icon.ico')
)
