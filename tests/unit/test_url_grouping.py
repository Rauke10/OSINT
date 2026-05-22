"""Unit tests for Wayback URL grouping (Fase 2C.3)."""

from __future__ import annotations

from globeye.services.url_grouping import classify_wayback_url


def test_admin_login_high():
    m = classify_wayback_url("https://example.com/admin/users")
    assert m.category == "admin_login"
    assert m.priority == "high"


def test_wp_login():
    m = classify_wayback_url("https://example.com/wp-login.php")
    assert m.category in {"admin_login", "wordpress"}
    assert m.priority == "high"


def test_api_endpoint():
    m = classify_wayback_url("https://api.example.com/v1/users")
    assert m.category == "api_endpoint"
    assert m.priority == "high"


def test_backup_zip():
    m = classify_wayback_url("https://example.com/db/backup.zip")
    assert m.category == "backup_archive"
    assert m.priority == "high"


def test_document_pdf():
    m = classify_wayback_url("https://example.com/reports/file.pdf")
    assert m.category == "document"
    assert m.priority == "medium"


def test_static_png():
    m = classify_wayback_url("https://example.com/assets/logo.png")
    assert m.category == "static_asset"
    assert m.priority == "noisy"


def test_static_js_cache_bust():
    m = classify_wayback_url("https://example.com/js/main.js?v=12345")
    assert m.category in {"static_asset", "parameterized_url"}
    assert m.priority == "noisy"


def test_normal_page_low():
    m = classify_wayback_url("https://example.com/about/team")
    assert m.category == "other"
    assert m.priority == "low"


def test_document_group_keeps_distinct_paths():
    from globeye.services.url_normalization import urls_must_remain_distinct

    a = classify_wayback_url("https://example.com/documents/informe.pdf")
    b = classify_wayback_url("https://example.com/documents/contrato.pdf")
    assert a.category == "document"
    assert b.category == "document"
    assert urls_must_remain_distinct(
        "https://example.com/documents/informe.pdf",
        "https://example.com/documents/contrato.pdf",
    )


def test_group_reason_non_empty():
    from globeye.services.url_grouping import wayback_group_reason

    m = classify_wayback_url("https://example.com/wp-login.php")
    assert "login" in wayback_group_reason(m).lower() or "admin" in wayback_group_reason(m).lower()
