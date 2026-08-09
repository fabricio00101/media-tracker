# DESIGN.md - Glassmorphism Premium Style

Inspiración: Apple Vision Pro, Stripe, Linear Premium, Aurora UI

## Brand

- **Nombre**: Media Tracker
- **Tono**: Premium, elegante, sofisticado
- **Sensación**: Interfaz de producto de alta gama, sensación táctil

## Colors

### Background
| Token | Valor | Uso |
|-------|-------|-----|
| `bg-primary` | `#0F0720` | Fondo principal (deep purple-black) |
| `bg-aurora-1` | `#1A0533` | Aurora position 1 |
| `bg-aurora-2` | `#071A2F` | Aurora position 2 |
| `bg-aurora-3` | `#0F2027` | Aurora position 3 |

### Glass Surfaces
| Token | Valor | Uso |
|-------|-------|-----|
| `glass-bg` | `rgba(255, 255, 255, 0.03)` | Superficie base |
| `glass-bg-hover` | `rgba(255, 255, 255, 0.06)` | Hover state |
| `glass-border` | `rgba(255, 255, 255, 0.08)` | Borde sutil |
| `glass-border-hover` | `rgba(255, 255, 255, 0.15)` | Borde hover |
| `glass-blur` | `blur(20px)` | backdrop-filter |

### Accents
| Token | Valor | Uso |
|-------|-------|-----|
| `accent-primary` | `#A855F7` | Violeta principal |
| `accent-secondary` | `#14B8A6` | Teal secundario |
| `accent-tertiary` | `#EC4899` | Rosa (terciario) |
| `accent-gradient` | `linear-gradient(135deg, #A855F7, #14B8A6)` | Gradiente de acento |
| `accent-glow` | `rgba(168, 85, 247, 0.3)` | Glow violeta |
| `accent-glow-teal` | `rgba(20, 184, 166, 0.3)` | Glow teal |

### Text
| Token | Valor | Uso |
|-------|-------|-----|
| `text-primary` | `#F8F8FF` | Títulos (near-white with slight blue) |
| `text-secondary` | `#B8B8D0` | Descripciones |
| `text-muted` | `#6B6B88` | Labels |
| `text-accent` | `#A855F7` | Links, elementos interactivos |

## Typography

### Font Family
```css
--font-display: 'Plus Jakarta Sans', sans-serif;
--font-body: 'Inter', sans-serif;
--font-mono: 'JetBrains Mono', monospace;
```

### Scale
| Elemento | Fuente | Peso | Tamaño | Line-height |
|----------|--------|------|--------|-------------|
| Hero Title | Display | 800 (ExtraBold) | 48-64px | 1.1 |
| Section Title | Display | 700 (Bold) | 28-36px | 1.2 |
| Card Title | Display | 600 (SemiBold) | 18-22px | 1.3 |
| Body | Body | 400 (Regular) | 15-16px | 1.6 |
| Caption | Body | 400 (Regular) | 13px | 1.4 |
| Badge | Body | 600 (SemiBold) | 12px | 1.0 |
| Stat Number | Display | 800 (ExtraBold) | 36-48px | 1.0 |

### Letter Spacing
- Display: `-0.04em` (muy compacto, elegante)
- Body: `0`
- Badge uppercase: `0.08em`

## Spacing

### Grid Base: 8px
```
4px  → xxs
8px  → xs
12px → sm
16px → md
24px → lg
32px → xl
48px → 2xl
64px → 3xl
96px → 4xl
```

### Component Spacing
| Componente | Padding | Gap |
|------------|---------|-----|
| Glass card | 24-32px | 16-20px |
| Hero section | 64-96px vertical | 24-32px |
| Modal | 32px | 24px |
| Search bar | 16-20px | 12px |
| Badge | 6px 14px | - |
| Chip | 8px 16px | 8px |

## Borders

### Radius
| Elemento | Radio |
|----------|-------|
| Glass card | 20px |
| Large card | 24px |
| Button | 14px |
| Badge | 10px |
| Input | 14px |
| Modal | 24px |
| Pill | 999px |

