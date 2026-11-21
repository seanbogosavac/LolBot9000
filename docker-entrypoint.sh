#!/bin/sh
# Starts as root only to fix the ownership of the data volume (volumes created by older
# images are root-owned), then drops to the unprivileged "app" user for the actual process.
set -e

if [ "$(id -u)" = "0" ]; then
    chown -R app:app /app/data
    exec setpriv --reuid=app --regid=app --init-groups "$@"
fi

exec "$@"
