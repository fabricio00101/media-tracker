# DESIGN.md - Retro Terminal / Hacker Style

Inspiración: Terminales DOS, Matrix, Hack the Planet, Cyberpunk

## Brand

- **Nombre**: Media Tracker
- **Tono**: Hacker, underground, técnico
- **Sensación**: Estar en una terminal de película de los 90s

## Colors

### Background
| Token | Valor | Uso |
|-------|-------|-----|
| `bg-primary` | `#0D0D0D` | Fondo principal (negro puro) |
| `bg-surface` | `#141414` | Superficies de paneles |
| `bg-elevated` | `#1A1A1A` | Paneles elevados |
| `bg-scanline` | `rgba(0,0,0,0.1)` | Overlay de scanlines |

### Text Colors (Terminal Palette)
| Token | Valor | Uso |
|-------|-------|-----|
| `text-green` | `#00FF41` | Texto primario (verde Matrix) |
| `text-green-dim` | `#00CC33` | Texto secundario |
| `text-green-dark` | `#009922` | Texto muted |
| `text-amber` | `#FFB000` | Warnings, highlights |
| `text-red` | `#FF0040` | Errores, crítico |
| `text-cyan` | `#00FFFF` | Links, información |
| `text-white` | `#CCCCCC` | Solo para datos puros |

### Accents
| Token | Valor | Uso |
|-------|-------|-----|
| `accent-glow` | `rgba(0, 255, 65, 0.3)` | Glow verde |
| `accent-glow-amber` | `rgba(255, 176, 0, 0.3)` | Glow ámbar |
| `accent-border` | `#00FF41` | Borders activos |

## Typography

### Font Family
```css
--font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
```

> **TODO monoespaciado**. No hay fuente sans-serif en este diseño.

### Scale
| Elemento | Peso | Tamaño | Line-height |
|----------|------|--------|-------------|
| ASCII Title | 700 (Bold) | 14-16px | 1.2 |
| Section Header | 700 (Bold) | 14px | 1.3 |
| Prompt Line | 400 (Regular) | 14px | 1.5 |
| Body | 400 (Regular) | 13-14px | 1.5 |
| Data | 400 (Regular) | 13px | 1.4 |
| Tiny | 400 (Regular) | 11px | 1.3 |

### Special Text Effects
```css
/* Texto parpadeante (cursor) */
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
.cursor-blink { animation: blink 1s step-end infinite; }

/* Texto con glow */
.text-glow {
  text-shadow: 0 0 8px rgba(0, 255, 65, 0.6);
}

/* Texto glitch */
@keyframes glitch {
  0% { transform: translate(0); }
  20% { transform: translate(-2px, 2px); }
  40% { transform: translate(-2px, -2px); }
  60% { transform: translate(2px, 2px); }
  80% { transform: translate(2px, -2px); }
  100% { transform: translate(0); }
}
```

## Spacing

### Grid Base: 4px
```
4px  → xs
8px  → sm
12px → md
16px → lg
24px → xl
32px → 2xl
```

### Component Spacing
| Componente | Padding | Gap |
|------------|---------|-----|
| Terminal panel | 12-16px | 8px |
| Line (result) | 4px 0 | - |
| Section | 16px | 8px |
| Input | 8px 12px | - |
| Modal | 16px | 12px |

## Borders

### Radius
| Elemento | Radio |
|----------|-------|
| Todo | **0px** (recto, sin bordes redondeados) |

### Borders
```css
border-terminal: 1px solid #00FF41;
border-dim: 1px solid #333333;
border-active: 1px solid #00FF41;
```

### ASCII Borders
```
╔══════════════════════════════════════╗
║  TÍTULO                             ║
╠══════════════════════════════════════╣
║  Contenido                          ║
╚══════════════════════════════════════╝
```

O más simple:
```
┌──────────────────────────────────────┐
│ TÍTULO                               │
├──────────────────────────────────────┤
│ Contenido                            │
└──────────────────────────────────────┘
```

## Shadows

```css
shadow-glow-green: 0 0 10px rgba(0, 255, 65, 0.3);
shadow-glow-green-strong: 0 0 20px rgba(0, 255, 65, 0.5);
shadow-glow-amber: 0 0 10px rgba(255, 176, 0, 0.3);
shadow-panel: 0 2px 8px rgba(0, 0, 0, 0.5);
```

## Components

### Terminal Panel
- Fondo: `#141414`
- Borde: 1px `#00FF41`
- Radio: 0px
- Header fake de terminal:
```
┌─── bash ──────────────────────────────┐
│ $ media-tracker --search "inception"  │
│                                       │
│ [resultados aquí]                     │
│                                       │
│ $ _                                   │
└───────────────────────────────────────┘
```

### Prompt Input
- Fijo en la parte inferior del panel
- Prefijo: `$ ` o `> ` en verde
- Input sin borde, fondo transparente
- Cursor parpadeante al final
- **Focus**: Borde verde glow

```html
<div class="flex items-center text-[#00FF41]">
  <span class="mr-2">$</span>
  <input class="bg-transparent outline-none flex-1 caret-[#00FF41]" />
  <span class="cursor-blink">█</span>
</div>
```

### Result Line
- Formato: `[STATUS] Título (año) — Tamaño — Seeds:Leech`
- Status badges: `[✓]` verde, `[!]` ámbar, `[✗]` rojo
- Datos separados por ` — ` (em dash)
- Todo en una línea, wrap si es necesario

```
[✓] Inception (2010) — 4.2GB — 1523:42
[✓] Inception (2010) — 8.5GB REMUX — 892:31
[!] Inception (2010) — 1.2GB — 23:89  [LOW SEEDS]
```

