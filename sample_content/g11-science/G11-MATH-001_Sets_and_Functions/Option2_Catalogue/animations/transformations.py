"""
Manim scene — transformations of y = x^2.

NOTE — this Python file is a deliverable artifact, not project source code.
The StudyBuddy backend / scripts are TypeScript-only per project policy.
This file exists because Manim is the right tool for this specific visual
and Manim is a Python library. Run it from a separate Python venv that you
manage outside the project's TypeScript dependencies.

Render:
    pip install manim                               # one-time, in a venv
    manim -pql transformations.py TransformParabola # 480p preview
    manim -pqh transformations.py TransformParabola # 1080p final

Output: media/videos/transformations/<quality>/TransformParabola.mp4
"""

from manim import *


class TransformParabola(Scene):
    """Walk through y = x² → -2(x + 3)² + 5 in four discrete steps."""

    def construct(self):
        axes = Axes(
            x_range=[-8, 4, 1],
            y_range=[-15, 15, 5],
            x_length=10,
            y_length=6,
            tips=False,
            axis_config={"include_numbers": True, "font_size": 22},
        )
        self.add(axes)

        title = Tex(r"Step 0 — base $y = x^2$").to_edge(UP)
        self.add(title)

        f0 = axes.plot(lambda x: x**2, color=BLUE, x_range=[-3.9, 3.9])
        self.play(Create(f0), run_time=1.5)
        self.wait(0.6)

        # Step 1 — shift left by 3
        f1 = axes.plot(lambda x: (x + 3) ** 2, color=BLUE, x_range=[-7, 1])
        new_title = Tex(r"Step 1 — shift LEFT by 3: $y = (x+3)^2$").to_edge(UP)
        self.play(Transform(title, new_title), Transform(f0, f1), run_time=1.5)
        self.wait(0.6)

        # Step 2 — vertical stretch
        f2 = axes.plot(lambda x: 2 * (x + 3) ** 2, color=BLUE, x_range=[-6, 0])
        new_title = Tex(r"Step 2 — vertical stretch by 2: $y = 2(x+3)^2$").to_edge(UP)
        self.play(Transform(title, new_title), Transform(f0, f2), run_time=1.5)
        self.wait(0.6)

        # Step 3 — reflect
        f3 = axes.plot(lambda x: -2 * (x + 3) ** 2, color=BLUE, x_range=[-6, 0])
        new_title = Tex(r"Step 3 — reflect across $x$-axis: $y = -2(x+3)^2$").to_edge(UP)
        self.play(Transform(title, new_title), Transform(f0, f3), run_time=1.5)
        self.wait(0.6)

        # Step 4 — shift up by 5
        f4 = axes.plot(lambda x: -2 * (x + 3) ** 2 + 5, color=BLUE, x_range=[-6.5, 0.5])
        new_title = Tex(
            r"Step 4 — shift UP by 5: $y = -2(x+3)^2 + 5$"
        ).to_edge(UP)
        self.play(Transform(title, new_title), Transform(f0, f4), run_time=1.5)
        self.wait(0.6)

        # Mark the vertex
        vertex = Dot(axes.c2p(-3, 5), color=RED, radius=0.1)
        vertex_label = Tex(r"$(-3, 5)$", font_size=28).next_to(vertex, UR, buff=0.1)
        self.play(FadeIn(vertex), Write(vertex_label))
        self.wait(2)