### Borders
```css
/* Base glass border */
border-glass: 1px solid rgba(255, 255, 255, 0.08);

/* Hover state */
border-glass-hover: 1px solid rgba(255, 255, 255, 0.15);

/* Inner glow border */
border-inner: inset 0 1px 0 rgba(255, 255, 255, 0.1);

/* Accent border */
border-accent: 1px solid rgba(168, 85, 247, 0.3);
```

## Shadows

### Multi-layer Shadows (Premium feel)
```css
/* Card base */
shadow-card: 
  0 4px 16px rgba(0, 0, 0, 0.3),
  0 8px 32px rgba(0, 0, 0, 0.2),
  inset 0 1px 0 rgba(255, 255, 255, 0.1);

/* Card hover */
shadow-card-hover:
  0 8px 32px rgba(0, 0, 0, 0.4),
  0 16px 48px rgba(0, 0, 0, 0.3),
  inset 0 1px 0 rgba(255, 255, 255, 0.15);

/* Glow effects */
shadow-glow-violet: 0 0 40px rgba(168, 85, 247, 0.25);
shadow-glow-teal: 0 0 40px rgba(20, 184, 166, 0.25);
shadow-glow-intense: 0 0 60px rgba(168, 85, 247, 0.4);

/* Modal */
shadow-modal:
  0 24px 80px rgba(0, 0, 0, 0.6),
  0 0 1px rgba(255, 255, 255, 0.1);
```

## Components

### Glass Card
- Background: `rgba(255,255,255,0.03)`
- Backdrop-filter: `blur(20px)`
- Border: 1px `rgba(255,255,255,0.08)`
- Border-radius: 20px
- Box-shadow: multi-layer
- **Hover**: Background `rgba(255,255,255,0.06)`, border intensifica, glow sutil

```html
<div class="glass-card rounded-[20px] p-6 
            bg-white/[0.03] backdrop-blur-xl 
            border border-white/[0.08]
            shadow-[0_4px_16px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.1)]
            hover:bg-white/[0.06] hover:border-white/[0.15]
            transition-all duration-300">
  <!-- content -->
</div>
```

### Hero Section
- Gradiente aurora animado de fondo
- Título con gradiente de texto (white → purple → teal)
- Glow effects decorativos (orbs de color con blur)
- Search bar integrada en el hero

```css
.hero-title {
  background: linear-gradient(135deg, #F8F8FF 0%, #A855F7 50%, #14B8A6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
```

### Glow Orbs (decorative)
- Posicionados absolute, grande (200-400px), blur muy fuerte (80-120px)
- Colores: violeta y teal con opacidad baja (0.15-0.25)
- Animación de float lenta

```html
<div class="absolute top-[-100px] left-[-100px] w-[400px] h-[400px] 
            rounded-full bg-purple-500/20 blur-[120px] pointer-events-none" />
<div class="absolute bottom-[-100px] right-[-100px] w-[300px] h-[300px] 
            rounded-full bg-teal-500/20 blur-[100px] pointer-events-none" />
```

### Search Bar
- Glass background con blur
- Borde con gradiente (violeta → teal) en focus
- Botón con gradiente de acento
- Icono de búsqueda con glow

```css
.search-bar {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  transition: all 0.3s ease;
}

.search-bar:focus-within {
  border-color: transparent;
  box-shadow: 0 0 0 2px rgba(168, 85, 247, 0.3);
}

.search-btn {
  background: linear-gradient(135deg, #A855F7, #14B8A6);
  border-radius: 10px;
  color: white;
  font-weight: 600;
}
```

### Filter Chips
- Glass background sutil
- Borde white/8
- **Active**: Gradiente border, fondo `rgba(168,85,247,0.15)`, glow
- Radio: 999px (pill shape)

```html
<button class="px-4 py-2 rounded-full text-sm font-medium
               bg-white/[0.03] border border-white/[0.08]
               hover:bg-white/[0.06] transition-all
               active:border-purple-500/30 active:bg-purple-500/10
               active:shadow-[0_0_20px_rgba(168,85,247,0.2)]">
  4K UHD
</button>
```

### Result Cards
- Glass card con poster + info
- Poster con overlay gradiente
- Tags de calidad con colores
- Glow en hover

