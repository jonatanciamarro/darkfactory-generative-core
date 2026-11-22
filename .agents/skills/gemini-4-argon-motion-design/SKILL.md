---
name: gemini-4-argon-motion-design
description: Build and render ultra-high-fidelity motion design, tactical telemetry, and investigative documentary sequences using the Swiss-Telemetry Kinetic Manifesto (Josef Müller-Brockmann × GMUNK × Kyle Cooper). Features 1080p60/1080p30 HyperFrames & GSAP 3.14 deterministic pipelines, monumental typography (Big Shoulders Display 900/300 + IBM Plex Mono tabular telemetry + Instrument Serif italic), CSS 3D Z-space parallax camera rigs (perspective 1250px), Catmull-Rom trajectory splines with ±2σ confidence bands and anomaly locks, and dramatic polarity inversions between deep obsidian (#090A0D) and archival paper (#F4F1EA).
license: MIT
compatibility: Node 22+, Python 3.11+ with Playwright & Chromium, FFmpeg 6+, GSAP 3.14.
---

# Gemini 4 Argon Motion Design // Swiss-Telemetry Kinetic Manifesto

A mathematically locked motion design engine (HyperFrames + GSAP 3.14 + CSS 3D + SVG + Playwright Headless Chromium) created for dark documentary thrillers, investigative OSINT visualizations, and monumental kinetic typography.

## 1. Visual & Spatial Foundations

### Core Color Palettes
- **Dark Polarity (Telemetry / Bunker / OSINT)**:
  - Canvas: `#090A0D` (Radial depth vignette to `#151A28`, never flat `#000000`)
  - Elevated Cards / Terminals: `#131722` with `1px solid #2A3246`
  - Titanium White Display: `#F7F6F2` (18.4:1 contrast)
  - Telemetry Silver: `#A3ADC2` (Readouts and labels)
  - Acid Volt: `#D4FF00` (High-velocity vectors, reticle locks, active indicators)
  - Signal Vermilion: `#FF4D38` / `#FF6452` (Alerts, anomalies, focal trajectory markers)
  - Cyan Telemetry: `#5CE1E6` (Grid coordinates, orbital lines)
- **Light Polarity (Declassified Archival Paper / Dossier Inversion)**:
  - Archival Paper: `#F4F1EA` (Aged parchment tone)
  - Stone Panel: `#E6E1D6` with `2px solid #0B0C10` rules
  - Carbon Ink: `#0B0C10` (Monumental typography and borders)
  - International Crimson: `#B01204` / `#C81908` (Confidential stamps and critical alerts)
  - Cobalt Telemetry: `#0033B8` (Technical annotations and calipers)

### Typography Stack
- **Primary Display**: `Big Shoulders Display` (weights `900` Black and `300` Light). Tight tracking (`-0.03em`), line-height `0.92`.
- **Technical Telemetry**: `IBM Plex Mono` (weights `400` Regular and `600` SemiBold). Tabular numbers: `font-variant-numeric: tabular-nums; font-variant-ligatures: none;`.
- **Editorial Counter-Voice**: `Instrument Serif` (`400 Italic`). Used for human emotional tension against mechanical telemetry.
- **Banned Fonts**: `Inter`, `Roboto`, `Open Sans`, `Poppins`, `Outfit`, `Syne`.

## 2. 3D Spatial Rigging (CSS 3D Stage)
```css
.stage-3d-viewport {
  perspective: 1250px;
  perspective-origin: 50% 50%;
  transform-style: preserve-3d;
}
.rig-3d {
  transform-style: preserve-3d;
}
```
Stepped Z-Planes:
- `Z = -200px` (`0.68×` scale): Background telemetry grid / starfield / radar grid.
- `Z = -100px`: Historical archival photography / CRT phosphor monitor.
- `Z = 0px` (`1.00×` scale): Tactical HUD, focal crosshairs, Catmull-Rom trajectory curves.
- `Z = +100px`: Monumental title slabs, status pills, classification badges.
- `Z = +200px` (`1.42×` scale): Volumetric god rays, lens flares, scanline overlays.

Driven by 3-axis Euler gimbal:
```javascript
tl.fromTo("#s2-rig", 
  { rotationX: 18, rotationY: -24, rotationZ: -2 }, 
  { rotationX: -12, rotationY: 22, rotationZ: 2, duration: 6.4, ease: "sine.inOut" }
);
```

## 3. Telemetry & Trajectory Math
- **Catmull-Rom Trajectory Splines**: Plotted with SVG `<path>` and animated with `strokeDashoffset`.
- **Confidence Corridors**: Semi-transparent polygons/ribbons (`fill: rgba(212, 255, 0, 0.12)`) bounding normal variance (`±2σ`).
- **Anomaly Reticle Locks**: Animated targeting brackets snapping to radar glitches (`+4.82σ`).
- **Tabular Counters**: Real-time frame and timestamp clocks updating synchronously without drift.

## 4. Deterministic Timeline Contract
- Every composition is registered to `window.__timelines["main"] = tl`.
- `tl = gsap.timeline({ paused: true });`
- All animations are deterministic: zero `Math.random()`, zero `Date.now()`, zero `requestAnimationFrame`. Use seeded PRNG (`mulberry32`).
- Headless render seek loop via Playwright Chromium: `window.__timelines["main"].seek(f / fps)`.
- Frames are piped directly to FFmpeg at 1080p (`-c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p`).
