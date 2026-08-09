# DESIGN.md - Streaming Platform Style

Inspiración: Netflix, HBO Max, Disney+

## Brand

- **Nombre**: Media Tracker
- **Tono**: Cinematográfico, premium, inmersivo
- **Sensación**: Como estar en una plataforma de streaming profesional

## Colors

### Background
| Token | Valor | Uso |
|-------|-------|-----|
| `bg-primary` | `#000000` | Fondo principal, pantalla completa |
| `bg-surface` | `#141414` | Cards, paneles, modales |
| `bg-elevated` | `#1A1A1A` | Elementos elevados, dropdowns |
| `bg-hover` | `#222222` | Estados hover |

### Accents
| Token | Valor | Uso |
|-------|-------|-----|
| `accent-primary` | `#E50914` | Botones principales, badges activos |
| `accent-secondary` | `#B81D24` | Hover de botones primarios |
| `accent-glow` | `rgba(229, 9, 20, 0.3)` | Sombras de elementos activos |

### Text
| Token | Valor | Uso |
|-------|-------|-----|
| `text-primary` | `#FFFFFF` | Títulos, texto principal |
| `text-secondary` | `#B3B3B3` | Descripciones, metadata |
| `text-muted` | `#808080` | Texto deshabilitado, labels |

### Quality Badges
| Token | Valor | Uso |
|-------|-------|-----|
| `badge-4k` | `#FFD700` | Badge 4K UHD |
| `badge-hdr` | `#00BFFF` | Badge HDR |
| `badge-remux` | `#FF6B6B` | Badge REMUX |
| `badge-web` | `#50FA7B` | Badge WEBRip |

## Typography

### Font Family
```css
--font-primary: 'Helvetica Neue', 'Arial', sans-serif;
```

> **Nota**: Netflix Sans no es pública. Usar Helvetica Neue como fallback cercano.

### Scale
| Elemento | Peso | Tamaño | Line-height |
|----------|------|--------|-------------|
| Hero Title | 800 (Black) | 48-64px | 1.1 |
| Section Title | 700 (Bold) | 24-32px | 1.2 |
| Card Title | 600 (SemiBold) | 16-20px | 1.3 |
| Body | 400 (Regular) | 14-16px | 1.5 |
| Caption | 400 (Regular) | 12-13px | 1.4 |
| Badge | 700 (Bold) | 11-12px | 1.0 |

### Letter Spacing
- Títulos: `-0.02em` (más compacto)
- Body: `0` (normal)
- Badges: `0.05em` (mayúsculas espaciadas)

## Spacing

### Grid Base: 4px
```
4px  → xs
8px  → sm
12px → md
16px → lg
24px → xl
32px → 2xl
48px → 3xl
64px → 4xl
```

### Component Spacing
| Componente | Padding | Gap |
|------------|---------|-----|
| Card | 0px (imagen llena) | - |
| Card overlay | 12-16px | 4-8px |
| Section | 24-32px vertical | - |
| Grid results | - | 8px |
| Modal | 24px | 16px |
| Search bar | 12px vertical, 16px horizontal | - |

## Borders

### Radius
| Elemento | Radio |
|----------|-------|
| Card | 4px |
| Badge | 2px |
| Button | 4px |
| Modal | 8px |
| Input | 4px |

### Borders
```css
border-subtle: 1px solid rgba(255, 255, 255, 0.08);
border-active: 1px solid rgba(255, 255, 255, 0.2);
```

## Shadows

```css
shadow-card: 0 2px 8px rgba(0, 0, 0, 0.6);
shadow-card-hover: 0 8px 24px rgba(0, 0, 0, 0.8);
shadow-modal: 0 16px 48px rgba(0, 0, 0, 0.9);
shadow-glow-red: 0 0 20px rgba(229, 9, 20, 0.4);
```

## Components

### Poster Card
- Ratio de imagen: **2:3** (portrait)
- Imagen cubre toda la card sin padding
- Overlay con gradiente de negro transparente a negro opaco en la parte inferior
- Título sobre el overlay
- Badge de calidad esquina superior derecha
- **Hover**: Scale 1.05, sombra intensificada, borde sutil blanco

