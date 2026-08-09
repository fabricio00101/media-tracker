# DESIGN.md - Bento Grid Style

Inspiración: Bento box layout, Apple WWDC layouts, Dashboard UIs 2026

## Brand

- **Nombre**: Media Tracker
- **Tono**: Moderno, vibrante, técnico
- **Sensación**: Dashboard de alta tecnología con estética japonesa minimalista

## Colors

### Background
| Token | Valor | Uso |
|-------|-------|-----|
| `bg-primary` | `#0A0A0F` | Fondo principal |
| `bg-surface` | `#12121A` | Superficies de bento boxes |
| `bg-elevated` | `#1A1A24` | Elementos elevados |
| `bg-hover` | `#1F1F2A` | Estados hover |

### Gradients (Aurora)
| Token | Valor | Uso |
|-------|-------|-----|
| `gradient-aurora` | `linear-gradient(135deg, #0A0A0F 0%, #1A0533 50%, #071A2F 100%)` | Fondo animado |
| `gradient-accent` | `linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%)` | Elementos de acento |

### Accents
| Token | Valor | Uso |
|-------|-------|-----|
| `accent-primary` | `#8B5CF6` | Violeta primario |
| `accent-secondary` | `#06B6D4` | Cyan secundario |
| `accent-tertiary` | `#A855F7` | Violeta claro |
| `accent-glow-violet` | `rgba(139, 92, 246, 0.25)` | Glow violeta |
| `accent-glow-cyan` | `rgba(6, 182, 212, 0.25)` | Glow cyan |

### Text
| Token | Valor | Uso |
|-------|-------|-----|
| `text-primary` | `#F0F0F5` | Títulos principales |
| `text-secondary` | `#A0A0B8` | Descripciones |
| `text-muted` | `#606078` | Labels, metadata |
| `text-accent` | `#8B5CF6` | Links, elementos interactivos |

## Typography

### Font Family
```css
--font-display: 'Space Grotesk', sans-serif;
--font-body: 'Inter', sans-serif;
--font-mono: 'JetBrains Mono', monospace;
```

### Scale
| Elemento | Fuente | Peso | Tamaño | Line-height |
|----------|--------|------|--------|-------------|
| Hero Title | Display | 700 (Bold) | 40-56px | 1.1 |
| Section Title | Display | 600 (SemiBold) | 24-28px | 1.2 |
| Bento Title | Display | 600 (SemiBold) | 18-20px | 1.3 |
| Card Title | Body | 600 (SemiBold) | 14-16px | 1.3 |
| Body | Body | 400 (Regular) | 14px | 1.5 |
| Caption | Body | 400 (Regular) | 12px | 1.4 |
| Stat Number | Mono | 700 (Bold) | 24-32px | 1.0 |
| Stat Label | Body | 400 (Regular) | 11-12px | 1.3 |
| Badge | Body | 600 (SemiBold) | 11px | 1.0 |

### Letter Spacing
- Display: `-0.03em` (compacto)
- Body: `0`
- Stats: `-0.02em`

## Spacing

### Grid Base: 8px
```
4px  → xxs
8px  → xs
12px → sm
16px → md
20px → lg
24px → xl
32px → 2xl
48px → 3xl
```

### Bento Grid Gap
- Gap entre boxes: `12-16px`
- Padding interno de boxes: `20-24px`

### Component Spacing
| Componente | Padding | Gap |
|------------|---------|-----|
| Bento box | 20-24px | 12-16px |
| Stat card | 16-20px | 8px |
| Badge | 4px 10px | - |
| Chip | 6px 12px | 6px |

## Borders

### Radius
| Elemento | Radio |
|----------|-------|
| Bento box | 16px |
| Card pequeña | 12px |
| Badge | 8px |
| Button | 10px |
| Input | 10px |
| Chip | 8px |

### Borders
```css
border-default: 1px solid rgba(139, 92, 246, 0.15);
border-hover: 1px solid rgba(139, 92, 246, 0.35);
border-cyan: 1px solid rgba(6, 182, 212, 0.2);
```

## Shadows

```css
shadow-box: 0 4px 24px rgba(0, 0, 0, 0.4);
shadow-box-hover: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 24px rgba(139, 92, 246, 0.1);
shadow-glow-violet: 0 0 30px rgba(139, 92, 246, 0.2);
shadow-glow-cyan: 0 0 30px rgba(6, 182, 212, 0.2);
shadow-glow-intense: 0 0 40px rgba(139, 92, 246, 0.35);
```

## Components

### Bento Box
- Superficie: `#12121A` con blur backdrop
- Border: 1px `rgba(139,92,246,0.15)`
- Radio: 16px
- Padding: 20-24px
- **Hover**: Border se intensifica, glow sutil
- Overflow hidden para content que se desborda

### Grid Sizes
```
┌─────────┬─────────┬─────────┬─────────┐
│  1x1    │  1x1    │  2x1    │         │
│         │         │         │         │
├─────────┼─────────┤         ├─────────┤
│  1x1    │  1x1    │         │  1x1    │
│         │         │         │         │
├─────────┴─────────┼─────────┼─────────┤
│      2x1          │  1x1    │  1x1    │
│                   │         │         │
├───────────────────┼─────────┴─────────┤
│  1x1              │      2x1          │
│                   │                   │
└───────────────────┴───────────────────┘
```

