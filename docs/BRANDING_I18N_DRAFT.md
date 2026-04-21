# Branding Refresh — FR / ES Translation Drafts

> **Status:** draft translations by Claude (machine-quality). **Needs native-speaker review
> before commit.** This doc is the companion to
> [EPIC_13_branding_refresh.md](epics/EPIC_13_branding_refresh.md) (T-BR-2).
>
> Last updated 2026-04-21.

---

## Scope

Every `web/i18n/*.json` key that currently contains **"STEM" / "STIM" / "tutorat" / "tutoría"**
branding, plus any key where the English is changing (T-BR-5) and the translations must
therefore follow. Keys whose current translation is already neutral (e.g. `social_proof_heading`,
`cta_heading`) are shown for completeness but marked **no change**.

---

## Canonical copy (the source of truth)

After T-BR-5 lands, the English copy will be:

| Key | New English |
|---|---|
| `landing.hero_heading` | `Study Buddy` (brand name — unchanged) |
| `landing.hero_tagline` | `Your bridge from lessons to a world that's always current.` |
| `landing.hero_subheading` | `An AI study buddy that connects your lessons to the world — and keeps learning alongside you.` |
| `landing.features_heading` | `A teacher can set their own study material using AI` (unchanged) |
| `landing.social_proof_heading` | `Trusted by students, teachers, and parents` (unchanged) |
| `landing.cta_heading` | `Ready to get started?` (unchanged) |
| `landing.cta_subheading` | `Join thousands of students mastering their subjects.` (unchanged in English — was never STEM in `en.json`) |
| `tagline` (line 291) | `Your bridge from lessons to a world that's always current.` |

All FR / ES translations below are targeted at **this** English, not the current interim copy.

---

## Structural note — key parity

Before translating, verify that `fr.json` and `es.json` contain the **same keys** as `en.json`.
Based on the 2026-04-21 grep:

- `en.json` has `hero_heading` (brand name) + `hero_tagline` (catchphrase) + `hero_subheading`
- `fr.json` and `es.json` currently **pack the tagline into `hero_heading`** and have no `hero_tagline` key. That is a structural drift, not just a copy issue.

**Action:** T-BR-2 must **add a `hero_tagline` key** to `fr.json` and `es.json` (currently missing),
and split the tagline out of `hero_heading`. Otherwise the landing page will render inconsistently
across locales.

---

## French (fr.json)

| Line | Key | Current FR (STIM/STEM) | Proposed new FR | Notes |
|---|---|---|---|---|
| 29 | `landing.hero_heading` | "Le tutorat STEM disponible dès que les élèves en ont besoin" | **"Study Buddy"** | Brand name — do not translate. Structural change: tagline moves to `hero_tagline`. |
| *(add)* | `landing.hero_tagline` | *(missing — new key)* | **"Votre pont entre vos leçons et un monde toujours actuel."** | Canonical tagline. Alt: *"Le pont entre vos leçons et un monde qui reste actuel."* |
| 30 | `landing.hero_subheading` | "Leçons, quiz et audio instantanés pour les classes 5 à 12. Sans attente. Sans clé API. Juste l'apprentissage." | **"Un compagnon d'apprentissage IA qui relie vos leçons au monde — et qui continue d'apprendre à vos côtés."** | Uses *"compagnon d'apprentissage"* — consistent with the existing hero watermark translation of "StudyBuddy." |
| 31 | `landing.hero_cta_primary` | "Commencer l'essai gratuit" | **no change** | Neutral. |
| 32 | `landing.hero_cta_secondary` | "Voir comment ça marche" | **no change** | Neutral. |
| 33 | `landing.features_heading` | "Tout ce dont les élèves ont besoin pour maîtriser les STIM" | **"Tout ce dont un enseignant a besoin pour créer son matériel pédagogique avec l'IA."** | Mirrors the neutral English; also drops *"STIM"*. Alt closer to EN: *"Un enseignant peut créer son propre matériel pédagogique grâce à l'IA."* |
| 46 | `landing.social_proof_heading` | "Approuvé par les élèves, les enseignants et les parents" | **no change** | Already neutral. |
| 47 | `landing.cta_heading` | "Prêt à commencer ?" | **no change** | Neutral. |
| 48 | `landing.cta_subheading` | "Rejoignez des milliers d'élèves qui améliorent leurs notes en STIM." | **"Rejoignez des milliers d'élèves qui maîtrisent toutes leurs matières."** | Drops *"en STIM"*, mirrors EN's *"mastering their subjects"*. |
| 49 | `landing.cta_btn` | "Démarrer votre essai gratuit" | **no change** | Neutral. |
| 197 | `tagline` | "Tutorat STIM pour les classes 5 à 12" | **"Votre pont entre vos leçons et un monde toujours actuel."** | Canonical tagline. |

