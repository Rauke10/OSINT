from globeye.utils.redact import mask_secret


def test_mask_secret_shows_tail_only():
    assert mask_secret("abcdefghijklmnop") == "****mnop"
