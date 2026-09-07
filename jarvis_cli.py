"""
JARVIS MARK III - INTERACTIVE CLI AGENT
=======================================
Full-featured, terminal-native client for JARVIS Mark III:
- Dual-mode input: Interactive Text Prompt or Hands-Free Voice Loop.
- Rich terminal UI with styled status panels, spinners, and markdown output.
- Automatic Brain microservice orchestration (starts & stops Brain server).
- Instant offline fallback PC control if Brain is unreachable.
- Commands: /voice, /text, /mute, /unmute, /history, /status, /weather, /clear, /help, exit.

Usage:
  python jarvis_cli.py          # Interactive Text mode (with optional voice toggle)
  python jarvis_cli.py --voice  # Hands-free continuous Voice mode
  python jarvis_cli.py --mute   # Quiet mode (text only, no speech audio)
"""

import sys
import os
import time
import json
import argparse
import subprocess
import threading
from pathlib import Path
import requests

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.text import Text
from rich.prompt import Prompt
from dotenv import dotenv_values

# Project paths
ROOT_DIR = Path(__file__).parent.resolve()
BRAIN_DIR = ROOT_DIR / "brain"
LOCAL_DIR = ROOT_DIR / "local"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from local.main import process_query
from local.voice.speech_to_text import listen, set_status_callback, is_mic_muted
from local.voice.text_to_speech import speak
from local.automation.system import (
    get_system_stats, display_system_info, display_weather,
    get_weather, battery_alert, internet_status
)

# Load configuration
env_vars = dotenv_values(".env")
Username = env_vars.get("Username", "Sir")
Assistantname = env_vars.get("Assistantname", "Jarvis")
BRAIN_URL = env_vars.get("BRAIN_URL", "http://localhost:8000")

# Windows UTF-8 console output safe configuration
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(highlight=False)
_brain_subprocess = None


# ============================================================
# BRAIN MICROSERVICE LIFECYCLE
# ============================================================

def is_brain_online(timeout: float = 1.0) -> bool:
    """Check if the Brain FastAPI microservice is healthy."""
    try:
        r = requests.get(f"{BRAIN_URL}/health", timeout=timeout)
        return r.status_code == 200 and r.json().get("status") == "healthy"
    except Exception:
        return False


def start_brain_server(timeout: int = 35) -> bool:
    """Launch brain/run.py in the background if not already online."""
    global _brain_subprocess

    if is_brain_online():
        console.print("[dim green][OK] Brain microservice already running.[/dim green]")
        return True

    console.print("[yellow][*] Starting Brain microservice (FastAPI + LangChain + FAISS)...[/yellow]")
    python_exe = sys.executable

    # Launch subprocess with stdout redirected to avoid terminal clutter
    log_file = ROOT_DIR / "brain_server.log"
    log_fp = open(log_file, "w", encoding="utf-8")
    _brain_subprocess = subprocess.Popen(
        [python_exe, "run.py"],
        cwd=str(BRAIN_DIR),
        stdout=log_fp,
        stderr=subprocess.STDOUT
    )

    with console.status("[bold cyan]Warming up neural models & vector store...[/bold cyan]", spinner="dots"):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if is_brain_online():
                console.print(f"[bold green][OK] Brain microservice online at {BRAIN_URL}[/bold green]")
                return True
            # Check if process terminated prematurely
            if _brain_subprocess.poll() is not None:
                console.print(f"[bold red][FAIL] Brain server failed to start. Check {log_file} for details.[/bold red]")
                return False
            time.sleep(1.0)

    console.print(f"[bold yellow][!] Brain startup timed out. Operating in offline fallback mode.[/bold yellow]")
    return False


def shutdown_brain():
    """Cleanly terminate the spawned Brain process on CLI exit."""
    global _brain_subprocess
    if _brain_subprocess and _brain_subprocess.poll() is None:
        console.print("[dim yellow]Stopping Brain microservice...[/dim yellow]")
        _brain_subprocess.terminate()
        try:
            _brain_subprocess.wait(timeout=4)
        except Exception:
            _brain_subprocess.kill()
        console.print("[dim green]Brain microservice stopped.[/dim green]")


# ============================================================
# CHAT LOG & HISTORY
# ============================================================

