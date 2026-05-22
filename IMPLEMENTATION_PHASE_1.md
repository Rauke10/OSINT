# GLOBEYE — Implementación Fase 1

> **Estado:** plan aprobado, **sin cambios de código aplicados aún**.
> **Referencia:** [`PLAN.md`](PLAN.md) (visión general).
> **Alcance:** casos + jobs + entidades básicas + API + frontend mínimo. **Sin** login, usuarios, evidencias avanzadas, documentos, teléfono, PDF, OpenSearch, Neo4j, Redis/Celery ni PostgreSQL obligatorio.

---

## 1. Objetivo y criterios de éxito

### 1.1 Objetivo

Convertir GLOBEYE en una aplicación **básica por casos de investigación**, reutilizando el motor pasivo existente (`Orchestrator`, fuentes, pivot, informes), con persistencia SQLModel ampliada y UI con navegación por rutas.

### 1.2 Criterios de éxito (Definition of Done)

| # | Criterio |
|---|----------|
| 1 | Modelos `Case`, `CaseTarget`, `Entity`, `EntityRelationship`, `ScanJob` creados y tablas generadas con `create_all` (SQLite por defecto). |
| 2 | Los 11 endpoints listados en §4 responden correctamente con `X-API-Key` (o `GLOBEYE_API_DEBUG=true`). |
| 3 | `POST /api/scan` sigue igual: mismo body, misma respuesta, mismo `ScanRecord` — **tests de integración API existentes en verde**. |
| 4 | `POST /api/cases/{case_id}/scans` ejecuta el orquestador, crea `ScanJob`, persiste entidades/relaciones y **también** un `ScanRecord` (para reutilizar informe HTML vía `scan_id` existente). |
| 5 | CLI `globeye scan` sin flags nuevos funciona igual; flag opcional `--case-id` asocia el scan a un caso (no obligatorio). |
| 6 | Frontend: rutas §7 navegables; búsqueda dentro de caso lanza scan por API de casos. |
| 7 | `make test` y `make lint` pasan; tests nuevos de casos/API añadidos. |
| 8 | No se elimina código ni endpoints existentes. |

---

## 2. Principios de diseño (Fase 1)

1. **Additive only:** nuevos módulos y rutas; `ScanRecord` y `core/db.py` se mantienen; funciones legacy reexportadas si hace falta.
2. **Un solo motor:** `Orchestrator.scan()` no se reescribe; un servicio `ScanService` envuelve persistencia post-scan.
3. **Normalización mínima:** reutilizar la lógica de `report/graph.py` (`GraphNodeHint` + target raíz) para poblar `Entity` / `EntityRelationship`.
4. **Jobs síncronos en Fase 1:** `POST .../scans` ejecuta el scan en la petición (como hoy `/api/scan`); `ScanJob.status` pasa `pending` → `running` → `completed`/`failed` en la misma request. Sin cola externa.
5. **Auth sin cambios:** solo `require_api_key` de despliegue; **sin** tablas User/Session.
6. **Futuro multiusuario:** columnas `owner_id: str | None = None` en `Case` y `ScanJob` (sin FK), documentadas como reservadas.

---

## 3. Modelo de datos (SQLModel mínimo)

### 3.1 Ubicación

Nuevos modelos en `src/globeye/db/models/` (paquete nuevo). `make_engine()` importará **todos** los modelos table=True antes de `create_all`.

`ScanRecord` permanece en `src/globeye/core/db.py` (sin mover en Fase 1, para no romper imports en tests y `scan.py`).

### 3.2 Tablas y campos

#### `Case`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `title` | str | index, max 200 |
| `description` | str \| None | opcional |
| `status` | str | `open` \| `archived` (default `open`) |
| `reference_code` | str \| None | opcional, único si se usa |
| `owner_id` | str \| None | **FUTURE:** usuario; sin FK |
| `created_at` | datetime UTC | |
| `updated_at` | datetime UTC | |

#### `CaseTarget`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `case_id` | int FK → Case | index |
| `raw_input` | str | texto introducido |
| `target_type` | str | valor de `TargetType` |
| `normalized_value` | str | |
| `is_primary` | bool | default False |
| `created_at` | datetime | |

Índice único: `(case_id, target_type, normalized_value)`.

