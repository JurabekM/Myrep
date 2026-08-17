import os
import subprocess
import sys
from pathlib import Path

ISCC_PATH = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

def build():
    print("=== Step 1: Running Inno Setup ISCC ===")
    if not os.path.exists(ISCC_PATH):
        print(f"Error: ISCC not found at {ISCC_PATH}")
        sys.exit(1)
        
    cmd = [ISCC_PATH, "installer_script.iss"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print("Inno Setup compilation failed!")
        print(res.stderr)
        sys.exit(1)

    setup_exe = Path("installer_output/GCOM_Signal_Dashboard_Setup_v1.0.exe")
    if setup_exe.exists():
        size_mb = setup_exe.stat().st_size / (1024 * 1024)
        print(f"\n[SUCCESS] Windows Setup Installer created: {setup_exe.resolve()}")
        print(f"File Size: {size_mb:.2f} MB")
    else:
        print("[ERROR] Setup file was not created!")
        sys.exit(1)

if __name__ == "__main__":
    build()
