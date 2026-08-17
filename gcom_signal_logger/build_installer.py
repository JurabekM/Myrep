#!/usr/bin/env python3
"""
Automated Build Script for GCOM Signal Logger.
Compiles Python sources into Windows Executables via PyInstaller,
then builds a full setup installer using Inno Setup Compiler (ISCC.exe).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Force UTF-8 output formatting for Windows console compatibility
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent

def find_iscc():
    """Find Inno Setup Compiler executable."""
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    # Check PATH
    iscc_path = shutil.which("ISCC") or shutil.which("iscc")
    return iscc_path

def clean_previous_builds():
    """Clean dist and build folders."""
    print("--> Clearing old build directories...")
    for folder in ["build", "dist", "dist_installer"]:
        path = SCRIPT_DIR / folder
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    print("[OK] Cleanup finished.")

def run_pyinstaller():
    """Build executables with PyInstaller."""
    print("\n[1/3] Building GCOM_Signal_Logger.exe (GUI)...")
    cmd_gui = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "GCOM_Signal_Logger",
        str(SCRIPT_DIR / "gui_launcher.py")
    ]
    res_gui = subprocess.run(cmd_gui, cwd=SCRIPT_DIR)
    if res_gui.returncode != 0:
        print("XATO: PyInstaller GUI build failed!", file=sys.stderr)
        sys.exit(1)

    print("\n[2/3] Building GCOM_Logger_CLI.exe (CLI)...")
    cmd_cli = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name", "GCOM_Logger_CLI",
        str(SCRIPT_DIR / "logger.py")
    ]
    res_cli = subprocess.run(cmd_cli, cwd=SCRIPT_DIR)
    if res_cli.returncode != 0:
        print("XATO: PyInstaller CLI build failed!", file=sys.stderr)
        sys.exit(1)

    print("[OK] PyInstaller build completed successfully.")

def run_inno_setup():
    """Compile Inno Setup installer."""
    print("\n[3/3] Building Windows Setup EXE (Inno Setup)...")
    iscc = find_iscc()
    if not iscc:
        print("XATO: ISCC.exe (Inno Setup Compiler) topilmadi!", file=sys.stderr)
        sys.exit(1)

    print(f"ISCC path: {iscc}")
    iss_file = SCRIPT_DIR / "setup.iss"
    
    res = subprocess.run([iscc, str(iss_file)], cwd=SCRIPT_DIR)
    if res.returncode != 0:
        print("XATO: Inno Setup compilation failed!", file=sys.stderr)
        sys.exit(1)

    output_exe = SCRIPT_DIR / "dist_installer" / "GCOM_Signal_Logger_Setup.exe"
    if output_exe.exists():
        size_mb = output_exe.stat().st_size / (1024 * 1024)
        print("\n=======================================================")
        print("[SUCCESS] Setup EXE installer created!")
        print(f"File: {output_exe}")
        print(f"Size: {size_mb:.2f} MB")
        print("=======================================================\n")
    else:
        print("XATO: Output setup.exe topilmadi!", file=sys.stderr)
        sys.exit(1)

def main():
    clean_previous_builds()
    run_pyinstaller()
    run_inno_setup()

if __name__ == "__main__":
    main()
