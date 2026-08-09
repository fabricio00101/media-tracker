# DESIGN.md - Magazine / Editorial Style

Inspiración: Vogue, The New York Times Magazine, Apple Editorial, Medium

## Brand

- **Nombre**: Media Tracker
- **Tono**: Elegante, cultural, curator
- **Sensación**: Revista de cine de alta calidad, no un utilitario

## Colors

### Background
| Token | Valor | Uso |
|-------|-------|-----|
| `bg-primary` | `#1A1A1A` | Fondo principal |
| `bg-surface` | `#242424` | Superficies, cards |
| `bg-elevated` | `#2E2E2E` | Elementos elevados |
| `bg-hover` | `#333333` | Estados hover |

### Accents
| Token | Valor | Uso |
|-------|-------|-----|
| `accent-primary` | `#8B5CF6` | Acento principal |
| `accent-secondary` | `#D4AF37` | Dorado (premium touch) |
| `accent-muted` | `rgba(139,92,246,0.12)` | Fondos sutiles |

### Text
| Token | Valor | Uso |
|-------|-------|-----|
| `text-primary` | `#F5F5F0` | Títulos (off-white cálido) |
| `text-secondary` | `#A0A0A0` | Descripciones |
| `text-muted` | `#666666` | Labels, metadata |
| `text-accent` | `#8B5CF6` | Links |

## Typography

### Font Family
```css
--font-serif: 'Playfair Display', 'Georgia', serif;
--font-sans: 'Inter', -apple-system, sans-serif;
--font-mono: 'JetBrains Mono', monospace;
```

### Scale
| Elemento | Fuente | Peso | Tamaño | Line-height |
|----------|--------|------|--------|-------------|
| Hero Title | Serif | 700 (Bold) | 48-72px | 1.05 |
| Section Title | Serif | 700 (Bold) | 32-40px | 1.15 |
| Subsection Title | Serif | 600 (SemiBold) | 24-28px | 1.2 |
| Card Title | Sans | 600 (SemiBold) | 16-18px | 1.3 |
| Body | Sans | 400 (Regular) | 15-16px | 1.7 |
| Caption | Sans | 400 (Regular) | 13px | 1.5 |
| Overline | Sans | 500 (Medium) | 11-12px | 1.3 |
| Stat | Serif | 700 (Bold) | 48-64px | 1.0 |

### Letter Spacing
- Serif titles: `-0.02em`
- Overline (uppercase labels): `0.15em` (bien espaciado)
- Body: `0.01em` (muy sutil)

### Font Pairing Rules
- **Títulos grandes (32px+)**: Siempre Playfair Display serif
- **Títulos medianos (18-28px)**: Inter semiBold
- **Body y captions**: Siempre Inter
- **Datos técnicos**: Solo cuando es necesario, JetBrains Mono

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
128px → 5xl
```

### Generous Whitespace
- Secciones: 96-128px vertical entre secciones
- Cards: 24-32px padding
- Headers: 48-64px padding vertical
- Entre elementos: 16-24px

### Component Spacing
| Componente | Padding | Gap |
|------------|---------|-----|
| Section | 64-96px vertical | 32px |
| Card | 24-32px | 16-20px |
| Hero | 96-128px vertical | 32-48px |
| Modal | 32-40px | 24px |
| Divider | 48px vertical | - |

## Borders

### Radius
| Elemento | Radio |
|----------|-------|
| Card | 2px (mínimo, casi recto) |
| Image | 2px |
| Button | 2px |
| Badge | 0px (recto) |
| Modal | 4px |

> **Estilo editorial**: Bordes casi rectos, elegancia en la simplicidad

### Borders
```css
border-subtle: 1px solid rgba(255, 255, 255, 0.06);
border-divider: 1px solid rgba(255, 255, 255, 0.1);
border-accent: 2px solid #8B5CF6;
```

### Dividers
```css
/* Separador horizontal elegante */
.editorial-divider {
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin: 48px 0;
}

