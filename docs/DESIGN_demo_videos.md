# Design — Demo Site Feature Videos

**Status:** Draft v0.1 (design only — not yet implemented)
**Date:** 2026-05-09
**Author:** Sivakumar (with Claude design assist)
**Companion docs:**
- [`DESIGN_demo_request_access.md`](./DESIGN_demo_request_access.md) — the self-service 7-day-trial flow (the CTA these videos funnel into)
- [`DEMO_LAUNCH_PLAN.md`](./DEMO_LAUNCH_PLAN.md) — the May 17 launch runbook

> **Long-term framing.** `demo.studybuddy.app` is a permanent demo
> environment (per the request-access doc). These videos are content,
> not implementation scaffolding — once dropped in, they age well with
> minimal maintenance, and the section structure can absorb new videos
> without a redesign.

---

## 1 · What it is

A pair of new sections on the `demo.studybuddy.app` home page that let
any visitor watch pre-recorded videos of the product:

1. **"See StudyBuddy in action"** — a small grid of polished feature
   videos (the BioStory + ChemStory). Click → modal lightbox player.
2. **"Visual content the platform generates"** — a horizontal strip of
   short auto-looping muted clips that show the AI-generated visuals
   the platform produces (the four Hydrocarbon clips).

Both sections sit **above** the Request-Demo CTA (per
`DESIGN_demo_request_access.md`), forming a natural funnel:
*watch → get convinced → request 7-day trial*.

**Privacy posture:** no per-viewer tracking, no third-party embed
(YouTube/Vimeo), no analytics. nginx access log records the same IPs
as any other page request — no user-scoped data.

## 2 · Asset inventory (already produced)

All six MP4 files are local at `/home/sivam/Downloads/mp4files/`.
Total **36 MB** — well under the 500 MB / CX22-bandwidth ceiling.

| File | Size | Role |
|---|---|---|
| `StudyBuddy_BioStory.mp4` | 15 MB | Feature/story video — biology |
| `StudyBuddy_ChemStory.mp4` | 15 MB | Feature/story video — chemistry |
| `Hydrocarbon_SingleBond.mp4` | 2.1 MB | Sample lesson visual — single bond |
| `Hydrocarbon_DoubleBond.mp4` | 1.7 MB | Sample lesson visual — double bond |
| `Hydrocarbon_TripleBond.mp4` | 1.5 MB | Sample lesson visual — triple bond |
| `Hydrocarbon_Aromatic.mp4` | 1.7 MB | Sample lesson visual — aromatic ring |

Estimated runtimes (from file size ÷ ~2 Mbps web-video bitrate):

- BioStory + ChemStory: ~1–2 min each
- Hydrocarbon clips: ~6–12 sec each

These are estimates only — confirm with `ffprobe` once it's installed
locally. Doesn't change the design.

## 3 · Why two sections (not one grid)

The naming pattern splits cleanly into two audiences with different
playback expectations:

| Story videos (BioStory, ChemStory) | Hydrocarbon clips |
|---|---|
| 1–2 min each, narrated | 6–12 sec each, silent |
| Audio-with-controls is essential | Audio + controls would be friction |
| Visitor watches one in full, then the next | Visitor glances at the strip while reading |
| Click-to-play modal is the right shape | Auto-loop inline is the right shape |

