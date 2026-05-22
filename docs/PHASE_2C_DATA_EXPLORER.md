# Fase 2C — Explorador de datos por investigación

## Objetivo

Vista central **Datos encontrados** (`/cases/:caseId/data`) para revisar todo lo descubierto en una investigación: clasificado por tipo, calidad y fuente, con filtros y exportación CSV.

## Endpoint

```http
GET /api/cases/{case_id}/data
```

Query params:

| Param | Descripción |
|-------|-------------|
| `type` | domain, subdomain, ip, email, url, username, … |
| `quality` | verified, likely, historical, unverified, noisy, possible_false_positive |
| `source` | rdap, crtsh, shodan, wayback, … |
| `q` | Búsqueda libre en valor/fuentes |
| `hide_noisy` | default `true` — oculta históricos/ruidosos |
| `hide_false_positive` | default `false` en API; UI suele activarlo |
| `verified_only` | solo verified + likely |
| `limit` / `offset` | paginación (máx. 2000) |

Respuesta: `summary`, `items[]`, `total`, `hidden_noisy_count`.

## Tipos soportados

| Tipo UI | Origen entidad |
|---------|----------------|
| domain | domain, registration |
| subdomain | subdomain |
| ip | ip, service |
| email | email |
| url | url, archived_url |
| username | username |
| phone / person / organization | según normalización |
| finding / evidence | contadores agregados en `summary` |

## Filtros en UI

- Cards por tipo (clic = filtro)
- Pestañas: Todos, Dominios, IPs, Emails, URLs, Usernames, Personas, Técnicos, Ruidosos/Históricos
- Calidad, fuente, texto
- Toggles: ocultar ruidosos, ocultar FP, solo verificados/probables

## Calidad (2B.1)

Badges integrados. Textos de ayuda en la cabecera de la vista.

## Wayback

Por defecto `hide_noisy=true` oculta URLs históricas masivas. Pestaña **Ruidosos/Históricos** o desmarcar el toggle las muestra. El resumen Wayback sigue en hallazgos al escanear.

## Exportar CSV

Botón **Exportar CSV**: tipo, valor, calidad, fuentes, evidencias, first_seen, last_seen (solo filas visibles).

## Cómo probar

1. Crear investigación → escanear `example.com` o `ecix.tech` o `8.8.8.8`.
2. Abrir pestaña **Datos encontrados**.
3. Filtrar por IPs / dominios / emails.
4. Exportar CSV si hace falta.

```bash
curl -H "X-API-Key: $KEY" /api/cases/1/data | jq '.summary'
curl -H "X-API-Key: $KEY" '/api/cases/1/data?type=ip&hide_noisy=true' | jq '.items | length'
```

## Fuentes con error de API

No bloquea el explorador. Revisa **Fuentes** del caso y ejecuta:

```bash
uv run python scripts/diagnose_sources.py --probe
```

Corrige Censys / VirusTotal / AbuseIPDB / Hunter si aparecen `invalid_key`.

## Limitaciones

- Marcar revisado / ocultar FP persistente: pendiente (sin backend).
- `finding` en summary es conteo global, no filas en tabla.
- Grafo no filtra por entidad seleccionada (enlace genérico al grafo del caso).

## Siguiente fase (2D)

- Persistir exclusiones del analista
- Informes PDF
- Agrupación Wayback por path en el explorador
