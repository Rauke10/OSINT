# GLOBEYE — Revisión UX Fase 1

> **Tipo:** auditoría funcional y visual (sin cambios de código).
> **Alcance:** UI implementada en Fase 1 (React Router, casos, entidades, grafo, `/scan` legacy).
> **Objetivo:** comprobar si un analista entiende el flujo y proponer mejoras de experiencia sin alterar la arquitectura backend.

---

## 1. Resumen ejecutivo

La Fase 1 **funciona técnicamente** y reutiliza bien componentes del scan original (formulario, tabla de hallazgos, grafo Cytoscape, panel de fuentes). A nivel de producto, la aplicación aún se percibe como **“el escáner antiguo con un menú lateral”** más que como **“workspace de investigación por casos”**.

| Dimensión | Valoración (1–5) | Comentario breve |
|-----------|------------------|------------------|
| Claridad del concepto “caso” | 2 | Falta definición y onboarding |
| Flujo crear → buscar → ver resultados | 3 | Existe, pero fragmentado entre pestañas |
| Diferencia legacy vs caso | 2 | Texto pequeño; fácil confundir |
| Navegación / orientación | 2 | Sin breadcrumbs; pestaña “Resumen” poco útil |
| Estados vacíos y errores | 2 | Muchos fallos silenciosos |
| Consistencia visual | 4 | Tailwind coherente con v0.1 |
| API key / configuración | 2 | Repetida en cada formulario de scan |

**Conclusión:** conviene un **paquete UX acotado** (copy, layout, componentes compartidos, estados) antes de abrir Fase 2 (dashboard rico, evidencias, informes).

---

## 2. Recorrido por pantalla (estado actual)

### 2.1 Mapa de rutas y flujo ideal

```text
                    ┌─────────────┐
                    │  /dashboard │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌──────────┐     ┌────────────┐    ┌──────────┐
   │  /cases  │     │ /cases/new │    │  /scan   │  ← legacy
   └────┬─────┘     └─────┬──────┘    └──────────┘
        │                 │
        │                 └──► /cases/:id
        │                           │
        │              ┌────────────┼────────────┐
        │              ▼            ▼            ▼
        │         (overview)    /search      /entities
        │                            │            │
        │                            └────► /graph
        └──────────────────────────────► /cases/:id
```

**Flujo recomendado para el usuario:** Dashboard → Nuevo caso → **Buscar** (no Resumen) → ver hallazgos → **Entidades** / **Grafo**.

**Flujo real por defecto:** tras crear caso → landing en **Resumen** (poco acción) → el usuario debe descubrir la pestaña Buscar.

---

### 2.2 `/dashboard` — Panel

**Qué muestra hoy**
- Título “Panel” / “Dashboard”.
- 3 cards: casos abiertos, scan jobs, entidades (agregados).
- Lista de hasta 8 casos con enlace y contador de entidades.
- Botón “Nuevo caso”.
- Sin aviso legal; sin bloque de API key.

**Descripción visual (wireframe ASCII)**

```text
┌──────────────────────────────────────────────────────────────┐
│ GLOBEYE header                                    [docs][ES] │
├──────────┬───────────────────────────────────────────────────┤
│ Panel    │  Panel                                            │
│ Casos    │  ┌────┐ ┌────┐ ┌────┐                             │
│ Escaneo  │  │ 2  │ │ 5  │ │ 12 │  ← métricas sin contexto   │
│ rápido   │  └────┘ └────┘ └────┘                             │
│          │  Casos                        [Nuevo caso]          │
│          │  · ACME (3 entidades)                               │
│          │  Aún no hay casos.  ← si sin API key: igual texto   │
└──────────┴───────────────────────────────────────────────────┘
```

**Problemas**
- P1: Sin API key, `listCases` falla → lista vacía → **mismo mensaje que “no hay casos”** (engañoso).
- P2: “scan jobs” es jerga técnica; el usuario piensa en “escaneos” o “consultas”.
- P3: No explica qué es un **caso** ni el primer paso (“crear investigación”).
- P4: No hay CTA principal visible (“Empezar investigación”).
- P5: Cards no son clicables (no llevan a casos filtrados).

