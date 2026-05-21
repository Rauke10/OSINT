"""Offline GeoIP / ASN enrichment via MaxMind GeoLite2 databases.

Strictly offline: it reads local ``.mmdb`` files only. If the databases are
not configured (``GLOBEYE_GEOIP_CITY_DB`` / ``GLOBEYE_GEOIP_ASN_DB``) the
enricher is a no-op — it never performs network lookups.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # pragma: no cover - import guard
    import geoip2.database
    import geoip2.errors
    import maxminddb.errors

    _HAVE_GEOIP2 = True
except ImportError:  # pragma: no cover
    _HAVE_GEOIP2 = False

# Concrete lookup failures: address not in the DB, a corrupt DB, or a bad IP.
_LOOKUP_ERRORS: tuple[type[Exception], ...] = (
    (geoip2.errors.GeoIP2Error, maxminddb.errors.InvalidDatabaseError, ValueError)
    if _HAVE_GEOIP2
    else (ValueError,)
)


class GeoIPEnricher:
    """Lazy, offline GeoLite2 City + ASN reader."""

    def __init__(self, city_db: str | None, asn_db: str | None) -> None:
        self._city_path = city_db
        self._asn_path = asn_db
        self._city: Any | None = None
        self._asn: Any | None = None

    @property
    def enabled(self) -> bool:
        return _HAVE_GEOIP2 and bool(self._city_path or self._asn_path)

    def _reader(self, path: str | None, cached: Any | None) -> Any | None:
        if cached is not None or not path or not _HAVE_GEOIP2:
            return cached
        if not Path(path).is_file():
            return None
        return geoip2.database.Reader(path)

    def city(self, ip: str) -> dict[str, Any] | None:
        self._city = self._reader(self._city_path, self._city)
        if self._city is None:
            return None
        try:
            r = self._city.city(ip)
        except _LOOKUP_ERRORS:
            return None
        return {
            "country": r.country.iso_code,
            "city": r.city.name,
            "latitude": r.location.latitude,
            "longitude": r.location.longitude,
        }

    def asn(self, ip: str) -> dict[str, Any] | None:
        self._asn = self._reader(self._asn_path, self._asn)
        if self._asn is None:
            return None
        try:
            r = self._asn.asn(ip)
        except _LOOKUP_ERRORS:
            return None
        return {
            "asn": r.autonomous_system_number,
            "org": r.autonomous_system_organization,
        }

    def close(self) -> None:
        for reader in (self._city, self._asn):
            if reader is not None:
                reader.close()
        self._city = self._asn = None
