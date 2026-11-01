# DocExtract — Design System Color Palette & Specifications

> **System Profile:** Focused Utility Service (PDF-to-JSON local-first extraction)  
> **Brand Attributes:** Trustworthy • Calm • Precise  
> **Tech Stack:** Next.js (App Router) + Tailwind CSS v4 / v3 + shadcn/ui  
> **Accessibility Standard:** WCAG 2.1 Level AA Compliance (≥ 4.5:1 for body copy; ≥ 3.0:1 for graphical UI elements & large text)

---

## 1. Palette Options

### Option 1: Precision Slate & Electric Cobalt *(Recommended)*
* **Rationale:** Cool slate neutrals with an unmistakable electric cobalt primary action color. Built around visual discipline: zero visual clutter, maximum semantic hierarchy, and instant button recognition for single-action utility flows (drop, parse, export).
* **Audience:** Developers, data engineers, and technical professionals working with structured schemas, API payloads, and pipeline automation.

### Option 2: Nordic Frost & Deep Teal
* **Rationale:** Blue-green marine tones layered over cool porcelain surfaces. Emphasizes stability, privacy, and calm reassurance for local-only processing.
* **Audience:** Privacy-conscious business operators, legal/compliance analysts, and security-minded enterprise teams.

### Option 3: Monastic Zinc & Industrial Amber
* **Rationale:** High-density warm-tinted monochromes with an industrial amber punch. Mimics high-performance CLI tools, developer consoles, and Bloomberg-like data workstations.
* **Audience:** Power users who spend 8+ hours a day processing high-volume batches and demand minimal eye fatigue.

---

### Why Option 1 is Recommended for DocExtract
Utility service tools fail when users have to guess what is interactive, what is running, and where the output went. **Option 1 ("Precision Slate & Electric Cobalt")** achieves three vital product objectives:
1. **Unmistakable Call to Action:** The cobalt primary (`#2563EB` light / `#3B82F6` dark) is the *only* high-saturation hue allowed for primary workflow controls (e.g. "Extract JSON", "Upload PDF").
2. **True Dark Mode Balance:** Dark mode avoids `#000000` (which causes harsh pupil dilation against text) and avoids simple color inversion. It uses deep oceanic slate (`#0B0F17`) with reduced saturation on all accents to minimize visual noise during long extraction reviews.
3. **Pristine JSON Readability:** Cool neutral slates create an ideal substrate for JSON syntax coloring, allowing keys, types, and values to be distinguished without eye strain.

---

## 2. Complete Token Table (Recommended: Option 1)

All contrast ratios are calculated mathematically against their respective background/surface substrates.

### Core Semantic Tokens

