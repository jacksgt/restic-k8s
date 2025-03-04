# restic-k8s: Simple Kubernetes Volume Backups with Restic

Straightforward File System Backups of Kubernetes Volumes attached to Pods. No CRDs, no daemons.
Uses restic under the hood for fast, reliable and encrypted backups that can be uploaded to a wide variety of storage providers.

This project is aimed at users who are already familiar with the Restic workflow (backup/forget/prune/check etc.).
It aims to provide a simple adapter for Restic into the Kubernetes world and expose Restic configuration options via resource annotations.

## Status

This project is in `alpha` state.
I'm using it for daily backups of my homelab.
Use at your own risk.

## Installation

Naturally, a Helm chart is the easiest way to deploy the required resources into a Kubernetes cluster.
The Helm chart deploys:

* a `ServiceAccount` with required RBAC
* a `CronJob` for taking backups
* a `CronJob `

### Helm

A Helm chart is available for deploying the tool with a `CronJob` into a Kubernetes cluster.

TODO: publish as OCI image

### Local

Due to its simplicity `restic-k8s` can be run locally easily.
Checkout this repository, install the Python dependencies and you can start the first backup as follows:

```sh
# get source code
git clone https://github.com/jacksgt/restic-k8s.git
cd restic-k8s

# install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt

# provide k8s cluster connection details
export KUBECONFIG=...

# provide backup storage details
kubectl create namespace restic-k8s
kubectl -n restic-k8s create secret generic restic-k8s-credentials \
    --from-literal=RESTIC_PASSWORD=hunter.2 \
    --from-literal=RESTIC_REPOSITORY=b2:my-bucket

# take backups!
./restic-k8s.py backup --pvc-label-selector app=frontend --dry-run
```

## Set up backup storage backend

TODO: https://restic.readthedocs.io/en/latest/030_preparing_a_new_repo.html

## FAQ

## How does it work?

The `restic-k8s.py` Python tool implements all the application logic:

* discovers of PVCs in the Kubernetes cluster
* determines backup strategy for each PVC (depending on the type of PVC, a different mount strategy needs to be used)
* spawns pods to take backups of each PVC with [restic](https://github.com/restic/restic/)
* monitors the pod and reports on its status

### How to disable/pause backups?

A particular volume can be excluded from being backed up by adding the `backup-enabled: "false"` annotation, like this:

```sh
kubectl annotate pvc/<NAME> backup-enabled=false
```

### How do I restore data?

There are no automatic restore procedures.
Copy the environment variables from the `restic-k8s-credentials` secret and export them in your local shell session.
Then, `restic` CLI can be used to restore the data locally: <https://restic.readthedocs.io/en/latest/050_restore.html>

### What does `Exception: Unable to determine backup strategy for PVC namespace/name` mean?

Most likely this means that this PVC is backed by a CSI driver and the volume is currently not mounted on any node. To resolve the issue, spin up a simple pod that uses the PVC, which will force the kubelet to mount the volume on one node.

## Development

Set up development environment:

```sh
python3 -m venv venv

source venv/bin/activate
# for Fish shell, use instead:
source venv/bin/activate.fish

python3 -m ensurepip

pip3 install -r requirements.txt
```

## Roadmap

- [x] implement cleanup (forget/prune) job
- [ ] implement check job
- [ ] publish Helm chart with OCI image
- [ ] add more type annotations
- [ ] improve logging (debug,info,warning,error)
- [ ] setup pylint + mypy
- [ ] automate building container image to GHCR
- [ ] publish prometheus metrics about repo stats and job durations
- [ ] add license
- [ ] notifications with apprise
- [ ] implement separate backup repo per pvc
- [ ] release v1