### ASCII Art Header
```
╔═══════════════════════════════════════════════╗
║  ███╗   ███╗ ██████╗ ███████╗██╗████████╗    ║
║  ████╗ ████║██╔═══██╗██╔════╝██║╚══██╔══╝    ║
║  ██╔████╔██║██║   ██║███████╗██║   ██║       ║
║  ██║╚██╔╝██║██║   ██║╚════██║██║   ██║       ║
║  ██║ ╚═╝ ██║╚██████╔╝███████║██║   ██║       ║
║  ╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═╝   ╚═╝       ║
║         ██████╗ ██╗   ██╗██╗███╗   ██╗        ║
║         ██╔══██╗██║   ██║██║████╗  ██║        ║
║         ██████╔╝██║   ██║██║██╔██╗ ██║        ║
║         ██╔══██╗╚██╗ ██╔╝██║██║╚██╗██║        ║
║         ██║  ██║ ╚████╔╝ ██║██║ ╚████║        ║
║         ╚═╝  ╚═╝  ╚═══╝  ╚═╝╚═╝  ╚═══╝       ║
╚═══════════════════════════════════════════════╝
```

O más compacto:
```
MEDIA TRACKER v2.0 — [Torrent Search Engine]
═══════════════════════════════════════════════
```

### Filter Chips (ASCII style)
```
[FILTROS]
  Calidad: [ALL] [REMUX] [4K] [1080p] [WEB]
           ^^^^  (activo = entre corchetes + ^)
  Idioma:  [LAT] [CAST] [SUB] [ALL]
  Tamaño:  > [___] GB
```

### Progress/Loading
```
Buscando... [████████░░░░░░░░] 50%
```

O spinner ASCII:
```
Buscando... ⠋
Buscando... ⠙
Buscando... ⠹
Buscando... ⠸
```

### Status Bar (footer)
```
═══════════════════════════════════════════════
 Seeds: 15,392 | Leechers: 1,247 | Found: 2,847 | Cache: 5min
═══════════════════════════════════════════════
```

## Layout

### Structure
```
╔═══════════════════════════════════════════════════╗
║  MEDIA TRACKER v2.0                               ║
║  ═══════════════════════════════════════════════   ║
╠═══════════════════════════════════════════════════╣
║                                                   ║
║  $ > [search input_____________________________]  ║
║                                                   ║
║  [FILTROS]                                        ║
║  Calidad: [ALL] [4K] [1080p] [WEB]               ║
║  Idioma:  [LAT] [CAST] [SUB]                     ║
║                                                   ║
║  ┌─── RESULTADOS (2,847 encontrados) ───────────┐ ║
║  │ [✓] Inception (2010) — 4.2GB — 1523:42      │ ║
║  │ [✓] Inception (2010) — 8.5GB — 892:31       │ ║
║  │ [!] Interstellar (2014) — 1.2GB — 23:89     │ ║
║  │ [✓] The Matrix (1999) — 6.1GB — 2104:156    │ ║
║  │                                               │ ║
║  │ $ _                                           │ ║
║  └───────────────────────────────────────────────┘ ║
║                                                   ║
║  [CARGAR MÁS...]                                  ║
║                                                   ║
╠═══════════════════════════════════════════════════╣
║  Seeds: 15,392 | Found: 2,847 | v2.0             ║
╚═══════════════════════════════════════════════════╝
```

### Width
- Max-width: `900px`, centrado
- En mobile: `100%` con padding 8px

### Breakpoints
| Breakpoint | Comportamiento |
|------------|----------------|
| < 640px | Todo apilado, filtros colapsables |
| > 640px | Layout completo |

## Animations

### Effects
```css
/* Scanlines overlay */
.scanlines::after {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.1) 0px,
    rgba(0, 0, 0, 0.1) 1px,
    transparent 1px,
    transparent 2px
  );
  pointer-events: none;
  z-index: 9999;
}

/* CRT flicker */
@keyframes flicker {
  0% { opacity: 0.97; }
  50% { opacity: 1; }
}
body { animation: flicker 0.15s infinite; }

/* Typing effect */
@keyframes typing {
  from { width: 0; }
  to { width: 100%; }
}
```

### Hover
- **Result lines**: Background `#1A1A1A`, borde verde glow
- **Buttons**: Texto parpadeante + glow
- **Links**: Underline + color change

### Loading
- Spinner ASCII (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏)
- Barra de progreso ASCII
- Texto "Loading..." con typing effect

### Glitch Effect (opcional)
```css
@keyframes glitch {
  0% { clip-path: inset(40% 0 61% 0); transform: translate(-2px, 0); }
  20% { clip-path: inset(92% 0 1% 0); transform: translate(2px, 0); }
  40% { clip-path: inset(43% 0 1% 0); transform: translate(-1px, 0); }
  60% { clip-path: inset(25% 0 58% 0); transform: translate(1px, 0); }
  80% { clip-path: inset(54% 0 7% 0); transform: translate(-2px, 0); }
  100% { clip-path: inset(58% 0 43% 0); transform: translate(0); }
}
```

## Rules

1. **TODO monoespaciado**: Sin excepciones, JetBrains Mono siempre
2. **Sin bordes redondeados**: Radio 0px en todo
3. **Colores limitados**: Verde, ámbar, rojo, cyan. Nada más
4. **ASCII art decorativo**: Bordes, headers, status bars
5. **Prefijo de prompt**: Siempre mostrar `$` o `>` en inputs
6. **Cursor parpadeante**: En inputs y estados de carga
7. **Scanlines opcionales**: Overlay sutil para efecto CRT
8. ** Datos en líneas**: Un resultado = una línea, sin cards
9. **Status badges ASCII**: `[✓]` `[!]` `[✗]` en lugar de iconos
10. **Glitch sparingly**: Solo en hover de elementos especiales, no constante
