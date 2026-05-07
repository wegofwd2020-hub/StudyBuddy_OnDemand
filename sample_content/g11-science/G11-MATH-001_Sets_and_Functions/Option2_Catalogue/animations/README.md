# Animations — Manim renderings + no-install SVG fallback

Two visuals from the chapter benefit most from animation: the **transformation walkthrough** of $y = x^2 \to -2(x+3)^2 + 5$, and the **projectile flight** under $h(t) = -4.9 t^2 + 14 t + 2$.

Per the catalogue's "right tool per visual" principle, these are rendered with **Manim** — the de-facto open-source library for mathematical animation, used heavily by 3Blue1Brown and educational creators.

## Note on Python in this catalogue

StudyBuddy backend / scripts are TypeScript-only (per project policy in `CLAUDE.md`). The Python files here (`transformations.py`, `projectile.py`) are **deliverable artifacts** — Manim scenes you run from a separate venv when you want fresh renders. They are not imported, called, or tested by any TypeScript code in the repo. Treat them like a `.docx` or `.tex` source file: input to a one-shot rendering pipeline that lives outside the project.

If we end up rendering animations regularly, the path forward is either:

- a small Manim render container (Docker image with Manim + LaTeX preinstalled), invoked by a TypeScript wrapper, OR
- migrating these animations to a TypeScript-native library (Remotion is already a first-class skill in PAI tooling and would be the natural choice).

## How to run the Manim scenes

One-time setup:

```bash
python3 -m venv .manim-venv
source .manim-venv/bin/activate
pip install manim
sudo apt install texlive texlive-latex-extra ffmpeg libcairo2 libpango1.0-0
```

Render:

```bash
# 480p preview, opens in your default video player
manim -pql transformations.py TransformParabola
manim -pql projectile.py     ProjectileMotion

# 1080p final
manim -pqh transformations.py TransformParabola
manim -pqh projectile.py     ProjectileMotion
```

Output lands in `media/videos/<scene-file>/<quality>/<SceneName>.mp4`.

## No-install fallback — `projectile-smil.svg`

If you don't want to install Manim just for one demo, `projectile-smil.svg` is a hand-authored SVG using SMIL `<animateMotion>` to animate a ball along an approximate parabola. Open it in any modern browser; the animation auto-plays and loops. Fidelity is lower than Manim (the path is a Bezier approximation rather than the exact parabola), but it costs nothing to ship.

## Which to use when

| Situation | Use |
|---|---|
| One-off demo, want it now | `projectile-smil.svg` (open in browser) |
| Production student-facing animation | render Manim → `.mp4` |
| Future-proof: want to keep TS-only | port to a Remotion composition |
| Want sliders / interactivity | the Desmos route in `../function-graphs/` is better than animation |