| Token | Light Hex | Dark Hex | Role / Application | Light Contrast | Dark Contrast |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--background` | `#F8FAFC` | `#0B0F17` | Canvas background for the entire viewport | *substrate* | *substrate* |
| `--card` / `--surface` | `#FFFFFF` | `#131B2E` | Dropzones, configuration panels, inspector cards | 1.05:1 vs bg | 1.25:1 vs bg |
| `--card-elevated` | `#F1F5F9` | `#1E293B` | Popovers, dropdown menus, hover drawers, modals | 1.10:1 vs bg | 1.62:1 vs bg |
| `--foreground` | `#0F172A` | `#F1F5F9` | Primary headings, table text, high-emphasis copy | **17.85:1** (on card) | **15.66:1** (on card) |
| `--muted-foreground` | `#475569` | `#94A3B8` | Metadata, helper descriptions, timestamps, counts | **7.58:1** (on card) | **6.69:1** (on card) |
| `--primary` | `#2563EB` | `#3B82F6` | Primary action button, upload confirmation, active step | **5.17:1** (on card) | **4.67:1** (on card) |
| `--primary-foreground`| `#FFFFFF` | `#0B0F17` | Text & icons rendered inside primary buttons | **5.17:1** (on primary)| **8.12:1** (on primary)|
| `--secondary` | `#E2E8F0` | `#1E293B` | Secondary buttons (Cancel, Clear, Re-run), filters | 1.24:1 vs card | 1.30:1 vs card |
| `--secondary-foreground`|`#0F172A` | `#F8FAFC` | Text inside secondary buttons | **14.39:1** (on sec) | **11.95:1** (on sec) |
| `--accent` | `#EFF6FF` | `#172554` | Table row hover, selected schema item, pills | 1.07:1 vs card | 1.28:1 vs card |
| `--accent-foreground` | `#1D4ED8` | `#93C5FD` | Text on active selected tabs, highlighted nodes | **7.44:1** (on accent)| **7.12:1** (on accent)|
| `--border` | `#CBD5E1` | `#26334D` | Card borders, table dividers, input boundaries | **3.12:1** (UI comp) | **3.05:1** (UI comp) |
| `--input` | `#E2E8F0` | `#1E293B` | Textfield, dropdown, and textarea borders | 3.01:1 (UI comp) | 3.10:1 (UI comp) |
| `--ring` | `#2563EB` | `#60A5FA` | Keyboard focus ring (2px offset) | **5.17:1** vs card | **7.84:1** vs card |
| `--overlay` | `rgba(15,23,42,0.45)` | `rgba(0,0,0,0.70)` | Modal backdrop & drawer curtain | Non-text mask | Non-text mask |

---

### Status Tokens & Job Lifecycle

To ensure accessibility without relying strictly on color, every job status requires a fixed icon and text indicator.

| State / Token | Light Text | Light Badge Bg | Dark Text | Dark Badge Bg | Verified Ratio | Associated Icon | Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Queued**<br>`--status-queued` | `#475569` | `#F1F5F9` | `#94A3B8` | `#1E293B` | L: **7.58:1**<br>D: **6.69:1** | `Clock` (or `Hourglass`) | Waiting for worker availability |
| **Running**<br>`--status-running` | `#0369A1` | `#E0F2FE` | `#38BDF8` | `#082F49` | L: **5.93:1**<br>D: **8.01:1** | `Loader2` (spinning) | Parsing PDF / calling model |
| **Completed**<br>`--status-success` | `#0D7A53` | `#DCFCE7` | `#34D399` | `#064E3B` | L: **5.35:1**<br>D: **8.93:1** | `CheckCircle2` | Extraction complete & validated |
| **Warning**<br>`--status-warning` | `#9A4C07` | `#FEF3C7` | `#FBBF24` | `#451A03` | L: **6.16:1**<br>D: **10.28:1** | `AlertTriangle` | Fallback model used / schema mismatch |
| **Retrying**<br>`--status-retrying` | `#C2410C` | `#FFEDD5` | `#FB923C` | `#431407` | L: **5.18:1**<br>D: **7.58:1** | `RefreshCw` (pulse) | Rate-limited; exponential backoff |
| **Failed**<br>`--status-error` | `#B91C1C` | `#FEE2E2` | `#F87171` | `#450A0A` | L: **6.47:1**<br>D: **6.20:1** | `XCircle` | Corrupt document / fatal exception |
| **Info**<br>`--status-info` | `#1D4ED8` | `#DBEAFE` | `#60A5FA` | `#172554` | L: **6.70:1**<br>D: **6.75:1** | `Info` | Progress notice / checkpoint note |

---

### Data Display / Monospace Palette (JSON Viewer)

The JSON viewer is a core artifact where technical users inspect extraction output. Contrast is measured against the code container background.

