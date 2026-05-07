"""
Manim scene — projectile motion h(t) = -4.9 t² + 14 t + 2.

See note in transformations.py about Python in this project. Same caveat applies.

Render:
    manim -pql projectile.py ProjectileMotion
"""

from manim import *


class ProjectileMotion(Scene):
    """Animate a ball tracing the parabola h(t) = -4.9 t² + 14 t + 2."""

    def construct(self):
        # h(t) hits 0 at t ≈ 2.706 seconds; max height 12 m at t ≈ 1.43 s
        T_MAX = 2.706
        H_MAX = 14

        axes = Axes(
            x_range=[0, 3, 0.5],
            y_range=[0, H_MAX, 2],
            x_length=10,
            y_length=5.5,
            tips=False,
            axis_config={"include_numbers": True, "font_size": 22},
        )
        x_label = axes.get_x_axis_label(Tex(r"$t$ (seconds)"), edge=DOWN)
        y_label = axes.get_y_axis_label(Tex(r"$h(t)$ (metres)"), edge=LEFT)
        self.add(axes, x_label, y_label)

        title = Tex(r"$h(t) = -4.9 t^{2} + 14 t + 2$").to_edge(UP)
        self.add(title)

        def h_of(t):
            return -4.9 * t * t + 14 * t + 2

        # Faint full-curve guide
        full_curve = axes.plot(h_of, color=GREY, x_range=[0, T_MAX])
        full_curve.set_stroke(width=2, opacity=0.4)
        self.add(full_curve)

        # Animated ball
        t_tracker = ValueTracker(0)
        ball = always_redraw(
            lambda: Dot(axes.c2p(t_tracker.get_value(), h_of(t_tracker.get_value())), color=RED, radius=0.12)
        )
        # Live readout
        readout = always_redraw(
            lambda: Tex(
                f"$t = {t_tracker.get_value():.2f}$ s,\\quad $h = {max(0, h_of(t_tracker.get_value())):.2f}$ m",
                font_size=30,
            ).to_corner(UR)
        )

        # Trace as the ball moves
        traced = TracedPath(ball.get_center, stroke_color=BLUE, stroke_width=4)
        self.add(ball, readout, traced)

        # Animate the flight
        self.play(t_tracker.animate.set_value(T_MAX), run_time=4, rate_func=linear)

        # Mark the max-height point
        peak_t = 14 / 9.8
        peak_dot = Dot(axes.c2p(peak_t, h_of(peak_t)), color=YELLOW, radius=0.10)
        peak_label = Tex(rf"max: $({peak_t:.2f}, 12.0)$", font_size=26).next_to(peak_dot, UP)
        self.play(FadeIn(peak_dot), Write(peak_label))
        self.wait(2)
