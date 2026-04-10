"""
mobile/src/ui/LoginScreen.py

Login screen — entry gate for every student (#73).

Auth flow (Auth0 PKCE):
  1. "Login" pressed → generate PKCE pair → open Auth0 URL in browser
  2. Auth0 redirects to studybuddy://callback?code=...
  3. App receives deep link → calls handle_auth_callback(url)
  4. Screen extracts code, exchanges with Auth0 → id_token
  5. POST /auth/exchange → internal JWT stored via token_store
  6. Navigate to DashboardScreen (or home screen)

Non-deep-link environments (desktop dev): a paste field appears in the
"waiting" state so the callback URL can be entered manually.

States:
  default  — "Login" button + "Create account" + "Forgot password"
  waiting  — browser opened; shows callback paste field + Cancel
  loading  — spinner text while exchanging tokens
  error    — friendly age-appropriate error, no stack traces

Layer rule: ui layer only — all network calls in daemon threads.
"""

from __future__ import annotations

import threading
import webbrowser

try:
    from kivy.uix.screenmanager import Screen  # type: ignore
    from kivy.uix.boxlayout import BoxLayout  # type: ignore
    from kivy.uix.label import Label  # type: ignore
    from kivy.uix.button import Button  # type: ignore
    from kivy.uix.textinput import TextInput  # type: ignore
    from kivy.clock import mainthread  # type: ignore
    KIVY_AVAILABLE = True
except ImportError:
    Screen = object  # type: ignore
    mainthread = lambda f: f  # type: ignore
    KIVY_AVAILABLE = False

try:
    from mobile.src.utils.logger import get_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(name: str):  # type: ignore
        return logging.getLogger(name)

log = get_logger("login_screen")

# Human-readable error messages — no technical detail exposed to students
_ERROR_MESSAGES: dict[str, str] = {
    "suspended":      "Your account has been suspended. Please contact your school.",
    "coppa_pending":  "Ask a parent or guardian to check their email to activate your account.",
    "network":        "Could not connect. Check your Wi-Fi and try again.",
    "invalid_code":   "Login did not complete. Please try again.",
    "server":         "Something went wrong on our end. Please try again shortly.",
}


def _map_error(exc: Exception) -> str:
    """Return a student-safe error message for any exception."""
    msg = str(exc).lower()
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status == 403:
        body = ""
        try:
            body = exc.response.json().get("detail", "").lower()  # type: ignore
        except Exception:
            pass
        if "coppa" in body or "consent" in body:
            return _ERROR_MESSAGES["coppa_pending"]
        return _ERROR_MESSAGES["suspended"]
    if "network" in msg or "connect" in msg or "timeout" in msg:
        return _ERROR_MESSAGES["network"]
    if "invalid" in msg or "code" in msg:
        return _ERROR_MESSAGES["invalid_code"]
    return _ERROR_MESSAGES["server"]


