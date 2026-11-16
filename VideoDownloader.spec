# Build on the target OS. PyInstaller does not cross-compile Windows from Linux.
from PyInstaller.utils.hooks import collect_all, copy_metadata

ydl_data, ydl_binaries, ydl_imports = collect_all('yt_dlp')
ejs_data, ejs_binaries, ejs_imports = collect_all('yt_dlp_ejs')
datas = ydl_data + ejs_data + copy_metadata('yt-dlp') + copy_metadata('yt-dlp-ejs')
datas += [('LICENSE', '.'), ('THIRD_PARTY.md', '.')]

a = Analysis(
    ['desktop.py'], pathex=['src'], binaries=ydl_binaries + ejs_binaries,
    datas=datas, hiddenimports=ydl_imports + ejs_imports,
    excludes=['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtPdf', 'PySide6.QtQml', 'PySide6.QtQuick'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='VideoDownloader',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='VideoDownloader')
