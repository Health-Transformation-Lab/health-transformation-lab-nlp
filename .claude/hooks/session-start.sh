#!/bin/bash
# Cloud sessions start on a fresh container: install the Python dev dependencies and the
# Superpowers plugin that .claude/settings.json enables (see CLAUDE.md "Setup for Superpowers").
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR/python"
python -m pip install -q -e ".[dev]"

if ! grep -q '"superpowers@claude-plugins-official"' "$HOME/.claude/plugins/installed_plugins.json" 2>/dev/null; then
  claude plugin install superpowers@claude-plugins-official >/dev/null 2>&1 \
    || echo "session-start: could not install superpowers; run /plugin install superpowers@claude-plugins-official" >&2
fi
