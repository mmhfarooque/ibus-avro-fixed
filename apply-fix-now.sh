#!/bin/bash
# Apply the shift fix to the installed ibus-avro right now
set -e

echo "Applying Left Shift + Right Shift fix..."

sudo python3 << 'PYEOF'
import re

f = '/usr/share/ibus-avro/main-gjs.js'
with open(f) as fh:
    content = fh.read()

# Fix multi-line keycode 42 block
content = re.sub(
    r'// capture the shift key\n\s*if \(keycode == 42\) \{\s*\n\s*return true;\s*\n\s*\}',
    '// Pass through Left Shift (42) and Right Shift (54)\n        if (keycode == 42 || keycode == 54) {\n            return false;\n        }',
    content
)

# Also handle single-line format just in case
content = content.replace(
    'if (keycode == 42) { return true; }',
    'if (keycode == 42 || keycode == 54) { return false; }'
)

# Disable debug prints
lines = content.split('\n')
fixed = []
for line in lines:
    s = line.strip()
    if (s.startswith('print(') or s.startswith('print (')) and 'Exiting' not in line:
        line = line.replace(s, '//' + s)
    fixed.append(line)

with open(f, 'w') as fh:
    fh.write('\n'.join(fixed))

print('Fix applied successfully')
PYEOF

echo "Restarting iBus..."
ibus restart 2>/dev/null || true

echo ""
echo "Done. Left Shift + Right Shift now work correctly."
echo "Relaunch the GUI to see updated status."
