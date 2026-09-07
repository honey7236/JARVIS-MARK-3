"""
JARVIS MARK III UNIFIED LAUNCHER
================================
Starts the Brain FastAPI microservice and launches the Local Desktop Client.

Usage:
  python run_jarvis.py          # Starts both Brain and Eel GUI
  python run_jarvis.py --cli    # Starts Brain and CLI/Voice Loop (no GUI)
  python run_jarvis.py --brain  # Starts Brain only (http://localhost:8000)
"""

import sys
import os
import time
import subprocess
import argparse
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).parent.resolve()
BRAIN_DIR = ROOT_DIR / "brain"
LOCAL_DIR = ROOT_DIR / "local"


def wait_for_brain(timeout: int = 45) -> bool:
    """Poll Brain /health until online or timeout."""
    print("[Launcher] Waiting for Brain to become ready at http://localhost:8000/health...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get("http://localhost:8000/health", timeout=1)
            if r.status_code == 200 and r.json().get("status") == "healthy":
                print("[Launcher] Brain microservice is online and ready!")
                return True
        except Exception:
            pass
        time.sleep(1)
    print("[Launcher] Warning: Brain did not respond within timeout.")
    return False


def main():
    parser = argparse.ArgumentParser(description="JARVIS Mark III Launcher")
    parser.add_argument("--cli", action="store_true", help="Launch in CLI/Voice mode without GUI")
    parser.add_argument("--brain", action="store_true", help="Launch Brain microservice only")
    args = parser.parse_args()

    # Determine Python executable (use current interpreter)
    python_exe = sys.executable

    if args.brain:
        print("[Launcher] Starting Brain microservice standalone...")
        subprocess.run([python_exe, "run.py"], cwd=str(BRAIN_DIR))
        return

    # Start Brain in background
    print("[Launcher] Starting Brain microservice...")
    brain_proc = subprocess.Popen([python_exe, "run.py"], cwd=str(BRAIN_DIR))

    try:
        # Wait for Brain to initialize
        if not wait_for_brain():
            print("[Launcher] Continuing launch; local client has offline fallbacks.")

        if args.cli:
            print("[Launcher] Launching Local Voice Client (CLI mode)...")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT_DIR)
            subprocess.run([python_exe, "-m", "local.main"], cwd=str(ROOT_DIR), env=env)
        else:
            print("[Launcher] Launching Local Desktop Assistant (Eel GUI)...")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT_DIR)
            subprocess.run([python_exe, "-m", "local.app"], cwd=str(ROOT_DIR), env=env)

    except KeyboardInterrupt:
        print("\n[Launcher] Shutting down...")
    finally:
        print("[Launcher] Stopping Brain microservice...")
        brain_proc.terminate()
        try:
            brain_proc.wait(timeout=5)
        except Exception:
            brain_proc.kill()
        print("[Launcher] Clean shutdown complete.")


if __name__ == "__main__":
    main()
