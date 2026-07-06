#!/usr/bin/env bash
# Daily entrypoint for the leveraged-ETF bot. Schedule this ~15 min before US market close
# (see live/com.trading.ibsbot.plist). Safe by default: computes + logs the target plan.
set -euo pipefail

REPO="/Users/ajhanwar/Documents/btc-trading-agent"
PY="$REPO/.venv/bin/python"          # <-- point this at your venv's python
cd "$REPO"

# 1) Compute today's target weights and log them. Needs NO Robinhood connection. Always safe.
"$PY" -m live.decide

# 2) LIVE EXECUTION (disabled by default).
#    Enable ONLY after you have: (a) completed live/ROBINHOOD_SETUP.md (opened + funded the
#    Agentic account, ran `claude mcp add robinhood-trading ...`, authenticated), and
#    (b) set PAPER_MODE=False in live/config.py.
#    Then uncomment the line below. It hands the execution recipe to Claude Code headless,
#    which reads the account via the Robinhood MCP and places exactly the orders in orders.json.
#
# claude -p "$(cat "$REPO/live/EXECUTION_PROMPT.md")" \
#     --allowedTools "Bash(python -m live.reconcile),Bash(python -m live.decide),Read,mcp__robinhood-trading__*" \
#     >> "$REPO/live/state/execution.log" 2>&1
