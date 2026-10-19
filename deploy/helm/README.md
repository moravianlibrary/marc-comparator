# Helm Chart

## Prerequisites

- Kubernetes 1.26+
- Helm 3.x
- [CloudNativePG operator](https://cloudnative-pg.io/) installed in the cluster

The chart creates a `postgresql.cnpg.io/v1` `Cluster`, so the operator (and its
CRDs) must exist before installing.

## Local testing (k3d)

```bash
make helm-test   # cluster + CNPG operator + images + install, in one invocation
```

Or step by step:

```bash
make k3d-up && make k3d-load && make cnpg-install && make helm-install
```

The local cluster lives in its own kubeconfig (`.k3d-kubeconfig.yaml`), so
creating it never rewrites or switches the context of a real cluster's
kubeconfig. `cnpg-install`, `helm-install` and `helm-uninstall` use that
kubeconfig regardless of what `$KUBECONFIG` your shell has — they cannot reach a
remote cluster by accident.

To inspect the local cluster with your own `kubectl`:

```fish
set -x KUBECONFIG (make k3d-env)     # fish
```

```bash
export KUBECONFIG=$(make k3d-env)    # bash/zsh
```

Installing into a real cluster is deliberate — `ALLOW_REMOTE=1` switches these
targets back to your current context:

```bash
ALLOW_REMOTE=1 make helm-install
```

Note that `make cnpg-install` runs `kubectl apply` on the CloudNativePG release
manifest. On a cluster that already runs CNPG this **upgrades the operator** for
every database it manages — check before running it anywhere but k3d.

## Install

The examples below install into the caller's current Kubernetes context.
Check that context explicitly before running them; this workstation's default
`KUBECONFIG` can point to production. Use the local Makefile targets for k3d.

```bash
helm install marc-comparator ./deploy/helm/marc-comparator \
  --set secrets.postgresPassword=<password> \
  --set secrets.secretKey=<jwt-secret> \
  --set secrets.adminPassword=<admin-password>
```

## Enable Ollama (LLM)

```bash
helm install marc-comparator ./deploy/helm/marc-comparator \
  --set ollama.enabled=true \
  --set secrets.postgresPassword=<password> \
  --set secrets.secretKey=<jwt-secret> \
  --set secrets.adminPassword=<admin-password>
```

## Enable Ingress

```bash
helm install marc-comparator ./deploy/helm/marc-comparator \
  --set ingress.enabled=true \
  --set ingress.host=marc.example.com \
  --set ingress.className=nginx
```

## Configuration

See `values.yaml` for all available options.
