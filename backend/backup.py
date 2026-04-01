import asyncio
import os
import tarfile
import tempfile
import time
from datetime import datetime
from typing import List

from config import (
  APP_VERSION,
  BACKUP_ENABLED,
  BACKUP_INTERVAL_SECONDS,
  BACKUP_DIR,
  BACKUP_RETENTION_DAYS,
  CHANNEL_SECRETS_FILE,
  COVERAGE_CACHE_FILE,
  DEVICE_COORDS_FILE,
  DEVICE_ROLES_FILE,
  MAP_BOUNDARY_FILE,
  NEIGHBOR_OVERRIDES_FILE,
  ROUTE_HISTORY_FILE,
  STATE_FILE,
)


BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M-%S"


def _backup_targets() -> List[str]:
  ordered = [
    STATE_FILE,
    DEVICE_ROLES_FILE,
    DEVICE_COORDS_FILE,
    NEIGHBOR_OVERRIDES_FILE,
    CHANNEL_SECRETS_FILE,
    MAP_BOUNDARY_FILE,
    ROUTE_HISTORY_FILE,
    COVERAGE_CACHE_FILE,
  ]
  seen = set()
  result: List[str] = []
  for path in ordered:
    normalized = (path or "").strip()
    if not normalized or normalized in seen:
      continue
    seen.add(normalized)
    result.append(normalized)
  return result


def _existing_backup_targets() -> List[str]:
  return [path for path in _backup_targets() if os.path.exists(path)]


def _backup_filename(now: float | None = None) -> str:
  ts = datetime.fromtimestamp(now or time.time()).strftime(BACKUP_TIMESTAMP_FORMAT)
  return f"meshmap-backup-{ts}.tar.gz"


def prune_backup_archives(now: float | None = None) -> int:
  if BACKUP_RETENTION_DAYS <= 0:
    return 0
  backup_dir = (BACKUP_DIR or "").strip()
  if not backup_dir or not os.path.isdir(backup_dir):
    return 0
  cutoff = (now or time.time()) - (float(BACKUP_RETENTION_DAYS) * 86400.0)
  removed = 0
  for name in os.listdir(backup_dir):
    if not name.endswith('.tar.gz'):
      continue
    path = os.path.join(backup_dir, name)
    try:
      if os.path.getmtime(path) < cutoff:
        os.remove(path)
        removed += 1
    except OSError:
      continue
  return removed


def create_backup_archive(now: float | None = None) -> str | None:
  backup_dir = (BACKUP_DIR or "").strip()
  if not backup_dir:
    return None
  os.makedirs(backup_dir, exist_ok=True)
  existing = _existing_backup_targets()
  if not existing:
    print("[backup] skipped; no backup target files exist")
    return None

  archive_name = _backup_filename(now)
  final_path = os.path.join(backup_dir, archive_name)
  fd, tmp_path = tempfile.mkstemp(prefix="meshmap-backup-", suffix=".tar.gz.tmp", dir=backup_dir)
  os.close(fd)
  try:
    with tarfile.open(tmp_path, mode="w:gz") as tar:
      for path in existing:
        tar.add(path, arcname=os.path.basename(path), recursive=False)
    os.replace(tmp_path, final_path)
  finally:
    if os.path.exists(tmp_path):
      try:
        os.remove(tmp_path)
      except OSError:
        pass

  removed = prune_backup_archives(now=now)
  print(
    f"[backup] wrote {final_path} files={len(existing)} version={APP_VERSION} pruned={removed}"
  )
  return final_path


async def _backup_loop() -> None:
  if not BACKUP_ENABLED:
    return
  interval = max(60, int(BACKUP_INTERVAL_SECONDS))
  try:
    create_backup_archive()
  except Exception as exc:
    print(f"[backup] initial backup failed: {exc}")
  while True:
    await asyncio.sleep(interval)
    try:
      create_backup_archive()
    except Exception as exc:
      print(f"[backup] periodic backup failed: {exc}")