**Mejora visual propuesta**

```text
┌──────────────────────────────────────────────────────────────┐
│ Panel de investigaciones                                      │
│ Organiza objetivos, escaneos y entidades por caso.            │
│                                                               │
│ [ + Nueva investigación ]          [ Escaneo rápido (sin caso) ]│
│                                                               │
│ ┌─ Configuración ─────────────────────────────────────────┐  │
│ │ API key: ••••••••  [Guardar]  ℹ Solo acceso al servidor │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌ Casos abiertos: 2 ┐ ┌ Escaneos: 5 ┐ ┌ Entidades: 12 ┐      │
│                                                               │
│ Investigaciones recientes                                       │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ ACME · abierto · 3 entidades · hace 2h        [Abrir →] │  │
│ └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

### 2.3 `/cases` — Listado

**Qué muestra hoy**
- Lista con título, `status · N jobs · N entidades`.
- Estado vacío: “Aún no hay casos.”
- Botón “Nuevo caso”.

**Problemas**
- P6: Duplica contenido del dashboard (lista + botón nuevo).
- P7: `status` en inglés crudo (`open`); `jobs` sin traducir.
- P8: Sin filtros (abiertos/archivados), sin búsqueda por título.
- P9: Sin fecha de última actividad (solo contadores).

**Mejora propuesta:** tabla o cards con badge de estado, última actividad, acciones “Abrir” / “Archivar”.

---

### 2.4 `/cases/new` — Crear caso

**Qué muestra hoy**
- Formulario: título, descripción, botón “Crear caso”.
- Sin enlace “← Casos”; sin texto explicativo; sin banner legal.

**Problemas**
- P10: No define **caso = contenedor de investigación** (objetivos, escaneos, entidades, grafo).
- P11: Si falta API key, error genérico tras enviar (401).
- P12: Tras crear, redirige a **Resumen**, no a **Buscar** (fricción extra).

**Mejora propuesta**

```text
Nueva investigación
Un caso agrupa todos los objetivos y resultados de una misma investigación.

Título *     [________________________]
Descripción  [________________________]
             (opcional: contexto interno, referencia del mandato)

⚠ Uso autorizado — solo activos propios o con permiso escrito.

[Cancelar]  [Crear e ir a búsqueda →]
```

---

### 2.5 `/cases/:caseId` — Detalle (layout + pestañas)

**Qué muestra hoy**
- Enlace `← Casos`.
- Título, descripción, línea `open · N entidades · N jobs`.
- Pestañas: **Resumen | Buscar | Entidades | Grafo de relaciones**.
- `<Outlet />` para subruta.

**Problemas**
- P13: **Sin breadcrumbs** completos (`Panel > Casos > ACME > Buscar`).
- P14: Pestaña **Resumen** por defecto con solo un párrafo y un enlace — ocupa slot principal sin valor.
- P15: Orden de pestañas: lo lógico para OSINT es **Buscar → Entidades → Grafo → Resumen** (o eliminar Resumen en Fase 1.5).
- P16: “Grafo de relaciones” como nombre de pestaña es largo; en header del caso ya hay mucho texto.
- P17: No hay **resumen del caso** persistente (último scan, targets semilla, acciones).
- P18: `CaseDetail` y `CaseOverviewTab` **duplican** la petición `getCase`.

**Mejora propuesta (cabecera de caso)**

```text
Panel › Casos › Investigación ACME

Investigación ACME                    [Abierto ▼]  [Archivar]
Referencia interna · Creado 21/05/2026

┌──────────┬──────────┬──────────┬──────────┐
│ 3        │ 5        │ 12       │ api.ex…  │
│ escaneos │ entidades│ relaciones│ último   │
└──────────┴──────────┴──────────┴──────────┘

[ Buscar ] [ Entidades ] [ Grafo ] [ Resumen ]
─────────────────────────────────────────────
  (contenido pestaña)
