import pytest

from restic_k8s import *
from kr8s.objects import PersistentVolumeClaim

def test_build_restic_check_cmd():
    result = build_restic_check_cmd(
        ResticCheckConfig(
            read_data_subset="99%",
        )
    )
    expected = "restic check --read-data-subset=99%"
    assert result == expected


@pytest.fixture
def example_pvc_with_various_annotations():
    return PersistentVolumeClaim(
        {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": "example",
                "namespace": "default",
                "annotations": {
                    "restic.net/backup-enabled": "true",
                    "restic.net/backup-exclude-caches": "false",
                    "restic.net/backup-excludes": "*.c",
                    "restic.net/backup-exclude-file": "excludes.txt",
                    "restic.net/tags": "foo bar baz",
                    "restic.net/forget-keep-last": "42",
                    "restic.net/forget-keep-within": "30d",
                }
            },
            "spec": {
                "accessModes": [
                    "ReadWriteMany"
                ],
                "resources": {
                    "requests": {
                        "storage": "20Gi"
                    }
                }
            }
        }
    )

_restic_forget_common_cmd = "restic forget --verbose --group-by tags,paths"
@pytest.mark.parametrize("config,example_pvc_with_various_annotations,expected_cmd", [
    (ResticForgetConfig(keep_last=42), "example_pvc_with_various_annotations", f"{_restic_forget_common_cmd} --tag namespace=default,persistentvolumeclaim=example --keep-last 42"),
    (ResticForgetConfig(keep_daily=30, keep_monthly=12, keep_yearly=3),  "example_pvc_with_various_annotations", f"{_restic_forget_common_cmd} --tag namespace=default,persistentvolumeclaim=example --keep-daily 30 --keep-monthly 12 --keep-yearly 3"),
    (ResticForgetConfig(dry_run=True, keep_within="1m15d12h"),  "example_pvc_with_various_annotations", f"{_restic_forget_common_cmd} --tag namespace=default,persistentvolumeclaim=example --dry-run --keep-within 1m15d12h"),
    ], indirect=["example_pvc_with_various_annotations"])
def test_build_restic_forget_cmd(config,example_pvc_with_various_annotations,expected_cmd):
    assert build_restic_forget_cmd(config, example_pvc_with_various_annotations) == expected_cmd


_restic_backup_common_cmd = "restic backup --one-file-system --group-by tags,paths --no-scan /data"
@pytest.mark.parametrize("config,example_pvc_with_various_annotations,expected_cmd", [
    (ResticBackupConfig(), "example_pvc_with_various_annotations", f"{_restic_backup_common_cmd}"),
    (ResticBackupConfig(dry_run=True), "example_pvc_with_various_annotations", f"{_restic_backup_common_cmd} --dry-run"),
    (ResticBackupConfig(exclude_caches=True), "example_pvc_with_various_annotations", f"{_restic_backup_common_cmd} --exclude-caches"),
    ], indirect=["example_pvc_with_various_annotations"])
def test_build_restic_backup_cmd(config,example_pvc_with_various_annotations,expected_cmd):
    assert build_restic_backup_cmd(config, example_pvc_with_various_annotations) == expected_cmd
