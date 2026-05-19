"""Target detection: table-driven units + adversarial property tests."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from globeye.core.models import TargetType
from globeye.core.target import TargetDetectionError, detect


@pytest.mark.parametrize(
    ("raw", "expected_type", "expected_value"),
    [
        ("example.com", TargetType.DOMAIN, "example.com"),
        ("https://Sub.Example.com/path?q=1", TargetType.DOMAIN, "sub.example.com"),
        ("192.0.2.10", TargetType.IP, "192.0.2.10"),
        ("2001:db8::1", TargetType.IP, "2001:db8::1"),
        ("192.0.2.0/24", TargetType.CIDR, "192.0.2.0/24"),
        ("AS64500", TargetType.ASN, "AS64500"),
        ("asn 64500", TargetType.ASN, "AS64500"),
        ("jane.doe@example.com", TargetType.EMAIL, "jane.doe@example.com"),
        ("a" * 40, TargetType.CERT_HASH, "a" * 40),
        ("DEADBEEF" * 8, TargetType.CERT_HASH, ("deadbeef" * 8)),
        ("+1 (202) 555-0143", TargetType.PHONE, "+12025550143"),
        ("jane_doe", TargetType.USERNAME, "jane_doe"),
        ("@octocat", TargetType.USERNAME, "octocat"),
        ("Jane Doe", TargetType.PERSON, "Jane Doe"),
        ("Example Corp S.L.", TargetType.ORG, "Example Corp S.L."),
    ],
)
def test_detect_known(raw, expected_type, expected_value):
    t = detect(raw)
    assert t.type is expected_type
    assert t.value == expected_value
    assert t.raw == raw


@pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
def test_detect_empty_raises(bad):
    with pytest.raises(TargetDetectionError):
        detect(bad)


@given(st.text())
def test_detect_never_crashes_on_arbitrary_text(s):
    """The detector must classify or raise cleanly — never explode."""
    try:
        result = detect(s)
    except TargetDetectionError:
        return
    assert result.type in TargetType
    assert isinstance(result.value, str)


@given(st.integers(min_value=1, max_value=4_294_967_295).map(lambda n: f"AS{n}"))
def test_asn_property(asn):
    assert detect(asn).type is TargetType.ASN