### Bento Box Types

#### Hero Box (2x1 o 2x2)
- Poster grande de fondo con opacidad reducida
- Título superpuesto con gradiente
- Badge de calidad grande

#### Stat Box (1x1)
- Número grande mono bold (ej: "2,847")
- Label pequeño debajo
- Icono decorativo con opacidad reducida

#### Result Box (1x1 o 2x1)
- Poster pequeño + info
- Tags de calidad como chips
- Seeds/leechers con iconos

#### Filter Box (sidebar, 1x1 height variable)
- Título de sección
- Chips/toggles apilados verticalmente

### Chips/Filtros
- Fondo inactive: `rgba(255,255,255,0.04)`
- Borde inactive: 1px `rgba(255,255,255,0.08)`
- Texto inactive: `#A0A0B8`
- **Active**: Gradiente border, fondo `rgba(139,92,246,0.15)`, texto `#8B5CF6`
- Radio: 8px
- Font: 13px

### Search Bar
- Dentro de un bento box dedicado
- Fondo: `rgba(255,255,255,0.04)`
- Borde: 1px `rgba(139,92,246,0.15)`
- Radio: 10px
- Input: texto blanco 14px
- Botón: gradiente violeta→cyan

### Stat Cards
- Número: Space Grotesk bold 28-32px
- Label: Inter regular 11px, muted
- Posible icono animado (spinner, pulse)

### Quality Tags
- Chips con color de fondo
- 4K: `rgba(255,215,0,0.15)` + `#FFD700`
- HDR: `rgba(0,191,255,0.15)` + `#00BFFF`
- REMUX: `rgba(255,107,107,0.15)` + `#FF6B6B`
- Radio: 8px, padding 4px 10px

## Layout

### Structure (Desktop)
```
┌──────────────────────────────────────────────────┐
│  ┌─────────────────────┬──────────────────────┐  │
│  │   HERO BOX (2x1)    │   STAT: Encontrados  │  │
│  │   Poster + Título   │      2,847           │  │
│  │                     ├──────────────────────┤  │
│  │                     │   STAT: Seeds        │  │
│  │                     │      15,392          │  │
│  ├─────────┬───────────┼──────┬───────────────┤  │
│  │ Filtros │ Filtros   │ Búsqueda             │  │
│  │ Calidad │ Idioma    │ [______________] 🔍  │  │
│  │ 4K ✓    │ Lat    ✓  │                      │  │
│  │ 1080p   │ Cast       ├──────┬──────────────┤  │
│  │ HDR ✓   │ Sub        │ Res  │ Res          │  │
│  ├─────────┴───────────┤  1    │  2           │  │
│  │ Result 1            │      │              │  │
│  │ [poster] info       ├──────┼──────────────┤  │
│  ├─────────────────────┤ Res  │ Res          │  │
│  │ Result 2            │  3    │  4           │  │
│  │ [poster] info       │      │              │  │
│  └─────────────────────┴──────┴──────────────┘  │
└──────────────────────────────────────────────────┘
```

### CSS Grid
```css
.bento-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: minmax(180px, auto);
  gap: 12-16px;
}

/* Box sizes */
.box-1x1 { grid-column: span 1; grid-row: span 1; }
.box-2x1 { grid-column: span 2; grid-row: span 1; }
.box-1x2 { grid-column: span 1; grid-row: span 2; }
.box-2x2 { grid-column: span 2; grid-row: span 2; }
```

### Breakpoints
| Breakpoint | Columnas | Comportamiento |
|------------|----------|----------------|
| < 640px | 1 | Todo apilado verticalmente |
| 640-1024px | 2 | Bento boxes 2 columnas |
| > 1024px | 4 | Grid completo con多种 sizes |

## Animations

### Transitions
```css
transition-box: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
transition-fast: all 150ms ease;
```

### Hover Effects
- **Bento boxes**: Border intensifica + `box-shadow` glow
- **Chips**: Scale 1.02 + glow
- **Numbers**: Pulse sutil (scale 1.02)

### Background Animation
```css
@keyframes aurora {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.aurora-bg {
  background: linear-gradient(135deg, #0A0A0F, #1A0533, #071A2F, #0A0A0F);
  background-size: 400% 400%;
  animation: aurora 15s ease infinite;
}
```

### Stagger-in
```css
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.bento-box {
  animation: fadeInUp 0.4s ease forwards;
  animation-delay: calc(var(--index) * 80ms);
}
```

### Loading
- Skeleton boxes con shimmer gradiente
- Spinner violeta en stat boxes

## Rules

1. **Asimetría intencional**: No todos los boxes del mismo tamaño
2. **Jerarquía por tamaño**: 2x2 = hero/destacado, 1x1 = info secundaria
3. **Glow moderation**: Solo en hover, nunca permanente
4. **Gradientes sutiles**: Aurora de fondo siempre dark, nunca bright
5. **Un gradiente de acento**: Violeta→Cyan para botones y borders especiales
6. **Datos grandes en stat boxes**: Números mono bold como elemento visual
7. **Chips sobre checkboxes**: Filtros como chips inline, no listas
8. **Padding generoso**: 20-24px mínimo en boxes
9. **Animaciones suaves**: Solo fade-in y hover, sin bounce ni elastic
10. **Mobile first apilado**: En mobile todo 1 columna, sin perder info
