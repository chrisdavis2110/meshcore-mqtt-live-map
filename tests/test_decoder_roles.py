import decoder


def test_extract_device_role_ignores_model_and_origin_hints():
  payload = {
    "status": {
      "model": "PyMC-Repeater",
      "origin": "PR-Room-Server",
      "client_version": "meshcore-room/1.2.3",
      "description": "Living room node",
    }
  }

  assert decoder._extract_device_role(payload, "meshcore/BOS/test/status"
                                     ) is None


def test_extract_device_role_from_numeric_role_code_string():
  payload = {
    "payload": {
      "decoded": {
        "appData": {
          "deviceRole": "3",
        }
      }
    }
  }

  assert decoder._extract_device_role(payload, "meshcore/BOS/test/packets"
                                     ) == "room"


def test_extract_device_role_from_explicit_nested_role_field():
  payload = {
    "payload": {
      "decoded": {
        "appData": {
          "role": "repeater",
        }
      }
    }
  }

  assert decoder._extract_device_role(payload, "meshcore/BOS/test/packets"
                                     ) == "repeater"


def test_apply_meta_role_accepts_numeric_string_role_codes():
  debug = {"device_role": None}

  decoder._apply_meta_role(debug, {"deviceRole": "2"})

  assert debug["device_role"] == "repeater"
