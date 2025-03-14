# restic-k8s: Simple Kubernetes Volume Backups with Restic

Straightforward File System Backups of Kubernetes Volumes attached to Pods. No CRDs, no daemons.
Uses restic under the hood for fast, reliable and encrypted backups that can be uploaded to a wide variety of storage providers.

This project is aimed at users who are already familiar with the Restic workflow (backup/forget/prune/check etc.).
It aims to provide a simple adapter for Restic into the Kubernetes world and expose Restic configuration options via resource annotations.

If you are not familiar with Restic, here is a quick overview highlighting the main advantages:

* Restic takes backups of the local filesystem by creating *snapshots* which are stored in a remote *repository*.
* Each snapshot is *incremental*, i.e. only differences compares to the last snapshot are uploaded and stored.
* All content stored remotely is *fully encrypted*.
* Restic uses *content-addressable storage* (CAS) to store the data in the remote repository as *blobs*.
* To delete snapshots from the remote repository, the `restic forget` command can be used to expire old snapshots. This operation only removes the reference to the *blobs* (the data making up the snapshot), but does not remove the blobs themselves.
* To delete unused blobs (data associated to deleted snapshots), the `restic prune` command is used.
* To verify that the data stored in the remote repository is correct, the `restic check` command is used. It recomputes the checksums of the blobs stored in the repository.

If you take a look at the commands implemented by the `restic-k8s` utility as well as the configuration values of the Helm chart, you will see the similarities to the typical Restic workflow.

## Status

This project is in `alpha` state.
I'm using it for daily backups of my homelab, aka. *"works on my machine"*.

Use at your own risk.

Bug reports and pull requests are welcome.

## Installation

Naturally, a Helm chart is the easiest way to deploy the required resources into a Kubernetes cluster.

### Helm

A Helm chart is available for deploying to a Kubernetes cluster.
The chart deploys:

* a `ServiceAccount` with required RBAC
* a `CronJob` for taking backups
* a `CronJob` for expiring old snapshot (`restic forget`)
* a `CronJob` for deleting old blobs (`restic prune`)

Use the following commands to get started.
You can generate a secure `RESTIC_PASSWORD` using the command `openssl rand -hex 32` .
For more information about setting up the storage backend (`RESTIC_REPOSITORY`), please refer to <https://restic.readthedocs.io/en/latest/030_preparing_a_new_repo.html>.

```sh
helm install restic-k8s oci://ghcr.io/jacksgt/restic-k8s --version 0.5.0 \
    --set restic.config.RESTIC_REPOSITORY="sftp:user@example.com:/srv/restic-repo"
    --set restic.config.RESTIC_PASSWORD="0xdeadbeef"
```


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
pip install .

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

# install base dependencies and development dependencies
pip3 install -e .[dev]
```

## Roadmap

- [x] implement cleanup (forget/prune) job
- [ ] implement check job
- [x] publish Helm chart with OCI image
- [ ] add `restic.net/` annotations on PVCs
- [ ] add more type annotations
- [ ] improve logging (debug,info,warning,error)
- [ ] setup pylint + mypy
- [x] automate building container image to GHCR
- [ ] publish prometheus metrics about repo stats and job durations
- [ ] add license
- [ ] notifications with apprise
- [ ] implement separate backup repo per pvc
- [ ] set up CI with k3s for end-to-end tests
- [ ] release v1
