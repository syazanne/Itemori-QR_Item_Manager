from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
datas = [(str(root / name), '.') for name in ['app.py', 'LICENSE', 'THIRD_PARTY_NOTICES.md']]
datas += [(str(root / name), name) for name in ['scanner_frontend', 'desktop_ui', 'docs/licenses']]
datas += [(str(root / 'docs/USER_GUIDE.md'), 'docs')]
datas += collect_data_files('streamlit') + collect_data_files('altair') + copy_metadata('streamlit', recursive=True)
a = Analysis([str(root / 'desktop_backend.py')], pathex=[str(root)],
    binaries=[], datas=datas,
    hiddenimports=['app'] + collect_submodules('streamlit'),
    excludes=['tkinter', 'pytest', 'IPython', 'camera_reading'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='qr-item-manager-backend',
    debug=False, strip=False, upx=False, console=True, target_arch='arm64')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='qr-item-manager-backend')
