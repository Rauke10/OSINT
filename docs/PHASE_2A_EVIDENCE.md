# Fase 2A — Trazabilidad y evidencias básicas

## Objetivo

Guardar **qué fuente** devolvió cada dato, con estado, latencia y evidencia redactada enlazada al caso y al escaneo.

## Modelo de datos

### `source_result`

Una fila por **fuente × escaneo (job)**.

| Campo | Descripción |
|-------|-------------|
| `case_id`, `scan_job_id` | Investigación y escaneo |
| `source_name` | Nombre interno (`crtsh`, `shodan`, …) |
| `status` | `used`, `no_results`, `missing_key`, `invalid_key`, `rate_limited`, `network_error`, `config_error`, `timeout`, `failed` |
| `findings_count` | Hallazgos de esa fuente en el job |
| `latency_ms` | Duración de la consulta (si aplica) |
| `message`, `error_type` | Texto legible / categoría |

### `evidence`

Artefacto auditable por hallazgo con `raw_evidence` (u URL/metadata).

| Campo | Descripción |
|-------|-------------|
| `source_result_id`, `entity_id` | Enlaces opcionales |
| `finding_kind`, `finding_value` | Contexto del hallazgo |
| `evidence_type` | `raw_json`, `url`, `metadata` |
| `raw_json` | JSON redactado (máx. ~100 KB) |
| `content_hash_sha256` | Integridad del contenido guardado |
| `sensitive`, `redacted` | Marcadores de seguridad |

## Flujo de persistencia

1. `POST /api/cases/{id}/scans` ejecuta el orchestrator.
2. Se guardan entidades (`persist_entities_from_scan`).
3. `persist_scan_traceability` escribe `source_result` + `evidence`.
4. **Legacy** `POST /api/scan` no persiste evidencias (sin caso).

Redacción: `Redactor` con secretos de `Settings` + patrones en `utils/redact.py`.

## Endpoints nuevos

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/cases/{case_id}/sources` | Filtros: `job_id`, `status_filter`, `source_name` |
| GET | `/api/cases/{case_id}/evidence` | Filtros: `job_id`, `source_name`, `entity_id` |
| GET | `/api/jobs/{job_id}/sources` | SourceResult del job |
| GET | `/api/jobs/{job_id}/evidence` | Evidence del job |
| GET | `/api/evidence/{evidence_id}` | Detalle (incl. `raw_json` redactado) |
| GET | `/api/evidence/{evidence_id}/hash` | `{ algorithm, content_hash_sha256 }` |

Ningún endpoint devuelve API keys.

## UI

Rutas:

- `/cases/:caseId/sources` — tabla de fuentes por escaneo
- `/cases/:caseId/evidence` — lista + panel de detalle

Pestañas del caso: Escanear · Entidades · Grafo · **Fuentes** · **Evidencias** · Resumen

## Cómo probar

```bash
# Crear investigación y escanear
curl -H "X-API-Key: $KEY" -X POST /api/cases -d '{"title":"Test"}'
curl -H "X-API-Key: $KEY" -X POST /api/cases/1/scans -d '{"target":"example.com"}'

# Ver trazabilidad
curl -H "X-API-Key: $KEY" /api/cases/1/sources
curl -H "X-API-Key: $KEY" /api/cases/1/evidence
```

En la web: crear investigación → escanear `example.com` → pestaña **Fuentes** → **Evidencias**.

CLI:

```bash
uv run globeye scan example.com --case-id 1 --no-cache
```

## Limitaciones (2A)

- Solo escaneos **con caso** persisten SourceResult/Evidence.
- No todos los hallazgos tienen `raw_evidence` (solo se guarda cuando existe).
- `entity_id` puede ser `null` si el hallazgo no enlaza con entidad normalizada.
- Sin ficheros externos (`storage_path`); JSON en SQLite.
- Sin informes PDF ni cadena de custodia legal completa.

## Fase 2B (futuro)

- Informes ejecutivos y export PDF
- Documentos públicos, teléfonos, personas
- Auditoría legal ampliada
- Posible almacenamiento de blobs grandes fuera de SQLite
