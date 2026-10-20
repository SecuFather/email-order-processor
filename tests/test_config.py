import config


def test_config_defaults():
    assert config.DB_PATH == "threads.db"
    assert config.MY_NIP is None


def test_config_overrides(monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", "/tmp/custom.db")
    monkeypatch.setattr(config, "MY_NIP", "1234567890")
    monkeypatch.setattr(config, "PORT", 9000)

    assert config.DB_PATH == "/tmp/custom.db"
    assert config.MY_NIP == "1234567890"
    assert config.PORT == 9000
