"""
build_helper.py - PyInstaller 打包輔助腳本
"""
import sys
import os
import subprocess
import platform
from pathlib import Path

# ─── 環境鎖定檢查 (避免 Python 3.14 等不相容版本) ───
if sys.version_info[:2] != (3, 12):
    print(f"\n[❌ 錯誤] 環境不相容！")
    print(f"目前使用的 Python 版本為: {platform.python_version()}")
    print(f"本專案嚴格要求使用 Python 3.12.x 進行打包，以避免 C-ABI 與 PyQt6 的相容性問題。")
    print(f"請切換至 Python 3.12 的虛擬環境後再試。")
    sys.exit(1)

HERE = Path(__file__).parent
APP_NAME = "支票查詢系統"

SPEC_TEMPLATE = """# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None

fitz_datas, fitz_binaries, fitz_hiddenimports = collect_all('fitz')

a = Analysis(
    ['{main_py}'],
    pathex=['{here_dir}'],
    binaries=fitz_binaries,
    datas=fitz_datas + [
        ('{config_py}', '.'),
        ('{core_dir}', 'core'),
        ('{ui_dir}', 'ui'),
    ],
    hiddenimports=fitz_hiddenimports + [
        'config',
        'core', 'core.ocr_engine', 'core.indexer', 'core.searcher', 'core.printer',
        'ui', 'ui.main_window', 'ui.settings_dialog', 'ui.workers',
        'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtGui', 'PyQt6.QtCore',
        'PyQt6.QtPrintSupport', 'PyQt6.sip',
        'winocr', 'asyncio',
        'PIL', 'PIL.Image', 'PIL.ImageEnhance', 'PIL.ImageFilter',
        'fitz', 'numpy',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{app_name}',
    debug={debug},
    strip=False,
    upx=False,
    console={console},
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='{app_name}',
)
"""

def write_spec(debug_mode=True):
    spec_text = SPEC_TEMPLATE.format(
        main_py=str(HERE / 'main.py').replace('\\', '/'),
        here_dir=str(HERE).replace('\\', '/'),
        config_py=str(HERE / 'config.py').replace('\\', '/'),
        core_dir=str(HERE / 'core').replace('\\', '/'),
        ui_dir=str(HERE / 'ui').replace('\\', '/'),
        app_name=APP_NAME,
        debug=debug_mode,
        console=debug_mode,
    )
    spec_path = HERE / 'check_finder.spec'
    spec_path.write_text(spec_text, encoding='utf-8')
    print(f'[OK] spec: {spec_path}')

def install_packages():
    packages = ["PyQt6", "PyMuPDF", "winocr", "Pillow", "numpy", "pyinstaller"]
    print("[install] Installing packages...")
    result = subprocess.run([sys.executable, "-m", "pip", "install"] + packages)
    if result.returncode != 0:
        print("[ERROR] Package install failed")
        sys.exit(1)
    print("[OK] Packages installed")

def build(debug_mode=True):
    write_spec(debug_mode=debug_mode)
    print("\n[build] Running PyInstaller...")
    os.chdir(HERE)
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "check_finder.spec", "--clean"],
        cwd=str(HERE)
    )
    if result.returncode != 0:
        print("\n[ERROR] Build failed")
        sys.exit(1)

    dist_dir = HERE / "dist" / APP_NAME
    exe_path = dist_dir / f"{APP_NAME}.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        total = sum(f.stat().st_size for f in dist_dir.rglob('*') if f.is_file())
        mode = "DEBUG" if debug_mode else "RELEASE"
        print(f"\n[OK] Build complete! ({mode})")
        print(f"  Folder: {dist_dir}")
        print(f"  EXE: {size_mb:.1f} MB, Total: {total / 1024 / 1024:.1f} MB")
    else:
        print("\n[WARNING] exe not found")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python build_helper.py install   Install packages")
        print("  python build_helper.py build     Debug build (with console)")
        print("  python build_helper.py release   Release build (no console)")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "install":
        install_packages()
    elif cmd == "build":
        install_packages()
        build(debug_mode=True)
    elif cmd == "release":
        install_packages()
        build(debug_mode=False)
    else:
        print(f"[ERROR] Unknown: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()