def get_chat_history(limit: int = 10) -> list:
    """Read recent session history from brain database in chronological order."""
    chat_dir = BRAIN_DIR / "database" / "chats_data"
    all_messages = []
    if chat_dir.exists():
        files = sorted(
            [f for f in chat_dir.glob("*.json") if f.name != "chat_legacy_history.json"],
            key=os.path.getmtime,
            reverse=True
        )[:5]

        if not files and (chat_dir / "chat_legacy_history.json").exists():
            files = [chat_dir / "chat_legacy_history.json"]

        for cf in reversed(files):
            try:
                with open(cf, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    all_messages.extend(data.get("messages", []))
            except Exception:
                pass

    return all_messages[-limit:] if len(all_messages) > limit else all_messages


def show_chat_history(limit: int = 10):
    """Render recent chat history as a formatted Rich table."""
    messages = get_chat_history(limit)
    if not messages:
        console.print("[dim]No previous conversation history found.[/dim]")
        return

    table = Table(title=f"Recent Conversation History (Last {len(messages)} turns)", border_style="cyan")
    table.add_column("Speaker", style="bold magenta", width=14)
    table.add_column("Message", style="white")

    for msg in messages:
        role = msg.get("role", "").capitalize()
        content = msg.get("content", "").strip()
        speaker = Username if role.lower() == "user" else Assistantname
        speaker_style = "bold cyan" if role.lower() == "user" else "bold green"
        table.add_row(f"[{speaker_style}]{speaker}[/{speaker_style}]", content)

    console.print(table)


# ============================================================
# UI RENDERING HELPERS
# ============================================================

def print_banner():
    """Display JARVIS Mark III header banner."""
    banner = (
        "+----------------------------------------------------------+\n"
        "|       J.A.R.V.I.S.   M A R K   I I I   -   C L I         |\n"
        "|      Autonomous Intelligence & Desktop PC Assistant      |\n"
        "+----------------------------------------------------------+"
    )
    console.print(f"[bold cyan]{banner}[/bold cyan]")


def show_status(enable_speech: bool = True, input_mode: str = "Text", speech_enabled: bool = None):
    """Display current system and environment telemetry."""
    if speech_enabled is not None:
        enable_speech = speech_enabled
    table = Table(title="J.A.R.V.I.S. System Telemetry", border_style="blue")
    table.add_column("Matrix", style="cyan", width=20)
    table.add_column("Telemetry Status", style="green")

    brain_status = "[bold green]Online[/bold green]" if is_brain_online() else "[bold red]Offline (Local Fallback)[/bold red]"
    table.add_row("Brain Service", brain_status)
    table.add_row("User / Assistant", f"{Username} / {Assistantname}")
    table.add_row("Voice Output (TTS)", "[green]Enabled[/green]" if enable_speech else "[yellow]Muted[/yellow]")
    table.add_row("Active Input Mode", f"[bold cyan]{input_mode.upper()}[/bold cyan]")

    # Hardware stats
    try:
        sys_info = display_system_info()
        table.add_row("CPU Load", sys_info.get("cpu", "N/A"))
        table.add_row("Memory Usage", f"{sys_info.get('ram_percent', 'N/A')} ({sys_info.get('ram_details', '')})")
    except Exception:
        pass

    try:
        weather = display_weather()
        table.add_row("Weather Telemetry", f"{weather.get('city')}: {weather.get('temp')}, {weather.get('description')}")
    except Exception:
        pass

    console.print(table)


def show_help():
    """Display CLI commands help table."""
    table = Table(title="Available CLI Commands", border_style="yellow")
    table.add_column("Command", style="bold yellow", width=18)
    table.add_column("Description", style="white")

    table.add_row("/voice, /v", "Switch to continuous hands-free voice loop")
    table.add_row("/text, /t", "Switch to text prompt mode")
    table.add_row("/mute, /unmute", "Toggle Edge-TTS voice audio on or off")
    table.add_row("/history", "View recent chat conversation turns")
    table.add_row("/status", "Display system and hardware telemetry table")
    table.add_row("/weather", "Check live local environmental weather")
    table.add_row("/clear, /cls", "Clear the terminal screen")
    table.add_row("/help", "Show this command reference guide")
    table.add_row("exit, quit, bye", "Cleanly shut down J.A.R.V.I.S.")

    console.print(table)
    console.print("[dim]Or simply type any question or instruction (e.g. 'open chrome', 'remind me to call dentist at 5pm').[/dim]\n")


# ============================================================
# VOICE EXECUTION LOOP
# ============================================================

def run_voice_loop(enable_speech: bool = True):
    """Hands-free continuous microphone listening loop."""
    console.print(Panel("[bold green]Voice loop active.[/bold green] Speak your command or say [bold yellow]'switch to text'[/bold yellow] / press [bold red]Ctrl+C[/bold red] to stop.", border_style="green"))

    try:
        while True:
            with console.status("[bold cyan]Listening for speech...[/bold cyan]", spinner="bouncingBar"):
                query = listen()

            if not query:
                continue

            console.print(f"[bold cyan]{Username}:[/bold cyan] {query}")

            q_clean = query.lower().strip()
            if any(phrase in q_clean for phrase in ["switch to text", "stop listening", "text mode", "exit voice"]):
                msg = "Switching back to text mode."
                console.print(f"[bold green]{Assistantname}:[/bold green] {msg}")
                if enable_speech:
                    speak(msg)
                break

            if q_clean in ["exit", "quit", "goodbye", "shut down"]:
                msg = "Goodbye sir. System shutting down."
                console.print(f"[bold green]{Assistantname}:[/bold green] {msg}")
                if enable_speech:
                    speak(msg)
                shutdown_brain()
                sys.exit(0)

            with console.status("[bold magenta]Processing intent...[/bold magenta]", spinner="dots"):
                process_query(query, enable_speech=enable_speech)

            console.print()

    except KeyboardInterrupt:
        console.print("\n[yellow]Voice loop interrupted. Returning to text prompt.[/yellow]")


# ============================================================
# MAIN INTERACTIVE CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="JARVIS Mark III Interactive CLI Agent")
    parser.add_argument("--voice", action="store_true", help="Start directly in hands-free voice loop")
    parser.add_argument("--mute", action="store_true", help="Disable voice audio replies (silent text mode)")
    parser.add_argument("--no-brain-start", action="store_true", help="Do not automatically launch Brain microservice")
    args = parser.parse_args()

    enable_speech = not args.mute

    # Print banner
    print_banner()

    # Orchestrate Brain microservice
    if not args.no_brain_start:
        start_brain_server()
    else:
        if is_brain_online():
            console.print(f"[bold green]✔ Connected to Brain at {BRAIN_URL}[/bold green]")
        else:
            console.print(f"[bold yellow]⚠ Brain offline. Operating with local PC automation fallback.[/bold yellow]")

    console.print(f"\n[dim]Type [bold cyan]/help[/bold cyan] for commands, [bold cyan]/voice[/bold cyan] for microphone mode, or [bold cyan]exit[/bold cyan] to quit.[/dim]\n")

    # If --voice flag passed, jump directly to voice loop
    if args.voice:
        run_voice_loop(enable_speech=enable_speech)

    # Interactive Text Prompt Loop
    try:
        while True:
            try:
                prompt_label = f"[bold cyan]{Username} > [/bold cyan]"
                query = Prompt.ask(prompt_label).strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Exiting...[/dim]")
                break

            if not query:
                continue

            q_lower = query.lower()

            # Command routing
            if q_lower in ["exit", "quit", "goodbye", "/exit", "/quit"]:
                farewell = "Goodbye sir. Shutting down system."
                console.print(f"[bold green]{Assistantname}:[/bold green] {farewell}")
                if enable_speech:
                    speak(farewell)
                break

            elif q_lower in ["/help", "help", "?"]:
                show_help()
                continue

            elif q_lower in ["/voice", "/v"]:
                run_voice_loop(enable_speech=enable_speech)
                continue

            elif q_lower in ["/text", "/t"]:
                console.print("[dim]Already in interactive text mode.[/dim]")
                continue

            elif q_lower in ["/mute"]:
                enable_speech = False
                console.print("[yellow]Voice output muted (Text only mode).[/yellow]")
                continue

            elif q_lower in ["/unmute"]:
                enable_speech = True
                console.print("[green]Voice output enabled (Edge-TTS active).[/green]")
                continue

            elif q_lower in ["/history"]:
                show_chat_history()
                continue

            elif q_lower in ["/status"]:
                show_status(enable_speech=enable_speech, input_mode="Text")
                continue

            elif q_lower in ["/weather"]:
                w_str = get_weather()
                console.print(f"[cyan]{w_str}[/cyan]")
                if enable_speech:
                    speak(w_str)
                continue

            elif q_lower in ["/clear", "/cls", "cls", "clear"]:
                console.clear()
                print_banner()
                continue

            # Process query through Brain & Local automation
            with console.status(f"[bold magenta]{Assistantname} thinking...[/bold magenta]", spinner="dots"):
                process_query(query, enable_speech=enable_speech)

            console.print()

    finally:
        shutdown_brain()
        console.print("[bold cyan]J.A.R.V.I.S. session concluded.[/bold cyan]")


if __name__ == "__main__":
    main()
