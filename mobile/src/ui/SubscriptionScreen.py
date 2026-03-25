"""
mobile/src/ui/SubscriptionScreen.py

Paywall / subscription screen — shown when the backend returns HTTP 402.

Phase 5: real plan cards + Stripe Checkout integration.

Flow:
  1. Student hits HTTP 402 on any content endpoint.
  2. App navigates to SubscriptionScreen.
  3. Screen loads plan options from GET /subscription/status.
  4. Student taps "Subscribe" on a plan.
  5. App calls POST /subscription/checkout → receives checkout_url.
  6. App opens checkout_url in system browser / WebView.
  7. After checkout Stripe fires webhook → backend activates subscription.
  8. Student taps "I've subscribed" to refresh their status and return.

Layer rule: UI screens only import from logic/ and api/ layers.
"""

from __future__ import annotations

import threading
import webbrowser

try:
    from mobile.src.utils.logger import get_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(name: str):
        return logging.getLogger(name)

log = get_logger("subscription_screen")

try:
    from kivy.uix.screenmanager import Screen  # type: ignore
    from kivy.uix.boxlayout import BoxLayout  # type: ignore
    from kivy.uix.label import Label  # type: ignore
    from kivy.uix.button import Button  # type: ignore
    from kivy.uix.scrollview import ScrollView  # type: ignore
    from kivy.clock import mainthread  # type: ignore
    _KIVY_AVAILABLE = True
except ImportError:
    _KIVY_AVAILABLE = False

    class Screen:  # type: ignore
        name: str = ""
        def __init__(self, **kwargs):
            self.name = kwargs.get("name", "")
        def add_widget(self, widget):
            pass

# Plan definitions — label, description, plan key
_PLANS = [
    {
        "plan": "monthly",
        "label": "Monthly",
        "description": "Unlimited lessons, quizzes & tutorials\nCancel any time",
        "cta": "Subscribe Monthly",
    },
    {
        "plan": "annual",
        "label": "Annual",
        "description": "Everything in Monthly\nBest value — save 2 months",
        "cta": "Subscribe Annually",
    },
]

# Deep-link / redirect URLs used by Stripe Checkout
_SUCCESS_URL = "studybuddy://subscription/success"
_CANCEL_URL = "studybuddy://subscription/cancel"


class SubscriptionScreen(Screen):
    """
    Paywall screen displayed when HTTP 402 is received.

    Shows two plan cards (Monthly / Annual) and handles the Stripe checkout flow.
    """

    def __init__(self, token: str = "", **kwargs):
        super().__init__(**kwargs)
        self.name = "subscription"
        self._token = token
        self._pending_plan: str | None = None

        if _KIVY_AVAILABLE:
            self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        scroll = ScrollView()
        root = BoxLayout(orientation="vertical", padding=32, spacing=16, size_hint_y=None)
        root.bind(minimum_height=root.setter("height"))

        root.add_widget(Label(
            text="Upgrade to StudyBuddy Premium",
            font_size=22,
            bold=True,
            size_hint_y=None,
            height=52,
        ))
        root.add_widget(Label(
            text="Free plan includes 2 lessons. Premium unlocks everything.",
            font_size=14,
            size_hint_y=None,
            height=36,
            halign="center",
        ))

        # ── Plan cards ────────────────────────────────────────────────────────
        for p in _PLANS:
            card = BoxLayout(orientation="vertical", size_hint_y=None, height=130,
                             padding=12, spacing=6)

            card.add_widget(Label(text=p["label"], font_size=18, bold=True,
                                  size_hint_y=None, height=32))
            card.add_widget(Label(text=p["description"], font_size=13,
                                  size_hint_y=None, height=40, halign="left"))

            btn = Button(text=p["cta"], size_hint_y=None, height=44,
                         background_color=(0.2, 0.5, 0.9, 1))
            btn.bind(on_release=lambda _, plan=p["plan"]: self._on_subscribe(plan))
            card.add_widget(btn)
            root.add_widget(card)

        # ── Restore / confirm button ──────────────────────────────────────────
        restore_btn = Button(
            text="I've already subscribed — refresh",
            size_hint_y=None,
            height=44,
            background_color=(0.3, 0.65, 0.4, 1),
        )
        restore_btn.bind(on_release=self._on_restore)
        root.add_widget(restore_btn)

        # ── Back button ───────────────────────────────────────────────────────
        back_btn = Button(
            text="Go Back",
            size_hint_y=None,
            height=44,
            background_color=(0.4, 0.4, 0.4, 1),
        )
        back_btn.bind(on_release=self._on_back)
        root.add_widget(back_btn)

        self._status_label = Label(text="", size_hint_y=None, height=28, font_size=13)
        root.add_widget(self._status_label)

        scroll.add_widget(root)
        self.add_widget(scroll)

    # ── Subscribe ─────────────────────────────────────────────────────────────

    def _on_subscribe(self, plan: str) -> None:
        """Fetch a Stripe checkout URL and open it in the system browser."""
        self._pending_plan = plan
        self._set_status("Opening checkout…")
        threading.Thread(
            target=self._open_checkout,
            args=(plan,),
            daemon=True,
        ).start()

    def _open_checkout(self, plan: str) -> None:
        try:
            import asyncio
            from mobile.src.api.subscription_client import get_checkout_url  # type: ignore
            loop = asyncio.new_event_loop()
            url = loop.run_until_complete(
                get_checkout_url(self._token, plan, _SUCCESS_URL, _CANCEL_URL)
            )
            loop.close()
            # Open in system browser — never proxy Stripe through our app
            webbrowser.open(url)
            self._set_status("Checkout opened in browser. Tap 'I've subscribed' when done.")
        except Exception as exc:
            log.warning("checkout_open_failed plan=%s error=%s", plan, exc)
            self._set_status(f"Could not open checkout: {exc}")

    # ── Restore / refresh ─────────────────────────────────────────────────────

    def _on_restore(self, *_) -> None:
        """Refresh subscription status and navigate back if now active."""
        self._set_status("Checking subscription…")
        threading.Thread(target=self._check_status, daemon=True).start()

    def _check_status(self) -> None:
        try:
            import asyncio
            from mobile.src.api.subscription_client import get_subscription_status  # type: ignore
            loop = asyncio.new_event_loop()
            status = loop.run_until_complete(get_subscription_status(self._token))
            loop.close()
            plan = status.get("plan", "free")
            if plan in ("monthly", "annual") and status.get("status") == "active":
                self._set_status(f"Active {plan} subscription confirmed!")
                self._navigate_back()
            else:
                self._set_status("Subscription not found yet. Please try again shortly.")
        except Exception as exc:
            log.warning("restore_check_failed error=%s", exc)
            self._set_status(f"Could not verify subscription: {exc}")

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_back(self, *_) -> None:
        self._navigate_back()

    @mainthread
    def _navigate_back(self) -> None:
        if _KIVY_AVAILABLE and hasattr(self, "manager") and self.manager:
            try:
                self.manager.current = self.manager.previous()
            except Exception:
                self.manager.current = "dashboard"

    # ── UI helpers ────────────────────────────────────────────────────────────

    @mainthread
    def _set_status(self, text: str) -> None:
        if hasattr(self, "_status_label"):
            self._status_label.text = text
