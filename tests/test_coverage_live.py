import asyncio
import os

import pytest

import app


LEGACY_COVERAGE_URL_ENV = "TEST_LEGACY_COVERAGE_URL"
MESHMAPPER_COVERAGE_URL_ENV = "TEST_MESHMAPPER_COVERAGE_URL"
MESHMAPPER_COVERAGE_KEY_ENV = "TEST_MESHMAPPER_COVERAGE_KEY"


def test_live_legacy_coverage_map():
  coverage_url = os.getenv(LEGACY_COVERAGE_URL_ENV, "").strip()
  if not coverage_url:
    pytest.skip(f"{LEGACY_COVERAGE_URL_ENV} is not set")

  samples, provider = asyncio.run(
    app._fetch_coverage_upstream_for_test(coverage_url, "")
  )

  assert provider == "legacy"
  assert isinstance(samples, list)
  assert len(samples) > 0
  first = samples[0]
  assert isinstance(first, dict)
  assert any(key in first for key in ("hash", "name", "id"))


def test_live_meshmapper_coverage_map():
  coverage_url = os.getenv(MESHMAPPER_COVERAGE_URL_ENV, "").strip()
  api_key = os.getenv(MESHMAPPER_COVERAGE_KEY_ENV, "").strip()
  if not coverage_url:
    pytest.skip(f"{MESHMAPPER_COVERAGE_URL_ENV} is not set")
  if not api_key:
    pytest.skip(f"{MESHMAPPER_COVERAGE_KEY_ENV} is not set")

  samples, provider = asyncio.run(
    app._fetch_coverage_upstream_for_test(coverage_url, api_key)
  )

  assert provider == "meshmapper"
  assert isinstance(samples, list)
  assert len(samples) > 0
  first = samples[0]
  assert isinstance(first, dict)
  assert "bounds" in first
  assert "fill_color" in first
