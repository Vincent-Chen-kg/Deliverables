
import subprocess
import sys
import os
from importlib.metadata import distributions

def ensure_requirements(requirements_file="requirements.txt"):
    if not os.path.exists(requirements_file):
        print(f"Warning: {requirements_file} not found.")
        return

    # Get set of installed package names (normalized to lowercase)
    installed = {dist.metadata["Name"].lower() for dist in distributions()}

    missing = []
    with open(requirements_file, "r") as f:
        for line in f:
            line = line.strip()
            # Ignore empty lines, comments, and flags
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Extract base package name before any specifiers (==, >=, <=, etc.)
            pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].strip().lower()
            
            if pkg_name not in installed:
                missing.append(line)
    if missing:
        print(f"Missing dependencies found: {missing}. Installing from {requirements_file}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", requirements_file
            ])
            print("Dependencies successfully installed!")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install requirements: {e}")
            sys.exit(1)