import decoder


def test_extract_device_role_from_nested_model_hint():
  payload = {
    "status": {
      "model": "PyMC-Repeater",
    }
  }

  assert decoder._extract_device_role(payload, "meshcore/BOS/test/status"
                                     ) == "repeater"


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


def test_apply_meta_role_accepts_numeric_string_role_codes():
  debug = {"device_role": None}

  decoder._apply_meta_role(debug, {"deviceRole": "2"})

  assert debug["device_role"] == "repeater"
