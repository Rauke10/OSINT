# Fase 2B.1 — Calidad, falsos positivos y diagnóstico de APIs

## Objetivo

Ayudar al analista a distinguir:

| Etiqueta | Significado |
|----------|-------------|
| **verified** | Mismo dato en ≥2 fuentes independientes |
| **likely** | Una fuente fiable (RDAP, Shodan, crt.sh, VT, etc.) sin contradicción |
| **historical** | Wayback, URLs archivadas, CT antiguo sin confirmación actual |
| **unverified** | Una sola fuente no fiable o baja confianza |
| **noisy** | Volumen alto o poco accionable (Wayback masivo, GitHub genérico) |
| **possible_false_positive** | Valor no alineado con el objetivo (dominio similar, email ajeno, etc.) |

## Cálculo (`finding_quality.py`)

- Se ejecuta tras cada escaneo de caso (`annotate_scan_result`).
- Metadatos en `finding.normalized_data.quality` (sin migración DB).
- Entidades: etiqueta derivada de hallazgos vinculados (`GET /api/cases/{id}/entities`).
- Resumen: `GET /api/cases/{id}/quality-summary`.

### Reglas principales

1. **verified** — `(kind, value)` repetido en fuentes distintas.
2. **historical / noisy** — `wayback`, `archived_url`, o resumen Wayback con `total_urls > 50`.
3. **likely** — fuente en `TRUSTED_SOURCES` + confianza medium/high.
4. **possible_false_positive** — dominio parecido pero no subdominio; email fuera del dominio objetivo; coincidencia textual sin target.
5. **unverified** — resto de casos de una sola fuente.

`confidence_score` 0–100 es orientativo (no scoring legal ni ML).

## Falso positivo en GLOBEYE

Un **falso positivo probable** es un hallazgo que:

- Comparte poca relación con el target (p. ej. `examp1e.com` vs `example.com`).
- Proviene de búsqueda textual (GitHub/Pastebin) sin enlace directo.
- Es histórico (Wayback) presentado como activo sin segunda fuente.
- Es passive DNS de un dominio popular (OTX) sin confirmación en CT/RDAP.

**No** se eliminan automáticamente: se etiquetan y se pueden ocultar en UI.

## Wayback (reducción de ruido)

- CDX: máx. 200 filas consultadas.
- Findings: máx. 50 URLs + 1 fila `wayback_summary`.
- Entidades: máx. 25 URLs como entidad `url`; el resto solo en findings/evidencia.
- UI: mensaje «Wayback devolvió {n} URLs históricas…».

## Diagnóstico API (sin secretos)

Script: `uv run python scripts/diagnose_sources.py --probe`

Mensajes HTTP normalizados (`source_errors.py`):

| HTTP / caso | Mensaje UI |
|-------------|------------|
| 401 | API key inválida o no autorizada |
| 403 | API key válida, pero sin permisos/cuota para este endpoint |
| 429 | Límite de cuota alcanzado |
| Timeout | Timeout de red |
| 5xx | Error temporal del proveedor |
| Endpoint distinto | El proveedor parece usar una API distinta a la esperada |

Pistas de clave: `****` + últimos 4 caracteres (`mask_secret`).

### Resultado típico en entorno con `.env` parcial

| Fuente | Estado probe | Causa probable |
|--------|--------------|----------------|
| shodan | ok | Clave válida |
| rdap, crtsh, gravatar, username_enum | ok / keyless | Sin clave |
| virustotal, abuseipdb, censys, hunter | invalid_key (401) | Clave rechazada o formato incorrecto |
| censys | invalid_key | PAT: `GLOBEYE_CENSYS_API_ID` + `GLOBEYE_CENSYS_API_SECRET` (no el token completo en un solo campo) |
| wayback | network_error | Timeout Archive.org (no es invalid_key) |
| otx | ok | Puede generar muchos findings (ruido) |
| securitytrails, hibp, dehashed, github, pastebin | missing_key | Variables vacías en `.env` |

## Matriz fuentes: fiable vs ruidosas

| Fiable (likely/verified) | Ruidosa / histórica |
|--------------------------|---------------------|
| rdap | wayback |
| crtsh | github (deep) |
| shodan | pastebin (deep) |
| virustotal | otx (dominios populares) |
| abuseipdb | dehashed (metadatos masivos) |
| securitytrails | |
| hibp (email) | |

## Revisión manual de un hallazgo

1. Ver badge de calidad en **Entidades** o **Hallazgos**.
2. Abrir **Evidencias** → hash + JSON redactado.
3. Comprobar si otra fuente repite el valor (→ verified).
4. Si `possible_false_positive`, validar relación con el target antes de informe.
5. Consultar **Fuentes** del job: `invalid_key` vs `missing_key` vs `no_results`.

## UI

- Badges en entidades y hallazgos.
- Filtros: ocultar falsos positivos; solo verificados/probables.
- Tooltips con `quality_reason`.

## API

```bash
curl -H "X-API-Key: $KEY" /api/cases/1/quality-summary | jq .
curl -H "X-API-Key: $KEY" /api/cases/1/entities | jq '.[0] | {display_value, quality_label, quality_reason}'
```

## Tests

- `tests/unit/test_finding_quality.py`
- `tests/integration/test_cases_api.py::test_case_quality_summary`

## Siguiente fase recomendada

- Persistir `quality_label` en DB y en informes PDF (2C).
- Agrupar Wayback por path en grafo.
- Probe por target-type (no siempre `example.com` para OTX).
- Corregir credenciales VT/AbuseIPDB/Censys/Hunter en `.env` y re-validar.
