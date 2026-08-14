import config


def test_app_version_prefers_environment(monkeypatch):
  monkeypatch.setenv("APP_VERSION", " 2.0.0-test ")

  assert config._load_app_version() == "2.0.0-test"


def test_app_version_falls_back_to_file(monkeypatch, tmp_path):
  version_file = tmp_path / "VERSION.txt"
  version_file.write_text("3.0.0-test\n", encoding="utf-8")
  monkeypatch.delenv("APP_VERSION", raising=False)
  monkeypatch.setattr(
    config,
    "VERSION_FILE_CANDIDATES",
    (str(version_file), ),
  )

  assert config._load_app_version() == "3.0.0-test"


def test_app_version_defaults_to_dev(monkeypatch, tmp_path):
  monkeypatch.delenv("APP_VERSION", raising=False)
  monkeypatch.setattr(
    config,
    "VERSION_FILE_CANDIDATES",
    (str(tmp_path / "missing.txt"), ),
  )

  assert config._load_app_version() == "dev"
