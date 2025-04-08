#!/usr/bin/env bats

load bats-support/load.bash
load bats-assert/load.bash
load bats-detik/load.bash

NAMESPACE=restic-k8s-tests
DETIK_CLIENT_NAME=kubectl

# will be run before each test case
setup() {
    true
}

# will be run at the beginning of the file (before the first test)
setup_file() {
    kubectl create namespace "${NAMESPACE}" || true
}

# will be run after each test case
teardown() {
    true
}

# will be run after all test cases in the file (after the last test)
teardown_file() {
    if [[ "$CUSTOM_BATS_SKIP_TEARDOWN" != "true" ]]; then
        kubectl delete --wait=true --ignore-not-found=true namespace "${NAMESPACE}" app-{1..3}
    fi
}

@test "Deploy Helm chart" {
    if [ -z "$IMAGE_TAG" ]; then
        echo "No IMAGE_TAG set for restic-k8s, cannot install Helm chart!" && return 1
    fi
    helm upgrade --install -n "$NAMESPACE" -f -  restic-k8s ../chart  <<EOF
image:
  tag: ${IMAGE_TAG}
restic:
  config:
    RESTIC_REPOSITORY: "s3:http://minio.minio.svc.cluster.local:9000/my-backup-bucket"
    RESTIC_PASSWORD: "foo.bar.baz"
    AWS_ACCESS_KEY_ID: "minio-admin"
    AWS_SECRET_ACCESS_KEY: "minio-hunter2"
  forget:
    keepPolicy:
      last: 1
      within: null
debugToolbox:
  enabled: true
EOF

    # smoke tests
    DETIK_CLIENT_NAMESPACE="$NAMESPACE"
    verify "there is 1 cronjob named 'restic-k8s-backup'"
    verify "'spec.jobTemplate.spec.template.spec.containers[0].image' is 'ghcr.io/jacksgt/restic-k8s:${IMAGE_TAG}' for cronjob named 'restic-k8s-backup'"

    try "at most 10 times every 5s to find 1 pods named 'restic-k8s-toolbox-.+' with 'status.phase' being 'Running'"
}

@test "Create PVCs and data" {
    for i in {1..3}; do
        APP_NAME="app-${i}"
        # create namespace, PVC and deployment
        cat "fixtures/app.yaml" | APP_NAME="${APP_NAME}" envsubst | kubectl create -f -
        # wait for the pod of the deployment to be running so we can execute commands
        # when the deployment is available, the PVC has also been provisioned
        kubectl wait --for=condition=Available=true -n "${APP_NAME}" "deployment/${APP_NAME}" --timeout=60s
        # write some data to the PVC
        cat "fixtures/index.html" | APP_NAME="${APP_NAME}" envsubst | kubectl exec -it -n "${APP_NAME}" deployment/"${APP_NAME}" -- dd of=/usr/local/apache2/htdocs/index.html
        kubectl exec -n "${APP_NAME}" "deployment/${APP_NAME}" -- dd if=/dev/random of=/usr/local/apache2/htdocs/data1.dat bs=1M count=100
     done
}

@test "Run backup job" {
    DETIK_CLIENT_NAMESPACE="$NAMESPACE"
    # start a new backup job
    kubectl -n "$NAMESPACE" create job test-backup --from=cronjob/restic-k8s-backup
    # job must be running
    try "at most 10 times every 5s to find 1 pod named 'test-backup-.+' with 'status' being 'running'"
    # wait for job to complete
    try "at most 10 times every 10s to find 1 job named 'test-backup' with '.status.succeeded' being '1'"
    # get job output
    run kubectl -n "$NAMESPACE" logs job/test-backup
    assert_success
    assert_output --partial "created restic repository"
    for i in {1..3}; do
        APP_NAME="app-${i}"
        assert_output --partial "Backing up PVC ${APP_NAME}/${APP_NAME} with 'hostPath' strategy"
        assert_output --regexp "Pod backup-${APP_NAME}-.+ terminated after .+: Succeeded"
    done
}

@test "Verify snapshots are present" {
    for i in {1..3}; do
        # make sure we have exactly one snapshot for the PVC
        APP_NAME="app-${i}"
        run kubectl -n "${NAMESPACE}" exec deploy/restic-k8s-toolbox -- restic snapshots --tag namespace=${APP_NAME},persistentvolumeclaim=${APP_NAME} --json
        assert_success
        assert [ $(echo "$output" | jq ". | length") -eq "1" ]
    done
}

@test "Add more data to PVCs" {
    for i in {1..3}; do
        APP_NAME="app-${i}"
        # write more data to the PVC
        kubectl exec -n "${APP_NAME}" "deployment/${APP_NAME}" -- cp -a /usr/share /usr/local/apache2/htdocs/
     done
}

@test "Run backup job again" {
    DETIK_CLIENT_NAMESPACE="$NAMESPACE"
    # start a new backup job
    kubectl -n "$NAMESPACE" create job test-backup-again --from=cronjob/restic-k8s-backup
    # job must be running
    try "at most 10 times every 5s to find 1 pod named 'test-backup-again-.+' with 'status' being 'running'"
    # wait for job to complete
    try "at most 10 times every 10s to find 1 job named 'test-backup-again' with '.status.succeeded' being '1'"
    # get job output
    run kubectl -n "$NAMESPACE" logs job/test-backup-again
    assert_success
    # TODO: add check that repo was detected as already initialized
    for i in {1..3}; do
        APP_NAME="app-${i}"
        assert_output --partial "Backing up PVC ${APP_NAME}/${APP_NAME} with 'hostPath' strategy"
        assert_output --regexp "Pod backup-${APP_NAME}-.+ terminated after .+: Succeeded"
    done
}

@test "Verify more snapshots are present" {
    for i in {1..3}; do
        # make sure there is more than one snapshot for the PVC
        APP_NAME="app-${i}"
        run kubectl -n "${NAMESPACE}" exec deploy/restic-k8s-toolbox -- restic snapshots --tag namespace=${APP_NAME},persistentvolumeclaim=${APP_NAME} --json
        assert_success
        assert [ $(echo "$output" | jq ". | length") -gt "1" ]
    done
}

@test "Run forget job" {
    DETIK_CLIENT_NAMESPACE="$NAMESPACE"
    # start a new backup job
    kubectl -n "$NAMESPACE" create job test-forget --from=cronjob/restic-k8s-forget
    # wait for job to complete
    try "at most 10 times every 10s to find 1 job named 'test-forget' with '.status.succeeded' being '1'"
    # get job output
    run kubectl -n "$NAMESPACE" logs job/test-forget
    assert_success
    assert_output --partial "Applying Policy: keep 1 latest snapshots"
    for i in {1..3}; do
        APP_NAME="app-${i}"
        assert_output --regexp "Pod forget-${APP_NAME}-.+ terminated after .+: Succeeded"
    done
}

@test "Verify snapshots have been removed" {
    for i in {1..3}; do
        # make sure there is exactly one snapshot for each PVC
        APP_NAME="app-${i}"
        run kubectl -n "${NAMESPACE}" exec deploy/restic-k8s-toolbox -- restic snapshots --tag namespace=${APP_NAME},persistentvolumeclaim=${APP_NAME} --json
        assert_success
        assert [ $(echo "$output" | jq ". | length") -eq "1" ]
    done
}
