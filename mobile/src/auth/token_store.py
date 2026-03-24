"""
mobile/src/auth/token_store.py

Secure JWT token storage for the Kivy mobile app.

Tokens are stored as plain-text files in the app's private data directory
(App.user_data_dir), with permissions restricted to owner read/write (0600).

Platform notes:
  Android: user_data_dir → app private internal storage (other apps cannot access)
  iOS:     user_data_dir → app sandbox Documents directory
  Linux:   user_data_dir → ~/.studybuddy/ or similar per-app directory

Never stores secrets in shared locations (e.g., /sdcard, SharedPreferences,
or the app bundle itself).
"""

from __future__ import annotations

import os
import stat
from typing import Optional


def _get_user_data_dir() -> str:
    """
    Return the app's private data directory.

    Tries to get it from the running Kivy app; falls back to a temp path
    for unit tests where no Kivy app is running.
    """
    try:
        from kivy.app import App
        running = App.get_running_app()
        if running is not None:
            return running.user_data_dir
    except ImportError:
        pass

    # Fallback for tests / non-Kivy environments.
    fallback = os.path.join(os.path.expanduser("~"), ".studybuddy")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def _path(filename: str) -> str:
    """Return the full path to a token file."""
    return os.path.join(_get_user_data_dir(), filename)


def save_token(filename: str, token: str) -> None:
    """
    Write *token* to *filename* in the app's private data dir.

    Sets file permissions to 0600 (owner read/write only).
    """
    path = _path(filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(token)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        # chmod may fail on some Android file systems; acceptable on mobile.
        pass


def load_token(filename: str) -> Optional[str]:
    """
    Read and return the token stored in *filename*.

    Returns None if the file does not exist or cannot be read.
    """
    path = _path(filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return content if content else None
    except OSError:
        return None


def delete_token(filename: str) -> None:
    """
    Delete the token file if it exists.

    Safe to call even if the file does not exist.
    """
    path = _path(filename)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def token_exists(filename: str) -> bool:
    """Return True if the token file exists and is non-empty."""
    return load_token(filename) is not None