#### `ScanJob`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `case_id` | int FK → Case | index |
| `target_raw` | str | |
| `target_type` | str | |
| `target_value` | str | |
| `pivot` | bool | default False |
| `status` | str | `pending`, `running`, `completed`, `failed` |
| `scan_record_id` | int \| None | FK lógico a `ScanRecord.id` |
| `error_message` | str \| None | si `failed` |
| `findings_count` | int | default 0 |
| `owner_id` | str \| None | FUTURE |
| `started_at` | datetime | |
| `finished_at` | datetime \| None | |

#### `Entity`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `case_id` | int FK | index |
| `entity_type` | str | `domain`, `subdomain`, `email`, `ip`, … (desde hint o kind) |
| `normalized_value` | str | clave de dedup (lower donde aplique) |
| `display_value` | str | etiqueta UI |
| `first_seen_at` | datetime | |
| `last_seen_at` | datetime | actualizar en scans posteriores |
| `last_job_id` | int \| None | último ScanJob que lo tocó |

Índice único: `(case_id, entity_type, normalized_value)`.

#### `EntityRelationship`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `case_id` | int FK | index |
| `source_entity_id` | int FK → Entity | |
| `target_entity_id` | int FK → Entity | |
| `relationship_type` | str | ej. `resolves_to`, `registered_by`, `mentions` |
| `source_name` | str | fuente OSINT (`crtsh`, …) |
| `created_at` | datetime | |

Índice único: `(case_id, source_entity_id, target_entity_id, relationship_type, source_name)`.

### 3.3 Registro de metadata

En `src/globeye/db/__init__.py`:

```python
def register_models() -> None:
    """Import all SQLModel table classes so metadata.create_all sees them."""
```

`create_app` / `make_engine` llamará `register_models()` antes de `create_all`.

---

## 4. Endpoints FastAPI (contratos)

Todos bajo el mismo `Depends(require_api_key)` que `scan` e `history`, salvo `health` y `sources`.

### 4.1 Casos

| Método | Ruta | Request | Response |
|--------|------|---------|----------|
| POST | `/api/cases` | `{ "title", "description?", "reference_code?" }` | `Case` serializado + `id` |
| GET | `/api/cases` | query: `status?`, `limit?` (default 50), `offset?` | `list[CaseSummary]` |
| GET | `/api/cases/{case_id}` | — | `CaseDetail` (+ contadores opcionales: targets, jobs, entities) |
| PATCH | `/api/cases/{case_id}` | `{ "title?", "description?", "status?" }` | `Case` actualizado |

Errores: `404` si caso no existe; `422` validación Pydantic.

### 4.2 Targets del caso

| Método | Ruta | Request | Response |
|--------|------|---------|----------|
| POST | `/api/cases/{case_id}/targets` | `{ "target": "example.com" }` | `CaseTarget` (tras `detect()`) |
| GET | `/api/cases/{case_id}/targets` | — | `list[CaseTarget]` |

Si `detect()` falla → `422`. Duplicado → `409` o upsert silencioso (decisión: **409** para claridad).

### 4.3 Scans y jobs

| Método | Ruta | Request | Response |
|--------|------|---------|----------|
| POST | `/api/cases/{case_id}/scans` | `{ "target", "pivot": false }` | Igual que `/api/scan` **más** `job_id`, `case_id`; incluye `scan_id` (`ScanRecord`) |
| GET | `/api/cases/{case_id}/jobs` | query: `limit?` | `list[JobSummary]` |
| GET | `/api/jobs/{job_id}` | — | `JobDetail` (+ payload scan si `completed`: findings resumidos o link a history) |

Flujo interno `POST .../scans`:

1. Validar caso existe.
2. `detect(target)` → `Target`.
3. Crear `ScanJob(status=pending)`.
4. `status=running` → `Orchestrator.scan()`.
5. `save_scan()` → `scan_record_id`.
6. `persist_entities_from_scan(case_id, job_id, result)` → entidades/relaciones.
7. `ScanJob.status=completed`, `findings_count`, `finished_at`.
8. En excepción: `status=failed`, `error_message`, re-raise o HTTP 500 según tipo.

### 4.4 Entidades

| Método | Ruta | Response |
|--------|------|----------|
| GET | `/api/cases/{case_id}/entities` | `list[EntityOut]` (filtro opcional `entity_type?`) |
| GET | `/api/entities/{entity_id}/relationships` | `{ "entity_id", "outgoing": [...], "incoming": [...] }` |

Validar que `entity_id` pertenece al caso cuando se pase `case_id` en query (opcional Fase 1: solo comprobar existencia de entidad).

