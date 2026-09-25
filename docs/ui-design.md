# 🎨 GUÍA DE DISEÑO UI/UX — CommunityLab

> Para el diseñador UI/UX (@Marcelo Rolon).
> Describe colores, tipografía, componentes, layouts y estados.

---

## 🎯 DIRECCIÓN DE DISEÑO

**Estilo visual:** Professional pero cercano. Community-first. Debe sentirse como una herramienta de trabajo que los community managers quieran usar todos los días.

**Analogía:** Piensa en un CRM simple pero poderoso. Como Notion meets Mailchimp. Limpio, espacioso, con información clara.

**Referentes visuales:**
- Notion (clean, spacing, typography)
- Linear (dark mode opcional, profesional)
- Mailchimp (colores cálidos, cercanía)
- Dashlytics (dashboards claros)

---

## 🎨 PALETA DE COLORES

### Modo claro (principal)

| Elemento | Color | Hex | Uso |
|----------|-------|-----|-----|
| **Background** | Blanco cálido | `#FAFAF9` | Fondo general |
| **Surface** | Blanco puro | `#FFFFFF` | Tarjetas, paneles, modales |
| **Text primary** | Gris oscuro | `#1C1917` | Títulos, texto principal |
| **Text secondary** | Gris medio | `#78716C` | Descripciones, subtítulos |
| **Border** | Gris claro | `#E7E5E4` | Bordes de tarjetas, inputs |

### Brand colors (CommunityLab)

| Color | Hex | Significado | Uso |
|-------|-----|-------------|-----|
| **Primary** | Verde bosque `#166534` | Comunidad, crecimiento | Botones principales, links activos, sidebar |
| **Primary hover** | Verde oscuro `#14532D` | Hover states | Hover de botones |
| **Secondary** | Dorado `#B45309` | Éxito, testimonios | Badges, estadísticas positivas, highlights |
| **Accent** | Azul claro `#0369A1` | Información, datos | Links secundarios, info tooltips |
| **Danger** | Rojo `#DC2626` | Alertas, riesgo, error | Alertas de riesgo, errores, reject |
| **Warning** | Amarillo `#D97706` | Preocupación moderada | Advertencias, pendientes |
| **Success** | Verde `#16A34A` | Éxito, aprobado | Aprobación, aprobado, positivo |

### Sentimiento (para gráficos y badges)

| Sentimiento | Color | Hex |
|-------------|-------|-----|
| Positivo | Verde claro | `#22C55E` |
| Negativo | Rojo | `#EF4444` |
| Neutral | Gris | `#94A3B8` |

### Dark mode (opcional, Sprint 4+)

| Elemento | Color | Hex |
|----------|-------|-----|
| Background | Gris muy oscuro | `#0C0A09` |
| Surface | Gris oscuro | `#1C1917` |
| Text primary | Blanco cálido | `#FAFAF9` |
| Text secondary | Gris medio oscuro | `#A8A29E` |
| Border | Gris oscuro claro | `#292524` |

---

## 🔤 TIPOGRAFÍA

### Fuentes

| Uso | Fuente | Peso | Tamaño |
|-----|--------|------|--------|
| **Títulos H1** | Inter | Bold (700) | 28px |
| **Títulos H2** | Inter | SemiBold (600) | 22px |
| **Títulos H3** | Inter | SemiBold (600) | 18px |
| **Texto body** | Inter | Regular (400) | 15px |
| **Descripciones** | Inter | Regular (400) | 14px |
| **Labels/captions** | Inter | Medium (500) | 13px |
| **Datos numéricos** | JetBrains Mono | Regular (400) | 14px |
| **Botones** | Inter | Medium (500) | 14px |

### Jerarquía visual

