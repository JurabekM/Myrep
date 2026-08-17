import os
import sys
import subprocess
from pathlib import Path

def check_and_install_requirements():
    """
    Checks if required packages are installed, if not, installs them from requirements.txt.
    """
    req_file = Path(__file__).resolve().parent / "requirements.txt"
    if not req_file.exists():
        print("requirements.txt not found. Skipping auto-install.")
        return

    try:
        print("Checking dependencies...")
        # Check if we need to install
        # We can do a quick check by trying to import a key package like PyQt6
        import PyQt6
        import g4f
        import chromadb
        print("All key dependencies seem to be installed.")
    except ImportError:
        print("Missing dependencies. Installing from requirements.txt...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
            print("Successfully installed dependencies.")
            # Restart the script to ensure new packages are picked up
            os.execv(sys.executable, ['python'] + sys.argv)
        except subprocess.CalledProcessError as e:
            print(f"Failed to install requirements: {e}")
            sys.exit(1)

def main():
    check_and_install_requirements()
    
    # Import core modules after ensuring dependencies are installed
    from core.logger import app_logger
    from core.config import APP_NAME, APP_VERSION
    from core.database import init_db
    
    app_logger.info(f"Starting {APP_NAME} v{APP_VERSION}...")
    
    # Initialize Database
    try:
        init_db()
        app_logger.info("Database initialized successfully.")
    except Exception as e:
        app_logger.error(f"Failed to initialize database: {e}")
    
    # Start UI
    app_logger.info("Initializing UI...")
    from ui.app_window import start_app
    start_app()

if __name__ == "__main__":
    main()