### 4.5 Sin cambios (compatibilidad)

| Método | Ruta | Notas |
|--------|------|-------|
| POST | `/api/scan` | **Idéntico** — no recibe `case_id`; solo `ScanRecord` |
| GET | `/api/history` | Sin cambios |
| GET | `/api/history/{scan_id}` | Sin cambios |
| GET | `/api/scan/{scan_id}/report` | Sin cambios |
| GET | `/api/health` | Sin cambios |
| GET | `/api/sources` | Sin cambios |

### 4.6 Endpoint auxiliar para grafo (opcional, recomendado)

No estaba en la lista del usuario, pero el frontend `/graph` lo necesita sin reimplementar lógica:

| Método | Ruta | Response |
|--------|------|----------|
| GET | `/api/cases/{case_id}/graph` | `{ "nodes": [...], "edges": [...] }` compatible Cytoscape |

Implementación: agregar entidades + relaciones del caso al formato de `report/graph.py`. **Si se prefiere estrictamente la lista del usuario**, el grafo en UI puede construirse client-side desde `entities` + `relationships` por entidad (más peticiones). **Recomendación:** añadir `/graph` como atajo (documentado aquí; confirmar al implementar).

---

## 5. Servicios y normalización

### 5.1 `ScanService` (`src/globeye/services/scan_service.py`)

```text
run_case_scan(engine, settings, case_id, target, pivot) -> CaseScanResponse
```

- Orquesta pasos §4.3.
- No modifica `Orchestrator`.

### 5.2 `EntityNormalizer` (`src/globeye/services/entity_normalizer.py`)

Entrada: `case_id`, `job_id`, `ScanResult`.

Algoritmo (alineado con `report/graph.py`):

1. **Entidad raíz:** target del scan (`entity_type` = `target.type`, `normalized_value` = `target.value`).
2. Por cada `Finding`:
   - Si `graph_node_hint`: entidad hijo (`node_id`, `node_type`, `label`); arista `parent_id` → `node_id` con `source_name` = `finding.source`, `relationship_type` = `discovered_via` (o mapeo por `kind` si existe).
   - Si no hay hint pero `value` es identificable: entidad con `entity_type` = `finding.kind`, arista raíz → valor.
3. **Upsert:** si `(case_id, entity_type, normalized_value)` existe → actualizar `last_seen_at`, `last_job_id`.
4. **Relaciones:** upsert por índice único; ignorar self-loops.

No persistir `raw_evidence` en tablas separadas (Fase 2). El JSON completo sigue en `ScanRecord.result_json`.

### 5.3 Tipos de relación (Fase 1, enum string simple)

| `relationship_type` | Cuándo |
|---------------------|--------|
| `discovered_via` | Default desde `graph_node_hint` |
| `pivot_to` | Opcional si se guardan pivots como entidades en el futuro |

---

## 6. Compatibilidad detallada

### 6.1 API

| Área | Estrategia |
|------|------------|
| `POST /api/scan` | `scan.py` sin cambios de contrato; opcionalmente extraer lógica compartida a `ScanService.run_legacy_scan()` para DRY **sin** cambiar respuesta JSON. |
| Historial | `ScanRecord` independiente de casos; scans legacy no tienen `ScanJob`. |
| Informes HTML | Casos usan `scan_record_id` → mismo endpoint `/api/scan/{id}/report`. |
| OpenAPI | Nuevos routers con tag `cases`; esquemas Pydantic en `api/schemas/cases.py`. |

### 6.2 CLI

| Comando | Cambio |
|---------|--------|
| `globeye scan TARGET` | Sin cambios por defecto. |
| `globeye scan TARGET --case-id 3` | Opcional: tras scan, llama persistencia caso (mismo `EntityNormalizer`) vía función compartida, sin requerir API. |

Implementación CLI: importar `ScanService` + `make_engine(get_settings())`; si falla DB, mensaje claro pero exit code 0 del scan si el scan en sí OK (o documentar que `--case-id` requiere DB).

### 6.3 Base de datos

- Misma `GLOBEYE_DB_URL`; `create_all` añade tablas nuevas **sin** migración Alembic en Fase 1 (SQLite dev: borrar DB solo en desarrollo manual; no script destructivo en repo).
- Tests usan `tmp_path` SQLite aislado (como `test_api.py`).

### 6.4 Frontend legacy

