# Visual Library Sidecar — `*.metadata.yaml` Contract

Every visual asset that should be promoted into the platform-curated visual library carries a sibling `*.metadata.yaml` file. The promotion CI step (issue #322) validates the sidecar before uploading the asset and inserting a `visual_library_entries` row.

> Authoring is **opt-in per asset** — assets without a sidecar are *not* promoted. This is by design: not every SVG in `sample_content/` deserves to be a library entry.

## File location

```
sample_content/<curriculum>/<unit>/Option2_Catalogue/<section>/<slug>.<ext>
sample_content/<curriculum>/<unit>/Option2_Catalogue/<section>/<slug>.metadata.yaml
```

The sidecar lives next to the asset and shares the asset's basename. Example:

```
sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-4-projectile/trajectory.svg
sample_content/g11-science/G11-PHYS-002_Kinematics/Option2_Catalogue/section-4-projectile/trajectory.metadata.yaml
```

## Schema

```yaml
# Schema version 1 — bump only via PR + a corresponding validator update.
schema_version: 1

# Globally unique slug. Convention: <subject>-<topic-slug>-<feature>.
# Format: lowercase alphanumerics + hyphens, max 80 chars.
id: physics-kinematics-projectile-trajectory

# What kind of visual this asset is.
# image          static raster or vector image (single)
# image-grid     intended to be displayed alongside siblings as a grid
# animated-svg   SVG with SMIL animation
# video          MP4 / WebM
kind: image

# Closed-enum subject. To add a new subject, edit:
#   - backend/src/visuals/library.py::SUBJECTS
#   - this validator's SUBJECTS constant
#   - the visual_library_entries table doesn't enforce this — the validator does.
subject: physics

# Human-readable topic. Used for resolver semantic-match and admin search.
topic_phrase: "projectile motion"

# Lowercase tokens that supplement topic_phrase for keyword search and
# embedding text. Non-empty; treat as alternates / contextual cues.
keywords:
  - projectile
  - trajectory
  - parabola
  - range
  - max-height

# License string. Closed enum.
#   platform-cc-by-sa     authored by the platform team, CC-BY-SA
#   platform-proprietary  authored by the platform team, proprietary
license: platform-cc-by-sa

# Optional — the unit_id this asset was originally authored for.
# Surfaced in the admin UI so curators can trace the asset's origin.
source_unit: G11-PHYS-002
```

## Field rules (validator-enforced)

| Field | Type | Required | Validation |
|---|---|---|---|
| `schema_version` | int | yes | Must be `1`. Future versions will live alongside via a discriminator. |
| `id` | str | yes | `^[a-z0-9-]+$`, max 80 chars, globally unique across all sidecars in the working tree. |
| `kind` | str | yes | One of `image`, `image-grid`, `animated-svg`, `video`. |
| `subject` | str | yes | One of the closed `SUBJECTS` enum (physics / chemistry / math / biology / geography / history / languages). |
| `topic_phrase` | str | yes | Non-empty, ≤ 200 chars. |
| `keywords` | list[str] | yes | Non-empty list. Each token: lowercase alphanumerics + hyphens, no spaces. |
| `license` | str | yes | One of `platform-cc-by-sa`, `platform-proprietary`. |
| `source_unit` | str | no | If present, conventionally a unit_id like `G11-PHYS-002`. |

### Filesystem rules

- The sibling asset file (same basename, kind-appropriate extension) must exist.
- Extension must match `kind`:

| `kind` | Allowed extensions |
|---|---|
| `image` | `.svg` `.png` `.jpg` `.jpeg` `.webp` |
| `image-grid` | same as `image` |
| `animated-svg` | `.svg` only |
| `video` | `.mp4` `.webm` |

## Authoring workflow

1. Drop the asset and the sidecar into a section folder under `Option2_Catalogue/`.
2. Run the local validator to catch obvious errors before pushing:
   ```bash
   bun scripts/validate_library_metadata.ts \
     sample_content/**/Option2_Catalogue/**/*.metadata.yaml
   ```
3. Open a PR. The promotion workflow (`promote_visual_library.yml`) re-validates everything and uploads the asset + INSERTs the library row on merge to `main`.

## Re-promoting an existing asset

The promotion workflow is **idempotent**: the same `id` UPSERTs (replacing the row's metadata + re-uploading the asset). Re-promotion is the path for "I improved the SVG; bump the same library entry." Use a *new* `id` only when the asset has fundamentally different semantics — otherwise re-using the id keeps existing tutorial JSON references stable.

## Cross-references

- Schema: `backend/src/visuals/library.py::LibraryEntry` + migration 0056/0057
- Validator: `scripts/validate_library_metadata.ts` (#322)
- Promotion workflow: `.github/workflows/promote_visual_library.yml` (#322)
- Resolver: `backend/src/visuals/resolver.py` (#323) — consumes the embedding computed from `topic_phrase + keywords` at promotion time