```
[Sidebar Navigation]     [Main Content Area]
                          ┌──────────────────────────────┐
                          │  Page Title (H1, 28px Bold)  │
                          │  Description (15px Regular)  │
                          │                              │
                          │  ┌────────────────────────┐  │
                          │  │ Card Title (H3, 18px)  │  │
                          │  │ Body text (15px)        │  │
                          │  │                         │  │
                          │  │ [Metric 01]  [Metric 2] │  │
                          │  │  1,234       89%        │  │
                          │  └────────────────────────┘  │
                          │                              │
                          │  ┌────────────────────────┐  │
                          │  │ Section Title (H2)     │  │
                          │  │ Table / Chart          │  │
                          │  └────────────────────────┘  │
                          └──────────────────────────────┘
```

### Clases de espaciado

```
8px  — padding interno mínimo (compact)
16px — padding estándar
24px — espaciado entre tarjetas
32px — margen entre secciones
48px — margen entre bloques grandes
64px — margen superior de páginas
```

---

## 📐 LAYOUT Y ESTRUCTURA VISUAL

### Layout principal

```
┌────────────────────────────────────────────────────────────────┐
│  HEADER                                                        │
│  [Logo "CommunityLab"] [Search] [Notif] [Avatar]              │
├──────────┬─────────────────────────────────────────────────────┤
│          │                                                    │
│ SIDEBAR  │  MAIN CONTENT                                      │
│          │                                                    │
│ 🏠 Home  │  ┌──────────────────────────────────────────┐      │
│ 📊 Dash  │  │  Page Title + Description                │      │
│ ✍️ Curate│  └──────────────────────────────────────────┘      │
│ 🚨 Alert │                                                    │
│ 📁 Data  │  [Filtros: fecha ▼ | source ▼ | search ____]     │
│ ⚙️ Set  │                                                    │
│          │  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│          │  │ Metric1 │  │ Metric2 │  │ Metric3 │           │
│          │  │  Senti  │  │ Posts   │  │ Alerts  │           │
│          │  │  78%    │  │ 142     │  │ 3       │           │
│          │  └─────────┘  └─────────┘  └─────────┘           │
│          │                                                    │
│          │  ┌──────────────────────────────────────────┐      │
│          │  │  Chart: Sentimiento esta semana          │      │
│          │  │  [chart]                                 │      │
│          │  └──────────────────────────────────────────┘      │
│          │                                                    │
│          │  ┌──────────────────────────────────────────┐      │
│          │  │  Mensajes recientes                      │      │
│          │  │  [Lista con badges de sentimiento]         │      │
│          │  └──────────────────────────────────────────┘      │
└──────────┴─────────────────────────────────────────────────────┘
```

### Responsive (mobile/tablet)

```
┌────────────────────┐
│ [Menu ≡] [Logo]    │
│ ┌────────────────┐ │
│ │  Metric 1      │ │
│ │  78%           │ │
│ ├────────────────┤ │
│ │  Metric 2      │ │
│ │  142           │ │
│ ├────────────────┤ │
│ │  [Chart]       │ │
│ ├────────────────┤ │
│ │  [List]        │ │
│ └────────────────┘ │
│ [Tab: Dash|Curate│ │
│  |Alert|Data]     │ │
└────────────────────┘
```

---

## 🧩 COMPONENTES UI

### 1. Cards (Tarjetas)

```
┌─────────────────────────────┐
│  [Icon] Card Title          │
│  Descripción breve (14px)   │
│                             │
│  ┌──────────┐  ┌──────────┐ │
│  │  Metrica │  │  Metrica │ │
│  │  principal│  │  secund. │ │
│  │  1,234   │  │    89%   │ │
│  └──────────┘  └──────────┘ │
│                             │
│  [Action Button]            │
└─────────────────────────────┘
```

**Especs:**
- Background: `#FFFFFF`
- Border: `1px solid #E7E5E4`
- Border radius: `8px`
- Padding: `16px`
- Hover: borde cambia a Primary `#166534`

### 2. Buttons