- La UI de scan “global” actual en `App.tsx` se **mueve** a componente `LegacyScanPage` o se integra en `/cases/:caseId/search` como vista principal de búsqueda.
- Rutas nuevas no eliminan funcionalidad: historial global puede quedar en dashboard o enlace desde sidebar (mínimo: enlace “Escaneo rápido (sin caso)” → ruta `/scan` que renderiza el formulario antiguo).

### 6.5 SPA + FastAPI

`main.py` hoy solo sirve `/` → `index.html`. Para React Router:

- Añadir ruta catch-all `GET /{full_path:path}` que devuelve `index.html` **excepto** paths que empiezan por `api/` o `assets/`.
- Vite `build` sin cambios de `outDir`.

---

## 7. Frontend (React Router mínimo)

### 7.1 Dependencias nuevas

```json
"react-router-dom": "^6.28.0"
```

Sin TanStack Query en Fase 1 (fetch + `useState`/`useEffect` suficiente).

### 7.2 Estructura de archivos

```text
frontend/src/
  main.tsx                    # BrowserRouter
  App.tsx                     # Routes + layout outlet (slim)
  api.ts                      # + funciones cases/jobs/entities
  types.ts                    # + Case, Entity, Job, ...
  layouts/
    AppShell.tsx              # sidebar + header + <Outlet />
  pages/
    Dashboard.tsx             # /dashboard
    LegacyScan.tsx            # /scan (opcional, compat UI)
    cases/
      CaseList.tsx            # /cases
      CaseNew.tsx             # /cases/new
      CaseDetail.tsx          # /cases/:caseId (tabs/links)
      CaseSearch.tsx          # /cases/:caseId/search
      CaseEntities.tsx        # /cases/:caseId/entities
      CaseGraph.tsx           # /cases/:caseId/graph
  components/                 # existentes reutilizados
    RelationshipGraph.tsx     # adaptar props: ScanResult | graph API
    ScanForm.tsx
    ...
```

### 7.3 Rutas

| Ruta | Página | Comportamiento |
|------|--------|----------------|
| `/` | redirect | → `/dashboard` |
| `/dashboard` | `Dashboard.tsx` | Contadores: casos abiertos, últimos jobs, entidades (API agregada o listas limitadas) |
| `/cases` | `CaseList.tsx` | GET `/api/cases` |
| `/cases/new` | `CaseNew.tsx` | POST `/api/cases` → redirect detalle |
| `/cases/:caseId` | `CaseDetail.tsx` | Resumen + nav a subrutas |
| `/cases/:caseId/search` | `CaseSearch.tsx` | `ScanForm` + POST `.../scans` |
| `/cases/:caseId/entities` | `CaseEntities.tsx` | Tabla entidades |
| `/cases/:caseId/graph` | `CaseGraph.tsx` | Cytoscape desde GET graph o entidades+rels |
| `/scan` | `LegacyScan.tsx` | UI actual `App.tsx` (POST `/api/scan`) |

### 7.4 Sidebar (`AppShell`)

```text
Dashboard
Casos
─────────
(Escaneo rápido → /scan)   # opcional
─────────
API docs (external /api/docs)
```

i18n: añadir claves mínimas en `i18n/index.tsx` para casos/dashboard (ES/EN).

### 7.5 API client (`api.ts`)

Funciones nuevas (misma auth `X-API-Key`):

- `createCase`, `listCases`, `getCase`, `updateCase`
- `addCaseTarget`, `listCaseTargets`
- `runCaseScan(caseId, target, pivot, apiKey)`
- `listCaseJobs`, `getJob`
- `listCaseEntities`, `getEntityRelationships`
- `getCaseGraph` (si endpoint §4.6)

---

## 8. Archivos a CREAR

### 8.1 Backend — Python

| Archivo | Propósito |
|---------|-----------|
| `src/globeye/db/__init__.py` | `register_models()` |
| `src/globeye/db/models/__init__.py` | exports |
| `src/globeye/db/models/case.py` | `Case`, `CaseTarget` |
| `src/globeye/db/models/job.py` | `ScanJob` |
| `src/globeye/db/models/entity.py` | `Entity`, `EntityRelationship` |
| `src/globeye/services/__init__.py` | |
| `src/globeye/services/scan_service.py` | Orquestación persistencia caso |
| `src/globeye/services/entity_normalizer.py` | Findings → entidades |
| `src/globeye/api/schemas/__init__.py` | |
| `src/globeye/api/schemas/cases.py` | Pydantic request/response |
| `src/globeye/api/routes/cases.py` | Router casos + targets |
| `src/globeye/api/routes/jobs.py` | Router jobs |
| `src/globeye/api/routes/entities.py` | Router entidades + relaciones (+ graph opcional) |

