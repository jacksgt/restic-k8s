#!/bin/sh

set -e

kubectl delete namespace minio --wait --ignore-not-found
