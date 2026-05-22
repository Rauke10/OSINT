"""URL normalization safety (Fase 2C.4)."""

from __future__ import annotations

from globeye.services.url_normalization import (
    normalize_url_for_entity,
    urls_are_equivalent,
    urls_must_remain_distinct,
)


def test_distinct_pdf_paths_not_merged():
    a = normalize_url_for_entity("https://example.com/uploads/a.pdf")
    b = normalize_url_for_entity("https://example.com/uploads/b.pdf")
    assert a.normalized_value != b.normalized_value
    assert urls_must_remain_distinct(a.original_value, b.original_value)


def test_distinct_year_paths_not_merged():
    a = "https://example.com/uploads/2021/a.pdf"
    b = "https://example.com/uploads/2022/a.pdf"
    assert urls_must_remain_distinct(a, b)


def test_distinct_api_endpoints_not_merged():
    assert urls_must_remain_distinct(
        "https://example.com/api/users", "https://example.com/api/orders"
    )


def test_distinct_subdirs_not_merged():
    assert urls_must_remain_distinct(
        "https://example.com/wp-content/uploads/2021/file1.jpg",
        "https://example.com/wp-content/uploads/2021/file2.jpg",
    )


def test_login_trailing_slash_equivalent():
    a = "https://example.com/login"
    b = "https://example.com/login/"
    assert urls_are_equivalent(a, b)
    assert not urls_must_remain_distinct(a, b)


def test_http_https_equivalent_canonical():
    a = "http://example.com/wp-login.php"
    b = "https://example.com/wp-login.php"
    assert urls_are_equivalent(a, b)


def test_tracking_stripped_keeps_original_in_result():
    raw = "https://example.com/page?utm_source=x&id=1"
    n = normalize_url_for_entity(raw)
    assert "utm_source" not in n.normalized_value
    assert "id=1" in n.normalized_value
    assert n.original_value == raw
    assert n.is_normalized_variant
    assert "utm_source" in n.stripped_tracking_params


def test_host_lowercased_path_preserved():
    n = normalize_url_for_entity("HTTPS://EXAMPLE.COM/Uploads/File.PDF")
    assert "example.com" in n.normalized_value
    assert "/Uploads/File.PDF" in n.normalized_value