### 8.2 Backend — Tests

| Archivo | Propósito |
|---------|-----------|
| `tests/unit/test_entity_normalizer.py` | Normalización con fixtures `ScanResult` |
| `tests/integration/test_cases_api.py` | CRUD caso, scan, entidades, jobs |
| `tests/fixtures/scan_result_domain.json` | Opcional: resultado mínimo para unit |

### 8.3 Frontend

| Archivo | Propósito |
|---------|-----------|
| `frontend/src/layouts/AppShell.tsx` | Layout sidebar |
| `frontend/src/pages/Dashboard.tsx` | |
| `frontend/src/pages/LegacyScan.tsx` | UI scan global |
| `frontend/src/pages/cases/CaseList.tsx` | |
| `frontend/src/pages/cases/CaseNew.tsx` | |
| `frontend/src/pages/cases/CaseDetail.tsx` | |
| `frontend/src/pages/cases/CaseSearch.tsx` | |
| `frontend/src/pages/cases/CaseEntities.tsx` | |
| `frontend/src/pages/cases/CaseGraph.tsx` | |

### 8.4 Documentación

| Archivo | Propósito |
|---------|-----------|
| `IMPLEMENTATION_PHASE_1.md` | Este documento |
| `CHANGELOG.md` | Entrada `Unreleased` / `0.2.0` Fase 1 (al implementar) |

---

## 9. Archivos a MODIFICAR (sin borrar)

| Archivo | Cambio previsto |
|---------|-----------------|
| `src/globeye/api/main.py` | `register_models()`; `include_router` cases/jobs/entities; catch-all SPA |
| `src/globeye/core/db.py` | Llamar `register_models()` desde `make_engine` **o** import models en `make_engine` |
| `src/globeye/api/routes/scan.py` | Opcional: extraer cuerpo a `ScanService` (comportamiento idéntico) |
| `src/globeye/cli/app.py` | Flag opcional `--case-id` |
| `frontend/package.json` | `react-router-dom` |
| `frontend/package-lock.json` | lockfile tras npm install |
| `frontend/src/main.tsx` | `BrowserRouter` |
| `frontend/src/App.tsx` | Rutas + delegación a páginas (contenido actual → `LegacyScan`) |
| `frontend/src/api.ts` | Cliente casos/jobs/entidades |
| `frontend/src/types.ts` | Tipos TS nuevos |
| `frontend/src/i18n/index.tsx` | Cadenas casos/dashboard |
| `frontend/src/components/RelationshipGraph.tsx` | Aceptar datos grafo API además de `ScanResult` |
| `docs/architecture.md` | Diagrama casos (breve) |
| `docs/usage.md` | Endpoints casos + rutas UI |
| `README.md` | Sección “Investigations (cases)” breve |
| `PLAN.md` | Opcional: marcar Fase 1 “en progreso” |

### 9.1 Archivos que NO se tocan (salvo imports indirectos)

- Todas las fuentes en `src/globeye/sources/**`
- `src/globeye/core/orchestrator.py` (sin cambios funcionales)
- `src/globeye/core/models.py` (Finding/ScanResult estables)
- `src/globeye/api/auth.py`
- `src/globeye/utils/http.py`
- Tests de fuentes existentes
- `Dockerfile`, `docker-compose.yml` (sin cambios obligatorios)

---

## 10. Archivos que NO se crean / NO se implementan en Fase 1

- `src/globeye/auth/` (User, Login, Session)
- `src/globeye/compliance/` (AuditLog, SearchJustification) — solo comentarios FUTURE si aplica
- `src/globeye/documents/`, `phone/`, `profiles/`
- Alembic / migraciones PostgreSQL
- Workers Redis/Celery
- Informes PDF nuevos
- Endpoints: login, users, roles, evidence, settings UI backend (keys siguen en `.env`)

---

## 11. Plan de tests

### 11.1 Tests existentes que deben seguir pasando

