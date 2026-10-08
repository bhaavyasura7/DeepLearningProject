# DESIGN.md — CineMind Film Intelligence System

## Design Language
- **Audited surface:** CineMind Recommendation & Reasoning Dashboard
- **Design system:** shadcn UI component primitives with **Sage Garden** theme registry (`https://tweakcn.com/r/themes/sage-garden.json`)
- **Philosophy:** Restrained, organic, editorial film intelligence interface inspired by the Criterion Collection, Letterboxd Pro, and modern shadcn aesthetics. Zero "vibe-coded" AI slop (no loud purple neon glows, no excessive gradients, no emojis).
- **Theme switchable:** Full support for both **Sage Garden Dark** (deep charcoal slate with sage accents) and **Sage Garden Light** (warm alabaster cream with sage accents) with persistent toggle.

---

## Token Architecture (Sage Garden Theme Registry)

### Theme Coordinates (OKLCH Color Space)
- `--primary`: `oklch(0.6333 0.0309 154.9039)` — Refined, organic sage green
- `--primary-foreground`: Light `oklch(1 0 0)` / Dark `oklch(0 0 0)`
- `--radius`: `0.35rem` — Crisp, modern rounded geometry
- `--font-sans`: `'Antic', 'Inter', -apple-system, sans-serif`
- `--font-mono`: `'JetBrains Mono', Courier New, monospace`
- `--font-serif`: `'Signifier', Georgia, serif`

### Dark Palette (`.dark`)
- `--background`: `oklch(0.1448 0 0)` — Deep charcoal slate
- `--card`: `oklch(0.1822 0 0)` — Elevated container card
- `--border`: `oklch(0.2850 0 0)` — Crisp 1px boundary
- `--input`: `oklch(0.1822 0 0)` — Recessed input container
- `--muted`: `oklch(0.2178 0 0)` — Muted pill backgrounds & secondary states
- `--muted-foreground`: `oklch(0.7058 0 0)` — Secondary telemetry & labels
- `--ring`: `oklch(0.6333 0.0309 154.9039)` — Focus ring with 25% sage glow

### Light Palette (`:root`)
- `--background`: `oklch(0.9761 0.0041 91.4461)` — Warm alabaster cream
- `--card`: `oklch(1.0000 0 0)` — Pure white elevated cards
- `--border`: `oklch(0.9251 0.0071 88.6450)` — Soft warm border
- `--input`: `oklch(1.0000 0 0)` — Clean white input box
- `--muted`: `oklch(0.9251 0.0071 88.6450)` — Muted pill containers
- `--muted-foreground`: `oklch(0.5510 0.0234 264.3637)` — Slate secondary text

---

## shadcn Component Implementations

1. **Button (Default, Ghost, Segmented)**:
   - Primary: `bg-primary text-primary-foreground font-semibold shadow-xs` with subtle scale interaction (`active:scale-[0.98]`).
   - Ghost / Outline: Clean border, hover elevation with `var(--accent)`.
   - Theme Toggle: Minimalist icon button with sun/moon SVG transitions.
2. **Card (Card, CardHeader, CardContent)**:
   - Built on `border border-border bg-card shadow-sm rounded-lg` with hover state elevating border to `var(--primary)`.
3. **Badge & Chips**:
   - `badge` pill primitives with mono typography (`0.72rem`, 600 weight) for `COLD-START`, `HYBRID EXCLUSIVE`, `GRAPH`, and `VECTOR`.
4. **Input & Search Console**:
   - Focus ring using shadcn's `ring-1 ring-ring` with seamless SVG icon slot.
5. **Switch**:
   - shadcn Switch component for `Instant Replay` and `Strict Mode` with smooth translateX animations.
6. **Tabs**:
   - shadcn `TabsList` and `TabsTrigger` layout with `bg-muted` pill container and `bg-card` active pill with shadow.
7. **Telemetry Rail**:
   - 5 distinct stage cards with step badges, status indicators, and expandable code block drawers.
8. **Callout / Blockquote**:
   - Synopsis evidence quotes featuring a 3px solid Sage Green left border with italicized editorial styling.
