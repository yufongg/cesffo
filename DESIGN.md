# Design System

## Visual Direction

**Sumi & Washi:** Japanese minimalism (wabi-sabi calm). Ink-on-paper restraint — a light, neutral field carrying small, deliberate earthen accents, mended with the occasional **kintsugi** gold seam. A serene, uncluttered space for focused financial learning.

Anchored on four natural swatches, plus a precious gold for the seams:
- **Sumi ink** `#231d1c` — text and headings
- **Washi paper** `#e2e3de` — the page ground
- **Tatami taupe** `#97876e` — warm accents, brand mark
- **Matcha** `#bdbf7f` — sparing highlight
- **Kintsugi gold** `oklch(76% 0.12 84)` — precious joinery: hairline dividers, page accents, the brand seam

**Emotional profile:** Serene. Grounded. Warm.

**Color strategy:** Restrained (product default). The field is warm light neutral; one walnut brand tone carries interaction (buttons, links, active states); matcha and kintsugi gold appear only as sparing accents — gold strictly as thin decorative seams (the philosophy of *kintsugi*: repairing with gold so the join is celebrated, not hidden), never as fills or body text. All values in OKLCH; every text pairing verified for WCAG AA.

---

## Color Palette

All colors use **OKLCH color space** for perceptually uniform scales.

### Light Theme (Default)

#### Primary Brand Color
**Walnut** — the tatami taupe darkened so one token works as both button fill (white text, 6.0:1) and link/text on the light field (4.7:1 on washi). Restrained use (≤10% of colored elements); the color serves interaction, not decoration. `--color-on-primary` holds the text color that sits on brand surfaces (white in light theme, ink in dark).

| Token | OKLCH | Usage |
|-------|-------|-------|
| `--color-primary` | `oklch(50% 0.052 72)` | Primary buttons, links, active states |
| `--color-primary-dark` | `oklch(43% 0.052 72)` | Hover, pressed, active nav |
| `--color-primary-hover` | `oklch(46% 0.052 72)` | Interactive feedback |
| `--color-primary-light` | `oklch(63% 0.045 78)` | Tatami taupe (`#97876e`) — soft accents, brand mark |
| `--color-primary-50` | `oklch(95% 0.012 88)` | Faintest background wash |
| `--color-primary-100` | `oklch(90% 0.022 86)` | Light tint — focus ring |
| `--color-on-primary` | `#fff` (light) / `oklch(22% 0.01 40)` (dark) | Text on brand surfaces |

#### Accent Color
**Matcha** `#bdbf7f` — reserved for sparing highlights, selected states, and success harmony. Note: only dark (`--color-ink`) text on matcha passes contrast; white fails (1.9:1).

| Token | OKLCH | Usage |
|-------|-------|-------|
| `--color-accent` | `oklch(79% 0.084 110)` | Highlight chips, XP, accents |
| `--color-accent-dark` | `oklch(55% 0.075 118)` | Deep matcha — accent text on light |

#### Kintsugi Gold (decorative seam only)
Real metallic gold — the lacquer of kintsugi. Used only on hairline dividers, page-title accents, the footer rule, the eyebrow tick, and the brand seal's vein. **Never a fill, never body text.** `--color-gold-deep` is the one tone that passes contrast (≈4.6:1 on washi) for any rare small-text use.

| Token | OKLCH (light) | Usage |
|-------|---------------|-------|
| `--color-gold` | `oklch(76% 0.120 84)` | Gold leaf — seam base, footer headings |
| `--color-gold-soft` | `oklch(84% 0.085 88)` | Highlight within the lacquer gradient |
| `--color-gold-deep` | `oklch(50% 0.095 78)` | Antique gold — contrast-safe text (≈4.6:1) |
| `--gradient-gold` | highlight → leaf → antique | Seam gradient (stat-card / account-level / section rules) |
| `--gold-line` | horizontal gold fade | Page-header & footer hairline seams |

In dark mode the gold brightens (`--color-gold: oklch(82% 0.115 86)`) so it keeps glinting on the tea-room ground.

#### Neutrals
Sumi ink on washi paper. Warm, very low chroma — no cool grays or blue-tints.