A single mixed grid would either force the hydrocarbon clips into a
modal (bad — the visitor doesn't want a 6-sec clip in a modal) or strip
the controls off the story videos (bad — they have narration). Splitting
them is the right call.

## 4 · Home page section order

```
1. Hero / tagline (whatever exists today)

2. ▶ See StudyBuddy in action               ← NEW (§5)
   ┌─────────────┐  ┌─────────────┐
   │  BioStory   │  │  ChemStory  │         (modal player)
   │  ▶ ~2 min   │  │  ▶ ~2 min   │         (click → lightbox + audio)
   └─────────────┘  └─────────────┘

3. Visual content the platform generates    ← NEW (§6)
   ┌────┐ ┌────┐ ┌────┐ ┌────┐
   │Sing│ │Dbl │ │Trip│ │Arom│              (auto-loop, muted, no controls)
   └────┘ └────┘ └────┘ └────┘              (4 hydrocarbon clips)

4. ┌──────────────────────────────────────┐
   │ Want to try it yourself?             │ ← existing CTA
   │ [Request 7-day demo →]               │   (per DESIGN_demo_request_access.md)
   └──────────────────────────────────────┘

5. Footer (whatever exists today)
```

## 5 · Section A — "See StudyBuddy in action" (story videos)

### Visitor experience

Click thumbnail → modal lightbox opens with native HTML5 player →
autoplay with audio + controls → close (× button or click outside) →
back to home page, scroll position preserved.

### Component sketch

```tsx
const [openSlug, setOpenSlug] = useState<string | null>(null);
const open = featureVideos.find(v => v.slug === openSlug);

return (
  <section className="py-16">
    <h2 className="text-3xl font-bold text-center">See StudyBuddy in action</h2>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10">
      {featureVideos.map(v => (
        <button
          key={v.slug}
          onClick={() => setOpenSlug(v.slug)}
          className="group relative rounded-lg overflow-hidden …"
        >
          <img src={v.thumb} alt="" className="w-full aspect-video object-cover" />
          <div className="absolute inset-0 flex items-center justify-center
                          bg-black/30 group-hover:bg-black/40 transition">
            <PlayIcon className="w-16 h-16 text-white" />
          </div>
          <div className="p-4">
            <h3 className="font-bold">{v.title}</h3>
            <p className="text-sm text-muted">{v.description}</p>
          </div>
        </button>
      ))}
    </div>

    {open && (
      <Dialog onClose={() => setOpenSlug(null)}>
        <video
          src={open.src}
          controls
          autoPlay
          playsInline       // iOS Safari: required, otherwise full-screen takeover
          preload="metadata"
          className="w-full max-w-4xl"
        />
      </Dialog>
    )}
  </section>
);
```

### Why native `<video controls>`

Zero new JS deps. Accessible by default (keyboard, screen-reader, and
captions all work via the standard `<track>` element). Adaptive bitrate
isn't needed for two short MP4s; video.js / plyr / shaka would be
overkill.

### Captions / accessibility

Adding `<track kind="captions" src="/videos/biostory.vtt" srclang="en" default>`
inside the `<video>` element is one extra line per video. **Strongly
recommended** — both for accessibility and because screen-reader / muted
viewers (~20% of social-style watchers) can still get the message. WebVTT
files are small text; commit them in `web/public/videos/captions/`.

If captions aren't ready by launch, ship without them and add later —
no architectural change needed.

## 6 · Section B — "Visual content the platform generates" (hydrocarbon clips)

### Visitor experience

The four clips render inline, muted, auto-looping, no controls. Like
animated GIFs but lighter and crisper. Visitor scans the strip while
reading the section heading; nothing to click.

### Component sketch

```tsx
return (
  <section className="py-12 bg-muted/5">
    <div className="text-center mb-8">
      <h2 className="text-2xl font-bold">Visual content the platform generates</h2>
      <p className="text-muted mt-2 max-w-2xl mx-auto">
        StudyBuddy renders concept-specific visuals as part of every lesson.
        Here are real organic-chemistry visuals from the Grade 11 Science
        curriculum.
      </p>
    </div>

    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
      {sampleVisuals.map(v => (
        <figure key={v.slug} className="rounded-lg overflow-hidden border">
          <video
            src={v.src}
            autoPlay loop muted playsInline
            className="w-full aspect-square object-cover"
            aria-label={v.alt}
          />
          <figcaption className="p-2 text-xs text-center text-muted">
            {v.label}
          </figcaption>
        </figure>
      ))}
    </div>
  </section>
);
```

### Why auto-loop muted, not modal

These are the *content* the platform produces, not feature demos.
A 6-second clip behind a modal click means the visitor has to *intend
to watch it*; on auto-loop, they absorb it passively while reading.
Same reason marketing pages auto-loop product-screenshot reels — the
asset is doing the talking.

`muted` is required for browser autoplay policies (Chrome, Safari,
Firefox all block autoplay-with-sound on first visit). `playsInline`
keeps iOS Safari from full-screen-taking-over.

### Accessibility

The figcaption + `aria-label` carry the meaning for screen readers.
The clips themselves have no audio, so no captions needed.

If the looping motion is a problem for users with vestibular
sensitivity, future enhancement: respect `prefers-reduced-motion` and
fall back to a static first-frame image. Out of scope for v1.

## 7 · File layout

```
StudyBuddy_OnDemand/
├── web/
│   ├── public/
│   │   └── videos/
│   │       ├── thumbs/
│   │       │   ├── biostory.jpg              ← committed (~100 KB)
│   │       │   └── chemstory.jpg             ← committed (~100 KB)
│   │       ├── captions/                     ← optional
│   │       │   ├── biostory.vtt              ← committed (small text)
│   │       │   └── chemstory.vtt             ← committed (small text)
│   │       └── README.md                     ← "MP4s NOT in git; see §10"
│   └── data/
│       └── demo-videos.json                  ← committed manifest (§8)
├── scripts/
│   └── demo/
│       └── sync-videos.sh                    ← one-shot rsync (§10)
└── .gitignore
    + web/public/videos/*.mp4                 ← exclude binary blobs

# On the VPS:
/data/videos/
├── StudyBuddy_BioStory.mp4
├── StudyBuddy_ChemStory.mp4
├── Hydrocarbon_SingleBond.mp4
├── Hydrocarbon_DoubleBond.mp4
├── Hydrocarbon_TripleBond.mp4
└── Hydrocarbon_Aromatic.mp4
```

**Why MP4s are not committed.** Even at 36 MB total, MP4 binaries bloat
git history (every `git clone` pulls them; every checkout copies them)
and rebase/merge mechanics on binaries are pointless. Thumbnails (~100 KB
each, 2 files) and WebVTT captions (text) ARE committed — they're small
and the build needs them.

**Why thumbnails commit, MP4s don't.** Thumbnails are render-time assets
(the home page needs them on first paint, before the visitor clicks).
MP4s are play-time assets (only fetched if the visitor clicks). Different
delivery requirements → different storage strategies.

## 8 · Manifest — `web/data/demo-videos.json`

Single declarative source. Adding a new video = drop the file, drop the
thumb, append one entry, push.

```json
{
  "feature_videos": [
    {
      "slug": "biostory",
      "title": "StudyBuddy: Biology",
      "description": "How a Grade 11 biology lesson comes together — content, visuals, voiceover.",
      "thumb": "/videos/thumbs/biostory.jpg",
      "src": "/videos/StudyBuddy_BioStory.mp4",
      "captions": "/videos/captions/biostory.vtt"
    },
    {
      "slug": "chemstory",
      "title": "StudyBuddy: Chemistry",
      "description": "From an organic-chemistry concept to a fully-rendered lesson with quizzes.",
      "thumb": "/videos/thumbs/chemstory.jpg",
      "src": "/videos/StudyBuddy_ChemStory.mp4",
      "captions": "/videos/captions/chemstory.vtt"
    }
  ],

  "sample_visuals": [
    { "slug": "hc-single",   "label": "Single bond",   "alt": "Single bond animation",   "src": "/videos/Hydrocarbon_SingleBond.mp4" },
    { "slug": "hc-double",   "label": "Double bond",   "alt": "Double bond animation",   "src": "/videos/Hydrocarbon_DoubleBond.mp4" },
    { "slug": "hc-triple",   "label": "Triple bond",   "alt": "Triple bond animation",   "src": "/videos/Hydrocarbon_TripleBond.mp4" },
    { "slug": "hc-aromatic", "label": "Aromatic ring", "alt": "Aromatic ring animation", "src": "/videos/Hydrocarbon_Aromatic.mp4" }
  ]
}
```

## 9 · nginx delta

In the host vhost (sibling of `mambakkam-net`'s vhost — see
`DEMO_LAUNCH_PLAN.md` §0):

```nginx
location /videos/ {
    alias /data/videos/;
    autoindex off;

    # Long-cache (videos rarely change; if a file is replaced under the
    # same filename, deploy a cache-bust query param via the manifest)
    add_header Cache-Control "public, max-age=2592000" always;   # 30 days

    # Range requests for video seeking
    add_header Accept-Ranges bytes always;

    # Optional: skip access log for video requests if you want zero
    # per-IP signal on these endpoints. Default off — access log is fine.
    # access_log off;
}
```

This is one block. Mirrors the `/_astro/*` long-cache pattern in
`infra/nginx/mambakkam.net.conf`.

## 10 · Deploy mechanics — `scripts/demo/sync-videos.sh`

```bash
#!/usr/bin/env bash
# scripts/demo/sync-videos.sh — one-shot rsync of demo videos to the VPS
#
# Run from the operator's laptop after recording / updating videos.
# Not part of the auto-deploy workflow — videos are rare changes;
# pulling them on every push would waste CI minutes and bandwidth.
#
# Usage:
#   bash scripts/demo/sync-videos.sh
#   # or with a custom source dir:
#   bash scripts/demo/sync-videos.sh ~/Downloads/mp4files/

set -euo pipefail

SRC="${1:-$HOME/Downloads/mp4files}"
HOST="${DEMO_VPS_HOST:-deploy@demo.studybuddy.app}"
DEST="/data/videos/"

echo "[info] syncing $SRC → $HOST:$DEST"
rsync -avz --delete \
  --include='*.mp4' --exclude='*' \
  "$SRC/" "$HOST:$DEST"

echo "[info] verifying:"
ssh "$HOST" "ls -lh $DEST"
```

Run once after recording a new batch; not on every deploy.

## 11 · Thumbnail extraction (one-time, local)

ffmpeg isn't installed on the dev machine yet (confirmed 2026-05-09).
One-time setup before extracting thumbnails:

```bash
sudo apt install ffmpeg

# Extract a frame ~3 seconds in (skips any title-card / fade-in)
cd ~/Downloads/mp4files/

ffmpeg -ss 00:00:03 -i StudyBuddy_BioStory.mp4 -vframes 1 \
       -q:v 2 ~/code/.../web/public/videos/thumbs/biostory.jpg

ffmpeg -ss 00:00:03 -i StudyBuddy_ChemStory.mp4 -vframes 1 \
       -q:v 2 ~/code/.../web/public/videos/thumbs/chemstory.jpg
```

`-q:v 2` keeps quality high (smaller is better quality on the 1–31 scale).

The hydrocarbon clips don't need thumbnails — they auto-loop, so the
first frame is the visible thumbnail by definition.

## 12 · Privacy posture

| Concern | Posture |
|---|---|
| Third-party tracking (YouTube / Vimeo) | None — self-hosted MP4s only |
| Per-viewer analytics | None — nginx access log records the IP and path; same as any page request, not user-tied |
| Cookies | None set by video playback |
| Cross-site request leakage | None — `/videos/*` is on the same origin |
| Aggregate "is anyone watching" signal | Available via grep of nginx access log if needed: `grep '/videos/.*\.mp4' /var/log/nginx/demo.studybuddy.app.access.log \| awk '{print $7}' \| sort \| uniq -c` |

If you want **zero** signal on these endpoints (paranoia mode): set
`access_log off;` inside the `/videos/` location block. Default is
"keep the log" — useful for debugging.

## 13 · Build estimate

| Piece | Effort |
|---|---|
| ffmpeg install + thumbnail extraction (2 thumbs) | 15 min |
| `web/data/demo-videos.json` manifest | 10 min |
| `<DemoVideoGrid>` (modal player) component | 1–2 hr |
| `<SampleVisualsStrip>` (auto-loop) component | 30 min |
| Wire both into the demo home page in the chosen order | 30 min |
| nginx vhost update (`/videos/` location block) | 10 min |
| `scripts/demo/sync-videos.sh` | 15 min |
| First sync of MP4s to VPS | 5 min |
| (Optional) WebVTT captions for the 2 story videos | 1–2 hr each, depends on length |

**Total: ~half a day** without captions. Captions add 2–4 more hours
if you author them; can be deferred.

## 14 · What's already in place vs. what to build

| Already there | Needs to be built |
|---|---|
| Six MP4 files at `/home/sivam/Downloads/mp4files/` (36 MB total) | Two React components (modal player + auto-loop strip) |
| `demo.studybuddy.app` host nginx (per `DEMO_LAUNCH_PLAN.md`) | One `location /videos/` block in the host vhost |
| `/data/` directory pattern on the VPS (already used for content) | `/data/videos/` directory + initial rsync |
| Auth-free public landing page | Two new home-page sections + manifest JSON |
| | Two thumbnail JPGs (one-time ffmpeg extract) |
| | `scripts/demo/sync-videos.sh` (one-shot, not in CI) |
| | (Optional) WebVTT captions per story video |

## 15 · Out of scope

- **Adaptive bitrate / multi-resolution variants.** 36 MB at one
  resolution is fine for the launch audience. If CDN delivery becomes
  a bottleneck, migrate to Cloudflare Stream (~$5/mo) — drop-in URL
  swap, no architectural change.
- **Video search / categorization page.** Two videos doesn't need a
  catalogue. Revisit at 10+ videos.
- **User-uploaded videos / community submissions.** This design is
  read-only marketing assets. User uploads would be a separate feature
  with auth, moderation, storage quotas.
- **Picture-in-picture / mini-player.** Native `<video controls>`
  supports it on most browsers via the right-click menu — not styled,
  but functional. Don't custom-build.
- **Engagement analytics ("how many people watched 50% of the video?").**
  Explicitly excluded by the user's "no per-viewer tracking" stance.
  Aggregate plays from the nginx log is the only available signal.

## 16 · Open small decisions

These can be deferred to implementation time but are flagged here:

1. **Section copy.** Working titles in this doc are
   *"See StudyBuddy in action"* and *"Visual content the platform
   generates"*. Final copy is a marketing call — confirm or revise
   when wiring in.
2. **Captions priority.** Ship without captions on day 1, or block on
   them? Lean ship-without; add later. Strongly recommended for v2.
3. **Thumbnail timestamp.** `00:00:03` is a reasonable default to skip
   any title card. Eyeball the first 5 seconds of each MP4 and pick the
   most visually compelling frame.
4. **Hydrocarbon clip ordering.** Manifest defaults to single → double
   → triple → aromatic (logical chemistry progression). Confirm the
   pedagogical order matches the curriculum.
5. **Captions hosting if added.** WebVTT files commit to git
   (`web/public/videos/captions/`) — small text, build needs them.

## Change Log

| Date | Version | Change |
|---|---|---|
| 2026-05-09 | 0.1 | Initial design — six existing MP4s split into Story (modal) + Hydrocarbon (auto-loop) sections; both above the Request-Demo CTA from `DESIGN_demo_request_access.md`. Self-hosted on the CX22; no third-party embeds; ~half-day implementation. |
