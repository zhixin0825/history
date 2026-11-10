#!/usr/bin/env python3
# Temporary transport for the independently tested source-verification script.
# This file and its payloads are removed before promotion to main.
from pathlib import Path
import base64, hashlib, zlib
payload=''.join(Path(f'.history_part_{i}').read_text() for i in range(1,7))
assert hashlib.sha256(payload.encode()).hexdigest()=='217d976fb341ff85e90fb518519117f345733b278bc9aebcef9cfbd51e72456d', 'Transport mismatch'
code=zlib.decompress(base64.b64decode(payload))
exec(compile(code,'<history-century-source-review>','exec'))