| Token | OKLCH | Contrast | Usage |
|-------|-------|----------|-------|
| `--color-ink` | `oklch(24% 0.010 30)` | 12.9:1 on washi | Headings, emphasis (sumi) |
| `--color-text` | `oklch(31% 0.012 38)` | ~10:1 | Body text |
| `--color-muted` | `oklch(47% 0.025 62)` | 5.0:1 | Secondary text, metadata |
| `--color-faint` | `oklch(50% 0.020 62)` | 4.6:1 | Placeholders, hints (kept ≥4.5) |
| `--color-border` | `oklch(83% 0.012 100)` | — | Hairline borders, dividers |
| `--color-border-strong` | `oklch(76% 0.015 92)` | — | Stronger borders, separators |
| `--color-bg` | `oklch(91% 0.008 112)` | — | Page ground (washi `#e2e3de`) |
| `--color-surface` | `oklch(95.5% 0.006 110)` | — | Cards, panels (lifted washi) |
| `--color-surface-alt` | `oklch(87% 0.010 105)` | — | Fills, hover backgrounds |

#### Status Colors
Natural, low-neon, harmonized with the earth palette.

| Token | OKLCH | Usage |
|-------|-------|-------|
| `--color-success` | `oklch(52% 0.090 138)` | Success — moss green |
| `--color-success-bg` | `oklch(93% 0.030 132)` | Success background tint |
| `--color-danger` | `oklch(52% 0.130 28)` | Error — muted terracotta |
| `--color-danger-bg` | `oklch(93% 0.035 30)` | Error background tint |
| `--color-warning` | `oklch(60% 0.100 72)` | Warning — ochre |
| `--color-warning-bg` | `oklch(93% 0.035 78)` | Warning background tint |

#### Semantic Aliases
| Token | Usage |
|-------|-------|
| `--color-link` | Links (defaults to `--color-primary`) |
| `--surface-translucent` | Navbar backdrop (warm white with blur) |
| `--footer-bg` | Footer background (very dark warm) |
| `--footer-text` | Footer text |
| `--footer-heading` | Footer headings |
| `--footer-muted` | Footer metadata |
| `--footer-border` | Footer dividers |

### Dark Theme — "Sumi Night"

A warm tea-room dark, never black or blue. The page sits at `oklch(24% 0.012 50)` (warm sumi-brown); surfaces lift in warm steps. The walnut brand **lightens to tatami** (`oklch(72% 0.060 78)`) so it reads on dark, and `--color-on-primary` flips to ink so button labels stay legible on the now-light brand fill. Matcha and status colors lift in lightness for visibility.

**Principle:** Warm throughout both themes. Never cool gray-blue or harsh black; always soft, natural warm tones. Dark mode feels like a dimly-lit tea room, not a pitch-black interface.

---

## Typography

### Font Stack
- **Display/Headings:** Fraunces (soft "old-style" serif, optical sizing, 600-800 weight)
- **Body/UI:** Inter (humanist sans-serif, 400-600 weight)

**Why this pair:** Serif + sans is a true contrast axis — not two near-identical sans-serifs, which read as an accident rather than a choice. Fraunces' soft, slightly calligraphic terminals echo sumi brush-ink and give headings a calm, editorial warmth; Inter keeps body and UI crisp and neutral. `font-optical-sizing: auto` lets Fraunces lower its stroke contrast at small sizes and open up for display headings. Headings use `text-wrap: balance`; long prose uses `text-wrap: pretty`.

### Scale
Fixed rem scale (no fluid type in product UI).

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| h1 | 28px | 600 | 1.18 | Page titles |
| h2 | 24px | 600 | 1.18 | Section heads |
| h3 | 20px | 600 | 1.18 | Subsection |
| h4 | 16px | 600 | 1.18 | Card titles |
| Body | 16px | 400 | 1.6 | Paragraph, data |
| Small | 14px | 500 | 1.5 | Labels, secondary |
| Tiny | 12px | 600 | 1.4 | Metadata, hints |

### Accessibility
- **Body measure:** 65–75 characters max (container max-width: 1120px)
- **Text on colored backgrounds:** Uses darker shades of the background hue, not gray (maintains color temperature)
- **Contrast:** All body text ≥4.5:1 against background (WCAG AA)
- **Labels & headings:** ≥3:1 (large text rule applies)

