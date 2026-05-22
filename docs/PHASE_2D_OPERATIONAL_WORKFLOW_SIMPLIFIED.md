# Fase 2D — Flujo operativo simplificado

## Decisión de producto: Aprobar = mover a Inventario OK

**Aprobar** un dato en Datos brutos significa:

1. Pasa a **Inventario OK** (`approved_for_inventory=true`, `inventory_status=approved`).
2. **Desaparece** de Datos brutos por defecto (bandeja pendiente).
3. Solo vuelve a verse en Datos brutos con el filtro explícito **En inventario** o **Todos**.

**Datos brutos** = bandeja de revisión pendiente.
**Inventario OK** = lista limpia de datos aprobados manualmente.

## Matriz de estados (`EntityReview`)

| Estado | approved | inventory_status | review_status | hidden | hidden_reason |
|--------|----------|------------------|---------------|--------|---------------|
| **Pendiente** (default en Datos brutos) | false | candidate / needs_review | pending | false | null |
| **En Inventario OK** | true | approved | reviewed | false | null |
| **Descartado** | false | rejected | discarded | true | motivo |
| **Necesita revisión** | false | needs_review | pending/reviewed | false | null |

### Reglas obligatorias

- Aprobar **nunca** pone `hidden=true` ni `review_status=discarded`.
- Descartar **quita** del inventario si estaba aprobado.
- Quitar de inventario **no** descarta (vuelve a pendiente).
- Restaurar descartado **no** aprueba automáticamente.
- No puede existir `approved_for_inventory=true` + `hidden=true`.
- No puede existir `inventory_status=approved` + `review_status=discarded`.

API: usar `action` en bulk-review: `approve`, `discard`, `restore`, `remove_inventory`.

## Navegación del caso

| Pestaña | Ruta |
|---------|------|
| Escanear | `/cases/:id/search` |
| Datos brutos | `/cases/:id/data` |
| Inventario OK | `/cases/:id/inventory` |
| Fuentes | `/cases/:id/sources` |
| Grafo | `/cases/:id/graph` |
| Informes | `/cases/:id/reports` (placeholder) |

## Datos brutos (bandeja pendiente)

### Default (`GET /api/cases/{id}/data`)

- `inventory_status=pending` (por defecto en API y UI).
- Muestra: no aprobados y no descartados.
- Oculta: aprobados en inventario y descartados.

### Filtros de bandeja

| Filtro API/UI | Qué muestra |
|---------------|-------------|
| **Pendientes** (`pending`) | No aprobados, no ocultos |
| **No aprobados** (`not_approved`) | Sin aprobación (puede incluir descartados si no se usa `hide_discarded`) |
| **En inventario** (`approved`) | Aprobados con badge «en inventario» |
| **Descartados** (`discarded`) | `hidden=true` |
| **Todos** (`all`) | Sin filtro de inventario |

Tras **Aprobar**: la fila desaparece de la vista default y `bumpRefresh()` actualiza tabla, contadores e Inventario OK.

### Comprobación activa (contacta el objetivo)

| Tipo | Botón | Comportamiento |
|------|-------|----------------|
| URL | Comprobar URL | HEAD/GET a la URL exacta |
| domain / subdomain | Comprobar web | `https://host`, si falla red → `http://host` (sin paths, sin crawling) |

- Máximo **25** por lote.
- Aviso en UI: la acción contacta directamente el sitio.

## Inventario OK

`GET /api/cases/{id}/inventory` — solo:

- `approved_for_inventory=true`
- `inventory_status=approved`
- `hidden=false`

## Paginación

- Backend: filtros **antes** de paginar; orden estable `last_seen_at DESC, id DESC`.
- `limit` / `offset` devuelven páginas distintas.
- Frontend: al cambiar filtro → `offset=0`; al pulsar siguiente → `offset += pageSize` y refetch (sin reutilizar filas antiguas).

## Rendimiento

- Enriquecimiento pesado (trazas/originales) solo en la **página** devuelta.
- Contadores en `counts` sin cargar todas las evidencias en la respuesta.
- `?debug_timing=true` en `/data` devuelve `timing_ms` (duración, entidades escaneadas, filas devueltas).

## Causa de bugs corregidos (2D.1)

| Síntoma | Causa |
|---------|--------|
| Aprobado + descartado a la vez | `bulk-review` aplicaba por defecto `review_status=discarded` y `hidden=true` al aprobar sin `action` |
| Inventario OK vacío | Mismo bug: aprobación dejaba `hidden=true` |
| Mismos 25 al paginar | Orden inestable + filtros locales sobre página ya paginada; corregido con orden por `id` y refetch por `offset` |

## Informes

Placeholder: *«Los informes se generarán desde Inventario OK y evidencias revisadas.»*