class LoginScreen(Screen):
    """
    Auth0 PKCE login screen.

    Usage (wired by the App / navigation layer):
        login_screen = LoginScreen(name="login")
        screen_manager.add_widget(login_screen)
        screen_manager.current = "login"

    When the deep-link callback arrives:
        login_screen.handle_auth_callback("studybuddy://callback?code=...")
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._pkce_verifier: str = ""
        self._state: str = "default"  # default | waiting | loading | error

        if KIVY_AVAILABLE:
            self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = BoxLayout(orientation="vertical", padding=40, spacing=20)

        # App wordmark
        root.add_widget(Label(
            text="StudyBuddy",
            font_size="28sp",
            bold=True,
            halign="center",
            size_hint=(1, None),
            height=56,
        ))
        root.add_widget(Label(
            text="Your personal learning companion",
            font_size="14sp",
            halign="center",
            color=(0.55, 0.55, 0.55, 1),
            size_hint=(1, None),
            height=28,
        ))

        # Status / error message
        self._status_label = Label(
            text="",
            font_size="14sp",
            halign="center",
            color=(0.85, 0.25, 0.2, 1),
            size_hint=(1, None),
            height=40,
        )
        self._status_label.bind(
            width=lambda *_: setattr(
                self._status_label, "text_size",
                (self._status_label.width, None),
            )
        )
        root.add_widget(self._status_label)

        # Primary login button
        self._login_btn = Button(
            text="Log in",
            font_size="16sp",
            size_hint=(1, None),
            height=52,
        )
        self._login_btn.bind(on_press=self._on_login_pressed)
        root.add_widget(self._login_btn)

        # Callback paste field (shown only in "waiting" state)
        self._callback_label = Label(
            text="Paste the callback URL here if your browser didn't redirect automatically:",
            font_size="12sp",
            halign="left",
            color=(0.55, 0.55, 0.55, 1),
            size_hint=(1, None),
            height=36,
            opacity=0,
        )
        root.add_widget(self._callback_label)

        self._callback_input = TextInput(
            hint_text="studybuddy://callback?code=...",
            multiline=False,
            font_size="13sp",
            size_hint=(1, None),
            height=44,
            opacity=0,
            disabled=True,
        )
        root.add_widget(self._callback_input)

        self._submit_callback_btn = Button(
            text="Submit",
            font_size="14sp",
            size_hint=(1, None),
            height=44,
            opacity=0,
            disabled=True,
        )
        self._submit_callback_btn.bind(on_press=self._on_submit_callback)
        root.add_widget(self._submit_callback_btn)

        self._cancel_btn = Button(
            text="Cancel",
            font_size="14sp",
            size_hint=(1, None),
            height=40,
            opacity=0,
            disabled=True,
        )
        self._cancel_btn.bind(on_press=self._on_cancel)
        root.add_widget(self._cancel_btn)

        # Spacer
        root.add_widget(Label(size_hint=(1, 1)))

        # Secondary actions
        create_btn = Button(
            text="Create a free account",
            font_size="14sp",
            background_color=(0.15, 0.4, 0.85, 1),
            size_hint=(1, None),
            height=48,
        )
        create_btn.bind(on_press=self._on_create_account)
        root.add_widget(create_btn)

        forgot_btn = Button(
            text="Forgot password",
            font_size="13sp",
            background_color=(0, 0, 0, 0),
            color=(0.4, 0.4, 0.8, 1),
            size_hint=(1, None),
            height=36,
        )
        forgot_btn.bind(on_press=self._on_forgot_password)
        root.add_widget(forgot_btn)

        self.add_widget(root)

    # ── State transitions ─────────────────────────────────────────────────────

    @mainthread
    def _set_state(self, state: str, message: str = "") -> None:
        self._state = state
        waiting = state == "waiting"
        loading = state == "loading"

        if not KIVY_AVAILABLE:
            return

        if hasattr(self, "_login_btn"):
            self._login_btn.text = "Loading…" if loading else "Log in"
            self._login_btn.disabled = loading or waiting

        if hasattr(self, "_status_label"):
            self._status_label.text = message
            self._status_label.color = (
                (0.85, 0.25, 0.2, 1) if state == "error"
                else (0.55, 0.55, 0.55, 1)
            )

        for widget_name, visible in [
            ("_callback_label", waiting),
            ("_callback_input", waiting),
            ("_submit_callback_btn", waiting),
            ("_cancel_btn", waiting),
        ]:
            w = getattr(self, widget_name, None)
            if w is not None:
                w.opacity = 1 if visible else 0
                w.disabled = not visible

    # ── Login button ──────────────────────────────────────────────────────────

    def _on_login_pressed(self, *_) -> None:
        if self._state in ("waiting", "loading"):
            return
        threading.Thread(target=self._start_pkce_thread, daemon=True).start()

    def _start_pkce_thread(self) -> None:
        """Generate PKCE pair and open Auth0 in the system browser."""
        try:
            from mobile.src.auth.auth0_client import (  # type: ignore
                generate_pkce_pair, get_auth0_login_url, open_auth0_login,
            )
            verifier, challenge = generate_pkce_pair()
            self._pkce_verifier = verifier
            url = get_auth0_login_url(challenge)
            open_auth0_login(url)
            self._set_state(
                "waiting",
                "Your browser opened. Log in and return to the app.",
            )
            log.info("pkce_flow_started")
        except Exception as exc:
            log.warning("pkce_start_failed error=%s", exc)
            self._set_state("error", _ERROR_MESSAGES["network"])

    # ── Callback handling ─────────────────────────────────────────────────────

    def handle_auth_callback(self, callback_url: str) -> None:
        """
        Called by the App when the Auth0 deep-link arrives.

        Extracts the authorization code and starts the token exchange in a
        daemon thread.  Safe to call from any thread.
        """
        log.info("handle_auth_callback url_prefix=%s", callback_url[:40])
        threading.Thread(
            target=self._exchange_tokens_thread,
            args=(callback_url,),
            daemon=True,
        ).start()

    def _on_submit_callback(self, *_) -> None:
        """Called when the user manually submits the callback URL."""
        url = ""
        if KIVY_AVAILABLE and hasattr(self, "_callback_input"):
            url = self._callback_input.text.strip()
        if url:
            self.handle_auth_callback(url)

    def _on_cancel(self, *_) -> None:
        self._pkce_verifier = ""
        self._set_state("default", "")

    # ── Token exchange ────────────────────────────────────────────────────────

    def _exchange_tokens_thread(self, callback_url: str) -> None:
        """Daemon thread: Auth0 code → id_token → internal JWT → store → navigate."""
        self._set_state("loading", "Logging you in…")
        import asyncio

        try:
            from mobile.src.auth.auth0_client import (  # type: ignore
                extract_code_from_callback, exchange_code_for_tokens,
            )
            code = extract_code_from_callback(callback_url)
            if not code:
                self._set_state("error", _ERROR_MESSAGES["invalid_code"])
                return

            loop = asyncio.new_event_loop()
            auth0_tokens = loop.run_until_complete(
                exchange_code_for_tokens(code, self._pkce_verifier)
            )
            loop.close()

            id_token: str = auth0_tokens.get("id_token", "")
            if not id_token:
                self._set_state("error", _ERROR_MESSAGES["invalid_code"])
                return

            # Exchange Auth0 id_token for internal JWT
            from mobile.src.api.auth_client import exchange_id_token  # type: ignore
            loop = asyncio.new_event_loop()
            backend_resp = loop.run_until_complete(exchange_id_token(id_token))
            loop.close()

            internal_token: str = backend_resp.get("token", "")
            refresh_token: str = backend_resp.get("refresh_token", "")

            if not internal_token:
                self._set_state("error", _ERROR_MESSAGES["server"])
                return

            # Persist tokens — never logged
            try:
                from mobile.src.auth.token_store import save_token  # type: ignore
                import config as cfg  # type: ignore
                save_token(cfg.JWT_STORAGE_FILENAME, internal_token)
                if refresh_token:
                    save_token(cfg.REFRESH_TOKEN_FILENAME, refresh_token)
            except Exception as exc:
                log.warning("token_save_failed error=%s", exc)

            log.info("login_complete")
            self._navigate_after_login(internal_token)

        except Exception as exc:
            log.warning("login_exchange_failed error=%s", exc)
            self._set_state("error", _map_error(exc))

    @mainthread
    def _navigate_after_login(self, token: str) -> None:
        """Navigate to DashboardScreen (or home fallback) on main thread."""
        if not (KIVY_AVAILABLE and hasattr(self, "manager") and self.manager):
            return
        mgr = self.manager
        target = "dashboard" if mgr.has_screen("dashboard") else "progress_dashboard"
        if mgr.has_screen(target):
            try:
                mgr.get_screen(target).set_token(token)
            except Exception:
                pass
        if mgr.has_screen(target):
            mgr.current = target

    # ── Secondary actions ─────────────────────────────────────────────────────

    def _on_create_account(self, *_) -> None:
        """Open Auth0 signup page in browser."""
        threading.Thread(target=self._open_signup_thread, daemon=True).start()

    def _open_signup_thread(self) -> None:
        try:
            import asyncio
            from mobile.src.api.auth_client import get_auth0_signup_url  # type: ignore
            loop = asyncio.new_event_loop()
            url = loop.run_until_complete(get_auth0_signup_url())
            loop.close()
            if url:
                webbrowser.open(url)
        except Exception as exc:
            log.warning("signup_open_failed error=%s", exc)

    def _on_forgot_password(self, *_) -> None:
        """Open Auth0 password reset page in browser."""
        threading.Thread(target=self._open_reset_thread, daemon=True).start()

    def _open_reset_thread(self) -> None:
        try:
            import asyncio
            from mobile.src.api.auth_client import get_auth0_reset_url  # type: ignore
            loop = asyncio.new_event_loop()
            url = loop.run_until_complete(get_auth0_reset_url())
            loop.close()
            if url:
                webbrowser.open(url)
        except Exception as exc:
            log.warning("reset_open_failed error=%s", exc)