| Suite | Archivo(s) | Motivo |
|-------|------------|--------|
| API legacy | `tests/integration/test_api.py` | `POST /api/scan`, history, report |
| CLI | `tests/integration/test_cli.py` | `globeye scan` |
| Orchestrator | `tests/unit/test_orchestrator.py` | Motor intacto |
| HTTP guard | `tests/unit/test_http_guard.py` | Pasividad |
| Sources | `tests/unit/sources/*` | Fuentes |
| E2E | `tests/e2e/test_full_scan.py` | Pipeline completo |
| DB/HTML | `tests/unit/test_html_graph_db.py` | ScanRecord |
| Smoke | `tests/test_smoke.py` | |

### 11.2 Tests nuevos

**`tests/unit/test_entity_normalizer.py`**

- ScanResult sintético con `graph_node_hint` (crtsh-like) → N entidades, M relaciones.
- Segundo scan mismo caso → `last_seen_at` actualizado, sin duplicar entidades.
- Finding sin hint → entidad + relación a raíz.

**`tests/integration/test_cases_api.py`**

- CRUD caso (create, list, get, patch).
- POST target + duplicado 409.
- POST scan en caso (mock HTTP como `test_scan_history_and_report`).
- GET jobs, GET job by id.
- GET entities count > 0 tras scan dominio (api.example.com).
- GET relationships para entidad hija.
- `POST /api/scan` sigue sin `case_id` y no crea `ScanJob`.
- 404 caso/job/entidad inexistente.

### 11.3 Comandos a ejecutar (orden)

```bash
make lint
make test
npm --prefix frontend ci && npm --prefix frontend run typecheck
npm --prefix frontend run build
```

En CI local reproducir `.github/workflows/ci.yml` si existe job frontend.

### 11.4 Criterio de regresión manual (opcional)

1. `make run` → `/dashboard`, crear caso, buscar `example.com`, ver entidades y grafo.
2. `curl POST /api/scan` sin case → igual que antes.
3. `uv run globeye scan example.com` sin flags.

---

## 12. Orden de implementación recomendado

```text
1. db/models/* + register_models + make_engine
2. services/entity_normalizer + unit tests
3. services/scan_service
4. api/schemas + routes (cases → jobs → entities)
5. tests/integration/test_cases_api.py
6. Refactor opcional scan.py → ScanService (verificar test_api)
7. cli --case-id (opcional, tras API verde)
8. frontend: router, layout, páginas, api.ts
9. main.py SPA fallback + build frontend
10. docs + CHANGELOG
```

Estimación: ~2–4 días de desarrollo concentrado según familiaridad con el repo.

---

## 13. Riesgos y mitigaciones (Fase 1)

| Riesgo | Mitigación |
|--------|------------|
| Romper `POST /api/scan` | Test de regresión primero; cambio mínimo en `scan.py` |
| SQLite bloqueado en scan largo | Mismo comportamiento que hoy; documentar timeout |
| Grafo vacío sin hints | Mostrar solo nodo raíz; mensaje en UI |
| SPA 404 al refrescar `/cases/1` | Catch-all en FastAPI |
| Duplicar entidades entre jobs | Índice único + upsert |
| Confusión API key vs usuario | README: API key = despliegue, no login |

---

## 14. Decisiones pendientes de confirmación (antes de codificar)

| # | Pregunta | Recomendación |
|---|----------|---------------|
| 1 | ¿Añadir `GET /api/cases/{case_id}/graph`? | **Sí** — menos carga en UI |
| 2 | ¿Duplicado `CaseTarget`? | **409 Conflict** |
| 3 | ¿CLI `--case-id` en Fase 1? | **Sí**, opcional, bajo esfuerzo |
| 4 | ¿Ruta `/scan` para UI legacy? | **Sí**, para no perder flujo sin caso |
| 5 | ¿`PATCH` permite `archived`? | **Sí** vía `status` (sin endpoint `/archive` separado) |

---

## 15. Checklist pre-merge (Fase 1)

- [ ] Todos los endpoints §4 implementados
- [ ] `tests/integration/test_api.py` verde
- [ ] `tests/integration/test_cases_api.py` verde
- [ ] `tests/unit/test_entity_normalizer.py` verde
- [ ] `make lint` verde
- [ ] Frontend build sin errores TS
- [ ] `POST /api/scan` documentado como legacy / sin caso
- [ ] Sin tablas User/Role/Session
- [ ] Sin código borrado de fuentes ni orchestrator

---

*Siguiente paso tras tu OK: implementar siguiendo §12 en el orden indicado.*
