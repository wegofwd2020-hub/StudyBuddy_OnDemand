"""
mobile/src/ui/SubscriptionScreen.py

Stub paywall screen displayed when the backend returns HTTP 402.

Shown when a free-tier student has exceeded their lesson access limit.
The Subscribe button is a placeholder — real Stripe integration is Phase 5.

Layer rule: UI screens only import from logic/ and api/ layers.
"""

from __future__ import annotations

import logging

log = logging.getLogger("mobile.ui.subscription_screen")

try:
    from kivy.uix.screenmanager import Screen  # type: ignore
    from kivy.uix.boxlayout import BoxLayout  # type: ignore
    from kivy.uix.label import Label  # type: ignore
    from kivy.uix.button import Button  # type: ignore
    _KIVY_AVAILABLE = True
except ImportError:
    # Kivy not installed in test/CI environments — provide stub base class.
    _KIVY_AVAILABLE = False

    class Screen:  # type: ignore
        """Stub Screen for non-Kivy environments."""
        name: str = ""

        def __init__(self, **kwargs):
            self.name = kwargs.get("name", "")

        def add_widget(self, widget):
            pass


class SubscriptionScreen(Screen):
    """
    Paywall screen shown when HTTP 402 is received from the content API.

    Displays an upgrade prompt and a placeholder Subscribe button.
    Real Stripe checkout integration will be implemented in Phase 5.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "subscription"

        if _KIVY_AVAILABLE:
            self._build_ui()

    def _build_ui(self) -> None:
        """Build the screen layout using Kivy widgets."""
        layout = BoxLayout(orientation="vertical", padding=40, spacing=20)

        title = Label(
            text="Upgrade to StudyBuddy Premium",
            font_size="22sp",
            bold=True,
            size_hint_y=None,
            height=50,
        )

        message = Label(
            text=(
                "Upgrade to StudyBuddy Premium to unlock all lessons.\n\n"
                "Free plan includes 2 lessons per unit.\n"
                "Premium unlocks unlimited lessons, quizzes, and tutorials."
            ),
            text_size=(400, None),
            halign="center",
            font_size="16sp",
        )

        subscribe_btn = Button(
            text="Subscribe — Coming Soon",
            size_hint_y=None,
            height=55,
            background_color=(0.2, 0.5, 0.9, 1),
        )
        subscribe_btn.bind(on_press=self._on_subscribe_pressed)

        back_btn = Button(
            text="Go Back",
            size_hint_y=None,
            height=44,
            background_color=(0.4, 0.4, 0.4, 1),
        )
        back_btn.bind(on_press=self._on_back_pressed)

        layout.add_widget(title)
        layout.add_widget(message)
        layout.add_widget(subscribe_btn)
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def _on_subscribe_pressed(self, *args) -> None:
        """
        Placeholder handler for the Subscribe button.
        Phase 5 will implement Stripe Checkout here.
        """
        log.info("TODO Phase 5: open Stripe checkout flow")

    def _on_back_pressed(self, *args) -> None:
        """Navigate back to the previous screen."""
        if _KIVY_AVAILABLE:
            try:
                self.manager.current = self.manager.previous()
            except Exception:
                pass