| Tipo | Background | Color texto | Borde | Hover |
|------|------------|-------------|-------|-------|
| **Primary** | `#166534` | Blanco | Ninguno | `#14532D` |
| **Secondary** | Transparente | `#166534` | `1px solid #166534` | `#14532D` bg, bg `#F0FDF4` |
| **Danger** | `#DC2626` | Blanco | Ninguno | `#B91C1C` |
| **Ghost** | Transparente | `#78716C` | Ninguno | `#1C1917` texto |
| **Disabled** | `#E7E5E4` | `#A8A29E` | Ninguno | - |

**Especificaciones:**
- Height: `36px` (default), `32px` (small), `44px` (large)
- Padding: `8px 16px` (default)
- Border radius: `6px`
- Font: Inter Medium 14px
- Icon + text con gap de `8px`

### 3. Badges/Pills

| Tipo | Background | Texto | Borde |
|------|------------|-------|-------|
| **Positivo** | `#DCFCE7` | `#166534` | `#BBF7D0` |
| **Negativo** | `#FEE2E2` | `#DC2626` | `#FECACA` |
| **Neutral** | `#F1F5F9` | `#475569` | `#E2E8F0` |
| **Warning** | `#FEF3C7` | `#D97706` | `#FDE68A` |
| **Info** | `#E0F2FE` | `#0369A1` | `#BAE6FD` |

**Especificaciones:**
- Padding: `2px 8px`
- Border radius: `4px` (full rounded for pills: `12px`)
- Font: Inter Medium 12px

### 4. Tags (para sentimiento)

```
[🟢 Positivo]  [🔴 Negativo]  [⚪ Neutral]
```

### 5. Inputs y campos de texto

```
┌───────────────────────────────────┐
│  Label (13px Medium, gris oscuro) │
│  ┌─────────────────────────────┐  │
│  │  Placeholder (14px gris)    │  │
│  └─────────────────────────────┘  │
│  Helper text (12px, gris claro)   │
└───────────────────────────────────┘
```

**Especificaciones:**
- Border: `1px solid #E7E5E4`
- Border radius: `6px`
- Padding: `8px 12px`
- Height: `36px`
- Focus: borde `#166534`, box-shadow `0 0 0 3px rgba(22, 101, 52, 0.15)`
- Error: borde `#DC2626`

### 6. Tables

```
┌──────────────────────────────────────────────────┐
│  Título de tabla (H3, 18px)                      │
│  ┌──────────┬──────────┬──────────┬──────────┐  │
│  │ Header 1 │ Header 2 │ Header 3 │ Header 4 │  │
│  ├──────────┼──────────┼──────────┼──────────┤  │
│  │  Dato 1  │  Badge   │  1,234  │ [Acción] │  │
│  │  Dato 2  │  Badge   │  567    │ [Acción] │  │
│  │  Dato 3  │  Badge   │  890    │ [Acción] │  │
│  └──────────┴──────────┴──────────┴──────────┘  │
│  Fila seleccionada: bg #F5F5F4                  │
│  Hover: bg #F5F5F4                              │
└──────────────────────────────────────────────────┘
```

**Especificaciones:**
- Header: bg `#F5F5F4`, font Inter Medium 13px
- Cell: font Inter Regular 14px, padding `12px 16px`
- Borde filas: `1px solid #E7E5E4`
- Max height con scroll vertical si > 10 filas

### 7. Expanders/Accordions

```
┌────────────────────────────────────┐
│  ▼ Título expandible (H3, 16px)   │
├────────────────────────────────────┤
│  Contenido oculto...             │
│  Más contenido...                │
└────────────────────────────────────┘
```

### 8. Alerts/Notificaciones

#### Alerta de éxito:
```
┌────────────────────────────────────┐
│  ✅  Título del éxito             │
│  Descripción del éxito...         │
└────────────────────────────────────┘
```
- Background: `#F0FDF4`
- Border-left: `4px solid #16A34A`
- Padding: `12px 16px`

