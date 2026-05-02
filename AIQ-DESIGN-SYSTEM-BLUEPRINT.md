# AI-Quant Bot — UI Design System & Style Blueprint v1.0

> **For Codex / Claude Code:** This document defines the complete visual design system for the AI-Quant Bot trading terminal. It pairs with `AI-Quant-Binance-Bot-Blueprint-v2.1.md` and replaces Section 13.1 (Design System) with full implementation detail.
>
> **Reference mockup:** `quantum-terminal-mockup.html` — open this in a browser to see the target aesthetic before implementing.

**Codename:** `AIQ // QUANTUM`
**Aesthetic Direction:** Dark Glassmorphism + Neon Signal Accents + Bloomberg-grade Information Density
**Version:** 1.0
**Status:** Implementation specification — Codex/Claude Code reference

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Visual Language](#2-visual-language)
3. [Color System](#3-color-system)
4. [Typography](#4-typography)
5. [Spacing & Layout](#5-spacing--layout)
6. [Atmospheric Effects](#6-atmospheric-effects)
7. [Component Library](#7-component-library)
8. [Motion & Animation](#8-motion--animation)
9. [Iconography](#9-iconography)
10. [Page Layouts](#10-page-layouts)
11. [Responsive Breakpoints](#11-responsive-breakpoints)
12. [Accessibility](#12-accessibility)
13. [Implementation Stack](#13-implementation-stack)
14. [Tailwind Configuration](#14-tailwind-configuration)
15. [Component Code Examples](#15-component-code-examples)
16. [Common Mistakes to Avoid](#16-common-mistakes-to-avoid)

---

## 1. Design Philosophy

### 1.1 The Three Pillars

Every design decision must serve one of these:

1. **Trader Trust** — Visual hierarchy that lets a trader scan critical numbers in under 1 second
2. **Premium Feel** — Looks like institutional software ($10M+ startup), not a hobby project
3. **Atmospheric Tech** — "Living" interface with subtle motion and depth, not flat/static

### 1.2 The Tension We Solve

Most crypto trading UIs fail in one of two ways:
- **Too cluttered** (Bloomberg Terminal copies that feel hostile)
- **Too pretty** (consumer apps that hide critical data)

Our system threads this needle by using **calm density** — high information per pixel, but with rest space, hierarchy, and atmospheric depth that prevents fatigue.

### 1.3 What This Is NOT

- ❌ Generic SaaS dashboard with purple gradients
- ❌ Flat material design with rectangles
- ❌ Memecoin-trader aesthetic (cartoonish, animated)
- ❌ Pure brutalist (no atmosphere = feels dead in trading context)
- ❌ Light mode (eye fatigue during long sessions, bad for OLED)

### 1.4 What This IS

- ✅ Dark void with intentional light leaks (ambient gradient orbs)
- ✅ Glass surfaces that reveal depth through blur and transparency
- ✅ Neon signal accents that draw eye to actionable data
- ✅ Monospace numbers with tabular figures (every digit aligns)
- ✅ Micro-motion that signals "system alive" without distraction

---

## 2. Visual Language

### 2.1 The Three-Layer Stack

Every screen is composed of three z-axis layers:

```
LAYER 3: GLASS PANELS    ← Where data lives (translucent over backdrop)
         ↑
         | backdrop-blur, semi-transparent
         |
LAYER 2: ATMOSPHERE      ← Ambient gradient orbs + grid pattern
         ↑
         | radial gradients, low opacity
         |
LAYER 1: VOID            ← Deep base color (#050610)
```

The genius of glassmorphism is that **glass needs something to distort**. Without Layer 2 atmosphere, the glass panels look gray and dead. We MUST have ambient gradients behind everything.

### 2.2 Visual Hierarchy Rules

Information importance is conveyed through (in order of impact):

1. **Glow** — Most important live data has subtle text-shadow glow (current price, profit numbers)
2. **Color** — Cyan = positive/active, Magenta = negative/alert, Amber = warning
3. **Size** — Hero numbers (24px), values (14px), labels (10px)
4. **Weight** — 700 for numbers, 500-600 for UI text, 400 for body
5. **Position** — Top-left = highest priority, top-right = status, bottom = supplementary

### 2.3 Information Density Targets

For a 1920×1080 dashboard:
- **KPI strip:** 5-7 metrics visible without scroll
- **Chart area:** Min 600×400px usable
- **Right rail:** 380px wide for AI/feed/risk
- **Order book:** Min 250px wide, 10+ rows visible
- **Status bar:** 8-10 status indicators

Density should feel **inevitable**, not crammed. Every element earns its space.

---

## 3. Color System

### 3.1 Token Definitions

```css
:root {
  /* ─── VOID (base layers) ─── */
  --void: #050610;            /* Deepest background */
  --void-2: #0a0d1f;          /* Sidebar, elevated bg */
  --void-3: #0f1330;          /* Card base before glass */
  
  /* ─── GLASS (translucent surfaces) ─── */
  --glass-tint: rgba(15, 19, 48, 0.4);
  --glass-border: rgba(120, 180, 255, 0.08);
  --glass-border-hot: rgba(0, 245, 200, 0.25);
  --glass-border-warn: rgba(255, 181, 71, 0.25);
  --glass-border-loss: rgba(255, 46, 136, 0.25);
  
  /* ─── NEON SIGNALS (accents) ─── */
  --cyan: #00f5c8;            /* PRIMARY signal — profit, active, OK */
  --cyan-soft: rgba(0, 245, 200, 0.15);
  --cyan-glow: rgba(0, 245, 200, 0.4);
  
  --magenta: #ff2e88;         /* SECONDARY signal — loss, alert, danger */
  --magenta-soft: rgba(255, 46, 136, 0.15);
  --magenta-glow: rgba(255, 46, 136, 0.4);
  
  --amber: #ffb547;           /* TERTIARY signal — warning, caution */
  --amber-soft: rgba(255, 181, 71, 0.15);
  
  --violet: #8b5cf6;          /* QUATERNARY — AI, special states */
  --violet-soft: rgba(139, 92, 246, 0.15);
  
  --ice: #d8e8ff;             /* Cool highlights */
  
  /* ─── SEMANTIC (mapped to neon) ─── */
  --profit: var(--cyan);
  --loss: var(--magenta);
  --warning: var(--amber);
  --neutral: #6c7894;
  
  /* ─── TEXT ─── */
  --text: #e8eeff;            /* Primary text */
  --text-dim: #8a93b3;        /* Secondary text */
  --text-faint: #4a5375;      /* Tertiary, labels */
  --text-disabled: #2d3450;   /* Disabled state */
}
```

### 3.2 Color Usage Rules

**Hard rules (Codex MUST follow):**

1. **Neon accents = under 20% of pixels.** Most surface = void/glass, neon only on data points and active states. Otherwise it becomes noise.

2. **Profit is ALWAYS cyan, Loss is ALWAYS magenta.** Never invert. Never use red/green directly. Cyan/magenta is our differentiator from generic crypto bots.

3. **Glass borders use cool blue tone** (`rgba(120, 180, 255, 0.08)`), NOT gray. This keeps the cool tech feel.

4. **Dark backgrounds NEVER pure black.** Use `#050610` not `#000000`. Pure black on OLED looks "off" and prevents glassmorphism from working.

5. **Text on glass:** primary text `--text`, NEVER pure white. Pure white on glass burns retinas.

### 3.3 State Colors

| State | Background | Border | Text |
|---|---|---|---|
| Default | `--glass-tint` | `--glass-border` | `--text` |
| Hover | `rgba(120,180,255,0.05)` | `--glass-border-hot` | `--text` |
| Active | `--cyan-soft` | `--cyan` | `--cyan` |
| Profit | `linear-gradient(135deg, rgba(0,245,200,0.06), --glass-tint)` | `rgba(0,245,200,0.2)` | `--profit` |
| Loss | `linear-gradient(135deg, rgba(255,46,136,0.06), --glass-tint)` | `rgba(255,46,136,0.2)` | `--loss` |
| Warning | `--amber-soft` | `--glass-border-warn` | `--amber` |
| Disabled | `--glass-tint` | `--glass-border` | `--text-disabled` |

### 3.4 Background Atmosphere Tokens

```css
/* Use these in body::before to create the ambient orbs */
--atmo-orb-1: radial-gradient(ellipse 800px 600px at 15% 25%, rgba(0, 245, 200, 0.12), transparent 60%);
--atmo-orb-2: radial-gradient(ellipse 700px 500px at 85% 75%, rgba(255, 46, 136, 0.10), transparent 60%);
--atmo-orb-3: radial-gradient(ellipse 600px 400px at 50% 100%, rgba(139, 92, 246, 0.08), transparent 60%);

/* Grid pattern for circuit-board feel */
--grid-pattern: 
  linear-gradient(rgba(120, 180, 255, 0.025) 1px, transparent 1px),
  linear-gradient(90deg, rgba(120, 180, 255, 0.025) 1px, transparent 1px);
--grid-size: 40px 40px;
```

---

## 4. Typography

### 4.1 Font Stack

We use **three fonts**, each with specific purpose:

```css
/* Display — for brand, headers, dramatic moments */
--font-display: 'Syncopate', 'Space Grotesk', sans-serif;

/* Sans — for UI text, body copy, labels */
--font-sans: 'Space Grotesk', system-ui, -apple-system, sans-serif;

/* Mono — for ALL numbers, tickers, code, technical data */
--font-mono: 'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace;
```

**Why these specific fonts:**
- **Syncopate** — Geometric, futuristic, distinctive. Not overused like Orbitron.
- **Space Grotesk** — Clean modern sans with character. Better than Inter (overused) for fintech.
- **JetBrains Mono** — Tabular numerals, ligatures, optimized for code/numbers.

**Do NOT use:** Inter, Roboto, Arial, Helvetica, generic system fonts. These signal "AI-generated UI."

### 4.2 Type Scale

```css
/* Display sizes */
--text-display-xl: 48px;     /* Hero numbers (rare, only for exceptional moments) */
--text-display-lg: 32px;     /* Page titles */
--text-display-md: 24px;     /* Symbol price, large values */

/* Numbers */
--text-num-xl: 22px;         /* KPI hero values */
--text-num-lg: 18px;         /* Symbol names, prominent values */
--text-num-md: 14px;         /* Standard table numbers */
--text-num-sm: 12px;         /* Compact tables */
--text-num-xs: 11px;         /* Order book rows */

/* UI Text */
--text-body: 13px;           /* Body text, AI messages */
--text-ui: 12px;             /* Buttons, controls */
--text-label: 10px;          /* Section labels (uppercase) */
--text-micro: 9px;           /* Microlabels, badges */
--text-tiny: 8px;            /* Stats labels */
```

### 4.3 Font Feature Settings

**MANDATORY for all numeric displays:**

```css
.numeric, .num, [data-num] {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;  /* Equal-width digits */
  letter-spacing: -0.01em;             /* Tighten slightly */
}

/* Body text optimization */
body {
  font-feature-settings: 'ss01', 'ss02', 'cv11';  /* Stylistic alternates */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
```

### 4.4 Letter Spacing Rules

| Use | Letter Spacing |
|---|---|
| All-uppercase labels | `0.18em` |
| All-uppercase micro labels | `0.15em` |
| Small caps | `0.1em` |
| Body text | `0` (default) |
| Display large | `-0.02em` (tighter) |
| Numbers | `-0.01em` (slightly tighter) |

### 4.5 Type Patterns

**Pattern: KPI Card**
```html
<div class="kpi">
  <div class="kpi-label">EQUITY</div>          <!-- 9px, uppercase, 0.18em, --text-faint -->
  <div class="kpi-value">$127.40</div>          <!-- 22px, mono, 700, --text -->
  <div class="kpi-meta">
    <span class="kpi-delta">+27.40%</span>      <!-- 10px, mono, --profit -->
    <span class="kpi-sublabel">SINCE INCEPTION</span>  <!-- 9px, --text-faint -->
  </div>
</div>
```

**Pattern: Symbol Display**
```html
<div class="symbol-name">                       <!-- mono, 18px, 700 -->
  BTC<span style="color:var(--text-faint)">/</span>USDT
  <span class="symbol-tag">PERP</span>          <!-- 9px badge, --magenta-soft -->
</div>
<div class="symbol-price">68,452.30</div>       <!-- mono, 22px, --profit, with glow -->
```

---

## 5. Spacing & Layout

### 5.1 Spacing Scale

We use a tight 4px base scale for trading density:

```css
--space-0: 0;
--space-1: 2px;
--space-2: 4px;
--space-3: 6px;
--space-4: 8px;
--space-5: 10px;
--space-6: 12px;
--space-8: 16px;
--space-10: 20px;
--space-12: 24px;
--space-16: 32px;
```

### 5.2 Grid System

**Top-level layout:** CSS Grid

```css
.terminal {
  display: grid;
  grid-template-columns: 64px 1fr 380px;       /* sidebar | main | rail */
  grid-template-rows: 56px 1fr 32px;            /* topbar | content | statusbar */
  gap: 1px;
  background: rgba(120, 180, 255, 0.04);        /* Visible as grid lines */
}
```

**Rationale for dimensions:**
- `64px` sidebar — fits 18px icons + padding, narrow but tappable
- `380px` rail — fits 4-up gauges + readable AI text
- `56px` topbar — accommodates ticker strip + brand
- `32px` statusbar — minimum for legible 10px text + dots

### 5.3 Border Radius Scale

```css
--radius-sm: 2px;            /* Pills, micro badges */
--radius-md: 3px;            /* Buttons, controls */
--radius-lg: 4px;            /* Cards, inputs */
--radius-xl: 6px;            /* Nav items */
--radius-2xl: 8px;           /* Panels, KPI cards */
--radius-3xl: 12px;          /* Modals, large containers */
```

**No fully rounded corners.** Sharp `2-8px` only. Rounded buttons feel consumer; we want institutional.

### 5.4 Border Widths

```css
--border-hairline: 1px;      /* Default everywhere */
--border-emphasis: 2px;      /* Active states, highlight */
```

**Borders are 1px ALWAYS.** Never 2px+ except for emphasized states. Thicker borders feel cheap.

---

## 6. Atmospheric Effects

This is what separates **AIQ Quantum** from other crypto UIs. These effects MUST be implemented.

### 6.1 Ambient Orbs (Mandatory)

Behind everything, floating colored gradients give the glass something to distort:

```css
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 800px 600px at 15% 25%, rgba(0, 245, 200, 0.12), transparent 60%),
    radial-gradient(ellipse 700px 500px at 85% 75%, rgba(255, 46, 136, 0.10), transparent 60%),
    radial-gradient(ellipse 600px 400px at 50% 100%, rgba(139, 92, 246, 0.08), transparent 60%);
  pointer-events: none;
  z-index: 0;
  animation: ambient-shift 20s ease-in-out infinite;
}

@keyframes ambient-shift {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(2%, -1%) scale(1.05); }
}
```

**Critical:** Without this, glassmorphism looks like flat gray rectangles. Verify by toggling — the difference is dramatic.

### 6.2 Grid Backdrop (Mandatory)

Subtle "circuit board" grid pattern:

```css
body::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(120, 180, 255, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(120, 180, 255, 0.025) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
  /* Mask so grid fades at edges */
  mask-image: radial-gradient(ellipse 100% 100% at 50% 50%, black 30%, transparent 80%);
}
```

### 6.3 Glass Surface Recipe

Every glass panel uses this exact formula:

```css
.panel {
  background: linear-gradient(135deg, 
    rgba(15, 19, 48, 0.6),       /* Top-left tint */
    rgba(10, 13, 31, 0.5)         /* Bottom-right slightly darker */
  );
  backdrop-filter: blur(16px) saturate(140%);
  -webkit-backdrop-filter: blur(16px) saturate(140%);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  /* Optional: Inner highlight */
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
```

**`saturate(140%)`** is the secret — it makes colors behind glass pop more, giving "premium" feel.

### 6.4 Neon Glow Effects

For elements that need to "live":

```css
/* Text glow (for prominent prices, profit) */
.glow-cyan {
  text-shadow: 0 0 16px rgba(0, 245, 200, 0.4);
}

/* Element glow (for active dots, status indicators) */
.glow-cyan-element {
  box-shadow: 0 0 8px var(--cyan), 0 0 16px var(--cyan-glow);
}

/* SVG glow (for chart elements) */
<svg>
  <defs>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <path filter="url(#glow)" stroke="#00f5c8" ... />
</svg>
```

**Use sparingly.** Glow on everything = noise. Use on:
- Current price display
- Active status dots
- Profit numbers (when significant)
- Chart price line
- Critical alerts

### 6.5 Scanning Beam Animation

For badges/cards that need "live system" feeling:

```css
.scan-beam {
  position: relative;
  overflow: hidden;
}

.scan-beam::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 30%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 245, 200, 0.15), transparent);
  animation: scan 3s ease-in-out infinite;
}

@keyframes scan {
  0%, 100% { left: -100%; }
  50% { left: 100%; }
}
```

Use on:
- Regime badge
- Active strategy cards
- AI Analyst card (with longer duration, 4s)

### 6.6 Edge Highlight (Top Gradient Line)

For featured cards, add a thin animated gradient at top:

```css
.featured::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--cyan), transparent);
  opacity: 0.6;
}

/* For AI card with multi-color shimmer */
.ai-card::before {
  background: linear-gradient(90deg, transparent, var(--cyan), var(--violet), transparent);
  animation: ai-shimmer 4s linear infinite;
}

@keyframes ai-shimmer {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}
```

---

## 7. Component Library

### 7.1 Component Inventory

| Category | Components |
|---|---|
| **Layout** | Topbar, Sidebar, Statusbar, Panel, Rail |
| **Display** | KPI Card, Stat Group, Symbol Display, Price Display |
| **Data Viz** | Chart Canvas, Order Book, Funding Heatmap, Sparkline, Gauge |
| **Action** | Button, Toggle, Tab, Slider |
| **Feedback** | Toast, Modal, Loading, Empty State |
| **AI** | AI Card, AI Tag, Suggestion |
| **Status** | Regime Badge, Status Dot, Connection Indicator |

### 7.2 KPI Card

**Anatomy:**
```
┌─────────────────────────────────┐
│ EQUITY                       ●  │  ← Label (9px, uppercase) + optional icon
│                                 │
│ $127.40                         │  ← Value (22px, mono, 700)
│                                 │
│ +27.40%   SINCE INCEPTION       │  ← Delta + sublabel
│ ╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱╱  │  ← Optional sparkline (bottom 24px)
└─────────────────────────────────┘
```

**Variants:**
- `default` — Standard KPI
- `featured` — Top gradient line, slightly tinted background (use for hero KPI like Equity)
- `profit` — Cyan tint background, cyan value
- `loss` — Magenta tint background, magenta value

**States:**
- Hover: `border-color: var(--glass-border-hot)`, `transform: translateY(-1px)`

**HTML structure:**
```html
<div class="kpi kpi--featured kpi--profit">
  <div class="kpi-label">
    EQUITY
    <span class="kpi-icon">●</span>
  </div>
  <div class="kpi-value">$127.40</div>
  <div class="kpi-meta">
    <span class="kpi-delta">+27.40%</span>
    <span class="kpi-sublabel">SINCE INCEPTION</span>
  </div>
  <svg class="kpi-spark"><!-- sparkline --></svg>
</div>
```

### 7.3 Panel (Generic Container)

**Anatomy:**
```
┌─ Panel Header ──────────────────┐
│ ● TITLE          [1m][5m][15m]  │  ← title + controls
├─────────────────────────────────┤
│                                 │
│         Panel Content           │
│                                 │
└─────────────────────────────────┘
```

**Header structure:**
```html
<div class="panel-header">
  <div class="panel-title">
    <span class="panel-title-dot"></span>
    PANEL TITLE
  </div>
  <div class="panel-controls">
    <button class="panel-control active">5m</button>
    <button class="panel-control">15m</button>
  </div>
</div>
```

### 7.4 Status Dot

A live indicator dot. Color = state.

```html
<span class="status-dot status-dot--ok"></span>     <!-- cyan, glowing -->
<span class="status-dot status-dot--warn"></span>   <!-- amber -->
<span class="status-dot status-dot--alert"></span>  <!-- magenta -->
<span class="status-dot status-dot--idle"></span>   <!-- gray, no glow -->
```

```css
.status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot--ok {
  background: var(--cyan);
  box-shadow: 0 0 4px var(--cyan-glow);
}

.status-dot--ok.pulsing {
  animation: pulse 1.5s ease-in-out infinite;
}
```

### 7.5 Regime Badge

The most distinctive component. Used in topbar.

```html
<div class="regime-badge">
  <span class="regime-dot"></span>
  <span class="regime-label">BULL_TRENDING</span>
</div>
```

**Six regime variants** (color-coded):

| Regime | Border | Dot/Text |
|---|---|---|
| BULL_TRENDING | `--glass-border-hot` (cyan) | `--cyan` |
| BEAR_TRENDING | `--glass-border-loss` (magenta) | `--magenta` |
| RANGE_LOW_VOL | `--glass-border` (default) | `--text-dim` |
| RANGE_HIGH_VOL | `--glass-border-warn` (amber) | `--amber` |
| CAPITULATION | `rgba(255, 46, 136, 0.4)` | `--magenta` |
| EUPHORIA | `rgba(255, 181, 71, 0.4)` | `--amber` |

Always with **scanning beam** animation overlay.

### 7.6 Order Book

**Critical specs:**
- Asks displayed top, ascending price (cheapest closest to spread)
- Bids displayed bottom, descending price
- Spread row in middle, slightly different background
- Background depth bar fills from right (proportional to size)
- Large orders (top 10% of size in window) get bold weight + glow

```html
<div class="ob-row ob-row--ask ob-row--large">
  <div class="ob-bg" style="width: 75%"></div>   <!-- depth fill -->
  <div>68,472.10</div>                            <!-- price -->
  <div>1.24</div>                                 <!-- size -->
  <div>1.84</div>                                 <!-- cumulative -->
</div>
```

### 7.7 Funding Rate Heatmap

**Unique component** — calendar-grid showing funding rate per period per symbol.

```html
<div class="funding-cells">
  <div class="funding-symbol">BTC</div>
  <div class="funding-cell fc-pos-low" title="0.005%"></div>
  <div class="funding-cell fc-pos-mid" title="0.012%"></div>
  <div class="funding-cell fc-pos-extreme" title="0.045%"></div>
  ...
</div>
```

**Color scale (8 buckets):**

```css
.fc-neg-extreme { background: rgba(255, 46, 136, 0.85); }
.fc-neg-high    { background: rgba(255, 46, 136, 0.7); }
.fc-neg-mid     { background: rgba(255, 46, 136, 0.4); }
.fc-neg-low     { background: rgba(255, 46, 136, 0.2); }
.fc-zero        { background: rgba(120, 180, 255, 0.05); }
.fc-pos-low     { background: rgba(0, 245, 200, 0.2); }
.fc-pos-mid     { background: rgba(0, 245, 200, 0.4); }
.fc-pos-high    { background: rgba(0, 245, 200, 0.7); }
.fc-pos-extreme { background: var(--cyan); box-shadow: 0 0 8px var(--cyan-glow); }
```

**Bucket thresholds (8h funding rate):**

| Bucket | Range |
|---|---|
| neg-extreme | < -0.05% |
| neg-high | -0.05% to -0.02% |
| neg-mid | -0.02% to -0.005% |
| neg-low | -0.005% to -0.001% |
| zero | -0.001% to 0.001% |
| pos-low | 0.001% to 0.005% |
| pos-mid | 0.005% to 0.02% |
| pos-high | 0.02% to 0.04% |
| pos-extreme | > 0.04% |

### 7.8 Risk Gauge

```html
<div class="gauge">
  <div class="gauge-label">DAILY LOSS</div>
  <div class="gauge-bar">
    <div class="gauge-fill gauge-fill--ok" style="width: 24%"></div>
  </div>
  <div class="gauge-value">-0.48<span class="unit">%</span></div>
</div>
```

**Fill variants:**
- `gauge-fill--ok` — cyan, 0-50% range
- `gauge-fill--warn` — amber, 50-80% range
- `gauge-fill--high` — magenta, 80-100% range

### 7.9 AI Card

The signature component. Used for AI Analyst output.

```html
<div class="ai-card">
  <div class="ai-tag">
    <span class="ai-thinking"></span>
    REGIME ANALYSIS · 14:30 UTC
  </div>
  <div class="ai-message">
    BTC entered <strong>BULL_TRENDING</strong> regime 6h ago. 
    Funding rate at <strong>+0.012%</strong>...
  </div>
</div>
```

**Special effects:**
- Background: `linear-gradient(135deg, rgba(0,245,200,0.06), rgba(139,92,246,0.04))`
- Top edge: animated multi-color shimmer (cyan → violet)
- "Thinking" dot pulses

### 7.10 Activity Feed

Streaming log of system events.

```html
<div class="feed-item">
  <div class="feed-icon feed-icon--signal">
    <svg><!-- arrow icon --></svg>
  </div>
  <div class="feed-content">
    <div class="feed-title">Funding Arb signal · ETH</div>
    <div class="feed-desc">Rate +0.024% / basis 0.08% · entered both legs</div>
    <div class="feed-time">14:28:42 · 4m ago</div>
  </div>
</div>
```

**Icon variants by event type:**
- `signal` — cyan tint, arrow icon
- `fill` — violet tint, checkmark
- `alert` — magenta tint, warning
- `info` — gray tint, info icon
- `risk` — amber tint, shield icon

---

## 8. Motion & Animation

### 8.1 Animation Principles

1. **Subtle > Splashy.** A single 200ms ease-out beats five different effects.
2. **Live, not busy.** System should feel "alive" but never demand attention from data.
3. **Performance first.** All animations use `transform` and `opacity` (GPU-accelerated).
4. **Respect `prefers-reduced-motion`.**

### 8.2 Standard Durations

```css
--duration-instant: 100ms;     /* Hover transitions */
--duration-fast: 200ms;        /* Standard UI */
--duration-medium: 300ms;      /* Modal/drawer */
--duration-slow: 600ms;        /* Page load reveal */
--duration-ambient: 20s;       /* Background atmosphere */
```

### 8.3 Easing Curves

```css
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);          /* Default — feels premium */
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);      /* Reversible animations */
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);   /* Bouncy (use sparingly) */
```

### 8.4 Required Animations

**On page load (staggered KPI reveal):**
```css
.kpi {
  opacity: 0;
  animation: fade-up 0.6s var(--ease-out) forwards;
}

.kpi:nth-child(1) { animation-delay: 0.05s; }
.kpi:nth-child(2) { animation-delay: 0.1s; }
.kpi:nth-child(3) { animation-delay: 0.15s; }
/* etc */

@keyframes fade-up {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

**On value change (number tick):**
```javascript
// When a price/value updates, briefly highlight
function tickValue(element, newValue) {
  const direction = newValue > parseFloat(element.dataset.prev) ? 'up' : 'down';
  element.classList.add(`tick-${direction}`);
  element.textContent = formatNumber(newValue);
  setTimeout(() => element.classList.remove(`tick-${direction}`), 400);
  element.dataset.prev = newValue;
}
```

```css
.tick-up {
  animation: tick-up 400ms ease-out;
}

.tick-down {
  animation: tick-down 400ms ease-out;
}

@keyframes tick-up {
  0% { background: var(--cyan-soft); }
  100% { background: transparent; }
}

@keyframes tick-down {
  0% { background: var(--magenta-soft); }
  100% { background: transparent; }
}
```

**On critical alert (attention pull):**
```css
.alert-pulse {
  animation: alert-pulse 1s ease-in-out 3;  /* 3 pulses then stop */
}

@keyframes alert-pulse {
  0%, 100% { box-shadow: 0 0 0 0 var(--magenta-glow); }
  50% { box-shadow: 0 0 0 8px transparent; }
}
```

### 8.5 Library Recommendation

For React frontend (per blueprint Section 4 stack):

```typescript
// Use Framer Motion for component animations
import { motion } from "framer-motion";

const KpiCard = ({ children }) => (
  <motion.div
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
  >
    {children}
  </motion.div>
);
```

For number animations:
```typescript
import { useSpring, animated } from "@react-spring/web";

const AnimatedNumber = ({ value }) => {
  const { num } = useSpring({ from: { num: 0 }, num: value });
  return <animated.span>{num.to(n => n.toFixed(2))}</animated.span>;
};
```

### 8.6 Reduced Motion Support

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  
  /* Keep critical state changes but make them instant */
  body::before {
    animation: none;
  }
}
```

---

## 9. Iconography

### 9.1 Icon Library

**Use Lucide React** (already in blueprint stack). NOT Heroicons (too generic), NOT FontAwesome (too consumer).

```typescript
import { 
  LayoutDashboard, Terminal, Workflow, BarChart3, 
  Shield, Brain, FileText, Settings 
} from "lucide-react";
```

### 9.2 Icon Sizing

```css
--icon-xs: 12px;      /* Inline with text */
--icon-sm: 14px;      /* Buttons, controls */
--icon-md: 18px;      /* Sidebar nav */
--icon-lg: 20px;      /* Section headers */
--icon-xl: 24px;      /* Empty states */
```

### 9.3 Stroke Width

**Always 1.5** for consistency:

```typescript
<LayoutDashboard size={18} strokeWidth={1.5} />
```

Stroke 2 looks chunky. Stroke 1 disappears on dark backgrounds. 1.5 is the sweet spot.

### 9.4 Icon Colors

| Context | Color |
|---|---|
| Sidebar nav (default) | `--text-faint` |
| Sidebar nav (active) | `--cyan` |
| Inline with text | inherit from parent |
| Status indicators | semantic color |
| Decorative | `--text-dim` |

### 9.5 Custom Brand Mark

The hexagon brand mark is a **custom SVG**:

```html
<svg viewBox="0 0 28 28" fill="none">
  <path d="M14 2 L24 8 L24 20 L14 26 L4 20 L4 8 Z" 
        stroke="#00f5c8" stroke-width="1.5"/>
  <path d="M14 8 L19 11 L19 17 L14 20 L9 17 L9 11 Z" 
        fill="#00f5c8" fill-opacity="0.3" 
        stroke="#00f5c8" stroke-width="1"/>
  <circle cx="14" cy="14" r="2" fill="#00f5c8"/>
</svg>
```

With glow filter: `filter: drop-shadow(0 0 8px var(--cyan-glow));`

---

## 10. Page Layouts

### 10.1 Main Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│ TOPBAR (56px) — Brand · Tickers · Regime · Clock            │
├──┬─────────────────────────────────────────┬────────────────┤
│  │ KPI STRIP (5 cards)                     │                │
│  ├─────────────────────────────────────────┤                │
│ S│                                         │  RIGHT RAIL    │
│ I│   CHART AREA              ORDER BOOK   │                │
│ D│   (with overlays)         (depth bars)  │  · AI Card     │
│ E│                                         │  · Risk Gauges │
│ B│                                         │  · Signal Feed │
│ A├─────────────────────────────────────────┤  · Activity    │
│ R│                                         │                │
│  │   FUNDING HEATMAP    OPEN POSITIONS    │   (380px)      │
│  │                                         │                │
├──┴─────────────────────────────────────────┴────────────────┤
│ STATUSBAR (32px) — Connection · Latency · Mode · Version    │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 Strategy Lab

```
┌─────────────────────────────────────────────────────────────┐
│ TOPBAR                                                       │
├──┬──────────────────────────────────────────────────────────┤
│  │ Filters: [All] [Live] [Paper] [Disabled]    Sort: [Sharpe]│
│ S├──────────────────────────────────────────────────────────┤
│ I│ ┌─Strategy────┐ ┌─Strategy────┐ ┌─Strategy────┐         │
│ D│ │ ● Funding   │ │ ● Mid-Cap   │ │ ● Regime    │         │
│ E│ │   Arb       │ │   Swing     │ │   Trend     │         │
│ B│ │             │ │             │ │             │         │
│ A│ │ Sparkline   │ │ Sparkline   │ │ Sparkline   │         │
│ R│ │             │ │             │ │             │         │
│  │ │ ROI Win DD  │ │ ROI Win DD  │ │ ROI Win DD  │         │
│  │ └─────────────┘ └─────────────┘ └─────────────┘         │
└──┴──────────────────────────────────────────────────────────┘
```

### 10.3 AI Analyst Page

```
┌─────────────────────────────────────────────────────────────┐
│ TOPBAR                                                       │
├──┬──────────────────────────┬───────────────────────────────┤
│ S│ DAILY BRIEFING            │ ASK AI                        │
│ I│ ┌────────────────────────┐│ ┌──────────────────────────┐ │
│ D│ │ [AI Card: Today's      ││ │ [Chat history]            │ │
│ E│ │  market summary]       ││ │                           │ │
│ B│ │                        ││ │                           │ │
│ A│ └────────────────────────┘│ │                           │ │
│ R│ SUGGESTIONS QUEUE         │ │                           │ │
│  │ [Pending review cards]    │ │ [Input box]               │ │
│  │                           │ └──────────────────────────┘ │
└──┴──────────────────────────┴───────────────────────────────┘
```

---

## 11. Responsive Breakpoints

### 11.1 Breakpoints

```css
/* Mobile-first NOT recommended for trading terminals */
/* This is a desktop-first system */

--bp-xl: 1920px;      /* Optimal */
--bp-lg: 1440px;      /* Standard laptop */
--bp-md: 1280px;      /* Minimum recommended */
--bp-sm: 1024px;      /* Tablet (read-only mode) */
--bp-xs: 768px;       /* Phone (alerts only mode) */
```

### 11.2 Layout Adaptation

| Breakpoint | Behavior |
|---|---|
| ≥1920px | Full layout, all panels visible |
| 1440-1920px | Right rail collapses to 320px |
| 1280-1440px | Order book inline (under chart), rail to 280px |
| 1024-1280px | Right rail hidden (toggle), funding heatmap full width |
| <1024px | Read-only mobile mode — KPIs + positions + alerts only. NO trading UI. |

**Critical:** On mobile, **disable trade execution UI**. Show banner: "Trading disabled on mobile. Use desktop for full terminal."

This is intentional safety — preventing fat-finger trades on small screens.

---

## 12. Accessibility

### 12.1 Contrast Ratios

All text must meet **WCAG AA** minimum:

| Text | Background | Ratio | Pass |
|---|---|---|---|
| `--text` (#e8eeff) | `--void` (#050610) | 17.2:1 | ✅ AAA |
| `--text-dim` (#8a93b3) | `--void` | 7.4:1 | ✅ AAA |
| `--text-faint` (#4a5375) | `--void` | 3.8:1 | ✅ AA Large |
| `--cyan` on glass | varies | 8.2:1 | ✅ AAA |
| `--magenta` on glass | varies | 5.4:1 | ✅ AA |

### 12.2 Focus States

**MANDATORY for all interactive elements:**

```css
*:focus-visible {
  outline: 2px solid var(--cyan);
  outline-offset: 2px;
  border-radius: 2px;
}
```

Never `outline: none` without replacement.

### 12.3 Keyboard Navigation

- `Tab` — Navigate between panels
- `Cmd/Ctrl + K` — Command palette (future)
- `Esc` — Close modal / cancel pending action
- `Arrow keys` — Navigate within tables
- `Enter` — Confirm action
- `?` — Show keyboard shortcuts

### 12.4 Screen Reader Support

```html
<!-- Use proper ARIA labels for icon-only buttons -->
<button aria-label="Close position">
  <X size={14} />
</button>

<!-- Live regions for real-time updates -->
<div aria-live="polite" aria-atomic="true" class="sr-only">
  Price updated: BTC at 68,452.30
</div>

<!-- Skip to main content -->
<a href="#main" class="skip-link">Skip to main content</a>
```

### 12.5 Color Independence

Never communicate state with color alone. Pair with:
- Text labels ("PROFIT", "LOSS")
- Icons (▲ up, ▼ down)
- Position (asks above, bids below)

---

## 13. Implementation Stack

### 13.1 Required Libraries

Per blueprint Section 4 + UI-specific additions:

```json
{
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "tailwindcss": "3.x",
    "framer-motion": "^11.0.0",
    "lucide-react": "^0.383.0",
    "@react-spring/web": "^9.7.0",
    "lightweight-charts": "^4.1.0",
    "recharts": "^2.12.0",
    "shadcn-ui": "latest"
  }
}
```

### 13.2 Font Loading

In `app/layout.tsx`:

```typescript
import { Space_Grotesk, JetBrains_Mono, Syncopate } from 'next/font/google';

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-sans',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700', '800'],
  variable: '--font-mono',
});

const syncopate = Syncopate({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-display',
});

// In body className:
className={`${spaceGrotesk.variable} ${jetbrainsMono.variable} ${syncopate.variable}`}
```

### 13.3 Global CSS Setup

`app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Insert all CSS variables from Section 3.1 here */
  }
  
  body {
    background: var(--void);
    color: var(--text);
    font-family: var(--font-sans);
    font-feature-settings: 'ss01', 'ss02', 'cv11';
    -webkit-font-smoothing: antialiased;
    overflow: hidden;  /* Prevent body scroll, panels handle scroll */
  }
  
  /* Atmosphere layers */
  body::before { /* ambient orbs */ }
  body::after { /* grid pattern */ }
}

@layer components {
  /* Component classes from Section 7 */
}
```

---

## 14. Tailwind Configuration

`tailwind.config.ts`:

```typescript
import type { Config } from 'tailwindcss';

export default {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        void: {
          DEFAULT: '#050610',
          2: '#0a0d1f',
          3: '#0f1330',
        },
        cyan: {
          DEFAULT: '#00f5c8',
          soft: 'rgba(0, 245, 200, 0.15)',
          glow: 'rgba(0, 245, 200, 0.4)',
        },
        magenta: {
          DEFAULT: '#ff2e88',
          soft: 'rgba(255, 46, 136, 0.15)',
          glow: 'rgba(255, 46, 136, 0.4)',
        },
        amber: {
          DEFAULT: '#ffb547',
          soft: 'rgba(255, 181, 71, 0.15)',
        },
        violet: {
          DEFAULT: '#8b5cf6',
          soft: 'rgba(139, 92, 246, 0.15)',
        },
        text: {
          DEFAULT: '#e8eeff',
          dim: '#8a93b3',
          faint: '#4a5375',
        },
        glass: {
          tint: 'rgba(15, 19, 48, 0.4)',
          border: 'rgba(120, 180, 255, 0.08)',
          'border-hot': 'rgba(0, 245, 200, 0.25)',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui'],
        mono: ['var(--font-mono)', 'ui-monospace'],
        display: ['var(--font-display)', 'sans-serif'],
      },
      fontSize: {
        'tiny': ['8px', { lineHeight: '1.2', letterSpacing: '0.15em' }],
        'micro': ['9px', { lineHeight: '1.2' }],
        'label': ['10px', { lineHeight: '1.4', letterSpacing: '0.18em' }],
      },
      backdropBlur: {
        'glass': '16px',
      },
      animation: {
        'pulse-glow': 'pulse-glow 1.5s ease-in-out infinite',
        'scan': 'scan 3s ease-in-out infinite',
        'ai-shimmer': 'ai-shimmer 4s linear infinite',
        'ambient-shift': 'ambient-shift 20s ease-in-out infinite',
        'fade-up': 'fade-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.5', transform: 'scale(1.2)' },
        },
        'scan': {
          '0%, 100%': { left: '-100%' },
          '50%': { left: '100%' },
        },
        'ai-shimmer': {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '1' },
        },
        'ambient-shift': {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '50%': { transform: 'translate(2%, -1%) scale(1.05)' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        'glow-cyan': '0 0 8px rgba(0, 245, 200, 0.4), 0 0 16px rgba(0, 245, 200, 0.2)',
        'glow-magenta': '0 0 8px rgba(255, 46, 136, 0.4), 0 0 16px rgba(255, 46, 136, 0.2)',
        'glass-inner': 'inset 0 1px 0 rgba(255, 255, 255, 0.03)',
      },
    },
  },
  plugins: [],
} satisfies Config;
```

---

## 15. Component Code Examples

### 15.1 Panel Component

```typescript
// components/ui/panel.tsx
import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface PanelProps {
  title?: string;
  controls?: ReactNode;
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'featured';
}

export function Panel({ title, controls, children, className, variant = 'default' }: PanelProps) {
  return (
    <div className={cn(
      "relative flex flex-col overflow-hidden rounded-lg border border-glass-border",
      "bg-gradient-to-br from-void-3/60 to-void-2/50",
      "backdrop-blur-glass backdrop-saturate-150",
      "shadow-glass-inner",
      variant === 'featured' && "border-cyan/20",
      className
    )}>
      {variant === 'featured' && (
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan to-transparent opacity-60" />
      )}
      
      {(title || controls) && (
        <div className="flex items-center justify-between border-b border-glass-border px-3.5 py-2.5">
          {title && (
            <div className="flex items-center gap-2 font-mono text-label uppercase text-text-dim">
              <span className="h-1 w-1 rounded-full bg-cyan shadow-glow-cyan" />
              {title}
            </div>
          )}
          {controls && <div className="flex gap-1">{controls}</div>}
        </div>
      )}
      
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  );
}
```

### 15.2 KPI Card Component

```typescript
// components/ui/kpi-card.tsx
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface KpiCardProps {
  label: string;
  value: string;
  delta?: string;
  deltaDirection?: 'up' | 'down' | 'neutral';
  sublabel?: string;
  variant?: 'default' | 'featured' | 'profit' | 'loss';
  sparkline?: number[];
  index?: number;
}

export function KpiCard({ 
  label, value, delta, deltaDirection = 'neutral', 
  sublabel, variant = 'default', sparkline, index = 0 
}: KpiCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "relative overflow-hidden rounded-lg border bg-gradient-to-br from-void-3/80 to-void-2/60",
        "backdrop-blur-md p-3.5 transition-all duration-200",
        "hover:border-glass-border-hot hover:-translate-y-0.5",
        variant === 'default' && "border-glass-border",
        variant === 'featured' && "border-cyan/20 bg-gradient-to-br from-cyan/[0.06] to-void-2/60",
        variant === 'profit' && "border-cyan/20",
        variant === 'loss' && "border-magenta/20",
      )}
    >
      {variant === 'featured' && (
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan to-transparent opacity-60" />
      )}
      
      <div className="flex items-center justify-between font-mono text-micro uppercase tracking-[0.18em] text-text-faint font-medium">
        {label}
      </div>
      
      <div className={cn(
        "mt-2 font-mono text-[22px] font-bold leading-none tracking-tight tabular-nums",
        variant === 'profit' && "text-cyan drop-shadow-[0_0_20px_rgba(0,245,200,0.3)]",
        variant === 'loss' && "text-magenta",
        variant !== 'profit' && variant !== 'loss' && "text-text"
      )}>
        {value}
      </div>
      
      {(delta || sublabel) && (
        <div className="mt-1.5 flex items-center gap-2 font-mono text-[10px]">
          {delta && (
            <span className={cn(
              "font-semibold tabular-nums",
              deltaDirection === 'up' && "text-cyan",
              deltaDirection === 'down' && "text-magenta",
              deltaDirection === 'neutral' && "text-text-dim"
            )}>
              {delta}
            </span>
          )}
          {sublabel && (
            <span className="text-text-faint text-[9px] tracking-wider">
              {sublabel}
            </span>
          )}
        </div>
      )}
      
      {sparkline && (
        <Sparkline data={sparkline} className="absolute bottom-0 left-0 right-0 h-6 opacity-50 pointer-events-none" />
      )}
    </motion.div>
  );
}
```

### 15.3 Sparkline Component

```typescript
// components/ui/sparkline.tsx
import { cn } from '@/lib/utils';

interface SparklineProps {
  data: number[];
  className?: string;
  color?: string;
}

export function Sparkline({ data, className, color = '#00f5c8' }: SparklineProps) {
  if (data.length < 2) return null;
  
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  
  const points = data.map((value, i) => {
    const x = (i / (data.length - 1)) * 200;
    const y = 24 - ((value - min) / range) * 22;
    return `${x},${y}`;
  }).join(' ');
  
  const pathD = `M${points.split(' ').join(' L')}`;
  const areaD = `${pathD} L200,24 L0,24 Z`;
  
  return (
    <svg viewBox="0 0 200 24" preserveAspectRatio="none" className={cn("w-full h-full", className)}>
      <defs>
        <linearGradient id={`spark-${color}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill={`url(#spark-${color})`} opacity="0.3" />
      <path d={pathD} fill="none" stroke={color} strokeWidth="1.5" opacity="0.7" />
    </svg>
  );
}
```

### 15.4 Status Dot Component

```typescript
// components/ui/status-dot.tsx
import { cn } from '@/lib/utils';

interface StatusDotProps {
  status: 'ok' | 'warn' | 'alert' | 'idle';
  pulsing?: boolean;
  size?: 'sm' | 'md';
}

export function StatusDot({ status, pulsing = false, size = 'sm' }: StatusDotProps) {
  return (
    <span
      className={cn(
        "inline-block rounded-full",
        size === 'sm' && "w-1.5 h-1.5",
        size === 'md' && "w-2 h-2",
        status === 'ok' && "bg-cyan shadow-[0_0_4px_rgba(0,245,200,0.4)]",
        status === 'warn' && "bg-amber shadow-[0_0_4px_rgba(255,181,71,0.4)]",
        status === 'alert' && "bg-magenta shadow-[0_0_4px_rgba(255,46,136,0.4)]",
        status === 'idle' && "bg-text-faint",
        pulsing && "animate-pulse-glow"
      )}
    />
  );
}
```

### 15.5 Regime Badge Component

```typescript
// components/ui/regime-badge.tsx
import { cn } from '@/lib/utils';

type Regime = 'BULL_TRENDING' | 'BEAR_TRENDING' | 'RANGE_LOW_VOL' 
            | 'RANGE_HIGH_VOL' | 'CAPITULATION' | 'EUPHORIA';

const regimeConfig: Record<Regime, { color: string; border: string; dotColor: string }> = {
  BULL_TRENDING:    { color: 'text-cyan',    border: 'border-cyan/25',    dotColor: 'bg-cyan' },
  BEAR_TRENDING:    { color: 'text-magenta', border: 'border-magenta/25', dotColor: 'bg-magenta' },
  RANGE_LOW_VOL:    { color: 'text-text-dim', border: 'border-glass-border', dotColor: 'bg-text-dim' },
  RANGE_HIGH_VOL:   { color: 'text-amber',   border: 'border-amber/25',   dotColor: 'bg-amber' },
  CAPITULATION:     { color: 'text-magenta', border: 'border-magenta/40', dotColor: 'bg-magenta' },
  EUPHORIA:         { color: 'text-amber',   border: 'border-amber/40',   dotColor: 'bg-amber' },
};

export function RegimeBadge({ regime }: { regime: Regime }) {
  const config = regimeConfig[regime];
  
  return (
    <div className={cn(
      "relative flex items-center gap-2 overflow-hidden rounded px-3 py-1.5",
      "border bg-glass-tint backdrop-blur-md",
      "font-mono text-[10px] font-semibold uppercase tracking-[0.12em]",
      config.border
    )}>
      {/* Scanning beam */}
      <div className="absolute inset-y-0 -left-full w-[30%] animate-scan bg-gradient-to-r from-transparent via-cyan/15 to-transparent" />
      
      <span className={cn(
        "h-1.5 w-1.5 rounded-full animate-pulse-glow shadow-[0_0_8px_rgba(0,245,200,0.5)]",
        config.dotColor
      )} />
      <span className={cn("relative", config.color)}>{regime}</span>
    </div>
  );
}
```

---

## 16. Common Mistakes to Avoid

### 16.1 Visual Mistakes

❌ **Using pure black `#000000`** — Use `#050610`. Pure black is too harsh and breaks glassmorphism.

❌ **Skipping the ambient orbs** — Glass panels need something to distort. Without orbs, your "glass" is just gray rectangles.

❌ **Using gray for glass borders** — Use cool blue tint `rgba(120, 180, 255, 0.08)`. Gray feels dead.

❌ **Adding glow to everything** — Glow is for emphasis. If everything glows, nothing does.

❌ **Using rounded corners > 8px** — Feels consumer/playful. Trading needs `2-8px` only.

❌ **Using gradients on text** — Hurts readability. Solid colors only for text.

❌ **Mixing too many accent colors** — Stick to cyan + magenta + amber. Adding more colors = chaos.

### 16.2 Typography Mistakes

❌ **Using Inter or Roboto** — Generic AI-UI signal. Use Space Grotesk + JetBrains Mono + Syncopate.

❌ **Using proportional numbers** — Numbers must align in tables. Always `font-variant-numeric: tabular-nums`.

❌ **Using sans-serif for prices** — All numbers, prices, percentages MUST be monospace.

❌ **Insufficient letter-spacing on labels** — Uppercase labels need `0.15-0.18em` to feel premium.

❌ **Pure white text** — Use `#e8eeff`. Pure white burns retinas on dark.

### 16.3 Layout Mistakes

❌ **Wasted space on standard density** — Trading dashboards should feel dense, not airy. Aim for high info-per-pixel.

❌ **Centering everything** — Asymmetric layouts feel intentional. Center is safe and boring.

❌ **Not using CSS Grid for top-level** — Grid is mandatory for 3-column terminal layout.

❌ **Mobile-first responsive** — Trading is desktop-first. Mobile is read-only mode.

### 16.4 Animation Mistakes

❌ **Animating background-color** — Causes paint. Use opacity + transform only.

❌ **Long durations (>500ms) for UI feedback** — Feels sluggish. Keep under 300ms for responses.

❌ **Continuous animations everywhere** — Distracting. Use sparingly: ambient, status indicators, AI shimmer.

❌ **Not respecting `prefers-reduced-motion`** — Accessibility violation. Always include the media query.

❌ **Bouncy springs on numbers** — Looks cheap. Numbers should ease-out smoothly.

### 16.5 Component Mistakes

❌ **Using shadcn/ui defaults without restyling** — They're a starting point, not the final look. Override styles to match this system.

❌ **Recharts default colors** — Override to use cyan/magenta semantic palette.

❌ **Lucide icons at default 2 stroke** — Use 1.5 strokeWidth for refined feel.

❌ **Missing focus states** — Accessibility violation. Every interactive element needs `:focus-visible`.

### 16.6 Performance Mistakes

❌ **Backdrop-filter on every element** — Expensive. Use only on top-level panels and modals.

❌ **Non-tabular numbers in real-time updates** — Causes layout shift on every tick. Always tabular-nums.

❌ **CSS animations on huge elements** — Animate small isolated elements, not whole panels.

❌ **Not using `will-change` for animated elements** — Use `will-change: transform` for elements that animate frequently.

---

## Quick Reference Card

**For Codex/Claude Code when implementing UI components:**

```
COLOR TOKENS:
  Profit/OK/Active     → var(--cyan) #00f5c8
  Loss/Alert           → var(--magenta) #ff2e88
  Warning              → var(--amber) #ffb547
  AI/Special           → var(--violet) #8b5cf6
  Background           → var(--void) #050610
  Glass                → rgba(15, 19, 48, 0.4)
  Glass border         → rgba(120, 180, 255, 0.08)
  Text                 → #e8eeff (NEVER pure white)

FONTS:
  Numbers/code         → JetBrains Mono (always tabular-nums)
  UI/body              → Space Grotesk
  Brand/display        → Syncopate

SPACING BASE: 4px
RADIUS: 2-8px max
BORDER: always 1px
ICONS: Lucide, strokeWidth 1.5

MUST HAVE:
  ✓ Ambient orbs in body::before
  ✓ Grid pattern in body::after
  ✓ backdrop-filter: blur(16px) saturate(140%) on panels
  ✓ Animated regime badge with scanning beam
  ✓ Pulsing status dots
  ✓ AI card with shimmer top edge
  ✓ Hover transitions on KPI cards (translateY -1px)
  ✓ Tabular nums on ALL numbers
  ✓ Focus visible outline (cyan)
  ✓ prefers-reduced-motion support

NEVER:
  ✗ Pure black #000000
  ✗ Inter, Roboto, Arial fonts
  ✗ Purple gradients on white
  ✗ Border > 1px (except focus state)
  ✗ Border-radius > 8px
  ✗ Glow on everything
  ✗ Trading UI on mobile (<1024px)
```

---

## Implementation Checklist for Codex/Claude Code

When implementing any component, verify ALL items:

```
[ ] Uses CSS variables from this spec, never hardcoded colors
[ ] Numbers use mono font + tabular-nums
[ ] Glass panels have backdrop-filter blur AND saturate
[ ] Body has ambient orbs + grid pattern
[ ] Animations use transform/opacity only (no layout properties)
[ ] Has prefers-reduced-motion fallback
[ ] Focus states visible with cyan outline
[ ] Hover states defined
[ ] Active states for interactive elements
[ ] Semantic ARIA labels for icon-only buttons
[ ] Uses Lucide icons at 1.5 strokeWidth
[ ] Letter spacing on uppercase labels (0.15-0.18em)
[ ] No pure white text (use #e8eeff)
[ ] Border 1px only (except focus 2px)
[ ] Border radius 2-8px max
[ ] Mobile breakpoint disables trading UI
[ ] Test with backdrop-filter disabled (some browsers) — fallback OK?
[ ] Test colorblind safe (cyan/magenta is RG-blind safe)
```

---

**End of Design System Blueprint**

*Refined density. Atmospheric depth. Signal-grade clarity.*

*This is what institutional crypto trading looks like in 2026.*
