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

@pytest.fixture
def example_pvcs():
    return [
    # this PVC should be excluded because it's not ready (Pending)
    PersistentVolumeClaim({
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "creationTimestamp": "2025-04-01T15:44:18Z",
            "finalizers": [
                "kubernetes.io/pvc-protection"
            ],
            "labels": {
                "app": "minio",
                "release": "minio"
            },
            "name": "pvc-not-ready",
            "namespace": "minio",
            "resourceVersion": "16882",
            "uid": "0bc47a1b-5b1b-45f7-97d6-08cf75440890"
        },
        "spec": {
            "accessModes": [
                "ReadWriteOnce"
            ],
            "resources": {
                "requests": {
                    "storage": "500Gi"
                }
            },
            "storageClassName": "standard",
            "volumeMode": "Filesystem"
        },
        "status": {
            "phase": "Pending"
        }
    }),
    # this PVC should be excluded because it's not ready (no status)
    PersistentVolumeClaim({
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "creationTimestamp": "2025-04-01T15:44:18Z",
            "finalizers": [
                "kubernetes.io/pvc-protection"
            ],
            "labels": {
                "app": "minio",
                "release": "minio"
            },
            "name": "pvc-no-status",
            "namespace": "minio",
            "resourceVersion": "16882",
            "uid": "0bc47a1b-5b1b-45f7-97d6-08cf75440890"
        },
        "spec": {
            "accessModes": [
                "ReadWriteOnce"
            ],
            "resources": {
                "requests": {
                    "storage": "500Gi"
                }
            },
            "storageClassName": "standard",
            "volumeMode": "Filesystem"
        },
        "status": {}
    }),
    # this PVC should be excluded because it's terminating
    PersistentVolumeClaim({
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "creationTimestamp": "2025-04-01T15:44:18Z",
            "deletionTimestamp": "2025-04-01T15:50:00Z",
            "finalizers": [
                "kubernetes.io/pvc-protection"
            ],
            "labels": {
                "app": "minio",
                "release": "minio"
            },
            "name": "pvc-terminating",
            "namespace": "minio",
            "resourceVersion": "16882",
            "uid": "0bc47a1b-5b1b-45f7-97d6-08cf75440890"
        },
        "spec": {
            "accessModes": [
                "ReadWriteOnce"
            ],
            "resources": {
                "requests": {
                    "storage": "500Gi"
                }
            },
            "storageClassName": "standard",
            "volumeMode": "Filesystem"
        },
        "status": {
            "phase": "Pending"
        }
    }),
    # this PVC should be included
    PersistentVolumeClaim({
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "creationTimestamp": "2025-04-01T15:44:18Z",
            "finalizers": [
                "kubernetes.io/pvc-protection"
            ],
            "name": "pvc-ok",
            "namespace": "minio",
            "resourceVersion": "16882",
            "uid": "0bc47a1b-5b1b-45f7-97d6-08cf75440890"
        },
        "spec": {
            "accessModes": [
                "ReadWriteOnce"
            ],
            "resources": {
                "requests": {
                    "storage": "1Gi"
                }
            },
            "storageClassName": "standard",
            "volumeMode": "Filesystem",
            "volumeName": "pvc-a8370b0e-d199-46a8-8908-da459b901eb3"
        },
        "status": {
            "phase": "Bound",
            "accessModes": ["ReadWriteOnce"],
            "capacity": {
                "storage": "1Gi",
            },
        }
    }),
    # this PVC should be excluded because backups are disabled for it
    PersistentVolumeClaim({
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "creationTimestamp": "2025-04-01T15:44:18Z",
            "finalizers": [
                "kubernetes.io/pvc-protection"
            ],
            "annotations": {
                "restic.net/backup-enabled": "false",
            },
            "name": "pvc-no-backup",
            "namespace": "minio",
            "resourceVersion": "16882",
            "uid": "0bc47a1b-5b1b-45f7-97d6-08cf75440890"
        },
        "spec": {
            "accessModes": [
                "ReadWriteOnce"
            ],
            "resources": {
                "requests": {
                    "storage": "1Gi"
                }
            },
            "storageClassName": "standard",
            "volumeMode": "Filesystem",
            "volumeName": "pvc-a8370b0e-d199-46a8-8908-da459b901eb3"
        },
        "status": {
            "phase": "Bound",
            "accessModes": ["ReadWriteOnce"],
            "capacity": {
                "storage": "1Gi",
            },
        }
    }),
]

def test_filter_pvcs(example_pvcs):
    result = list(filter_pvcs(example_pvcs))
    assert len(result) == 1
    assert result[0].metadata.name != "pvc-not-bound"
    assert result[0].metadata.name != "pvc-no-status"
    assert result[0].metadata.name != "pvc-terminating"
    assert result[0].metadata.name != "pvc-no-backup"
    assert result[0].metadata.name == "pvc-ok"
