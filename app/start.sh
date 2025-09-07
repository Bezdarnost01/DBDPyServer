set -euo pipefail

sudo systemctl start redis-server
sudo systemctl enable redis-server

REDIS_HOST=${REDIS_HOST:-127.0.0.1}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_DB=${REDIS_DB:-0}
PREFIX=${REDIS_KEY_PREFIX:-"prod:"}
CLI="redis-cli -h $REDIS_HOST -p $REDIS_PORT -n $REDIS_DB"

LOCK_KEY="${PREFIX}startup:cleanup_lock"
LOCK=$($CLI SET "$LOCK_KEY" 1 NX EX 120)
if [[ "$LOCK" == "OK" ]]; then
  echo "[redis] cleanup ${PREFIX}* ..."
  patterns=(
    "${PREFIX}queue:*"
    "${PREFIX}lobbies:open"
    "${PREFIX}lobbies:open:z"
    "${PREFIX}lobby:*"
  )
  for pat in "${patterns[@]}"; do
    $CLI --scan --pattern "$pat" | awk '{print "DEL",$1}' | $CLI --pipe
  done
else
  echo "[redis] cleanup skipped (another instance already did it)"
fi

exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker \
  main:app --bind 0.0.0.0:443 \
  --keyfile /etc/letsencrypt/live/dbdclub.live/privkey.pem \
  --certfile /etc/letsencrypt/live/dbdclub.live/fullchain.pem
