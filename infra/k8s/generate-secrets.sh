#!/bin/bash
# Generate Redis password secret for miss-islington
# Run once per cluster setup
set -e

NAMESPACE="redis"
SECRET_NAME="miss-islington-password"

echo "=== Miss Islington Redis Secret ==="

if kubectl get secret -n "$NAMESPACE" "$SECRET_NAME" &>/dev/null; then
    echo "Secret '$SECRET_NAME' already exists in namespace '$NAMESPACE'."
    echo "Delete it first if you want to regenerate: kubectl delete secret -n $NAMESPACE $SECRET_NAME"
    exit 1
fi

PASSWORD=$(openssl rand -hex 24)

kubectl create secret -n "$NAMESPACE" generic "$SECRET_NAME" --from-literal=password="$PASSWORD"

echo ""
echo "Secret '$SECRET_NAME' created in namespace '$NAMESPACE'."
echo ""
echo "Redis connection URI (set as REDIS_URL in cabotage):"
echo "rediss://:${PASSWORD}@miss-islington.redis.svc.cluster.local:6379/0?ssl_ca_certs=/var/run/secrets/cabotage.io/ca.crt&ssl_cert_reqs=required"
echo ""
echo "=== Done ==="
