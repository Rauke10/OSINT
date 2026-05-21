"""Target detection: table-driven units + adversarial property tests."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from globeye.core.models import TargetType
from globeye.core.target import _EMAIL_RE, TargetDetectionError, detect


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


@given(st.ip_addresses())
def test_any_valid_ip_is_detected_as_ip(addr):
    """Property: every valid IPv4/IPv6 address classifies as TargetType.IP."""
    assert detect(str(addr)).type is TargetType.IP


@given(st.from_regex(_EMAIL_RE, fullmatch=True))
def test_any_valid_email_is_detected_as_email(email):
    """Property: every string matching the email regex classifies as EMAIL."""
    assert detect(email).type is TargetType.EMAIL


@given(st.from_regex(r"[ \t\n\r\f\v]*", fullmatch=True))
def test_blank_input_always_raises(blank):
    """Property: empty / whitespace-only input is rejected, never classified."""
    with pytest.raises(TargetDetectionError):
        detect(blank)


# Adversarial code points (built via chr() to keep the source pure ASCII):
# zero-width space, LTR/RTL marks, BOM, and Cyrillic homoglyphs of a/e/o.
_ADVERSARIAL_CHARS = [
    chr(0x200B),
    chr(0x200E),
    chr(0x202E),
    chr(0xFEFF),
    " ",
    chr(0x0430),
    chr(0x0435),
    chr(0x043E),
    "x",
    ".",
]


@given(st.text(alphabet=st.sampled_from(_ADVERSARIAL_CHARS), min_size=1))
def test_adversarial_unicode_never_crashes(s):
    """Property: zero-width / RTL / homoglyph input classifies or raises cleanly."""
    try:
        result = detect(s)
    except TargetDetectionError:
        return
    assert result.type in TargetType
    assert isinstance(result.value, str)
