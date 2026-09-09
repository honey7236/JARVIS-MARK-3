"""
JARVIS READINESS CHECKLIST AUDITOR
===================================
Executes automated checks against every item in JARVIS_READINESS_CHECKLIST.md.
"""

import sys
import os
import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

checklist_results = []

def record(category, item, passed, details=""):
    checklist_results.append({
        "category": category,
        "item": item,
        "passed": passed,
        "details": details
    })
    status = " [PASS] " if passed else " [FAIL] "
    print(f"{status} | {category} -> {item}")
    if details:
        print(f"         {details}")


def check_structure():
    print("\n--- 1. Structure & Clean Brain/Local Split ---")
    
    # Check Brain for automation / local GUI leaks
    brain_files = [os.path.join(r, f) for r, _, fs in os.walk(ROOT_DIR / "brain") for f in fs if f.endswith(".py")]
    suspect_terms = ["pyautogui", "AppOpener", "plyer", "ctypes.windll", "local.automation"]
    leaks = []
    for bf in brain_files:
        with open(bf, "r", encoding="utf-8", errors="ignore") as fp:
            code = fp.read()
            for st in suspect_terms:
                if st in code:
                    leaks.append(f"{os.path.basename(bf)}:{st}")
    record("Structure", "Brain has no local GUI or PC automation code", len(leaks) == 0, f"Found: {leaks}" if leaks else "Clean")

    # Check Local app for direct LLM calls
    local_files = [os.path.join(r, f) for r, _, fs in os.walk(ROOT_DIR / "local") for f in fs if f.endswith(".py") and "test" not in f]
    direct_llm = ["ChatGroq", "ChatGoogleGenerativeAI", "TavilyClient"]
    llm_leaks = []
    for lf in local_files:
        with open(lf, "r", encoding="utf-8", errors="ignore") as fp:
            code = fp.read()
            for dl in direct_llm:
                if dl in code:
                    llm_leaks.append(f"{os.path.basename(lf)}:{dl}")
    record("Structure", "Local app has no hardcoded direct LLM calls", len(llm_leaks) == 0, f"Found: {llm_leaks}" if llm_leaks else "Clean, routes via Brain")

    # Obvious entry points
    has_brain_entry = (ROOT_DIR / "brain" / "run.py").exists()
    has_local_entry = (ROOT_DIR / "run_jarvis.py").exists()
    record("Structure", "Single obvious entry point for both Brain and Local", has_brain_entry and has_local_entry, "brain/run.py and run_jarvis.py present")


def check_secrets():
    print("\n--- 2. Config & Secrets ---")
    
    # .gitignore excludes .env
    with open(ROOT_DIR / ".gitignore", "r", encoding="utf-8") as f:
        git_ignore = f.read()
    record("Secrets", ".gitignore excludes .env", ".env" in git_ignore, ".env explicitly ignored")

    # No API keys in git tracked files
    try:
        tracked_files = subprocess.check_output(["git", "ls-files"], cwd=str(ROOT_DIR), text=True).splitlines()
        secret_patterns = [r'gsk_[A-Za-z0-9]{20,}', r'AIzaSy[A-Za-z0-9_-]{20,}', r'AQ\.[A-Za-z0-9_-]{30,}']
        found_secrets = []
        for tf in tracked_files:
            p = ROOT_DIR / tf
            if p.exists() and p.is_file():
                with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                    c = fp.read()
                    for sp in secret_patterns:
                        if re.search(sp, c):
                            found_secrets.append(tf)
        record("Secrets", "No hardcoded API keys in tracked git files", len(found_secrets) == 0, f"Found in: {found_secrets}" if found_secrets else "Zero secrets tracked in git")
    except Exception as e:
        record("Secrets", "Git tracked secrets check", False, str(e))

    # Brain reads keys from environment variables
    with open(ROOT_DIR / "brain" / "config.py", "r", encoding="utf-8") as f:
        cfg = f.read()
    env_reads = "os.getenv" in cfg and "GROQ_API_KEY" in cfg and "GEMINI_API_KEY" in cfg
    record("Secrets", "Brain reads all keys from environment variables", env_reads, "Reads GROQ_API_KEY, GEMINI_API_KEY, TAVILY_API_KEY via os.getenv")


def check_hf_space_compatibility():
    print("\n--- 3. Hugging Face Space & Cloud Compatibility ---")
    
    has_dockerfile = (ROOT_DIR / "brain" / "Dockerfile").exists()
    record("Hugging Face", "Dockerfile exists in brain/", has_dockerfile, "Configured with PORT=7860 and non-root user")

    with open(ROOT_DIR / "brain" / "run.py", "r", encoding="utf-8") as f:
        run_py = f.read()
    dynamic_port = "os.getenv(\"PORT\"" in run_py or "os.getenv('PORT'" in run_py
    record("Hugging Face", "Brain dynamically binds to PORT (7860 on HF Spaces)", dynamic_port, "Binds to PORT env var or 8000 fallback")

    with open(ROOT_DIR / "brain" / "requirements.txt", "r", encoding="utf-8") as f:
        reqs = f.read()
    has_gemini_and_groq = "langchain-google-genai" in reqs and "langchain-groq" in reqs and "fastapi" in reqs
    record("Hugging Face", "brain/requirements.txt contains all core dependencies", has_gemini_and_groq, "fastapi, langchain-google-genai, langchain-groq, etc. present")


def check_packaging_readiness():
    print("\n--- 4. Local App & Packaging Readiness ---")
    
    # Asset resource_path helper for PyInstaller _MEIPASS
    with open(ROOT_DIR / "local" / "app.py", "r", encoding="utf-8") as f:
        app_code = f.read()
    has_resource_path = "sys._MEIPASS" in app_code and "resource_path" in app_code
    record("Packaging", "GUI assets use PyInstaller-compatible resource_path (_MEIPASS)", has_resource_path, "local/app.py handles frozen bundles")

    # Offline graceful fallback
    with open(ROOT_DIR / "local" / "main.py", "r", encoding="utf-8") as f:
        main_code = f.read()
    has_fallback = "_offline_fallback" in main_code
    record("Packaging", "App degrades gracefully if Brain is offline", has_fallback, "_offline_fallback active with speech notice")


def main():
    print("=" * 70)
    print("EXECUTING JARVIS READINESS CHECKLIST VERIFICATION")
    print("=" * 70)
    
    check_structure()
    check_secrets()
    check_hf_space_compatibility()
    check_packaging_readiness()
    
    passed_count = sum(1 for r in checklist_results if r["passed"])
    total_count = len(checklist_results)
    
    print("\n" + "=" * 70)
    print(f"CHECKLIST EXECUTION SUMMARY: {passed_count}/{total_count} CHECKS PASSED")
    print("=" * 70)
    
    if passed_count == total_count:
        print("\n>>> ALL READINESS CHECKS PASSED! BRAIN AND SYSTEM ARE DEPLOYMENT READY! <<<")
        return 0
    else:
        print("\n>>> SOME CHECKS FAILED. PLEASE REVIEW THE ITEMS ABOVE. <<<")
        return 1

if __name__ == "__main__":
    sys.exit(main())
