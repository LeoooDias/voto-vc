#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Backend: lint ==="
cd "$ROOT/backend"
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/

echo ""
echo "=== Backend: tests ==="
uv run pytest tests/ -v

echo ""
echo "=== Frontend: svelte-check ==="
cd "$ROOT/frontend"
pnpm check

echo ""
echo "=== Frontend: tests ==="
pnpm test

echo ""
echo "All tests passed."
