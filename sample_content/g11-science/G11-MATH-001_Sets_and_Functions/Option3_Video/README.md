# Option 3 — Remotion explainer video

A Remotion (React → MP4) project that animates the worked examples from `Sets_and_Functions.md` into a single ~2-minute explainer.

## Layout

```
Option3_Video/
├── package.json
├── tsconfig.json
├── remotion.config.ts
├── src/
│   ├── index.ts            ← registerRoot
│   ├── Root.tsx            ← composition + scene-duration constants
│   ├── Video.tsx           ← Series of 9 scenes
│   ├── theme.ts            ← PAI_THEME (charcoal + purple aesthetic)
│   └── scenes/
│       ├── TitleScene.tsx
│       ├── VennScene.tsx                  (∪, ∩, \, ᶜ)
│       ├── VerticalLineTestScene.tsx     (function vs y² = x)
│       ├── ArrowDiagramScene.tsx         (inj / surj / bij)
│       ├── CompositionScene.tsx          (g∘f vs f∘g, side-by-side)
│       ├── InverseScene.tsx              (eˣ + ln + y=x)
│       ├── TransformationsScene.tsx      (x² → −2(x+3)² + 5, 4 steps)
│       ├── ProjectileScene.tsx           (h(t) animated dot)
│       └── ClosingScene.tsx
└── public/
```

Total duration: 3,510 frames at 30 fps  ≈  1 min 57 s.

## Render

```bash
cd sample_content/g11-science/G11-MATH-001_Sets_and_Functions/Option3_Video
bun install                                      # one-time
bun run render                                   # → ~/Downloads/Sets_and_Functions_Demo.mp4
# or
bunx remotion render sets-and-functions ~/Downloads/Sets_and_Functions_Demo.mp4
```

The render is CPU-intensive — expect 2–5 minutes on a developer laptop. Run it in the background.

## Studio (live editing)

```bash
bun run studio
# opens http://localhost:3000 with hot-reload
```

## Why a Remotion video?

| Axis | Option 1 (HTML page) | Option 2 (catalogue) | Option 3 (this) |
|---|---|---|---|
| Format | interactive HTML | individual SVGs / MP4s | single MP4 |
| Best for | side-by-side idiom comparison | production-quality individual artifacts | external sharing, decks, intros |
| Install | none | varies (Manim) | Bun, then it's a one-shot render |
| Stays current as content evolves | yes | yes | re-render on demand |

Option 3 plays linearly: title → topic → topic → … → close. It cannot show two idioms side-by-side (that's Option 1's job), but it produces a single artifact that ships into a deck, a website, or a YouTube upload.

## Scene timings (Root.tsx)

| Scene | Frames @ 30 fps | Seconds |
|---|---:|---:|
| Title | 150 | 5.0 |
| Venn (4 ops) | 600 | 20.0 |
| Vertical line test | 300 | 10.0 |
| Arrow diagrams (3) | 450 | 15.0 |
| Composition | 450 | 15.0 |
| Inverse | 360 | 12.0 |
| Transformations (4 steps) | 600 | 20.0 |
| Projectile | 450 | 15.0 |
| Closing | 150 | 5.0 |
| **Total** | **3,510** | **117.0** |

Edit `SCENE` in `src/Root.tsx` to retime any segment; durations propagate to `Video.tsx` via the same constants.

## Caveats

- All animation is `useCurrentFrame()`-driven — no CSS animations, no third-party motion libraries (per Remotion critical rules).
- KaTeX is not used here — math is rendered as plain text + Unicode glyphs to keep the project install-light. If you want true LaTeX rendering, add `katex` and use `dangerouslySetInnerHTML` in scene labels.
- The Bun lockfile lands at `bun.lockb`. Don't commit `node_modules/`; it's already gitignored at the repo root.