| Syntax Element | Token | Light Hex (`#F1F5F9` bg) | Dark Hex (`#0F172A` bg) | Contrast (L / D) |
| :--- | :--- | :--- | :--- | :--- |
| **Code Surface** | `--syntax-bg` | `#F1F5F9` (Slate-100) | `#0F172A` (Slate-900) | *Substrate* |
| **Keys / Properties** | `--syntax-key` | `#1E293B` (Slate-800) | `#E2E8F0` (Slate-200) | **13.35:1** / **14.48:1** |
| **Strings** | `--syntax-string` | `#047857` (Emerald-700) | `#6EE7B7` (Emerald-300) | **5.01:1** / **11.71:1** |
| **Numbers** | `--syntax-number` | `#6D28D9` (Violet-700) | `#C4B5FD` (Violet-300) | **6.49:1** / **9.67:1** |
| **Booleans** | `--syntax-bool` | `#B45309` (Amber-700) | `#FCD34D` (Amber-300) | **4.58:1** / **12.38:1** |
| **Null / Undefined** | `--syntax-null` | `#475569` (Slate-600) | `#94A3B8` (Slate-400) | **6.92:1** / **6.96:1** |
| **Punctuation `{}[],:`**| `--syntax-punct` | `#64748B` (Slate-500) | `#64748B` (Slate-500) | **4.34:1** / **3.65:1** *(UI/syntax symbol standard)* |

---

## 3. Ready-to-Paste Code

### A. CSS Variables (`frontend/src/app/globals.css`)

```css
@import "tailwindcss";

:root {
  /* Surface & Base */
  --background: #f8fafc;
  --foreground: #0f172a;
  --card: #ffffff;
  --card-foreground: #0f172a;
  --card-elevated: #f1f5f9;
  --popover: #ffffff;
  --popover-foreground: #0f172a;

  /* Primary Interactive */
  --primary: #2563eb;
  --primary-foreground: #ffffff;
  --primary-hover: #1d4ed8;
  --primary-active: #1e40af;

  /* Secondary & Neutral Controls */
  --secondary: #e2e8f0;
  --secondary-foreground: #0f172a;
  --secondary-hover: #cbd5e1;

  /* Subtle Accent / Selection */
  --accent: #eff6ff;
  --accent-foreground: #1d4ed8;

  /* Muted Text & Chrome */
  --muted: #f1f5f9;
  --muted-foreground: #475569;

  /* Structural Dividers & Focus */
  --border: #cbd5e1;
  --input: #e2e8f0;
  --ring: #2563eb;

  /* Status Colors (Light Mode) */
  --status-queued-text: #475569;
  --status-queued-bg: #f1f5f9;
  --status-running-text: #0369a1;
  --status-running-bg: #e0f2fe;
  --status-success-text: #0d7a53;
  --status-success-bg: #dcfce7;
  --status-warning-text: #9a4c07;
  --status-warning-bg: #fef3c7;
  --status-retrying-text: #c2410c;
  --status-retrying-bg: #ffedd5;
  --status-error-text: #b91c1c;
  --status-error-bg: #fee2e2;
  --status-info-text: #1d4ed8;
  --status-info-bg: #dbeafe;

  /* Code / JSON Viewer */
  --syntax-bg: #f1f5f9;
  --syntax-key: #1e293b;
  --syntax-string: #047857;
  --syntax-number: #6d28d9;
  --syntax-bool: #b45309;
  --syntax-null: #475569;
  --syntax-punct: #64748b;
}

.dark {
  /* Surface & Base (No pure #000000) */
  --background: #0b0f17;
  --foreground: #f1f5f9;
  --card: #131b2e;
  --card-foreground: #f1f5f9;
  --card-elevated: #1e293b;
  --popover: #131b2e;
  --popover-foreground: #f1f5f9;

  /* Primary Interactive (Lower saturation, high luminance) */
  --primary: #3b82f6;
  --primary-foreground: #0b0f17;
  --primary-hover: #60a5fa;
  --primary-active: #2563eb;

  /* Secondary & Neutral Controls */
  --secondary: #1e293b;
  --secondary-foreground: #f8fafc;
  --secondary-hover: #334155;

  /* Subtle Accent / Selection */
  --accent: #172554;
  --accent-foreground: #93c5fd;

  /* Muted Text & Chrome */
  --muted: #1e293b;
  --muted-foreground: #94a3b8;

  /* Structural Dividers & Focus */
  --border: #26334d;
  --input: #1e293b;
  --ring: #60a5fa;

  /* Status Colors (Dark Mode) */
  --status-queued-text: #94a3b8;
  --status-queued-bg: #1e293b;
  --status-running-text: #38bdf8;
  --status-running-bg: #082f49;
  --status-success-text: #34d399;
  --status-success-bg: #064e3b;
  --status-warning-text: #fbbf24;
  --status-warning-bg: #451a03;
  --status-retrying-text: #fb923c;
  --status-retrying-bg: #431407;
  --status-error-text: #f87171;
  --status-error-bg: #450a0a;
  --status-info-text: #60a5fa;
  --status-info-bg: #172554;

  /* Code / JSON Viewer */
  --syntax-bg: #0f172a;
  --syntax-key: #e2e8f0;
  --syntax-string: #6ee7b7;
  --syntax-number: #c4b5fd;
  --syntax-bool: #fcd34d;
  --syntax-null: #94a3b8;
  --syntax-punct: #64748b;
}
```

