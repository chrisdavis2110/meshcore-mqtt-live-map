import json

import decoder


def test_load_channel_secrets_supports_named_mapping(tmp_path, monkeypatch):
  path = tmp_path / "channel_secrets.json"
  path.write_text(json.dumps({
    "Public": "8B3387E9C5CDEA6AC9E5EDBAA115CD72",
    "#chat": "D0BDD6D71538138ED979EEC00D98AD97",
  }), encoding="utf-8")
  monkeypatch.setattr(decoder, "CHANNEL_SECRETS_FILE", str(path))

  secrets = decoder._load_channel_secrets()

  assert secrets == [
    "8b3387e9c5cdea6ac9e5edbaa115cd72",
    "d0bdd6d71538138ed979eec00d98ad97",
  ]


def test_load_channel_secrets_filters_invalid_values(tmp_path, monkeypatch):
  path = tmp_path / "channel_secrets.json"
  path.write_text(json.dumps([
    "8B3387E9C5CDEA6AC9E5EDBAA115CD72",
    "8B3387E9C5CDEA6AC9E5EDBAA115CD72",
    "short",
    123,
  ]), encoding="utf-8")
  monkeypatch.setattr(decoder, "CHANNEL_SECRETS_FILE", str(path))

  secrets = decoder._load_channel_secrets()

  assert secrets == ["8b3387e9c5cdea6ac9e5edbaa115cd72"]