---

## Spanish (es.json)

| Line | Key | Current ES (STEM) | Proposed new ES | Notes |
|---|---|---|---|---|
| 29 | `landing.hero_heading` | "Tutoría STEM disponible en el momento en que los estudiantes la necesitan" | **"Study Buddy"** | Brand name — do not translate. Structural change: tagline moves to `hero_tagline`. |
| *(add)* | `landing.hero_tagline` | *(missing — new key)* | **"Tu puente entre las lecciones y un mundo siempre actual."** | Canonical tagline. Alt: *"El puente entre tus lecciones y un mundo que se mantiene actual."* |
| 30 | `landing.hero_subheading` | "Lecciones, cuestionarios y audio instantáneos para los grados 5 a 12. Sin esperas. Sin claves de API. Solo aprendizaje." | **"Un compañero de aprendizaje con IA que conecta tus lecciones con el mundo — y sigue aprendiendo a tu lado."** | Uses *"compañero de aprendizaje"* — consistent with the existing hero watermark translation of "StudyBuddy." |
| 31 | `landing.hero_cta_primary` | "Comenzar prueba gratuita" | **no change** | Neutral. |
| 32 | `landing.hero_cta_secondary` | "Ver cómo funciona" | **no change** | Neutral. |
| 33 | `landing.features_heading` | "Todo lo que los estudiantes necesitan para dominar STEM" | **"Un profesor puede crear su propio material de estudio con IA."** | Mirrors neutral EN. Alt: *"Todo lo que un profesor necesita para crear su material con IA."* |
| 46 | `landing.social_proof_heading` | "Confiado por estudiantes, profesores y padres" | **no change** *(minor: could polish to "De confianza para…")* | Already neutral; minor polish optional. |
| 47 | `landing.cta_heading` | "¿Listo para comenzar?" | **no change** | Neutral. |
| 48 | `landing.cta_subheading` | "Únete a miles de estudiantes que mejoran sus calificaciones en STEM." | **"Únete a miles de estudiantes que dominan todas sus materias."** | Drops *"en STEM"*, mirrors EN's *"mastering their subjects"*. |
| 49 | `landing.cta_btn` | "Comienza tu prueba gratuita" | **no change** | Neutral. |
| 197 | `tagline` | "Tutoría STEM para los grados 5 a 12" | **"Tu puente entre las lecciones y un mundo siempre actual."** | Canonical tagline. |

---

## Translation quality caveats

The translations above were drafted by Claude. They are **grammatically correct and
semantically faithful**, but may not be **idiomatically optimal** for native speakers.
Specific flags for a reviewer to consider:

| Concern | FR | ES |
|---|---|---|
| Bridge metaphor idiom | *"Votre pont entre"* is direct and works, but a native speaker may prefer *"Le pont entre…"* (with article) or a metaphor that reads more naturally in French — e.g. *"Le lien entre vos leçons et le monde actuel."* | *"Tu puente entre"* works. Native speakers may prefer *"El puente entre…"* (article) or *"El enlace entre…"* (the link between). |
| "Always current" | *"toujours actuel"* is clear but slightly literal; alternatives: *"qui reste actuel"*, *"toujours d'actualité"* | *"siempre actual"* is clear; alternatives: *"que se mantiene al día"*, *"siempre al día"* |
| "AI study buddy" | *"compagnon d'apprentissage IA"* — "IA" adjective placement after the noun is idiomatic; *"compagnon IA d'apprentissage"* would be wrong. | *"compañero de aprendizaje con IA"* — using *con IA* (with AI) is cleaner than *de IA*. |
| Em-dash rendering | French typographic convention uses spaces around em-dashes (` — `). Confirm the existing JSON preserves this. | Spanish convention also uses ` — `. Confirm. |

**Recommendation:** ship T-BR-5 (English) first; then have a native French speaker and a native
Spanish speaker each do a 15-minute review of this table before T-BR-2 lands. Much cheaper than
a post-launch rewrite if a translation reads off to a user.

---

## Quick links

- Epic & tickets: [EPIC_13_branding_refresh.md](epics/EPIC_13_branding_refresh.md)
- Full decision log: [BRANDING_TAGLINE_OPTIONS.md](BRANDING_TAGLINE_OPTIONS.md)
