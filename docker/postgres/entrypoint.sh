#!/bin/bash
# Custom postgres entrypoint:
#   - On start : restores the latest dump from $DUMPS_DIR (if any)
#   - On SIGTERM: creates a new dump before letting postgres shut down

set -e

DUMPS_DIR="${DUMPS_DIR:-/dumps}"
mkdir -p "$DUMPS_DIR"

# ── Restore ───────────────────────────────────────────────────────────────────
LATEST_DUMP=$(ls -t "$DUMPS_DIR"/*.sql 2>/dev/null | head -1)

if [ -n "$LATEST_DUMP" ]; then
    echo "[dump-postgres] Restore: $(basename "$LATEST_DUMP")"
    # This script is picked up by the official postgres entrypoint
    # and executed once the empty data directory has been initialised.
    cat > /docker-entrypoint-initdb.d/00-restore.sh <<RESTORE
#!/bin/bash
echo "[dump-postgres] Loading $(basename "$LATEST_DUMP")..."
psql -v ON_ERROR_STOP=0 -U "\$POSTGRES_USER" -d "\$POSTGRES_DB" < "$LATEST_DUMP" \
    && echo "[dump-postgres] Restore complete." \
    || echo "[dump-postgres] Restore finished with warnings (usually harmless)."
RESTORE
    chmod +x /docker-entrypoint-initdb.d/00-restore.sh
else
    echo "[dump-postgres] No dump found — starting with empty database."
fi

# ── Dump on shutdown ──────────────────────────────────────────────────────────
_dump_and_exit() {
    echo "[dump-postgres] Shutdown — saving dump..."
    local dump_file="$DUMPS_DIR/dump_$(date +%Y%m%d_%H%M%S).sql"

    # Give postgres a moment if it is still initialising
    local tries=20
    while ! pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q 2>/dev/null; do
        sleep 1
        tries=$((tries - 1))
        [ $tries -le 0 ] && break
    done

    if pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q 2>/dev/null; then
        pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$dump_file" 2>/dev/null
        if [ $? -eq 0 ] && [ -s "$dump_file" ]; then
            echo "[dump-postgres] Saved: $(basename "$dump_file")"
            # Keep only the 5 most recent dumps
            ls -t "$DUMPS_DIR"/*.sql 2>/dev/null | tail -n +6 | xargs -r rm -f
        else
            rm -f "$dump_file"
            echo "[dump-postgres] Nothing to dump (empty database)."
        fi
    else
        rm -f "$dump_file" 2>/dev/null
        echo "[dump-postgres] Database unreachable — dump skipped."
    fi

    kill -SIGTERM "$PG_PID" 2>/dev/null
    wait "$PG_PID" 2>/dev/null
    exit 0
}

# ── Start postgres ────────────────────────────────────────────────────────────
docker-entrypoint.sh postgres "$@" &
PG_PID=$!

trap _dump_and_exit SIGTERM SIGINT SIGQUIT

wait "$PG_PID"