#### Alerta de riesgo:
```
┌────────────────────────────────────┐
│  🚨  Riesgo detectado: Juan       │
│  Nivel: ALTO | Motivo: 5 mensajes │
│  negativos recientes              │
│  [Ver detalle] [Marcar como atendido] │
└────────────────────────────────────┘
```
- Background: `#FEF2F2`
- Border-left: `4px solid #DC2626`
- Icono de alerta a la izquierda

#### Info:
```
┌────────────────────────────────────┐
│  ℹ️  Información                  │
│  Texto informativo...             │
└────────────────────────────────────┘
```
- Background: `#E0F2FE`
- Border-left: `4px solid #0369A1`

---

## 📊 COMPONENTES DE GRÁFICOS

### 1. Pie chart (Distribución de sentimiento)
```
         ╭──────╮
       ╭─┤ Posi │─╮
      ╭──┤ 78%  ├──╮
     ╭─┤    Neg  ├─╮ 22%
    ╭──┤  Neg   ├──╮
     ╰────────────╯
```
- Colores: Positivo `#22C55E`, Negativo `#EF4444`, Neutral `#94A3B8`
- Mostrar porcentajes
- Legend debajo o a la derecha

### 2. Bar chart (Top temas)
```
  50│      ████
 40│      ████  ████
 30│ ████  ████  ████  ████
 20│ ████  ████  ████  ████  ████
 10│ ████  ████  ████  ████  ████  ████
  0└─────────────────────────────────────
    Lang   Python AI    ML   Cloud  Data
```
- Horizontal bars
- Color: Primary `#166534`
- Labels a la izquierda, valores a la derecha

### 3. Line chart (Evolución temporal)
```
  100│                ╭─────
   80│            ╭───╯
   60│        ╭───╯
   40│    ╭───╯
   20│───╯
    0└──────────────────────────────
     Sem1  Sem2  Sem3  Sem4  Sem5
```
- Color: Primary `#166534`
- Grid lines: `#E7E5E4`
- Tooltip on hover

---

## 📱 ESTADOS DE LOS COMPONENTES

### 1. Loading (Cargando)
```
┌─────────────────────────────┐
│  [Spinner circular verde]   │
│  Procesando...              │
│  Análisis de sentimiento 67%│
└─────────────────────────────┘
```
- Spinner: circular, Primary color, 24px
- Texto: "Procesando..." + porcentaje si aplica
- Background: blanco con opacity 50% sobre el contenido

### 2. Empty state (Sin datos)
```
┌─────────────────────────────┐
│                             │
│     📭 (Icono grande)       │
│                             │
│    No hay datos aún         │
│    Comienza subiendo un     │
│    archivo JSON             │
│                             │
│    [Subir archivo]          │
│                             │
└─────────────────────────────┘
```
- Icono ilustrativo grande (48-64px)
- Título: H3, griso oscuro
- Descripción: 14px, gris medio
- CTA: botón Primary

### 3. Error state (Error)
```
┌─────────────────────────────┐
│     ❌ (Icono 48px)         │
│                             │
│  Error al cargar datos      │
│  No se pudo conectar con    │
│  el servidor. Inténtalo     │
│  de nuevo.                  │
│                             │
│  [Reintentar] [Contactar]  │
│                             │
└─────────────────────────────┘
```
- Icono error (48px)
- Título: H3, Rojo `#DC2626`
- Descripción: 14px, gris medio
- CTAs: botón Secondary "Reintentar", link "Contactar"

### 4. Success state (Éxito)
```
┌─────────────────────────────┐
│     ✅ (Icono 48px)         │
│                             │
│  ¡Procesamiento completo!   │
│  Se analizaron 142 mensajes │
│  y se generaron 12 activos. │
│                             │
│  [Ver resultados]           │
│                             │
└─────────────────────────────┘
```

### 5. Hover/Focus/Active/Disabled

