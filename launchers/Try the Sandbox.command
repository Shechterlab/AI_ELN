#!/bin/bash
# Double-click me: the same page as "Open ELN", but on the fictional practice record in sandbox/.
cd "$(dirname "$0")/.." || exit 1
if ! python3 --version >/dev/null 2>&1; then
  echo "Python 3 is needed. If a window just offered to install 'command line"
  echo "developer tools', click Install (one time), then double-click me again."
  read -r -p "Press Enter to close."
  exit 1
fi
python3 scripts/eln_web.py --root sandbox --port 8766
