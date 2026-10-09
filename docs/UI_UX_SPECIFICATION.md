# UI/UX Mockup: AI-Driven Smart Logistics Platform

**Version:** 1.0 | **Target:** 80% prototype | **Style:** premium, muted, gradient-led

---

## 1. Design Direction

A quiet, high-end operations interface. Graphite and mist surfaces, soft steel gradients, and colour reserved strictly for status.

**Principles**

1. Neutral by default. Colour appears only when it carries meaning.
2. Gradients are subtle (same hue family, 8–15% lightness shift).
3. Status = colour + icon + text label. Never colour alone.
4. Serif numerals for KPIs, sans-serif for everything else.
5. One memorable element per screen (the lead KPI card or the AI card). Everything else stays quiet.

---

## 2. Design Tokens

### 2.1 Colour

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#E6E8EB` | `#0F1216` | Page background |
| `--bg-2` | `#D6DADF` | `#181C22` | Background gradient end |
| `--surface` | `#F6F7F8` | `#1B2027` | Cards |
| `--surface-2` | `#ECEEF0` | `#232932` | Inset panels, inputs |
| `--line` | `#D3D7DC` | `#2D343E` | Borders, dividers |
| `--ink` | `#171A1F` | `#E7EAEE` | Primary text |
| `--mute` | `#5E6670` | `#98A1AD` | Secondary text |
| `--accent-1` | `#4A5563` | `#7C8898` | Gradient start |
| `--accent-2` | `#2C333D` | `#4B5563` | Gradient end |

### 2.2 Status colours (muted)

| Status | Light | Dark | Icon | Label example |
|---|---|---|---|---|
| Healthy / available | `#4F6B5A` | `#88A594` | ✓ | Available |
| Warning | `#8A6A34` | `#C0A063` | ▲ | Low battery |
| Critical | `#8C4A47` | `#C58783` | ✕ | Speeding |
| Active / info | `#4A6078` | `#8FA6BE` | ● | On route |

### 2.3 Gradients

```css
--grad-lead:    linear-gradient(135deg, #4A5563, #2C333D); /* lead KPI, primary button, ETA card */
--grad-side:    linear-gradient(180deg, #20252C, #14171C); /* sidebar */
--grad-page:    linear-gradient(160deg, #E6E8EB, #D6DADF); /* page background */
--grad-inset:   linear-gradient(160deg, #F6F7F8, #ECEEF0); /* AI recommendation card */
```

### 2.4 Typography

| Role | Font | Fallback | Size / weight |
|---|---|---|---|
| Page title | Newsreader | Georgia, serif | 26 / 400 |
| Hero KPI | Newsreader | Georgia, serif | 40 / 400 |
| KPI | Newsreader | Georgia, serif | 30 / 400 |
| Section title | Instrument Sans | system-ui, sans-serif | 15 / 500 |
| Body | Instrument Sans | system-ui, sans-serif | 14 / 400 |
| Caption, table | Instrument Sans | system-ui, sans-serif | 12.5 / 400 |

### 2.5 Shape, spacing, elevation

- Radius: 18 (frames), 14 (cards), 10 (inputs, map), 9 (buttons), 999 (badges)
- Spacing scale: 4, 8, 12, 16, 24, 32
- Shadow: `0 1px 2px rgba(20,23,28,.06), 0 12px 32px -12px rgba(20,23,28,.18)`

---

## 3. Global Layout

```text
┌────────────────────────────────────────────────────────────┐
│ Search                          ▲ 3 critical alerts   User │
├─────────────┬──────────────────────────────────────────────┤
│  Meridian   │  Dashboard                                   │
│ ▌Dashboard  │  ┌────────┬──────┬──────┬──────┬─────┬─────┐ │
│  Warehouse  │  │ LEAD   │ KPI  │ KPI  │ KPI  │ KPI │ KPI │ │
│  Deliveries │  └────────┴──────┴──────┴──────┴─────┴─────┘ │
│  Safety     │  ┌───────────────────────┬──────────────────┐│
│  EV charging│  │ Live operations map   │ AI recommendation││
│  Analytics  │  │                       ├──────────────────┤│
│  AI insights│  │                       │ Safety events    ││
│  Settings   │  └───────────────────────┴──────────────────┘│
└─────────────┴──────────────────────────────────────────────┘
```

Mobile (< 768 px): header, page content, bottom navigation. Sidebar becomes a horizontal scroll strip on small tablets.

---

## 4. Screens

### 4.1 Dashboard (Fleet Manager, desktop)

**KPI row** (lead card uses `--grad-lead`, the rest use `--surface-2`):

| Orders Today (lead) | Active Deliveries | Safety Score | Warehouse Efficiency | EVs Charging | Delayed |
|---|---|---|---|---|---|
| 12,480 | 382 | 91 | 87% | 42 | 17 |

**Below the KPIs**

- Live operations map with vehicle markers and route lines.
- Status legend: `● On route`, `▲ Charging needed`, `✕ Speeding`.
- Safety event list:

| Time | Vehicle | Event | Severity |
|---|---|---|---|
| 18:02 | V101 | Speeding | ✕ High |
| 18:04 | V113 | Harsh braking | ▲ Medium |
| 18:06 | V108 | Route deviation | ▲ Medium |

