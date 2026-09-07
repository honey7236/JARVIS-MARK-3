"""
WEB AUTOMATION MODULE
=====================
Handles website opening, Google search, and YouTube search in default browser.
Ported from JARVIS-MARK-2 backend/automation.py.
"""

import webbrowser
from urllib.parse import quote

try:
    from local.data.web_data import websites
except ImportError:
    from data.web_data import websites


def open_website(site: str) -> str:
    """Open a website URL or named website from web_data map."""
    if not site:
        return "No website specified"

    site_clean = site.lower().replace("open", "").strip()
    if not site_clean:
        return "No website specified"

    if site_clean in websites:
        url = websites[site_clean]
    elif "." in site_clean:
        url = f"https://{site_clean}"
    else:
        url = f"https://www.{site_clean}.com"

    try:
        webbrowser.open(url)
    except Exception:
        webbrowser.open(f"https://www.google.com/search?q={quote(site_clean)}")
    return f"Opening {site_clean}"


def google_search(query: str) -> str:
    """Perform a Google search in the default web browser."""
    clean_query = query.replace("google search", "").replace("search", "").strip()
    if not clean_query:
        return "What should I search for on Google?"

    url = f"https://www.google.com/search?q={quote(clean_query)}"
    webbrowser.open(url)
    return f"Searching Google for {clean_query}"


def youtube_search(query: str) -> str:
    """Perform a YouTube search in the default web browser."""
    clean_query = query.replace("youtube search", "").replace("search", "").strip()
    if not clean_query:
        return "What should I search for on YouTube?"

    url = f"https://www.youtube.com/results?search_query={quote(clean_query)}"
    webbrowser.open(url)
    return f"Searching YouTube for {clean_query}"
