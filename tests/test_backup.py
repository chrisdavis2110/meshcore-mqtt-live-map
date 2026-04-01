import os
import tarfile
import time

import backup


def test_create_backup_archive_writes_tar_gz(tmp_path, monkeypatch):
  state_file = tmp_path / 'state.json'
  route_file = tmp_path / 'route_history.jsonl'
  boundary_file = tmp_path / 'map_boundary.json'
  backup_dir = tmp_path / 'backup'

  state_file.write_text('{"ok":true}\n', encoding='utf-8')
  route_file.write_text('{"edge":1}\n', encoding='utf-8')
  boundary_file.write_text('{"points": []}\n', encoding='utf-8')

  monkeypatch.setattr(backup, 'BACKUP_DIR', str(backup_dir))
  monkeypatch.setattr(backup, 'STATE_FILE', str(state_file))
  monkeypatch.setattr(backup, 'DEVICE_ROLES_FILE', str(tmp_path / 'missing_roles.json'))
  monkeypatch.setattr(backup, 'DEVICE_COORDS_FILE', str(tmp_path / 'missing_coords.json'))
  monkeypatch.setattr(backup, 'NEIGHBOR_OVERRIDES_FILE', str(tmp_path / 'missing_neighbors.json'))
  monkeypatch.setattr(backup, 'CHANNEL_SECRETS_FILE', str(tmp_path / 'missing_channels.json'))
  monkeypatch.setattr(backup, 'MAP_BOUNDARY_FILE', str(boundary_file))
  monkeypatch.setattr(backup, 'ROUTE_HISTORY_FILE', str(route_file))
  monkeypatch.setattr(backup, 'COVERAGE_CACHE_FILE', str(tmp_path / 'missing_coverage.json'))
  monkeypatch.setattr(backup, 'BACKUP_RETENTION_DAYS', 7)

  archive_path = backup.create_backup_archive(now=1_774_000_000)

  assert archive_path is not None
  assert archive_path.endswith('.tar.gz')
  assert os.path.exists(archive_path)

  with tarfile.open(archive_path, 'r:gz') as tar:
    names = sorted(tar.getnames())

  assert names == ['map_boundary.json', 'route_history.jsonl', 'state.json']


def test_prune_backup_archives_removes_old_archives(tmp_path, monkeypatch):
  backup_dir = tmp_path / 'backup'
  backup_dir.mkdir()
  old_archive = backup_dir / 'meshmap-backup-old.tar.gz'
  new_archive = backup_dir / 'meshmap-backup-new.tar.gz'
  old_archive.write_bytes(b'old')
  new_archive.write_bytes(b'new')

  now = time.time()
  os.utime(old_archive, (now - (9 * 86400), now - (9 * 86400)))
  os.utime(new_archive, (now, now))

  monkeypatch.setattr(backup, 'BACKUP_DIR', str(backup_dir))
  monkeypatch.setattr(backup, 'BACKUP_RETENTION_DAYS', 7)

  removed = backup.prune_backup_archives(now=now)

  assert removed == 1
  assert not old_archive.exists()
  assert new_archive.exists()
