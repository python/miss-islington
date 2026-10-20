# miss-islington k8s infra

Kubernetes manifests for running miss-islington on cabotage instead of Heroku.

## What's here

`redis.yaml` and `cert.yaml` provision a standalone Redis instance in the `redis` namespace using the OpsTree Redis Operator (already running cluster-wide).
The Redis CR uses `v1beta2` with `podSecurityContext.fsGroup: 1000` so the non-root Redis process can write to its persistent volume.
The cert is issued by the internal `operators-ca-issuer` ClusterIssuer, ECDSA P-256, 90-day rotation.

`ingress.yaml` goes in the `python` namespace where cabotage deploys the app. It's a standard nginx ingress with backend-protocol
HTTPS because cabotage serves on 8443/TLS behind a Service on port 443.

The Redis password lives in the `miss-islington-password` Secret in the `redis` namespace; the Redis operator reads it from there.

## Setup

Create the Redis password Secret (once per cluster):

```
kubectl create secret -n redis generic miss-islington-password --from-literal=password="$(openssl rand -hex 24)"
```

Apply the Redis CR and TLS cert:

```
kubectl apply -k infra/k8s -n redis
```

After cabotage has deployed the app and the Service exists, apply the ingress:

```
kubectl apply -f infra/k8s/ingress.yaml
```

## Cabotage env vars

Set these in the cabotage UI for the miss-islington application:

- `GH_SECRET` - GitHub webhook secret
- `GH_APP_ID` - GitHub App ID
- `GH_PRIVATE_KEY` - GitHub App private key
- `GH_AUTH` - GitHub auth token (used by the celery worker to clone cpython)
- `SENTRY_DSN` - Sentry DSN for error tracking
- `REDIS_URL` - built from the password in the `miss-islington-password` Secret, looks
 like `rediss://:<password>@miss-islington.redis.svc.cluster.local:6379/0?ssl_ca_certs=/var/run/secrets/cabotage.io/ca.crt&ssl_cert_reqs=required`