```

---

### 2.6 `/cases/:caseId/search` — Búsqueda en caso

**Qué muestra hoy**
- `ScanForm` (objetivo, API key, pivot, Escanear).
- Tras scan: botón informe HTML, SourcesPanel, **grafo del scan actual** (`result`), FindingsTable.
- Sin banner legal (sí en `/scan`).
- Sin cards de resumen (sí en legacy).
- Sin mensaje “entidades actualizadas” ni enlaces a Entidades/Grafo del caso.

**Problemas**
- P19: Usuario no sabe que el scan **alimenta** Entidades y Grafo del caso (solo si lee Resumen).
- P20: **Dos grafos distintos:** en Buscar = grafo del último scan; en pestaña Grafo = grafo acumulado del caso → **muy confuso**.
- P21: API key otra vez dentro del formulario (ruido).
- P22: Scan largo: solo `Escaneando…` en botón; sin indicador global ni tiempo estimado.
- P23: Tras scan exitoso, no hay CTA “Ver 12 entidades” / “Ver grafo del caso”.
- P24: Sin export JSON en caso (sí en legacy).
- P25: `pivot` sin ayuda contextual (checkbox críptico).

**Mejora propuesta**

```text
Buscar en esta investigación
Los resultados se guardan en el caso y actualizan entidades y grafo.

⚠ Banner legal (igual que legacy)

Objetivo  [ example.com                    ]
          Detectado: dominio · confianza alta   ← futuro: detección UI

☐ Pivotar (seguir emails/usernames descubiertos)  [?]

[ Escanear pasivo ]

── Tras completar ──
┌ hallazgos: 42 │ alta: 7 │ … ┐  [JSON] [Informe HTML]

✓ Caso actualizado: +3 entidades · +5 relaciones
   [Ver entidades] [Ver grafo del caso]

Fuentes consultadas | Grafo (este escaneo) | Tabla hallazgos
```

---

### 2.7 `/cases/:caseId/entities` — Entidades

**Qué muestra hoy**
- Tabla: tipo (`entity_type`), valor, última vez.
- Vacío: mensaje bajo la tabla.

**Problemas**
- P26: **“Entidades” sin glosario** — el usuario no sabe que son dominios, IPs, emails normalizados, etc.
- P27: `entity_type` en crudo (`subdomain`, `domain`) — sin badges ni colores.
- P28: Filas no clicables (API tiene relaciones por entidad, UI no las usa).
- P29: Sin filtro por tipo, sin búsqueda de texto.
- P30: Estado vacío compite con cabeceras de tabla vacías (layout raro).
- P31: No se refresca automáticamente tras scan en otra pestaña (hay que cambiar de pestaña manualmente; no hay botón Actualizar).

**Mejora propuesta**

```text
Entidades descubiertas
Nodos normalizados a partir de todos los escaneos de este caso.

[Filtrar tipo ▼] [Buscar valor…]  [Actualizar]

┌──────────┬─────────────────────┬──────────────┐
│ DOMAIN   │ example.com         │ hace 1 min   │
│ SUBDOMAIN│ api.example.com     │ hace 1 min   │
└──────────┴─────────────────────┴──────────────┘

Clic en fila → panel lateral con relaciones entrantes/salientes (fase UX+)
```

---

### 2.8 `/cases/:caseId/graph` — Grafo del caso

**Qué muestra hoy**
- `GET /api/cases/{id}/graph` → Cytoscape con nodos por `entity.id` (IDs numéricos internos en aristas).
- Vacío: “Sin datos de grafo — ejecuta un scan primero.”
- Carga: mismo texto que vacío (**no hay loading**).

**Problemas**
- P32: No explica que es el **grafo acumulado de toda la investigación**, no el último scan.
- P33: Etiquetas de nodos pueden ser truncadas; IDs numéricos en edges poco legibles para humanos.
- P34: Sin leyenda de tipos (dominio, email, etc.).
- P35: Sin controles (reset zoom, filtrar por tipo).
- P36: Confusión con grafo en pestaña Buscar (P20).

**Mejora propuesta**

```text
Grafo de la investigación
Relaciones entre entidades de todos los escaneos de este caso.
(El grafo en «Buscar» muestra solo el último escaneo.)

[Leyenda: ● dominio ● email ─ descubierto vía fuente]

        [ área Cytoscape 420px ]

