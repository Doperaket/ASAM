import os
import sys
import hashlib
from pathlib import Path

def get_app_directory():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent

def ensure_data_directories():
    app_dir = get_app_directory()

    directories = [
        app_dir / "config",
        app_dir / "data",
        app_dir / "data" / "mafiles", 
        app_dir / "data" / "sessions",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    return app_dir

def validate_runtime_environment():
    try:
        app_dir = ensure_data_directories()

        first_run_file = app_dir / "config" / ".first_run"
        if not first_run_file.exists():
            first_run_file.write_text("AcidSAM initialized successfully")

        return True
    except Exception as e:
        print(f"Runtime validation failed: {e}")
        return False

if not validate_runtime_environment():
    sys.exit(1)