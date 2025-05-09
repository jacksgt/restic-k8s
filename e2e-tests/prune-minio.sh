$!/bin/sh

kubectl -n minio rollout restart deploy/minio
