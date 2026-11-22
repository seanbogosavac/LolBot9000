from lolbot.version import version_string


def test_version_defaults_to_dev(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("APP_COMMIT", raising=False)
    assert version_string() == "dev"


def test_version_includes_short_commit(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.4.2")
    monkeypatch.setenv("APP_COMMIT", "a1b2c3d4e5f6")
    assert version_string() == "1.4.2 (a1b2c3d)"
