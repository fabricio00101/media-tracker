# DESIGN.md - Minimal Dashboard Style

Inspiración: Notion, Linear, Raycast

## Brand

- **Nombre**: Media Tracker
- **Tono**: Limpio, funcional, profesional
- **Sensación**: Herramienta de productividad, no entretenimiento

## Colors

### Background
| Token | Valor | Uso |
|-------|-------|-----|
| `bg-primary` | `#1E1E2E` | Fondo principal |
| `bg-surface` | `#252536` | Cards, paneles |
| `bg-elevated` | `#2D2D40` | Dropdowns, tooltips |
| `bg-hover` | `#32324A` | Estados hover |
| `bg-active` | `#3A3A52` | Elemento seleccionado |

### Borders
| Token | Valor | Uso |
|-------|-------|-----|
| `border-default` | `#363649` | Borders generales |
| `border-subtle` | `rgba(255,255,255,0.04)` | Separadores internos |
| `border-focus` | `#8B5CF6` | Focus rings |

### Accents
| Token | Valor | Uso |
|-------|-------|-----|
| `accent-primary` | `#8B5CF6` | Acciones primarias, links |
| `accent-hover` | `#7C3AED` | Hover de acentos |
| `accent-muted` | `rgba(139,92,246,0.15)` | Fondos de tags activos |
| `accent-success` | `#10B981` | Estados exitosos |
| `accent-warning` | `#F59E0B` | Warnings |
| `accent-error` | `#EF4444` | Errores |

### Text
| Token | Valor | Uso |
|-------|-------|-----|
| `text-primary` | `#E0E0E0` | Títulos, texto principal |
| `text-secondary` | `#8888A0` | Descripciones, metadata |
| `text-muted` | `#5C5C72` | Labels, texto deshabilitado |
| `text-inverse` | `#1E1E2E` | Texto sobre fondos de acento |

## Typography

### Font Family
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
```

### Scale
| Elemento | Fuente | Peso | Tamaño | Line-height |
|----------|--------|------|--------|-------------|
| Page Title | Sans | 700 (Bold) | 24px | 1.2 |
| Section Title | Sans | 600 (SemiBold) | 18px | 1.3 |
| Card Title | Sans | 600 (SemiBold) | 14px | 1.4 |
| Body | Sans | 400 (Regular) | 14px | 1.5 |
| Caption | Sans | 400 (Regular) | 12px | 1.4 |
| Data (size, seeds) | Mono | 500 (Medium) | 13px | 1.3 |
| Code/Tags | Mono | 400 (Regular) | 12px | 1.3 |

### Letter Spacing
- Todo: `0` (normal, sin tracking especial)

## Spacing

### Grid Base: 8px
```
2px  → xxs (inline spacing)
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
| Sidebar | 16px | 4px entre items |
| List item | 12px vertical, 16px horizontal | 8px |
| Card | 16px | 8px |
| Section | 24px | 16px |
| Modal | 24px | 16px |
| Search bar | 10px vertical, 14px horizontal | - |

## Borders

### Radius
| Elemento | Radio |
|----------|-------|
| Card | 6px |
| Button | 6px |
| Badge | 4px |
| Input | 6px |
| Modal | 8px |
| Avatar | 50% (circle) |

### Borders
```css
border-default: 1px solid #363649;
border-subtle: 1px solid rgba(255, 255, 255, 0.04);
border-focus: 2px solid #8B5CF6;
```

### Dividers
```css
/* Separador horizontal */
border-top: 1px solid rgba(255, 255, 255, 0.06);
```

## Shadows

```css
shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.2);
shadow-md: 0 2px 8px rgba(0, 0, 0, 0.3);
shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.4);
shadow-focus: 0 0 0 3px rgba(139, 92, 246, 0.2);
```

> **Regla**: Sombras mínimas. La profundidad se comunica con backgroundColor más claro, no con sombras.

## Components

### Sidebar Filters
- Ancho fijo: `280px` en desktop, `0px` (drawer) en mobile
- Fondo: `#252536`
- Borde derecho: 1px `#363649`
- Secciones con título uppercase muted 11px
- Items con padding 8px 12px, radio 6px
- **Hover**: Fondo `#32324A`
- **Activo**: Fondo `rgba(139,92,246,0.15)`, texto `#8B5CF6`, borde izquierdo 2px sólido

