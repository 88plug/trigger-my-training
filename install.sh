#!/usr/bin/env bash
# Optional: wire the trigger-my-training status-line badge into Claude Code.
# Plugins cannot register a main `statusLine`, so this merges it into your
# ~/.claude/settings.json (preserving any existing statusLine). Safe to re-run.
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
mkdir -p "$(dirname "$SETTINGS")"
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"

CMD="bash \"$PLUGIN_ROOT/bin/tmt_statusline.sh\""

python3 - "$SETTINGS" "$CMD" <<'PY'
import json, sys, shutil
settings_path, cmd = sys.argv[1], sys.argv[2]
data = json.load(open(settings_path))
prev = data.get("statusLine")
if prev and prev.get("command") and "tmt_statusline" not in prev.get("command", ""):
    print(f"  note: preserving your existing statusLine ({prev.get('command')[:40]}...)")
    print("  trigger-my-training badge not installed (you already have a status line).")
    print("  To use it, set statusLine.command to:", cmd)
    sys.exit(0)
shutil.copyfile(settings_path, settings_path + ".bak")
data["statusLine"] = {"type": "command", "command": cmd, "padding": 0}
json.dump(data, open(settings_path, "w"), indent=2)
print("  installed trigger-my-training status line (backup:", settings_path + ".bak)")
PY

echo "Done. The hard gate and the ground-first reflex work without this — the"
echo "status line is just a live [TMT:armed/grounded] badge."
