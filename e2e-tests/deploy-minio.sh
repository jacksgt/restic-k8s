#!/bin/bash

set -e

helm repo add minio https://charts.min.io/
kubectl create namespace minio || true
helm upgrade --install minio -n minio -f - minio/minio <<EOF
# https://github.com/minio/minio/blob/master/helm/minio/values.yaml
rootUser: minio-admin
rootPassword: minio-hunter2
resources:
  requests:
    memory: 100Mi
replicas: 1
persistence:
  enabled: false
mode: standalone
buckets:
  - name: my-backup-bucket
    # Policy to be set on the bucket [none|download|upload|public]
    policy: none
    # Purge if bucket exists already
    purge: true
    # disable versioning
    versioning: false
    # disable objectlocking
    objectlocking: false
EOF