12 entidades · 8 relaciones
```

---

### 2.9 `/scan` — Escaneo rápido (legacy)

**Qué muestra hoy**
- Hint: “Escaneo legacy sin caso…”.
- Banner legal rojo.
- ScanForm completo + resultados + historial global (`HistoryPanel`).
- Cards de resumen, export JSON/HTML, grafo, tabla, fuentes.

**Problemas**
- P37: **Mejor experiencia que búsqueda en caso** (más completa) → incentiva **no usar casos**.
- P38: “Escaneo rápido” en sidebar no comunica “sin investigación / historial global”.
- P39: Historial global solo aquí; usuario en caso no ve escaneos previos del mismo caso en UI (solo vía API jobs).

**Mejora propuesta:** renombrar a **“Escaneo sin caso”**, icono distinto, aviso más visible; enlazar desde dashboard como acción secundaria.

---

## 3. Evaluación de comprensión (preguntas del usuario)

| Pregunta | ¿Se entiende hoy? | Evidencia / causa |
|----------|-------------------|-----------------|
| ¿Qué es un caso? | **Parcial** | Solo hint en Resumen; título “Casos” genérico |
| ¿Cómo crear una investigación? | **Sí**, con fricción | Botones “Nuevo caso” existen; falta guía |
| ¿Cómo lanzar una búsqueda? | **Sí**, si encuentra pestaña Buscar | No obvia desde Resumen |
| ¿Dónde ver resultados? | **Parcial** | En Buscar (tabla); entidades/grafo separados |
| ¿Qué son las entidades? | **No** | Sin copy ni badges |
| ¿Qué representa el grafo? | **No** | Dos grafos; sin leyenda ni subtítulo |
| ¿Cómo volver al caso? | **Sí** | `← Casos` y sidebar |
| ¿Legacy vs búsqueda en caso? | **No** | Hint pequeño en legacy; nada en caso |

---

## 4. Problemas detectados (consolidado)

### 4.1 Críticos (bloquean comprensión)

| ID | Problema |
|----|----------|
| C1 | Dos grafos con el mismo nombre conceptual (“Relationship graph”) y distinto alcance de datos |
| C2 | API key dentro de ScanForm: parece campo del scan, no configuración global; errores confundidos con “sin casos” |
| C3 | Sin explicación de “caso” y “entidad” en lenguaje de investigador |
| C4 | Pestaña Resumen por defecto sin valor; oculta el flujo principal |

### 4.2 Importantes (fricción alta)

| ID | Problema |
|----|----------|
| I1 | Fallos de API → listas vacías sin mensaje de error |
| I2 | Sin breadcrumbs; solo un back link |
| I3 | Legacy más completo que búsqueda en caso |
| I4 | Sin loading skeleton en caso/entidades/grafo |
| I5 | Entidades: tabla sin badges, filtros ni enlace a relaciones |
| I6 | Jerga: jobs, status, pivot, legacy |
| I7 | Sin lista de escaneos del caso en UI (jobs API existe) |

### 4.3 Menores (pulido)

| ID | Problema |
|----|----------|
| M1 | Header no enlaza a dashboard |
| M2 | Duplicación fetch `getCase` |
| M3 | CaseNew sin cancelar / volver |
| M4 | Botón loading solo muestra "…" |
| M5 | Pestaña grafo con nombre largo |
| M6 | Sin aviso legal en búsqueda de caso |

---

## 5. Mejoras recomendadas (sin cambiar arquitectura)

### 5.1 Copy y terminología (i18n)

| Clave / uso | Actual | Propuesto (ES) |
|-------------|--------|----------------|
| `nav_cases` | Casos | **Investigaciones** (o “Casos de investigación”) |
| `case_new` | Nuevo caso | **Nueva investigación** |
| `dash_total_jobs` | trabajos de scan | **Escaneos realizados** |
| `nav_quick_scan` | Escaneo rápido | **Escaneo sin investigación** |
| `case_search` | Buscar | **Escanear objetivo** |
| `case_entities` | Entidades | **Entidades descubiertas** |
| Nuevo | — | Subtítulo bajo header caso: qué agrupa la investigación |
| Nuevo | — | Tooltip `pivot` en 1 línea |
| Nuevo | — | `graph_scan_title` vs `graph_case_title` para diferenciar grafos |

**Archivos:** `frontend/src/i18n/index.tsx` (+ consumo en páginas).

### 5.2 Componentes nuevos (solo frontend)

| Componente | Función |
|------------|---------|
| `Breadcrumbs.tsx` | `Panel › Investigaciones › {title} › {tab}` |
| `ApiKeyBanner.tsx` | Configuración global sticky o en dashboard |
| `CaseHeader.tsx` | Título, badges, mini-stats, acciones |
| `EmptyState.tsx` | Icono + título + descripción + CTA |
| `LoadingBlock.tsx` | Skeleton o spinner consistente |
| `EntityTypeBadge.tsx` | Color por `domain`, `email`, `subdomain`, … |
| `LegalBanner.tsx` | Reutilizar en Search y CaseNew |
| `PostScanBanner.tsx` | “Caso actualizado” + links entidades/grafo |

**Archivos:** `frontend/src/components/*` (nuevos).

### 5.3 Cambios por pantalla (comportamiento UI)

| Pantalla | Cambio |
|----------|--------|
| Dashboard | ApiKeyBanner; CTA primario; mensaje distinto sin key vs sin casos |
| CaseList | Badges estado; fechas; opcional filtro |
| CaseNew | Texto intro; legal; redirect a `/search`; breadcrumb |
| CaseDetail | CaseHeader; breadcrumbs; reordenar tabs; redirect index → search |
| CaseSearch | Legal; summary cards; renombrar grafo local; PostScanBanner; quitar API key del form si hay banner global |
| CaseEntities | Badges; EmptyState; botón refresh; texto intro |
| CaseGraph | Título distinto; leyenda; loading; EmptyState con CTA a Buscar |
| LegacyScan | Renombrar nav; card comparativa “¿Primera vez? Crear investigación” |
| ScanForm | Props opcionales: `showApiKey`, `scanLabel`, `contextHint` |
| AppShell | Enlace logo → dashboard; opcional iconos en nav |

### 5.4 Orden de pestañas recomendado

```text
[ Escanear ] [ Entidades ] [ Grafo ] [ Resumen ]
     ↑ default route (/cases/:id → redirect to /search)
```

---

## 6. Prioridades

### P0 — Hacer antes de demo interna (esfuerzo bajo, impacto alto)

1. **Diferenciar los dos grafos** (títulos + una línea de ayuda cada uno).
2. **Redirect** `/cases/:id` → `/cases/:id/search` (eliminar o reducir Resumen).
3. **ApiKeyBanner** en dashboard + mensajes de error cuando falta key.
4. **PostScanBanner** con enlaces a entidades y grafo del caso.
5. **LegalBanner** en búsqueda de caso.
6. **Copy** investigación / escaneo sin investigación (i18n).
7. **EmptyState** diferenciado: sin key / sin casos / sin entidades / cargando.

### P1 — Siguiente iteración UX Fase 1 (1–2 días)

1. Breadcrumbs + `CaseHeader` con mini-stats.
2. Badges tipo entidad + filtro simple en tabla.
3. Summary cards en CaseSearch (reutilizar legacy).
4. Lista “Escaneos de este caso” (consumir `GET .../jobs` ya existente).
5. Renombrar y estilar `/scan` como acción secundaria.
6. Botón Actualizar en Entidades/Grafo.
7. Tooltip pivot.

### P2 — Opcional / prep Fase 2

1. Panel lateral relaciones al clicar entidad.
2. Filtros avanzados grafo.
3. Archivar caso desde UI (PATCH ya existe).
4. Onboarding modal primera visita.
5. Mover API key a `/settings` (ruta futura).

---

## 7. Lista exacta de archivos a tocar (cuando se implemente)

### Nuevos (propuestos)

```text
frontend/src/components/Breadcrumbs.tsx
frontend/src/components/ApiKeyBanner.tsx
frontend/src/components/CaseHeader.tsx
frontend/src/components/EmptyState.tsx
frontend/src/components/LoadingBlock.tsx
frontend/src/components/EntityTypeBadge.tsx
frontend/src/components/LegalBanner.tsx
frontend/src/components/PostScanBanner.tsx
```

### Modificar

```text
frontend/src/i18n/index.tsx
frontend/src/layouts/AppShell.tsx
frontend/src/components/Header.tsx
frontend/src/components/ScanForm.tsx
frontend/src/components/RelationshipGraph.tsx
frontend/src/pages/Dashboard.tsx
frontend/src/pages/LegacyScan.tsx
frontend/src/pages/cases/CaseList.tsx
frontend/src/pages/cases/CaseNew.tsx
frontend/src/pages/cases/CaseDetail.tsx
frontend/src/pages/cases/CaseSearch.tsx
frontend/src/pages/cases/CaseEntities.tsx
frontend/src/pages/cases/CaseGraph.tsx
frontend/src/App.tsx                    # redirect case index → search
frontend/src/api.ts                     # solo si se expone listCaseJobs en UI
frontend/src/index.css                  # opcional: utilidades badge
```

### No tocar (arquitectura Fase 1)

```text
src/globeye/core/orchestrator.py
src/globeye/sources/**
src/globeye/api/routes/**   # salvo textos OpenAPI opcionales
src/globeye/db/**
```

---

## 8. Propuesta visual por pantalla (resumen)

| Ruta | Jerarquía visual propuesta |
|------|----------------------------|
| `/dashboard` | H1 + subtítulo → ApiKey → 2 CTAs → métricas → lista investigaciones |
| `/cases` | H1 + CTA → tabla/cards con estado y actividad |
| `/cases/new` | Breadcrumb → form centrado → legal → primario “Crear e escanear” |
| `/cases/:id/*` | Breadcrumb → CaseHeader (stats) → tabs → contenido |
| `/cases/:id/search` | Contexto → legal → form compacto → resultados → post-scan links |
| `/cases/:id/entities` | Intro → filtros → tabla con badges |
| `/cases/:id/graph` | Título “Grafo de la investigación” → leyenda → cytoscape |
| `/scan` | Aviso comparativo → legal → form → resultados + historial (como hoy) |

---

## 9. Referencia: capturas / estado visual actual

No se generaron capturas PNG en esta revisión (entorno sin sesión de navegador documentada). **Referencia aproximada:**

- El **shell global** (header blanco/oscuro + sidebar 192px + área principal) coincide con el layout post-Fase 1 descrito en `AppShell.tsx`.
- La **experiencia rica de resultados** (cards, historial, JSON) sigue alineada con `docs/screenshots/ui.svg` y `LegacyScan.tsx` — **no** con `CaseSearch.tsx`.
- **Documento de muestra HTML** (`docs/sample-report.html`) sigue siendo el gold standard de informe; la UI de caso solo enlaza “Informe HTML” sin previsualización.

**Recomendación:** al implementar P0, añadir 6–8 capturas reales en `docs/screenshots/phase1/` para regresión visual.

---

## 10. Checklist de validación (para cuando apruebes cambios UX)

- [ ] Usuario nuevo entiende “investigación” sin leer código
- [ ] Tras crear investigación, llega directo a escanear
- [ ] Tras escanear, sabe que entidades/grafo del caso se actualizaron
- [ ] Diferencia clara entre escaneo sin caso y escaneo en investigación
- [ ] Sin API key: mensaje claro, no “lista vacía”
- [ ] Grafo del caso vs grafo del escaneo: títulos distintos en ES y EN
- [ ] Flujo completo realizable solo con sidebar + pestañas, sin atajos ocultos

---

## 11. Siguiente paso sugerido

1. Revisar y priorizar P0/P1 en este documento.
2. Aprobar redacción ES/EN en i18n.
3. Implementar **solo paquete P0** (~1 día) sin abrir Fase 2 backend.
4. Validar con 1 usuario interno siguiendo el checklist §10.

---

*Documento generado tras revisión estática del código frontend Fase 1. Sin modificaciones de código aplicadas.*
