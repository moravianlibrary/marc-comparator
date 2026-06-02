# Helm Chart

## Prerequisites

- Kubernetes 1.26+
- Helm 3.x
- [CloudNativePG operator](https://cloudnative-pg.io/) installed in the cluster

## Install

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
