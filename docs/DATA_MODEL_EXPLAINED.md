# Modelo de datos GLOBEYE — explicado

## Capas

| Capa | Qué es | Dónde vive |
|------|--------|------------|
| **Dato bruto** | Respuesta original de la fuente (CDX, JSON API, etc.) | Evidencia (`StoredEvidence.raw_json`) |
| **Hallazgo** | Elemento detectado en un escaneo antes de normalizar | `Finding` en resultado de escaneo |
| **Evidencia** | Prueba auditable almacenada y enlazada al caso | `StoredEvidence` |
| **Entidad** | Dato normalizado en inventario operativo del caso | `Entity` |
| **Grupo Wayback** | Etiqueta operativa (admin, document, …) | Calculado — **no borra filas** |
| **Activo operativo** | Estado para trabajo (activo, histórico, descartado, …) | `operational_status` + `EntityReview` |
| **Inventario OK** | Aprobación manual del analista (Fase 2D) | `EntityReview.approved_for_inventory`, `inventory_status` |

## Inventario OK (Fase 2D)

- **Datos brutos** muestra todo; **Inventario OK** solo filas con `approved_for_inventory=true` y `inventory_status=approved`.
- Live 200 puede marcar `inventory_suggested`; **no** auto-aprueba.
- Grafo por defecto usa solo inventario aprobado (`?mode=inventory`).

## Inventario Wayback (desde Fase 2C.4 revisada)

Por escaneo, Wayback (CDX) puede devolver hasta **200 URLs únicas** (`CDX_FETCH_LIMIT`).

**Todas** las URLs devueltas en ese lote:

1. Se guardan como hallazgo `archived_url`
2. Se convierten en **Entity** `type=url` (inventario operativo)
3. Aparecen en **Datos brutos** con paginación (25/50/100/250 por página, hasta 2000 filas filtradas vía API)
4. Llevan calidad `historical` o `noisy`, categoría/prioridad Wayback, y `operational_status` acorde

No se eliminan del explorador por defecto. Si CDX reporta más de 200 URLs totales, el resumen `wayback_summary` indica truncado; las no pedidas a CDX en ese escaneo no entran en el lote (límite pasivo de la consulta, no borrado).

### Límite 25 — solo live check activo

`MAX_BATCH_URLS = 25` en `url_live_check.py` aplica **únicamente** a «Comprobar seleccionadas». No limita:

- entidades guardadas
- filas visibles / paginadas
- export CSV (hasta 2000 filtradas)
- descarte / restauración
- agrupación

## Normalización vs agrupación vs fusión

### Normalización (`url_normalization.py`)

- Host en minúsculas; path/archivo/endpoint **intactos**
- Variantes `http/https`, barra final, `utm_*` → `canonical_key` (originales en trazas)

### Agrupación (`url_grouping.py`)

Organiza por categoría; **no fusiona** ni elimina URLs.

### Fusión

Solo equivalencia real (`canonical_key`); cada path distinto sigue siendo su entidad.

## Por qué evidencias ≥ datos

- Varias evidencias pueden apuntar a la misma entidad
- Hallazgos `wayback_summary` y otros no son filas del explorador
- Entidades de otras fuentes (dominio, subdominio, …) cuentan en `total_count`

Tras la revisión operativa, **hallazgos `archived_url` del lote CDX ≈ entidades URL Wayback** del mismo escaneo.

## Cómo comprobar que no se pierden datos

1. Datos brutos — contadores Wayback y paginación «Mostrando X–Y de Z»
2. Inventario OK — solo tras aprobación manual
2. **Ver trazabilidad** por fila
3. **Exportar todo lo filtrado** (hasta 2000)
4. `GET /api/entities/{id}/trace`

## Límites

| Límite | Valor | Aplica a |
|--------|-------|----------|
| Live check por lote | 25 | Comprobar seleccionadas |
| URLs Wayback por escaneo (CDX) | 200 | Fetch + entidades + explorador |
| Página UI | 25–250 | Presentación |
| API datos filtrados | 2000 | `GET .../data?limit=` |
