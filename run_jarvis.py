"""
JARVIS MARK III LAUNCHER
========================
Starts the Holographic 3D UI Frontend while running the full Brain microservice
and Voice Recognition / Desktop Automation system in the background.

Usage:
  python run_jarvis.py          # Holographic 3D Cybernetic UI (Frontend + Background Backend)
  python run_jarvis.py --cli    # Interactive Terminal CLI Agent
  python run_jarvis.py --brain  # Brain microservice standalone (http://localhost:8000)
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
BRAIN_DIR = ROOT_DIR / "brain"


def main():
    parser = argparse.ArgumentParser(description="JARVIS Mark III Launcher")
    parser.add_argument("--cli", action="store_true", help="Launch in Interactive Terminal CLI mode")
    parser.add_argument("--brain", action="store_true", help="Launch Brain microservice standalone")
    args = parser.parse_args()

    python_exe = sys.executable

    if args.brain:
        print("[Launcher] Starting Brain microservice standalone...")
        subprocess.run([python_exe, "run.py"], cwd=str(BRAIN_DIR))
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)

    if args.cli:
        print("[Launcher] Launching Interactive Terminal CLI...")
        subprocess.run([python_exe, "jarvis_cli.py"], cwd=str(ROOT_DIR), env=env)
    else:
        print("[Launcher] Starting Holographic 3D Frontend & Background Backend...")
        subprocess.run([python_exe, "-m", "local.app"], cwd=str(ROOT_DIR), env=env)


if __name__ == "__main__":
    main()
