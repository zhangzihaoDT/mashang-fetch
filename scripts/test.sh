#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for c in "$ROOT/.venv/bin/python" "$ROOT/venv/bin/python"; do
  if [[ -x "$c" ]]; then
    exec "$c" -m unittest discover -s "$ROOT/tests" -t "$ROOT" -v
  fi
done

exec python3 -m unittest discover -s "$ROOT/tests" -t "$ROOT" -v
