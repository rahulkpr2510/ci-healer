#!/usr/bin/env bash
# backend/scripts/migrate.sh
#
# Run Alembic migrations in production (CI/CD or manual).
# Usage:
#   ./scripts/migrate.sh            # upgrade to head
#   ./scripts/migrate.sh downgrade  # fallback: downgrade one revision
#
# Environment variables required:
#   DATABASE_URL   - PostgreSQL connection string
#
# ─────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$BACKEND_DIR"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "❌  DATABASE_URL is not set"
  exit 1
fi

echo "📦 Running Alembic migrations..."
echo "   Target: ${DATABASE_URL%%@*}@..."

COMMAND="${1:-upgrade}"

case "$COMMAND" in
  upgrade)
    python -m alembic upgrade head
    echo "✅ Migrations applied to HEAD"
    ;;
  downgrade)
    python -m alembic downgrade -1
    echo "✅ Downgraded one revision"
    ;;
  current)
    python -m alembic current
    ;;
  history)
    python -m alembic history --verbose
    ;;
  *)
    echo "Usage: $0 [upgrade|downgrade|current|history]"
    exit 1
    ;;
esac
