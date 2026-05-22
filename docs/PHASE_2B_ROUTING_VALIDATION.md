# Fase 2B — Validación de routing (targets reales)

Documento generado tras implementar Smart Source Routing.
Regenerar preview: `uv run python scripts/validate_routing.py`

## Resumen ejecutivo

| Target | Tipo | Perfil | will_run (standard) | Notas |
|--------|------|--------|---------------------|-------|
| 8.8.8.8 | ip | ip_reputation_infrastructure | rdap, shodan, censys, virustotal, abuseipdb, otx* | crt.sh/hunter no aplicables |
| 1.1.1.1 | ip | ip_reputation_infrastructure | igual que 8.8.8.8 | |
| example.com | domain | domain_passive_intel | rdap, crtsh, censys, shodan, virustotal, otx, wayback, hunter | securitytrails si falta key → skipped |
| github.com | domain | domain_passive_intel | igual perfil dominio | Más subdominios / ruido CT posible |
| wikipedia.org | domain | domain_passive_intel | igual | Wayback puede devolver muchas URLs |
| ecix.tech | domain | domain_passive_intel | igual | Dominio real del operador |
| test@example.com | email | email_identity_breach | hibp, gravatar; hunter N/A | dehashed/github solo en `deep` |
| github | username | username_social | username_enum (+ deep: github, dehashed) | |
| +34600111222 | phone | phone_lookup | ninguna | Warning: sin fuentes teléfono |
| Juan Pérez García | person | person_sensitive | ninguna | Warning: tipo sensible |

\* OTX aparece en `will_run` si `GLOBEYE_OTX_API_KEY` está configurada; si no, en `skipped_missing_key`.

## Profundidad `quick`

| Target | will_run típico |
|--------|-----------------|
| example.com | rdap, crtsh, wayback |
| 8.8.8.8 | rdap |
| test@example.com | gravatar |

Sin pivot. Sin fuentes `high` (GitHub, Pastebin, DeHashed).

## Profundidad `deep`

Añade github, pastebin, dehashed (si hay credenciales). Muestra aviso de cuota en UI.

## Validación de escaneo (caso)

Tras `POST /api/cases/{id}/scans`:

1. Solo se persisten `SourceResult` de fuentes en `will_run` + `skipped_missing_key`.
2. `not_applicable` no se guardan en SQLite (solo en `routing` del JSON de respuesta).
3. Respuesta incluye bloque `routing` para auditoría.

### Ejemplo dominio (tests / mocks)

- Fuentes ejecutadas: crtsh, rdap, otx, wayback (según mocks).
- Findings: subdominios CT (`api.example.com`).
- Entidades: dominio raíz + subdominios (no cada URL Wayback masiva tras 2B.1).

### Ejemplo IP 8.8.8.8 (`quick`)

- will_run: rdap (keyless).
- Sin crt.sh en tabla de fuentes.
- Findings: registro RDAP si la red responde.

## Consumo de cuota

| Fuente | Riesgo cuota | Observación en entorno de prueba |
|--------|--------------|----------------------------------|
| shodan | medio | Probe OK con clave válida |
| virustotal | bajo/medio | 401 si clave inválida — no consume datos útiles |
| censys | medio | 401 si PAT mal partido |
| abuseipdb | bajo | 401 si clave inválida |
| hunter | medio | 401 en dominio de prueba |
| otx | bajo | Probe puede devolver cientos de passive DNS (ruido) |
| wayback | bajo | Timeout ocasional; sin API key |
| crt.sh | bajo | Keyless; a veces lento |

## Fuentes que más ruido generan

1. **wayback** — hasta 200 URLs CDX; UI muestra 50 + resumen.
2. **otx** — passive DNS masivo en dominios populares.
3. **github / pastebin** (deep) — coincidencias textuales débiles.

## Cómo reproducir

```bash
# Preview sin escanear
uv run python scripts/validate_routing.py --depth standard

# Diagnóstico API (máscara ****abcd)
uv run python scripts/diagnose_sources.py --probe

# Escaneo de caso
curl -H "X-API-Key: $KEY" -X POST /api/cases/1/scans \
  -d '{"target":"example.com","depth":"standard"}' | jq '.routing,.summary'
```

## Limitaciones

- `cert_hash`, `cidr`, `person`, `phone`: sin fuentes ejecutables en 2B.
- Legacy `POST /api/scan` no usa perfiles (compatibilidad tests).