| Estado | Botón Primary | Input | Card |
|--------|---------------|-------|------|
| **Default** | `#166534` bg | borde `#E7E5E4` | borde `#E7E5E4` |
| **Hover** | `#14532D` bg | borde `#166534` | borde `#166534` |
| **Focus** | `#14532D` bg | borde `#166534` + shadow | borde `#166534` |
| **Active** | `#166534` bg oscuro | - | bg `#F5F5F4` |
| **Disabled** | `#E7E5E4` bg | `#E7E5E4` borde | opacity 0.5 |

---

## 🧭 NAVEGACIÓN Y SIDEBAR

### Sidebar

```
┌──────────────────┐
│  🟢 CommunityLab │  (Logo, 20px Bold)
│                  │
│  ─── Workspace ──│
│  🏠 Home         │  (16px Medium, icon 20px)
│  📊 Dashboard    │
│  ✍️ Curaduría    │
│  🚨 Alertas      │
│  📁 Datasets     │
│                  │
│  ─── Tools ──────│
│  ⚙️ Configuración│
│  📊 Analytics    │
│                  │
│  ─── Help ──────│
│  ❓ Documentación│
│  👤 Perfil       │
│                  │
│  ┌──────────────┐│
│ │ [Admin User] ││  (Avatar circle 32px)
│ │  @emanuel    ││  (13px)
│ │   ↓          ││
│ └──────────────┘│
└──────────────────┘
```

**Especificaciones:**
- Width: `240px` (desktop), `64px` (collapsed), `100%` (mobile)
- Background: `#FFFFFF`
- Border-right: `1px solid #E7E5E4`
- Nav items padding: `8px 12px`
- Nav items hover: bg `#F5F5F4`, border-radius `6px`
- Nav items active: bg `#F0FDF4`, text Primary `#166534`, border-left `3px solid #166534`
- Height: `calc(100vh - 56px)` (header 56px)
- Sticky/fixed position

---

## 📐 RESPONSIVE BREAKPOINTS

| Breakpoint | Width | Cambios |
|------------|-------|---------|
| **Desktop** | ≥1200px | Sidebar visible, multi-column |
| **Tablet** | 768-1199px | Sidebar colapsado (iconos), 2 columns |
| **Mobile** | <768px | Sidebar como bottom tab, 1 column |

---

## 🎬 MICROINTERACCIONES

| Interacción | Animación | Duración |
|-------------|-----------|----------|
| **Hover botones** | bg color smooth | 150ms |
| **Hover tarjetas** | border color + subtle shadow | 200ms |
| **Clic botón** | scale 0.98 | 100ms |
| **Loading spinner** | rotate 360° infinite | 1s linear |
| **Page transition** | fade + slide | 250ms ease-out |
| **Toast notification** | slide in right | 300ms ease-out |
| **Modal open** | fade + scale | 200ms ease-out |
| **Sidebar collapse** | width smooth | 250ms ease |

---

## 📋 PANTALLAS PRINCIPALES (Wireframes en texto)

### Pantalla 1: Dashboard

```
┌────────────────────────────────────────────────────────┐
│ 🟢 CommunityLab  [🔍 Buscar] [🔔 3] [👤 Admin ↓]      │
├──────────┬─────────────────────────────────────────────┤
│ 🏠 Home  │  Welcome back, @emanuel                    │
│ 📊 Dash  │  Última semana procesada: 142 mensajes     │
│ ✍️ Curate│                                       │
│ 🚨 Alert │  ┌────────┐ ┌────────┐ ┌────────┐        │
│ ⚙️ Config│  │Sentim. │ │ Posts  │ │Alertas │        │
│ 📊 Anális│  │  78%   │ │  142   │ │   3    │        │
│          │  │Positivo│ │Publicados│ │Riesgo │        │
│          │  └────────┘ └────────┘ └────────┘        │
│          │                                         │
│          │  ┌─────────────────────────────────┐     │
│          │  │ Sentimiento esta semana         │     │
│          │  │ [Chart]                         │     │
│          │  └─────────────────────────────────┘     │
│          │                                         │
│          │  ┌─────────────────────────────────┐     │
│          │  │ Últimos mensajes                │     │
│          │  │ [Lista con badges]              │     │
│          │  │ [Ver más]                       │     │
│          │  └─────────────────────────────────┘     │
└──────────┴─────────────────────────────────────────────┘
```

