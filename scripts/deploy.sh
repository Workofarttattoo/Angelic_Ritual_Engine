#!/usr/bin/env bash
# ── Agentic Ritual Engine – Production Deploy Script ───────────────────
#
# Usage:
#   ./scripts/deploy.sh              # full deploy (build + up)
#   ./scripts/deploy.sh --build-only # just build images
#   ./scripts/deploy.sh --restart    # restart without rebuild
#
# Requires: docker, docker compose
# ───────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# ── Colour helpers ─────────────────────────────────────────────────────
info()  { printf "\033[36m[deploy]\033[0m %s\n" "$*"; }
ok()    { printf "\033[32m[deploy]\033[0m %s\n" "$*"; }
err()   { printf "\033[31m[deploy]\033[0m %s\n" "$*" >&2; }

# ── Pre-flight checks ─────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    err "Docker is not installed or not in PATH."
    exit 1
fi

if ! docker compose version &>/dev/null; then
    err "Docker Compose v2 plugin is required."
    exit 1
fi

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        info "No .env found — copying .env.example → .env"
        cp .env.example .env
    else
        err "No .env or .env.example found. Create one before deploying."
        exit 1
    fi
fi

# ── Parse arguments ───────────────────────────────────────────────────
MODE="full"
for arg in "$@"; do
    case "$arg" in
        --build-only) MODE="build" ;;
        --restart)    MODE="restart" ;;
        --help|-h)
            echo "Usage: $0 [--build-only|--restart|--help]"
            exit 0
            ;;
        *)
            err "Unknown option: $arg"
            exit 1
            ;;
    esac
done

# ── Deploy ─────────────────────────────────────────────────────────────
case "$MODE" in
    build)
        info "Building images…"
        docker compose build
        ok "Build complete."
        ;;
    restart)
        info "Restarting services…"
        docker compose restart
        ok "Services restarted."
        ;;
    full)
        info "Pulling latest code on current branch…"
        git pull --ff-only 2>/dev/null || info "Git pull skipped (not a git repo or no remote)."

        info "Building and starting services…"
        docker compose up -d --build --remove-orphans

        info "Waiting for API health check…"
        for i in $(seq 1 30); do
            if docker compose exec -T api curl -sf http://localhost:8000/health >/dev/null 2>&1; then
                ok "API is healthy."
                break
            fi
            if [ "$i" -eq 30 ]; then
                err "API did not become healthy within 30 seconds."
                docker compose logs --tail=30 api
                exit 1
            fi
            sleep 1
        done

        ok "Deploy complete. Services running:"
        docker compose ps
        ;;
esac