### List Item (Resultado)
```
┌──────────────────────────────────────────────────────┐
│ [Poster 48x68]  Título (año)              4.2 GB     │
│                  1080p · x265 · HDR       [↓] [▶]    │
└──────────────────────────────────────────────────────┘
```
- Layout: flex horizontal, alineado centro
- Poster: 48x68px, radio 4px
- Título: bold 14px, color primario
- Año: regular 13px, color secundario
- Tamaño: mono 13px, color primario
- Tags: mono 12px, color muted, separados por `·`
- Botones: icono 32x32px, radio 6px, ghost style

### Data Table (Torrents dentro de resultado)
- Header: uppercase muted 11px, border-bottom
- Filas: border-bottom `rgba(255,255,255,0.04)`
- **Hover fila**: Background `#2D2D40`
- Celdas: padding 10px 12px
- Datos numéricos: mono font

### Search Bar
- Ancho: `100%`
- Fondo: `#1E1E2E`
- Borde: 1px `#363649`
- Radio: 6px
- Input: texto blanco 14px, sin borde interno
- Icono búsqueda: muted, 16px, izquierda
- **Focus**: Borde `#8B5CF6`, shadow-focus

### Toggle Chips (Filtros de calidad)
- Fondo inactive: `#252536`
- Borde inactive: 1px `#363649`
- Texto inactive: `#8888A0`
- **Active**: Fondo `rgba(139,92,246,0.15)`, borde `#8B5CF6`, texto `#8B5CF6`
- Padding: 6px 12px
- Radio: 6px
- Font: 13px, medium

### Button
- **Primary**: Fondo `#8B5CF6`, texto blanco, hover `#7C3AED`
- **Secondary**: Fondo transparente, borde `#363649`, texto `#E0E0E0`, hover bg `#2D2D40`
- **Ghost**: Sin fondo, sin borde, texto `#8888A0`, hover texto `#E0E0E0`
- Padding: 8px 16px
- Radio: 6px
- Font: 14px, medium

### Modal
- Overlay: `rgba(0,0,0,0.6)`
- Fondo modal: `#252536`
- Borde: 1px `#363649`
- Radio: 8px
- Max-width: `560px` (small), `800px` (large)
- Header: flex, space-between, título + close button

## Layout

### Structure
```
┌─────────┬───────────────────────────────────────────┐
│         │  HEADER (breadcrumb + search)             │
│ SIDEBAR ├───────────────────────────────────────────┤
│ Filtros │  TOOLBAR (vista + ordenar + count)        │
│         ├───────────────────────────────────────────┤
│         │  LIST                                     │
│ Categoría│  [item]  12 resultados                   │
│ Calidad │  [item]                                   │
│ Idioma  │  [item]                                   │
│ Tamaño  │  [item]                                   │
│         │  ...                                      │
│         ├───────────────────────────────────────────┤
│         │  PAGINATION                               │
└─────────┴───────────────────────────────────────────┘
```

### Grid
- **No grid de cards**. Layout de lista vertical.
- Sidebar fijo a la izquierda
- Contenido principal con `flex-1`
- Max-width del contenido: `none` (llena el espacio disponible)

### Breakpoints
| Breakpoint | Comportamiento |
|------------|----------------|
| < 768px | Sidebar como drawer overlay |
| 768-1024px | Sidebar colapsado (solo iconos) |
| > 1024px | Sidebar completo 280px |

## Animations

### Transitions
```css
transition-fast: 150ms ease;
transition-normal: 200ms ease;
```

### Hover Effects
- **List items**: Background change suave
- **Buttons**: Background change
- **Toggles**: Color change inmediato

### No animations llamativas
- Sin scale en hover
- Sin glow effects
- Sin transiciones mayores a 200ms
- **Excepción**: Modal open/close (fade)

### Loading
- Skeleton lines con shimmer
- Spinner pequeño 16px inline

## Rules

1. **Información > Decorative**: Cada pixel comunica datos
2. **Sin imágenes grandes**: Thumbnails pequeños (48x68), no posters grandes
3. **Datos monoespaciados**: Tamaños, seeds, ratios siempre en mono font
4. **Un solo color de acento**: Violeta para todo lo interactivo
5. **Bordes sutiles**: Solo para separar, no para decorar
6. **Sin gradientes**: Colores planos uniformes
7. **Sin glassmorphism**: Superficies opacas
8. **Sidebar siempre visible** en desktop: Filtros no se ocultan
9. **Lista sobre grid**: Resultados en lista, no en cards
10. **Máximo 2 levels de jerarquía**: Título → Subtítulo → Datos
