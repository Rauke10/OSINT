"""``PassiveSource`` ABC — the common interface every source implements.

Implemented in Phase 2. Each source declares ``requires_api_key``,
``supported_target_types`` and ``rate_limit``, and must only contact its
allowlisted third-party host (never the target).
"""