### Quality Tags
- 4K: `rgba(255,215,0,0.2)` + `#FFD700` + glow dorado
- HDR: `rgba(0,191,255,0.2)` + `#00BFFF` + glow cyan
- REMUX: `rgba(255,107,107,0.2)` + `#FF6B6B` + glow rojo
- Radio: 10px, padding 5px 12px, borde con glow

### Button Primary
- Background: gradiente `#A855F7 → #14B8A6`
- Texto: blanco bold
- Radio: 14px
- Padding: 12px 24px
- **Hover**: Intensidad del gradiente + glow shadow
- **Active**: Scale 0.98

### Progress Ring
- SVG circular con stroke gradiente
- Glow en el trazo
- centrado con label

## Layout

### Structure
```
┌──────────────────────────────────────────────────┐
│  ★ GLOW ORB (decorative, absolute)               │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  MEDIA TRACKER                             │  │
│  │  Buscador de Alta Fidelidad                 │  │
│  │                                            │  │
│  │  ┌──────────────────────────────────┐ 🔍  │  │
│  │  │ [Buscar película o serie...]     │ BUSCAR│ │
│  │  └──────────────────────────────────┘      │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ FILTROS                                    │  │
│  │ [Todos] [Películas] [Series] [Docs]       │  │
│  │ [4K] [1080p] [HDR] [REMUX]               │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  POSTER  │ │  POSTER  │ │  POSTER  │        │
│  │  Título  │ │  Título  │ │  Título  │        │
│  │  4K HDR  │ │  1080p   │ │  REMUX   │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  POSTER  │ │  POSTER  │ │  POSTER  │        │
│  │  Título  │ │  Título  │ │  Título  │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                  │
│  ★ GLOW ORB (decorative, absolute)               │
└──────────────────────────────────────────────────┘
```

### Grid
- Max-width: `1200px`, centrado
- Grid de resultados: 3 columnas desktop, 2 tablet, 1 mobile
- Gap: 20-24px

### Breakpoints
| Breakpoint | Columnas | Gap |
|------------|----------|-----|
| < 640px | 1 | 16px |
| 640-1024px | 2 | 20px |
| > 1024px | 3 | 24px |

## Animations

### Transitions
```css
transition-glass: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
transition-fast: all 0.15s ease;
```

### Background Aurora
```css
@keyframes aurora-shift {
  0%, 100% { 
    background-position: 0% 50%;
    filter: hue-rotate(0deg);
  }
  33% { 
    background-position: 50% 0%;
    filter: hue-rotate(10deg);
  }
  66% { 
    background-position: 100% 50%;
    filter: hue-rotate(-10deg);
  }
}

.aurora-bg {
  background: linear-gradient(135deg, #0F0720, #1A0533, #071A2F, #0F2027, #0F0720);
  background-size: 300% 300%;
  animation: aurora-shift 20s ease infinite;
}
```

### Glow Orb Float
```css
@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

.glow-orb {
  animation: float 8s ease-in-out infinite;
}
```

### Card Hover
- Background brightens
- Border intensifica
- Glow aparece
- Scale 1.02

### Modal
- **Open**: Fade + scale(0.95 → 1) + blur in
- **Close**: Fade + scale(1 → 0.95) + blur out
- Duration: 300ms

### Stagger Results
```css
.result-card {
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.5s ease forwards;
  animation-delay: calc(var(--index) * 100ms);
}

@keyframes fadeInUp {
  to { opacity: 1; transform: translateY(0); }
}
```

### Loading
- Skeleton con shimmer glassmorphism
- Spinner con gradiente rotativo
- Pulse en stats

## Rules

1. **Glass en todo**: Cada superficie usa backdrop-blur
2. **Múltiples capas de blur**: Background blur + inner shadow + border
3. **Gradientes vibrantes**: Aurora background, gradient accents
4. **Glow moderation**: Solo en hover y elementos activos
5. **Bordes brillantes**: Inner glow con `inset 0 1px 0 rgba(255,255,255,0.1)`
6. **Tipografía display**: Plus Jakarta Sans para títulos, dar peso visual
7. **Espacio generoso**: 24-32px padding mínimo, whitespace abundante
8. **Dos colores de acento**: Violeta primario, teal secundario
9. **Decorative orbs**: Glow orbs flotantes para profundidad
10. **Transiciones suaves**: 300ms cubic-bezier, sin saltos