---

## Components

### Buttons

**Sizes:**
- Default: `10px 18px` (base)
- Small: `7px 12px` (`.btn--sm`)

**Variants:**

| Variant | Usage | States |
|---------|-------|--------|
| `--primary` | Primary actions (save, submit, enroll) | default, hover, active, disabled, loading |
| `--secondary` | Secondary actions (cancel, back) | default, hover, active, disabled |
| `--ghost` | Tertiary actions, navigation | default, hover, active, disabled |
| `--danger` | Destructive (delete, revoke) | default, hover, active, disabled |

All buttons:
- Border radius: `var(--radius-sm)` (6px)
- Transition: 150ms ease on `background`, `border-color`, `color`, `box-shadow`
- Focus: 3px outline with `--color-primary-100` (focus ring)
- Active: 1px downward translate (active feedback)
- Disabled: 60% opacity, `cursor: not-allowed`

### Form Controls

| Element | Styles |
|---------|--------|
| Input, Select, Textarea | Background: `--color-surface`, border: `--color-border-strong`, 11px padding, rounded `--radius-sm` |
| Placeholder | Color: `--color-faint` (maintains 4.5:1 contrast) |
| Focus | Border color: `--color-primary`, box-shadow: 3px ring of `--color-primary-100` |
| Disabled | Opacity: 60%, cursor: not-allowed |
| Field hint | Font: 12.5px, color: `--color-muted` |

### Cards & Containers

| Element | Styles |
|---------|--------|
| Card | Background: `--color-surface`, border: 1px `--color-border`, border-radius: `--radius-lg` (16px), box-shadow: `--shadow-sm` |
| Page container | Max-width: 1120px, padding: 0 24px |
| Page section | Padding: 40px 0 64px |

### Navigation

**Navbar:**
- Height: 68px
- Sticky, z-index: 50
- Background: `--surface-translucent` (warm white 0.9 opacity)
- Backdrop filter: `saturate(180%) blur(10px)` (subtle glass effect, japandi-warm)
- Border bottom: 1px `--color-border`

**Nav links:**
- Padding: 8px 14px
- Border radius: `--radius-sm`
- Color: `--color-text`
- Hover: background becomes `--color-surface-alt`, color becomes `--color-ink`
- Active: walnut underline (2px, `--color-primary`)

### Brand Mark
- Size: 34×34px
- Background: Walnut gradient (135deg, `--color-primary-light` → `--color-primary`)
- Text color: `--color-on-primary`
- Border: 1px `--color-primary`
- Border radius: 8px
- Shadow: `var(--shadow-sm)` with subtle inset border
- Kintsugi seam: a thin diagonal gold vein (`::after`, a ~6% band of `--gradient-gold`) glints across the seal — the brand's signature "repair" mark

---

## Spacing & Layout

### Scale
| Token | Value | Usage |
|-------|-------|-------|
| Gap/Margin XS | 4px | Inline gaps, tight spacing |
| Gap/Margin SM | 8px | Button gaps, small spacing |
| Gap/Margin MD | 12px | Form field spacing, moderate |
| Gap/Margin LG | 16px | Component gaps, breathing room |
| Gap/Margin XL | 24px | Section gaps, prominent separation |
| Gap/Margin 2XL | 40px | Page padding, major sections |

**Padding constants:**
- Page container: 24px horizontal
- Page section: 40px top, 64px bottom
- Form grid: 24px (with 20px column gap)

### Grids
- **Data grid:** `repeat(auto-fit, minmax(280px, 1fr))` for responsive 2+ columns
- **2-column form:** `grid-template-columns: repeat(2, minmax(0, 1fr))` with 20px gap
- **Mobile collapse:** `@media (max-width: 640px)` → `1fr` (single column)

---

## Shadows

