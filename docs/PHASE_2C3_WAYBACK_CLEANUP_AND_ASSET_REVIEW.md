# Fase 2C.3 — Limpieza de activos, agrupación Wayback y diagnóstico de APIs

> **Fase 2C.4** añade trazabilidad de normalización, agrupación no destructiva y auditoría Wayback.
> Ver también [DATA_MODEL_EXPLAINED.md](./DATA_MODEL_EXPLAINED.md).

## Objetivo

Convertir **Datos brutos** en la vista operativa de revisión: selección masiva, comprobación live limitada, descarte reversible, agrupación Wayback y diagnóstico claro de fuentes/APIs.

> **Fase 2D** fusiona la comprobación URL en Datos brutos y añade Inventario OK — ver [PHASE_2D_OPERATIONAL_WORKFLOW_SIMPLIFIED.md](./PHASE_2D_OPERATIONAL_WORKFLOW_SIMPLIFIED.md). Antes del recorte de menú la pestaña se llamaba «Datos encontrados».

## Datos, evidencias y hallazgos

| Concepto | Qué es |
|----------|--------|
| **Datos** | Entidades normalizadas y agrupadas (dominio, IP, email, URL, etc.) mostradas en Datos brutos. |
| **Evidencias** | Pruebas originales (respuestas raw, URLs Wayback, hashes, registros de fuente). Puede haber **más evidencias que datos** porque varias evidencias apuntan al mismo dato o porque no toda evidencia histórica se convierte en entidad principal. |
| **Hallazgos** | Elementos detectados por fuentes **antes** de normalizar. Un hallazgo puede generar una entidad y una o varias evidencias. |

### Inventario Wayback operativo (revisión 2C.4)

- Hasta **200 URLs** por escaneo desde CDX (`CDX_FETCH_LIMIT`) → **todas** pasan a `Entity` URL y al Data Explorer.
- Calidad `historical` / `noisy` y prioridad Wayback marcan **prioridad**, no visibilidad por defecto.
- Paginación UI + API hasta 2000 filas filtradas; export «todo lo filtrado».
- **25** solo en live check por lote (`MAX_BATCH_URLS`), no en inventario.
- Si CDX devuelve más URLs de las pedidas al API, `wayback_summary` indica truncado del fetch (pasivo), no borrado en app.

## Filtros y «Mostrar todo»

- Por defecto: `hide_noisy=false`, `hide_historical=false`, `hide_false_positive=false`, `hide_discarded=false`.
- Si algún filtro oculta filas, aparece banner **«Hay datos ocultos por filtros activos»** y bloque **Filtros activos** con botón **Mostrar todo** (resetea ocultar históricos/ruidosos/FP/descartados, calidad, live, operativo, búsqueda, etc.).
- **Ocultar** ≠ **borrar**: descartar marca `EntityReview` y oculta en vista; restaurar revierte sin borrar entidades ni evidencias.

## Contadores API (`GET /api/cases/{id}/data`)

Campos principales en `counts` y top-level:

- `total_count` — entidades en el caso
- `filtered_count` — tras filtros query (antes de paginar)
- `visible_count` — filas en la página actual
- `hidden_by_filters_count` — ocultos por filtros activos
- `evidence_total_count`, `evidence_filtered_count`
- `findings_total_count`, `archived_url_findings_count`, `url_entity_count`, `wayback_entity_limit`
- `limit`, `offset` — paginación (UI: 25 / 50 / 100 / 250; API máx. 2000 filas filtradas)

## Selección masiva

| Acción | Alcance |
|--------|---------|
| Checkbox cabecera / «Seleccionar visibles» | Solo filas **visibles** en pantalla (tras filtros y ordenación local) |
| «Seleccionar todos los filtrados» | Hasta **2000** filas que cumplen filtros API activos (no solo la página) |
| «Comprobar seleccionadas» | Máximo **25** URLs; aviso si hay más seleccionadas |

## Descartar / restaurar

- Modelo `EntityReview`: `review_status`, `hidden`, `hidden_reason`, `note`.
- **No borra** entidades ni evidencias.
- Endpoints:
  - `PATCH /api/entities/{entity_id}/review`
  - `POST /api/cases/{case_id}/data/bulk-review`
- Acciones UI: descartar seleccionadas, descartar 404 filtrados, restaurar seleccionadas, **Mostrar descartadas** / **Ocultar descartadas**.

## Agrupación Wayback

Servicio `url_grouping.py`: categorías (`admin_login`, `api_endpoint`, …) y prioridades (`high`, `medium`, `low`, `noisy`).

Panel en UI con contadores y «Comprobar URLs de alta prioridad» (≤25, no comprobadas).

Filtros API: `wayback_category`, `wayback_priority`, `only_high_priority`.

## operational_status

Valores: `active`, `inactive`, `unknown`, `historical`, `discarded`, `needs_review`.

Filtro query: `operational_status=active` (etc.).

## Diagnóstico de APIs

`GET /api/sources/status` enriquecido con `ui_category`, `fix_hint`, `env_vars`, `masked_hint` (****abcd).

Vista **Fuentes**: panel global + sección **Por qué no se ejecutaron otras fuentes** (no aplican, sin key, key inválida, profundidad, deshabilitadas, rate limit/red).

## Cómo probar

1. Escanear dominio con muchas URLs Wayback → **Datos encontrados**.
2. Confirmar contador: total entidades vs visibles vs evidencias totales; nota Wayback si hallazgos ≫ entidades URL.
3. Por defecto deben verse históricos/ruidosos/FP/descartados (si existen).
4. Activar «Ocultar históricos» → banner y contador de ocultos; **Mostrar todo** limpia filtros.
5. Paginación: cambiar 25/50/100/250 y navegar páginas; texto «Mostrando X–Y de Z filtrados».
6. **Comprobar seleccionadas** sigue limitado a 25; el listado no.
7. Descartar 404 → **Mostrar descartadas** → **Restaurar seleccionadas**.
8. **Fuentes** → revisar «Por qué no se ejecutaron otras fuentes».

## Fase 2C.4 — Trazabilidad (resumen)

- `url_normalization.py`: claves de entidad sin fusionar paths/archivos distintos.
- Campos en items de datos: `original_values`, `canonical_key`, `variant_of`, `group_reason`, `evidence_ids`, …
- `GET /api/entities/{entity_id}/trace`
- UI: **Ver trazabilidad**, contadores Wayback ampliados, CSV de auditoría, grupos con **Ver URLs**.

## Limitaciones

- «Seleccionar todos filtrados» y la API no superan **2000** filas filtradas.
- Hasta **200 URLs Wayback** por escaneo CDX en inventario (consulta pasiva a Internet Archive).
- Sin persistencia de preferencias de usuario ni informes PDF.