/* Separador con ornamento */
.editorial-divider-ornament {
  text-align: center;
  margin: 64px 0;
}
.editorial-divider-ornament::before {
  content: '◆';
  color: #666;
  font-size: 10px;
}
```

## Shadows

```css
/* Minimalistas */
shadow-card: 0 1px 3px rgba(0, 0, 0, 0.2);
shadow-card-hover: 0 4px 12px rgba(0, 0, 0, 0.3);
shadow-modal: 0 16px 48px rgba(0, 0, 0, 0.5);

/* No glow effects, no color shadows */
```

## Components

### Masonry Gallery
- CSS columns o grid con masonry layout
- Items de diferentes alturas
- Gap: 16-20px
- Responsive: 3→2→1 columnas

```css
.masonry-grid {
  columns: 3;
  column-gap: 20px;
}

.masonry-item {
  break-inside: avoid;
  margin-bottom: 20px;
}
```

### Editorial Card
- Imagen grande arriba (ratio variable, no fijo)
- Overlay de gradiente suave en la parte inferior
- Título serif grande sobre el overlay
- Metadata debajo: año · categoría · tamaño
- Borde inferior sutil

```html
<article class="editorial-card">
  <div class="relative overflow-hidden">
    <img class="w-full aspect-[4/3] object-cover" />
    <div class="absolute bottom-0 left-0 right-0 p-6 
                bg-gradient-to-t from-black/80 to-transparent">
      <span class="overline text-[#8B5CF6]">PELÍCULA</span>
      <h2 class="font-serif text-3xl text-white mt-2">Título</h2>
    </div>
  </div>
  <div class="p-4">
    <p class="text-[#A0A0A0] text-sm">2024 · 4.2 GB · 1080p</p>
  </div>
</article>
```

### Section Header
- Overline uppercase pequeño (categoría)
- Título serif grande
- Línea divisoria debajo

```html
<div class="section-header mb-8">
  <span class="overline text-[#666] text-xs tracking-[0.15em] uppercase">
    Descubrir
  </span>
  <h2 class="font-serif text-4xl text-[#F5F5F0] mt-2">
    Películas Destacadas
  </h2>
  <div class="w-16 h-[2px] bg-[#8B5CF6] mt-4"></div>