```html
<div class="poster-card group relative overflow-hidden rounded bg-[#141414]">
  <img class="aspect-[2/3] w-full object-cover transition-transform duration-300 group-hover:scale-105" />
  <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
  <span class="absolute top-2 right-2 badge-4k">4K</span>
  <div class="absolute bottom-0 left-0 right-0 p-3">
    <h3 class="text-white font-semibold text-sm">Título</h3>
  </div>
</div>
```

### Quality Badge
- Fondo del color del badge
- Texto blanco bold 11px
- Padding: 2px 6px
- Radio: 2px
- Mayúsculas

### Search Bar
- Fondo: `#141414`
- Borde: 1px `rgba(255,255,255,0.08)`
- Input sin borde, texto blanco
- Botón buscar: fondo rojo `#E50914`, texto blanco
- Icono de búsqueda gris a la izquierda

### Filter Pills
- Fondo: `#1A1A1A`
- Borde: 1px `rgba(255,255,255,0.08)`
- Texto: `#B3B3B3`
- **Activo**: Fondo rojo, texto blanco, sin borde

### Horizontal Carousel
- Scroll horizontal con `overflow-x: auto`
- Snap points en cada card
- Flechas de navegación laterales (solo desktop)
- Sin scrollbar visible

### Detail Modal
- Fondo: `#141414`
- Overlay: rgba(0,0,0,0.85)
- Layout: imagen izquierda (40%) + info derecha (60%)
- Botón descargar: rojo, grande, centrado
- Lista de torrents como filas alternas

## Layout

### Structure
```
┌─────────────────────────────────────────┐
│  HEADER (logo + nav)                    │
├─────────────────────────────────────────┤
│  HERO (título grande + search)          │
├─────────────────────────────────────────┤
│  CAROUSEL: Películas Destacadas         │
│  [card][card][card][card][card] →       │
├─────────────────────────────────────────┤
│  CAROUSEL: Series Populares             │
│  [card][card][card][card][card] →       │
├─────────────────────────────────────────┤
│  GRID: Resultados de Búsqueda           │
│  [card][card][card][card][card][card]   │
│  [card][card][card][card][card][card]   │
├─────────────────────────────────────────┤
│  FOOTER                                 │
└─────────────────────────────────────────┘
```

### Grid Breakpoints
| Breakpoint | Columnas | Gap |
|------------|----------|-----|
| Mobile (< 640px) | 2 | 8px |
| Tablet (640-1024px) | 3-4 | 8px |
| Desktop (> 1024px) | 5-6 | 8px |

### Max Width
- Contenido: `100%` con padding lateral 4-5%
- No hay max-width fijo (estilo Netflix full-bleed)

## Animations

### Transitions
```css
transition-card: transform 300ms ease, box-shadow 300ms ease;
transition-button: background-color 150ms ease;
transition-modal: opacity 200ms ease, transform 200ms ease;
```

### Hover Effects
- **Cards**: `scale(1.05)` + sombra intensificada
- **Botones**: Oscurecer background 10%
- **Pills**: Cambio de color inmediato

### Modal Open/Close
- **Open**: `opacity 0 → 1`, `scale(0.95 → 1)` en 200ms
- **Close**: `opacity 1 → 0`, `scale(1 → 0.95)` en 150ms

### Loading States
- Skeleton screens con gradiente animado (shimmer effect)
- Spinner rojo en botones

## Rules

1. **Imagen siempre priority**: Las imágenes de poster son el elemento visual principal
2. **Texto mínimo en cards**: Solo título, nada de metadata visible hasta hover
3. **Hover revela info**: Al pasar el mouse se muestra año, rating, calidad
4. **Un solo color de acento**: Rojo para todo lo interactivo
5. **Fondo negro puro**: Nunca usar.grises claros como fondo
6. **Bordes sutiles**: Solo en hover o elementos activos
7. **Scroll horizontal para categorías**: Nunca grid vertical para secciones browse
8. **Badges pequeños y discretos**: No más de 2 badges por card
9. **Modal con info completa**: Al click en card, modal con sinopsis + todos los torrents
10. **Responsive first**: Mobile 2 columnas, desktop expande a 5-6
