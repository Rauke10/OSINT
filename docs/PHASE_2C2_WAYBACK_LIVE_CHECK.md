# Fase 2C.2 — Validación activa opcional de URLs Wayback

## OSINT pasivo vs validación activa

| Modo | Qué hace | Cuándo |
|------|----------|--------|
| **Pasivo (defecto)** | Solo APIs de terceros (Wayback, RDAP, …). Nunca contacta el objetivo. | Escaneos automáticos |
| **Validación activa** | HEAD/GET directo a la URL descubierta. Manual, con aviso. | Cuando el analista pulsa «Comprobar» |

Wayback devuelve URLs **históricas** archivadas. Muchas ya no existen; algunas siguen activas y son muy relevantes. La comprobación activa responde a: *¿responde hoy esta URL?*

## Qué es Wayback

Wayback Machine (Internet Archive) indexa capturas antiguas. GLOBEYE las trata como datos **históricos** (`quality_label: historical`), no como vulnerabilidades.

Texto de producto (UI):

> Wayback muestra URLs históricas archivadas. Una URL histórica puede no existir ya. Si necesitas saber si sigue viva, usa la validación activa controlada. Esta acción contacta con el servidor objetivo y debe usarse solo con autorización.

## Cuándo usar live check

- Tras un escaneo con muchas URLs Wayback, para priorizar las que **siguen respondiendo**.
- Antes de incluir una URL histórica en un informe operativo.
- **Solo** con autorización para contactar el objetivo.

**No** se ejecuta en escaneos, pivots ni en segundo plano.

## Por qué HEAD/GET y no ping

- HTTP refleja el servicio real (200, 301, 403, 404).
- HEAD evita descargar el cuerpo; si el servidor devuelve 405, se puede usar GET ligero (`fallback_get=true`).
- ICMP/ping no indica si la ruta HTTP sigue existiendo.

## Límites de seguridad

- Máximo **25 URLs** por lote (`POST /api/cases/{id}/url-checks`).
- Timeout **5 s**, sin guardar cuerpo HTML.
- Solo esquemas `http`/`https`.
- Sin crawling, fuzzing, rutas derivadas, JS ni fuerza bruta.
- User-Agent identificable (`GLOBEYE-URL-Check/...`).
- Secretos en query redactados al guardar.
- Respeta `GLOBEYE_PROXY_URL` si está configurado.

## Interpretación de estados

| Estado | Significado |
|--------|-------------|
| `not_checked` | Aún no comprobada |
| `live_200` | Responde 2xx (típ. 200) |
| `redirect` | 301/302/… (sin seguir redirección en el informe) |
| `forbidden` | 401/403 |
| `not_found` | 404 |
| `server_error` | 5xx |
| `timeout` | Timeout de red |
| `network_error` | Error de transporte |
| `invalid_url` | No es http(s) válida |

La calidad Wayback **no** pasa a «vulnerabilidad» por estar activa; solo se añade contexto en `quality_reason` / columna «Estado actual».

## API

```http
POST /api/cases/{case_id}/url-checks
GET  /api/cases/{case_id}/url-checks?status=live_200&entity_id=1&q=example
GET  /api/url-checks/{check_id}
```

Body ejemplo:

```json
{
  "urls": ["https://example.com/old-path"],
  "method": "HEAD",
  "fallback_get": true,
  "max_urls": 25
}
```

Con vínculo a entidad:

```json
{
  "entries": [
    { "url": "https://example.com/old-path", "entity_id": 42, "evidence_id": 7 }
  ]
}
```

Filtro en Data Explorer: query `live_status` en `GET /api/cases/{id}/data`.

## Cómo probar en UI

1. Crear investigación y escanear un dominio (p. ej. `example.com`).
2. **Datos encontrados** → pestaña URLs o Ruidosos/Históricos.
3. Seleccionar URLs Wayback (checkbox) → **Comprobar seleccionadas** (máx. 25).
4. O **Comprobar si sigue activa** en una fila.
5. Revisar columna **Estado actual** y filtros de comprobación activa.
6. En **Evidencias**, abrir una fila Wayback → **Comprobar URL** y ver metadatos en el detalle.

## Cómo probar en API

```bash
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"urls":["https://example.com/legacy"],"method":"HEAD"}' \
  http://localhost:8000/api/cases/1/url-checks
```

## Limitaciones

- No persiste exclusiones «marcar revisado» del analista.
- No agrupa Wayback por path.
- Una comprobación por petición manual; sin colas ni reintentos automáticos.
- El grafo no filtra por URL comprobada.
