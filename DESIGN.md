# DESIGN.md — CineMind Design System

## Design language
- Audited surface: CineMind Recommendation & Reasoning Dashboard
- Design sources: `src/cinemind/static/style.css`, `src/cinemind/static/index.html`
- Documented decisions: Modern dark observatory theme with high-contrast semantics, strict accessibility, `h-dvh` responsive shell, and GPU-composited animations.
- Governing owners: CineMind UI Engine
- Explicit exceptions: None documented

## Token Architecture

### Colors & Surfaces
- `--bg-canvas`: `hsl(224, 25%, 5%)` (#090b10) — Main canvas deep obsidian
- `--bg-surface`: `hsl(224, 20%, 9%)` (#10141d) — Elevated container background
- `--bg-card`: `hsl(224, 18%, 13%)` (#19202e) — Card surface with subtle translucency
- `--bg-card-hover`: `hsl(224, 18%, 17%)` (#232c3f) — Hover state elevation
- `--border-subtle`: `hsl(224, 15%, 20%)` (#2a3449) — Base structural borders
- `--border-active`: `hsl(260, 80%, 65%)` (#8b5cf6) — Active / focus border
- `--text-primary`: `hsl(220, 20%, 98%)` (#f8fafc) — Primary high-contrast typography
- `--text-secondary`: `hsl(220, 14%, 72%)` (#a0aec0) — Supporting copy & subtitles
- `--text-muted`: `hsl(220, 12%, 50%)` (#718096) — Meta labels & footnotes

### Semantic Accents
- `--accent-purple`: `hsl(265, 89%, 66%)` (#8b5cf6) — Primary brand & reasoning agent highlight
- `--accent-cyan`: `hsl(188, 86%, 53%)` (#06b6d4) — Graph traversal & discovery chip
- `--accent-emerald`: `hsl(158, 64%, 52%)` (#10b981) — Verified match & exact quote evidence
- `--accent-amber`: `hsl(38, 92%, 50%)` (#f59e0b) — Cold-start new movie highlight & warning
- `--accent-rose`: `hsl(350, 89%, 60%)` (#f43f5e) — Rejection & constraint violation

### Typography
- Primary UI: `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- Display / Headings: `Outfit, Inter, sans-serif`
- Code / Badges / Metrics: `"JetBrains Mono", "Fira Code", monospace`

### Motion & Composite Constraints (Baseline UI)
- All transitions constrained to `transform` and `opacity`. Zero layout-thrashing animations on `height`/`width`.
- Transition duration: `150ms` (hover) to `250ms` (stage transitions) with `cubic-bezier(0.16, 1, 0.3, 1)`.
- Viewport unit: `h-dvh` / `min-h-dvh` to prevent mobile address bar jumping.