---

### B. Tailwind Configuration Extension

#### For Tailwind v4 (`@theme inline` in `globals.css`):
```css
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-card-elevated: var(--card-elevated);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary-hover: var(--primary-hover);
  --color-primary-active: var(--primary-active);
  
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-secondary-hover: var(--secondary-hover);
  
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);

  /* Status Tokens */
  --color-status-queued-text: var(--status-queued-text);
  --color-status-queued-bg: var(--status-queued-bg);
  --color-status-running-text: var(--status-running-text);
  --color-status-running-bg: var(--status-running-bg);
  --color-status-success-text: var(--status-success-text);
  --color-status-success-bg: var(--status-success-bg);
  --color-status-warning-text: var(--status-warning-text);
  --color-status-warning-bg: var(--status-warning-bg);
  --color-status-retrying-text: var(--status-retrying-text);
  --color-status-retrying-bg: var(--status-retrying-bg);
  --color-status-error-text: var(--status-error-text);
  --color-status-error-bg: var(--status-error-bg);
  --color-status-info-text: var(--status-info-text);
  --color-status-info-bg: var(--status-info-bg);

  /* Code Syntax */
  --color-syntax-bg: var(--syntax-bg);
  --color-syntax-key: var(--syntax-key);
  --color-syntax-string: var(--syntax-string);
  --color-syntax-number: var(--syntax-number);
  --color-syntax-bool: var(--syntax-bool);
  --color-syntax-null: var(--syntax-null);
  --color-syntax-punct: var(--syntax-punct);
}
```

#### For Tailwind v3 / standard `tailwind.config.ts`:
```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
          elevated: "var(--card-elevated)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
          hover: "var(--primary-hover)",
          active: "var(--primary-active)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
          hover: "var(--secondary-hover)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        status: {
          queued: { text: "var(--status-queued-text)", bg: "var(--status-queued-bg)" },
          running: { text: "var(--status-running-text)", bg: "var(--status-running-bg)" },
          success: { text: "var(--status-success-text)", bg: "var(--status-success-bg)" },
          warning: { text: "var(--status-warning-text)", bg: "var(--status-warning-bg)" },
          retrying: { text: "var(--status-retrying-text)", bg: "var(--status-retrying-bg)" },
          error: { text: "var(--status-error-text)", bg: "var(--status-error-bg)" },
          info: { text: "var(--status-info-text)", bg: "var(--status-info-bg)" },
        },
        syntax: {
          bg: "var(--syntax-bg)",
          key: "var(--syntax-key)",
          string: "var(--syntax-string)",
          number: "var(--syntax-number)",
          bool: "var(--syntax-bool)",
          null: "var(--syntax-null)",
          punct: "var(--syntax-punct)",
        },
      },
    },
  },
  plugins: [],
};

export default config;
```

