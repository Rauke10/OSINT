# Fase 2B — Smart Source Routing

## Por qué existe

Sin enrutamiento, un escaneo consulta todas las fuentes cuyo `supported_target_types` coincide con el objetivo, aunque no aporten valor (p. ej. crt.sh para una IP). Eso genera:

- filas confusas en **Fuentes** (omitidas / no aplicables mezcladas con errores reales),
- consumo innecesario de cuota,
- peor experiencia en la UI.

El **Source Router** elige fuentes según **tipo de objetivo** y **profundidad** antes de ejecutar nada.

## Componentes

| Módulo | Rol |
|--------|-----|
| `core/source_profiles.py` | Perfiles por `TargetType`, coste, profundidades |
| `services/source_router.py` | `plan_routing()` — sin HTTP |
| `core/orchestrator.py` | `source_names` opcional para filtrar fuentes |
| `services/scan_service.py` | Escaneos de caso usan el router; legacy no |

## Profundidad

| Nivel | Comportamiento |
|-------|----------------|
| `quick` | Solo fuentes sin API key (rdap, crtsh, wayback, gravatar, username_enum). Sin pivot. |
| `standard` | Perfil completo salvo fuentes `high` (GitHub, Pastebin, DeHashed). Pivot opcional. |
| `deep` | Incluye fuentes caras y metadatos de filtraciones. Aviso de cuota en UI. |

## Matriz `target_type` → fuentes (perfil)

| Tipo | Perfil | Fuentes del perfil |
|------|--------|-------------------|
| `domain` | `domain_passive_intel` | rdap, crtsh, securitytrails, censys, shodan, virustotal, otx, wayback, hunter, github, pastebin |
| `ip` | `ip_reputation_infrastructure` | rdap, shodan, censys, virustotal, abuseipdb, otx |
| `email` | `email_identity_breach` | hibp, hunter*, dehashed†, gravatar, github†, pastebin† |
| `username` | `username_social` | username_enum, github†, dehashed†, pastebin† |
| `phone` | `phone_lookup` | *(ninguna en 2B)* |
| `person` | `person_sensitive` | *(ninguna en 2B)* |
| `org` | `organization_public` | github† |
| `asn` | `asn_infrastructure` | rdap, shodan, censys |
| `cidr` | `cidr_limited` | *(escaneo masivo deshabilitado)* |
| `cert_hash` | `cert_fingerprint` | censys, virustotal, crtsh* |

\* *hunter* en email: no compatible técnicamente → `not_applicable`.
† Solo en profundidad `deep` (coste alto).

## Endpoint de previsualización

```http
POST /api/source-routing/preview
Content-Type: application/json
X-API-Key: …

{"target": "8.8.8.8", "depth": "standard"}
```

Respuesta: `target_type`, `normalized_value`, `profile`, `will_run`, `skipped_missing_key`, `not_applicable`, `warnings`.

## Escaneo de caso

```http
POST /api/cases/{id}/scans
{"target": "example.com", "depth": "standard", "pivot": false}
```

- Solo se ejecutan fuentes en `will_run`.
- `skipped_missing_key` se persiste como `SourceResult` con estado `missing_key`.
- `not_applicable` **no** se guarda en SQLite (solo en `routing` del JSON de respuesta / informe).

## Legacy

`POST /api/scan` sigue usando el orchestrator sin filtro de perfiles (compatibilidad con tests y contrato histórico).

## Cómo probar

```bash
# Preview
curl -s -H "X-API-Key: $KEY" -X POST /api/source-routing/preview \
  -d '{"target":"8.8.8.8","depth":"standard"}' | jq .

# Caso + escaneo
curl -s -H "X-API-Key: $KEY" -X POST /api/cases/1/scans \
  -d '{"target":"example.com","depth":"quick"}' | jq .routing
```

En la UI: **Escanear objetivo** → escribe el target → previsualización automática → elige profundidad → escanear.

## Evitar consumo de cuota

1. Usar `quick` para reconocimiento inicial.
2. Revisar el preview antes de `deep`.
3. Configurar solo las API keys que necesitas en `.env`.
4. Las fuentes `not_applicable` nunca se llaman.

## Calidad de hallazgos (2B.1)

Tras el escaneo de caso, cada finding incluye `normalized_data.quality`.
Ver [PHASE_2B1_QUALITY_VALIDATION.md](PHASE_2B1_QUALITY_VALIDATION.md) y validación de routing en [PHASE_2B_ROUTING_VALIDATION.md](PHASE_2B_ROUTING_VALIDATION.md).

## Limitaciones (2B)

- Teléfono, persona y CIDR: sin fuentes ejecutables.
- `cert_hash`: perfil definido; fuentes aún no implementan ese tipo en `PassiveSource`.
- Sin override manual para forzar fuentes no aplicables.
- Sin pantalla de settings (metadatos `cost_level` / `enabled` preparados en código).

## Fase 2C+

- Informes PDF, OpenCorporates, documentos públicos, Twilio/numverify, override auditado, persistir `routing` en `scan_job`.
