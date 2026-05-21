"""Enrichment pipeline: offline reputation tagging + GeoIP/ASN.

Takes the deduplicated findings of a scan and annotates them in place.
Everything here is offline — no network calls.
"""

from __future__ import annotations

import ipaddress

from globeye.config import Settings
from globeye.core.models import Finding
from globeye.enrichment.geoip import GeoIPEnricher
from globeye.enrichment.reputation import assess


def finding_ip(finding: Finding) -> str | None:
    """Return the IP a finding relates to (its target or value), if any."""
    for candidate in (finding.target, finding.value.split(":")[0]):
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return None


class EnrichmentPipeline:
    """Applies offline enrichment to a batch of findings (in place)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run(self, findings: list[Finding]) -> list[Finding]:
        """Tag reputation, and GeoIP/ASN when the local databases exist."""
        geo = GeoIPEnricher(self._settings.geoip_city_db, self._settings.geoip_asn_db)
        try:
            for f in findings:
                f.normalized_data["reputation"] = assess(f)
                ip = finding_ip(f)
                if ip is None or not geo.enabled:
                    continue
                geo_data: dict[str, object] = {"ip": ip}
                if city := geo.city(ip):
                    geo_data.update(city)
                if asn := geo.asn(ip):
                    geo_data["asn"] = asn
                if len(geo_data) > 1:
                    f.normalized_data["geo"] = geo_data
        finally:
            geo.close()
        return findings