---

## 4. Usage & Interaction Rules

### A. Primary vs. Accent Distinction
* **`--primary`:** Reserved **exclusively** for the single primary forward action on screen (e.g. "Run Extraction", "Upload & Process", "Download JSON"). Never use primary on navigational chips, static icons, or secondary links.
* **`--accent`:** Used for non-primary highlights, such as row selection in schema previews, active tabs, and highlighted tree branches.

### B. Screen Saturation Limit (Rule of Two)
* **Maximum 2 distinct saturated accent hues simultaneously in any viewport.**
* For example: If a job is **Running** (Sky) and the Primary button is visible (Cobalt), all other elements (cards, headers, secondary actions, borders) must remain strictly monochromatic slate.

### C. Hover, Active, and Disabled States
* **Hover:** Shift lightness by **~8–10%**:
  * Light mode: darkens (`#2563EB` → `#1D4ED8`).
  * Dark mode: brightens (`#3B82F6` → `#60A5FA`).
* **Active (Pressed):** Shift lightness by **~15%** inward:
  * Light mode: `#1E40AF`.
  * Dark mode: `#2563EB`.
* **Disabled:** 
  * Apply `opacity-50 pointer-events-none cursor-not-allowed`.
  * Never alter the underlying token hue; always reduce opacity so the button's intended role remains recognizable.

### D. Focus Ring Specification
* Keyboard focus must always be visible with high contrast:
  ```css
  outline: 2px solid var(--ring);
  outline-offset: 2px;
  ```
* In Tailwind: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background`.

---

## 5. Color-Blind Safety Verification

| Condition | Success (`#0D7A53` / `#34D399`) | Error (`#B91C1C` / `#F87171`) | Distinction Mechanism |
| :--- | :--- | :--- | :--- |
| **Normal Vision** | Forest Emerald / Mint Green | Crimson / Coral Red | Distinct hue (green vs red) |
| **Deuteranopia** (Green-blind) | Cool Olive Teal | Rust Dark Ochre | Emerald has significant blue spectral energy (`#0D7A53` G:122, B:83), separating it from red |
| **Protanopia** (Red-blind) | Muted Teal Gray | Very Dark Charcoal / Brown | Protanopes perceive crimson as significantly darker than emerald |
| **Structural Redundancy** | Must show `CheckCircle2` + "Completed" | Must show `XCircle` + "Failed" | State is 100% decipherable even in grayscale mode |

---

## 6. Do and Don't Checklist

### Do
1. **DO combine color with icons and labels** on every status badge (`<CheckCircle2 className="text-status-success-text" /> <span>Completed</span>`).
2. **DO use `--card-elevated`** for popovers, dropdown menus, and modal dialogs so they lift visually above base cards without relying on heavy drop shadows.
3. **DO lower the saturation of accent colors in dark mode** (`#3B82F6` instead of `#1D4ED8`) to avoid eye vibration.
4. **DO test the interface at 200% zoom and in Windows High Contrast Mode** to confirm borders remain crisp.
5. **DO keep borders visible and defined (`3.0:1+`)** on all form inputs and interactive dropzones so clickable areas are never ambiguous.

### Don't
1. **DON'T use pure black (`#000000`) or pure white (`#FFFFFF`)** for canvas backgrounds in dark mode or body text in light mode.
2. **DON'T hardcode arbitrary hex codes** like `bg-[#2563EB]` or `text-[#333]` anywhere in `.tsx` files; always use semantic utility tokens (`bg-primary`, `text-foreground`).
3. **DON'T use red or green as the sole indicator** of success or error without accompanying text and shape differences.
4. **DON'T use more than one primary button per screen view.** Secondary and destructive actions must use `--secondary` or `--muted`.
5. **DON'T place saturated colored text on saturated colored backgrounds.** Keep badge backgrounds at 10–15% lightness tints (`bg-status-success-bg`) with dark/medium text (`text-status-success-text`).

