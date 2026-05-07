# Function graphs — Desmos & GeoGebra recipes

The "Per-example artifact catalogue" approach intentionally uses the **right tool per visual**. For function graphs Desmos and GeoGebra both produce production-grade interactive graphs without a code path — you paste an expression, the rendering is handled.

## How to use this file

For each example below:

1. Open https://www.desmos.com/calculator (or https://www.geogebra.org/graphing).
2. Paste the **expression** into a new cell.
3. **Save** the graph (Desmos: top-right "Save" → name → copy share URL; GeoGebra: File → Share).
4. Capture the share URL into the `Saved URL` column below for repeat use.

Saving once gives you a stable iframe-embeddable URL that can be dropped into any LMS, slide deck, or web page.

---

## Vertical Line Test

| What | Expression | Saved URL |
|---|---|---|
| Function | `y = x^2 - 1` | _to fill_ |
| Not a function | `y^2 = x` (or implicitly: `x = y^2`) | _to fill_ |
| Sweep line | `x = 1` (Desmos: add as separate line) | _to fill_ |

## Polynomial / rational / absolute value (tutorial § 3.2–3.4)

| What | Expression | Notes |
|---|---|---|
| Cubic | `y = x^3 - x` | Three real zeroes at $x = -1, 0, 1$ |
| Rational | `y = (3x + 1) / ((x - 2)(x - 3))` | Vertical asymptotes at $x = 2, 3$ |
| Absolute value | `y = abs(x)` | V-shape; non-differentiable at origin |

## Piecewise (tutorial § 3.5)

Desmos supports piecewise via `{}` syntax:

```
g(x) = {x < 0: x^2, 0 <= x <= 3: 2x + 1, x > 3: 10 - x}
```

GeoGebra equivalent:

```
g(x) = If(x < 0, x^2, If(x <= 3, 2x + 1, 10 - x))
```

For the closed/open boundary dots that are the pedagogical point of piecewise functions, add separately:

```
(0, 1)        # closed dot — middle piece includes 0
(3, 7)        # closed dot — middle piece includes 3
(3, 7)        # open dot — right piece does NOT include 3 (style as hollow)
```

## Even / odd / neither (tutorial § 3.7)

| Function | Expression | Symmetry |
|---|---|---|
| $h(x)$ — even | `h(x) = 4x^4 - 2x^2 + 1` | Mirror across the $y$-axis |
| $k(x)$ — odd | `k(x) = 3x^3 - x` | Rotational symmetry about origin |
| $p(x)$ — neither | `p(x) = x^2 + x` | No symmetry |

To highlight the symmetry test in Desmos, plot `h(-x)` as a separate cell with a different colour — for an even function it lands exactly on top of `h(x)`.

## Inverse functions and reflection across $y = x$ (tutorial § 4.3)

```
f(x)     = e^x
g(x)     = ln(x)        # = f⁻¹(x)
y        = x            # the mirror line — add as a separate cell
```

The visual point: `g` is `f` reflected across `y = x`. In GeoGebra you can use `Reflect[f, y = x]` to construct the reflection from `f` directly and prove the equivalence.

## Transformations of $y = x^2$ (tutorial § 5.1)

A nice GeoGebra construction uses **sliders** to make every transformation parameter interactive:

```
a = Slider(-5, 5, step = 0.5, init = 1)
b = Slider(0.1, 3, step = 0.1, init = 1)
h = Slider(-5, 5, step = 0.5, init = 0)
k = Slider(-5, 5, step = 0.5, init = 0)
y = a * (b * (x - h))^2 + k
```

Drag each slider in turn to demonstrate horizontal shift, vertical scale, reflection, and vertical shift independently. This is hard to beat with a static graphic.

## Projectile motion $h(t) = -4.9 t^2 + 14 t + 2$ (tutorial § 5.3)

Desmos has **time-based animation** built in via the `t` slider:

```
h(t) = -4.9 t^2 + 14 t + 2
(t, h(t))           # animate the dot
```

Set the `t` slider to range `[0, 2.71]` and press play — the dot traces the parabola in real time, same effect as a Manim render with zero install.

---

## Why Desmos / GeoGebra rather than a hand-coded graph?

For function graphs specifically, both tools beat any custom rendering on every axis that matters for research:

| Axis | Hand-coded SVG / Plotly | Desmos / GeoGebra |
|---|---|---|
| Visual quality | OK | excellent |
| Interactivity (zoom / pan / hover) | depends on library | built in |
| Sliders for parameter studies | bespoke code | one line each |
| Embedding | iframe / inline | iframe URL |
| Time animation | rAF loop you write | `t` slider, free |
| Math-aware syntax (e.g. `e^x`, `ln`) | one line each | native |

The cost is dependency on a third-party service (URLs can rot, branding shows on the iframe). Both Desmos and GeoGebra also have offline-installable apps if that becomes a concern.