All shadows use a warm dark base (`rgba(15, 23, 42, ...)` — warm dark neutral).

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-xs` | `0 1px 2px rgba(15, 23, 42, 0.05)` | Subtle depth, inputs |
| `--shadow-sm` | `0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04)` | Cards, buttons, popovers |
| `--shadow-md` | `0 4px 12px rgba(15, 23, 42, 0.08)` | Elevation, modals |
| `--shadow-lg` | `0 12px 32px rgba(15, 23, 42, 0.12)` | High elevation, hero overlays |

**Dark theme:** Shadows intensify slightly (`0.4–0.65` opacity) to maintain contrast on dark surfaces.

---

## Radius Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Inputs, small buttons, chips |
| `--radius` | 10px | Default roundness |
| `--radius-lg` | 16px | Cards, modals, large components |
| `--radius-pill` | 999px | Badges, pills, fully rounded |

**Japandi note:** Radius is deliberately moderate, not sharp (sharp = digital) and not overly rounded (rounded = playful). 6–16px range feels organic without being soft.

---

## Motion

### Timing
- **Standard transitions:** 150ms ease (interactive feedback, color changes)
- **Active press:** 50ms (button press feedback)
- **No page-load choreography** (product loads into a task, users don't watch)

### Easing
- **Transitions:** `ease` (CSS default, ease-out implicitly)
- **No bounce, no elastic:** Japandi is calm and controlled

### Reduced Motion
Every transition respects `@media (prefers-reduced-motion: reduce)`, using instant or crossfade alternatives.

---

## Texture & Material

Large negative spaces get a faint tactile surface so they don't read as flat digital fields:

- **Washi paper grain** — `--paper-grain`, an inline SVG `feTurbulence` (fractal noise, desaturated, ~4.5% opacity, 160px tile). Applied to the page `body` and the login aside, *behind* all opaque surfaces — cards and panels cover it, so it only shows in the open field. Dark mode raises it to ~6% so the texture survives on the darker ground.
- **Kintsugi seams** — the gold counterpart to the grain; thin lacquer lines that "repair" the layout:
  - Login aside: a vertical gold seam marks the join between the two panels.
  - Page headers, section heads, stat/account cards, and the footer carry hairline gold rules (`--gold-line` / `--gradient-gold`).
  - The brand seal carries a single diagonal gold vein.

All textures are **static** (no shimmer or animation) to preserve the calm.

---

## Accessibility

- **Contrast:** All text ≥4.5:1 (WCAG AA). Placeholder text uses `--color-faint` which maintains 4.5:1 on `--color-surface`.
- **Focus indicators:** 3px outline with `--color-primary-100` (high contrast, clear)
- **Semantic HTML:** Real `<button>`, `<input>`, `<label>`, `<form>` elements, not divs
- **Keyboard navigation:** Tab order follows visual flow; focus visible always
- **Labels:** Every form control has an associated `<label>` with `for` attribute
- **ARIA:** Modals, dropdowns, and toggles use proper roles and attributes
- **Color not alone:** Status indicators use color + icon/text, never color alone
- **Dark mode:** Sufficient contrast maintained in both light and dark themes

---

## File Structure

- **Global tokens:** `react-app/src/index.css` (CSS custom properties, theme definitions)
- **Component styles:** `react-app/src/App.css` (buttons, forms, navbar, layout utilities)
- **Fonts:** loaded in `react-app/public/index.html` (Fraunces + Inter via Google Fonts)
- **Legacy (unused):** `react-app/src/styles/navbar.css`, `global.css` — not imported by the app; safe to delete

---

## Implementation Notes

### OKLCH Usage
All color values use OKLCH to ensure:
- Perceptually uniform lightness changes (equal steps look equal)
- Natural saturation scaling (chroma adjustments feel natural)
- Easy dark mode generation (invert lightness, keep hue/chroma)

### Brand Cohesion
- Warm tone throughout (no cool grays or blue-tints)
- Walnut carries interaction; matcha and other accents stay sparse
- Consistency > variation (same button style everywhere)

### Responsive Behavior
- No breakpoint-driven font scaling (fixed rem scale)
- Layout collapses structurally at 640px (form grids, data grids)
- Touch targets remain ≥44px
- Mobile-first component stack (stack, then expand)

### Future Enhancements
- **Phase 2:** Japandi dark mode refinement and user testing
- **Phase 3:** Illustration system aligned with japandi warmth
- **Phase 4:** Animation library (entrance/exit, loading states, microinteractions)