### 4.2 AI Recommendation Card

```text
┌──────────────────────────────────────────┐
│ AI recommendation                Charging│
│                                          │
│ Reserve Station S04 for V104.            │
│ Low wait and a short detour.             │
│                                          │
│ Confidence 88%                           │
│ ██████████████████░░░░                   │
│                                          │
│ Based on: battery level, distance,       │
│ queue, route, connector availability.    │
│                                          │
│ [Accept]  [Reject]  [Details]            │
└──────────────────────────────────────────┘
```

Rules: never show a bare "AI says X". Always show reason, confidence and inputs. Primary button uses `--grad-lead`.

### 4.3 Driver Mobile Home (360 px)

```text
┌───────────────────────────┐
│ Good evening              │
│ ┌───────────────────────┐ │
│ │ Delivery D1024        │ │
│ │ ETA 18:42             │ │
│ │ 3.2 km remaining      │ │
│ │ [Start navigation]    │ │
│ └───────────────────────┘ │
│ Safety score          88  │
│  Speed compliant  ✓ Good  │
│  1 harsh braking  ▲ Review│
│                           │
│ Charging          24%     │
│  Station S04 · 0.8 km     │
│  detour · ~6 min wait     │
│  [Reserve slot]           │
│                           │
│ Home  Route  Charge Safety│
└───────────────────────────┘
```

### 4.4 Warehouse Pick Task

```text
Batch #B102                        Estimated 8 min · 125 m

1. Aisle A → Shelf 04 → SKU 1023
2. Aisle B → Shelf 11 → SKU 2091
3. Aisle C → Shelf 02 → SKU 3012

[Start]  [Pause]  [Complete]
```

Map legend: `● Picker`, `□ Pick location`, `— Normal path`, `━━ Optimized path`, `X Blocked`. The optimized path uses the accent gradient stroke.

### 4.5 EV Station Detail

```text
Station S04                       ✓ Operational

C1 ✓ Available    C2 ● Charging    C3 ✓ Available
C4 ● Reserved     C5 ✕ Fault       C6 ✓ Available

Queue
1. V104 — 4 min
2. V118 — 9 min

[Block connector]  [Create maintenance alert]
```

### 4.6 Charging Recommendation

```text
Recommended station
S04 · 2.1 km · 7 min wait · 22 kW · about 32 min to charge

Why
• Short route detour
• Low queue
• Connector available

[Reserve]  [View alternatives]
```

---

## 5. Component Inventory

| Component | Notes |
|---|---|
| KPI card | Label above, serif number below. One lead variant with gradient. |
| Status badge | Outline pill, coloured text, icon + label. |
| Alert card | Severity badge, source, timestamp, Acknowledge and View details. |
| AI recommendation card | Reason, confidence bar, inputs, Accept/Reject/Details. |
| Data table | Compact rows, 1px `--line` dividers. Becomes cards below 768 px. |
| Map panel | Gradient inset, muted route strokes, status-coloured markers. |
| Buttons | Primary (gradient), secondary (outline). Sentence case, verb-first. |
| Modal, drawer, confirmation dialog | Destructive actions always confirm. |
| Empty, loading skeleton, error | See section 6. |

---

## 6. UI States (every major screen)

| State | Behaviour |
|---|---|
| Loading | Skeleton blocks in `--surface-2`, no spinner-only screens. |
| Success | Inline confirmation, e.g. "Slot reserved". |
| Empty | Say what is missing and offer the next action. |
| Error | Plain language, with a way to recover. |
| Offline | Show last known state with a timestamp. |

Examples:

```text
Unable to load charging availability.
Showing last known state from 18:40.
[Retry]
```

```text
Cancel reservation?
This will release the charging slot.
[Cancel reservation]  [Keep]
```

Long-running optimization shows staged progress: Preparing orders ✓, Building constraints ✓, Running optimizer…, Generating result.

---

## 7. Responsive Rules

| Breakpoint | Layout |
|---|---|
| < 768 px | Cards instead of tables, bottom navigation, full-width map, fixed bottom actions |
| 768–1024 px | 3-column KPI grid, single-column content |
| > 1024 px | Sidebar, 6-column KPI row, 2-column content |

---

## 8. Accessibility

- Keyboard navigation with visible focus (2 px ring, `--info` colour).
- Text contrast at least 4.5:1 on all surfaces, in both themes.
- No colour-only status. Every status has an icon and a label.
- Icon-only controls need text labels or `aria-label`.
- Respect `prefers-reduced-motion` and `prefers-color-scheme`.
- Error messages are plain text and announced to assistive tech.

---

## 9. Acceptance Checklist

- [ ] Each persona reaches their main task in 3 navigation actions or fewer.
- [ ] Critical alerts are visible without opening the AI panel.
- [ ] Every AI recommendation shows reason, confidence and inputs.
- [ ] Driver screen works at 360 px.
- [ ] Light and dark themes both pass contrast checks.
- [ ] All screens implement loading, empty, error and offline states.

---

## 10. Build Order

1. Design tokens
2. App shell
3. Dashboard
4. Warehouse pages
5. Delivery and safety pages
6. EV pages
7. AI insights
8. Responsive behaviour
9. States and accessibility
10. Usability testing

