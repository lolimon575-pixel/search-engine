from urllib.error import URLError

import pytest

from app.verification.engine import VerificationEngine, _RedirectRecorder


def test_redirect_recorder_rejects_private_redirect():
    engine = VerificationEngine()
    recorder = _RedirectRecorder(engine._assert_public_host)

    with pytest.raises(ValueError):
        recorder.redirect_request(
            type("Req", (), {"full_url": "https://example.com"})(),
            None,
            302,
            "Found",
            {},
            "http://127.0.0.1/admin",
        )


def test_assert_public_host_rejects_non_http_scheme():
    engine = VerificationEngine()

    with pytest.raises(ValueError, match="unsupported URL scheme"):
        engine._assert_public_host("file:///etc/passwd")
