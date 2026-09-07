"""
JARVIS MARK III LAUNCHER
========================
Starts the Brain FastAPI microservice and launches the CLI Agent.

Usage:
  python run_jarvis.py          # Interactive CLI Agent (Text & Voice)
  python run_jarvis.py --voice  # Continuous Voice Loop mode
  python run_jarvis.py --brain  # Brain microservice only (http://localhost:8000)
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
    parser.add_argument("--voice", action="store_true", help="Launch in hands-free voice loop mode")
    parser.add_argument("--mute", action="store_true", help="Disable voice audio responses")
    parser.add_argument("--brain", action="store_true", help="Launch Brain microservice standalone")
    args = parser.parse_args()

    python_exe = sys.executable

    if args.brain:
        print("[Launcher] Starting Brain microservice standalone...")
        subprocess.run([python_exe, "run.py"], cwd=str(BRAIN_DIR))
        return

    # Delegate to jarvis_cli.py
    cli_args = [python_exe, "jarvis_cli.py"]
    if args.voice:
        cli_args.append("--voice")
    if args.mute:
        cli_args.append("--mute")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)
    subprocess.run(cli_args, cwd=str(ROOT_DIR), env=env)


if __name__ == "__main__":
    main()
