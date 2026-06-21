#!/usr/bin/env python3
"""SessionStart hook: prune stale per-session state files.

Long-lived machines accumulate armed-gate state files in the data dir; nothing
else GCs them. On every session start we delete per-session JSON state older
than ~24h (by mtime) and exit 0. This is cleanup only -- SessionStart cannot
block, and we never touch the current session's freshly-written state.

Resolution of the data dir mirrors tmt_lib._state_dir so the hooks (running
with the plugin env) and the model-invoked CLI always agree.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tmt_lib as L  # noqa: E402

MAX_AGE_SECONDS = 24 * 60 * 60


def main():
    # Reuse the library's resolution (TMT_DATA override, ~/.tmt fallback).
    try:
        d = L._state_dir(None)
    except OSError:
        sys.exit(0)

    cutoff = time.time() - MAX_AGE_SECONDS
    try:
        names = os.listdir(d)
    except OSError:
        sys.exit(0)

    for name in names:
        if not name.endswith(".json"):
            continue
        p = os.path.join(d, name)
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except OSError:
            continue

    sys.exit(0)


if __name__ == "__main__":
    main()