</div>
```

### Search Bar
- Borde inferior solamente (estilo editorial)
- Sin background, transparente
- Input con tipografía serif para el placeholder
- Botón como texto link

```html
<div class="border-b border-white/10 pb-2">
  <input class="bg-transparent w-full text-lg font-serif 
                 text-white placeholder:text-[#666] outline-none" 
         placeholder="Buscar películas, series..." />
</div>
```

### Overline Labels
- Uppercase, letter-spacing 0.15em
- Font-size 11-12px
- Color muted o accent

```css
.overline {
  font-family: var(--font-sans);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: #666;
}
```

### Stat Display (Big Numbers)
- Serif bold 48-64px
- Label debajo sans regular 12px muted
- Centrado

```html
<div class="text-center">
  <div class="font-serif text-6xl font-bold text-[#F5F5F0]">2,847</div>
  <div class="text-[#666] text-xs mt-2 uppercase tracking-wider">
    Resultados Encontrados
  </div>
</div>
```

### Quote Block (para sinopsis)
- Border-left 3px accent
- Italic serif
- Padding left 24px

```html
<blockquote class="border-l-2 border-[#8B5CF6] pl-6 italic font-serif text-[#A0A0A0]">
  "Una sinopsis elegante que acompañe el resultado..."
</blockquote>
```

### Filter Chips (Minimalistas)
- Solo borde, sin fondo
- Texto uppercase overline style
- **Active**: Bordes accent, texto accent

```html
<button class="px-4 py-2 border border-white/10 text-xs 
               uppercase tracking-wider text-[#666]
               hover:border-white/20 hover:text-[#A0A0A0]
               active:border-[#8B5CF6] active:text-[#8B5CF6]
               transition-colors">
  4K
</button>
```

## Layout

### Structure (Editorial Flow)
```
┌──────────────────────────────────────────────────┐
│                                                  │
│                    MEDIA TRACKER                  │
│              Buscador de Alta Fidelidad           │
│                                                  │
│         ─────────── ◆ ───────────                │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  [Buscar película o serie...]              │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  DESCUBrir                                      │
│  Películas Destacadas                            │
│  ────────                                       │
│                                                  │
│  ┌─────────────┬─────────────┬─────────────┐    │
│  │   ┌─────┐   │   ┌─────┐   │             │    │
│  │   │     │   │   │     │   │   ┌─────┐   │    │
│  │   │ IMG │   │   │ IMG │   │   │     │   │    │
│  │   │     │   │   │     │   │   │ IMG │   │    │
│  │   └─────┘   │   └─────┘   │   │     │   │    │
│  │  Título     │  Título     │   └─────┘   │    │
│  │  2024·4GB   │  2023·8GB   │  Título     │    │
│  ├─────────────┼─────────────┤  2024·6GB   │    │
│  │   ┌─────┐   │             ├─────────────┤    │
│  │   │     │   │   ┌─────┐   │   ┌─────┐   │    │
│  │   │ IMG │   │   │     │   │   │     │   │    │
│  │   │     │   │   │ IMG │   │   │ IMG │   │    │
│  │   └─────┘   │   │     │   │   │     │   │    │
│  │  Título     │   └─────┘   │   └─────┘   │    │
│  │  2024·2GB   │  Título     │  Título     │    │
│  └─────────────┴─────────────┴─────────────┘    │
│                                                  │
│                    ◆                             │
│                                                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  SERIES POPULARES                                │
│  ────────                                       │
│                                                  │
│  [Grid de cards editorial]                       │
│                                                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  FOOTER                                          │
│  © 2026 Media Tracker                            │
│  ─────────────────                               │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Masonry Grid (para resultados)
```css
/* Desktop: 3 columnas con alturas variables */
.masonry { columns: 3; column-gap: 20px; }

/* Tablet: 2 columnas */
@media (max-width: 1024px) { .masonry { columns: 2; } }

/* Mobile: 1 columna */
@media (max-width: 640px) { .masonry { columns: 1; } }
```

### Breakpoints
| Breakpoint | Columnas masonry | Spacing |
|------------|------------------|---------|
| < 640px | 1 | 16px |
| 640-1024px | 2 | 20px |
| > 1024px | 3 | 24px |

### Max Width
- Contenido: `1400px`
- Lectura (body text): `680px` (ancho óptimo de lectura)

## Animations

### Transitions
```css
transition-editorial: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
transition-fast: all 0.15s ease;
```

### Hover Effects
- **Cards**: Opacidad 0.9 → 1, sombra sutil
- **Images**: Scale 1.02 (muy sutil)
- **Text links**: Underline aparece
- **No glow, no scale llamativo**

### Scroll Reveal
```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.reveal {
  opacity: 0;
  animation: fadeIn 0.6s ease forwards;
  animation-delay: calc(var(--index) * 100ms);
}
```

### Parallax (opcional)
```css
.parallax-hero {
  background-attachment: fixed;
  background-position: center;
  background-size: cover;
}
```

### Loading
- Skeleton con opacidad pulsante
- Sin shimmer llamativo
- Fade-in de resultados

## Rules

1. **Jerarquía tipográfica clara**: Serif = títulos grandes, Sans = body
2. **Imagen siempre priority**: Imágenes grandes, immersive
3. **Whitespace abundante**: No llenar cada pixel
4. **Bordes sutiles**: 1px, casi invisibles
5. **Sin glassmorphism**: Superficies opacas, sin blur
6. **Sin glow effects**: Sombras neutras solamente
7. **Dividers elegantes**: Líneas finas o ornamentos `◆`
8. **Overline labels**: Categorías en uppercase spaced
9. **Masonry sobre grid uniforme**: Alturas variables crean interés visual
10. **Color limitado**: Negro, blanco, gris, un acento (violeta)
11. **Citas serif**: Sinopsis en blockquote italic serif
12. **Footer editorial**: Línea + copyright centered