### Pantalla 2: Curaduría

```
┌────────────────────────────────────────────────────────┐
│ 🟢 CommunityLab  [🔍 Buscar] [🔔 3] [👤 Admin ↓]      │
├──────────┬─────────────────────────────────────────────┤
│          │  Curaduría de Activos                      │
│          │  Filtro: [Pendiente ▼] [LinkedIn ▼] [🔍]  │
│          │                                           │
│          │  ┌──────────────────────────────────┐     │
│          │  │ [Preview del post LinkedIn]      │     │
│          │  │                                  │     │
│          │  │ "Texto del post generado..."     │     │
│          │  │                                  │     │
│          │  │ Mensaje original: [Expandir]     │     │
│          │  │                                  │     │
│          │  │ [✏️ Editar] [✅ Aprobar] [❌ Rechazar]│  │
│          │  └──────────────────────────────────┘     │
│          │                                           │
│          │  ┌──────────────────────────────────┐     │
│          │  │ [Otro activo...]                 │     │
│          │  └──────────────────────────────────┘     │
│          │                                           │
│          │  Pagination: ← 1 2 3 4 5 →              │
└──────────┴─────────────────────────────────────────────┘
```

### Pantalla 3: Alertas

```
┌────────────────────────────────────────────────────────┐
│ 🟢 CommunityLab  [🔍 Buscar] [🔔 3] [👤 Admin ↓]      │
├──────────┬─────────────────────────────────────────────┤
│          │  🚨 Alertas                                │
│          │                                           │
│          │  ┌──────────────────────────────────┐     │
│          │  │ 🔴 RIESGO ALTO                   │     │
│          │  │                                  │     │
│          │  │ Juan Pérez                       │     │
│          │  │ Sentimiento promedio: 0.15       │     │
│          │  │ 5 mensajes negativos recientes    │     │
│          │  │ Última actividad: 2h ago          │     │
│          │  │                                  │     │
│          │  │ Motivos:                         │     │
│          │  │ • Reenvío de "estoy cansado..."   │     │
│          │  │ • Frustración con el curso        │     │
│          │  │                                  │     │
│          │  │ [📞 Contactar] [✅ Atendido]     │     │
│          │  └──────────────────────────────────┘     │
│          │                                           │
│          │  ┌──────────────────────────────────┐     │
│          │  │ 🟡 RIESGO MEDIO                  │     │
│          │  │ María López - dudas recurrentes   │     │
│          │  └──────────────────────────────────┘     │
│          │                                           │
│          │  ─── Dudas recurrentes ──────────────    │
│          │  ┌──────────────────────────────────┐     │
│          │  │ 📌 LangGraph: 12 preguntas       │     │
│          │  │ 📌 API keys: 8 preguntas          │     │
│          │  └──────────────────────────────────┘     │
└──────────┴─────────────────────────────────────────────┘
```

---

## 🖼️ ICONOGRAFÍA

Recomendación: **Lucide Icons** (lucide.dev) o **Phosphor Icons** (phosphoricons.com)
- Stroke style (consistente)
- 24px por defecto
- 20px para sidebar icons
- 16px para inline icons
- Stroke width: 2px

---

## 🔗 RECURSOS

| Recurso | Link |
|---------|------|
| Lucide Icons | lucide.dev |
| Phosphor Icons | phosphoricons.com |
| Inter Font | fonts.google.com/inter |
| JetBrains Mono | fonts.google.com/jetbrains-mono |
| Figma UI Kit | (para crear) |
| Color contrast checker | webaim.org/resources/contrastchecker/ |

---

*Guía de diseño UI/UX para CommunityLab*
*Para @Marcelo Rolon — Sprint 4*
*Basado en: Fichas HU-S4-003, HU-S4-004, HU-S4-005*
