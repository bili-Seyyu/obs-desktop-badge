# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['F:/AI Workplace/OBS桌面角标/main.py'],
    pathex=['F:/AI Workplace/OBS桌面角标/vendor'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtNetwork', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets', 'PySide6.QtPrintSupport', 'PySide6.QtSvg', 'PySide6.QtSvgWidgets', 'PySide6.QtXml', 'PySide6.QtBluetooth', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtDBus', 'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtLocation', 'PySide6.QtNfc', 'PySide6.QtPositioning', 'PySide6.QtSerialPort', 'PySide6.QtTextToSpeech', 'PySide6.QtWebSockets', 'PySide6.QtUiTools', 'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtGraphs', 'PySide6.QtQuick3D', 'PySide6.QtScxml', 'PySide6.QtStateMachine', 'PySide6.QtSensors', 'PySide6.QtRemoteObjects', 'PySide6.QtConcurrent', 'PySide6.QtWebChannel', 'PySide6.QtWebEngineQuick', 'PySide6.QtWebView'],
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
    name='OBSBadge',
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
    icon=['F:/AI Workplace/OBS桌面角标/icon.ico'],
)
